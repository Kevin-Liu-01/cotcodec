"""Stage 0 analysis: ladder composition, audit tiers, MS/FAR/FRR/FA-share, cost.

Pure Python (scipy for exact intervals). Inputs are the journal's final rows
(``Journal.final_rows()``) and a kernel table built from the corpus
(``kernel_table``). Definitions follow the preregistration
(``program/preregistrations/q1-stage0-gate-validation.md``, sections 4-6):

- ladder: ``b = a and b1 and b2`` (b1/b2 ``error`` counts as accept, as the
  released check fails open); ``c = b and c1 and c2 and c3``;
  ``c_1e-2 = b and c_1e-2``; ``c_kbv_raw = b and c_kbv_raw``;
- a gate ``timeout`` is a rejection; ``error`` (unrefereeable) removes the
  kernel from that gate's denominators;
- audit channels A1-A3 per TF32 policy from their aggregate rows; A4 is the
  conjunction of the in-process, poison-allocator and sanitizer rows present;
  tiers from ``audit.tiers.tier_verdicts``;
- a mutant is witnessed when the primary audit (tier G, TF32-admissible)
  rejects it; MS = rejected by the gate / witnessed; FAR = 1 - MS;
- FRR over correct substrates (kind substrate, primary audit accepts);
- FA-share = accepted by the gate and audit-rejected / accepted by the gate.
"""

from __future__ import annotations

import random
import statistics
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from harness.q1.audit.tiers import tier_verdicts
from harness.q1.schema import iter_kernel_dirs

SINGLE_ROW_GATES = ("a", "a_1e-3", "a_head_1e-4", "a_head_1e-2", "a_static", "b1", "b2", "b_native")
C_FAMILIES = ("c1", "c2", "c3")
LADDER = ("a", "a_1e-3", "a_head_1e-4", "a_head_1e-2", "a_static", "b", "c", "c_1e-2", "c_kbv_raw")
POLICIES = ("tf32-admissible", "strict-fp32")
PRIMARY_POLICY, PRIMARY_TIER = "tf32-admissible", "G"


def kernel_table(corpus_roots: Iterable[Path]) -> dict[str, dict[str, Any]]:
    """kernel_id -> kind, problem_id, family (mutants), source_kind (substrates/mutants)."""
    table = {}
    for root in corpus_roots:
        for kernel in iter_kernel_dirs(root):
            table[kernel.kernel_id] = {
                "kind": kernel.kind,
                "problem_id": kernel.problem_id,
                "family": (kernel.mutation or {}).get("family"),
                "source_kind": (kernel.substrate or {}).get("source_kind"),
                "control_kind": (kernel.control or {}).get("control_kind"),
            }
    return table


def calibration_split(problem_ids: Iterable[str], seed: int = 42) -> tuple[list[str], list[str]]:
    """S1 calibration split: sort, ``random.Random(seed).shuffle``, first ceil(n/2) calibrate."""
    ordered = sorted(set(problem_ids))
    random.Random(seed).shuffle(ordered)
    half = (len(ordered) + 1) // 2
    return sorted(ordered[:half]), sorted(ordered[half:])


def mutant_split(mutant_ids: Iterable[str], seed: int = 42) -> tuple[list[str], list[str]]:
    """Mutant dev/test split: sort, shuffle with ``random.Random(seed)``, first half dev."""
    ordered = sorted(set(mutant_ids))
    random.Random(seed).shuffle(ordered)
    half = len(ordered) // 2
    return sorted(ordered[:half]), sorted(ordered[half:])


def _gate_verdict(verdict: str) -> str:
    return "reject" if verdict == "timeout" else verdict


def _conjoin(verdicts: Sequence[str]) -> str:
    for verdict in ("reject", "error"):
        if verdict in verdicts:
            return verdict
    return "accept" if verdicts else "error"


