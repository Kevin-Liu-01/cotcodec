"""Matched port of MemPalace's released raw LongMemEval retrieval mechanism.

The upstream raw runner is intentionally narrow: it creates one document per
session by joining only user turns, embeds those documents with Chroma's pinned
ONNX MiniLM default, and ranks them for the benchmark question.  This module
owns the task-blind rendering, attribution, budget, and accounting contract.
The actual Chroma execution remains behind ``MemPalaceRetrievalPort`` so the
publication lane can require the reviewed source, lock, image, and model
receipts without importing Chroma into the harness core.

This is a mechanism port, not a claim that MemPalace implements CRUD, paging,
consolidation, answer generation, or persistent lifecycle semantics.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from harness.memory_trials.schema import canonical_json, sha256_text
from harness.memory_trials.systems import (
    MemoryEvidence,
    MemorySelection,
    MemorySystemReceipt,
    MemorySystemRequest,
    _costs,
    _fit_evidence_budget,
    _seal_selection,
)

MEMPALACE_REPOSITORY = "https://github.com/MemPalace/mempalace"
MEMPALACE_REVISION = "906b918a7c6ebb2a9198a6bf5a78f30a173fea56"
MEMPALACE_TREE = "98789ad017781f52550b511fcedd9e00c3346761"
MEMPALACE_SOURCE_ARCHIVE_SHA256 = (
    "efbc106cb344a1c5031268909adc2fb5c11cc783ec61adccbe3da0867b4d25c7"
)
MEMPALACE_RUNNER_SHA256 = (
    "c4b4ba3da9e2d7e0e3f27bc93918877fe5f46e202be9ff98b1e90c7e0124628d"
)
MEMPALACE_UV_LOCK_SHA256 = (
    "9cea6756cee6b4a4c24d03c23e92116e62479d0d062c1cd3af8da806d1aeb4da"
)
MEMPALACE_CHROMADB_VERSION = "1.5.7"
MEMPALACE_MINILM_MODEL = "all-MiniLM-L6-v2"
MEMPALACE_MINILM_ARCHIVE_URL = (
    "https://chroma-onnx-models.s3.amazonaws.com/"
    "all-MiniLM-L6-v2/onnx.tar.gz"
)
MEMPALACE_MINILM_ARCHIVE_SHA256 = (
    "913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3"
)
MEMPALACE_MINILM_DIMENSIONS = 384
MEMPALACE_MINILM_MAXIMUM_TOKENS = 256
MEMPALACE_MINILM_POOLING = "attention-mean-l2-normalized-v1"
MEMPALACE_UPSTREAM_RETRIEVAL_LIMIT = 50


class MemPalaceRuntimeIdentity(BaseModel):
    """Reviewed current-lock runtime identity for the raw retrieval port."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    repository: Literal[
        "https://github.com/MemPalace/mempalace"
    ] = MEMPALACE_REPOSITORY
    revision: Literal[
        "906b918a7c6ebb2a9198a6bf5a78f30a173fea56"
    ] = MEMPALACE_REVISION
    tree_sha: Literal[
        "98789ad017781f52550b511fcedd9e00c3346761"
    ] = MEMPALACE_TREE
    source_archive_sha256: Literal[
        "efbc106cb344a1c5031268909adc2fb5c11cc783ec61adccbe3da0867b4d25c7"
    ] = MEMPALACE_SOURCE_ARCHIVE_SHA256
    runner_sha256: Literal[
        "c4b4ba3da9e2d7e0e3f27bc93918877fe5f46e202be9ff98b1e90c7e0124628d"
    ] = MEMPALACE_RUNNER_SHA256
    uv_lock_sha256: Literal[
        "9cea6756cee6b4a4c24d03c23e92116e62479d0d062c1cd3af8da806d1aeb4da"
    ] = MEMPALACE_UV_LOCK_SHA256
    chromadb_version: Literal["1.5.7"] = MEMPALACE_CHROMADB_VERSION
    embedding_model: Literal["all-MiniLM-L6-v2"] = MEMPALACE_MINILM_MODEL
    embedding_archive_url: Literal[
        "https://chroma-onnx-models.s3.amazonaws.com/"
        "all-MiniLM-L6-v2/onnx.tar.gz"
    ] = MEMPALACE_MINILM_ARCHIVE_URL
    embedding_archive_sha256: Literal[
        "913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3"
    ] = MEMPALACE_MINILM_ARCHIVE_SHA256
    dimensions: Literal[384] = MEMPALACE_MINILM_DIMENSIONS
    maximum_tokens: Literal[256] = MEMPALACE_MINILM_MAXIMUM_TOKENS
    pooling_strategy: Literal[
        "attention-mean-l2-normalized-v1"
    ] = MEMPALACE_MINILM_POOLING
    execution_provider: Literal["CPUExecutionProvider"] = "CPUExecutionProvider"
    model_artifact_root_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    image_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    runtime_artifacts_verified: Literal[True] = True
    implementation_kind: Literal["in_process_reference", "oci_sidecar"] = (
        "in_process_reference"
    )
    publication_ready: Literal[False] = False


