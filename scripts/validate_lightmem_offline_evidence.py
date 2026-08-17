#!/usr/bin/env python3
"""Validate the retained two-repeat LightMem exact-source negative."""

from __future__ import annotations

import hashlib
import json
import tarfile
from io import BytesIO
from pathlib import Path
from typing import Any

EXPECTED_STATUS = (
    "BLOCKED_DESTRUCTIVE_DEFAULT_REOPEN_AND_CONSOLIDATION_CONTRACT_DRIFT"
)
EXPECTED_REVISION = "8fc9a9179f9170c4a40fc653fcb410375900f26e"
EXPECTED_TREE = "343831b5f0aa1d6dec62cb1c12ed71d9c7ab4a62"
EXPECTED_SOURCE_SHA256 = (
    "50830e429b65043767f485b5494829715a4c98980f98c1dd4c52c0342e588601"
)
EXPECTED_IMAGE_ID = (
    "sha256:7590709501e0d2cbfadd59284818fd96d1962a3210d26c911b56ebd153fd9b6f"
)
EXPECTED_PROJECTION = (
    "80a2b06c818ece9fce8319c0121d3e951b7469e456ed636b79d6d02f1aa72b56"
)
EXPECTED_CHECKS = {
    "automatic_offline_trigger_raises_keyword_typeerror",
    "context_only_retrieval_is_broken",
    "default_qdrant_reopen_deletes_existing_state",
    "license_metadata_conflicts_root_license",
    "native_scoped_purge_absent",
    "official_offline_script_omits_persistence_flag",
    "offline_update_leaves_embedding_stale",
    "online_update_is_noop",
    "root_dependency_lock_absent",
    "source_lineage_absent",
    "update_queue_points_later_source_to_earlier_target",
}
EXPECTED_CLAIM_BOUNDARY = {
    "active_inactive_paging_demonstrated": False,
    "h100_actor_admission": False,
    "offline_consolidation_quality_measured": False,
    "persistent_restart_safe": False,
    "scoped_purge_available": False,
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


class LightMemEvidenceError(ValueError):
    """Raised when the retained LightMem evidence drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _object(data: bytes, owner: str) -> dict[str, Any]:
    def reject(value: str) -> None:
        raise LightMemEvidenceError(f"{owner}: non-finite JSON {value}")

    try:
        payload = json.loads(data, parse_constant=reject)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LightMemEvidenceError(f"{owner}: invalid JSON") from exc
    if not isinstance(payload, dict):
        raise LightMemEvidenceError(f"{owner}: expected object")
    return payload


def _safe_root(project_root: Path, value: Any) -> Path:
    if (
        not isinstance(value, str)
        or not value
        or Path(value).is_absolute()
        or ".." in Path(value).parts
    ):
        raise LightMemEvidenceError("artifact root is unsafe")
    root = project_root / value
    if root.is_symlink() or not root.is_dir():
        raise LightMemEvidenceError("artifact root is missing")
    return root


def _files(bundle: dict[str, Any], project_root: Path) -> dict[str, bytes]:
    receipts = bundle.get("artifact_files")
    if not isinstance(receipts, dict) or set(receipts) != EXPECTED_ARTIFACTS:
        raise LightMemEvidenceError("artifact roster drifted")
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
            raise LightMemEvidenceError(f"artifact {name} is invalid")
        data = path.read_bytes()
        if _sha(data) != expected:
            raise LightMemEvidenceError(f"artifact {name} drifted")
        files[name] = data
    return files


def _validate_source(files: dict[str, bytes]) -> None:
    receipt = _object(files["source-receipt.json"], "source receipt")
    if receipt != {
        "archive_bytes": 18954240,
        "archive_sha256": EXPECTED_SOURCE_SHA256,
        "git_sha": EXPECTED_REVISION,
        "git_tree": EXPECTED_TREE,
        "license_sha256": (
            "5ec1877dbe08c6d6ee2213e44a64bc011bd21819b50b4172e3bca4acab4bf4e8"
        ),
        "pyproject_sha256": (
            "632334023335283070abb2eebfc5bece3eea11387724eaccb7aeda40732b97bb"
        ),
        "root_dependency_lock": "absent",
    } or _sha(files["source.tar"]) != EXPECTED_SOURCE_SHA256:
        raise LightMemEvidenceError("source receipt drifted")
    try:
        with tarfile.open(fileobj=BytesIO(files["source.tar"]), mode="r:") as archive:
            members = archive.getmembers()
    except tarfile.TarError as exc:
        raise LightMemEvidenceError("source archive is invalid") from exc
    names = {member.name for member in members}
    required = {
        "LICENSE",
        "pyproject.toml",
        "experiments/longmemeval/offline_update.py",
        "src/lightmem/memory/lightmem.py",
        "src/lightmem/factory/retriever/embeddingretriever/qdrant.py",
    }
    if not required.issubset(names) or any(
        name.startswith("/") or ".." in Path(name).parts for name in names
    ):
        raise LightMemEvidenceError("source archive roster is unsafe or incomplete")


def _validate_runtime(files: dict[str, bytes]) -> None:
    try:
        rows = json.loads(files["image-inspect.json"])
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LightMemEvidenceError("image inspection is invalid") from exc
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise LightMemEvidenceError("image inspection roster drifted")
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
        raise LightMemEvidenceError("image provenance drifted")


def _validate_reports(files: dict[str, bytes]) -> None:
    first = _object(files["repeat-1.json"], "repeat 1")
    second = _object(files["repeat-2.json"], "repeat 2")
    if first != second:
        raise LightMemEvidenceError("clean-state reports diverged")
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
        or projection.get("claim_boundary") != EXPECTED_CLAIM_BOUNDARY
        or not isinstance(checks, dict)
        or set(checks) != EXPECTED_CHECKS
        or not all(value is True for value in checks.values())
    ):
        raise LightMemEvidenceError("repeat semantics drifted")
    report = _object(files["report.json"], "report")
    if (
        report.get("status") != EXPECTED_STATUS
        or report.get("run_count") != 2
        or report.get("stable_projection_sha256") != EXPECTED_PROJECTION
        or report.get("h100_actor_admission") != "forbidden-for-this-revision"
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("claim_boundary") != EXPECTED_CLAIM_BOUNDARY
        or report.get("findings") != checks
    ):
        raise LightMemEvidenceError("summary semantics drifted")


def validate_lightmem_offline_evidence(
    bundle_or_path: dict[str, Any] | Path,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    if isinstance(bundle_or_path, Path):
        bundle = _object(bundle_or_path.read_bytes(), "LightMem evidence")
        root = project_root or bundle_or_path.resolve().parents[3]
    else:
        bundle = bundle_or_path
        if project_root is None:
            raise LightMemEvidenceError("project_root is required")
        root = project_root
    if (
        bundle.get("schema_version") != 1
        or bundle.get("source_id") != "lightmem"
        or bundle.get("source_revisions")
        != {"https://github.com/zjunlp/LightMem": EXPECTED_REVISION}
        or bundle.get("evidence_kind")
        != "contained-exact-source-consolidation-negative"
        or bundle.get("evidence_grade") != "local-negative-reproduced"
        or bundle.get("status") != EXPECTED_STATUS
        or bundle.get("scientific_result") is not False
        or bundle.get("publication_ready") is not False
        or bundle.get("runtime_lane") != "local-arm64-docker-network-none"
        or bundle.get("run_count") != 2
        or bundle.get("stable_projection_sha256") != EXPECTED_PROJECTION
        or bundle.get("claim_boundary") != EXPECTED_CLAIM_BOUNDARY
    ):
        raise LightMemEvidenceError("LightMem evidence identity drifted")
    code_files = bundle.get("code_files")
    if not isinstance(code_files, dict) or not code_files:
        raise LightMemEvidenceError("code receipt roster is missing")
    for name, expected in code_files.items():
        path = root / name
        if path.is_symlink() or not path.is_file() or _sha(path.read_bytes()) != expected:
            raise LightMemEvidenceError(f"code receipt drifted: {name}")
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
        manifest.get("status") != EXPECTED_STATUS
        or manifest.get("file_count") != len(expected_manifest_files)
        or manifest.get("files") != expected_manifest_files
    ):
        raise LightMemEvidenceError("artifact manifest drifted")
    return bundle


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    path = root / "research/evidence/memory/lightmem-offline-negative-v1.json"
    evidence = validate_lightmem_offline_evidence(path, project_root=root)
    print(evidence["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
