#!/usr/bin/env python3
"""Run the pinned Neo4j preference lifecycle doctor in isolated Docker."""

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
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validate_neo4j_preference_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    validate_experiment_contract,
)

DOCKERFILE = PROJECT_ROOT / "infra/memory-baselines/neo4j-agent-memory/Dockerfile"
DOCTOR = PROJECT_ROOT / "infra/memory-baselines/neo4j-agent-memory/doctor.py"
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "data/results/neo4j-preference-lifecycle/2026-08-14-doctor-v1"
)
STATUS = "NEO4J_PREFERENCE_LIFECYCLE_CONFORMANCE_PASS"


class DoctorError(RuntimeError):
    """Raised when containment, provenance, or lifecycle semantics drift."""


def _run(argv: list[str], *, cwd: Path | None = None, capture: bool = True) -> str:
    completed = subprocess.run(
        argv,
        cwd=cwd,
        check=False,
        capture_output=capture,
        text=True,
        timeout=900,
    )
    if completed.returncode != 0:
        raise DoctorError(
            f"command failed ({completed.returncode}): {argv!r}\n{completed.stderr}"
        )
    return completed.stdout.strip() if capture else ""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _write_once(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, 0o600)
    try:
        os.write(descriptor, data)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _safe_extract_tar(data: bytes, destination: Path) -> None:
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
        members = archive.getmembers()
        if len(members) > 20_000:
            raise DoctorError("source archive member ceiling exceeded")
        total = 0
        for member in members:
            path = Path(member.name)
            if path.is_absolute() or ".." in path.parts:
                raise DoctorError("source archive contains traversal")
            if not (member.isfile() or member.isdir()):
                raise DoctorError("source archive contains a non-file member")
            total += member.size
        if total > 512 * 1024 * 1024:
            raise DoctorError("source archive byte ceiling exceeded")
        archive.extractall(destination, filter="data")


def _prepare_context(root: Path, experiment: dict[str, Any]) -> dict[str, Any]:
    checkout = root / "checkout"
    source = experiment["source"]
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
    if _run(["git", "rev-parse", "HEAD"], cwd=checkout) != source["revision"]:
        raise DoctorError("Neo4j Agent Memory revision drifted")
    if _run(["git", "rev-parse", "HEAD^{tree}"], cwd=checkout) != source["tree"]:
        raise DoctorError("Neo4j Agent Memory tree drifted")
    if _run(["git", "status", "--porcelain"], cwd=checkout):
        raise DoctorError("Neo4j Agent Memory checkout is dirty")
    archive = subprocess.run(
        ["git", "archive", "--format=tar", "HEAD"],
        cwd=checkout,
        check=True,
        capture_output=True,
    ).stdout
    if _sha(archive) != source["git_archive_tar_sha256"]:
        raise DoctorError("Neo4j Agent Memory archive digest drifted")
    if _sha((checkout / "LICENSE").read_bytes()) != source["license_sha256"]:
        raise DoctorError("Neo4j Agent Memory license digest drifted")
    if _sha((checkout / "uv.lock").read_bytes()) != source["uv_lock_sha256"]:
        raise DoctorError("Neo4j Agent Memory lock digest drifted")
    context = root / "context"
    upstream = context / "upstream"
    upstream.mkdir(parents=True)
    _safe_extract_tar(archive, upstream)
    shutil.copy2(DOCKERFILE, context / "Dockerfile")
    shutil.copy2(DOCTOR, context / "doctor.py")
    return {
        "context": context,
        "git_archive_tar_sha256": _sha(archive),
        "dockerfile_sha256": _sha(DOCKERFILE.read_bytes()),
        "doctor_sha256": _sha(DOCTOR.read_bytes()),
    }


def _wait_healthy(name: str) -> None:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        status = _run(
            ["docker", "inspect", "--format", "{{.State.Health.Status}}", name]
        )
        if status == "healthy":
            return
        if status == "unhealthy":
            state = _run(["docker", "inspect", "--format", "{{json .State}}", name])
            logs = subprocess.run(
                ["docker", "logs", name],
                check=False,
                capture_output=True,
                text=True,
            )
            raise DoctorError(
                "Neo4j container became unhealthy\n"
                f"state={state}\nstdout={logs.stdout}\nstderr={logs.stderr}"
            )
        time.sleep(1)
    raise DoctorError("Neo4j did not become healthy within 60 seconds")


def _initialize_volume(*, volume: str, image: str, platform: str) -> None:
    _run(
        [
            "docker",
            "run",
            "--rm",
            "--pull=never",
            "--platform",
            platform,
            "--network",
            "none",
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
            "-v",
            f"{volume}:/data",
            "--entrypoint",
            "/bin/chown",
            image,
            "7474:7474",
            "/data",
        ]
    )


