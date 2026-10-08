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
| A4 | the first A1 draw and one signed (randn) draw | ``6042``, ``4042`` |
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


def validity_reasons(ref: oracle.OracleReference) -> list[str]:
    """The audit validity gate (A2, A3) on one draw's references."""
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
    return reasons


def _judge(
    subject: AuditSubject,
    inputs: Sequence[Any],
    *,
    validity: bool,
    multiplier: float,
    stored: Any = None,
) -> dict[str, Any]:
    """Run reference(s) and candidate on ``inputs`` and apply the A1 rule (both policies).

    ``stored`` (a ``refstore.Taken``) replaces the reference side with what a
    reference item computed for this draw (:func:`reference_draws`)."""
    if stored is None:
        try:
            ref = oracle.build_reference(subject.reference, inputs, device=subject.device)
        except Exception as exc:
            return {
                "admissible": False,
                "validity_reasons": ["reference-raised"],
                **exception_details(exc),
            }
    else:
        ref = _stored_reference(stored)
    result: dict[str, Any] = {
        "e_r32_device": ref.e_device,
        "e_r32_cpu": ref.e_cpu,
        "e_r32_tf32": ref.e_tf32,
        "matmul_or_conv": ref.matmul_or_conv,
        "admissible": True,
        "validity_reasons": [],
    }
    if validity:
        reasons = (
            list(stored.meta["validity_reasons"]) if stored is not None else validity_reasons(ref)
        )
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


