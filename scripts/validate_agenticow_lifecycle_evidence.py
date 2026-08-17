#!/usr/bin/env python3
"""Validate the retained two-repeat agenticow branch-lifecycle negative."""

from __future__ import annotations

import hashlib
import json
import tarfile
from io import BytesIO
from pathlib import Path
from typing import Any

EXPECTED_STATUS = (
    "BLOCKED_BLIND_PROMOTION_LOST_UPDATE_TOMBSTONE_RESIDUE_AND_NO_SCOPED_PURGE"
)
EXPECTED_REVISION = "dd4f437b92d2dbbc1f40dfa00023eed6e9c3bd84"
EXPECTED_TREE = "b64b6fae03aac0491e3d3b78281b5c6997516ebf"
EXPECTED_SOURCE_SHA256 = "a563784a4c7645f51a45ab430c7c8d3aec77b61cad609585389173da21bdfeac"
EXPECTED_IMAGE_ID = "sha256:b36438eed60b23c0e95f8a69c4cccbde930ea495c059a423c8062b73b7938ef3"
EXPECTED_PROJECTION = "eeb24984a901d4bcb2982eab89af6c9a85c5a07ce8db6ce8ca640e5942709571"
EXPECTED_CLAIM_BOUNDARY = (
    "Exact pinned native branch, nested-fork, checkpoint, rollback, promotion, "
    "save/load, tombstone, restart, and plaintext-residue behavior; not memory "
    "quality, active/inactive paging, model-effect, H100-actor, or publication evidence."
)
EXPECTED_FINDINGS = {
    "branch_isolation", "branch_isolation_survived_restart",
    "branch_text_payloads_survived_restart", "checkpoint_poison_visible_before_rollback",
    "checkpoint_rollback_removed_poison", "delete_is_tombstone_over_ancestor",
    "manifest_persists_text_for_every_node", "native_scoped_purge_absent",
    "nested_fork_isolation", "nested_fork_isolation_survived_restart",
    "parent_later_update_existed_before_promotion", "promoted_child_value_survived_restart",
    "promotion_blindly_overwrites_later_parent_update", "promotion_has_no_conflict_guard",
    "repeated_promotion_logically_idempotent", "sibling_still_sees_tombstoned_ancestor",
    "sibling_visibility_survived_restart", "tombstone_masks_ancestor",
    "tombstone_survived_restart", "tombstoned_plaintext_survived_restart",
}
EXPECTED_ARTIFACTS = {
    "Dockerfile", "doctor-image-inspect.json", "doctor.mjs", "experiment.yaml",
    "manifest.json", "repeat-1-phase-1.txt", "repeat-1-phase-2.txt",
    "repeat-1.json", "repeat-2-phase-1.txt", "repeat-2-phase-2.txt",
    "repeat-2.json", "report.json", "source-receipt.json", "source.tar",
}


