#!/usr/bin/env python3
"""Validate the retained two-repeat Memoria transactional-lifecycle negative."""

from __future__ import annotations

import hashlib
import json
import tarfile
from io import BytesIO
from pathlib import Path
from typing import Any

EXPECTED_STATUS = (
    "BLOCKED_SHARED_TABLE_BRANCH_EXPOSURE_SOFT_PURGE_RESIDUE_AND_NONATOMIC_ROLLBACK"
)
EXPECTED_REVISION = "efd3d6515969971dfa894737272b8317bcb643e7"
EXPECTED_TREE = "c07d7b427a9d664d8473b0c2139ecc0d72e229d4"
EXPECTED_SOURCE_SHA256 = (
    "a81f15ca11c616d477e929853019a2156799229f75c1d264a761fe7b42cdaa2e"
)
EXPECTED_DOCTOR_IMAGE_ID = (
    "sha256:47198b00190e64a35459c83a76008a2f01b20358f220aab0ee356ea7b84046c4"
)
EXPECTED_MATRIXONE_IMAGE_ID = (
    "sha256:66e2e0123d32094bff32ef7b8ba06d6d84391983cd1c9c41329dc3f7a05a2518"
)
EXPECTED_PROJECTION = (
    "b5281d07d35d4bbdc5cb053d4a06cc3ea53026e93f4d7ed2c2ec55e909a06a33"
)
EXPECTED_CLAIM_BOUNDARY = (
    "Exact pinned native branch/snapshot/merge/restart component evidence in "
    "legacy shared-database mode; not multi-db, retrieval-quality, active/inactive "
    "paging, paper-result, H100-actor, or publication evidence."
)
EXPECTED_FINDINGS = {
    "branch_drop_survived_restart",
    "branch_isolated_from_main",
    "conflicting_main_value_kept",
    "native_merge_added_branch_row",
    "native_merge_idempotent",
    "public_purge_count_ignores_deactivated_count",
    "purge_leaves_inactive_memory_row",
    "purge_residue_survived_restart",
    "shared_database_branch_contains_other_user_rows",
    "snapshot_created",
    "snapshot_drop_survived_restart",
    "snapshot_restore_is_delete_then_insert",
    "snapshot_restore_positive_path",
    "soft_purge_is_idempotent_underneath",
    "state_survived_first_restart",
    "state_survived_second_restart",
}
EXPECTED_ARTIFACTS = {
    "Dockerfile",
    "cotcodec_lifecycle.rs",
    "doctor-image-inspect.json",
    "experiment.yaml",
    "manifest.json",
    "matrixone-image-inspect.json",
    "repeat-1-matrixone-inspect.json",
    "repeat-1-matrixone.log",
    "repeat-1-phase-1.txt",
    "repeat-1-phase-2.txt",
    "repeat-1-phase-3.txt",
    "repeat-1.json",
    "repeat-2-matrixone-inspect.json",
    "repeat-2-matrixone.log",
    "repeat-2-phase-1.txt",
    "repeat-2-phase-2.txt",
    "repeat-2-phase-3.txt",
    "repeat-2.json",
    "report.json",
    "source-receipt.json",
    "source.tar",
}


