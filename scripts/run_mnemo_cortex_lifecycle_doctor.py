#!/usr/bin/env python3
"""Build and run the exact-source Mnemo Cortex lifecycle doctor twice."""

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

from scripts.validate_mnemo_cortex_lifecycle_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    EXPECTED_STATUS,
    validate_experiment_contract,
)

DEFAULT_SOURCE = PROJECT_ROOT / "raw/baselines/mnemo-cortex"
DEFAULT_WHEELHOUSE = (
    PROJECT_ROOT / "raw/dependencies/mnemo-cortex-linux-x86_64-cp312-v1"
)
DEFAULT_IMAGE = "cotcodec-mnemo-cortex-lifecycle:8a0cff9-amd64-v1"
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "data/results/mnemo-cortex-lifecycle/2026-08-26-slurm-cpu-v1"
)
DOCKERFILE = PROJECT_ROOT / "infra/memory-baselines/mnemo-cortex/Dockerfile"
DOCTOR = PROJECT_ROOT / "infra/memory-baselines/mnemo-cortex/doctor.py"
WHEELHOUSE_MANIFEST = (
    PROJECT_ROOT
    / "infra/memory-baselines/mnemo-cortex/wheelhouse-manifest.json"
)
BATCH = PROJECT_ROOT / "infra/slurm/host-single-node/mnemo-cortex-lifecycle.sbatch"
UNEXPECTED_STATUS = "MNEMO_CORTEX_ADMISSION_KILLED_UNEXPECTED_PROJECTION"


class MnemoCortexLifecycleRunnerError(RuntimeError):
    """Raised when source, image, runtime, or result evidence drifts."""


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
                raise MnemoCortexLifecycleRunnerError(f"short write: {path}")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _run(argv: list[str], *, timeout: int = 1800) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(argv, capture_output=True, check=False, timeout=timeout)
    if completed.returncode:
        raise MnemoCortexLifecycleRunnerError(
            f"command failed ({completed.returncode}): {argv!r}\n"
            + completed.stdout.decode(errors="replace")[-8000:]
            + completed.stderr.decode(errors="replace")[-8000:]
        )
    return completed


def _extract_source_archive(raw: bytes, destination: Path) -> None:
    """Extract a Git archive after rejecting links, devices, and path escape."""
    root = destination.resolve()
    with tarfile.open(fileobj=BytesIO(raw), mode="r:") as archive:
        members = archive.getmembers()
        for member in members:
            target = (root / member.name).resolve()
            target_is_confined = target == root or root in target.parents
            link_is_confined = False
            if member.issym() and not Path(member.linkname).is_absolute():
                link_target = (target.parent / member.linkname).resolve()
                link_is_confined = link_target == root or root in link_target.parents
            if (
                not target_is_confined
                or not (
                    member.isdir()
                    or member.isfile()
                    or (member.issym() and link_is_confined)
                )
            ):
                raise MnemoCortexLifecycleRunnerError(
                    f"unsafe Mnemo Cortex source archive member: {member.name}"
                )
        if sys.version_info >= (3, 12):
            archive.extractall(root, members=members, filter="fully_trusted")
        else:
            archive.extractall(root, members=members)


