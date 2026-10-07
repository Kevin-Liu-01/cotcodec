"""A4 GPU probes: dual-poison allocator runs and compute-sanitizer memcheck.

Both run the candidate once in a fresh child process of the A4 worker (so the
runner's watchdog, which kills the worker's process group, covers them):

- ``poison``: the child installs ``libq1_poison_alloc.so`` as a
  ``CUDAPluggableAllocator`` before any CUDA allocation, with poison byte 0x00
  in one child and 0xFF in the other, runs the candidate on the first A1 draw
  and writes the SHA-256 of its output bytes. Different hashes mean the
  candidate returned bytes it never wrote.
- ``sanitizer``: the child runs under ``compute-sanitizer --tool memcheck`` on
  the smallest A3 configuration (by input bytes). Exit code 86 means memcheck
  found an error.

    python -m harness.q1.audit.gpu_probes poison ITEM.json OUT.json
    python -m harness.q1.audit.gpu_probes sanitizer ITEM.json OUT.json
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from harness.q1.audit.contracts import (
    POISON_BYTES,
    interpret_sanitizer,
    poison_allocator_env,
    sanitizer_command,
)
from harness.q1.gates.outcome import GateOutcome

SO_ENV = "Q1_POISON_ALLOC_SO_PATH"
PROBE_TIMEOUT_S = 170.0


def _child(mode: str, item_path: Path, out_path: Path) -> int:
    """Child body: allocator first (poison mode), then import torch and run once."""
    if mode == "poison":
        from harness.q1.audit.contracts import install_poison_allocator_from_env

        if install_poison_allocator_from_env() is None:
            raise SystemExit("poison child needs Q1_POISON_BYTE and Q1_POISON_ALLOC_SO")
    import torch

    from harness.q1 import problems as problem_lib
    from harness.q1.audit import run as audit
    from harness.q1.gates.common import first_tensor_outputs, load_reference
    from harness.q1.gates.outcome import channel_seed

    item = json.loads(item_path.read_text(encoding="utf-8"))
    problem_id = item["problem_id"]
    if item.get("problem_source_path"):
        source = Path(item["problem_source_path"]).read_text(encoding="utf-8")
    else:
        source = problem_lib.load_problem_source(problem_id)
    kernel = Path(item["kernel_path"]).read_text(encoding="utf-8")
    seed = int(item["seed"])
    subject = audit.prepare(problem_id, source, kernel, replicate_seed=seed, device="cuda:0")
    try:
        get_inputs = subject.get_inputs
        config_id = "native"
        if mode == "sanitizer":
            entry = item.get("a3_entry") or {}
            configs = sorted(entry.get("A3", []), key=lambda c: c.get("input_bytes", 0))
            if configs:
                analysis = problem_lib.analyze_problem(problem_id, source)
                variant = problem_lib.override_constants(source, analysis, configs[0]["overrides"])
                get_inputs = load_reference(variant)[2]
                config_id = configs[0]["config_id"]
        inputs = audit.draw_inputs(get_inputs, channel_seed(audit.A1_BASE, seed, 0), subject.device)
        with torch.no_grad():
            outputs = first_tensor_outputs(subject.candidate(*inputs))
        torch.cuda.synchronize()
        digest = hashlib.sha256()
        for tensor in outputs:
            digest.update(tensor.detach().contiguous().cpu().reshape(-1).view(torch.uint8).numpy())
        out_path.write_text(
            json.dumps(
                {
                    "sha256": digest.hexdigest(),
                    "config_id": config_id,
                    "shapes": [list(t.shape) for t in outputs],
                }
            ),
            encoding="utf-8",
        )
    finally:
        subject.cleanup()
    return 0


def _spawn(argv: list[str], env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(argv, env=env, capture_output=True, text=True, timeout=PROBE_TIMEOUT_S)


def run_poison(item: dict[str, Any], workdir: Path, so_path: str | None = None) -> GateOutcome:
    start = time.perf_counter()
    so_path = so_path or os.environ.get(SO_ENV)
    if not so_path or not Path(so_path).is_file():
        return GateOutcome(
            "A4",
            "poison-allocator",
            "error",
            details={"reason": "poison allocator library missing"},
            wall_seconds=time.perf_counter() - start,
        )
    item_path = workdir / "probe-item.json"
    item_path.write_text(json.dumps(item), encoding="utf-8")
    hashes: dict[int, Any] = {}
    for byte in POISON_BYTES:
        out = workdir / f"poison-{byte}.json"
        env = {**os.environ, **poison_allocator_env(byte, so_path)}
        done = _spawn(
            [
                sys.executable,
                "-m",
                "harness.q1.audit.gpu_probes",
                "--child",
                "poison",
                str(item_path),
                str(out),
            ],
            env,
        )
        if done.returncode != 0 or not out.exists():
            return GateOutcome(
                "A4",
                "poison-allocator",
                "reject",
                details={
                    "reason": "candidate-raised-under-poison",
                    "byte": byte,
                    "stderr_tail": done.stderr[-2000:],
                },
                wall_seconds=time.perf_counter() - start,
            )
        hashes[byte] = json.loads(out.read_text(encoding="utf-8"))
    same = hashes[POISON_BYTES[0]]["sha256"] == hashes[POISON_BYTES[1]]["sha256"]
    return GateOutcome(
        "A4",
        "poison-allocator",
        "accept" if same else "reject",
        details={
            "hashes": {str(k): v for k, v in hashes.items()},
            "reason": "" if same else "output-depends-on-poison",
        },
        wall_seconds=time.perf_counter() - start,
    )


def run_sanitizer(item: dict[str, Any], workdir: Path) -> GateOutcome:
    start = time.perf_counter()
    item_path = workdir / "probe-item.json"
    item_path.write_text(json.dumps(item), encoding="utf-8")
    out = workdir / "sanitizer.json"
    argv = sanitizer_command(
        [
            sys.executable,
            "-m",
            "harness.q1.audit.gpu_probes",
            "--child",
            "sanitizer",
            str(item_path),
            str(out),
        ]
    )
    try:
        done = _spawn(argv, dict(os.environ))
    except FileNotFoundError:
        return GateOutcome(
            "A4",
            "compute-sanitizer",
            "error",
            details={"reason": "compute-sanitizer not found"},
            wall_seconds=time.perf_counter() - start,
        )
    result = interpret_sanitizer(done.returncode)
    probe = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    # 0: memcheck clean; 86: memcheck error; anything else: the run did not
    # complete under the sanitizer (reported as error; A3 already judges the
    # candidate at this shape without the sanitizer).
    verdict = {True: "accept", False: "reject", None: "error"}[result.passed]
    return GateOutcome(
        "A4",
        "compute-sanitizer",
        verdict,
        details={**result.details, "probe": probe, "stdout_tail": done.stdout[-3000:]},
        wall_seconds=time.perf_counter() - start,
    )


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) == 4 and args[0] == "--child" and args[1] in {"poison", "sanitizer"}:
        return _child(args[1], Path(args[2]), Path(args[3]))
    print(
        "usage: python -m harness.q1.audit.gpu_probes --child poison|sanitizer ITEM OUT",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
