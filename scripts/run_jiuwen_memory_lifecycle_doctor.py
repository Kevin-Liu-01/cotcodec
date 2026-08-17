#!/usr/bin/env python3
"""Run and retain the JiuwenMemory file-backend lifecycle falsifier."""

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
from typing import TypeAlias

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validate_jiuwen_memory_lifecycle_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    EXPECTED_STATUS,
    validate_experiment_contract,
)

JSONPrimitive: TypeAlias = None | bool | int | float | str
JSONValue: TypeAlias = JSONPrimitive | list["JSONValue"] | dict[str, "JSONValue"]
JSONObject: TypeAlias = dict[str, JSONValue]
DEFAULT_IMAGE = "cotcodec-jiuwen-memory-lifecycle:600432b-arm64-v1"
DEFAULT_OUTPUT = PROJECT_ROOT / "data/results/jiuwen-memory-lifecycle/2026-08-17-local-docker-v1"
DOCKERFILE = PROJECT_ROOT / "infra/memory-baselines/jiuwen-memory/Dockerfile"
DOCTOR = PROJECT_ROOT / "infra/memory-baselines/jiuwen-memory/lifecycle_doctor.py"
MARKER = b"COTCODEC_JIUWEN_PHASE="


class JiuwenRunnerError(RuntimeError):
    """Raise when source, runtime, or lifecycle evidence drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _json_bytes(value: JSONValue) -> bytes:
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
                raise JiuwenRunnerError(f"short write: {path}")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _run(
    argv: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout_seconds: int = 900,
) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        capture_output=True,
        check=False,
        timeout=timeout_seconds,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.decode(errors="replace")[-8000:]
        raise JiuwenRunnerError(f"command failed ({completed.returncode}): {argv!r}\n{stderr}")
    return completed


def _expected_failure(
    argv: list[str],
    *,
    cwd: Path,
    expected: str,
    env: dict[str, str] | None = None,
) -> bytes:
    completed = subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        capture_output=True,
        check=False,
        timeout=300,
    )
    raw = completed.stdout + completed.stderr
    if completed.returncode == 0 or expected.encode() not in raw:
        raise JiuwenRunnerError(f"expected failure did not reproduce: {argv!r}")
    return raw


def _git_output(source_root: Path, arguments: list[str]) -> bytes:
    completed = _run(["git", "-C", str(source_root), *arguments])
    return completed.stdout


def _source_checks(source_root: Path) -> dict[str, bool]:
    vector = (
        source_root / "jiuwen_memory/foundation/store/index/file_index/_vector_index.py"
    ).read_text(encoding="utf-8")
    file_index = (
        source_root / "jiuwen_memory/foundation/store/index/file_index/file_memory_index.py"
    ).read_text(encoding="utf-8")
    return {
        "file_index_uses_global_memory_id_primary_key": "mem_id TEXT PRIMARY KEY" in vector,
        "file_index_upsert_overwrites_on_global_memory_id": (
            "ON CONFLICT(mem_id) DO UPDATE SET" in vector
        ),
        "file_index_migration_version_is_process_local": (
            "self._schema_version = 0" in file_index
            and "return self._schema_version" in file_index
            and "self._schema_version = version" in file_index
        ),
        "file_index_exposes_native_user_scope_delete": (
            "async def delete_by_user_and_scope" in file_index
        ),
        "file_index_does_not_enable_sqlite_secure_delete": ("PRAGMA secure_delete" not in vector),
    }


def _packaging_checks(source_root: Path) -> tuple[dict[str, bool], dict[str, bytes]]:
    artifacts: dict[str, bytes] = {}
    artifacts["uv-lock-check.txt"] = _expected_failure(
        ["uv", "lock", "--check"],
        cwd=source_root,
        expected="needs to be updated",
    )
    with tempfile.TemporaryDirectory(prefix="cotcodec-jiuwen-extra-") as directory:
        env = dict(os.environ)
        env["UV_PROJECT_ENVIRONMENT"] = str(Path(directory) / "environment")
        artifacts["uv-file-index-extra.txt"] = _expected_failure(
            ["uv", "sync", "--frozen", "--extra", "file-index", "--no-install-project"],
            cwd=source_root,
            expected="Extra `file-index` is not defined",
            env=env,
        )
    with tempfile.TemporaryDirectory(prefix="cotcodec-jiuwen-base-") as directory:
        environment_root = Path(directory) / "environment"
        env = dict(os.environ)
        env["UV_PROJECT_ENVIRONMENT"] = str(environment_root)
        sync = _run(
            ["uv", "sync", "--frozen", "--no-dev", "--extra", "sqlite", "--no-install-project"],
            cwd=source_root,
            env=env,
        )
        artifacts["uv-frozen-base-sync.txt"] = sync.stdout + sync.stderr
        artifacts["uv-frozen-base-import.txt"] = _expected_failure(
            [str(environment_root / "bin/python"), "-c", "import jiuwen_memory.memory_core"],
            cwd=source_root,
            expected="No module named 'gmssl'",
            env=env,
        )
    checks = {
        "committed_lock_fails_uv_check": True,
        "committed_lock_omits_declared_file_index_extra": True,
        "frozen_base_environment_cannot_import_declared_package": True,
    }
    return checks, artifacts


def _source_contract(
    source_root: Path, source: JSONObject
) -> tuple[JSONObject, bytes, dict[str, bytes]]:
    head = _git_output(source_root, ["rev-parse", "HEAD"]).decode().strip()
    tree = _git_output(source_root, ["rev-parse", "HEAD^{tree}"]).decode().strip()
    state = _git_output(source_root, ["status", "--porcelain=v1", "--untracked-files=all"])
    if head != source["revision"] or tree != source["tree"] or state:
        raise JiuwenRunnerError("JiuwenMemory source checkout drifted")
    archive = _git_output(source_root, ["archive", "--format=tar", head])
    hashes = {
        "license_sha256": _sha_path(source_root / "LICENSE"),
        "pyproject_sha256": _sha_path(source_root / "pyproject.toml"),
        "uv_lock_sha256": _sha_path(source_root / "uv.lock"),
    }
    expected_hashes = {key: source[key] for key in hashes}
    if hashes != expected_hashes or _sha(archive) != source["git_archive_tar_sha256"]:
        raise JiuwenRunnerError("JiuwenMemory source archive or metadata drifted")
    source_checks = _source_checks(source_root)
    if not all(source_checks.values()):
        raise JiuwenRunnerError("JiuwenMemory source-level checks drifted")
    packaging_checks, packaging_artifacts = _packaging_checks(source_root)
    receipt: JSONObject = {
        "revision": head,
        "tree": tree,
        "archive_sha256": _sha(archive),
        "archive_bytes": len(archive),
        **hashes,
        "source_checks": source_checks,
        "packaging_checks": packaging_checks,
    }
    return receipt, archive, packaging_artifacts


def _extract_source(archive: bytes, destination: Path) -> None:
    destination.mkdir(parents=True)
    with tarfile.open(fileobj=BytesIO(archive), mode="r:") as source:
        members = source.getmembers()
        if any(
            member.name.startswith("/") or ".." in Path(member.name).parts for member in members
        ):
            raise JiuwenRunnerError("JiuwenMemory source archive contains an unsafe path")
        source.extractall(destination, filter="data")


def _build_image(
    image: str,
    archive: bytes,
    source: JSONObject,
    runtime: JSONObject,
) -> bytes:
    with tempfile.TemporaryDirectory(prefix="cotcodec-jiuwen-build-") as directory:
        context = Path(directory)
        _extract_source(archive, context / "jiuwen-source")
        shutil.copy2(DOCTOR, context / "lifecycle_doctor.py")
        argv = [
            "docker",
            "build",
            "--pull=false",
            "--platform",
            "linux/arm64",
            "--tag",
            image,
            "--file",
            str(DOCKERFILE),
            "--build-arg",
            f"COTCODEC_BASE_IMAGE={runtime['base_image']}",
            "--build-arg",
            f"COTCODEC_DOCTOR_SHA256={_sha_path(DOCTOR)}",
            "--build-arg",
            f"COTCODEC_SOURCE_ARCHIVE_SHA256={source['git_archive_tar_sha256']}",
            "--build-arg",
            f"COTCODEC_SOURCE_TREE={source['tree']}",
            str(context),
        ]
        completed = _run(argv, timeout_seconds=1200)
        return completed.stdout + completed.stderr


def _image_contract(image: str, source: JSONObject) -> tuple[JSONObject, bytes]:
    raw = _run(["docker", "image", "inspect", image]).stdout
    rows = json.loads(raw)
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise JiuwenRunnerError("JiuwenMemory image inspect roster drifted")
    inspect = rows[0]
    config = inspect.get("Config") or {}
    labels = config.get("Labels") or {}
    expected_labels = {
        "org.opencontainers.image.source": source["repository"],
        "org.opencontainers.image.revision": source["revision"],
        "org.opencontainers.image.licenses": source["license"],
        "org.cotcodec.source-tree": source["tree"],
        "org.cotcodec.source-archive-sha256": source["git_archive_tar_sha256"],
        "org.cotcodec.doctor-sha256": _sha_path(DOCTOR),
        "org.cotcodec.discovery-only": "true",
        "org.cotcodec.repair-overlay": ("gmssl==3.2.2,pycryptodomex==3.23.0,sqlite-vec==0.1.9"),
    }
    image_id = inspect.get("Id")
    valid = isinstance(image_id, str) and image_id.startswith("sha256:")
    valid = valid and inspect.get("Architecture") == "arm64" and inspect.get("Os") == "linux"
    valid = valid and config.get("User") == "65532:65532"
    valid = valid and set(config.get("Volumes") or {}) == {"/state"}
    valid = valid and all(labels.get(key) == value for key, value in expected_labels.items())
    if not valid:
        raise JiuwenRunnerError("JiuwenMemory image provenance drifted")
    receipt: JSONObject = {
        "image_id": image_id,
        "architecture": "arm64",
        "os": "linux",
        "user": "65532:65532",
        "volumes": ["/state"],
        "labels": expected_labels,
        "inspect_sha256": _sha(raw),
    }
    return receipt, raw


def _phase_argv(image_id: str, volume: str, phase: int, hash_seed: int) -> list[str]:
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
        "128",
        "--memory",
        "1g",
        "--cpus",
        "2",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=128m,uid=65532,gid=65532",
        "--mount",
        f"type=volume,src={volume},dst=/state",
        "-e",
        f"COTCODEC_PHASE={phase}",
        "-e",
        f"PYTHONHASHSEED={hash_seed}",
        image_id,
    ]


def _parse_phase(raw: bytes, expected_phase: int) -> JSONObject:
    rows = [line.split(MARKER, 1)[1] for line in raw.splitlines() if MARKER in line]
    if len(rows) != 1:
        raise JiuwenRunnerError(f"phase {expected_phase} emitted {len(rows)} markers")
    payload = json.loads(rows[0])
    if not isinstance(payload, dict) or payload.get("phase") != expected_phase:
        raise JiuwenRunnerError(f"phase {expected_phase} report drifted")
    checks = payload.get("checks")
    if (
        not isinstance(checks, dict)
        or not checks
        or not all(value is True for value in checks.values())
    ):
        raise JiuwenRunnerError(f"phase {expected_phase} checks failed")
    return payload


def _stable_projection(phases: list[JSONObject]) -> list[JSONObject]:
    projection: list[JSONObject] = []
    for phase in phases:
        row: JSONObject = {"phase": phase["phase"], "checks": phase["checks"]}
        metrics = phase.get("metrics")
        if isinstance(metrics, dict):
            row["residue_canaries"] = metrics.get("residue_canaries")
        projection.append(row)
    return projection


def _run_repeat(repeat: int, image_id: str, hash_seed: int) -> tuple[JSONObject, dict[str, bytes]]:
    volume = f"cotcodec-jiuwen-{secrets.token_hex(6)}"
    artifacts: dict[str, bytes] = {}
    _run(["docker", "volume", "create", volume])
    try:
        phases: list[JSONObject] = []
        for phase in (1, 2):
            completed = _run(_phase_argv(image_id, volume, phase, hash_seed), timeout_seconds=180)
            raw = completed.stdout + completed.stderr
            artifacts[f"repeat-{repeat}-phase-{phase}.txt"] = raw
            phases.append(_parse_phase(raw, phase))
        projection = _stable_projection(phases)
        report: JSONObject = {
            "repeat": repeat,
            "python_hash_seed": hash_seed,
            "phases": phases,
            "stable_projection": projection,
            "stable_projection_sha256": _sha(
                json.dumps(projection, separators=(",", ":"), sort_keys=True).encode()
            ),
        }
        return report, artifacts
    finally:
        subprocess.run(["docker", "volume", "rm", volume], capture_output=True, check=False)


def _findings(source_receipt: JSONObject, repeats: list[JSONObject]) -> dict[str, bool]:
    findings: dict[str, bool] = {}
    for group in (source_receipt["source_checks"], source_receipt["packaging_checks"]):
        if not isinstance(group, dict):
            raise JiuwenRunnerError("JiuwenMemory source finding group drifted")
        findings.update({name: value is True for name, value in group.items()})
    phases = repeats[0]["phases"]
    if not isinstance(phases, list):
        raise JiuwenRunnerError("JiuwenMemory phase roster drifted")
    for phase in phases:
        if not isinstance(phase, dict) or not isinstance(phase.get("checks"), dict):
            raise JiuwenRunnerError("JiuwenMemory phase check roster drifted")
        findings.update({name: value is True for name, value in phase["checks"].items()})
    owners = [repeat["phases"][0]["metrics"]["migrated_chunk_row"][0] for repeat in repeats]
    findings["migration_index_owner_depends_on_process_hash_order"] = owners == [
        "user-a",
        "user-b",
    ]
    if not all(findings.values()):
        raise JiuwenRunnerError("JiuwenMemory combined findings failed")
    return findings


def run(source_root: Path, image: str, output: Path) -> JSONObject:
    experiment = validate_experiment_contract()
    source = experiment["source"]
    runtime = experiment["runtime"]
    if not isinstance(source, dict) or not isinstance(runtime, dict):
        raise JiuwenRunnerError("JiuwenMemory contract sections drifted")
    source_receipt, archive, packaging_artifacts = _source_contract(source_root, source)
    build_log = _build_image(image, archive, source, runtime)
    image_receipt, image_inspect = _image_contract(image, source)
    repeats: list[JSONObject] = []
    run_artifacts: dict[str, bytes] = {}
    hash_seeds = runtime.get("python_hash_seeds")
    if hash_seeds != [1, 7]:
        raise JiuwenRunnerError("JiuwenMemory process hash-seed roster drifted")
    for repeat, hash_seed in enumerate(hash_seeds, start=1):
        report, artifacts = _run_repeat(repeat, str(image_receipt["image_id"]), hash_seed)
        repeats.append(report)
        run_artifacts.update(artifacts)
    first_projection = repeats[0]["stable_projection"]
    if first_projection != repeats[1]["stable_projection"]:
        raise JiuwenRunnerError("JiuwenMemory clean-state repeats diverged")
    findings = _findings(source_receipt, repeats)
    summary: JSONObject = {
        "schema_version": 1,
        "status": EXPECTED_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "h100_actor_admission": "forbidden-for-this-revision",
        "source": source_receipt,
        "doctor_image": image_receipt,
        "run_count": 2,
        "fresh_process_restart_count_per_run": 1,
        "stable_projection_sha256": repeats[0]["stable_projection_sha256"],
        "findings": findings,
        "claim_boundary": experiment["claim_boundary"],
    }
    output.mkdir(parents=True, exist_ok=False)
    fixed_artifacts = {
        "experiment.yaml": DEFAULT_EXPERIMENT.read_bytes(),
        "Dockerfile": DOCKERFILE.read_bytes(),
        "lifecycle_doctor.py": DOCTOR.read_bytes(),
        "source.tar": archive,
        "source-receipt.json": _json_bytes(source_receipt),
        "doctor-image-inspect.json": image_inspect,
        "docker-build.txt": build_log,
        **packaging_artifacts,
        **run_artifacts,
    }
    for name, data in fixed_artifacts.items():
        _write_once(output / name, data)
    for repeat, report in enumerate(repeats, start=1):
        _write_once(output / f"repeat-{repeat}.json", _json_bytes(report))
    _write_once(output / "report.json", _json_bytes(summary))
    files = {
        path.relative_to(output).as_posix(): _sha_path(path)
        for path in sorted(output.rglob("*"))
        if path.is_file() and path.name != "manifest.json"
    }
    manifest: JSONObject = {
        "schema_version": 1,
        "status": EXPECTED_STATUS,
        "file_count": len(files),
        "files": files,
    }
    _write_once(output / "manifest.json", _json_bytes(manifest))
    return summary


def main() -> int:
    """Run the default JiuwenMemory lifecycle falsifier."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    summary = run(arguments.source_root.resolve(), arguments.image, arguments.output.resolve())
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
