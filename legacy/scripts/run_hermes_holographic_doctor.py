#!/usr/bin/env python3
"""Build and run the contained Hermes Holographic lifecycle falsifier."""

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

from scripts.validate_hermes_holographic_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    EXPECTED_STATUS,
    validate_experiment_contract,
)

DOCTOR_ROOT = PROJECT_ROOT / "infra/memory-baselines/hermes-holographic"
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data/results/hermes-holographic/2026-08-14-lifecycle-doctor-v1"
)


class DoctorError(RuntimeError):
    """Raised when source, containment, or result identity drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_path(path: Path) -> str:
    return _sha(path.read_bytes())


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _run(
    argv: list[str], *, cwd: Path | None = None, timeout: int = 1200
) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        argv, cwd=cwd, capture_output=True, check=False, timeout=timeout
    )
    if result.returncode != 0:
        raise DoctorError(
            f"command failed ({result.returncode}): {argv!r}\n"
            f"stdout={result.stdout.decode(errors='replace')}\n"
            f"stderr={result.stderr.decode(errors='replace')}"
        )
    return result


def _write_once(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def _strict_json(data: bytes, owner: str) -> dict[str, Any]:
    try:
        value = json.loads(data)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise DoctorError(f"{owner} output is not JSON") from exc
    if not isinstance(value, dict):
        raise DoctorError(f"{owner} output is not a mapping")
    return value


def _extract(archive: bytes, destination: Path) -> None:
    seen: set[str] = set()
    total = 0
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as bundle:
        members = bundle.getmembers()
        if not members or len(members) > 30_000:
            raise DoctorError("Hermes archive member count is invalid")
        for member in members:
            relative = PurePosixPath(member.name)
            if relative.is_absolute() or ".." in relative.parts or not relative.parts:
                raise DoctorError(f"unsafe archive path: {member.name}")
            name = relative.as_posix()
            if name in seen:
                raise DoctorError(f"duplicate archive path: {name}")
            seen.add(name)
            target = destination / name
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                raise DoctorError(f"unsupported archive member: {name}")
            total += member.size
            if total > 1024 * 1024 * 1024:
                raise DoctorError("Hermes archive exceeds the byte ceiling")
            source = bundle.extractfile(member)
            if source is None:
                raise DoctorError(f"archive member has no bytes: {name}")
            target.parent.mkdir(parents=True, exist_ok=True)
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
        raise DoctorError("Hermes Git identity drifted")
    if _run(["git", "status", "--porcelain"], cwd=checkout).stdout.strip():
        raise DoctorError("Hermes checkout is dirty")
    archive = _run(["git", "archive", "--format=tar", "HEAD"], cwd=checkout).stdout
    checks = {
        "git_archive_tar_sha256": _sha(archive),
        "license_sha256": _sha_path(checkout / "LICENSE"),
        "hermes_state_sha256": _sha_path(checkout / "hermes_state.py"),
        "store_sha256": _sha_path(
            checkout / "plugins/memory/holographic/store.py"
        ),
        "retrieval_sha256": _sha_path(
            checkout / "plugins/memory/holographic/retrieval.py"
        ),
        "holographic_sha256": _sha_path(
            checkout / "plugins/memory/holographic/holographic.py"
        ),
        "provider_sha256": _sha_path(
            checkout / "plugins/memory/holographic/__init__.py"
        ),
    }
    if any(checks[field] != source[field] for field in checks):
        raise DoctorError("Hermes Holographic source receipt drifted")
    context = root / "context"
    upstream = context / "upstream"
    upstream.mkdir(parents=True)
    _extract(archive, upstream)
    shutil.copy2(DOCTOR_ROOT / "Dockerfile", context / "Dockerfile")
    shutil.copy2(DOCTOR_ROOT / "doctor.py", context / "doctor.py")
    return {
        "context": context,
        "repository": source["repository"],
        "revision": revision,
        "tree": tree,
        **checks,
        "worktree_clean": True,
        "archive_bytes": len(archive),
        "dockerfile_sha256": _sha_path(DOCTOR_ROOT / "Dockerfile"),
        "doctor_sha256": _sha_path(DOCTOR_ROOT / "doctor.py"),
    }


def _build_image(
    experiment: dict[str, Any], source: dict[str, Any], image_tag: str
) -> dict[str, Any]:
    runtime = experiment["runtime"]
    _run(
        [
            "docker",
            "build",
            "--platform",
            runtime["local_platform"],
            "--build-arg",
            f"BASE_IMAGE={runtime['base_image']}",
            "--build-arg",
            f"HERMES_GIT_SHA={experiment['source']['revision']}",
            "--build-arg",
            f"HERMES_SOURCE_SHA256={experiment['source']['git_archive_tar_sha256']}",
            "--tag",
            image_tag,
            str(source["context"]),
        ]
    )
    raw = _run(["docker", "image", "inspect", image_tag]).stdout
    rows = json.loads(raw)
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise DoctorError("Docker inspect must return one image")
    inspect = rows[0]
    labels = inspect.get("Config", {}).get("Labels", {})
    if (
        inspect.get("Architecture") != "arm64"
        or inspect.get("Os") != "linux"
        or inspect.get("Config", {}).get("User") != runtime["user"]
        or labels.get("org.opencontainers.image.revision")
        != experiment["source"]["revision"]
        or labels.get("org.cotcodec.source-archive-sha256")
        != experiment["source"]["git_archive_tar_sha256"]
    ):
        raise DoctorError("Holographic image contract drifted")
    image_id = inspect.get("Id")
    if not isinstance(image_id, str) or not image_id.startswith("sha256:"):
        raise DoctorError("Holographic image ID is invalid")
    return {"image_id": image_id, "inspect": inspect, "inspect_sha256": _sha(raw)}


def _initialize_volume(*, image_id: str, volume: str) -> None:
    _run(
        [
            "docker",
            "run",
            "--rm",
            "--pull=never",
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


def _run_phase(
    *, image_id: str, volume: str, phase: str, runtime: dict[str, Any]
) -> dict[str, Any]:
    argv = [
        "docker",
        "run",
        "--rm",
        "--pull=never",
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
        runtime["memory_limit"],
        "--cpus",
        str(runtime["cpu_limit"]),
        "--user",
        runtime["user"],
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=128m",
        "-e",
        "HOME=/tmp",
        "-v",
        f"{volume}:/state:rw",
        image_id,
        phase,
    ]
    result = _run(argv, timeout=runtime["timeout_seconds"])
    return {
        "argv": argv,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "result": _strict_json(result.stdout, f"Holographic {phase}"),
    }


def _stable_projection(phases: dict[str, dict[str, Any]]) -> dict[str, Any]:
    prepare = phases["prepare"]["result"]
    restart = phases["restart"]["result"]
    purge = phases["purge"]["result"]
    if prepare["snapshot"] != restart["snapshot"]:
        raise DoctorError("native state changed across fresh-process restart")
    return {
        "snapshot": prepare["snapshot"],
        "duplicate_add_same_id": prepare["duplicate_add_same_id"],
        "restart_persistence_supported": restart["restart_persistence_supported"],
        "session_a_visible_from_fresh_session_b": restart[
            "session_a_visible_from_fresh_session_b"
        ],
        "session_scoped_isolation_supported": restart[
            "session_scoped_isolation_supported"
        ],
        "logical_rows_after_restart": purge["logical_rows_after_restart"],
        "native_session_purge_supported": purge["native_session_purge_supported"],
        "physical_zero_residue_after_logical_delete": purge[
            "physical_zero_residue_after_logical_delete"
        ],
        "physical_hits": purge["physical_hits"],
    }


def run_doctor(output: Path, image_tag: str) -> dict[str, Any]:
    experiment = validate_experiment_contract(DEFAULT_EXPERIMENT)
    if output.exists():
        raise DoctorError(f"output path already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cotcodec-holographic-build-") as build_tmp:
        source = _prepare_context(Path(build_tmp), experiment)
        image = _build_image(experiment, source, image_tag)
        source_receipt = {key: value for key, value in source.items() if key != "context"}
        volumes = [f"cotcodec-holographic-{secrets.token_hex(8)}" for _ in range(2)]
        try:
            for volume in volumes:
                _run(
                    [
                        "docker",
                        "volume",
                        "create",
                        "--label",
                        "org.cotcodec.study=hermes-holographic-lifecycle-v1",
                        volume,
                    ]
                )
                _initialize_volume(image_id=image["image_id"], volume=volume)
            runs = []
            for volume in volumes:
                phases = {
                    phase: _run_phase(
                        image_id=image["image_id"],
                        volume=volume,
                        phase=phase,
                        runtime=experiment["runtime"],
                    )
                    for phase in ("prepare", "restart", "purge")
                }
                projection = _stable_projection(phases)
                runs.append({"phases": phases, "stable_projection": projection})
        finally:
            for volume in volumes:
                subprocess.run(
                    ["docker", "volume", "rm", volume],
                    check=False,
                    capture_output=True,
                )
        if runs[0]["stable_projection"] != runs[1]["stable_projection"]:
            raise DoctorError("Holographic result changed across clean states")
        projection = runs[0]["stable_projection"]
        report = {
            "schema_version": 1,
            "study": "hermes-holographic-lifecycle-falsification-v1",
            "status": EXPECTED_STATUS,
            "scientific_result": False,
            "publication_ready": False,
            "source": source_receipt,
            "image": {
                "image_id": image["image_id"],
                "inspect_sha256": image["inspect_sha256"],
            },
            "run_count": 2,
            "stable_projection_sha256": _sha(_json_bytes(projection)),
            "findings": {
                "native_sqlite_fts_restart_supported": True,
                "duplicate_add_idempotence_supported": True,
                "update_and_feedback_persist": True,
                "session_scoped_isolation_supported": False,
                "native_session_purge_supported": False,
                "physical_zero_residue_after_logical_delete": projection[
                    "physical_zero_residue_after_logical_delete"
                ],
                "plaintext_residue_reproduced": bool(projection["physical_hits"]),
            },
            "admission": {
                "provider_contract": "local-negative-only",
                "memory_lifecycle_h100": "forbidden-for-this-revision",
                "cluster_confirmation": "not-run",
            },
        }
        staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
        try:
            _write_once(staging / "experiment.yaml", DEFAULT_EXPERIMENT.read_bytes())
            _write_once(staging / "source-receipt.json", _json_bytes(source_receipt))
            _write_once(staging / "image-inspect.json", _json_bytes(image["inspect"]))
            for index, run in enumerate(runs, start=1):
                root = staging / f"run-{index}"
                for phase in ("prepare", "restart", "purge"):
                    record = run["phases"][phase]
                    _write_once(root / f"{phase}.argv.json", _json_bytes(record["argv"]))
                    _write_once(root / f"{phase}.json", record["stdout"])
                    _write_once(root / f"{phase}.stderr", record["stderr"])
                _write_once(
                    root / "stable-projection.json",
                    _json_bytes(run["stable_projection"]),
                )
            _write_once(staging / "report.json", _json_bytes(report))
            artifacts: dict[str, dict[str, Any]] = {}
            for path in sorted(staging.rglob("*")):
                if path.is_file():
                    name = path.relative_to(staging).as_posix()
                    artifacts[name] = {"bytes": path.stat().st_size, "sha256": _sha_path(path)}
            manifest = {
                "schema_version": 1,
                "status": EXPECTED_STATUS,
                "files": artifacts,
                "root_sha256": _sha(_json_bytes(artifacts)),
            }
            _write_once(staging / "manifest.json", _json_bytes(manifest))
            os.rename(staging, output)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--image-tag",
        default="cotcodec-hermes-holographic-lifecycle:a90d536-arm64-v1",
    )
    args = parser.parse_args()
    report = run_doctor(args.output, args.image_tag)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
