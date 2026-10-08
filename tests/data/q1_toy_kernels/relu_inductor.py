import torch
import triton
import triton.language as tl
from torch._inductor.runtime import triton_helpers


@triton.jit
def triton_poi_fused_relu_0(in_ptr0, out_ptr0, xnumel, XBLOCK: tl.constexpr):
    xoffset = tl.program_id(0) * XBLOCK
    xindex = xoffset + tl.arange(0, XBLOCK)[:]
    xmask = xindex < xnumel
    x0 = xindex
    tmp0 = tl.load(in_ptr0 + (x0), xmask)
    tmp1 = tl.full([1], 0, tl.int32)
    tmp2 = triton_helpers.maximum(tmp1, tmp0)
    tl.store(out_ptr0 + (x0), tmp2, xmask)


class ModelNew(torch.nn.Module):
    def __init__(self):
        super(ModelNew, self).__init__()  # noqa: UP008 - KernelBench style, tests the rename

    def forward(self, x):
        out = torch.empty_like(x)
        xnumel = x.numel()
        triton_poi_fused_relu_0[(triton.cdiv(xnumel, 1024),)](x, out, xnumel, XBLOCK=1024)
        return out