def _source_contract(source_root: Path, experiment: dict[str, Any]) -> dict[str, Any]:
    source = experiment["source"]
    if not source_root.is_dir() or source_root.is_symlink():
        raise MnemoCortexLifecycleRunnerError(
            "Mnemo Cortex source root must be a real directory"
        )
    revision = _run(["git", "-C", str(source_root), "rev-parse", "HEAD"]).stdout.decode().strip()
    tree = _run(
        ["git", "-C", str(source_root), "rev-parse", "HEAD^{tree}"]
    ).stdout.decode().strip()
    status = _run([
        "git", "-C", str(source_root), "status", "--porcelain=v1",
        "--untracked-files=all",
    ]).stdout
    if revision != source["revision"] or tree != source["tree"] or status:
        raise MnemoCortexLifecycleRunnerError("Mnemo Cortex source checkout drifted")

    archive = _run([
        "git", "-C", str(source_root), "archive", "--format=tar", revision
    ]).stdout
    exact = {
        name: _sha_path(source_root / name) for name in source["exact_source_files"]
    }
    pyproject = (source_root / "pyproject.toml").read_text(encoding="utf-8")
    upstream_dockerfile = (source_root / "Dockerfile").read_text(encoding="utf-8")
    server = (source_root / "agentb/server.py").read_text(encoding="utf-8")
    analyst = (source_root / "agentb/analyst.py").read_text(encoding="utf-8")
    passport_api = (source_root / "passport/api.py").read_text(encoding="utf-8")
    dreamer = (source_root / "mnemo-dream.py").read_text(encoding="utf-8")
    tracked = set(
        _run(["git", "-C", str(source_root), "ls-files"]).stdout.decode().splitlines()
    )
    static_checks = {
        "archive_only_reachable_by_direct_sha_fetch": (
            not _run([
                "git", "-C", str(source_root), "branch", "-r", "--contains", revision
            ]).stdout.strip()
            and not _run([
                "git", "-C", str(source_root), "tag", "--contains", revision
            ]).stdout.strip()
        ),
        "python_dependency_lock_absent": not any(
            name in tracked for name in ("uv.lock", "poetry.lock", "Pipfile.lock")
        ),
        "pyproject_uses_lower_bounds": all(
            token in pyproject
            for token in (
                '"fastapi>=0.115,!=0.136.3"',
                '"pydantic>=2.8"',
                '"numpy>=1.24"',
                '"sqlite-vec>=0.1.6"',
            )
        ),
        "upstream_base_image_mutable": "FROM python:3.12-slim" in upstream_dockerfile,
        "upstream_container_does_not_install_git": (
            "apt-get" not in upstream_dockerfile and "apk add" not in upstream_dockerfile
        ),
        "passport_mutates_pending_before_git_commit": (
            passport_api.index("pending.add(") < passport_api.index("git_helper.commit(")
        ),
        "primary_memory_delete_route_absent": all(
            route not in server
            for route in (
                '@app.delete("/memory',
                '@app.post("/memory/delete',
                '@app.post("/memory/purge',
                '@app.post("/delete',
                '@app.post("/forget',
                '@app.post("/purge',
            )
        ),
        "analyst_preserves_source_lineage": (
            '"derived_from": source_ids' in analyst
            and 'fresh[marker] = True' in analyst
        ),
        "dreamer_uses_per_agent_then_rollup_stages": all(
            token in dreamer
            for token in (
                "PER_AGENT_SYSTEM_PROMPT",
                "ROLLUP_SYSTEM_PROMPT",
                "per_agent_briefs.append",
                "rollup_input =",
            )
        ),
    }
    if (
        _sha(archive) != source["git_archive_tar_sha256"]
        or len(archive) != source["git_archive_tar_bytes"]
        or _sha_path(source_root / "LICENSE") != source["license_sha256"]
        or _sha_path(source_root / "pyproject.toml") != source["pyproject_sha256"]
        or _sha_path(source_root / "Dockerfile")
        != source["upstream_dockerfile_sha256"]
        or exact != source["exact_source_files"]
        or not all(static_checks.values())
    ):
        raise MnemoCortexLifecycleRunnerError("Mnemo Cortex source receipt drifted")
    return {
        "revision": revision,
        "tree": tree,
        "archive": archive,
        "archive_sha256": _sha(archive),
        "archive_bytes": len(archive),
        "license_sha256": source["license_sha256"],
        "pyproject_sha256": source["pyproject_sha256"],
        "upstream_dockerfile_sha256": source["upstream_dockerfile_sha256"],
        "exact_source_files": exact,
        "static_source_checks": static_checks,
    }


