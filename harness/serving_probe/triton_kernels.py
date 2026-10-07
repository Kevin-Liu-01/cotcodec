"""The Triton kernel the step-0 doctor compiles (gate G0.4). Imported only in the container."""

from __future__ import annotations

import torch
import triton
import triton.language as tl


@triton.jit
def _add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK: tl.constexpr):
    offsets = tl.program_id(axis=0) * BLOCK + tl.arange(0, BLOCK)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    tl.store(out_ptr + offsets, x + y, mask=mask)


def vector_add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    """Elementwise ``x + y`` through a freshly JIT-compiled Triton kernel."""
    out = torch.empty_like(x)
    n_elements = out.numel()

    def grid(meta: dict[str, int]) -> tuple[int]:
        return (triton.cdiv(n_elements, meta["BLOCK"]),)

    _add_kernel[grid](x, y, out, n_elements, BLOCK=1024)
    return out
