#!/usr/bin/env python3
"""Audit the pinned MemPalace raw artifact without calling a model or retriever.

This is artifact archaeology, not a reproduction.  It verifies the current
source pin and released JSONL, recomputes MemPalace's custom any-hit recall and
the official LongMemEval all-hit metric from the independently pinned dataset,
and records the historical-lock mismatch that requires a fresh container run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials.mempalace_control import (  # noqa: E402
    MEMPALACE_REVISION,
    MEMPALACE_RUNNER_SHA256,
    MEMPALACE_SOURCE_ARCHIVE_SHA256,
    MEMPALACE_TREE,
    MEMPALACE_UV_LOCK_SHA256,
)
from harness.memory_trials.public_sources import (  # noqa: E402
    LONGMEMEVAL_DATASET_REVISION,
    LONGMEMEVAL_REPOSITORY_REVISION,
    LONGMEMEVAL_S_SHA256,
    LONGMEMEVAL_S_SIZE,
)
from harness.memory_trials.schema import canonical_json, sha256_text  # noqa: E402

MEMPALACE_RELEASED_RAW_ARTIFACT = (
    "benchmarks/results_mempal_raw_session_20260414_1629.jsonl"
)
MEMPALACE_RELEASED_RAW_SHA256 = (
    "2b71b5e514279c28443736561e2ac453045520b0f8832ff092e8a6143965e5d1"
)
MEMPALACE_RELEASED_RAW_SIZE = 13_113_499
MEMPALACE_RELEASED_RAW_ROWS = 500
MEMPALACE_ARTIFACT_COMMIT = "61d02e10fe23ce102b11c64fff91f50da55f5dd7"
MEMPALACE_ARTIFACT_LOCK_SHA256 = (
    "c6eb70271a40ddcba3204fe451574ebe579bf87b23d557111b1293776cefb545"
)
MEMPALACE_ARTIFACT_CHROMADB_VERSION = "0.6.3"
MEMPALACE_CURRENT_CHROMADB_VERSION = "1.5.7"
MEMPALACE_LICENSE_SHA256 = (
    "81dc6cc278d80f0f1b028ecd86af30d61e441b9ae53d9d9a2ed19389ba657a5d"
)
MEMPALACE_PYPROJECT_SHA256 = (
    "269ebdab137e27db20efdf7a9d0ddb6079e917b44f470b4848f5a2d2309be182"
)
LONGMEMEVAL_OFFICIAL_METRICS_SHA256 = (
    "58b70c0b562ea57372a7774a554c347cd908e901b77ac0149fc90b097b6f1b8f"
)
LONGMEMEVAL_OFFICIAL_EVAL_UTILS_SHA256 = (
    "c98b8d1096877a15aa755c9de44fe33c195298466a2eb6f3c0f9f6bde8c72349"
)


@dataclass(frozen=True)
class ArtifactExpectations:
    result_sha256: str = MEMPALACE_RELEASED_RAW_SHA256
    result_size: int = MEMPALACE_RELEASED_RAW_SIZE
    result_rows: int = MEMPALACE_RELEASED_RAW_ROWS
    dataset_sha256: str = LONGMEMEVAL_S_SHA256
    dataset_size: int = LONGMEMEVAL_S_SIZE
    runner_sha256: str = MEMPALACE_RUNNER_SHA256
    lock_sha256: str = MEMPALACE_UV_LOCK_SHA256
    license_sha256: str = MEMPALACE_LICENSE_SHA256
    pyproject_sha256: str = MEMPALACE_PYPROJECT_SHA256


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_file(path: Path, *, sha256: str, size: int | None = None) -> None:
    if not path.is_file():
        raise ValueError(f"missing required artifact: {path}")
    if size is not None and path.stat().st_size != size:
        raise ValueError(f"artifact size mismatch: {path}")
    if _sha256_file(path) != sha256:
        raise ValueError(f"artifact SHA-256 mismatch: {path}")


def _dcg_official(relevances: list[int]) -> float:
    if not relevances:
        return 0.0
    return float(
        relevances[0]
        + sum(
            relevance / math.log2(index)
            for index, relevance in enumerate(relevances[1:], start=2)
        )
    )


def _official_ndcg(
    ranked: list[str], correct: set[str], corpus_ids: list[str], k: int
) -> float:
    actual = [int(document_id in correct) for document_id in ranked[:k]]
    # Official LongMemEval builds the ideal relevance vector from the complete
    # corpus, including duplicate corpus entries with the same session ID.
    relevant_corpus_entries = sum(document_id in correct for document_id in corpus_ids)
    ideal = [1] * min(k, relevant_corpus_entries)
    denominator = _dcg_official(ideal)
    return 0.0 if denominator == 0 else _dcg_official(actual) / denominator


def audit_upstream_artifact(
    *,
    source_root: Path,
    dataset_path: Path,
    result_path: Path,
    expectations: ArtifactExpectations | None = None,
) -> dict[str, Any]:
    """Verify and recompute one released artifact under explicit expectations."""

    expectations = expectations or ArtifactExpectations()
    source_root = source_root.resolve()
    dataset_path = dataset_path.resolve()
    result_path = result_path.resolve()
    _verify_file(
        source_root / "benchmarks/longmemeval_bench.py",
        sha256=expectations.runner_sha256,
    )
    _verify_file(source_root / "uv.lock", sha256=expectations.lock_sha256)
    _verify_file(source_root / "LICENSE", sha256=expectations.license_sha256)
    _verify_file(source_root / "pyproject.toml", sha256=expectations.pyproject_sha256)
    _verify_file(
        dataset_path,
        sha256=expectations.dataset_sha256,
        size=expectations.dataset_size,
    )
    _verify_file(
        result_path,
        sha256=expectations.result_sha256,
        size=expectations.result_size,
    )

    try:
        dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("LongMemEval dataset is not valid JSON") from exc
    if not isinstance(dataset, list):
        raise ValueError("LongMemEval dataset must be a JSON array")
    by_id = {row.get("question_id"): row for row in dataset if isinstance(row, dict)}
    if len(by_id) != len(dataset) or None in by_id:
        raise ValueError("LongMemEval question IDs must be present and unique")

    rows: list[dict[str, Any]] = []
    with result_path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"MemPalace JSONL line {line_number} is invalid"
                ) from exc
            if not isinstance(row, dict):
                raise ValueError("MemPalace JSONL rows must be objects")
            rows.append(row)
    if len(rows) != expectations.result_rows:
        raise ValueError("MemPalace artifact row count mismatch")
    question_ids = [row.get("question_id") for row in rows]
    if len(question_ids) != len(set(question_ids)) or set(question_ids) != set(by_id):
        raise ValueError("MemPalace artifact question roster differs from LongMemEval")

    custom_any = {5: 0, 10: 0}
    official_all = {5: 0, 10: 0}
    official_ndcg = {5: 0.0, 10: 0.0}
    official_count = 0
    abstention_count = 0
    for row in rows:
        question_id = row["question_id"]
        source = by_id[question_id]
        if row.get("question") != source.get("question") or row.get("answer") != source.get(
            "answer"
        ):
            raise ValueError("MemPalace artifact question or answer drifted")
        retrieval = row.get("retrieval_results")
        ranked_items = retrieval.get("ranked_items") if isinstance(retrieval, dict) else None
        if not isinstance(ranked_items, list) or not ranked_items:
            raise ValueError("MemPalace artifact has no ranked items")
        ranked = [item.get("corpus_id") for item in ranked_items if isinstance(item, dict)]
        if len(ranked) != len(ranked_items) or any(
            not isinstance(document_id, str) or not document_id for document_id in ranked
        ):
            raise ValueError("MemPalace artifact ranking is malformed")
        sessions = source.get("haystack_sessions")
        session_ids = source.get("haystack_session_ids")
        if (
            not isinstance(sessions, list)
            or not isinstance(session_ids, list)
            or len(sessions) != len(session_ids)
        ):
            raise ValueError("LongMemEval haystack sessions are malformed")
        corpus_ids: list[str] = []
        for session, session_id in zip(sessions, session_ids, strict=True):
            if not isinstance(session, list) or not isinstance(session_id, str):
                raise ValueError("LongMemEval haystack session entry is malformed")
            if any(
                isinstance(turn, dict) and turn.get("role") == "user"
                for turn in session
            ):
                corpus_ids.append(session_id)
        ranked_counts = Counter(ranked)
        corpus_counts = Counter(corpus_ids)
        if any(count > corpus_counts[document_id] for document_id, count in ranked_counts.items()):
            raise ValueError("MemPalace artifact ranking exceeds its source corpus")
        haystack_ids = set(corpus_ids)
        correct = set(source.get("answer_session_ids", []))
        if not set(ranked).issubset(haystack_ids) or not correct.issubset(haystack_ids):
            raise ValueError("MemPalace artifact contains an unknown session ID")
        stored = retrieval.get("metrics")
        stored_session = stored.get("session") if isinstance(stored, dict) else None
        for k in (5, 10):
            any_hit = int(any(document_id in correct for document_id in ranked[:k]))
            custom_any[k] += any_hit
            if not isinstance(stored_session, dict) or stored_session.get(
                f"recall_any@{k}"
            ) != float(any_hit):
                raise ValueError("stored custom recall differs from recomputation")
        if "_abs" in question_id:
            abstention_count += 1
            continue
        official_count += 1
        for k in (5, 10):
            official_all[k] += int(correct.issubset(set(ranked[:k])))
            official_ndcg[k] += _official_ndcg(ranked, correct, corpus_ids, k)

    report = {
        "schema_version": 1,
        "status": "UPSTREAM_ARTIFACT_AUDITED_NOT_REPRODUCED",
        "scientific_result": False,
        "claim_scope": "released-artifact-integrity-and-metric-recomputation-only",
        "source": {
            "repository": "https://github.com/MemPalace/mempalace",
            "revision": MEMPALACE_REVISION,
            "tree_sha": MEMPALACE_TREE,
            "source_archive_sha256": MEMPALACE_SOURCE_ARCHIVE_SHA256,
            "runner_sha256": expectations.runner_sha256,
            "current_uv_lock_sha256": expectations.lock_sha256,
        },
        "released_artifact": {
            "path": MEMPALACE_RELEASED_RAW_ARTIFACT,
            "sha256": expectations.result_sha256,
            "rows": len(rows),
            "contains_reference_answers": True,
            "quarantine_from_actor_inputs": True,
            "artifact_commit": MEMPALACE_ARTIFACT_COMMIT,
            "artifact_lock_sha256": MEMPALACE_ARTIFACT_LOCK_SHA256,
            "artifact_chromadb_version": MEMPALACE_ARTIFACT_CHROMADB_VERSION,
            "current_chromadb_version": MEMPALACE_CURRENT_CHROMADB_VERSION,
            "current_lock_reproduction_required": True,
        },
        "dataset": {
            "repository_revision": LONGMEMEVAL_REPOSITORY_REVISION,
            "dataset_revision": LONGMEMEVAL_DATASET_REVISION,
            "sha256": expectations.dataset_sha256,
            "rows": len(dataset),
            "abstention_rows": abstention_count,
        },
        "metrics": {
            "mempalace_custom_recall_any_at_5": custom_any[5] / len(rows),
            "mempalace_custom_recall_any_at_10": custom_any[10] / len(rows),
            "official_non_abstention_count": official_count,
            "official_recall_all_at_5": official_all[5] / official_count,
            "official_recall_all_at_10": official_all[10] / official_count,
            "official_ndcg_any_at_5": official_ndcg[5] / official_count,
            "official_ndcg_any_at_10": official_ndcg[10] / official_count,
            "official_metric_code": {
                "repository_revision": LONGMEMEVAL_REPOSITORY_REVISION,
                "print_retrieval_metrics_sha256": LONGMEMEVAL_OFFICIAL_METRICS_SHA256,
                "eval_utils_sha256": LONGMEMEVAL_OFFICIAL_EVAL_UTILS_SHA256,
            },
        },
        "required_fresh_tests": [
            "two offline current-lock container runs have identical ordered rankings",
            "current-lock custom recall_any@5 reproduces 483/500",
            "permuting answer and answer_session_ids leaves every ranking unchanged",
            "mutating assistant turns leaves raw user-only rankings unchanged",
            "matched mechanism port is not labeled byte-exact unless all ranks match",
        ],
    }
    return {**report, "report_sha256": sha256_text(canonical_json(report))}


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise ValueError(f"refusing to overwrite audit report: {path}")
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    encoded = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode()
    with temporary.open("xb", buffering=0) as handle:
        handle.write(encoded)
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--result", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = args.result or args.source_root / MEMPALACE_RELEASED_RAW_ARTIFACT
    try:
        report = audit_upstream_artifact(
            source_root=args.source_root,
            dataset_path=args.dataset,
            result_path=result,
        )
        _write_report(args.output, report)
    except ValueError as exc:
        parser.error(str(exc))
    print(
        f"{report['status']} rows={report['released_artifact']['rows']} "
        f"report={report['report_sha256']} output={args.output.resolve()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
