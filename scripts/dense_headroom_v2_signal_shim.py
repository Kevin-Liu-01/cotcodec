#!/usr/bin/env python3
"""Run a dense pre-check entry point with job 730's signal hazard reproduced (tests only).

Slurm 730 (v1, Qwen3.5-4B-Base) ignored SIGUSR1: flash-linear-attention's
Triton kernels compile inside the model's first forward, and Triton's LLVM
installs process-wide signal handlers at that moment, replacing CPython's
OS-level handler; LLVM's handler for SIGUSR1 swallows it. This shim runs the
entry point (``runpy``, in this process, so it keeps the process's PID, PID 1
in a container) and, at the start of the first forward of the model returned
by ``harness.sparse_indexer_torch.load_teacher``, does what fla's first
compile does:

* ``--mode triton``: compile a small Triton kernel for an sm_90 target (no GPU
  is needed to compile), which registers LLVM's handlers exactly as in 730;
* ``--mode ignore``: set SIGUSR1's OS-level disposition to SIG_IGN through
  libc behind CPython's back (a stand-in where Triton is not installed: the
  signal is discarded the same way, and ``signal.getsignal`` still reports
  CPython's handler).

The shim imports only the standard library before the entry point runs, so
the entry point's own first lines still run before any thread exists. It
writes what it did to ``$COTCODEC_SHIM_REPORT`` (JSON) when that is set.

Usage: ``python scripts/dense_headroom_v2_signal_shim.py --mode triton -- ENTRY.py ARGS...``
"""

from __future__ import annotations

import ctypes
import ctypes.util
import importlib.abc
import importlib.machinery
import json
import os
import runpy
import signal
import sys
from typing import Any

TARGET_MODULE = "harness.sparse_indexer_torch"
REPORT: dict[str, Any] = {"mode": None, "displaced": False, "pid": os.getpid()}


def _handler_address(signum: int) -> int | None:
    name = ctypes.util.find_library("c")
    libc = ctypes.CDLL(name) if name else ctypes.CDLL(None)
    buffer = ctypes.create_string_buffer(512)
    if libc.sigaction(int(signum), None, buffer) != 0:
        return None
    return int(ctypes.c_void_p.from_buffer(buffer).value or 0)


def _write_report() -> None:
    path = os.environ.get("COTCODEC_SHIM_REPORT")
    if path:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(REPORT, handle, indent=2, sort_keys=True)


def _triton_compile() -> None:
    import triton
    import triton.language as tl
    from triton.backends.compiler import GPUTarget

    @triton.jit
    def _add(x, y, out, n, block: tl.constexpr):
        offsets = tl.program_id(0) * block + tl.arange(0, block)
        mask = offsets < n
        tl.store(out + offsets, tl.load(x + offsets, mask=mask) + tl.load(y + offsets, mask=mask),
                 mask=mask)

    source = triton.compiler.ASTSource(
        fn=_add, signature={"x": "*fp32", "y": "*fp32", "out": "*fp32", "n": "i32",
                            "block": "constexpr"}, constexprs={"block": 64})
    triton.compile(source, target=GPUTarget("cuda", 90, 32))


def _displace(mode: str) -> None:
    before = {s.name: _handler_address(s) for s in (signal.SIGUSR1, signal.SIGTERM)}
    if mode == "triton":
        _triton_compile()
    else:
        name = ctypes.util.find_library("c")
        libc = ctypes.CDLL(name) if name else ctypes.CDLL(None)
        libc.signal.restype = ctypes.c_void_p
        libc.signal.argtypes = [ctypes.c_int, ctypes.c_void_p]
        libc.signal(int(signal.SIGUSR1), ctypes.c_void_p(1))  # SIG_IGN
    after = {s.name: _handler_address(s) for s in (signal.SIGUSR1, signal.SIGTERM)}
    REPORT.update({"before": {k: hex(v or 0) for k, v in before.items()},
                   "after": {k: hex(v or 0) for k, v in after.items()},
                   "displaced": after["SIGUSR1"] != before["SIGUSR1"],
                   "python_getsignal_unchanged": callable(signal.getsignal(signal.SIGUSR1))})
    _write_report()


def _patch(module: Any, mode: str) -> None:
    original = module.load_teacher

    def load_teacher(*args: Any, **kwargs: Any) -> Any:
        model = original(*args, **kwargs)
        state: dict[str, Any] = {}

        def first_forward(_module: Any, _args: Any) -> None:
            state["handle"].remove()
            _displace(mode)

        state["handle"] = model.register_forward_pre_hook(first_forward)
        return model

    module.load_teacher = load_teacher


class _Finder(importlib.abc.MetaPathFinder):
    def __init__(self, mode: str) -> None:
        self.mode = mode

    def find_spec(self, fullname: str, path: Any, target: Any = None) -> Any:
        if fullname != TARGET_MODULE:
            return None
        spec = importlib.machinery.PathFinder.find_spec(fullname, path)
        if spec is None or spec.loader is None:
            return spec
        loader = spec.loader
        execute = loader.exec_module
        mode = self.mode

        def exec_module(module: Any) -> None:
            execute(module)
            _patch(module, mode)

        loader.exec_module = exec_module  # type: ignore[method-assign]
        return spec


def main() -> None:
    argv = sys.argv[1:]
    if len(argv) < 4 or argv[0] != "--mode" or argv[1] not in ("triton", "ignore") \
            or argv[2] != "--":
        raise SystemExit("usage: dense_headroom_v2_signal_shim.py --mode triton|ignore -- "
                         "ENTRY.py ARGS...")
    mode, entry = argv[1], argv[3]
    REPORT["mode"] = mode
    _write_report()
    sys.meta_path.insert(0, _Finder(mode))
    sys.argv = [entry, *argv[4:]]
    project = os.path.dirname(os.path.dirname(os.path.abspath(entry)))
    if project not in sys.path:
        sys.path.insert(0, project)
    runpy.run_path(entry, run_name="__main__")


if __name__ == "__main__":
    main()
