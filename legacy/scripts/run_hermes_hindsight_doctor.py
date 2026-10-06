#!/usr/bin/env python3
"""Run a contained native Hindsight lifecycle doctor through Hermes."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCTOR_ROOT = PROJECT_ROOT / "infra/memory-baselines/hermes-hindsight"
MODEL_STUB = PROJECT_ROOT / "infra/memory-baselines/hermes-openviking/model_stub.py"
DEFAULT_OUTPUT = PROJECT_ROOT / "data/results/hermes-hindsight/2026-08-14-lifecycle-doctor-v1"
PGVECTOR_REPO_DIGEST = (
    "pgvector/pgvector@sha256:78bf48b801e792f99e3ac62b5036fd3876e9be48afda16c1e331af1c75ceb2ff"
)


class DoctorError(RuntimeError):
    """Raised when containment or lifecycle behavior is invalid."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _run(
    argv: list[str], *, timeout: int = 1200, check: bool = True
) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(argv, capture_output=True, check=False, timeout=timeout)
    if check and result.returncode != 0:
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


def _inspect_image(reference: str) -> dict[str, Any]:
    raw = _run(["docker", "image", "inspect", reference]).stdout
    rows = json.loads(raw)
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise DoctorError(f"Docker inspect for {reference!r} did not return one image")
    row = rows[0]
    image_id = row.get("Id")
    if (
        not isinstance(image_id, str)
        or not image_id.startswith("sha256:")
        or row.get("Os") != "linux"
        or row.get("Architecture") != "arm64"
    ):
        raise DoctorError(f"image identity is invalid for {reference!r}")
    return {
        "reference": reference,
        "image_id": image_id,
        "inspect_sha256": _sha(raw),
        "repo_digests": row.get("RepoDigests") or [],
        "user": (row.get("Config") or {}).get("User") or "",
        "size": row.get("Size"),
    }


def _container_logs(name: str) -> str:
    result = _run(["docker", "logs", name], check=False)
    return (result.stdout + result.stderr).decode(errors="replace")


def _container_running(name: str) -> bool:
    result = _run(
        ["docker", "inspect", "--format", "{{.State.Running}}", name],
        check=False,
    )
    return result.returncode == 0 and result.stdout.strip() == b"true"


