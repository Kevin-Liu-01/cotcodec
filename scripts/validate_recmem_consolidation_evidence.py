#!/usr/bin/env python3
"""Validate the retained two-repeat RecMem consolidation negative."""

from __future__ import annotations

import hashlib
import json
import tarfile
from io import BytesIO
from pathlib import Path
from typing import Any

EXPECTED_STATUS = (
    "BLOCKED_NON_IDEMPOTENT_WRITE_MERGE_DATA_LOSS_AND_INCOMPLETE_LINEAGE"
)
EXPECTED_REVISION = "a84252f6e5587fd4a8caac03ec9f6c732b7a7f35"
EXPECTED_TREE = "46d131594833547b275cf278db665976dc63b2f1"
EXPECTED_SOURCE_SHA256 = "274aba9567b7f1f3a738d159c873d3cbc2744bc3f6f01f857484fc01ec3076f9"
EXPECTED_IMAGE_ID = "sha256:3c6b4da614d823dcc8dcaf0706b011facd4e18b47b15c9fbfc89bf64bf5d5d2b"
EXPECTED_PROJECTION = "6c25871f30b3cf9a2cfcf84b95041c5b59642315e105a783125dd5d9f6e12fcc"
EXPECTED_CLAIM_BOUNDARY = {
    "conversation_isolation_preserved": True,
    "duplicate_retry_non_idempotent": True,
    "failed_merge_loses_prior_episode": True,
    "h100_actor_admission": "forbidden-for-this-revision",
    "recurrence_quality_evaluated": False,
    "successful_consolidation_restart_stable": True,
    "trigger_lineage_incomplete": True,
}
EXPECTED_ARTIFACTS = {
    "Dockerfile",
    "doctor.py",
    "experiment.yaml",
    "image-inspect.json",
    "manifest.json",
    "repeat-1.json",
    "repeat-1.txt",
    "repeat-2.json",
    "repeat-2.txt",
    "report.json",
    "source-receipt.json",
    "source.tar",
}


