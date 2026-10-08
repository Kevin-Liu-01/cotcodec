"""SIGUSR1 reaches the entry point as a container's PID 1, as in the discovery lane.

Job 730 (v1, Qwen3.5-4B-Base) ignored Slurm's SIGUSR1. Its container ran
``/bin/bash -lc "... && exec python scripts/exec_research_workload.py"``, which
execs the workload argv, so the entry point was the container's PID 1; the
batch script forwards the signal with ``docker kill --signal USR1``. At the
first forward, flash-linear-attention's Triton kernels compiled and Triton's
LLVM replaced CPython's OS-level SIGUSR1 handler with one that swallows the
signal.

This test runs the tiny hybrid lane in the research image exactly that way
(same entrypoint, the same exec chain, ``--network none``, ``--cap-drop ALL``,
no-new-privileges, the job's uid), with ``scripts/dense_headroom_v2_signal_shim.py``
compiling a real Triton kernel (sm_90 target, no GPU needed) inside the first
forward, and sends SIGUSR1 with ``docker kill`` after the first chunk. v2's
entry point exits 75 with the marker; v1's does not answer (the 730 failure).

It needs Docker and an image with the architecture dependencies (torch,
transformers, flash-linear-attention, triton): set ``COTCODEC_USR1_PID1_IMAGE``
to the image ID. Run it on the host inside a CPU-only Slurm allocation.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMAGE = os.environ.get("COTCODEC_USR1_PID1_IMAGE")
pytestmark = pytest.mark.skipif(
    not IMAGE or shutil.which("docker") is None,
    reason="needs Docker and COTCODEC_USR1_PID1_IMAGE (a research image with torch and triton)")

FIXTURES = r"""
import json, sys
from pathlib import Path
sys.path.insert(0, "/work")
from harness import dense_headroom_data as dhd
dhd.block_gpu_only_kernels()
from scripts import run_dense_headroom_precheck_v2_doctor as d2
root = Path("/fx")
run = d2.TinyRunV2(root / "fixtures")
for which, entry in (("v2", "scripts/run_dense_headroom_precheck_v2.py"),
                     ("v1", "scripts/run_dense_headroom_precheck.py")):
    run_dir = root / f"run-{which}"
    run.batch_files("tiny-hybrid", run_dir, job_id="7001")
    argv = run.argv("tiny-hybrid", run_dir, entry=Path("/work") / entry, v1=which == "v1")
    (root / f"argv-{which}.json").write_text(json.dumps(argv[1:]))
print("fixtures ready")
"""


def _docker(*args: str, timeout: int = 600, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout,
                          check=check)


def _common(fixtures: Path) -> list[str]:
    return ["--network", "none", "--user", f"{os.getuid()}:{os.getgid()}",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--tmpfs", "/tmp:rw,exec,nosuid,nodev,size=8g",
            "--env", "USER=cotcodec", "--env", "LOGNAME=cotcodec", "--env", "HOME=/tmp/home",
            "--env", "HF_HUB_OFFLINE=1", "--env", "PYTHONUNBUFFERED=1",
            "--env", "OMP_NUM_THREADS=4",
            "--volume", f"{fixtures}:/fx:rw", "--volume", f"{PROJECT_ROOT}:/work:ro",
            "--workdir", "/work"]


def _run_as_pid1(fixtures: Path, which: str) -> dict:
    name = f"cotcodec-usr1-pid1-{which}-{os.getpid()}"
    argv = json.loads((fixtures / f"argv-{which}.json").read_text())
    command = ["python", "scripts/dense_headroom_v2_signal_shim.py", "--mode", "triton", "--",
               *argv]
    run_dir = fixtures / f"run-{which}"
    env = ["--env", f"COTCODEC_COMMAND_JSON_HEX={json.dumps(command).encode().hex()}",
           "--env", f"COTCODEC_OUTPUT_DIR=/fx/run-{which}",
           "--env", f"COTCODEC_CHECKPOINT_MARKER=/fx/run-{which}/checkpoint.ready",
           "--env", "COTCODEC_MODEL_ID=tiny", "--env", "COTCODEC_GIT_SHA=" + "b" * 40,
           "--env", "COTCODEC_SOURCE_SHA256=" + "c" * 64,
           "--env", f"COTCODEC_SHIM_REPORT=/fx/run-{which}/shim.json"]
    _docker("run", "-d", "--name", name, *_common(fixtures), *env, "--entrypoint", "/bin/bash",
            IMAGE, "-lc", "exec python scripts/exec_research_workload.py")
    try:
        eval_dir = run_dir / "dense-precheck" / "checkpoints" / "eval"
        deadline = time.time() + 900
        sent = False
        while time.time() < deadline:
            state = _docker("inspect", "--format", "{{.State.Running}}", name).stdout.strip()
            if state != "true":
                break
            if list(eval_dir.glob("*/chunk-*.npz")):
                _docker("kill", "--signal", "USR1", name)
                sent = True
                break
            time.sleep(0.2)
        exited = False
        deadline = time.time() + (900 if which == "v2" else 150)
        while time.time() < deadline:
            if _docker("inspect", "--format", "{{.State.Running}}", name).stdout.strip() != "true":
                exited = True
                break
            time.sleep(0.5)
        code = _docker("inspect", "--format", "{{.State.ExitCode}}", name).stdout.strip()
        logs = _docker("logs", name, check=False).stderr[-3000:]
    finally:
        _docker("rm", "--force", name, check=False)
    marker = run_dir / "checkpoint.ready"
    shim = run_dir / "shim.json"
    return {"sent": sent, "exited": exited, "exit_code": int(code) if exited else None,
            "marker": marker.read_text() if marker.is_file() else None,
            "shim": json.loads(shim.read_text()) if shim.is_file() else {}, "logs": logs}


def test_usr1_reaches_pid1_after_triton_replaced_the_handler(tmp_path: Path) -> None:
    fixtures = tmp_path / "fx"
    fixtures.mkdir()
    built = _docker("run", "--rm", *_common(fixtures), "--entrypoint", "python", IMAGE, "-c",
                    FIXTURES, timeout=900, check=False)
    assert built.returncode == 0, built.stderr[-3000:]

    v2 = _run_as_pid1(fixtures, "v2")
    assert v2["sent"], v2["logs"]
    assert v2["shim"].get("pid") == 1 and v2["shim"].get("mode") == "triton"
    assert v2["shim"].get("displaced") is True, v2["shim"]
    assert v2["exit_code"] == 75, v2["logs"]
    assert v2["marker"] is not None and "trigger=SIGUSR1" in v2["marker"]
    interrupted = json.loads((fixtures / "run-v2" / "dense-precheck" /
                              "receipt-interrupted.json").read_text())
    assert interrupted["signals"]["received"] == "SIGUSR1"
    assert interrupted["signals"]["handler_replacement_count"] >= 1
    assert interrupted["slurm_job_id"] == "7001"

    v1 = _run_as_pid1(fixtures, "v1")
    assert v1["sent"], v1["logs"]
    assert v1["shim"].get("pid") == 1 and v1["shim"].get("displaced") is True
    assert v1["marker"] is None and v1["exit_code"] != 75  # job 730's failure, reproduced
    (tmp_path / "usr1-pid1-result.json").write_text(json.dumps({"v2": v2, "v1": v1}, indent=2))
