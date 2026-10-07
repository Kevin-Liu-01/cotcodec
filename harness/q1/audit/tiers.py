"""Contract tiers, precision-only class, audit-hole adjudication and audit versioning.

Contract tiers (decision D14; primary = G):

- **N** = A1 and A2 and A4 at native shapes;
- **G** = N and A3, where an A3 refusal-before-launch is "non-general", not a fault;
- **G-strict** = N and A3, where a refusal counts as a fault;
- **c-disjoint** = A1 and A4 (the audit channels gate (c) does not share).

A channel verdict ``error`` (no admissible draw, reference failure) makes the
tier ``error`` unless another channel already rejects. The exception is a
channel the caller declares *vacuous*: A2 or A3 with no admissible draw for
the problem, which the reference alone decides (validity is computed before
the candidate runs). A vacuous channel is dropped from every tier's
conjunction, so whether a kernel enters a denominator never depends on what
the other channels said about it. A1 and A4 are never vacuous.

Precision-only rejection: the kernel fails A1 but passes A1 at 64·T and
passes A2, A3 and A4; reported as its own class.

Audit hole: a gate rejected a kernel on a validity-gated input the audit
accepted. Replay the kernel on that input against the fp64 oracle: if it
deviates beyond T the audit has a hole (bump the audit version and rerun
everything); otherwise the gate falsely rejected it.

This module imports torch only inside the functions that need the oracle, so
tier composition runs in torch-free analyses.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Collection, Mapping
from pathlib import Path
from typing import Any

TIERS = ("N", "G", "G-strict", "c-disjoint")
AUDIT_FILES = (
    "audit/oracle.py",
    "audit/values.py",
    "audit/contracts.py",
    "audit/lethe_contracts.py",
    "audit/run.py",
    "audit/tiers.py",
    "audit/poison_alloc.c",
    "audit/gpu_probes.py",
    "audit/calibration.py",
    "audit/replay.py",
    # The audit's fp64 error metric and byte comparisons (shared numeric helpers).
    "gates/reductions.py",
)


def _conjoin(verdicts: list[str]) -> str:
    for verdict in ("reject", "timeout", "error"):
        if verdict in verdicts:
            return verdict
    return "accept"


VACUOUS_ALLOWED = ("A2", "A3")


def tier_verdicts(channels: Mapping[str, str], *, vacuous: Collection[str] = ()) -> dict[str, str]:
    """Tier verdicts from channel aggregate verdicts for one TF32 policy.

    ``channels`` maps ``A1``..``A4`` to ``accept``/``reject``/``refuse``/
    ``error``/``timeout``. Only A3 may legitimately ``refuse``. Channels in
    ``vacuous`` (only A2 and A3 are allowed) are left out of the conjunctions.
    """
    unknown = set(vacuous) - set(VACUOUS_ALLOWED)
    if unknown:
        raise ValueError(f"only {VACUOUS_ALLOWED} may be vacuous, not {sorted(unknown)}")
    channels = {**channels, **{name: "accept" for name in vacuous}}
    a1, a2, a3, a4 = (channels.get(name, "error") for name in ("A1", "A2", "A3", "A4"))

    def strict(verdict: str) -> str:
        return "reject" if verdict == "refuse" else verdict

    n = _conjoin([strict(a1), strict(a2), strict(a4)])
    a3_general = "accept" if a3 == "refuse" else a3
    return {
        "N": n,
        "G": _conjoin([n, a3_general]),
        "G-strict": _conjoin([n, strict(a3)]),
        "c-disjoint": _conjoin([strict(a1), strict(a4)]),
    }


def precision_only(a1_aggregate_details: Mapping[str, Any], channels: Mapping[str, str]) -> bool:
    """Fails A1 only by precision: every A1 failure within 64·T and A2-A4 pass."""
    counts = a1_aggregate_details.get("counts", {})
    return (
        channels.get("A1") == "reject"
        and counts.get("crash-after-launch", 0) == 0
        and bool(a1_aggregate_details.get("silent_wrong_all_within_64T"))
        and all(channels.get(name) == "accept" for name in ("A2", "A3", "A4"))
    )


def adjudicate_gate_rejection(
    candidate_output: Any,
    reference: Any,
    *,
    policy: str = "tf32-admissible",
    multiplier: float = 16,
    candidate_tl_dot: bool = False,
) -> dict[str, Any]:
    """Audit-hole replay on the gate's rejecting input (already validity-gated).

    ``reference`` is an ``oracle.OracleReference`` built on that input.
    """
    from harness.q1.audit import oracle

    result = oracle.a1_compare(
        candidate_output,
        reference,
        policy=policy,
        multiplier=multiplier,
        candidate_tl_dot=candidate_tl_dot,
    )
    return {
        "classification": "false-reject-by-gate" if result.passed else "audit-hole",
        **result.details(),
    }


def audit_version_hash(
    *, multiplier: int, multiplier_raised: bool, q1_root: Path | None = None
) -> dict[str, Any]:
    """Freeze record for audit v1: constants plus SHA-256 of every audit source file."""
    from harness.q1.audit import oracle

    root = q1_root or Path(__file__).resolve().parents[1]
    files = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in AUDIT_FILES}
    record = {
        "multiplier": multiplier,
        "multiplier_raised": multiplier_raised,
        "kappa": oracle.KAPPA,
        "t_floor": oracle.T_FLOOR,
        "precision_only_factor": oracle.PRECISION_ONLY_FACTOR,
        "policies": list(oracle.POLICIES),
        "primary_policy": "tf32-admissible",
        "primary_tier": "G",
        "files": files,
    }
    payload = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    record["audit_version_sha256"] = hashlib.sha256(payload).hexdigest()
    return record
