from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from harness.memory_trials import (
    MemoryBudget,
    MemorySystemEvent,
    MemorySystemRequest,
    MemPalaceEquivalenceEvidence,
    MemPalaceRawSessionMemorySystem,
    MemPalaceRetrievalBatch,
    MemPalaceRuntimeIdentity,
    MemPalaceSessionDocument,
)
from scripts.mempalace_control_factory import (
    EQUIVALENCE_FILES,
    build_verified_mempalace_control,
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


def _system(backend: FakeMemPalaceBackend) -> MemPalaceRawSessionMemorySystem:
    return MemPalaceRawSessionMemorySystem(
        backend,
        equivalence_evidence=_evidence(),
    )


class FakeMemPalaceBackend:
    def __init__(self, *, corrupt: str | None = None) -> None:
        self.identity = MemPalaceRuntimeIdentity(
            model_artifact_root_sha256="a" * 64,
            model_receipt_sha256="b" * 64,
            image_digest="sha256:" + "c" * 64,
        )
        self.corrupt = corrupt
        self.query = ""
        self.documents: tuple[MemPalaceSessionDocument, ...] = ()
        self.n_results = 0

    def retrieve(
        self,
        *,
        query: str,
        documents: Sequence[MemPalaceSessionDocument],
        n_results: int,
    ) -> MemPalaceRetrievalBatch:
        self.query = query
        self.documents = tuple(documents)
        self.n_results = n_results
        ranked = tuple(reversed([document.document_id for document in documents]))[
            :n_results
        ]
        writes = len(documents)
        inputs = len(documents) + 1
        if self.corrupt == "unknown":
            ranked = ("not-a-session", *ranked[1:])
        elif self.corrupt == "short":
            ranked = ranked[:-1]
        elif self.corrupt == "writes":
            writes += 1
        elif self.corrupt == "inputs":
            inputs += 1
        return MemPalaceRetrievalBatch(
            ranked_document_ids=ranked,
            distances=tuple(float(index) for index, _item in enumerate(ranked)),
            embedding_input_count=inputs,
            collection_write_count=writes,
            latency_ms=4.5,
        )


def _request(*, events: tuple[MemorySystemEvent, ...] | None = None) -> MemorySystemRequest:
    return MemorySystemRequest(
        request_id="mempalace-request-1",
        session_scope="mempalace-session-1",
        events=events
        or (
            MemorySystemEvent(
                source_event_id="s1-user-1",
                step=0,
                kind="write",
                entity_id="session-one",
                key="user",
                value="I moved to Paris.",
                untrusted=False,
            ),
            MemorySystemEvent(
                source_event_id="s1-assistant-1",
                step=1,
                kind="write",
                entity_id="session-one",
                key="assistant",
                value="Thanks for telling me.",
                untrusted=False,
            ),
            MemorySystemEvent(
                source_event_id="s1-user-2",
                step=2,
                kind="write",
                entity_id="session-one",
                key="user",
                value="My apartment is near the river.",
                untrusted=False,
            ),
            MemorySystemEvent(
                source_event_id="s2-user-1",
                step=3,
                kind="write",
                entity_id="session-two",
                key="user",
                value="I like oranges.",
                untrusted=False,
            ),
        ),
        query="Where do I live?",
        budget=MemoryBudget(
            active_slots=4,
            max_archive_reads=1,
            retrieval_top_k=2,
            max_injected_tokens=256,
        ),
    )


def test_mempalace_port_groups_user_turns_and_accounts_exact_inputs() -> None:
    backend = FakeMemPalaceBackend()
    system = _system(backend)
    selection = system.select(_request())

    assert backend.query == "Where do I live?"
    assert backend.n_results == 2
    assert [document.document_id for document in backend.documents] == [
        "session-one",
        "session-two",
    ]
    assert backend.documents[0].text == (
        "I moved to Paris.\nMy apartment is near the river."
    )
    assert backend.documents[0].source_record_ids == ("s1-user-1", "s1-user-2")
    assert "Thanks" not in backend.documents[0].text
    assert selection.evidence[0].source_record_ids == ("s2-user-1",)
    assert selection.evidence[1].source_record_ids == ("s1-user-1", "s1-user-2")
    assert selection.costs.writes == 2
    assert selection.costs.reads == 1
    assert selection.costs.embedding_calls == 3
    assert selection.costs.latency_ms == 4.5
    assert system.receipt.source_archive_sha256 == backend.identity.source_archive_sha256
    assert system.receipt.image_digest == backend.identity.image_digest
    assert system.receipt.publication_ready is False


def test_mempalace_port_is_explicitly_not_a_crud_or_paging_adapter() -> None:
    update = MemorySystemEvent(
        source_event_id="update-1",
        step=0,
        kind="update",
        entity_id="session-one",
        key="user",
        value="new value",
        untrusted=False,
    )
    with pytest.raises(ValueError, match="append-only benchmark writes"):
        _system(FakeMemPalaceBackend()).select(
            _request(events=(update,))
        )


@pytest.mark.parametrize("corrupt", ["unknown", "short", "writes", "inputs"])
def test_mempalace_port_fails_closed_on_backend_contract_drift(corrupt: str) -> None:
    with pytest.raises(ValueError, match="MemPalace backend"):
        _system(FakeMemPalaceBackend(corrupt=corrupt)).select(_request())


def test_mempalace_batch_rejects_duplicate_or_nonfinite_rankings() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        MemPalaceRetrievalBatch(
            ranked_document_ids=("same", "same"),
            distances=(0.1, 0.2),
            embedding_input_count=3,
            collection_write_count=2,
            latency_ms=1.0,
        )
    with pytest.raises(ValueError, match="non-finite"):
        MemPalaceRetrievalBatch(
            ranked_document_ids=("one",),
            distances=(float("nan"),),
            embedding_input_count=2,
            collection_write_count=1,
            latency_ms=1.0,
        )


def test_mempalace_factory_rejects_runtime_receipts_without_equivalence_bundle(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    equivalence = tmp_path / "equivalence"
    equivalence.mkdir()
    runtime = tmp_path / "runtime.json"
    runtime.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="bundle file roster"):
        build_verified_mempalace_control(
            source_root=source,
            equivalence_root=equivalence,
            expected_equivalence_contract_sha256="1" * 64,
            expected_equivalence_bundle_root_sha256="4" * 64,
            direct_runtime_receipt_path=runtime,
            expected_direct_runtime_receipt_sha256="2" * 64,
            port_runtime_receipt_path=runtime,
            expected_port_runtime_receipt_sha256="3" * 64,
        )


def test_mempalace_factory_requires_a_registered_complete_bundle_root(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    equivalence = tmp_path / "equivalence"
    equivalence.mkdir()
    for name in EQUIVALENCE_FILES:
        (equivalence / name).write_text("{}\n", encoding="utf-8")
    runtime = tmp_path / "runtime.json"
    runtime.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="bundle root drifted"):
        build_verified_mempalace_control(
            source_root=source,
            equivalence_root=equivalence,
            expected_equivalence_contract_sha256="1" * 64,
            expected_equivalence_bundle_root_sha256="4" * 64,
            direct_runtime_receipt_path=runtime,
            expected_direct_runtime_receipt_sha256="2" * 64,
            port_runtime_receipt_path=runtime,
            expected_port_runtime_receipt_sha256="3" * 64,
        )
