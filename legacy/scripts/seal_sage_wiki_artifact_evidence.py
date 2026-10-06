#!/usr/bin/env python3
# ruff: noqa: E501 -- immutable hashes and exact claim-boundary text are kept inline.
"""Seal and validate Sage Wiki's bounded published-artifact audit evidence."""

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

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.audit_sage_wiki_published_artifacts import (  # noqa: E402
    ARTIFACTS,
    GO_BINARY_SHA256,
    GO_SUMMARY_SHA256,
    GO_TOOLCHAIN_ARCHIVE_SHA256,
    LME_SHA256,
    LME_SIZE,
    LOCOMO_SHA256,
    LOCOMO_SIZE,
    PYTEST_JUNIT_SHA256,
    SAGE_ARCHIVE_SHA256,
    SAGE_REPOSITORY,
    SAGE_REVISION,
    SAGE_TREE,
    SOURCE_FILES,
    STATUS,
    canonical,
)

DEFAULT_FIRST_ROOT = PROJECT_ROOT / "data/results/sage-wiki-artifact-audit/2026-08-17-local-cpu-v1"
DEFAULT_SECOND_ROOT = PROJECT_ROOT / "data/results/sage-wiki-artifact-audit/2026-08-17-local-cpu-v1-repeat-2"
DEFAULT_OUTPUT = PROJECT_ROOT / "research/evidence/memory/sage-wiki-published-artifact-audit-v1.json"
EVIDENCE_KIND = "published-benchmark-artifact-audit"
EVIDENCE_GRADE = "local-artifact-audited"
REPORT_SEMANTIC_SHA256 = "15c995de84955d444be94688e5ec70876ce66d3a89277c3fbbbab4d641922d4f"
REPORT_FILE_SHA256 = "527c55df1c21fdac421ffe9a85aae3702f8825639ffb36f5bf6677a766dfbcac"
PROJECTION_SEMANTIC_SHA256 = "9d4c35cca58d04ccf95908a8b4db1269c0c20c4b0bfc6c2d3447f478bf63e954"
PROJECTION_FILE_SHA256 = "0bf086084ef99c8218e927510e883c52c7fc241e480ec42f2e210941ff6a2ff6"
CLAIM_BOUNDARY = (
    "Exact committed-artifact integrity, source-test conformance, stored aggregate "
    "recomputation, report-annotation verification, and independently pinned LoCoMo "
    "and LongMemEval roster alignment; not a binary-bound rerun, retrieval "
    "reproduction, independent regrade, BEAM source reproduction, construction "
    "reproduction, graph mechanism effect, memory-quality result, H100 actor "
    "admission, or publication evidence."
)
CODE_PATHS = {
    "experiments/memory/stage3-sage-wiki-published-artifact-audit.yaml",
    "scripts/audit_sage_wiki_published_artifacts.py",
    "scripts/seal_sage_wiki_artifact_evidence.py",
    "scripts/validate_sage_wiki_artifact_experiment.py",
}


