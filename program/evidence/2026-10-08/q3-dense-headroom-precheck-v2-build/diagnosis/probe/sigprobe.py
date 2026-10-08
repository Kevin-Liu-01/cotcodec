"""Diagnostic (CPU): which import or compile step changes the OS-level SIGUSR1 disposition."""
import ctypes
import ctypes.util
import os
import signal
import sys
import time
import traceback

libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)


class Sigaction(ctypes.Structure):
    _fields_ = [("sa_handler", ctypes.c_void_p), ("sa_mask", ctypes.c_ulong * 16),
                ("sa_flags", ctypes.c_int), ("sa_restorer", ctypes.c_void_p)]


def os_handler(signum=signal.SIGUSR1):
    old = Sigaction()
    if libc.sigaction(signum, None, ctypes.byref(old)) != 0:
        return "err"
    return old.sa_handler or 0


def masks():
    out = {}
    with open("/proc/self/status") as fh:
        for line in fh:
            if line.startswith(("SigBlk", "SigIgn", "SigCgt")):
                key, val = line.split(":")
                out[key] = int(val.strip(), 16)
    return out


def bit(mask, signum):
    return (mask >> (signum - 1)) & 1


received = []
signal.signal(signal.SIGUSR1, lambda s, f: received.append(s))
signal.signal(signal.SIGTERM, lambda s, f: received.append(s))
PY = os_handler()
PYT = os_handler(signal.SIGTERM)
print(f"pid={os.getpid()} python_handler_addr=0x{PY:x} term=0x{PYT:x}", flush=True)


def report(step):
    m = masks()
    h, t = os_handler(), os_handler(signal.SIGTERM)
    tasks = os.listdir("/proc/self/task")
    blocked = 0
    for tid in tasks:
        try:
            with open(f"/proc/self/task/{tid}/status") as fh:
                for line in fh:
                    if line.startswith("SigBlk") and bit(int(line.split(":")[1].strip(), 16), 10):
                        blocked += 1
        except OSError:
            pass
    print(f"{step:40s} usr1_os=0x{h:x} same={h == PY} term_same={t == PYT} "
          f"cgt={bit(m['SigCgt'], 10)} ign={bit(m['SigIgn'], 10)} blk_main={bit(m['SigBlk'], 10)} "
          f"threads={len(tasks)} threads_blocking_usr1={blocked} "
          f"py_getsignal={'ours' if callable(signal.getsignal(signal.SIGUSR1)) else signal.getsignal(signal.SIGUSR1)}",
          flush=True)


def step(name, fn):
    t0 = time.time()
    try:
        fn()
        status = "ok"
    except Exception as exc:  # noqa: BLE001
        status = f"FAILED {type(exc).__name__}: {exc}"[:300]
    report(f"{name} ({time.time() - t0:.1f}s) {status}"[:40])
    if status != "ok":
        print("   ", status, flush=True)


report("start")
step("import torch", lambda: __import__("torch"))
step("import transformers", lambda: __import__("transformers"))
step("import triton", lambda: __import__("triton"))
step("import tilelang", lambda: __import__("tilelang"))
step("import fla", lambda: __import__("fla"))


def qwen35():
    from transformers.models.qwen3_5 import modeling_qwen3_5 as m
    fn = m.torch_chunk_gated_delta_rule
    impl = None
    for cell in (getattr(fn, "__closure__", None) or ()):
        try:
            v = cell.cell_contents
        except ValueError:
            continue
        if callable(v) and getattr(v, "__module__", "").startswith(("fla", "transformers")):
            impl = v
    seen = []
    f = fn
    while f is not None and len(seen) < 6:
        seen.append(f"{getattr(f, '__module__', '?')}.{getattr(f, '__qualname__', '?')}")
        cl = getattr(f, "__closure__", None) or ()
        nxt = None
        for cell in cl:
            try:
                v = cell.cell_contents
            except ValueError:
                continue
            if callable(v) and v is not f and hasattr(v, "__module__"):
                if v.__module__ and (v.__module__.startswith("fla") or "qwen3_5" in v.__module__):
                    nxt = v
        f = nxt
    print("    chunk_gated_delta_rule chain:", seen, flush=True)
    fn = m.torch_recurrent_gated_delta_rule
    print("    recurrent:", [getattr(c.cell_contents, "__module__", None) for c in (fn.__closure__ or ()) if callable(getattr(c, "cell_contents", None))], flush=True)
    print("    conv1d_fn:", [getattr(c.cell_contents, "__module__", None) for c in (m.causal_conv1d_fn.__closure__ or ()) if callable(getattr(c, "cell_contents", None))], flush=True)


step("import modeling_qwen3_5", qwen35)
step("import torch._dynamo", lambda: __import__("torch._dynamo"))


def triton_compile():
    import triton
    import triton.language as tl
    from triton.backends.compiler import GPUTarget

    @triton.jit
    def add(x, y, out, n, BLOCK: tl.constexpr):
        i = tl.program_id(0) * BLOCK + tl.arange(0, BLOCK)
        tl.store(out + i, tl.load(x + i, mask=i < n) + tl.load(y + i, mask=i < n), mask=i < n)

    src = triton.compiler.ASTSource(fn=add, signature={"x": "*fp32", "y": "*fp32", "out": "*fp32",
                                                        "n": "i32", "BLOCK": "constexpr"},
                                    constexprs={"BLOCK": 64})
    triton.compile(src, target=GPUTarget("cuda", 90, 32))


step("triton.compile sm90 (no GPU)", triton_compile)


def tilelang_compile():
    import tilelang
    import tilelang.language as T

    @tilelang.jit(target="cuda", execution_backend="cython")
    def k(N: int = 128):
        @T.prim_func
        def main(A: T.Tensor((N,), "float32"), B: T.Tensor((N,), "float32")):
            with T.Kernel(1, threads=128) as bx:
                for i in T.Parallel(N):
                    B[i] = A[i] + 1.0
        return main

    k()


step("tilelang.jit compile cuda (no GPU)", tilelang_compile)
os.kill(os.getpid(), signal.SIGUSR1)
time.sleep(0.2)
print("self-sent SIGUSR1 seen by python handler:", signal.SIGUSR1 in received, flush=True)
