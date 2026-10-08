"""Q1 Stage 0 validation job under ``q1-stage0-exec/2`` (decision D37 iii): rule
``q1-exec2-validation/1``.

Pure Python (no torch). D37 (iii): one lane job, within the 0.17 GPU-h left of
D31's 0.5, on the D31 re-pilot's non-evaluation kernels plus the three
KernelBench adversarial controls under the reference store, measures the safety
and cost of the memory-aware execution policy ``q1-stage0-exec/2``
(``harness.q1.memory``, the runner's free-memory guard and contention-safe
health check). This module is that job's registered rule, written before the
job runs. It decides which items the job queues and in which order; it never
changes a gate, tolerance, family, tier, sample, seed or verdict rule.

- **Kernels.** The re-pilot's 24 kernels (rule ``q1-repilot/1``: per S1-cal
  problem its substrate, its reference-identity control and one mutant; no
  evaluation unit, decision D28) and the three KernelBench adversarial controls
  (``controls.kernelbench_adversarial``; decision D29).
- **Re-pilot items.** Every kernel gets all 15 scoring gates at replicate 42
  through the reference store (``refschedule.with_references``: one reference
  item per problem and consumer channel, just before its first consumer; gate
  (a) is not a consumer). Units and estimated peak memory come from
  ``trim.item_units`` (``q1-stage0-exec/2``), watchdog limits from
  ``pilot.watchdog_limits``, as in a Stage 0 job.
- **Adversarial items.** The store's consumer gates (c, A1, A2, A3, A5), which
  never ran on these kernels, through the store, each followed by an inline twin
  (kernel id plus ``.inline``, no store) so the job checks the store on them
  (D37 ii-iii, section 18.9 "still open"). Their other gates (a, b1, b2, A4)
  read no reference, so the store cannot change them; their registered
  expectations were checked in pilot job 518 and are not rerun. The three
  kernels load a CUDA extension under one name (``fast_matmul``) with different
  sources; torch writes the sources into one shared build directory before its
  build lock and imports the library after it, so two of them in flight at once
  could load each other's library. Each adversarial kernel's items therefore
  require every item of the previous one (``requires``; a requirement that
  failed or was deferred counts as done).
- **Order.** The adversarial items first (kernel order ``ADVERSARIAL``), then the
  re-pilot kernels in rounds (substrates, then identity controls, then mutants),
  and within a round by ``PROBLEM_ORDER``: ascending model cost of one kernel
  replicate under ``q1-stage0-exec/2`` (the D31 cost card's size model and
  job-548 factors, times ``cost_card.concurrency_multiplier`` at each gate's
  units), so a time box cuts the problems the model expects to be most
  expensive, and every problem reached has its substrate first. The 0.17 GPU-h
  cap cannot hold every item (the model alone puts the re-pilot's 24 kernels at
  about 0.2 GPU-h); what the time box leaves is reported, never extrapolated as
  measured.
- **Exposure.** Every re-pilot kernel's problem is in the S1 calibration half
  and has no S2 substrate (``exposure``); the adversarial controls are on
  L1/1 and were already exposed in pilot job 518 (``pilot_exposed.json``).

The driver is ``scripts/run_q1_exec2_validation.py``.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Any

from harness.q1 import pilot, refstore, trim
from harness.q1.journal import item_key

RULE = "q1-exec2-validation/1"
REPLICATE = 42
INLINE_SUFFIX = ".inline"
SCORING_GATES = trim.SCORING_GATES
#: Consumer gates of the reference store (``refstore.CONSUMERS``), run on the
#: adversarial controls through the store and inline.
ADVERSARIAL_GATES: tuple[str, ...] = tuple(g for gs in refstore.CONSUMERS.values() for g in gs)
#: Adversarial controls (``controls.ADVERSARIAL_EXPECTED``) in run order.
ADVERSARIAL: tuple[str, ...] = ("result_reuse", "zero_out", "non_default_stream")
ADVERSARIAL_PROBLEM = "L1/1_Square_matrix_multiplication_"
#: The re-pilot's problems in ascending exec/2 model cost per kernel replicate
#: (GPU-seconds: L2/95 7.5, L2/77 10.1, L1/10 15.8, L1/18 20.5, L2/59 33.6,
#: L2/46 101.6, L2/100 126.3, L2/87 133.2). ``tests/test_q1_exec2_validation.py``
#: recomputes it from the committed D31 cost card.
PROBLEM_ORDER: tuple[str, ...] = (
    "L2/95_Matmul_Add_Swish_Tanh_GELU_Hardtanh",
    "L2/77_ConvTranspose3d_Scale_BatchNorm_GlobalAvgPool",
    "L1/10_3D_tensor_matrix_multiplication",
    "L1/18_Matmul_with_transposed_both",
    "L2/59_Matmul_Swish_Scaling",
    "L2/46_Conv2d_Subtract_Tanh_Subtract_AvgPool",
    "L2/100_ConvTranspose3d_Clamp_Min_Divide",
    "L2/87_Conv2d_Subtract_Subtract_Mish",
)
ROUNDS: tuple[str, ...] = ("substrate", "identity-control", "mutant")


def problem_order(cost: Callable[[str], float], problems: Iterable[str]) -> list[str]:
    """Problems by ascending ``cost`` (ties by id)."""
    return sorted(set(problems), key=lambda p: (round(float(cost(p)), 6), p))


def kernel_role(kernel_id: str) -> str:
    if kernel_id.startswith("ctl-identity-"):
        return "identity-control"
    if kernel_id.startswith("s1-inductor-") and kernel_id.count(".") == 0:
        return "substrate"
    return "mutant"


def round_robin(
    kernels: Sequence[Mapping[str, Any]], order: Sequence[str] = PROBLEM_ORDER
) -> list[dict[str, Any]]:
    """The re-pilot kernels in rounds (substrate, identity control, mutant), each round
    in ``order``; refuses kernels of other problems or a missing round."""
    by_problem: dict[str, dict[str, Mapping[str, Any]]] = {}
    for kernel in kernels:
        problem_id = kernel["problem_id"]
        if problem_id not in order:
            raise ValueError(f"{kernel['kernel_id']}: {problem_id} is not a re-pilot problem")
        role = kernel_role(kernel["kernel_id"])
        if role in by_problem.setdefault(problem_id, {}):
            raise ValueError(f"{problem_id} has two kernels of role {role}")
        by_problem[problem_id][role] = kernel
    if set(by_problem) != set(order):
        raise ValueError("the re-pilot kernels must cover every problem of the order")
    out = []
    for role in ROUNDS:
        for problem_id in order:
            if role not in by_problem[problem_id]:
                raise ValueError(f"{problem_id} has no {role}")
            out.append(dict(by_problem[problem_id][role]))
    return out


def _item(kernel: Mapping[str, Any], gate: str) -> dict[str, Any]:
    problem_id = kernel["problem_id"]
    units, peak = trim.item_units(problem_id, gate)
    return {
        "kernel_id": kernel["kernel_id"],
        "kernel_path": kernel["kernel_path"],
        "problem_id": problem_id,
        "gate": gate,
        "seed": REPLICATE,
        "problem_source_path": None,
        "options": {},
        "exclusive": units >= int(trim.TRIM_RULE["slot_capacity"]),
        "timeouts": dict(pilot.watchdog_limits(problem_id)),
        "units": units,
        "requires": [],
        "journal": None,
        "memory_bytes": peak,
    }


def items(
    repilot_kernels: Sequence[Mapping[str, Any]],
    adversarial_kernels: Sequence[Mapping[str, Any]],
    *,
    store_root: str,
    journal: str,
    store_cap_bytes: int | None = refstore.STORE_CAP_BYTES,
    over_cap: list[dict[str, Any]] | None = None,
    estimates: dict[str, int | None] | None = None,
) -> list[dict[str, Any]]:
    """Run-ordered ``WorkItem`` field dicts (module docstring).

    ``repilot_kernels`` and ``adversarial_kernels``: dicts with ``kernel_id``,
    ``kernel_path`` and ``problem_id``; the adversarial ones in ``ADVERSARIAL``
    order. ``journal``: the reference items' journal."""
    from harness.q1 import refschedule

    if [k["problem_id"] for k in adversarial_kernels] != [ADVERSARIAL_PROBLEM] * len(ADVERSARIAL):
        raise ValueError("expected the three adversarial controls of L1/1")
    store: list[dict[str, Any]] = []
    previous: list[str] = []
    for kernel in adversarial_kernels:
        mine: list[str] = []
        for gate in ADVERSARIAL_GATES:
            item = _item(kernel, gate)
            item["requires"] = list(previous)
            store.append(item)
            mine += [
                item_key(kernel["kernel_id"], gate, REPLICATE),
                item_key(kernel["kernel_id"] + INLINE_SUFFIX, gate, REPLICATE),
            ]
        previous = mine
    for kernel in round_robin(repilot_kernels):
        store += [_item(kernel, gate) for gate in SCORING_GATES]
    scheduled = refschedule.with_references(
        store,
        root=store_root,
        store_cap_bytes=store_cap_bytes,
        over_cap=over_cap,
        estimates=estimates,
    )
    adversarial_ids = {k["kernel_id"] for k in adversarial_kernels}
    out: list[dict[str, Any]] = []
    for entry in scheduled:
        if entry.get("journal"):
            out.append({**entry, "journal": journal})
            continue
        out.append(entry)
        if entry["kernel_id"] in adversarial_ids:
            twin = {
                **entry,
                "kernel_id": entry["kernel_id"] + INLINE_SUFFIX,
                "options": {k: v for k, v in entry["options"].items() if k != refstore.OPTION},
                "requires": [r for r in entry["requires"] if not r.startswith("reference.")],
            }
            out.append(twin)
    return out


