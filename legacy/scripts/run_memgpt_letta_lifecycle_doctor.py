#!/usr/bin/env python3
"""Run the exact-source legacy Letta lifecycle doctor under Docker."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validate_memgpt_letta_lifecycle_experiment import (  # noqa: E402
    ARCHIVE_SHA256,
    DEFAULT_EXPERIMENT,
    EXPECTED_STATUS,
    IMAGE,
    REVISION,
    TREE,
    validate_experiment_contract,
)

DOCTOR = PROJECT_ROOT / "infra/memory-baselines/memgpt-letta/doctor.py"
RUNNER = Path(__file__).resolve()
VALIDATOR = PROJECT_ROOT / "scripts/validate_memgpt_letta_lifecycle_experiment.py"


class RunnerError(RuntimeError):
    """Raised when provenance or runtime setup cannot produce a result."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _run(
    command: list[str],
    *,
    check: bool = True,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if check and completed.returncode != 0:
        raise RunnerError(
            f"command failed ({completed.returncode}): {command!r}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def _git(source_root: Path, *arguments: str) -> str:
    return _run(["git", "-C", str(source_root), *arguments]).stdout.strip()


def _validate_source(
    source_root: Path,
    source_archive: Path,
    contract: dict[str, Any],
) -> dict[str, Any]:
    if not source_root.is_dir() or source_root.is_symlink():
        raise RunnerError("source root must be a real directory")
    if _git(source_root, "rev-parse", "HEAD") != REVISION:
        raise RunnerError("source revision drifted")
    if _git(source_root, "rev-parse", "HEAD^{tree}") != TREE:
        raise RunnerError("source tree drifted")
    if _git(source_root, "status", "--porcelain"):
        raise RunnerError("source checkout is dirty")
    if not source_archive.is_file() or source_archive.is_symlink():
        raise RunnerError("source archive must be a regular file")
    archive_sha = _sha256(source_archive)
    if archive_sha != ARCHIVE_SHA256:
        raise RunnerError("source archive digest drifted")
    if source_archive.stat().st_size != contract["source"]["git_archive_tar_bytes"]:
        raise RunnerError("source archive size drifted")

    expected_files = {
        "LICENSE": contract["source"]["license_sha256"],
        "pyproject.toml": contract["source"]["pyproject_sha256"],
        "uv.lock": contract["source"]["lock_sha256"],
        "Dockerfile": contract["source"]["upstream_dockerfile_sha256"],
        **contract["source"]["exact_source_files"],
    }
    actual_files = {}
    for relative, expected_sha in expected_files.items():
        path = source_root / relative
        if not path.is_file() or path.is_symlink():
            raise RunnerError(f"source file is missing or unsafe: {relative}")
        actual_sha = _sha256(path)
        if actual_sha != expected_sha:
            raise RunnerError(f"source file digest drifted: {relative}")
        actual_files[relative] = actual_sha
    return {
        "repository": contract["source"]["repository"],
        "revision": REVISION,
        "tree": TREE,
        "archive_sha256": archive_sha,
        "archive_bytes": source_archive.stat().st_size,
        "file_sha256": actual_files,
    }


def _validate_context_source(
    context_root: Path,
    context_archive: Path,
    contract: dict[str, Any],
) -> dict[str, Any]:
    context = contract["current_runtime_context"]
    if not context_root.is_dir() or context_root.is_symlink():
        raise RunnerError("current runtime context root must be a real directory")
    if _git(context_root, "rev-parse", "HEAD") != context["revision"]:
        raise RunnerError("current runtime context revision drifted")
    if _git(context_root, "rev-parse", "HEAD^{tree}") != context["tree"]:
        raise RunnerError("current runtime context tree drifted")
    if _git(context_root, "status", "--porcelain"):
        raise RunnerError("current runtime context checkout is dirty")
    expected_files = {
        "LICENSE": context["license_sha256"],
        "package.json": context["package_sha256"],
        "bun.lock": context["lock_sha256"],
    }
    for relative, expected_sha in expected_files.items():
        if _sha256(context_root / relative) != expected_sha:
            raise RunnerError(f"current runtime context digest drifted: {relative}")
    if (
        not context_archive.is_file()
        or context_archive.is_symlink()
        or _sha256(context_archive) != context["git_archive_tar_sha256"]
        or context_archive.stat().st_size != context["git_archive_tar_bytes"]
    ):
        raise RunnerError("current runtime context archive drifted")
    return {
        "repository": context["repository"],
        "revision": context["revision"],
        "tree": context["tree"],
        "archive_sha256": context["git_archive_tar_sha256"],
        "archive_bytes": context["git_archive_tar_bytes"],
        "role": context["role"],
    }


def _pull_and_validate_image(contract: dict[str, Any]) -> dict[str, Any]:
    pull = _run(["docker", "pull", IMAGE], timeout=1200)
    inspect = _run(["docker", "image", "inspect", IMAGE])
    inspect_payload = json.loads(inspect.stdout)
    if not isinstance(inspect_payload, list) or len(inspect_payload) != 1:
        raise RunnerError("docker image inspection returned an unexpected shape")

    expected_files = {
        "/app/LICENSE": contract["source"]["license_sha256"],
        "/app/pyproject.toml": contract["source"]["pyproject_sha256"],
        "/app/uv.lock": contract["source"]["lock_sha256"],
        "/app/Dockerfile": contract["source"]["upstream_dockerfile_sha256"],
        **{
            f"/app/{relative}": digest
            for relative, digest in contract["source"]["exact_source_files"].items()
        },
    }
    hashes = _run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--entrypoint",
            "sha256sum",
            IMAGE,
            *expected_files,
        ],
        timeout=300,
    )
    actual_files = {}
    for line in hashes.stdout.splitlines():
        digest, path = line.split(maxsplit=1)
        actual_files[path] = digest
    if actual_files != expected_files:
        raise RunnerError("official image source files do not match the exact checkout")
    version = _run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--entrypoint",
            "python",
            IMAGE,
            "-c",
            (
                "import importlib.metadata,platform;"
                "print(importlib.metadata.version('letta'));"
                "print(platform.python_version())"
            ),
        ],
        timeout=300,
    ).stdout.splitlines()
    if not version or version[0] != contract["runtime"]["image_version"]:
        raise RunnerError("official image package version drifted")
    config_env = inspect_payload[0].get("Config", {}).get("Env", [])
    secret_env = [
        item
        for item in config_env
        if ("API_KEY=" in item or "TOKEN=" in item) and item.split("=", 1)[-1]
    ]
    if secret_env:
        raise RunnerError("official image contains a nonempty provider credential")
    return {
        "reference": IMAGE,
        "image_id": inspect_payload[0]["Id"],
        "repo_digests": sorted(inspect_payload[0].get("RepoDigests", [])),
        "source_file_sha256": actual_files,
        "letta_version": version[0],
        "python_version": version[1] if len(version) > 1 else None,
        "pull_stdout": pull.stdout,
        "pull_stderr": pull.stderr,
    }


