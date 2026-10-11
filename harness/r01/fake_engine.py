"""An OpenAI-compatible fake engine with controllable nondeterminism (R01 tests only).

It stands in for vLLM v0.31.0 where no GPU may run. It never serves a measurement: the replay
driver and P0 refuse it unless ``allow_fake`` is set, which only the tests do.

Replies are H-OSW-fixed tool calls whose thinking and click coordinates are functions of the
request, so the fake has the properties the drivers must handle:

* **text identity**: with every noise knob at 0 the reply is a function of the request's text and
  image *count* only (``text_key``), so equal requests get byte-identical replies;
* **pixel sensitivity** (``pixel_text_p``, ``pixel_ir_p``): for that share of distinct image
  contents (a deterministic function of the full request, ``full_key``) the thinking, or also
  the action, changes, as a clock swap might;
* **serving noise** (``noise_text_p``, ``noise_ir_p``): a seeded draw per request in arrival
  order perturbs the thinking, or also the action; ``noise_needs_concurrency`` limits it to
  requests that arrive while another is in flight (batch-composition noise);
* **logprob dependence** (``logprobs_shift``): asking for log-probabilities changes the reply;
* vLLM's stream shape: the first chunk carries ``prompt_token_ids`` (text and per-image
  placeholder ids, never pixels), content chunks carry ``token_ids`` and, when asked,
  ``logprobs``; a usage chunk; ``[DONE]``;
* ``POST /reset_prefix_cache`` and ``POST /reset_encoder_cache`` (vLLM's dev-mode routes) answer
  200 and are logged with the in-flight count.

Standard library only.
"""

from __future__ import annotations

import hashlib
import http.server
import json
import os
import random
import socketserver
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

IMAGE_PLACEHOLDER_IDS = 64


def _strip_images(messages: Sequence[Mapping[str, Any]]) -> list[Any]:
    out = []
    for m in messages:
        content = m.get("content")
        if isinstance(content, list):
            parts = []
            for p in content:
                if isinstance(p, dict) and p.get("type") == "image_url":
                    parts.append({"type": "image"})
                else:
                    parts.append(p)
            out.append({**m, "content": parts})
        else:
            out.append(dict(m))
    return out


