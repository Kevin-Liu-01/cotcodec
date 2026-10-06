#!/usr/bin/env python3
"""Validate the self-contained Fidelis zero-LLM reproduction evidence."""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.seal_fidelis_zero_llm_evidence import (  # noqa: E402
    DATASET_REVISION,
    DATASET_SHA256,
    DATASET_SIZE,
    DATASET_URL,
    EXPECTED_DEPENDENCY_WHEELS,
    EXPECTED_HOST,
    EXPECTED_PACKAGE_TREES,
    EXPECTED_PACKAGES,
    FIDELIS_REPOSITORY,
    FIDELIS_REVISION,
    FIDELIS_SOURCE_ARCHIVE_SHA256,
    FIDELIS_TREE,
    LICENSE_SHA256,
    MODEL_BLOBS,
    MODEL_MANIFEST_SHA256,
    OLLAMA_ARCHIVE_SHA256,
    OLLAMA_BINARY_SHA256,
    OLLAMA_DRIFT_ARCHIVE_SHA256,
    OLLAMA_DRIFT_BINARY_SHA256,
    OLLAMA_DRIFT_RUN_SHA256,
    PIPELINE_SHA256,
    PROJECTION_SHA256,
    PYPROJECT_SHA256,
    PYTHON_EXECUTABLE_SHA256,
    PYTHON_VENV_CONFIG_SHA256,
    QUESTION_ID_ROOT_SHA256,
    SHARD_MANIFEST_SHA256,
    UPSTREAM_AGGREGATE_SHA256,
    UPSTREAM_PER_QUESTION_SHA256,
)

SHA256_RE = re.compile(r"[0-9a-f]{64}")
EXPECTED_STATUS = "FIDELIS_ZERO_LLM_RETRIEVAL_REPRODUCTION_PASS"
EXPECTED_QUESTION_COUNT = 470
EXPECTED_R1_HITS = 391
EXPECTED_R5_HITS = 462
EXPECTED_TEMPORAL_BOOST_QUESTIONS = 90
EXPECTED_SHARD_COUNTS = [118, 118, 117, 117]
EXPECTED_HISTORICAL_DRIFT_TOP5 = [
    "answer_280352e9",
    "sharegpt_UnjngE7_65",
    "sharegpt_rnG0ZuV_0",
    "sharegpt_QZMeA7V_17",
    "sharegpt_T1EiHWI_13",
]
EXPECTED_CURRENT_DRIFT_TOP5 = [
    "sharegpt_UnjngE7_65",
    "sharegpt_QZMeA7V_17",
    "answer_280352e9",
    "sharegpt_Jcy1CVN_0",
    "sharegpt_PdnvIns_0",
]


