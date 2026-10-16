#!/usr/bin/env python3
"""LM2 code grader: run model-written programs against LiveCodeBench tests, CPU only, sandboxed.

This is the only place in LM2 where model output is executed. It must run inside the locked-down
container that ``program/evidence/2026-10-16/lm2-resident-eval/ops/lm2-code-sandbox.sbatch``
starts: runc runtime with no GPU devices, ``--network none``, a read-only root, a size-capped
tmpfs, all capabilities dropped, no-new-privileges, an unprivileged user, and pid, memory and CPU
limits, in a CPU-only Slurm job. The grader refuses to start if it can see a GPU device node or a
network interface other than loopback.

Inside, each program runs in its own temporary directory as a child process with rlimits (address
space, CPU time, file size, open files, no core files) and a wall-clock timeout per test (6 s,
LiveCodeBench's default). Tests run in order and the first failure stops a program, as in
LiveCodeBench. The grader marks itself non-dumpable, so a child cannot reach its file descriptors
through /proc, and it writes verdicts only to its own stdout; children write to pipes it reads.

Input: JSONL rows {key, item_id, testtype, func_name, code, tests: [{input, output}]}.
Output (stdout): JSONL rows {key, item_id, passed, tests, passed_tests, failure, elapsed_s}.
"""

from __future__ import annotations

import argparse
import contextlib
import ctypes
import json
import multiprocessing
import os
import resource
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.lm2_resident_eval import functional_match, stdio_match  # noqa: E402

# LiveCodeBench's import preamble (lcb_runner/evaluation/testing_util.py).
IMPORTS = (
    "from string import *\nfrom re import *\nfrom datetime import *\nfrom collections import *\n"
    "from heapq import *\nfrom bisect import *\nfrom copy import *\nfrom math import *\n"
    "from random import *\nfrom statistics import *\nfrom itertools import *\n"
    "from functools import *\nfrom operator import *\nfrom io import *\nfrom sys import *\n"
    "from json import *\nfrom builtins import *\nfrom typing import *\nimport string\nimport re\n"
    "import datetime\nimport collections\nimport heapq\nimport bisect\nimport copy\nimport math\n"
    "import random\nimport statistics\nimport itertools\nimport functools\nimport operator\n"
    "import io\nimport sys\nimport json\nsys.setrecursionlimit(50000)\n"
)
# A call-based test: load the program, find Solution.<func_name>, call it on the JSON arguments
# from stdin and print the JSON result between markers (stdout noise from the program is ignored).
CALL_HARNESS = r"""
import json, sys
sys.setrecursionlimit(50000)
_src = open(sys.argv[1], encoding="utf-8").read()
_ns = {"__name__": "__lm2_solution__"}
exec(compile(_src, "solution.py", "exec"), _ns)
_args = json.loads(sys.stdin.read())
_cls = _ns.get("Solution")
_fn = getattr(_cls(), sys.argv[2]) if _cls is not None else _ns[sys.argv[2]]
_out = _fn(*_args)
if isinstance(_out, tuple):
    _out = list(_out)
sys.stdout.write("\n@@LM2_RESULT@@" + json.dumps(_out) + "@@LM2_END@@\n")
"""
MARK_START, MARK_END = "@@LM2_RESULT@@", "@@LM2_END@@"
MAX_OUTPUT_BYTES = 32 * 1024 * 1024


def assert_sandbox() -> dict[str, Any]:
    """Refuse to run where a GPU device node or a non-loopback interface is visible."""

    gpu_nodes = sorted(str(p) for p in Path("/dev").glob("nvidia*"))
    gpu_nodes += sorted(str(p) for p in Path("/dev").glob("dri/*"))
    interfaces = (
        sorted(p.name for p in Path("/sys/class/net").glob("*"))
        if Path("/sys/class/net").is_dir()
        else []
    )
    if gpu_nodes:
        raise SystemExit(f"sandbox check failed: GPU device nodes visible {gpu_nodes}")
    if any(name != "lo" for name in interfaces):
        raise SystemExit(f"sandbox check failed: network interfaces {interfaces}")
    if os.getuid() == 0:
        raise SystemExit("sandbox check failed: running as root")
    return {"gpu_nodes": gpu_nodes, "interfaces": interfaces, "uid": os.getuid()}


def make_non_dumpable() -> None:
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        libc.prctl(4, 0, 0, 0, 0)  # PR_SET_DUMPABLE = 4
    except (OSError, AttributeError):
        pass


def _limits(cpu_s: int, mem_bytes: int) -> Any:
    strict = sys.platform.startswith("linux")  # the sandbox; macOS only runs the unit tests

    def apply() -> None:
        os.setsid()
        for limit, value in (
            (resource.RLIMIT_CPU, (cpu_s, cpu_s + 1)),
            (resource.RLIMIT_AS, (mem_bytes, mem_bytes)),
            (resource.RLIMIT_FSIZE, (64 << 20, 64 << 20)),
            (resource.RLIMIT_NOFILE, (64, 64)),
            (resource.RLIMIT_CORE, (0, 0)),
        ):
            try:
                resource.setrlimit(limit, value)
            except (ValueError, OSError):
                if strict:
                    raise

    return apply


