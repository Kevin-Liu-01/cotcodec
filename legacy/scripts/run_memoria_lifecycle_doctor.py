#!/usr/bin/env python3
"""Run and seal the exact-source Memoria transactional lifecycle falsifier."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validate_memoria_lifecycle_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    EXPECTED_STATUS,
    validate_experiment_contract,
)

DEFAULT_IMAGE = "cotcodec-memoria-lifecycle:efd3d65-arm64-v2"
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data/results/memoria-transactional-lifecycle/2026-08-16-local-docker-v1"
)
DOCKERFILE = PROJECT_ROOT / "infra/memory-baselines/memoria/Dockerfile"
DOCTOR = PROJECT_ROOT / "infra/memory-baselines/memoria/cotcodec_lifecycle.rs"


class MemoriaRunnerError(RuntimeError):
    """Raised when source, runtime, or report evidence drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_path(path: Path) -> str:
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
                raise MemoriaRunnerError(f"short write: {path}")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _run(argv: list[str], *, timeout: int = 900) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(argv, capture_output=True, check=False, timeout=timeout)
    if completed.returncode != 0:
        raise MemoriaRunnerError(
            f"command failed ({completed.returncode}): {argv!r}\n"
            + completed.stderr.decode(errors="replace")[-8000:]
        )
    return completed


def _source_contract(source_root: Path, experiment: dict[str, Any]) -> dict[str, Any]:
    source = experiment["source"]
    if not source_root.is_dir() or source_root.is_symlink():
        raise MemoriaRunnerError("Memoria source root must be a regular directory")
    head = _run(["git", "-C", str(source_root), "rev-parse", "HEAD"]).stdout.decode().strip()
    tree = _run(
        ["git", "-C", str(source_root), "rev-parse", "HEAD^{tree}"]
    ).stdout.decode().strip()
    state = _run(
        [
            "git",
            "-C",
            str(source_root),
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ]
    ).stdout
    if head != source["revision"] or tree != source["tree"] or state:
        raise MemoriaRunnerError("Memoria source checkout drifted")
    archive = _run(["git", "-C", str(source_root), "archive", "--format=tar", head]).stdout
    if _sha(archive) != source["git_archive_tar_sha256"]:
        raise MemoriaRunnerError("Memoria source archive drifted")
    checks = {
        "license_sha256": _sha_path(source_root / "LICENSE"),
        "cargo_lock_sha256": _sha_path(source_root / "memoria/Cargo.lock"),
    }
    if checks != {
        "license_sha256": source["license_sha256"],
        "cargo_lock_sha256": source["cargo_lock_sha256"],
    }:
        raise MemoriaRunnerError("Memoria license or Cargo lock drifted")
    service = (source_root / "memoria/crates/memoria-git/src/service.rs").read_text()
    memory_service = (
        source_root / "memoria/crates/memoria-service/src/service.rs"
    ).read_text()
    source_checks = {
        "snapshot_restore_is_delete_then_insert": (
            "DELETE FROM {qualified_table}" in service
            and "INSERT INTO {qualified_table} SELECT *" in service
            and "The DELETE+INSERT\n        // is non-atomic" in service
        ),
        "public_purge_count_ignores_deactivated_count": (
            "let deactivated = sql.soft_delete_from(&table, memory_id).await?;"
            in memory_service
            and "purged: 1" in memory_service
        ),
    }
    if not all(source_checks.values()):
        raise MemoriaRunnerError("Memoria source-level falsifier drifted")
    return {
        "git_sha": head,
        "git_tree": tree,
        "archive": archive,
        "archive_sha256": _sha(archive),
        "archive_bytes": len(archive),
        **checks,
        "source_checks": source_checks,
    }


def _inspect_image(image: str) -> tuple[dict[str, Any], bytes]:
    raw = _run(["docker", "image", "inspect", image]).stdout
    rows = json.loads(raw)
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise MemoriaRunnerError("Docker inspect roster drifted")
    return rows[0], raw


