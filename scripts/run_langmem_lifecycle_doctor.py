#!/usr/bin/env python3
"""Run the exact-source LangMem/PostgreSQL lifecycle falsifier twice."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.prepare_memory_baseline_context import prepare_context  # noqa: E402

EXPERIMENT = PROJECT_ROOT / "experiments/memory/stage3-langmem-native-lifecycle-doctor.yaml"
DOCKERFILE = PROJECT_ROOT / "infra/memory-baselines/langmem/Dockerfile.lifecycle-doctor"
DOCTOR = PROJECT_ROOT / "infra/memory-baselines/langmem/lifecycle_doctor.py"
SOURCE_ROOT = PROJECT_ROOT / "raw/baselines/langmem"
DEFAULT_OUTPUT = PROJECT_ROOT / "data/results/langmem-native-lifecycle/2026-08-17-local-docker-v1"
DEFAULT_IMAGE = "cotcodec-langmem-lifecycle:29cbe41-arm64-v1"
STATUS = "BLOCKED_NO_FIRST_CLASS_SCOPED_PURGE_AND_POSTGRES_PLAINTEXT_RESIDUE"
MARKER = b"COTCODEC_LANGMEM_PHASE="


class LangMemDoctorError(RuntimeError):
    """Raised when provenance, containment, or lifecycle evidence drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_path(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise LangMemDoctorError(f"expected regular file: {path}")
    return _sha(path.read_bytes())


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
                raise LangMemDoctorError(f"short write: {path}")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _run(
    argv: list[str], *, timeout: int = 900, check: bool = True
) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        argv, capture_output=True, check=False, timeout=timeout, cwd=PROJECT_ROOT
    )
    if check and completed.returncode != 0:
        raise LangMemDoctorError(
            f"command failed ({completed.returncode}): {argv!r}\n"
            f"stdout={completed.stdout.decode(errors='replace')[-8000:]}\n"
            f"stderr={completed.stderr.decode(errors='replace')[-8000:]}"
        )
    return completed


def _strict_object(data: bytes, owner: str) -> dict[str, Any]:
    def reject(value: str) -> None:
        raise LangMemDoctorError(f"{owner}: non-finite JSON {value}")

    try:
        payload = json.loads(data, parse_constant=reject)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LangMemDoctorError(f"{owner}: invalid JSON") from exc
    if not isinstance(payload, dict):
        raise LangMemDoctorError(f"{owner}: expected object")
    return payload


def _source_contract() -> dict[str, Any]:
    head = _run(["git", "-C", str(SOURCE_ROOT), "rev-parse", "HEAD"]).stdout.decode().strip()
    tree = _run(["git", "-C", str(SOURCE_ROOT), "rev-parse", "HEAD^{tree}"]).stdout.decode().strip()
    state = _run(
        [
            "git",
            "-C",
            str(SOURCE_ROOT),
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ]
    ).stdout
    archive = _run(["git", "-C", str(SOURCE_ROOT), "archive", "--format=tar", "HEAD"]).stdout
    expected = {
        "revision": "29cbe41e58528f92e9efa773c12e15c47be3808c",
        "tree": "d85d1f815fb2b54bbc0a85c18453b7a7953ca38c",
        "archive_sha256": "24c85c514c80bb263a16626971e8ef53978fd1bc7f9319e47d8a5a0bf4956521",
        "license_sha256": "98af1351ea856e008c835bc89a312905960a318072f950732bf346c741027c7d",
    }
    observed = {
        "revision": head,
        "tree": tree,
        "archive_sha256": _sha(archive),
        "license_sha256": _sha_path(SOURCE_ROOT / "LICENSE"),
    }
    if state or observed != expected:
        raise LangMemDoctorError(f"LangMem source checkout drifted: {observed}")
    tools = (SOURCE_ROOT / "src/langmem/knowledge/tools.py").read_text()
    manager = (SOURCE_ROOT / "src/langmem/knowledge/extraction.py").read_text()
    source_checks = {
        "public_manage_tool_has_record_delete_only": (
            "await store.adelete(namespace, key=str(id))" in tools
            and "store.delete(namespace, key=str(id))" in tools
        ),
        "background_manager_applies_record_puts_and_deletes": (
            "*(store.aput(**put) for put in final_puts)" in manager
            and "*(store.adelete(ns, key)" in manager
        ),
    }
    if not all(source_checks.values()):
        raise LangMemDoctorError("LangMem source lifecycle checks drifted")
    return {**observed, "archive_bytes": len(archive), "source_checks": source_checks}


