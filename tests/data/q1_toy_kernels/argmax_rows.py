import torch
import triton
import triton.language as tl


@triton.jit
def argmax_kernel(x_ptr, out_ptr, n_rows, n_cols, BLOCK_N: tl.constexpr):
    row = tl.program_id(0)
    if row >= n_rows:
        return
    cols = tl.arange(0, BLOCK_N)
    x = tl.load(x_ptr + row * n_cols + cols, mask=cols < n_cols, other=-float("inf"))
    best = tl.argmax(x, axis=0)
    tl.store(out_ptr + row, best)


@triton.jit
def rowmin_kernel(x_ptr, out_ptr, n_cols, BLOCK_N: tl.constexpr):
    row = tl.program_id(0)
    cols = tl.arange(0, BLOCK_N)
    m = tl.full([BLOCK_N], float("inf"), tl.float32)
    x = tl.load(x_ptr + row * n_cols + cols, mask=cols < n_cols, other=float("inf"))
    m = tl.minimum(m, x)
    tl.store(out_ptr + row, tl.min(m, axis=0))


class ModelNew(torch.nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.dim = dim

    def forward(self, x):
        n_rows, n_cols = x.shape
        out = torch.empty((n_rows,), device=x.device, dtype=torch.int64)
        argmax_kernel[(n_rows,)](x, out, n_rows, n_cols, BLOCK_N=triton.next_power_of_2(n_cols))
        return out