def _draw_plan(
    channel: str,
    problem_id: str,
    problem_source: str,
    replicate_seed: int,
    get_inputs: Any,
    manifest_entry: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    """The draws of A1, A2 or A3 in order: config id, seed, row facts and a
    function that draws the raw inputs (before ``process_inputs``) as the
    channel always has."""
    plan: list[dict[str, Any]] = []
    if channel == "A1":
        for t in range(A1_DRAWS):
            seed = channel_seed(A1_BASE, replicate_seed, t)

            def raw(seed: int = seed) -> list[Any]:
                set_seed(seed)
                return get_inputs()

            plan.append(
                {"config_id": f"A1/native/seed-{seed}", "facts": {"seed": seed}, "raw": raw}
            )
    elif channel == "A2":
        for j, name in enumerate(DISTRIBUTIONS):
            seed = channel_seed(A2_BASE, replicate_seed, j)

            def raw(seed: int = seed, name: str = name) -> list[Any]:
                set_seed(seed)
                return apply_distribution(get_inputs(), name)

            plan.append(
                {
                    "config_id": f"A2/{name}/seed-{seed}",
                    "facts": {"seed": seed, "distribution": name},
                    "raw": raw,
                }
            )
    elif channel == "A3":
        analysis = problem_lib.analyze_problem(problem_id, problem_source)
        for k, config in enumerate((manifest_entry or {}).get("A3", [])):
            seed = channel_seed(A3_BASE, replicate_seed, k)

            def raw(seed: int = seed, config: Mapping[str, Any] = config) -> list[Any]:
                source = problem_lib.override_constants(
                    problem_source, analysis, config["overrides"]
                )
                variant_inputs = load_reference(source)[2]
                set_seed(seed)
                return variant_inputs()

            plan.append(
                {
                    "config_id": f"{config['config_id']}/seed-{seed}",
                    "facts": {"seed": seed, "overrides": dict(config["overrides"])},
                    "raw": raw,
                }
            )
    else:
        raise ValueError(f"no draw plan for {channel}")
    return plan


def _run_channel(
    channel: str,
    subject: AuditSubject,
    *,
    multiplier: float,
    manifest_entry: Mapping[str, Any] | None = None,
    reference_store: str | None = None,
) -> list:
    plan = _draw_plan(
        channel,
        subject.problem_id,
        subject.problem_source,
        subject.replicate_seed,
        subject.get_inputs,
        manifest_entry,
    )
    stored = None
    if reference_store:
        from harness.q1 import refstore

        stored = refstore.lookup(
            reference_store,
            reference_payload(
                channel,
                subject.problem_id,
                subject.problem_source,
                replicate_seed=subject.replicate_seed,
                device=subject.device,
                manifest_entry=manifest_entry,
            ),
            draws=len(plan),
        )
    rows = []
    for index, draw in enumerate(plan):
        start = time.perf_counter()
        inputs = process_inputs(draw["raw"](), subject.device, "preserve")
        # The original reference module never runs here (``oracle.build_reference``
        # works on copies), so computing a draw inline after a fallback needs no replay.
        taken = stored.take(index, subject.device, inputs) if stored is not None else None
        if taken is None:
            stored = None
        judged = _judge(
            subject,
            inputs,
            validity=channel != "A1",
            multiplier=multiplier,
            stored=taken,
        )
        judged.update(draw["facts"])
        rows.append(_row(channel, draw["config_id"], judged, start, PRIMARY_POLICY))
    return rows + [_aggregate(channel, rows, p) for p in oracle.POLICIES]


def run_a1(
    subject: AuditSubject,
    *,
    multiplier: float = oracle.DEFAULT_MULTIPLIER,
    reference_store: str | None = None,
) -> list:
    return _run_channel("A1", subject, multiplier=multiplier, reference_store=reference_store)


def run_a2(
    subject: AuditSubject,
    *,
    multiplier: float = oracle.DEFAULT_MULTIPLIER,
    reference_store: str | None = None,
) -> list:
    return _run_channel("A2", subject, multiplier=multiplier, reference_store=reference_store)


def run_a3(
    subject: AuditSubject,
    *,
    manifest_entry: Mapping[str, Any],
    multiplier: float = oracle.DEFAULT_MULTIPLIER,
    reference_store: str | None = None,
) -> list:
    return _run_channel(
        "A3",
        subject,
        multiplier=multiplier,
        manifest_entry=manifest_entry,
        reference_store=reference_store,
    )


def run_a4(subject: AuditSubject) -> list:
    """Contracts on two draws: the first native draw and a signed (randn) draw.

    The signed draw exposes value-dependent in-place writes and aliasing that a
    non-negative ``torch.rand`` input hides (for example an in-place ReLU).
    """
    start = time.perf_counter()
    native_seed = channel_seed(A1_BASE, subject.replicate_seed, 0)
    signed_seed = channel_seed(A2_BASE, subject.replicate_seed, 0)
    draws = {"native": draw_inputs(subject.get_inputs, native_seed, subject.device)}
    set_seed(signed_seed)
    draws["signed"] = process_inputs(
        apply_distribution(subject.get_inputs(), "randn"), subject.device, "preserve"
    )
    sub: dict[str, Any] = {}
    failed: set[str] = set()
    for label, inputs in draws.items():
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
                    details={"reason": "candidate-raised", "draw": label, **exception_details(exc)},
                    wall_seconds=time.perf_counter() - start,
                )
            ]
        sub[label] = {r.name: {"passed": r.passed, **r.details} for r in results}
        failed |= {r.name for r in results if r.passed is False}
    verdict = "reject" if failed else "accept"
    return [
        GateOutcome(
            "A4",
            "in-process",
            verdict,
            details={
                "subchecks": sub,
                "failed": sorted(failed),
                "seeds": {"native": native_seed, "signed": signed_seed},
            },
            wall_seconds=time.perf_counter() - start,
        )
    ]


