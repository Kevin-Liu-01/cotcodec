"""Pinned dense-retrieval control over the task-blind memory-system contract.

The system owns document rendering, query instructions, vector validation,
ranking, budget fitting, attribution, and cost accounting.  Model execution is
the only seam: contained runs use a verified local BGE encoder (directly or over
loopback HTTP), while tests use an in-memory encoder through the same interface.
"""

from __future__ import annotations

import math
import time
from collections.abc import Sequence
from typing import Literal, Protocol
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator

from harness.memory_trials.schema import canonical_json, sha256_text
from harness.memory_trials.systems import (
    MemoryCostLedger,
    MemorySelection,
    MemorySystemReceipt,
    MemorySystemRequest,
    _costs,
    _fit_evidence_budget,
    _record_evidence,
    _seal_selection,
    materialize_request_records,
)

BGE_SMALL_EN_V15_REGISTRY_ID = "bge-small-en-v1.5"
BGE_SMALL_EN_V15_REPO_ID = "BAAI/bge-small-en-v1.5"
BGE_SMALL_EN_V15_REVISION = "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"
BGE_SMALL_EN_V15_DIMENSIONS = 384
BGE_SMALL_EN_V15_MAXIMUM_TOKENS = 512
BGE_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "
BGE_POOLING_STRATEGY = "cls-l2-normalized-v1"


