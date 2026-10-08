"""Audit calibration driver (preregistration section 6.1): choose M once, freeze audit v1.

Pure Python over journal rows (torch-free). Inputs are the final A1 rows of
the calibration run at replicate 42 under the default multiplier
(``oracle.DEFAULT_MULTIPLIER`` = 16) and the corpus table.

**Members.** Calibration uses the S1 calibration half only: substrates whose
``source_kind`` is ``inductor`` and whose problem is in the frozen S1
calibration split (``analysis.s1_split``). Which of them are "correct"
cannot be decided by A1 itself (that is what is being calibrated), so the
rule is set by tolerance-free facts and a fault ceiling:

- a substrate whose A1 draws are not all admissible (the reference raised)
  is ``excluded-unrefereeable``;
- a substrate that raises on a native draw is ``fault-candidate-raised``
  (D14: a refusal at native shapes is a fault);
- a substrate whose required multiplier exceeds :data:`FAULT_CEILING`
  (``DEFAULT_MULTIPLIER x PRECISION_ONLY_FACTOR`` = 1024: it fails A1 even
  at 64·T, the precision-only boundary) or is infinite is
  ``fault-candidate-error``;
- every other substrate is a ``member``.

Fault candidates do not move M; they are listed for adjudication like any
natural fault (an upstream fix or a second implementation that agrees with
fp64), and they are S1-cal, so they never enter FRR.

**Required multiplier** of one draw, with ``e`` the candidate's error and
``E`` the largest finite reference error that sets T under the policy
(``e_r32_device``, ``e_r32_cpu``, and ``e_r32_tf32`` when the TF32-admissible
policy applied it), since ``T = max(M · E, T_FLOOR)``:

- ``0`` when ``e <= T_FLOOR`` (any M passes; this is the exact-reference
  case, e.g. ReLU or HardTanh with ``E = 0``);
- ``0`` when no reference error is finite (T is infinite);
- ``inf`` when ``e`` is not finite, or ``E = 0`` and ``e > T_FLOOR`` (no M
  passes);
- ``e / E`` otherwise.

A member's required multiplier is the largest over its draws. M is the
smallest power of two that is at least 16 and at least every member's
requirement (``oracle.calibrate_multiplier``), raised at most once. The
result names the frozen audit version (``tiers.audit_version_hash``).
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from harness.q1.audit.oracle import (
    DEFAULT_MULTIPLIER,
    PRECISION_ONLY_FACTOR,
    T_FLOOR,
    calibrate_multiplier,
)

CALIBRATION_VERSION = "q1-audit-calibration/1"
FAULT_CEILING = float(DEFAULT_MULTIPLIER * PRECISION_ONLY_FACTOR)
PRIMARY_POLICY = "tf32-admissible"


def required_multiplier(
    e_candidate: float | None, reference_errors: Sequence[float | None]
) -> float:
    """Smallest M with ``e_candidate <= max(M * max(reference_errors), T_FLOOR)`` (see above)."""
    if e_candidate is None or not math.isfinite(e_candidate):
        return math.inf
    if e_candidate <= T_FLOOR:
        return 0.0
    finite = [e for e in reference_errors if e is not None and math.isfinite(e)]
    if not finite:
        return 0.0
    worst = max(finite)
    if worst <= 0.0:
        return math.inf
    return e_candidate / worst


def draw_requirement(details: Mapping[str, Any], policy: str = PRIMARY_POLICY) -> float:
    """Required multiplier of one A1 per-draw row (its ``details``)."""
    judged = details.get(policy, {})
    references = [details.get("e_r32_device"), details.get("e_r32_cpu")]
    if judged.get("tf32_applied"):
        references.append(details.get("e_r32_tf32"))
    if judged.get("reason") not in (None, "", "exceeds-T"):
        return math.inf  # shape, dtype, non-finite mask or integer mismatch: no M passes
    return required_multiplier(judged.get("e"), references)


def calibration_members(
    table: Mapping[str, Mapping[str, Any]], calibration_problems: Iterable[str]
) -> list[str]:
    cal = set(calibration_problems)
    return sorted(
        k
        for k, v in table.items()
        if v["kind"] == "substrate" and v["source_kind"] == "inductor" and v["problem_id"] in cal
    )


def calibrate(
    rows: Iterable[Mapping[str, Any]],
    table: Mapping[str, Mapping[str, Any]],
    calibration_problems: Iterable[str],
    *,
    seed: int = 42,
    policy: str = PRIMARY_POLICY,
    base: int = DEFAULT_MULTIPLIER,
) -> dict[str, Any]:
    """Classify S1-cal substrates, compute M, and name the frozen audit version."""
    from harness.q1.audit.tiers import audit_version_hash

    candidates = calibration_members(table, calibration_problems)
    wanted = set(candidates)
    draws: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        if (
            row["gate"] == "A1"
            and row.get("seed", 42) == seed
            and row["kernel_id"] in wanted
            and row["config_id"].startswith("A1/native/")
        ):
            draws[row["kernel_id"]].append(row["details"])
    per_kernel: dict[str, dict[str, Any]] = {}
    for kernel in candidates:
        details = draws.get(kernel, [])
        if not details:
            status, need = "missing", None
        elif not all(d.get("admissible") for d in details):
            status, need = "excluded-unrefereeable", None
        elif any(d.get("candidate_raised") for d in details):
            status, need = "fault-candidate-raised", math.inf
        else:
            need = max(draw_requirement(d, policy) for d in details)
            status = "member" if need <= FAULT_CEILING else "fault-candidate-error"
        per_kernel[kernel] = {
            "status": status,
            "draws": len(details),
            "required_multiplier": None if need is None or math.isinf(need) else need,
            "infinite": need is not None and math.isinf(need),
        }
    member_needs = [
        v["required_multiplier"] for v in per_kernel.values() if v["status"] == "member"
    ]
    multiplier, raised = calibrate_multiplier(member_needs, base=base)
    by_status: dict[str, int] = defaultdict(int)
    for v in per_kernel.values():
        by_status[v["status"]] += 1
    return {
        "calibration_version": CALIBRATION_VERSION,
        "policy": policy,
        "seed": seed,
        "fault_ceiling": FAULT_CEILING,
        "multiplier": multiplier,
        "multiplier_raised": raised,
        "largest_member_requirement": max(member_needs) if member_needs else None,
        "counts": dict(sorted(by_status.items())),
        "fault_candidates": sorted(
            k for k, v in per_kernel.items() if v["status"].startswith("fault-candidate")
        ),
        "kernels": per_kernel,
        "audit_version": audit_version_hash(multiplier=multiplier, multiplier_raised=raised),
    }
