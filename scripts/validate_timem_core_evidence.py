#!/usr/bin/env python3
"""Validate the retained two-repeat TiMem core runtime negative."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

EXPECTED_STATUS = "TIMEM_CORE_RUNTIME_ADMISSION_KILLED"
EXPECTED_REVISION = "6d279a5f5d40ee229e1995df15c182cb2062c71c"
EXPECTED_IMAGE_ID = "sha256:7d2ad09126337eaa3403d3bcda7210d2ebdeae07a99ca3b628e9f3124eea9ad6"
EXPECTED_PROJECTION = "f46736fa962cb71feb7edbf9055e378467b00b604e2df4d8f8b0aecb48a68f22"
EXPECTED_BOUNDARY = {
    "active_inactive_residency_evaluated": False,
    "h100_actor_admission": "forbidden-for-this-revision",
    "hierarchy_quality_evaluated": False,
}


class TiMemEvidenceError(ValueError):
    """Raised when retained TiMem evidence drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _object(data: bytes, owner: str) -> dict[str, Any]:
    try:
        payload = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TiMemEvidenceError(f"{owner}: invalid JSON") from exc
    if not isinstance(payload, dict):
        raise TiMemEvidenceError(f"{owner}: expected object")
    return payload


def validate_timem_core_evidence(
    bundle_or_path: dict[str, Any] | Path,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    if isinstance(bundle_or_path, Path):
        bundle = _object(bundle_or_path.read_bytes(), "TiMem evidence")
        root = project_root or bundle_or_path.resolve().parents[3]
    else:
        bundle = bundle_or_path
        if project_root is None:
            raise TiMemEvidenceError("project_root is required")
        root = project_root
    if (
        bundle.get("schema_version") != 1
        or bundle.get("source_id") != "timem"
        or bundle.get("source_revisions")
        != {"https://github.com/TiMEM-AI/TiMEM": EXPECTED_REVISION}
        or bundle.get("evidence_kind") != "contained-core-runtime-negative"
        or bundle.get("evidence_grade") != "local-negative-reproduced"
        or bundle.get("status") != EXPECTED_STATUS
        or bundle.get("scientific_result") is not False
        or bundle.get("publication_ready") is not False
        or bundle.get("image_id") != EXPECTED_IMAGE_ID
        or bundle.get("projection_sha256") != EXPECTED_PROJECTION
        or bundle.get("claim_boundary") != EXPECTED_BOUNDARY
    ):
        raise TiMemEvidenceError("TiMem evidence identity drifted")

    code_files = bundle.get("code_files")
    if not isinstance(code_files, dict) or not code_files:
        raise TiMemEvidenceError("code receipt roster is missing")
    for name, expected in code_files.items():
        path = root / name
        if path.is_symlink() or not path.is_file() or _sha(path.read_bytes()) != expected:
            raise TiMemEvidenceError(f"code receipt drifted: {name}")

    artifact_root = root / bundle.get("artifact_root", "")
    receipts = bundle.get("artifact_files")
    if artifact_root.is_symlink() or not artifact_root.is_dir() or not isinstance(receipts, dict):
        raise TiMemEvidenceError("artifact root or roster is invalid")
    files: dict[str, bytes] = {}
    for name, expected in receipts.items():
        path = artifact_root / name
        if path.is_symlink() or not path.is_file():
            raise TiMemEvidenceError(f"artifact missing: {name}")
        files[name] = path.read_bytes()
        if _sha(files[name]) != expected:
            raise TiMemEvidenceError(f"artifact drifted: {name}")

    first = _object(files["repeat-1.json"], "repeat 1")
    second = _object(files["repeat-2.json"], "repeat 2")
    projection = first.get("projection")
    encoded = json.dumps(projection, separators=(",", ":"), sort_keys=True).encode()
    checks = projection.get("checks") if isinstance(projection, dict) else None
    failures = projection.get("failures") if isinstance(projection, dict) else None
    if (
        first != second
        or first.get("status") != EXPECTED_STATUS
        or first.get("source_revision") != EXPECTED_REVISION
        or first.get("scientific_result") is not False
        or first.get("publication_ready") is not False
        or first.get("h100_actor_admission") is not False
        or first.get("provider_calls") != 0
        or first.get("model_backend_calls") != 0
        or first.get("projection_sha256") != EXPECTED_PROJECTION
        or _sha(encoded) != EXPECTED_PROJECTION
        or not isinstance(checks, dict)
        or not checks
        or not all(value is True for value in checks.values())
        or not isinstance(failures, dict)
        or "unexpected keyword argument 'id'" not in failures.get(
            "l1_fragment_constructor", ""
        )
        or failures.get("l2_session_constructor")
        != "summarize-returned-none-after-unsupported-SessionMemory-fields"
        or "updated_at" not in failures.get("l5_high_level_constructor", "")
    ):
        raise TiMemEvidenceError("repeat semantics drifted")

    report = _object(files["report.json"], "report")
    if (
        report.get("status") != EXPECTED_STATUS
        or report.get("source_revision") != EXPECTED_REVISION
        or report.get("run_count") != 2
        or report.get("projection_sha256") != EXPECTED_PROJECTION
        or report.get("image_id") != EXPECTED_IMAGE_ID
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("claim_boundary", {}).get("h100_actor_admission")
        != "forbidden-for-this-revision"
        or not all(report.get("findings", {}).values())
    ):
        raise TiMemEvidenceError("summary semantics drifted")

    rows = json.loads(files["image-inspect.json"])
    image = rows[0] if isinstance(rows, list) and len(rows) == 1 else {}
    labels = image.get("Config", {}).get("Labels", {}) if isinstance(image, dict) else {}
    if (
        image.get("Id") != EXPECTED_IMAGE_ID
        or image.get("Architecture") != "arm64"
        or image.get("Config", {}).get("User") != "65532:65532"
        or labels.get("org.opencontainers.image.revision") != EXPECTED_REVISION
        or labels.get("org.cotcodec.discovery-only") != "true"
        or labels.get("org.cotcodec.source-archive-sha256")
        != "44e15508366070028c6e4b79f3f94137e8bff90956c627cb0073bf2efa5e6fbe"
    ):
        raise TiMemEvidenceError("image provenance drifted")

    source = _object(files["source-receipt.json"], "source receipt")
    if (
        source.get("git_sha") != EXPECTED_REVISION
        or source.get("git_tree") != "24645b2c9f2c9b40e5da7762f2159afa321edd2e"
        or source.get("archive_sha256") != _sha(files["source.tar"])
        or source.get("dependency_lock") != "absent-upstream"
    ):
        raise TiMemEvidenceError("source receipt drifted")

    manifest = _object(files["manifest.json"], "manifest")
    expected_files = {name: digest for name, digest in receipts.items() if name != "manifest.json"}
    if (
        manifest.get("status") != EXPECTED_STATUS
        or manifest.get("file_count") != len(expected_files)
        or manifest.get("files") != expected_files
    ):
        raise TiMemEvidenceError("artifact manifest drifted")
    return bundle


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    path = root / "research/evidence/memory/timem-core-runtime-negative-v1.json"
    evidence = validate_timem_core_evidence(path, project_root=root)
    print(evidence["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