class AgenticowEvidenceError(ValueError):
    """Raised when retained agenticow evidence drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _object(data: bytes, owner: str) -> dict[str, Any]:
    def reject(value: str) -> None:
        raise AgenticowEvidenceError(f"{owner}: non-finite JSON {value}")

    try:
        payload = json.loads(data, parse_constant=reject)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AgenticowEvidenceError(f"{owner}: invalid JSON") from exc
    if not isinstance(payload, dict):
        raise AgenticowEvidenceError(f"{owner}: expected object")
    return payload


def _artifact_files(bundle: dict[str, Any], project_root: Path) -> dict[str, bytes]:
    receipts = bundle.get("artifact_files")
    if not isinstance(receipts, dict) or set(receipts) != EXPECTED_ARTIFACTS:
        raise AgenticowEvidenceError("artifact roster drifted")
    value = bundle.get("artifact_root")
    if (
        not isinstance(value, str) or not value or Path(value).is_absolute()
        or ".." in Path(value).parts
    ):
        raise AgenticowEvidenceError("artifact root is unsafe")
    root = project_root / value
    if root.is_symlink() or not root.is_dir():
        raise AgenticowEvidenceError("artifact root is missing")
    if {path.name for path in root.iterdir() if path.is_file()} != EXPECTED_ARTIFACTS:
        raise AgenticowEvidenceError("artifact directory roster drifted")
    files: dict[str, bytes] = {}
    for name, expected in receipts.items():
        path = root / name
        if (
            not isinstance(expected, str) or len(expected) != 64
            or path.is_symlink() or not path.is_file()
        ):
            raise AgenticowEvidenceError(f"artifact {name} is invalid")
        data = path.read_bytes()
        if _sha(data) != expected:
            raise AgenticowEvidenceError(f"artifact {name} drifted")
        files[name] = data
    return files


def _validate_source(files: dict[str, bytes]) -> None:
    receipt = _object(files["source-receipt.json"], "source receipt")
    if receipt != {
        "archive_bytes": 6983680,
        "archive_sha256": EXPECTED_SOURCE_SHA256,
        "git_sha": EXPECTED_REVISION,
        "git_tree": EXPECTED_TREE,
        "license_sha256": "631f94984f626818d42ecf717aa6e8e0afd4f9f355ca706bd2effafbd1416d06",
        "package_lock_sha256": "3a567fe53f577b56101b5410398b181c4ed2750fd29708ac36dc2f6189982129",
        "source_checks": {
            "delete_is_tombstone_over_ancestor": True,
            "manifest_persists_text_for_every_node": True,
            "promotion_has_no_conflict_guard": True,
        },
    } or _sha(files["source.tar"]) != EXPECTED_SOURCE_SHA256:
        raise AgenticowEvidenceError("source receipt drifted")
    try:
        with tarfile.open(fileobj=BytesIO(files["source.tar"]), mode="r:") as archive:
            members = archive.getmembers()
    except tarfile.TarError as exc:
        raise AgenticowEvidenceError("source archive is invalid") from exc
    names = {member.name for member in members}
    required = {"LICENSE", "package.json", "package-lock.json", "src/index.js"}
    if not required.issubset(names) or any(
        name.startswith("/") or ".." in Path(name).parts for name in names
    ):
        raise AgenticowEvidenceError("source archive roster is unsafe or incomplete")


def _validate_runtime(files: dict[str, bytes]) -> None:
    try:
        rows = json.loads(files["doctor-image-inspect.json"])
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AgenticowEvidenceError("doctor image inspection is invalid") from exc
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise AgenticowEvidenceError("doctor image inspection roster drifted")
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
        or labels.get("org.cotcodec.source-archive-sha256") != EXPECTED_SOURCE_SHA256
        or labels.get("org.cotcodec.discovery-only") != "true"
        or labels.get("org.cotcodec.doctor-sha256") != _sha(files["doctor.mjs"])
    ):
        raise AgenticowEvidenceError("doctor image provenance drifted")


def _phases(repeat: dict[str, Any]) -> list[dict[str, Any]]:
    phases = repeat.get("phases")
    if not isinstance(phases, list) or [row.get("phase") for row in phases] != [1, 2]:
        raise AgenticowEvidenceError("phase roster drifted")
    if any(
        not isinstance(row, dict)
        or not all(value is True for key, value in row.items() if key != "phase")
        for row in phases
    ):
        raise AgenticowEvidenceError("phase check failed")
    return phases


def _validate_reports(files: dict[str, bytes]) -> None:
    first = _object(files["repeat-1.json"], "repeat 1")
    second = _object(files["repeat-2.json"], "repeat 2")
    first_phases, second_phases = _phases(first), _phases(second)
    if (
        first.get("repeat") != 1 or second.get("repeat") != 2
        or first_phases != second_phases
        or first.get("phase_projection_sha256") != EXPECTED_PROJECTION
        or second.get("phase_projection_sha256") != EXPECTED_PROJECTION
        or _sha(json.dumps(first_phases, separators=(",", ":"), sort_keys=True).encode())
        != EXPECTED_PROJECTION
    ):
        raise AgenticowEvidenceError("clean-state phase reports diverged")
    findings = {
        key: value for phase in first_phases for key, value in phase.items()
        if key != "phase"
    }
    findings.update({
        "delete_is_tombstone_over_ancestor": True,
        "manifest_persists_text_for_every_node": True,
        "promotion_has_no_conflict_guard": True,
    })
    if set(findings) != EXPECTED_FINDINGS or not all(findings.values()):
        raise AgenticowEvidenceError("finding roster drifted")
    report = _object(files["report.json"], "report")
    if (
        report.get("status") != EXPECTED_STATUS or report.get("run_count") != 2
        or report.get("fresh_process_restart_count_per_run") != 1
        or report.get("stable_phase_projection_sha256") != EXPECTED_PROJECTION
        or report.get("h100_actor_admission") != "forbidden-for-this-revision"
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("claim_boundary") != EXPECTED_CLAIM_BOUNDARY
        or report.get("findings") != findings
        or report.get("source") != _object(files["source-receipt.json"], "source receipt")
    ):
        raise AgenticowEvidenceError("summary semantics drifted")


def validate_agenticow_lifecycle_evidence(
    bundle_or_path: dict[str, Any] | Path,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    if isinstance(bundle_or_path, Path):
        bundle = _object(bundle_or_path.read_bytes(), "agenticow evidence")
        root = project_root or bundle_or_path.resolve().parents[3]
    else:
        bundle = bundle_or_path
        if project_root is None:
            raise AgenticowEvidenceError("project_root is required")
        root = project_root
    if (
        bundle.get("schema_version") != 1 or bundle.get("source_id") != "agenticow"
        or bundle.get("source_revisions")
        != {"https://github.com/ruvnet/agenticow": EXPECTED_REVISION}
        or bundle.get("evidence_kind") != "contained-native-branch-lifecycle-negative"
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
        or bundle.get("findings") != {finding: True for finding in sorted(EXPECTED_FINDINGS)}
    ):
        raise AgenticowEvidenceError("agenticow evidence identity drifted")
    code_files = bundle.get("code_files")
    if not isinstance(code_files, dict) or not code_files:
        raise AgenticowEvidenceError("code receipt roster is missing")
    for name, expected in code_files.items():
        path = root / name
        if (
            not isinstance(expected, str) or len(expected) != 64
            or path.is_symlink() or not path.is_file() or _sha(path.read_bytes()) != expected
        ):
            raise AgenticowEvidenceError(f"code receipt drifted: {name}")
    files = _artifact_files(bundle, root)
    _validate_source(files)
    _validate_runtime(files)
    _validate_reports(files)
    manifest = _object(files["manifest.json"], "manifest")
    expected_files = {
        name: digest for name, digest in bundle["artifact_files"].items()
        if name != "manifest.json"
    }
    if (
        manifest.get("schema_version") != 1 or manifest.get("status") != EXPECTED_STATUS
        or manifest.get("file_count") != len(expected_files)
        or manifest.get("files") != expected_files
    ):
        raise AgenticowEvidenceError("artifact manifest drifted")
    return bundle


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    path = root / "research/evidence/memory/agenticow-branch-lifecycle-negative-v1.json"
    evidence = validate_agenticow_lifecycle_evidence(path, project_root=root)
    print(evidence["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