def _start_database(
    *,
    name: str,
    network: str,
    volume: str,
    image: str,
    password: str,
    platform: str,
) -> None:
    _run(
        [
            "docker",
            "run",
            "-d",
            "--pull=never",
            "--platform",
            platform,
            "--name",
            name,
            "--network",
            network,
            "--user",
            "7474:7474",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "256",
            "--memory",
            "3g",
            "--cpus",
            "1",
            "-e",
            f"NEO4J_AUTH=neo4j/{password}",
            "-e",
            "NEO4J_server_memory_heap_initial__size=256m",
            "-e",
            "NEO4J_server_memory_heap_max__size=512m",
            "-e",
            "NEO4J_server_http_enabled=false",
            "-e",
            "NEO4J_server_https_enabled=false",
            "-v",
            f"{volume}:/data",
            "--tmpfs",
            "/logs:rw,noexec,nosuid,nodev,size=64m,uid=7474,gid=7474,mode=0750",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,nodev,size=256m,uid=7474,gid=7474,mode=1777",
            "--health-cmd",
            "bash -c 'exec 3<>/dev/tcp/127.0.0.1/7687'",
            "--health-interval",
            "2s",
            "--health-timeout",
            "10s",
            "--health-retries",
            "12",
            "--health-start-period",
            "30s",
            image,
        ]
    )
    _wait_healthy(name)


def _run_client(
    *,
    image_id: str,
    network: str,
    password: str,
    phase: str,
    expected: dict[str, Any] | None,
    platform: str,
) -> dict[str, Any]:
    argv = [
        "docker",
        "run",
        "--rm",
        "--pull=never",
        "--platform",
        platform,
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
        "1",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=64m",
        "-e",
        "NEO4J_URI=bolt://neo4j:7687",
        "-e",
        f"NEO4J_PASSWORD={password}",
        image_id,
        "--phase",
        phase,
    ]
    if expected is not None:
        expected_json = json.dumps(expected, sort_keys=True, separators=(",", ":"))
        argv.extend(("--expected-json", expected_json))
    output = _run(argv)
    lines = output.splitlines()
    if len(lines) != 1:
        raise DoctorError(f"client phase {phase} emitted unexpected output")
    value = json.loads(lines[0])
    if not isinstance(value, dict) or value.get("phase") != phase:
        raise DoctorError(f"client phase {phase} returned an invalid receipt")
    return value


def _semantic_projection(
    establish: dict[str, Any],
    verify: dict[str, Any],
    empty: dict[str, Any],
) -> dict[str, Any]:
    nodes = establish["state"]["nodes"]
    return {
        "node_semantics": sorted(
            (row["user"], row["category"], row["preference"], row["superseded"])
            for row in nodes
        ),
        "supersession_edge_count": len(establish["state"]["supersession_edges"]),
        "active_count": len(establish["expected"]["active_ids"]),
        "history_count": len(establish["expected"]["all_ids"]),
        "past_count": len(establish["expected"]["as_of_ids"]),
        "restart_hash_preserved": verify["state_sha256"]
        == establish["state"]["state_sha256"],
        "purge_nodes": empty["nodes"],
        "purge_edges": empty["edges"],
        "model_calls": establish["model_calls"] + verify["model_calls"] + empty["model_calls"],
    }


def _one_repeat(
    *, repeat: int, client_image: str, neo4j_image: str, platform: str
) -> dict[str, Any]:
    token = secrets.token_hex(5)
    network = f"cotcodec-neo4j-{token}"
    volume = f"cotcodec-neo4j-{token}"
    database = "neo4j"
    password = f"cotcodec-{secrets.token_hex(12)}"
    _run(["docker", "network", "create", "--internal", network])
    _run(["docker", "volume", "create", volume])
    try:
        _initialize_volume(volume=volume, image=neo4j_image, platform=platform)
        _start_database(
            name=database,
            network=network,
            volume=volume,
            image=neo4j_image,
            password=password,
            platform=platform,
        )
        establish = _run_client(
            image_id=client_image,
            network=network,
            password=password,
            phase="establish",
            expected=None,
            platform=platform,
        )
        _run(["docker", "rm", "-f", database])
        _start_database(
            name=database,
            network=network,
            volume=volume,
            image=neo4j_image,
            password=password,
            platform=platform,
        )
        verify = _run_client(
            image_id=client_image,
            network=network,
            password=password,
            phase="verify-purge",
            expected=establish,
            platform=platform,
        )
        _run(["docker", "rm", "-f", database])
        _start_database(
            name=database,
            network=network,
            volume=volume,
            image=neo4j_image,
            password=password,
            platform=platform,
        )
        empty = _run_client(
            image_id=client_image,
            network=network,
            password=password,
            phase="verify-empty",
            expected=None,
            platform=platform,
        )
        return {
            "repeat": repeat,
            "establish": establish,
            "verify_purge": verify,
            "verify_empty": empty,
            "semantic_projection": _semantic_projection(establish, verify, empty),
        }
    finally:
        subprocess.run(["docker", "rm", "-f", database], check=False, capture_output=True)
        subprocess.run(["docker", "volume", "rm", "-f", volume], check=False, capture_output=True)
        subprocess.run(["docker", "network", "rm", network], check=False, capture_output=True)


