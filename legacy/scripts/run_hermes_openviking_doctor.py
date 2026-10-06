#!/usr/bin/env python3
"""Run a contained native OpenViking lifecycle doctor through Hermes."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCTOR_ROOT = PROJECT_ROOT / "infra/memory-baselines/hermes-openviking"
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "data/results/hermes-openviking/2026-08-14-lifecycle-doctor-v2"
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


def _wait_healthy(name: str, *, timeout_seconds: float = 120.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    last = ""
    while time.monotonic() < deadline:
        result = _run(
            ["docker", "exec", name, "curl", "-fsS", "http://127.0.0.1:1933/health"],
            timeout=10,
            check=False,
        )
        if result.returncode == 0:
            return
        last = (result.stdout + result.stderr).decode(errors="replace")
        running = _run(
            ["docker", "inspect", "--format", "{{.State.Running}}", name],
            check=False,
        )
        if running.returncode != 0 or running.stdout.strip() != b"true":
            raise DoctorError(
                f"OpenViking exited before health: {last}\n{_container_logs(name)}"
            )
        time.sleep(0.5)
    raise DoctorError(f"OpenViking health timed out: {last}\n{_container_logs(name)}")


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
            "openviking-model-stub",
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


def _start_server(
    *, name: str, network: str, image_id: str, state_dir: Path
) -> None:
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
            "openviking",
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
            "5g",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,nodev,size=1g,mode=0700",
            "-v",
            f"{state_dir}:/app/.openviking:rw",
            "-e",
            "OPENVIKING_WITH_BOT=0",
            image_id,
        ],
        timeout=60,
    )
    _wait_healthy(name)


def _adapter_action(
    *,
    image_id: str,
    network: str,
    account: str,
    user: str,
    session_id: str,
    action: str,
    canary: str,
    uri: str = "",
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
        "/tmp:rw,noexec,nosuid,nodev,size=64m,mode=0700,uid=65532,gid=65532",
        "--tmpfs",
        "/state:rw,noexec,nosuid,nodev,size=16m,mode=0700,uid=65532,gid=65532",
        "-e",
        "OPENVIKING_ENDPOINT=http://openviking:1933",
        "-e",
        "OPENVIKING_API_KEY=doctor-root-key-not-a-secret",
        "-e",
        f"OPENVIKING_ACCOUNT={account}",
        "-e",
        f"OPENVIKING_USER={user}",
        "-e",
        "OPENVIKING_AGENT=hermes-doctor",
        image_id,
        "--action",
        action,
        "--session-id",
        session_id,
        "--canary",
        canary,
    ]
    if uri:
        argv.extend(["--uri", uri])
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
    residue_proofs: dict[str, list[dict[str, Any]]] = {
        canary: [] for canary in canaries
    }
    total = 0
    for path in sorted(state_dir.rglob("*")):
        if path.is_symlink():
            raise DoctorError(f"state contains a symlink: {path}")
        if not path.is_file():
            continue
        relative = path.relative_to(state_dir).as_posix()
        data = path.read_bytes()
        total += len(data)
        if total > 2 * 1024 * 1024 * 1024:
            raise DoctorError("OpenViking state exceeds the 2 GiB doctor ceiling")
        for canary in canaries:
            encoded_canary = canary.encode("utf-8")
            offset = data.find(encoded_canary)
            if offset >= 0:
                residues[canary].append(relative)
                start = max(0, offset - 16)
                end = min(len(data), offset + len(encoded_canary) + 16)
                window = data[start:end]
                residue_proofs[canary].append(
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
        "plaintext_residue_proofs": residue_proofs,
    }


def run_doctor(
    *, openviking_image: str, stub_image: str, adapter_image: str
) -> dict[str, Any]:
    images = {
        "openviking": _inspect_image(openviking_image),
        "model_stub": _inspect_image(stub_image),
        "hermes_adapter": _inspect_image(adapter_image),
    }
    token = secrets.token_hex(6)
    network = f"cotcodec-ov-{token}"
    stub_name = f"cotcodec-ov-stub-{token}"
    server_name = f"cotcodec-ov-server-{token}"
    canary_a = f"cotcodec-openviking-tenant-a-{token}"
    canary_b = f"cotcodec-openviking-tenant-b-{token}"
    operations: list[dict[str, Any]] = []
    server_logs: list[str] = []

    runtime_tmp = PROJECT_ROOT / "data/results/.runtime-tmp"
    runtime_tmp.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="cotcodec-openviking-state-", dir=runtime_tmp
    ) as state_tmp:
        state_dir = Path(state_tmp)
        shutil.copy2(DOCTOR_ROOT / "ov.conf.doctor.json", state_dir / "ov.conf")
        _run(["docker", "network", "create", "--internal", network])
        try:
            network_inspect = json.loads(
                _run(["docker", "network", "inspect", network]).stdout
            )
            if (
                not isinstance(network_inspect, list)
                or len(network_inspect) != 1
                or network_inspect[0].get("Internal") is not True
            ):
                raise DoctorError("Docker doctor network is not internal")
            _start_stub(name=stub_name, network=network, image_id=images["model_stub"]["image_id"])
            _start_server(
                name=server_name,
                network=network,
                image_id=images["openviking"]["image_id"],
                state_dir=state_dir,
            )

            write_a = _adapter_action(
                image_id=images["hermes_adapter"]["image_id"],
                network=network,
                account="tenant-a",
                user="user-a",
                session_id="session-a-write",
                action="write",
                canary=canary_a,
            )
            operations.append({"name": "tenant-a-write", **write_a})
            uri_a = write_a["payload"]["result"]["uri"]

            server_logs.append(_container_logs(server_name))
            _stop(server_name)
            _remove(server_name)
            _start_server(
                name=server_name,
                network=network,
                image_id=images["openviking"]["image_id"],
                state_dir=state_dir,
            )

            operations.append(
                {
                    "name": "tenant-a-restart-search",
                    **_adapter_action(
                        image_id=images["hermes_adapter"]["image_id"],
                        network=network,
                        account="tenant-a",
                        user="user-a",
                        session_id="session-a-restart",
                        action="search",
                        canary=canary_a,
                        uri=uri_a,
                    ),
                }
            )
            operations.append(
                {
                    "name": "tenant-b-cannot-see-a",
                    **_adapter_action(
                        image_id=images["hermes_adapter"]["image_id"],
                        network=network,
                        account="tenant-b",
                        user="user-b",
                        session_id="session-b-isolation",
                        action="search",
                        canary=canary_a,
                        uri=uri_a,
                        expect_present=False,
                    ),
                }
            )
            write_b = _adapter_action(
                image_id=images["hermes_adapter"]["image_id"],
                network=network,
                account="tenant-b",
                user="user-b",
                session_id="session-b-write",
                action="write",
                canary=canary_b,
            )
            operations.append({"name": "tenant-b-write", **write_b})
            uri_b = write_b["payload"]["result"]["uri"]
            operations.append(
                {
                    "name": "tenant-a-cannot-see-b",
                    **_adapter_action(
                        image_id=images["hermes_adapter"]["image_id"],
                        network=network,
                        account="tenant-a",
                        user="user-a",
                        session_id="session-a-isolation",
                        action="search",
                        canary=canary_b,
                        uri=uri_b,
                        expect_present=False,
                    ),
                }
            )
            operations.append(
                {
                    "name": "tenant-a-restart-read",
                    **_adapter_action(
                        image_id=images["hermes_adapter"]["image_id"],
                        network=network,
                        account="tenant-a",
                        user="user-a",
                        session_id="session-a-read",
                        action="read",
                        canary=canary_a,
                        uri=uri_a,
                    ),
                }
            )
            operations.append(
                {
                    "name": "tenant-a-forget",
                    **_adapter_action(
                        image_id=images["hermes_adapter"]["image_id"],
                        network=network,
                        account="tenant-a",
                        user="user-a",
                        session_id="session-a-forget",
                        action="forget",
                        canary=canary_a,
                        uri=uri_a,
                    ),
                }
            )
            operations.append(
                {
                    "name": "tenant-b-forget",
                    **_adapter_action(
                        image_id=images["hermes_adapter"]["image_id"],
                        network=network,
                        account="tenant-b",
                        user="user-b",
                        session_id="session-b-forget",
                        action="forget",
                        canary=canary_b,
                        uri=uri_b,
                    ),
                }
            )

            server_logs.append(_container_logs(server_name))
            _stop(server_name)
            _remove(server_name)
            _start_server(
                name=server_name,
                network=network,
                image_id=images["openviking"]["image_id"],
                state_dir=state_dir,
            )
            for account, user, canary, uri in (
                ("tenant-a", "user-a", canary_a, uri_a),
                ("tenant-b", "user-b", canary_b, uri_b),
            ):
                operations.append(
                    {
                        "name": f"{account}-delete-survives-restart",
                        **_adapter_action(
                            image_id=images["hermes_adapter"]["image_id"],
                            network=network,
                            account=account,
                            user=user,
                            session_id=f"{account}-post-delete",
                            action="search",
                            canary=canary,
                            uri=uri,
                            expect_present=False,
                        ),
                    }
                )
            server_logs.append(_container_logs(server_name))
            _stop(server_name)
            _remove(server_name)
            state = _state_manifest(state_dir, [canary_a, canary_b])
        finally:
            _remove(server_name)
            _remove(stub_name)
            _run(["docker", "network", "rm", network], check=False)

    residue = state["plaintext_residue"]
    any_residue = any(paths for paths in residue.values())
    status = (
        "BLOCKED_NATIVE_PHYSICAL_PURGE_RESIDUE"
        if any_residue
        else "PASS_NATIVE_RESTART_ISOLATION_AND_PURGE"
    )
    return {
        "schema_version": 1,
        "status": status,
        "scientific_result": False,
        "publication_ready": False,
        "provider_quality_evaluated": False,
        "h100_admitted": False,
        "scope": "native CPU lifecycle and exact Hermes provider transport only",
        "images": images,
        "network": {"internal": True, "external_api_access": False},
        "runtime": {
            "rootfs_read_only": True,
            "cap_drop": "ALL",
            "no_new_privileges": True,
            "host_uid": os.getuid(),
            "host_gid": os.getgid(),
            "gpu_count": 0,
        },
        "controls": {
            "embedding": "deterministic 16-dimensional token-hash stub",
            "vlm": "deterministic empty-JSON stub; not used by direct memory tools",
            "openviking_config_sha256": _sha(
                (DOCTOR_ROOT / "ov.conf.doctor.json").read_bytes()
            ),
            "model_stub_sha256": _sha((DOCTOR_ROOT / "model_stub.py").read_bytes()),
            "adapter_doctor_sha256": _sha(
                (DOCTOR_ROOT / "adapter_doctor.py").read_bytes()
            ),
            "doctor_sha256": _sha(Path(__file__).read_bytes()),
            "source_dockerfile_sha256": _sha(
                (DOCTOR_ROOT / "Dockerfile.source-doctor").read_bytes()
            ),
            "stub_dockerfile_sha256": _sha(
                (DOCTOR_ROOT / "Dockerfile.model-stub").read_bytes()
            ),
            "adapter_dockerfile_sha256": _sha(
                (DOCTOR_ROOT / "Dockerfile.adapter-doctor").read_bytes()
            ),
        },
        "operations": operations,
        "state": state,
        "server_logs_sha256": [_sha(log.encode("utf-8")) for log in server_logs],
        "server_logs": server_logs,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--openviking-image", default="cotcodec/openviking:eeff5a49-doctor-v1"
    )
    parser.add_argument(
        "--stub-image", default="cotcodec/openviking-model-stub:doctor-v1"
    )
    parser.add_argument(
        "--adapter-image", default="cotcodec/hermes-openviking-adapter:doctor-v1"
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise SystemExit(f"output directory already exists: {args.output_dir}")
    report = run_doctor(
        openviking_image=args.openviking_image,
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
