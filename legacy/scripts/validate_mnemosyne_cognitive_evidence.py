#!/usr/bin/env python3
"""Validate the retained Mnemosyne Cognitive lifecycle negative."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

EXPECTED_STATUS = "MNEMOSYNE_COGNITIVE_ACTIVE_INACTIVE_ADMISSION_KILLED"
EXPECTED_REVISION = "5506aae7cec9ada5523099fd5ab858a4eee593b6"
EXPECTED_TREE = "d5cb986483135f016d731d73baad95f2326d84bb"
EXPECTED_IMAGE_ID = (
    "sha256:b64c3e21d431440cadd289e72eea3a2d63bb9bb38da95bf9ebbc3469dceef6d4"
)
EXPECTED_QDRANT_IMAGE_ID = (
    "sha256:affb67e1d6f2f93d7d20b90d238a7d4b974d36351c162e73bda794e4b2e03483"
)
EXPECTED_INITIAL_PROJECTION = (
    "a78cf1418f4687e6744c43d5408617b420b6a31a78c42d8ccf89e99f5996b691"
)
EXPECTED_RESTART_PROJECTION = (
    "fcebdca6cf05a724e57719f91e789a28ccd8911e56d859179bb4ec5fab23641a"
)
EXPECTED_BOUNDARY = {
    "active_inactive_quality_evaluated": False,
    "graph_quality_evaluated": False,
    "h100_actor_admission": "forbidden-for-this-revision",
}


class MnemosyneCognitiveEvidenceError(ValueError):
    """Raised when retained Mnemosyne Cognitive evidence drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _object(data: bytes, owner: str) -> dict[str, Any]:
    try:
        payload = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MnemosyneCognitiveEvidenceError(f"{owner}: invalid JSON") from exc
    if not isinstance(payload, dict):
        raise MnemosyneCognitiveEvidenceError(f"{owner}: expected object")
    return payload


def _validate_run(
    payload: dict[str, Any], *, phase: str, projection_sha256: str
) -> dict[str, Any]:
    if (
        payload.get("status") != EXPECTED_STATUS
        or payload.get("source_revision") != EXPECTED_REVISION
        or payload.get("phase") != phase
        or payload.get("scientific_result") is not False
        or payload.get("publication_ready") is not False
        or payload.get("h100_actor_admission") is not False
        or payload.get("provider_calls") != 0
        or payload.get("model_backend_calls") != 0
        or payload.get("projection_sha256") != projection_sha256
    ):
        raise MnemosyneCognitiveEvidenceError(f"{phase} run identity drifted")
    projection = payload.get("projection")
    if not isinstance(projection, dict):
        raise MnemosyneCognitiveEvidenceError(f"{phase} projection missing")
    encoded = json.dumps(projection, separators=(",", ":"), sort_keys=True).encode()
    if _sha(encoded) != projection_sha256:
        raise MnemosyneCognitiveEvidenceError(f"{phase} projection digest drifted")
    checks = projection.get("checks")
    if not isinstance(checks, dict) or not checks or not all(v is True for v in checks.values()):
        raise MnemosyneCognitiveEvidenceError(f"{phase} checks drifted")
    return projection


