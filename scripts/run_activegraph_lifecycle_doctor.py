#!/usr/bin/env python3
"""Run and seal the exact-source Active Graph fork/retention falsifier."""

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

from scripts.validate_activegraph_lifecycle_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    EXPECTED_STATUS,
    validate_experiment_contract,
)

DEFAULT_IMAGE = "cotcodec-activegraph-lifecycle:8aedb18-arm64-v1"
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data/results/activegraph-fork-lifecycle/2026-08-16-local-docker-v1"
)
DOCKERFILE = PROJECT_ROOT / "infra/memory-baselines/activegraph/Dockerfile"
DOCTOR = PROJECT_ROOT / "infra/memory-baselines/activegraph/doctor.py"


class ActiveGraphRunnerError(RuntimeError):
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
                raise ActiveGraphRunnerError(f"short write: {path}")
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
        raise ActiveGraphRunnerError(
            f"command failed ({completed.returncode}): {argv!r}\n"
            + completed.stderr.decode(errors="replace")[-8000:]
        )
    return completed


def _source_contract(source_root: Path, experiment: dict[str, Any]) -> dict[str, Any]:
    source = experiment["source"]
    if not source_root.is_dir() or source_root.is_symlink():
        raise ActiveGraphRunnerError("Active Graph source root must be a directory")
    head = _run(["git", "-C", str(source_root), "rev-parse", "HEAD"]).stdout.decode().strip()
    tree = _run(["git", "-C", str(source_root), "rev-parse", "HEAD^{tree}"]).stdout.decode().strip()
    state = _run(
        ["git", "-C", str(source_root), "status", "--porcelain=v1", "--untracked-files=all"]
    ).stdout
    if head != source["revision"] or tree != source["tree"] or state:
        raise ActiveGraphRunnerError("Active Graph source checkout drifted")
    archive = _run(["git", "-C", str(source_root), "archive", "--format=tar", head]).stdout
    checks = {
        "license_sha256": _sha_path(source_root / "LICENSE"),
        "pyproject_sha256": _sha_path(source_root / "pyproject.toml"),
    }
    if _sha(archive) != source["git_archive_tar_sha256"] or checks != {
        "license_sha256": source["license_sha256"],
        "pyproject_sha256": source["pyproject_sha256"],
    }:
        raise ActiveGraphRunnerError("Active Graph source archive or metadata drifted")
    retention = (source_root / "activegraph/store/retention.py").read_text()
    sqlite = (source_root / "activegraph/store/sqlite.py").read_text()
    source_checks = {
        "retention_contract_is_archive_never_delete": (
            "snapshot + archive tier, never deletion" in retention
            and "the archive tier is a table in" in retention
            and "the same store file" in retention
        ),
        "retire_calls_archive_run": "return store.archive_run(archived_at=_now_iso())" in retention,
        "archive_run_moves_rows_not_erases": (
            "Move ALL of this run's rows to the archive tier" in sqlite
            and "INSERT OR IGNORE INTO events_archive" in sqlite
        ),
    }
    if not all(source_checks.values()):
        raise ActiveGraphRunnerError("Active Graph source-level falsifier drifted")
    return {
        "git_sha": head,
        "git_tree": tree,
        "archive": archive,
        "archive_sha256": _sha(archive),
        "archive_bytes": len(archive),
        **checks,
        "source_checks": source_checks,
    }


