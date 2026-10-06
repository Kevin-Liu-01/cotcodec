#!/usr/bin/env python3
"""Run uninterrupted and SIGUSR1-resumed deterministic canary admission proofs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.run_state import canonical_json  # noqa: E402
from scripts.analyze_degradation_canary import analyze  # noqa: E402
from scripts.validate_degradation_canary_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    validate_experiment,
)

DEFAULT_OUTPUT = (
    PROJECT_ROOT / "data/results/orchvar-canary/2026-08-26-local-admission-v1"
)
RUN_ID = "orchvar-canary-admission-v1"
BOUND_FILES = [
    "experiments/degradation_canary_local_01.yaml",
    "harness/agent_loop.py",
    "harness/benchmarks/orchvar_canary.py",
    "harness/benchmarks/specs/orchvar_canary_tasks.yaml",
    "harness/metrics/degradation.py",
    "harness/run_state.py",
    "harness/runner.py",
    "scripts/analyze_degradation_canary.py",
    "scripts/run_orchvar_canary_proof.py",
    "scripts/validate_degradation_canary_experiment.py",
]


class CanaryProofError(RuntimeError):
    """Raised when the admission proof is incomplete or non-reproducible."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_command(root: Path, *, resume: bool, delay_ms: int = 0) -> subprocess.CompletedProcess:
    environment = {
        **os.environ,
        "COTCODEC_OUTPUT_DIR": str(root),
        "COTCODEC_RUN_ID": RUN_ID,
    }
    if resume:
        environment["COTCODEC_RESUME"] = "1"
    if delay_ms:
        environment["COTCODEC_CELL_DELAY_MS"] = str(delay_ms)
    return subprocess.run(
        [sys.executable, "-m", "harness.runner", str(DEFAULT_EXPERIMENT)],
        cwd=PROJECT_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )


def _write_process_receipt(
    root: Path, name: str, completed: subprocess.CompletedProcess
) -> None:
    receipt = root / "process-receipts"
    receipt.mkdir(parents=True, exist_ok=True)
    (receipt / f"{name}.stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (receipt / f"{name}.stderr.txt").write_text(completed.stderr, encoding="utf-8")
    (receipt / f"{name}.json").write_text(
        canonical_json({"returncode": completed.returncode}) + "\n",
        encoding="utf-8",
    )


def _scientific_outputs(root: Path) -> dict[str, str]:
    selected = [
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.relative_to(root).parts[0] in {"traces", "results"}
    ]
    return {str(path.relative_to(root)): _sha256(path) for path in sorted(selected)}


def run_proof(output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    """Run both paths and require byte-identical trace, summary, and analysis files."""
    validate_experiment()
    if output.exists() and any(output.iterdir()):
        raise CanaryProofError(f"proof output is not empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    uninterrupted = output / "uninterrupted"
    resumed = output / "usr1-resumed"

    first = _run_command(uninterrupted, resume=False)
    _write_process_receipt(output, "uninterrupted", first)
    if first.returncode != 0:
        raise CanaryProofError("uninterrupted runner failed")
    analyze(uninterrupted, RUN_ID)

    environment = {
        **os.environ,
        "COTCODEC_OUTPUT_DIR": str(resumed),
        "COTCODEC_RUN_ID": RUN_ID,
        "COTCODEC_CELL_DELAY_MS": "20",
    }
    interrupted = subprocess.Popen(
        [sys.executable, "-m", "harness.runner", str(DEFAULT_EXPERIMENT)],
        cwd=PROJECT_ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    checkpoint = resumed / f"run-state/{RUN_ID}/checkpoint.json"
    deadline = time.monotonic() + 15
    completed_cells = 0
    while time.monotonic() < deadline:
        if checkpoint.is_file():
            try:
                completed_cells = json.loads(checkpoint.read_text(encoding="utf-8"))[
                    "completed_cells"
                ]
            except (OSError, json.JSONDecodeError, KeyError):
                completed_cells = 0
            if completed_cells >= 2:
                break
        time.sleep(0.01)
    if completed_cells < 2:
        interrupted.kill()
        interrupted.communicate()
        raise CanaryProofError("runner did not reach an interruptible checkpoint")
    os.kill(interrupted.pid, signal.SIGUSR1)
    stdout, stderr = interrupted.communicate(timeout=15)
    interrupted_receipt = subprocess.CompletedProcess(
        interrupted.args,
        interrupted.returncode,
        stdout,
        stderr,
    )
    _write_process_receipt(output, "usr1-interrupted", interrupted_receipt)
    if interrupted.returncode != 0:
        raise CanaryProofError("SIGUSR1-interrupted runner did not exit cleanly")
    ack = resumed / f"run-state/{RUN_ID}/checkpoint-ack.json"
    if not ack.is_file():
        raise CanaryProofError("SIGUSR1 runner did not acknowledge its checkpoint")
    ack_payload = json.loads(ack.read_text(encoding="utf-8"))
    acknowledged_cells = ack_payload.get("completed_cells")
    if (
        isinstance(acknowledged_cells, bool)
        or not isinstance(acknowledged_cells, int)
        or not 0 < acknowledged_cells < 120
    ):
        raise CanaryProofError("SIGUSR1 checkpoint did not bind a strict plan prefix")

    final = _run_command(resumed, resume=True)
    _write_process_receipt(output, "usr1-resume", final)
    if final.returncode != 0:
        raise CanaryProofError("resumed runner failed")
    analyze(resumed, RUN_ID)

    left = _scientific_outputs(uninterrupted)
    right = _scientific_outputs(resumed)
    if left != right:
        raise CanaryProofError("resumed outputs differ from uninterrupted outputs")
    if len(left) != 6:
        raise CanaryProofError(f"unexpected scientific output roster: {sorted(left)}")

    git_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    manifest = {
        "schema_version": 1,
        "status": "PASS",
        "scientific_result": False,
        "publication_ready": False,
        "run_id": RUN_ID,
        "git_head": git_head,
        "source_state": "dirty-uncommitted-local-admission",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "external_model_calls": 0,
        "external_tool_calls": 0,
        "planned_cells": 120,
        "usr1_acknowledged_cells": acknowledged_cells,
        "byte_identical_scientific_outputs": True,
        "output_sha256": left,
        "bound_source_sha256": {
            path: _sha256(PROJECT_ROOT / path) for path in BOUND_FILES
        },
        "claim_boundary": (
            "Deterministic local harness admission only; not a language-routing, "
            "model-quality, benchmark-validity, Paper 1, or publication result."
        ),
    }
    (output / "manifest.json").write_text(
        canonical_json(manifest) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    manifest = run_proof(args.output)
    print(f"OrchVar-Canary admission proof {manifest['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
