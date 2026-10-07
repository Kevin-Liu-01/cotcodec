"""Audit-hole replay (preregistration section 6.7), one worker item per kernel and replicate.

For a kernel the primary audit accepts but a gate rejected, the gate's
rejecting input is rebuilt exactly as the gate built it and the kernel is
judged on it by the audit's own rule against the fp64 oracle, with the frozen
multiplier. ``analysis.audit_hole_candidates`` lists the requests;
``scripts/q1_audit_hole_replay.py`` runs them as ``audit_hole`` items.

Inputs:

- a gate (c) configuration (``c1``/``c2``/``c3``): the spec with that config
  id from ``gate_c.c_configs`` at the item's replicate, its override variant
  of the problem, ``set_seed(spec.seed)``, the draw transform, no dtype cast;
- a failing gate (a) trial (``a``, ``a_1e-3``): KernelBench's trial seed for
  that trial (``kernelbench_trial_seeds(replicate, 5)``), no dtype cast.

Weights come from ``audit.run.prepare`` (``set_seed(replicate)`` before each
construction, as gates (a) and (c) do), so the replay sees the same models.

Classification (row ``details.classification``; row verdict ``reject`` means
the oracle finds the kernel wrong on that input):

- the audit validity gate fails on the input (the reference raises, its
  error exceeds 1e-3, or its non-finite mask differs from fp64):
  ``not-adjudicable`` (verdict ``error``);
- the kernel raises: on a gate (a) input (native shapes) or after a Triton
  launch on a gate (c) input, ``audit-hole`` (the audit missed a fault its
  own rules count); before any launch on a gate (c) input,
  ``false-reject-by-gate`` (a refusal at a held-out shape is not a fault
  under contract tier G, decision D14);
- otherwise ``tiers.adjudicate_gate_rejection``: ``audit-hole`` if the output
  deviates beyond T, else ``false-reject-by-gate``.
"""

from __future__ import annotations

import json
import math
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import torch

from harness.q1 import problems as problem_lib
from harness.q1.audit import oracle, run, tiers
from harness.q1.gates.common import (
    GateOutcome,
    exception_details,
    kernelbench_trial_seeds,
    load_reference,
    process_inputs,
    set_seed,
    synchronize,
)

GATE = "audit_hole"
C_FAMILIES = ("c1", "c2", "c3")
A_GATES = ("a", "a_1e-3")
GATE_A_TRIALS = 5


def _finite(value: Any) -> float | None:
    return float(value) if isinstance(value, int | float) and math.isfinite(value) else None


def _c_inputs(
    subject: run.AuditSubject, request: Mapping[str, Any], manifest: Mapping[str, Any] | None
) -> list[Any]:
    from harness.q1.gates import gate_c

    specs = gate_c.c_configs(
        subject.problem_id,
        families=(request["gate"],),
        replicate_seed=subject.replicate_seed,
        manifest=manifest,
    )
    matching = [spec for spec in specs if spec.config_id == request["config_id"]]
    if len(matching) != 1:
        raise LookupError(f"no unique gate (c) spec {request['config_id']}")
    spec = matching[0]
    get_inputs = subject.get_inputs
    if spec.overrides:
        analysis = problem_lib.analyze_problem(subject.problem_id, subject.problem_source)
        variant = problem_lib.override_constants(subject.problem_source, analysis, spec.overrides)
        get_inputs = load_reference(variant)[2]
    set_seed(spec.seed)
    raw = gate_c.transform_inputs(list(get_inputs()), spec.draw)
    return process_inputs(raw, subject.device, "preserve")


def _a_inputs(subject: run.AuditSubject, trial: int) -> list[Any]:
    trial_seed = kernelbench_trial_seeds(subject.replicate_seed, GATE_A_TRIALS)[trial]
    set_seed(trial_seed)
    return process_inputs(subject.get_inputs(), subject.device, "preserve")


