#!/usr/bin/env python3
"""Validate and compare two complete pinned MemPalace reproduction bundles."""

from __future__ import annotations

import argparse
import json
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
    MEMPALACE_TREE,
)
from harness.memory_trials.public_sources import (  # noqa: E402
    LONGMEMEVAL_DATASET_REVISION,
)
from harness.memory_trials.schema import canonical_json, sha256_text  # noqa: E402
from scripts.audit_mempalace_upstream_artifact import _official_ndcg  # noqa: E402
from scripts.run_mempalace_upstream_reproduction import (  # noqa: E402
    ReproductionExpectations,
    _absolute_without_symlinks,
    _load_dataset,
    _load_runtime_receipt,
    _validate_completed_bundle,
)


@dataclass(frozen=True)
class PairTargets:
    released_recall_any_at_5_count: int = 483
    released_recall_any_at_10_count: int = 491


def _load_object(path: Path, description: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{description} must be a regular non-symlink file")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{description} is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{description} must contain one JSON object")
    return payload


def _validate_contract(
    path: Path,
    dataset: list[dict[str, Any]],
    expectations: ReproductionExpectations,
    runtime_receipt: dict[str, Any],
    runtime_receipt_sha256: str,
) -> dict[str, Any]:
    contract = _load_object(path, "reproduction contract")
    unsigned = {key: value for key, value in contract.items() if key != "contract_sha256"}
    if contract.get("contract_sha256") != sha256_text(canonical_json(unsigned)):
        raise ValueError("reproduction contract digest mismatch")
    expected_source = {
        "revision": MEMPALACE_REVISION,
        "tree": MEMPALACE_TREE,
        "source_archive_sha256": expectations.source_archive_sha256,
        "runner_sha256": expectations.runner_sha256,
        "uv_lock_sha256": expectations.lock_sha256,
    }
    expected_dataset = {
        "revision": LONGMEMEVAL_DATASET_REVISION,
        "sha256": expectations.dataset_sha256,
        "size": expectations.dataset_size,
        "task_count": len(dataset),
        "ordered_task_ids_sha256": sha256_text(
            canonical_json([row["question_id"] for row in dataset])
        ),
    }
    expected_retrieval = {
        "mode": "raw",
        "granularity": "session",
        "n_results": 50,
        "embed_model": "default",
        "network": "none",
        "labels_opened_after_retrieval": True,
        "metric_contract": {
            "stored_rows": "mempalace-custom-any-hit-v1",
            "ndcg_denominator": "retrieved-hits-only-upstream-custom",
            "official_longmemeval_metrics": (
                "external-auditor-complete-relevant-set-v1"
            ),
        },
    }
    if (
        contract.get("schema_version") != 1
        or contract.get("status") != "MEMPALACE_CURRENT_LOCK_REPRODUCTION_CONTRACT"
        or contract.get("source") != expected_source
        or contract.get("dataset") != expected_dataset
        or contract.get("retrieval") != expected_retrieval
        or contract.get("runtime") != runtime_receipt
        or contract.get("runtime_receipt_sha256") != runtime_receipt_sha256
    ):
        raise ValueError("reproduction contract differs from the pinned study")
    return contract


def _validate_bundle(
    bundle: Path,
    dataset: list[dict[str, Any]],
    expectations: ReproductionExpectations,
    runtime_receipt: dict[str, Any],
    runtime_receipt_sha256: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    bundle = _absolute_without_symlinks(bundle, "reproduction bundle")
    if not bundle.is_dir():
        raise ValueError("reproduction bundle must be a non-symlink directory")
    contract = _validate_contract(
        bundle / "contract.json",
        dataset,
        expectations,
        runtime_receipt,
        runtime_receipt_sha256,
    )
    records, final_record_sha256 = _load_journal_strict(
        bundle / "journal.jsonl", dataset
    )
    if len(records) != len(dataset):
        raise ValueError("reproduction bundle is not complete")
    manifest = _validate_completed_bundle(
        output_dir=bundle,
        records=records,
        final_record_sha256=final_record_sha256,
        contract_sha256=contract["contract_sha256"],
    )
    return contract, records, manifest


def _load_journal_strict(
    path: Path, dataset: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], str]:
    """Read a finalized journal without resume-mode tail repair."""

    if not path.is_file() or path.is_symlink():
        raise ValueError("journal must be a regular non-symlink file")
    encoded = path.read_bytes()
    if not encoded or not encoded.endswith(b"\n"):
        raise ValueError("finalized journal has an incomplete or empty tail")
    records: list[dict[str, Any]] = []
    previous = "0" * 64
    for index, line in enumerate(encoded.splitlines()):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError("journal contains invalid JSON") from exc
        if not isinstance(record, dict) or index >= len(dataset):
            raise ValueError("journal record is outside the task roster")
        expected = {
            "schema_version": 1,
            "index": index,
            "question_id": dataset[index]["question_id"],
            "previous_record_sha256": previous,
        }
        if any(record.get(field) != value for field, value in expected.items()):
            raise ValueError("journal ordering or hash-chain identity drifted")
        unsigned = {key: value for key, value in record.items() if key != "record_sha256"}
        if record.get("record_sha256") != sha256_text(canonical_json(unsigned)):
            raise ValueError("journal record digest mismatch")
        result = record.get("result")
        if not isinstance(result, dict) or result.get("question_id") != expected[
            "question_id"
        ]:
            raise ValueError("journal result differs from its task identity")
        records.append(record)
        previous = record["record_sha256"]
    return records, previous


