"""A5 (secondary tier): lethe-style contract checks, reimplemented for KernelBench models.

Behavior follows lethe@eaff0bb6 ``src/lethe/verifier/contracts.py`` gates
EXC-01, EXC-02, PRC-01 and PRC-02 (MIT; reimplemented, not copied), with the
audit-harness defaults lethe used for its KernelBench audit (EXC-02 atol 1e-4;
PRC-02 atol scaled by ``max(1, max|ref|)``). Three deliberate fixes to lethe's
adapter (``audit_harness.py``):

1. models stay in **training mode**, as KernelBench evaluates them (lethe calls
   ``.eval()``, which changes BatchNorm and Dropout semantics);
2. **every** floating input is perturbed, not only the first;
3. the reference is the problem's own ``Model`` with the same weights as the
   candidate (``set_seed`` before construction), not a re-instantiation.

A reference that raises on a perturbed input makes that check not
applicable (``na``); a candidate that raises fails it.

Reference store (decision D31): every reference call A5 makes depends only on
the reference, its weights and the drawn inputs, so a reference item computes
them once per problem and replicate (:func:`reference_results`, in the same
order on the same module) and the checks read them through ``refs`` instead of
calling the reference (``refs=None`` is the inline path).
"""

from __future__ import annotations

import copy
import math
from collections.abc import Sequence
from typing import Any

import torch

from harness.q1.gates.common import first_tensor_outputs, synchronize

A5_BASE = 7042
CHECKS = ("EXC-01", "EXC-02", "PRC-01", "PRC-02")


def _floats(values: Sequence[Any]) -> list[int]:
    return [
        i for i, v in enumerate(values) if isinstance(v, torch.Tensor) and v.is_floating_point()
    ]


def _replace(values: Sequence[Any], fn: Any) -> list[Any]:
    return [fn(v) if isinstance(v, torch.Tensor) and v.is_floating_point() else v for v in values]


def _run(model: torch.nn.Module, inputs: Sequence[Any], device: torch.device) -> list[torch.Tensor]:
    with torch.no_grad():
        out = first_tensor_outputs(model(*inputs))
    synchronize(device)
    return out


def _scale(ref: torch.Tensor) -> float:
    r = ref.detach().float()
    finite = r[torch.isfinite(r)]
    return max(1.0, float(finite.abs().max())) if finite.numel() else 1.0


def _pair(
    reference: torch.nn.Module | None,
    candidate: torch.nn.Module,
    ref_inputs: Sequence[Any] | None,
    cand_inputs: Sequence[Any],
    device: torch.device,
    stored: tuple[str, Any] | None = None,
) -> tuple[str, list[torch.Tensor] | None, list[torch.Tensor] | None, str]:
    if stored is None:
        try:
            ref_out = _run(reference, ref_inputs, device)
        except Exception as exc:
            return "na", None, None, _reference_raised(exc)
    elif stored[0] == "na":
        return "na", None, None, stored[1]
    else:
        ref_out = stored[1]
    try:
        cand_out = _run(candidate, cand_inputs, device)
    except Exception as exc:
        return "fail", ref_out, None, f"candidate raised {type(exc).__name__}: {str(exc)[:120]}"
    if len(cand_out) != len(ref_out) or any(
        c.shape != r.shape for c, r in zip(cand_out, ref_out, strict=True)
    ):
        return "fail", ref_out, cand_out, "shape mismatch"
    return "ok", ref_out, cand_out, ""


def _reference_raised(exc: BaseException) -> str:
    return f"reference raised {type(exc).__name__}"


EXC01_VALUES = (("nan", math.nan), ("pos_inf", math.inf), ("neg_inf", -math.inf))


