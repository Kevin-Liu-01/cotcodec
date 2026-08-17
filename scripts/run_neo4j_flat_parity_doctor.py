#!/usr/bin/env python3
"""Run the registered Neo4j identical-tuple flat-parity doctor in Docker."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_neo4j_preference_lifecycle_doctor import (  # noqa: E402
    DoctorError,
    _initialize_volume,
    _run,
    _start_database,
)
from scripts.validate_neo4j_flat_parity_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    EXPECTED_STATUS,
    validate_experiment_contract,
)

DEFAULT_OUTPUT = (
    PROJECT_ROOT / "data/results/neo4j-flat-parity/2026-08-15-h100-v1"
)
DEFAULT_PARITY_DOCTOR = (
    PROJECT_ROOT / "infra/memory-baselines/neo4j-agent-memory/parity_doctor.py"
)
DEFAULT_FIXTURE_MODULE = PROJECT_ROOT / "harness/memory_trials/neo4j_flat_parity.py"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


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


def _strict_file(path: Path, label: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise DoctorError(f"{label} must be a regular non-symlink file")


def _validate_digest(value: str, label: str) -> None:
    if (
        len(value) != 71
        or not value.startswith("sha256:")
        or any(character not in "0123456789abcdef" for character in value[7:])
    ):
        raise DoctorError(f"{label} is not an immutable SHA-256 image ID")


def _run_client(
    *,
    image_id: str,
    network: str,
    database_host: str,
    password: str,
    parity_doctor: Path,
    fixture_module: Path,
) -> dict[str, Any]:
    output = _run(
        [
            "docker",
            "run",
            "--rm",
            "--pull=never",
            "--platform",
            "linux/amd64",
            "--network",
            network,
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "192",
            "--memory",
            "2g",
            "--cpus",
            "2",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,nodev,size=128m",
            "-e",
            f"NEO4J_URI=bolt://{database_host}:7687",
            "-e",
            f"NEO4J_PASSWORD={password}",
            "-v",
            f"{parity_doctor}:/opt/cotcodec/parity_doctor.py:ro",
            "-v",
            f"{fixture_module}:/opt/cotcodec/neo4j_flat_parity.py:ro",
            "--entrypoint",
            "/opt/neo4j-agent-memory/.venv/bin/python",
            image_id,
            "/opt/cotcodec/parity_doctor.py",
        ]
    )
    lines = output.splitlines()
    if len(lines) != 1:
        raise DoctorError("parity client emitted unexpected stdout")

    def reject_constant(value: str) -> None:
        raise DoctorError(f"parity report contains non-finite {value}")

    try:
        report = json.loads(lines[0], parse_constant=reject_constant)
    except json.JSONDecodeError as exc:
        raise DoctorError("parity client did not return JSON") from exc
    if not isinstance(report, dict):
        raise DoctorError("parity client report must be an object")
    return report


def _validate_component_report(report: dict[str, Any]) -> None:
    supplied_sha = report.get("report_sha256")
    content = {key: value for key, value in report.items() if key != "report_sha256"}
    expected_hit_counts = {
        "flat_bm25_dense": 0,
        "zero_traversal": 0,
        "flat_sql_join": 48,
        "true_graph": 48,
        "shuffled_graph": 0,
    }
    if (
        report.get("schema_version") != 1
        or report.get("study") != "neo4j-identical-tuple-flat-parity-v1"
        or report.get("status") != EXPECTED_STATUS
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("source_revision")
        != "231d60eac9401ab156ba194b519d89dd644dadb8"
        or report.get("case_count") != 48
        or report.get("tuple_count") != 672
        or report.get("top_k") != 2
        or report.get("max_injected_bytes") != 256
        or report.get("hit_counts") != expected_hit_counts
        or report.get("model_calls") != 0
        or report.get("embedding_model_calls") != 0
        or report.get("external_network_calls") != 0
        or not isinstance(report.get("gates"), dict)
        or not all(report["gates"].values())
        or not isinstance(report.get("rows"), list)
        or len(report["rows"]) != 48
        or supplied_sha != _sha(_canonical(content))
    ):
        raise DoctorError("parity component report contract or hash drifted")


def _semantic_projection(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key not in {"elapsed_seconds", "report_sha256"}
    }


def _one_repeat(
    *,
    repeat: int,
    client_image_id: str,
    neo4j_image: str,
    parity_doctor: Path,
    fixture_module: Path,
) -> dict[str, Any]:
    token = secrets.token_hex(6)
    network = f"cotcodec-neo4j-parity-{token}"
    volume = f"cotcodec-neo4j-parity-{token}"
    password = f"cotcodec-{secrets.token_hex(12)}"
    database_name = f"neo4j-parity-{token}"
    _run(["docker", "network", "create", "--internal", network])
    _run(["docker", "volume", "create", volume])
    try:
        _initialize_volume(volume=volume, image=neo4j_image, platform="linux/amd64")
        _start_database(
            name=database_name,
            network=network,
            volume=volume,
            image=neo4j_image,
            password=password,
            platform="linux/amd64",
        )
        report = _run_client(
            image_id=client_image_id,
            network=network,
            database_host=database_name,
            password=password,
            parity_doctor=parity_doctor,
            fixture_module=fixture_module,
        )
        _validate_component_report(report)
        return {"repeat": repeat, "component_report": report}
    finally:
        subprocess.run(
            ["docker", "rm", "-f", database_name], check=False, capture_output=True
        )
        subprocess.run(
            ["docker", "volume", "rm", "-f", volume], check=False, capture_output=True
        )
        subprocess.run(
            ["docker", "network", "rm", network], check=False, capture_output=True
        )


def _manifest(root: Path) -> dict[str, Any]:
    files: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise DoctorError(f"output contains symlink: {path}")
        if path.is_file() and path.name != "manifest.json":
            data = path.read_bytes()
            files[path.relative_to(root).as_posix()] = {
                "bytes": len(data),
                "sha256": _sha(data),
            }
    return {
        "schema_version": 1,
        "status": EXPECTED_STATUS,
        "files": files,
        "root_sha256": _sha(_json_bytes(files)),
    }


def run_doctor(
    output: Path,
    *,
    client_image: str,
    expected_client_image_id: str,
    parity_doctor: Path = DEFAULT_PARITY_DOCTOR,
    fixture_module: Path = DEFAULT_FIXTURE_MODULE,
) -> dict[str, Any]:
    experiment = validate_experiment_contract(DEFAULT_EXPERIMENT)
    _validate_digest(expected_client_image_id, "client image ID")
    if client_image != experiment["runtime"]["client_image"]:
        raise DoctorError("client image tag differs from the experiment")
    if expected_client_image_id != experiment["runtime"]["client_image_id"]:
        raise DoctorError("client image ID differs from the experiment")
    _strict_file(parity_doctor, "parity doctor")
    _strict_file(fixture_module, "fixture module")
    if output.exists():
        raise DoctorError(f"output already exists: {output}")
    inspect_rows = json.loads(_run(["docker", "image", "inspect", client_image]))
    if (
        not isinstance(inspect_rows, list)
        or len(inspect_rows) != 1
        or inspect_rows[0].get("Id") != expected_client_image_id
        or inspect_rows[0].get("Os") != "linux"
        or inspect_rows[0].get("Architecture") != "amd64"
    ):
        raise DoctorError("prebuilt client image inspect drifted")
    neo4j_image = experiment["runtime"]["neo4j_image"]
    _run(["docker", "pull", "--platform", "linux/amd64", neo4j_image])
    neo4j_inspect = json.loads(_run(["docker", "image", "inspect", neo4j_image]))[0]
    started = time.monotonic()
    repeats = [
        _one_repeat(
            repeat=index,
            client_image_id=expected_client_image_id,
            neo4j_image=neo4j_image,
            parity_doctor=parity_doctor,
            fixture_module=fixture_module,
        )
        for index in (1, 2)
    ]
    if _semantic_projection(repeats[0]["component_report"]) != _semantic_projection(
        repeats[1]["component_report"]
    ):
        raise DoctorError("clean parity repetitions differ")
    elapsed = time.monotonic() - started
    if elapsed > experiment["runtime"]["wall_clock_minutes"] * 60:
        raise DoctorError("parity doctor exceeded the wall-clock budget")
    report = {
        "schema_version": 1,
        "study": experiment["study_id"],
        "status": EXPECTED_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "runtime_lane": "cluster-amd64-slurm",
        "slurm_h100_count": 1,
        "container_gpu_count": 0,
        "model_calls": 0,
        "source": experiment["source"],
        "runtime": {
            "client_image": client_image,
            "client_image_id": expected_client_image_id,
            "neo4j_image": neo4j_image,
            "neo4j_image_id": neo4j_inspect["Id"],
            "network": "private-internal-only",
            "sudo_used": False,
        },
        "inputs": {
            "experiment_sha256": _sha(DEFAULT_EXPERIMENT.read_bytes()),
            "parity_doctor_sha256": _sha(parity_doctor.read_bytes()),
            "fixture_module_sha256": _sha(fixture_module.read_bytes()),
        },
        "repeats": repeats,
        "semantic_projection": _semantic_projection(repeats[0]["component_report"]),
        "elapsed_seconds": elapsed,
        "interpretation": "designed traversal-component evidence only",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.parent / f".{output.name}.{secrets.token_hex(5)}"
    temporary.mkdir(mode=0o700)
    try:
        _write_once(temporary / "experiment.yaml", DEFAULT_EXPERIMENT.read_bytes())
        _write_once(temporary / "report.json", _json_bytes(report))
        _write_once(temporary / "manifest.json", _json_bytes(_manifest(temporary)))
        os.rename(temporary, output)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--client-image", required=True)
    parser.add_argument("--expected-client-image-id", required=True)
    parser.add_argument("--parity-doctor", type=Path, default=DEFAULT_PARITY_DOCTOR)
    parser.add_argument("--fixture-module", type=Path, default=DEFAULT_FIXTURE_MODULE)
    args = parser.parse_args()
    report = run_doctor(
        args.output_dir.resolve(),
        client_image=args.client_image,
        expected_client_image_id=args.expected_client_image_id,
        parity_doctor=args.parity_doctor.resolve(),
        fixture_module=args.fixture_module.resolve(),
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
