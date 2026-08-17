#!/usr/bin/env python3
"""Seal and validate SodaMem's bounded published-artifact audit evidence."""

from __future__ import annotations

import argparse
import base64
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

from scripts.audit_sodamem_published_artifacts import (  # noqa: E402
    EXPECTED_ARTIFACTS,
    EXPECTED_SOURCE_FILES,
    LONGMEMEVAL_S_SHA256,
    LONGMEMEVAL_S_SIZE,
    QUESTION_TYPES,
    SODAMEM_REPOSITORY,
    SODAMEM_REVISION,
    SODAMEM_SOURCE_ARCHIVE_SHA256,
    SODAMEM_TREE,
    _canonical,
)

DEFAULT_FIRST_ROOT = PROJECT_ROOT / "data/results/sodamem-artifact-audit/2026-08-17-local-cpu-v1"
DEFAULT_SECOND_ROOT = PROJECT_ROOT / (
    "data/results/sodamem-artifact-audit/2026-08-17-local-cpu-v1-repeat-2"
)
DEFAULT_OUTPUT = PROJECT_ROOT / "research/evidence/memory/sodamem-published-artifact-audit-v1.json"
STATUS = "SODAMEM_RELEASED_ARTIFACTS_AUDITED_NOT_REPRODUCED"
EVIDENCE_KIND = "published-answer-retrieval-artifact-audit"
EVIDENCE_GRADE = "local-artifact-audited"
REPORT_SEMANTIC_SHA256 = "28f4b6af89024ec05d6d18ff73f52cb3120127eb9e52682cd23d6f37786d7841"
REPORT_FILE_SHA256 = "6256ce5e729a21865846106dcbab223079054d2d2acbb64dc40e21947e07ea45"
PROJECTION_SHA256 = "edaa44805322fe555b85647ccd818e887ebf95db01ae642178988e3d09600921"
PROJECTION_FILE_SHA256 = "091e17ce13d1a90135967f1c29df39576d0e7ce440e22be0a3119a4a1887a340"
DATASET_ID_ROOT_SHA256 = "de4270b2356a6fbf2eea5ddbbbf47f06230c9b60656dac9489626edfd28f8761"
LONGMEMEVAL_REPOSITORY_REVISION = "9e0b455f4ef0e2ab8f2e582289761153549043fc"
LONGMEMEVAL_DATASET_REVISION = "98d7416c24c778c2fee6e6f3006e7a073259d48f"
OFFICIAL_EVALUATOR_SHA256 = "ecce9c4c79dc89d99534ac17b383a5cbb5b9f0c69ee98adaf0684742e3d95251"
PROMPT_PORT_VERSION = "longmemeval-evaluate-qa-get-anscheck-prompt-v1"
CLAIM_BOUNDARY = (
    "Exact pinned released-artifact integrity, dataset alignment, stored "
    "deepseek-v4-flash self-judge score recomputation, evidence-schema diagnostics, "
    "deterministic reference-containment diagnostics, and official-prompt case "
    "preparation; not an independent regrade, retrieval reproduction, ingest or "
    "construction reproduction, temporal-graph mechanism effect, memory-quality "
    "result, H100 actor admission, or publication evidence."
)
CODE_PATHS = {
    "experiments/memory/stage3-sodamem-published-artifact-audit.yaml",
    "harness/memory_trials/longmemeval_judge.py",
    "harness/memory_trials/public_sources.py",
    "scripts/audit_sodamem_published_artifacts.py",
    "scripts/seal_sodamem_artifact_evidence.py",
    "scripts/validate_sodamem_artifact_experiment.py",
}
EXPECTED_BY_TYPE = {
    "knowledge-update": {"count": 78, "self_judge_correct": 76},
    "multi-session": {"count": 133, "self_judge_correct": 108},
    "single-session-assistant": {"count": 56, "self_judge_correct": 55},
    "single-session-preference": {"count": 30, "self_judge_correct": 30},
    "single-session-user": {"count": 70, "self_judge_correct": 69},
    "temporal-reasoning": {"count": 133, "self_judge_correct": 126},
}
EXPECTED_USAGE = {
    "cached_input_tokens": 4_391_680,
    "calls": 2_836,
    "completion_tokens": 881_135,
    "planner_steps": 1_835,
    "prompt_tokens": 8_293_078,
    "provider_calls": 2_836,
    "total_tokens": 9_174_213,
}


