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
#: Problems below this many native input bytes run 12 items per GPU under the
#: trimming rule (measured in job 548 up to 0.54 GB); larger shared-class problems
#: run 4 per GPU (as in job 518), exclusive ones alone.
CONCURRENCY_BELOW_BYTES = 600_000_000


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


#: Native-size input draws per item, from the gate and channel code (preregistration
#: sections 5-6): gate (a) variants run 5 KernelBench trials; b1/b2 replay b0's 5
#: calls and draw once more; c draws its c1 configs plus two draws per c2/c3 shape;
#: A1 5, A2 7, A3 5, A4 2, A5 about 6; the poison and sanitizer probes 2 and 1.
DRAWS = {
    "a": 5,
    "a_1e-3": 5,
    "a_head_1e-4": 5,
    "a_head_1e-2": 5,
    "a_static": 5,
    "b1": 6,
    "b2": 6,
    "c": 20,
    "A1": 5,
    "A2": 7,
    "A3": 5,
    "A4": 2,
    "A4_poison": 2,
    "A4_sanitizer": 1,
    "A5": 6,
}


def _gigabytes(problem_id: str | None) -> float:
    from harness.q1 import pilot

    if not problem_id:
        return 0.0
    return (pilot.native_input_bytes(problem_id) or 0) / 1e9