def _rankings_and_metrics(
    records: list[dict[str, Any]], dataset: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, float | int]]:
    rankings: list[dict[str, Any]] = []
    any_at_5 = 0
    any_at_10 = 0
    all_at_5 = 0
    all_at_10 = 0
    ndcg_at_5 = 0.0
    ndcg_at_10 = 0.0
    official_count = 0
    for record, source in zip(records, dataset, strict=True):
        result = record["result"]
        if (
            result.get("question_id") != source["question_id"]
            or result.get("question") != source.get("question")
            or result.get("answer") != source.get("answer")
        ):
            raise ValueError("reproduction result differs from the pinned task")
        retrieval = result.get("retrieval_results")
        ranked_items = retrieval.get("ranked_items") if isinstance(retrieval, dict) else None
        if not isinstance(ranked_items, list) or not ranked_items:
            raise ValueError("reproduction result has an empty ranking")
        ranked = [
            item.get("corpus_id") for item in ranked_items if isinstance(item, dict)
        ]
        if len(ranked) != len(ranked_items) or any(
            not isinstance(item, str) or not item for item in ranked
        ):
            raise ValueError("reproduction result has a malformed ranking")
        sessions = source.get("haystack_sessions")
        session_ids = source.get("haystack_session_ids")
        if not isinstance(sessions, list) or not isinstance(session_ids, list) or len(
            sessions
        ) != len(session_ids):
            raise ValueError("LongMemEval source sessions are malformed")
        corpus_ids = [
            session_id
            for session, session_id in zip(sessions, session_ids, strict=True)
            if isinstance(session, list)
            and isinstance(session_id, str)
            and any(
                isinstance(turn, dict) and turn.get("role") == "user"
                for turn in session
            )
        ]
        expected_rank_count = min(50, len(corpus_ids))
        if len(ranked) != expected_rank_count:
            raise ValueError("reproduction ranking length differs from the pinned top-50")
        ranked_counts = Counter(ranked)
        corpus_counts = Counter(corpus_ids)
        if any(
            count > corpus_counts[corpus_id]
            for corpus_id, count in ranked_counts.items()
        ):
            raise ValueError("reproduction ranking exceeds its source corpus")
        correct = set(source.get("answer_session_ids", []))
        if not correct.issubset(set(corpus_ids)):
            raise ValueError("LongMemEval answer session is absent from the source corpus")
        any_at_5 += int(any(item in correct for item in ranked[:5]))
        any_at_10 += int(any(item in correct for item in ranked[:10]))
        rankings.append({"question_id": source["question_id"], "corpus_ids": ranked})
        if "_abs" in source["question_id"]:
            continue
        official_count += 1
        all_at_5 += int(correct.issubset(set(ranked[:5])))
        all_at_10 += int(correct.issubset(set(ranked[:10])))
        ndcg_at_5 += _official_ndcg(ranked, correct, corpus_ids, 5)
        ndcg_at_10 += _official_ndcg(ranked, correct, corpus_ids, 10)
    if official_count <= 0:
        raise ValueError("reproduction contains no official non-abstention tasks")
    return rankings, {
        "task_count": len(records),
        "custom_recall_any_at_5_count": any_at_5,
        "custom_recall_any_at_5": any_at_5 / len(records),
        "custom_recall_any_at_10_count": any_at_10,
        "custom_recall_any_at_10": any_at_10 / len(records),
        "official_non_abstention_count": official_count,
        "official_recall_all_at_5": all_at_5 / official_count,
        "official_recall_all_at_10": all_at_10 / official_count,
        "official_ndcg_at_5": ndcg_at_5 / official_count,
        "official_ndcg_at_10": ndcg_at_10 / official_count,
    }