class SodaMemArtifactEvidenceError(ValueError):
    """Raised when retained SodaMem artifact evidence is incomplete or drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _object(data: bytes, owner: str) -> dict[str, Any]:
    def reject(value: str) -> None:
        raise SodaMemArtifactEvidenceError(f"{owner}: non-finite JSON {value}")

    try:
        payload = json.loads(data, parse_constant=reject)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SodaMemArtifactEvidenceError(f"{owner}: invalid JSON") from exc
    if not isinstance(payload, dict):
        raise SodaMemArtifactEvidenceError(f"{owner}: expected object")
    return payload


def _array(data: bytes, owner: str) -> list[dict[str, Any]]:
    def reject(value: str) -> None:
        raise SodaMemArtifactEvidenceError(f"{owner}: non-finite JSON {value}")

    try:
        payload = json.loads(data, parse_constant=reject)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SodaMemArtifactEvidenceError(f"{owner}: invalid JSON") from exc
    if not isinstance(payload, list) or not all(isinstance(row, dict) for row in payload):
        raise SodaMemArtifactEvidenceError(f"{owner}: expected object array")
    return payload


def _capture(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise SodaMemArtifactEvidenceError(f"expected regular artifact: {path}")
    data = path.read_bytes()
    return {
        "size": len(data),
        "sha256": _sha(data),
        "content_base64": base64.b64encode(data).decode(),
    }


def _decode(files: Any) -> dict[str, bytes]:
    if not isinstance(files, dict) or set(files) != {"projection.json", "report.json"}:
        raise SodaMemArtifactEvidenceError("SodaMem evidence file roster drifted")
    decoded: dict[str, bytes] = {}
    for name, receipt in files.items():
        if not isinstance(receipt, dict) or set(receipt) != {
            "content_base64",
            "sha256",
            "size",
        }:
            raise SodaMemArtifactEvidenceError(f"SodaMem file receipt drifted: {name}")
        try:
            data = base64.b64decode(receipt["content_base64"], validate=True)
        except (TypeError, ValueError) as exc:
            raise SodaMemArtifactEvidenceError(
                f"SodaMem file receipt cannot be decoded: {name}"
            ) from exc
        if receipt.get("size") != len(data) or receipt.get("sha256") != _sha(data):
            raise SodaMemArtifactEvidenceError(f"SodaMem file hash drifted: {name}")
        decoded[name] = data
    return decoded


def _validate_report(report: dict[str, Any]) -> None:
    semantic = dict(report)
    observed_semantic = semantic.pop("report_sha256", None)
    if (
        observed_semantic != REPORT_SEMANTIC_SHA256
        or _sha(_canonical(semantic)) != REPORT_SEMANTIC_SHA256
        or report.get("status") != STATUS
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("h100_actor_admission") != "not-granted-by-artifact-audit"
    ):
        raise SodaMemArtifactEvidenceError("SodaMem report identity drifted")
    source = report.get("source")
    if source != {
        "repository": SODAMEM_REPOSITORY,
        "revision": SODAMEM_REVISION,
        "tree": SODAMEM_TREE,
        "source_archive_sha256": SODAMEM_SOURCE_ARCHIVE_SHA256,
        "source_files": EXPECTED_SOURCE_FILES,
    }:
        raise SodaMemArtifactEvidenceError("SodaMem report source receipt drifted")
    if report.get("artifacts") != EXPECTED_ARTIFACTS:
        raise SodaMemArtifactEvidenceError("SodaMem report artifact receipt drifted")
    dataset = report.get("dataset")
    if dataset != {
        "repository_revision": LONGMEMEVAL_REPOSITORY_REVISION,
        "dataset_revision": LONGMEMEVAL_DATASET_REVISION,
        "sha256": LONGMEMEVAL_S_SHA256,
        "size": LONGMEMEVAL_S_SIZE,
        "rows": 500,
        "abstention_rows": 30,
        "ordered_aligned_question_id_root_sha256": DATASET_ID_ROOT_SHA256,
    }:
        raise SodaMemArtifactEvidenceError("SodaMem report dataset receipt drifted")
    self_judge = report.get("stored_self_judge")
    if not isinstance(self_judge, dict):
        raise SodaMemArtifactEvidenceError("SodaMem self-judge summary is missing")
    by_type = self_judge.get("by_question_type")
    if not isinstance(by_type, dict) or set(by_type) != set(EXPECTED_BY_TYPE):
        raise SodaMemArtifactEvidenceError("SodaMem question-type summary drifted")
    for name, expected in EXPECTED_BY_TYPE.items():
        cell = by_type[name]
        if (
            not isinstance(cell, dict)
            or cell.get("count") != expected["count"]
            or cell.get("self_judge_correct") != expected["self_judge_correct"]
            or cell.get("self_judge_accuracy") != expected["self_judge_correct"] / expected["count"]
        ):
            raise SodaMemArtifactEvidenceError(f"SodaMem question-type summary drifted: {name}")
    if {
        key: self_judge.get(key)
        for key in (
            "model",
            "reader_planner_model",
            "same_model_self_grading",
            "correct",
            "total",
            "accuracy",
        )
    } != {
        "model": "deepseek-v4-flash",
        "reader_planner_model": "deepseek-v4-flash",
        "same_model_self_grading": True,
        "correct": 464,
        "total": 500,
        "accuracy": 0.928,
    }:
        raise SodaMemArtifactEvidenceError("SodaMem self-judge score drifted")
    if report.get("usage") != EXPECTED_USAGE:
        raise SodaMemArtifactEvidenceError("SodaMem usage summary drifted")
    if report.get("deterministic_diagnostics_not_accuracy_metrics") != {
        "normalization": "NFKC-casefold-alphanumeric-whitespace",
        "hypothesis_contains_full_normalized_reference": 314,
        "retrieved_evidence_contains_full_normalized_reference": 239,
        "non_abstention_total": 470,
        "non_abstention_hypothesis_contains_full_normalized_reference": 314,
        "non_abstention_retrieved_evidence_contains_full_normalized_reference": 239,
    }:
        raise SodaMemArtifactEvidenceError("SodaMem deterministic diagnostics drifted")
    if report.get("retrieval_artifact") != {
        "evidence_rows": 8_427,
        "minimum_evidence_rows_per_question": 10,
        "maximum_evidence_rows_per_question": 70,
        "mean_evidence_rows_per_question": 16.854,
        "questions_with_no_evidence": 0,
        "questions_with_duplicate_evidence_ids": 0,
        "evidence_rows_with_no_source_trace_id": 0,
        "answer_rows_with_evidence_id_lists": 0,
        "answer_rows_with_boolean_evidence_sentinel": 500,
        "planner_queries": 1_610,
    }:
        raise SodaMemArtifactEvidenceError("SodaMem retrieval summary drifted")
    if report.get("independent_judge_cases") != {
        "count": 500,
        "prompt_port_version": PROMPT_PORT_VERSION,
        "evaluator_repository_revision": LONGMEMEVAL_REPOSITORY_REVISION,
        "evaluator_source_sha256": OFFICIAL_EVALUATOR_SHA256,
        "projection_sha256": PROJECTION_SHA256,
    }:
        raise SodaMemArtifactEvidenceError("SodaMem judge-case summary drifted")
    limitations = report.get("limitations")
    if not isinstance(limitations, list) or len(limitations) != 7:
        raise SodaMemArtifactEvidenceError("SodaMem limitation roster drifted")


def _validate_projection(projection: list[dict[str, Any]]) -> None:
    if len(projection) != 500 or _sha(_canonical(projection)) != PROJECTION_SHA256:
        raise SodaMemArtifactEvidenceError("SodaMem projection identity drifted")
    expected_keys = {
        "abstention",
        "context_row_sha256",
        "hypothesis_contains_normalized_reference",
        "judged_row_sha256",
        "longmemeval_question_id",
        "official_prompt_sha256",
        "published_question_id",
        "question_type",
        "retrieved_evidence_contains_normalized_reference",
        "retrieved_evidence_count",
        "self_judge_correct",
        "source_trace_ids_complete",
    }
    original_ids: set[str] = set()
    self_correct = 0
    abstention_count = 0
    evidence_counts: list[int] = []
    hypothesis_contains = 0
    evidence_contains = 0
    for index, row in enumerate(projection, start=1):
        original_id = row.get("longmemeval_question_id")
        hashes = (
            row.get("context_row_sha256"),
            row.get("judged_row_sha256"),
            row.get("official_prompt_sha256"),
        )
        evidence_count = row.get("retrieved_evidence_count")
        if (
            set(row) != expected_keys
            or row.get("published_question_id") != f"q{index:03d}"
            or not isinstance(original_id, str)
            or not original_id
            or original_id in original_ids
            or row.get("question_type") not in QUESTION_TYPES
            or not all(
                isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) for value in hashes
            )
            or not isinstance(row.get("abstention"), bool)
            or not isinstance(row.get("self_judge_correct"), bool)
            or not isinstance(row.get("hypothesis_contains_normalized_reference"), bool)
            or not isinstance(row.get("retrieved_evidence_contains_normalized_reference"), bool)
            or row.get("source_trace_ids_complete") is not True
            or not isinstance(evidence_count, int)
            or isinstance(evidence_count, bool)
            or evidence_count < 1
        ):
            raise SodaMemArtifactEvidenceError("SodaMem projection row drifted")
        original_ids.add(original_id)
        self_correct += int(row["self_judge_correct"])
        abstention_count += int(row["abstention"])
        evidence_counts.append(evidence_count)
        hypothesis_contains += int(row["hypothesis_contains_normalized_reference"])
        evidence_contains += int(row["retrieved_evidence_contains_normalized_reference"])
    if (
        self_correct != 464
        or abstention_count != 30
        or sum(evidence_counts) != 8_427
        or min(evidence_counts) != 10
        or max(evidence_counts) != 70
        or hypothesis_contains != 314
        or evidence_contains != 239
        or _sha(_canonical([row["longmemeval_question_id"] for row in projection]))
        != DATASET_ID_ROOT_SHA256
    ):
        raise SodaMemArtifactEvidenceError("SodaMem projection metrics drifted")


def validate_sodamem_artifact_evidence(
    bundle_or_path: dict[str, Any] | Path,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    if isinstance(bundle_or_path, Path):
        bundle = _object(bundle_or_path.read_bytes(), "SodaMem evidence")
        root = project_root or bundle_or_path.resolve().parents[3]
    else:
        bundle = bundle_or_path
        if project_root is None:
            raise SodaMemArtifactEvidenceError("project_root is required")
        root = project_root
    expected_identity = {
        "schema_version": 1,
        "source_id": "sodamem",
        "source_revisions": {SODAMEM_REPOSITORY: SODAMEM_REVISION},
        "source_tree": SODAMEM_TREE,
        "source_archive_sha256": SODAMEM_SOURCE_ARCHIVE_SHA256,
        "source_license": "Apache-2.0",
        "evidence_kind": EVIDENCE_KIND,
        "evidence_grade": EVIDENCE_GRADE,
        "status": STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "runtime_lane": "local-arm64-read-only-artifact-audit",
        "repeat_count": 2,
        "repetitions_byte_identical": True,
        "h100_actor_admission": "not-granted-by-artifact-audit",
        "claim_boundary": CLAIM_BOUNDARY,
    }
    if any(bundle.get(key) != value for key, value in expected_identity.items()):
        raise SodaMemArtifactEvidenceError("SodaMem evidence identity drifted")
    if bundle.get("source_files") != EXPECTED_SOURCE_FILES:
        raise SodaMemArtifactEvidenceError("SodaMem source file receipt drifted")
    if bundle.get("published_artifacts") != EXPECTED_ARTIFACTS:
        raise SodaMemArtifactEvidenceError("SodaMem published artifact receipt drifted")
    if bundle.get("dataset") != {
        "repository_revision": LONGMEMEVAL_REPOSITORY_REVISION,
        "dataset_revision": LONGMEMEVAL_DATASET_REVISION,
        "sha256": LONGMEMEVAL_S_SHA256,
        "size": LONGMEMEVAL_S_SIZE,
        "rows": 500,
        "abstention_rows": 30,
    }:
        raise SodaMemArtifactEvidenceError("SodaMem evidence dataset receipt drifted")
    if bundle.get("repeat_receipts") != [
        {
            "report_file_sha256": REPORT_FILE_SHA256,
            "projection_file_sha256": PROJECTION_FILE_SHA256,
        },
        {
            "report_file_sha256": REPORT_FILE_SHA256,
            "projection_file_sha256": PROJECTION_FILE_SHA256,
        },
    ]:
        raise SodaMemArtifactEvidenceError("SodaMem repeat receipts drifted")
    code_files = bundle.get("code_files")
    if not isinstance(code_files, dict) or set(code_files) != CODE_PATHS:
        raise SodaMemArtifactEvidenceError("SodaMem code receipt roster drifted")
    for name, expected in code_files.items():
        path = root / name
        if (
            not isinstance(expected, str)
            or re.fullmatch(r"[0-9a-f]{64}", expected) is None
            or not path.is_file()
            or path.is_symlink()
            or _sha(path.read_bytes()) != expected
        ):
            raise SodaMemArtifactEvidenceError(f"SodaMem code receipt drifted: {name}")
    files = _decode(bundle.get("files"))
    if (
        _sha(files["report.json"]) != REPORT_FILE_SHA256
        or _sha(files["projection.json"]) != PROJECTION_FILE_SHA256
    ):
        raise SodaMemArtifactEvidenceError("SodaMem embedded artifact identity drifted")
    _validate_report(_object(files["report.json"], "SodaMem report"))
    _validate_projection(_array(files["projection.json"], "SodaMem projection"))
    return bundle


def seal(first_root: Path, second_root: Path, output: Path) -> dict[str, Any]:
    first_report = first_root / "report.json"
    first_projection = first_root / "projection.json"
    second_report = second_root / "report.json"
    second_projection = second_root / "projection.json"
    paths = (first_report, first_projection, second_report, second_projection)
    if any(not path.is_file() or path.is_symlink() for path in paths):
        raise SodaMemArtifactEvidenceError("SodaMem repeat input is missing")
    if (
        first_report.read_bytes() != second_report.read_bytes()
        or first_projection.read_bytes() != second_projection.read_bytes()
    ):
        raise SodaMemArtifactEvidenceError("SodaMem audit repetitions differ")
    if (
        _sha(first_report.read_bytes()) != REPORT_FILE_SHA256
        or _sha(first_projection.read_bytes()) != PROJECTION_FILE_SHA256
    ):
        raise SodaMemArtifactEvidenceError("SodaMem audit input bytes drifted")
    report = _object(first_report.read_bytes(), "SodaMem report")
    projection = _array(first_projection.read_bytes(), "SodaMem projection")
    _validate_report(report)
    _validate_projection(projection)
    bundle = {
        "schema_version": 1,
        "source_id": "sodamem",
        "source_revisions": {SODAMEM_REPOSITORY: SODAMEM_REVISION},
        "source_tree": SODAMEM_TREE,
        "source_archive_sha256": SODAMEM_SOURCE_ARCHIVE_SHA256,
        "source_license": "Apache-2.0",
        "source_files": EXPECTED_SOURCE_FILES,
        "published_artifacts": EXPECTED_ARTIFACTS,
        "dataset": {
            "repository_revision": LONGMEMEVAL_REPOSITORY_REVISION,
            "dataset_revision": LONGMEMEVAL_DATASET_REVISION,
            "sha256": LONGMEMEVAL_S_SHA256,
            "size": LONGMEMEVAL_S_SIZE,
            "rows": 500,
            "abstention_rows": 30,
        },
        "evidence_kind": EVIDENCE_KIND,
        "evidence_grade": EVIDENCE_GRADE,
        "status": STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "runtime_lane": "local-arm64-read-only-artifact-audit",
        "repeat_count": 2,
        "repetitions_byte_identical": True,
        "repeat_receipts": [
            {
                "report_file_sha256": _sha(first_report.read_bytes()),
                "projection_file_sha256": _sha(first_projection.read_bytes()),
            },
            {
                "report_file_sha256": _sha(second_report.read_bytes()),
                "projection_file_sha256": _sha(second_projection.read_bytes()),
            },
        ],
        "h100_actor_admission": "not-granted-by-artifact-audit",
        "claim_boundary": CLAIM_BOUNDARY,
        "code_files": {
            name: _sha((PROJECT_ROOT / name).read_bytes()) for name in sorted(CODE_PATHS)
        },
        "files": {
            "projection.json": _capture(first_projection),
            "report.json": _capture(first_report),
        },
    }
    validate_sodamem_artifact_evidence(bundle, project_root=PROJECT_ROOT)
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
    validate_sodamem_artifact_evidence(output, project_root=PROJECT_ROOT)
    return bundle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first-root", type=Path, default=DEFAULT_FIRST_ROOT)
    parser.add_argument("--second-root", type=Path, default=DEFAULT_SECOND_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    seal(args.first_root, args.second_root, args.output)
    print(f"SodaMem artifact evidence PASS: {_sha(args.output.read_bytes())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
