#!/usr/bin/env python3
"""Run the pinned Shodh tier-admission doctor twice in clean containers."""

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

from scripts.validate_shodh_tier_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    EXPECTED_STATUS,
    validate_experiment_contract,
)

DEFAULT_IMAGE = "cotcodec-shodh-tier-admission:98c6e48-arm64-v3"
DEFAULT_OUTPUT = PROJECT_ROOT / "data/results/shodh-tier-admission/2026-08-16-local-docker-v1"
DOCKERFILE = PROJECT_ROOT / "infra/memory-baselines/shodh/Dockerfile"
DOCTOR = PROJECT_ROOT / "infra/memory-baselines/shodh/doctor.rs"
SOURCE_PATHS = {
    "AUDIT-MEMORY-2026-08-06.md": "/opt/shodh/AUDIT-MEMORY-2026-08-06.md",
    "Cargo.lock": "/opt/shodh/Cargo.lock",
    "Cargo.toml": "/opt/shodh/Cargo.toml",
    "LICENSE": "/opt/shodh/LICENSE",
    "memory-mod.rs": "/opt/shodh/src/memory/mod.rs",
    "memory-types.rs": "/opt/shodh/src/memory/types.rs",
    "memory-persistence-tests.rs": "/opt/shodh/tests/memory_persistence_tests.rs",
    "memory-tiering-tests.rs": "/opt/shodh/tests/memory_tiering_tests.rs",
}


