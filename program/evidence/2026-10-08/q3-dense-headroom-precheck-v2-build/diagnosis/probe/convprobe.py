"""Diagnostic (CPU): which convolution backend torch selects for Qwen3.5-4B's depthwise conv1d."""
import torch
from torch._subclasses.fake_tensor import FakeTensorMode

print("torch", torch.__version__, "cudnn compiled", torch.backends.cudnn.is_available(),
      "cudnn version", torch.backends.cudnn.version() if torch.backends.cudnn.is_available() else None)
for dtype in (torch.bfloat16, torch.float16):
    try:
        with FakeTensorMode(allow_non_fake_inputs=True):
            x = torch.empty(1, 8192, 6007, dtype=dtype, device="cuda")
            w = torch.empty(8192, 1, 4, dtype=dtype, device="cuda")
            backend = torch._C._select_conv_backend(x, w, None, [1], [3], [1], False, [0], 8192, None)
        print(dtype, "3d input ->", backend)
    except Exception as exc:  # noqa: BLE001
        print(dtype, "3d failed:", type(exc).__name__, str(exc)[:300])
    try:
        with FakeTensorMode(allow_non_fake_inputs=True):
            x = torch.empty(1, 8192, 1, 6007, dtype=dtype, device="cuda")
            w = torch.empty(8192, 1, 1, 4, dtype=dtype, device="cuda")
            backend = torch._C._select_conv_backend(x, w, None, [1, 1], [0, 3], [1, 1], False, [0, 0], 8192, None)
        print(dtype, "4d input ->", backend)
    except Exception as exc:  # noqa: BLE001
        print(dtype, "4d failed:", type(exc).__name__, str(exc)[:300])
