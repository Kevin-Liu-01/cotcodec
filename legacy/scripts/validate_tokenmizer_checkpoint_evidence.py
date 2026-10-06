#!/usr/bin/env python3
"""Validate the retained two-repeat TokenMizer checkpoint negative."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

EXPECTED_STATUS = "TOKENMIZER_ACTIVE_INACTIVE_ADMISSION_KILLED"
EXPECTED_REVISION = "131e3d1569de3e8f70c198ade4e791b47f63dc41"
EXPECTED_IMAGE_ID = "sha256:a1827caaef364fcff624b4d61cec6e79f6c883a0e4b6a68955f6f1290f315c34"
EXPECTED_PROJECTION = "5a9cb5226d51b464f20576bbda3de2d3609fa7016dae88c2d2c4bb92a0765f86"
EXPECTED_CLAIM_BOUNDARY = {
    "active_inactive_h100_admission": "forbidden-for-this-revision",
    "context_compaction_quality_evaluated": False,
    "context_compaction_quality_future_contract": "separate-preregistered-study-required",
}


class TokenMizerEvidenceError(ValueError):
    """Raised when retained TokenMizer evidence drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _object(data: bytes, owner: str) -> dict[str, Any]:
    try:
        payload = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TokenMizerEvidenceError(f"{owner}: invalid JSON") from exc
    if not isinstance(payload, dict):
        raise TokenMizerEvidenceError(f"{owner}: expected object")
    return payload


def validate_tokenmizer_checkpoint_evidence(
    bundle_or_path: dict[str, Any] | Path,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    if isinstance(bundle_or_path, Path):
        bundle = _object(bundle_or_path.read_bytes(), "TokenMizer evidence")
        root = project_root or bundle_or_path.resolve().parents[3]
    else:
        bundle = bundle_or_path
        if project_root is None:
            raise TokenMizerEvidenceError("project_root is required")
        root = project_root
    if (
        bundle.get("schema_version") != 1
        or bundle.get("source_id") != "tokenmizer"
        or bundle.get("source_revisions")
        != {"https://github.com/Shweta-Mishra-ai/tokenmizer": EXPECTED_REVISION}
        or bundle.get("evidence_kind") != "contained-checkpoint-lifecycle-negative"
        or bundle.get("evidence_grade") != "local-negative-reproduced"
        or bundle.get("status") != EXPECTED_STATUS
        or bundle.get("scientific_result") is not False
        or bundle.get("publication_ready") is not False
        or bundle.get("image_id") != EXPECTED_IMAGE_ID
        or bundle.get("projection_sha256") != EXPECTED_PROJECTION
        or bundle.get("claim_boundary") != EXPECTED_CLAIM_BOUNDARY
    ):
        raise TokenMizerEvidenceError("TokenMizer evidence identity drifted")

    code_files = bundle.get("code_files")
    if not isinstance(code_files, dict) or not code_files:
        raise TokenMizerEvidenceError("code receipt roster is missing")
    for name, expected in code_files.items():
        path = root / name
        if path.is_symlink() or not path.is_file() or _sha(path.read_bytes()) != expected:
            raise TokenMizerEvidenceError(f"code receipt drifted: {name}")

    artifact_root = root / bundle.get("artifact_root", "")
    receipts = bundle.get("artifact_files")
    if artifact_root.is_symlink() or not artifact_root.is_dir() or not isinstance(receipts, dict):
        raise TokenMizerEvidenceError("artifact root or roster is invalid")
    files: dict[str, bytes] = {}
    for name, expected in receipts.items():
        path = artifact_root / name
        if path.is_symlink() or not path.is_file():
            raise TokenMizerEvidenceError(f"artifact missing: {name}")
        files[name] = path.read_bytes()
        if _sha(files[name]) != expected:
            raise TokenMizerEvidenceError(f"artifact drifted: {name}")

    first = _object(files["repeat-1.json"], "repeat 1")
    second = _object(files["repeat-2.json"], "repeat 2")
    projection = first.get("projection")
    canonical = json.dumps(projection, separators=(",", ":"), sort_keys=True).encode()
    checks = projection.get("checks") if isinstance(projection, dict) else None
    if (
        first != second
        or first.get("status") != EXPECTED_STATUS
        or first.get("source_revision") != EXPECTED_REVISION
        or first.get("scientific_result") is not False
        or first.get("publication_ready") is not False
        or first.get("active_inactive_h100_admission") is not False
        or first.get("context_compaction_quality_evaluated") is not False
        or first.get("provider_calls") != 0
        or first.get("model_backend_calls") != 0
        or first.get("projection_sha256") != EXPECTED_PROJECTION
        or _sha(canonical) != EXPECTED_PROJECTION
        or not isinstance(checks, dict)
        or not checks
        or not all(value is True for value in checks.values())
    ):
        raise TokenMizerEvidenceError("repeat semantics drifted")

    report = _object(files["report.json"], "report")
    if (
        report.get("status") != EXPECTED_STATUS
        or report.get("source_revision") != EXPECTED_REVISION
        or report.get("run_count") != 2
        or report.get("projection_sha256") != EXPECTED_PROJECTION
        or report.get("image_id") != EXPECTED_IMAGE_ID
        or report.get("claim_boundary") != EXPECTED_CLAIM_BOUNDARY
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or not all(report.get("findings", {}).values())
    ):
        raise TokenMizerEvidenceError("summary semantics drifted")

    rows = json.loads(files["image-inspect.json"])
    image = rows[0] if isinstance(rows, list) and len(rows) == 1 else {}
    labels = image.get("Config", {}).get("Labels", {}) if isinstance(image, dict) else {}
    if (
        image.get("Id") != EXPECTED_IMAGE_ID
        or image.get("Architecture") != "arm64"
        or image.get("Config", {}).get("User") != "65532:65532"
        or labels.get("org.opencontainers.image.revision") != EXPECTED_REVISION
        or labels.get("org.cotcodec.discovery-only") != "true"
    ):
        raise TokenMizerEvidenceError("image provenance drifted")

    manifest = _object(files["manifest.json"], "manifest")
    expected_files = {name: digest for name, digest in receipts.items() if name != "manifest.json"}
    if (
        manifest.get("status") != EXPECTED_STATUS
        or manifest.get("file_count") != len(expected_files)
        or manifest.get("files") != expected_files
    ):
        raise TokenMizerEvidenceError("artifact manifest drifted")
    return bundle


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    path = root / "research/evidence/memory/tokenmizer-checkpoint-negative-v1.json"
    evidence = validate_tokenmizer_checkpoint_evidence(path, project_root=root)
    print(evidence["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