def run_child(
    argv: list[str], stdin: str, cwd: str, timeout_s: float, mem_bytes: int
) -> tuple[str, str, int | None, bool]:
    """Run one child; return (stdout, stderr tail, returncode, timed_out)."""

    env = {
        "PATH": "/usr/bin:/bin",
        "PYTHONHASHSEED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
        "HOME": cwd,
        "TMPDIR": cwd,
        "LANG": "C.UTF-8",
    }
    proc = subprocess.Popen(
        argv,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        env=env,
        preexec_fn=_limits(int(timeout_s) + 1, mem_bytes),
        close_fds=True,
    )
    timed_out = False
    try:
        out, err = proc.communicate(stdin.encode("utf-8"), timeout=timeout_s)
    except subprocess.TimeoutExpired:
        timed_out = True
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGKILL)
        out, err = proc.communicate()
    finally:
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(proc.pid, signal.SIGKILL)
    return (
        out[:MAX_OUTPUT_BYTES].decode("utf-8", "replace"),
        err[-2000:].decode("utf-8", "replace"),
        proc.returncode,
        timed_out,
    )


def grade_one(row: dict[str, Any], timeout_s: float, mem_bytes: int) -> dict[str, Any]:
    started = time.monotonic()
    verdict: dict[str, Any] = {
        "key": row["key"],
        "item_id": row["item_id"],
        "passed": False,
        "tests": len(row["tests"]),
        "passed_tests": 0,
        "failure": None,
    }
    code = row.get("code") or ""
    if not code.strip():
        verdict.update(failure="no_code", elapsed_s=0.0)
        return verdict
    with tempfile.TemporaryDirectory(prefix="lm2-") as work:
        program = Path(work) / "solution.py"
        program.write_text(IMPORTS + "\n" + code, encoding="utf-8")
        harness = Path(work) / "call_harness.py"
        harness.write_text(CALL_HARNESS, encoding="utf-8")
        for test in row["tests"]:
            if row["testtype"] == "functional":
                try:
                    args = [json.loads(line) for line in test["input"].split("\n") if line.strip()]
                except json.JSONDecodeError:
                    verdict["failure"] = "bad_test_input"
                    break
                argv = [sys.executable, "-I", str(harness), str(program), row["func_name"]]
                out, _err, code_rc, timed_out = run_child(
                    argv, json.dumps(args), work, timeout_s, mem_bytes
                )
                if timed_out:
                    verdict["failure"] = "timeout"
                    break
                if code_rc != 0 or MARK_START not in out:
                    verdict["failure"] = "runtime_error"
                    break
                result = out.rsplit(MARK_START, 1)[1].split(MARK_END, 1)[0]
                if not functional_match(result, test["output"]):
                    verdict["failure"] = "wrong_answer"
                    break
            else:
                argv = [sys.executable, "-I", str(program)]
                out, _err, code_rc, timed_out = run_child(
                    argv, test["input"], work, timeout_s, mem_bytes
                )
                if timed_out:
                    verdict["failure"] = "timeout"
                    break
                if code_rc != 0:
                    verdict["failure"] = "runtime_error"
                    break
                if not stdio_match(out, test["output"]):
                    verdict["failure"] = "wrong_answer"
                    break
            verdict["passed_tests"] += 1
    verdict["passed"] = verdict["failure"] is None and verdict["passed_tests"] == verdict["tests"]
    verdict["elapsed_s"] = round(time.monotonic() - started, 2)
    return verdict


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--timeout-s", type=float, default=6.0)
    parser.add_argument("--mem-gb", type=float, default=4.0)
    parser.add_argument("--skip-sandbox-check", action="store_true", help="unit tests only")
    args = parser.parse_args(argv)
    info = {} if args.skip_sandbox_check else assert_sandbox()
    make_non_dumpable()
    rows = [
        json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line
    ]
    print(
        json.dumps({"sandbox": info, "rows": len(rows), "workers": args.workers}), file=sys.stderr
    )
    mem = int(args.mem_gb * (1 << 30))
    jobs = [(row, args.timeout_s, mem) for row in rows]
    # Forked, single-threaded workers (preexec_fn is not safe under threads). They inherit the
    # non-dumpable flag; the programs they exec do not.
    with multiprocessing.get_context("fork").Pool(args.workers) as pool:
        for verdict in pool.imap(_grade_star, jobs, chunksize=1):
            sys.stdout.write(json.dumps(verdict, sort_keys=True) + "\n")
            sys.stdout.flush()
    return 0


def _grade_star(job: tuple[dict[str, Any], float, int]) -> dict[str, Any]:
    return grade_one(*job)


if __name__ == "__main__":
    sys.exit(main())
