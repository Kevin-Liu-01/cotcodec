#!/usr/bin/env python3
"""Seal and validate bounded exact-source GBrain BrainBench evidence."""

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

from scripts.audit_gbrain_brainbench import (  # noqa: E402
    BUN_ARCHIVE_SHA256,
    BUN_BINARY_SHA256,
    BUN_VERSION,
    EXPECTED_CELLS,
    EXPECTED_TURN_COUNTS,
    GBRAIN_ARCHIVE_SHA256,
    GBRAIN_REPOSITORY,
    GBRAIN_REVISION,
    GBRAIN_TREE,
    SOURCE_FILES,
    STATUS,
    canonical,
)

DEFAULT_RUN_ROOT = PROJECT_ROOT / ("data/results/gbrain-brainbench/2026-08-17-local-cpu-v1")
DEFAULT_OUTPUT = PROJECT_ROOT / ("research/evidence/memory/gbrain-brainbench-conformance-v1.json")
EVIDENCE_KIND = "brainbench-cross-harness-conformance-reproduction"
EVIDENCE_GRADE = "local-conformance-reproduced"
REPORT_SEMANTIC_SHA256 = "e777c02be6556da651639d9c9a3886253d6814ed0830511e2a27d636307fc53e"
REPORT_FILE_SHA256 = "0445a43e24541aac8190b7220f84ec04101e700980c854c4f3e4786c53078b1e"
PROJECTION_SEMANTIC_SHA256 = "8e4ebad237c774eaeed37ee40c4b4b8a2a6a9fa9511485257655cd2f6dc1ab27"
PROJECTION_FILE_SHA256 = "dbed6c986319efcdd4c4e7bdef891e9ccecfc1d7e92605e898e30c369d2c5e52"
RAW_RUNS = [
    {
        "sha256": "b7f20dc3dbe27ab4a42e6f5877668132930ab0491eaccb88af41cf9b81d25f53",
        "role": "primary",
    },
    {
        "sha256": "5d6ac1bed1d4ff7248c650684e34960de72f9770084c46ae52b5621c81a03cf5",
        "role": "replication",
    },
]
JUNIT_SHA256 = "9d75d322f5dc785a756e066dda3210011a5749d9fe70146175ecd4fbc26ca85a"
CLAIM_BOUNDARY = (
    "Exact-source deterministic BrainBench conformance with one shipped OpenClaw "
    "production injection seam and two GBrain-owned contract adapters; not a "
    "matched pull-retrieval comparison, live-agent evaluation, memory-quality "
    "result, model-quality result, H100 actor admission, or publication evidence."
)
CODE_PATHS = {
    "experiments/memory/stage3-gbrain-brainbench-conformance-doctor.yaml",
    "scripts/audit_gbrain_brainbench.py",
    "scripts/seal_gbrain_brainbench_evidence.py",
    "scripts/validate_gbrain_brainbench_experiment.py",
}


