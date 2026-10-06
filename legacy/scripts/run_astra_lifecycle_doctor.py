#!/usr/bin/env python3
"""Run ASTRA's native lifecycle admission doctor inside an H100 Slurm job."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path, PurePosixPath
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validate_astra_lifecycle_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    EXPECTED_STATUS,
    validate_experiment_contract,
)

DOCTOR_ROOT = PROJECT_ROOT / "infra" / "memory-baselines" / "astra"
RUNNER_PATH = PROJECT_ROOT / "scripts" / "run_astra_lifecycle_doctor.py"
BATCH_PATH = PROJECT_ROOT / "infra" / "slurm" / "host-single-node" / "astra-lifecycle.sbatch"
EXTRACTOR_PATH = PROJECT_ROOT / "scripts" / "extract_discovery_source_archive.py"
DEFAULT_OUTPUT = Path("/home/kevin/cotcodec-runs/astra-native-lifecycle")
DEFAULT_IMAGE_TAG = "cotcodec-astra-lifecycle:644f9d4-amd64-v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
MAX_ARCHIVE_MEMBERS = 20_000
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
_PREEMPT_REQUESTED: int | None = None


class DoctorError(RuntimeError):
    """Raised when ASTRA provenance, containment, or lifecycle behavior drifts."""


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
    check: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        argv,
        cwd=cwd,
        check=False,
        capture_output=True,
        timeout=timeout,
    )
    if check and completed.returncode != 0:
        raise DoctorError(
            f"command failed ({completed.returncode}): {argv!r}\n"
            f"stdout={completed.stdout.decode(errors='replace')}\n"
            f"stderr={completed.stderr.decode(errors='replace')}"
        )
    return completed


def _strict_json(data: bytes, label: str) -> dict[str, Any]:
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
    directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _request_preemption(signum: int, _frame: object) -> None:
    global _PREEMPT_REQUESTED
    _PREEMPT_REQUESTED = signum


def _extract_archive(archive: bytes, destination: Path) -> None:
    total = 0
    seen: set[str] = set()
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as bundle:
        members = bundle.getmembers()
        if not members or len(members) > MAX_ARCHIVE_MEMBERS:
            raise DoctorError("ASTRA archive member count is invalid")
        for member in members:
            relative = PurePosixPath(member.name)
            if relative.is_absolute() or ".." in relative.parts or not relative.parts:
                raise DoctorError(f"unsafe ASTRA archive path: {member.name}")
            name = relative.as_posix()
            if name in seen:
                raise DoctorError(f"duplicate ASTRA archive path: {name}")
            seen.add(name)
            target = destination / name
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                raise DoctorError(f"unsupported ASTRA archive member: {name}")
            total += member.size
            if total > MAX_ARCHIVE_BYTES:
                raise DoctorError("ASTRA archive exceeds uncompressed byte ceiling")
            target.parent.mkdir(parents=True, exist_ok=True)
            source = bundle.extractfile(member)
            if source is None:
                raise DoctorError(f"ASTRA archive member has no bytes: {name}")
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
        raise DoctorError("ASTRA Git identity drifted")
    if _run(["git", "status", "--porcelain"], cwd=checkout).stdout.strip():
        raise DoctorError("ASTRA checkout is dirty")
    archive = _run(["git", "archive", "--format=tar", "HEAD"], cwd=checkout).stdout
    if _sha(archive) != source["git_archive_tar_sha256"]:
        raise DoctorError("ASTRA source archive drifted")
    expected_files = {
        "LICENSE": source["license_sha256"],
        "package-lock.json": source["package_lock_sha256"],
        "package.json": source["package_json_sha256"],
    }
    for name, expected in expected_files.items():
        if _sha_path(checkout / name) != expected:
            raise DoctorError(f"ASTRA {name} drifted")

    context = root / "context"
    upstream = context / "upstream"
    upstream.mkdir(parents=True)
    _extract_archive(archive, upstream)
    shutil.copy2(DOCTOR_ROOT / "Dockerfile", context / "Dockerfile")
    shutil.copy2(DOCTOR_ROOT / "doctor.ts", context / "doctor.ts")
    return {
        "context": context,
        "repository": source["repository"],
        "revision": revision,
        "tree": tree,
        "git_archive_tar_sha256": _sha(archive),
        "archive_bytes": len(archive),
        "license_sha256": _sha_path(checkout / "LICENSE"),
        "package_lock_sha256": _sha_path(checkout / "package-lock.json"),
        "package_json_sha256": _sha_path(checkout / "package.json"),
        "dockerfile_sha256": _sha_path(DOCTOR_ROOT / "Dockerfile"),
        "doctor_sha256": _sha_path(DOCTOR_ROOT / "doctor.ts"),
        "worktree_clean": True,
    }


def _inspect_one(image: str) -> dict[str, Any]:
    raw = _run(["docker", "image", "inspect", image]).stdout
    try:
        rows = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DoctorError(f"Docker inspect is invalid for {image}") from exc
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise DoctorError(f"Docker inspect must return one image for {image}")
    return {"raw_sha256": _sha(raw), "payload": rows[0]}


def _acquire_images(
    experiment: dict[str, Any],
    source: dict[str, Any],
    image_tag: str,
    app_image_archive: Path,
) -> dict[str, Any]:
    runtime = experiment["runtime"]
    if not app_image_archive.is_file() or app_image_archive.is_symlink():
        raise DoctorError("ASTRA preloaded app image archive must be a regular file")
    archive_sha256 = _sha_path(app_image_archive)
    if archive_sha256 != runtime["app_image_archive_sha256"]:
        raise DoctorError("ASTRA preloaded app image archive drifted")
    _run(
        ["docker", "load", "--input", str(app_image_archive)],
        timeout=1800,
    )
    database_probe = _run(
        ["docker", "image", "inspect", runtime["database_image"]],
        check=False,
    )
    if database_probe.returncode != 0:
        _run(["docker", "pull", runtime["database_image"]], timeout=1800)
    app = _inspect_one(image_tag)
    database = _inspect_one(runtime["database_image"])
    for label, inspect in (("app", app), ("database", database)):
        payload = inspect["payload"]
        if payload.get("Architecture") != "amd64" or payload.get("Os") != "linux":
            raise DoctorError(f"ASTRA {label} image platform drifted")
        image_id = payload.get("Id")
        if not isinstance(image_id, str) or not image_id.startswith("sha256:"):
            raise DoctorError(f"ASTRA {label} image ID is invalid")
    labels = app["payload"].get("Config", {}).get("Labels", {})
    if app["payload"].get("Id") != runtime["app_image_id"]:
        raise DoctorError("ASTRA preloaded app image ID drifted")
    if labels.get("org.opencontainers.image.revision") != experiment["source"]["revision"]:
        raise DoctorError("ASTRA app image revision label drifted")
    if labels.get("org.cotcodec.source-archive-sha256") != experiment["source"][
        "git_archive_tar_sha256"
    ]:
        raise DoctorError("ASTRA app image source label drifted")
    repo_digests = database["payload"].get("RepoDigests", [])
    expected_digest = runtime["database_image"].split("@", 1)[1]
    if not any(
        isinstance(value, str) and value.endswith(f"@{expected_digest}")
        for value in repo_digests
    ):
        raise DoctorError("CockroachDB resolved repository digest drifted")
    return {
        "app_image_id": app["payload"]["Id"],
        "app_image_acquisition": runtime["app_image_acquisition"],
        "app_image_archive_sha256": archive_sha256,
        "database_image_id": database["payload"]["Id"],
        "app_inspect_sha256": app["raw_sha256"],
        "database_inspect_sha256": database["raw_sha256"],
        "database_repo_digests": repo_digests,
    }


def _start_database(
    *, name: str, state_dir: Path, database_image_id: str
) -> list[str]:
    uid = str(os.getuid())
    gid = str(os.getgid())
    argv = [
        "docker",
        "run",
        "--detach",
        "--pull=never",
        "--name",
        name,
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        "2048",
        "--memory",
        "4g",
        "--cpus",
        "8",
        "--user",
        f"{uid}:{gid}",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=512m",
        "-v",
        f"{state_dir}:/cockroach/cockroach-data:rw",
        "--entrypoint",
        "/cockroach/cockroach",
        database_image_id,
        "start-single-node",
        "--insecure",
        "--listen-addr=127.0.0.1:26257",
        "--http-addr=127.0.0.1:8080",
        "--store=/cockroach/cockroach-data",
        "--cache=256MiB",
        "--max-sql-memory=256MiB",
    ]
    _run(argv)
    return argv


def _wait_database(name: str, *, timeout: int = 120) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        check = _run(
            [
                "docker",
                "exec",
                name,
                "/cockroach/cockroach",
                "sql",
                "--insecure",
                "--host=localhost:26257",
                "--execute=SELECT 1",
            ],
            timeout=20,
            check=False,
        )
        if check.returncode == 0:
            return
        status = _run(
            ["docker", "inspect", "--format={{.State.Running}}", name],
            check=False,
        )
        if status.returncode != 0 or status.stdout.strip() != b"true":
            log_result = _run(["docker", "logs", name], check=False)
            logs = (log_result.stdout + log_result.stderr).decode(errors="replace")
            raise DoctorError(f"CockroachDB exited during startup: {logs[-4000:]}")
        time.sleep(2)
    raise DoctorError("CockroachDB readiness timed out")


def _run_app_phase(
    *, app_image_id: str, database_name: str, phase: str
) -> dict[str, Any]:
    doctor_path = (DOCTOR_ROOT / "doctor.ts").resolve(strict=True)
    _sha_path(doctor_path)
    argv = [
        "docker",
        "run",
        "--rm",
        "--pull=never",
        "--network",
        f"container:{database_name}",
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
        "4",
        "--user",
        "65532:65532",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=256m",
        "-e",
        "HOME=/tmp",
        "-e",
        "ASTRA_DB_URL=postgresql://root@127.0.0.1:26257/astra?sslmode=disable",
        "--mount",
        f"type=bind,src={doctor_path},dst=/opt/astra/cotcodec-doctor.ts,readonly",
        "--entrypoint",
        "node",
        app_image_id,
        "--import",
        "tsx",
        "/opt/astra/cotcodec-doctor.ts",
        phase,
    ]
    completed = _run(argv, timeout=900)
    return {
        "argv": argv,
        "stdout_sha256": _sha(completed.stdout),
        "stderr_sha256": _sha(completed.stderr),
        "result": _strict_json(completed.stdout, f"ASTRA {phase}"),
    }


def _safe_remove_container(name: str) -> None:
    _run(["docker", "rm", "--force", name], timeout=60, check=False)


def _one_repeat(
    *, root: Path, index: int, app_image_id: str, database_image_id: str
) -> dict[str, Any]:
    suffix = f"{os.getpid()}-{index}"
    database = f"cotcodec-astra-db-{suffix}"
    state_dir = root / f"state-{index}"
    state_dir.mkdir(mode=0o700)
    first_start: list[str] | None = None
    second_start: list[str] | None = None
    first_logs = b""
    second_logs = b""
    try:
        first_start = _start_database(
            name=database,
            state_dir=state_dir,
            database_image_id=database_image_id,
        )
        _wait_database(database)
        prepared = _run_app_phase(
            app_image_id=app_image_id,
            database_name=database,
            phase="prepare",
        )
        _run(["docker", "kill", "--signal=KILL", database], timeout=60)
        first_logs = _run(["docker", "logs", database], check=False).stdout
        _safe_remove_container(database)

        second_start = _start_database(
            name=database,
            state_dir=state_dir,
            database_image_id=database_image_id,
        )
        _wait_database(database)
        restarted = _run_app_phase(
            app_image_id=app_image_id,
            database_name=database,
            phase="restart",
        )
        _run(["docker", "stop", "--time=15", database], timeout=60)
        second_logs = _run(["docker", "logs", database], check=False).stdout
        if restarted["result"].get("terminal_status") != EXPECTED_STATUS:
            raise DoctorError("ASTRA terminal status drifted")
        return {
            "repeat": index,
            "database_first_start_argv": first_start,
            "database_second_start_argv": second_start,
            "database_first_log_sha256": _sha(first_logs),
            "database_second_log_sha256": _sha(second_logs),
            "forced_database_sigkill": True,
            "prepare": prepared,
            "restart": restarted,
        }
    finally:
        _safe_remove_container(database)


def _semantic_projection(run: dict[str, Any]) -> dict[str, Any]:
    prepare = run["prepare"]["result"]
    restart = run["restart"]["result"]
    return {
        "prepare": {
            key: prepare[key]
            for key in (
                "bounded_unpinned_window",
                "evicted_memory_remains_durable",
                "retrieval_driven_readmission",
                "user_isolation",
                "duplicate_write_creates_distinct_rows",
                "all_pinned_window_size",
                "all_pinned_window_exceeds_capacity",
                "projection",
            )
        },
        "restart": {
            key: restart[key]
            for key in (
                "terminal_status",
                "forced_restart_preserves_acknowledged_state",
                "retrieval_driven_readmission",
                "user_isolation",
                "soft_deleted_plaintext_row_remains",
                "session_state_retains_soft_deleted_reference",
                "native_physical_user_purge_available",
                "native_idempotency_key_available",
                "projection",
            )
        },
    }


def _execution_contract(
    experiment_path: Path,
    app_image_archive: Path,
    expected_app_image_archive_sha256: str,
) -> dict[str, Any]:
    source_sha256 = os.environ.get("COTCODEC_SOURCE_SHA256", "")
    git_sha = os.environ.get("COTCODEC_GIT_SHA", "")
    git_tree = os.environ.get("COTCODEC_GIT_TREE", "")
    active_batch_sha256 = os.environ.get("COTCODEC_BATCH_SHA256", "")
    extractor_sha256 = os.environ.get("COTCODEC_SOURCE_EXTRACTOR_SHA256", "")
    if not SHA256_RE.fullmatch(source_sha256):
        raise DoctorError("COTCODEC_SOURCE_SHA256 is missing or malformed")
    if re.fullmatch(r"[0-9a-f]{40}", git_sha) is None or re.fullmatch(
        r"[0-9a-f]{40}", git_tree
    ) is None:
        raise DoctorError("COTCODEC Git identities are missing or malformed")
    if not SHA256_RE.fullmatch(active_batch_sha256) or not SHA256_RE.fullmatch(
        extractor_sha256
    ):
        raise DoctorError("active batch or extractor identity is missing or malformed")
    code_sha256 = {
        "runner": _sha_path(RUNNER_PATH),
        "dockerfile": _sha_path(DOCTOR_ROOT / "Dockerfile"),
        "doctor": _sha_path(DOCTOR_ROOT / "doctor.ts"),
        "experiment": _sha_path(experiment_path),
        "batch": _sha_path(BATCH_PATH),
        "extractor": _sha_path(EXTRACTOR_PATH),
    }
    if code_sha256["batch"] != active_batch_sha256:
        raise DoctorError("active Slurm batch differs from the extracted source")
    if code_sha256["extractor"] != extractor_sha256:
        raise DoctorError("active source extractor differs from the extracted source")
    app_image_archive_sha256 = _sha_path(app_image_archive)
    if app_image_archive_sha256 != expected_app_image_archive_sha256:
        raise DoctorError("active ASTRA app image archive differs from the experiment")
    payload = {
        "source_archive_sha256": source_sha256,
        "app_image_archive_sha256": app_image_archive_sha256,
        "git_sha": git_sha,
        "git_tree": git_tree,
        "code_sha256": code_sha256,
        "python": {
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
            "executable": sys.executable,
        },
    }
    return {"payload": payload, "sha256": _sha(_json_bytes(payload))}


def _validate_repeat_checkpoint(
    *, path: Path, index: int, execution_contract_sha256: str
) -> dict[str, Any]:
    run = _strict_json(path.read_bytes(), f"ASTRA repeat {index}")
    if (
        run.get("repeat") != index
        or run.get("execution_contract_sha256") != execution_contract_sha256
        or run.get("restart", {}).get("result", {}).get("terminal_status")
        != EXPECTED_STATUS
    ):
        raise DoctorError(f"ASTRA repeat {index} checkpoint drifted")
    _semantic_projection(run)
    return run


def _validate_completed_report(
    *,
    output: Path,
    experiment_path: Path,
    execution_contract: dict[str, Any],
) -> dict[str, Any]:
    expected_files = {"report.json", "repeat-0.json", "repeat-1.json"}
    observed_files = {path.name for path in output.iterdir()}
    if observed_files != expected_files or any(
        not path.is_file() or path.is_symlink() for path in output.iterdir()
    ):
        raise DoctorError("completed ASTRA output roster drifted")
    report = _strict_json((output / "report.json").read_bytes(), "ASTRA report")
    if (
        report.get("status") != EXPECTED_STATUS
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("experiment_sha256") != _sha_path(experiment_path)
        or report.get("execution_contract") != execution_contract
    ):
        raise DoctorError("completed ASTRA report drifted")
    repeat_files = report.get("repeat_files")
    if not isinstance(repeat_files, list) or len(repeat_files) != 2:
        raise DoctorError("completed ASTRA repeat manifest drifted")
    runs: list[dict[str, Any]] = []
    for index, item in enumerate(repeat_files):
        if not isinstance(item, dict) or item.get("path") != f"repeat-{index}.json":
            raise DoctorError("completed ASTRA repeat entry is invalid")
        path = output / item["path"]
        if _sha_path(path) != item.get("sha256"):
            raise DoctorError("completed ASTRA repeat hash drifted")
        runs.append(
            _validate_repeat_checkpoint(
                path=path,
                index=index,
                execution_contract_sha256=execution_contract["sha256"],
            )
        )
    projections = [_semantic_projection(run) for run in runs]
    projection_sha256s = [_sha(_json_bytes(value)) for value in projections]
    if (
        len(set(projection_sha256s)) != 1
        or report.get("semantic_projection") != projections[0]
        or report.get("semantic_projection_sha256") != projection_sha256s[0]
    ):
        raise DoctorError("completed ASTRA semantic projection drifted")
    return report


def _cluster_receipt() -> dict[str, Any]:
    job_id = os.environ.get("SLURM_JOB_ID")
    job_gpus = os.environ.get("SLURM_JOB_GPUS")
    visible = os.environ.get("CUDA_VISIBLE_DEVICES")
    if not job_id or not job_id.isdigit() or int(job_id) <= 0:
        raise DoctorError("ASTRA doctor requires a real Slurm job")
    if not job_gpus or not visible:
        raise DoctorError("ASTRA doctor requires one allocated visible H100")
    visible_devices = [value for value in visible.split(",") if value]
    if len(visible_devices) != 1:
        raise DoctorError(f"expected one CUDA-visible device, observed {visible!r}")
    gpu = _run(
        [
            "nvidia-smi",
            "--id",
            visible_devices[0],
            "--query-gpu=name,uuid,memory.total",
            "--format=csv,noheader",
        ]
    ).stdout.decode().strip().splitlines()
    if len(gpu) != 1 or "H100" not in gpu[0]:
        raise DoctorError(f"expected exactly one H100, observed {gpu!r}")
    return {
        "slurm_job_id": int(job_id),
        "slurm_job_gpus": job_gpus,
        "cuda_visible_devices": visible,
        "gpu_inventory": gpu,
    }


def run_doctor(
    *,
    experiment_path: Path,
    output: Path,
    image_tag: str,
    app_image_archive: Path,
    resume: bool,
) -> dict[str, Any]:
    experiment = validate_experiment_contract(experiment_path)
    cluster = _cluster_receipt()
    execution_contract = _execution_contract(
        experiment_path,
        app_image_archive,
        experiment["runtime"]["app_image_archive_sha256"],
    )
    if output.exists() and not resume:
        raise DoctorError(f"output already exists: {output}")
    if output.exists() and (not output.is_dir() or output.is_symlink()):
        raise DoctorError("resume output must be a regular directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and (output / "report.json").exists():
        return _validate_completed_report(
            output=output,
            experiment_path=experiment_path,
            execution_contract=execution_contract,
        )

    with tempfile.TemporaryDirectory(prefix="cotcodec-astra-") as temp:
        root = Path(temp)
        source = _prepare_context(root, experiment)
        images = _acquire_images(
            experiment,
            source,
            image_tag,
            app_image_archive,
        )
        runs: list[dict[str, Any]] = []
        if not output.exists():
            output.mkdir(mode=0o700)
        allowed = {f"repeat-{index}.json" for index in range(2)}
        unexpected = {path.name for path in output.iterdir()} - allowed
        if unexpected:
            raise DoctorError(f"unexpected ASTRA resume artifacts: {sorted(unexpected)}")
        for index in range(experiment["runtime"]["clean_state_repeats"]):
            repeat_path = output / f"repeat-{index}.json"
            if repeat_path.exists():
                run = _validate_repeat_checkpoint(
                    path=repeat_path,
                    index=index,
                    execution_contract_sha256=execution_contract["sha256"],
                )
            else:
                run = _one_repeat(
                    root=root,
                    index=index,
                    app_image_id=images["app_image_id"],
                    database_image_id=images["database_image_id"],
                )
                run["slurm_job_id"] = cluster["slurm_job_id"]
                run["execution_contract_sha256"] = execution_contract["sha256"]
                _write_once(repeat_path, _json_bytes(run))
            runs.append(run)
            if _PREEMPT_REQUESTED is not None:
                raise DoctorError(
                    "preemption signal received; stopped after durable clean-repeat checkpoint"
                )
        projections = [_semantic_projection(run) for run in runs]
        projection_sha256s = [_sha(_json_bytes(value)) for value in projections]
        if len(set(projection_sha256s)) != 1:
            raise DoctorError("ASTRA clean-state semantic projections differ")
        report = {
            "schema_version": 1,
            "status": EXPECTED_STATUS,
            "scientific_result": False,
            "publication_ready": False,
            "evidence_role": "native-lifecycle-admission-negative",
            "experiment_sha256": _sha_path(experiment_path),
            "execution_contract": execution_contract,
            "source": {key: value for key, value in source.items() if key != "context"},
            "images": images,
            "cluster": cluster,
            "checkpoint_slurm_job_ids": sorted(
                {int(run["slurm_job_id"]) for run in runs}
            ),
            "runtime": {
                "containment": "docker-under-slurm",
                "host_acquisition_network": (
                    "pinned-git-and-cached-database-digest-only"
                ),
                "app_image_acquisition": "preloaded-docker-save",
                "measured_container_external_network": "none",
                "measured_container_network": (
                    "shared-container-namespace-loopback-only"
                ),
                "sudo_used": False,
                "model_calls": 0,
                "external_embedding_calls": 0,
                "clean_state_repeats": len(runs),
                "checkpoint_boundary": "completed-clean-repeat",
            },
            "semantic_projection": projections[0],
            "semantic_projection_sha256": projection_sha256s[0],
            "repeat_files": [
                {
                    "path": f"repeat-{index}.json",
                    "sha256": _sha_path(output / f"repeat-{index}.json"),
                }
                for index in range(len(runs))
            ],
            "claim_boundary": {
                "component_conformance": True,
                "native_cockroach_lifecycle_executed": True,
                "h100_actor_admission": "forbidden-for-this-revision",
                "memory_quality_evaluated": False,
                "causal_credit_evaluated": False,
            },
        }
        _write_once(output / "report.json", _json_bytes(report))
        return _validate_completed_report(
            output=output,
            experiment_path=experiment_path,
            execution_contract=execution_contract,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, default=DEFAULT_EXPERIMENT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--image-tag", default=DEFAULT_IMAGE_TAG)
    parser.add_argument("--app-image-archive", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    signal.signal(signal.SIGUSR1, _request_preemption)
    signal.signal(signal.SIGTERM, _request_preemption)
    try:
        report = run_doctor(
            experiment_path=args.experiment.resolve(),
            output=args.output.resolve(),
            image_tag=args.image_tag,
            app_image_archive=args.app_image_archive.resolve(),
            resume=args.resume,
        )
    except (DoctorError, ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f"ASTRA lifecycle doctor FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