def _judge(
    subject: run.AuditSubject,
    inputs: Sequence[Any],
    *,
    rejecting_gate: str,
    policy: str,
    multiplier: float,
) -> tuple[str, dict[str, Any]]:
    try:
        ref = oracle.build_reference(subject.reference, inputs, device=subject.device)
    except Exception as exc:
        return "not-adjudicable", {"reason": "reference-raised", **exception_details(exc)}
    worst_ref = max(e for e in (ref.e_device, ref.e_cpu) if e is not None)
    reasons = []
    if worst_ref > run.VALIDITY_CEILING:
        reasons.append("reference-error-above-ceiling")
    if not all(
        oracle.masks_equal(r32, r64)
        for r32, r64 in zip(ref.r32_device, ref.r64, strict=True)
        if r64.is_floating_point()
    ):
        reasons.append("reference-nonfinite-mask-differs-from-fp64")
    if reasons:
        return "not-adjudicable", {"reason": ",".join(reasons), "e_r32": worst_ref}
    counter = run.LaunchCounter()
    try:
        with torch.no_grad(), counter:
            out = subject.candidate(*inputs)
            synchronize(subject.device)
    except Exception as exc:
        launched = bool(counter.launches)
        fault = rejecting_gate in A_GATES or launched
        return (
            "audit-hole" if fault else "false-reject-by-gate",
            {
                "reason": "crash-after-launch" if launched else "refusal-before-launch",
                "launches_before_exception": counter.launches,
                **exception_details(exc),
            },
        )
    adjudication = tiers.adjudicate_gate_rejection(
        out, ref, policy=policy, multiplier=multiplier, candidate_tl_dot=subject.tl_dot
    )
    classification = adjudication.pop("classification")
    return classification, {"reason": "oracle-compare", **adjudication}


def run_replays(
    problem_id: str,
    problem_source: str,
    kernel_source: str,
    *,
    replicate_seed: int,
    device: torch.device,
    rejections: Sequence[Mapping[str, Any]],
    multiplier: float = oracle.DEFAULT_MULTIPLIER,
    manifest_path: str | None = None,
    policy: str = run.PRIMARY_POLICY,
) -> list[GateOutcome]:
    """One ``audit_hole`` outcome per replayed input (see the module docstring)."""
    manifest = (
        json.loads(Path(manifest_path).read_text(encoding="utf-8")) if manifest_path else None
    )
    subject = run.prepare(
        problem_id, problem_source, kernel_source, replicate_seed=replicate_seed, device=device
    )
    outcomes: list[GateOutcome] = []
    try:
        for request in rejections:
            gate = request["gate"]
            if gate in C_FAMILIES:
                cases = [(request["config_id"], lambda r=request: _c_inputs(subject, r, manifest))]
            elif gate in A_GATES:
                cases = [
                    (
                        f"{request['config_id']}/trial-{trial}",
                        lambda t=int(trial): _a_inputs(subject, t),
                    )
                    for trial in request.get("trials", [])
                ]
            else:
                raise ValueError(f"gate {gate} rejections are not replayable")
            for label, build in cases:
                start = time.perf_counter()
                try:
                    inputs = build()
                except Exception as exc:
                    classification = "not-adjudicable"
                    facts = {"reason": "input-rebuild-failed", **exception_details(exc)}
                else:
                    classification, facts = _judge(
                        subject, inputs, rejecting_gate=gate, policy=policy, multiplier=multiplier
                    )
                verdict = {"audit-hole": "reject", "false-reject-by-gate": "accept"}.get(
                    classification, "error"
                )
                outcomes.append(
                    GateOutcome(
                        GATE,
                        f"{gate}:{label}",
                        verdict,
                        max_rel_err=_finite(facts.get("e")),
                        tolerance=_finite(facts.get("T")),
                        details={
                            "classification": classification,
                            "rejecting_gate": gate,
                            "rejecting_config": request["config_id"],
                            "policy": policy,
                            "multiplier": multiplier,
                            **facts,
                        },
                        wall_seconds=time.perf_counter() - start,
                    )
                )
    finally:
        subject.cleanup()
    return outcomes
