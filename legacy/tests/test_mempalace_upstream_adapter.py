from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from harness.memory_trials import (
    MemoryBudget,
    MemorySystemEvent,
    MemorySystemRequest,
    MemPalaceEquivalenceEvidence,
    MemPalaceRawSessionMemorySystem,
    MemPalaceRuntimeIdentity,
    MemPalaceSessionDocument,
)
from scripts.mempalace_upstream_adapter import PinnedUpstreamMemPalaceAdapter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SIDECAR = PROJECT_ROOT / "infra" / "memory-baselines" / "mempalace_sidecar.py"


def _identity() -> MemPalaceRuntimeIdentity:
    return MemPalaceRuntimeIdentity(
        model_artifact_root_sha256="a" * 64,
        model_receipt_sha256="b" * 64,
        image_digest="sha256:" + "c" * 64,
        implementation_kind="oci_sidecar",
    )


def _evidence() -> MemPalaceEquivalenceEvidence:
    return MemPalaceEquivalenceEvidence(
        equivalence_contract_sha256="1" * 64,
        equivalence_manifest_sha256="2" * 64,
        equivalence_manifest_file_sha256="3" * 64,
        equivalence_report_sha256="4" * 64,
        equivalence_journal_sha256="5" * 64,
        equivalence_bundle_root_sha256="6" * 64,
        direct_runtime_receipt_sha256="7" * 64,
        port_runtime_receipt_sha256="8" * 64,
    )


def test_upstream_adapter_preserves_documents_and_exposes_rank_order() -> None:
    captured = {}

    def retrieve(entry):
        captured.update(entry)
        corpus = ["first\ncontinued", "second"]
        ids = ["session-a", "session-b"]
        return [1, 0], corpus, ids, ["2", "3"]

    adapter = PinnedUpstreamMemPalaceAdapter.from_retriever(
        identity=_identity(), retrieve=retrieve
    )
    documents = (
        MemPalaceSessionDocument(
            document_id="session-a",
            text="first\ncontinued",
            source_record_ids=("event-a1", "event-a2"),
            first_step=0,
            last_step=2,
        ),
        MemPalaceSessionDocument(
            document_id="session-b",
            text="second",
            source_record_ids=("event-b1",),
            first_step=3,
            last_step=3,
        ),
    )
    batch = adapter.retrieve(query="where?", documents=documents, n_results=2)

    assert captured == {
        "question": "where?",
        "haystack_sessions": [
            [{"role": "user", "content": "first\ncontinued"}],
            [{"role": "user", "content": "second"}],
        ],
        "haystack_session_ids": ["session-a", "session-b"],
        "haystack_dates": ["2", "3"],
    }
    assert batch.ranked_document_ids == ("session-b", "session-a")
    assert batch.distances == (0.0, 1.0)
    assert batch.embedding_input_count == 3
    assert batch.collection_write_count == 2


def test_upstream_adapter_fails_closed_on_roster_or_count_drift() -> None:
    document = MemPalaceSessionDocument(
        document_id="session-a",
        text="first",
        source_record_ids=("event-a",),
        first_step=0,
        last_step=0,
    )

    def retrieve(entry):
        return [0], [entry["haystack_sessions"][0][0]["content"]], ["wrong"], ["0"]

    adapter = PinnedUpstreamMemPalaceAdapter.from_retriever(
        identity=_identity(), retrieve=retrieve
    )
    with pytest.raises(ValueError, match="count"):
        adapter.retrieve(query="where?", documents=(document,), n_results=0)
    with pytest.raises(ValueError, match="session corpus"):
        adapter.retrieve(query="where?", documents=(document,), n_results=1)


def test_sidecar_protocol_selection_requires_runtime_receipt() -> None:
    # This test exercises the real protocol script only at import/argument time;
    # the Chroma runtime itself is admitted by the contained image doctor.
    completed = subprocess.run(
        [sys.executable, str(SIDECAR)],
        input=json.dumps(
            {
                "protocol": "memory-system-v1",
                "operation": "handshake",
                "payload": {},
            }
        )
        + "\n",
        capture_output=True,
        text=True,
        env={"PATH": "", "PYTHONPATH": str(PROJECT_ROOT)},
        check=False,
    )
    assert completed.returncode != 0
    assert "COTCODEC_MEMPALACE_RUNTIME_RECEIPT is required" in completed.stderr


def test_system_receipt_and_selection_preserve_oci_adapter_identity() -> None:
    def retrieve(entry):
        corpus = [
            session[0]["content"] for session in entry["haystack_sessions"]
        ]
        return list(range(len(corpus))), corpus, entry["haystack_session_ids"], ["0"]

    adapter = PinnedUpstreamMemPalaceAdapter.from_retriever(
        identity=_identity(), retrieve=retrieve
    )
    system = MemPalaceRawSessionMemorySystem(
        adapter,
        equivalence_evidence=_evidence(),
    )
    request = MemorySystemRequest(
        request_id="request-1",
        session_scope="scope-1",
        events=(
            MemorySystemEvent(
                source_event_id="event-1",
                step=0,
                kind="write",
                entity_id="session-a",
                key="user",
                value="remember this",
                untrusted=False,
            ),
        ),
        query="what?",
        budget=MemoryBudget(
            active_slots=4,
            max_archive_reads=1,
            retrieval_top_k=4,
            max_injected_tokens=256,
        ),
    )
    selection = system.select(request)
    assert selection.receipt.implementation_kind == "oci_sidecar"
    assert selection.receipt.image_digest == "sha256:" + "c" * 64
    assert selection.receipt.publication_ready is False
    assert selection.evidence[0].source_record_ids == ("event-1",)
