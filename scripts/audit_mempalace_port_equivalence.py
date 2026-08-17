#!/usr/bin/env python3
"""Audit the matched MemPalace port against a sealed direct reproduction.

The direct upstream runner and the matched harness port intentionally use
different input objects.  This audit executes the port over the same ordered
LongMemEval rows, translates the raw session IDs into the harness's opaque
identifiers, and compares every top-50 rank.  It also records preprocessing
drift (query whitespace, session order/roster, and user-only document bytes)
separately from retrieval drift.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import sys
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials import (  # noqa: E402
    LONGMEMEVAL_RETRIEVAL_ARTIFACT_ROLE,
    LongMemEvalTaskSource,
    MemPalaceRetrievalPort,
    MemPalaceRuntimeIdentity,
    build_memory_system_request,
    build_mempalace_session_documents,
)
from harness.memory_trials.schema import canonical_json, sha256_text  # noqa: E402
from scripts.compare_mempalace_reproductions import _validate_bundle  # noqa: E402
from scripts.mempalace_upstream_adapter import (  # noqa: E402
    PinnedUpstreamMemPalaceAdapter,
)
from scripts.run_mempalace_upstream_reproduction import (  # noqa: E402
    ReproductionExpectations,
    _absolute_without_symlinks,
    _append_record,
    _atomic_write,
    _journal_record,
    _load_dataset,
    _load_journal,
    _load_runtime_receipt,
    _progress,
    _sha256_file,
    _write_json,
)

StopRequested = Callable[[], bool]
RawSessionRef = tuple[str, str]


def _direct_rankings(
    records: list[dict[str, Any]],
) -> dict[str, tuple[RawSessionRef, ...]]:
    rankings: dict[str, tuple[RawSessionRef, ...]] = {}
    for record in records:
        result = record["result"]
        items = result.get("retrieval_results", {}).get("ranked_items")
        if not isinstance(items, list) or not items:
            raise ValueError("direct reproduction contains an empty ranking")
        ranked = tuple(
            (item.get("corpus_id"), item.get("timestamp"))
            for item in items
            if isinstance(item, dict)
        )
        if len(ranked) != len(items) or any(
            not isinstance(session_id, str)
            or not session_id
            or not isinstance(timestamp, str)
            or not timestamp
            for session_id, timestamp in ranked
        ):
            raise ValueError("direct reproduction contains a malformed ranking")
        question_id = result["question_id"]
        if question_id in rankings:
            raise ValueError("direct reproduction repeats a question ID")
        rankings[question_id] = ranked
    return rankings


def _raw_session_documents(
    row: dict[str, Any],
) -> tuple[tuple[RawSessionRef, str], ...]:
    documents: list[tuple[RawSessionRef, str]] = []
    for session_id, timestamp, session in zip(
        row["haystack_session_ids"],
        row["haystack_dates"],
        row["haystack_sessions"],
        strict=True,
    ):
        user_turns = [
            turn["content"]
            for turn in session
            if isinstance(turn, dict) and turn.get("role") == "user"
        ]
        if user_turns:
            documents.append(((session_id, timestamp), "\n".join(user_turns)))
    return tuple(documents)


def _raw_to_opaque_session_ids(
    *, row: dict[str, Any], task: Any, request: Any
) -> dict[RawSessionRef, str]:
    digest_to_raw: dict[tuple[str, str], RawSessionRef] = {}
    for session_id, timestamp in zip(
        row["haystack_session_ids"], row["haystack_dates"], strict=True
    ):
        digest = hashlib.sha256(session_id.encode()).hexdigest()
        lineage = (digest, timestamp)
        if lineage in digest_to_raw:
            raise ValueError(
                "LongMemEval row repeats a session identity and timestamp"
            )
        digest_to_raw[lineage] = (session_id, timestamp)
    included = tuple(event for event in task.events if event.step < task.eligibility_step)
    if len(included) != len(request.events):
        raise ValueError("serve request omitted a prefix event")
    mapping: dict[RawSessionRef, str] = {}
    for task_event, request_event in zip(included, request.events, strict=True):
        source_digest = task_event.metadata.get("source_session_sha256")
        source_timestamp = task_event.metadata.get("session_date")
        raw_ref = digest_to_raw.get((source_digest, source_timestamp))
        if raw_ref is None:
            raise ValueError("task event lost its source-session lineage")
        previous = mapping.setdefault(raw_ref, request_event.entity_id)
        if previous != request_event.entity_id:
            raise ValueError(
                "one raw session occurrence mapped to multiple opaque sessions"
            )
    return mapping


def _render_session_refs(refs: tuple[RawSessionRef, ...]) -> list[dict[str, str]]:
    return [
        {"corpus_id": session_id, "timestamp": timestamp}
        for session_id, timestamp in refs
    ]


def _audit_one(
    *,
    row: dict[str, Any],
    task: Any,
    retrieval: MemPalaceRetrievalPort,
    direct_ranked_raw_ids: tuple[RawSessionRef, ...],
) -> dict[str, Any]:
    request, _expected = build_memory_system_request(
        task, visibility="serve", treatment_mode="storage_and_service"
    )
    documents = build_mempalace_session_documents(request)
    if not documents:
        raise ValueError("matched MemPalace port produced no session documents")
    raw_to_opaque = _raw_to_opaque_session_ids(row=row, task=task, request=request)
    direct_documents = _raw_session_documents(row)
    direct_ids = tuple(session_ref for session_ref, _text in direct_documents)
    port_ids = tuple(document.document_id for document in documents)
    translated_direct_ids = tuple(
        raw_to_opaque[session_ref]
        for session_ref in direct_ids
        if session_ref in raw_to_opaque
    )
    unmapped_direct_ids = tuple(
        session_ref for session_ref in direct_ids if session_ref not in raw_to_opaque
    )
    direct_text = dict(direct_documents)
    opaque_to_raw = {opaque: raw for raw, opaque in raw_to_opaque.items()}
    port_text_by_raw = {
        opaque_to_raw[document.document_id]: document.text
        for document in documents
        if document.document_id in opaque_to_raw
    }
    text_exact = (
        not unmapped_direct_ids
        and set(port_text_by_raw) == set(direct_text)
        and all(port_text_by_raw[key] == value for key, value in direct_text.items())
    )

    batch = retrieval.retrieve(
        query=request.query,
        documents=documents,
        n_results=min(50, len(documents)),
    )
    translated_direct_ranking = tuple(
        raw_to_opaque[session_ref]
        for session_ref in direct_ranked_raw_ids
        if session_ref in raw_to_opaque
    )
    unmapped_rank_ids = tuple(
        session_ref
        for session_ref in direct_ranked_raw_ids
        if session_ref not in raw_to_opaque
    )
    port_ranking = batch.ranked_document_ids
    ranking_exact = (
        not unmapped_rank_ids and translated_direct_ranking == port_ranking
    )
    return {
        "question_id": row["question_id"],
        "task_id": task.task_id,
        "request_sha256": sha256_text(canonical_json(request.model_dump(mode="json"))),
        "query_exact": request.query == row["question"],
        "direct_session_count": len(direct_ids),
        "port_session_count": len(port_ids),
        "session_roster_exact": (
            not unmapped_direct_ids and set(translated_direct_ids) == set(port_ids)
        ),
        "session_order_exact": (
            not unmapped_direct_ids and translated_direct_ids == port_ids
        ),
        "session_text_exact": text_exact,
        "unmapped_direct_sessions": _render_session_refs(unmapped_direct_ids),
        "direct_ranked_sessions": _render_session_refs(direct_ranked_raw_ids),
        "translated_direct_ranked_ids": list(translated_direct_ranking),
        "port_ranked_document_ids": list(port_ranking),
        "unmapped_direct_ranked_sessions": _render_session_refs(unmapped_rank_ids),
        "ranking_exact": ranking_exact,
        "top_5_exact": translated_direct_ranking[:5] == port_ranking[:5],
        "top_10_exact": translated_direct_ranking[:10] == port_ranking[:10],
    }


def _contract(
    *,
    dataset: list[dict[str, Any]],
    source: LongMemEvalTaskSource,
    direct_manifest: dict[str, Any],
    direct_runtime_receipt: dict[str, Any],
    direct_runtime_receipt_sha256: str,
    port_runtime_receipt: dict[str, Any],
    port_runtime_receipt_sha256: str,
    retrieval_identity: MemPalaceRuntimeIdentity,
) -> dict[str, Any]:
    code_paths = (
        PROJECT_ROOT / "harness/memory_trials/mempalace_control.py",
        PROJECT_ROOT / "harness/memory_trials/public_sources.py",
        PROJECT_ROOT / "harness/memory_trials/schema.py",
        PROJECT_ROOT / "harness/memory_trials/systems.py",
        PROJECT_ROOT / "scripts/mempalace_upstream_adapter.py",
        PROJECT_ROOT / "scripts/compare_mempalace_reproductions.py",
        PROJECT_ROOT / "scripts/run_mempalace_upstream_reproduction.py",
        PROJECT_ROOT / "scripts/audit_mempalace_port_equivalence.py",
    )
    unsigned = {
        "schema_version": 2,
        "status": "MEMPALACE_MATCHED_PORT_EQUIVALENCE_CONTRACT",
        "scientific_result": False,
        "dataset": {
            "sha256": source.provenance["dataset_sha256"],
            "size": source.provenance["dataset_size"],
            "ordered_question_ids_sha256": sha256_text(
                canonical_json([row["question_id"] for row in dataset])
            ),
            "task_manifest_sha256": sha256_text(
                canonical_json([source.load(task_id).task_sha256 for task_id in source.ids()])
            ),
        },
        "direct_reproduction": {
            "manifest_sha256": direct_manifest["manifest_sha256"],
            "results_sha256": direct_manifest["results_sha256"],
            "journal_sha256": direct_manifest["journal_sha256"],
            "runtime_receipt_sha256": direct_runtime_receipt_sha256,
            "runtime": direct_runtime_receipt,
        },
        "port": {
            "visibility": "serve",
            "treatment_mode": "storage_and_service",
            "upstream_top_k": 50,
            "session_document": "newline-joined-user-turns-only",
            "session_order": "source-artifact-order",
            "text_normalization": "verbatim-source-bytes",
            "runtime_receipt_sha256": port_runtime_receipt_sha256,
            "runtime": port_runtime_receipt,
            "runtime_identity": retrieval_identity.model_dump(mode="json"),
            "code_sha256": {
                str(path.relative_to(PROJECT_ROOT)): _sha256_file(path)
                for path in code_paths
            },
        },
    }
    return {**unsigned, "contract_sha256": sha256_text(canonical_json(unsigned))}


def _summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    results = [record["result"] for record in records]
    gate_names = (
        "query_exact",
        "session_roster_exact",
        "session_order_exact",
        "session_text_exact",
        "ranking_exact",
        "top_5_exact",
        "top_10_exact",
    )
    counts = {
        name: sum(bool(result[name]) for result in results) for name in gate_names
    }
    gates = {name: count == len(results) for name, count in counts.items()}
    return {
        "status": (
            "EXACT_MATCHED_PORT_EQUIVALENCE_PASS"
            if all(gates.values())
            else "MATCHED_PORT_PREPROCESSING_OR_RANKING_DRIFT"
        ),
        "scientific_result": False,
        "task_count": len(results),
        "exact_counts": counts,
        "gates": gates,
        "first_ranking_mismatches": [
            result["question_id"] for result in results if not result["ranking_exact"]
        ][:20],
        "first_preprocessing_mismatches": [
            result["question_id"]
            for result in results
            if not (
                result["query_exact"]
                and result["session_roster_exact"]
                and result["session_order_exact"]
                and result["session_text_exact"]
            )
        ][:20],
    }


def _validate_completed(
    *,
    output_dir: Path,
    records: list[dict[str, Any]],
    previous_sha256: str,
    contract: dict[str, Any],
) -> dict[str, Any]:
    expected_names = {
        "contract.json",
        "journal.jsonl",
        "manifest.json",
        "progress.json",
        "report.json",
    }
    if {path.name for path in output_dir.iterdir()} != expected_names or any(
        path.is_symlink() for path in output_dir.iterdir()
    ):
        raise ValueError("completed equivalence bundle file roster drifted")
    report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
    expected_report = _summarize(records)
    if report != expected_report:
        raise ValueError("equivalence report differs from the sealed journal")
    expected_progress = _progress(
        completed=len(records),
        total=len(records),
        final_record_sha256=previous_sha256,
        contract_sha256=contract["contract_sha256"],
    )
    progress = json.loads((output_dir / "progress.json").read_text(encoding="utf-8"))
    if progress != expected_progress:
        raise ValueError("equivalence progress differs from the sealed journal")
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    unsigned = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    expected_unsigned = {
        "schema_version": 1,
        "status": "MEMPALACE_MATCHED_PORT_EQUIVALENCE_COMPLETE",
        "scientific_result": False,
        "contract_sha256": contract["contract_sha256"],
        "task_count": len(records),
        "journal_sha256": _sha256_file(output_dir / "journal.jsonl"),
        "report_sha256": _sha256_file(output_dir / "report.json"),
        "final_record_sha256": previous_sha256,
        "all_gates_pass": all(report["gates"].values()),
    }
    if unsigned != expected_unsigned or manifest.get("manifest_sha256") != sha256_text(
        canonical_json(expected_unsigned)
    ):
        raise ValueError("equivalence manifest differs from its artifacts")
    return manifest


def _run_equivalence_audit(
    *,
    source_root: Path,
    dataset_path: Path,
    direct_bundle: Path,
    direct_runtime_receipt_path: Path,
    expected_direct_runtime_receipt_sha256: str,
    port_runtime_receipt_path: Path,
    expected_port_runtime_receipt_sha256: str,
    output_dir: Path,
    resume: bool,
    retrieval: MemPalaceRetrievalPort | None = None,
    stop_requested: StopRequested = lambda: False,
    checkpoint_marker: Path | None = None,
    expectations: ReproductionExpectations | None = None,
) -> dict[str, Any]:
    expectations = expectations or ReproductionExpectations()
    dataset = _load_dataset(dataset_path, expectations)
    direct_runtime_receipt, direct_runtime_receipt_sha256 = _load_runtime_receipt(
        direct_runtime_receipt_path, expectations
    )
    if direct_runtime_receipt_sha256 != expected_direct_runtime_receipt_sha256:
        raise ValueError(
            "direct runtime receipt differs from the registered equivalence study"
        )
    port_runtime_receipt, port_runtime_receipt_sha256 = _load_runtime_receipt(
        port_runtime_receipt_path, expectations
    )
    if port_runtime_receipt_sha256 != expected_port_runtime_receipt_sha256:
        raise ValueError(
            "port runtime receipt differs from the registered equivalence study"
        )
    _direct_contract, direct_records, direct_manifest = _validate_bundle(
        direct_bundle,
        dataset,
        expectations,
        direct_runtime_receipt,
        direct_runtime_receipt_sha256,
    )
    direct_rankings = _direct_rankings(direct_records)
    source = LongMemEvalTaskSource(
        dataset_path,
        expected_sha256=expectations.dataset_sha256,
        expected_size=expectations.dataset_size,
        artifact_role=LONGMEMEVAL_RETRIEVAL_ARTIFACT_ROLE,
        session_order="source",
        text_normalization="verbatim",
    )
    if len(source.ids()) != len(dataset):
        raise ValueError("matched task source does not cover the direct task roster")
    retrieval = retrieval or PinnedUpstreamMemPalaceAdapter(
        source_root=source_root,
        runtime_receipt_path=port_runtime_receipt_path,
        expected_runtime_receipt_sha256=expected_port_runtime_receipt_sha256,
        implementation_kind="in_process_reference",
    )
    expected_identity = MemPalaceRuntimeIdentity(
        model_artifact_root_sha256=port_runtime_receipt[
            "embedding_artifact_root_sha256"
        ],
        model_receipt_sha256=port_runtime_receipt["minilm_receipt_sha256"],
        image_digest=port_runtime_receipt["image_id"],
        implementation_kind="in_process_reference",
    )
    if retrieval.identity != expected_identity:
        raise ValueError("retrieval adapter identity differs from the runtime receipt")
    contract = _contract(
        dataset=dataset,
        source=source,
        direct_manifest=direct_manifest,
        direct_runtime_receipt=direct_runtime_receipt,
        direct_runtime_receipt_sha256=direct_runtime_receipt_sha256,
        port_runtime_receipt=port_runtime_receipt,
        port_runtime_receipt_sha256=port_runtime_receipt_sha256,
        retrieval_identity=retrieval.identity,
    )

    output_dir = _absolute_without_symlinks(output_dir, "output directory")
    if output_dir.exists() and not resume:
        raise ValueError(f"output directory already exists; pass resume: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    if output_dir.is_symlink():
        raise ValueError("output directory cannot be a symbolic link")
    allowed_children = {
        "contract.json",
        "journal.jsonl",
        "manifest.json",
        "progress.json",
        "report.json",
    }
    for child in output_dir.iterdir():
        if child.name not in allowed_children:
            raise ValueError("equivalence output directory has an unexpected artifact")
        if child.is_symlink() or not child.is_file():
            raise ValueError("equivalence artifacts must be regular non-symlink files")
    contract_path = output_dir / "contract.json"
    if contract_path.exists():
        if json.loads(contract_path.read_text(encoding="utf-8")) != contract:
            raise ValueError("resume contract differs from the existing equivalence audit")
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
            raise ValueError("completed equivalence manifest has an incomplete journal")
        return _validate_completed(
            output_dir=output_dir,
            records=records,
            previous_sha256=previous,
            contract=contract,
        )

    for index in range(len(records), len(dataset)):
        row = dataset[index]
        task = source.load(source.ids()[index])
        if source.evaluation_reference(task.task_id)["question_id"] != row["question_id"]:
            raise ValueError("matched task order differs from the direct dataset")
        result = _audit_one(
            row=row,
            task=task,
            retrieval=retrieval,
            direct_ranked_raw_ids=direct_rankings[row["question_id"]],
        )
        record = _journal_record(
            index=index,
            question_id=row["question_id"],
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

    report = _summarize(records)
    report_path = output_dir / "report.json"
    if report_path.exists():
        if json.loads(report_path.read_text(encoding="utf-8")) != report:
            raise ValueError("existing equivalence report differs from the journal")
    else:
        _write_json(report_path, report)
    unsigned_manifest = {
        "schema_version": 1,
        "status": "MEMPALACE_MATCHED_PORT_EQUIVALENCE_COMPLETE",
        "scientific_result": False,
        "contract_sha256": contract["contract_sha256"],
        "task_count": len(records),
        "journal_sha256": _sha256_file(journal_path),
        "report_sha256": _sha256_file(report_path),
        "final_record_sha256": previous,
        "all_gates_pass": all(report["gates"].values()),
    }
    manifest = {
        **unsigned_manifest,
        "manifest_sha256": sha256_text(canonical_json(unsigned_manifest)),
    }
    if manifest_path.exists():
        raise ValueError("refusing to overwrite a completed equivalence manifest")
    _write_json(manifest_path, manifest)
    return _validate_completed(
        output_dir=output_dir,
        records=records,
        previous_sha256=previous,
        contract=contract,
    )


def run_equivalence_audit(
    *,
    source_root: Path,
    dataset_path: Path,
    direct_bundle: Path,
    direct_runtime_receipt_path: Path,
    expected_direct_runtime_receipt_sha256: str,
    port_runtime_receipt_path: Path,
    expected_port_runtime_receipt_sha256: str,
    output_dir: Path,
    resume: bool,
    stop_requested: StopRequested = lambda: False,
    checkpoint_marker: Path | None = None,
    expectations: ReproductionExpectations | None = None,
) -> dict[str, Any]:
    """Run the production audit with a receipt-bound pinned port adapter."""

    return _run_equivalence_audit(
        source_root=source_root,
        dataset_path=dataset_path,
        direct_bundle=direct_bundle,
        direct_runtime_receipt_path=direct_runtime_receipt_path,
        expected_direct_runtime_receipt_sha256=(
            expected_direct_runtime_receipt_sha256
        ),
        port_runtime_receipt_path=port_runtime_receipt_path,
        expected_port_runtime_receipt_sha256=expected_port_runtime_receipt_sha256,
        output_dir=output_dir,
        resume=resume,
        retrieval=None,
        stop_requested=stop_requested,
        checkpoint_marker=checkpoint_marker,
        expectations=expectations,
    )


def _run_equivalence_audit_for_test(
    *,
    source_root: Path,
    dataset_path: Path,
    direct_bundle: Path,
    direct_runtime_receipt_path: Path,
    expected_direct_runtime_receipt_sha256: str,
    port_runtime_receipt_path: Path,
    expected_port_runtime_receipt_sha256: str,
    output_dir: Path,
    resume: bool,
    retrieval: MemPalaceRetrievalPort,
    stop_requested: StopRequested = lambda: False,
    checkpoint_marker: Path | None = None,
    expectations: ReproductionExpectations | None = None,
) -> dict[str, Any]:
    """Exercise orchestration with a deterministic fake retrieval port in tests."""

    return _run_equivalence_audit(
        source_root=source_root,
        dataset_path=dataset_path,
        direct_bundle=direct_bundle,
        direct_runtime_receipt_path=direct_runtime_receipt_path,
        expected_direct_runtime_receipt_sha256=(
            expected_direct_runtime_receipt_sha256
        ),
        port_runtime_receipt_path=port_runtime_receipt_path,
        expected_port_runtime_receipt_sha256=expected_port_runtime_receipt_sha256,
        output_dir=output_dir,
        resume=resume,
        retrieval=retrieval,
        stop_requested=stop_requested,
        checkpoint_marker=checkpoint_marker,
        expectations=expectations,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--direct-bundle", type=Path, required=True)
    parser.add_argument("--direct-runtime-receipt", type=Path, required=True)
    parser.add_argument("--expected-direct-runtime-receipt-sha256", required=True)
    parser.add_argument("--port-runtime-receipt", type=Path, required=True)
    parser.add_argument("--expected-port-runtime-receipt-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--require-gates", action="store_true")
    args = parser.parse_args()
    stop = threading.Event()
    signal.signal(signal.SIGUSR1, lambda _signum, _frame: stop.set())
    marker_value = os.environ.get("COTCODEC_CHECKPOINT_MARKER")
    marker = Path(marker_value) if marker_value else None
    try:
        result = run_equivalence_audit(
            source_root=args.source_root,
            dataset_path=args.dataset,
            direct_bundle=args.direct_bundle,
            direct_runtime_receipt_path=args.direct_runtime_receipt,
            expected_direct_runtime_receipt_sha256=(
                args.expected_direct_runtime_receipt_sha256
            ),
            port_runtime_receipt_path=args.port_runtime_receipt,
            expected_port_runtime_receipt_sha256=(
                args.expected_port_runtime_receipt_sha256
            ),
            output_dir=args.output_dir,
            resume=args.resume,
            stop_requested=stop.is_set,
            checkpoint_marker=marker,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(canonical_json(result))
    if result["status"] != "MEMPALACE_MATCHED_PORT_EQUIVALENCE_COMPLETE":
        return 75
    return int(args.require_gates and not result["all_gates_pass"])


if __name__ == "__main__":
    raise SystemExit(main())