def arm_of(kernel_id: str) -> tuple[str, str]:
    """(kernel id without the arm suffix, ``store`` or ``inline``)."""
    if kernel_id.endswith(INLINE_SUFFIX):
        return kernel_id[: -len(INLINE_SUFFIX)], "inline"
    return kernel_id, "store"


def exposure(
    repilot_kernels: Sequence[Mapping[str, Any]],
    adversarial_kernels: Sequence[Mapping[str, Any]],
    *,
    calibration: Iterable[str],
    evaluation: Iterable[str],
    s2_problems: Iterable[str],
    exposed: Mapping[str, Any],
) -> dict[str, Any]:
    """Which split half each kernel's problem is in; ``ok`` is False when a re-pilot
    kernel's problem is in the evaluation half or has an S2 substrate, or an
    adversarial control is not among the pilot-exposed controls."""
    calibration, evaluation, s2 = set(calibration), set(evaluation), set(s2_problems)
    exposed_controls = {c["kernel_id"] for c in exposed.get("controls", [])}
    rows = []
    for role, kernels in (("repilot", repilot_kernels), ("adversarial", adversarial_kernels)):
        for kernel in kernels:
            problem_id = kernel["problem_id"]
            rows.append(
                {
                    "kernel_id": kernel["kernel_id"],
                    "problem_id": problem_id,
                    "role": role,
                    "s1_half": "calibration"
                    if problem_id in calibration
                    else "evaluation"
                    if problem_id in evaluation
                    else None,
                    "problem_has_s2_substrate": problem_id in s2,
                    "pilot_exposed_control": kernel["kernel_id"] in exposed_controls,
                }
            )
    bad = [
        r
        for r in rows
        if (
            r["role"] == "repilot"
            and (r["s1_half"] != "calibration" or r["problem_has_s2_substrate"])
        )
        or (r["role"] == "adversarial" and not r["pilot_exposed_control"])
    ]
    return {"ok": not bad, "violations": bad, "kernels": rows}


def items_sha256(entries: Sequence[Mapping[str, Any]]) -> str:
    """SHA-256 of the queued items without kernel and store paths (the CPU plan and the
    job unpack the corpus at different places)."""
    body = [
        {
            k: v
            for k, v in entry.items()
            if k not in {"kernel_path", "journal"} and not (k == "options" and isinstance(v, dict))
        }
        | {"options": sorted((entry.get("options") or {}).keys())}
        for entry in entries
    ]
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()


__all__ = [
    "ADVERSARIAL",
    "ADVERSARIAL_GATES",
    "ADVERSARIAL_PROBLEM",
    "INLINE_SUFFIX",
    "PROBLEM_ORDER",
    "REPLICATE",
    "ROUNDS",
    "RULE",
    "arm_of",
    "exposure",
    "items",
    "items_sha256",
    "kernel_role",
    "problem_order",
    "round_robin",
]