def fit_item_costs(items: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per gate, GPU-seconds of an item as ``alpha + beta * GB`` (native input GB).

    Least squares over the gate's final scored items when they span problems more
    than 1 GB apart; otherwise ``beta`` comes from the pooled per-draw slope of the
    gates that do (scaled by ``DRAWS``), and ``alpha`` is the gate's mean residual.
    ``beta`` is never negative.
    """
    by_gate: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for item in items:
        if item["final"] and item["gate"] in SCORING_GATES and item["gpu_seconds"] is not None:
            by_gate[item["gate"]].append((_gigabytes(item.get("problem_id")), item["gpu_seconds"]))
    fits: dict[str, dict[str, Any]] = {}
    per_draw: list[float] = []
    for gate, points in by_gate.items():
        xs = [x for x, _ in points]
        if len(points) >= 3 and max(xs) - min(xs) > 1.0:
            mx, my = statistics.fmean(xs), statistics.fmean(y for _, y in points)
            sxx = sum((x - mx) ** 2 for x in xs)
            beta = max(0.0, sum((x - mx) * (y - my) for x, y in points) / sxx)
            alpha = max(0.0, my - beta * mx)
            fits[gate] = {"alpha": alpha, "beta": beta, "n": len(points), "method": "fit"}
            per_draw.append(beta / DRAWS[gate])
    slope = statistics.median(per_draw) if per_draw else None
    for gate, points in by_gate.items():
        if gate in fits:
            continue
        beta = (slope or 0.0) * DRAWS[gate]
        alpha = max(0.0, statistics.fmean(y - beta * x for x, y in points))
        fits[gate] = {
            "alpha": alpha,
            "beta": beta,
            "n": len(points),
            "method": "per-draw-slope" if slope is not None else "mean-no-slope",
        }
    for fit in fits.values():
        fit["alpha"] = round(fit["alpha"], 3)
        fit["beta"] = round(fit["beta"], 3)
    return fits


def _s2_family(substrate_id: str) -> str:
    return substrate_id.removeprefix("s2-").split("-L1-", 1)[0]


def project_scoring(
    counts: Mapping[str, Any],
    fits: Mapping[str, Mapping[str, Any]],
    *,
    cap: int,
    survival: float,
    seeds: int = SEEDS,
    mutant_seeds: int | None = None,
    control_seeds: int | None = None,
    scope: str = "all",
    hack_fraction: float = 1.0,
) -> dict[str, Any]:
    """Stage 0 scoring GPU-seconds from per-problem kernel counts and the size model.

    A trimming rule may score mutants (``mutant_seeds``) or controls
    (``control_seeds``) at fewer replicates than substrates (``seeds``), restrict
    the problems to the shared input-size class (``scope="shared"``: native inputs
    below 1 GB), and score each hack-control kind on a deterministic fraction of
    the substrates (``hack_fraction``). Every kernel scored keeps every gate."""
    from harness.q1 import pilot

    if scope not in {"all", "shared"}:
        raise ValueError("scope must be all or shared")
    missing = [g for g in SCORING_GATES if g not in fits]
    alpha = sum(fits[g]["alpha"] for g in SCORING_GATES if g in fits)
    beta = sum(fits[g]["beta"] for g in SCORING_GATES if g in fits)
    mutant_seeds = seeds if mutant_seeds is None else mutant_seeds
    control_seeds = seeds if control_seeds is None else control_seeds
    seconds: Counter[str] = Counter()
    kernels: Counter[str] = Counter()
    per_family: Counter[str] = Counter()
    s1_units: set[str] = set()
    s2_units: set[str] = set()

    def in_scope(exclusive: bool) -> bool:
        return scope == "all" or not exclusive

    def add(role: str, problem_id: str, n: float, replicates: int) -> None:
        if n <= 0:
            return
        kernels[role] += n
        seconds[role] += n * replicates * (alpha + beta * _gigabytes(problem_id))

    for row in counts["evaluation_substrates"]:
        if not in_scope(row["exclusive"]):
            continue
        by_family = row.get("cpu_distinct_by_family") or {}
        families = [f for f in MUTATION_FAMILIES if by_family.get(f)]
        sizes = [max(0, round(by_family[f] * survival)) for f in families]
        alloc = waterfill(sizes, cap) if sizes else []
        for family, k in zip(families, alloc, strict=True):
            per_family[family] += k
        add("substrate", row["problem_id"], 1, seeds)
        add("mutant", row["problem_id"], sum(alloc), mutant_seeds)
        add("hack-control", row["problem_id"], row["hack_controls"] * hack_fraction, control_seeds)
        if row["source_kind"] == "inductor":
            s1_units.add(row["problem_id"])
        else:
            s2_units.add(_s2_family(row["substrate_id"]))
    for row in counts["identity_controls"]:
        if in_scope(row["exclusive"]):
            add("identity-control", row["problem_id"], 1, control_seeds)
    fixed_controls = (
        (
            "adversarial-control",
            "L1/1_Square_matrix_multiplication_",
            int(counts.get("adversarial_controls", 3)),
        ),
        ("mutant-control", "L1/19_ReLU", int(counts.get("hack_emulating_mutant_controls", 5))),
    )
    for role, problem_id, n in fixed_controls:
        if in_scope(pilot.exclusive_problem(problem_id)):
            add(role, problem_id, n, control_seeds)
    units = len(s1_units) + len(s2_units)
    return {
        "rule": {
            "scope": scope,
            "cap": cap,
            "substrate_seeds": seeds,
            "mutant_seeds": mutant_seeds,
            "control_seeds": control_seeds,
            "hack_fraction": hack_fraction,
        },
        "cap": cap,
        "seeds": seeds,
        "mutant_seeds": mutant_seeds,
        "kernels": {k: round(v, 1) for k, v in kernels.items()},
        "mutants_per_family": dict(per_family),
        "n_eval_independent": units,
        "frr_upper_bound_at_zero_rejections": None
        if not units
        else round(1 - 0.025 ** (1 / units), 4),
        "gpu_hours_by_role": {k: round(v / 3600, 3) for k, v in seconds.items()},
        "gpu_hours": round(sum(seconds.values()) / 3600, 3),
        "missing_gates": missing,
    }


def bootstrap_projection(
    items: Sequence[Mapping[str, Any]],
    kinds: Mapping[str, Mapping[str, Any]],
    counts: Mapping[str, Any],
    *,
    cap: int,
    survival: float,
    mutant_seeds: int | None = None,
    resamples: int = 1000,
    seed: int = 0,
    **rule: Any,
) -> dict[str, float | None]:
    """Cluster bootstrap of the projection over pilot parent substrates (each with
    its mutants and controls), refitting the size model in each resample."""
    clusters: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for item in items:
        parent = kinds.get(item["kernel_id"], {}).get("parent", item["kernel_id"])
        clusters[parent].append(item)
    keys = sorted(clusters)
    if len(keys) < 2:
        return {"low": None, "high": None}
    rng = random.Random(seed)
    totals = []
    for _ in range(resamples):
        sample = [i for _ in keys for i in clusters[rng.choice(keys)]]
        fits = fit_item_costs(sample)
        totals.append(
            project_scoring(
                counts, fits, cap=cap, survival=survival, mutant_seeds=mutant_seeds, **rule
            )["gpu_hours"]
        )
    return {"low": _quantile(totals, 0.025), "high": _quantile(totals, 0.975)}


# --- censored items, paired jobs and the trimming rule ---------------------------


def censored_items(job_dir: Path) -> list[dict[str, Any]]:
    """Items a time box killed before they wrote any journal row (lower bounds).

    The runner never journals an item it kills at the hard deadline, so its
    GPU time would vanish from the card. Each such item left an item directory
    with ``item.json`` and no journal row; it ran at least from that file's
    mtime to the phase's ``summary.json`` mtime (written when the runner
    returned). Exclusive items held the GPU alone, so for them this is GPU
    time; shared items are listed with their raw wall time only.
    """
    root = Path(job_dir)
    out: list[dict[str, Any]] = []
    for journal in sorted(root.glob("*/journal.jsonl")):
        phase_dir = journal.parent
        summary = phase_dir / "summary.json"
        if not summary.exists():
            continue
        journaled = set()
        for line in journal.read_text(encoding="utf-8").splitlines():
            if line.strip():
                journaled.add(json.loads(line)["details"]["item_key"])
        for item_path in sorted(phase_dir.glob("items/*/item.json")):
            item = json.loads(item_path.read_text(encoding="utf-8"))
            if item.get("item_key") in journaled:
                continue
            wall = summary.stat().st_mtime - item_path.stat().st_mtime
            exclusive = bool(item.get("exclusive"))
            out.append(
                {
                    "phase": phase_dir.name,
                    "item_key": item.get("item_key"),
                    "gate": item.get("gate"),
                    "problem_id": item.get("problem_id"),
                    "exclusive": exclusive,
                    "wall_seconds_lower_bound": round(wall, 1),
                    "gpu_seconds_lower_bound": round(wall, 1) if exclusive else None,
                }
            )
    return out


def pair_jobs(
    base: Sequence[Mapping[str, Any]], other: Sequence[Mapping[str, Any]], *, phase: str = "scoring"
) -> dict[str, Any]:
    """Item-by-item comparison of two runs of the same items (same keys).

    Per gate: the median ratio of GPU-seconds and of raw wall seconds
    (``other / base``) over items final in both, and whether each item's
    verdict multiset is identical. A concurrency change must not change a
    verdict; any difference is listed.
    """

    def finals(items: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
        return {
            i["item_key"]: i
            for i in items
            if i["phase"] == phase and i["final"] and i["gpu_seconds"] is not None
        }

    left, right = finals(base), finals(other)
    common = sorted(set(left) & set(right))
    by_gate: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    differences = []
    for key in common:
        a, b = left[key], right[key]
        gate = a["gate"]
        if a["gpu_seconds"] > 0:
            by_gate[gate]["gpu"].append(b["gpu_seconds"] / a["gpu_seconds"])
        if a["wall"]:
            by_gate[gate]["wall"].append((b["wall"] or 0.0) / a["wall"])
        by_gate[gate]["base_gpu"].append(a["gpu_seconds"])
        by_gate[gate]["other_gpu"].append(b["gpu_seconds"])
        if dict(a["verdicts"]) != dict(b["verdicts"]):
            differences.append(
                {"item_key": key, "base": dict(a["verdicts"]), "other": dict(b["verdicts"])}
            )
    gates = {
        gate: {
            "n": len(v["gpu"]),
            "gpu_seconds_ratio_median": round(statistics.median(v["gpu"]), 3) if v["gpu"] else None,
            "wall_ratio_median": round(statistics.median(v["wall"]), 3) if v["wall"] else None,
            "base_gpu_seconds_sum": round(sum(v["base_gpu"]), 2),
            "other_gpu_seconds_sum": round(sum(v["other_gpu"]), 2),
        }
        for gate, v in sorted(by_gate.items())
    }
    base_sum = sum(left[k]["gpu_seconds"] for k in common)
    other_sum = sum(right[k]["gpu_seconds"] for k in common)
    return {
        "items_in_both": len(common),
        "only_base": len(set(left) - set(right)),
        "only_other": len(set(right) - set(left)),
        "gpu_seconds_base": round(base_sum, 1),
        "gpu_seconds_other": round(other_sum, 1),
        "gpu_seconds_ratio_total": round(other_sum / base_sum, 3) if base_sum else None,
        "per_gate": gates,
        "verdict_differences": differences,
    }


#: The proposed trimming rule (``q1-stage0-trim/1``), as drafted for the
#: preregistration (section 18): every gate, family, contract tier and TF32
#: policy is kept; what shrinks is which problems and kernels are scored, and at
#: how many replicates.
TRIM_RULE: dict[str, Any] = {
    "name": "q1-stage0-trim/1",
    "scope_bytes": 1_000_000_000,
    "frr_min_units": 72,
    "family_quota_test": 60,
    "family_quota_test_max": 120,
    "family_quota_dev": 15,
    "cap": 40,
    "mutant_robustness_fraction": 0.1,
    "substrate_seeds": 3,
    "identity_seeds": 1,
    "hack_fraction": 0.15,
    "hack_seeds": 3,
    "adversarial_seeds": 3,
    "fidelity_mutants_per_family_tier": 1,
    "timing_floor_items": 80,
    "slots_per_gpu": {"below_0.6_GB": 12, "0.6_to_1_GB": 4, "from_1_GB": "alone"},
    "priority": [
        "P1 substrates at replicate 42 (in scope and FRR set), every control at replicate 42",
        "P2 test-quota mutants at replicate 42",
        "P3 hack-emulating and adversarial controls at replicates 43 and 44",
        "P4 in-scope substrates at replicates 43 and 44",
        "P5 the mutant robustness subsample at replicates 43 and 44",
        "P6 dev-quota mutants at replicate 42",
        "P7 further test-split mutants up to family_quota_test_max per family, one family at a"
        " time in a seeded round-robin order, at replicate 42, until the stop",
    ],
    "stop": "no item starts once the Stage 0 GPU-hours (every job, pilot included) reach 8.0",
}


def _unit(row: Mapping[str, Any]) -> str:
    return (
        row["problem_id"]
        if row["source_kind"] == "inductor"
        else "s2:" + _s2_family(row["substrate_id"])
    )


def kernel_replicate_seconds(
    fits: Mapping[str, Mapping[str, Any]],
    problem_id: str,
    *,
    factors: Mapping[str, float] | None = None,
    gates: Sequence[str] = SCORING_GATES,
    factor_below_bytes: int = CONCURRENCY_BELOW_BYTES,
) -> float:
    """Size-model GPU-seconds of one kernel at one replicate (every scoring gate).

    ``factors`` (per gate) scale problems whose native inputs are below
    ``factor_below_bytes`` only, as measured by a paired re-run at another
    concurrency (the largest problem in that re-run had 0.54 GB of inputs);
    larger shared problems keep the measured 4-per-GPU cost and exclusive
    problems run alone.
    """
    from harness.q1 import pilot

    shared = (pilot.native_input_bytes(problem_id) or 0) < factor_below_bytes
    gb = _gigabytes(problem_id)
    total = 0.0
    for gate in gates:
        fit = fits.get(gate)
        if fit is None:
            continue
        seconds = fit["alpha"] + fit["beta"] * gb
        if shared and factors and gate in factors:
            seconds *= factors[gate]
        total += seconds
    return total


def project_trimmed(
    counts: Mapping[str, Any],
    fits: Mapping[str, Mapping[str, Any]],
    *,
    survival: float,
    rule: Mapping[str, Any] = TRIM_RULE,
    factors: Mapping[str, float] | None = None,
    witness_rate: float = 0.5,
) -> dict[str, Any]:
    """Scoring GPU-hours, kernel counts and precision under the trimming rule.

    - **Scope.** Mutants, hack-emulating controls, identity controls, the
      KernelBench adversarial controls and replicates 43/44 only on problems
      whose native inputs are below ``scope_bytes`` (the pilot's shared class).
    - **FRR set.** The in-scope evaluation substrates, plus the out-of-scope ones
      in ascending native input bytes (ties by substrate id) until
      ``n_eval_independent`` reaches ``frr_min_units``; those extra substrates
      are scored at replicate 42 only (criterion 3 is at replicate 42).
    - **Mutants.** Per family, a simple random sample without replacement of
      ``family_quota_test`` test-split and ``family_quota_dev`` dev-split
      mutants from the capped (cap 40, cap seed 42) mutants of in-scope
      evaluation parents (all of them where fewer exist), at replicate 42; a
      ``mutant_robustness_fraction`` subsample of the test ones also at 43 and
      44; then (P7, cut by the budget stop) further test-split mutants up to
      ``family_quota_test_max`` per family. Expected cost uses the family's
      frame (each parent's capped allocation).
    - **Controls.** Identity controls at ``identity_seeds`` replicates; each
      hack-control kind on a ``hack_fraction`` sample of its applicable
      in-scope substrates at ``hack_seeds`` replicates; adversarial controls at
      ``adversarial_seeds``.
    """
    scope = int(rule["scope_bytes"])
    rows = counts["evaluation_substrates"]

    def bytes_of(row: Mapping[str, Any]) -> int:
        return int(row.get("native_input_bytes") or 0)

    def cost(problem_id: str) -> float:
        return kernel_replicate_seconds(fits, problem_id, factors=factors)

    in_scope = [r for r in rows if bytes_of(r) < scope]
    units = {_unit(r) for r in in_scope}
    frr_extra = []
    for row in sorted(
        (r for r in rows if bytes_of(r) >= scope), key=lambda r: (bytes_of(r), r["substrate_id"])
    ):
        if len(units) >= int(rule["frr_min_units"]):
            break
        frr_extra.append(row)
        units.add(_unit(row))
    seconds: Counter[str] = Counter()
    priority: Counter[str] = Counter()
    kernels: Counter[str] = Counter()

    def add(role: str, bucket: str, value: float) -> None:
        seconds[role] += value
        priority[bucket] += value

    extra_seeds = int(rule["substrate_seeds"]) - 1
    for row in in_scope:
        add("substrate", "P1", cost(row["problem_id"]))
        add("substrate", "P4", extra_seeds * cost(row["problem_id"]))
        kernels["substrate"] += 1
    for row in frr_extra:
        add("frr-substrate-replicate-42", "P1", cost(row["problem_id"]))
        kernels["frr-substrate-replicate-42"] += 1
    # Mutant frame: each in-scope parent's capped allocation per family.
    frame: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for row in in_scope:
        by_family = row.get("cpu_distinct_by_family") or {}
        families = [f for f in MUTATION_FAMILIES if by_family.get(f)]
        sizes = [max(0, round(by_family[f] * survival)) for f in families]
        alloc = waterfill(sizes, int(rule["cap"])) if sizes else []
        for family, k in zip(families, alloc, strict=True):
            if k:
                frame[family].append((row["problem_id"], float(k)))
    per_family: dict[str, dict[str, Any]] = {}
    robustness = float(rule["mutant_robustness_fraction"])
    for family in MUTATION_FAMILIES:
        entries = frame.get(family, [])
        available = sum(k for _, k in entries)
        test = min(float(rule["family_quota_test"]), available / 2)
        dev = min(float(rule["family_quota_dev"]), available / 2)
        mean_cost = sum(k * cost(p) for p, k in entries) / available if available else 0.0
        extra = max(0.0, min(float(rule.get("family_quota_test_max", 0)), available / 2) - test)
        add("mutant", "P2", test * mean_cost)
        add("mutant", "P5", 2 * robustness * test * mean_cost)
        add("mutant", "P6", dev * mean_cost)
        add("mutant-extension", "P7", extra * mean_cost)
        kernels["mutant"] += test + dev
        kernels["mutant-extension"] += extra
        witnessed = test * witness_rate
        per_family[family] = {
            "capped_frame": round(available),
            "test": round(test),
            "test_extension_max": round(extra),
            "dev": round(dev),
            "witnessed_test_planning": round(witnessed),
            "half_width_pp": None
            if witnessed < 1
            else round(100 * half_width(round(witnessed)), 1),
        }
    identity_seeds = int(rule["identity_seeds"])
    for row in counts["identity_controls"]:
        if not row["exclusive"]:
            add("identity-control", "P1", cost(row["problem_id"]))
            add("identity-control", "P3", (identity_seeds - 1) * cost(row["problem_id"]))
            kernels["identity-control"] += 1
    hack = float(rule["hack_fraction"])
    for row in in_scope:
        n = row["hack_controls"] * hack
        add("hack-control", "P1", n * cost(row["problem_id"]))
        add("hack-control", "P3", n * (int(rule["hack_seeds"]) - 1) * cost(row["problem_id"]))
        kernels["hack-control"] += n
    adversarial = int(counts.get("adversarial_controls", 3))
    adversarial_cost = adversarial * cost("L1/1_Square_matrix_multiplication_")
    add("adversarial-control", "P1", adversarial_cost)
    add("adversarial-control", "P3", (int(rule["adversarial_seeds"]) - 1) * adversarial_cost)
    kernels["adversarial-control"] += adversarial
    pooled = sum(v["witnessed_test_planning"] for v in per_family.values())
    n_units = len(units)
    return {
        "rule": dict(rule),
        "factors": dict(factors) if factors else None,
        "in_scope_substrates": len(in_scope),
        "frr_extra_substrates": [r["substrate_id"] for r in frr_extra],
        "n_eval_independent": n_units,
        "frr_upper_bound_at_zero_rejections": round(1 - 0.025 ** (1 / n_units), 4)
        if n_units
        else None,
        "kernels": {k: round(v, 1) for k, v in kernels.items()},
        "mutants_per_family": per_family,
        "pooled_witnessed_test_planning": pooled,
        "pooled_half_width_pp": None if not pooled else round(100 * half_width(pooled, p=0.17), 1),
        "detectable_difference_pp": None
        if not pooled
        else round(100 * detectable_difference(pooled), 1),
        "families_with_30_witnessed_test": sum(
            1 for v in per_family.values() if v["witnessed_test_planning"] >= 30
        ),
        "gpu_hours_by_role": {k: round(v / 3600, 3) for k, v in seconds.items()},
        "gpu_hours_by_priority": {k: round(priority[k] / 3600, 3) for k in sorted(priority)},
        "gpu_hours": round(sum(seconds.values()) / 3600, 3),
    }


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
    "TRIM_RULE",
    "censored_items",
    "kernel_replicate_seconds",
    "pair_jobs",
    "project_trimmed",
    "DRAWS",
    "bootstrap_projection",
    "fit_item_costs",
    "project_scoring",
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
