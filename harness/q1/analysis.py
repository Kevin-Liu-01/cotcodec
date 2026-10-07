"""Stage 0 analysis: ladder composition, audit tiers, MS/FAR/FRR/FA-share, cost.

Pure Python with numpy and scipy (intervals). Inputs are the journal's final rows
(``Journal.final_rows()``) and a kernel table built from the corpus
(``kernel_table``). Definitions follow the preregistration
(``program/preregistrations/q1-stage0-gate-validation.md``, sections 5-8):

- ladder: ``b = a and b1 and b2`` (b1/b2 ``error`` counts as accept, as the
  released check fails open); ``c = b and c1 and c2 and c3``;
  ``c_1e-2 = b and c_1e-2``; ``c_kbv_raw = b and c_kbv_raw``;
- a gate ``timeout`` is a rejection; ``error`` removes the kernel from that
  gate's denominators and is reported;
- **unrefereeable components are vacuous.** A gate (c) family with no
  admissible configuration for a problem, and an audit channel A2 or A3 with
  no admissible draw, is decided by the reference alone (validity is
  computed before the candidate runs). Such a component is dropped from the
  conjunction for every kernel of that problem instead of making the kernel
  ``error``: otherwise a kernel would enter the denominators only when
  another component rejected it, which makes the denominators depend on the
  outcome. With ``problem_of``, a component is vacuous for a problem only
  when every kernel of that problem agrees; disagreements are listed;
- audit channels A1-A3 per TF32 policy from their aggregate rows; A4 is the
  conjunction of the in-process, poison-allocator and sanitizer rows present;
  tiers from ``audit.tiers.tier_verdicts``;
- **mutant scope and parent filter.** A mutant is scored only if its parent
  substrate is in scope (the evaluation set for the primary metrics; mutants
  of S1 calibration parents are a labelled secondary) and the same audit
  policy and tier accept the parent at the same replicate. A mutant of a
  faulty parent would be "witnessed" by the parent's own fault;
- a scored mutant is witnessed when the audit tier rejects it; MS = rejected
  by the gate / witnessed; FAR = 1 - MS; MS is also weighted by the
  Horvitz-Thompson weight ``n/k`` of the cap;
- **one kernel set.** MS and FRR of every gate use the kernels that a, b and c
  all referee (``PRIMARY_LADDER``); paired differences between gates are on
  that set;
- FRR over correct substrates (kind substrate, in the evaluation set, audit
  accepts); FRR_independent over independent units (one per S1 problem, one
  per S2 kernel family; a unit is a false rejection if any of its correct
  substrates is rejected), which is the unit of acceptance criterion 3;
- intervals: Clopper-Pearson, and a cluster bootstrap whose clusters are the
  connected components of problems linked by shared kernel families;
- FA-share = accepted by the gate and audit-rejected / accepted by the gate;
- precision-only class (``audit.tiers.precision_only``), audit-hole replay
  candidates and summaries, c-lite greedy set cover, marginal and amortized
  cost, and the control checks (:func:`control_checks`).

Splits are the component owners' frozen rules, never re-derived here: the S1
calibration split is ``harness.q1.substrates.split`` over every vendored L1/L2
problem id (excluded ids included, as the substrate corpus computed it before
any build), and the mutant dev/test split is ``harness.q1.mutate.sampling``'s
content hash of ``(parent_substrate_id, dedup_hash)``.
"""

from __future__ import annotations

import json
import re
import statistics
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from harness.q1.audit.tiers import precision_only, tier_verdicts
from harness.q1.schema import iter_kernel_dirs

SINGLE_ROW_GATES = ("a", "a_1e-3", "a_head_1e-4", "a_head_1e-2", "a_static", "b1", "b2", "b_native")
C_FAMILIES = ("c1", "c2", "c3")
C_AGGREGATES = (*C_FAMILIES, "c_1e-2", "c_kbv_raw")
LADDER = ("a", "a_1e-3", "a_head_1e-4", "a_head_1e-2", "a_static", "b", "c", "c_1e-2", "c_kbv_raw")
#: The gates whose comparison is the Stage 0 question; every gate's MS and FRR use
#: the kernels all three referee.
PRIMARY_LADDER = ("a", "b", "c")
PAIRED = (("c", "a"), ("c", "b"), ("b", "a"), ("c_1e-2", "a"), ("c", "a_1e-3"))
POLICIES = ("tf32-admissible", "strict-fp32")
TIERS = ("N", "G", "G-strict", "c-disjoint")
PRIMARY_POLICY, PRIMARY_TIER = "tf32-admissible", "G"
#: Audit channels that may be unrefereeable for a problem without making the tier error.
OPTIONAL_CHANNELS = ("A2", "A3")
#: Acceptance criterion 3 (preregistration section 8.2).
FRR_MIN_UNITS, FRR_MAX_RATE, FRR_MAX_UPPER = 72, 0.02, 0.05
#: Gates whose rejections are replayed against the audit oracle (section 6.7).
REPLAYED_GATES = ("a", "a_1e-3", *C_FAMILIES)
_SEED_SUFFIX = re.compile(r"/seed-[0-9]+$")


