#!/usr/bin/env python3
"""Build and run the exact-source Infini Memory lifecycle doctor twice."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
import tarfile
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validate_infini_memory_lifecycle_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    EXPECTED_STATUS,
    validate_experiment_contract,
)

DEFAULT_SOURCE = PROJECT_ROOT / "raw/baselines/infini-memory"
DEFAULT_IMAGE = "cotcodec-infini-memory-lifecycle:ddac08e-arm64-v1"
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "data/results/infini-memory-lifecycle/2026-08-26-local-docker-v1"
)
DOCKERFILE = PROJECT_ROOT / "infra/memory-baselines/infini-memory/Dockerfile"
DOCTOR = PROJECT_ROOT / "infra/memory-baselines/infini-memory/doctor.py"


class InfiniMemoryLifecycleRunnerError(RuntimeError):
    """Raised when source, image, execution, or retained evidence drifts."""


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
                raise InfiniMemoryLifecycleRunnerError(f"short write: {path}")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _run(argv: list[str], *, timeout: int = 1200) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(argv, capture_output=True, check=False, timeout=timeout)
    if completed.returncode:
        raise InfiniMemoryLifecycleRunnerError(
            f"command failed ({completed.returncode}): {argv!r}\n"
            + completed.stdout.decode(errors="replace")[-6000:]
            + completed.stderr.decode(errors="replace")[-6000:]
        )
    return completed


def _source_contract(source_root: Path, experiment: dict[str, Any]) -> dict[str, Any]:
    source = experiment["source"]
    if not source_root.is_dir() or source_root.is_symlink():
        raise InfiniMemoryLifecycleRunnerError(
            "Infini Memory source root must be a real directory"
        )
    revision = _run(["git", "-C", str(source_root), "rev-parse", "HEAD"]).stdout.decode().strip()
    tree = _run(
        ["git", "-C", str(source_root), "rev-parse", "HEAD^{tree}"]
    ).stdout.decode().strip()
    status = _run(
        ["git", "-C", str(source_root), "status", "--porcelain=v1", "--untracked-files=all"]
    ).stdout
    if revision != source["revision"] or tree != source["tree"] or status:
        raise InfiniMemoryLifecycleRunnerError("Infini Memory source checkout drifted")
    archive = _run(
        ["git", "-C", str(source_root), "archive", "--format=tar", revision]
    ).stdout
    exact = {
        name: _sha_path(source_root / name) for name in source["exact_source_files"]
    }
    manager = (source_root / "src/infini_memory/manager.py").read_text(
        encoding="utf-8"
    )
    static_source_checks = {
        "manager_joins_unvalidated_user_id": (
            "self.data_dir = self.root / data_root / user_id" in manager
        ),
        "recursive_user_delete_joins_unvalidated_user_id": (
            "user_dir = Path(root) / data_root / user_id" in manager
            and "shutil.rmtree(user_dir)" in manager
        ),
        "invalid_index_silently_loads_empty": (
            'return {"docs": []}' in manager
            and "return json.loads(self.index_path.read_text" in manager
        ),
        "update_writes_markdown_before_index": (
            manager.index("path.write_text(new_content")
            < manager.index("self._save_index(idx)", manager.index("def update_doc("))
        ),
        "delete_unlinks_markdown_before_index": (
            manager.index("path.unlink()", manager.index("def delete_doc("))
            < manager.index("self._save_index(idx)", manager.index("def delete_doc("))
        ),
    }
    if (
        _sha(archive) != source["git_archive_tar_sha256"]
        or _sha_path(source_root / "LICENSE") != source["license_sha256"]
        or _sha_path(source_root / "pyproject.toml") != source["pyproject_sha256"]
        or _sha_path(source_root / "uv.lock") != source["uv_lock_sha256"]
        or exact != source["exact_source_files"]
        or not all(static_source_checks.values())
    ):
        raise InfiniMemoryLifecycleRunnerError("Infini Memory source receipt drifted")
    return {
        "revision": revision,
        "tree": tree,
        "archive": archive,
        "archive_sha256": _sha(archive),
        "archive_bytes": len(archive),
        "license_sha256": source["license_sha256"],
        "pyproject_sha256": source["pyproject_sha256"],
        "uv_lock_sha256": source["uv_lock_sha256"],
        "exact_source_files": exact,
        "static_source_checks": static_source_checks,
    }


def _build_image(
    *, source_archive: bytes, source: dict[str, Any], image: str
) -> tuple[bytes, dict[str, Any], bytes]:
    with tempfile.TemporaryDirectory(prefix="cotcodec-infini-memory-build-") as raw:
        root = Path(raw)
        source_dir = root / "source"
        source_dir.mkdir()
        with tarfile.open(fileobj=BytesIO(source_archive), mode="r:") as archive:
            archive.extractall(source_dir, filter="data")
        shutil.copy2(DOCKERFILE, root / "Dockerfile")
        shutil.copy2(DOCTOR, root / "doctor.py")
        completed = _run(
            [
                "docker",
                "build",
                "--pull=false",
                "--platform",
                "linux/arm64",
                "--build-arg",
                f"SOURCE_REVISION={source['revision']}",
                "--build-arg",
                f"SOURCE_TREE={source['tree']}",
                "--build-arg",
                f"SOURCE_ARCHIVE_SHA256={source['archive_sha256']}",
                "--build-arg",
                f"DOCTOR_SHA256={_sha_path(DOCTOR)}",
                "-t",
                image,
                str(root),
            ],
            timeout=1800,
        )
        build_log = completed.stdout + completed.stderr
    raw_inspect = _run(["docker", "image", "inspect", image]).stdout
    rows = json.loads(raw_inspect)
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise InfiniMemoryLifecycleRunnerError("Infini Memory image inspection drifted")
    inspect = rows[0]
    config = inspect.get("Config") or {}
    labels = config.get("Labels") or {}
    expected_labels = {
        "org.opencontainers.image.source": "https://github.com/infinigence/Infini-Memory",
        "org.opencontainers.image.revision": source["revision"],
        "org.opencontainers.image.licenses": "Apache-2.0",
        "org.cotcodec.source-tree": source["tree"],
        "org.cotcodec.source-archive-sha256": source["archive_sha256"],
        "org.cotcodec.doctor-sha256": _sha_path(DOCTOR),
        "org.cotcodec.discovery-only": "true",
    }
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
        raise InfiniMemoryLifecycleRunnerError("Infini Memory image provenance drifted")
    return (
        build_log,
        {
            "image_id": image_id,
            "architecture": "arm64",
            "os": "linux",
            "user": "65532:65532",
            "volumes": ["/state"],
            "labels": expected_labels,
        },
        raw_inspect,
    )


def _phase_argv(*, image_id: str, volume: str, phase: int, token: str) -> list[str]:
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
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=256m",
        "--mount",
        f"type=volume,src={volume},dst=/state",
        "-e",
        f"COTCODEC_PHASE={phase}",
        "-e",
        f"COTCODEC_RUN_TOKEN={token}",
        image_id,
    ]


def _parse_phase(raw: bytes, expected_phase: int) -> dict[str, Any]:
    marker = b"COTCODEC_INFINI_MEMORY_PHASE="
    rows = [line.split(marker, 1)[1] for line in raw.splitlines() if marker in line]
    if len(rows) != 1:
        raise InfiniMemoryLifecycleRunnerError(
            f"Infini Memory phase {expected_phase} emitted {len(rows)} markers"
        )
    payload = json.loads(rows[0])
    checks = payload.get("checks") if isinstance(payload, dict) else None
    if (
        not isinstance(payload, dict)
        or payload.get("phase") != expected_phase
        or not isinstance(checks, dict)
        or not checks
        or not all(value is True for value in checks.values())
        or not isinstance(payload.get("metrics"), dict)
    ):
        raise InfiniMemoryLifecycleRunnerError(
            f"Infini Memory phase {expected_phase} report drifted"
        )
    return payload


def _run_repeat(
    *, repeat: int, image_id: str
) -> tuple[dict[str, Any], dict[str, bytes]]:
    volume = f"cotcodec-infini-memory-{secrets.token_hex(5)}"
    token = secrets.token_hex(8).upper()
    artifacts: dict[str, bytes] = {}
    _run(["docker", "volume", "create", volume])
    try:
        phases: list[dict[str, Any]] = []
        for phase in (1, 2, 3, 4):
            completed = _run(
                _phase_argv(
                    image_id=image_id, volume=volume, phase=phase, token=token
                ),
                timeout=600,
            )
            raw = completed.stdout + completed.stderr
            artifacts[f"repeat-{repeat}-phase-{phase}.txt"] = raw
            phases.append(_parse_phase(raw, phase))
        stable_projection = [row["checks"] for row in phases]
        return (
            {
                "repeat": repeat,
                "phase_count": len(phases),
                "fresh_process_restart_count": len(phases) - 1,
                "phases": phases,
                "stable_projection": stable_projection,
                "stable_projection_sha256": _sha(
                    json.dumps(
                        stable_projection, separators=(",", ":"), sort_keys=True
                    ).encode()
                ),
            },
            artifacts,
        )
    finally:
        subprocess.run(
            ["docker", "volume", "rm", volume], capture_output=True, check=False
        )


def run(*, source_root: Path, image: str, output: Path) -> dict[str, Any]:
    experiment = validate_experiment_contract()
    source = _source_contract(source_root.resolve(), experiment)
    source_archive = source.pop("archive")
    output.mkdir(parents=True, exist_ok=False)
    build_log, image_contract, image_inspect = _build_image(
        source_archive=source_archive, source=source, image=image
    )
    pip_freeze = _run(
        [
            "docker",
            "run",
            "--rm",
            "--pull=never",
            "--network",
            "none",
            "--entrypoint",
            "uv",
            image_contract["image_id"],
            "--cache-dir",
            "/tmp/uv-cache",
            "pip",
            "freeze",
            "--python",
            "/opt/infini-memory/.venv/bin/python",
        ],
        timeout=120,
    ).stdout
    fixed = {
        "Dockerfile": DOCKERFILE.read_bytes(),
        "doctor.py": DOCTOR.read_bytes(),
        "docker-build.txt": build_log,
        "doctor-image-inspect.json": image_inspect,
        "experiment.yaml": DEFAULT_EXPERIMENT.read_bytes(),
        "pip-freeze.txt": pip_freeze,
        "source-receipt.json": _json_bytes(source),
        "source.tar": source_archive,
    }
    for name, data in fixed.items():
        _write_once(output / name, data)

    repeats: list[dict[str, Any]] = []
    for repeat in (1, 2):
        projection, artifacts = _run_repeat(
            repeat=repeat, image_id=image_contract["image_id"]
        )
        for name, data in artifacts.items():
            _write_once(output / name, data)
        _write_once(output / f"repeat-{repeat}.json", _json_bytes(projection))
        repeats.append(projection)
    if repeats[0]["stable_projection"] != repeats[1]["stable_projection"]:
        raise InfiniMemoryLifecycleRunnerError(
            "Infini Memory clean-state projections diverged"
        )
    findings = {
        key: value
        for phase in repeats[0]["phases"]
        for key, value in phase["checks"].items()
    }
    findings.update(source["static_source_checks"])
    if not all(findings.values()):
        raise InfiniMemoryLifecycleRunnerError("Infini Memory combined findings failed")
    report = {
        "schema_version": 1,
        "status": EXPECTED_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "h100_actor_admission": "forbidden-for-this-revision",
        "source": source,
        "doctor_image": image_contract,
        "run_count": 2,
        "fresh_process_restart_count_per_run": 3,
        "stable_projection_sha256": repeats[0]["stable_projection_sha256"],
        "findings": findings,
        "write_path_diagnostics": [
            repeat["phases"][2]["metrics"]["write_path_diagnostic"]
            for repeat in repeats
        ],
        "post_delete_plaintext_residue_paths": [
            repeat["phases"][2]["metrics"]["post_delete_plaintext_residue_paths"]
            for repeat in repeats
        ],
        "claim_boundary": experiment["claim_boundary"],
    }
    _write_once(output / "report.json", _json_bytes(report))
    files = {
        path.relative_to(output).as_posix(): _sha_path(path)
        for path in sorted(output.rglob("*"))
        if path.is_file() and path.name != "manifest.json"
    }
    _write_once(
        output / "manifest.json",
        _json_bytes(
            {
                "schema_version": 1,
                "status": EXPECTED_STATUS,
                "file_count": len(files),
                "files": files,
            }
        ),
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = run(source_root=args.source_root, image=args.image, output=args.output)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
