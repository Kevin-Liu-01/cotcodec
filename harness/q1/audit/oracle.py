"""A1: the fp64 oracle, its threshold, the dual TF32 policy (D14) and calibration.

Error metric for a float output ``x`` against the fp64 oracle ``r64``::

    e(x) = max_i |x_i - r64_i| / (|r64_i| + kappa * ||r64||_inf),  kappa = 1e-3

taken over positions where both are finite; the NaN, +Inf and -Inf masks of
``x`` must equal ``r64``'s exactly. A candidate passes A1 if
``e(candidate) <= T`` with::

    T = max(M * max(e(r32_device), e(r32_cpu)), 2**-20),  M = 16

TF32 policy (decision D14, fixed before any mutant is scored):

- ``tf32-admissible`` (primary): when the reference executes a matmul or
  convolution, or the candidate source calls ``tl.dot``, T is also computed
  from a device reference run with ``torch.backends.cuda.matmul.allow_tf32``
  and ``torch.backends.cudnn.allow_tf32`` both on, and the larger T is used;
- ``strict-fp32`` (secondary): the device reference runs with both flags off.

Integer and bool outputs need an exact match with the fp64 oracle (torch's
first-index rule for argmax/argmin ties). A mismatch is excused only at
positions where an fp32 reference itself disagrees with the oracle (a
near-tie certified by fp64), and only if the candidate equals the oracle or
one of those fp32 references there.

Calibration: ``M`` may be raised once, before any evaluation-split or mutant
scoring, to the smallest power of two that gives zero A1 rejections on the
S1 calibration split. The audit is then frozen by ``audit_version_hash``.
"""

from __future__ import annotations

import copy
import math
import re
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

import torch

from harness.q1.gates.common import first_tensor_outputs, synchronize

KAPPA = 1e-3
T_FLOOR = 2.0**-20
DEFAULT_MULTIPLIER = 16
PRECISION_ONLY_FACTOR = 64
POLICIES = ("tf32-admissible", "strict-fp32")

_MATMUL_CONV_OP = re.compile(
    r"^(mm|bmm|addmm|addbmm|baddbmm|matmul|linear|_linear|addmv|mv|dot|vdot|einsum|tensordot"
    r"|convolution|_convolution|cudnn_convolution\w*|conv\w*|_scaled_dot_product\w*"
    r"|scaled_dot_product_attention|_scaled_mm|_int_mm)$"
)
_TL_DOT = re.compile(r"\b(tl|triton\.language|language)\s*\.\s*dot(_scaled)?\s*\(")


@contextmanager
def tf32(enabled: bool) -> Iterator[None]:
    """Set both TF32 switches for the duration of the block."""
    old = (torch.backends.cuda.matmul.allow_tf32, torch.backends.cudnn.allow_tf32)
    torch.backends.cuda.matmul.allow_tf32 = enabled
    torch.backends.cudnn.allow_tf32 = enabled
    try:
        yield
    finally:
        torch.backends.cuda.matmul.allow_tf32, torch.backends.cudnn.allow_tf32 = old


class OpRecorder(torch.utils._python_dispatch.TorchDispatchMode):
    """Records the aten op names a forward pass dispatches."""

    def __init__(self) -> None:
        super().__init__()
        self.ops: set[str] = set()

    def __torch_dispatch__(self, func, types, args=(), kwargs=None):  # noqa: ANN001
        name = getattr(getattr(func, "_schema", None), "name", str(func))
        self.ops.add(name.split("::")[-1].split(".")[0])
        return func(*args, **(kwargs or {}))


def uses_matmul_or_conv(ops: Sequence[str]) -> bool:
    return any(_MATMUL_CONV_OP.match(op) for op in ops)


def candidate_uses_tl_dot(kernel_source: str) -> bool:
    return bool(_TL_DOT.search(kernel_source))


# --- Error metric ------------------------------------------------------------------


def masks_equal(x: torch.Tensor, r64: torch.Tensor) -> bool:
    x = x.detach().cpu().double()
    r = r64.detach().cpu().double()
    if x.shape != r.shape:
        return False
    return bool(
        torch.equal(torch.isnan(x), torch.isnan(r))
        and torch.equal(torch.isposinf(x), torch.isposinf(r))
        and torch.equal(torch.isneginf(x), torch.isneginf(r))
    )


