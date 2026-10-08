"""A scripted OpenAI-compatible engine on a Unix-domain socket (tests and the CPU smoke).

It stands in for vLLM wherever no GPU may run: the unit tests, and the development VM
smoke of the episode lane (registration section 3.1 item 3: the driver is "tested end to
end against a fake engine"). It is never used for an episode that counts: the lane refuses
it outside ``purpose: development`` (``lane.validate_manifest``).

The script is JSON: ``{"replies": [REPLY, ...]}``. The reply for a request is chosen by the
number of assistant turns in its messages (turn ``k`` gets ``replies[min(k, n - 1)]``), so
concurrent episodes each walk the script from the start. A REPLY is either a string (the
completion text) or an object with any of ``text``, ``finish_reason`` (default ``stop``),
``completion_tokens``, ``status`` and ``message`` (an HTTP error instead of a completion),
``stream_error`` (an error object inside the stream) and ``sleep_s`` (before answering).

Like vLLM v0.31.0 with ``return_token_ids``, the first chunk carries ``prompt_token_ids``
(here: 16 integers derived from the SHA-256 of the canonical request messages), and the
stream ends with a usage chunk and ``[DONE]``. Every request is appended to ``--log`` as one
JSON line with its sampling fields and the SHA-256 of its messages (images by digest only).
Standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import http.server
import json
import os
import socketserver
import threading
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


def canonical_messages(messages: Sequence[Mapping[str, Any]]) -> str:
    return json.dumps(messages, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def fake_prompt_ids(messages: Sequence[Mapping[str, Any]]) -> list[int]:
    digest = hashlib.sha256(canonical_messages(messages).encode()).digest()
    return [int.from_bytes(digest[i : i + 2], "little") for i in range(0, 32, 2)]


def redact_images(messages: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """The messages with every data URL replaced by its SHA-256 (for logs)."""
    out = []
    for message in messages:
        content = message.get("content")
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "image_url":
                    url = (part.get("image_url") or {}).get("url", "")
                    digest = hashlib.sha256(url.encode()).hexdigest()
                    parts.append({"type": "image_url", "sha256": digest, "chars": len(url)})
                else:
                    parts.append(part)
            out.append({**message, "content": parts})
        else:
            out.append(dict(message))
    return out


class _Server(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    allow_reuse_address = True


class _TCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True


class FakeEngine:
    """Serve a script on ``socket_path`` (or 127.0.0.1:``tcp_port`` when the path is None) in
    a background thread (``start`` / ``stop``)."""

    def __init__(
        self,
        socket_path: str | None,
        script: Mapping[str, Any],
        log: str | None = None,
        tcp_port: int | None = None,
    ):
        if (socket_path is None) == (tcp_port is None):
            raise ValueError("give a socket path or a TCP port")
        self.socket_path = socket_path
        self.tcp_port = tcp_port
        self.replies = list(
            script.get("replies")
            or [
                "Action: Done.\n<tool_call>\n"
                "<function=computer_use>\n"
                "<parameter=action>\nterminate\n"
                "</parameter>\n<parameter=status>\n"
                "success\n</parameter>\n</function>\n"
                "</tool_call>"
            ]
        )
        self.log = log
        self.requests: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self._server: _Server | None = None
        self._thread: threading.Thread | None = None

    def reply_for(self, messages: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        turn = sum(1 for m in messages if m.get("role") == "assistant")
        reply = self.replies[min(turn, len(self.replies) - 1)]
        return {"text": reply} if isinstance(reply, str) else dict(reply)

    def record(self, body: Mapping[str, Any]) -> None:
        entry = {
            "t": time.time(),
            "model": body.get("model"),
            "sampling": {k: body.get(k) for k in ("temperature", "top_p", "top_k", "max_tokens")},
            "stream": body.get("stream"),
            "return_token_ids": body.get("return_token_ids"),
            "messages_sha256": hashlib.sha256(
                canonical_messages(body.get("messages") or []).encode()
            ).hexdigest(),
            "messages": redact_images(body.get("messages") or []),
        }
        with self._lock:
            self.requests.append(entry)
            if self.log:
                with open(self.log, "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(entry, sort_keys=True) + "\n")

    def handler(self) -> type[http.server.BaseHTTPRequestHandler]:
        engine = self

        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"

            def address_string(self) -> str:  # a Unix peer has no address
                return "unix"

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
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
                    self._json(200, {"data": [{"id": "fake"}]})
                else:
                    self._json(404, {"error": "not found"})

            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length) or b"{}")
                if self.path != "/v1/chat/completions":
                    self._json(404, {"error": "not found"})
                    return
                engine.record(body)
                messages = body.get("messages") or []
                reply = engine.reply_for(messages)
                if reply.get("sleep_s"):
                    time.sleep(float(reply["sleep_s"]))
                if reply.get("status"):
                    self._json(
                        int(reply["status"]),
                        {"error": {"message": reply.get("message", "scripted error")}},
                    )
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()

                def send(payload: Mapping[str, Any] | str) -> None:
                    text = payload if isinstance(payload, str) else json.dumps(payload)
                    self.wfile.write(f"data: {text}\n\n".encode())
                    self.wfile.flush()

                ids = fake_prompt_ids(messages)
                send({"id": "fake", "choices": [{"index": 0, "delta": {"role": "assistant"}}],
                      "prompt_token_ids": ids})  # fmt: skip
                if reply.get("stream_error"):
                    send({"error": {"message": reply["stream_error"]}})
                    send("[DONE]")
                    return
                text = str(reply.get("text", ""))
                for start in range(0, len(text), 24):
                    send({"choices": [{"index": 0, "delta": {"content": text[start:start + 24]},
                                       "token_ids": [0]}]})  # fmt: skip
                finish = reply.get("finish_reason", "stop")
                send({"choices": [{"index": 0, "delta": {}, "finish_reason": finish}]})
                completion_tokens = int(reply.get("completion_tokens", max(1, len(text) // 4)))
                send({"choices": [], "usage": {
                    "prompt_tokens": len(canonical_messages(messages)) // 4,
                    "completion_tokens": completion_tokens,
                    "total_tokens": completion_tokens + len(canonical_messages(messages)) // 4,
                }})  # fmt: skip
                send("[DONE]")

        return Handler

    def start(self) -> FakeEngine:
        if self.socket_path is None:
            self._server = _TCPServer(("127.0.0.1", self.tcp_port), self.handler())
        else:
            if os.path.exists(self.socket_path):
                os.unlink(self.socket_path)
            self._server = _Server(self.socket_path, self.handler())
            os.chmod(self.socket_path, 0o600)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self.socket_path is not None and os.path.exists(self.socket_path):
            os.unlink(self.socket_path)

    def __enter__(self) -> FakeEngine:
        return self.start()

    def __exit__(self, *exc: Any) -> None:
        self.stop()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    where = parser.add_mutually_exclusive_group(required=True)
    where.add_argument("--socket")
    where.add_argument("--tcp-port", type=int, help="serve on 127.0.0.1 (the bridge's tests)")
    parser.add_argument("--script", type=Path, required=True)
    parser.add_argument("--log", default=None)
    parser.add_argument("--stop-file", type=Path, default=None, help="exit when this file exists")
    args = parser.parse_args(argv)
    script = json.loads(args.script.read_text(encoding="utf-8"))
    engine = FakeEngine(args.socket, script, args.log, tcp_port=args.tcp_port)
    engine.start()
    try:
        while args.stop_file is None or not args.stop_file.exists():
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        engine.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
