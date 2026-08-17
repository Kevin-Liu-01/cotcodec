#!/usr/bin/env python3
"""Run the pinned MemPalace raw retriever with durable per-question resume.

The wrapper imports the exact reviewed upstream ``build_palace_and_retrieve``
function but owns the cluster contract: source/runtime verification, ordered
task coverage, hash-chained append-only records, atomic progress, USR1 stops,
and deterministic finalization.  It never calls an LLM and never reads labels
before retrieval.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
import re
import signal
import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials.mempalace_control import (  # noqa: E402
    MEMPALACE_CHROMADB_VERSION,
    MEMPALACE_MINILM_ARCHIVE_SHA256,
    MEMPALACE_MINILM_MODEL,
    MEMPALACE_REVISION,
    MEMPALACE_RUNNER_SHA256,
    MEMPALACE_SOURCE_ARCHIVE_SHA256,
    MEMPALACE_TREE,
    MEMPALACE_UV_LOCK_SHA256,
)
from harness.memory_trials.public_sources import (  # noqa: E402
    LONGMEMEVAL_DATASET_REVISION,
    LONGMEMEVAL_S_SHA256,
    LONGMEMEVAL_S_SIZE,
)
from harness.memory_trials.schema import canonical_json, sha256_text  # noqa: E402
from scripts.audit_mempalace_upstream_artifact import (  # noqa: E402
    MEMPALACE_LICENSE_SHA256,
    MEMPALACE_PYPROJECT_SHA256,
)

Retrieval = Callable[
    [dict[str, Any]], tuple[list[int], list[str], list[str], list[str]]
]


@dataclass(frozen=True)
class ReproductionExpectations:
    runner_sha256: str = MEMPALACE_RUNNER_SHA256
    lock_sha256: str = MEMPALACE_UV_LOCK_SHA256
    license_sha256: str = MEMPALACE_LICENSE_SHA256
    pyproject_sha256: str = MEMPALACE_PYPROJECT_SHA256
    source_archive_sha256: str = MEMPALACE_SOURCE_ARCHIVE_SHA256
    dataset_sha256: str = LONGMEMEVAL_S_SHA256
    dataset_size: int = LONGMEMEVAL_S_SIZE


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _absolute_without_symlinks(path: Path, description: str) -> Path:
    absolute = Path(os.path.abspath(os.fspath(path)))
    for component in (absolute, *absolute.parents):
        if component.is_symlink():
            raise ValueError(f"{description} cannot contain symbolic links: {component}")
    return absolute


def _verify_file(path: Path, sha256: str, size: int | None = None) -> None:
    path = _absolute_without_symlinks(path, "required input path")
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"required input must be a regular non-symlink file: {path}")
    if size is not None and path.stat().st_size != size:
        raise ValueError(f"input size mismatch: {path}")
    if _sha256_file(path) != sha256:
        raise ValueError(f"input SHA-256 mismatch: {path}")


def _atomic_write(path: Path, payload: bytes) -> None:
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("xb", buffering=0) as handle:
        handle.write(payload)
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    _atomic_write(path, (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode())


def _load_runtime_receipt(
    path: Path, expectations: ReproductionExpectations
) -> tuple[dict[str, Any], str]:
    _verify_file(path, _sha256_file(path))
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("runtime receipt is not valid JSON") from exc
    if not isinstance(receipt, dict):
        raise ValueError("runtime receipt must be one JSON object")
    status = receipt.get("status")
    if status not in {
        "VERIFIED_OFFLINE_MEMPALACE_RUNTIME",
        "SELF_ATTESTED_DISCOVERY_MEMPALACE_RUNTIME",
    }:
        raise ValueError("runtime receipt field 'status' drifted")
    if status == "SELF_ATTESTED_DISCOVERY_MEMPALACE_RUNTIME" and (
        receipt.get("external_attestation") is not False
        or receipt.get("publication_ready") is not False
        or receipt.get("scientific_result") is not False
    ):
        raise ValueError("self-attested discovery runtime is mislabeled")
    expected = {
        "schema_version": 1,
        "repository_revision": MEMPALACE_REVISION,
        "repository_tree": MEMPALACE_TREE,
        "source_archive_sha256": expectations.source_archive_sha256,
        "runner_sha256": expectations.runner_sha256,
        "uv_lock_sha256": expectations.lock_sha256,
        "chromadb_version": MEMPALACE_CHROMADB_VERSION,
        "embedding_model": MEMPALACE_MINILM_MODEL,
        "embedding_archive_sha256": MEMPALACE_MINILM_ARCHIVE_SHA256,
        "execution_provider": "CPUExecutionProvider",
        "network_policy": "none",
    }
    for field, value in expected.items():
        if receipt.get(field) != value:
            raise ValueError(f"runtime receipt field {field!r} drifted")
    for field in (
        "image_id",
        "image_sbom_sha256",
        "embedding_artifact_root_sha256",
        "minilm_receipt_sha256",
    ):
        value = receipt.get(field)
        prefix = "sha256:" if field == "image_id" else ""
        digest = value.removeprefix(prefix) if isinstance(value, str) else ""
        if not isinstance(value, str) or not value.startswith(prefix) or (
            len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise ValueError(f"runtime receipt field {field!r} is not a SHA-256 identity")
    for field in ("cotcodec_base_image_reference", "image_repo_digest"):
        reference = receipt.get(field)
        if not isinstance(reference, str) or re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[0-9a-f]{64}", reference
        ) is None:
            raise ValueError(f"runtime receipt field {field!r} is not immutable")
    return receipt, _sha256_file(path)


def _load_dataset(
    path: Path, expectations: ReproductionExpectations
) -> list[dict[str, Any]]:
    _verify_file(path, expectations.dataset_sha256, expectations.dataset_size)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("LongMemEval dataset is not valid JSON") from exc
    if not isinstance(payload, list) or not payload:
        raise ValueError("LongMemEval dataset must be a non-empty array")
    rows = [row for row in payload if isinstance(row, dict)]
    question_ids = [row.get("question_id") for row in rows]
    if (
        len(rows) != len(payload)
        or any(not isinstance(question_id, str) or not question_id for question_id in question_ids)
        or len(question_ids) != len(set(question_ids))
    ):
        raise ValueError("LongMemEval rows and question IDs must be valid and unique")
    return rows


def _verify_source_root(
    source_root: Path, expectations: ReproductionExpectations
) -> Path:
    source_root = _absolute_without_symlinks(source_root, "source root")
    _verify_file(
        source_root / "benchmarks/longmemeval_bench.py", expectations.runner_sha256
    )
    _verify_file(source_root / "uv.lock", expectations.lock_sha256)
    _verify_file(source_root / "LICENSE", expectations.license_sha256)
    _verify_file(source_root / "pyproject.toml", expectations.pyproject_sha256)
    return source_root


def _evaluate(
    rankings: list[int], correct_ids: set[str], corpus_ids: list[str], k: int
) -> tuple[float, float, float]:
    """Reproduce MemPalace's released custom metrics, not official LME NDCG.

    In particular, the upstream ``ndcg_any`` ideal is formed from retrieved
    hits.  The separately pinned artifact auditor computes official LongMemEval
    ``recall_all`` and NDCG from the complete relevant-session set.
    """
    top_ids = {corpus_ids[index] for index in rankings[:k]}
    recall_any = float(any(item in top_ids for item in correct_ids))
    recall_all = float(all(item in top_ids for item in correct_ids))
    relevances = [1.0 if corpus_ids[index] in correct_ids else 0.0 for index in rankings[:k]]
    ideal = sorted(relevances, reverse=True)

    def dcg(values: list[float]) -> float:
        return sum(value / math.log2(index + 2) for index, value in enumerate(values))

    denominator = dcg(ideal)
    ndcg = 0.0 if denominator == 0 else dcg(relevances) / denominator
    return recall_any, recall_all, ndcg


def _build_result_row(entry: dict[str, Any], retrieve: Retrieval) -> dict[str, Any]:
    # The backend receives only the four fields read by the pinned raw runner.
    # This positive contract excludes current and future benchmark labels such
    # as answer, answer_session_ids, has_answer, category, and split metadata.
    retrieval_fields = (
        "question",
        "haystack_sessions",
        "haystack_session_ids",
        "haystack_dates",
    )
    missing = [field for field in retrieval_fields if field not in entry]
    if missing:
        raise ValueError(f"retrieval row is missing required fields: {missing}")
    retrieval_entry = {field: entry[field] for field in retrieval_fields}
    rankings, corpus, corpus_ids, timestamps = retrieve(retrieval_entry)
    if not corpus or not rankings:
        raise ValueError(f"empty retrieval corpus for {entry.get('question_id')}")
    # The exact pinned upstream function asks Chroma for at most 50 hits, then
    # appends every unseen corpus index in source order.  Its public return is
    # therefore a complete permutation even when the retrieved prefix is top-50.
    if not (
        len(corpus) == len(corpus_ids) == len(timestamps) == len(rankings)
        and sorted(rankings) == list(range(len(corpus)))
    ):
        raise ValueError("upstream retriever did not return one complete corpus permutation")

    correct = set(entry["answer_session_ids"])
    metrics_session: dict[str, float] = {}
    metrics_turn: dict[str, float] = {}
    for k in (1, 3, 5, 10, 30, 50):
        recall_any, _recall_all, ndcg = _evaluate(rankings, correct, corpus_ids, k)
        metrics_session[f"recall_any@{k}"] = recall_any
        metrics_session[f"ndcg_any@{k}"] = ndcg
        metrics_turn[f"recall_any@{k}"] = recall_any
    ranked_items = [
        {
            "corpus_id": corpus_ids[index],
            "text": corpus[index][:500],
            "timestamp": timestamps[index],
        }
        for index in rankings[:50]
    ]
    return {
        "question_id": entry["question_id"],
        "question_type": entry["question_type"],
        "question": entry["question"],
        "answer": entry["answer"],
        "retrieval_results": {
            "query": entry["question"],
            "ranked_items": ranked_items,
            "metrics": {"session": metrics_session, "turn": metrics_turn},
        },
    }


def _journal_record(
    *, index: int, question_id: str, result: dict[str, Any], previous_sha256: str
) -> dict[str, Any]:
    unsigned = {
        "schema_version": 1,
        "index": index,
        "question_id": question_id,
        "result": result,
        "previous_record_sha256": previous_sha256,
    }
    return {**unsigned, "record_sha256": sha256_text(canonical_json(unsigned))}


def _load_journal(
    path: Path,
    dataset: list[dict[str, Any]],
    *,
    repair_incomplete_tail: bool = True,
) -> tuple[list[dict[str, Any]], str]:
    if not path.exists():
        return [], "0" * 64
    if not path.is_file() or path.is_symlink():
        raise ValueError("journal must be a regular non-symlink file")
    encoded = path.read_bytes()
    if encoded and not encoded.endswith(b"\n"):
        if not repair_incomplete_tail:
            raise ValueError("finalized journal has an incomplete tail")
        last_complete = encoded.rfind(b"\n")
        encoded = encoded[: last_complete + 1] if last_complete >= 0 else b""
        with path.open("r+b", buffering=0) as handle:
            handle.truncate(len(encoded))
            os.fsync(handle.fileno())
    records: list[dict[str, Any]] = []
    previous = "0" * 64
    for index, line in enumerate(encoded.splitlines()):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError("journal contains invalid JSON") from exc
        if not isinstance(record, dict) or index >= len(dataset):
            raise ValueError("journal record is outside the task roster")
        unsigned = {key: value for key, value in record.items() if key != "record_sha256"}
        expected = {
            "schema_version": 1,
            "index": index,
            "question_id": dataset[index]["question_id"],
            "previous_record_sha256": previous,
        }
        if any(record.get(field) != value for field, value in expected.items()):
            raise ValueError("journal ordering or hash-chain identity drifted")
        if record.get("record_sha256") != sha256_text(canonical_json(unsigned)):
            raise ValueError("journal record digest mismatch")
        result = record.get("result")
        if not isinstance(result, dict) or result.get("question_id") != expected["question_id"]:
            raise ValueError("journal result differs from its task identity")
        records.append(record)
        previous = record["record_sha256"]
    return records, previous


def _append_record(path: Path, record: dict[str, Any]) -> None:
    encoded = (canonical_json(record) + "\n").encode()
    with path.open("ab", buffering=0) as handle:
        handle.write(encoded)
        os.fsync(handle.fileno())


def _contract(
    *,
    expectations: ReproductionExpectations,
    runtime_receipt_sha256: str,
    runtime_receipt: dict[str, Any],
    task_ids: list[str],
) -> dict[str, Any]:
    unsigned = {
        "schema_version": 1,
        "status": "MEMPALACE_CURRENT_LOCK_REPRODUCTION_CONTRACT",
        "source": {
            "revision": MEMPALACE_REVISION,
            "tree": MEMPALACE_TREE,
            "source_archive_sha256": expectations.source_archive_sha256,
            "runner_sha256": expectations.runner_sha256,
            "uv_lock_sha256": expectations.lock_sha256,
        },
        "dataset": {
            "revision": LONGMEMEVAL_DATASET_REVISION,
            "sha256": expectations.dataset_sha256,
            "size": expectations.dataset_size,
            "task_count": len(task_ids),
            "ordered_task_ids_sha256": sha256_text(canonical_json(task_ids)),
        },
        "runtime_receipt_sha256": runtime_receipt_sha256,
        "runtime": runtime_receipt,
        "retrieval": {
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
        },
    }
    return {**unsigned, "contract_sha256": sha256_text(canonical_json(unsigned))}


def _progress(
    *, completed: int, total: int, final_record_sha256: str, contract_sha256: str
) -> dict[str, Any]:
    unsigned = {
        "schema_version": 1,
        "status": "COMPLETE" if completed == total else "CHECKPOINTED",
        "completed": completed,
        "total": total,
        "next_index": completed,
        "final_record_sha256": final_record_sha256,
        "contract_sha256": contract_sha256,
    }
    return {**unsigned, "progress_sha256": sha256_text(canonical_json(unsigned))}


def _validate_completed_bundle(
    *,
    output_dir: Path,
    records: list[dict[str, Any]],
    final_record_sha256: str,
    contract_sha256: str,
) -> dict[str, Any]:
    expected_names = {
        "contract.json",
        "journal.jsonl",
        "manifest.json",
        "progress.json",
        "results.jsonl",
    }
    actual_names = {path.name for path in output_dir.iterdir()}
    if actual_names != expected_names or any(path.is_symlink() for path in output_dir.iterdir()):
        raise ValueError("completed reproduction bundle file roster drifted")
    manifest_path = output_dir / "manifest.json"
    results_path = output_dir / "results.jsonl"
    journal_path = output_dir / "journal.jsonl"
    progress_path = output_dir / "progress.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        progress = json.loads(progress_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("completed reproduction metadata is invalid") from exc
    if not isinstance(manifest, dict) or not isinstance(progress, dict):
        raise ValueError("completed reproduction metadata must contain objects")
    unsigned_manifest = {
        key: value for key, value in manifest.items() if key != "manifest_sha256"
    }
    expected_manifest = {
        "schema_version": 1,
        "status": "MEMPALACE_CURRENT_LOCK_REPRODUCTION_COMPLETE",
        "scientific_result": False,
        "reason": "retrieval reproduction only; no actor or QA result",
        "contract_sha256": contract_sha256,
        "task_count": len(records),
        "journal_sha256": _sha256_file(journal_path),
        "results_sha256": _sha256_file(results_path),
        "final_record_sha256": final_record_sha256,
    }
    if unsigned_manifest != expected_manifest or manifest.get(
        "manifest_sha256"
    ) != sha256_text(canonical_json(expected_manifest)):
        raise ValueError("completed reproduction manifest differs from its artifacts")
    expected_results = b"".join(
        (canonical_json(record["result"]) + "\n").encode() for record in records
    )
    if results_path.read_bytes() != expected_results:
        raise ValueError("completed reproduction results differ from the journal")
    expected_progress = _progress(
        completed=len(records),
        total=len(records),
        final_record_sha256=final_record_sha256,
        contract_sha256=contract_sha256,
    )
    if progress != expected_progress:
        raise ValueError("completed reproduction progress differs from the journal")
    return manifest


def run_reproduction(
    *,
    source_root: Path,
    dataset_path: Path,
    runtime_receipt_path: Path,
    output_dir: Path,
    retrieve: Retrieval,
    resume: bool,
    stop_requested: Callable[[], bool] = lambda: False,
    checkpoint_marker: Path | None = None,
    expectations: ReproductionExpectations | None = None,
) -> dict[str, Any]:
    expectations = expectations or ReproductionExpectations()
    source_root = _verify_source_root(source_root, expectations)
    dataset = _load_dataset(dataset_path, expectations)
    runtime, runtime_sha256 = _load_runtime_receipt(
        runtime_receipt_path, expectations
    )
    contract = _contract(
        expectations=expectations,
        runtime_receipt_sha256=runtime_sha256,
        runtime_receipt=runtime,
        task_ids=[row["question_id"] for row in dataset],
    )

    output_dir = _absolute_without_symlinks(output_dir, "output directory")
    if output_dir.exists() and not resume:
        raise ValueError(f"output directory already exists; pass resume: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    if output_dir.is_symlink():
        raise ValueError("output directory cannot be a symbolic link")
    contract_path = output_dir / "contract.json"
    if contract_path.exists():
        try:
            existing = json.loads(contract_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("existing reproduction contract is invalid") from exc
        if existing != contract:
            raise ValueError("resume contract differs from the existing run")
    else:
        _write_json(contract_path, contract)

    journal_path = output_dir / "journal.jsonl"
    manifest_path = output_dir / "manifest.json"
    records, previous = _load_journal(
        journal_path,
        dataset,
        repair_incomplete_tail=not manifest_path.exists(),
    )
    if manifest_path.exists():
        if len(records) != len(dataset):
            raise ValueError("completed manifest exists before the task roster is complete")
        return _validate_completed_bundle(
            output_dir=output_dir,
            records=records,
            final_record_sha256=previous,
            contract_sha256=contract["contract_sha256"],
        )

    for index in range(len(records), len(dataset)):
        result = _build_result_row(dataset[index], retrieve)
        record = _journal_record(
            index=index,
            question_id=dataset[index]["question_id"],
            result=result,
            previous_sha256=previous,
        )
        _append_record(journal_path, record)
        records.append(record)
        previous = record["record_sha256"]
        progress = _progress(
            completed=len(records),
            total=len(dataset),
            final_record_sha256=previous,
            contract_sha256=contract["contract_sha256"],
        )
        _write_json(output_dir / "progress.json", progress)
        if stop_requested() and len(records) < len(dataset):
            if checkpoint_marker is not None:
                checkpoint_marker.parent.mkdir(parents=True, exist_ok=True)
                _atomic_write(checkpoint_marker, b"checkpointed\n")
            return progress

    result_bytes = b"".join(
        (canonical_json(record["result"]) + "\n").encode() for record in records
    )
    results_path = output_dir / "results.jsonl"
    if results_path.exists():
        if results_path.read_bytes() != result_bytes:
            raise ValueError("existing finalized results differ from the journal")
    else:
        _atomic_write(results_path, result_bytes)
    unsigned_manifest = {
        "schema_version": 1,
        "status": "MEMPALACE_CURRENT_LOCK_REPRODUCTION_COMPLETE",
        "scientific_result": False,
        "reason": "retrieval reproduction only; no actor or QA result",
        "contract_sha256": contract["contract_sha256"],
        "task_count": len(records),
        "journal_sha256": _sha256_file(journal_path),
        "results_sha256": _sha256_file(results_path),
        "final_record_sha256": previous,
    }
    manifest = {
        **unsigned_manifest,
        "manifest_sha256": sha256_text(canonical_json(unsigned_manifest)),
    }
    if manifest_path.exists():
        raise ValueError("refusing to overwrite a completed reproduction manifest")
    _write_json(manifest_path, manifest)
    return manifest


def _load_upstream_retriever(
    source_root: Path, expectations: ReproductionExpectations
) -> Retrieval:
    # Verify every imported source-contract file before Python executes any
    # byte from the caller-supplied source root.
    source_root = _verify_source_root(source_root, expectations)
    runner_path = source_root / "benchmarks/longmemeval_bench.py"
    if importlib.metadata.version("chromadb") != MEMPALACE_CHROMADB_VERSION:
        raise ValueError("installed ChromaDB differs from the pinned current lock")
    specification = importlib.util.spec_from_file_location(
        "cotcodec_pinned_mempalace_runner", runner_path
    )
    if specification is None or specification.loader is None:
        raise ValueError("cannot load the pinned MemPalace runner")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    upstream: ModuleType = module
    upstream._bench_embed_fn = None

    def retrieve(entry: dict[str, Any]) -> tuple[list[int], list[str], list[str], list[str]]:
        return upstream.build_palace_and_retrieve(
            entry, granularity="session", n_results=50
        )

    return retrieve


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--runtime-receipt", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    stop = threading.Event()
    signal.signal(signal.SIGUSR1, lambda _signum, _frame: stop.set())
    marker_value = os.environ.get("COTCODEC_CHECKPOINT_MARKER")
    marker = Path(marker_value) if marker_value else None
    expectations = ReproductionExpectations()
    try:
        retrieve = _load_upstream_retriever(args.source_root, expectations)
        result = run_reproduction(
            source_root=args.source_root,
            dataset_path=args.dataset,
            runtime_receipt_path=args.runtime_receipt,
            output_dir=args.output_dir,
            retrieve=retrieve,
            resume=args.resume,
            stop_requested=stop.is_set,
            checkpoint_marker=marker,
            expectations=expectations,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(canonical_json(result))
    return 0 if result["status"].endswith("COMPLETE") else 75


if __name__ == "__main__":
    raise SystemExit(main())
