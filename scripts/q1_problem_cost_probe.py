#!/usr/bin/env python3
"""CPU cost covariates per KernelBench problem (GPU-less container; no candidate code).

For each pinned problem, in its own process: the seconds of one native
``get_inputs()`` (KernelBench's CPU tensors) and of one fp32 reference forward
pass on the CPU (the audit and gate (c)'s validity gate compute CPU references),
with the problem's native input bytes. These are covariates for the pilot cost
card: on the H100 the gates spend most of a large problem's item time in this
CPU work, not in GPU kernels.

    python scripts/q1_problem_cost_probe.py --out probe.json [--jobs 4] [--threads 12]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

ONE = r"""
import json, sys, time
import torch
from harness.q1 import problems
from harness.q1.gates.common import load_reference, set_seed
pid = sys.argv[1]
source = problems.load_problem_source(pid)
Model, get_init_inputs, get_inputs = load_reference(source)
set_seed(42)
init = get_init_inputs()
set_seed(42)
model = Model(*init)
t0 = time.perf_counter()
set_seed(42)
inputs = get_inputs()
t1 = time.perf_counter()
nbytes = sum(x.numel() * x.element_size() for x in inputs if torch.is_tensor(x))
print(json.dumps({"problem_id": pid, "get_inputs_seconds": round(t1 - t0, 3),
                  "input_bytes": nbytes}), flush=True)
with torch.no_grad():
    t2 = time.perf_counter()
    model(*inputs)
    t3 = time.perf_counter()
print(json.dumps({"problem_id": pid, "get_inputs_seconds": round(t1 - t0, 3),
                  "cpu_forward_seconds": round(t3 - t2, 3), "input_bytes": nbytes}), flush=True)
"""


def probe(problem_id: str, threads: int, timeout: float) -> dict:
    env = {
        **os.environ,
        "OMP_NUM_THREADS": str(threads),
        "MKL_NUM_THREADS": str(threads),
        "PYTHONPATH": str(PROJECT_ROOT),
        "CUDA_VISIBLE_DEVICES": "",
    }
    start = time.perf_counter()
    try:
        done = subprocess.run(
            [sys.executable, "-c", ONE, problem_id],
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout,
            check=False,
        )
        lines = [line for line in done.stdout.splitlines() if line.startswith("{")]
        row = json.loads(lines[-1]) if lines else {"problem_id": problem_id}
        if done.returncode != 0:
            row["error"] = done.stderr[-400:]
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        lines = [line for line in out.splitlines() if line.startswith("{")]
        row = json.loads(lines[-1]) if lines else {"problem_id": problem_id}
        row["cpu_forward_seconds"] = None
        row["timeout_seconds"] = timeout
    row["process_seconds"] = round(time.perf_counter() - start, 3)
    return row


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--threads", type=int, default=12)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--problems", nargs="*")
    args = parser.parse_args(argv)
    from harness.q1 import problems

    ids = args.problems or problems.list_problem_ids()
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        rows = []
        for row in pool.map(lambda pid: probe(pid, args.threads, args.timeout), ids):
            rows.append(row)
            print(json.dumps(row), flush=True)
    args.out.write_text(
        json.dumps(
            {"schema": "q1-problem-cost-probe/1", "threads": args.threads, "rows": rows},
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
