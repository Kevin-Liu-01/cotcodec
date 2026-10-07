"""Independent audit channels A1-A5 for one candidate.

The audit never reads a gate's inputs or verdicts. Each channel is meant to
run in its own process (the runner spawns one per channel), builds the
reference ``Model`` and the candidate ``ModelNew`` with the same weights
(``set_seed(replicate)`` before each construction, as KernelBench does),
keeps both in training mode, and draws its own inputs from its own seeds:

| channel | inputs | seeds |
|---|---|---|
| A1 | five native ``get_inputs()`` draws | ``channel_seed(6042, r, t)`` |
| A2 | seven held-out value distributions at native shapes | ``channel_seed(4042, r, j)`` |
| A3 | the manifest's prime shapes, ``get_inputs()`` values | ``channel_seed(5042, r, k)`` |
| A4 | the first A1 draw | |
| A5 | lethe-style perturbations of a native draw | ``channel_seed(7042, r, 0)`` |

A1, A2 and A3 judge every output with the A1 rule (``oracle.py``) under both
TF32 policies; rows carry the primary policy in ``tf32_policy`` and the
strict result in ``details.strict``; aggregates are written for both
policies. A2 and A3 draws pass an audit validity gate first: the reference
runs, its fp32 non-finite masks equal the oracle's, and
``max(e(r32_device), e(r32_cpu)) <= 1e-3``.
"""

from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import torch

from harness.q1 import problems as problem_lib
from harness.q1.audit import contracts, lethe_contracts, oracle
from harness.q1.audit.values import A2_BASE, DISTRIBUTIONS, apply_distribution
from harness.q1.gates.common import (
    GateOutcome,
    channel_seed,
    exception_details,
    first_tensor_outputs,
    load_candidate,
    load_reference,
    process_inputs,
    resolve_device,
    set_seed,
    synchronize,
)

A1_BASE, A3_BASE = 6042, 5042
A1_DRAWS = 5
VALIDITY_CEILING = 1e-3
PRIMARY_POLICY = "tf32-admissible"
SECONDARY_POLICY = "strict-fp32"

#: aten ops that allocate or reshape without computing; they do not count as a launch.
_NONCOMPUTE_OPS = frozenset(
    {
        "empty",
        "empty_like",
        "empty_strided",
        "new_empty",
        "new_empty_strided",
        "view",
        "_unsafe_view",
        "reshape",
        "as_strided",
        "alias",
        "detach",
        "t",
        "transpose",
        "permute",
        "expand",
        "select",
        "slice",
        "unsqueeze",
        "squeeze",
        "size",
        "stride",
        "sym_size",
        "sym_stride",
        "numel",
        "dim",
        "is_contiguous",
        "lift_fresh",
        "_to_copy_meta",
        "split",
        "unbind",
        "chunk",
        "narrow",
        "unfold",
        "view_as",
        "expand_as",
    }
)


class LaunchCounter(torch.utils._python_dispatch.TorchDispatchMode):
    """Counts compute work: aten compute ops plus Triton launches (via the b1 hook)."""

    def __init__(self) -> None:
        super().__init__()
        self.aten_compute = 0
        self._hook = None

    def __enter__(self):  # noqa: ANN204
        from harness.q1.gates.gate_b import LaunchHook

        self._hook = LaunchHook().__enter__()
        return super().__enter__()

    def __exit__(self, *exc: object) -> None:
        super().__exit__(*exc)
        if self._hook is not None:
            self._hook.__exit__(*exc)

    @property
    def launches(self) -> int:
        triton = len(self._hook.captured) if self._hook is not None else 0
        return triton + self.aten_compute

    def __torch_dispatch__(self, func, types, args=(), kwargs=None):  # noqa: ANN001
        name = getattr(getattr(func, "_schema", None), "name", str(func))
        if name.split("::")[-1].split(".")[0] not in _NONCOMPUTE_OPS:
            self.aten_compute += 1
        return func(*args, **(kwargs or {}))


@dataclass
class AuditSubject:
    problem_id: str
    problem_source: str
    reference: torch.nn.Module
    candidate: torch.nn.Module
    get_inputs: Any
    device: torch.device
    replicate_seed: int
    tl_dot: bool
    cleanup: Any


def prepare(
    problem_id: str,
    problem_source: str,
    kernel_source: str,
    *,
    replicate_seed: int = 42,
    device: str | torch.device | None = None,
) -> AuditSubject:
    dev = resolve_device(device)
    Model, get_init_inputs, get_inputs = load_reference(problem_source)
    set_seed(replicate_seed)
    init_inputs = process_inputs(get_init_inputs(), dev, "preserve")
    with torch.no_grad():
        set_seed(replicate_seed)
        reference = Model(*init_inputs)
    loaded = load_candidate(kernel_source)
    with torch.no_grad():
        set_seed(replicate_seed)
        candidate = loaded.model_class(*init_inputs)
    return AuditSubject(
        problem_id=problem_id,
        problem_source=problem_source,
        reference=reference.to(dev),
        candidate=candidate.to(dev),
        get_inputs=get_inputs,
        device=dev,
        replicate_seed=replicate_seed,
        tl_dot=oracle.candidate_uses_tl_dot(kernel_source),
        cleanup=loaded.cleanup,
    )


