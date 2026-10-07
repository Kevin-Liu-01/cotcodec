import torch
import triton
import triton.language as tl
from triton.language.extra import libdevice


@triton.jit
def gelu_kernel(x_ptr, y_ptr, n, BLOCK: tl.constexpr):
    offs = tl.program_id(0) * BLOCK + tl.arange(0, BLOCK)
    mask = offs < n
    x = tl.load(x_ptr + offs, mask=mask)
    y = 0.5 * x * (1.0 + libdevice.erf(x * 0.7071067811865476))
    tl.store(y_ptr + offs, y, mask=mask)


@triton.jit
def gelu_tanh_kernel(x_ptr, y_ptr, n, BLOCK: tl.constexpr):
    offs = tl.program_id(0) * BLOCK + tl.arange(0, BLOCK)
    mask = offs < n
    x = tl.load(x_ptr + offs, mask=mask)
    inner = 0.7978845608028654 * (x + 0.044715 * x * x * x)
    t = 2.0 / (1.0 + libdevice.exp(-2.0 * inner)) - 1.0
    tl.store(y_ptr + offs, 0.5 * x * (1.0 + t), mask=mask)


class ModelNew(torch.nn.Module):
    def __init__(self):
        super().__init__()

    def forward(self, x):
        y = torch.empty_like(x)
        n = x.numel()
        gelu_kernel[((n + 1023) // 1024,)](x, y, n, BLOCK=1024)
        return y