class MemPalaceEquivalenceEvidence(BaseModel):
    """Immutable evidence that the matched port reproduced the upstream runner."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[1] = 1
    status: Literal["VERIFIED_MEMPALACE_CONTROL_EVIDENCE"] = (
        "VERIFIED_MEMPALACE_CONTROL_EVIDENCE"
    )
    equivalence_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    equivalence_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    equivalence_manifest_file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    equivalence_report_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    equivalence_journal_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    equivalence_bundle_root_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    direct_runtime_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    port_runtime_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    task_count: Literal[500] = 500
    all_gates_pass: Literal[True] = True


class MemPalaceSessionDocument(BaseModel):
    """One raw user-only session document sent to the retrieval backend."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    source_record_ids: tuple[str, ...] = Field(min_length=1)
    first_step: int = Field(ge=0)
    last_step: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_steps(self) -> MemPalaceSessionDocument:
        if self.last_step < self.first_step:
            raise ValueError("session document steps are reversed")
        if len(self.source_record_ids) != len(set(self.source_record_ids)):
            raise ValueError("session document source IDs must be unique")
        return self


class MemPalaceRetrievalBatch(BaseModel):
    """Ordered result from one exact Chroma/MiniLM retrieval execution."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ranked_document_ids: tuple[str, ...] = Field(min_length=1)
    distances: tuple[float, ...] = Field(min_length=1)
    embedding_input_count: int = Field(ge=2)
    collection_write_count: int = Field(ge=1)
    query_count: Literal[1] = 1
    latency_ms: float = Field(ge=0.0, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_ranking(self) -> MemPalaceRetrievalBatch:
        if len(self.ranked_document_ids) != len(self.distances):
            raise ValueError("MemPalace ranking and distance counts differ")
        if len(self.ranked_document_ids) != len(set(self.ranked_document_ids)):
            raise ValueError("MemPalace ranking contains duplicate documents")
        if not all(math.isfinite(distance) for distance in self.distances):
            raise ValueError("MemPalace ranking contains a non-finite distance")
        return self


class MemPalaceRetrievalPort(Protocol):
    """The exact current-lock Chroma execution boundary."""

    identity: MemPalaceRuntimeIdentity

    def retrieve(
        self,
        *,
        query: str,
        documents: Sequence[MemPalaceSessionDocument],
        n_results: int,
    ) -> MemPalaceRetrievalBatch: ...


def build_mempalace_session_documents(
    request: MemorySystemRequest,
) -> tuple[MemPalaceSessionDocument, ...]:
    """Render the exact task-blind user-only session documents for retrieval."""

    if any(event.kind != "write" for event in request.events):
        raise ValueError(
            "MemPalace raw-session port supports append-only benchmark writes only"
        )
    grouped: dict[str, list[tuple[str, str, int]]] = {}
    for event in request.events:
        if event.key != "user" or event.value is None:
            continue
        grouped.setdefault(event.entity_id, []).append(
            (event.source_event_id, event.value, event.step)
        )
    return tuple(
        MemPalaceSessionDocument(
            document_id=entity_id,
            text="\n".join(value for _source_id, value, _step in turns),
            source_record_ids=tuple(source_id for source_id, _value, _step in turns),
            first_step=turns[0][2],
            last_step=turns[-1][2],
        )
        for entity_id, turns in grouped.items()
    )


class MemPalaceRawSessionMemorySystem:
    """User-only per-session MiniLM retrieval as a matched mechanism port."""

    identity = "mempalace-raw-user-session-minilm-port-v1"

    def __init__(
        self,
        retrieval: MemPalaceRetrievalPort,
        *,
        equivalence_evidence: MemPalaceEquivalenceEvidence,
    ) -> None:
        self._retrieval = retrieval
        self.admission_evidence = equivalence_evidence
        runtime = retrieval.identity
        config = {
            "scientific_role": "matched-raw-session-no-write-llm-retrieval-floor",
            "upstream_mode": "raw",
            "granularity": "session",
            "session_document": "newline-joined-user-turns-only",
            "assistant_turns": "excluded",
            "upstream_retrieval_limit": MEMPALACE_UPSTREAM_RETRIEVAL_LIMIT,
            "score_semantics": (
                "negative-rank-index-proxy; upstream runner does not expose distances"
            ),
            "actor_top_k": "request-budget",
            "actor_token_budget": "request-budget",
            "lifecycle_scope": "append-only-public-benchmark-transport",
            "not_claimed": [
                "byte-exact-upstream-reproduction",
                "answer-generation",
                "active-inactive-paging",
                "crud",
                "persistence",
                "consolidation",
            ],
            "matched_port_equivalence": equivalence_evidence.model_dump(mode="json"),
            **runtime.model_dump(mode="json"),
        }
        self.receipt = MemorySystemReceipt(
            system_id=self.identity,
            implementation_kind=runtime.implementation_kind,
            implementation_revision=(
                "harness.memory_trials.mempalace_control:"
                "raw-user-session-minilm-port-v1:equivalence-"
                f"{equivalence_evidence.equivalence_contract_sha256}"
            ),
            configuration_sha256=sha256_text(canonical_json(config)),
            backend_id=(
                f"mempalace@{runtime.revision}:chromadb-{runtime.chromadb_version}:"
                f"{runtime.embedding_model}:{runtime.execution_provider}:"
                f"direct-runtime-{equivalence_evidence.direct_runtime_receipt_sha256}:"
                f"port-runtime-{equivalence_evidence.port_runtime_receipt_sha256}"
            ),
            source_archive_sha256=runtime.source_archive_sha256,
            image_digest=runtime.image_digest,
            model_receipt_sha256s=(runtime.model_receipt_sha256,),
            publication_ready=runtime.publication_ready,
        )

    def select(self, request: MemorySystemRequest) -> MemorySelection:
        documents = build_mempalace_session_documents(request)
        if not documents:
            costs = _costs(request, ()).model_copy(
                update={"writes": 0, "reads": 0, "embedding_calls": 0}
            )
            return _seal_selection(request, (), costs, self.receipt)

        n_results = min(MEMPALACE_UPSTREAM_RETRIEVAL_LIMIT, len(documents))
        batch = self._retrieval.retrieve(
            query=request.query,
            documents=documents,
            n_results=n_results,
        )
        expected_ids = {document.document_id for document in documents}
        if (
            len(batch.ranked_document_ids) != n_results
            or not set(batch.ranked_document_ids).issubset(expected_ids)
        ):
            raise ValueError("MemPalace backend returned an invalid document roster")
        if batch.collection_write_count != len(documents):
            raise ValueError("MemPalace backend changed the session-document write count")
        if batch.embedding_input_count != len(documents) + 1:
            raise ValueError("MemPalace backend changed embedding-input accounting")

        by_id = {document.document_id: document for document in documents}
        ranked_evidence = tuple(
            MemoryEvidence(
                evidence_id=f"mempalace-session:{document_id}",
                text=by_id[document_id].text,
                source_record_ids=by_id[document_id].source_record_ids,
                score=-distance,
                kind="record",
            )
            for document_id, distance in zip(
                batch.ranked_document_ids,
                batch.distances,
                strict=True,
            )
        )[: request.budget.retrieval_top_k]
        evidence = _fit_evidence_budget(request, ranked_evidence)
        costs = _costs(request, evidence).model_copy(
            update={
                "writes": batch.collection_write_count,
                "reads": batch.query_count,
                "embedding_calls": batch.embedding_input_count,
                "latency_ms": batch.latency_ms,
            }
        )
        return _seal_selection(request, evidence, costs, self.receipt)