def draw_inputs(get_inputs: Any, seed: int, device: torch.device) -> list[Any]:
    set_seed(seed)
    return process_inputs(get_inputs(), device, "preserve")


def _judge(
    subject: AuditSubject, inputs: Sequence[Any], *, validity: bool, multiplier: float
) -> dict[str, Any]:
    """Run reference(s) and candidate on ``inputs`` and apply the A1 rule (both policies)."""
    try:
        ref = oracle.build_reference(subject.reference, inputs, device=subject.device)
    except Exception as exc:
        return {
            "admissible": False,
            "validity_reasons": ["reference-raised"],
            **exception_details(exc),
        }
    result: dict[str, Any] = {
        "e_r32_device": ref.e_device,
        "e_r32_cpu": ref.e_cpu,
        "e_r32_tf32": ref.e_tf32,
        "matmul_or_conv": ref.matmul_or_conv,
        "admissible": True,
        "validity_reasons": [],
    }
    if validity:
        reasons = []
        worst_ref = max(e for e in (ref.e_device, ref.e_cpu) if e is not None)
        if worst_ref > VALIDITY_CEILING:
            reasons.append("reference-error-above-ceiling")
        if not all(
            oracle.masks_equal(r32, r64)
            for r32, r64 in zip(ref.r32_device, ref.r64, strict=True)
            if r64.is_floating_point()
        ):
            reasons.append("reference-nonfinite-mask-differs-from-fp64")
        result["admissible"] = not reasons
        result["validity_reasons"] = reasons
    counter = LaunchCounter()
    try:
        with torch.no_grad(), counter:
            out = subject.candidate(*inputs)
            synchronize(subject.device)
    except Exception as exc:
        result["candidate_raised"] = True
        result["launches_before_exception"] = counter.launches
        result["outcome"] = "crash-after-launch" if counter.launches else "refusal-before-launch"
        result.update(exception_details(exc))
        return result
    result["candidate_raised"] = False
    for policy in oracle.POLICIES:
        verdict = oracle.a1_compare(
            out, ref, policy=policy, multiplier=multiplier, candidate_tl_dot=subject.tl_dot
        )
        result[policy] = verdict.details() | {"passed": verdict.passed}
    result["outcome"] = "pass" if result[PRIMARY_POLICY]["passed"] else "silent-wrong"
    return result


def _row(
    gate: str, config_id: str, judged: Mapping[str, Any], start: float, policy: str
) -> GateOutcome:
    if not judged.get("admissible", False):
        verdict = "error"
    elif judged.get("candidate_raised"):
        verdict = "refuse" if judged["outcome"] == "refusal-before-launch" else "reject"
    else:
        verdict = "accept" if judged[policy]["passed"] else "reject"
    primary = judged.get(policy, {})
    return GateOutcome(
        gate,
        config_id,
        verdict,
        max_abs_err=None,
        max_rel_err=primary.get("e"),
        tolerance=primary.get("T"),
        details=dict(judged),
        wall_seconds=time.perf_counter() - start,
    )


def _aggregate(gate: str, rows: Sequence[GateOutcome], policy: str) -> GateOutcome:
    """Channel verdict for one TF32 policy, ignoring inadmissible draws."""
    counts = {
        "pass": 0,
        "silent-wrong": 0,
        "crash-after-launch": 0,
        "refusal-before-launch": 0,
        "inadmissible": 0,
    }
    precision_only = True
    for row in rows:
        d = row.details
        if not d.get("admissible", False):
            counts["inadmissible"] += 1
        elif d.get("candidate_raised"):
            counts[d["outcome"]] += 1
            precision_only = False
        elif d[policy]["passed"]:
            counts["pass"] += 1
        else:
            counts["silent-wrong"] += 1
            precision_only = precision_only and bool(d[policy]["passes_at_64T"])
    if counts["silent-wrong"] or counts["crash-after-launch"]:
        verdict = "reject"
    elif counts["refusal-before-launch"]:
        verdict = "refuse"
    elif counts["pass"]:
        verdict = "accept"
    else:
        verdict = "error"
    worst = [r.details.get(policy, {}).get("e") for r in rows]
    worst = [w for w in worst if w is not None]
    return GateOutcome(
        gate,
        "aggregate",
        verdict,
        max_rel_err=max(worst) if worst else None,
        details={
            "policy": policy,
            "counts": counts,
            "silent_wrong_all_within_64T": bool(counts["silent-wrong"]) and precision_only,
        },
        wall_seconds=sum(r.wall_seconds for r in rows),
    )