def run_doctor(
    output: Path,
    *,
    lane: str | None = None,
    prebuilt_client_image: str | None = None,
    expected_client_image_id: str | None = None,
) -> dict[str, Any]:
    experiment = validate_experiment_contract(DEFAULT_EXPERIMENT)
    selected_lane = lane or experiment["runtime"]["default_lane"]
    lanes = experiment["runtime"]["lanes"]
    if selected_lane not in lanes:
        raise DoctorError(f"unknown runtime lane: {selected_lane}")
    lane_contract = lanes[selected_lane]
    platform = lane_contract["platform"]
    if (prebuilt_client_image is None) != (expected_client_image_id is None):
        raise DoctorError(
            "prebuilt client image and expected image ID must be supplied together"
        )
    if expected_client_image_id is not None and (
        len(expected_client_image_id) != 71
        or not expected_client_image_id.startswith("sha256:")
        or any(
            character not in "0123456789abcdef"
            for character in expected_client_image_id.removeprefix("sha256:")
        )
    ):
        raise DoctorError("expected client image ID is not an immutable SHA-256 ID")
    if output.exists():
        raise DoctorError(f"output already exists: {output}")
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="cotcodec-neo4j-doctor-") as temp:
        context_receipt = _prepare_context(Path(temp), experiment)
        image_tag = f"cotcodec-neo4j-preference-doctor:231d60e-{selected_lane}-v1"
        if prebuilt_client_image is None:
            _run(
                [
                    "docker",
                    "build",
                    "--platform",
                    platform,
                    "--pull",
                    "--build-arg",
                    f"BASE_IMAGE={lane_contract['client_base_image']}",
                    "-t",
                    image_tag,
                    str(context_receipt["context"]),
                ],
                capture=False,
            )
            client_image_source = "built-in-run"
        else:
            if prebuilt_client_image != image_tag:
                raise DoctorError("prebuilt client image tag differs from the lane tag")
            client_image_source = "prebuilt-verified"
        client_inspect = json.loads(_run(["docker", "image", "inspect", image_tag]))[0]
        client_image_id = client_inspect["Id"]
        if (
            expected_client_image_id is not None
            and client_image_id != expected_client_image_id
        ):
            raise DoctorError("prebuilt client image identity drifted")
        if (
            client_inspect.get("Os") != "linux"
            or client_inspect.get("Architecture") != platform.split("/", 1)[1]
        ):
            raise DoctorError("client image platform drifted")
        neo4j_image = lane_contract["neo4j_image"]
        _run(["docker", "pull", "--platform", platform, neo4j_image], capture=False)
        neo4j_inspect = json.loads(_run(["docker", "image", "inspect", neo4j_image]))[0]
        repeats = [
            _one_repeat(
                repeat=index,
                client_image=client_image_id,
                neo4j_image=neo4j_image,
                platform=platform,
            )
            for index in (1, 2)
        ]
    if repeats[0]["semantic_projection"] != repeats[1]["semantic_projection"]:
        raise DoctorError("clean-volume semantic projections differ")
    if repeats[0]["semantic_projection"]["model_calls"] != 0:
        raise DoctorError("the lifecycle doctor used a model")
    if time.monotonic() - started > 15 * 60:
        raise DoctorError("the lifecycle doctor exceeded its wall-clock budget")
    report = {
        "schema_version": 1,
        "study": "neo4j-preference-supersession-lifecycle-v1",
        "status": STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "runtime_lane": selected_lane,
        "confirmation_required": (
            selected_lane != experiment["runtime"]["required_confirmation_lane"]
        ),
        "gpu_hours": 0,
        "source": experiment["source"],
        "runtime": {
            "client_image_id": client_image_id,
            "client_image_source": client_image_source,
            "neo4j_image_id": neo4j_inspect["Id"],
            "neo4j_repo_digests": neo4j_inspect.get("RepoDigests") or [],
            "platform": platform,
            "network": "private-internal-only",
            "sudo_used": False,
        },
        "inputs": {
            key: value for key, value in context_receipt.items() if key != "context"
        },
        "repeats": repeats,
        "semantic_projection": repeats[0]["semantic_projection"],
        "elapsed_seconds": time.monotonic() - started,
        "interpretation": "one-way preference version-lifecycle conformance only",
    }
    output.mkdir(parents=True, mode=0o700)
    artifacts = {
        "experiment.yaml": DEFAULT_EXPERIMENT.read_bytes(),
        "report.json": _json_bytes(report),
    }
    for name, data in artifacts.items():
        _write_once(output / name, data)
    manifest = {
        "schema_version": 1,
        "status": STATUS,
        "artifacts": {
            name: {"bytes": len(data), "sha256": _sha(data)}
            for name, data in artifacts.items()
        },
    }
    manifest["manifest_sha256"] = _sha(_json_bytes(manifest))
    _write_once(output / "manifest.json", _json_bytes(manifest))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--lane",
        choices=("local-arm64", "cluster-amd64-slurm"),
        default=None,
    )
    parser.add_argument("--prebuilt-client-image")
    parser.add_argument("--expected-client-image-id")
    args = parser.parse_args()
    report = run_doctor(
        args.output_dir.resolve(),
        lane=args.lane,
        prebuilt_client_image=args.prebuilt_client_image,
        expected_client_image_id=args.expected_client_image_id,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
