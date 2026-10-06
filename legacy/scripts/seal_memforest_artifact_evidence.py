#!/usr/bin/env python3
# ruff: noqa: E402, E501 -- project import follows explicit path bootstrap.
"""Seal and validate MemForest's bounded published-artifact audit evidence."""

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

from scripts.audit_memforest_published_artifacts import (
    ARCHIVE_SHA256,
    CLAIM_BOUNDARY,
    MAIN_VALUES,
    REPOSITORY,
    REVISION,
    SOURCE_FILES,
    STATUS,
    SUBMITTED,
    TREE,
    canonical,
)

DEFAULT_FIRST_ROOT = PROJECT_ROOT / "data/results/memforest-artifact-audit/2026-08-17-local-cpu-v1"
DEFAULT_SECOND_ROOT = (
    PROJECT_ROOT / "data/results/memforest-artifact-audit/2026-08-17-local-cpu-v1-repeat-2"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "research/evidence/memory/memforest-published-artifact-audit-v1.json"
)
EVIDENCE_KIND = "published-benchmark-and-revision-artifact-audit"
EVIDENCE_GRADE = "local-artifact-audited"
REPORT_FILE_SHA256 = "867d784cad7c0c8baf4eaa51a5edeec25a1048014e14d7eadb4790317caba039"
PROJECTION_FILE_SHA256 = "bc7948a06ac728ee34e5bf50956b5bee31074eda2b7e3341761a2b4d443cf1b5"
REPORT_SEMANTIC_SHA256 = "8d3df85fe439deca1364c3149c2f58a7d32005ce83dde767c14ab7957dc53cc9"
PROJECTION_SEMANTIC_SHA256 = "bd2e8a28c125add61058dbf75e5fc78899fbbc19b53fc7b336515708d2ab13db"
CODE_PATHS = {
    "experiments/memory/stage3-memforest-published-artifact-audit.yaml",
    "scripts/audit_memforest_published_artifacts.py",
    "scripts/seal_memforest_artifact_evidence.py",
    "scripts/validate_memforest_artifact_experiment.py",
}