def run_a1(subject: AuditSubject, *, multiplier: float = oracle.DEFAULT_MULTIPLIER) -> list:
    rows = []
    for t in range(A1_DRAWS):
        seed = channel_seed(A1_BASE, subject.replicate_seed, t)
        start = time.perf_counter()
        judged = _judge(
            subject,
            draw_inputs(subject.get_inputs, seed, subject.device),
            validity=False,
            multiplier=multiplier,
        )
        judged["seed"] = seed
        rows.append(_row("A1", f"A1/native/seed-{seed}", judged, start, PRIMARY_POLICY))
    return rows + [_aggregate("A1", rows, p) for p in oracle.POLICIES]


def run_a2(subject: AuditSubject, *, multiplier: float = oracle.DEFAULT_MULTIPLIER) -> list:
    rows = []
    for j, name in enumerate(DISTRIBUTIONS):
        seed = channel_seed(A2_BASE, subject.replicate_seed, j)
        start = time.perf_counter()
        set_seed(seed)
        raw = apply_distribution(subject.get_inputs(), name)
        inputs = process_inputs(raw, subject.device, "preserve")
        judged = _judge(subject, inputs, validity=True, multiplier=multiplier)
        judged.update({"seed": seed, "distribution": name})
        rows.append(_row("A2", f"A2/{name}/seed-{seed}", judged, start, PRIMARY_POLICY))
    return rows + [_aggregate("A2", rows, p) for p in oracle.POLICIES]


def run_a3(
    subject: AuditSubject,
    *,
    manifest_entry: Mapping[str, Any],
    multiplier: float = oracle.DEFAULT_MULTIPLIER,
) -> list:
    rows = []
    analysis = problem_lib.analyze_problem(subject.problem_id, subject.problem_source)
    for k, config in enumerate(manifest_entry.get("A3", [])):
        seed = channel_seed(A3_BASE, subject.replicate_seed, k)
        start = time.perf_counter()
        source = problem_lib.override_constants(
            subject.problem_source, analysis, config["overrides"]
        )
        get_inputs = load_reference(source)[2]
        judged = _judge(
            subject,
            draw_inputs(get_inputs, seed, subject.device),
            validity=True,
            multiplier=multiplier,
        )
        judged.update({"seed": seed, "overrides": dict(config["overrides"])})
        rows.append(_row("A3", f"{config['config_id']}/seed-{seed}", judged, start, PRIMARY_POLICY))
    return rows + [_aggregate("A3", rows, p) for p in oracle.POLICIES]


def run_a4(subject: AuditSubject) -> list:
    start = time.perf_counter()
    seed = channel_seed(A1_BASE, subject.replicate_seed, 0)
    inputs = draw_inputs(subject.get_inputs, seed, subject.device)
    try:
        results = contracts.check_determinism_and_aliasing(
            subject.candidate, inputs, device=subject.device
        )
        results.append(
            contracts.check_factory_poison(subject.candidate, inputs, device=subject.device)
        )
    except Exception as exc:
        return [
            GateOutcome(
                "A4",
                "aggregate",
                "reject",
                details={"reason": "candidate-raised", **exception_details(exc)},
                wall_seconds=time.perf_counter() - start,
            )
        ]
    sub = {r.name: {"passed": r.passed, **r.details} for r in results}
    failed = [r.name for r in results if r.passed is False]
    verdict = "reject" if failed else "accept"
    return [
        GateOutcome(
            "A4",
            "in-process",
            verdict,
            details={"subchecks": sub, "failed": failed, "seed": seed},
            wall_seconds=time.perf_counter() - start,
        )
    ]


def run_a5(subject: AuditSubject) -> list:
    start = time.perf_counter()
    seed = channel_seed(lethe_contracts.A5_BASE, subject.replicate_seed, 0)
    inputs = draw_inputs(subject.get_inputs, seed, subject.device)
    results = lethe_contracts.run_a5(
        subject.reference, subject.candidate, inputs, device=subject.device
    )
    statuses = [r["status"] for r in results]
    if "fail" in statuses:
        verdict = "reject"
    elif "error" in statuses or all(s == "na" for s in statuses):
        verdict = "error"
    else:
        verdict = "accept"
    return [
        GateOutcome(
            "A5",
            "aggregate",
            verdict,
            details={"checks": results, "seed": seed},
            wall_seconds=time.perf_counter() - start,
        )
    ]


CHANNELS = {"A1": run_a1, "A2": run_a2, "A3": run_a3, "A4": run_a4, "A5": run_a5}


def first_outputs(module: torch.nn.Module, inputs: Sequence[Any]) -> list[torch.Tensor]:
    with torch.no_grad():
        return first_tensor_outputs(module(*inputs))