def validate_mnemosyne_cognitive_evidence(
    bundle_or_path: dict[str, Any] | Path,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    if isinstance(bundle_or_path, Path):
        bundle = _object(bundle_or_path.read_bytes(), "Mnemosyne Cognitive evidence")
        root = project_root or bundle_or_path.resolve().parents[3]
    else:
        bundle = bundle_or_path
        if project_root is None:
            raise MnemosyneCognitiveEvidenceError("project_root is required")
        root = project_root

    if (
        bundle.get("schema_version") != 1
        or bundle.get("source_id") != "mnemosyne-cognitive-os"
        or bundle.get("source_revisions")
        != {"https://github.com/28naem-del/mnemosyne": EXPECTED_REVISION}
        or bundle.get("evidence_kind") != "native-negative-reproduction"
        or bundle.get("evidence_grade") != "local-negative-reproduced"
        or bundle.get("status") != EXPECTED_STATUS
        or bundle.get("scientific_result") is not False
        or bundle.get("publication_ready") is not False
        or bundle.get("run_count") != 2
        or bundle.get("image_id") != EXPECTED_IMAGE_ID
        or bundle.get("qdrant_image_id") != EXPECTED_QDRANT_IMAGE_ID
        or bundle.get("initial_projection_sha256") != EXPECTED_INITIAL_PROJECTION
        or bundle.get("restart_projection_sha256") != EXPECTED_RESTART_PROJECTION
        or bundle.get("claim_boundary") != EXPECTED_BOUNDARY
    ):
        raise MnemosyneCognitiveEvidenceError("evidence identity drifted")

    code_files = bundle.get("code_files")
    if not isinstance(code_files, dict) or not code_files:
        raise MnemosyneCognitiveEvidenceError("code receipt roster is missing")
    for name, expected in code_files.items():
        path = root / name
        if path.is_symlink() or not path.is_file() or _sha(path.read_bytes()) != expected:
            raise MnemosyneCognitiveEvidenceError(f"code receipt drifted: {name}")

    artifact_root = root / bundle.get("artifact_root", "")
    receipts = bundle.get("artifact_files")
    if artifact_root.is_symlink() or not artifact_root.is_dir() or not isinstance(receipts, dict):
        raise MnemosyneCognitiveEvidenceError("artifact root or roster is invalid")
    files: dict[str, bytes] = {}
    for name, expected in receipts.items():
        path = artifact_root / name
        if path.is_symlink() or not path.is_file():
            raise MnemosyneCognitiveEvidenceError(f"artifact missing: {name}")
        files[name] = path.read_bytes()
        if _sha(files[name]) != expected:
            raise MnemosyneCognitiveEvidenceError(f"artifact drifted: {name}")

    initial_1 = _object(files["repeat-1-initial.json"], "initial repeat 1")
    initial_2 = _object(files["repeat-2-initial.json"], "initial repeat 2")
    restart_1 = _object(files["repeat-1-restart.json"], "restart repeat 1")
    restart_2 = _object(files["repeat-2-restart.json"], "restart repeat 2")
    if initial_1 != initial_2 or restart_1 != restart_2:
        raise MnemosyneCognitiveEvidenceError("clean repeats are not byte-equivalent")
    initial = _validate_run(
        initial_1, phase="initial", projection_sha256=EXPECTED_INITIAL_PROJECTION
    )
    restart = _validate_run(
        restart_1, phase="restart", projection_sha256=EXPECTED_RESTART_PROJECTION
    )
    first_report = initial.get("firstReport")
    second_report = initial.get("secondReport")
    if (
        not isinstance(first_report, dict)
        or not isinstance(second_report, dict)
        or first_report.get("analyzed") != 200
        or first_report.get("staleDemoted") != 1
        or first_report.get("nearDuplicatesMerged") != 1
        or first_report.get("popularPromoted") != 1
        or second_report.get("analyzed") != 200
        or second_report.get("staleDemoted") != 1
        or second_report.get("nearDuplicatesMerged") != 0
        or second_report.get("popularPromoted") != 0
        or restart.get("checks", {}).get("forgotten_plaintext_persists") is not True
    ):
        raise MnemosyneCognitiveEvidenceError("lifecycle failure semantics drifted")

    report = _object(files["report.json"], "report")
    if (
        report.get("status") != EXPECTED_STATUS
        or report.get("run_count") != 2
        or report.get("initial_projection_sha256") != EXPECTED_INITIAL_PROJECTION
        or report.get("restart_projection_sha256") != EXPECTED_RESTART_PROJECTION
        or report.get("h100_actor_admission") != "forbidden-for-this-revision"
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("claim_boundary") != EXPECTED_BOUNDARY
        or not all(report.get("findings", {}).values())
        or report.get("upstream_tests") != {"passed": True, "suites": 4, "tests": 62}
    ):
        raise MnemosyneCognitiveEvidenceError("summary semantics drifted")

    image_rows = json.loads(files["image-inspect.json"])
    image = image_rows[0] if isinstance(image_rows, list) and len(image_rows) == 1 else {}
    labels = image.get("Config", {}).get("Labels", {}) if isinstance(image, dict) else {}
    if (
        image.get("Id") != EXPECTED_IMAGE_ID
        or image.get("Architecture") != "arm64"
        or image.get("Os") != "linux"
        or image.get("Config", {}).get("User") != "65534:65534"
        or labels.get("org.opencontainers.image.revision") != EXPECTED_REVISION
        or labels.get("org.cotcodec.source-tree") != EXPECTED_TREE
        or labels.get("org.cotcodec.discovery-only") != "true"
        or labels.get("org.cotcodec.source-archive-sha256") != _sha(files["source.tar"])
        or labels.get("org.cotcodec.doctor-sha256") != _sha(files["doctor.mjs"])
    ):
        raise MnemosyneCognitiveEvidenceError("doctor image provenance drifted")

    qdrant_rows = json.loads(files["qdrant-image-inspect.json"])
    qdrant = qdrant_rows[0] if isinstance(qdrant_rows, list) and len(qdrant_rows) == 1 else {}
    if (
        qdrant.get("Id") != EXPECTED_QDRANT_IMAGE_ID
        or qdrant.get("Architecture") != "arm64"
        or qdrant.get("Os") != "linux"
        or qdrant.get("Config", {}).get("User") != "1000:1000"
    ):
        raise MnemosyneCognitiveEvidenceError("Qdrant image provenance drifted")

    source = _object(files["source-receipt.json"], "source receipt")
    if (
        source.get("git_sha") != EXPECTED_REVISION
        or source.get("git_tree") != EXPECTED_TREE
        or source.get("archive_sha256") != _sha(files["source.tar"])
        or source.get("package_lock_sha256")
        != "791028b9eb8b0c918157436a41f1d4f7d675920ec39018e2b9b7364025d887b9"
    ):
        raise MnemosyneCognitiveEvidenceError("source receipt drifted")

    tests = _object(files["upstream-tests.json"], "upstream tests")
    if (
        tests.get("success") is not True
        or tests.get("numTotalTests") != 62
        or tests.get("numPassedTests") != 62
        or tests.get("numFailedTests") != 0
        or len(tests.get("testResults", [])) != 4
    ):
        raise MnemosyneCognitiveEvidenceError("upstream test receipt drifted")

    for name in (
        "repeat-1-initial-qdrant.log",
        "repeat-1-restart-qdrant.log",
        "repeat-2-initial-qdrant.log",
        "repeat-2-restart-qdrant.log",
    ):
        if not files[name].strip():
            raise MnemosyneCognitiveEvidenceError(f"empty database log: {name}")

    manifest = _object(files["manifest.json"], "manifest")
    expected_files = {name: digest for name, digest in receipts.items() if name != "manifest.json"}
    if (
        manifest.get("status") != EXPECTED_STATUS
        or manifest.get("file_count") != len(expected_files)
        or manifest.get("files") != expected_files
    ):
        raise MnemosyneCognitiveEvidenceError("artifact manifest drifted")
    return bundle


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    path = root / "research/evidence/memory/mnemosyne-cognitive-lifecycle-negative-v1.json"
    evidence = validate_mnemosyne_cognitive_evidence(path, project_root=root)
    print(evidence["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