class MemForestArtifactEvidenceError(ValueError):
    """Raised when retained MemForest artifact evidence is incomplete or drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _object(data: bytes, owner: str) -> dict[str, Any]:
    def reject(value: str) -> None:
        raise MemForestArtifactEvidenceError(f"{owner}: non-finite JSON {value}")

    try:
        payload = json.loads(data, parse_constant=reject)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MemForestArtifactEvidenceError(f"{owner}: invalid JSON") from exc
    if not isinstance(payload, dict):
        raise MemForestArtifactEvidenceError(f"{owner}: expected object")
    return payload


def _capture(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise MemForestArtifactEvidenceError(f"expected regular artifact: {path}")
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
        raise MemForestArtifactEvidenceError("MemForest evidence file roster drifted")
    fields = {
        "compression",
        "raw_size",
        "raw_sha256",
        "compressed_size",
        "compressed_sha256",
        "content_gzip_base64",
    }
    decoded: dict[str, bytes] = {}
    for name, receipt in files.items():
        if not isinstance(receipt, dict) or set(receipt) != fields:
            raise MemForestArtifactEvidenceError(f"MemForest file receipt drifted: {name}")
        try:
            compressed = base64.b64decode(receipt["content_gzip_base64"], validate=True)
            raw = gzip.decompress(compressed)
        except (TypeError, ValueError, OSError) as exc:
            raise MemForestArtifactEvidenceError(
                f"MemForest file cannot be decoded: {name}"
            ) from exc
        if (
            receipt["compression"] != "gzip-mtime-0"
            or receipt["compressed_size"] != len(compressed)
            or receipt["compressed_sha256"] != _sha(compressed)
            or receipt["raw_size"] != len(raw)
            or receipt["raw_sha256"] != _sha(raw)
        ):
            raise MemForestArtifactEvidenceError(f"MemForest file receipt hash drifted: {name}")
        decoded[name] = raw
    return decoded


def _validate_projection(projection: dict[str, Any]) -> None:
    if _sha(canonical(projection)) != PROJECTION_SEMANTIC_SHA256 or projection.get("_meta") != {
        "schema_version": 1,
        "source_id": "memforest",
        "revision": REVISION,
        "status": STATUS,
    }:
        raise MemForestArtifactEvidenceError("MemForest semantic projection identity drifted")
    headline = (
        projection.get("submitted", {})
        .get("benchmark/longmemeval_per_question_30b.csv", {})
        .get("methods", {})
        .get("memforest")
    )
    if headline != {
        "rows": 500,
        "pass1_correct": 399,
        "pass1": 0.798,
        "eight_sample_correct": 3167,
        "eight_sample_accuracy": 0.79175,
    }:
        raise MemForestArtifactEvidenceError("MemForest submitted headline drifted")
    public = projection.get("public_summary")
    if (
        not isinstance(public, dict)
        or public.get("label_rows") != 59664
        or public.get("summary_rows_recomputed") != 336
        or public.get("unresolved_rows") != 0
        or public.get("selected_main_values")
        != {"|".join(key): value for key, value in sorted(MAIN_VALUES.items())}
    ):
        raise MemForestArtifactEvidenceError("MemForest public summary projection drifted")
    checksums = projection.get("revision_checksums")
    if checksums != {
        "declared_files": 154,
        "manifest_sha256": SOURCE_FILES["reproducibility/SHA256SUMS"],
        "submitted_snapshot_paths_declared": [],
    }:
        raise MemForestArtifactEvidenceError("MemForest checksum projection drifted")


def _validate_report(report: dict[str, Any]) -> None:
    semantic = dict(report)
    observed = semantic.pop("report_sha256", None)
    if (
        observed != REPORT_SEMANTIC_SHA256
        or _sha(canonical(semantic)) != REPORT_SEMANTIC_SHA256
        or report.get("semantic_projection_sha256") != PROJECTION_SEMANTIC_SHA256
        or report.get("status") != STATUS
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("h100_actor_admission") != "not-granted-by-artifact-audit"
        or report.get("claim_boundary") != CLAIM_BOUNDARY
    ):
        raise MemForestArtifactEvidenceError("MemForest report identity drifted")
    source = report.get("source")
    if source != {
        "repository": REPOSITORY,
        "revision": REVISION,
        "tree": TREE,
        "git_archive_tar_sha256": ARCHIVE_SHA256,
        "files": SOURCE_FILES,
    }:
        raise MemForestArtifactEvidenceError("MemForest report source receipt drifted")
    if report.get("upstream_verifier", {}).get("stdout") != "revision release verification: PASS":
        raise MemForestArtifactEvidenceError("MemForest upstream verifier receipt drifted")


def validate_memforest_artifact_evidence(
    bundle_or_path: dict[str, Any] | Path,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Validate the self-contained MemForest evidence bundle and live code bindings."""
    if isinstance(bundle_or_path, Path):
        bundle = _object(bundle_or_path.read_bytes(), "MemForest evidence")
        root = project_root or bundle_or_path.resolve().parents[3]
    else:
        bundle = bundle_or_path
        if project_root is None:
            raise MemForestArtifactEvidenceError("project_root is required")
        root = project_root
    expected = {
        "schema_version": 1,
        "source_id": "memforest",
        "source_revisions": {REPOSITORY: REVISION},
        "source_tree": TREE,
        "source_archive_sha256": ARCHIVE_SHA256,
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
        raise MemForestArtifactEvidenceError("MemForest evidence identity drifted")
    if bundle.get("source_files") != SOURCE_FILES:
        raise MemForestArtifactEvidenceError("MemForest evidence source files drifted")
    expected_submitted = {
        path: {"sha256": receipt["sha256"], "size": receipt["size"]}
        for path, receipt in SUBMITTED.items()
    }
    if bundle.get("submitted_artifacts") != expected_submitted:
        raise MemForestArtifactEvidenceError("MemForest submitted artifact receipts drifted")
    if bundle.get("repetitions") != [
        {
            "role": "primary",
            "report_sha256": REPORT_FILE_SHA256,
            "projection_sha256": PROJECTION_FILE_SHA256,
        },
        {
            "role": "replication",
            "report_sha256": REPORT_FILE_SHA256,
            "projection_sha256": PROJECTION_FILE_SHA256,
        },
    ]:
        raise MemForestArtifactEvidenceError("MemForest evidence repetitions drifted")
    code_files = bundle.get("code_files")
    if not isinstance(code_files, dict) or set(code_files) != CODE_PATHS:
        raise MemForestArtifactEvidenceError("MemForest code receipt roster drifted")
    for name, expected_sha in code_files.items():
        path = root / name
        if (
            not isinstance(expected_sha, str)
            or re.fullmatch(r"[0-9a-f]{64}", expected_sha) is None
            or not path.is_file()
            or path.is_symlink()
            or _sha(path.read_bytes()) != expected_sha
        ):
            raise MemForestArtifactEvidenceError(f"MemForest code receipt drifted: {name}")
    files = _decode(bundle.get("files"))
    if (
        _sha(files["report.json"]) != REPORT_FILE_SHA256
        or _sha(files["projection.json"]) != PROJECTION_FILE_SHA256
    ):
        raise MemForestArtifactEvidenceError("MemForest embedded artifact identity drifted")
    _validate_report(_object(files["report.json"], "MemForest report"))
    _validate_projection(_object(files["projection.json"], "MemForest projection"))
    return bundle


def seal(first_root: Path, second_root: Path, output: Path) -> dict[str, Any]:
    """Seal two byte-identical audit repetitions into one self-contained receipt."""
    paths = [
        first_root / "report.json",
        first_root / "projection.json",
        second_root / "report.json",
        second_root / "projection.json",
    ]
    if any(not path.is_file() or path.is_symlink() for path in paths):
        raise MemForestArtifactEvidenceError("MemForest audit input is missing")
    if [_sha(path.read_bytes()) for path in paths] != [
        REPORT_FILE_SHA256,
        PROJECTION_FILE_SHA256,
        REPORT_FILE_SHA256,
        PROJECTION_FILE_SHA256,
    ]:
        raise MemForestArtifactEvidenceError("MemForest audit repetitions are not byte-identical")
    _validate_report(_object(paths[0].read_bytes(), "MemForest report"))
    _validate_projection(_object(paths[1].read_bytes(), "MemForest projection"))
    bundle = {
        "schema_version": 1,
        "source_id": "memforest",
        "source_revisions": {REPOSITORY: REVISION},
        "source_tree": TREE,
        "source_archive_sha256": ARCHIVE_SHA256,
        "source_license": "MIT",
        "source_files": SOURCE_FILES,
        "submitted_artifacts": {
            path: {"sha256": receipt["sha256"], "size": receipt["size"]}
            for path, receipt in SUBMITTED.items()
        },
        "evidence_kind": EVIDENCE_KIND,
        "evidence_grade": EVIDENCE_GRADE,
        "status": STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "runtime_lane": "local-darwin-arm64-read-only-artifact-audit",
        "run_count": 2,
        "repetitions": [
            {
                "role": "primary",
                "report_sha256": REPORT_FILE_SHA256,
                "projection_sha256": PROJECTION_FILE_SHA256,
            },
            {
                "role": "replication",
                "report_sha256": REPORT_FILE_SHA256,
                "projection_sha256": PROJECTION_FILE_SHA256,
            },
        ],
        "byte_identical_repetitions": True,
        "h100_actor_admission": "not-granted-by-artifact-audit",
        "claim_boundary": CLAIM_BOUNDARY,
        "code_files": {
            name: _sha((PROJECT_ROOT / name).read_bytes()) for name in sorted(CODE_PATHS)
        },
        "files": {
            "projection.json": _capture(paths[1]),
            "report.json": _capture(paths[0]),
        },
    }
    validate_memforest_artifact_evidence(bundle, project_root=PROJECT_ROOT)
    output.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(bundle, indent=2, sort_keys=True) + "\n").encode()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(output, flags, 0o644)
    try:
        os.write(descriptor, encoded)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return bundle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--first-root", type=Path, default=DEFAULT_FIRST_ROOT)
    parser.add_argument("--second-root", type=Path, default=DEFAULT_SECOND_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    if arguments.check:
        validate_memforest_artifact_evidence(arguments.output, project_root=PROJECT_ROOT)
        print("MemForest artifact evidence PASS")
        return 0
    bundle = seal(arguments.first_root, arguments.second_root, arguments.output)
    print(json.dumps({"status": bundle["status"], "output": str(arguments.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
