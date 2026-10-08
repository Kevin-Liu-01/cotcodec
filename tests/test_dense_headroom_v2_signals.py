"""SIGUSR1/SIGTERM in q3-dense-headroom-precheck-v2 (torch-free).

Job 730 (v1, Qwen3.5-4B-Base) ignored Slurm's SIGUSR1: Triton's LLVM replaced
CPython's OS-level handler at the first kernel compile, and LLVM's handler for
SIGUSR1 swallows it. These tests replace the OS-level disposition behind
CPython's back (libc ``signal(SIGUSR1, SIG_IGN)``, the stand-in available on
every platform) and check that v2's guard still sees the signal, in this
process and in a child process that starts the way the entry point does.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import json
import os
import signal
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

from harness import dense_headroom_v2 as dv2

PROJECT_ROOT = Path(__file__).resolve().parents[1]
POSIX = pytest.mark.skipif(not hasattr(signal, "pthread_sigmask"), reason="POSIX signals")


def _libc_ignore(signum: int) -> None:
    name = ctypes.util.find_library("c")
    libc = ctypes.CDLL(name) if name else ctypes.CDLL(None)
    libc.signal.restype = ctypes.c_void_p
    libc.signal.argtypes = [ctypes.c_int, ctypes.c_void_p]
    libc.signal(int(signum), ctypes.c_void_p(1))  # SIG_IGN


CHILD = textwrap.dedent("""
    import signal, sys, time, json, ctypes, ctypes.util
    if MODE == "v2":
        signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGUSR1, signal.SIGTERM})
    sys.path.insert(0, ROOT)
    from harness import dense_headroom_v2 as dv2
    received = []
    if MODE == "v2":
        guard = dv2.SignalGuard()
        guard.install()
    else:  # v1: a CPython handler and a flag, as harness.sparse_indexer_k1_runtime.SignalFlag
        signal.signal(signal.SIGUSR1, lambda s, f: received.append("SIGUSR1"))
    name = ctypes.util.find_library("c")
    libc = ctypes.CDLL(name) if name else ctypes.CDLL(None)
    libc.signal.restype = ctypes.c_void_p
    libc.signal.argtypes = [ctypes.c_int, ctypes.c_void_p]
    libc.signal(int(signal.SIGUSR1), ctypes.c_void_p(1))  # a library replaces the handler
    print("ready", flush=True)
    deadline = time.time() + 4
    got = None
    while time.time() < deadline and got is None:
        time.sleep(0.05)
        got = guard.poll("loop") if MODE == "v2" else (received[0] if received else None)
    report = guard.as_dict() if MODE == "v2" else {}
    print(json.dumps({"got": got, "guard": report}), flush=True)
""")


def _run_child(mode: str) -> dict:
    code = f"MODE = {mode!r}\nROOT = {str(PROJECT_ROOT)!r}\n" + CHILD
    process = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True)
    assert process.stdout is not None
    assert process.stdout.readline().strip() == "ready"
    time.sleep(0.2)
    os.kill(process.pid, signal.SIGUSR1)
    out, err = process.communicate(timeout=30)
    return json.loads(out.strip().splitlines()[-1])


@POSIX
def test_a_replaced_handler_swallows_usr1_without_the_guard() -> None:
    # The job-730 failure, reproduced: CPython's handler is installed, a native
    # library replaces the OS-level disposition, SIGUSR1 never reaches Python.
    assert _run_child("v1")["got"] is None


@POSIX
def test_the_guard_sees_usr1_after_its_handler_was_replaced() -> None:
    result = _run_child("v2")
    assert result["got"] == "SIGUSR1"
    assert result["guard"]["blocked_in_every_thread_from_start"] is True
    assert result["guard"]["via"] == "pending"


@POSIX
def test_poll_restores_a_replaced_handler_and_records_it() -> None:
    previous = {s: signal.getsignal(s) for s in dv2.GUARDED_SIGNALS}
    old_mask = signal.pthread_sigmask(signal.SIG_BLOCK, set(dv2.GUARDED_SIGNALS))
    try:
        guard = dv2.SignalGuard()
        guard.install()
        reference = dv2.os_handler_address(signal.SIGUSR1)
        _libc_ignore(signal.SIGUSR1)
        if reference is not None:
            assert dv2.os_handler_address(signal.SIGUSR1) != reference
        assert guard.poll("after-replacement") is None
        if reference is not None:
            assert dv2.os_handler_address(signal.SIGUSR1) == reference
            assert guard.as_dict()["handler_replacement_count"] == 1
        os.kill(os.getpid(), signal.SIGUSR1)
        assert guard.poll("after-signal") == "SIGUSR1"
        os.kill(os.getpid(), signal.SIGTERM)
        guard.poll("again")
        assert guard.received == "SIGUSR1"  # the first signal is kept
        assert not (signal.sigpending() & set(dv2.GUARDED_SIGNALS))
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)
        for signum, handler in previous.items():
            signal.signal(signum, handler)


def test_the_entry_point_blocks_the_signals_before_any_import() -> None:
    source = (PROJECT_ROOT / "scripts" / "run_dense_headroom_precheck_v2.py").read_text()
    body = source[source.index('"""', source.index('"""') + 3) + 3:]
    first_import = body.index("\nimport argparse")
    assert "pthread_sigmask" in body[:first_import]
    assert "SIGUSR1" in body[:first_import] and "SIGTERM" in body[:first_import]
    lines = [line for line in body[:first_import].splitlines()
             if line.startswith(("import ", "from "))]
    assert lines == ["from __future__ import annotations", "import signal as _signal"]
