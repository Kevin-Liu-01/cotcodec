"""Q1 Stage 0 trimming rule ``q1-stage0-trim/2``: what Stage 0 scores, in which order,
how much runs at once, and how it stops (preregistration section 18.6).

Pure Python (no torch). The rule is applied to the Stage 0 corpus on the CPU
before any Stage 0 scoring job; ``scripts/run_q1_stage0.py`` runs the plan it
produces and nothing else, and ``scripts/report_q1_stage0.py`` reads the same
plan record for the Horvitz-Thompson weights, the control schedule and the
pilot-exposure sensitivity analysis. Every random choice is a seeded
permutation whose seed is ``sha256("q1-stage0-trim/2/<purpose>/...")``, so the
plan is a pure function of the corpus, this module and
``data/pilot_exposed.json``.

Differences from the proposed ``q1-stage0-trim/1`` (pilot pass, never adopted),
each answering a finding of the second adversarial review:

- **Pilot exposure.** Mutants the pilot scored (``data/pilot_exposed.json``)
  are removed from every sampling frame, so no sampled mutant has a known
  verdict. Pilot-scored substrates are scored again (their verdicts feed the
  parent filter); the analysis reports every primary quantity also without the
  pilot-exposed units (a pre-specified sensitivity analysis), and drops from
  the primary analysis any unit whose correctness a data-motivated audit change
  would alter (``data_motivated_units``).
- **FRR set with a margin.** Out-of-scope evaluation substrates are added in
  ascending native input bytes, skipping substrates whose independent unit is
  already in the set, until ``frr_min_units`` admitted units (the *core*,
  bucket P1) and then ``frr_margin_units`` more (the *margin*, bucket P3).
- **Every control kind is accounted for.** Hack-control kinds are sampled per
  kind; kinds with no in-scope applicable substrate (the KBV H.1 identity
  shortcuts and the hack-emulating mutant controls, all on problems of 6.4 GB
  and more) are listed as not scheduled, never silently absent.
- **Seeds, frames and weights are explicit** (``seed_of``, ``mutant_frames``,
  ``ht_weights``), and the priority order is rank-major across families so a
  cut leaves every family a simple random sample.
- **Execution classes and the stop.** Concurrency units by native input size,
  size-scaled watchdog limits on every item, contention failures retried alone
  (``runner``), and a stop enforced by Slurm job caps (``budget_check``).
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from harness.q1 import pilot
from harness.q1.schema import MUTATION_FAMILIES

RULE_VERSION = "q1-stage0-trim/2"
SEED_PREFIX = RULE_VERSION
PRIMARY_SEED = 42
REPLICATE_SEEDS = (43, 44)
SCORING_GATES = pilot.SCORING_GATES

#: The registered rule (preregistration section 18.6). ``cost_card`` projects it;
#: ``plan`` applies it.
TRIM_RULE: dict[str, Any] = {
    "name": RULE_VERSION,
    "scope_bytes": 1_000_000_000,
    "frr_min_units": 72,
    "frr_margin_units": 6,
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
    "timing_floor_job_gpus": 8,
    "timing_floor_timing_gpus": 2,
    # Execution (measured conditions of jobs 518 and 548): one GPU and 32 CPUs per
    # scoring job, one Stage 0 job at a time, 12 capacity units per GPU.
    "gpus_per_job": 1,
    "cpus_per_job": 32,
    "concurrent_stage0_jobs": 1,
    "slot_capacity": 12,
    "small_below_bytes": 600_000_000,
    "units_small": 1,
    "units_medium": 3,
    "gpu_hour_cap_total": 8.0,
}

BUCKETS: dict[str, str] = {
    "P1": "in-scope evaluation substrates, identity controls, the hack-control sample and the "
    "adversarial controls at replicate 42; then the FRR-set core (out-of-scope substrates "
    "up to frr_min_units admitted units) at replicate 42",
    "P2": "test-quota mutants at replicate 42, rank-major across families",
    "P3": "the hack-control sample and the adversarial controls at replicates 43 and 44",
    "P4": "the FRR-set margin (frr_margin_units more units) at replicate 42",
    "P5": "in-scope evaluation substrates at replicates 43 and 44",
    "P6": "the mutant robustness subsample at replicates 43 and 44",
    "P7": "dev-quota mutants at replicate 42, rank-major across families",
    "P8": "further test-split mutants up to family_quota_test_max per family at replicate 42, "
    "rank-major across families",
}

PILOT_EXPOSED_PATH = Path(__file__).resolve().parent / "data" / "pilot_exposed.json"
#: SHA-256 of ``data/pilot_exposed.json`` (written by ``scripts/q1_pilot_records.py``
#: from the pilot jobs' journals); ``load_exposed`` refuses any other file.
PILOT_EXPOSED_SHA256 = "cb4a0c369d5ae5f3bc5e0c9e52d4ba2ab3f4d27905df4ce86bc3c70489875646"


# --- seeds -------------------------------------------------------------------------


def seed_of(*parts: object) -> int:
    """The seed of one random choice: ``sha256("q1-stage0-trim/2/<parts...>")``, first 8 bytes."""
    text = "/".join([SEED_PREFIX, *map(str, parts)])
    return int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "big")


def seeded_order(ids: Iterable[str], *parts: object) -> list[str]:
    """A seeded permutation of ``ids`` (sorted first, so input order never matters)."""
    ordered = sorted(set(ids))
    random.Random(seed_of(*parts)).shuffle(ordered)
    return ordered


def sample_size(fraction: float, n: int, minimum: int = 1) -> int:
    """``ceil(fraction * n)``, at least ``minimum`` when ``n`` is positive."""
    if n <= 0:
        return 0
    return min(n, max(minimum, math.ceil(fraction * n - 1e-9)))


# --- execution classes -------------------------------------------------------------


def concurrency_class(problem_id: str, rule: Mapping[str, Any] = TRIM_RULE) -> str:
    size = pilot.native_input_bytes(problem_id)
    if size is None or size >= int(rule["scope_bytes"]):
        return "exclusive"
    return "small" if size < int(rule["small_below_bytes"]) else "medium"


def concurrency_units(problem_id: str, rule: Mapping[str, Any] = TRIM_RULE) -> int:
    """Capacity units an item holds on its GPU (``slot_capacity`` = alone)."""
    klass = concurrency_class(problem_id, rule)
    if klass == "exclusive":
        return int(rule["slot_capacity"])
    return int(rule["units_small"] if klass == "small" else rule["units_medium"])


# --- corpus records ----------------------------------------------------------------


@dataclass(frozen=True)
class KernelRecord:
    kernel_id: str
    kernel_path: str
    problem_id: str
    kind: str  # substrate | mutant | control
    half: str | None = None  # evaluation | calibration (substrates and mutants)
    unit: str | None = None  # independent unit (kernel family) of a substrate
    parent: str | None = None  # parent substrate of a mutant or derived control
    family: str | None = None
    split: str | None = None
    dedup_hash: str | None = None
    control_kind: str | None = None
    hack_kind: str | None = None  # control id suffix after ".hack."
    base_weight: float | None = None

    @property
    def native_bytes(self) -> int:
        return int(pilot.native_input_bytes(self.problem_id) or 0)


def records_from_corpus(corpus_roots: Sequence[Path]) -> list[KernelRecord]:
    """One record per kernel directory under the corpus roots (substrates of both
    S1 halves and S2, mutants with their ``mutants.jsonl`` weights, and controls)."""
    from harness.q1 import analysis
    from harness.q1.schema import iter_kernel_dirs

    table = analysis.kernel_table(corpus_roots)
    halves = analysis.substrate_halves(table, analysis.s1_split())
    half_of = {k: "evaluation" for k in halves["evaluation"]}
    half_of.update({k: "calibration" for k in halves["calibration"]})
    out: list[KernelRecord] = []
    for root in corpus_roots:
        for kernel in iter_kernel_dirs(root):
            facts = table[kernel.kernel_id]
            parent = facts.get("parent_substrate_id")
            hack_kind = None
            if facts["kind"] == "control":
                if ".hack." in kernel.kernel_id:
                    parent, hack_kind = kernel.kernel_id.split(".hack.", 1)
                elif kernel.kernel_id.endswith(".control"):
                    mutant_id = kernel.kernel_id.removesuffix(".control")
                    parent = mutant_id.split(".", 1)[0]
                    hack_kind = "hack-emulating-mutant"
            out.append(
                KernelRecord(
                    kernel_id=kernel.kernel_id,
                    kernel_path=str(kernel.kernel_path),
                    problem_id=kernel.problem_id,
                    kind=facts["kind"],
                    half=half_of.get(parent if facts["kind"] == "mutant" else kernel.kernel_id),
                    unit=facts.get("kernel_family"),
                    parent=parent,
                    family=facts.get("family"),
                    split=facts.get("split"),
                    dedup_hash=(kernel.mutation or {}).get("dedup_hash"),
                    control_kind=facts.get("control_kind"),
                    hack_kind=hack_kind,
                    base_weight=facts.get("weight"),
                )
            )
    return sorted(out, key=lambda r: r.kernel_id)


# --- pilot exposure ----------------------------------------------------------------


def load_exposed(path: Path | None = None, *, check: bool = True) -> dict[str, Any]:
    """The pilot-exposed kernels and units (``scripts/q1_pilot_records.py``), hash-checked."""
    path = Path(path) if path is not None else PILOT_EXPOSED_PATH
    data = path.read_bytes()
    if check and hashlib.sha256(data).hexdigest() != PILOT_EXPOSED_SHA256:
        raise ValueError(f"{path} does not match PILOT_EXPOSED_SHA256")
    return json.loads(data)


def exposed_mutant_keys(exposed: Mapping[str, Any]) -> tuple[set[str], set[tuple[str, str]]]:
    """Exposed mutants by id and by ``(parent substrate, dedup hash)``."""
    ids = {m["kernel_id"] for m in exposed.get("mutants", [])}
    content = {(m["parent"], m["dedup_hash"]) for m in exposed.get("mutants", [])}
    return ids, content


# --- the FRR set ---------------------------------------------------------------------


def frr_set(
    substrates: Sequence[KernelRecord], rule: Mapping[str, Any] = TRIM_RULE
) -> dict[str, Any]:
    """In-scope evaluation substrates, then out-of-scope ones in ascending native input
    bytes (ties by substrate id), skipping a substrate whose unit is already present,
    until ``frr_min_units`` units (core, P1) and ``frr_margin_units`` more (margin, P4)."""
    scope = int(rule["scope_bytes"])
    in_scope = sorted((s for s in substrates if s.native_bytes < scope), key=lambda s: s.kernel_id)
    units = {s.unit or s.kernel_id for s in in_scope}
    target_core = int(rule["frr_min_units"])
    target = target_core + int(rule["frr_margin_units"])
    core: list[KernelRecord] = []
    margin: list[KernelRecord] = []
    skipped: list[str] = []
    for sub in sorted(
        (s for s in substrates if s.native_bytes >= scope),
        key=lambda s: (s.native_bytes, s.kernel_id),
    ):
        if len(units) >= target:
            break
        unit = sub.unit or sub.kernel_id
        if unit in units:
            skipped.append(sub.kernel_id)
            continue
        (core if len(units) < target_core else margin).append(sub)
        units.add(unit)
    return {
        "in_scope": in_scope,
        "core": core,
        "margin": margin,
        "skipped_no_new_unit": skipped,
        "in_scope_units": len({s.unit or s.kernel_id for s in in_scope}),
        "units_with_core": len({s.unit or s.kernel_id for s in [*in_scope, *core]}),
        "units_with_margin": len(units),
    }


# --- mutant sampling -----------------------------------------------------------------


def mutant_frames(
    mutants: Sequence[KernelRecord],
    in_scope_parents: set[str],
    exposed: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Per (family, split): capped mutants of in-scope evaluation parents, without the
    pilot-exposed ones, as seeded permutations. ``N`` of the Horvitz-Thompson factor
    is the frame size."""
    ids, content = exposed_mutant_keys(exposed or {})
    frames: dict[str, dict[str, list[str]]] = {
        f: {"test": [], "dev": []} for f in MUTATION_FAMILIES
    }
    removed: list[str] = []
    for m in mutants:
        if m.parent not in in_scope_parents:
            continue
        if m.kernel_id in ids or (m.parent, m.dedup_hash) in content:
            removed.append(m.kernel_id)
            continue
        frames.setdefault(m.family or "unknown", {"test": [], "dev": []})[m.split or "test"].append(
            m.kernel_id
        )
    ordered = {
        family: {
            split: seeded_order(members, "mutants", family, split) for split, members in sp.items()
        }
        for family, sp in frames.items()
    }
    return {"frames": ordered, "exposed_removed": sorted(removed)}


