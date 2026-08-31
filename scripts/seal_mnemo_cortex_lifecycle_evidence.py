#!/usr/bin/env python3
"""Seal and validate Mnemo Cortex's exact-source Slurm lifecycle negative."""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validate_mnemo_cortex_lifecycle_experiment import (  # noqa: E402
    EXPECTED_STATUS,
    validate_experiment_contract,
)

DEFAULT_ROOT = (
    PROJECT_ROOT
    / "data/results/mnemo-cortex-lifecycle/2026-08-26-slurm-cpu-v6"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "research/evidence/memory/mnemo-cortex-native-lifecycle-negative-v1.json"
)
REVISION = "8a0cff9492f010f73d722688924b09938b2dd682"
TREE = "5a87d92d70052717a928c3c109b138da4d8af723"
ARCHIVE_SHA256 = "6b6e7709a85f9f949f2a7820ee4c2a7e60112671297fa5229919a266f014c113"
ARCHIVE_BYTES = 18_810_880
IMAGE_ID = "sha256:6a81c7eac7a1105736e1fa0d271a0d531448f1c9c80da7b980b8fda3af3e1cdb"
STABLE_PROJECTION_SHA256 = (
    "f07a317a4dfa6cea1ccf2b33364a607ca279dcabf4feb33fea014786f1cd2779"
)
REPORT_SHA256 = "97d2d5abab74982194b53065b3481db0dd2431b512c3510c05361c4c64006970"
MANIFEST_SHA256 = "4651effc1bf92080f4784d6816c20c511d3ae883760ffadd4a1af313cb0eb194"
WHEELHOUSE_MANIFEST_SHA256 = (
    "95395024deabd10961d58ca20fd2b19afad9b4c654207e243e9edf35796dcd9a"
)
REQUIREMENTS_SHA256 = (
    "e7661ad02aad751446fd3f889c8a7c1a4f61a3ee333e940e583b3ed9b9a0b055"
)
SLURM_JOB_ID = "347"
CLAIM_BOUNDARY = (
    "Exact pinned Mnemo Cortex smart-note classification, session-log filtering, "
    "Analyst source lineage, deterministic map-reduce dream topology, Passport "
    "observe failure semantics in the official no-Git container surface, "
    "fresh-process persistence, native primary-memory purge surface, current-file "
    "plaintext scan, and dependency provenance; not semantic extraction quality, "
    "real-provider dream quality, secure filesystem erasure, concurrent serving, "
    "sustained throughput, H100 actor quality, or publication evidence."
)
ARTIFACT_NAMES = {
    "Dockerfile",
    "batch.sbatch",
    "doctor-image-build.txt",
    "doctor-image-inspect.json",
    "doctor.py",
    "experiment.yaml",
    "git-probe.txt",
    "manifest.json",
    "pip-freeze.txt",
    "repeat-1-phase-1.txt",
    "repeat-1-phase-2.txt",
    "repeat-1.json",
    "repeat-2-phase-1.txt",
    "repeat-2-phase-2.txt",
    "repeat-2.json",
    "report.json",
    "requirements-linux-x86_64-cp312.txt",
    "runner.py",
    "runtime-receipt.json",
    "source-receipt.json",
    "wheelhouse-manifest.json",
}
MANIFEST_FILE_NAMES = (ARTIFACT_NAMES - {"manifest.json"}) | {"source.tar"}
CODE_PATHS = {
    "experiments/memory/stage3-mnemo-cortex-native-lifecycle-doctor.yaml",
    "infra/memory-baselines/mnemo-cortex/Dockerfile",
    "infra/memory-baselines/mnemo-cortex/doctor.py",
    "infra/memory-baselines/mnemo-cortex/wheelhouse-build-requirements.in",
    "infra/memory-baselines/mnemo-cortex/wheelhouse-manifest.json",
    "infra/slurm/host-single-node/mnemo-cortex-lifecycle.sbatch",
    "scripts/run_mnemo_cortex_lifecycle_doctor.py",
    "scripts/seal_mnemo_cortex_lifecycle_evidence.py",
    "scripts/validate_mnemo_cortex_lifecycle_experiment.py",
}
PHASE_CHECKS = [
    {
        "analyst_note_has_source_lineage",
        "analyst_retains_raw_source_log",
        "default_recall_hides_session_log",
        "deterministic_two_agent_rollup_passes",
        "explicit_drilldown_recalls_session_log",
        "native_primary_memory_purge_absent",
        "official_container_has_no_git",
        "passport_observe_returns_server_error_after_pending_mutation",
        "repeated_failed_observe_creates_duplicate_pending_rows",
        "smart_note_classification_passes",
    },
    {
        "current_file_plaintext_residue_present",
        "default_recall_hides_session_log_after_restart",
        "duplicate_pending_rows_survive_fresh_process",
        "explicit_drilldown_recalls_session_log_after_restart",
        "native_primary_memory_purge_absent_after_restart",
        "normal_state_survives_fresh_process",
    },
]
STATIC_FINDINGS = {
    "analyst_preserves_source_lineage",
    "archive_only_reachable_by_direct_sha_fetch",
    "dreamer_uses_per_agent_then_rollup_stages",
    "passport_mutates_pending_before_git_commit",
    "primary_memory_delete_route_absent",
    "pyproject_uses_lower_bounds",
    "python_dependency_lock_absent",
    "upstream_base_image_mutable",
    "upstream_container_does_not_install_git",
}
OBSERVED_FINDINGS = {
    "analyst_note_has_source_lineage",
    "analyst_retains_raw_source_log",
    "current_file_plaintext_residue_present",
    "default_recall_hides_session_log",
    "deterministic_two_agent_rollup_passes",
    "duplicate_pending_rows_survive_fresh_process",
    "explicit_drilldown_recalls_session_log",
    "native_primary_memory_purge_absent",
    "normal_state_survives_fresh_process",
    "official_container_has_no_git",
    "passport_observe_returns_server_error_after_pending_mutation",
    "repeated_failed_observe_creates_duplicate_pending_rows",
    "smart_note_classification_passes",
}
EXPECTED_FREEZE = {
    "annotated-doc==0.0.5",
    "annotated-types==0.8.0",
    "anyio==4.14.2",
    "certifi==2026.7.22",
    "click==8.5.0",
    "fastapi==0.141.1",
    "h11==0.16.0",
    "httpcore==1.0.9",
    "httpx==0.28.1",
    "idna==3.19",
    "markdown-it-py==4.2.0",
    "mdurl==0.1.2",
    "mnemo-cortex==4.15.0",
    "numpy==2.5.2",
    "packaging==26.3",
    "pydantic==2.13.4",
    "pydantic_core==2.46.4",
    "Pygments==2.21.0",
    "PyYAML==6.0.3",
    "rich==15.0.0",
    "setuptools==84.0.0",
    "sqlite-vec==0.1.9",
    "starlette==1.6.0",
    "typing-inspection==0.4.4",
    "typing_extensions==4.16.0",
    "uvicorn==0.52.4",
    "wheel==0.48.0",
}
TOKEN_RE = re.compile(r"^[0-9A-F]{16}$")