def compare_reproductions(
    *,
    bundle_a: Path,
    bundle_b: Path,
    dataset_path: Path,
    runtime_receipt_path: Path,
    expected_runtime_receipt_sha256: str,
    expectations: ReproductionExpectations | None = None,
    targets: PairTargets | None = None,
) -> dict[str, Any]:
    expectations = expectations or ReproductionExpectations()
    targets = targets or PairTargets()
    dataset = _load_dataset(dataset_path.resolve(), expectations)
    runtime_receipt, runtime_receipt_sha256 = _load_runtime_receipt(
        runtime_receipt_path.resolve(), expectations
    )
    if runtime_receipt_sha256 != expected_runtime_receipt_sha256:
        raise ValueError("external runtime receipt digest differs from the registered study")
    contract_a, records_a, manifest_a = _validate_bundle(
        bundle_a,
        dataset,
        expectations,
        runtime_receipt,
        runtime_receipt_sha256,
    )
    contract_b, records_b, manifest_b = _validate_bundle(
        bundle_b,
        dataset,
        expectations,
        runtime_receipt,
        runtime_receipt_sha256,
    )
    rankings_a, metrics_a = _rankings_and_metrics(records_a, dataset)
    rankings_b, metrics_b = _rankings_and_metrics(records_b, dataset)
    first_mismatch = next(
        (
            row_a["question_id"]
            for row_a, row_b in zip(rankings_a, rankings_b, strict=True)
            if row_a != row_b
        ),
        None,
    )
    gates = {
        "contracts_identical": contract_a == contract_b,
        "ordered_rankings_identical": rankings_a == rankings_b,
        "results_identical": manifest_a["results_sha256"]
        == manifest_b["results_sha256"],
        "metrics_identical": metrics_a == metrics_b,
        "released_any_at_5_reproduced": metrics_a[
            "custom_recall_any_at_5_count"
        ]
        == targets.released_recall_any_at_5_count,
        "released_any_at_10_reproduced": metrics_a[
            "custom_recall_any_at_10_count"
        ]
        == targets.released_recall_any_at_10_count,
    }
    passed = all(gates.values())
    unsigned = {
        "schema_version": 1,
        "status": (
            "MEMPALACE_CURRENT_LOCK_PAIR_REPRODUCTION_PASS"
            if passed
            else "MEMPALACE_CURRENT_LOCK_PAIR_REPRODUCTION_FAIL"
        ),
        "scientific_result": False,
        "reason": "retrieval reproduction only; no actor or QA result",
        "bundle_a_manifest_sha256": manifest_a["manifest_sha256"],
        "bundle_b_manifest_sha256": manifest_b["manifest_sha256"],
        "contract_sha256": contract_a["contract_sha256"],
        "rankings_a_sha256": sha256_text(canonical_json(rankings_a)),
        "rankings_b_sha256": sha256_text(canonical_json(rankings_b)),
        "first_ranking_mismatch_question_id": first_mismatch,
        "metrics_a": metrics_a,
        "metrics_b": metrics_b,
        "released_targets": {
            "custom_recall_any_at_5_count": targets.released_recall_any_at_5_count,
            "custom_recall_any_at_10_count": targets.released_recall_any_at_10_count,
        },
        "gates": gates,
    }
    return {**unsigned, "report_sha256": sha256_text(canonical_json(unsigned))}


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    encoded = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode()
    try:
        with temporary.open("xb", buffering=0) as handle:
            handle.write(encoded)
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as exc:
            raise ValueError(f"refusing to overwrite comparison report: {path}") from exc
        temporary.unlink()
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-a", type=Path, required=True)
    parser.add_argument("--bundle-b", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--runtime-receipt", type=Path, required=True)
    parser.add_argument("--runtime-receipt-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-gates", action="store_true")
    args = parser.parse_args()
    try:
        report = compare_reproductions(
            bundle_a=args.bundle_a,
            bundle_b=args.bundle_b,
            dataset_path=args.dataset,
            runtime_receipt_path=args.runtime_receipt,
            expected_runtime_receipt_sha256=args.runtime_receipt_sha256,
        )
        _write_report(args.output, report)
    except ValueError as exc:
        parser.error(str(exc))
    print(canonical_json(report))
    return int(args.require_gates and not all(report["gates"].values()))


if __name__ == "__main__":
    raise SystemExit(main())
