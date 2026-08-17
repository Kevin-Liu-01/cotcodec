#!/usr/bin/env python3
"""Seal two clean, contained RecMem lifecycle falsifier repetitions."""

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

from scripts.validate_recmem_consolidation_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    EXPECTED_STATUS,
    validate_experiment_contract,
)

DEFAULT_IMAGE = "cotcodec-recmem-consolidation:a84252f-arm64-v2"
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data/results/recmem-consolidation/2026-08-16-local-docker-v1"
)
DOCKERFILE = PROJECT_ROOT / "infra/memory-baselines/recmem/Dockerfile"
DOCTOR = PROJECT_ROOT / "infra/memory-baselines/recmem/doctor.py"


class RecMemRunnerError(RuntimeError):
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
                raise RecMemRunnerError(f"short write: {path}")
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
    completed = subprocess.run(
        argv,
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    if completed.returncode != 0:
        raise RecMemRunnerError(
            f"command failed ({completed.returncode}): {argv!r}\n"
            + completed.stderr.decode(errors="replace")[-5000:]
        )
    return completed


def _source_contract(source_root: Path, experiment: dict[str, Any]) -> dict[str, Any]:
    source = experiment["source"]
    if not source_root.is_dir() or source_root.is_symlink():
        raise RecMemRunnerError("RecMem source root must be a regular directory")
    head = _run(["git", "-C", str(source_root), "rev-parse", "HEAD"]).stdout.decode().strip()
    tree = _run(
        ["git", "-C", str(source_root), "rev-parse", "HEAD^{tree}"]
    ).stdout.decode().strip()
    status = _run(
        ["git", "-C", str(source_root), "status", "--porcelain=v1", "--untracked-files=all"]
    ).stdout
    if head != source["revision"] or tree != source["tree"] or status:
        raise RecMemRunnerError("RecMem source checkout drifted")
    archive = _run(
        [
            "git",
            "-C",
            str(source_root),
            "archive",
            "--format=tar",
            source["revision"],
        ]
    ).stdout
    if _sha(archive) != source["git_archive_tar_sha256"]:
        raise RecMemRunnerError("RecMem source archive drifted")
    if _sha_path(source_root / "LICENSE") != source["license_sha256"]:
        raise RecMemRunnerError("RecMem license drifted")
    if _sha_path(source_root / "uv.lock") != source["uv_lock_sha256"]:
        raise RecMemRunnerError("RecMem lock drifted")
    return {
        "git_sha": head,
        "git_tree": tree,
        "archive": archive,
        "archive_sha256": _sha(archive),
        "archive_bytes": len(archive),
        "license_sha256": source["license_sha256"],
        "uv_lock_sha256": source["uv_lock_sha256"],
    }


def _image_contract(image: str, experiment: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
    raw = _run(["docker", "image", "inspect", image]).stdout
    try:
        rows = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RecMemRunnerError("Docker inspect is not JSON") from exc
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise RecMemRunnerError("Docker inspect roster drifted")
    inspect = rows[0]
    config = inspect.get("Config") or {}
    labels = config.get("Labels") or {}
    source = experiment["source"]
    expected_labels = {
        "org.opencontainers.image.revision": source["revision"],
        "org.opencontainers.image.licenses": source["license"],
        "org.cotcodec.discovery-only": "true",
        "org.cotcodec.source-tree": source["tree"],
        "org.cotcodec.source-archive-sha256": source["git_archive_tar_sha256"],
        "org.cotcodec.lock-sha256": source["uv_lock_sha256"],
        "org.cotcodec.doctor-sha256": _sha_path(DOCTOR),
    }
    if any(labels.get(key) != value for key, value in expected_labels.items()):
        raise RecMemRunnerError("RecMem image labels drifted")
    image_id = inspect.get("Id")
    if (
        not isinstance(image_id, str)
        or not image_id.startswith("sha256:")
        or inspect.get("Architecture") != "arm64"
        or inspect.get("Os") != "linux"
        or config.get("User") != "65532:65532"
    ):
        raise RecMemRunnerError("RecMem image runtime drifted")
    return (
        {
            "image_id": image_id,
            "architecture": inspect["Architecture"],
            "os": inspect["Os"],
            "inspect_sha256": _sha(raw),
            "labels": expected_labels,
        },
        raw,
    )


def _container_argv(image_id: str, repeat: int) -> list[str]:
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
        "2g",
        "--cpus",
        "2",
        "--user",
        "65532:65532",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=256m,uid=65532,gid=65532,mode=0700",
        "--tmpfs",
        "/state:rw,nosuid,nodev,size=1g,uid=65532,gid=65532,mode=0700",
        image_id,
        "--source-root",
        "/opt/recmem/source",
        "--state-root",
        "/state",
        "--repeat",
        str(repeat),
    ]


def _strict_report(raw: bytes, repeat: int) -> dict[str, Any]:
    marker = b"COTCODEC_RECMEM_REPORT="
    rows = [line[len(marker) :] for line in raw.splitlines() if line.startswith(marker)]
    if len(rows) != 1:
        raise RecMemRunnerError(f"repeat {repeat} emitted {len(rows)} report markers")
    try:
        report = json.loads(rows[0])
    except json.JSONDecodeError as exc:
        raise RecMemRunnerError(f"repeat {repeat} report is not JSON") from exc
    checks = report.get("projection", {}).get("checks", {})
    if (
        report.get("schema_version") != 1
        or report.get("source_revision")
        != "a84252f6e5587fd4a8caac03ec9f6c732b7a7f35"
        or report.get("status") != EXPECTED_STATUS
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("h100_actor_admission") is not False
        or report.get("provider_calls") != 0
        or report.get("model_backend_calls") != 0
        or not isinstance(checks, dict)
        or not checks
        or not all(value is True for value in checks.values())
    ):
        raise RecMemRunnerError(f"repeat {repeat} report contract drifted")
    projection = report.get("projection")
    canonical_projection = json.dumps(
        projection, separators=(",", ":"), sort_keys=True
    ).encode()
    if report.get("projection_sha256") != _sha(canonical_projection):
        raise RecMemRunnerError(f"repeat {repeat} projection digest drifted")
    return report


def run(*, source_root: Path, image: str, output: Path) -> dict[str, Any]:
    experiment = validate_experiment_contract()
    output.mkdir(parents=True, exist_ok=False)
    source = _source_contract(source_root.resolve(), experiment)
    image_contract, inspect_raw = _image_contract(image, experiment)
    _write_once(output / "experiment.yaml", DEFAULT_EXPERIMENT.read_bytes())
    _write_once(output / "Dockerfile", DOCKERFILE.read_bytes())
    _write_once(output / "doctor.py", DOCTOR.read_bytes())
    _write_once(output / "source.tar", source.pop("archive"))
    _write_once(output / "source-receipt.json", _json_bytes(source))
    _write_once(output / "image-inspect.json", inspect_raw)

    reports: list[dict[str, Any]] = []
    for repeat in (1, 2):
        completed = _run(_container_argv(image_contract["image_id"], repeat))
        raw = completed.stdout + completed.stderr
        _write_once(output / f"repeat-{repeat}.txt", raw)
        report = _strict_report(raw, repeat)
        _write_once(output / f"repeat-{repeat}.json", _json_bytes(report))
        reports.append(report)
    if reports[0] != reports[1]:
        raise RecMemRunnerError("RecMem clean-state repetitions diverged")

    summary = {
        "schema_version": 1,
        "status": EXPECTED_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "h100_actor_admission": "forbidden-for-this-revision",
        "source": source,
        "image": image_contract,
        "run_count": 2,
        "stable_projection_sha256": reports[0]["projection_sha256"],
        "findings": {
            "duplicate_retry_non_idempotent": True,
            "trigger_lineage_incomplete": True,
            "failed_merge_loses_prior_episode": True,
            "successful_consolidation_restart_stable": True,
            "conversation_isolation_preserved": True,
        },
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
