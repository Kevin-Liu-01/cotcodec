#!/usr/bin/env python3
"""Validate the retained two-repeat Active Graph lifecycle negative."""

from __future__ import annotations

import hashlib
import json
import tarfile
from io import BytesIO
from pathlib import Path
from typing import Any

EXPECTED_STATUS = "BLOCKED_ARCHIVE_ONLY_RETENTION_NO_SCOPED_PURGE_AND_SHARED_DB_ERASURE"
EXPECTED_REVISION = "8aedb1866cf5dce056af97529152ffd6f468a1ed"
EXPECTED_TREE = "8f101d35376f5ef12f197b34a27a2c5aa80ac584"
EXPECTED_SOURCE_SHA256 = "91e0f4099336d34fdb60aee6d9c134ba8f91a2b358d1f46548501353e448461a"
EXPECTED_IMAGE_ID = "sha256:59fb38ce501a861d1670b1cc385e77d83c5f55fdf6567053ea71cd0a9c10acaf"
EXPECTED_PROJECTION = "bc1be630657d7629ce35975b0387f4e34968c8eb79c3a18f7ca838fd204940a1"
EXPECTED_CLAIM_BOUNDARY = (
    "Exact pinned native fork, nested-fork, replay, retirement, archive, restart, "
    "and plaintext-residue behavior; not retrieval quality, active/inactive paging, "
    "model-effect, H100-actor, or publication evidence."
)
EXPECTED_FINDINGS = {
    "archive_run_moves_rows_not_erases",
    "native_scoped_purge_absent",
    "nested_fork_isolated",
    "nested_fork_restart_isolated",
    "parent_fork_divergence",
    "parent_fork_restart_isolated",
    "rejected_archive_contains_canary",
    "rejected_run_active_log_empty",
    "rejected_run_archive_survived_restart",
    "rejected_run_metadata_survived_restart",
    "rejected_run_moved_to_archive",
    "rejected_run_plaintext_survived_restart",
    "rejected_run_retire_idempotent",
    "retention_contract_is_archive_never_delete",
    "retire_calls_archive_run",
}
EXPECTED_ARTIFACTS = {
    "Dockerfile", "doctor-image-inspect.json", "doctor.py", "experiment.yaml",
    "manifest.json", "repeat-1-phase-1.txt", "repeat-1-phase-2.txt",
    "repeat-1.json", "repeat-2-phase-1.txt", "repeat-2-phase-2.txt",
    "repeat-2.json", "report.json", "source-receipt.json", "source.tar",
}