def compose(rows: Iterable[Mapping[str, Any]], *, seed: int = 42) -> dict[str, dict[str, Any]]:
    """Per kernel: gate ladder verdicts and audit tiers (both policies) for one replicate."""
    by_kernel: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("seed", 42) == seed:
            by_kernel[row["kernel_id"]].append(row)
    out: dict[str, dict[str, Any]] = {}
    for kernel_id, kernel_rows in by_kernel.items():
        gates: dict[str, str] = {}
        audit: dict[str, dict[str, str]] = {policy: {} for policy in POLICIES}
        a4_parts: list[str] = []
        fail_open: list[str] = []
        for row in kernel_rows:
            gate, config, verdict = row["gate"], row["config_id"], row["verdict"]
            item_level = config.startswith("item/")  # runner timeout or crash row
            if gate in SINGLE_ROW_GATES:
                gates[gate] = _gate_verdict(verdict)
            elif gate == "c" and item_level:
                for family in (*C_FAMILIES, "c_1e-2", "c_kbv_raw"):
                    gates[family] = _gate_verdict(verdict)
            elif gate in (*C_FAMILIES, "c_1e-2", "c_kbv_raw") and config == "aggregate":
                gates[gate] = verdict
            elif gate in {"A1", "A2", "A3"}:
                if item_level:
                    for policy in POLICIES:
                        audit[policy][gate] = "reject" if verdict == "timeout" else verdict
                elif config == "aggregate":
                    audit[row["tf32_policy"]][gate] = verdict
            elif gate in {"A4", "A4_poison", "A4_sanitizer"}:
                a4_parts.append("reject" if verdict == "timeout" else verdict)
        for name in ("b1", "b2"):
            if gates.get(name) == "error":
                fail_open.append(name)
        b_parts = [gates.get("a", "error")] + [
            "accept" if gates.get(name) == "error" else gates.get(name, "error")
            for name in ("b1", "b2")
        ]
        ladder = {
            name: gates.get(name, "error")
            for name in ("a", "a_1e-3", "a_head_1e-4", "a_head_1e-2", "a_static")
        }
        ladder["b"] = _conjoin(b_parts)
        ladder["c"] = _conjoin([ladder["b"], *(gates.get(f, "error") for f in C_FAMILIES)])
        ladder["c_1e-2"] = _conjoin([ladder["b"], gates.get("c_1e-2", "error")])
        ladder["c_kbv_raw"] = _conjoin([ladder["b"], gates.get("c_kbv_raw", "error")])
        a4 = _conjoin(a4_parts) if a4_parts else "error"
        tiers = {}
        for policy in POLICIES:
            channels = {**audit[policy], "A4": a4}
            tiers[policy] = tier_verdicts(channels)
        out[kernel_id] = {
            "gates": gates,
            "ladder": ladder,
            "audit": audit,
            "A4": a4,
            "tiers": tiers,
            "b_fail_open": fail_open,
        }
    return out


def clopper_pearson(k: int, n: int, level: float = 0.95) -> list[float]:
    from scipy.stats import beta

    if n == 0:
        return [0.0, 1.0]
    alpha = 1 - level
    lo = 0.0 if k == 0 else float(beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - alpha / 2, k + 1, n - k))
    return [lo, hi]


def cluster_bootstrap(
    units: Sequence[tuple[str, int, int]], *, resamples: int = 10_000, seed: int = 0
) -> list[float] | None:
    """95% percentile CI of sum(k)/sum(n) resampling problems (clusters) with replacement.

    ``units`` holds (problem_id, k, n) per kernel.
    """
    clusters: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for problem, k, n in units:
        clusters[problem][0] += k
        clusters[problem][1] += n
    keys = sorted(clusters)
    if not keys:
        return None
    rng = random.Random(seed)
    stats = []
    for _ in range(resamples):
        k = n = 0
        for _ in keys:
            ck, cn = clusters[keys[rng.randrange(len(keys))]]
            k += ck
            n += cn
        if n:
            stats.append(k / n)
    stats.sort()
    if not stats:
        return None
    return [stats[int(0.025 * len(stats))], stats[min(len(stats) - 1, int(0.975 * len(stats)))]]


def _rate(units: list[tuple[str, int, int]], resamples: int) -> dict[str, Any]:
    k = sum(u[1] for u in units)
    n = sum(u[2] for u in units)
    return {
        "k": k,
        "n": n,
        "rate": (k / n) if n else None,
        "clopper_pearson": clopper_pearson(k, n),
        "cluster_bootstrap": cluster_bootstrap(units, resamples=resamples),
    }


