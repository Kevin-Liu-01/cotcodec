#!/usr/bin/env python3
"""Validate the retained two-repeat Agent Recall scoped-lifecycle negative."""

from __future__ import annotations

import hashlib
import json
import tarfile
from io import BytesIO
from pathlib import Path
from typing import Any

EXPECTED_STATUS = (
    "BLOCKED_CROSS_SCOPE_DESTRUCTIVE_DELETE_STALE_CHILD_BRIEFING_AND_"
    "SOFT_DELETE_RESIDUE"
)
EXPECTED_REVISION = "dcf21b5cc9691e1371299917e2e474fb82e07cab"
EXPECTED_TREE = "1c0395b24d2d9f45d04443f7f187b026ce41f43b"
EXPECTED_SOURCE_SHA256 = (
    "f1412268b653e971df41c730bd4d1aa19cb0e20e79f358c4c41c8ec80350a06a"
)
EXPECTED_IMAGE_ID = (
    "sha256:3891f21f20cebb58b7faea07ee86f30d22570a8b8a9c0902b82d1b36f4b115a0"
)
EXPECTED_PROJECTION = (
    "2fed18f7943ef6e96ce343ee665c31b90c03f1115eb6ddf0a807989abddcc5a3"
)
EXPECTED_CLAIM_BOUNDARY = (
    "Exact pinned native scope precedence, bitemporal correction, delete, "
    "cache-invalidation, and restart behavior; not retrieval quality, "
    "active/inactive paging, model-effect, H100-actor, or publication evidence."
)
EXPECTED_FINDINGS = {
    "bitemporal_history_survived_restart",
    "bitemporal_history_written",
    "child_inherits_parent_scope",
    "cross_scope_delete_cascades_other_scope",
    "cross_scope_delete_survived_restart",
    "delete_observations_archives_plaintext",
    "entity_delete_is_unscoped_row_delete",
    "native_scoped_purge_absent",
    "observation_delete_is_soft_archive",
    "parent_change_leaves_child_cache_fresh",
    "parent_scope_invalidation_omits_descendants",
    "scope_precedence_local_wins",
    "scope_precedence_survived_restart",
    "soft_deleted_observation_survived_restart",
    "soft_deleted_plaintext_in_database",
}
EXPECTED_ARTIFACTS = {
    "Dockerfile",
    "doctor-image-inspect.json",
    "doctor.py",
    "experiment.yaml",
    "manifest.json",
    "repeat-1-phase-1.txt",
    "repeat-1-phase-2.txt",
    "repeat-1.json",
    "repeat-2-phase-1.txt",
    "repeat-2-phase-2.txt",
    "repeat-2.json",
    "report.json",
    "source-receipt.json",
    "source.tar",
}