class MemoriaEvidenceError(ValueError):
    """Raised when the retained Memoria evidence drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _object(data: bytes, owner: str) -> dict[str, Any]:
    def reject(value: str) -> None:
        raise MemoriaEvidenceError(f"{owner}: non-finite JSON {value}")

    try:
        payload = json.loads(data, parse_constant=reject)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MemoriaEvidenceError(f"{owner}: invalid JSON") from exc
    if not isinstance(payload, dict):
        raise MemoriaEvidenceError(f"{owner}: expected object")
    return payload


def _safe_root(project_root: Path, value: Any) -> Path:
    if (
        not isinstance(value, str)
        or not value
        or Path(value).is_absolute()
        or ".." in Path(value).parts
    ):
        raise MemoriaEvidenceError("artifact root is unsafe")
    root = project_root / value
    if root.is_symlink() or not root.is_dir():
        raise MemoriaEvidenceError("artifact root is missing")
    return root


def _files(bundle: dict[str, Any], project_root: Path) -> dict[str, bytes]:
    receipts = bundle.get("artifact_files")
    if not isinstance(receipts, dict) or set(receipts) != EXPECTED_ARTIFACTS:
        raise MemoriaEvidenceError("artifact roster drifted")
    root = _safe_root(project_root, bundle.get("artifact_root"))
    files: dict[str, bytes] = {}
    for name, expected in receipts.items():
        path = root / name
        if (
            not isinstance(expected, str)
            or len(expected) != 64
            or path.is_symlink()
            or not path.is_file()
        ):
            raise MemoriaEvidenceError(f"artifact {name} is invalid")
        data = path.read_bytes()
        if _sha(data) != expected:
            raise MemoriaEvidenceError(f"artifact {name} drifted")
        files[name] = data
    return files


def _validate_source(files: dict[str, bytes]) -> None:
    receipt = _object(files["source-receipt.json"], "source receipt")
    if receipt != {
        "archive_bytes": 7383040,
        "archive_sha256": EXPECTED_SOURCE_SHA256,
        "cargo_lock_sha256": (
            "904c09b1ba24b6c27ca8c20093b1e96de1386201fcc4a0f333a3149e0782d435"
        ),
        "git_sha": EXPECTED_REVISION,
        "git_tree": EXPECTED_TREE,
        "license_sha256": (
            "a6e2f408924ad44acabe43da942d149060a4e8174a8f30240a089bda10279607"
        ),
        "source_checks": {
            "public_purge_count_ignores_deactivated_count": True,
            "snapshot_restore_is_delete_then_insert": True,
        },
    } or _sha(files["source.tar"]) != EXPECTED_SOURCE_SHA256:
        raise MemoriaEvidenceError("source receipt drifted")
    try:
        with tarfile.open(fileobj=BytesIO(files["source.tar"]), mode="r:") as archive:
            members = archive.getmembers()
    except tarfile.TarError as exc:
        raise MemoriaEvidenceError("source archive is invalid") from exc
    names = {member.name for member in members}
    required = {
        "LICENSE",
        "memoria/Cargo.lock",
        "memoria/crates/memoria-git/src/service.rs",
        "memoria/crates/memoria-service/src/service.rs",
        "memoria/crates/memoria-storage/src/store.rs",
    }
    if not required.issubset(names) or any(
        name.startswith("/") or ".." in Path(name).parts for name in names
    ):
        raise MemoriaEvidenceError("source archive roster is unsafe or incomplete")


def _inspect_row(data: bytes, owner: str) -> dict[str, Any]:
    try:
        rows = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MemoriaEvidenceError(f"{owner} inspection is invalid") from exc
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise MemoriaEvidenceError(f"{owner} inspection roster drifted")
    return rows[0]


def _validate_runtime(files: dict[str, bytes]) -> None:
    doctor = _inspect_row(files["doctor-image-inspect.json"], "doctor image")
    config = doctor.get("Config") or {}
    labels = config.get("Labels") or {}
    if (
        doctor.get("Id") != EXPECTED_DOCTOR_IMAGE_ID
        or doctor.get("Architecture") != "arm64"
        or doctor.get("Os") != "linux"
        or config.get("User") != "65532:65532"
        or labels.get("org.opencontainers.image.revision") != EXPECTED_REVISION
        or labels.get("org.cotcodec.source-tree") != EXPECTED_TREE
        or labels.get("org.cotcodec.source-archive-sha256")
        != EXPECTED_SOURCE_SHA256
        or labels.get("org.cotcodec.discovery-only") != "true"
        or labels.get("org.cotcodec.doctor-sha256")
        != _sha(files["cotcodec_lifecycle.rs"])
    ):
        raise MemoriaEvidenceError("doctor image provenance drifted")
    matrixone = _inspect_row(files["matrixone-image-inspect.json"], "MatrixOne")
    if (
        matrixone.get("Id") != EXPECTED_MATRIXONE_IMAGE_ID
        or matrixone.get("Architecture") != "arm64"
        or matrixone.get("Os") != "linux"
        or f"matrixorigin/matrixone@{EXPECTED_MATRIXONE_IMAGE_ID}"
        not in set(matrixone.get("RepoDigests") or [])
    ):
        raise MemoriaEvidenceError("MatrixOne provenance drifted")


def _phase_projection(repeat: dict[str, Any]) -> list[dict[str, Any]]:
    phases = repeat.get("phases")
    if not isinstance(phases, list) or [row.get("phase") for row in phases] != [1, 2, 3]:
        raise MemoriaEvidenceError("phase roster drifted")
    for row in phases:
        if not isinstance(row, dict) or not all(
            value is True for key, value in row.items() if key != "phase"
        ):
            raise MemoriaEvidenceError("phase check failed")
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
        raise MemoriaEvidenceError("clean-state phase reports diverged")
    findings = {
        key: value
        for phase in first_phases
        for key, value in phase.items()
        if key != "phase"
    }
    findings.update(
        {
            "public_purge_count_ignores_deactivated_count": True,
            "snapshot_restore_is_delete_then_insert": True,
        }
    )
    if set(findings) != EXPECTED_FINDINGS or not all(findings.values()):
        raise MemoriaEvidenceError("finding roster drifted")
    report = _object(files["report.json"], "report")
    if (
        report.get("status") != EXPECTED_STATUS
        or report.get("run_count") != 2
        or report.get("matrixone_restart_count_per_run") != 2
        or report.get("stable_phase_projection_sha256") != EXPECTED_PROJECTION
        or report.get("h100_actor_admission") != "forbidden-for-this-revision"
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("claim_boundary") != EXPECTED_CLAIM_BOUNDARY
        or report.get("findings") != findings
        or report.get("source")
        != _object(files["source-receipt.json"], "source receipt")
    ):
        raise MemoriaEvidenceError("summary semantics drifted")


def validate_memoria_lifecycle_evidence(
    bundle_or_path: dict[str, Any] | Path,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    if isinstance(bundle_or_path, Path):
        bundle = _object(bundle_or_path.read_bytes(), "Memoria evidence")
        root = project_root or bundle_or_path.resolve().parents[3]
    else:
        bundle = bundle_or_path
        if project_root is None:
            raise MemoriaEvidenceError("project_root is required")
        root = project_root
    if (
        bundle.get("schema_version") != 1
        or bundle.get("source_id") != "memoria-matrixorigin"
        or bundle.get("source_revisions")
        != {"https://github.com/matrixorigin/Memoria": EXPECTED_REVISION}
        or bundle.get("evidence_kind")
        != "contained-native-transactional-lifecycle-negative"
        or bundle.get("evidence_grade") != "local-negative-reproduced"
        or bundle.get("status") != EXPECTED_STATUS
        or bundle.get("scientific_result") is not False
        or bundle.get("publication_ready") is not False
        or bundle.get("runtime_lane") != "local-arm64-docker-internal-network"
        or bundle.get("run_count") != 2
        or bundle.get("matrixone_restart_count_per_run") != 2
        or bundle.get("stable_phase_projection_sha256") != EXPECTED_PROJECTION
        or bundle.get("claim_boundary") != EXPECTED_CLAIM_BOUNDARY
        or bundle.get("h100_actor_admission") != "forbidden-for-this-revision"
        or bundle.get("findings")
        != {finding: True for finding in sorted(EXPECTED_FINDINGS)}
    ):
        raise MemoriaEvidenceError("Memoria evidence identity drifted")
    code_files = bundle.get("code_files")
    if not isinstance(code_files, dict) or not code_files:
        raise MemoriaEvidenceError("code receipt roster is missing")
    for name, expected in code_files.items():
        path = root / name
        if (
            not isinstance(expected, str)
            or len(expected) != 64
            or path.is_symlink()
            or not path.is_file()
            or _sha(path.read_bytes()) != expected
        ):
            raise MemoriaEvidenceError(f"code receipt drifted: {name}")
    files = _files(bundle, root)
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
        raise MemoriaEvidenceError("artifact manifest drifted")
    return bundle


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    path = root / "research/evidence/memory/memoria-transactional-lifecycle-negative-v1.json"
    evidence = validate_memoria_lifecycle_evidence(path, project_root=root)
    print(evidence["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
