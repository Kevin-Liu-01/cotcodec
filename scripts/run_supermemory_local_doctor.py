#!/usr/bin/env python3
"""Run the pinned Supermemory local binary lifecycle doctor in Docker."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validate_supermemory_local_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    EXPECTED_STATUS,
    validate_experiment_contract,
)

DOCTOR_ROOT = PROJECT_ROOT / "infra" / "memory-baselines" / "supermemory"
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data"
    / "results"
    / "supermemory-local-binary"
    / "2026-08-15-doctor-v1"
)
DEFAULT_IMAGE_TAG = "cotcodec-supermemory-local-doctor:server-v0.0.3-arm64-v1"


class DoctorError(RuntimeError):
    """Raised when acquisition, containment, or lifecycle evidence drifts."""


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
    timeout: int = 1800,
) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        argv,
        cwd=cwd,
        check=False,
        capture_output=True,
        timeout=timeout,
    )
    if completed.returncode != 0:
        raise DoctorError(
            f"command failed ({completed.returncode}): {argv!r}\n"
            f"stdout={completed.stdout.decode(errors='replace')}\n"
            f"stderr={completed.stderr.decode(errors='replace')}"
        )
    return completed


def _strict_object(data: bytes, label: str) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise DoctorError(f"{label} contains non-finite value {value}")

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


def _verify_source(experiment: dict[str, Any], root: Path) -> dict[str, Any]:
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
    _run(["git", "checkout", "--detach", source["documentation_revision"]], cwd=checkout)
    if _run(["git", "status", "--porcelain"], cwd=checkout).stdout.strip():
        raise DoctorError("Supermemory documentation checkout is dirty")
    revision = _run(["git", "rev-parse", "HEAD"], cwd=checkout).stdout.decode().strip()
    tree = _run(["git", "rev-parse", "HEAD^{tree}"], cwd=checkout).stdout.decode().strip()
    if revision != source["documentation_revision"] or tree != source["documentation_tree"]:
        raise DoctorError("Supermemory documentation Git identity drifted")
    doc_archive = _run(["git", "archive", "--format=tar", revision], cwd=checkout).stdout
    if _sha(doc_archive) != source["documentation_archive_tar_sha256"]:
        raise DoctorError("Supermemory documentation archive drifted")
    expected_files = {
        "LICENSE": source["license_sha256"],
        "README.md": source["readme_sha256"],
        "apps/docs/self-hosting/configuration.mdx": source[
            "configuration_doc_sha256"
        ],
        "apps/docs/recall/memory-operations.mdx": source[
            "memory_operations_doc_sha256"
        ],
    }
    for relative, expected in expected_files.items():
        if _sha_path(checkout / relative) != expected:
            raise DoctorError(f"Supermemory documentation file drifted: {relative}")

    release = source["release_revision"]
    _run(["git", "cat-file", "-e", f"{release}^{{commit}}"], cwd=checkout)
    release_tree = _run(
        ["git", "rev-parse", f"{release}^{{tree}}"], cwd=checkout
    ).stdout.decode().strip()
    if release_tree != source["release_tree"]:
        raise DoctorError("Supermemory release tree drifted")
    release_archive = _run(
        ["git", "archive", "--format=tar", release], cwd=checkout
    ).stdout
    if _sha(release_archive) != source["release_archive_tar_sha256"]:
        raise DoctorError("Supermemory release archive drifted")
    path_list = _run(
        ["git", "ls-tree", "-r", "--name-only", release], cwd=checkout
    ).stdout
    if _sha(path_list) != source["release_tree_path_list_sha256"]:
        raise DoctorError("Supermemory release path list drifted")
    paths = path_list.decode().splitlines()
    server_source_candidates = [
        path
        for path in paths
        if not path.startswith("apps/docs/")
        and (
            "supermemory-server" in path
            or path.startswith("apps/server/")
            or path.startswith("packages/server/")
            or "self-host" in path
        )
    ]
    if server_source_candidates or source["local_server_source_in_release_tree"] is not False:
        raise DoctorError("Supermemory release unexpectedly contains local-server source")
    return {
        "repository": source["repository"],
        "documentation_revision": revision,
        "documentation_tree": tree,
        "documentation_archive_tar_sha256": _sha(doc_archive),
        "release_revision": release,
        "release_tree": release_tree,
        "release_archive_tar_sha256": _sha(release_archive),
        "release_tree_path_list_sha256": _sha(path_list),
        "release_tree_file_count": len(paths),
        "local_server_source_candidates": server_source_candidates,
        "local_server_source_available": False,
        "verified_documentation_files": expected_files,
        "worktree_clean": True,
    }


def _prepare_context(
    *,
    root: Path,
    experiment: dict[str, Any],
    server_binary: Path,
    release_manifest: Path,
    model_cache: Path,
) -> tuple[Path, dict[str, Any]]:
    source_receipt = _verify_source(experiment, root)
    binary_contract = experiment["source"]["binary_artifact"]
    if _sha_path(server_binary) != binary_contract["sha256"]:
        raise DoctorError("Supermemory server binary hash drifted")
    if server_binary.stat().st_size != binary_contract["bytes"]:
        raise DoctorError("Supermemory server binary size drifted")
    if _sha_path(release_manifest) != binary_contract["manifest_sha256"]:
        raise DoctorError("Supermemory release manifest hash drifted")
    manifest = _strict_object(release_manifest.read_bytes(), "Supermemory release manifest")
    if (
        manifest.get("version") != "0.0.3"
        or manifest.get("platforms", {}).get("linux-arm64", {}).get("checksum")
        != binary_contract["sha256"]
    ):
        raise DoctorError("Supermemory release manifest content drifted")

    context = root / "context"
    context.mkdir()
    shutil.copyfile(server_binary, context / "supermemory-server")
    shutil.copyfile(DOCTOR_ROOT / "doctor.py", context / "doctor.py")
    model_destination = context / "model-cache"
    model_destination.mkdir()
    verified_model_files: dict[str, str] = {}
    for relative, expected in experiment["embedding_model"]["files"].items():
        source = model_cache / relative
        if _sha_path(source) != expected:
            raise DoctorError(f"Supermemory embedding artifact drifted: {relative}")
        destination = model_destination / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        verified_model_files[relative] = expected
    source_receipt.update(
        {
            "binary_artifact": {
                "sha256": _sha_path(server_binary),
                "bytes": server_binary.stat().st_size,
                "manifest_sha256": _sha_path(release_manifest),
                "manifest": manifest,
            },
            "embedding_model": {
                "revision": experiment["embedding_model"]["revision"],
                "files": verified_model_files,
            },
            "doctor_sha256": _sha_path(DOCTOR_ROOT / "doctor.py"),
            "dockerfile_sha256": _sha_path(DOCTOR_ROOT / "Dockerfile.binary-doctor"),
        }
    )
    return context, source_receipt


def _build_image(
    experiment: dict[str, Any], context: Path, image_tag: str
) -> tuple[str, dict[str, Any], str]:
    runtime = experiment["runtime"]
    source = experiment["source"]
    model = experiment["embedding_model"]
    _run(
        [
            "docker",
            "build",
            "--platform",
            runtime["local_platform"],
            "--pull=false",
            "--build-arg",
            f"BASE_IMAGE={runtime['local_base_image']}",
            "--build-arg",
            f"COTCODEC_SUPERMEMORY_SOURCE_REVISION={source['documentation_revision']}",
            "--build-arg",
            f"COTCODEC_SUPERMEMORY_RELEASE_REVISION={source['release_revision']}",
            "--build-arg",
            f"COTCODEC_SUPERMEMORY_BINARY_SHA256={source['binary_artifact']['sha256']}",
            "--build-arg",
            f"COTCODEC_SUPERMEMORY_MODEL_REVISION={model['revision']}",
            "-f",
            str(DOCTOR_ROOT / "Dockerfile.binary-doctor"),
            "--tag",
            image_tag,
            str(context),
        ]
    )
    raw = _run(["docker", "image", "inspect", image_tag]).stdout
    try:
        rows = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DoctorError("Docker inspect is not JSON") from exc
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise DoctorError("Docker inspect must contain one image")
    inspect = rows[0]
    labels = inspect.get("Config", {}).get("Labels", {})
    expected_labels = {
        "org.opencontainers.image.revision": source["documentation_revision"],
        "org.cotcodec.supermemory-release-revision": source["release_revision"],
        "org.cotcodec.supermemory-binary-sha256": source["binary_artifact"]["sha256"],
        "org.cotcodec.supermemory-model-revision": model["revision"],
        "org.cotcodec.evidence-role": "binary-only-cpu-lifecycle-doctor",
    }
    for key, expected in expected_labels.items():
        if labels.get(key) != expected:
            raise DoctorError(f"Supermemory image label drifted: {key}")
    if inspect.get("Architecture") != "arm64" or inspect.get("Os") != "linux":
        raise DoctorError("Supermemory image platform drifted")
    image_id = inspect.get("Id")
    if not isinstance(image_id, str) or not image_id.startswith("sha256:"):
        raise DoctorError("Supermemory image ID is invalid")
    return image_id, inspect, _sha(raw)


def _initialize_volume(image_id: str, volume: str) -> None:
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
            "--user",
            "0:0",
            "-v",
            f"{volume}:/state:rw",
            "--entrypoint",
            "/bin/chown",
            image_id,
            "65532:65532",
            "/state",
        ]
    )


def _run_phase(image_id: str, volume: str, phase: str) -> dict[str, Any]:
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
        "256",
        "--memory",
        "2560m",
        "--cpus",
        "2",
        "--user",
        "65532:65532",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=64m,mode=0700,uid=65532,gid=65532",
        "-v",
        f"{volume}:/state:rw",
        image_id,
        phase,
    ]
    completed = _run(argv, timeout=300)
    return {
        "argv": argv,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "result": _strict_object(completed.stdout, f"Supermemory {phase}"),
    }


def _stable_projection(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "prepare": run["prepare"]["result"]["checks"],
        "restart": {
            "checks": run["restart"]["result"]["checks"],
            "counts": run["restart"]["result"]["counts"],
        },
        "forget": {
            "checks": run["forget"]["result"]["checks"],
            "plaintext_hits": run["forget"]["result"]["plaintext_hits"],
        },
    }


def _execute_once(image_id: str, volume: str) -> dict[str, Any]:
    run = {
        phase: _run_phase(image_id, volume, phase)
        for phase in ("prepare", "restart", "forget")
    }
    run["stable_projection"] = _stable_projection(run)
    run["stable_projection_sha256"] = _sha(_json_bytes(run["stable_projection"]))
    return run


def run_doctor(
    *,
    output: Path,
    image_tag: str,
    server_binary: Path,
    release_manifest: Path,
    model_cache: Path,
) -> dict[str, Any]:
    experiment = validate_experiment_contract(DEFAULT_EXPERIMENT)
    if output.exists():
        raise DoctorError(f"output path already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cotcodec-supermemory-build-") as build_tmp:
        context, source_receipt = _prepare_context(
            root=Path(build_tmp),
            experiment=experiment,
            server_binary=server_binary,
            release_manifest=release_manifest,
            model_cache=model_cache,
        )
        image_id, image_inspect, inspect_sha = _build_image(
            experiment, context, image_tag
        )
        volumes = [f"cotcodec-supermemory-doctor-{secrets.token_hex(8)}" for _ in (1, 2)]
        try:
            for volume in volumes:
                _run(
                    [
                        "docker",
                        "volume",
                        "create",
                        "--label",
                        "org.cotcodec.study=supermemory-local-binary-doctor-v1",
                        volume,
                    ]
                )
                _initialize_volume(image_id, volume)
            runs = [_execute_once(image_id, volume) for volume in volumes]
        finally:
            for volume in volumes:
                subprocess.run(
                    ["docker", "volume", "rm", volume],
                    check=False,
                    capture_output=True,
                )
        projection_hashes = [run["stable_projection_sha256"] for run in runs]
        if len(set(projection_hashes)) != 1:
            raise DoctorError("Supermemory lifecycle projection changed across clean states")
        for run in runs:
            restart_checks = run["restart"]["result"]["checks"]
            restart_counts = run["restart"]["result"]["counts"]
            if any(
                restart_checks.get(field) is not False
                for field in (
                    "acknowledged_tenant_a_survives_sigkill",
                    "acknowledged_tenant_b_survives_sigkill",
                    "version_history_survives_sigkill",
                )
            ) or restart_counts != {
                "tenant_a_latest_after_sigkill": 0,
                "tenant_b_latest_after_sigkill": 0,
            }:
                raise DoctorError(
                    "Supermemory SIGKILL loss did not match the registered negative"
                )
            forget_checks = run["forget"]["result"]["checks"]
            required_forget = {
                "soft_forget_excludes_normal_search": True,
                "soft_forget_excludes_normal_list": True,
                "other_tenant_survives": True,
                "graceful_restart_persists_acknowledged_pair": True,
                "native_tenant_scoped_physical_purge_available": False,
                "provider_plaintext_at_rest_detected": False,
            }
            if any(
                forget_checks.get(field) is not expected
                for field, expected in required_forget.items()
            ):
                raise DoctorError("Supermemory soft-forget observation drifted")
        report = {
            "schema_version": 1,
            "study": "supermemory-local-binary-doctor-v1",
            "status": EXPECTED_STATUS,
            "scientific_result": False,
            "publication_ready": False,
            "source_evidence": "binary-only-release-artifact",
            "local_server_source_available": False,
            "source": source_receipt,
            "image": {"image_id": image_id, "inspect_sha256": inspect_sha},
            "run_count": len(runs),
            "stable_projection_sha256": projection_hashes[0],
            "findings": {
                "direct_memory_crud_works": True,
                "versioned_update_and_history_work": True,
                "acknowledged_writes_survive_sigkill_restart": False,
                "graceful_restart_persists_acknowledged_pair": True,
                "cross_container_plaintext_disclosure": False,
                "soft_forget_excludes_normal_reads": True,
                "provider_plaintext_at_rest_detected": False,
                "native_tenant_scoped_physical_purge_available": False,
                "release_v003_ignores_current_remote_embedding_configuration": True,
            },
            "admission": {
                "memory_lifecycle_h100": "forbidden-for-this-release",
                "reason": (
                    "acknowledged writes lost on SIGKILL, binary-only server, and no "
                    "tenant-scoped physical purge"
                ),
                "cluster_confirmation": "not-run",
            },
        }

        staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
        try:
            _write_once(staging / "experiment.yaml", DEFAULT_EXPERIMENT.read_bytes())
            _write_once(staging / "source-receipt.json", _json_bytes(source_receipt))
            _write_once(staging / "image-inspect.json", _json_bytes(image_inspect))
            for index, run in enumerate(runs, start=1):
                run_root = staging / f"run-{index}"
                for phase in ("prepare", "restart", "forget"):
                    record = run[phase]
                    _write_once(run_root / f"{phase}.json", _json_bytes(record["result"]))
                    _write_once(run_root / f"{phase}.stderr", record["stderr"])
                    _write_once(
                        run_root / f"{phase}.argv.json", _json_bytes(record["argv"])
                    )
                _write_once(
                    run_root / "stable-projection.json",
                    _json_bytes(run["stable_projection"]),
                )
            _write_once(staging / "report.json", _json_bytes(report))
            files: dict[str, dict[str, Any]] = {}
            for path in sorted(staging.rglob("*")):
                if path.is_file() and path.name != "manifest.json":
                    relative = path.relative_to(staging).as_posix()
                    files[relative] = {
                        "bytes": path.stat().st_size,
                        "sha256": _sha_path(path),
                    }
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
    parser.add_argument("--server-binary", type=Path, required=True)
    parser.add_argument("--release-manifest", type=Path, required=True)
    parser.add_argument("--model-cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--image-tag", default=DEFAULT_IMAGE_TAG)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run_doctor(
        output=args.output.resolve(),
        image_tag=args.image_tag,
        server_binary=args.server_binary.resolve(),
        release_manifest=args.release_manifest.resolve(),
        model_cache=args.model_cache.resolve(),
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