def mutant_sample(
    frames: Mapping[str, Mapping[str, Sequence[str]]], rule: Mapping[str, Any] = TRIM_RULE
) -> dict[str, dict[str, list[str]]]:
    """Prefixes of each family's seeded permutations: test quota, its robustness
    subsample (the first ``ceil(fraction * quota)``), the test extension and the dev
    quota. Each prefix of a uniform permutation is a simple random sample."""
    out: dict[str, dict[str, list[str]]] = {}
    for family, splits in frames.items():
        test, dev = list(splits.get("test", ())), list(splits.get("dev", ()))
        quota = test[: int(rule["family_quota_test"])]
        out[family] = {
            "test_quota": quota,
            "robustness": quota[
                : sample_size(float(rule["mutant_robustness_fraction"]), len(quota))
            ],
            "test_extension": test[
                int(rule["family_quota_test"]) : int(rule["family_quota_test_max"])
            ],
            "dev_quota": dev[: int(rule["family_quota_dev"])],
        }
    return out


def family_order() -> list[str]:
    """The seeded family order of the rank-major buckets."""
    return seeded_order(MUTATION_FAMILIES, "family-order")


def rank_major(groups: Mapping[str, Sequence[str]]) -> list[str]:
    """Rank 0 of every family (seeded family order), then rank 1, ... A cut at any
    point leaves each family a prefix of its permutation."""
    order = [f for f in family_order() if f in groups] + sorted(
        f for f in groups if f not in MUTATION_FAMILIES
    )
    depth = max((len(groups[f]) for f in order), default=0)
    return [groups[f][r] for r in range(depth) for f in order if r < len(groups[f])]