def metrics(
    composed: Mapping[str, Mapping[str, Any]],
    table: Mapping[str, Mapping[str, Any]],
    *,
    policy: str = PRIMARY_POLICY,
    tier: str = PRIMARY_TIER,
    evaluation_substrates: set[str] | None = None,
    resamples: int = 10_000,
) -> dict[str, Any]:
    """MS, FAR, FA-share over mutants and FRR over correct substrates, per ladder gate."""
    out: dict[str, Any] = {"policy": policy, "tier": tier, "gates": {}}
    mutants = [k for k, v in table.items() if v["kind"] == "mutant" and k in composed]
    substrates = [k for k, v in table.items() if v["kind"] == "substrate" and k in composed]
    if evaluation_substrates is not None:
        substrates = [k for k in substrates if k in evaluation_substrates]
    witnessed = [k for k in mutants if composed[k]["tiers"][policy][tier] == "reject"]
    correct = [k for k in substrates if composed[k]["tiers"][policy][tier] == "accept"]
    out["counts"] = {
        "mutants": len(mutants),
        "witnessed": len(witnessed),
        "substrates": len(substrates),
        "correct_substrates": len(correct),
    }
    for gate in LADDER:
        ms_units = [
            (table[k]["problem_id"], int(composed[k]["ladder"][gate] == "reject"), 1)
            for k in witnessed
            if composed[k]["ladder"][gate] in {"accept", "reject"}
        ]
        frr_units = [
            (table[k]["problem_id"], int(composed[k]["ladder"][gate] == "reject"), 1)
            for k in correct
            if composed[k]["ladder"][gate] in {"accept", "reject"}
        ]
        accepted = [
            k
            for k in mutants
            if composed[k]["ladder"][gate] == "accept"
            and composed[k]["tiers"][policy][tier] in {"accept", "reject"}
        ]
        fa_units = [
            (table[k]["problem_id"], int(composed[k]["tiers"][policy][tier] == "reject"), 1)
            for k in accepted
        ]
        ms = _rate(ms_units, resamples)
        out["gates"][gate] = {
            "MS": ms,
            "FAR": None if ms["rate"] is None else 1 - ms["rate"],
            "FRR": _rate(frr_units, resamples),
            "FA_share_uninterpreted": _rate(fa_units, resamples),
            "unrefereeable_mutants": sum(composed[k]["ladder"][gate] == "error" for k in mutants),
        }
    families = sorted({table[k]["family"] for k in witnessed if table[k]["family"]})
    out["MS_by_family"] = {
        family: {
            gate: _rate(
                [
                    (table[k]["problem_id"], int(composed[k]["ladder"][gate] == "reject"), 1)
                    for k in witnessed
                    if table[k]["family"] == family
                    and composed[k]["ladder"][gate] in {"accept", "reject"}
                ],
                0,
            )
            for gate in LADDER
        }
        for family in families
    }
    return out


def cost(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """GPU-seconds per kernel per gate item (median, p95), and per-kernel ladder costs.

    ``b`` costs a + b1 + b2 for a kernel; ``c`` costs b + the c item. The
    Stage 1 rule compares their medians over kernels that have all four items.
    """
    per_item: dict[tuple[str, str, Any], float] = defaultdict(float)
    for row in rows:
        key = row["details"].get("item_key")
        item_gate = key.split("|")[1] if key else row["gate"]
        per_item[(row["kernel_id"], item_gate, row.get("seed"))] += float(row["gpu_seconds"])
    by_gate: dict[str, list[float]] = defaultdict(list)
    by_kernel: dict[tuple[str, Any], dict[str, float]] = defaultdict(dict)
    for (kernel, gate, seed), seconds in per_item.items():
        by_gate[gate].append(seconds)
        by_kernel[(kernel, seed)][gate] = seconds

    def p95(values: list[float]) -> float:
        ordered = sorted(values)
        return ordered[min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))]

    summary: dict[str, Any] = {
        gate: {"median": statistics.median(v), "p95": p95(v), "items": len(v)}
        for gate, v in sorted(by_gate.items())
    }
    complete = [g for g in by_kernel.values() if all(x in g for x in ("a", "b1", "b2", "c"))]
    if complete:
        b_costs = [g["a"] + g["b1"] + g["b2"] for g in complete]
        c_costs = [b + g["c"] for b, g in zip(b_costs, complete, strict=True)]
        b_median, c_median = statistics.median(b_costs), statistics.median(c_costs)
        summary["ladder"] = {
            "kernels": len(complete),
            "b_median": b_median,
            "c_median": c_median,
            "c_over_b": (c_median / b_median) if b_median else None,
        }
    return summary