def _image_contract(image: str, experiment: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
    inspect, raw = _inspect_image(image)
    labels = (inspect.get("Config") or {}).get("Labels") or {}
    source = experiment["source"]
    expected_labels = {
        "org.opencontainers.image.revision": source["revision"],
        "org.opencontainers.image.licenses": source["license"],
        "org.cotcodec.discovery-only": "true",
        "org.cotcodec.source-tree": source["tree"],
        "org.cotcodec.source-archive-sha256": source["git_archive_tar_sha256"],
        "org.cotcodec.doctor-sha256": _sha_path(DOCTOR),
    }
    if any(labels.get(key) != value for key, value in expected_labels.items()):
        raise MemoriaRunnerError("Memoria doctor image labels drifted")
    image_id = inspect.get("Id")
    if (
        not isinstance(image_id, str)
        or not image_id.startswith("sha256:")
        or inspect.get("Architecture") != "arm64"
        or inspect.get("Os") != "linux"
        or (inspect.get("Config") or {}).get("User") != "65532:65532"
    ):
        raise MemoriaRunnerError("Memoria doctor image runtime drifted")
    projection = {
        "image_id": image_id,
        "architecture": "arm64",
        "os": "linux",
        "labels": expected_labels,
    }
    return {
        **projection,
        "inspect_sha256": _sha(raw),
        "inspect_projection_sha256": _sha(
            json.dumps(projection, separators=(",", ":"), sort_keys=True).encode()
        ),
    }, raw


def _matrixone_contract(experiment: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
    image = experiment["runtime"]["matrixone_image"]
    inspect, raw = _inspect_image(image)
    if (
        inspect.get("Id")
        != "sha256:66e2e0123d32094bff32ef7b8ba06d6d84391983cd1c9c41329dc3f7a05a2518"
        or inspect.get("Architecture") != "arm64"
        or inspect.get("Os") != "linux"
    ):
        raise MemoriaRunnerError("MatrixOne image identity drifted")
    return {
        "image": image,
        "image_id": inspect["Id"],
        "architecture": "arm64",
        "os": "linux",
        "inspect_sha256": _sha(raw),
    }, raw


def _phase_argv(image_id: str, network: str, phase: int) -> list[str]:
    return [
        "docker",
        "run",
        "--rm",
        "--pull=never",
        "--platform",
        "linux/arm64",
        "--network",
        network,
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
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=64m,uid=65532,gid=65532",
        "-e",
        f"COTCODEC_PHASE={phase}",
        image_id,
    ]


def _parse_phase(raw: bytes, expected_phase: int) -> dict[str, Any]:
    marker = b"COTCODEC_MEMORIA_PHASE="
    rows = [line.split(marker, 1)[1] for line in raw.splitlines() if marker in line]
    if len(rows) != 1:
        raise MemoriaRunnerError(
            f"phase {expected_phase} emitted {len(rows)} report markers"
        )
    payload = json.loads(rows[0])
    if not isinstance(payload, dict) or payload.get("phase") != expected_phase:
        raise MemoriaRunnerError(f"phase {expected_phase} report drifted")
    values = [value for key, value in payload.items() if key != "phase"]
    if not values or not all(value is True for value in values):
        raise MemoriaRunnerError(f"phase {expected_phase} checks failed: {payload}")
    return payload


def _run_repeat(
    *, repeat: int, image_id: str, matrixone_image: str
) -> tuple[dict[str, Any], dict[str, bytes]]:
    suffix = secrets.token_hex(4)
    network = f"cotcodec-memoria-{suffix}-net"
    volume = f"cotcodec-memoria-{suffix}-data"
    database = f"cotcodec-memoria-{suffix}-db"
    artifacts: dict[str, bytes] = {}
    _run(["docker", "network", "create", "--internal", network])
    _run(["docker", "volume", "create", volume])
    try:
        _run(
            [
                "docker",
                "run",
                "-d",
                "--pull=never",
                "--platform",
                "linux/arm64",
                "--name",
                database,
                "--network",
                network,
                "--network-alias",
                "matrixone",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--pids-limit",
                "1024",
                "--memory",
                "6g",
                "--cpus",
                "2",
                "--mount",
                f"type=volume,src={volume},dst=/mo-data",
                "--tmpfs",
                "/tmp:rw,nosuid,nodev,size=1g",
                "--tmpfs",
                "/var/log:rw,nosuid,nodev,size=256m",
                matrixone_image,
            ]
        )
        phases: list[dict[str, Any]] = []
        for phase in (1, 2, 3):
            if phase > 1:
                _run(["docker", "restart", database], timeout=180)
            completed = _run(_phase_argv(image_id, network, phase), timeout=240)
            raw = completed.stdout + completed.stderr
            artifacts[f"repeat-{repeat}-phase-{phase}.txt"] = raw
            phases.append(_parse_phase(raw, phase))
        logs = _run(["docker", "logs", database])
        artifacts[f"repeat-{repeat}-matrixone.log"] = logs.stdout + logs.stderr
        artifacts[f"repeat-{repeat}-matrixone-inspect.json"] = _run(
            ["docker", "inspect", database]
        ).stdout
        projection = {"repeat": repeat, "phases": phases}
        projection["phase_projection_sha256"] = _sha(
            json.dumps(phases, separators=(",", ":"), sort_keys=True).encode()
        )
        return projection, artifacts
    finally:
        subprocess.run(
            ["docker", "rm", "-f", database], capture_output=True, check=False
        )
        subprocess.run(
            ["docker", "volume", "rm", volume], capture_output=True, check=False
        )
        subprocess.run(
            ["docker", "network", "rm", network], capture_output=True, check=False
        )


def run(*, source_root: Path, image: str, output: Path) -> dict[str, Any]:
    experiment = validate_experiment_contract()
    output.mkdir(parents=True, exist_ok=False)
    source = _source_contract(source_root.resolve(), experiment)
    image_contract, image_inspect = _image_contract(image, experiment)
    matrixone, matrixone_inspect = _matrixone_contract(experiment)
    source_archive = source.pop("archive")
    fixed_artifacts = {
        "experiment.yaml": DEFAULT_EXPERIMENT.read_bytes(),
        "Dockerfile": DOCKERFILE.read_bytes(),
        "cotcodec_lifecycle.rs": DOCTOR.read_bytes(),
        "source.tar": source_archive,
        "source-receipt.json": _json_bytes(source),
        "doctor-image-inspect.json": image_inspect,
        "matrixone-image-inspect.json": matrixone_inspect,
    }
    for name, data in fixed_artifacts.items():
        _write_once(output / name, data)

    repeats: list[dict[str, Any]] = []
    for repeat in (1, 2):
        projection, artifacts = _run_repeat(
            repeat=repeat,
            image_id=image_contract["image_id"],
            matrixone_image=matrixone["image"],
        )
        for name, data in artifacts.items():
            _write_once(output / name, data)
        _write_once(output / f"repeat-{repeat}.json", _json_bytes(projection))
        repeats.append(projection)
    if repeats[0]["phases"] != repeats[1]["phases"]:
        raise MemoriaRunnerError("Memoria clean-state repetitions diverged")

    checks = {
        key: value
        for phase in repeats[0]["phases"]
        for key, value in phase.items()
        if key != "phase"
    }
    checks.update(source["source_checks"])
    if not all(checks.values()):
        raise MemoriaRunnerError(f"Memoria combined checks failed: {checks}")
    summary = {
        "schema_version": 1,
        "status": EXPECTED_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "h100_actor_admission": "forbidden-for-this-revision",
        "source": source,
        "doctor_image": image_contract,
        "matrixone": matrixone,
        "run_count": 2,
        "matrixone_restart_count_per_run": 2,
        "stable_phase_projection_sha256": repeats[0]["phase_projection_sha256"],
        "findings": checks,
        "claim_boundary": (
            "Exact pinned native branch/snapshot/merge/restart component evidence in "
            "legacy shared-database mode; not multi-db, retrieval-quality, active/inactive "
            "paging, paper-result, H100-actor, or publication evidence."
        ),
    }
    _write_once(output / "report.json", _json_bytes(summary))
    files = {
        path.relative_to(output).as_posix(): _sha_path(path)
        for path in sorted(output.rglob("*"))
        if path.is_file() and path.name != "manifest.json"
    }
    manifest = {
        "schema_version": 1,
        "status": EXPECTED_STATUS,
        "files": files,
        "file_count": len(files),
    }
    _write_once(output / "manifest.json", _json_bytes(manifest))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    summary = run(source_root=args.source_root, image=args.image, output=args.output)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