def _build_image(image: str, source_context: Path) -> dict[str, Any]:
    doctor_sha = _sha_path(DOCTOR)
    experiment_sha = _sha_path(EXPERIMENT)
    build_context = source_context.parent / "build-context"
    build_context.mkdir()
    shutil.copytree(source_context, build_context / "langmem-source")
    shutil.copy2(PROJECT_ROOT / "pyproject.toml", build_context / "pyproject.toml")
    shutil.copy2(PROJECT_ROOT / "uv.lock", build_context / "uv.lock")
    shutil.copy2(DOCKERFILE, build_context / "Dockerfile")
    doctor_target = build_context / "infra/memory-baselines/langmem"
    doctor_target.mkdir(parents=True)
    shutil.copy2(DOCTOR, doctor_target / "lifecycle_doctor.py")
    experiment_target = build_context / "experiments/memory"
    experiment_target.mkdir(parents=True)
    shutil.copy2(EXPERIMENT, experiment_target / EXPERIMENT.name)
    _run(
        [
            "docker",
            "build",
            "--pull=false",
            "--platform",
            "linux/arm64",
            "--build-arg",
            "COTCODEC_IMAGE=ghcr.io/astral-sh/uv:python3.13-trixie-slim@sha256:d1e005e6f5aac724b7554db95f1c128a77d8d35b59ebe70e188852b4bdad3a3d",
            "--build-arg",
            f"COTCODEC_DOCTOR_SHA256={doctor_sha}",
            "--build-arg",
            f"COTCODEC_EXPERIMENT_SHA256={experiment_sha}",
            "--file",
            str(build_context / "Dockerfile"),
            "--tag",
            image,
            str(build_context),
        ],
        timeout=1800,
    )
    raw = _run(["docker", "image", "inspect", image]).stdout
    rows = json.loads(raw)
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise LangMemDoctorError("LangMem image inspection drifted")
    row = rows[0]
    config = row.get("Config") or {}
    labels = config.get("Labels") or {}
    expected_labels = {
        "org.opencontainers.image.revision": "29cbe41e58528f92e9efa773c12e15c47be3808c",
        "org.cotcodec.source-tree": "d85d1f815fb2b54bbc0a85c18453b7a7953ca38c",
        "org.cotcodec.source-archive-sha256": (
            "24c85c514c80bb263a16626971e8ef53978fd1bc7f9319e47d8a5a0bf4956521"
        ),
        "org.cotcodec.lifecycle-doctor-sha256": doctor_sha,
        "org.cotcodec.lifecycle-experiment-sha256": experiment_sha,
        "org.cotcodec.discovery-only": "true",
    }
    if (
        row.get("Architecture") != "arm64"
        or row.get("Os") != "linux"
        or config.get("User") != "65532:65532"
        or any(labels.get(key) != value for key, value in expected_labels.items())
    ):
        raise LangMemDoctorError("LangMem image provenance or confinement drifted")
    return {
        "image_id": row["Id"],
        "architecture": "arm64",
        "os": "linux",
        "user": "65532:65532",
        "inspect_sha256": _sha(raw),
        "labels": expected_labels,
        "raw": raw,
    }


