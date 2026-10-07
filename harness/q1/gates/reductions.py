"""Chunked, device-side versions of the gates' and audit's element-wise reductions.

The first implementations copied whole outputs to the host in fp64 before
reducing them (``x.detach().cpu().double()``). On KernelBench@423217d9's
level-1 problems, whose inputs and outputs reach 6.4-17 GB, that made one
gate (a) item exceed its 180 s watchdog on a reference-identity control (pilot
job 474) and pushed host memory past 60 GB per process. The functions here
compute the same quantities in fp64 over fixed-size chunks on the tensors'
device (the CUDA device when either tensor is on one), so the results are the
same numbers: fp32 to fp64 conversion is exact, and fp64 subtraction, absolute
value, addition, multiplication and division are correctly rounded IEEE
operations on both the CPU and the GPU; max, all, any and equality do not
depend on how the elements are split. ``tests/test_q1_reductions.py`` checks
each against the previous whole-tensor implementation on tensors with NaN,
infinities, zeros and chunk-boundary positions.
"""

from __future__ import annotations

import math
from collections.abc import Iterator

import torch

#: Elements per chunk (512 MiB per fp64 operand).
CHUNK = 1 << 26


def _common_device(a: torch.Tensor, b: torch.Tensor) -> torch.device:
    for t in (a, b):
        if t.device.type == "cuda":
            return t.device
    return a.device


def paired_chunks(
    a: torch.Tensor, b: torch.Tensor, *, dtype: torch.dtype = torch.float64, chunk: int = CHUNK
) -> Iterator[tuple[torch.Tensor, torch.Tensor]]:
    """Equal-length flat chunks of ``a`` and ``b`` (same shape) on one device."""
    device = _common_device(a, b)
    flat_a = a.detach().reshape(-1)
    flat_b = b.detach().reshape(-1)
    for start in range(0, flat_a.numel(), chunk):
        yield (
            flat_a[start : start + chunk].to(device=device, dtype=dtype),
            flat_b[start : start + chunk].to(device=device, dtype=dtype),
        )


def error_stats(
    output: torch.Tensor, reference: torch.Tensor, *, chunk: int = CHUNK
) -> tuple[float, float]:
    """Max absolute and relative error over positions where both are finite
    (``gates.common.error_stats``)."""
    if output.shape != reference.shape:
        return math.inf, math.inf
    if output.numel() == 0:
        return 0.0, 0.0
    max_abs = None
    max_rel = 0.0
    any_finite = False
    for out, ref in paired_chunks(output, reference, chunk=chunk):
        both_finite = torch.isfinite(out) & torch.isfinite(ref)
        same_nonfinite = (torch.isnan(out) & torch.isnan(ref)) | (
            torch.isinf(out) & torch.isinf(ref) & (torch.sign(out) == torch.sign(ref))
        )
        if bool((~both_finite & ~same_nonfinite).any()):
            return math.inf, math.inf
        if not bool(both_finite.any()):
            continue
        any_finite = True
        diff = (out - ref).abs()[both_finite]
        denom = ref.abs()[both_finite]
        chunk_abs = float(diff.max())
        max_abs = chunk_abs if max_abs is None else max(max_abs, chunk_abs)
        nonzero = denom > 0
        if bool(nonzero.any()):
            max_rel = max(max_rel, float((diff[nonzero] / denom[nonzero]).max()))
    if not any_finite:
        return 0.0, 0.0
    return float(max_abs), max_rel


def allclose_fp64(a: torch.Tensor, b: torch.Tensor, tol: float, *, chunk: int = CHUNK) -> bool:
    """``torch.allclose(a.double(), b.double(), atol=tol, rtol=tol)``."""
    if a.shape != b.shape:
        return False
    return all(
        bool(torch.allclose(x, y, atol=tol, rtol=tol))
        for x, y in paired_chunks(a, b, chunk=chunk)
    )


def equal_int64(a: torch.Tensor, b: torch.Tensor, *, chunk: int = CHUNK) -> bool:
    """``torch.equal(a.cpu().to(torch.int64), b.cpu().to(torch.int64))``."""
    if a.shape != b.shape:
        return False
    return all(
        bool(torch.equal(x, y)) for x, y in paired_chunks(a, b, dtype=torch.int64, chunk=chunk)
    )


def masks_equal(x: torch.Tensor, r: torch.Tensor, *, chunk: int = CHUNK) -> bool:
    """NaN, +Inf and -Inf masks of ``x`` and ``r`` agree (``audit.oracle.masks_equal``)."""
    if x.shape != r.shape:
        return False
    for a, b in paired_chunks(x, r, chunk=chunk):
        if not (
            torch.equal(torch.isnan(a), torch.isnan(b))
            and torch.equal(torch.isposinf(a), torch.isposinf(b))
            and torch.equal(torch.isneginf(a), torch.isneginf(b))
        ):
            return False
    return True


def scaled_error(x: torch.Tensor, r: torch.Tensor, kappa: float, *, chunk: int = CHUNK) -> float:
    """``e(x) = max |x - r| / (|r| + kappa * max|r|)`` over positions where both are
    finite (``audit.oracle.scaled_error``); two passes, the first for ``max|r|``."""
    if x.shape != r.shape:
        return math.inf
    norm = None
    for a, b in paired_chunks(x, r, chunk=chunk):
        finite = torch.isfinite(a) & torch.isfinite(b)
        if bool(finite.any()):
            value = float(b[finite].abs().max())
            norm = value if norm is None else max(norm, value)
    if norm is None:
        return 0.0
    worst = None
    for a, b in paired_chunks(x, r, chunk=chunk):
        finite = torch.isfinite(a) & torch.isfinite(b)
        if not bool(finite.any()):
            continue
        r_finite = b[finite]
        denom = r_finite.abs() + kappa * norm
        diff = (a[finite] - r_finite).abs()
        zero = denom == 0
        if bool(zero.any()):
            if bool((diff[zero] > 0).any()):
                return math.inf
            diff, denom = diff[~zero], denom[~zero]
            if diff.numel() == 0:
                continue
        value = float((diff / denom).max())
        worst = value if worst is None else max(worst, value)
    return 0.0 if worst is None else worst


def bytes_equal(a: torch.Tensor, b: torch.Tensor) -> bool:
    """Byte-for-byte equality of two tensors' contiguous data, on the device
    (``audit.contracts.tensor_bytes(a) == tensor_bytes(b)``)."""
    if a.numel() * a.element_size() != b.numel() * b.element_size():
        return False
    if a.numel() == 0:
        return True
    left = a.detach().contiguous().reshape(-1).view(torch.uint8)
    right = b.detach().contiguous().reshape(-1).view(torch.uint8)
    if left.device != right.device:
        right = right.to(left.device)
    return bool(torch.equal(left, right))


__all__ = [
    "CHUNK",
    "allclose_fp64",
    "bytes_equal",
    "equal_int64",
    "error_stats",
    "masks_equal",
    "paired_chunks",
    "scaled_error",
]