# --- controls -------------------------------------------------------------------------


def control_schedule(
    controls: Sequence[KernelRecord],
    in_scope_substrates: set[str],
    evaluation_problems: set[str],
    rule: Mapping[str, Any] = TRIM_RULE,
) -> dict[str, Any]:
    """Which controls are scored. Identity controls of in-scope problems; per hack kind a
    seeded ``hack_fraction`` (at least one) of its in-scope instances; the three
    KernelBench adversarial controls. Every other control is listed as not scheduled
    with its reason (kinds with no in-scope instance among them)."""
    identity, adversarial = [], []
    hacks: dict[str, list[str]] = defaultdict(list)
    not_scheduled: dict[str, list[str]] = defaultdict(list)
    for c in controls:
        if c.control_kind == "reference-identity":
            if c.native_bytes < int(rule["scope_bytes"]) and c.problem_id in evaluation_problems:
                identity.append(c.kernel_id)
            else:
                not_scheduled["identity-out-of-scope"].append(c.kernel_id)
        elif c.control_kind == "kernelbench-adversarial":
            adversarial.append(c.kernel_id)
        elif c.hack_kind is not None:
            if c.parent in in_scope_substrates:
                hacks[c.hack_kind].append(c.kernel_id)
            else:
                not_scheduled[f"{c.hack_kind}:parent-out-of-scope"].append(c.kernel_id)
        else:
            not_scheduled["unknown-control-kind"].append(c.kernel_id)
    sample = {
        kind: seeded_order(members, "hack", kind)[
            : sample_size(float(rule["hack_fraction"]), len(members))
        ]
        for kind, members in sorted(hacks.items())
    }
    for kind, members in hacks.items():
        chosen = set(sample[kind])
        rest = [m for m in members if m not in chosen]
        if rest:
            not_scheduled[f"{kind}:not-sampled"].extend(rest)
    kinds_without_instance = sorted(
        {k.split(":", 1)[0] for k in not_scheduled if k.endswith(":parent-out-of-scope")}
        - set(sample)
    )
    return {
        "identity": sorted(identity),
        "adversarial": sorted(adversarial),
        "hack_sample": sample,
        "not_scheduled": {k: sorted(v) for k, v in sorted(not_scheduled.items())},
        "kinds_without_in_scope_instance": kinds_without_instance,
    }


