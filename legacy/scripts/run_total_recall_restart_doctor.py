#!/usr/bin/env python3
"""Reproduce Total Recall's native auto-demotion restart defect in Docker."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validate_total_recall_experiment import (  # noqa: E402
    validate_experiment_contract,
)

SOURCE_ROOT = PROJECT_ROOT / "raw" / "baselines" / "total-recall"
DOCTOR_ROOT = PROJECT_ROOT / "infra" / "memory-baselines" / "total-recall"
EXPERIMENT = (
    PROJECT_ROOT
    / "experiments"
    / "memory"
    / "stage3-total-recall-lifecycle-doctor.yaml"
)
EXPECTED_GIT_SHA = "a2630f671be9b12df8b8ac78df9d26f7053d2fa9"
EXPECTED_GIT_TREE = "6d62153e3db4026d2146a80251146f9bc3efca68"
EXPECTED_LICENSE_SHA256 = (
    "d97ac8afe40f62ed6f5bffe8dd941a1fac3543b6c68475f6f4e5923f7c128f15"
)
EXPECTED_SOURCE_ARCHIVE_SHA256 = (
    "19c7e803e6887c740b841043d6a86980f59947b51e6b282a155c477fc37a1338"
)
DOTNET_IMAGE = (
    "mcr.microsoft.com/dotnet/sdk:10.0.100@"
    "sha256:4c85fffe3c700195278ea4f86ca47ecac394da6d91b8fd3282fde63807e26659"
)
NODE_IMAGE = (
    "node:20.19.4-bookworm-slim@"
    "sha256:ea5377506163eeea3b3b163b10d74d7e82d735dc89435d3f54f1a783afc83d89"
)
DEFAULT_IMAGE_TAG = "cotcodec-total-recall-restart-doctor:a2630f6-arm64-v1"
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data"
    / "results"
    / "total-recall-lifecycle"
    / "2026-08-14-restart-doctor"
)
MAX_ARCHIVE_MEMBERS = 20_000
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024


class DoctorError(RuntimeError):
    """Raised when the negative doctor cannot be reproduced honestly."""


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_path(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise DoctorError(f"expected regular file: {path}")
    return _sha256_bytes(path.read_bytes())


def _run(
    argv: list[str],
    *,
    cwd: Path | None = None,
    input_bytes: bytes | None = None,
    capture: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        argv,
        cwd=cwd,
        input=input_bytes,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        check=False,
    )
    if completed.returncode != 0:
        stderr = (completed.stderr or b"").decode("utf-8", errors="replace")
        raise DoctorError(f"command failed ({completed.returncode}): {argv!r}\n{stderr}")
    return completed


def _git_text(*args: str) -> str:
    return _run(["git", *args], cwd=SOURCE_ROOT).stdout.decode().strip()


def _verify_source() -> dict[str, Any]:
    if _git_text("rev-parse", "HEAD") != EXPECTED_GIT_SHA:
        raise DoctorError("Total Recall source HEAD drifted")
    if _git_text("rev-parse", "HEAD^{tree}") != EXPECTED_GIT_TREE:
        raise DoctorError("Total Recall source tree drifted")
    if _git_text("status", "--porcelain"):
        raise DoctorError("Total Recall source checkout must be clean")
    license_path = SOURCE_ROOT / "LICENSE"
    if _sha256_path(license_path) != EXPECTED_LICENSE_SHA256:
        raise DoctorError("Total Recall license file drifted")
    archive = _run(
        ["git", "archive", "--format=tar", EXPECTED_GIT_SHA], cwd=SOURCE_ROOT
    ).stdout
    archive_sha = _sha256_bytes(archive)
    if archive_sha != EXPECTED_SOURCE_ARCHIVE_SHA256:
        raise DoctorError("Total Recall source archive drifted")
    return {
        "repository": "https://github.com/strvmarv/total-recall",
        "git_sha": EXPECTED_GIT_SHA,
        "git_tree": EXPECTED_GIT_TREE,
        "git_archive_sha256": archive_sha,
        "license": "MIT",
        "license_sha256": EXPECTED_LICENSE_SHA256,
        "worktree_clean": True,
        "archive_bytes": len(archive),
        "archive": archive,
    }


def _extract_archive(archive: bytes, destination: Path) -> None:
    total = 0
    seen: set[str] = set()
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as bundle:
        members = bundle.getmembers()
        if not members or len(members) > MAX_ARCHIVE_MEMBERS:
            raise DoctorError("source archive member count is invalid")
        for member in members:
            path = PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts or not path.parts:
                raise DoctorError(f"unsafe source archive path: {member.name}")
            normalized = path.as_posix()
            if normalized in seen:
                raise DoctorError(f"duplicate source archive path: {normalized}")
            seen.add(normalized)
            if member.isdir():
                (destination / normalized).mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                raise DoctorError(f"unsupported source archive member: {normalized}")
            total += member.size
            if total > MAX_ARCHIVE_BYTES:
                raise DoctorError("source archive exceeds uncompressed byte ceiling")
            target = destination / normalized
            target.parent.mkdir(parents=True, exist_ok=True)
            stream = bundle.extractfile(member)
            if stream is None:
                raise DoctorError(f"source archive member has no bytes: {normalized}")
            with target.open("xb") as output:
                shutil.copyfileobj(stream, output)
            target.chmod(member.mode & 0o777)


def _prepare_context(source_receipt: dict[str, Any], context: Path) -> dict[str, Any]:
    _extract_archive(source_receipt["archive"], context)
    shutil.copytree(DOCTOR_ROOT / "doctor", context / "doctor", dirs_exist_ok=False)
    shutil.copy2(DOCTOR_ROOT / "Dockerfile.restart-doctor", context / "Dockerfile")
    inputs = {
        "Dockerfile": _sha256_path(context / "Dockerfile"),
        "doctor/Program.cs": _sha256_path(context / "doctor" / "Program.cs"),
        "doctor/TotalRecall.RestartDoctor.csproj": _sha256_path(
            context / "doctor" / "TotalRecall.RestartDoctor.csproj"
        ),
        "doctor/packages.lock.json": _sha256_path(
            context / "doctor" / "packages.lock.json"
        ),
        "package-lock.json": _sha256_path(context / "package-lock.json"),
        "global.json": _sha256_path(context / "global.json"),
    }
    return inputs


def _strict_json(data: bytes, label: str) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise DoctorError(f"{label} contains non-finite value {value}")

    try:
        value = json.loads(data, parse_constant=reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DoctorError(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise DoctorError(f"{label} must be a JSON object")
    return value


def _write_once(path: Path, data: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise DoctorError(f"short write for {path}")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def _run_doctor_complete(output: Path, image_tag: str, rebuild: bool) -> dict[str, Any]:
    experiment = validate_experiment_contract(EXPERIMENT)
    if output.exists():
        raise DoctorError(f"output path already exists: {output}")
    output.mkdir(parents=True, mode=0o700)
    source_receipt = _verify_source()
    archive = source_receipt.pop("archive")
    source_receipt["archive_sha256_reverified"] = _sha256_bytes(archive)

    with tempfile.TemporaryDirectory(prefix="cotcodec-total-recall-doctor-") as tmp:
        context = Path(tmp)
        source_for_context = dict(source_receipt)
        source_for_context["archive"] = archive
        input_receipt = _prepare_context(source_for_context, context)
        input_receipt.update(
            {
                "experiments/memory/stage3-total-recall-lifecycle-doctor.yaml": (
                    _sha256_path(EXPERIMENT)
                ),
                "scripts/run_total_recall_restart_doctor.py": _sha256_path(
                    Path(__file__).resolve()
                ),
                "scripts/validate_total_recall_experiment.py": _sha256_path(
                    PROJECT_ROOT / "scripts" / "validate_total_recall_experiment.py"
                ),
            }
        )
        if (
            input_receipt["doctor/packages.lock.json"]
            != experiment["execution"]["nuget_lock_sha256"]
        ):
            raise DoctorError("doctor NuGet lock differs from experiment contract")
        build_argv = [
            "docker",
            "build",
            "--platform",
            "linux/arm64",
            "--build-arg",
            f"COTCODEC_TOTAL_RECALL_GIT_SHA={EXPECTED_GIT_SHA}",
            "--build-arg",
            f"COTCODEC_TOTAL_RECALL_SOURCE_SHA256={EXPECTED_SOURCE_ARCHIVE_SHA256}",
            "--tag",
            image_tag,
            str(context),
        ]
        if rebuild:
            build_argv.insert(-1, "--no-cache")
        _run(build_argv, capture=False)

    inspect_value = json.loads(
        _run(["docker", "image", "inspect", image_tag]).stdout,
        parse_constant=lambda value: (_ for _ in ()).throw(
            DoctorError(f"docker inspect contains non-finite value {value}")
        ),
    )
    if not isinstance(inspect_value, list) or len(inspect_value) != 1:
        raise DoctorError("docker image inspection must contain exactly one image")
    image = inspect_value[0]
    if not isinstance(image, dict):
        raise DoctorError("docker image inspection row is invalid")
    image_id = image.get("Id")
    architecture = image.get("Architecture")
    labels = image.get("Config", {}).get("Labels", {})
    if not isinstance(image_id, str) or not image_id.startswith("sha256:"):
        raise DoctorError("docker image ID is invalid")
    if architecture != "arm64":
        raise DoctorError("restart doctor image must be linux/arm64")
    expected_labels = {
        "org.opencontainers.image.revision": EXPECTED_GIT_SHA,
        "org.cotcodec.total-recall-source-sha256": EXPECTED_SOURCE_ARCHIVE_SHA256,
        "org.cotcodec.study": "total-recall-native-auto-demotion-restart-v1",
        "org.cotcodec.publication-ready": "false",
    }
    if not isinstance(labels, dict) or any(
        labels.get(key) != value for key, value in expected_labels.items()
    ):
        raise DoctorError("restart doctor image labels do not bind source/study")

    run_argv = [
        "docker",
        "run",
        "--rm",
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
        "2g",
        "--cpus",
        "2",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=64m,mode=0700,uid=65532,gid=65532",
        image_id,
    ]
    completed = _run(run_argv)
    lines = completed.stdout.splitlines()
    if len(lines) != 1:
        raise DoctorError("native doctor must emit exactly one JSON line")
    native_report = _strict_json(lines[0], "native doctor output")
    expected_status = "BLOCKED_NATIVE_RESTART_DEFECT_REPRODUCED"
    if native_report.get("status") != expected_status:
        raise DoctorError(f"native restart defect did not reproduce: {native_report}")
    gates = native_report.get("gates")
    if not isinstance(gates, dict) or not gates or not all(gates.values()):
        raise DoctorError("native restart defect gate set is incomplete")

    runtime_receipt = {
        "container_runtime": "docker",
        "image_tag": image_tag,
        "image_id": image_id,
        "architecture": architecture,
        "os": image.get("Os"),
        "image_labels": expected_labels,
        "repo_digests": image.get("RepoDigests") or [],
        "run_argv": run_argv,
        "runtime_network": "none",
        "read_only_root": True,
        "capabilities_dropped": "ALL",
        "no_new_privileges": True,
        "gpu_count": 0,
        "sudo_used": False,
        "publication_attested": False,
        "build_network": "default-dependency-acquisition",
        "base_images": {"dotnet": DOTNET_IMAGE, "node": NODE_IMAGE},
    }
    report = {
        "schema_version": 1,
        "study": "stage3-total-recall-lifecycle-doctor",
        "status": expected_status,
        "scientific_result": False,
        "publication_ready": False,
        "h100_admission": "blocked",
        "native_report": native_report,
        "source_receipt": source_receipt,
        "input_receipt": input_receipt,
        "runtime_receipt": runtime_receipt,
        "interpretation": (
            "The pinned native automatic hot-to-warm path loses the vector row; "
            "startup orphan cleanup then deletes the demoted content row. The "
            "vector-preserving control survives the same restart."
        ),
        "required_next_gate": (
            "newer upstream pin or an explicitly labeled patch arm must preserve "
            "content and vector identity across automatic transition and restart"
        ),
    }

    artifacts = {
        "experiment.yaml": EXPERIMENT.read_bytes(),
        "source-receipt.json": _json_bytes(source_receipt),
        "input-receipt.json": _json_bytes(input_receipt),
        "runtime-receipt.json": _json_bytes(runtime_receipt),
        "native-report.json": _json_bytes(native_report),
        "report.json": _json_bytes(report),
    }
    for name, data in artifacts.items():
        _write_once(output / name, data)
    manifest = {
        "schema_version": 1,
        "status": expected_status,
        "artifacts": {
            name: {"sha256": _sha256_bytes(data), "bytes": len(data)}
            for name, data in sorted(artifacts.items())
        },
    }
    manifest["manifest_sha256"] = _sha256_bytes(_json_bytes(manifest))
    _write_once(output / "manifest.json", _json_bytes(manifest))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--image-tag", default=DEFAULT_IMAGE_TAG)
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()
    try:
        report = _run_doctor_complete(
            args.output_dir.resolve(), args.image_tag, args.rebuild
        )
    except DoctorError as exc:
        with contextlib.suppress(OSError):
            args.output_dir.resolve().rmdir()
        print(f"total recall restart doctor failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
