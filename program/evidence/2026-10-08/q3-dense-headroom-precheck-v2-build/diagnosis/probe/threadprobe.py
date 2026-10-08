"""Diagnostic (CPU): Python threads and per-thread CPU after the 4B lane's imports and a model load."""
import os, sys, threading, time
sys.path.insert(0, sys.argv[1])


def snapshot(label):
    ticks = {}
    for tid in os.listdir("/proc/self/task"):
        try:
            stat = open(f"/proc/self/task/{tid}/stat").read()
            name = open(f"/proc/self/task/{tid}/comm").read().strip()
            fields = stat.rsplit(")", 1)[1].split()
            ticks[tid] = (name, int(fields[11]) + int(fields[12]))
        except OSError:
            pass
    return ticks


def report(label):
    a = snapshot(label)
    time.sleep(3)
    b = snapshot(label)
    busy = {tid: (b[tid][0], b[tid][1] - a[tid][1]) for tid in b if tid in a and b[tid][1] - a[tid][1] > 5}
    print(f"{label}: native threads {len(b)}; python threads {[t.name for t in threading.enumerate()]}; "
          f"busy over 3 s (ticks): {busy}", flush=True)


report("start")
import torch  # noqa: E402
report("torch")
import transformers  # noqa: E402
from transformers.models.qwen3_5 import modeling_qwen3_5  # noqa: E402,F401  (imports fla)
report("qwen3_5+fla")
from scripts import run_dense_headroom_precheck_doctor as d1  # noqa: E402
from harness import sparse_indexer_torch as sit  # noqa: E402
import tempfile  # noqa: E402
from pathlib import Path  # noqa: E402
tmp = Path(tempfile.mkdtemp())
# make_tiny_hybrid blocks fla only if not yet imported; it is imported already.
path = d1.make_tiny_hybrid(tmp / "h")
model = sit.load_teacher(path, "cpu")
report("after load_teacher (tqdm bars)")
print("sys.getswitchinterval", sys.getswitchinterval())