def _wait_for_server(container: str, timeout_seconds: float = 240.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    command = [
        "docker",
        "exec",
        container,
        "python",
        "-c",
        (
            "import urllib.request;"
            "r=urllib.request.urlopen('http://127.0.0.1:8283/v1/health',timeout=2);"
            "assert r.status < 500"
        ),
    ]
    while time.monotonic() < deadline:
        completed = _run(command, check=False, timeout=10)
        if completed.returncode == 0:
            return
        time.sleep(2)
    logs = _run(["docker", "logs", container], check=False).stdout
    raise RunnerError(f"Letta server did not become ready\n{logs[-8000:]}")


def _record_logs(container: str, path: Path, heading: str) -> None:
    logs = _run(["docker", "logs", container], check=False)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"\n===== {heading} stdout =====\n")
        handle.write(logs.stdout)
        handle.write(f"\n===== {heading} stderr =====\n")
        handle.write(logs.stderr)


def _stop_container(container: str, evidence_dir: Path, heading: str) -> None:
    pg_stop = _run(
        [
            "docker",
            "exec",
            "-u",
            "postgres",
            container,
            "pg_ctl",
            "-D",
            "/var/lib/postgresql/data",
            "-m",
            "fast",
            "-w",
            "stop",
        ],
        check=False,
        timeout=60,
    )
    _write_json(
        evidence_dir / f"postgres-stop-{heading}.json",
        {
            "returncode": pg_stop.returncode,
            "stdout": pg_stop.stdout,
            "stderr": pg_stop.stderr,
        },
    )
    _record_logs(container, evidence_dir / "server.log", heading)
    stopped = _run(
        ["docker", "stop", "--time", "20", container],
        check=False,
        timeout=60,
    )
    if stopped.returncode != 0:
        raise RunnerError(f"failed to stop container {container}: {stopped.stderr}")