class MnemoCortexLifecycleEvidenceError(ValueError):
    """Raised when retained Mnemo Cortex lifecycle evidence drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _object(data: bytes, owner: str) -> dict[str, Any]:
    def reject(value: str) -> None:
        raise MnemoCortexLifecycleEvidenceError(
            f"{owner} contains non-finite JSON {value}"
        )

    try:
        payload = json.loads(data, parse_constant=reject)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise MnemoCortexLifecycleEvidenceError(f"{owner} is not strict JSON") from error
    if not isinstance(payload, dict):
        raise MnemoCortexLifecycleEvidenceError(f"{owner} must be an object")
    return payload


def _capture(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise MnemoCortexLifecycleEvidenceError(
            f"expected regular evidence input: {path}"
        )
    raw = path.read_bytes()
    compressed = gzip.compress(raw, compresslevel=9, mtime=0)
    return {
        "compression": "gzip-mtime-0",
        "raw_size": len(raw),
        "raw_sha256": _sha(raw),
        "compressed_size": len(compressed),
        "compressed_sha256": _sha(compressed),
        "content_gzip_base64": base64.b64encode(compressed).decode(),
    }


def _decode(receipts: Any) -> dict[str, bytes]:
    if not isinstance(receipts, dict) or set(receipts) != ARTIFACT_NAMES:
        raise MnemoCortexLifecycleEvidenceError(
            "Mnemo Cortex lifecycle artifact roster drifted"
        )
    fields = {
        "compression",
        "raw_size",
        "raw_sha256",
        "compressed_size",
        "compressed_sha256",
        "content_gzip_base64",
    }
    decoded: dict[str, bytes] = {}
    for name, receipt in receipts.items():
        if not isinstance(receipt, dict) or set(receipt) != fields:
            raise MnemoCortexLifecycleEvidenceError(f"invalid artifact receipt: {name}")
        try:
            compressed = base64.b64decode(
                receipt["content_gzip_base64"], validate=True
            )
            raw = gzip.decompress(compressed)
        except (TypeError, ValueError, OSError) as error:
            raise MnemoCortexLifecycleEvidenceError(
                f"cannot decode artifact: {name}"
            ) from error
        if (
            receipt["compression"] != "gzip-mtime-0"
            or receipt["compressed_size"] != len(compressed)
            or receipt["compressed_sha256"] != _sha(compressed)
            or receipt["raw_size"] != len(raw)
            or receipt["raw_sha256"] != _sha(raw)
        ):
            raise MnemoCortexLifecycleEvidenceError(f"artifact receipt drifted: {name}")
        decoded[name] = raw
    return decoded


def _validate_code(bundle: dict[str, Any], project_root: Path) -> None:
    receipts = bundle.get("code_files")
    if not isinstance(receipts, dict) or set(receipts) != CODE_PATHS:
        raise MnemoCortexLifecycleEvidenceError("Mnemo Cortex code roster drifted")
    for name, expected in receipts.items():
        path = project_root / name
        if (
            not isinstance(expected, str)
            or len(expected) != 64
            or path.is_symlink()
            or not path.is_file()
            or _sha(path.read_bytes()) != expected
        ):
            raise MnemoCortexLifecycleEvidenceError(
                f"Mnemo Cortex code drifted: {name}"
            )


def _validate_manifest(files: dict[str, bytes]) -> None:
    manifest = _object(files["manifest.json"], "Mnemo Cortex manifest")
    declared = manifest.get("files")
    if (
        _sha(files["manifest.json"]) != MANIFEST_SHA256
        or manifest.get("schema_version") != 1
        or manifest.get("status") != EXPECTED_STATUS
        or manifest.get("file_count") != len(MANIFEST_FILE_NAMES)
        or not isinstance(declared, dict)
        or set(declared) != MANIFEST_FILE_NAMES
        or declared.get("source.tar") != ARCHIVE_SHA256
        or manifest.get("report_sha256") != REPORT_SHA256
    ):
        raise MnemoCortexLifecycleEvidenceError("Mnemo Cortex manifest drifted")
    for name in ARTIFACT_NAMES - {"manifest.json"}:
        if declared.get(name) != _sha(files[name]):
            raise MnemoCortexLifecycleEvidenceError(f"manifest hash drifted: {name}")


def _validate_source(files: dict[str, bytes]) -> dict[str, Any]:
    source = _object(files["source-receipt.json"], "Mnemo Cortex source receipt")
    if (
        source.get("revision") != REVISION
        or source.get("tree") != TREE
        or source.get("archive_sha256") != ARCHIVE_SHA256
        or source.get("archive_bytes") != ARCHIVE_BYTES
        or source.get("static_source_checks")
        != {finding: True for finding in sorted(STATIC_FINDINGS)}
    ):
        raise MnemoCortexLifecycleEvidenceError("Mnemo Cortex source receipt drifted")
    return source


def _validate_image(files: dict[str, bytes]) -> None:
    try:
        rows = json.loads(files["doctor-image-inspect.json"])
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise MnemoCortexLifecycleEvidenceError(
            "Mnemo Cortex image inspection is invalid"
        ) from error
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise MnemoCortexLifecycleEvidenceError("Mnemo Cortex image roster drifted")
    image = rows[0]
    config = image.get("Config") or {}
    labels = config.get("Labels") or {}
    if (
        image.get("Id") != IMAGE_ID
        or image.get("Architecture") != "amd64"
        or image.get("Os") != "linux"
        or config.get("User") != "65532:65532"
        or set(config.get("Volumes") or {}) != {"/state"}
        or labels.get("org.opencontainers.image.revision") != REVISION
        or labels.get("org.cotcodec.source-tree") != TREE
        or labels.get("org.cotcodec.source-archive-sha256") != ARCHIVE_SHA256
        or labels.get("org.cotcodec.doctor-sha256") != _sha(files["doctor.py"])
        or labels.get("org.cotcodec.wheelhouse-manifest-sha256")
        != WHEELHOUSE_MANIFEST_SHA256
        or labels.get("org.cotcodec.requirements-sha256") != REQUIREMENTS_SHA256
        or labels.get("org.cotcodec.upstream-container-git") != "absent"
        or labels.get("org.cotcodec.discovery-only") != "true"
    ):
        raise MnemoCortexLifecycleEvidenceError(
            "Mnemo Cortex image provenance drifted"
        )


def _validate_phase_one(metrics: dict[str, Any], token: str) -> None:
    smart = metrics.get("smart_response") or {}
    raw = metrics.get("raw_response") or {}
    first = metrics.get("pending_after_first")
    second = metrics.get("pending_after_second")
    dream = metrics.get("dream_projection") or {}
    calls = dream.get("calls")
    routes = metrics.get("routes")
    if (
        smart.get("category_used") != "decision"
        or raw.get("category_used") != "session_log"
        or metrics.get("passport_first_status") != 500
        or metrics.get("passport_second_status") != 500
        or not isinstance(first, list)
        or len(first) != 1
        or not isinstance(second, list)
        or [row.get("observation_id") for row in second] != ["obs_001", "obs_002"]
        or len({row.get("proposed_claim") for row in second}) != 1
        or f"COTMC_PASSPORT_{token}" not in second[0].get("proposed_claim", "")
        or dream.get("result") != f"JOINT_{token}"
        or not isinstance(calls, list)
        or [row.get("kind") for row in calls] != ["per-agent", "per-agent", "rollup"]
        or [row.get("kind") for row in metrics.get("reasoning_calls", [])]
        != ["classification", "analyst"]
        or not isinstance(routes, list)
        or any(
            route in routes
            for route in (
                "/delete",
                "/forget",
                "/purge",
                "/memory/delete",
                "/memory/purge",
            )
        )
    ):
        raise MnemoCortexLifecycleEvidenceError(
            "Mnemo Cortex phase-one semantics drifted"
        )


def _validate_phase_two(metrics: dict[str, Any], token: str) -> None:
    rows = metrics.get("memory_rows")
    raw_ids = metrics.get("raw_memory_ids")
    default_chunks = (metrics.get("raw_default_context") or {}).get("chunks")
    drill_chunks = (metrics.get("raw_drill_context") or {}).get("chunks")
    pending = metrics.get("pending_after_restart")
    scan = metrics.get("current_file_scan")
    if (
        not isinstance(rows, list)
        or len(rows) != 3
        or sorted(row.get("category") for row in rows)
        != ["decision", "decision", "session_log"]
        or not isinstance(raw_ids, list)
        or len(raw_ids) != 1
        or not isinstance(default_chunks, list)
        or any(
            row.get("category") == "session_log"
            or row.get("memory_id") in raw_ids
            for row in default_chunks
        )
        or not isinstance(drill_chunks, list)
        or not any(
            row.get("category") == "session_log"
            and row.get("memory_id") in raw_ids
            for row in drill_chunks
        )
        or not isinstance(pending, list)
        or [row.get("observation_id") for row in pending] != ["obs_001", "obs_002"]
        or not isinstance(scan, dict)
        or set(scan)
        != {
            f"COTMC_SMART_{token}",
            f"COTMC_RAW_{token}",
            f"COTMC_ANALYST_{token}",
            f"COTMC_PASSPORT_{token}",
        }
        or not all(isinstance(paths, list) and paths for paths in scan.values())
    ):
        raise MnemoCortexLifecycleEvidenceError(
            "Mnemo Cortex phase-two semantics drifted"
        )


def _validate_repeat(files: dict[str, bytes], repeat: int) -> dict[str, Any]:
    payload = _object(files[f"repeat-{repeat}.json"], f"Mnemo Cortex repeat {repeat}")
    phases = payload.get("phases")
    token = payload.get("token")
    if (
        payload.get("repeat") != repeat
        or payload.get("phase_count") != 2
        or payload.get("fresh_process_restart_count") != 1
        or payload.get("simulated_reasoning_stage_calls") != 5
        or payload.get("external_model_calls") != 0
        or payload.get("stable_projection_sha256") != STABLE_PROJECTION_SHA256
        or not isinstance(token, str)
        or not TOKEN_RE.fullmatch(token)
        or not isinstance(phases, list)
        or len(phases) != 2
    ):
        raise MnemoCortexLifecycleEvidenceError(
            f"Mnemo Cortex repeat {repeat} identity drifted"
        )
    stable: list[dict[str, bool]] = []
    for index, phase in enumerate(phases, start=1):
        checks = phase.get("checks") if isinstance(phase, dict) else None
        if (
            not isinstance(phase, dict)
            or phase.get("phase") != index
            or phase.get("process_returncode") != 0
            or not isinstance(checks, dict)
            or set(checks) != PHASE_CHECKS[index - 1]
            or not all(value is True for value in checks.values())
            or not isinstance(phase.get("metrics"), dict)
        ):
            raise MnemoCortexLifecycleEvidenceError(
                f"Mnemo Cortex repeat {repeat} phase {index} drifted"
            )
        stable.append(checks)
        raw = files[f"repeat-{repeat}-phase-{index}.txt"]
        marker = b"COTCODEC_MNEMO_CORTEX_PHASE="
        markers = [
            line.split(marker, 1)[1] for line in raw.splitlines() if marker in line
        ]
        expected_marker = {
            key: value for key, value in phase.items() if key != "process_returncode"
        }
        if (
            len(markers) != 1
            or _object(markers[0], "Mnemo Cortex phase marker") != expected_marker
        ):
            raise MnemoCortexLifecycleEvidenceError(
                f"Mnemo Cortex repeat {repeat} marker drifted"
            )
    if (
        payload.get("stable_projection") != stable
        or _sha(json.dumps(stable, separators=(",", ":"), sort_keys=True).encode())
        != STABLE_PROJECTION_SHA256
    ):
        raise MnemoCortexLifecycleEvidenceError(
            f"Mnemo Cortex repeat {repeat} projection drifted"
        )
    _validate_phase_one(phases[0]["metrics"], token)
    _validate_phase_two(phases[1]["metrics"], token)
    return payload


def _validate_report(
    files: dict[str, bytes], repeats: list[dict[str, Any]]
) -> dict[str, Any]:
    report = _object(files["report.json"], "Mnemo Cortex report")
    expected_observed = {finding: True for finding in sorted(OBSERVED_FINDINGS)}
    runtime = report.get("runtime") or {}
    wheelhouse = report.get("wheelhouse") or {}
    if (
        _sha(files["report.json"]) != REPORT_SHA256
        or report.get("schema_version") != 1
        or report.get("status") != EXPECTED_STATUS
        or report.get("registered_expected_status") != EXPECTED_STATUS
        or report.get("registered_projection_matches") is not True
        or report.get("unexpected_checks") != []
        or report.get("observed_checks") != expected_observed
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("h100_admission") is not False
        or report.get("reproduced_in_two_clean_states") is not True
        or report.get("stable_projection_sha256") != STABLE_PROJECTION_SHA256
        or report.get("claim_boundary") != CLAIM_BOUNDARY
        or report.get("source")
        != _object(files["source-receipt.json"], "source receipt")
        or report.get("repeats") != repeats
        or runtime.get("slurm_job_id") != SLURM_JOB_ID
        or runtime.get("slurm_cpus_per_task") != "4"
        or runtime.get("slurm_mem_per_node") != "16384"
        or runtime.get("gpu_requested") is not False
        or runtime.get("provider_secrets") is not False
        or runtime.get("external_model_calls") != 0
        or runtime.get("docker_execution_network") != "none"
        or wheelhouse.get("manifest_sha256") != WHEELHOUSE_MANIFEST_SHA256
        or wheelhouse.get("requirements_sha256") != REQUIREMENTS_SHA256
        or wheelhouse.get("wheel_count") != 26
        or wheelhouse.get("total_wheel_bytes") != 23_917_516
        or wheelhouse.get("docker_build_network") != "none"
        or (report.get("image") or {}).get("image_id") != IMAGE_ID
    ):
        raise MnemoCortexLifecycleEvidenceError("Mnemo Cortex report drifted")
    return report


def validate_evidence(
    source: Path | dict[str, Any] = DEFAULT_OUTPUT,
    *,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Validate the self-contained bundle against exact code and run receipts."""
    if isinstance(source, Path):
        if source.is_symlink() or not source.is_file():
            raise MnemoCortexLifecycleEvidenceError(
                "Mnemo Cortex lifecycle evidence is missing"
            )
        bundle = _object(source.read_bytes(), "Mnemo Cortex lifecycle evidence")
    else:
        bundle = source
    expected_findings = {
        finding: True for finding in sorted(STATIC_FINDINGS | OBSERVED_FINDINGS)
    }
    if (
        bundle.get("schema_version") != 1
        or bundle.get("source_id") != "mnemo-cortex"
        or bundle.get("source_revision") != REVISION
        or bundle.get("source_revisions")
        != {"https://github.com/GuyMannDude/mnemo-cortex": REVISION}
        or bundle.get("source_tree") != TREE
        or bundle.get("evidence_kind") != "contained-native-lifecycle-negative"
        or bundle.get("evidence_grade") != "local-negative-reproduced"
        or bundle.get("status") != EXPECTED_STATUS
        or bundle.get("scientific_result") is not False
        or bundle.get("publication_ready") is not False
        or bundle.get("runtime_lane") != "slurm-cpu-amd64-docker-network-none"
        or bundle.get("slurm_job_id") != SLURM_JOB_ID
        or bundle.get("run_count") != 2
        or bundle.get("fresh_process_restart_count_per_run") != 1
        or bundle.get("stable_projection_sha256") != STABLE_PROJECTION_SHA256
        or bundle.get("report_sha256") != REPORT_SHA256
        or bundle.get("manifest_sha256") != MANIFEST_SHA256
        or bundle.get("wheelhouse_manifest_sha256")
        != WHEELHOUSE_MANIFEST_SHA256
        or bundle.get("requirements_sha256") != REQUIREMENTS_SHA256
        or bundle.get("claim_boundary") != CLAIM_BOUNDARY
        or bundle.get("h100_actor_admission") != "forbidden-for-this-revision"
        or bundle.get("findings") != expected_findings
        or bundle.get("source_archive")
        != {"bytes": ARCHIVE_BYTES, "sha256": ARCHIVE_SHA256, "embedded": False}
    ):
        raise MnemoCortexLifecycleEvidenceError(
            "Mnemo Cortex lifecycle evidence identity drifted"
        )
    _validate_code(bundle, project_root)
    files = _decode(bundle.get("artifact_files"))
    _validate_manifest(files)
    _validate_source(files)
    _validate_image(files)
    local_pairs = {
        "Dockerfile": "infra/memory-baselines/mnemo-cortex/Dockerfile",
        "doctor.py": "infra/memory-baselines/mnemo-cortex/doctor.py",
        "runner.py": "scripts/run_mnemo_cortex_lifecycle_doctor.py",
        "batch.sbatch": "infra/slurm/host-single-node/mnemo-cortex-lifecycle.sbatch",
        "wheelhouse-manifest.json": (
            "infra/memory-baselines/mnemo-cortex/wheelhouse-manifest.json"
        ),
    }
    for artifact, local in local_pairs.items():
        if files[artifact] != (project_root / local).read_bytes():
            raise MnemoCortexLifecycleEvidenceError(
                f"embedded Mnemo Cortex code drifted: {artifact}"
            )
    if _sha(files["wheelhouse-manifest.json"]) != WHEELHOUSE_MANIFEST_SHA256:
        raise MnemoCortexLifecycleEvidenceError("wheelhouse manifest drifted")
    if _sha(files["requirements-linux-x86_64-cp312.txt"]) != REQUIREMENTS_SHA256:
        raise MnemoCortexLifecycleEvidenceError("requirements receipt drifted")
    if set(files["pip-freeze.txt"].decode().splitlines()) != EXPECTED_FREEZE:
        raise MnemoCortexLifecycleEvidenceError("dependency freeze drifted")
    if files["git-probe.txt"] != b"":
        raise MnemoCortexLifecycleEvidenceError("Git absence probe drifted")
    experiment = yaml.safe_load(files["experiment.yaml"])
    if not isinstance(experiment, dict) or experiment != validate_experiment_contract():
        raise MnemoCortexLifecycleEvidenceError("embedded experiment drifted")
    repeats = [_validate_repeat(files, repeat) for repeat in (1, 2)]
    if repeats[0]["stable_projection"] != repeats[1]["stable_projection"]:
        raise MnemoCortexLifecycleEvidenceError(
            "Mnemo Cortex clean-state projections diverged"
        )
    _validate_report(files, repeats)
    return bundle


