#!/usr/bin/env python3
"""Reproduce and seal the exact MemForge fresh-install blockers."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validate_memforge_fresh_install_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    EXPECTED_STATUS,
    validate_experiment_contract,
)

DEFAULT_SOURCE = (
    PROJECT_ROOT
    / "data/cache/memforge/16e2f15c5881a38911f64ca81b3dc0b25d6207ec"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data/results/memforge-fresh-install/2026-08-16-local-docker-v1"
)
LANES = {
    "official-compose-postgres": {
        "uid": 70,
        "failure_markers": (
            'extension "vector" is not available',
            "/usr/local/share/postgresql/extension/vector.control",
            "schema.sql:14",
        ),
    },
    "pgvector-enabled-control": {
        "uid": 999,
        "failure_markers": (
            'relation "warm_tier" does not exist',
            "schema.sql:57",
        ),
    },
}


class MemForgeRunnerError(RuntimeError):
    """Raised when the registered source, runtime, or failure drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_path(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise MemForgeRunnerError(f"expected regular file: {path}")
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
                raise MemForgeRunnerError(f"short write: {path}")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _run(
    argv: list[str], *, timeout: int = 300, check: bool = True
) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        argv,
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    if check and completed.returncode != 0:
        raise MemForgeRunnerError(
            f"command failed ({completed.returncode}): {argv!r}\n"
            f"stdout={completed.stdout.decode(errors='replace')[-4000:]}\n"
            f"stderr={completed.stderr.decode(errors='replace')[-4000:]}"
        )
    return completed


def _source_contract(source_root: Path, experiment: dict[str, Any]) -> dict[str, Any]:
    source = experiment["source"]
    if source_root.is_symlink() or not source_root.is_dir():
        raise MemForgeRunnerError("source root is invalid")
    head = _run(["git", "-C", str(source_root), "rev-parse", "HEAD"]).stdout.decode().strip()
    tree = _run(
        ["git", "-C", str(source_root), "rev-parse", "HEAD^{tree}"]
    ).stdout.decode().strip()
    status = _run(
        [
            "git",
            "-C",
            str(source_root),
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ]
    ).stdout
    if head != source["revision"] or tree != source["tree"] or status:
        raise MemForgeRunnerError("source checkout drifted")
    archive = _run(
        ["git", "-C", str(source_root), "archive", "--format=tar", head]
    ).stdout
    schema = source_root / "schema/schema.sql"
    if (
        _sha(archive) != source["git_archive_tar_sha256"]
        or _sha_path(source_root / "LICENSE") != source["license_sha256"]
        or _sha_path(source_root / "package-lock.json")
        != source["dependency_lock_sha256"]
        or _sha_path(schema) != source["canonical_schema_sha256"]
    ):
        raise MemForgeRunnerError("source bytes drifted")
    return {
        "git_sha": head,
        "git_tree": tree,
        "archive": archive,
        "archive_sha256": _sha(archive),
        "archive_bytes": len(archive),
        "license_sha256": source["license_sha256"],
        "package_lock_sha256": source["dependency_lock_sha256"],
        "canonical_schema_sha256": source["canonical_schema_sha256"],
    }


def _inspect_image(image: str) -> tuple[dict[str, Any], bytes]:
    raw = _run(["docker", "image", "inspect", image]).stdout
    try:
        rows = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise MemForgeRunnerError("image inspect is not JSON") from exc
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise MemForgeRunnerError("image inspect roster drifted")
    row = rows[0]
    if (
        row.get("Id") != image.removeprefix(image.split("@")[0] + "@")
        or row.get("Architecture") != "arm64"
        or row.get("Os") != "linux"
        or image not in (row.get("RepoDigests") or [])
        or (row.get("Config") or {}).get("Entrypoint") != ["docker-entrypoint.sh"]
        or (row.get("Config") or {}).get("Cmd") != ["postgres"]
    ):
        raise MemForgeRunnerError(f"image runtime drifted: {image}")
    return row, raw


def _container_argv(
    *, image: str, schema: Path, name: str, uid: int
) -> list[str]:
    tmpfs_data = (
        "/var/lib/postgresql/data:rw,noexec,nosuid,nodev,size=512m,"
        f"uid={uid},gid={uid},mode=0700"
    )
    tmpfs_run = (
        "/var/run/postgresql:rw,noexec,nosuid,nodev,size=16m,"
        f"uid={uid},gid={uid},mode=0700"
    )
    return [
        "docker",
        "run",
        "-d",
        "--name",
        name,
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
        "1g",
        "--cpus",
        "1",
        "--user",
        f"{uid}:{uid}",
        "--tmpfs",
        tmpfs_data,
        "--tmpfs",
        tmpfs_run,
        "--mount",
        f"type=bind,src={schema},dst=/docker-entrypoint-initdb.d/schema.sql,readonly",
        "--env",
        "POSTGRES_PASSWORD=memforge-doctor",
        "--env",
        "POSTGRES_USER=memforge",
        "--env",
        "POSTGRES_DB=memforge",
        image,
    ]


def _canonical_argv(argv: list[str]) -> list[str]:
    result = list(argv)
    result[result.index("--name") + 1] = "<container>"
    mount_index = result.index("--mount") + 1
    result[mount_index] = (
        "type=bind,src=<canonical-schema>,"
        "dst=/docker-entrypoint-initdb.d/schema.sql,readonly"
    )
    return result


def _classify_lane(
    *, lane: str, exit_code: int, logs: bytes
) -> dict[str, bool]:
    if lane not in LANES:
        raise MemForgeRunnerError(f"unknown lane: {lane}")
    decoded = logs.decode(errors="replace")
    markers = LANES[lane]["failure_markers"]
    checks = {
        "registered_nonzero_exit": exit_code == 3,
        "all_failure_markers_present": all(marker in decoded for marker in markers),
        "fresh_install_never_completed": (
            "PostgreSQL init process complete; ready for start up." not in decoded
        ),
    }
    if not all(checks.values()):
        raise MemForgeRunnerError(f"{lane} failure semantics drifted: {checks}")
    return checks


def _run_lane(
    *, lane: str, repeat: int, image: str, schema: Path, output: Path
) -> dict[str, Any]:
    name = f"cotcodec-memforge-{os.getpid()}-{repeat}-{lane}"
    uid = int(LANES[lane]["uid"])
    argv = _container_argv(image=image, schema=schema, name=name, uid=uid)
    _run(["docker", "rm", "-f", name], timeout=60, check=False)
    try:
        _run(argv)
        wait = _run(["docker", "wait", name], timeout=180)
        try:
            exit_code = int(wait.stdout.decode().strip())
        except ValueError as exc:
            raise MemForgeRunnerError(f"invalid docker wait output: {wait.stdout!r}") from exc
        log_result = _run(["docker", "logs", name], timeout=60, check=False)
        logs = log_result.stdout + log_result.stderr
        checks = _classify_lane(lane=lane, exit_code=exit_code, logs=logs)
        _write_once(output / f"repeat-{repeat}-{lane}.log", logs)
        report = {
            "schema_version": 1,
            "source_revision": "16e2f15c5881a38911f64ca81b3dc0b25d6207ec",
            "repeat": repeat,
            "lane": lane,
            "status": EXPECTED_STATUS,
            "exit_code": exit_code,
            "runtime_argv": _canonical_argv(argv),
            "logs_sha256": _sha(logs),
            "checks": checks,
            "scientific_result": False,
            "publication_ready": False,
            "h100_actor_admission": False,
        }
        _write_once(output / f"repeat-{repeat}-{lane}.json", _json_bytes(report))
        return report
    finally:
        _run(["docker", "rm", "-f", name], timeout=60, check=False)


def run(*, source_root: Path, output: Path) -> dict[str, Any]:
    experiment = validate_experiment_contract()
    output.mkdir(parents=True, exist_ok=False)
    source = _source_contract(source_root.resolve(), experiment)
    schema = source_root.resolve() / "schema/schema.sql"
    runtime = experiment["runtime"]
    images = {
        "official-compose-postgres": runtime["official_compose_postgres_image"],
        "pgvector-enabled-control": runtime["pgvector_control_image"],
    }
    image_contracts: dict[str, dict[str, Any]] = {}
    for lane, image in images.items():
        row, raw = _inspect_image(image)
        image_contracts[lane] = {
            "image_ref": image,
            "image_id": row["Id"],
            "architecture": row["Architecture"],
            "os": row["Os"],
            "inspect_sha256": _sha(raw),
        }
        _write_once(output / f"image-inspect-{lane}.json", raw)

    _write_once(output / "experiment.yaml", DEFAULT_EXPERIMENT.read_bytes())
    _write_once(output / "schema.sql", schema.read_bytes())
    _write_once(output / "source.tar", source.pop("archive"))
    _write_once(output / "source-receipt.json", _json_bytes(source))

    lane_reports = []
    for repeat in range(1, runtime["clean_state_repeats"] + 1):
        for lane, image in images.items():
            lane_reports.append(
                _run_lane(
                    lane=lane,
                    repeat=repeat,
                    image=image,
                    schema=schema,
                    output=output,
                )
            )

    report = {
        "schema_version": 1,
        "source_id": "memforge",
        "source_revision": experiment["source"]["revision"],
        "source_tree": experiment["source"]["tree"],
        "status": EXPECTED_STATUS,
        "run_count": runtime["clean_state_repeats"],
        "lane_count": len(lane_reports),
        "images": image_contracts,
        "findings": {
            "official_compose_image_lacks_vector_extension": True,
            "canonical_schema_references_warm_tier_before_creation": True,
            "exact_revision_lifecycle_not_executable": True,
        },
        "claim_boundary": {
            "hot_warm_cold_lifecycle_evaluated": False,
            "graph_quality_evaluated": False,
            "memory_quality_evaluated": False,
            "repair_arm_evaluated": False,
        },
        "h100_actor_admission": "forbidden-for-this-revision",
        "scientific_result": False,
        "publication_ready": False,
    }
    _write_once(output / "report.json", _json_bytes(report))
    files = {
        path.name: _sha_path(path)
        for path in sorted(output.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    manifest = {
        "schema_version": 1,
        "status": EXPECTED_STATUS,
        "file_count": len(files),
        "files": files,
    }
    _write_once(output / "manifest.json", _json_bytes(manifest))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = run(source_root=args.source_root, output=args.output)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