def _wheelhouse_contract(
    wheelhouse_root: Path,
    *,
    expected_manifest_path: Path = WHEELHOUSE_MANIFEST,
) -> dict[str, Any]:
    """Verify the complete offline wheel transport before it enters Docker."""
    if not wheelhouse_root.is_dir() or wheelhouse_root.is_symlink():
        raise MnemoCortexLifecycleRunnerError(
            "Mnemo Cortex wheelhouse root must be a real directory"
        )
    if not expected_manifest_path.is_file() or expected_manifest_path.is_symlink():
        raise MnemoCortexLifecycleRunnerError(
            "Mnemo Cortex expected wheelhouse manifest must be a real file"
        )
    expected_raw = expected_manifest_path.read_bytes()
    try:
        manifest = json.loads(expected_raw)
    except json.JSONDecodeError as error:
        raise MnemoCortexLifecycleRunnerError(
            "Mnemo Cortex wheelhouse manifest is not JSON"
        ) from error
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise MnemoCortexLifecycleRunnerError(
            "Mnemo Cortex wheelhouse manifest schema drifted"
        )

    transported_manifest = wheelhouse_root / "wheelhouse-manifest.json"
    requirements = manifest.get("requirements")
    wheels = manifest.get("wheels")
    if (
        not transported_manifest.is_file()
        or transported_manifest.is_symlink()
        or transported_manifest.read_bytes() != expected_raw
        or not isinstance(requirements, dict)
        or not isinstance(requirements.get("filename"), str)
        or not isinstance(wheels, list)
        or not wheels
    ):
        raise MnemoCortexLifecycleRunnerError(
            "Mnemo Cortex transported wheelhouse manifest drifted"
        )

    lock_path = wheelhouse_root / requirements["filename"]
    wheels_root = wheelhouse_root / "wheels"
    if (
        not lock_path.is_file()
        or lock_path.is_symlink()
        or not wheels_root.is_dir()
        or wheels_root.is_symlink()
        or lock_path.stat().st_size != requirements.get("bytes")
        or _sha_path(lock_path) != requirements.get("sha256")
    ):
        raise MnemoCortexLifecycleRunnerError(
            "Mnemo Cortex wheelhouse requirements receipt drifted"
        )

    expected_rows: dict[str, tuple[int, str]] = {}
    for row in wheels:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("filename"), str)
            or Path(row["filename"]).name != row["filename"]
            or not row["filename"].endswith(".whl")
            or not isinstance(row.get("bytes"), int)
            or not isinstance(row.get("sha256"), str)
            or len(row["sha256"]) != 64
            or row["filename"] in expected_rows
        ):
            raise MnemoCortexLifecycleRunnerError(
                "Mnemo Cortex wheelhouse file manifest drifted"
            )
        expected_rows[row["filename"]] = (row["bytes"], row["sha256"])
    actual_names = {
        path.name for path in wheels_root.iterdir() if path.is_file()
    }
    if actual_names != set(expected_rows) or any(
        path.is_symlink() or not path.is_file() for path in wheels_root.iterdir()
    ):
        raise MnemoCortexLifecycleRunnerError(
            "Mnemo Cortex wheelhouse file set drifted"
        )
    for name, (expected_bytes, expected_sha) in expected_rows.items():
        path = wheels_root / name
        if path.stat().st_size != expected_bytes or _sha_path(path) != expected_sha:
            raise MnemoCortexLifecycleRunnerError(
                f"Mnemo Cortex wheelhouse artifact drifted: {name}"
            )
    top_level = {path.name for path in wheelhouse_root.iterdir()}
    if top_level != {
        "wheelhouse-manifest.json",
        requirements["filename"],
        "wheels",
    }:
        raise MnemoCortexLifecycleRunnerError(
            "Mnemo Cortex wheelhouse contains an unreceipted top-level artifact"
        )
    if (
        manifest.get("wheel_count") != len(expected_rows)
        or manifest.get("total_wheel_bytes")
        != sum(row[0] for row in expected_rows.values())
    ):
        raise MnemoCortexLifecycleRunnerError(
            "Mnemo Cortex wheelhouse aggregate receipt drifted"
        )
    return {
        "manifest": manifest,
        "manifest_bytes": expected_raw,
        "manifest_sha256": _sha(expected_raw),
        "requirements_bytes": lock_path.read_bytes(),
        "requirements_sha256": requirements["sha256"],
        "wheel_count": len(expected_rows),
        "total_wheel_bytes": manifest["total_wheel_bytes"],
    }