def scaled_error(x: torch.Tensor, r64: torch.Tensor, kappa: float = KAPPA) -> float:
    """``e(x)``; ``inf`` on shape mismatch, 0 for empty or all-non-finite outputs."""
    x = x.detach().cpu().double()
    r = r64.detach().cpu().double()
    if x.shape != r.shape:
        return math.inf
    finite = torch.isfinite(x) & torch.isfinite(r)
    if not bool(finite.any()):
        return 0.0
    r_finite = r[finite]
    norm = float(r_finite.abs().max())
    denom = r_finite.abs() + kappa * norm
    diff = (x[finite] - r_finite).abs()
    zero = denom == 0
    if bool(zero.any()):
        if bool((diff[zero] > 0).any()):
            return math.inf
        diff, denom = diff[~zero], denom[~zero]
        if diff.numel() == 0:
            return 0.0
    return float((diff / denom).max())


def threshold(reference_errors: Sequence[float], multiplier: float) -> float:
    finite = [e for e in reference_errors if math.isfinite(e)]
    worst = max(finite) if finite else math.inf
    return max(multiplier * worst, T_FLOOR)


# --- References ---------------------------------------------------------------------


@dataclass
class OracleReference:
    """fp64 oracle outputs and the fp32 reference errors that set T."""

    r64: list[torch.Tensor]
    r32_device: list[torch.Tensor]
    r32_cpu: list[torch.Tensor] | None
    r32_tf32: list[torch.Tensor] | None
    e_device: float
    e_cpu: float | None
    e_tf32: float | None
    ops: list[str] = field(default_factory=list)

    @property
    def matmul_or_conv(self) -> bool:
        return uses_matmul_or_conv(self.ops)


def _errors(outputs: Sequence[torch.Tensor], r64: Sequence[torch.Tensor]) -> float:
    errs = [
        scaled_error(o, r) if o.is_floating_point() else 0.0
        for o, r in zip(outputs, r64, strict=True)
    ]
    return max(errs) if errs else 0.0


def _double_inputs(inputs: Sequence[Any]) -> list[Any]:
    return [
        x.double() if isinstance(x, torch.Tensor) and x.is_floating_point() else x for x in inputs
    ]


def build_reference(
    reference: torch.nn.Module,
    inputs: Sequence[Any],
    *,
    device: torch.device,
    with_cpu: bool = True,
    with_tf32: bool = True,
) -> OracleReference:
    """Oracle and fp32 references on the same input values, models in training mode.

    The fp64 oracle is a deep copy with parameters and buffers in fp64 (TF32
    is irrelevant in fp64). The device fp32 reference runs with TF32 off
    (strict); the TF32 reference runs with both switches on; the CPU fp32
    reference runs on CPU copies. Every forward runs under ``no_grad``.
    """
    with torch.no_grad():
        oracle = copy.deepcopy(reference).double()
        with tf32(False):
            r64 = [o.detach() for o in first_tensor_outputs(oracle(*_double_inputs(inputs)))]
            recorder = OpRecorder()
            with recorder:
                r32 = first_tensor_outputs(copy.deepcopy(reference)(*inputs))
            synchronize(device)
        r32_tf32 = None
        if with_tf32 and device.type == "cuda":
            with tf32(True):
                r32_tf32 = first_tensor_outputs(copy.deepcopy(reference)(*inputs))
                synchronize(device)
        r32_cpu = None
        if with_cpu:
            if device.type == "cpu":
                r32_cpu = r32
            else:
                cpu_inputs = [x.cpu() if isinstance(x, torch.Tensor) else x for x in inputs]
                r32_cpu = first_tensor_outputs(copy.deepcopy(reference).to("cpu")(*cpu_inputs))
    return OracleReference(
        r64=r64,
        r32_device=r32,
        r32_cpu=r32_cpu,
        r32_tf32=r32_tf32,
        e_device=_errors(r32, r64),
        e_cpu=_errors(r32_cpu, r64) if r32_cpu is not None else None,
        e_tf32=_errors(r32_tf32, r64) if r32_tf32 is not None else None,
        ops=sorted(recorder.ops),
    )


# --- A1 verdict ------------------------------------------------------------------------


@dataclass
class A1Result:
    passed: bool
    policy: str
    error: float
    threshold: float
    passes_at_precision_factor: bool
    tf32_applied: bool
    integer_mismatches: int = 0
    certified_near_ties: int = 0
    reason: str = ""

    def details(self) -> dict[str, Any]:
        return {
            "policy": self.policy,
            "e": self.error if math.isfinite(self.error) else None,
            "T": self.threshold,
            "passes_at_64T": self.passes_at_precision_factor,
            "tf32_applied": self.tf32_applied,
            "integer_mismatches": self.integer_mismatches,
            "certified_near_ties": self.certified_near_ties,
            "reason": self.reason,
        }