def _write_once(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        os.write(descriptor, data)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def seal(root: Path = DEFAULT_ROOT, output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    """Validate the retained directory and write one portable evidence bundle."""
    if root.is_symlink() or not root.is_dir():
        raise MnemoCortexLifecycleEvidenceError(
            "Mnemo Cortex lifecycle artifact root is missing"
        )
    actual = {path.name for path in root.iterdir() if path.is_file()}
    if actual != ARTIFACT_NAMES | {"source.tar"}:
        raise MnemoCortexLifecycleEvidenceError(
            "Mnemo Cortex lifecycle artifact directory drifted"
        )
    report = _object((root / "report.json").read_bytes(), "Mnemo Cortex report")
    source_receipt = _object(
        (root / "source-receipt.json").read_bytes(), "Mnemo Cortex source"
    )
    findings = {
        **source_receipt["static_source_checks"],
        **report["observed_checks"],
    }
    bundle = {
        "schema_version": 1,
        "source_id": "mnemo-cortex",
        "source_revision": REVISION,
        "source_revisions": {
            "https://github.com/GuyMannDude/mnemo-cortex": REVISION
        },
        "source_tree": TREE,
        "evidence_kind": "contained-native-lifecycle-negative",
        "evidence_grade": "local-negative-reproduced",
        "status": EXPECTED_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "runtime_lane": "slurm-cpu-amd64-docker-network-none",
        "slurm_job_id": SLURM_JOB_ID,
        "run_count": 2,
        "fresh_process_restart_count_per_run": 1,
        "stable_projection_sha256": STABLE_PROJECTION_SHA256,
        "report_sha256": REPORT_SHA256,
        "manifest_sha256": MANIFEST_SHA256,
        "wheelhouse_manifest_sha256": WHEELHOUSE_MANIFEST_SHA256,
        "requirements_sha256": REQUIREMENTS_SHA256,
        "claim_boundary": CLAIM_BOUNDARY,
        "h100_actor_admission": "forbidden-for-this-revision",
        "findings": findings,
        "source_archive": {
            "bytes": ARCHIVE_BYTES,
            "sha256": ARCHIVE_SHA256,
            "embedded": False,
        },
        "code_files": {
            name: _sha((PROJECT_ROOT / name).read_bytes()) for name in CODE_PATHS
        },
        "artifact_files": {
            name: _capture(root / name) for name in sorted(ARTIFACT_NAMES)
        },
        "current_file_plaintext_paths": [
            repeat["phases"][1]["metrics"]["current_file_scan"]
            for repeat in report["repeats"]
        ],
    }
    validate_evidence(bundle)
    _write_once(output, (json.dumps(bundle, indent=2, sort_keys=True) + "\n").encode())
    return bundle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        validate_evidence(args.output)
        print("Mnemo Cortex native lifecycle evidence PASS")
    else:
        bundle = seal(args.root, args.output)
        print(json.dumps({"output": str(args.output), "status": bundle["status"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