def _start_database(name: str, network: str, state_root: Path) -> list[str]:
    state_root.mkdir(mode=0o777, exist_ok=True)
    state_root.chmod(0o777)
    argv = [
        "docker",
        "run",
        "--detach",
        "--pull=never",
        "--name",
        name,
        "--network",
        network,
        "--network-alias",
        "postgres",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        "512",
        "--memory",
        "2g",
        "--cpus",
        "2",
        "--user",
        "70:70",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=128m,uid=70,gid=70",
        "--tmpfs",
        "/var/run/postgresql:rw,noexec,nosuid,nodev,size=16m,uid=70,gid=70",
        "--mount",
        f"type=bind,src={state_root},dst=/var/lib/postgresql/data",
        "-e",
        "POSTGRES_PASSWORD=langmem_lifecycle_local_only",
        "-e",
        "POSTGRES_DB=langmem_lifecycle",
        "-e",
        "PGDATA=/var/lib/postgresql/data/pgdata",
        "sha256:ef257d85f76e48da1c64832459b59fcaba1a4dac97bf5d7450c77753542eee94",
    ]
    _run(argv)
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        ready = _run(
            ["docker", "exec", name, "pg_isready", "-U", "postgres", "-d", "langmem_lifecycle"],
            timeout=15,
            check=False,
        )
        if ready.returncode == 0:
            return argv
        state = _run(["docker", "inspect", "--format={{.State.Running}}", name], check=False)
        if state.returncode != 0 or state.stdout.strip() != b"true":
            logs = _run(["docker", "logs", name], check=False)
            raise LangMemDoctorError(
                "PostgreSQL exited during startup: "
                + (logs.stdout + logs.stderr).decode(errors="replace")[-8000:]
            )
        time.sleep(1)
    raise LangMemDoctorError("PostgreSQL readiness timed out")


def _stop_database(name: str) -> None:
    _run(["docker", "stop", "--timeout", "30", name], timeout=60)
    _run(["docker", "rm", name], timeout=60)


def _phase(
    *, image_id: str, network: str, phase: str, values: dict[str, str]
) -> tuple[dict[str, Any], bytes, list[str]]:
    argv = [
        "docker",
        "run",
        "--rm",
        "--pull=never",
        "--platform",
        "linux/arm64",
        "--network",
        network,
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
        "-e",
        f"COTCODEC_PHASE={phase}",
        "-e",
        "COTCODEC_DATABASE_URL=postgresql://postgres:langmem_lifecycle_local_only@postgres:5432/langmem_lifecycle?sslmode=disable",
    ]
    for key, value in sorted(values.items()):
        argv.extend(["-e", f"{key}={value}"])
    argv.append(image_id)
    completed = _run(argv, timeout=180)
    combined = completed.stdout + completed.stderr
    rows = [line.split(MARKER, 1)[1] for line in combined.splitlines() if MARKER in line]
    if len(rows) != 1:
        raise LangMemDoctorError(f"phase {phase} emitted {len(rows)} result markers")
    payload = _strict_object(rows[0], f"phase {phase}")
    if payload.get("phase") != phase:
        raise LangMemDoctorError(f"phase identity drifted: {payload}")
    return payload, combined, argv


def _proofs(root: Path, needles: dict[str, bytes]) -> dict[str, list[dict[str, Any]]]:
    proofs: dict[str, list[dict[str, Any]]] = {}
    total_bytes = 0
    file_count = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        file_count += 1
        if file_count > 20_000:
            raise LangMemDoctorError("PostgreSQL residue scan file ceiling exceeded")
        data = path.read_bytes()
        total_bytes += len(data)
        if total_bytes > 512 * 1024 * 1024:
            raise LangMemDoctorError("PostgreSQL residue scan byte ceiling exceeded")
        hits: list[dict[str, Any]] = []
        for label, needle in needles.items():
            offset = data.find(needle)
            if offset < 0:
                continue
            start = max(0, offset - 64)
            end = min(len(data), offset + len(needle) + 64)
            window = data[start:end]
            hits.append(
                {
                    "canary": label,
                    "needle_sha256": _sha(needle),
                    "offset": offset,
                    "window_start": start,
                    "window_base64": base64.b64encode(window).decode(),
                    "window_sha256": _sha(window),
                }
            )
        if hits:
            proofs[path.relative_to(root).as_posix()] = hits
    return proofs