def a1_threshold(
    ref: OracleReference, *, policy: str, multiplier: float, candidate_tl_dot: bool
) -> tuple[float, bool]:
    if policy not in POLICIES:
        raise ValueError(f"unknown TF32 policy {policy}")
    base = [ref.e_device] + ([ref.e_cpu] if ref.e_cpu is not None else [])
    strict_t = threshold(base, multiplier)
    applies = policy == "tf32-admissible" and (ref.matmul_or_conv or candidate_tl_dot)
    if applies and ref.e_tf32 is not None:
        return max(strict_t, threshold([ref.e_tf32], multiplier)), True
    return strict_t, False


def _integer_check(
    candidate: torch.Tensor, ref: OracleReference, index: int, policy: str
) -> tuple[int, int]:
    """(unexcused mismatches, certified near-ties) for an integer or bool output."""
    cand = candidate.detach().cpu().to(torch.int64)
    oracle = ref.r64[index].detach().cpu().to(torch.int64)
    if cand.shape != oracle.shape:
        return max(1, oracle.numel()), 0
    alternatives = [ref.r32_device[index]]
    if ref.r32_cpu is not None:
        alternatives.append(ref.r32_cpu[index])
    if policy == "tf32-admissible" and ref.r32_tf32 is not None:
        alternatives.append(ref.r32_tf32[index])
    alts = [a.detach().cpu().to(torch.int64) for a in alternatives]
    mismatch = cand != oracle
    if not bool(mismatch.any()):
        return 0, 0
    near_tie = torch.zeros_like(mismatch)
    matches_alt = torch.zeros_like(mismatch)
    for alt in alts:
        near_tie |= alt != oracle
        matches_alt |= cand == alt
    excused = mismatch & near_tie & matches_alt
    return int((mismatch & ~excused).sum()), int(excused.sum())


def a1_compare(
    candidate_output: Any,
    ref: OracleReference,
    *,
    policy: str,
    multiplier: float = DEFAULT_MULTIPLIER,
    candidate_tl_dot: bool = False,
) -> A1Result:
    try:
        outputs = first_tensor_outputs(candidate_output)
    except TypeError as exc:
        return A1Result(False, policy, math.inf, math.nan, False, False, reason=str(exc))
    t, tf32_applied = a1_threshold(
        ref, policy=policy, multiplier=multiplier, candidate_tl_dot=candidate_tl_dot
    )
    if len(outputs) != len(ref.r64):
        return A1Result(False, policy, math.inf, t, False, tf32_applied, reason="output-count")
    worst = 0.0
    unexcused = certified = 0
    for index, (out, r64) in enumerate(zip(outputs, ref.r64, strict=True)):
        if tuple(out.shape) != tuple(r64.shape):
            return A1Result(False, policy, math.inf, t, False, tf32_applied, reason="shape")
        if not r64.is_floating_point():
            bad, ok = _integer_check(out, ref, index, policy)
            unexcused += bad
            certified += ok
            continue
        if not out.is_floating_point():
            return A1Result(False, policy, math.inf, t, False, tf32_applied, reason="dtype-kind")
        if not masks_equal(out, r64):
            return A1Result(
                False, policy, math.inf, t, False, tf32_applied, reason="nonfinite-mask"
            )
        worst = max(worst, scaled_error(out, r64))
    if unexcused:
        return A1Result(
            False, policy, worst, t, False, tf32_applied, unexcused, certified, "integer-mismatch"
        )
    passed = worst <= t
    return A1Result(
        passed,
        policy,
        worst,
        t,
        worst <= PRECISION_ONLY_FACTOR * t,
        tf32_applied,
        0,
        certified,
        "" if passed else "exceeds-T",
    )


def calibrate_multiplier(
    required_multipliers: Sequence[float], base: int = DEFAULT_MULTIPLIER
) -> tuple[int, bool]:
    """Smallest power of two >= ``base`` that admits every calibration kernel.

    ``required_multipliers[k]`` is calibration member ``k``'s requirement from
    ``calibration.required_multiplier`` (which handles exact references and
    the T floor); the driver (``calibration.calibrate``) leaves infinite and
    over-ceiling requirements out as fault candidates. Returns ``(M, raised)``.
    The raise is allowed once; the caller records it in the audit version.
    """
    need = max([float(base), *required_multipliers]) if required_multipliers else float(base)
    if not math.isfinite(need):
        raise ValueError("a calibration kernel has an infinite required multiplier")
    m = base
    while m < need:
        m *= 2
    return m, m != base
