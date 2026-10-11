"""K2 classification rules (registration ``q2-evaluator-mutation-v1-k2`` sections 5 and 6).

Pure functions over run records and offline verdicts; no I/O. The executor uses the run-level
helpers to fill its record, and ``report.py`` uses the pair-level rules and the fitness gate.
Nothing here reads an audit decision, an adjudication answer or a rater output.

Run level (one in-VM run of one sampled job): ``scored`` (an in-VM verdict exists), or
``excluded`` under one of the parent registration's two exclusion causes, (3)
``injection_hash_mismatch`` or (4) ``vm_infrastructure_failure``. A run lost to
infrastructure on its first attempt is dispatched once more (the lane's re-queue); the run is
scored if either attempt scored.

Pair level (one sampled job, ``RUNS_PER_PAIR`` independent runs in fresh VMs): ``excluded``
when no run scored (cause (3) if any attempt of the pair ended in a hash mismatch, else (4));
``agree`` when every scored run's verdict equals the offline lock-exact verdict; otherwise
``differ``, with the first explanation that holds:

1. ``save_slower_than_0_5s`` (cause 1): every differing run read, at the checker, the
   pre-postconfig bytes of a target the postconfig saves, and that file changed on disk after
   the read (the save landed late);
2. ``nondeterministic`` (cause 2): the candidate's offline repeat scorings disagree, or the
   pair's scored in-VM runs disagree with each other;
3. ``unexplained``: anything else.

The fitness gate: the registered sample's 80 pairs may have at most ``MAX_EXCLUDED_PAIRS``
excluded pairs (10%); above that the executor is not fit, no K2 report is written for the
registered analysis, and its label stays "offline harness, VM fidelity unverified".
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

RUN_SCHEMA = "q2m-k2-run-v1"
EXPERIMENT_ID = "q2-evaluator-mutation-v1-k2"
PARENT_ID = "q2-evaluator-mutation-v1"
# The parent's four registered explanations (``harness.q2_mutation.analysis.K2_EXPLANATIONS``,
# frozen; a test checks the two tuples are equal).
SAVE_LATE = "save_slower_than_0_5s"
NONDETERMINISTIC = "nondeterministic"
HASH_MISMATCH = "injection_hash_mismatch"
VM_INFRA = "vm_infrastructure_failure"
K2_EXPLANATIONS = (SAVE_LATE, NONDETERMINISTIC, HASH_MISMATCH, VM_INFRA)
EXCLUSIONS = (HASH_MISMATCH, VM_INFRA)
UNEXPLAINED = "unexplained"
VERDICTS = ("pass", "fail", "error")
RUNS_PER_PAIR = 2
REGISTERED_PAIRS = 80
MAX_EXCLUDED_PAIRS = 8
OUTCOMES = ("VERIFIED", "FAMILIES_DROPPED", "INCOMPLETE")


class RuleError(ValueError):
    """A record does not have the shape the rules read."""


def run_state(record: Mapping[str, Any]) -> dict[str, Any]:
    """One attempt's reading: ``scored`` (with its verdict and save-timing evidence),
    ``excluded`` (with its cause) or ``missing`` (cut at a stop, never dispatched)."""
    status = record.get("status")
    if status == "scored":
        verdict = record.get("verdict")
        if verdict not in VERDICTS:
            raise RuleError(f"{record.get('slot')}: scored without a verdict ({verdict!r})")
        return {"state": "scored", "verdict": verdict, "save_late": save_late(record)}
    if status == "infrastructure":
        cause = record.get("exclusion") or VM_INFRA
        if cause not in EXCLUSIONS:
            raise RuleError(f"{record.get('slot')}: exclusion {cause!r} is not registered")
        return {"state": "excluded", "cause": cause}
    if status == "cap_truncated":
        return {"state": "missing", "cause": VM_INFRA}
    raise RuleError(f"{record.get('slot')}: unknown status {status!r}")


def save_late(record: Mapping[str, Any]) -> bool:
    """Cause (1)'s evidence on one scored run: some target the postconfig saves was read by
    the checker with its pre-postconfig bytes, and its bytes on disk changed after the read."""
    unsaved = list(record.get("unsaved_at_read") or [])
    late = record.get("late_write") or {}
    paths = record.get("save_paths") or {}
    return any(
        paths.get(path) == "postconfig_save" and (late.get(path) or {}).get("changed") is True
        for path in unsaved
    )


def unsaved_at_read(
    save_paths: Mapping[str, str],
    pre_postconfig: Mapping[str, str | None],
    checker_read: Mapping[str, str | None],
) -> list[str]:
    """Postconfig-saved targets whose bytes at the checker's read equal their pre-postconfig
    bytes (the plan's ``expect_changed`` check, recorded rather than failed; section 5.1)."""
    out = []
    for path, how in sorted(save_paths.items()):
        if how != "postconfig_save" or path not in checker_read:
            continue
        if checker_read[path] is not None and checker_read[path] == pre_postconfig.get(path):
            out.append(path)
    return out


def run_reading(attempts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """A run from its attempts (at most two): scored if an attempt scored, else excluded."""
    if not attempts:
        return {"state": "missing", "cause": VM_INFRA, "attempts": 0}
    states = [run_state(a) for a in attempts]
    scored = [s for s in states if s["state"] == "scored"]
    if len(scored) > 1:
        raise RuleError(f"{attempts[0].get('slot')}: more than one scored attempt")
    if scored:
        return {**scored[0], "attempts": len(states)}
    cause = HASH_MISMATCH if any(s.get("cause") == HASH_MISMATCH for s in states) else VM_INFRA
    state = "excluded" if any(s["state"] == "excluded" for s in states) else "missing"
    return {"state": state, "cause": cause, "attempts": len(states)}


def classify_pair(
    runs: Sequence[Mapping[str, Any]], offline_verdict: str, offline_nondeterministic: bool
) -> dict[str, Any]:
    """A pair's reading from its runs (``run_reading``) and the offline lock-exact verdict."""
    if offline_verdict not in VERDICTS:
        raise RuleError(f"offline verdict {offline_verdict!r}")
    scored = [r for r in runs if r["state"] == "scored"]
    out: dict[str, Any] = {
        "runs_scored": len(scored),
        "vm_verdicts": [r["verdict"] for r in scored],
        "offline_verdict": offline_verdict,
    }
    if not scored:
        cause = HASH_MISMATCH if any(r.get("cause") == HASH_MISMATCH for r in runs) else VM_INFRA
        return {**out, "state": "excluded", "explanation": cause}
    differing = [r for r in scored if r["verdict"] != offline_verdict]
    if not differing:
        return {**out, "state": "agree", "explanation": None}
    if all(r.get("save_late") for r in differing):
        explanation = SAVE_LATE
    elif offline_nondeterministic or len({r["verdict"] for r in scored}) > 1:
        explanation = NONDETERMINISTIC
    else:
        explanation = UNEXPLAINED
    return {**out, "state": "differ", "explanation": explanation}


def gate(pairs: Iterable[Mapping[str, Any]], n_registered: int = REGISTERED_PAIRS) -> dict:
    """The fitness gate over the registered sample's pair readings."""
    rows = list(pairs)
    if len(rows) != n_registered:
        raise RuleError(f"the gate reads {n_registered} pairs, got {len(rows)}")
    excluded = [r for r in rows if r["state"] == "excluded"]
    return {
        "pairs": len(rows),
        "excluded": len(excluded),
        "excluded_by_cause": dict(Counter(r["explanation"] for r in excluded)),
        "max_excluded": MAX_EXCLUDED_PAIRS,
        "passes": len(excluded) <= MAX_EXCLUDED_PAIRS,
    }


def outcome(gate_result: Mapping[str, Any], pairs: Iterable[Mapping[str, Any]]) -> dict:
    """The registered K2 outcome (section 6) and the families the parent's consequence drops."""
    rows = list(pairs)
    dropped = sorted(
        {str(r["checker_family"]) for r in rows if r.get("explanation") == UNEXPLAINED}
    )
    if not gate_result["passes"]:
        return {
            "outcome": "INCOMPLETE",
            "families_dropped": [],
            "write_analysis_report": False,
            "label": "offline harness, VM fidelity unverified",
        }
    return {
        "outcome": "FAMILIES_DROPPED" if dropped else "VERIFIED",
        "families_dropped": dropped,
        "write_analysis_report": True,
        "label": "VM fidelity checked (K2)",
    }
