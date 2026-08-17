#!/usr/bin/env python3
"""Run the registered Mnemosyne lifecycle falsifier in locked-down Docker."""

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

from scripts.validate_mnemosyne_lifecycle_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    EXPECTED_STATUS,
    validate_experiment_contract,
)

DOCTOR_ROOT = PROJECT_ROOT / "infra" / "memory-baselines" / "mnemosyne"
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data"
    / "results"
    / "mnemosyne-lifecycle"
    / "2026-08-16-local-docker-v1"
)
DEFAULT_IMAGE = "cotcodec-mnemosyne-lifecycle:a0e1424-arm64-v1"


class RunnerError(RuntimeError):
    """Raised when image provenance, containment, or lifecycle evidence drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_path(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise RunnerError(f"expected regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


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
                raise RunnerError(f"short write: {path}")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _run(argv: list[str], *, timeout: int = 900) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        argv,
        check=False,
        capture_output=True,
        timeout=timeout,
    )
    if completed.returncode != 0:
        raise RunnerError(
            f"command failed ({completed.returncode}): {argv!r}\n"
            f"stdout={completed.stdout.decode(errors='replace')}\n"
            f"stderr={completed.stderr.decode(errors='replace')}"
        )
    return completed


def _strict_json(data: bytes, label: str) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise RunnerError(f"{label} contains non-finite value: {value}")

    try:
        payload = json.loads(data, parse_constant=reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RunnerError(f"{label} is not strict JSON") from exc
    if not isinstance(payload, dict):
        raise RunnerError(f"{label} must be a JSON object")
    return payload


def _image_contract(image: str, experiment: dict[str, Any]) -> dict[str, Any]:
    raw = _run(["docker", "image", "inspect", image]).stdout
    try:
        rows = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RunnerError("Docker image inspect is not JSON") from exc
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise RunnerError("Docker image inspect must return one image")
    inspect = rows[0]
    image_id = inspect.get("Id")
    if not isinstance(image_id, str) or not image_id.startswith("sha256:"):
        raise RunnerError("Mnemosyne image ID is invalid")
    if inspect.get("Architecture") != "arm64" or inspect.get("Os") != "linux":
        raise RunnerError("Mnemosyne image platform drifted")
    labels = inspect.get("Config", {}).get("Labels", {})
    source = experiment["source"]
    expected_labels = {
        "org.opencontainers.image.revision": source["revision"],
        "org.cotcodec.source-tree": source["tree"],
        "org.cotcodec.source-archive-sha256": source["git_archive_tar_sha256"],
        "org.cotcodec.lock-sha256": source["uv_lock_sha256"],
        "org.cotcodec.doctor-sha256": _sha_path(DOCTOR_ROOT / "doctor.py"),
        "org.cotcodec.discovery-only": "true",
    }
    for key, expected in expected_labels.items():
        if labels.get(key) != expected:
            raise RunnerError(f"Mnemosyne image label {key} drifted")
    return {
        "image_id": image_id,
        "inspect_sha256": _sha(raw),
        "labels": expected_labels,
        "architecture": inspect["Architecture"],
        "os": inspect["Os"],
    }


def _container_argv(
    *, image_id: str, state_root: Path, phase: str, repeat: int
) -> list[str]:
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
        "256",
        "--memory",
        "1g",
        "--cpus",
        "1",
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=256m",
        "-e",
        "HOME=/tmp/mnemosyne-home",
        "-e",
        "MNEMOSYNE_DATA_DIR=/state/data",
        "-e",
        "MNEMOSYNE_NO_EMBEDDINGS=1",
        "-e",
        "PYTHONDONTWRITEBYTECODE=1",
        "-v",
        f"{state_root}:/state:rw",
        image_id,
        "/opt/cotcodec/doctor.py",
        phase,
        "--state-root",
        "/state",
        "--repeat",
        str(repeat),
    ]


def _stable_projection(run: dict[str, Any]) -> dict[str, Any]:
    prepare = run["prepare"]
    restart = run["verify-restart"]
    purge = run["purge"]
    return {
        "prepare": {
            key: prepare[key]
            for key in (
                "duplicate_retry_idempotent",
                "session_isolation_before_sleep",
                "source_rows_marked_consolidated",
                "episodic_summary_created",
                "consolidated_removed_from_active_context",
                "consolidated_recallable",
                "cross_session_recall_blocked",
                "documented_forget_deleted_source",
                "episodic_summary_survived_source_forget",
                "forgotten_canary_still_recallable",
            )
        },
        "restart": {
            key: restart[key]
            for key in (
                "restart_preserved_episodic_summary",
                "restart_preserved_recall",
                "restart_preserved_session_isolation",
                "recall_did_not_reactivate",
                "episodic_source_lineage_present",
            )
        },
        "purge": {
            "status": purge["status"],
            "episodic_forget_results": purge["episodic_forget_results"],
            "native_session_scoped_purge_available": purge[
                "native_session_scoped_purge_available"
            ],
            "logical_episodic_canary_rows": purge[
                "logical_canary_rows_after_documented_forget"
            ]["episodic_memory"],
            "plaintext_canary_residue_reproduced": purge[
                "plaintext_canary_residue_reproduced"
            ],
            "archive_to_active_transition_available": purge[
                "archive_to_active_transition_available"
            ],
            "h100_actor_admission": purge["h100_actor_admission"],
        },
    }


def run_doctor(
    *, experiment_path: Path, output: Path, image: str
) -> dict[str, Any]:
    experiment = validate_experiment_contract(experiment_path)
    if output.exists():
        raise RunnerError(f"output already exists: {output}")
    output.mkdir(parents=True, mode=0o700)
    image_contract = _image_contract(image, experiment)

    runs: list[dict[str, Any]] = []
    phase_receipts: list[dict[str, Any]] = []
    for repeat in (1, 2):
        state_root = output / f"repeat-{repeat}" / "state"
        state_root.mkdir(parents=True, mode=0o700)
        run: dict[str, Any] = {}
        for phase in ("prepare", "verify-restart", "purge"):
            argv = _container_argv(
                image_id=image_contract["image_id"],
                state_root=state_root,
                phase=phase,
                repeat=repeat,
            )
            completed = _run(argv)
            result = _strict_json(
                completed.stdout, f"Mnemosyne repeat {repeat} {phase}"
            )
            if result.get("phase") != phase or result.get("repeat") != repeat:
                raise RunnerError("Mnemosyne phase identity drifted")
            artifact = output / f"repeat-{repeat}" / f"{phase}.json"
            _write_once(artifact, _json_bytes(result))
            run[phase] = result
            phase_receipts.append(
                {
                    "repeat": repeat,
                    "phase": phase,
                    "argv": argv,
                    "artifact": str(artifact.relative_to(PROJECT_ROOT)),
                    "artifact_sha256": _sha_path(artifact),
                    "stderr_sha256": _sha(completed.stderr),
                }
            )
        runs.append(run)

    projections = [_stable_projection(run) for run in runs]
    if projections[0] != projections[1]:
        raise RunnerError("Mnemosyne clean-state semantic projections differ")
    projection = projections[0]
    expected_truths = [
        *projection["prepare"].values(),
        *projection["restart"].values(),
    ]
    if not all(value is True for value in expected_truths):
        raise RunnerError("Mnemosyne positive lifecycle prerequisites did not all pass")
    purge_projection = projection["purge"]
    if (
        purge_projection["status"] != EXPECTED_STATUS
        or purge_projection["episodic_forget_results"] == []
        or any(purge_projection["episodic_forget_results"])
        or purge_projection["native_session_scoped_purge_available"] is not False
        or purge_projection["logical_episodic_canary_rows"] <= 0
        or purge_projection["plaintext_canary_residue_reproduced"] is not True
        or purge_projection["archive_to_active_transition_available"] is not False
        or purge_projection["h100_actor_admission"]
        != "forbidden-for-this-revision"
    ):
        raise RunnerError("Mnemosyne preregistered falsification was not reproduced")

    report = {
        "schema_version": 1,
        "status": EXPECTED_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "h100_actor_admission": "forbidden-for-this-revision",
        "experiment": str(experiment_path.relative_to(PROJECT_ROOT)),
        "experiment_sha256": _sha_path(experiment_path),
        "source": experiment["source"],
        "runtime": experiment["runtime"],
        "image": image_contract,
        "dockerfile_sha256": _sha_path(DOCTOR_ROOT / "Dockerfile"),
        "doctor_sha256": _sha_path(DOCTOR_ROOT / "doctor.py"),
        "phase_receipts": phase_receipts,
        "stable_projection": projection,
        "stable_projection_sha256": _sha(_json_bytes(projection)),
        "reproduced_in_two_clean_states": True,
        "conclusion": (
            "Pinned Mnemosyne reproduces session-isolated working-to-episodic "
            "consolidation and fresh-process recall, but recall does not reactivate "
            "a consolidated record. The documented forget API deletes the source "
            "working row while the episodic summary remains logically recallable "
            "and physically present. This pin is a one-way consolidation control, "
            "not a bidirectional pager or source-complete purge implementation."
        ),
    }
    report_path = output / "report.json"
    _write_once(report_path, _json_bytes(report))
    manifest = {
        "schema_version": 1,
        "status": "SEALED_DISCOVERY_NEGATIVE",
        "report": "report.json",
        "report_sha256": _sha_path(report_path),
        "artifact_count": len(phase_receipts),
        "image_id": image_contract["image_id"],
        "stable_projection_sha256": report["stable_projection_sha256"],
    }
    _write_once(output / "manifest.json", _json_bytes(manifest))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", type=Path, default=DEFAULT_EXPERIMENT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    args = parser.parse_args()
    report = run_doctor(
        experiment_path=args.experiment.resolve(),
        output=args.output.resolve(),
        image=args.image,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
