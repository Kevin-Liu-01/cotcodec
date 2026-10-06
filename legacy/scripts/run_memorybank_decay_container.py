#!/usr/bin/env python3
"""Run and seal two network-disabled MemoryBank decay contract repetitions."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validate_memorybank_decay_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    EXPECTED_IMAGE,
    EXPECTED_STATUS,
    validate_experiment_contract,
)

DEFAULT_OUTPUT = (
    PROJECT_ROOT / "data/results/memorybank-decay/2026-08-16-local-docker-v1"
)
MODULE = PROJECT_ROOT / "harness/memory_trials/memorybank_decay.py"
DOCTOR = PROJECT_ROOT / "scripts/run_memorybank_decay_doctor.py"


class MemoryBankContainerError(RuntimeError):
    """Raised when containment or deterministic contract evidence drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_once(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise MemoryBankContainerError(f"short write: {path}")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _run(argv: list[str], *, timeout: int = 120) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(argv, capture_output=True, check=False, timeout=timeout)
    if completed.returncode != 0:
        raise MemoryBankContainerError(
            f"command failed ({completed.returncode}): {argv!r}\n"
            f"stdout={completed.stdout.decode(errors='replace')[-4000:]}\n"
            f"stderr={completed.stderr.decode(errors='replace')[-4000:]}"
        )
    return completed


def _container_argv() -> list[str]:
    return [
        "docker",
        "run",
        "--rm",
        "--pull=never",
        "--platform",
        "linux/arm64",
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        "64",
        "--memory",
        "128m",
        "--cpus",
        "1",
        "--user",
        "65534:65534",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=16m,uid=65534,gid=65534,mode=0700",
        "--mount",
        f"type=bind,src={PROJECT_ROOT},dst=/workspace/cotcodec,readonly",
        "--workdir",
        "/workspace/cotcodec",
        "--entrypoint",
        "python",
        EXPECTED_IMAGE,
        "scripts/run_memorybank_decay_doctor.py",
    ]


def _strict_report(data: bytes) -> dict[str, Any]:
    try:
        report = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MemoryBankContainerError("container report is not strict JSON") from exc
    if (
        not isinstance(report, dict)
        or report.get("status") != EXPECTED_STATUS
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("h100_actor_admission")
        != "blocked-pending-frozen-system-integration"
        or report.get("source", {}).get("upstream_code_imported") is not False
        or not all(report.get("checks", {}).values())
        or report.get("code_sha256")
        != {
            "harness/memory_trials/memorybank_decay.py": _sha(MODULE.read_bytes()),
            "scripts/run_memorybank_decay_doctor.py": _sha(DOCTOR.read_bytes()),
        }
    ):
        raise MemoryBankContainerError("container report semantics drifted")
    return report


def run(output: Path) -> dict[str, Any]:
    experiment = validate_experiment_contract()
    output.mkdir(parents=True, exist_ok=False)
    inspect_raw = _run(["docker", "image", "inspect", EXPECTED_IMAGE]).stdout
    rows = json.loads(inspect_raw)
    image = rows[0] if isinstance(rows, list) and len(rows) == 1 else {}
    expected_id = "sha256:" + EXPECTED_IMAGE.rsplit("sha256:", 1)[1]
    if (
        image.get("Id") != expected_id
        or image.get("Architecture") != experiment["runtime"]["architecture"]
        or image.get("Os") != "linux"
        or EXPECTED_IMAGE.replace("docker.io/library/", "")
        not in (image.get("RepoDigests") or [])
    ):
        raise MemoryBankContainerError("container image identity drifted")

    argv = _container_argv()
    repeats = []
    for repeat in range(1, experiment["runtime"]["clean_state_repeats"] + 1):
        stdout = _run(argv).stdout
        report = _strict_report(stdout)
        repeats.append(stdout)
        _write_once(output / f"repeat-{repeat}.json", stdout)
        if report["status"] != EXPECTED_STATUS:
            raise MemoryBankContainerError("repeat status drifted")
    if repeats[0] != repeats[1]:
        raise MemoryBankContainerError("clean repeats are not byte-identical")

    _write_once(output / "experiment.yaml", DEFAULT_EXPERIMENT.read_bytes())
    _write_once(output / "memorybank_decay.py", MODULE.read_bytes())
    _write_once(output / "doctor.py", DOCTOR.read_bytes())
    _write_once(output / "image-inspect.json", inspect_raw)
    summary = {
        "schema_version": 1,
        "status": EXPECTED_STATUS,
        "run_count": 2,
        "report_sha256": _sha(repeats[0]),
        "image_id": expected_id,
        "runtime_argv": [
            item.replace(str(PROJECT_ROOT), "<project-root>") for item in argv
        ],
        "scientific_result": False,
        "publication_ready": False,
        "h100_actor_admission": "blocked-pending-frozen-system-integration",
    }
    _write_once(
        output / "report.json",
        (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode(),
    )
    files = {
        path.name: _sha(path.read_bytes())
        for path in sorted(output.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    manifest = {
        "schema_version": 1,
        "status": EXPECTED_STATUS,
        "file_count": len(files),
        "files": files,
    }
    _write_once(
        output / "manifest.json",
        (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode(),
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(run(args.output), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