def run_a5(subject: AuditSubject, *, reference_store: str | None = None) -> list:
    start = time.perf_counter()
    seed = channel_seed(lethe_contracts.A5_BASE, subject.replicate_seed, 0)
    stored = None
    if reference_store:
        from harness.q1 import refstore

        stored = refstore.lookup(
            reference_store,
            reference_payload(
                "A5",
                subject.problem_id,
                subject.problem_source,
                replicate_seed=subject.replicate_seed,
                device=subject.device,
            ),
            draws=1,
        )
    inputs = draw_inputs(subject.get_inputs, seed, subject.device)
    taken = stored.take(0, subject.device, inputs) if stored is not None else None
    refs = None
    if taken is not None:
        refs = _checked_refs(taken, inputs)
    results = lethe_contracts.run_a5(
        subject.reference, subject.candidate, inputs, device=subject.device, refs=refs
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


def _checked_refs(taken: Any, inputs: Sequence[Any]) -> Any:
    """A5's stored reference calls, each released only while the draw's inputs still
    match the entry's fingerprint. A5 passes integer inputs to the candidate by
    identity, so a candidate can write them in place between checks; inline, the
    later reference calls would see the written values, so from the first mismatch
    every remaining reference call is computed inline (``None``)."""
    from harness.q1 import refstore

    table = {tag: ("ok", taken.value[tag]) for tag in taken.meta["tags"]}
    expected = taken.meta.get("inputs_fp")
    state = {"inline": False}

    def refs(tag: str) -> tuple[str, Any] | None:
        if state["inline"]:
            return None
        if expected is not None and refstore.safe_fingerprint(list(inputs)) != expected:
            state["inline"] = True
            refstore.note(inline_from_tag=tag, inline_reason="inputs-differ")
            return None
        return table[tag]

    return refs


CHANNELS = {"A1": run_a1, "A2": run_a2, "A3": run_a3, "A4": run_a4, "A5": run_a5}


# --- reference store (decision D31) ---------------------------------------------------


def reference_payload(
    channel: str,
    problem_id: str,
    problem_source: str,
    *,
    replicate_seed: int,
    device: torch.device,
    manifest_entry: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    from harness.q1 import refstore

    params: dict[str, Any] = {"cast_mode": "preserve"}
    if channel == "A1":
        params.update({"draws": A1_DRAWS, "base": A1_BASE, "validity": False})
    elif channel == "A2":
        params.update({"distributions": list(DISTRIBUTIONS), "base": A2_BASE, "validity": True})
    elif channel == "A3":
        params.update(
            {"a3": list((manifest_entry or {}).get("A3", [])), "base": A3_BASE, "validity": True}
        )
    elif channel == "A5":
        params.update(
            {"base": lethe_contracts.A5_BASE, "tags": list(lethe_contracts.REFERENCE_TAGS)}
        )
    else:
        raise ValueError(f"no reference channel {channel}")
    return refstore.key_payload(
        channel,
        problem_id=problem_id,
        problem_source=problem_source,
        seed=replicate_seed,
        device_type=device.type,
        params=params,
    )


def _reference_module(
    problem_source: str, replicate_seed: int, device: torch.device
) -> tuple[torch.nn.Module, Any]:
    """The audit's reference exactly as :func:`prepare` builds it (no candidate)."""
    Model, get_init_inputs, get_inputs = load_reference(problem_source)
    set_seed(replicate_seed)
    init_inputs = process_inputs(get_init_inputs(), device, "preserve")
    with torch.no_grad():
        set_seed(replicate_seed)
        reference = Model(*init_inputs)
    return reference.to(device), get_inputs


def _stored_reference(taken: Any) -> oracle.OracleReference:
    """The ``OracleReference`` a reference item stored for one draw. fp32 reference
    tensors are kept only at integer outputs (the near-tie rule reads them)."""
    meta, value = taken.meta, taken.value
    return oracle.OracleReference(
        r64=list(value["r64"]),
        r32_device=list(value["r32_device"]),
        r32_cpu=list(value["r32_cpu"]) if meta["has_cpu"] else None,
        r32_tf32=list(value["r32_tf32"]) if meta["has_tf32"] else None,
        e_device=meta["e_device"],
        e_cpu=meta["e_cpu"],
        e_tf32=meta["e_tf32"],
        ops=list(meta["ops"]),
    )


def _integer_only(tensors: Sequence[torch.Tensor] | None, r64: Sequence[torch.Tensor]) -> Any:
    if tensors is None:
        return None
    return [t if not r.is_floating_point() else None for t, r in zip(tensors, r64, strict=True)]


def reference_draws(
    channel: str,
    problem_id: str,
    problem_source: str,
    *,
    replicate_seed: int,
    device: torch.device,
    manifest_entry: Mapping[str, Any] | None = None,
) -> Any:
    """The reference side of A1, A2, A3 or A5 without a candidate, draw by draw in
    the channel's order, on the reference :func:`prepare` would build, with each
    draw's input fingerprint. A reference that raises makes the entry unusable
    (consumers compute inline) and ends the work; a resource failure raises
    ``refstore.ResourceFailure`` (no entry)."""
    from harness.q1 import refstore

    reference, get_inputs = _reference_module(problem_source, replicate_seed, device)
    built = refstore.Built(draws=[])
    if channel == "A5":
        seed = channel_seed(lethe_contracts.A5_BASE, replicate_seed, 0)
        inputs = draw_inputs(get_inputs, seed, device)
        fp = refstore.safe_fingerprint(inputs)
        results, problems = lethe_contracts.reference_results(reference, inputs, device=device)
        built.problems.extend(problems)
        if fp is None:
            built.problems.append("inputs-fingerprint-failed")
        tags = {tag: {"status": status} for tag, (status, _value) in results.items()}
        outputs = {tag: value for tag, (status, value) in results.items() if status == "ok"}
        built.draws.append(
            refstore.Draw(
                {"kind": "ok", "seed": seed, "tags": tags, "inputs_fp": fp},
                refstore.to_cpu(outputs),
            )
        )
        return built
    plan = _draw_plan(
        channel, problem_id, problem_source, replicate_seed, get_inputs, manifest_entry
    )
    for draw in plan:
        inputs = process_inputs(draw["raw"](), device, "preserve")
        meta: dict[str, Any] = {
            "config_id": draw["config_id"],
            "inputs_fp": refstore.safe_fingerprint(inputs),
        }
        probe = refstore.Probe(inputs, device)
        try:
            ref = oracle.build_reference(reference, inputs, device=device)
        except Exception as exc:
            refstore.reraise_resource(draw["config_id"], exc)
            built.problems.append(f"{draw['config_id']}: reference-raised {type(exc).__name__}")
            break
        try:
            reasons = validity_reasons(ref) if channel != "A1" else []
        except Exception as exc:
            refstore.reraise_resource(f"{draw['config_id']} validity", exc)
            built.problems.append(f"validity-raised: {type(exc).__name__}")
            break
        built.problems.extend(probe.changes())
        if meta["inputs_fp"] is None:
            built.problems.append(f"{draw['config_id']}: inputs-fingerprint-failed")
        held = [*ref.r64, *ref.r32_device, *(ref.r32_cpu or []), *(ref.r32_tf32 or [])]
        if refstore.aliases(held, inputs):
            built.problems.append(f"{draw['config_id']}: reference-output-aliases-input")
        if built.problems:
            break
        payload = {
            "r64": ref.r64,
            "r32_device": _integer_only(ref.r32_device, ref.r64),
            "r32_cpu": _integer_only(ref.r32_cpu, ref.r64),
            "r32_tf32": _integer_only(ref.r32_tf32, ref.r64),
        }
        built.draws.append(
            refstore.Draw(
                {
                    **meta,
                    "kind": "ok",
                    "e_device": ref.e_device,
                    "e_cpu": ref.e_cpu,
                    "e_tf32": ref.e_tf32,
                    "ops": list(ref.ops),
                    "has_cpu": ref.r32_cpu is not None,
                    "has_tf32": ref.r32_tf32 is not None,
                    "validity_reasons": reasons,
                },
                refstore.to_cpu(payload),
            )
        )
    return built


def first_outputs(module: torch.nn.Module, inputs: Sequence[Any]) -> list[torch.Tensor]:
    with torch.no_grad():
        return first_tensor_outputs(module(*inputs))
