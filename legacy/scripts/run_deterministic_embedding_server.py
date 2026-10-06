#!/usr/bin/env python3
"""OpenAI-compatible deterministic embedding server for interface smokes only."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

TOKEN_RE = re.compile(r"[a-z0-9]+")


def deterministic_embedding(text: str, dimensions: int) -> list[float]:
    if dimensions < 8:
        raise ValueError("dimensions must be at least 8")
    values = [0.0] * dimensions
    tokens = TOKEN_RE.findall(text.casefold()) or ["empty"]
    for token in tokens:
        digest = hashlib.sha256(token.encode()).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = -1.0 if digest[4] & 1 else 1.0
        values[index] += sign
    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return [value / norm for value in values]


class EmbeddingHandler(BaseHTTPRequestHandler):
    server: EmbeddingServer

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._json(
                200,
                {
                    "status": "ok",
                    "model": self.server.model_id,
                    "dimensions": self.server.dimensions,
                    "scientific_evidence": False,
                },
            )
            return
        if self.path == "/stats":
            with self.server.counter_lock:
                request_count = self.server.request_count
                input_count = self.server.input_count
            self._json(
                200,
                {
                    "model": self.server.model_id,
                    "request_count": request_count,
                    "input_count": input_count,
                    "scientific_evidence": False,
                },
            )
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path.rstrip("/") != "/v1/embeddings":
            self._json(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 4 * 1024 * 1024:
                raise ValueError("invalid request size")
            payload = json.loads(self.rfile.read(length))
            if payload.get("model") != self.server.model_id:
                raise ValueError("unexpected embedding model")
            inputs = payload.get("input")
            if isinstance(inputs, str):
                inputs = [inputs]
            if not isinstance(inputs, list) or not all(isinstance(item, str) for item in inputs):
                raise ValueError("input must be a string or string list")
            requested_dimensions = payload.get("dimensions", self.server.dimensions)
            if requested_dimensions != self.server.dimensions:
                raise ValueError("unexpected embedding dimensions")
            data = [
                {
                    "object": "embedding",
                    "index": index,
                    "embedding": deterministic_embedding(text, self.server.dimensions),
                }
                for index, text in enumerate(inputs)
            ]
            token_count = sum(len(TOKEN_RE.findall(text.casefold())) for text in inputs)
            with self.server.counter_lock:
                self.server.request_count += 1
                self.server.input_count += len(inputs)
            self._json(
                200,
                {
                    "object": "list",
                    "model": self.server.model_id,
                    "data": data,
                    "usage": {"prompt_tokens": token_count, "total_tokens": token_count},
                },
            )
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            self._json(400, {"error": {"message": str(exc), "type": "invalid_request"}})


class EmbeddingServer(ThreadingHTTPServer):
    def __init__(
        self,
        address: tuple[str, int],
        *,
        model_id: str,
        dimensions: int,
    ) -> None:
        self.model_id = model_id
        self.dimensions = dimensions
        self.counter_lock = threading.Lock()
        self.request_count = 0
        self.input_count = 0
        super().__init__(address, EmbeddingHandler)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18081)
    parser.add_argument("--model", default="cotcodec-deterministic-embedding-v1")
    parser.add_argument("--dimensions", type=int, default=384)
    args = parser.parse_args()
    server = EmbeddingServer(
        (args.host, args.port),
        model_id=args.model,
        dimensions=args.dimensions,
    )
    print(
        json.dumps(
            {
                "status": "ready",
                "url": f"http://{args.host}:{args.port}/v1",
                "model": args.model,
                "dimensions": args.dimensions,
                "scientific_evidence": False,
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
