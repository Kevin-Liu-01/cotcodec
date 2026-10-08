"""Q1 Stage 0 pilot: which substrates it uses and in which order it scores work.

Pure Python (no torch). The pilot measures cost, not gate quality: per-gate
GPU-seconds (median, p95) and the projected Stage 0 total against the 8 GPU-h
cap (preregistration section 10). Its substrates are fixed by a rule written
before any GPU run, so neither admission outcomes nor cost can steer them.

**Selection rule** (``q1-pilot/1``). Each stratum is a predicate over built
substrates; inside a stratum, candidates are ordered by
``sha256("q1-pilot/v1/" + substrate_id)`` and the first ``n`` that pass the
static launch-path check and GPU admission are taken (a candidate that fails
is replaced by the next one in that order, and the replacement is recorded).

Evaluation strata (8 substrates, the cost-card sample):

- ``s1-eval-l1-activation``: S1 evaluation half, one of the 13 elementwise
  activations the hack controls target (1);
- ``s1-eval-l1-other``: S1 evaluation half, any other level-1 problem (1);
- ``s1-eval-l2``: S1 evaluation half, level 2 (2);
- ``s2-flaggems``, ``s2-liger``, ``s2-triton-tutorial``: one per S2 source (3);
- ``s2-any``: the next S2 substrate in key order not already taken (1).

Calibration stratum (``s1-cal``, 2 level-1 and 2 level-2 S1 calibration-half
substrates): runs A1 at M = 16 and replicate 42 only, to exercise the
calibration driver and measure its cost. Its mutants are never scored here.

**Schedule.** Work is ordered so that a time box cuts it at a deterministic
point and every kernel's gates run together (``schedule``): shared-class
substrates first (inputs below 1 GB, several items side by side), then one
control and two mutants of each, then the exclusive-class substrates in
ascending input size, then replicates 43 and 44, then the rest. Items the time
box cuts are counted and listed, never silently dropped. Problems whose
native inputs reach 1 GB run alone on the GPU (``exclusive_problem``) and get
watchdog limits that grow with input size (``watchdog_limits``).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from harness.q1.mutate.fixtures import ELEMENTWISE_ACTIVATIONS
from harness.q1.schema import MUTATION_FAMILIES, parse_problem_id

PILOT_VERSION = "q1-pilot/1"
KEY_PREFIX = "q1-pilot/v1/"

#: Every gate and audit channel that scores a kernel (the cost-card rows).
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
#: Fidelity gates: unmodified upstream code next to our implementation.
FIDELITY_GATES = (
    "a_upstream_44130946",
    "a_upstream_423217d9",
    "b_native",
    "c1_kbv_compat",
    "c1_kbv_native",
)
PRIMARY_SEED = 42
REPLICATE_SEEDS = (43, 44)
#: Problems whose native inputs reach this size run alone on their GPU: gate (c)
#: and audit A3 draw inputs up to twice the native bytes and replay them in fp64,
#: so two such items side by side can exhaust an 80 GB H100.
EXCLUSIVE_INPUT_BYTES = 1_000_000_000


@lru_cache(maxsize=1)
def _shape_manifest() -> dict[str, Any]:
    path = Path(__file__).resolve().parent / "data" / "shape_manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


def native_input_bytes(problem_id: str) -> int | None:
    """Native ``get_inputs()`` bytes from the committed shape manifest (meta device)."""
    entry = _shape_manifest()["problems"].get(problem_id, {})
    return (entry.get("native") or {}).get("input_bytes")


#: Watchdog rule for the pilot (measured in job 1: gate (a) on the L1/19 reference-
#: identity control needed more than the default 180 s correctness limit, because
#: KernelBench's CPU ``get_inputs`` for 6.4 GB of inputs dominates). Limits grow with
#: native input size: ``base + per_gb * GB`` per phase.
WATCHDOG_BASE = {"compile": 120.0, "correctness": 180.0, "timing": 300.0}
WATCHDOG_PER_GB = {"compile": 30.0, "correctness": 150.0, "timing": 60.0}


def watchdog_limits(problem_id: str) -> dict[str, float]:
    gigabytes = (native_input_bytes(problem_id) or 0) / 1e9
    return {
        phase: round(WATCHDOG_BASE[phase] + WATCHDOG_PER_GB[phase] * gigabytes, 1)
        for phase in WATCHDOG_BASE
    }


def exclusive_problem(problem_id: str) -> bool:
    size = native_input_bytes(problem_id)
    return size is None or size >= EXCLUSIVE_INPUT_BYTES


def pilot_key(substrate_id: str) -> str:
    """The rank of a substrate inside its stratum (smaller first)."""
    return hashlib.sha256(f"{KEY_PREFIX}{substrate_id}".encode()).hexdigest()


@dataclass(frozen=True)
class Stratum:
    name: str
    count: int
    role: str  # "evaluation" or "calibration"
    predicate: Callable[[Mapping[str, Any]], bool]


def _s1(half: str) -> Callable[[Mapping[str, Any]], bool]:
    return lambda c: c["source_kind"] == "inductor" and c.get("split_half") == half


def _level(candidate: Mapping[str, Any]) -> int:
    return parse_problem_id(candidate["problem_id"])[0]


STRATA: tuple[Stratum, ...] = (
    Stratum(
        "s1-eval-l1-activation",
        1,
        "evaluation",
        lambda c: _s1("evaluation")(c) and c["problem_id"] in ELEMENTWISE_ACTIVATIONS,
    ),
    Stratum(
        "s1-eval-l1-other",
        1,
        "evaluation",
        lambda c: (
            _s1("evaluation")(c)
            and _level(c) == 1
            and c["problem_id"] not in ELEMENTWISE_ACTIVATIONS
        ),
    ),
    Stratum("s1-eval-l2", 2, "evaluation", lambda c: _s1("evaluation")(c) and _level(c) == 2),
    Stratum("s2-flaggems", 1, "evaluation", lambda c: c["source_kind"] == "flaggems"),
    Stratum("s2-liger", 1, "evaluation", lambda c: c["source_kind"] == "liger"),
    Stratum("s2-triton-tutorial", 1, "evaluation", lambda c: c["source_kind"] == "triton-tutorial"),
    Stratum("s2-any", 1, "evaluation", lambda c: c["source_kind"] != "inductor"),
    Stratum("s1-cal-l1", 2, "calibration", lambda c: _s1("calibration")(c) and _level(c) == 1),
    Stratum("s1-cal-l2", 2, "calibration", lambda c: _s1("calibration")(c) and _level(c) == 2),
)


def select_pilot(
    candidates: Iterable[Mapping[str, Any]],
    *,
    eligible: Callable[[Mapping[str, Any]], bool] = lambda c: True,
) -> dict[str, Any]:
    """Apply the selection rule. ``candidates`` need ``substrate_id``, ``problem_id``,
    ``source_kind`` and, for S1, ``split_half``; ``eligible`` says whether a
    candidate passed the static check and admission (unknown counts as eligible
    when the rule is applied before admission, to list the expected picks)."""
    pool = sorted(candidates, key=lambda c: pilot_key(c["substrate_id"]))
    taken: set[str] = set()
    strata: list[dict[str, Any]] = []
    for stratum in STRATA:
        members = [c for c in pool if stratum.predicate(c)]
        chosen: list[str] = []
        skipped: list[str] = []
        for candidate in members:
            if len(chosen) == stratum.count:
                break
            if candidate["substrate_id"] in taken:
                continue
            if not eligible(candidate):
                skipped.append(candidate["substrate_id"])
                continue
            chosen.append(candidate["substrate_id"])
            taken.add(candidate["substrate_id"])
        strata.append(
            {
                "stratum": stratum.name,
                "role": stratum.role,
                "wanted": stratum.count,
                "chosen": chosen,
                "replaced_ineligible": skipped,
                "candidates": len(members),
            }
        )
    return {
        "pilot_version": PILOT_VERSION,
        "rule": "per stratum, ascending sha256('q1-pilot/v1/' + substrate_id); "
        "ineligible candidates are skipped and listed",
        "strata": strata,
        "evaluation": [s for row in strata if row["role"] == "evaluation" for s in row["chosen"]],
        "calibration": [s for row in strata if row["role"] == "calibration" for s in row["chosen"]],
    }


@dataclass(frozen=True)
class PlannedItem:
    tier: str
    kernel_id: str
    kernel_path: str
    problem_id: str
    gate: str
    seed: int


def _round_robin(groups: Sequence[Sequence[Any]]) -> list[Any]:
    out: list[Any] = []
    depth = max((len(group) for group in groups), default=0)
    for index in range(depth):
        for group in groups:
            if index < len(group):
                out.append(group[index])
    return out


def order_mutants(mutants: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """One substrate's mutants: families in schema order, round robin, then by
    ``sha256(mutant_id)`` inside a family."""
    by_family: dict[str, list[Mapping[str, Any]]] = {f: [] for f in MUTATION_FAMILIES}
    for mutant in mutants:
        by_family.setdefault(mutant["family"], []).append(mutant)
    groups = [
        sorted(members, key=lambda m: hashlib.sha256(m["kernel_id"].encode()).hexdigest())
        for _, members in sorted(
            by_family.items(),
            key=lambda kv: (
                MUTATION_FAMILIES.index(kv[0]) if kv[0] in MUTATION_FAMILIES else 99,
                kv[0],
            ),
        )
    ]
    return _round_robin(groups)


def schedule(
    substrates: Sequence[Mapping[str, Any]],
    controls: Mapping[str, Sequence[Mapping[str, Any]]],
    mutants: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    gates: Sequence[str] = SCORING_GATES,
    mutant_rounds: int = 2,
) -> list[PlannedItem]:
    """The pilot's scoring order. ``substrates``: pilot evaluation substrates in
    selection order (``kernel_id``, ``kernel_path``, ``problem_id``);
    ``controls`` and ``mutants``: per substrate id, kernels with the same keys
    (mutants also ``family``).

    Shared-class substrates (inputs below 1 GB) come first because several run
    side by side; exclusive ones (each holds the GPU alone) follow in ascending
    input size, so the time box always measures every gate on the small
    problems and as many gates as fit on the large ones:

    - P0: shared substrates, every gate, replicate 42;
    - P1: one control per shared substrate (round robin);
    - P2: ``mutant_rounds`` rounds of one mutant per shared substrate;
    - P3: exclusive substrates, ascending native input bytes, every gate;
    - P4: replicates 43 and 44 of the shared substrates;
    - P5: the remaining mutants and controls, shared substrates first.
    """

    def items(tier: str, kernel: Mapping[str, Any], seed: int) -> list[PlannedItem]:
        return [
            PlannedItem(
                tier, kernel["kernel_id"], kernel["kernel_path"], kernel["problem_id"], gate, seed
            )
            for gate in gates
        ]

    shared = [s for s in substrates if not exclusive_problem(s["problem_id"])]
    large = sorted(
        (s for s in substrates if exclusive_problem(s["problem_id"])),
        key=lambda s: native_input_bytes(s["problem_id"]) or 0,
    )
    plan: list[PlannedItem] = []
    for substrate in shared:
        plan += items("P0", substrate, PRIMARY_SEED)
    control_groups = {s["kernel_id"]: list(controls.get(s["kernel_id"], ())) for s in substrates}
    mutant_groups = {
        s["kernel_id"]: order_mutants(mutants.get(s["kernel_id"], ())) for s in substrates
    }
    for kernel in _round_robin([control_groups[s["kernel_id"]][:1] for s in shared]):
        plan += items("P1", kernel, PRIMARY_SEED)
    for kernel in _round_robin([mutant_groups[s["kernel_id"]][:mutant_rounds] for s in shared]):
        plan += items("P2", kernel, PRIMARY_SEED)
    for substrate in large:
        plan += items("P3", substrate, PRIMARY_SEED)
    for substrate in shared:
        for seed in REPLICATE_SEEDS:
            plan += items("P4", substrate, seed)
    rest = _round_robin(
        [
            mutant_groups[s["kernel_id"]][mutant_rounds:] + control_groups[s["kernel_id"]][1:]
            for s in shared
        ]
    ) + _round_robin(
        [mutant_groups[s["kernel_id"]] + control_groups[s["kernel_id"]] for s in large]
    )
    for kernel in rest:
        plan += items("P5", kernel, PRIMARY_SEED)
    return plan


__all__ = [
    "FIDELITY_GATES",
    "PILOT_VERSION",
    "PlannedItem",
    "SCORING_GATES",
    "STRATA",
    "order_mutants",
    "pilot_key",
    "schedule",
    "select_pilot",
]
