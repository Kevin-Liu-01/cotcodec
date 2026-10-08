"""Diagnostic (CPU): which gated-delta implementation transformers resolves in the image."""
import importlib.util
import inspect
import os
import time

t0 = time.time()
import transformers  # noqa: E402
from transformers.utils import import_utils  # noqa: E402

print("kernels package:", importlib.util.find_spec("kernels") is not None)
print("causal_conv1d package:", importlib.util.find_spec("causal_conv1d") is not None)
print("flash_qla:", importlib.util.find_spec("flash_qla") is not None)
try:
    import fla  # noqa: F401
    print("import fla: ok", fla.__file__)
except Exception as exc:  # noqa: BLE001
    import traceback
    traceback.print_exc()
    print("import fla FAILED:", repr(exc))
from transformers.models.qwen3_5 import modeling_qwen3_5 as m  # noqa: E402


def resolved(fn):
    out = []
    for cell in fn.__closure__ or ():
        try:
            v = cell.cell_contents
        except ValueError:
            continue
        if callable(v):
            out.append(f"{getattr(v, '__module__', '?')}.{getattr(v, '__qualname__', '?')}")
            inner = getattr(v, "__closure__", None) or ()
            for c2 in inner:
                try:
                    w = c2.cell_contents
                except ValueError:
                    continue
                if callable(w):
                    out.append("  -> " + f"{getattr(w, '__module__', '?')}.{getattr(w, '__qualname__', '?')}")
    return out


for name in ("torch_chunk_gated_delta_rule", "torch_recurrent_gated_delta_rule", "causal_conv1d_fn",
             "causal_conv1d_update"):
    print(name, resolved(getattr(m, name)))
print("Qwen3_5GatedDeltaNet.forward from", inspect.getsourcefile(m.Qwen3_5GatedDeltaNet.forward))
print("RMSNormGated:", m.Qwen3_5RMSNormGated, m.Qwen3_5RMSNormGated.forward.__module__)
print(f"done in {time.time() - t0:.1f}s")