def _build_image(
    *,
    source_archive: bytes,
    source: dict[str, Any],
    wheelhouse_root: Path,
    wheelhouse: dict[str, Any],
    image: str,
) -> tuple[bytes, dict[str, Any], bytes]:
    with tempfile.TemporaryDirectory(prefix="cotcodec-mnemo-cortex-build-") as raw:
        root = Path(raw)
        source_dir = root / "source"
        source_dir.mkdir()
        _extract_source_archive(source_archive, source_dir)
        shutil.copytree(wheelhouse_root / "wheels", root / "wheels")
        requirements_filename = wheelhouse["manifest"]["requirements"]["filename"]
        shutil.copy2(wheelhouse_root / requirements_filename, root / requirements_filename)
        shutil.copy2(
            wheelhouse_root / "wheelhouse-manifest.json",
            root / "wheelhouse-manifest.json",
        )
        shutil.copy2(DOCKERFILE, root / "Dockerfile")
        shutil.copy2(DOCTOR, root / "doctor.py")
        completed = _run([
            "docker", "build", "--network", "none", "--platform", "linux/amd64",
            "--build-arg", f"SOURCE_REVISION={source['revision']}",
            "--build-arg", f"SOURCE_TREE={source['tree']}",
            "--build-arg", f"SOURCE_ARCHIVE_SHA256={source['archive_sha256']}",
            "--build-arg", f"DOCTOR_SHA256={_sha_path(DOCTOR)}",
            "--build-arg", f"WHEELHOUSE_MANIFEST_SHA256={wheelhouse['manifest_sha256']}",
            "--build-arg", f"REQUIREMENTS_SHA256={wheelhouse['requirements_sha256']}",
            "-t", image, str(root),
        ], timeout=2400)
        build_log = completed.stdout + completed.stderr
    raw_inspect = _run(["docker", "image", "inspect", image]).stdout
    rows = json.loads(raw_inspect)
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise MnemoCortexLifecycleRunnerError("Mnemo Cortex image inspection drifted")
    inspect = rows[0]
    config = inspect.get("Config") or {}
    labels = config.get("Labels") or {}
    expected_labels = {
        "org.opencontainers.image.source": "https://github.com/GuyMannDude/mnemo-cortex",
        "org.opencontainers.image.revision": source["revision"],
        "org.opencontainers.image.licenses": "MIT",
        "org.cotcodec.source-tree": source["tree"],
        "org.cotcodec.source-archive-sha256": source["archive_sha256"],
        "org.cotcodec.doctor-sha256": _sha_path(DOCTOR),
        "org.cotcodec.wheelhouse-manifest-sha256": wheelhouse["manifest_sha256"],
        "org.cotcodec.requirements-sha256": wheelhouse["requirements_sha256"],
        "org.cotcodec.discovery-only": "true",
        "org.cotcodec.upstream-container-git": "absent",
    }
    image_id = inspect.get("Id")
    if (
        any(labels.get(key) != value for key, value in expected_labels.items())
        or not isinstance(image_id, str)
        or not image_id.startswith("sha256:")
        or inspect.get("Architecture") != "amd64"
        or inspect.get("Os") != "linux"
        or config.get("User") != "65532:65532"
        or set(config.get("Volumes") or {}) != {"/state"}
    ):
        raise MnemoCortexLifecycleRunnerError("Mnemo Cortex image provenance drifted")
    projection = {
        "image_id": image_id,
        "architecture": "amd64",
        "os": "linux",
        "user": "65532:65532",
        "volumes": ["/state"],
        "labels": expected_labels,
    }
    return build_log, projection, raw_inspect


def _phase_argv(*, image_id: str, volume: str, phase: int, token: str) -> list[str]:
    return [
        "docker", "run", "--rm", "--pull=never", "--platform", "linux/amd64",
        "--network", "none", "--read-only", "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges", "--pids-limit", "256",
        "--memory", "4g", "--cpus", "2",
        "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=256m",
        "--mount", f"type=volume,src={volume},dst=/state",
        "-e", f"COTCODEC_PHASE={phase}",
        "-e", f"COTCODEC_RUN_TOKEN={token}",
        image_id,
    ]


def _parse_phase(raw: bytes, expected_phase: int) -> dict[str, Any]:
    marker = b"COTCODEC_MNEMO_CORTEX_PHASE="
    rows = [line.split(marker, 1)[1] for line in raw.splitlines() if marker in line]
    if len(rows) != 1:
        raise MnemoCortexLifecycleRunnerError(
            f"Mnemo Cortex phase {expected_phase} emitted {len(rows)} markers"
        )
    payload = json.loads(rows[0])
    checks = payload.get("checks") if isinstance(payload, dict) else None
    if (
        not isinstance(payload, dict)
        or payload.get("phase") != expected_phase
        or not isinstance(checks, dict)
        or not checks
        or not all(isinstance(value, bool) for value in checks.values())
        or not isinstance(payload.get("metrics"), dict)
    ):
        raise MnemoCortexLifecycleRunnerError(
            f"Mnemo Cortex phase {expected_phase} report drifted"
        )
    return payload