class FidelisEvidenceError(ValueError):
    """Raised when the sealed Fidelis evidence contract drifts."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _require_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise FidelisEvidenceError(f"{label} must be one lowercase SHA-256 digest")
    return value


def _decode_projection(receipt: dict[str, Any]) -> list[dict[str, Any]]:
    if receipt.get("encoding") != "canonical-json+gzip+base64":
        raise FidelisEvidenceError("Fidelis projection encoding drifted")
    try:
        compressed = base64.b64decode(receipt.get("content_gzip_base64", ""), validate=True)
        encoded = gzip.decompress(compressed)
        projection = json.loads(encoded)
    except (ValueError, TypeError, gzip.BadGzipFile, json.JSONDecodeError) as exc:
        raise FidelisEvidenceError("Fidelis projection cannot be decoded") from exc
    if (
        not isinstance(projection, list)
        or receipt.get("row_count") != len(projection)
        or receipt.get("bytes") != len(encoded)
        or receipt.get("sha256") != hashlib.sha256(encoded).hexdigest()
        or receipt.get("compressed_bytes") != len(compressed)
        or receipt.get("compressed_sha256") != hashlib.sha256(compressed).hexdigest()
        or encoded != _canonical(projection)
    ):
        raise FidelisEvidenceError("Fidelis projection receipt drifted")
    return projection


def validate_fidelis_zero_llm_evidence(bundle: dict[str, Any]) -> dict[str, Any]:
    expected_identity = {
        "schema_version": 1,
        "status": EXPECTED_STATUS,
        "source_id": "fidelis",
        "evidence_grade": "local-reproduced",
        "evidence_kind": "zero-llm-retrieval-benchmark-reproduction",
        "scientific_result": True,
        "publication_ready": False,
        "runtime_lane": "local-arm64-bound-artifact-runtime",
        "source_revisions": {FIDELIS_REPOSITORY: FIDELIS_REVISION},
        "source_tree": FIDELIS_TREE,
        "source_archive_sha256": FIDELIS_SOURCE_ARCHIVE_SHA256,
        "source_license": "MIT",
        "source_file_sha256": {
            "LICENSE": LICENSE_SHA256,
            "pyproject.toml": PYPROJECT_SHA256,
            "bench/longmemeval_combined_pipeline_v35.py": PIPELINE_SHA256,
        },
        "pipeline_sha256": PIPELINE_SHA256,
    }
    if any(bundle.get(key) != value for key, value in expected_identity.items()):
        raise FidelisEvidenceError("Fidelis evidence identity drifted")
    if bundle.get("dataset") != {
        "name": "LongMemEval-S cleaned",
        "url": DATASET_URL,
        "revision": DATASET_REVISION,
        "license": "MIT",
        "sha256": DATASET_SHA256,
        "size": DATASET_SIZE,
        "source_row_count": 500,
        "non_abstention_row_count": EXPECTED_QUESTION_COUNT,
    }:
        raise FidelisEvidenceError("Fidelis dataset receipt drifted")
    if bundle.get("upstream_artifacts") != {
        "per_question_path": "bench/runs/runP-v35/per_question.json",
        "per_question_sha256": UPSTREAM_PER_QUESTION_SHA256,
        "aggregate_path": "bench/runs/runP-v35/aggregate.json",
        "aggregate_sha256": UPSTREAM_AGGREGATE_SHA256,
    }:
        raise FidelisEvidenceError("Fidelis upstream artifact receipt drifted")
    if bundle.get("shard_manifest_sha256") != SHARD_MANIFEST_SHA256:
        raise FidelisEvidenceError("Fidelis shard manifest receipt drifted")

    runtime = bundle.get("runtime")
    if not isinstance(runtime, dict):
        raise FidelisEvidenceError("Fidelis runtime receipt is missing")
    if (
        runtime.get("host") != EXPECTED_HOST
        or runtime.get("ollama_version") != "0.20.6"
        or runtime.get("ollama_release_archive_sha256") != OLLAMA_ARCHIVE_SHA256
        or runtime.get("ollama_binary_sha256") != OLLAMA_BINARY_SHA256
        or runtime.get("ollama_num_parallel") != 4
        or runtime.get("model")
        != {
            "name": "nomic-embed-text:latest",
            "manifest_sha256": MODEL_MANIFEST_SHA256,
            "blobs": MODEL_BLOBS,
        }
        or runtime.get("dependency_wheels") != EXPECTED_DEPENDENCY_WHEELS
    ):
        raise FidelisEvidenceError("Fidelis bound runtime identity drifted")
    python = runtime.get("python")
    if (
        not isinstance(python, dict)
        or python.get("python") != "3.11.15"
        or {key: python.get(key) for key in EXPECTED_PACKAGES} != EXPECTED_PACKAGES
        or python.get("executable_sha256") != PYTHON_EXECUTABLE_SHA256
        or python.get("venv_config_sha256") != PYTHON_VENV_CONFIG_SHA256
        or python.get("package_trees") != EXPECTED_PACKAGE_TREES
    ):
        raise FidelisEvidenceError("Fidelis Python runtime identity drifted")

    result = bundle.get("result")
    if not isinstance(result, dict):
        raise FidelisEvidenceError("Fidelis result is missing")
    metrics = result.get("metrics")
    expected_metrics = {
        "question_count": EXPECTED_QUESTION_COUNT,
        "recall_any_at_1_hits": EXPECTED_R1_HITS,
        "recall_any_at_1": EXPECTED_R1_HITS / EXPECTED_QUESTION_COUNT,
        "recall_any_at_5_hits": EXPECTED_R5_HITS,
        "recall_any_at_5": EXPECTED_R5_HITS / EXPECTED_QUESTION_COUNT,
    }
    if (
        metrics != expected_metrics
        or result.get("question_id_root_sha256") != QUESTION_ID_ROOT_SHA256
        or result.get("exact_top5_id_match_count") != EXPECTED_QUESTION_COUNT
        or result.get("exact_logged_score_match_count") != EXPECTED_QUESTION_COUNT
        or result.get("temporal_boost_question_count")
        != EXPECTED_TEMPORAL_BOOST_QUESTIONS
    ):
        raise FidelisEvidenceError("Fidelis reproduced metrics drifted")
    run_files = result.get("run_files")
    if (
        not isinstance(run_files, list)
        or not all(isinstance(row, dict) for row in run_files)
        or [row.get("index") for row in run_files] != [0, 1, 2, 3]
        or [row.get("row_count") for row in run_files] != EXPECTED_SHARD_COUNTS
    ):
        raise FidelisEvidenceError("Fidelis run-file roster drifted")
    for index, row in enumerate(run_files):
        _require_sha256(row.get("sha256"), f"run file {index}")

    projection_receipt = result.get("projection")
    if not isinstance(projection_receipt, dict):
        raise FidelisEvidenceError("Fidelis claim projection receipt is missing")
    projection = _decode_projection(projection_receipt)
    if projection_receipt.get("sha256") != PROJECTION_SHA256:
        raise FidelisEvidenceError("Fidelis exact claim projection drifted")
    qids: set[str] = set()
    ordered_qids: list[str] = []
    r1_hits = 0
    r5_hits = 0
    for row in projection:
        if not isinstance(row, dict):
            raise FidelisEvidenceError("Fidelis projection row is invalid")
        qid = row.get("qid")
        top5_ids = row.get("top5_ids")
        top5_scores = row.get("top5_scores")
        if (
            not isinstance(qid, str)
            or not qid
            or qid in qids
            or not isinstance(top5_ids, list)
            or len(top5_ids) != 5
            or not all(isinstance(item, str) and item for item in top5_ids)
            or len(set(top5_ids)) != 5
            or not isinstance(top5_scores, list)
            or len(top5_scores) != 5
            or not all(
                isinstance(score, (int, float))
                and not isinstance(score, bool)
                and math.isfinite(score)
                for score in top5_scores
            )
            or not isinstance(row.get("r1"), bool)
            or not isinstance(row.get("r5"), bool)
            or (row.get("r1") is True and row.get("r5") is not True)
        ):
            raise FidelisEvidenceError("Fidelis projection row contract drifted")
        qids.add(qid)
        ordered_qids.append(qid)
        r1_hits += int(row["r1"])
        r5_hits += int(row["r5"])
    if (
        len(qids) != EXPECTED_QUESTION_COUNT
        or hashlib.sha256(_canonical(ordered_qids)).hexdigest()
        != QUESTION_ID_ROOT_SHA256
        or r1_hits != EXPECTED_R1_HITS
        or r5_hits != EXPECTED_R5_HITS
    ):
        raise FidelisEvidenceError("Fidelis projection metrics drifted")
    drift = bundle.get("runtime_drift_falsifier")
    if (
        not isinstance(drift, dict)
        or drift.get("status") != "RUNTIME_VERSION_CHANGES_RETRIEVAL"
        or drift.get("question_id") != "e47becba"
        or drift.get("historical_runtime") != "0.20.6"
        or drift.get("drift_runtime") != "0.32.9"
        or drift.get("drift_release_archive_sha256") != OLLAMA_DRIFT_ARCHIVE_SHA256
        or drift.get("drift_binary_sha256") != OLLAMA_DRIFT_BINARY_SHA256
        or drift.get("shared_model_manifest_sha256") != MODEL_MANIFEST_SHA256
        or drift.get("historical_recall_any_at_1") is not True
        or drift.get("drift_recall_any_at_1") is not False
        or drift.get("drift_recall_any_at_5") is not True
        or drift.get("drift_run_sha256") != OLLAMA_DRIFT_RUN_SHA256
        or drift.get("historical_top5_ids") != EXPECTED_HISTORICAL_DRIFT_TOP5
        or drift.get("drift_top5_ids") != EXPECTED_CURRENT_DRIFT_TOP5
    ):
        raise FidelisEvidenceError("Fidelis runtime-drift falsifier drifted")
    if bundle.get("claim_boundary") != {
        "retrieval_hot_path_zero_llm": True,
        "write_path_evaluated": False,
        "persistence_lifecycle_evaluated": False,
        "answer_quality_evaluated": False,
        "latency_evaluated": False,
        "packaged_service_equivalence_evaluated": False,
        "out_of_distribution_generalization_evaluated": False,
        "logged_score_id_alignment_fully_valid": False,
        "network_isolation_evaluated": False,
        "external_attestation": False,
        "h100_actor_admission": "cpu-retrieval-gate-pass-common-actor-still-required",
    }:
        raise FidelisEvidenceError("Fidelis claim boundary drifted")
    if bundle.get("execution_protocol") != {
        "shard_count": 4,
        "resumed_from_incremental_per_question_files": True,
        "local_aggregate_used": False,
        "upstream_stage2_or_qa_reproduced": False,
        "compared_fields": [
            "question",
            "qtype",
            "gold_session_ids",
            "s1_top5_ids",
            "s1_top5_scores",
            "s1_hit_at_1",
            "s1_hit_at_5",
            "temporal_boost_fired",
            "temporal_boost_count",
        ],
    }:
        raise FidelisEvidenceError("Fidelis execution protocol drifted")
    if bundle.get("instrumentation_findings") != {
        "temporal_boost_question_count": EXPECTED_TEMPORAL_BOOST_QUESTIONS,
        "logged_top5_id_phase": "post-temporal-boost",
        "logged_top5_score_phase": "pre-temporal-boost",
        "score_id_alignment_guaranteed_for_temporal_boosted_rows": False,
        "metric_recomputation_uses_hit_flags_and_ids_not_logged_scores": True,
        "local_resume_aggregate_excluded": True,
        "local_resume_aggregate_exclusion_reason": (
            "upstream resume restores per-question rows and selected counters but not "
            "retrieval timing or every metric accumulator"
        ),
    }:
        raise FidelisEvidenceError("Fidelis instrumentation finding drifted")
    return {
        "status": EXPECTED_STATUS,
        "question_count": EXPECTED_QUESTION_COUNT,
        "recall_any_at_1_hits": EXPECTED_R1_HITS,
        "recall_any_at_5_hits": EXPECTED_R5_HITS,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    try:
        payload = json.loads(args.evidence.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise TypeError
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
        parser.error(f"cannot load Fidelis evidence: {exc}")
    try:
        result = validate_fidelis_zero_llm_evidence(payload)
    except FidelisEvidenceError as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
