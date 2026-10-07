import torch
import triton
import triton.language as tl


@triton.jit
def activations_kernel(x_ptr, y_ptr, n, alpha, BLOCK: tl.constexpr):
    offs = tl.program_id(0) * BLOCK + tl.arange(0, BLOCK)
    mask = offs < n
    x = tl.load(x_ptr + offs, mask=mask, other=0.0)
    hardtanh = tl.minimum(tl.maximum(x, -1.0), 1.0)
    softsign = x / (1.0 + tl.abs(x))
    elu = tl.where(x > 0, x, alpha * (tl.exp(x) - 1.0))
    softplus = tl.where(x > 20.0, x, tl.log(1.0 + tl.exp(x)))
    clipped = tl.clamp(x, -1.0, 1.0)
    upper = tl.minimum(x, 1.0)
    y = hardtanh + softsign + elu + softplus + clipped + upper + 1e-06
    tl.store(y_ptr + offs, y, mask=mask)


class ModelNew(torch.nn.Module):
    def __init__(self, alpha=1.0):
        super().__init__()
        self.alpha = alpha

    def forward(self, x):
        y = torch.empty_like(x)
        n = x.numel()
        activations_kernel[(triton.cdiv(n, 1024),)](x, y, n, self.alpha, BLOCK=1024)
        return y
