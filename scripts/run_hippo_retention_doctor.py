#!/usr/bin/env python3
"""Run Hippo's retention/consolidation falsification in isolated Docker."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import secrets
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

from scripts.validate_hippo_retention_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    EXPECTED_STATUS,
    validate_experiment_contract,
)

DOCTOR_ROOT = PROJECT_ROOT / "infra" / "memory-baselines" / "hippo-memory"
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "data" / "results" / "hippo-retention" / "2026-08-14-doctor-v1"
)
DEFAULT_IMAGE_TAG = "cotcodec-hippo-retention-doctor:4aeb04c-arm64-v1"
MAX_ARCHIVE_MEMBERS = 20_000
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024


class DoctorError(RuntimeError):
    """Raised when Hippo provenance, containment, or falsification drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_path(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise DoctorError(f"expected regular file: {path}")
    return _sha(path.read_bytes())


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _run(
    argv: list[str],
    *,
    cwd: Path | None = None,
    timeout: int = 900,
) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        argv,
        cwd=cwd,
        check=False,
        capture_output=True,
        timeout=timeout,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.decode(errors="replace")
        stdout = completed.stdout.decode(errors="replace")
        raise DoctorError(
            f"command failed ({completed.returncode}): {argv!r}\n"
            f"stdout={stdout}\nstderr={stderr}"
        )
    return completed


def _strict_json(data: bytes, label: str) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise DoctorError(f"{label} contains non-finite value: {value}")

    try:
        payload = json.loads(data, parse_constant=reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DoctorError(f"{label} is not strict JSON") from exc
    if not isinstance(payload, dict):
        raise DoctorError(f"{label} must be a JSON object")
    return payload


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
                raise DoctorError(f"short write: {path}")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _extract_archive(archive: bytes, destination: Path) -> None:
    total = 0
    seen: set[str] = set()
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as bundle:
        members = bundle.getmembers()
        if not members or len(members) > MAX_ARCHIVE_MEMBERS:
            raise DoctorError("Hippo archive member count is invalid")
        for member in members:
            relative = PurePosixPath(member.name)
            if relative.is_absolute() or ".." in relative.parts or not relative.parts:
                raise DoctorError(f"unsafe Hippo archive path: {member.name}")
            name = relative.as_posix()
            if name in seen:
                raise DoctorError(f"duplicate Hippo archive path: {name}")
            seen.add(name)
            target = destination / name
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                raise DoctorError(f"unsupported Hippo archive member: {name}")
            total += member.size
            if total > MAX_ARCHIVE_BYTES:
                raise DoctorError("Hippo archive exceeds uncompressed byte ceiling")
            target.parent.mkdir(parents=True, exist_ok=True)
            source = bundle.extractfile(member)
            if source is None:
                raise DoctorError(f"Hippo archive member has no bytes: {name}")
            with target.open("xb") as output:
                shutil.copyfileobj(source, output)
            target.chmod(member.mode & 0o777)


def _prepare_context(root: Path, experiment: dict[str, Any]) -> dict[str, Any]:
    source = experiment["source"]
    checkout = root / "checkout"
    _run(
        [
            "git",
            "clone",
            "--filter=blob:none",
            "--no-checkout",
            source["repository"],
            str(checkout),
        ]
    )
    _run(["git", "checkout", "--detach", source["revision"]], cwd=checkout)
    revision = _run(["git", "rev-parse", "HEAD"], cwd=checkout).stdout.decode().strip()
    tree = _run(["git", "rev-parse", "HEAD^{tree}"], cwd=checkout).stdout.decode().strip()
    if revision != source["revision"] or tree != source["tree"]:
        raise DoctorError("Hippo Git identity drifted")
    if _run(["git", "status", "--porcelain"], cwd=checkout).stdout.strip():
        raise DoctorError("Hippo checkout is dirty")
    archive = _run(
        ["git", "archive", "--format=tar", "HEAD"], cwd=checkout
    ).stdout
    if _sha(archive) != source["git_archive_tar_sha256"]:
        raise DoctorError("Hippo source archive drifted")
    if _sha_path(checkout / "LICENSE") != source["license_sha256"]:
        raise DoctorError("Hippo license drifted")
    if _sha_path(checkout / "package-lock.json") != source["package_lock_sha256"]:
        raise DoctorError("Hippo package lock drifted")

    context = root / "context"
    upstream = context / "upstream"
    upstream.mkdir(parents=True)
    _extract_archive(archive, upstream)
    shutil.copy2(DOCTOR_ROOT / "Dockerfile", context / "Dockerfile")
    shutil.copy2(DOCTOR_ROOT / "doctor.mjs", context / "doctor.mjs")
    return {
        "context": context,
        "repository": source["repository"],
        "revision": revision,
        "tree": tree,
        "git_archive_tar_sha256": _sha(archive),
        "license_sha256": _sha_path(checkout / "LICENSE"),
        "package_lock_sha256": _sha_path(checkout / "package-lock.json"),
        "dockerfile_sha256": _sha_path(DOCTOR_ROOT / "Dockerfile"),
        "doctor_sha256": _sha_path(DOCTOR_ROOT / "doctor.mjs"),
        "archive_bytes": len(archive),
        "worktree_clean": True,
    }


def _build_image(
    experiment: dict[str, Any], source: dict[str, Any], image_tag: str
) -> dict[str, Any]:
    runtime = experiment["runtime"]
    context = source["context"]
    _run(
        [
            "docker",
            "build",
            "--platform",
            runtime["local_platform"],
            "--build-arg",
            f"BASE_IMAGE={runtime['local_base_image']}",
            "--build-arg",
            f"COTCODEC_HIPPO_GIT_SHA={experiment['source']['revision']}",
            "--build-arg",
            f"COTCODEC_HIPPO_SOURCE_SHA256={experiment['source']['git_archive_tar_sha256']}",
            "--tag",
            image_tag,
            str(context),
        ],
        timeout=1800,
    )
    raw = _run(["docker", "image", "inspect", image_tag]).stdout
    try:
        rows = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DoctorError("Docker inspect output is invalid") from exc
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise DoctorError("Docker inspect must return one image")
    inspect = rows[0]
    labels = inspect.get("Config", {}).get("Labels", {})
    expected_labels = {
        "org.opencontainers.image.revision": experiment["source"]["revision"],
        "org.cotcodec.source-archive-sha256": experiment["source"][
            "git_archive_tar_sha256"
        ],
    }
    for key, value in expected_labels.items():
        if labels.get(key) != value:
            raise DoctorError(f"Hippo image label {key} drifted")
    if inspect.get("Architecture") != "arm64" or inspect.get("Os") != "linux":
        raise DoctorError("Hippo image platform drifted")
    image_id = inspect.get("Id")
    if not isinstance(image_id, str) or not image_id.startswith("sha256:"):
        raise DoctorError("Hippo image ID is invalid")
    return {"image_id": image_id, "inspect": inspect, "inspect_sha256": _sha(raw)}


def _run_phase(
    *, image_tag: str, image_id: str, volume: str, phase: str
) -> dict[str, Any]:
    argv = [
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
        "768m",
        "--cpus",
        "1",
        "--user",
        "65532:65532",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=128m",
        "-e",
        "HOME=/tmp",
        "-v",
        f"{volume}:/state/hippo:rw",
        image_id,
        phase,
    ]
    completed = _run(argv)
    result = _strict_json(completed.stdout, f"Hippo {phase}")
    return {
        "argv": argv,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "result": result,
        "image_tag": image_tag,
    }


def _initialize_volume(*, image_id: str, volume: str) -> None:
    _run(
        [
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
            "--cap-add",
            "CHOWN",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "32",
            "--memory",
            "128m",
            "--cpus",
            "0.25",
            "--user",
            "0:0",
            "-v",
            f"{volume}:/state/hippo:rw",
            "--entrypoint",
            "/bin/chown",
            image_id,
            "65532:65532",
            "/state/hippo",
        ]
    )


def _stable_projection(run: dict[str, Any]) -> dict[str, Any]:
    prepare = run["prepare"]["result"]
    purge = run["purge"]["result"]
    return {
        "forbidden_capabilities": prepare["forbidden_capabilities"],
        "sleep": prepare["sleep"],
        "cross_tenant": prepare["cross_tenant"],
        "retention": prepare["retention"],
        "projection": prepare["projection"],
        "purge": {
            "working_memory_flush_count": purge["working_memory_flush_count"],
            "working_memory_flush_archived": purge["working_memory_flush_archived"],
            "logical_record_count": purge["logical_record_count"],
            "native_scoped_purge_available": purge["native_scoped_purge_available"],
            "plaintext_residue_reproduced": purge["plaintext_residue_reproduced"],
            "physical_hits": purge["physical_hits"],
        },
    }


def _execute_once(
    *, image_tag: str, image_id: str, volume: str
) -> dict[str, Any]:
    prepare = _run_phase(
        image_tag=image_tag, image_id=image_id, volume=volume, phase="prepare"
    )
    restart = _run_phase(
        image_tag=image_tag, image_id=image_id, volume=volume, phase="restart"
    )
    if prepare["result"]["projection_sha256"] != restart["result"]["projection_sha256"]:
        raise DoctorError("Hippo normalized state changed after fresh-process restart")
    purge = _run_phase(
        image_tag=image_tag, image_id=image_id, volume=volume, phase="purge"
    )
    run = {"prepare": prepare, "restart": restart, "purge": purge}
    run["stable_projection"] = _stable_projection(run)
    run["stable_projection_sha256"] = _sha(_json_bytes(run["stable_projection"]))
    return run


def run_doctor(output: Path, image_tag: str) -> dict[str, Any]:
    experiment = validate_experiment_contract(DEFAULT_EXPERIMENT)
    if output.exists():
        raise DoctorError(f"output path already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="cotcodec-hippo-build-") as build_tmp:
        source = _prepare_context(Path(build_tmp), experiment)
        image = _build_image(experiment, source, image_tag)
        source_without_context = {k: v for k, v in source.items() if k != "context"}
        volumes = [f"cotcodec-hippo-doctor-{secrets.token_hex(8)}" for _ in (1, 2)]
        try:
            for volume in volumes:
                _run(
                    [
                        "docker",
                        "volume",
                        "create",
                        "--label",
                        "org.cotcodec.study=hippo-retention-doctor-v1",
                        volume,
                    ]
                )
                _initialize_volume(image_id=image["image_id"], volume=volume)
            runs = [
                _execute_once(
                    image_tag=image_tag,
                    image_id=image["image_id"],
                    volume=volume,
                )
                for volume in volumes
            ]
        finally:
            for volume in volumes:
                subprocess.run(
                    ["docker", "volume", "rm", volume],
                    check=False,
                    capture_output=True,
                )

        projection_hashes = [run["stable_projection_sha256"] for run in runs]
        if len(set(projection_hashes)) != 1:
            raise DoctorError("Hippo falsification projection changed across clean states")
        report = {
            "schema_version": 1,
            "study": "hippo-retention-cross-tenant-doctor-v1",
            "status": EXPECTED_STATUS,
            "scientific_result": False,
            "publication_ready": False,
            "source": source_without_context,
            "image": {
                "image_id": image["image_id"],
                "inspect_sha256": image["inspect_sha256"],
            },
            "run_count": len(runs),
            "stable_projection_sha256": projection_hashes[0],
            "findings": {
                "active_inactive_paging_supported": False,
                "working_memory_eviction_is_deletion": True,
                "working_memory_flush_archives": False,
                "positive_outcome_extends_retention": True,
                "cross_tenant_semantic_created": True,
                "cross_tenant_semantic_owned_by_default_tenant": True,
                "cross_tenant_semantic_retrievable_by_default_tenant": True,
                "cross_tenant_semantic_source_lineage_complete": False,
                "logical_delete_reaches_zero_rows": True,
                "plaintext_canary_residue_in_sqlite": True,
            },
            "admission": {
                "active_inactive_h100": "forbidden-for-this-revision",
                "retention_actor_pilot": "blocked",
                "cluster_confirmation": "not-run",
            },
        }

        staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
        try:
            _write_once(staging / "experiment.yaml", DEFAULT_EXPERIMENT.read_bytes())
            _write_once(staging / "source-receipt.json", _json_bytes(source_without_context))
            _write_once(staging / "image-inspect.json", _json_bytes(image["inspect"]))
            for index, run in enumerate(runs, start=1):
                run_root = staging / f"run-{index}"
                for phase in ("prepare", "restart", "purge"):
                    record = run[phase]
                    _write_once(run_root / f"{phase}.json", _json_bytes(record["result"]))
                    _write_once(run_root / f"{phase}.stderr", record["stderr"])
                    _write_once(run_root / f"{phase}.argv.json", _json_bytes(record["argv"]))
                _write_once(
                    run_root / "stable-projection.json",
                    _json_bytes(run["stable_projection"]),
                )
            _write_once(staging / "report.json", _json_bytes(report))
            files = {}
            for path in sorted(staging.rglob("*")):
                if path.is_file() and path.name != "manifest.json":
                    relative = path.relative_to(staging).as_posix()
                    files[relative] = {"bytes": path.stat().st_size, "sha256": _sha_path(path)}
            manifest = {
                "schema_version": 1,
                "status": EXPECTED_STATUS,
                "files": files,
                "root_sha256": _sha(_json_bytes(files)),
            }
            _write_once(staging / "manifest.json", _json_bytes(manifest))
            os.rename(staging, output)
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--image-tag", default=DEFAULT_IMAGE_TAG)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run_doctor(args.output.resolve(), args.image_tag)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