# --- Corpus ---------------------------------------------------------------------------


def _mutant_weights(root: Path) -> dict[str, float]:
    """Horvitz-Thompson weights from a mutant corpus's ``mutants.jsonl`` (if present)."""
    path = Path(root) / "mutants.jsonl"
    if not path.is_file():
        return {}
    weights = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            if row.get("weight") is not None:
                weights[row["mutant_id"]] = float(row["weight"])
    return weights


def _kernel_family(path: Path, source_kind: str | None, problem_id: str, kernel_id: str) -> str:
    build = path / "build.json"
    if build.is_file():
        family = json.loads(build.read_text(encoding="utf-8")).get("source_kernel_family")
        if family:
            return str(family)
    if source_kind == "inductor":
        return f"inductor:{problem_id}"
    return f"{source_kind}:{kernel_id}"


def kernel_table(corpus_roots: Iterable[Path]) -> dict[str, dict[str, Any]]:
    """kernel_id -> kind, problem, mutant facts (family, operator, origin, parent, split,
    weight), source kind and tier, kernel family, and control facts."""
    from harness.q1.mutate.sampling import split_of

    table: dict[str, dict[str, Any]] = {}
    for root in corpus_roots:
        weights = _mutant_weights(root)
        for kernel in iter_kernel_dirs(root):
            if kernel.kernel_id in table:
                raise ValueError(f"kernel id {kernel.kernel_id} appears in two corpus roots")
            mutation = kernel.mutation or {}
            source_kind = (kernel.substrate or {}).get("source_kind")
            parent = mutation.get("parent_substrate_id")
            table[kernel.kernel_id] = {
                "kind": kernel.kind,
                "problem_id": kernel.problem_id,
                "family": mutation.get("family"),
                "operator": mutation.get("operator"),
                "rule_origin": mutation.get("rule_origin"),
                "parent_substrate_id": parent,
                "split": split_of(parent, mutation["dedup_hash"])
                if kernel.kind == "mutant"
                else None,
                "weight": weights.get(kernel.kernel_id) if kernel.kind == "mutant" else None,
                "source_kind": source_kind,
                "source_tier": None
                if kernel.kind == "control"
                else ("S1" if source_kind == "inductor" else "S2"),
                "kernel_family": None
                if kernel.kind == "control"
                else _kernel_family(
                    kernel.path, source_kind, kernel.problem_id, parent or kernel.kernel_id
                ),
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


def substrate_halves(
    table: Mapping[str, Mapping[str, Any]], split: Mapping[str, Any]
) -> dict[str, set[str]]:
    """Substrate ids by half: S1-eval and every S2 substrate evaluate; S1-cal calibrates."""
    evaluation_problems = set(split["evaluation"])
    halves: dict[str, set[str]] = {"evaluation": set(), "calibration": set()}
    for kernel_id, facts in table.items():
        if facts["kind"] != "substrate":
            continue
        if facts["source_kind"] != "inductor" or facts["problem_id"] in evaluation_problems:
            halves["evaluation"].add(kernel_id)
        else:
            halves["calibration"].add(kernel_id)
    return halves


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


def cluster_map(table: Mapping[str, Mapping[str, Any]]) -> dict[str, str]:
    """problem_id -> bootstrap cluster: connected components of problems that share a
    kernel family (an S2 family spans several problems; S1 families are per problem)."""
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    by_family: dict[str, set[str]] = defaultdict(set)
    for facts in table.values():
        find(facts["problem_id"])
        if facts.get("kernel_family"):
            by_family[facts["kernel_family"]].add(facts["problem_id"])
    for problems in by_family.values():
        ordered = sorted(problems)
        for other in ordered[1:]:
            union(ordered[0], other)
    return {problem: find(problem) for problem in list(parent)}


# --- Composition -------------------------------------------------------------------------


def _gate_verdict(verdict: str) -> str:
    return "reject" if verdict == "timeout" else verdict


def _conjoin(verdicts: Sequence[str]) -> str:
    for verdict in ("reject", "error"):
        if verdict in verdicts:
            return verdict
    return "accept" if verdicts else "error"


def _c_unrefereeable(row: Mapping[str, Any]) -> bool:
    """A gate (c) aggregate decided by the reference alone: no admissible configuration."""
    if row["verdict"] != "error":
        return False
    details = row["details"]
    if row["gate"] == "c_kbv_raw":
        return int(details.get("configs", 0)) == 0
    return int(details.get("admissible", 0)) == 0


def _audit_unrefereeable(row: Mapping[str, Any]) -> bool:
    """An A2/A3 aggregate with no admissible draw (every draw inadmissible, or none)."""
    if row["verdict"] != "error":
        return False
    counts = row["details"].get("counts", {})
    return not any(
        counts.get(k, 0)
        for k in ("pass", "silent-wrong", "crash-after-launch", "refusal-before-launch")
    )


def compose(
    rows: Iterable[Mapping[str, Any]],
    *,
    seed: int = 42,
    problem_of: Mapping[str, str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Per kernel: gate ladder verdicts and audit tiers (both policies) for one replicate.

    ``problem_of`` (kernel id -> problem id, from :func:`kernel_table`) makes the
    vacuous-component decision per problem (see the module docstring).
    """
    by_kernel: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("seed", 42) == seed and row["gate"] != "audit_hole":
            by_kernel[row["kernel_id"]].append(row)

    facts: dict[str, dict[str, Any]] = {}
    for kernel_id, kernel_rows in by_kernel.items():
        gates: dict[str, str] = {}
        audit: dict[str, dict[str, str]] = {policy: {} for policy in POLICIES}
        a1_details: dict[str, dict[str, Any]] = {}
        flags: dict[tuple[str, str], bool] = {}  # (scope, component) -> unrefereeable
        a4_parts: list[str] = []
        for row in kernel_rows:
            gate, config, verdict = row["gate"], row["config_id"], row["verdict"]
            item_level = config.startswith("item/")  # runner timeout or crash row
            if gate in SINGLE_ROW_GATES:
                gates[gate] = _gate_verdict(verdict)
            elif gate == "c" and item_level:
                for family in C_AGGREGATES:
                    gates[family] = _gate_verdict(verdict)
            elif gate in C_AGGREGATES and config == "aggregate":
                gates[gate] = verdict
                flags[("c", gate)] = _c_unrefereeable(row)
            elif gate in {"A1", "A2", "A3"}:
                if item_level:
                    for policy in POLICIES:
                        audit[policy][gate] = "reject" if verdict == "timeout" else verdict
                elif config == "aggregate":
                    policy = row["tf32_policy"]
                    audit[policy][gate] = verdict
                    if gate == "A1":
                        a1_details[policy] = dict(row["details"])
                    if gate in OPTIONAL_CHANNELS:
                        flags[(policy, gate)] = _audit_unrefereeable(row)
            elif gate in {"A4", "A4_poison", "A4_sanitizer"}:
                a4_parts.append("reject" if verdict == "timeout" else verdict)
        facts[kernel_id] = {
            "gates": gates,
            "audit": audit,
            "a1_details": a1_details,
            "flags": flags,
            "a4_parts": a4_parts,
        }

    vacuous, anomalies = _vacuous_components(facts, problem_of)
    out: dict[str, dict[str, Any]] = {}
    for kernel_id, f in facts.items():
        gates, audit = f["gates"], f["audit"]
        fail_open = [name for name in ("b1", "b2") if gates.get(name) == "error"]
        b_parts = [gates.get("a", "error")] + [
            "accept" if gates.get(name) == "error" else gates.get(name, "error")
            for name in ("b1", "b2")
        ]
        ladder = {
            name: gates.get(name, "error")
            for name in ("a", "a_1e-3", "a_head_1e-4", "a_head_1e-2", "a_static")
        }
        ladder["b"] = _conjoin(b_parts)
        skip_c = vacuous[kernel_id].get("c", set())
        ladder["c"] = _conjoin(
            [ladder["b"], *(gates.get(fam, "error") for fam in C_FAMILIES if fam not in skip_c)]
        )
        for secondary in ("c_1e-2", "c_kbv_raw"):
            parts = [ladder["b"]]
            if secondary not in skip_c:
                parts.append(gates.get(secondary, "error"))
            ladder[secondary] = _conjoin(parts)
        a4 = _conjoin(f["a4_parts"]) if f["a4_parts"] else "error"
        tiers, precision = {}, {}
        for policy in POLICIES:
            skip = vacuous[kernel_id].get(policy, set())
            channels = {**audit[policy], "A4": a4}
            tiers[policy] = tier_verdicts(channels, vacuous=skip)
            judged = {name: ("accept" if name in skip else v) for name, v in channels.items()}
            precision[policy] = precision_only(f["a1_details"].get(policy, {}), judged)
        out[kernel_id] = {
            "gates": gates,
            "ladder": ladder,
            "audit": audit,
            "A4": a4,
            "tiers": tiers,
            "precision_only": precision,
            "b_fail_open": fail_open,
            "vacuous": {scope: sorted(items) for scope, items in vacuous[kernel_id].items()},
            "refereeability_anomalies": anomalies.get(kernel_id, []),
        }
    return out


def _vacuous_components(
    facts: Mapping[str, Mapping[str, Any]], problem_of: Mapping[str, str] | None
) -> tuple[dict[str, dict[str, set[str]]], dict[str, list[dict[str, Any]]]]:
    vacuous: dict[str, dict[str, set[str]]] = {k: defaultdict(set) for k in facts}
    anomalies: dict[str, list[dict[str, Any]]] = defaultdict(list)
    groups: dict[str, list[str]] = defaultdict(list)
    for kernel_id in facts:
        groups[problem_of.get(kernel_id, kernel_id) if problem_of else kernel_id].append(kernel_id)
    for problem, kernels in groups.items():
        components = {key for k in kernels for key in facts[k]["flags"]}
        for scope, component in components:
            seen = {
                k: facts[k]["flags"][(scope, component)]
                for k in kernels
                if (scope, component) in facts[k]["flags"]
            }
            if all(seen.values()):
                for k in kernels:
                    vacuous[k][scope].add(component)
            elif any(seen.values()):
                note = {
                    "problem_id": problem,
                    "scope": scope,
                    "component": component,
                    "unrefereeable_for": sorted(k for k, v in seen.items() if v),
                    "refereed_for": sorted(k for k, v in seen.items() if not v),
                }
                for k in seen:
                    anomalies[k].append(note)
    return vacuous, anomalies


def refereeability_report(
    composed: Mapping[str, Mapping[str, Any]], table: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    """Vacuous components per problem, and every per-problem disagreement."""
    per_problem: dict[str, dict[str, list[str]]] = {}
    anomalies: dict[tuple, dict[str, Any]] = {}
    for kernel_id, entry in composed.items():
        problem = table.get(kernel_id, {}).get("problem_id", kernel_id)
        if entry["vacuous"]:
            per_problem[problem] = entry["vacuous"]
        for note in entry["refereeability_anomalies"]:
            anomalies[(note["problem_id"], note["scope"], note["component"])] = note
    return {
        "vacuous_by_problem": dict(sorted(per_problem.items())),
        "problems_with_vacuous_components": len(per_problem),
        "anomalies": [anomalies[key] for key in sorted(anomalies)],
    }


# --- Intervals ------------------------------------------------------------------------------


def clopper_pearson(k: int, n: int, level: float = 0.95) -> list[float]:
    from scipy.stats import beta

    if n == 0:
        return [0.0, 1.0]
    alpha = 1 - level
    lo = 0.0 if k == 0 else float(beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - alpha / 2, k + 1, n - k))
    return [lo, hi]


def cluster_bootstrap(
    units: Sequence[tuple[str, float, float]], *, resamples: int = 10_000, seed: int = 0
) -> list[float] | None:
    """95% percentile CI of sum(k)/sum(n) resampling clusters with replacement.

    ``units`` holds (cluster, k, n) per kernel; k and n may be weights. Draws
    use ``numpy.random.default_rng(seed)`` in blocks of 1,000 resamples, each a
    row of cluster indices; a resample with sum(n) = 0 is dropped.
    """
    import numpy as np

    clusters: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
    for cluster, k, n in units:
        clusters[cluster][0] += k
        clusters[cluster][1] += n
    keys = sorted(clusters)
    if not keys or resamples <= 0:
        return None
    ks = np.array([clusters[key][0] for key in keys], dtype=np.float64)
    ns = np.array([clusters[key][1] for key in keys], dtype=np.float64)
    rng = np.random.default_rng(seed)
    stats = []
    for start in range(0, resamples, 1000):
        draws = rng.integers(0, len(keys), size=(min(1000, resamples - start), len(keys)))
        k, n = ks[draws].sum(axis=1), ns[draws].sum(axis=1)
        keep = n != 0
        stats.append(k[keep] / n[keep])
    values = np.sort(np.concatenate(stats))
    if values.size == 0:
        return None
    upper = min(values.size - 1, int(0.975 * values.size))
    return [float(values[int(0.025 * values.size)]), float(values[upper])]


def _rate(units: list[tuple[str, int, int]], resamples: int) -> dict[str, Any]:
    k = sum(u[1] for u in units)
    n = sum(u[2] for u in units)
    return {
        "k": k,
        "n": n,
        "rate": (k / n) if n else None,
        "clopper_pearson": clopper_pearson(k, n),
        "cluster_bootstrap": cluster_bootstrap(units, resamples=resamples),
        "clusters": len({u[0] for u in units}),
    }


def _weighted_rate(units: list[tuple[str, int, float | None]], resamples: int) -> dict[str, Any]:
    """Horvitz-Thompson weighted rate; ``None`` weights make it unavailable."""
    if any(w is None for _, _, w in units):
        return {"rate": None, "reason": "missing-weights"}
    weighted = [(c, x * w, w) for c, x, w in units]
    total = sum(w for _, _, w in weighted)
    return {
        "k_weighted": sum(x for _, x, _ in weighted),
        "n_weighted": total,
        "rate": (sum(x for _, x, _ in weighted) / total) if total else None,
        "cluster_bootstrap": cluster_bootstrap(weighted, resamples=resamples),
    }


# --- Metrics ------------------------------------------------------------------------------


def _refereed(entry: Mapping[str, Any], gates: Iterable[str]) -> bool:
    return all(entry["ladder"][g] in {"accept", "reject"} for g in gates)


def scope_mutants(
    composed: Mapping[str, Mapping[str, Any]],
    table: Mapping[str, Mapping[str, Any]],
    *,
    policy: str,
    tier: str,
    parents: set[str] | None,
) -> dict[str, Any]:
    """Mutants in scope whose parent the same audit tier accepts at this replicate."""
    eligible, excluded = [], defaultdict(int)
    for kernel_id, facts in sorted(table.items()):
        if facts["kind"] != "mutant" or kernel_id not in composed:
            continue
        parent = facts["parent_substrate_id"]
        if parents is not None and parent not in parents:
            excluded["parent-out-of-scope"] += 1
            continue
        verdict = composed[parent]["tiers"][policy][tier] if parent in composed else "missing"
        if verdict != "accept":
            excluded[f"parent-{verdict}"] += 1
            continue
        eligible.append(kernel_id)
    return {"eligible": eligible, "excluded": dict(sorted(excluded.items()))}


def metrics(
    composed: Mapping[str, Mapping[str, Any]],
    table: Mapping[str, Mapping[str, Any]],
    *,
    policy: str = PRIMARY_POLICY,
    tier: str = PRIMARY_TIER,
    evaluation_substrates: set[str] | None = None,
    mutant_parents: set[str] | None = None,
    resamples: int = 10_000,
    clusters: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """MS, FAR, FA-share over scored mutants and FRR over correct substrates, per ladder gate.

    ``evaluation_substrates`` restricts FRR; ``mutant_parents`` restricts which
    parents' mutants are scored (``None`` keeps all; the parent filter applies
    either way).
    """
    clusters = dict(clusters) if clusters is not None else cluster_map(table)

    def cluster(kernel_id: str) -> str:
        problem = table[kernel_id]["problem_id"]
        return clusters.get(problem, problem)

    out: dict[str, Any] = {"policy": policy, "tier": tier, "gates": {}}
    scope = scope_mutants(composed, table, policy=policy, tier=tier, parents=mutant_parents)
    mutants = scope["eligible"]
    substrates = [k for k, v in table.items() if v["kind"] == "substrate" and k in composed]
    if evaluation_substrates is not None:
        substrates = [k for k in substrates if k in evaluation_substrates]
    tier_of = {k: composed[k]["tiers"][policy][tier] for k in [*mutants, *substrates]}
    witnessed = [k for k in mutants if tier_of[k] == "reject"]
    correct = [k for k in substrates if tier_of[k] == "accept"]
    common_witnessed = [k for k in witnessed if _refereed(composed[k], PRIMARY_LADDER)]
    common_correct = [k for k in correct if _refereed(composed[k], PRIMARY_LADDER)]
    out["counts"] = {
        "mutants_in_corpus": sum(
            1 for k, v in table.items() if v["kind"] == "mutant" and k in composed
        ),
        "mutants_excluded": scope["excluded"],
        "mutants_scored": len(mutants),
        "witnessed": len(witnessed),
        "witnessed_refereed_by_a_b_c": len(common_witnessed),
        "substrates": len(substrates),
        "correct_substrates": len(correct),
        "correct_refereed_by_a_b_c": len(common_correct),
        "precision_only_witnessed": sum(composed[k]["precision_only"][policy] for k in witnessed),
    }
    out["precision_only_kernels"] = sorted(
        k for k in [*mutants, *substrates] if composed[k]["precision_only"][policy]
    )

    def rejected(kernel_id: str, gate: str) -> int:
        return int(composed[kernel_id]["ladder"][gate] == "reject")

    for gate in LADDER:
        ms_set = [
            k for k in common_witnessed if composed[k]["ladder"][gate] in {"accept", "reject"}
        ]
        frr_set = [k for k in common_correct if composed[k]["ladder"][gate] in {"accept", "reject"}]
        ms = _rate([(cluster(k), rejected(k, gate), 1) for k in ms_set], resamples)
        accepted = [
            k
            for k in mutants
            if composed[k]["ladder"][gate] == "accept" and tier_of[k] in {"accept", "reject"}
        ]
        out["gates"][gate] = {
            "MS": ms,
            "MS_weighted": _weighted_rate(
                [(cluster(k), rejected(k, gate), table[k].get("weight")) for k in ms_set],
                resamples,
            ),
            "FAR": None if ms["rate"] is None else 1 - ms["rate"],
            "FRR": _rate([(cluster(k), rejected(k, gate), 1) for k in frr_set], resamples),
            "FRR_independent": _independent_frr(frr_set, table, gate, composed, clusters),
            "FA_share_uninterpreted": _rate(
                [(cluster(k), int(tier_of[k] == "reject"), 1) for k in accepted], resamples
            ),
            "unrefereeable_witnessed": sum(
                composed[k]["ladder"][gate] == "error" for k in witnessed
            ),
            "unrefereeable_correct": sum(composed[k]["ladder"][gate] == "error" for k in correct),
            "unrefereeable_scored_mutants": sum(
                composed[k]["ladder"][gate] == "error" for k in mutants
            ),
        }
    out["paired_differences"] = {
        f"MS_{hi}-MS_{lo}": _paired(common_witnessed, hi, lo, composed, cluster, resamples)
        for hi, lo in PAIRED
    }
    for name, key in (
        ("MS_by_family", "family"),
        ("MS_by_origin", "rule_origin"),
        ("MS_by_source_tier", "source_tier"),
    ):
        out[name] = _breakdown(common_witnessed, table, key, composed, cluster)
    c = out["gates"]["c"]["FRR_independent"]
    out["criterion_3_FRR_c"] = {
        **c,
        "min_units": FRR_MIN_UNITS,
        "evaluable": c["n"] >= FRR_MIN_UNITS,
        "holds": c["n"] >= FRR_MIN_UNITS
        and c["rate"] is not None
        and c["rate"] <= FRR_MAX_RATE
        and c["clopper_pearson"][1] <= FRR_MAX_UPPER,
    }
    return out


def _independent_frr(
    frr_set: Sequence[str],
    table: Mapping[str, Mapping[str, Any]],
    gate: str,
    composed: Mapping[str, Mapping[str, Any]],
    clusters: Mapping[str, str],
) -> dict[str, Any]:
    """FRR over independent units (kernel families): a unit fails if any member is rejected."""
    units: dict[str, list[str]] = defaultdict(list)
    for kernel_id in frr_set:
        units[table[kernel_id]["kernel_family"] or kernel_id].append(kernel_id)
    k = sum(
        any(composed[m]["ladder"][gate] == "reject" for m in members) for members in units.values()
    )
    n = len(units)
    return {
        "k": k,
        "n": n,
        "rate": (k / n) if n else None,
        "clopper_pearson": clopper_pearson(k, n),
        "units_rejected": sorted(
            u
            for u, members in units.items()
            if any(composed[m]["ladder"][gate] == "reject" for m in members)
        ),
        "clusters": len({clusters.get(table[m[0]]["problem_id"]) for m in units.values()}),
    }


def _paired(
    kernels: Sequence[str],
    hi: str,
    lo: str,
    composed: Mapping[str, Mapping[str, Any]],
    cluster: Callable[[str], str],
    resamples: int,
) -> dict[str, Any]:
    """MS_hi - MS_lo on kernels both referee: discordant counts and a cluster bootstrap CI."""
    both = [
        k
        for k in kernels
        if composed[k]["ladder"][hi] in {"accept", "reject"}
        and composed[k]["ladder"][lo] in {"accept", "reject"}
    ]
    x = {
        k: int(composed[k]["ladder"][hi] == "reject") - int(composed[k]["ladder"][lo] == "reject")
        for k in both
    }
    return {
        "n": len(both),
        "difference": (sum(x.values()) / len(both)) if both else None,
        "hi_only": sum(v == 1 for v in x.values()),
        "lo_only": sum(v == -1 for v in x.values()),
        "cluster_bootstrap": cluster_bootstrap(
            [(cluster(k), v, 1) for k, v in x.items()], resamples=resamples
        ),
    }


def _breakdown(
    kernels: Sequence[str],
    table: Mapping[str, Mapping[str, Any]],
    key: str,
    composed: Mapping[str, Mapping[str, Any]],
    cluster: Callable[[str], str],
) -> dict[str, Any]:
    groups = sorted({str(table[k].get(key)) for k in kernels})
    out = {}
    for group in groups:
        members = [k for k in kernels if str(table[k].get(key)) == group]
        out[group] = {}
        for gate in LADDER:
            units = [
                (cluster(k), int(composed[k]["ladder"][gate] == "reject"), 1)
                for k in members
                if composed[k]["ladder"][gate] in {"accept", "reject"}
            ]
            weighted = [
                (cluster(k), int(composed[k]["ladder"][gate] == "reject"), table[k].get("weight"))
                for k in members
                if composed[k]["ladder"][gate] in {"accept", "reject"}
            ]
            out[group][gate] = {**_rate(units, 0), "weighted": _weighted_rate(weighted, 0)}
    return out


# --- Controls --------------------------------------------------------------------------------

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
    """Per kernel, why gate (c) rejected: ``candidate-raised``, ``mismatch``,
    ``shape-mismatch`` or ``worker-crashed`` (an item-level row: the worker died
    after the candidate loaded, so no per-configuration row exists).

    Read from the admissible per-configuration c1/c2/c3 rejections, so FRR(c)
    can be split into refusals or crashes and silent numerical failures.
    """
    causes: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        if row.get("seed", 42) != seed:
            continue
        if row["gate"] == "c" and row["config_id"].startswith("item/"):
            if row["verdict"] in {"reject", "timeout"}:
                causes[row["kernel_id"]][str(row["details"].get("reason", "worker-crashed"))] += 1
            continue
        if row["gate"] not in C_FAMILIES:
            continue
        if row["config_id"] == "aggregate" or row["verdict"] != "reject":
            continue
        if not row["details"].get("admissible"):
            continue
        reason = row["details"].get("reason") or "mismatch"
        causes[row["kernel_id"]][reason] += 1
    return {kernel: dict(counts) for kernel, counts in sorted(causes.items())}


# --- Audit holes (preregistration section 6.7) -----------------------------------------------


def audit_hole_candidates(
    rows: Iterable[Mapping[str, Any]],
    composed: Mapping[str, Mapping[str, Any]],
    table: Mapping[str, Mapping[str, Any]],
    *,
    seed: int = 42,
    policy: str = PRIMARY_POLICY,
    tier: str = PRIMARY_TIER,
) -> dict[str, dict[str, Any]]:
    """Gate rejections of kernels the audit tier accepts, as replay requests per kernel.

    Replayed: every admissible gate (c) configuration a c family rejected, and
    every failing gate (a) / ``a_1e-3`` trial. Not replayable (listed): an
    item-level rejection (the worker died or timed out) and a static-check
    rejection.
    """
    accepted = {
        k
        for k, e in composed.items()
        if e["tiers"][policy][tier] == "accept" and table.get(k, {}).get("kind") != "control"
    }
    out: dict[str, dict[str, Any]] = defaultdict(lambda: {"replay": [], "not_replayable": []})
    for row in rows:
        kernel = row["kernel_id"]
        if row.get("seed", 42) != seed or kernel not in accepted:
            continue
        gate, verdict, details = row["gate"], row["verdict"], row["details"]
        if verdict not in {"reject", "timeout"}:
            continue
        if row["config_id"].startswith("item/"):
            if gate in {"a", "a_1e-3", "c"}:
                out[kernel]["not_replayable"].append({"gate": gate, "reason": "item-level"})
            continue
        if gate in C_FAMILIES and row["config_id"] != "aggregate" and details.get("admissible"):
            out[kernel]["replay"].append({"gate": gate, "config_id": row["config_id"]})
        elif gate in {"a", "a_1e-3"}:
            trials = details.get("failed_trials") or (
                [details["trial"]] if details.get("trial") is not None else []
            )
            if trials:
                out[kernel]["replay"].append(
                    {"gate": gate, "config_id": row["config_id"], "trials": sorted(trials)}
                )
            else:
                out[kernel]["not_replayable"].append(
                    {"gate": gate, "reason": details.get("reason", "no-trial")}
                )
    return {k: v for k, v in sorted(out.items())}


def audit_hole_summary(
    replay_rows: Iterable[Mapping[str, Any]],
    candidates: Mapping[str, Mapping[str, Any]],
    *,
    seed: int = 42,
) -> dict[str, Any]:
    """Adjudications per rejecting gate, unreplayed requests, and criterion 4."""
    done: dict[tuple[str, str, str], str] = {}
    by_gate: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    holes = []
    for row in replay_rows:
        if row["gate"] != "audit_hole" or row.get("seed", 42) != seed:
            continue
        if row["config_id"].startswith("item/"):
            continue
        details = row["details"]
        key = (row["kernel_id"], details["rejecting_gate"], details["rejecting_config"])
        done[key] = details["classification"]
        by_gate[details["rejecting_gate"]][details["classification"]] += 1
        if details["classification"] == "audit-hole":
            holes.append(
                {
                    "kernel_id": row["kernel_id"],
                    **{k: details.get(k) for k in ("rejecting_gate", "rejecting_config", "reason")},
                }
            )
    requested = [
        (kernel, request["gate"], request["config_id"])
        for kernel, entry in candidates.items()
        for request in entry["replay"]
    ]
    unreplayed = [key for key in requested if key not in done]
    not_replayable = sum(len(entry["not_replayable"]) for entry in candidates.values())
    return {
        "requested": len(requested),
        "adjudicated": len(requested) - len(unreplayed),
        "unadjudicated": len(unreplayed),
        "not_replayable": not_replayable,
        "by_rejecting_gate": {g: dict(c) for g, c in sorted(by_gate.items())},
        "audit_holes": holes,
        "criterion_4_holds": not unreplayed and not holes and not not_replayable,
    }


# --- c-lite (preregistration section 5.5) -----------------------------------------------------


def c_lite_set_cover(
    rows: Iterable[Mapping[str, Any]],
    composed: Mapping[str, Mapping[str, Any]],
    table: Mapping[str, Mapping[str, Any]],
    dev_mutants: Iterable[str],
    *,
    seed: int = 42,
    policy: str = PRIMARY_POLICY,
    tier: str = PRIMARY_TIER,
    mutant_parents: set[str] | None = None,
) -> dict[str, Any]:
    """Greedy set cover of gate (c) configurations over dev mutants b misses.

    Universe: scored dev mutants (parent filter and scope as in :func:`metrics`)
    that the audit tier witnesses and the ladder gate ``b`` accepts. A
    configuration (its config id without the replicate's ``/seed-N``) covers
    the mutants it rejects on an admissible draw. Each step takes the
    configuration with the most newly covered mutants per GPU-second (median
    over that configuration's rows; wall seconds when no row has GPU time, as
    on CPU), ties by configuration id, until nothing new is covered.
    """
    rows = [r for r in rows if r.get("seed", 42) == seed]
    dev = set(dev_mutants)
    scoped = scope_mutants(composed, table, policy=policy, tier=tier, parents=mutant_parents)
    universe = {
        k
        for k in scoped["eligible"]
        if k in dev
        and composed[k]["tiers"][policy][tier] == "reject"
        and composed[k]["ladder"]["b"] == "accept"
    }
    covers: dict[str, set[str]] = defaultdict(set)
    gpu: dict[str, list[float]] = defaultdict(list)
    wall: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        if row["gate"] not in C_FAMILIES or row["config_id"] == "aggregate":
            continue
        if row["config_id"].startswith("item/") or row["kernel_id"] not in dev:
            continue
        config = _SEED_SUFFIX.sub("", row["config_id"])
        gpu[config].append(float(row["gpu_seconds"]))
        wall[config].append(float(row["wall_seconds"]))
        if (
            row["kernel_id"] in universe
            and row["verdict"] == "reject"
            and row["details"].get("admissible")
        ):
            covers[config].add(row["kernel_id"])
    basis = "gpu_seconds" if any(v for values in gpu.values() for v in values) else "wall_seconds"
    cost = {
        c: max(statistics.median((gpu if basis == "gpu_seconds" else wall)[c]), 1e-9) for c in gpu
    }
    uncovered = set(universe)
    selected, total_cost = [], 0.0
    while uncovered:
        scored = sorted(
            ((len(covers[c] & uncovered) / cost[c], c) for c in cost if covers[c] & uncovered),
            key=lambda item: (-item[0], item[1]),
        )
        if not scored:
            break
        _, best = scored[0]
        newly = covers[best] & uncovered
        uncovered -= newly
        total_cost += cost[best]
        selected.append(
            {
                "config": best,
                "newly_covered": len(newly),
                "cost": cost[best],
                "covered_so_far": len(universe) - len(uncovered),
                "cost_so_far": total_cost,
            }
        )
    return {
        "universe": len(universe),
        "covered": len(universe) - len(uncovered),
        "never_covered": sorted(uncovered),
        "cost_basis": basis,
        "selected": selected,
        "configurations_considered": len(cost),
    }


# --- Cost ---------------------------------------------------------------------------------------

_RUNGS = {"a": ("a",), "b": ("a", "b1", "b2"), "c": ("a", "b1", "b2", "c")}


def _item_gate(row: Mapping[str, Any]) -> str:
    key = row["details"].get("item_key")
    return key.split("|")[1] if key else row["gate"]


def cost(
    rows: Iterable[Mapping[str, Any]], all_rows: Iterable[Mapping[str, Any]] | None = None
) -> dict[str, Any]:
    """GPU-seconds per kernel per gate item (median, p95), and per-kernel ladder costs.

    ``ladder``: ``b`` costs a + b1 + b2 for a kernel; ``c`` costs b + the c item;
    the Stage 1 rule compares their medians over kernels that have all four
    items. ``marginal``: per kernel, the items a rung adds over the previous
    one (a; b1 + b2; c), median and p95. ``amortized`` (needs ``all_rows``,
    every journal row of every attempt): all GPU-seconds spent on a rung's
    cumulative items (a; a, b1, b2; a, b1, b2, c), retried and
    infrastructure-failed attempts and shared ``validity`` precompute rows
    (charged to c) included, divided by the kernels with a final row for
    every one of those items.
    """
    rows = list(rows)
    per_item: dict[tuple[str, str, Any], float] = defaultdict(float)
    for row in rows:
        per_item[(row["kernel_id"], _item_gate(row), row.get("seed"))] += float(row["gpu_seconds"])
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
        marginal = {
            "a": [g["a"] for g in complete],
            "b": [g["b1"] + g["b2"] for g in complete],
            "c": [g["c"] for g in complete],
        }
        summary["marginal"] = {
            rung: {"median": statistics.median(v), "p95": p95(v)} for rung, v in marginal.items()
        }
    if all_rows is not None:
        spent: dict[str, float] = defaultdict(float)
        shared = 0.0
        for row in all_rows:
            gate = _item_gate(row)
            if gate == "validity":
                shared += float(row["gpu_seconds"])
            for rung, items in _RUNGS.items():
                if gate in items:
                    spent[rung] += float(row["gpu_seconds"])
        amortized = {}
        for rung, items in _RUNGS.items():
            kernels = sum(1 for g in by_kernel.values() if all(x in g for x in items))
            total = spent[rung] + (shared if rung == "c" else 0.0)
            amortized[rung] = {
                "gpu_seconds_total": total,
                "kernels": kernels,
                "per_kernel": (total / kernels) if kernels else None,
            }
        amortized["shared_validity_gpu_seconds"] = shared
        summary["amortized"] = amortized
    return summary
