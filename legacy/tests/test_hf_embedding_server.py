from __future__ import annotations

import math
import threading
from collections.abc import Sequence

import httpx

from scripts.run_hf_embedding_server import HuggingFaceEmbeddingServer


class FakeSemanticBackend:
    dimensions = 3
    maximum_tokens = 16
    pooling_strategy = "cls-l2-normalized-v1"

    def embed(self, texts: Sequence[str]) -> tuple[list[list[float]], int]:
        rows = []
        for text in texts:
            raw = [float(len(text)), float(text.count(" ") + 1), 1.0]
            norm = math.sqrt(sum(value * value for value in raw))
            rows.append([value / norm for value in raw])
        return rows, sum(len(text.split()) for text in texts)


def test_hf_embedding_server_binds_receipt_and_counts_usage() -> None:
    server = HuggingFaceEmbeddingServer(
        ("127.0.0.1", 0),
        api_model_id="BAAI/bge-small-en-v1.5",
        registry_model_id="bge-small-en-v1.5",
        revision="5c38ec7c405ec4b44b94cc5a9bb96e735b38267a",
        artifact_root_sha256="a" * 64,
        model_receipt_sha256="c" * 64,
        publication_eligible=True,
        backend=FakeSemanticBackend(),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        response = httpx.post(
            f"http://{host}:{port}/v1/embeddings",
            json={
                "model": "BAAI/bge-small-en-v1.5",
                "input": ["alpha beta", "gamma"],
                "dimensions": 3,
            },
        )
        response.raise_for_status()
        payload = response.json()
        assert len(payload["data"]) == 2
        assert payload["usage"]["prompt_tokens"] == 3

        health = httpx.get(f"http://{host}:{port}/health").json()
        assert health["revision"] == "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"
        assert health["artifact_root_sha256"] == "a" * 64
        assert health["publication_eligible"] is True
        assert health["model_receipt_sha256"] == "c" * 64
        assert health["pooling_strategy"] == "cls-l2-normalized-v1"

        stats = httpx.get(f"http://{host}:{port}/stats").json()
        assert stats["request_count"] == 1
        assert stats["input_count"] == 2
        assert stats["token_count"] == 3
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_hf_embedding_server_rejects_model_and_dimension_drift() -> None:
    server = HuggingFaceEmbeddingServer(
        ("127.0.0.1", 0),
        api_model_id="BAAI/bge-small-en-v1.5",
        registry_model_id="bge-small-en-v1.5",
        revision="5c38ec7c405ec4b44b94cc5a9bb96e735b38267a",
        artifact_root_sha256="b" * 64,
        model_receipt_sha256="d" * 64,
        publication_eligible=True,
        backend=FakeSemanticBackend(),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        wrong_model = httpx.post(
            f"http://{host}:{port}/v1/embeddings",
            json={"model": "mutable-alias", "input": "alpha"},
        )
        assert wrong_model.status_code == 400
        wrong_dimensions = httpx.post(
            f"http://{host}:{port}/v1/embeddings",
            json={
                "model": "BAAI/bge-small-en-v1.5",
                "input": "alpha",
                "dimensions": 384,
            },
        )
        assert wrong_dimensions.status_code == 400
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