def _run_phase(
    container: str,
    phase: str,
    repeat: int,
    evidence_dir: Path,
) -> int:
    completed = _run(
        [
            "docker",
            "exec",
            container,
            "python",
            "/opt/cotcodec/doctor.py",
            "--phase",
            phase,
            "--evidence-dir",
            "/evidence",
            "--repeat",
            str(repeat),
        ],
        check=False,
        timeout=600,
    )
    (evidence_dir / f"{phase}.stdout").write_text(
        completed.stdout, encoding="utf-8"
    )
    (evidence_dir / f"{phase}.stderr").write_text(
        completed.stderr, encoding="utf-8"
    )
    if completed.returncode not in (0, 3):
        raise RunnerError(
            f"phase {phase} crashed with {completed.returncode}: {completed.stderr}"
        )
    return completed.returncode


def _run_repeat(root: Path, repeat: int) -> dict[str, Any]:
    evidence_dir = root / f"repeat-{repeat}"
    state_dir = evidence_dir / "postgres"
    evidence_dir.mkdir(parents=True)
    state_dir.mkdir()
    container = f"cotcodec-letta-{os.getpid()}-{repeat}"
    absolute_doctor = DOCTOR.resolve()
    try:
        _run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                container,
                "--network",
                "none",
                "--env",
                "LETTA_ENVIRONMENT=DEV",
                "--env",
                "LETTA_LOGGING_LEVEL=WARNING",
                "--volume",
                f"{state_dir.resolve()}:/var/lib/postgresql/data",
                "--volume",
                f"{evidence_dir.resolve()}:/evidence",
                "--volume",
                f"{absolute_doctor}:/opt/cotcodec/doctor.py:ro",
                IMAGE,
            ],
            timeout=300,
        )
        _wait_for_server(container)
        initial_returncode = _run_phase(container, "initial", repeat, evidence_dir)
        _stop_container(container, evidence_dir, "after-initial")

        _run(["docker", "start", container], timeout=60)
        _wait_for_server(container)
        restart_returncode = _run_phase(
            container, "restart-cleanup", repeat, evidence_dir
        )
        _stop_container(container, evidence_dir, "after-cleanup")

        scan = _run(
            [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--entrypoint",
                "python",
                "--volume",
                f"{state_dir.resolve()}:/scan:ro",
                "--volume",
                f"{evidence_dir.resolve()}:/evidence",
                "--volume",
                f"{absolute_doctor}:/opt/cotcodec/doctor.py:ro",
                IMAGE,
                "/opt/cotcodec/doctor.py",
                "--phase",
                "scan",
                "--evidence-dir",
                "/evidence",
                "--repeat",
                str(repeat),
                "--scan-root",
                "/scan",
            ],
            check=False,
            timeout=600,
        )
        (evidence_dir / "scan.stdout").write_text(scan.stdout, encoding="utf-8")
        (evidence_dir / "scan.stderr").write_text(scan.stderr, encoding="utf-8")
        if scan.returncode not in (0, 3):
            raise RunnerError(f"scan phase crashed with {scan.returncode}: {scan.stderr}")
    finally:
        _run(["docker", "rm", "-f", container], check=False, timeout=60)

    initial = json.loads(
        (evidence_dir / "phase-initial.json").read_text(encoding="utf-8")
    )
    restart = json.loads(
        (evidence_dir / "phase-restart-cleanup.json").read_text(encoding="utf-8")
    )
    scan_payload = json.loads(
        (evidence_dir / "phase-scan.json").read_text(encoding="utf-8")
    )
    projection = {
        **initial["checks"],
        **restart["checks"],
        **scan_payload["checks"],
    }
    return {
        "repeat": repeat,
        "phase_returncodes": {
            "initial": initial_returncode,
            "restart_cleanup": restart_returncode,
            "scan": scan.returncode,
        },
        "projection": projection,
        "http_call_count": initial["http_call_count"]
        + restart["http_call_count"],
        "stopped_state_bytes": scan_payload["stopped_state_bytes"],
        "plaintext_hits": scan_payload["plaintext_hits"],
    }


