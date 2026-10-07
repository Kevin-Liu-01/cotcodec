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
- FA-share = accepted by the gate and audit-rejected / accepted by the gate;
- control checks: every ``control.json`` expectation against the composed
  verdict of the gate or tier it names (:func:`control_checks`).

Splits are the component owners' frozen rules, never re-derived here: the S1
calibration split is ``harness.q1.substrates.split`` over every vendored L1/L2
problem id (excluded ids included, as the substrate corpus computed it before
any build), and the mutant dev/test split is ``harness.q1.mutate.sampling``'s
content hash of ``(parent_substrate_id, dedup_hash)``.
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
    """kernel_id -> kind, problem_id, family and split (mutants), source_kind, control facts."""
    from harness.q1.mutate.sampling import split_of

    table: dict[str, dict[str, Any]] = {}
    for root in corpus_roots:
        for kernel in iter_kernel_dirs(root):
            if kernel.kernel_id in table:
                raise ValueError(f"kernel id {kernel.kernel_id} appears in two corpus roots")
            mutation = kernel.mutation or {}
            table[kernel.kernel_id] = {
                "kind": kernel.kind,
                "problem_id": kernel.problem_id,
                "family": mutation.get("family"),
                "operator": mutation.get("operator"),
                "parent_substrate_id": mutation.get("parent_substrate_id"),
                "split": split_of(mutation["parent_substrate_id"], mutation["dedup_hash"])
                if kernel.kind == "mutant"
                else None,
                "source_kind": (kernel.substrate or {}).get("source_kind"),
                "control_kind": (kernel.control or {}).get("control_kind"),
                "expected": dict((kernel.control or {}).get("expected", {})),
            }
    return table


def s1_split(seed: int = 42) -> dict[str, Any]:
    """The frozen S1 calibration/evaluation split (``harness.q1.substrates.split``).

    Computed over every vendored L1/L2 problem id, excluded ids included, exactly
    as the substrate corpus computed it before any build; ``sha256`` is the
    value the preregistration names.
    """
    from harness.q1 import problems
    from harness.q1.substrates.split import calibration_split as substrate_split

    return substrate_split(problems.list_problem_ids(include_excluded=True), seed=seed)


def calibration_split(
    problem_ids: Iterable[str] | None = None, seed: int = 42
) -> tuple[list[str], list[str]]:
    """S1 calibration and evaluation problem ids.

    With ``problem_ids=None`` (the preregistered use) this is :func:`s1_split`.
    Given ids, the same per-level rule is applied to them, which is only
    useful for tests: the frozen split is defined over the full problem list.
    """
    from harness.q1.substrates.split import calibration_split as substrate_split

    split = s1_split(seed) if problem_ids is None else substrate_split(problem_ids, seed=seed)
    return list(split["calibration"]), list(split["evaluation"])


def mutant_split(table: Mapping[str, Mapping[str, Any]]) -> tuple[list[str], list[str]]:
    """Mutant dev/test ids from the mutator's frozen content-hash split (seed 42).

    ``table`` is :func:`kernel_table`'s output; each mutant's ``split`` was
    computed there from ``(parent_substrate_id, dedup_hash)``.
    """
    mutants = {k: v for k, v in table.items() if v["kind"] == "mutant"}
    dev = sorted(k for k, v in mutants.items() if v["split"] == "dev")
    test = sorted(k for k, v in mutants.items() if v["split"] == "test")
    if len(dev) + len(test) != len(mutants):
        raise ValueError("every mutant needs a dev or test split")
    return dev, test


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


#: Control ``expected`` gate ids read from the composed ladder.
_LADDER_IDS = frozenset(LADDER)
#: ... from single gate rows and c-family aggregates.
_GATE_IDS = frozenset({*SINGLE_ROW_GATES, *C_FAMILIES})
#: ... from the audit tiers (schema ``KNOWN_GATES`` spelling -> tier name).
_TIER_IDS = {
    "audit_N": "N",
    "audit_G": "G",
    "audit_G_strict": "G-strict",
    "audit_c_disjoint": "c-disjoint",
}


def composed_verdict(entry: Mapping[str, Any], gate: str, *, policy: str = PRIMARY_POLICY) -> str:
    """The verdict a ``control.json`` gate id names, read from one :func:`compose` entry.

    ``missing`` means no row for that gate exists for this replicate;
    ``unknown-gate`` means the id is not a gate, channel or tier.
    """
    if gate in _LADDER_IDS:
        return entry["ladder"].get(gate, "missing")
    if gate in _GATE_IDS:
        return entry["gates"].get(gate, "missing")
    if gate in {"A1", "A2", "A3"}:
        return entry["audit"][policy].get(gate, "missing")
    if gate == "A1_strict":
        return entry["audit"]["strict-fp32"].get("A1", "missing")
    if gate == "A4":
        return entry["A4"]
    if gate in _TIER_IDS:
        return entry["tiers"][policy][_TIER_IDS[gate]]
    return "unknown-gate"


def control_checks(
    composed: Mapping[str, Mapping[str, Any]],
    table: Mapping[str, Mapping[str, Any]],
    *,
    policy: str = PRIMARY_POLICY,
) -> dict[str, Any]:
    """Every control expectation against its composed verdict (acceptance criterion 5).

    A control with no rows at all, a missing gate and an unknown gate id each
    count as a failed cell: the criterion needs 100% of cells to hold.
    """
    cells = []
    for kernel_id, facts in sorted(table.items()):
        if facts["kind"] != "control":
            continue
        entry = composed.get(kernel_id)
        for gate, expected in sorted(facts["expected"].items()):
            got = "missing" if entry is None else composed_verdict(entry, gate, policy=policy)
            cells.append(
                {
                    "control_id": kernel_id,
                    "control_kind": facts["control_kind"],
                    "gate": gate,
                    "expected": expected,
                    "got": got,
                    "ok": got == expected,
                }
            )
    failed = [cell for cell in cells if not cell["ok"]]
    return {
        "policy": policy,
        "cells": len(cells),
        "held": len(cells) - len(failed),
        "failed": failed,
        "all_hold": bool(cells) and not failed,
    }


def c_rejection_causes(rows: Iterable[Mapping[str, Any]], *, seed: int = 42) -> dict[str, Any]:
    """Per kernel, why gate (c) rejected: ``candidate-raised``, ``mismatch`` or ``shape-mismatch``.

    Read from the admissible per-configuration c1/c2/c3 rejections, so FRR(c)
    can be split into refusals or crashes and silent numerical failures.
    """
    causes: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        if row.get("seed", 42) != seed or row["gate"] not in C_FAMILIES:
            continue
        if row["config_id"] == "aggregate" or row["verdict"] != "reject":
            continue
        if not row["details"].get("admissible"):
            continue
        reason = row["details"].get("reason") or "mismatch"
        causes[row["kernel_id"]][reason] += 1
    return {kernel: dict(counts) for kernel, counts in sorted(causes.items())}


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
