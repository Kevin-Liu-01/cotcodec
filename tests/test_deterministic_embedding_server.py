from __future__ import annotations

import math
import threading

import httpx
import pytest

from scripts.run_deterministic_embedding_server import (
    EmbeddingServer,
    deterministic_embedding,
)


def test_deterministic_embedding_is_stable_and_normalized() -> None:
    first = deterministic_embedding("alpha beta beta", 32)
    second = deterministic_embedding("alpha beta beta", 32)
    different = deterministic_embedding("gamma delta", 32)
    assert first == second
    assert first != different
    assert math.sqrt(sum(value * value for value in first)) == pytest.approx(1.0)


def test_embedding_server_exposes_smoke_usage_counts() -> None:
    server = EmbeddingServer(
        ("127.0.0.1", 0), model_id="test-embedding", dimensions=16
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        response = httpx.post(
            f"http://{host}:{port}/v1/embeddings",
            json={"model": "test-embedding", "input": ["one", "two"]},
        )
        response.raise_for_status()
        stats = httpx.get(f"http://{host}:{port}/stats").json()
        assert stats["request_count"] == 1
        assert stats["input_count"] == 2
        assert stats["scientific_evidence"] is False
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
