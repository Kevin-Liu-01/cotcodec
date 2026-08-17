#!/usr/bin/env python3
"""Deterministic private-network OpenAI-compatible stub for the CPU doctor."""

from __future__ import annotations

import hashlib
import json
import math
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

DIMENSION = 16
MODEL = "cotcodec-deterministic-hash-v1"


def _vector(text: str) -> list[float]:
    values = [0.0] * DIMENSION
    tokens = re.findall(r"[a-z0-9_]+", text.lower())
    for token in tokens or ["<empty>"]:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:2], "big") % DIMENSION
        values[index] += 1.0 if digest[2] & 1 else -1.0
    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return [round(value / norm, 9) for value in values]


class Handler(BaseHTTPRequestHandler):
    server_version = "cotcodec-openviking-model-stub/1"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/health", "/v1/models"}:
            self._json(
                200,
                {
                    "object": "list",
                    "data": [{"id": MODEL, "object": "model"}],
                },
            )
            return
        self._json(404, {"error": {"message": "not found"}})

    def do_POST(self) -> None:  # noqa: N802
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._json(400, {"error": {"message": "invalid JSON"}})
            return

        if self.path == "/v1/embeddings":
            raw_input = payload.get("input", [])
            inputs = raw_input if isinstance(raw_input, list) else [raw_input]
            data = [
                {"object": "embedding", "index": index, "embedding": _vector(str(value))}
                for index, value in enumerate(inputs)
            ]
            self._json(
                200,
                {
                    "object": "list",
                    "model": payload.get("model") or MODEL,
                    "data": data,
                    "usage": {"prompt_tokens": len(inputs), "total_tokens": len(inputs)},
                },
            )
            return

        if self.path == "/v1/chat/completions":
            self._json(
                200,
                {
                    "id": "chatcmpl-cotcodec-openviking-doctor",
                    "object": "chat.completion",
                    "created": 0,
                    "model": payload.get("model") or MODEL,
                    "choices": [
                        {
                            "index": 0,
                            "finish_reason": "stop",
                            "message": {"role": "assistant", "content": "{}"},
                        }
                    ],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                },
            )
            return

        self._json(404, {"error": {"message": "not found"}})


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", 8080), Handler)
    server.serve_forever(poll_interval=0.1)


if __name__ == "__main__":
    main()