class RecMemEvidenceError(ValueError):
    """Raised when the retained RecMem evidence drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _object(data: bytes, owner: str) -> dict[str, Any]:
    def reject(value: str) -> None:
        raise RecMemEvidenceError(f"{owner}: non-finite JSON {value}")

    try:
        payload = json.loads(data, parse_constant=reject)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RecMemEvidenceError(f"{owner}: invalid JSON") from exc
    if not isinstance(payload, dict):
        raise RecMemEvidenceError(f"{owner}: expected object")
    return payload


def _safe_root(project_root: Path, value: Any) -> Path:
    if (
        not isinstance(value, str)
        or not value
        or Path(value).is_absolute()
        or ".." in Path(value).parts
    ):
        raise RecMemEvidenceError("artifact root is unsafe")
    root = project_root / value
    if root.is_symlink() or not root.is_dir():
        raise RecMemEvidenceError("artifact root is missing")
    return root


def _files(bundle: dict[str, Any], project_root: Path) -> dict[str, bytes]:
    receipts = bundle.get("artifact_files")
    if not isinstance(receipts, dict) or set(receipts) != EXPECTED_ARTIFACTS:
        raise RecMemEvidenceError("artifact roster drifted")
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
            raise RecMemEvidenceError(f"artifact {name} is invalid")
        data = path.read_bytes()
        if _sha(data) != expected:
            raise RecMemEvidenceError(f"artifact {name} drifted")
        files[name] = data
    return files


def _validate_source(files: dict[str, bytes]) -> None:
    receipt = _object(files["source-receipt.json"], "source receipt")
    if receipt != {
        "archive_bytes": 1443840,
        "archive_sha256": EXPECTED_SOURCE_SHA256,
        "git_sha": EXPECTED_REVISION,
        "git_tree": EXPECTED_TREE,
        "license_sha256": (
            "761ab33482afa265a75929a9de057b5a2f7d8fd3161fc5ab85ffa62553014537"
        ),
        "uv_lock_sha256": (
            "94803e92d128d5b42849fb179cff798b26a5b3fa5ff0995a05d28e24ad205c40"
        ),
    } or _sha(files["source.tar"]) != EXPECTED_SOURCE_SHA256:
        raise RecMemEvidenceError("source receipt drifted")
    try:
        with tarfile.open(fileobj=BytesIO(files["source.tar"]), mode="r:") as archive:
            names = archive.getnames()
    except tarfile.TarError as exc:
        raise RecMemEvidenceError("source archive is invalid") from exc
    required = {"LICENSE", "uv.lock", "recmem/rec_mem.py", "recmem/episodic_memory.py"}
    if not required.issubset(names) or any(
        name.startswith("/") or ".." in Path(name).parts for name in names
    ):
        raise RecMemEvidenceError("source archive roster is unsafe or incomplete")


def _validate_runtime(files: dict[str, bytes]) -> None:
    try:
        rows = json.loads(files["image-inspect.json"])
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RecMemEvidenceError("image inspection is invalid") from exc
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise RecMemEvidenceError("image inspection roster drifted")
    image = rows[0]
    config = image.get("Config") or {}
    labels = config.get("Labels") or {}
    if (
        image.get("Id") != EXPECTED_IMAGE_ID
        or image.get("Architecture") != "arm64"
        or image.get("Os") != "linux"
        or config.get("User") != "65532:65532"
        or labels.get("org.opencontainers.image.revision") != EXPECTED_REVISION
        or labels.get("org.cotcodec.source-tree") != EXPECTED_TREE
        or labels.get("org.cotcodec.source-archive-sha256")
        != EXPECTED_SOURCE_SHA256
        or labels.get("org.cotcodec.discovery-only") != "true"
        or labels.get("org.cotcodec.doctor-sha256") != _sha(files["doctor.py"])
    ):
        raise RecMemEvidenceError("image provenance drifted")


def _validate_reports(files: dict[str, bytes]) -> None:
    first = _object(files["repeat-1.json"], "repeat 1")
    second = _object(files["repeat-2.json"], "repeat 2")
    if first != second:
        raise RecMemEvidenceError("clean-state reports diverged")
    projection = first.get("projection")
    canonical = json.dumps(projection, separators=(",", ":"), sort_keys=True).encode()
    checks = projection.get("checks") if isinstance(projection, dict) else None
    if (
        first.get("status") != EXPECTED_STATUS
        or first.get("source_revision") != EXPECTED_REVISION
        or first.get("scientific_result") is not False
        or first.get("publication_ready") is not False
        or first.get("h100_actor_admission") is not False
        or first.get("provider_calls") != 0
        or first.get("model_backend_calls") != 0
        or first.get("projection_sha256") != EXPECTED_PROJECTION
        or _sha(canonical) != EXPECTED_PROJECTION
        or not isinstance(checks, dict)
        or not checks
        or not all(value is True for value in checks.values())
    ):
        raise RecMemEvidenceError("repeat semantics drifted")
    report = _object(files["report.json"], "report")
    if (
        report.get("status") != EXPECTED_STATUS
        or report.get("run_count") != 2
        or report.get("stable_projection_sha256") != EXPECTED_PROJECTION
        or report.get("h100_actor_admission") != "forbidden-for-this-revision"
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("findings")
        != {
            "conversation_isolation_preserved": True,
            "duplicate_retry_non_idempotent": True,
            "failed_merge_loses_prior_episode": True,
            "successful_consolidation_restart_stable": True,
            "trigger_lineage_incomplete": True,
        }
    ):
        raise RecMemEvidenceError("summary semantics drifted")


def validate_recmem_consolidation_evidence(
    bundle_or_path: dict[str, Any] | Path,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    if isinstance(bundle_or_path, Path):
        bundle = _object(bundle_or_path.read_bytes(), "RecMem evidence")
        root = project_root or bundle_or_path.resolve().parents[3]
    else:
        bundle = bundle_or_path
        if project_root is None:
            raise RecMemEvidenceError("project_root is required")
        root = project_root
    if (
        bundle.get("schema_version") != 1
        or bundle.get("source_id") != "recmem"
        or bundle.get("source_revisions")
        != {"https://github.com/CaiusDai/RecMem": EXPECTED_REVISION}
        or bundle.get("evidence_kind")
        != "contained-recurrence-consolidation-lifecycle-negative"
        or bundle.get("evidence_grade") != "local-negative-reproduced"
        or bundle.get("status") != EXPECTED_STATUS
        or bundle.get("scientific_result") is not False
        or bundle.get("publication_ready") is not False
        or bundle.get("runtime_lane") != "local-arm64-docker-network-none"
        or bundle.get("stable_projection_sha256") != EXPECTED_PROJECTION
        or bundle.get("claim_boundary") != EXPECTED_CLAIM_BOUNDARY
    ):
        raise RecMemEvidenceError("RecMem evidence identity drifted")
    code_files = bundle.get("code_files")
    if not isinstance(code_files, dict) or not code_files:
        raise RecMemEvidenceError("code receipt roster is missing")
    for name, expected in code_files.items():
        path = root / name
        if path.is_symlink() or not path.is_file() or _sha(path.read_bytes()) != expected:
            raise RecMemEvidenceError(f"code receipt drifted: {name}")
    files = _files(bundle, root)
    _validate_source(files)
    _validate_runtime(files)
    _validate_reports(files)
    manifest = _object(files["manifest.json"], "manifest")
    manifest_files = manifest.get("files")
    expected_manifest_files = {
        name: digest
        for name, digest in bundle["artifact_files"].items()
        if name != "manifest.json"
    }
    if (
        manifest.get("status") != EXPECTED_STATUS
        or manifest.get("file_count") != len(expected_manifest_files)
        or manifest_files != expected_manifest_files
    ):
        raise RecMemEvidenceError("artifact manifest drifted")
    return bundle


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    path = root / "research/evidence/memory/recmem-consolidation-negative-v1.json"
    evidence = validate_recmem_consolidation_evidence(path, project_root=root)
    print(evidence["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
