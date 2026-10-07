"""A4 GPU probes: dual-poison allocator runs and compute-sanitizer memcheck.

Both run the candidate once in a fresh child process of the A4 worker (so the
runner's watchdog, which kills the worker's process group, covers them):

- ``poison``: the child installs ``libq1_poison_alloc.so`` as a
  ``CUDAPluggableAllocator`` before any CUDA allocation, with poison byte 0x00
  in one child and 0xFF in the other, runs the candidate on the first A1 draw
  and writes the SHA-256 of its output bytes. Different hashes mean the
  candidate returned bytes it never wrote.
- ``sanitizer``: the child runs under ``compute-sanitizer --tool memcheck`` on
  the smallest A3 configuration (by input bytes) at which the candidate does
  not refuse before launch (the A3 classification: an exception before any
  Triton launch or aten compute op), else at native shape. Exit code 86 means
  memcheck found an error. (Pilot job 518: every S1 substrate refuses
  ``A3/lead1``, a size below its compiled range, so a probe fixed to the
  smallest configuration never ran a kernel and reported ``error``, which made
  A4 and every tier ``error`` for all S1 kernels.) The row is memcheck's
  verdict alone: when the candidate raises *after* a launch at that held-out
  configuration, the exception is recorded (``workload_raised_after_launch``)
  and the child exits 0, so the row is ``accept`` unless memcheck reports an
  error. A3 runs the same configuration and judges the crash; without this, a
  held-out-shape crash made the row ``error`` and removed the kernel from tiers
  N and c-disjoint, whose other channels run at native shapes (second review,
  finding 11). At native shape an exception still propagates (``error``; A1
  rejects that kernel anyway).

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


def sanitizer_configs(entry: dict[str, Any]) -> list[dict[str, Any]]:
    """The A3 configurations in probe order: input bytes, then config id."""
    configs = list(entry.get("A3", []))
    return sorted(configs, key=lambda c: (c.get("input_bytes", 0), c.get("config_id", "")))


def run_first_accepted(
    subject: Any,
    problem_id: str,
    source: str,
    configs: list[dict[str, Any]],
    seed: int,
) -> tuple[list[Any], str, list[dict[str, Any]], dict[str, Any] | None]:
    """Run the candidate on the first configuration it does not refuse, else native.

    A refusal is an exception before any launch (``audit.run.LaunchCounter``:
    no Triton launch and no aten compute op), exactly as A3 classifies it; it
    is recorded and the next configuration is tried. An exception after a
    launch at a held-out configuration is returned as the fourth value (no
    outputs): the sanitizer row then reports memcheck alone and A3 judges the
    crash. At native shape an exception propagates. Returns the outputs, the
    configuration id, the refused configurations and the post-launch exception.
    """
    import torch

    from harness.q1 import problems as problem_lib
    from harness.q1.audit import run as audit
    from harness.q1.gates.common import first_tensor_outputs, load_reference, synchronize
    from harness.q1.gates.outcome import channel_seed

    refused: list[dict[str, Any]] = []
    analysis = problem_lib.analyze_problem(problem_id, source) if configs else None
    for config in [*configs, None]:
        if config is None:
            get_inputs, config_id = subject.get_inputs, "native"
        else:
            variant = problem_lib.override_constants(source, analysis, config["overrides"])
            get_inputs, config_id = load_reference(variant)[2], config["config_id"]
        inputs = audit.draw_inputs(get_inputs, channel_seed(audit.A1_BASE, seed, 0), subject.device)
        counter = audit.LaunchCounter()
        try:
            with torch.no_grad(), counter:
                outputs = first_tensor_outputs(subject.candidate(*inputs))
                synchronize(subject.device)
        except Exception as exc:
            if config is None:
                raise
            if counter.launches:
                raised = {
                    "config_id": config_id,
                    "exception": type(exc).__name__,
                    "message": str(exc)[:500],
                    "launches_before_exception": counter.launches,
                }
                return [], config_id, refused, raised
            refused.append({"config_id": config_id, "exception": type(exc).__name__})
            continue
        return outputs, config_id, refused, None
    raise AssertionError("unreachable: the native configuration either returns or raises")


def _child(mode: str, item_path: Path, out_path: Path) -> int:
    """Child body: allocator first (poison mode), then import torch and run once."""
    if mode == "poison":
        from harness.q1.audit.contracts import install_poison_allocator_from_env

        if install_poison_allocator_from_env() is None:
            raise SystemExit("poison child needs Q1_POISON_BYTE and Q1_POISON_ALLOC_SO")
    import torch

    from harness.q1 import problems as problem_lib
    from harness.q1.audit import run as audit
    from harness.q1.gates.common import first_tensor_outputs
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
        refused: list[dict[str, Any]] = []
        raised: dict[str, Any] | None = None
        if mode == "sanitizer":
            configs = sanitizer_configs(item.get("a3_entry") or {})
            outputs, config_id, refused, raised = run_first_accepted(
                subject, problem_id, source, configs, seed
            )
            if raised is not None:
                # memcheck alone decides the row; A3 judges the crash at this shape.
                out_path.write_text(
                    json.dumps(
                        {
                            "sha256": None,
                            "config_id": config_id,
                            "refused_configs": refused,
                            "workload_raised_after_launch": raised,
                        }
                    ),
                    encoding="utf-8",
                )
                return 0
        else:
            config_id = "native"
            inputs = audit.draw_inputs(
                subject.get_inputs, channel_seed(audit.A1_BASE, seed, 0), subject.device
            )
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
                    "refused_configs": refused,
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
    details = {**result.details, "probe": probe, "stdout_tail": done.stdout[-3000:]}
    if probe.get("workload_raised_after_launch"):
        details["workload_raised_after_launch"] = probe["workload_raised_after_launch"]
    return GateOutcome(
        "A4",
        "compute-sanitizer",
        verdict,
        details=details,
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