def _wait_postgres(name: str, *, timeout_seconds: float = 120.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    last = ""
    while time.monotonic() < deadline:
        result = _run(
            ["docker", "exec", name, "pg_isready", "-U", "hindsight", "-d", "hindsight"],
            timeout=10,
            check=False,
        )
        if result.returncode == 0:
            return
        last = (result.stdout + result.stderr).decode(errors="replace")
        if not _container_running(name):
            raise DoctorError(
                f"PostgreSQL exited before readiness: {last}\n{_container_logs(name)}"
            )
        time.sleep(0.5)
    raise DoctorError(f"PostgreSQL readiness timed out: {last}\n{_container_logs(name)}")


def _wait_hindsight(name: str, *, timeout_seconds: float = 180.0) -> None:
    probe = (
        "import httpx; "
        "r=httpx.get('http://127.0.0.1:8888/health',timeout=3); "
        "raise SystemExit(0 if r.status_code == 200 else 1)"
    )
    deadline = time.monotonic() + timeout_seconds
    last = ""
    while time.monotonic() < deadline:
        result = _run(
            [
                "docker",
                "exec",
                name,
                "/opt/hindsight-runtime/bin/python",
                "-c",
                probe,
            ],
            timeout=10,
            check=False,
        )
        if result.returncode == 0:
            return
        last = (result.stdout + result.stderr).decode(errors="replace")
        if not _container_running(name):
            raise DoctorError(f"Hindsight exited before health: {last}\n{_container_logs(name)}")
        time.sleep(0.5)
    raise DoctorError(f"Hindsight health timed out: {last}\n{_container_logs(name)}")


def _start_stub(*, name: str, network: str, image_id: str) -> None:
    _run(
        [
            "docker",
            "run",
            "-d",
            "--pull=never",
            "--name",
            name,
            "--network",
            network,
            "--network-alias",
            "hindsight-model-stub",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "64",
            "--cpus",
            "1",
            "--memory",
            "256m",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,nodev,size=16m,mode=0700,uid=65532,gid=65532",
            image_id,
        ]
    )


def _start_postgres(*, name: str, network: str, image_id: str, state_dir: Path) -> None:
    _run(
        [
            "docker",
            "run",
            "-d",
            "--pull=never",
            "--name",
            name,
            "--network",
            network,
            "--network-alias",
            "hindsight-postgres",
            "--user",
            "postgres",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "256",
            "--cpus",
            "2",
            "--memory",
            "2g",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,nodev,size=128m,mode=1777,uid=999,gid=999",
            "--tmpfs",
            "/var/run/postgresql:rw,noexec,nosuid,nodev,size=32m,mode=0755,uid=999,gid=999",
            "--mount",
            f"type=bind,src={state_dir},dst=/var/lib/postgresql/data",
            "-e",
            "PGDATA=/var/lib/postgresql/data/pgdata",
            "-e",
            "POSTGRES_USER=hindsight",
            "-e",
            "POSTGRES_PASSWORD=hindsight",
            "-e",
            "POSTGRES_DB=hindsight",
            "-e",
            "POSTGRES_INITDB_ARGS=--data-checksums",
            image_id,
        ],
        timeout=60,
    )
    _wait_postgres(name)


def _start_backend(*, name: str, network: str, image_id: str) -> None:
    _run(
        [
            "docker",
            "run",
            "-d",
            "--pull=never",
            "--name",
            name,
            "--network",
            network,
            "--network-alias",
            "hindsight",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "512",
            "--cpus",
            "2",
            "--memory",
            "4g",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,nodev,size=256m,mode=1777,uid=65532,gid=65532",
            "--tmpfs",
            "/state:rw,noexec,nosuid,nodev,size=128m,mode=0700,uid=65532,gid=65532",
            "-e",
            "HINDSIGHT_API_DATABASE_URL=postgresql://hindsight:hindsight@hindsight-postgres:5432/hindsight",
            "-e",
            "HINDSIGHT_API_WORKER_ID=cotcodec-hermes-hindsight-doctor",
            image_id,
        ],
        timeout=60,
    )
    _wait_hindsight(name)


def _adapter_action(
    *,
    image_id: str,
    network: str,
    user: str,
    session_id: str,
    action: str,
    canary: str,
    expect_present: bool = True,
) -> dict[str, Any]:
    argv = [
        "docker",
        "run",
        "--rm",
        "--pull=never",
        "--network",
        network,
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        "128",
        "--cpus",
        "1",
        "--memory",
        "1g",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777,uid=65532,gid=65532",
        "--tmpfs",
        "/state:rw,noexec,nosuid,nodev,size=64m,mode=0700,uid=65532,gid=65532",
        image_id,
        "--action",
        action,
        "--session-id",
        session_id,
        "--user",
        user,
        "--canary",
        canary,
    ]
    if action == "search" and not expect_present:
        argv.append("--no-expect-present")
    result = _run(argv, timeout=90, check=False)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise DoctorError(
            f"adapter emitted invalid JSON: stdout={result.stdout!r}; stderr={result.stderr!r}"
        ) from exc
    if result.returncode != 0 or payload.get("status") != "PASS":
        raise DoctorError(
            f"adapter action failed: {action}; payload={payload}; "
            f"stderr={result.stderr.decode(errors='replace')}"
        )
    return {
        "payload": payload,
        "stdout_sha256": _sha(result.stdout),
        "stderr": result.stderr.decode(errors="replace"),
    }


def _stop(name: str) -> None:
    _run(["docker", "stop", "--time", "20", name], timeout=40, check=False)


def _remove(name: str) -> None:
    _run(["docker", "rm", "--force", name], timeout=30, check=False)


def _state_manifest(state_dir: Path, canaries: list[str]) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    residues: dict[str, list[str]] = {canary: [] for canary in canaries}
    proofs: dict[str, list[dict[str, Any]]] = {canary: [] for canary in canaries}
    total = 0
    for path in sorted(state_dir.rglob("*")):
        if path.is_symlink():
            raise DoctorError(f"PostgreSQL state contains a symlink: {path}")
        if not path.is_file():
            continue
        relative = path.relative_to(state_dir).as_posix()
        data = path.read_bytes()
        total += len(data)
        if total > 2 * 1024 * 1024 * 1024:
            raise DoctorError("PostgreSQL state exceeds the 2 GiB doctor ceiling")
        for canary in canaries:
            encoded = canary.encode("utf-8")
            offset = data.find(encoded)
            if offset < 0:
                continue
            residues[canary].append(relative)
            start = max(0, offset - 16)
            end = min(len(data), offset + len(encoded) + 16)
            window = data[start:end]
            proofs[canary].append(
                {
                    "path": relative,
                    "offset": offset,
                    "window_start": start,
                    "window_base64": base64.b64encode(window).decode("ascii"),
                    "window_sha256": _sha(window),
                }
            )
        files.append({"path": relative, "bytes": len(data), "sha256": _sha(data)})
    return {
        "files": files,
        "file_count": len(files),
        "total_bytes": total,
        "manifest_sha256": _sha(_json_bytes(files)),
        "plaintext_residue": residues,
        "plaintext_residue_proofs": proofs,
    }


def run_doctor(
    *, backend_image: str, postgres_image: str, stub_image: str, adapter_image: str
) -> dict[str, Any]:
    images = {
        "hindsight_backend": _inspect_image(backend_image),
        "postgres_pgvector": _inspect_image(postgres_image),
        "model_stub": _inspect_image(stub_image),
        "hermes_adapter": _inspect_image(adapter_image),
    }
    token = secrets.token_hex(6)
    network = f"cotcodec-hindsight-{token}"
    stub_name = f"cotcodec-hindsight-stub-{token}"
    postgres_name = f"cotcodec-hindsight-postgres-{token}"
    backend_name = f"cotcodec-hindsight-backend-{token}"
    canary_a = f"cotcodec-hindsight-tenant-a-{token}"
    canary_b = f"cotcodec-hindsight-tenant-b-{token}"
    operations: list[dict[str, Any]] = []
    backend_logs: list[str] = []
    postgres_logs: list[str] = []

    runtime_tmp = PROJECT_ROOT / "data/results/.runtime-tmp"
    runtime_tmp.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cotcodec-hindsight-pg-", dir=runtime_tmp) as state_tmp:
        state_dir = Path(state_tmp)
        _run(["docker", "network", "create", "--internal", network])
        try:
            network_inspect = json.loads(_run(["docker", "network", "inspect", network]).stdout)
            if (
                not isinstance(network_inspect, list)
                or len(network_inspect) != 1
                or network_inspect[0].get("Internal") is not True
            ):
                raise DoctorError("Docker doctor network is not internal")
            _start_stub(
                name=stub_name,
                network=network,
                image_id=images["model_stub"]["image_id"],
            )
            _start_postgres(
                name=postgres_name,
                network=network,
                image_id=images["postgres_pgvector"]["image_id"],
                state_dir=state_dir,
            )
            _start_backend(
                name=backend_name,
                network=network,
                image_id=images["hindsight_backend"]["image_id"],
            )

            def record(name: str, **kwargs: Any) -> None:
                operations.append(
                    {
                        "name": name,
                        **_adapter_action(
                            image_id=images["hermes_adapter"]["image_id"],
                            network=network,
                            **kwargs,
                        ),
                    }
                )

            record(
                "tenant-a-tool-retain",
                user="tenant-a",
                session_id="tenant-a-tool-retain",
                action="write",
                canary=canary_a,
            )
            record(
                "tenant-a-prefetch",
                user="tenant-a",
                session_id="tenant-a-prefetch",
                action="prefetch",
                canary=canary_a,
            )
            record(
                "tenant-b-cannot-see-a",
                user="tenant-b",
                session_id="tenant-b-isolation",
                action="search",
                canary=canary_a,
                expect_present=False,
            )
            record(
                "tenant-b-sync-turn-retain",
                user="tenant-b",
                session_id="tenant-b-sync-turn",
                action="sync-turn",
                canary=canary_b,
            )
            record(
                "tenant-b-search-own",
                user="tenant-b",
                session_id="tenant-b-own",
                action="search",
                canary=canary_b,
            )
            record(
                "tenant-a-cannot-see-b",
                user="tenant-a",
                session_id="tenant-a-isolation",
                action="search",
                canary=canary_b,
                expect_present=False,
            )

            backend_logs.append(_container_logs(backend_name))
            postgres_logs.append(_container_logs(postgres_name))
            _stop(backend_name)
            _remove(backend_name)
            _stop(postgres_name)
            _remove(postgres_name)
            _start_postgres(
                name=postgres_name,
                network=network,
                image_id=images["postgres_pgvector"]["image_id"],
                state_dir=state_dir,
            )
            _start_backend(
                name=backend_name,
                network=network,
                image_id=images["hindsight_backend"]["image_id"],
            )
            record(
                "tenant-a-full-restart-search",
                user="tenant-a",
                session_id="tenant-a-restart",
                action="search",
                canary=canary_a,
            )
            record(
                "tenant-b-full-restart-search",
                user="tenant-b",
                session_id="tenant-b-restart",
                action="search",
                canary=canary_b,
            )
            record(
                "tenant-a-admin-delete",
                user="tenant-a",
                session_id="tenant-a-delete",
                action="admin-delete",
                canary=canary_a,
            )
            record(
                "tenant-b-admin-delete",
                user="tenant-b",
                session_id="tenant-b-delete",
                action="admin-delete",
                canary=canary_b,
            )

            backend_logs.append(_container_logs(backend_name))
            postgres_logs.append(_container_logs(postgres_name))
            _stop(backend_name)
            _remove(backend_name)
            _stop(postgres_name)
            _remove(postgres_name)
            _start_postgres(
                name=postgres_name,
                network=network,
                image_id=images["postgres_pgvector"]["image_id"],
                state_dir=state_dir,
            )
            _start_backend(
                name=backend_name,
                network=network,
                image_id=images["hindsight_backend"]["image_id"],
            )
            for user, canary in (("tenant-a", canary_a), ("tenant-b", canary_b)):
                record(
                    f"{user}-delete-survives-full-restart",
                    user=user,
                    session_id=f"{user}-post-delete",
                    action="search",
                    canary=canary,
                    expect_present=False,
                )

            backend_logs.append(_container_logs(backend_name))
            postgres_logs.append(_container_logs(postgres_name))
            _stop(backend_name)
            _remove(backend_name)
            _stop(postgres_name)
            _remove(postgres_name)
            state = _state_manifest(state_dir, [canary_a, canary_b])
        finally:
            _remove(backend_name)
            _remove(postgres_name)
            _remove(stub_name)
            _run(["docker", "network", "rm", network], check=False)

    residues = state["plaintext_residue"]
    any_residue = any(paths for paths in residues.values())
    status = (
        "BLOCKED_NATIVE_PHYSICAL_PURGE_RESIDUE"
        if any_residue
        else "BLOCKED_NATIVE_NO_HERMES_PURGE_TOOL"
    )
    return {
        "schema_version": 1,
        "status": status,
        "scientific_result": False,
        "publication_ready": False,
        "provider_quality_evaluated": False,
        "h100_admitted": False,
        "scope": "native CPU lifecycle and exact Hermes Hindsight provider transport only",
        "images": images,
        "network": {"internal": True, "external_api_access": False},
        "runtime": {
            "rootfs_read_only": True,
            "cap_drop": "ALL",
            "no_new_privileges": True,
            "gpu_count": 0,
            "database_mode": "external-postgresql-pgvector",
            "database_data_checksums": True,
            "stable_worker_id": "cotcodec-hermes-hindsight-doctor",
        },
        "provider_contract": {
            "exact_hermes_provider": True,
            "tool_names": [
                "hindsight_retain",
                "hindsight_recall",
                "hindsight_reflect",
            ],
            "hermes_purge_tool_exposed": False,
            "delete_path": "hindsight-client-admin-delete-bank",
            "hermes_client_version": "0.6.1",
            "native_service_version": "0.9.0",
        },
        "controls": {
            "embedding": "deterministic 16-dimensional token-hash stub",
            "model_calls": 0,
            "external_network_calls": 0,
            "model_stub_sha256": _sha(MODEL_STUB.read_bytes()),
            "adapter_doctor_sha256": _sha((DOCTOR_ROOT / "adapter_doctor.py").read_bytes()),
            "doctor_sha256": _sha(Path(__file__).read_bytes()),
            "backend_dockerfile_sha256": _sha(
                (DOCTOR_ROOT / "Dockerfile.backend-doctor").read_bytes()
            ),
            "adapter_dockerfile_sha256": _sha(
                (DOCTOR_ROOT / "Dockerfile.adapter-doctor").read_bytes()
            ),
            "postgres_repo_digest": PGVECTOR_REPO_DIGEST,
        },
        "operations": operations,
        "state": state,
        "backend_logs_sha256": [_sha(log.encode("utf-8")) for log in backend_logs],
        "backend_logs": backend_logs,
        "postgres_logs_sha256": [_sha(log.encode("utf-8")) for log in postgres_logs],
        "postgres_logs": postgres_logs,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend-image", default="cotcodec/hermes-hindsight-backend:doctor-v1")
    parser.add_argument("--postgres-image", default=PGVECTOR_REPO_DIGEST)
    parser.add_argument("--stub-image", default="cotcodec/openviking-model-stub:doctor-v1")
    parser.add_argument("--adapter-image", default="cotcodec/hermes-hindsight-adapter:doctor-v1")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise SystemExit(f"output directory already exists: {args.output_dir}")
    report = run_doctor(
        backend_image=args.backend_image,
        postgres_image=args.postgres_image,
        stub_image=args.stub_image,
        adapter_image=args.adapter_image,
    )
    report_bytes = _json_bytes(report)
    _write_once(args.output_dir / "report.json", report_bytes)
    manifest = {
        "schema_version": 1,
        "status": report["status"],
        "report": "report.json",
        "report_sha256": _sha(report_bytes),
    }
    _write_once(args.output_dir / "manifest.json", _json_bytes(manifest))
    print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