def _redacted(argv: list[str]) -> list[str]:
    return [
        "COTCODEC_DATABASE_URL=<redacted>" if value.startswith("COTCODEC_DATABASE_URL=") else value
        for value in argv
    ]


def _run_repeat(repeat: int, image_id: str) -> tuple[dict[str, Any], dict[str, bytes]]:
    suffix = secrets.token_hex(5)
    network = f"cotcodec-langmem-net-{suffix}"
    database = f"cotcodec-langmem-db-{suffix}"
    canaries = {
        "original": f"LANGMEM_ORIGINAL_{secrets.token_hex(16)}",
        "updated": f"LANGMEM_UPDATED_{secrets.token_hex(16)}",
        "isolated": f"LANGMEM_ISOLATED_{secrets.token_hex(16)}",
        "background": f"LANGMEM_BACKGROUND_{secrets.token_hex(16)}",
    }
    artifacts: dict[str, bytes] = {}
    _run(["docker", "network", "create", "--internal", network])
    scratch_parent = PROJECT_ROOT / "data/tmp/langmem-lifecycle"
    scratch_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="cotcodec-langmem-pg-", dir=scratch_parent
    ) as temporary:
        state_root = Path(temporary) / "state"
        database_running = False
        try:
            first_db_argv = _start_database(database, network, state_root)
            database_running = True
            common = {
                "COTCODEC_ORIGINAL_CANARY": canaries["original"],
                "COTCODEC_UPDATED_CANARY": canaries["updated"],
                "COTCODEC_ISOLATED_CANARY": canaries["isolated"],
                "COTCODEC_BACKGROUND_CANARY": canaries["background"],
            }
            prepare, raw, prepare_argv = _phase(
                image_id=image_id, network=network, phase="prepare", values=common
            )
            artifacts[f"repeat-{repeat}-prepare.txt"] = raw
            _stop_database(database)
            database_running = False

            second_db_argv = _start_database(database, network, state_root)
            database_running = True
            restart_values = {
                **common,
                "COTCODEC_MEMORY_A": prepare["memory_a"],
                "COTCODEC_MEMORY_B": prepare["memory_b"],
            }
            restart, raw, restart_argv = _phase(
                image_id=image_id, network=network, phase="restart", values=restart_values
            )
            artifacts[f"repeat-{repeat}-restart.txt"] = raw
            purge, raw, purge_argv = _phase(
                image_id=image_id, network=network, phase="purge", values=common
            )
            artifacts[f"repeat-{repeat}-purge.txt"] = raw
            _stop_database(database)
            database_running = False
            proofs = _proofs(
                state_root,
                {key: value.encode() for key, value in canaries.items()},
            )
            paths = set(proofs)
            residue = {
                "plaintext_residue_after_logical_purge_and_clean_shutdown": bool(proofs),
                "plaintext_residue_in_postgresql_heap": any(
                    path.startswith("pgdata/base/") for path in paths
                ),
                "plaintext_residue_in_postgresql_wal": any(
                    path.startswith("pgdata/pg_wal/") for path in paths
                ),
                "all_four_canaries_have_bounded_proof_windows": (
                    {hit["canary"] for hits in proofs.values() for hit in hits} == set(canaries)
                ),
            }
            if not all(residue.values()):
                raise LangMemDoctorError(f"expected residue proof drifted: {residue}")
            projection = {
                "prepare": {
                    key: value for key, value in prepare.items() if not key.startswith("memory_")
                },
                "restart": restart,
                "purge": purge,
                "residue": residue,
            }
            report = {
                "repeat": repeat,
                "projection": projection,
                "projection_sha256": _sha(
                    json.dumps(projection, separators=(",", ":"), sort_keys=True).encode()
                ),
                "proofs": proofs,
                "security": {
                    "network_internal": True,
                    "app_read_only_nonroot_cap_drop_all": True,
                    "database_read_only_rootfs_uid_70_cap_drop_all": True,
                    "database_first_start_argv": first_db_argv,
                    "database_second_start_argv": second_db_argv,
                    "prepare_argv": _redacted(prepare_argv),
                    "restart_argv": _redacted(restart_argv),
                    "purge_argv": _redacted(purge_argv),
                },
            }
            return report, artifacts
        finally:
            if database_running:
                subprocess.run(["docker", "rm", "-f", database], capture_output=True, check=False)
            subprocess.run(["docker", "network", "rm", network], capture_output=True, check=False)