class ShodhRunnerError(RuntimeError):
    """Raised when measured Shodh evidence violates its contract."""


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode()


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


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
                raise ShodhRunnerError(f"short write: {path}")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _run(argv: list[str], *, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(argv, capture_output=True, check=False)
    if check and completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace")[-5000:]
        raise ShodhRunnerError(
            f"command failed ({completed.returncode}): {argv!r}\n{stderr}"
        )
    return completed


def _docker_options() -> list[str]:
    return [
        "docker",
        "run",
        "--rm",
        "--pull",
        "never",
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
        "1024",
        "--memory",
        "6g",
        "--cpus",
        "4",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=3g",
        "--user",
        "65532:65532",
        "-e",
        "HOME=/tmp/shodh-home",
        "-e",
        "SHODH_OFFLINE=true",
        "-e",
        "SHODH_ALLOW_SIMPLIFIED_EMBEDDINGS=1",
    ]


def _image_contract(image: str, experiment: dict[str, Any], output: Path) -> dict[str, Any]:
    completed = _run(["docker", "image", "inspect", image])
    _write_once(output / "image-inspect.json", completed.stdout)
    try:
        values = json.loads(completed.stdout)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ShodhRunnerError("docker image inspect was not JSON") from exc
    if not isinstance(values, list) or len(values) != 1 or not isinstance(values[0], dict):
        raise ShodhRunnerError("docker image inspect returned an unexpected roster")
    inspect = values[0]
    labels = (inspect.get("Config") or {}).get("Labels") or {}
    source = experiment["source"]
    expected_labels = {
        "org.opencontainers.image.revision": source["revision"],
        "org.opencontainers.image.licenses": source["license"],
        "org.cotcodec.discovery-only": "true",
        "org.cotcodec.source-tree": source["tree"],
        "org.cotcodec.source-archive-sha256": source["git_archive_tar_sha256"],
        "org.cotcodec.doctor-sha256": _sha_path(DOCTOR),
    }
    for key, value in expected_labels.items():
        if labels.get(key) != value:
            raise ShodhRunnerError(f"Shodh image label {key} drifted")
    config = inspect.get("Config") or {}
    if (
        inspect.get("Architecture") != "arm64"
        or inspect.get("Os") != "linux"
        or config.get("User") != "65532:65532"
        or config.get("Entrypoint") != ["/bin/sh", "-c"]
    ):
        raise ShodhRunnerError("Shodh image runtime contract drifted")
    return {
        "image_id": inspect.get("Id"),
        "architecture": inspect.get("Architecture"),
        "os": inspect.get("Os"),
        "inspect_sha256": _sha_bytes(completed.stdout),
        "labels": expected_labels,
    }


def _export_source_files(image_id: str, output: Path) -> dict[str, str]:
    digests: dict[str, str] = {}
    for name, source_path in SOURCE_PATHS.items():
        completed = _run(
            [*_docker_options(), "--entrypoint", "/bin/cat", image_id, source_path]
        )
        path = output / "source" / name
        _write_once(path, completed.stdout)
        digests[name] = _sha_path(path)
    return digests


def _strict_report(raw: bytes, repeat: int) -> dict[str, Any]:
    marker = b"COTCODEC_SHODH_REPORT="
    rows = [line[len(marker) :] for line in raw.splitlines() if line.startswith(marker)]
    if len(rows) != 1:
        raise ShodhRunnerError(f"repeat {repeat} emitted {len(rows)} report markers")

    def reject_constant(value: str) -> None:
        raise ShodhRunnerError(f"repeat {repeat} emitted non-finite value {value}")

    try:
        report = json.loads(rows[0], parse_constant=reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ShodhRunnerError(f"repeat {repeat} emitted invalid JSON") from exc
    if not isinstance(report, dict):
        raise ShodhRunnerError(f"repeat {repeat} report is not an object")
    expected_checks = {
        "new_working_record_already_in_long_term_storage",
        "restart_drops_active_caches",
        "restart_preserves_stale_working_tier_label",
        "eligible_persisted_session_is_stranded_after_restart",
        "logical_forget_all_hides_record_after_restart",
        "forget_all_return_overcounts_overlapping_tiers",
        "plaintext_residue_not_observed_after_forget_all",
    }
    if (
        report.get("schema_version") != 1
        or report.get("system_id") != "shodh-memory-98c6e48-tier-admission-v1"
        or report.get("status") != EXPECTED_STATUS
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("h100_actor_admission") is not False
        or set(report.get("checks", {})) != expected_checks
        or any(report["checks"].get(field) is not True for field in expected_checks)
    ):
        raise ShodhRunnerError(f"repeat {repeat} falsification contract drifted")
    return report


def _doctor_repeat(image_id: str, repeat: int, output: Path) -> dict[str, Any]:
    argv = [
        *_docker_options(),
        "--entrypoint",
        "/opt/shodh/target/debug/cotcodec_shodh_doctor",
        image_id,
    ]
    completed = _run(argv, check=False)
    raw = completed.stdout + completed.stderr
    _write_once(output / f"repeat-{repeat}.txt", raw)
    if completed.returncode != 0:
        raise ShodhRunnerError(
            f"repeat {repeat} failed ({completed.returncode}): "
            + raw.decode("utf-8", errors="replace")[-5000:]
        )
    report = _strict_report(raw, repeat)
    _write_once(output / f"repeat-{repeat}.json", _json_bytes(report))
    return report


def run(image: str, output: Path) -> dict[str, Any]:
    experiment = validate_experiment_contract()
    output.mkdir(parents=True, exist_ok=False)
    _write_once(output / "experiment.yaml", DEFAULT_EXPERIMENT.read_bytes())
    _write_once(output / "Dockerfile", DOCKERFILE.read_bytes())
    _write_once(output / "doctor.rs", DOCTOR.read_bytes())
    image_contract = _image_contract(image, experiment, output)
    image_id = image_contract["image_id"]
    if not isinstance(image_id, str) or not image_id.startswith("sha256:"):
        raise ShodhRunnerError("Shodh image lacks immutable local ID")
    source_digests = _export_source_files(image_id, output)
    repeats = [_doctor_repeat(image_id, repeat, output) for repeat in (1, 2)]
    if repeats[0] != repeats[1]:
        raise ShodhRunnerError("Shodh clean-state repeats diverged")
    stable_projection_sha256 = _sha_bytes(_canonical(repeats[0]))
    report = {
        "schema_version": 1,
        "status": EXPECTED_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "h100_actor_admission": "forbidden-for-this-revision",
        "source": experiment["source"],
        "runtime": experiment["runtime"],
        "image": image_contract,
        "source_file_sha256": source_digests,
        "experiment_sha256": _sha_path(DEFAULT_EXPERIMENT),
        "dockerfile_sha256": _sha_path(DOCKERFILE),
        "doctor_sha256": _sha_path(DOCTOR),
        "stable_projection_sha256": stable_projection_sha256,
        "reproduced_in_two_clean_states": True,
        "projection": repeats[0],
    }
    _write_once(output / "report.json", _json_bytes(report))
    manifest = {
        "schema_version": 1,
        "status": "SEALED_DISCOVERY_NEGATIVE",
        "report": "report.json",
        "report_sha256": _sha_path(output / "report.json"),
        "stable_projection_sha256": stable_projection_sha256,
        "image_id": image_id,
        "artifact_count": len([path for path in output.rglob("*") if path.is_file()]) + 1,
    }
    _write_once(output / "manifest.json", _json_bytes(manifest))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = run(args.image, args.output)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