def _image_contract(image: str, experiment: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
    raw = _run(["docker", "image", "inspect", image]).stdout
    rows = json.loads(raw)
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise ActiveGraphRunnerError("Docker inspect roster drifted")
    inspect = rows[0]
    labels = (inspect.get("Config") or {}).get("Labels") or {}
    source = experiment["source"]
    expected_labels = {
        "org.opencontainers.image.source": source["repository"],
        "org.opencontainers.image.revision": source["revision"],
        "org.opencontainers.image.licenses": source["license"],
        "org.cotcodec.source-tree": source["tree"],
        "org.cotcodec.source-archive-sha256": source["git_archive_tar_sha256"],
        "org.cotcodec.doctor-sha256": _sha_path(DOCTOR),
        "org.cotcodec.discovery-only": "true",
    }
    config = inspect.get("Config") or {}
    image_id = inspect.get("Id")
    if (
        any(labels.get(key) != value for key, value in expected_labels.items())
        or not isinstance(image_id, str)
        or not image_id.startswith("sha256:")
        or inspect.get("Architecture") != "arm64"
        or inspect.get("Os") != "linux"
        or config.get("User") != "65532:65532"
        or set(config.get("Volumes") or {}) != {"/state"}
    ):
        raise ActiveGraphRunnerError("Active Graph doctor image drifted")
    projection = {
        "image_id": image_id,
        "architecture": "arm64",
        "os": "linux",
        "user": "65532:65532",
        "volumes": ["/state"],
        "labels": expected_labels,
    }
    return {
        **projection,
        "inspect_sha256": _sha(raw),
        "inspect_projection_sha256": _sha(
            json.dumps(projection, separators=(",", ":"), sort_keys=True).encode()
        ),
    }, raw


def _phase_argv(*, image_id: str, volume: str, phase: int, canaries: dict[str, str]) -> list[str]:
    return [
        "docker", "run", "--rm", "--pull=never", "--platform", "linux/arm64",
        "--network", "none", "--read-only", "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges", "--pids-limit", "128",
        "--memory", "1g", "--cpus", "2", "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=128m", "--mount",
        f"type=volume,src={volume},dst=/state", "-e", f"COTCODEC_PHASE={phase}",
        "-e", f"COTCODEC_PARENT_CANARY={canaries['parent']}",
        "-e", f"COTCODEC_FORK_CANARY={canaries['fork']}",
        "-e", f"COTCODEC_SIBLING_CANARY={canaries['sibling']}",
        "-e", f"COTCODEC_REJECTED_CANARY={canaries['rejected']}", image_id,
    ]


def _parse_phase(raw: bytes, expected_phase: int) -> dict[str, Any]:
    marker = b"COTCODEC_ACTIVEGRAPH_PHASE="
    rows = [line.split(marker, 1)[1] for line in raw.splitlines() if marker in line]
    if len(rows) != 1:
        raise ActiveGraphRunnerError(f"phase {expected_phase} emitted {len(rows)} report markers")
    payload = json.loads(rows[0])
    if not isinstance(payload, dict) or payload.get("phase") != expected_phase:
        raise ActiveGraphRunnerError(f"phase {expected_phase} report drifted")
    values = [value for key, value in payload.items() if key != "phase"]
    if not values or not all(value is True for value in values):
        raise ActiveGraphRunnerError(f"phase {expected_phase} checks failed: {payload}")
    return payload


def _run_repeat(*, repeat: int, image_id: str) -> tuple[dict[str, Any], dict[str, bytes]]:
    volume = f"cotcodec-activegraph-{secrets.token_hex(5)}"
    canaries = {
        key: f"{key}-{secrets.token_hex(16)}"
        for key in ("parent", "fork", "sibling", "rejected")
    }
    artifacts: dict[str, bytes] = {}
    _run(["docker", "volume", "create", volume])
    try:
        phases: list[dict[str, Any]] = []
        for phase in (1, 2):
            completed = _run(
                _phase_argv(image_id=image_id, volume=volume, phase=phase, canaries=canaries),
                timeout=120,
            )
            raw = completed.stdout + completed.stderr
            artifacts[f"repeat-{repeat}-phase-{phase}.txt"] = raw
            phases.append(_parse_phase(raw, phase))
        projection = {"repeat": repeat, "phases": phases}
        projection["phase_projection_sha256"] = _sha(
            json.dumps(phases, separators=(",", ":"), sort_keys=True).encode()
        )
        return projection, artifacts
    finally:
        subprocess.run(["docker", "volume", "rm", volume], capture_output=True, check=False)


def run(*, source_root: Path, image: str, output: Path) -> dict[str, Any]:
    experiment = validate_experiment_contract()
    output.mkdir(parents=True, exist_ok=False)
    source = _source_contract(source_root.resolve(), experiment)
    image_contract, image_inspect = _image_contract(image, experiment)
    source_archive = source.pop("archive")
    fixed_artifacts = {
        "experiment.yaml": DEFAULT_EXPERIMENT.read_bytes(),
        "Dockerfile": DOCKERFILE.read_bytes(),
        "doctor.py": DOCTOR.read_bytes(),
        "source.tar": source_archive,
        "source-receipt.json": _json_bytes(source),
        "doctor-image-inspect.json": image_inspect,
    }
    for name, data in fixed_artifacts.items():
        _write_once(output / name, data)
    repeats: list[dict[str, Any]] = []
    for repeat in (1, 2):
        projection, artifacts = _run_repeat(repeat=repeat, image_id=image_contract["image_id"])
        for name, data in artifacts.items():
            _write_once(output / name, data)
        _write_once(output / f"repeat-{repeat}.json", _json_bytes(projection))
        repeats.append(projection)
    if repeats[0]["phases"] != repeats[1]["phases"]:
        raise ActiveGraphRunnerError("Active Graph clean-state repeats diverged")
    findings = {
        key: value
        for phase in repeats[0]["phases"]
        for key, value in phase.items()
        if key != "phase"
    }
    findings.update(source["source_checks"])
    if not all(findings.values()):
        raise ActiveGraphRunnerError(f"Active Graph combined checks failed: {findings}")
    summary = {
        "schema_version": 1,
        "status": EXPECTED_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "h100_actor_admission": "forbidden-for-this-revision",
        "source": source,
        "doctor_image": image_contract,
        "run_count": 2,
        "fresh_process_restart_count_per_run": 1,
        "stable_phase_projection_sha256": repeats[0]["phase_projection_sha256"],
        "findings": findings,
        "claim_boundary": (
            "Exact pinned native fork, nested-fork, replay, retirement, archive, restart, "
            "and plaintext-residue behavior; not retrieval quality, active/inactive paging, "
            "model-effect, H100-actor, or publication evidence."
        ),
    }
    _write_once(output / "report.json", _json_bytes(summary))
    files = {
        path.relative_to(output).as_posix(): _sha_path(path)
        for path in sorted(output.rglob("*"))
        if path.is_file() and path.name != "manifest.json"
    }
    _write_once(output / "manifest.json", _json_bytes({
        "schema_version": 1, "status": EXPECTED_STATUS, "files": files, "file_count": len(files)
    }))
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