def text_key(messages: Sequence[Mapping[str, Any]]) -> str:
    stripped = json.dumps(_strip_images(messages), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(stripped.encode()).hexdigest()


def full_key(messages: Sequence[Mapping[str, Any]]) -> str:
    return hashlib.sha256(
        json.dumps(messages, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def prompt_ids(messages: Sequence[Mapping[str, Any]]) -> list[int]:
    """Text chunk ids plus a fixed run of placeholder ids per image: pixels never enter."""
    ids: list[int] = []
    for m in _strip_images(messages):
        content = m.get("content")
        parts = content if isinstance(content, list) else [{"type": "text", "text": str(content)}]
        for p in parts:
            if p.get("type") == "image":
                ids.extend([151655] * IMAGE_PLACEHOLDER_IDS)
            else:
                text = str(p.get("text", ""))
                ids.extend(
                    int(hashlib.sha256(text[i : i + 8].encode()).hexdigest()[:4], 16)
                    for i in range(0, len(text), 8)
                )
    return ids


def unit(hexdigest: str) -> float:
    return int(hexdigest[:8], 16) / 2**32


def tool_call(think: str, x: int, y: int) -> str:
    return (
        f"<think>\n{think}\n</think>\n\nAction: click.\n<tool_call>\n<function=computer_use>\n"
        f"<parameter=action>\nleft_click\n</parameter>\n<parameter=coordinate>\n[{x}, {y}]\n"
        "</parameter>\n</function>\n</tool_call>"
    )


class _Unix(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True


class _TCP(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True


class FakeEngine:
    def __init__(
        self,
        *,
        socket_path: str | None = None,
        seed: int = 0,
        noise_text_p: float = 0.0,
        noise_ir_p: float = 0.0,
        noise_needs_concurrency: bool = False,
        pixel_text_p: float = 0.0,
        pixel_ir_p: float = 0.0,
        logprobs_shift: bool = False,
        latency_s: float | Callable[[Mapping[str, Any]], float] = 0.0,
        mamba_mode: str | None = None,
    ):
        self.socket_path = socket_path
        self.rng = random.Random(seed)
        self.noise_text_p, self.noise_ir_p = noise_text_p, noise_ir_p
        self.noise_needs_concurrency = noise_needs_concurrency
        self.pixel_text_p, self.pixel_ir_p = pixel_text_p, pixel_ir_p
        self.logprobs_shift = logprobs_shift
        self.latency_s = latency_s
        self.mamba_mode = mamba_mode
        self.lock = threading.Lock()
        self.inflight = 0
        self.max_inflight = 0
        self.requests: list[dict[str, Any]] = []
        self.resets: list[dict[str, Any]] = []
        self._server: Any = None

    # ------------------------------------------------------------------ replies
    def reply(self, body: Mapping[str, Any], inflight: int, draw: float) -> str:
        messages = body.get("messages") or []
        tk, fk = text_key(messages), full_key(messages)
        think = f"plan {tk[:12]}"
        x, y = int(tk[12:16], 16) % 1000, int(tk[16:20], 16) % 1000
        u = unit(hashlib.sha256(("pix" + fk).encode()).hexdigest())
        if u < self.pixel_text_p:
            think += f" saw {fk[:6]}"
        if u < self.pixel_ir_p:
            x = (x + 1 + int(fk[:4], 16) % 97) % 1000
        noisy = not self.noise_needs_concurrency or inflight >= 2
        if noisy and draw < self.noise_text_p:
            think += f" drift {int(draw * 1e6)}"
        if noisy and draw < self.noise_ir_p:
            y = (y + 1 + int(draw * 1e6) % 89) % 1000
        if self.logprobs_shift and body.get("logprobs"):
            think += " lp"
        return tool_call(think, x, y)

    # ------------------------------------------------------------------ server
    def handler(self) -> type[http.server.BaseHTTPRequestHandler]:
        engine = self

        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"

            def address_string(self) -> str:
                return "local"

            def log_message(self, *args: Any) -> None:
                return None

            def _json(self, status: int, payload: Mapping[str, Any]) -> None:
                data = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self) -> None:  # noqa: N802
                if self.path == "/health":
                    self._json(200, {})
                elif self.path == "/v1/models":
                    self._json(200, {"data": [{"id": "s1a-model"}]})
                else:
                    self._json(404, {"error": "not found"})

            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                if self.path in ("/reset_prefix_cache", "/reset_encoder_cache"):
                    with engine.lock:
                        engine.resets.append(
                            {"path": self.path, "t": time.time(), "inflight": engine.inflight}
                        )
                    self._json(200, {})
                    return
                if self.path != "/v1/chat/completions":
                    self._json(404, {"error": "not found"})
                    return
                body = json.loads(raw or b"{}")
                with engine.lock:
                    engine.inflight += 1
                    engine.max_inflight = max(engine.max_inflight, engine.inflight)
                    inflight = engine.inflight
                    draw = engine.rng.random()
                try:
                    delay = (
                        engine.latency_s(body) if callable(engine.latency_s) else engine.latency_s
                    )
                    if delay:
                        time.sleep(delay)
                    text = engine.reply(body, inflight, draw)
                    with engine.lock:
                        engine.requests.append(
                            {
                                "t": time.time(),
                                "inflight": inflight,
                                "full_key": full_key(body.get("messages") or []),
                            }
                        )
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.end_headers()

                    def send(payload: Any) -> None:
                        data = payload if isinstance(payload, str) else json.dumps(payload)
                        self.wfile.write(f"data: {data}\n\n".encode())
                        self.wfile.flush()

                    ids = prompt_ids(body.get("messages") or [])
                    send(
                        {
                            "id": "fake",
                            "choices": [{"index": 0, "delta": {"role": "assistant"}}],
                            "prompt_token_ids": ids,
                        }
                    )
                    n = 0
                    for i in range(0, len(text), 4):
                        piece = text[i : i + 4]
                        tid = int(hashlib.sha256(piece.encode()).hexdigest()[:4], 16)
                        choice: dict[str, Any] = {
                            "index": 0,
                            "delta": {"content": piece},
                            "token_ids": [tid],
                        }
                        if body.get("logprobs"):
                            second = -2.0 - (tid % 100) / 100
                            choice["logprobs"] = {
                                "content": [
                                    {
                                        "token": piece,
                                        "logprob": -0.05,
                                        "top_logprobs": [
                                            {"token": piece, "logprob": -0.05},
                                            {"token": "~", "logprob": second},
                                        ],
                                    }
                                ]
                            }
                        send({"choices": [choice]})
                        n += 1
                    send({"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]})
                    send(
                        {
                            "choices": [],
                            "usage": {
                                "prompt_tokens": len(ids),
                                "completion_tokens": n,
                                "total_tokens": len(ids) + n,
                            },
                        }
                    )
                    send("[DONE]")
                finally:
                    with engine.lock:
                        engine.inflight -= 1

        return Handler

    def start(self) -> FakeEngine:
        if self.socket_path:
            if os.path.exists(self.socket_path):
                os.unlink(self.socket_path)
            self._server = _Unix(self.socket_path, self.handler())
        else:
            self._server = _TCP(("127.0.0.1", 0), self.handler())
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        return self

    @property
    def transport(self) -> str:
        if self.socket_path:
            return f"unix:{self.socket_path}"
        return f"tcp:127.0.0.1:{self._server.server_address[1]}"

    def engine_log(self) -> str:
        """A vLLM-like log line for the Mamba cache mode check (P0)."""
        if self.mamba_mode is None:
            return "INFO [scheduler.py:308] Chunked prefill is enabled.\n"
        return (
            f"INFO [config.py:643] Mamba cache mode is set to '{self.mamba_mode}' for "
            "Qwen3_5ForConditionalGeneration by default when prefix caching is enabled\n"
        )

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self.socket_path and os.path.exists(self.socket_path):
            os.unlink(self.socket_path)

    def __enter__(self) -> FakeEngine:
        return self.start()

    def __exit__(self, *exc: Any) -> None:
        self.stop()
