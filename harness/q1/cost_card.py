"""Q1 Stage 0 pilot cost card (preregistration section 10): measured costs and projection.

Pure Python. Inputs are the pilot jobs' journals (every row carries the
runner's ``item_started_at``/``item_ended_at``/``item_wall_seconds``), their
``phases.json`` (the GPU is held for the whole job, so phase wall time is GPU
allocation time), the pilot corpus (to classify kernels) and the planning
counts of the full Stage 0 corpus (``scripts/q1_stage0_counts.py``).

**GPU-seconds of an item.** Items of one job share one GPU, sometimes several
at once. An item is charged its share of the allocation while it runs: the
integral over its lifetime of ``1 / (items running at that moment)``. Raw
spawn-to-verdict seconds are reported too. With one item at a time the two
are equal (the definition in section 7.1).

**Projection.** A kernel's cost is driven by its problem's input size, so the
per-kernel-replicate cost (all 15 scoring items) is averaged inside cost
classes ``(level, exclusive)`` (exclusive = native inputs of at least 1 GB, run
alone on the GPU), pooling substrates, mutants and controls of the class; the
Stage 0 kernel counts per class times 3 replicates times the class mean is the
scoring cost. Fixed phases are measured per unit and scaled to the full
corpus; two are not measured by the pilot and carry the draft's estimates
(timing noise floor, audit-hole replay), labelled as such. A cluster
bootstrap over pilot parent substrates (each with its own mutants and
controls) gives an interval.
"""

from __future__ import annotations

import json
import math
import random
import statistics
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from harness.q1.mutate.sampling import waterfill
from harness.q1.schema import MUTATION_FAMILIES, iter_kernel_dirs, parse_problem_id

SCORING_GATES = (
    "a",
    "a_1e-3",
    "a_head_1e-4",
    "a_head_1e-2",
    "a_static",
    "b1",
    "b2",
    "c",
    "A1",
    "A2",
    "A3",
    "A4",
    "A4_poison",
    "A4_sanitizer",
    "A5",
)
RUNGS = {
    "a": ("a",),
    "b_marginal": ("b1", "b2"),
    "c_marginal": ("c",),
    "audit": ("A1", "A2", "A3", "A4", "A4_poison", "A4_sanitizer", "A5"),
    "a_secondaries": ("a_1e-3", "a_head_1e-4", "a_head_1e-2", "a_static"),
}
CAP_GPU_HOURS = 8.0
SEEDS = 3


# --- loading -------------------------------------------------------------------


