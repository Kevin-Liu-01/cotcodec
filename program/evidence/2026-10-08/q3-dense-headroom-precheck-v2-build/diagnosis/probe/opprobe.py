"""Diagnostic (CPU): per-op Python overhead before and after importing the 4B lane's libraries."""
import sys
import time

import torch


def per_op(n=20000):
    x = torch.ones(8)
    y = torch.ones(8)
    for _ in range(200):
        x = x + y
    t0 = time.perf_counter()
    for _ in range(n):
        x = torch.add(x, y)
        x = x.mul(1.0)
    return (time.perf_counter() - t0) / (2 * n) * 1e6


def state(label):
    from torch.overrides import _get_current_function_mode_stack
    try:
        from torch.utils._python_dispatch import _get_current_dispatch_mode_stack
        dispatch = _get_current_dispatch_mode_stack()
    except Exception as exc:  # noqa: BLE001
        dispatch = f"err {exc}"
    print(f"{label:34s} per-op {per_op():6.2f} us | fn-modes {_get_current_function_mode_stack()} "
          f"| dispatch-modes {dispatch} | anomaly {torch.is_anomaly_enabled()} "
          f"| det {torch.are_deterministic_algorithms_enabled()} "
          f"warn_only {torch.is_deterministic_algorithms_warn_only_enabled()} "
          f"| grad {torch.is_grad_enabled()} | profiler {torch.autograd.profiler._is_profiler_enabled} "
          f"| default_device {torch.get_default_device()}", flush=True)


state("torch only")
torch.use_deterministic_algorithms(True)
state("deterministic strict")
torch.use_deterministic_algorithms(True, warn_only=True)
state("deterministic warn_only")
torch.use_deterministic_algorithms(True)
import transformers  # noqa: E402,F401
state("+ transformers")
import triton  # noqa: E402,F401
state("+ triton")
import tilelang  # noqa: E402,F401
state("+ tilelang")
import fla  # noqa: E402,F401
state("+ fla")
from transformers.models.qwen3_5 import modeling_qwen3_5  # noqa: E402,F401
state("+ modeling_qwen3_5")
torch.use_deterministic_algorithms(True, warn_only=True)
state("+ warn_only")
import torch._dynamo  # noqa: E402,F401
state("+ torch._dynamo")
print("sys.setprofile:", sys.getprofile(), "settrace:", sys.gettrace())
