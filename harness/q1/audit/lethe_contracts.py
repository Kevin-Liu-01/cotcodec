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
    reference: torch.nn.Module,
    candidate: torch.nn.Module,
    ref_inputs: Sequence[Any],
    cand_inputs: Sequence[Any],
    device: torch.device,
) -> tuple[str, list[torch.Tensor] | None, list[torch.Tensor] | None, str]:
    try:
        ref_out = _run(reference, ref_inputs, device)
    except Exception as exc:
        return "na", None, None, f"reference raised {type(exc).__name__}"
    try:
        cand_out = _run(candidate, cand_inputs, device)
    except Exception as exc:
        return "fail", ref_out, None, f"candidate raised {type(exc).__name__}: {str(exc)[:120]}"
    if len(cand_out) != len(ref_out) or any(
        c.shape != r.shape for c, r in zip(cand_out, ref_out, strict=True)
    ):
        return "fail", ref_out, cand_out, "shape mismatch"
    return "ok", ref_out, cand_out, ""


def exc_01(reference, candidate, inputs, device) -> dict[str, Any]:  # noqa: ANN001
    """NaN, +Inf and -Inf scattered into every float input; masks must agree."""
    failures, statuses = [], []
    for label, value in (("nan", math.nan), ("pos_inf", math.inf), ("neg_inf", -math.inf)):

        def scatter(t: torch.Tensor, value: float = value) -> torch.Tensor:
            t = t.clone()
            t.view(-1)[:: max(1, t.numel() // 8)] = value
            return t

        perturbed = _replace(inputs, scatter)
        status, ref_out, cand_out, why = _pair(reference, candidate, perturbed, perturbed, device)
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


def exc_02(reference, candidate, inputs, device, atol: float = 1e-4) -> dict[str, Any]:  # noqa: ANN001
    """Subnormal inputs; flush-to-zero and non-finite masks agree, others within atol."""

    def subnormal(t: torch.Tensor) -> torch.Tensor:
        tiny = {torch.float32: 1e-40, torch.float16: 1e-7}.get(t.dtype, 1e-39)
        out = torch.full_like(t, tiny)
        flat = out.view(-1)
        flat[::3] = -tiny
        flat[::7] = 0.0
        return out

    perturbed = _replace(inputs, subnormal)
    status, ref_out, cand_out, why = _pair(reference, candidate, perturbed, perturbed, device)
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


def prc_01(reference, candidate, inputs, device) -> dict[str, Any]:  # noqa: ANN001
    """fp16 and bf16 regimes: candidate in the low dtype vs fp32 reference on rounded values."""
    failures, statuses = [], []
    for dtype, tol in ((torch.float16, 1e-3), (torch.bfloat16, 1e-2)):
        ref_model = copy.deepcopy(reference)
        with torch.no_grad():
            for p in ref_model.parameters():
                p.copy_(p.to(dtype).float())
            for b in ref_model.buffers():
                if b.is_floating_point():
                    b.copy_(b.to(dtype).float())
        ref_inputs = _replace(inputs, lambda t, d=dtype: t.to(d).float())
        cand_model = copy.deepcopy(candidate).to(dtype)
        cand_inputs = _replace(inputs, lambda t, d=dtype: t.to(d))
        status, ref_out, cand_out, why = _pair(
            ref_model, cand_model, ref_inputs, cand_inputs, device
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


def prc_02(reference, candidate, inputs, device, atol: float = 2e-2) -> dict[str, Any]:  # noqa: ANN001
    """fp16 inputs to the candidate must match the fp32 reference (fp32 accumulation)."""
    cand_model = copy.deepcopy(candidate).to(torch.float16)
    cand_inputs = _replace(inputs, lambda t: t.to(torch.float16))
    status, ref_out, cand_out, why = _pair(reference, cand_model, inputs, cand_inputs, device)
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
) -> list[dict[str, Any]]:
    """Run the four checks; both models must already be on ``device`` in training mode."""
    if not _floats(inputs):
        return [{"check": c, "status": "na", "failures": ["no float input"]} for c in CHECKS]
    results = []
    for check in (exc_01, exc_02, prc_01, prc_02):
        try:
            results.append(check(reference, candidate, inputs, device))
        except Exception as exc:
            results.append(
                {
                    "check": check.__name__.upper().replace("_", "-"),
                    "status": "error",
                    "failures": [f"{type(exc).__name__}: {str(exc)[:200]}"],
                }
            )
    return results