class AgentRecallEvidenceError(ValueError):
    """Raised when retained Agent Recall evidence drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _object(data: bytes, owner: str) -> dict[str, Any]:
    def reject(value: str) -> None:
        raise AgentRecallEvidenceError(f"{owner}: non-finite JSON {value}")

    try:
        payload = json.loads(data, parse_constant=reject)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AgentRecallEvidenceError(f"{owner}: invalid JSON") from exc
    if not isinstance(payload, dict):
        raise AgentRecallEvidenceError(f"{owner}: expected object")
    return payload


def _files(
    bundle: dict[str, Any], project_root: Path
) -> tuple[dict[str, bytes], Path]:
    receipts = bundle.get("artifact_files")
    if not isinstance(receipts, dict) or set(receipts) != EXPECTED_ARTIFACTS:
        raise AgentRecallEvidenceError("artifact roster drifted")
    value = bundle.get("artifact_root")
    if (
        not isinstance(value, str)
        or not value
        or Path(value).is_absolute()
        or ".." in Path(value).parts
    ):
        raise AgentRecallEvidenceError("artifact root is unsafe")
    root = project_root / value
    if root.is_symlink() or not root.is_dir():
        raise AgentRecallEvidenceError("artifact root is missing")
    actual = {path.name for path in root.iterdir() if path.is_file()}
    if actual != EXPECTED_ARTIFACTS:
        raise AgentRecallEvidenceError("artifact directory roster drifted")
    files: dict[str, bytes] = {}
    for name, expected in receipts.items():
        path = root / name
        if (
            not isinstance(expected, str)
            or len(expected) != 64
            or path.is_symlink()
            or not path.is_file()
        ):
            raise AgentRecallEvidenceError(f"artifact {name} is invalid")
        data = path.read_bytes()
        if _sha(data) != expected:
            raise AgentRecallEvidenceError(f"artifact {name} drifted")
        files[name] = data
    return files, root


def _validate_source(files: dict[str, bytes]) -> None:
    receipt = _object(files["source-receipt.json"], "source receipt")
    if receipt != {
        "archive_bytes": 552960,
        "archive_sha256": EXPECTED_SOURCE_SHA256,
        "git_sha": EXPECTED_REVISION,
        "git_tree": EXPECTED_TREE,
        "license_sha256": (
            "0c51e5594c40bfe9e039ff0925d3efff5cb83402f21e5d466250958e724ff6c6"
        ),
        "pyproject_sha256": (
            "9272395436cbcba0b6e537bf26d45c4cbe7593560bfb83309c46fb963acfc70f"
        ),
        "source_checks": {
            "entity_delete_is_unscoped_row_delete": True,
            "observation_delete_is_soft_archive": True,
            "parent_scope_invalidation_omits_descendants": True,
        },
    } or _sha(files["source.tar"]) != EXPECTED_SOURCE_SHA256:
        raise AgentRecallEvidenceError("source receipt drifted")
    try:
        with tarfile.open(fileobj=BytesIO(files["source.tar"]), mode="r:") as archive:
            members = archive.getmembers()
    except tarfile.TarError as exc:
        raise AgentRecallEvidenceError("source archive is invalid") from exc
    names = {member.name for member in members}
    required = {
        "LICENSE",
        "pyproject.toml",
        "agent_recall/store.py",
        "agent_recall/hierarchy.py",
        "agent_recall/mcp_bridge.py",
        "agent_recall/context_gen/cache.py",
    }
    if not required.issubset(names) or any(
        name.startswith("/") or ".." in Path(name).parts for name in names
    ):
        raise AgentRecallEvidenceError("source archive roster is unsafe or incomplete")


def _validate_runtime(files: dict[str, bytes]) -> None:
    try:
        rows = json.loads(files["doctor-image-inspect.json"])
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AgentRecallEvidenceError("doctor image inspection is invalid") from exc
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise AgentRecallEvidenceError("doctor image inspection roster drifted")
    image = rows[0]
    config = image.get("Config") or {}
    labels = config.get("Labels") or {}
    if (
        image.get("Id") != EXPECTED_IMAGE_ID
        or image.get("Architecture") != "arm64"
        or image.get("Os") != "linux"
        or config.get("User") != "65532:65532"
        or set(config.get("Volumes") or {}) != {"/state"}
        or labels.get("org.opencontainers.image.revision") != EXPECTED_REVISION
        or labels.get("org.cotcodec.source-tree") != EXPECTED_TREE
        or labels.get("org.cotcodec.source-archive-sha256")
        != EXPECTED_SOURCE_SHA256
        or labels.get("org.cotcodec.discovery-only") != "true"
        or labels.get("org.cotcodec.doctor-sha256") != _sha(files["doctor.py"])
    ):
        raise AgentRecallEvidenceError("doctor image provenance drifted")


def _phase_projection(repeat: dict[str, Any]) -> list[dict[str, Any]]:
    phases = repeat.get("phases")
    if not isinstance(phases, list) or [row.get("phase") for row in phases] != [1, 2]:
        raise AgentRecallEvidenceError("phase roster drifted")
    for row in phases:
        if not isinstance(row, dict) or not all(
            value is True for key, value in row.items() if key != "phase"
        ):
            raise AgentRecallEvidenceError("phase check failed")
    return phases


def _validate_reports(files: dict[str, bytes]) -> None:
    first = _object(files["repeat-1.json"], "repeat 1")
    second = _object(files["repeat-2.json"], "repeat 2")
    first_phases = _phase_projection(first)
    second_phases = _phase_projection(second)
    if (
        first.get("repeat") != 1
        or second.get("repeat") != 2
        or first_phases != second_phases
        or first.get("phase_projection_sha256") != EXPECTED_PROJECTION
        or second.get("phase_projection_sha256") != EXPECTED_PROJECTION
        or _sha(
            json.dumps(first_phases, separators=(",", ":"), sort_keys=True).encode()
        )
        != EXPECTED_PROJECTION
    ):
        raise AgentRecallEvidenceError("clean-state phase reports diverged")
    findings = {
        key: value
        for phase in first_phases
        for key, value in phase.items()
        if key != "phase"
    }
    findings.update(
        {
            "entity_delete_is_unscoped_row_delete": True,
            "observation_delete_is_soft_archive": True,
            "parent_scope_invalidation_omits_descendants": True,
        }
    )
    if set(findings) != EXPECTED_FINDINGS or not all(findings.values()):
        raise AgentRecallEvidenceError("finding roster drifted")
    report = _object(files["report.json"], "report")
    if (
        report.get("status") != EXPECTED_STATUS
        or report.get("run_count") != 2
        or report.get("fresh_process_restart_count_per_run") != 1
        or report.get("stable_phase_projection_sha256") != EXPECTED_PROJECTION
        or report.get("h100_actor_admission") != "forbidden-for-this-revision"
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("claim_boundary") != EXPECTED_CLAIM_BOUNDARY
        or report.get("findings") != findings
        or report.get("source")
        != _object(files["source-receipt.json"], "source receipt")
    ):
        raise AgentRecallEvidenceError("summary semantics drifted")


def validate_agent_recall_lifecycle_evidence(
    bundle_or_path: dict[str, Any] | Path,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    if isinstance(bundle_or_path, Path):
        bundle = _object(bundle_or_path.read_bytes(), "Agent Recall evidence")
        root = project_root or bundle_or_path.resolve().parents[3]
    else:
        bundle = bundle_or_path
        if project_root is None:
            raise AgentRecallEvidenceError("project_root is required")
        root = project_root
    if (
        bundle.get("schema_version") != 1
        or bundle.get("source_id") != "agent-recall"
        or bundle.get("source_revisions")
        != {"https://github.com/mnardit/agent-recall": EXPECTED_REVISION}
        or bundle.get("evidence_kind")
        != "contained-native-scoped-lifecycle-negative"
        or bundle.get("evidence_grade") != "local-negative-reproduced"
        or bundle.get("status") != EXPECTED_STATUS
        or bundle.get("scientific_result") is not False
        or bundle.get("publication_ready") is not False
        or bundle.get("runtime_lane") != "local-arm64-docker-network-none"
        or bundle.get("run_count") != 2
        or bundle.get("fresh_process_restart_count_per_run") != 1
        or bundle.get("stable_phase_projection_sha256") != EXPECTED_PROJECTION
        or bundle.get("claim_boundary") != EXPECTED_CLAIM_BOUNDARY
        or bundle.get("h100_actor_admission") != "forbidden-for-this-revision"
        or bundle.get("findings")
        != {finding: True for finding in sorted(EXPECTED_FINDINGS)}
    ):
        raise AgentRecallEvidenceError("Agent Recall evidence identity drifted")
    code_files = bundle.get("code_files")
    if not isinstance(code_files, dict) or not code_files:
        raise AgentRecallEvidenceError("code receipt roster is missing")
    for name, expected in code_files.items():
        path = root / name
        if (
            not isinstance(expected, str)
            or len(expected) != 64
            or path.is_symlink()
            or not path.is_file()
            or _sha(path.read_bytes()) != expected
        ):
            raise AgentRecallEvidenceError(f"code receipt drifted: {name}")
    files, _ = _files(bundle, root)
    _validate_source(files)
    _validate_runtime(files)
    _validate_reports(files)
    manifest = _object(files["manifest.json"], "manifest")
    expected_manifest_files = {
        name: digest
        for name, digest in bundle["artifact_files"].items()
        if name != "manifest.json"
    }
    if (
        manifest.get("schema_version") != 1
        or manifest.get("status") != EXPECTED_STATUS
        or manifest.get("file_count") != len(expected_manifest_files)
        or manifest.get("files") != expected_manifest_files
    ):
        raise AgentRecallEvidenceError("artifact manifest drifted")
    return bundle


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    path = root / "research/evidence/memory/agent-recall-scope-lifecycle-negative-v1.json"
    evidence = validate_agent_recall_lifecycle_evidence(path, project_root=root)
    print(evidence["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