def run(*, output: Path, image: str) -> dict[str, Any]:
    if output.exists():
        raise LangMemDoctorError(f"output already exists: {output}")
    source = _source_contract()
    with tempfile.TemporaryDirectory(prefix="cotcodec-langmem-source-") as temporary:
        source_context = Path(temporary) / "langmem"
        context_receipt = prepare_context("langmem", source_context)
        image_receipt = _build_image(image, source_context)
    image_raw = image_receipt.pop("raw")
    output.mkdir(parents=True)
    fixed = {
        "experiment.yaml": EXPERIMENT.read_bytes(),
        "Dockerfile.lifecycle-doctor": DOCKERFILE.read_bytes(),
        "lifecycle_doctor.py": DOCTOR.read_bytes(),
        "source-receipt.json": _json_bytes({**source, "context_receipt": context_receipt}),
        "image-inspect.json": image_raw,
    }
    for name, data in fixed.items():
        _write_once(output / name, data)
    repeats: list[dict[str, Any]] = []
    for repeat in (1, 2):
        report, artifacts = _run_repeat(repeat, image_receipt["image_id"])
        _write_once(output / f"repeat-{repeat}.json", _json_bytes(report))
        for name, data in artifacts.items():
            _write_once(output / name, data)
        repeats.append(report)
    if repeats[0]["projection"] != repeats[1]["projection"]:
        raise LangMemDoctorError("LangMem clean-state lifecycle projections diverged")
    findings = {
        "exact_source_background_manager_transport_executed": True,
        "hot_path_public_tool_crud_passed": True,
        "database_and_fresh_process_restart_passed": True,
        "user_namespace_isolation_passed": True,
        "logical_record_delete_passed": True,
        "first_class_namespace_purge_absent": True,
        "enumerate_then_delete_logical_fallback_passed": True,
        "purged_plaintext_remains_in_postgresql_heap": True,
        "purged_plaintext_remains_in_postgresql_wal": True,
    }
    summary = {
        "schema_version": 1,
        "status": STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "h100_actor_admission": "forbidden-for-this-revision",
        "run_count": 2,
        "fresh_database_restart_count_per_run": 1,
        "source": source,
        "image": image_receipt,
        "stable_projection_sha256": repeats[0]["projection_sha256"],
        "findings": findings,
        "claim_boundary": (
            "Exact pinned LangMem public tool, deterministic background-manager transport, "
            "official PostgresStore lifecycle, logical deletion, namespace-purge surface, "
            "and physical plaintext residue; not extraction quality, semantic retrieval, "
            "procedural prompt quality, model effect, managed LangGraph service behavior, "
            "H100 actor quality, or publication evidence."
        ),
    }
    _write_once(output / "report.json", _json_bytes(summary))
    files = {
        path.name: _sha_path(path)
        for path in sorted(output.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    _write_once(
        output / "manifest.json",
        _json_bytes({"schema_version": 1, "status": STATUS, "files": files}),
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    args = parser.parse_args()
    print(json.dumps(run(output=args.output, image=args.image), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