# --- the plan ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PlannedItem:
    bucket: str
    kernel_id: str
    kernel_path: str
    problem_id: str
    gate: str
    seed: int
    units: int
    timeouts: dict[str, float]


def _items(
    bucket: str,
    record: KernelRecord,
    seeds: Sequence[int],
    gates: Sequence[str],
    rule: Mapping[str, Any],
) -> list[PlannedItem]:
    units = concurrency_units(record.problem_id, rule)
    limits = pilot.watchdog_limits(record.problem_id)
    return [
        PlannedItem(
            bucket, record.kernel_id, record.kernel_path, record.problem_id, g, s, units, limits
        )
        for s in seeds
        for g in gates
    ]


def plan(
    records: Sequence[KernelRecord],
    *,
    rule: Mapping[str, Any] = TRIM_RULE,
    exposed: Mapping[str, Any] | None = None,
    gates: Sequence[str] = SCORING_GATES,
) -> dict[str, Any]:
    """Apply the rule to the corpus records: the FRR set, the mutant frames and
    samples, the control schedule and every planned item in bucket order."""
    by_id = {r.kernel_id: r for r in records}
    evaluation = [r for r in records if r.kind == "substrate" and r.half == "evaluation"]
    frr = frr_set(evaluation, rule)
    in_scope = frr["in_scope"]
    in_scope_ids = {s.kernel_id for s in in_scope}
    mutants = [r for r in records if r.kind == "mutant" and r.half == "evaluation"]
    framed = mutant_frames(mutants, in_scope_ids, exposed)
    sample = mutant_sample(framed["frames"], rule)
    controls = control_schedule(
        [r for r in records if r.kind == "control"],
        in_scope_ids,
        {r.problem_id for r in evaluation},
        rule,
    )
    items: list[PlannedItem] = []

    def add(bucket: str, ids: Iterable[str], seeds: Sequence[int]) -> None:
        small_first = sorted(
            ids,
            key=lambda k: (
                concurrency_units(by_id[k].problem_id, rule) >= int(rule["slot_capacity"])
            ),
        )
        for kernel_id in small_first:
            items.extend(_items(bucket, by_id[kernel_id], seeds, gates, rule))

    hack_ids = [
        k for kind in sorted(controls["hack_sample"]) for k in controls["hack_sample"][kind]
    ]
    p1 = [s.kernel_id for s in in_scope] + controls["identity"] + hack_ids + controls["adversarial"]
    add("P1", p1, [PRIMARY_SEED])
    add("P1", [s.kernel_id for s in frr["core"]], [PRIMARY_SEED])
    add("P2", rank_major({f: v["test_quota"] for f, v in sample.items()}), [PRIMARY_SEED])
    add("P3", hack_ids + controls["adversarial"], REPLICATE_SEEDS)
    add("P4", [s.kernel_id for s in frr["margin"]], [PRIMARY_SEED])
    add("P5", [s.kernel_id for s in in_scope], REPLICATE_SEEDS)
    add("P6", rank_major({f: v["robustness"] for f, v in sample.items()}), REPLICATE_SEEDS)
    add("P7", rank_major({f: v["dev_quota"] for f, v in sample.items()}), [PRIMARY_SEED])
    add("P8", rank_major({f: v["test_extension"] for f, v in sample.items()}), [PRIMARY_SEED])
    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"items": 0, "kernel_replicates": 0})
    for item in items:
        counts[item.bucket]["items"] += 1
    for bucket in counts:
        counts[bucket]["kernel_replicates"] = len(
            {(i.kernel_id, i.seed) for i in items if i.bucket == bucket}
        )
    record = {
        "rule": dict(rule),
        "rule_version": RULE_VERSION,
        "buckets": dict(BUCKETS),
        "family_order": family_order(),
        "frr_set": {
            "in_scope": [s.kernel_id for s in in_scope],
            "core": [s.kernel_id for s in frr["core"]],
            "margin": [s.kernel_id for s in frr["margin"]],
            "skipped_no_new_unit": frr["skipped_no_new_unit"],
            "in_scope_units": frr["in_scope_units"],
            "units_with_core": frr["units_with_core"],
            "units_with_margin": frr["units_with_margin"],
        },
        "mutant_frames": {
            f: {split: list(ids) for split, ids in sp.items()} for f, sp in framed["frames"].items()
        },
        "mutants_exposed_removed": framed["exposed_removed"],
        "mutant_sample": sample,
        "controls": controls,
        "exposed_sha256": None
        if exposed is None
        else hashlib.sha256(json.dumps(exposed, sort_keys=True).encode()).hexdigest(),
        "bucket_counts": {b: counts[b] for b in BUCKETS if b in counts},
        "items": [asdict(i) for i in items],
    }
    record["plan_sha256"] = plan_digest(record)
    return record


