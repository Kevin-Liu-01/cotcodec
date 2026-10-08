"""CPU emulation of reduced-precision matmul and convolution (no GPU).

TF32 keeps fp32's 8-bit exponent and a 10-bit mantissa. A TF32 tensor-core
matmul rounds both operands to TF32, forms exact products (11 x 11 significand
bits fit in fp32) and accumulates in fp32. ``TF32Mode`` emulates that on the CPU:
it intercepts the aten matmul and convolution ops of an fp32 forward pass,
rounds their two main operands to TF32 and runs the op in fp32, so products are
exact and the CPU's fp32 accumulation stands in for the tensor core's. Bias
terms (addmm's ``self``, convolution's ``bias``) are added in fp32, unrounded,
as cuBLAS and cuDNN do.

Rounding modes: ``rne`` (round to nearest even, as cuBLAS documents for
CUBLAS_COMPUTE_32F_FAST_TF32), ``rz`` (truncation, what Triton's ``tl.dot`` does
by default for fp32 operands) and ``sr`` (stochastic rounding, an unbiased random
member of the same error class, for ensembles).
"""

from __future__ import annotations

import torch
from torch.utils._python_dispatch import TorchDispatchMode

aten = torch.ops.aten
_LOW = 13  # fp32 has 23 mantissa bits, TF32 keeps 10
_MASK = ~((1 << _LOW) - 1)


def round_tf32(x: torch.Tensor, mode: str, generator: torch.Generator | None = None) -> torch.Tensor:
    """Round an fp32 tensor to TF32 (values stay fp32). Finite inputs only."""
    if x.dtype != torch.float32:
        raise TypeError(f"round_tf32 needs fp32, got {x.dtype}")
    bits = x.contiguous().view(torch.int32)
    if mode == "rz":
        out = bits & _MASK
    elif mode == "rne":
        lsb = (bits >> _LOW) & 1
        out = (bits + ((1 << (_LOW - 1)) - 1) + lsb) & _MASK
    elif mode == "sr":
        noise = torch.randint(0, 1 << _LOW, bits.shape, dtype=torch.int32, generator=generator)
        out = (bits + noise) & _MASK
    else:
        raise ValueError(mode)
    return out.view(torch.float32).view(x.shape)


def round_fp16(x: torch.Tensor) -> torch.Tensor:
    return x.to(torch.float16).to(x.dtype)


class TF32Mode(TorchDispatchMode):
    """Round the operands of fp32 matmuls and convolutions to TF32."""

    OPS = {
        aten.mm.default: (0, 1),
        aten.bmm.default: (0, 1),
        aten.addmm.default: (1, 2),
        aten.baddbmm.default: (1, 2),
        aten.convolution.default: (0, 1),
    }

    def __init__(self, mode: str, seed: int = 0) -> None:
        super().__init__()
        self.mode = mode
        self.generator = torch.Generator().manual_seed(seed) if mode == "sr" else None
        self.calls: dict[str, int] = {}

    def __torch_dispatch__(self, func, types, args=(), kwargs=None):  # noqa: ANN001
        kwargs = kwargs or {}
        slots = self.OPS.get(func)
        if slots is not None and all(
            isinstance(args[i], torch.Tensor) and args[i].dtype == torch.float32 for i in slots
        ):
            args = list(args)
            for i in slots:
                args[i] = round_tf32(args[i], self.mode, self.generator)
            self.calls[str(func)] = self.calls.get(str(func), 0) + 1
        return func(*args, **kwargs)


class OpLog(TorchDispatchMode):
    def __init__(self) -> None:
        super().__init__()
        self.ops: list[str] = []

    def __torch_dispatch__(self, func, types, args=(), kwargs=None):  # noqa: ANN001
        self.ops.append(str(func))
        return func(*args, **(kwargs or {}))