class ActiveGraphEvidenceError(ValueError):
    """Raised when retained Active Graph evidence drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _object(data: bytes, owner: str) -> dict[str, Any]:
    def reject(value: str) -> None:
        raise ActiveGraphEvidenceError(f"{owner}: non-finite JSON {value}")

    try:
        payload = json.loads(data, parse_constant=reject)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ActiveGraphEvidenceError(f"{owner}: invalid JSON") from exc
    if not isinstance(payload, dict):
        raise ActiveGraphEvidenceError(f"{owner}: expected object")
    return payload


def _artifact_files(bundle: dict[str, Any], project_root: Path) -> dict[str, bytes]:
    receipts = bundle.get("artifact_files")
    if not isinstance(receipts, dict) or set(receipts) != EXPECTED_ARTIFACTS:
        raise ActiveGraphEvidenceError("artifact roster drifted")
    value = bundle.get("artifact_root")
    if (
        not isinstance(value, str)
        or not value
        or Path(value).is_absolute()
        or ".." in Path(value).parts
    ):
        raise ActiveGraphEvidenceError("artifact root is unsafe")
    root = project_root / value
    if root.is_symlink() or not root.is_dir():
        raise ActiveGraphEvidenceError("artifact root is missing")
    actual = {path.name for path in root.iterdir() if path.is_file()}
    if actual != EXPECTED_ARTIFACTS:
        raise ActiveGraphEvidenceError("artifact directory roster drifted")
    files: dict[str, bytes] = {}
    for name, expected in receipts.items():
        path = root / name
        if (
            not isinstance(expected, str)
            or len(expected) != 64
            or path.is_symlink()
            or not path.is_file()
        ):
            raise ActiveGraphEvidenceError(f"artifact {name} is invalid")
        data = path.read_bytes()
        if _sha(data) != expected:
            raise ActiveGraphEvidenceError(f"artifact {name} drifted")
        files[name] = data
    return files


def _validate_source(files: dict[str, bytes]) -> None:
    receipt = _object(files["source-receipt.json"], "source receipt")
    if receipt != {
        "archive_bytes": 3737600,
        "archive_sha256": EXPECTED_SOURCE_SHA256,
        "git_sha": EXPECTED_REVISION,
        "git_tree": EXPECTED_TREE,
        "license_sha256": "fbb7ac8857b6ce4b826937908e73d96bdc20cbdbbcbad1836f20c6543266b36f",
        "pyproject_sha256": "a1ee2296e45138abacb1a6c557fc2f1f9e39c7b63a2e95364d84a5fbc8f90768",
        "source_checks": {
            "archive_run_moves_rows_not_erases": True,
            "retention_contract_is_archive_never_delete": True,
            "retire_calls_archive_run": True,
        },
    } or _sha(files["source.tar"]) != EXPECTED_SOURCE_SHA256:
        raise ActiveGraphEvidenceError("source receipt drifted")
    try:
        with tarfile.open(fileobj=BytesIO(files["source.tar"]), mode="r:") as archive:
            members = archive.getmembers()
    except tarfile.TarError as exc:
        raise ActiveGraphEvidenceError("source archive is invalid") from exc
    names = {member.name for member in members}
    required = {
        "LICENSE", "pyproject.toml", "activegraph/runtime/runtime.py",
        "activegraph/store/sqlite.py", "activegraph/store/retention.py",
    }
    if not required.issubset(names) or any(
        name.startswith("/") or ".." in Path(name).parts for name in names
    ):
        raise ActiveGraphEvidenceError("source archive roster is unsafe or incomplete")


def _validate_runtime(files: dict[str, bytes]) -> None:
    try:
        rows = json.loads(files["doctor-image-inspect.json"])
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ActiveGraphEvidenceError("doctor image inspection is invalid") from exc
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise ActiveGraphEvidenceError("doctor image inspection roster drifted")
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
        or labels.get("org.cotcodec.doctor-sha256") != _sha(files["doctor.py"])
    ):
        raise ActiveGraphEvidenceError("doctor image provenance drifted")


def _phase_projection(repeat: dict[str, Any]) -> list[dict[str, Any]]:
    phases = repeat.get("phases")
    if not isinstance(phases, list) or [row.get("phase") for row in phases] != [1, 2]:
        raise ActiveGraphEvidenceError("phase roster drifted")
    for row in phases:
        if not isinstance(row, dict) or not all(
            value is True for key, value in row.items() if key != "phase"
        ):
            raise ActiveGraphEvidenceError("phase check failed")
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
        or _sha(json.dumps(first_phases, separators=(",", ":"), sort_keys=True).encode())
        != EXPECTED_PROJECTION
    ):
        raise ActiveGraphEvidenceError("clean-state phase reports diverged")
    findings = {
        key: value
        for phase in first_phases
        for key, value in phase.items()
        if key != "phase"
    }
    findings.update({
        "archive_run_moves_rows_not_erases": True,
        "retention_contract_is_archive_never_delete": True,
        "retire_calls_archive_run": True,
    })
    if set(findings) != EXPECTED_FINDINGS or not all(findings.values()):
        raise ActiveGraphEvidenceError("finding roster drifted")
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
        or report.get("source") != _object(files["source-receipt.json"], "source receipt")
    ):
        raise ActiveGraphEvidenceError("summary semantics drifted")


def validate_activegraph_lifecycle_evidence(
    bundle_or_path: dict[str, Any] | Path,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    if isinstance(bundle_or_path, Path):
        bundle = _object(bundle_or_path.read_bytes(), "Active Graph evidence")
        root = project_root or bundle_or_path.resolve().parents[3]
    else:
        bundle = bundle_or_path
        if project_root is None:
            raise ActiveGraphEvidenceError("project_root is required")
        root = project_root
    if (
        bundle.get("schema_version") != 1
        or bundle.get("source_id") != "activegraph-event-sourced-runtime"
        or bundle.get("source_revisions")
        != {"https://github.com/yoheinakajima/activegraph": EXPECTED_REVISION}
        or bundle.get("evidence_kind") != "contained-native-fork-lifecycle-negative"
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
        raise ActiveGraphEvidenceError("Active Graph evidence identity drifted")
    code_files = bundle.get("code_files")
    if not isinstance(code_files, dict) or not code_files:
        raise ActiveGraphEvidenceError("code receipt roster is missing")
    for name, expected in code_files.items():
        path = root / name
        if (
            not isinstance(expected, str)
            or len(expected) != 64
            or path.is_symlink()
            or not path.is_file()
            or _sha(path.read_bytes()) != expected
        ):
            raise ActiveGraphEvidenceError(f"code receipt drifted: {name}")
    files = _artifact_files(bundle, root)
    _validate_source(files)
    _validate_runtime(files)
    _validate_reports(files)
    manifest = _object(files["manifest.json"], "manifest")
    expected_manifest_files = {
        name: digest for name, digest in bundle["artifact_files"].items()
        if name != "manifest.json"
    }
    if (
        manifest.get("schema_version") != 1
        or manifest.get("status") != EXPECTED_STATUS
        or manifest.get("file_count") != len(expected_manifest_files)
        or manifest.get("files") != expected_manifest_files
    ):
        raise ActiveGraphEvidenceError("artifact manifest drifted")
    return bundle


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    path = root / "research/evidence/memory/activegraph-fork-lifecycle-negative-v1.json"
    evidence = validate_activegraph_lifecycle_evidence(path, project_root=root)
    print(evidence["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