def _decision_checks(
    repeats: list[dict[str, Any]], image_receipt: dict[str, Any]
) -> dict[str, bool]:
    key_map = {
        "provider_free_agent_creation_passes": "provider_free_agent_creation_passes",
        "core_block_mutation_passes": "core_block_mutation_passes",
        "inactive_archive_write_and_read_passes": (
            "inactive_archive_write_and_read_passes"
        ),
        "cross_organization_isolation_passes": "cross_organization_isolation_passes",
        "normal_state_survives_fresh_process": "normal_state_survives_fresh_process",
        "failed_core_update_returns_server_error_after_block_mutation": (
            "failed_core_update_returns_server_error_after_block_mutation"
        ),
        "failed_core_update_mutation_survives_fresh_process": (
            "failed_core_update_mutation_survives_fresh_process"
        ),
        "identical_archive_retry_creates_duplicate_rows": (
            "identical_archive_retry_creates_duplicate_rows"
        ),
        "duplicate_archive_rows_survive_fresh_process": (
            "duplicate_archive_rows_survive_fresh_process"
        ),
        "deleting_agent_retains_owner_archive_and_core_blocks": (
            "deleting_agent_retains_owner_archive_and_core_blocks"
        ),
        "explicit_archive_and_block_delete_is_logically_effective": (
            "explicit_archive_and_block_delete_is_logically_effective"
        ),
        "stopped_postgres_plaintext_residue_present": (
            "stopped_postgres_plaintext_residue_present"
        ),
    }
    checks = {"official_image_matches_exact_source": bool(image_receipt)}
    for output_key, projection_key in key_map.items():
        checks[output_key] = all(
            repeat["projection"].get(projection_key) is True for repeat in repeats
        )
    checks["reproduced_in_two_clean_states"] = (
        len(repeats) == 2 and repeats[0]["projection"] == repeats[1]["projection"]
    )
    return checks


def _manifest(root: Path) -> dict[str, dict[str, Any]]:
    files = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            files[str(path.relative_to(root))] = {
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
            }
    return files


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--source-archive", type=Path, required=True)
    parser.add_argument("--context-root", type=Path, required=True)
    parser.add_argument("--context-archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    contract = validate_experiment_contract()
    if args.output.exists():
        raise RunnerError("output directory already exists")
    args.output.mkdir(parents=True)

    source_receipt = _validate_source(args.source_root, args.source_archive, contract)
    context_receipt = _validate_context_source(
        args.context_root, args.context_archive, contract
    )
    image_receipt = _pull_and_validate_image(contract)
    _write_json(args.output / "source-receipt.json", source_receipt)
    _write_json(args.output / "current-runtime-context-receipt.json", context_receipt)
    _write_json(args.output / "image-receipt.json", image_receipt)
    shutil.copy2(args.source_archive, args.output / "source.tar")
    shutil.copy2(args.context_archive, args.output / "letta-code-source.tar")
    shutil.copy2(DEFAULT_EXPERIMENT, args.output / "experiment.yaml")
    shutil.copy2(DOCTOR, args.output / "doctor.py")
    shutil.copy2(RUNNER, args.output / "runner.py")
    shutil.copy2(VALIDATOR, args.output / "validator.py")

    repeats = [_run_repeat(args.output, repeat) for repeat in (1, 2)]
    checks = _decision_checks(repeats, image_receipt)
    expected_checks = {
        key: value
        for key, value in contract["expected_falsification"].items()
        if key != "status"
    }
    unexpected_checks = sorted(
        key for key, expected in expected_checks.items() if checks.get(key) != expected
    )
    status = EXPECTED_STATUS if not unexpected_checks else "UNEXPECTED_STATUS"
    stable_projection = [repeat["projection"] for repeat in repeats]
    stable_projection_sha256 = hashlib.sha256(
        json.dumps(stable_projection, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    report = {
        "schema_version": 1,
        "status": status,
        "scientific_result": False,
        "publication_ready": False,
        "h100_admission": False,
        "source": source_receipt,
        "current_runtime_context": context_receipt,
        "image": image_receipt,
        "checks": checks,
        "expected_checks": expected_checks,
        "unexpected_checks": unexpected_checks,
        "repeats": repeats,
        "stable_projection_sha256": stable_projection_sha256,
        "runtime": {
            "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
            "slurm_cpus_per_task": os.environ.get("SLURM_CPUS_PER_TASK"),
            "slurm_mem_per_node": os.environ.get("SLURM_MEM_PER_NODE"),
            "gpu_count": 0,
            "container_network": "none",
            "external_model_calls": 0,
            "provider_calls": 0,
        },
        "code_sha256": {
            "experiment": _sha256(DEFAULT_EXPERIMENT),
            "doctor": _sha256(DOCTOR),
            "runner": _sha256(RUNNER),
            "validator": _sha256(VALIDATOR),
        },
        "claim_boundary": contract["claim_boundary"],
    }
    _write_json(args.output / "report.json", report)
    _write_json(args.output / "manifest.json", {"files": _manifest(args.output)})
    print(status)
    print(f"stable_projection_sha256={stable_projection_sha256}")
    return 0 if not unexpected_checks else 3


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RunnerError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"MemGPT/Letta lifecycle runner failed: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
