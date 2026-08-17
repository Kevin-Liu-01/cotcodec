#!/usr/bin/env python3
"""Serve a pinned local Hugging Face embedding checkpoint through OpenAI's API shape."""

from __future__ import annotations

import argparse
import json
import sys
import threading
from collections.abc import Sequence
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Protocol

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.fetch_open_model import (  # noqa: E402
    DEFAULT_MODEL_ROOT,
    DEFAULT_RECEIPT_ROOT,
    DEFAULT_REGISTRY,
    load_registry,
    receipt_path,
    sha256_file,
    verify_receipt,
)


class EmbeddingBackend(Protocol):
    dimensions: int
    maximum_tokens: int
    pooling_strategy: str

    def embed(self, texts: Sequence[str]) -> tuple[list[list[float]], int]: ...


class TransformersEmbeddingBackend:
    """CLS-pool and L2-normalize one reviewed local BGE checkpoint."""

    pooling_strategy = "cls-l2-normalized-v1"

    def __init__(self, snapshot: Path, *, maximum_tokens: int = 512) -> None:
        import torch
        from transformers import AutoModel, AutoTokenizer

        self._torch = torch
        self._tokenizer = AutoTokenizer.from_pretrained(
            snapshot,
            local_files_only=True,
            trust_remote_code=False,
        )
        self._model = AutoModel.from_pretrained(
            snapshot,
            local_files_only=True,
            trust_remote_code=False,
        )
        self._model.eval()
        self.maximum_tokens = maximum_tokens
        self.dimensions = int(self._model.config.hidden_size)
        self._inference_lock = threading.Lock()

    def embed(self, texts: Sequence[str]) -> tuple[list[list[float]], int]:
        if not texts:
            return [], 0
        encoded = self._tokenizer(
            list(texts),
            padding=True,
            truncation=True,
            max_length=self.maximum_tokens,
            return_tensors="pt",
        )
        token_count = int(encoded["attention_mask"].sum().item())
        with self._inference_lock, self._torch.inference_mode():
            hidden = self._model(**encoded).last_hidden_state
            pooled = hidden[:, 0]
            normalized = self._torch.nn.functional.normalize(pooled, p=2, dim=1)
        return normalized.cpu().tolist(), token_count


class HuggingFaceEmbeddingHandler(BaseHTTPRequestHandler):
    server: HuggingFaceEmbeddingServer

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, separators=(",", ":"), allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._json(200, self.server.health_payload())
            return
        if self.path == "/stats":
            with self.server.counter_lock:
                counters = {
                    "request_count": self.server.request_count,
                    "input_count": self.server.input_count,
                    "token_count": self.server.token_count,
                }
            self._json(200, {**self.server.identity_payload(), **counters})
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path.rstrip("/") != "/v1/embeddings":
            self._json(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > self.server.maximum_request_bytes:
                raise ValueError("invalid request size")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("request must be a JSON object")
            if payload.get("model") != self.server.api_model_id:
                raise ValueError("unexpected embedding model")
            inputs = payload.get("input")
            if isinstance(inputs, str):
                inputs = [inputs]
            if (
                not isinstance(inputs, list)
                or not inputs
                or len(inputs) > self.server.maximum_batch_size
                or not all(isinstance(item, str) for item in inputs)
            ):
                raise ValueError("input must be a non-empty bounded string list")
            requested_dimensions = payload.get("dimensions", self.server.backend.dimensions)
            if requested_dimensions != self.server.backend.dimensions:
                raise ValueError("unexpected embedding dimensions")
            embeddings, token_count = self.server.backend.embed(inputs)
            if len(embeddings) != len(inputs):
                raise RuntimeError("embedding backend returned the wrong row count")
            with self.server.counter_lock:
                self.server.request_count += 1
                self.server.input_count += len(inputs)
                self.server.token_count += token_count
            self._json(
                200,
                {
                    "object": "list",
                    **self.server.identity_payload(),
                    "data": [
                        {"object": "embedding", "index": index, "embedding": embedding}
                        for index, embedding in enumerate(embeddings)
                    ],
                    "usage": {"prompt_tokens": token_count, "total_tokens": token_count},
                },
            )
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            self._json(400, {"error": {"message": str(exc), "type": "invalid_request"}})


class HuggingFaceEmbeddingServer(ThreadingHTTPServer):
    def __init__(
        self,
        address: tuple[str, int],
        *,
        api_model_id: str,
        registry_model_id: str,
        revision: str,
        artifact_root_sha256: str,
        model_receipt_sha256: str,
        publication_eligible: bool,
        backend: EmbeddingBackend,
        maximum_batch_size: int = 128,
        maximum_request_bytes: int = 4 * 1024 * 1024,
    ) -> None:
        self.api_model_id = api_model_id
        self.registry_model_id = registry_model_id
        self.revision = revision
        self.artifact_root_sha256 = artifact_root_sha256
        self.model_receipt_sha256 = model_receipt_sha256
        self.publication_eligible = publication_eligible
        self.backend = backend
        self.maximum_batch_size = maximum_batch_size
        self.maximum_request_bytes = maximum_request_bytes
        self.counter_lock = threading.Lock()
        self.request_count = 0
        self.input_count = 0
        self.token_count = 0
        super().__init__(address, HuggingFaceEmbeddingHandler)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "model": self.api_model_id,
            "registry_model_id": self.registry_model_id,
            "revision": self.revision,
            "artifact_root_sha256": self.artifact_root_sha256,
            "model_receipt_sha256": self.model_receipt_sha256,
            "dimensions": self.backend.dimensions,
            "maximum_tokens": self.backend.maximum_tokens,
            "pooling_strategy": self.backend.pooling_strategy,
            "publication_eligible": self.publication_eligible,
        }

    def health_payload(self) -> dict[str, Any]:
        return {"status": "ok", **self.identity_payload()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18082)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--model-root", type=Path, default=DEFAULT_MODEL_ROOT)
    parser.add_argument("--receipt-root", type=Path, default=DEFAULT_RECEIPT_ROOT)
    parser.add_argument("--model-id", default="bge-small-en-v1.5")
    parser.add_argument("--maximum-tokens", type=int, default=512)
    args = parser.parse_args()

    registry = load_registry(args.registry.resolve())
    entry = registry["models"].get(args.model_id)
    if not isinstance(entry, dict) or entry.get("backend") != "huggingface":
        raise ValueError(f"{args.model_id!r} is not a registered Hugging Face model")
    receipt = verify_receipt(
        args.model_id,
        entry,
        args.model_root.resolve(),
        args.receipt_root.resolve(),
    )
    if receipt.get("mode") != "full" or not receipt.get("publication_eligible"):
        raise ValueError("embedding server requires a full publication-eligible receipt")
    backend = TransformersEmbeddingBackend(
        args.model_root.resolve() / args.model_id,
        maximum_tokens=args.maximum_tokens,
    )
    server = HuggingFaceEmbeddingServer(
        (args.host, args.port),
        api_model_id=entry["repo_id"],
        registry_model_id=args.model_id,
        revision=entry["revision"],
        artifact_root_sha256=receipt["artifact_root_sha256"],
        model_receipt_sha256=sha256_file(
            receipt_path(args.receipt_root.resolve(), args.model_id)
        ),
        publication_eligible=True,
        backend=backend,
    )
    print(
        json.dumps(
            {
                "status": "ready",
                "url": f"http://{args.host}:{args.port}/v1",
                **server.identity_payload(),
            },
            sort_keys=True,
        ),
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