def plan_digest(record: Mapping[str, Any]) -> str:
    body = {k: v for k, v in record.items() if k != "plan_sha256"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()


# --- weights and scheduled controls for the analysis ------------------------------------


def scored_kernel_replicates(
    final_items: Iterable[tuple[str, str, int]], gates: Sequence[str] = SCORING_GATES
) -> set[tuple[str, int]]:
    """(kernel, replicate) pairs whose every scoring item has a final row."""
    have: dict[tuple[str, int], set[str]] = defaultdict(set)
    for kernel_id, gate, seed in final_items:
        have[(kernel_id, int(seed))].add(gate)
    return {key for key, done in have.items() if set(gates) <= done}


def ht_weights(
    record: Mapping[str, Any],
    scored: set[str],
    base_weights: Mapping[str, float | None],
) -> dict[str, Any]:
    """Horvitz-Thompson weights of scored sampled mutants: ``(n/k) x (N_fs / m_fs)``.

    ``N_fs`` is the frame size of family ``f`` and split ``s`` (exposed mutants
    removed); ``m_fs`` the frame members scored at replicate 42 with every scoring
    gate final (``scored``). Mutants the stop cut, or that never started, are not
    in ``m_fs`` and are listed per family and split.
    """
    weights: dict[str, float] = {}
    factors: dict[str, dict[str, Any]] = {}
    for family, splits in record["mutant_frames"].items():
        for split, frame in splits.items():
            done = [k for k in frame if k in scored]
            sampled = (
                set(record["mutant_sample"].get(family, {}).get("test_quota", ()))
                | set(record["mutant_sample"].get(family, {}).get("test_extension", ()))
                | set(record["mutant_sample"].get(family, {}).get("dev_quota", ()))
            )
            factor = (len(frame) / len(done)) if done else None
            factors[f"{family}/{split}"] = {
                "N": len(frame),
                "m": len(done),
                "factor": factor,
                "sampled_not_scored": sorted(k for k in frame if k in sampled and k not in scored),
            }
            for k in done:
                base = base_weights.get(k)
                weights[k] = (1.0 if base is None else float(base)) * (factor or 0.0)
    return {"weights": weights, "factors": factors}


def scheduled_controls(record: Mapping[str, Any]) -> dict[int, set[str]]:
    """Controls the plan scores, per replicate (criterion 5's cells under the rule)."""
    out: dict[int, set[str]] = defaultdict(set)
    controls = record["controls"]
    hacks = {k for ids in controls["hack_sample"].values() for k in ids}
    for seed in (PRIMARY_SEED, *REPLICATE_SEEDS):
        out[seed] |= hacks | set(controls["adversarial"])
    out[PRIMARY_SEED] |= set(controls["identity"])
    return dict(out)


# --- budget ------------------------------------------------------------------------------


def budget_check(
    *,
    spent_gpu_hours: float,
    job_cap_gpu_hours: float,
    reserve_gpu_hours: float,
    rule: Mapping[str, Any] = TRIM_RULE,
) -> dict[str, Any]:
    """The stop, enforced by caps: a Stage 0 scoring job may start only if every
    Stage 0 GPU-hour already spent (pilot included, from the Slurm records), this
    job's cap (its Slurm time limit times its GPUs, the manifest's
    ``max_gpu_hours``) and the reserve (timing floor and replay cap) fit in the
    total. Slurm ends the job at its limit, so the sum of caps bounds the spend."""
    total = float(rule["gpu_hour_cap_total"])
    needed = spent_gpu_hours + job_cap_gpu_hours + reserve_gpu_hours
    return {
        "spent_gpu_hours": spent_gpu_hours,
        "job_cap_gpu_hours": job_cap_gpu_hours,
        "reserve_gpu_hours": reserve_gpu_hours,
        "total_cap_gpu_hours": total,
        "headroom_gpu_hours": round(total - needed, 6),
        "ok": needed <= total + 1e-9 and job_cap_gpu_hours > 0,
    }


__all__ = [
    "BUCKETS",
    "KernelRecord",
    "PILOT_EXPOSED_PATH",
    "PILOT_EXPOSED_SHA256",
    "PlannedItem",
    "RULE_VERSION",
    "TRIM_RULE",
    "budget_check",
    "concurrency_class",
    "concurrency_units",
    "control_schedule",
    "exposed_mutant_keys",
    "family_order",
    "frr_set",
    "ht_weights",
    "load_exposed",
    "mutant_frames",
    "mutant_sample",
    "plan",
    "plan_digest",
    "rank_major",
    "records_from_corpus",
    "sample_size",
    "scheduled_controls",
    "scored_kernel_replicates",
    "seed_of",
    "seeded_order",
]