class GBrainEvidenceError(ValueError):
    """Raised when retained GBrain conformance evidence is incomplete or drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _object(data: bytes, owner: str) -> dict[str, Any]:
    def reject(value: str) -> None:
        raise GBrainEvidenceError(f"{owner}: non-finite JSON {value}")

    try:
        payload = json.loads(data, parse_constant=reject)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GBrainEvidenceError(f"{owner}: invalid JSON") from exc
    if not isinstance(payload, dict):
        raise GBrainEvidenceError(f"{owner}: expected object")
    return payload


def _capture(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise GBrainEvidenceError(f"expected regular artifact: {path}")
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
        raise GBrainEvidenceError("GBrain evidence file roster drifted")
    decoded: dict[str, bytes] = {}
    expected_fields = {
        "compression",
        "raw_size",
        "raw_sha256",
        "compressed_size",
        "compressed_sha256",
        "content_gzip_base64",
    }
    for name, receipt in files.items():
        if not isinstance(receipt, dict) or set(receipt) != expected_fields:
            raise GBrainEvidenceError(f"GBrain file receipt drifted: {name}")
        try:
            compressed = base64.b64decode(receipt["content_gzip_base64"], validate=True)
            raw = gzip.decompress(compressed)
        except (TypeError, ValueError, OSError) as exc:
            raise GBrainEvidenceError(f"GBrain file cannot be decoded: {name}") from exc
        if (
            receipt["compression"] != "gzip-mtime-0"
            or receipt["compressed_size"] != len(compressed)
            or receipt["compressed_sha256"] != _sha(compressed)
            or receipt["raw_size"] != len(raw)
            or receipt["raw_sha256"] != _sha(raw)
        ):
            raise GBrainEvidenceError(f"GBrain file receipt hash drifted: {name}")
        decoded[name] = raw
    return decoded


def _validate_projection(projection: dict[str, Any]) -> None:
    if (
        _sha(canonical(projection)) != PROJECTION_SEMANTIC_SHA256
        or set(projection) != {"_meta", "cells", "compare", "seed_failures", "turn_rows"}
        or projection.get("compare")
        != {"verdict": "pass", "mode": "same-hash", "breaches": [], "notes": []}
        or projection.get("seed_failures") != []
    ):
        raise GBrainEvidenceError("GBrain semantic projection identity drifted")
    cells = projection.get("cells")
    if not isinstance(cells, list) or len(cells) != 12:
        raise GBrainEvidenceError("GBrain projection cell roster drifted")
    observed: dict[str, tuple[Any, ...]] = {}
    for cell in cells:
        if not isinstance(cell, dict):
            raise GBrainEvidenceError("GBrain projection cell is malformed")
        observed[f"{cell.get('harness')}/{cell.get('suite')}"] = (
            cell.get("seam"),
            cell.get("gold_total"),
            cell.get("gold_failed"),
            cell.get("metrics"),
        )
    if observed != EXPECTED_CELLS:
        raise GBrainEvidenceError("GBrain projection cell metrics drifted")
    rows = projection.get("turn_rows")
    if not isinstance(rows, list) or len(rows) != 786:
        raise GBrainEvidenceError("GBrain projection row roster drifted")
    counts: dict[str, int] = {}
    for row in rows:
        if not isinstance(row, dict) or "latency_ms" in row or row.get("cross_source_slugs") != []:
            raise GBrainEvidenceError("GBrain projection row drifted")
        suite = row.get("suite")
        if not isinstance(suite, str):
            raise GBrainEvidenceError("GBrain projection row suite drifted")
        counts[suite] = counts.get(suite, 0) + 1
    if counts != EXPECTED_TURN_COUNTS:
        raise GBrainEvidenceError("GBrain projection row counts drifted")


def _validate_report(report: dict[str, Any]) -> None:
    semantic = dict(report)
    observed_semantic = semantic.pop("report_sha256", None)
    if (
        observed_semantic != REPORT_SEMANTIC_SHA256
        or _sha(canonical(semantic)) != REPORT_SEMANTIC_SHA256
        or report.get("status") != STATUS
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("h100_actor_admission") != "not-granted-matched-pull-arm-missing"
    ):
        raise GBrainEvidenceError("GBrain report identity drifted")
    source = report.get("source")
    if source != {
        "repository": GBRAIN_REPOSITORY,
        "revision": GBRAIN_REVISION,
        "tree": GBRAIN_TREE,
        "git_archive_tar_sha256": GBRAIN_ARCHIVE_SHA256,
        "files": SOURCE_FILES,
    }:
        raise GBrainEvidenceError("GBrain report source receipt drifted")
    if report.get("runtime") != {
        "platform": "darwin-arm64",
        "version": BUN_VERSION,
        "release_archive_sha256": BUN_ARCHIVE_SHA256,
        "binary_sha256": BUN_BINARY_SHA256,
    }:
        raise GBrainEvidenceError("GBrain report runtime receipt drifted")
    if report.get("semantic_projection_sha256") != PROJECTION_SEMANTIC_SHA256:
        raise GBrainEvidenceError("GBrain report projection receipt drifted")
    boundary = report.get("claim_boundary")
    if not isinstance(boundary, dict) or boundary != {
        "production_seams_reproduced": ["openclaw"],
        "contract_only_seams_reproduced": ["claude-code", "codex"],
        "matched_pull_retrieval_arm_present": False,
        "live_agent_or_model_calls": False,
        "llm_extraction_evaluated": False,
        "memory_quality_evaluated": False,
        "h100_actor_admission": False,
    }:
        raise GBrainEvidenceError("GBrain report claim boundary drifted")


def validate_gbrain_brainbench_evidence(
    bundle_or_path: dict[str, Any] | Path,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    if isinstance(bundle_or_path, Path):
        bundle = _object(bundle_or_path.read_bytes(), "GBrain evidence")
        root = project_root or bundle_or_path.resolve().parents[3]
    else:
        bundle = bundle_or_path
        if project_root is None:
            raise GBrainEvidenceError("project_root is required")
        root = project_root
    expected = {
        "schema_version": 1,
        "source_id": "gbrain",
        "source_revisions": {GBRAIN_REPOSITORY: GBRAIN_REVISION},
        "source_tree": GBRAIN_TREE,
        "source_archive_sha256": GBRAIN_ARCHIVE_SHA256,
        "source_license": "MIT",
        "evidence_kind": EVIDENCE_KIND,
        "evidence_grade": EVIDENCE_GRADE,
        "status": STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "runtime_lane": "local-darwin-arm64-bun-conformance",
        "run_count": 2,
        "semantic_repetitions_identical": True,
        "h100_actor_admission": "not-granted-matched-pull-arm-missing",
        "claim_boundary": CLAIM_BOUNDARY,
    }
    if any(bundle.get(key) != value for key, value in expected.items()):
        raise GBrainEvidenceError("GBrain evidence identity drifted")
    if bundle.get("source_files") != SOURCE_FILES:
        raise GBrainEvidenceError("GBrain evidence source files drifted")
    if bundle.get("runtime") != {
        "bun_version": BUN_VERSION,
        "release_archive_sha256": BUN_ARCHIVE_SHA256,
        "binary_sha256": BUN_BINARY_SHA256,
    }:
        raise GBrainEvidenceError("GBrain evidence runtime drifted")
    if bundle.get("raw_runs") != RAW_RUNS or bundle.get("focused_junit_sha256") != JUNIT_SHA256:
        raise GBrainEvidenceError("GBrain raw execution receipt drifted")
    code_files = bundle.get("code_files")
    if not isinstance(code_files, dict) or set(code_files) != CODE_PATHS:
        raise GBrainEvidenceError("GBrain code receipt roster drifted")
    for name, expected_sha in code_files.items():
        path = root / name
        if (
            not isinstance(expected_sha, str)
            or re.fullmatch(r"[0-9a-f]{64}", expected_sha) is None
            or not path.is_file()
            or path.is_symlink()
            or _sha(path.read_bytes()) != expected_sha
        ):
            raise GBrainEvidenceError(f"GBrain code receipt drifted: {name}")
    files = _decode(bundle.get("files"))
    if (
        _sha(files["report.json"]) != REPORT_FILE_SHA256
        or _sha(files["projection.json"]) != PROJECTION_FILE_SHA256
    ):
        raise GBrainEvidenceError("GBrain embedded artifact identity drifted")
    _validate_report(_object(files["report.json"], "GBrain report"))
    _validate_projection(_object(files["projection.json"], "GBrain projection"))
    return bundle


def seal(run_root: Path, output: Path) -> dict[str, Any]:
    report_path = run_root / "audit/report.json"
    projection_path = run_root / "audit/projection.json"
    raw_paths = [run_root / "run-1/brainbench.json", run_root / "run-2/brainbench.json"]
    junit_path = run_root / "upstream-focused-tests.junit.xml"
    for path in [report_path, projection_path, *raw_paths, junit_path]:
        if not path.is_file() or path.is_symlink():
            raise GBrainEvidenceError(f"GBrain audit input is missing: {path}")
    if (
        _sha(report_path.read_bytes()) != REPORT_FILE_SHA256
        or _sha(projection_path.read_bytes()) != PROJECTION_FILE_SHA256
        or [_sha(path.read_bytes()) for path in raw_paths]
        != [receipt["sha256"] for receipt in RAW_RUNS]
        or _sha(junit_path.read_bytes()) != JUNIT_SHA256
    ):
        raise GBrainEvidenceError("GBrain audit input bytes drifted")
    _validate_report(_object(report_path.read_bytes(), "GBrain report"))
    _validate_projection(_object(projection_path.read_bytes(), "GBrain projection"))
    bundle = {
        "schema_version": 1,
        "source_id": "gbrain",
        "source_revisions": {GBRAIN_REPOSITORY: GBRAIN_REVISION},
        "source_tree": GBRAIN_TREE,
        "source_archive_sha256": GBRAIN_ARCHIVE_SHA256,
        "source_license": "MIT",
        "source_files": SOURCE_FILES,
        "runtime": {
            "bun_version": BUN_VERSION,
            "release_archive_sha256": BUN_ARCHIVE_SHA256,
            "binary_sha256": BUN_BINARY_SHA256,
        },
        "evidence_kind": EVIDENCE_KIND,
        "evidence_grade": EVIDENCE_GRADE,
        "status": STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "runtime_lane": "local-darwin-arm64-bun-conformance",
        "run_count": 2,
        "raw_runs": RAW_RUNS,
        "focused_junit_sha256": JUNIT_SHA256,
        "semantic_repetitions_identical": True,
        "h100_actor_admission": "not-granted-matched-pull-arm-missing",
        "claim_boundary": CLAIM_BOUNDARY,
        "code_files": {
            name: _sha((PROJECT_ROOT / name).read_bytes()) for name in sorted(CODE_PATHS)
        },
        "files": {
            "projection.json": _capture(projection_path),
            "report.json": _capture(report_path),
        },
    }
    validate_gbrain_brainbench_evidence(bundle, project_root=PROJECT_ROOT)
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
    validate_gbrain_brainbench_evidence(output, project_root=PROJECT_ROOT)
    return bundle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    seal(args.run_root, args.output)
    print(f"GBrain BrainBench evidence PASS: {_sha(args.output.read_bytes())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