def _run_repeat(
    *, repeat: int, image_id: str
) -> tuple[dict[str, Any], dict[str, bytes]]:
    volume = f"cotcodec-mnemo-cortex-{secrets.token_hex(5)}"
    token = secrets.token_hex(8).upper()
    artifacts: dict[str, bytes] = {}
    _run(["docker", "volume", "create", volume])
    try:
        phases: list[dict[str, Any]] = []
        for phase in (1, 2):
            completed = subprocess.run(
                _phase_argv(
                    image_id=image_id, volume=volume, phase=phase, token=token
                ),
                capture_output=True,
                check=False,
                timeout=900,
            )
            raw = completed.stdout + completed.stderr
            artifacts[f"repeat-{repeat}-phase-{phase}.txt"] = raw
            payload = _parse_phase(raw, phase)
            checks_passed = all(payload["checks"].values())
            if completed.returncode not in {0, 3} or (
                completed.returncode == 0
            ) != checks_passed:
                raise MnemoCortexLifecycleRunnerError(
                    f"Mnemo Cortex phase {phase} exit/check contract drifted: "
                    f"returncode={completed.returncode}, checks_passed={checks_passed}"
                )
            payload["process_returncode"] = completed.returncode
            phases.append(payload)
        phase_one = phases[0]["metrics"]
        reasoning_stages = len(phase_one["reasoning_calls"]) + len(
            phase_one["dream_projection"]["calls"]
        )
        if reasoning_stages != 5:
            raise MnemoCortexLifecycleRunnerError(
                "Mnemo Cortex simulated reasoning-stage budget drifted"
            )
        stable_projection = [row["checks"] for row in phases]
        projection = {
            "repeat": repeat,
            "token": token,
            "phase_count": len(phases),
            "fresh_process_restart_count": len(phases) - 1,
            "simulated_reasoning_stage_calls": reasoning_stages,
            "external_model_calls": 0,
            "phases": phases,
            "stable_projection": stable_projection,
            "stable_projection_sha256": _sha(
                json.dumps(
                    stable_projection, separators=(",", ":"), sort_keys=True
                ).encode()
            ),
        }
        return projection, artifacts
    finally:
        subprocess.run(
            ["docker", "volume", "rm", volume], capture_output=True, check=False
        )


def _runtime_receipt() -> dict[str, Any]:
    job_id = os.environ.get("SLURM_JOB_ID")
    if not job_id:
        raise MnemoCortexLifecycleRunnerError(
            "Mnemo Cortex remote doctor requires Slurm ownership"
        )
    return {
        "schema_version": 1,
        "slurm_job_id": job_id,
        "slurm_job_name": os.environ.get("SLURM_JOB_NAME"),
        "slurm_cpus_per_task": os.environ.get("SLURM_CPUS_PER_TASK"),
        "slurm_mem_per_node": os.environ.get("SLURM_MEM_PER_NODE"),
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "gpu_requested": False,
        "docker_execution_network": "none",
        "provider_secrets": False,
        "external_model_calls": 0,
    }


