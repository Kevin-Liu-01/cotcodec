#!/usr/bin/env python3
"""Run and seal the registered LightMem2 lifecycle falsifier."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validate_lightmem2_context_paging_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    EXPECTED_STATUS,
    validate_experiment_contract,
)

DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data/results/lightmem2-context-paging/2026-08-16-local-docker-v1"
)
DEFAULT_IMAGE = "cotcodec-lightmem2-context-paging:dfc67e8-arm64-v4"
DOCTOR = PROJECT_ROOT / "infra/memory-baselines/lightmem2/doctor.ts"
DOCKERFILE = PROJECT_ROOT / "infra/memory-baselines/lightmem2/Dockerfile"
SOURCE_PATHS = {
    "archive-recovery-index.ts": (
        "/opt/lightmem2/source/components/packages/foundation/artifact-store/"
        "src/archive-recovery/index.ts"
    ),
    "mcp-index.ts": "/opt/lightmem2/source/components/products/mcp/src/index.ts",
    "history-apply.ts": (
        "/opt/lightmem2/source/components/packages/features/eviction/"
        "src/history-apply.ts"
    ),
    "package.json": "/opt/lightmem2/source/package.json",
    "pnpm-lock.yaml": "/opt/lightmem2/source/pnpm-lock.yaml",
}
SUITE_PATHS = (
    "components/packages/foundation/artifact-store/tests/*.test.ts",
    "components/packages/features/eviction/tests/*.test.ts",
    "components/products/mcp/tests/*.test.ts",
    "components/adapters/claude-code/tests/context-rewrite-apply-archive-plan.test.ts",
    "components/adapters/claude-code/tests/context-rewrite-archive.test.ts",
)
COUNT_PATTERNS = {
    name: re.compile(rf"ℹ {name} (?P<count>\d+)")
    for name in ("tests", "pass", "fail", "skipped")
}


class RunnerError(RuntimeError):
    """Raised when contained LightMem2 evidence drifts."""


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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
                raise RunnerError(f"short write: {path}")
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
        raise RunnerError(f"command failed ({completed.returncode}): {argv!r}\n{stderr}")
    return completed


def _strict_json(raw: bytes, label: str) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise RunnerError(f"{label} contains non-finite value {value}")

    try:
        value = json.loads(raw, parse_constant=reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RunnerError(f"{label} did not emit strict JSON") from exc
    if not isinstance(value, dict):
        raise RunnerError(f"{label} did not emit a JSON object")
    return value


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
        "512",
        "--memory",
        "4g",
        "--cpus",
        "4",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=1g",
        "--user",
        "65532:65532",
        "-e",
        "HOME=/tmp/lightmem2-home",
    ]


def _image_contract(image: str, experiment: dict[str, Any], output: Path) -> dict[str, Any]:
    completed = _run(["docker", "image", "inspect", image])
    _write_once(output / "image-inspect.json", completed.stdout)
    try:
        values = json.loads(completed.stdout)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RunnerError("docker image inspect was not JSON") from exc
    if not isinstance(values, list) or len(values) != 1 or not isinstance(values[0], dict):
        raise RunnerError("docker image inspect returned an unexpected roster")
    inspect = values[0]
    labels = (inspect.get("Config") or {}).get("Labels") or {}
    source = experiment["source"]
    expected = {
        "org.opencontainers.image.revision": source["revision"],
        "org.opencontainers.image.licenses": source["license"],
        "org.cotcodec.discovery-only": "true",
        "org.cotcodec.source-tree": source["tree"],
        "org.cotcodec.source-archive-sha256": source["git_archive_tar_sha256"],
        "org.cotcodec.doctor-sha256": _sha_path(DOCTOR),
    }
    for key, expected_value in expected.items():
        if labels.get(key) != expected_value:
            raise RunnerError(f"LightMem2 image label {key} drifted")
    config = inspect.get("Config") or {}
    if (
        inspect.get("Architecture") != "arm64"
        or inspect.get("Os") != "linux"
        or config.get("User") != "65532:65532"
        or config.get("Entrypoint")
        != ["node", "--import", "tsx", "/opt/cotcodec/doctor.ts"]
    ):
        raise RunnerError("LightMem2 image runtime contract drifted")
    return {
        "image_id": inspect.get("Id"),
        "architecture": inspect.get("Architecture"),
        "os": inspect.get("Os"),
        "inspect_sha256": _sha_bytes(completed.stdout),
        "labels": expected,
    }


def _relevant_suite(image_id: str, output: Path) -> dict[str, Any]:
    argv = [
        *_docker_options(),
        "--entrypoint",
        "node",
        image_id,
        "--import",
        "tsx",
        "--test",
        *SUITE_PATHS,
    ]
    completed = _run(argv, check=False)
    raw = completed.stdout + completed.stderr
    _write_once(output / "upstream-relevant-suite.txt", raw)
    text = raw.decode("utf-8", errors="replace")
    counts: dict[str, int] = {}
    for name, pattern in COUNT_PATTERNS.items():
        matches = list(pattern.finditer(text))
        if not matches:
            raise RunnerError(f"cannot parse LightMem2 suite {name} count")
        counts[name] = int(matches[-1].group("count"))
    expected = {"tests": 49, "pass": 47, "fail": 2, "skipped": 0}
    if completed.returncode != 1 or counts != expected:
        raise RunnerError(f"LightMem2 relevant-suite outcome drifted: {counts}")
    if text.count("Cannot find module '@lightmem2/kernel'") < 2:
        raise RunnerError("LightMem2 expected MCP dependency failure disappeared")
    return {
        "argv": argv,
        "exit_code": completed.returncode,
        **counts,
        "output": "upstream-relevant-suite.txt",
        "output_sha256": _sha_path(output / "upstream-relevant-suite.txt"),
        "failure_class": "undeclared-product-surface-kernel-dependency-breaks-mcp-tests",
    }


def _export_source_files(image_id: str, output: Path) -> dict[str, str]:
    digests: dict[str, str] = {}
    for name, source_path in SOURCE_PATHS.items():
        completed = _run(
            [*_docker_options(), "--entrypoint", "cat", image_id, source_path]
        )
        path = output / "source" / name
        _write_once(path, completed.stdout)
        digests[name] = _sha_path(path)
    return digests


def _initialize_volume(image_id: str, volume: str) -> None:
    # Root only initializes the new Docker-managed volume. Every measured phase
    # runs as uid/gid 65532 with all capabilities dropped and no network.
    _run(
        [
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
            "--user",
            "0:0",
            "--entrypoint",
            "node",
            "-v",
            f"{volume}:/state:rw",
            image_id,
            "--eval",
            'require("fs").chmodSync("/state", 0o777)',
        ]
    )


def _phase(
    image_id: str, volume: str, phase: str, repeat: int
) -> tuple[dict[str, Any], list[str]]:
    argv = [
        *_docker_options(),
        "-v",
        f"{volume}:/state:rw",
        image_id,
        phase,
        "--state-root",
        "/state",
        "--repeat",
        str(repeat),
    ]
    completed = _run(argv)
    return _strict_json(completed.stdout, f"LightMem2 repeat {repeat} {phase}"), argv


def _export_volume_file(image_id: str, volume: str, path: str) -> bytes:
    return _run(
        [
            *_docker_options(),
            "-v",
            f"{volume}:/state:ro",
            "--entrypoint",
            "cat",
            image_id,
            f"/state/{path}",
        ]
    ).stdout


def _export_volume_tar(image_id: str, volume: str) -> bytes:
    return _run(
        [
            *_docker_options(),
            "-v",
            f"{volume}:/state:ro",
            "--entrypoint",
            "tar",
            image_id,
            "-cf",
            "-",
            "-C",
            "/state",
            ".",
        ]
    ).stdout


def _projection(run: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "prepare": {
            field: run["prepare"][field]
            for field in (
                "archive_before_stub_succeeded",
                "strict_session_lookup_rejected_other_session",
                "unscoped_mcp_resolver_recovered_other_session",
                "archive_filename_collision_reused_path",
                "first_key_resolved_to_second_payload",
            )
        },
        "restart": {
            field: run["verify-restart"][field]
            for field in (
                "restart_preserved_session_a_archive",
                "restart_strict_session_lookup_rejected_b",
                "restart_unscoped_mcp_resolver_disclosed_b_to_any_caller",
                "recovery_api_accepts_session_scope",
            )
        },
        "purge": {
            field: run["purge-probe"][field]
            for field in (
                "status",
                "native_artifact_store_methods",
                "native_scoped_purge_api_available",
                "plaintext_a_remains",
                "plaintext_b_remains",
                "other_session_remains_recoverable",
                "h100_actor_admission",
            )
        },
    }


def run_doctor(*, experiment_path: Path, output: Path, image: str) -> dict[str, Any]:
    experiment = validate_experiment_contract(experiment_path)
    if output.exists():
        raise RunnerError(f"output already exists: {output}")
    output.mkdir(parents=True, mode=0o700)
    _write_once(output / "experiment.yaml", experiment_path.read_bytes())
    image_contract = _image_contract(image, experiment, output)
    image_id = str(image_contract["image_id"])
    suite = _relevant_suite(image_id, output)
    source_files = _export_source_files(image_id, output)

    expected_source_files = {
        "archive-recovery-index.ts": experiment["source"]["archive_source_sha256"],
        "mcp-index.ts": experiment["source"]["mcp_source_sha256"],
        "history-apply.ts": experiment["source"]["eviction_source_sha256"],
        "package.json": experiment["source"]["package_json_sha256"],
        "pnpm-lock.yaml": experiment["source"]["pnpm_lock_sha256"],
    }
    if source_files != expected_source_files:
        raise RunnerError("LightMem2 retained source files drifted")

    runs: list[dict[str, dict[str, Any]]] = []
    artifact_receipts: list[dict[str, Any]] = []
    for repeat in (1, 2):
        repeat_root = output / f"repeat-{repeat}"
        repeat_root.mkdir(mode=0o700)
        volume = f"cotcodec-lightmem2-{uuid.uuid4().hex}"
        _run(["docker", "volume", "create", volume])
        try:
            _initialize_volume(image_id, volume)
            run: dict[str, dict[str, Any]] = {}
            for phase in ("prepare", "verify-restart", "purge-probe"):
                payload, argv = _phase(image_id, volume, phase, repeat)
                path = repeat_root / f"{phase}.json"
                _write_once(path, _json_bytes(payload))
                artifact_receipts.append(
                    {
                        "artifact": str(path.relative_to(PROJECT_ROOT)),
                        "artifact_sha256": _sha_path(path),
                        "argv": argv,
                    }
                )
                run[phase] = payload
            contract_path = repeat_root / "contract.json"
            _write_once(contract_path, _export_volume_file(image_id, volume, "contract.json"))
            state_path = repeat_root / "state.tar"
            _write_once(state_path, _export_volume_tar(image_id, volume))
            for path in (contract_path, state_path):
                artifact_receipts.append(
                    {
                        "artifact": str(path.relative_to(PROJECT_ROOT)),
                        "artifact_sha256": _sha_path(path),
                    }
                )
            runs.append(run)
        finally:
            _run(["docker", "volume", "rm", volume], check=False)

    projections = [_projection(run) for run in runs]
    if projections[0] != projections[1]:
        raise RunnerError("LightMem2 clean-state semantic projections diverged")
    projection = projections[0]
    expected_projection = {
        "prepare": {
            "archive_before_stub_succeeded": True,
            "strict_session_lookup_rejected_other_session": True,
            "unscoped_mcp_resolver_recovered_other_session": True,
            "archive_filename_collision_reused_path": True,
            "first_key_resolved_to_second_payload": True,
        },
        "restart": {
            "restart_preserved_session_a_archive": True,
            "restart_strict_session_lookup_rejected_b": True,
            "restart_unscoped_mcp_resolver_disclosed_b_to_any_caller": True,
            "recovery_api_accepts_session_scope": False,
        },
        "purge": {
            "status": EXPECTED_STATUS,
            "native_artifact_store_methods": ["archive", "read", "resolve"],
            "native_scoped_purge_api_available": False,
            "plaintext_a_remains": True,
            "plaintext_b_remains": True,
            "other_session_remains_recoverable": True,
            "h100_actor_admission": "forbidden-for-this-revision",
        },
    }
    if projection != expected_projection:
        raise RunnerError("LightMem2 expected falsification did not reproduce")

    report = {
        "schema_version": 1,
        "status": EXPECTED_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "h100_actor_admission": "forbidden-for-this-revision",
        "source": experiment["source"],
        "runtime": experiment["runtime"],
        "experiment_sha256": _sha_path(output / "experiment.yaml"),
        "dockerfile_sha256": _sha_path(DOCKERFILE),
        "doctor_sha256": _sha_path(DOCTOR),
        "image": image_contract,
        "upstream_relevant_suite": suite,
        "source_file_sha256": source_files,
        "stable_projection": projection,
        "stable_projection_sha256": _sha_bytes(_json_bytes(projection)),
        "reproduced_in_two_clean_states": True,
        "artifact_receipts": artifact_receipts,
    }
    _write_once(output / "report.json", _json_bytes(report))
    manifest = {
        "schema_version": 1,
        "status": "SEALED_DISCOVERY_NEGATIVE",
        "report": "report.json",
        "report_sha256": _sha_path(output / "report.json"),
        "image_id": image_id,
        "stable_projection_sha256": report["stable_projection_sha256"],
        "artifact_count": len(artifact_receipts),
    }
    _write_once(output / "manifest.json", _json_bytes(manifest))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", type=Path, default=DEFAULT_EXPERIMENT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    args = parser.parse_args()
    report = run_doctor(
        experiment_path=args.experiment.resolve(),
        output=args.output.resolve(),
        image=args.image,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
