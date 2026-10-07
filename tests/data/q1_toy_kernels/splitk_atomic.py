import torch
import triton
import triton.language as tl


@triton.jit
def rowsum_splitk_kernel(x_ptr, out_ptr, n_cols, SPLIT: tl.constexpr, BLOCK: tl.constexpr):
    row = tl.program_id(0)
    split = tl.program_id(1)
    acc = tl.zeros([BLOCK], dtype=tl.float32)
    for start in range(split * BLOCK, n_cols, SPLIT * BLOCK):
        cols = start + tl.arange(0, BLOCK)
        acc += tl.load(x_ptr + row * n_cols + cols, mask=cols < n_cols, other=0.0)
    tl.debug_barrier()
    tl.atomic_add(out_ptr + row, tl.sum(acc, axis=0))


class ModelNew(torch.nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.dim = dim

    def forward(self, x):
        n_rows, n_cols = x.shape
        out = torch.zeros((n_rows,), device=x.device, dtype=torch.float32)
        rowsum_splitk_kernel[(n_rows, 4)](x, out, n_cols, SPLIT=4, BLOCK=1024)
        return out