def run(
    *, source_root: Path, wheelhouse_root: Path, image: str, output: Path
) -> dict[str, Any]:
    experiment = validate_experiment_contract()
    runtime = _runtime_receipt()
    source = _source_contract(source_root.resolve(), experiment)
    source_archive = source.pop("archive")
    wheelhouse = _wheelhouse_contract(wheelhouse_root.resolve())
    output.mkdir(parents=True, exist_ok=False)
    build_log, image_contract, image_inspect = _build_image(
        source_archive=source_archive,
        source=source,
        wheelhouse_root=wheelhouse_root.resolve(),
        wheelhouse=wheelhouse,
        image=image,
    )
    pip_freeze = _run([
        "docker", "run", "--rm", "--pull=never", "--network", "none",
        "--entrypoint", "python", image_contract["image_id"], "-m", "pip", "freeze",
    ]).stdout
    git_probe = _run([
        "docker", "run", "--rm", "--pull=never", "--network", "none",
        "--entrypoint", "python", image_contract["image_id"], "-c",
        "import shutil; assert shutil.which('git') is None",
    ]).stdout

    repeats: list[dict[str, Any]] = []
    phase_artifacts: dict[str, bytes] = {}
    for repeat in (1, 2):
        projection, artifacts = _run_repeat(
            repeat=repeat, image_id=image_contract["image_id"]
        )
        repeats.append(projection)
        phase_artifacts.update(artifacts)

    clean_states_reproduced = (
        repeats[0]["stable_projection"] == repeats[1]["stable_projection"]
    )
    normalized_values: dict[str, list[bool]] = {}
    for repeat in repeats:
        for phase in repeat["phases"]:
            for key, value in phase["checks"].items():
                normalized_values.setdefault(
                    key.removesuffix("_after_restart"), []
                ).append(value)
    expected = {
        key: value
        for key, value in experiment["expected_falsification"].items()
        if key not in {"status", "reproduced_in_two_clean_states"}
    }
    if not set(expected).issubset(normalized_values):
        missing = sorted(set(expected) - set(normalized_values))
        raise MnemoCortexLifecycleRunnerError(
            f"Mnemo Cortex expected finding projection drifted: {missing}"
        )
    observed = {
        key: all(values) for key, values in sorted(normalized_values.items())
    }
    registered_projection_matches = clean_states_reproduced and all(
        all(value == expected[key] for value in normalized_values[key])
        for key in expected
    )
    status = EXPECTED_STATUS if registered_projection_matches else UNEXPECTED_STATUS
    unexpected_checks = sorted(
        key
        for key in expected
        if any(value != expected[key] for value in normalized_values[key])
    )
    report = {
        "schema_version": 1,
        "status": status,
        "registered_expected_status": EXPECTED_STATUS,
        "registered_projection_matches": registered_projection_matches,
        "unexpected_checks": unexpected_checks,
        "observed_checks": observed,
        "scientific_result": False,
        "publication_ready": False,
        "h100_admission": False,
        "source": source,
        "wheelhouse": {
            "manifest_sha256": wheelhouse["manifest_sha256"],
            "requirements_sha256": wheelhouse["requirements_sha256"],
            "wheel_count": wheelhouse["wheel_count"],
            "total_wheel_bytes": wheelhouse["total_wheel_bytes"],
            "target": wheelhouse["manifest"]["target"],
            "resolver": wheelhouse["manifest"]["resolver"],
            "downloader": wheelhouse["manifest"]["downloader"],
            "docker_build_network": "none",
        },
        "image": image_contract,
        "runtime": runtime,
        "repeats": repeats,
        "stable_projection_sha256": repeats[0]["stable_projection_sha256"],
        "reproduced_in_two_clean_states": clean_states_reproduced,
        "claim_boundary": experiment["claim_boundary"],
        "next_gate": experiment["admission"]["next_gate"],
    }

    files: dict[str, bytes] = {
        "source.tar": source_archive,
        "source-receipt.json": _json_bytes(source),
        "wheelhouse-manifest.json": wheelhouse["manifest_bytes"],
        wheelhouse["manifest"]["requirements"]["filename"]: wheelhouse[
            "requirements_bytes"
        ],
        "doctor-image-build.txt": build_log,
        "doctor-image-inspect.json": image_inspect,
        "pip-freeze.txt": pip_freeze,
        "git-probe.txt": git_probe,
        "runtime-receipt.json": _json_bytes(runtime),
        "experiment.yaml": DEFAULT_EXPERIMENT.read_bytes(),
        "Dockerfile": DOCKERFILE.read_bytes(),
        "doctor.py": DOCTOR.read_bytes(),
        "runner.py": Path(__file__).read_bytes(),
        "batch.sbatch": BATCH.read_bytes(),
    }
    files.update(phase_artifacts)
    for repeat in repeats:
        files[f"repeat-{repeat['repeat']}.json"] = _json_bytes(repeat)
    files["report.json"] = _json_bytes(report)
    for name, data in files.items():
        _write_once(output / name, data)
    manifest_files = {name: _sha(data) for name, data in sorted(files.items())}
    manifest = {
        "schema_version": 1,
        "status": status,
        "file_count": len(manifest_files),
        "files": manifest_files,
        "report_sha256": manifest_files["report.json"],
        "source_archive_sha256": manifest_files["source.tar"],
    }
    _write_once(output / "manifest.json", _json_bytes(manifest))
    print(json.dumps(report, indent=2, sort_keys=True))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument(
        "--wheelhouse-root", type=Path, default=DEFAULT_WHEELHOUSE
    )
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    run(
        source_root=args.source_root,
        wheelhouse_root=args.wheelhouse_root,
        image=args.image,
        output=args.output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
