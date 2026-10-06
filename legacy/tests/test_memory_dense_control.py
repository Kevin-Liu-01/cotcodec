from __future__ import annotations

import json
import math
import threading
from collections.abc import Sequence
from pathlib import Path

import pytest

from harness.memory_trials import (
    BGE_QUERY_INSTRUCTION,
    DenseBGERetrievalMemorySystem,
    DenseEmbeddingIdentity,
    HTTPDenseEmbeddingClient,
    InProcessDenseEmbeddingClient,
    MemoryBudget,
    MemorySystemEvent,
    MemorySystemRequest,
)
from scripts.dense_bge_factory import build_dense_bge_system
from scripts.fetch_open_model import artifact_root, receipt_path, snapshot_files
from scripts.run_hf_embedding_server import HuggingFaceEmbeddingServer


class SemanticEncoder:
    dimensions = 384
    maximum_tokens = 512
    pooling_strategy = "cls-l2-normalized-v1"

    def __init__(self, *, corrupt: str | None = None) -> None:
        self.corrupt = corrupt
        self.seen: tuple[str, ...] = ()

    def embed(self, texts: Sequence[str]) -> tuple[list[list[float]], int]:
        self.seen = tuple(texts)
        rows: list[list[float]] = []
        for text in texts:
            row = [0.0] * self.dimensions
            row[0 if text.startswith(BGE_QUERY_INSTRUCTION) or "Paris" in text else 1] = 1.0
            rows.append(row)
        if self.corrupt == "dimensions":
            rows[0] = rows[0][:-1]
        elif self.corrupt == "nan":
            rows[0][0] = math.nan
        elif self.corrupt == "norm":
            rows[0][0] = 2.0
        return rows, sum(len(text.split()) for text in texts)


def _identity(*, artifact: str = "a" * 64) -> DenseEmbeddingIdentity:
    return DenseEmbeddingIdentity(
        artifact_root_sha256=artifact,
        model_receipt_sha256="b" * 64,
    )


def _request(*, top_k: int = 1) -> MemorySystemRequest:
    return MemorySystemRequest(
        request_id="request-dense-1",
        session_scope="session-dense-1",
        events=(
            MemorySystemEvent(
                source_event_id="event-paris",
                step=1,
                kind="write",
                entity_id="france",
                key="seat",
                value="Paris",
                untrusted=False,
            ),
            MemorySystemEvent(
                source_event_id="event-orange",
                step=2,
                kind="write",
                entity_id="fruit",
                key="color",
                value="orange",
                untrusted=False,
            ),
        ),
        query="What is the capital of France?",
        budget=MemoryBudget(
            active_slots=4,
            max_archive_reads=1,
            retrieval_top_k=top_k,
            max_injected_tokens=256,
        ),
    )


def test_dense_control_ranks_semantically_and_accounts_every_embedding_input() -> None:
    encoder = SemanticEncoder()
    system = DenseBGERetrievalMemorySystem(
        InProcessDenseEmbeddingClient(encoder, _identity())
    )
    selection = system.select(_request())

    assert selection.evidence[0].source_record_ids == ("event-paris",)
    assert selection.costs.embedding_calls == 3
    assert selection.costs.reads == 1
    assert selection.costs.injected_tokens_estimate <= 256
    assert encoder.seen[0] == BGE_QUERY_INSTRUCTION + "What is the capital of France?"
    assert all(not text.startswith(BGE_QUERY_INSTRUCTION) for text in encoder.seen[1:])
    assert system.receipt.model_receipt_sha256s == ("b" * 64,)
    assert system.receipt.publication_ready is False


def test_dense_control_ties_are_resolved_by_recency_then_record_id() -> None:
    class TiedEncoder(SemanticEncoder):
        def embed(self, texts: Sequence[str]) -> tuple[list[list[float]], int]:
            rows = [[1.0, *([0.0] * 383)] for _ in texts]
            return rows, len(texts)

    system = DenseBGERetrievalMemorySystem(
        InProcessDenseEmbeddingClient(TiedEncoder(), _identity())
    )
    selection = system.select(_request())
    assert selection.evidence[0].source_record_ids == ("event-orange",)


@pytest.mark.parametrize("corrupt", ["dimensions", "nan", "norm"])
def test_dense_control_fails_closed_on_invalid_vectors(corrupt: str) -> None:
    system = DenseBGERetrievalMemorySystem(
        InProcessDenseEmbeddingClient(SemanticEncoder(corrupt=corrupt), _identity())
    )
    with pytest.raises(ValueError, match="embedding adapter"):
        system.select(_request())


def test_dense_http_adapter_binds_every_model_identity_field() -> None:
    identity = _identity()
    server = HuggingFaceEmbeddingServer(
        ("127.0.0.1", 0),
        api_model_id=identity.model,
        registry_model_id=identity.registry_model_id,
        revision=identity.revision,
        artifact_root_sha256=identity.artifact_root_sha256,
        model_receipt_sha256=identity.model_receipt_sha256,
        publication_eligible=True,
        backend=SemanticEncoder(),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        client = HTTPDenseEmbeddingClient(f"http://{host}:{port}/v1", identity)
        selection = DenseBGERetrievalMemorySystem(client).select(_request())
        assert selection.evidence[0].source_record_ids == ("event-paris",)
        with pytest.raises(ValueError, match="identity differs"):
            HTTPDenseEmbeddingClient(
                f"http://{host}:{port}/v1",
                _identity(artifact="c" * 64),
            )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_dense_factory_requires_and_binds_a_full_local_model_receipt(
    tmp_path: Path,
) -> None:
    model_root = tmp_path / "models"
    snapshot = model_root / "bge-small-en-v1.5"
    snapshot.mkdir(parents=True)
    (snapshot / "config.json").write_text("{}", encoding="utf-8")
    files = snapshot_files(snapshot)
    receipt_root = tmp_path / "receipts"
    receipt_root.mkdir()
    receipt = {
        "schema_version": 1,
        "model_id": "bge-small-en-v1.5",
        "backend": "huggingface",
        "repo_id": "BAAI/bge-small-en-v1.5",
        "revision": "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a",
        "mode": "full",
        "publication_eligible": True,
        "files": files,
        "artifact_root_sha256": artifact_root(files),
    }
    path = receipt_path(receipt_root, "bge-small-en-v1.5")
    path.write_text(json.dumps(receipt), encoding="utf-8")

    system = build_dense_bge_system(
        registry_path=Path("models/registry.yaml"),
        model_root=model_root,
        receipt_root=receipt_root,
        encoder=SemanticEncoder(),
    )
    assert system.receipt.system_id == "dense-bge-retrieval-v1"
    assert len(system.receipt.model_receipt_sha256s) == 1

    receipt["mode"] = "metadata"
    path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ValueError, match="full publication-eligible"):
        build_dense_bge_system(
            registry_path=Path("models/registry.yaml"),
            model_root=model_root,
            receipt_root=receipt_root,
            encoder=SemanticEncoder(),
        )

