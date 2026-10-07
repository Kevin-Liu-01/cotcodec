import torch
import triton
import triton.language as tl


@triton.jit
def running_extrema_kernel(
    x_ptr, out_ptr, n_rows, n_cols, BLOCK_R: tl.constexpr, BLOCK_C: tl.constexpr
):
    pid = tl.program_id(0)
    rows = pid * BLOCK_R + tl.arange(0, BLOCK_R)
    run_max = tl.full([BLOCK_R], -float("inf"), tl.float32)
    for start in range(0, n_cols, BLOCK_C):
        cols = start + tl.arange(0, BLOCK_C)
        mask = (rows[:, None] < n_rows) & (cols[None, :] <= n_cols - 1)
        x = tl.load(x_ptr + rows[:, None] * n_cols + cols[None, :], mask=mask, other=0.0)
        blk = tl.max(tl.maximum(x, 0.0), axis=1)
        run_max = tl.maximum(run_max, blk)
    lowest = tl.argmin(tl.minimum(1.0, run_max), axis=0)
    safe = tl.maximum(run_max, 0.0, propagate_nan=tl.PropagateNan.ALL)
    tl.store(out_ptr + rows, safe + lowest, mask=rows < n_rows)


class ModelNew(torch.nn.Module):
    def __init__(self):
        super().__init__()

    def forward(self, x):
        n_rows, n_cols = x.shape
        out = torch.empty((n_rows,), device=x.device, dtype=torch.float32)
        grid = (triton.cdiv(n_rows, 16),)
        running_extrema_kernel[grid](x, out, n_rows, n_cols, BLOCK_R=16, BLOCK_C=128)
        return out