class SageWikiArtifactEvidenceError(ValueError):
    """Raised when retained Sage Wiki artifact evidence is incomplete or drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _object(data: bytes, owner: str) -> dict[str, Any]:
    def reject(value: str) -> None:
        raise SageWikiArtifactEvidenceError(f"{owner}: non-finite JSON {value}")

    try:
        payload = json.loads(data, parse_constant=reject)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SageWikiArtifactEvidenceError(f"{owner}: invalid JSON") from exc
    if not isinstance(payload, dict):
        raise SageWikiArtifactEvidenceError(f"{owner}: expected object")
    return payload


def _capture(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise SageWikiArtifactEvidenceError(f"expected regular artifact: {path}")
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


def _decode(files: Any) -> dict[str, bytes]:
    if not isinstance(files, dict) or set(files) != {"projection.json", "report.json"}:
        raise SageWikiArtifactEvidenceError("Sage Wiki evidence file roster drifted")
    expected_fields = {
        "compression",
        "raw_size",
        "raw_sha256",
        "compressed_size",
        "compressed_sha256",
        "content_gzip_base64",
    }
    decoded: dict[str, bytes] = {}
    for name, receipt in files.items():
        if not isinstance(receipt, dict) or set(receipt) != expected_fields:
            raise SageWikiArtifactEvidenceError(f"Sage Wiki file receipt drifted: {name}")
        try:
            compressed = base64.b64decode(receipt["content_gzip_base64"], validate=True)
            raw = gzip.decompress(compressed)
        except (TypeError, ValueError, OSError) as exc:
            raise SageWikiArtifactEvidenceError(f"Sage Wiki file cannot be decoded: {name}") from exc
        if (
            receipt["compression"] != "gzip-mtime-0"
            or receipt["compressed_size"] != len(compressed)
            or receipt["compressed_sha256"] != _sha(compressed)
            or receipt["raw_size"] != len(raw)
            or receipt["raw_sha256"] != _sha(raw)
        ):
            raise SageWikiArtifactEvidenceError(f"Sage Wiki file receipt hash drifted: {name}")
        decoded[name] = raw
    return decoded


def _validate_projection(projection: dict[str, Any]) -> None:
    if (
        _sha(canonical(projection)) != PROJECTION_SEMANTIC_SHA256
        or projection.get("_meta")
        != {
            "schema_version": 1,
            "source_id": "sage-wiki",
            "revision": SAGE_REVISION,
            "status": STATUS,
        }
        or projection.get("report_annotations", {}).get("checks") != 45
        or projection.get("report_annotations", {}).get("failures") != 0
    ):
        raise SageWikiArtifactEvidenceError("Sage Wiki semantic projection identity drifted")
    artifacts = projection.get("artifacts")
    if not isinstance(artifacts, list) or len(artifacts) != 10:
        raise SageWikiArtifactEvidenceError("Sage Wiki artifact projection roster drifted")
    expected = {
        name: {"sha256": receipt[0], "size": receipt[1], "rows": receipt[2]}
        for name, receipt in ARTIFACTS.items()
    }
    observed = {
        row.get("name"): {
            "sha256": row.get("sha256"),
            "size": row.get("size"),
            "rows": row.get("rows"),
        }
        for row in artifacts
        if isinstance(row, dict)
    }
    if observed != expected or any(row.get("retrieval_payload_rows") != 0 for row in artifacts):
        raise SageWikiArtifactEvidenceError("Sage Wiki artifact projection receipts drifted")


def _validate_report(report: dict[str, Any]) -> None:
    semantic = dict(report)
    observed = semantic.pop("report_sha256", None)
    if (
        observed != REPORT_SEMANTIC_SHA256
        or _sha(canonical(semantic)) != REPORT_SEMANTIC_SHA256
        or report.get("status") != STATUS
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("h100_actor_admission") != "not-granted-by-artifact-audit"
        or report.get("semantic_projection_sha256") != PROJECTION_SEMANTIC_SHA256
    ):
        raise SageWikiArtifactEvidenceError("Sage Wiki report identity drifted")
    source = report.get("source")
    if not isinstance(source, dict) or source.get("repository") != SAGE_REPOSITORY or source.get("revision") != SAGE_REVISION or source.get("tree") != SAGE_TREE or source.get("git_archive_tar_sha256") != SAGE_ARCHIVE_SHA256 or source.get("files") != SOURCE_FILES:
        raise SageWikiArtifactEvidenceError("Sage Wiki report source receipt drifted")
    boundary = report.get("claim_boundary")
    if not isinstance(boundary, dict) or boundary.get("binary_bound_to_source_revision") is not False or boundary.get("retrieval_ids_or_text_retained") is not False or boundary.get("independent_rejudge_completed") is not False or boundary.get("matched_flat_vs_graph_arm_present") is not False or boundary.get("memory_or_graph_mechanism_effect_established") is not False:
        raise SageWikiArtifactEvidenceError("Sage Wiki report claim boundary drifted")


def validate_sage_wiki_artifact_evidence(
    bundle_or_path: dict[str, Any] | Path,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    if isinstance(bundle_or_path, Path):
        bundle = _object(bundle_or_path.read_bytes(), "Sage Wiki evidence")
        root = project_root or bundle_or_path.resolve().parents[3]
    else:
        bundle = bundle_or_path
        if project_root is None:
            raise SageWikiArtifactEvidenceError("project_root is required")
        root = project_root
    expected = {
        "schema_version": 1,
        "source_id": "sage-wiki",
        "source_revisions": {SAGE_REPOSITORY: SAGE_REVISION},
        "source_tree": SAGE_TREE,
        "source_archive_sha256": SAGE_ARCHIVE_SHA256,
        "source_license": "MIT",
        "evidence_kind": EVIDENCE_KIND,
        "evidence_grade": EVIDENCE_GRADE,
        "status": STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "runtime_lane": "local-darwin-arm64-read-only-artifact-audit",
        "run_count": 2,
        "byte_identical_repetitions": True,
        "h100_actor_admission": "not-granted-by-artifact-audit",
        "claim_boundary": CLAIM_BOUNDARY,
    }
    if any(bundle.get(key) != value for key, value in expected.items()):
        raise SageWikiArtifactEvidenceError("Sage Wiki evidence identity drifted")
    if bundle.get("source_files") != SOURCE_FILES:
        raise SageWikiArtifactEvidenceError("Sage Wiki evidence source files drifted")
    if bundle.get("datasets") != {
        "longmemeval_s": {"sha256": LME_SHA256, "size": LME_SIZE, "rows": 500},
        "locomo10": {"sha256": LOCOMO_SHA256, "size": LOCOMO_SIZE, "conversations": 10},
        "beam": {"immutable_source_bound": False},
    }:
        raise SageWikiArtifactEvidenceError("Sage Wiki evidence dataset receipts drifted")
    if bundle.get("runtime") != {
        "go_version": "go1.26.6",
        "go_toolchain_module_zip_sha256": GO_TOOLCHAIN_ARCHIVE_SHA256,
        "go_binary_sha256": GO_BINARY_SHA256,
        "python_junit_sha256": PYTEST_JUNIT_SHA256,
        "go_test_summary_sha256": GO_SUMMARY_SHA256,
    }:
        raise SageWikiArtifactEvidenceError("Sage Wiki evidence runtime receipts drifted")
    if bundle.get("repetitions") != [
        {"role": "primary", "report_sha256": REPORT_FILE_SHA256, "projection_sha256": PROJECTION_FILE_SHA256},
        {"role": "replication", "report_sha256": REPORT_FILE_SHA256, "projection_sha256": PROJECTION_FILE_SHA256},
    ]:
        raise SageWikiArtifactEvidenceError("Sage Wiki evidence repetitions drifted")
    code_files = bundle.get("code_files")
    if not isinstance(code_files, dict) or set(code_files) != CODE_PATHS:
        raise SageWikiArtifactEvidenceError("Sage Wiki code receipt roster drifted")
    for name, expected_sha in code_files.items():
        path = root / name
        if not isinstance(expected_sha, str) or re.fullmatch(r"[0-9a-f]{64}", expected_sha) is None or not path.is_file() or path.is_symlink() or _sha(path.read_bytes()) != expected_sha:
            raise SageWikiArtifactEvidenceError(f"Sage Wiki code receipt drifted: {name}")
    files = _decode(bundle.get("files"))
    if _sha(files["report.json"]) != REPORT_FILE_SHA256 or _sha(files["projection.json"]) != PROJECTION_FILE_SHA256:
        raise SageWikiArtifactEvidenceError("Sage Wiki embedded artifact identity drifted")
    _validate_report(_object(files["report.json"], "Sage Wiki report"))
    _validate_projection(_object(files["projection.json"], "Sage Wiki projection"))
    return bundle


def seal(first_root: Path, second_root: Path, output: Path) -> dict[str, Any]:
    first_report = first_root / "audit/report.json"
    first_projection = first_root / "audit/projection.json"
    second_report = second_root / "audit/report.json"
    second_projection = second_root / "audit/projection.json"
    paths = [first_report, first_projection, second_report, second_projection]
    if any(not path.is_file() or path.is_symlink() for path in paths):
        raise SageWikiArtifactEvidenceError("Sage Wiki audit input is missing")
    if [_sha(path.read_bytes()) for path in paths] != [
        REPORT_FILE_SHA256,
        PROJECTION_FILE_SHA256,
        REPORT_FILE_SHA256,
        PROJECTION_FILE_SHA256,
    ]:
        raise SageWikiArtifactEvidenceError("Sage Wiki audit repetitions are not byte-identical")
    _validate_report(_object(first_report.read_bytes(), "Sage Wiki report"))
    _validate_projection(_object(first_projection.read_bytes(), "Sage Wiki projection"))
    bundle = {
        "schema_version": 1,
        "source_id": "sage-wiki",
        "source_revisions": {SAGE_REPOSITORY: SAGE_REVISION},
        "source_tree": SAGE_TREE,
        "source_archive_sha256": SAGE_ARCHIVE_SHA256,
        "source_license": "MIT",
        "source_files": SOURCE_FILES,
        "datasets": {
            "longmemeval_s": {"sha256": LME_SHA256, "size": LME_SIZE, "rows": 500},
            "locomo10": {"sha256": LOCOMO_SHA256, "size": LOCOMO_SIZE, "conversations": 10},
            "beam": {"immutable_source_bound": False},
        },
        "runtime": {
            "go_version": "go1.26.6",
            "go_toolchain_module_zip_sha256": GO_TOOLCHAIN_ARCHIVE_SHA256,
            "go_binary_sha256": GO_BINARY_SHA256,
            "python_junit_sha256": PYTEST_JUNIT_SHA256,
            "go_test_summary_sha256": GO_SUMMARY_SHA256,
        },
        "evidence_kind": EVIDENCE_KIND,
        "evidence_grade": EVIDENCE_GRADE,
        "status": STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "runtime_lane": "local-darwin-arm64-read-only-artifact-audit",
        "run_count": 2,
        "repetitions": [
            {"role": "primary", "report_sha256": REPORT_FILE_SHA256, "projection_sha256": PROJECTION_FILE_SHA256},
            {"role": "replication", "report_sha256": REPORT_FILE_SHA256, "projection_sha256": PROJECTION_FILE_SHA256},
        ],
        "byte_identical_repetitions": True,
        "h100_actor_admission": "not-granted-by-artifact-audit",
        "claim_boundary": CLAIM_BOUNDARY,
        "code_files": {name: _sha((PROJECT_ROOT / name).read_bytes()) for name in sorted(CODE_PATHS)},
        "files": {
            "projection.json": _capture(first_projection),
            "report.json": _capture(first_report),
        },
    }
    validate_sage_wiki_artifact_evidence(bundle, project_root=PROJECT_ROOT)
    output.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(bundle, indent=2, sort_keys=True) + "\n").encode()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(output, flags, 0o600)
    try:
        os.write(descriptor, encoded)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    validate_sage_wiki_artifact_evidence(output, project_root=PROJECT_ROOT)
    return bundle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first-root", type=Path, default=DEFAULT_FIRST_ROOT)
    parser.add_argument("--second-root", type=Path, default=DEFAULT_SECOND_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    seal(args.first_root, args.second_root, args.output)
    print(f"Sage Wiki artifact evidence PASS: {_sha(args.output.read_bytes())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