def _quantile(values: Sequence[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = q * (len(ordered) - 1)
    low, high = math.floor(position), math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def summarize(values: Sequence[float]) -> dict[str, Any]:
    return {
        "n": len(values),
        "mean": round(statistics.fmean(values), 3) if values else None,
        "median": round(_quantile(values, 0.5), 3) if values else None,
        "p95": round(_quantile(values, 0.95), 3) if values else None,
        "max": round(max(values), 3) if values else None,
        "sum": round(sum(values), 3),
    }


def load_job(job_dir: Path) -> dict[str, Any]:
    """One lane job's driver output (``<run_dir>/q1``): phases and items."""
    root = Path(job_dir)
    phases = json.loads((root / "phases.json").read_text())
    items: dict[tuple[str, str, int], dict[str, Any]] = {}
    for journal in sorted(root.glob("*/journal.jsonl")):
        phase = journal.parent.name
        problems = {}
        planned = journal.parent / "items.jsonl"
        if planned.exists():
            for line in planned.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    entry = json.loads(line)
                    key = f"{entry['kernel_id']}|{entry['gate']}|seed-{entry['seed']}"
                    problems[key] = entry["problem_id"]
        for line in journal.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            details = row["details"]
            key = (phase, details["item_key"], int(row.get("attempt") or 1))
            kernel_id, gate, seed = details["item_key"].rsplit("|", 2)
            item = items.setdefault(
                key,
                {
                    "phase": phase,
                    "item_key": details["item_key"],
                    "kernel_id": kernel_id,
                    "gate": gate,
                    "seed": int(seed.removeprefix("seed-")),
                    "problem_id": problems.get(details["item_key"]),
                    "attempt": key[2],
                    "start": details.get("item_started_at"),
                    "end": details.get("item_ended_at"),
                    "wall": details.get("item_wall_seconds"),
                    "exclusive": details.get("item_exclusive"),
                    "final": False,
                    "verdicts": Counter(),
                    "reasons": Counter(),
                },
            )
            item["verdicts"][row["verdict"]] += 1
            if details.get("reason"):
                item["reasons"][str(details["reason"])[:80]] += 1
            if details.get("item_final"):
                item["final"] = True
    listed = list(items.values())
    charge(listed)
    return {"dir": str(root), "phases": phases, "items": listed}


def charge(items: list[dict[str, Any]]) -> None:
    """Apportion the GPU among concurrently running items (sweep line)."""
    timed = [i for i in items if i["start"] is not None and i["end"] is not None]
    events = sorted({t for i in timed for t in (i["start"], i["end"])})
    for item in items:
        item["gpu_seconds"] = 0.0 if item in timed else None
    if len(events) < 2:
        return
    for left, right in zip(events, events[1:], strict=False):
        active = [i for i in timed if i["start"] <= left and i["end"] >= right]
        if active:
            share = (right - left) / len(active)
            for item in active:
                item["gpu_seconds"] += share


# --- classification and per-gate statistics ------------------------------------


def classify(corpus_root: Path | None) -> dict[str, dict[str, Any]]:
    """kernel_id -> {kind, role, problem_id, parent, family} from the pilot corpus."""
    out: dict[str, dict[str, Any]] = {}
    if corpus_root is None:
        return out
    folders = {
        "pilot-substrates": "substrate",
        "pilot-calibration": "calibration-substrate",
        "mutants": "mutant",
        "controls-hacks": "hack-control",
        "controls-mutants": "mutant-control",
        "controls-core": "core-control",
    }
    for folder, role in folders.items():
        path = Path(corpus_root) / folder
        if not path.is_dir():
            continue
        for kernel in iter_kernel_dirs(path):
            parent = kernel.kernel_id
            if kernel.mutation:
                parent = kernel.mutation["parent_substrate_id"]
            elif role in {"hack-control", "mutant-control"}:
                parent = kernel.kernel_id.split(".", 1)[0]
            out[kernel.kernel_id] = {
                "role": role
                if not (kernel.control and kernel.control["control_kind"] == "reference-identity")
                else "identity-control",
                "problem_id": kernel.problem_id,
                "parent": parent,
                "family": (kernel.mutation or {}).get("family"),
            }
    return out


def cost_class(problem_id: str, exclusive: bool) -> str:
    level = parse_problem_id(problem_id)[0]
    return f"L{level}-{'exclusive' if exclusive else 'shared'}"


def gate_stats(items: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    by_gate: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for item in items:
        if item["final"]:
            by_gate[item["gate"]].append(item)
    return {
        gate: {
            "gpu_seconds": summarize(
                [i["gpu_seconds"] for i in rows if i["gpu_seconds"] is not None]
            ),
            "item_wall_seconds": summarize([i["wall"] for i in rows if i["wall"] is not None]),
            "verdicts": dict(sum((i["verdicts"] for i in rows), Counter())),
            "timeouts": sum(1 for i in rows if i["verdicts"].get("timeout")),
            "crash_rows": sum(1 for i in rows if i["reasons"].get("worker-crashed")),
        }
        for gate, rows in sorted(by_gate.items())
    }


def kernel_seed_costs(
    items: Iterable[Mapping[str, Any]], kinds: Mapping[str, Mapping[str, Any]]
) -> list[dict[str, Any]]:
    """Per (kernel, replicate) with every scoring gate final: total and per rung."""
    grouped: dict[tuple[str, int], dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for item in items:
        if item["final"] and item["gate"] in SCORING_GATES and item["gpu_seconds"] is not None:
            grouped[(item["kernel_id"], item["seed"])][item["gate"]] = item
    rows = []
    for (kernel_id, seed), gates in sorted(grouped.items()):
        if set(gates) != set(SCORING_GATES):
            continue
        info = kinds.get(kernel_id, {})
        problem = info.get("problem_id") or next(iter(gates.values())).get("problem_id")
        exclusive = bool(next(iter(gates.values())).get("exclusive"))
        rows.append(
            {
                "kernel_id": kernel_id,
                "seed": seed,
                "role": info.get("role", "unknown"),
                "parent": info.get("parent", kernel_id),
                "problem_id": problem,
                "cost_class": cost_class(problem, exclusive) if problem else "unknown",
                "total": sum(g["gpu_seconds"] for g in gates.values()),
                "wall_total": sum(g["wall"] or 0.0 for g in gates.values()),
                **{
                    rung: sum(gates[g]["gpu_seconds"] for g in members)
                    for rung, members in RUNGS.items()
                },
            }
        )
    return rows


# --- projection ----------------------------------------------------------------


def stage0_kernel_counts(counts: Mapping[str, Any], *, cap: int, survival: float) -> dict[str, Any]:
    """Stage 0 scoring kernels per cost class (one replicate), and per family."""
    from harness.q1 import pilot

    per_class: Counter[str] = Counter()
    per_role: Counter[str] = Counter()
    per_family: Counter[str] = Counter()
    for row in counts["evaluation_substrates"]:
        klass = cost_class(row["problem_id"], row["exclusive"])
        by_family = row.get("cpu_distinct_by_family") or {}
        families = [f for f in MUTATION_FAMILIES if by_family.get(f)]
        sizes = [max(0, round(by_family[f] * survival)) for f in families]
        alloc = waterfill(sizes, cap) if sizes else []
        mutants = sum(alloc)
        for family, k in zip(families, alloc, strict=True):
            per_family[family] += k
        per_class[klass] += 1 + mutants + row["hack_controls"]
        per_role["substrate"] += 1
        per_role["mutant"] += mutants
        per_role["hack-control"] += row["hack_controls"]
    for row in counts["identity_controls"]:
        per_class[cost_class(row["problem_id"], row["exclusive"])] += 1
        per_role["identity-control"] += 1
    adversarial = int(counts.get("adversarial_controls", 3))
    if adversarial:
        klass = cost_class(
            "L1/1_Square_matrix_multiplication_",
            pilot.exclusive_problem("L1/1_Square_matrix_multiplication_"),
        )
        per_class[klass] += adversarial
        per_role["adversarial-control"] += adversarial
    mutant_controls = int(counts.get("hack_emulating_mutant_controls", 5))
    if mutant_controls:
        per_class[cost_class("L1/19_ReLU", True)] += mutant_controls
        per_role["mutant-control"] += mutant_controls
    return {
        "per_class": {k: v for k, v in per_class.items() if v},
        "per_role": dict(per_role),
        "mutants_per_family": dict(per_family),
        "cap": cap,
        "survival": survival,
    }


def class_means(rows: Sequence[Mapping[str, Any]]) -> dict[str, float]:
    by: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        by[row["cost_class"]].append(row["total"])
    return {klass: statistics.fmean(values) for klass, values in by.items()}


def scoring_seconds(
    per_class: Mapping[str, int], means: Mapping[str, float], *, seeds: int = SEEDS
) -> tuple[float, list[str]]:
    """Projected scoring GPU-seconds; classes without pilot data borrow the mean
    of the same exclusivity, else the pooled mean (listed)."""
    pooled = statistics.fmean(means.values()) if means else 0.0
    borrowed = []
    total = 0.0
    for klass, n in per_class.items():
        mean = means.get(klass)
        if mean is None:
            same = [v for k, v in means.items() if k.split("-", 1)[1] == klass.split("-", 1)[1]]
            mean = statistics.fmean(same) if same else pooled
            borrowed.append(klass)
        total += n * seeds * mean
    return total, borrowed


def bootstrap_scoring(
    rows: Sequence[Mapping[str, Any]],
    per_class: Mapping[str, int],
    *,
    resamples: int = 2000,
    seed: int = 0,
) -> dict[str, float | None]:
    clusters: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        clusters[row["parent"]].append(row)
    keys = sorted(clusters)
    if len(keys) < 2:
        return {"low": None, "high": None}
    rng = random.Random(seed)
    totals = []
    for _ in range(resamples):
        sample = [r for _ in keys for r in clusters[rng.choice(keys)]]
        totals.append(scoring_seconds(per_class, class_means(sample))[0])
    return {"low": _quantile(totals, 0.025), "high": _quantile(totals, 0.975)}


def half_width(n: int, p: float = 0.2, design_effect: float = 2.0) -> float | None:
    """95% normal half-width of a miss rate with a cluster design effect (section 9)."""
    if n <= 0:
        return None
    return 1.96 * math.sqrt(p * (1 - p) * design_effect / n)


def detectable_difference(n: int, design_effect: float = 2.0) -> float | None:
    """Section 9's smallest detectable paired difference, 7.84 x deff / n."""
    return 7.84 * design_effect / n if n > 0 else None


__all__ = [
    "CAP_GPU_HOURS",
    "RUNGS",
    "SCORING_GATES",
    "bootstrap_scoring",
    "charge",
    "class_means",
    "classify",
    "cost_class",
    "detectable_difference",
    "gate_stats",
    "half_width",
    "kernel_seed_costs",
    "load_job",
    "scoring_seconds",
    "stage0_kernel_counts",
    "summarize",
]