class DenseEmbeddingIdentity(BaseModel):
    """Immutable model/runtime identity required by the dense control."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    model: Literal["BAAI/bge-small-en-v1.5"] = BGE_SMALL_EN_V15_REPO_ID
    registry_model_id: Literal["bge-small-en-v1.5"] = BGE_SMALL_EN_V15_REGISTRY_ID
    revision: Literal[
        "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"
    ] = BGE_SMALL_EN_V15_REVISION
    artifact_root_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    dimensions: Literal[384] = BGE_SMALL_EN_V15_DIMENSIONS
    maximum_tokens: Literal[512] = BGE_SMALL_EN_V15_MAXIMUM_TOKENS
    pooling_strategy: Literal["cls-l2-normalized-v1"] = BGE_POOLING_STRATEGY
    publication_eligible: Literal[True] = True


class DenseEmbeddingBatch(BaseModel):
    """One auditable encoder execution returned by an embedding adapter."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    vectors: tuple[tuple[float, ...], ...]
    input_count: int = Field(ge=1)
    request_count: Literal[1] = 1
    prompt_tokens: int = Field(ge=0)
    latency_ms: float = Field(ge=0.0, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_row_count(self) -> DenseEmbeddingBatch:
        if len(self.vectors) != self.input_count:
            raise ValueError("embedding batch row count differs from input_count")
        return self


class DenseEmbeddingPort(Protocol):
    """The only variable seam in the dense retrieval control."""

    identity: DenseEmbeddingIdentity

    def embed(self, texts: Sequence[str]) -> DenseEmbeddingBatch: ...


class DenseVectorEncoder(Protocol):
    """Minimal local encoder interface used by the in-process adapter."""

    dimensions: int
    maximum_tokens: int
    pooling_strategy: str

    def embed(self, texts: Sequence[str]) -> tuple[list[list[float]], int]: ...


def _validate_vectors(
    vectors: Sequence[Sequence[float]],
    *,
    input_count: int,
    dimensions: int,
) -> tuple[tuple[float, ...], ...]:
    if len(vectors) != input_count:
        raise ValueError("embedding adapter returned the wrong row count")
    validated: list[tuple[float, ...]] = []
    for vector in vectors:
        if len(vector) != dimensions:
            raise ValueError("embedding adapter returned the wrong dimensions")
        row = tuple(float(value) for value in vector)
        if not all(math.isfinite(value) for value in row):
            raise ValueError("embedding adapter returned a non-finite value")
        norm = math.sqrt(sum(value * value for value in row))
        if not math.isclose(norm, 1.0, rel_tol=1e-4, abs_tol=1e-4):
            raise ValueError("embedding adapter did not return L2-normalized vectors")
        validated.append(row)
    return tuple(validated)


class InProcessDenseEmbeddingClient:
    """Adapter for a verified encoder loaded in the freezer process."""

    def __init__(
        self,
        encoder: DenseVectorEncoder,
        identity: DenseEmbeddingIdentity,
    ) -> None:
        if (
            encoder.dimensions != identity.dimensions
            or encoder.maximum_tokens != identity.maximum_tokens
            or encoder.pooling_strategy != identity.pooling_strategy
        ):
            raise ValueError("local encoder runtime differs from its pinned identity")
        self._encoder = encoder
        self.identity = identity

    def embed(self, texts: Sequence[str]) -> DenseEmbeddingBatch:
        if not texts or not all(isinstance(text, str) and text for text in texts):
            raise ValueError("embedding inputs must be non-empty strings")
        started = time.perf_counter()
        vectors, prompt_tokens = self._encoder.embed(texts)
        latency_ms = (time.perf_counter() - started) * 1000
        return DenseEmbeddingBatch(
            vectors=_validate_vectors(
                vectors,
                input_count=len(texts),
                dimensions=self.identity.dimensions,
            ),
            input_count=len(texts),
            prompt_tokens=prompt_tokens,
            latency_ms=latency_ms,
        )


class HTTPDenseEmbeddingClient:
    """Loopback-only adapter for the reviewed local HF embedding server."""

    def __init__(
        self,
        base_url: str,
        identity: DenseEmbeddingIdentity,
        *,
        timeout_seconds: float = 120.0,
    ) -> None:
        parsed = urlparse(base_url)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.path.rstrip("/") not in {"", "/v1"}
        ):
            raise ValueError("embedding service must be an uncredentialed loopback /v1 URL")
        self._base_url = base_url.rstrip("/")
        if not self._base_url.endswith("/v1"):
            self._base_url += "/v1"
        self._timeout = timeout_seconds
        self.identity = identity
        health = self._request_identity("/health")
        self._validate_identity(health)

    def _root_url(self, path: str) -> str:
        return self._base_url.removesuffix("/v1") + path

    def _request_identity(self, path: str) -> dict[str, object]:
        try:
            response = httpx.get(self._root_url(path), timeout=self._timeout)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ValueError("embedding service identity request failed") from exc
        if not isinstance(payload, dict):
            raise ValueError("embedding service identity must be a JSON object")
        return payload

    def _validate_identity(self, payload: dict[str, object]) -> None:
        expected = self.identity.model_dump(mode="json")
        if payload.get("status", "ok") != "ok" or any(
            payload.get(field) != value for field, value in expected.items()
        ):
            raise ValueError("embedding service identity differs from the pinned control")

    def embed(self, texts: Sequence[str]) -> DenseEmbeddingBatch:
        if not texts or not all(isinstance(text, str) and text for text in texts):
            raise ValueError("embedding inputs must be non-empty strings")
        started = time.perf_counter()
        try:
            response = httpx.post(
                f"{self._base_url}/embeddings",
                json={
                    "model": self.identity.model,
                    "input": list(texts),
                    "dimensions": self.identity.dimensions,
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ValueError("embedding request failed") from exc
        if not isinstance(payload, dict):
            raise ValueError("embedding response must be a JSON object")
        self._validate_identity(payload)
        data = payload.get("data")
        if not isinstance(data, list) or len(data) != len(texts):
            raise ValueError("embedding response row count drifted")
        ordered = sorted(
            data,
            key=lambda row: row.get("index", -1)
            if isinstance(row, dict)
            else -1,
        )
        if [row.get("index") for row in ordered if isinstance(row, dict)] != list(
            range(len(texts))
        ):
            raise ValueError("embedding response indexes drifted")
        vectors = [row.get("embedding") for row in ordered if isinstance(row, dict)]
        if len(vectors) != len(texts) or not all(isinstance(row, list) for row in vectors):
            raise ValueError("embedding response vectors are invalid")
        usage = payload.get("usage")
        prompt_tokens = usage.get("prompt_tokens") if isinstance(usage, dict) else None
        if (
            isinstance(prompt_tokens, bool)
            or not isinstance(prompt_tokens, int)
            or prompt_tokens < 0
        ):
            raise ValueError("embedding response usage is invalid")
        return DenseEmbeddingBatch(
            vectors=_validate_vectors(
                vectors,
                input_count=len(texts),
                dimensions=self.identity.dimensions,
            ),
            input_count=len(texts),
            prompt_tokens=prompt_tokens,
            latency_ms=(time.perf_counter() - started) * 1000,
        )


def _passage(entity_id: str, key: str, value: str) -> str:
    return f"entity: {entity_id}\nkey: {key}\nvalue: {value}"


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    return float(sum(a * b for a, b in zip(left, right, strict=True)))


class DenseBGERetrievalMemorySystem:
    """Matched raw-record dense retrieval using the pinned BGE v1.5 encoder."""

    identity = "dense-bge-retrieval-v1"

    def __init__(self, embedding: DenseEmbeddingPort) -> None:
        self._embedding = embedding
        model = embedding.identity
        config = {
            "strategy": "dense-cosine-over-valid-task-blind-records",
            "document": "entity-id key value",
            "query_instruction": BGE_QUERY_INSTRUCTION,
            "query_instruction_scope": "query-only",
            "tie_break": "recency-then-source-record-id",
            "embedding_model": model.model,
            "embedding_registry_model_id": model.registry_model_id,
            "embedding_revision": model.revision,
            "embedding_artifact_root_sha256": model.artifact_root_sha256,
            "embedding_receipt_sha256": model.model_receipt_sha256,
            "embedding_dimensions": model.dimensions,
            "embedding_maximum_tokens": model.maximum_tokens,
            "embedding_pooling": model.pooling_strategy,
            "embedding_call_accounting": "encoded-input-count-v1",
            "source_model_card": (
                "https://huggingface.co/BAAI/bge-small-en-v1.5/blob/"
                f"{model.revision}/README.md"
            ),
        }
        self.receipt = MemorySystemReceipt(
            system_id=self.identity,
            implementation_kind="in_process_reference",
            implementation_revision=(
                "harness.memory_trials.dense_control:dense-bge-retrieval-v1"
            ),
            configuration_sha256=sha256_text(canonical_json(config)),
            backend_id=f"hf-transformers:{model.registry_model_id}@{model.revision}",
            model_receipt_sha256s=(model.model_receipt_sha256,),
            publication_ready=False,
        )

    def select(self, request: MemorySystemRequest) -> MemorySelection:
        records = tuple(
            record for record in materialize_request_records(request) if record.valid
        )
        if not records:
            return _seal_selection(request, (), _costs(request, ()), self.receipt)

        texts = (
            BGE_QUERY_INSTRUCTION + request.query,
            *(
                _passage(record.entity_id, record.key, record.value)
                for record in records
            ),
        )
        batch = self._embedding.embed(texts)
        query_vector = batch.vectors[0]
        scores = {
            record.source_record_id: _cosine(query_vector, vector)
            for record, vector in zip(records, batch.vectors[1:], strict=True)
        }
        ranked = sorted(
            records,
            key=lambda record: (
                -scores[record.source_record_id],
                -record.written_step,
                record.source_record_id,
            ),
        )[: request.budget.retrieval_top_k]
        ranked_evidence = tuple(
            _record_evidence(record, score=scores[record.source_record_id])
            for record in ranked
        )
        evidence = _fit_evidence_budget(request, ranked_evidence)
        costs: MemoryCostLedger = _costs(request, evidence).model_copy(
            update={
                "embedding_calls": batch.input_count,
                "latency_ms": batch.latency_ms,
            }
        )
        return _seal_selection(request, evidence, costs, self.receipt)