def _scatter(value: float) -> Any:
    def scatter(t: torch.Tensor) -> torch.Tensor:
        t = t.clone()
        t.view(-1)[:: max(1, t.numel() // 8)] = value
        return t

    return scatter


def _subnormal(t: torch.Tensor) -> torch.Tensor:
    tiny = {torch.float32: 1e-40, torch.float16: 1e-7}.get(t.dtype, 1e-39)
    out = torch.full_like(t, tiny)
    flat = out.view(-1)
    flat[::3] = -tiny
    flat[::7] = 0.0
    return out


PRC01_DTYPES = ((torch.float16, 1e-3), (torch.bfloat16, 1e-2))


def _rounded_reference(reference: torch.nn.Module, dtype: torch.dtype) -> torch.nn.Module:
    ref_model = copy.deepcopy(reference)
    with torch.no_grad():
        for p in ref_model.parameters():
            p.copy_(p.to(dtype).float())
        for b in ref_model.buffers():
            if b.is_floating_point():
                b.copy_(b.to(dtype).float())
    return ref_model


def _stored(refs: Any, tag: str) -> tuple[str, Any] | None:
    return None if refs is None else refs[tag]


def exc_01(reference, candidate, inputs, device, refs=None) -> dict[str, Any]:  # noqa: ANN001
    """NaN, +Inf and -Inf scattered into every float input; masks must agree."""
    failures, statuses = [], []
    for label, value in EXC01_VALUES:
        perturbed = _replace(inputs, _scatter(value))
        status, ref_out, cand_out, why = _pair(
            reference, candidate, perturbed, perturbed, device, _stored(refs, f"EXC-01/{label}")
        )
        statuses.append(status)
        if status == "fail":
            failures.append(f"{label}: {why}")
        elif status == "ok":
            for r, c in zip(ref_out, cand_out, strict=True):
                if not r.is_floating_point():
                    continue
                for name, fn in (
                    ("nan", torch.isnan),
                    ("+inf", torch.isposinf),
                    ("-inf", torch.isneginf),
                ):
                    if not torch.equal(fn(r).cpu(), fn(c).cpu()):
                        failures.append(f"{label}: {name} mask mismatch")
    return _status("EXC-01", statuses, failures)


def exc_02(reference, candidate, inputs, device, atol: float = 1e-4, refs=None) -> dict[str, Any]:  # noqa: ANN001
    """Subnormal inputs; flush-to-zero and non-finite masks agree, others within atol."""
    perturbed = _replace(inputs, _subnormal)
    status, ref_out, cand_out, why = _pair(
        reference, candidate, perturbed, perturbed, device, _stored(refs, "EXC-02")
    )
    failures = [why] if status == "fail" else []
    if status == "ok":
        for r, c in zip(ref_out, cand_out, strict=True):
            r64, c64 = r.detach().cpu().double(), c.detach().cpu().double()
            if not torch.equal(r64 == 0, c64 == 0):
                failures.append("flush-to-zero mismatch")
            if not torch.equal(~torch.isfinite(r64), ~torch.isfinite(c64)):
                failures.append("non-finite mismatch")
            keep = (r64 != 0) & torch.isfinite(r64)
            if bool(keep.any()):
                err = float((r64[keep] - c64[keep]).abs().max())
                if not math.isfinite(err) or err > atol:
                    failures.append(f"subnormal values differ by {err:.3e}")
    return _status("EXC-02", [status], failures)


def prc_01(reference, candidate, inputs, device, refs=None) -> dict[str, Any]:  # noqa: ANN001
    """fp16 and bf16 regimes: candidate in the low dtype vs fp32 reference on rounded values."""
    failures, statuses = [], []
    for dtype, tol in PRC01_DTYPES:
        ref_model = ref_inputs = None
        if refs is None:
            ref_model = _rounded_reference(reference, dtype)
            ref_inputs = _replace(inputs, lambda t, d=dtype: t.to(d).float())
        cand_model = copy.deepcopy(candidate).to(dtype)
        cand_inputs = _replace(inputs, lambda t, d=dtype: t.to(d))
        status, ref_out, cand_out, why = _pair(
            ref_model, cand_model, ref_inputs, cand_inputs, device, _stored(refs, f"PRC-01/{dtype}")
        )
        statuses.append(status)
        if status == "fail":
            failures.append(f"{dtype}: {why}")
        elif status == "ok":
            for r, c in zip(ref_out, cand_out, strict=True):
                r_low = r.to(dtype).float()
                atol = tol * _scale(r_low)
                if not torch.allclose(c.float(), r_low, atol=atol, rtol=tol, equal_nan=True):
                    failures.append(f"{dtype}: beyond atol={atol:.2e}")
    return _status("PRC-01", statuses, failures)


def prc_02(reference, candidate, inputs, device, atol: float = 2e-2, refs=None) -> dict[str, Any]:  # noqa: ANN001
    """fp16 inputs to the candidate must match the fp32 reference (fp32 accumulation)."""
    cand_model = copy.deepcopy(candidate).to(torch.float16)
    cand_inputs = _replace(inputs, lambda t: t.to(torch.float16))
    status, ref_out, cand_out, why = _pair(
        reference, cand_model, inputs, cand_inputs, device, _stored(refs, "PRC-02")
    )
    failures = [why] if status == "fail" else []
    if status == "ok":
        for r, c in zip(ref_out, cand_out, strict=True):
            r32, c32 = r.detach().float(), c.detach().float()
            effective = atol * _scale(r32)
            diff = (c32 - r32).abs()
            within = (diff <= effective) | (torch.isnan(c32) & torch.isnan(r32)) | (c32 == r32)
            if not bool(within.all()):
                failures.append(f"max_err={float(diff[~within].max()):.3e} > {effective:.3e}")
    return _status("PRC-02", [status], failures)


def _status(name: str, statuses: Sequence[str], failures: Sequence[str]) -> dict[str, Any]:
    if failures:
        verdict = "fail"
    elif statuses and all(s == "na" for s in statuses):
        verdict = "na"
    else:
        verdict = "pass"
    return {"check": name, "status": verdict, "failures": list(failures)[:10]}


def run_a5(
    reference: torch.nn.Module,
    candidate: torch.nn.Module,
    inputs: Sequence[Any],
    *,
    device: torch.device,
    refs: Any = None,
) -> list[dict[str, Any]]:
    """Run the four checks; both models must already be on ``device`` in training mode.

    ``refs`` (tag -> ``("ok", outputs)`` or ``("na", message)``, from
    :func:`reference_results`) replaces every reference call."""
    if not _floats(inputs):
        return [{"check": c, "status": "na", "failures": ["no float input"]} for c in CHECKS]
    results = []
    for check in (exc_01, exc_02, prc_01, prc_02):
        try:
            results.append(check(reference, candidate, inputs, device, refs=refs))
        except Exception as exc:
            results.append(
                {
                    "check": check.__name__.upper().replace("_", "-"),
                    "status": "error",
                    "failures": [f"{type(exc).__name__}: {str(exc)[:200]}"],
                }
            )
    return results


REFERENCE_TAGS = (
    *(f"EXC-01/{label}" for label, _ in EXC01_VALUES),
    "EXC-02",
    *(f"PRC-01/{dtype}" for dtype, _ in PRC01_DTYPES),
    "PRC-02",
)


def reference_results(
    reference: torch.nn.Module, inputs: Sequence[Any], *, device: torch.device
) -> tuple[dict[str, tuple[str, Any]], list[str]]:
    """Every reference call of :func:`run_a5`, in its order, on the same module.

    Returns tag -> ``("ok", outputs)`` or ``("na", message)`` and the problems
    that make the result unusable (a reference call that changed its inputs or
    the RNG state, an output that is not storable or aliases an input, a CUDA
    resource failure, an exception outside a reference call)."""
    from harness.q1 import refstore

    results: dict[str, tuple[str, Any]] = {}
    problems: list[str] = []

    def call(tag: str, model: torch.nn.Module, ref_inputs: Sequence[Any]) -> None:
        probe = refstore.Probe(list(ref_inputs), device)
        try:
            out = _run(model, ref_inputs, device)
        except Exception as exc:
            if refstore.resource_failure(exc):
                problems.append(f"{tag}: resource failure")
            results[tag] = ("na", _reference_raised(exc))
            return
        problems.extend(f"{tag}: {p}" for p in probe.changes())
        if refstore.aliases(out, list(ref_inputs)):
            problems.append(f"{tag}: reference-output-aliases-input")
        results[tag] = ("ok", out)

    if not _floats(inputs):
        return results, problems
    try:
        for label, value in EXC01_VALUES:
            perturbed = _replace(inputs, _scatter(value))
            call(f"EXC-01/{label}", reference, perturbed)
        call("EXC-02", reference, _replace(inputs, _subnormal))
        for dtype, _ in PRC01_DTYPES:
            ref_model = _rounded_reference(reference, dtype)
            ref_inputs = _replace(inputs, lambda t, d=dtype: t.to(d).float())
            call(f"PRC-01/{dtype}", ref_model, ref_inputs)
        call("PRC-02", reference, inputs)
    except Exception as exc:  # outside a reference call: inline, the check would error
        problems.append(f"reference side raised {type(exc).__name__}")
    return results, problems
