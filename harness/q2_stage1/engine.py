"""The S1a engine client: OpenAI-compatible chat completions over a Unix-domain socket.

Registration section 3.1 items 3-4 and section 7. The episode runner reaches the engine only
through the bridge's socket (D13: it sits in the VM container's ``--network none``
namespace), so this client speaks HTTP/1.1 over ``AF_UNIX`` with the standard library.

Every request streams (``stream: true``, ``stream_options.include_usage``) and sets
``return_token_ids``, so the step log gets what section 7.3 asks for without changing the
card's engine flags:

* the prompt token ids' SHA-256 (little-endian int64, the serving probe v2's digest) and
  count, from vLLM v0.31.0's first chunk (``prompt_token_ids``);
* prompt and output tokens (the usage chunk), and the cached-token count when the engine
  reports one (``usage.prompt_tokens_details.cached_tokens``; ``None`` otherwise);
* latency, time to first content token and time per output token; ``finish_reason``.

The request body is the registered sampling (``plan.sampling``: temperature 0.0, top_p 0.9,
top_k -1, max_tokens 2,048) plus the messages; nothing else that would change decoding is
sent. One retry policy serves both harnesses (registration section 5.2, "matched
runtime"): a transport error, HTTP 429 or a 5xx is retried up to ``ATTEMPTS`` times with
OSWorld's backoff (``min(5 x attempt, 30)`` s); a 4xx is not retried, and a context-length
rejection raises ``ContextLengthError`` so H-GA's context-variant fallback can tell it from
any other failure (section 7.2). A request that has not finished ``TIMEOUT_S`` after it was
sent raises ``EngineError(kind="timeout")`` and is not retried. Standard library only.
"""

from __future__ import annotations

import hashlib
import http.client
import json
import re
import socket
import struct
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

TIMEOUT_S = 600.0
ATTEMPTS = 5
CONNECT_TIMEOUT_S = 10.0
CHAT_PATH = "/v1/chat/completions"
CONTEXT_PATTERNS = re.compile(
    r"maximum context length|context length|context window|too long|exceeds? the model",
    re.IGNORECASE,
)


def backoff_s(attempt: int) -> float:
    """OSWorld ``Qwen35VLAgent.call_llm``'s sleep after a failed attempt (1-based)."""
    return min(5.0 * attempt, 30.0)


class EngineError(RuntimeError):
    """The engine did not return a completion. ``kind`` names why (section 7.2)."""

    def __init__(self, message: str, kind: str, attempts: Sequence[Mapping[str, Any]] = ()):
        super().__init__(message)
        self.kind = kind
        self.attempts = list(attempts)


class ContextLengthError(EngineError):
    """The engine rejected the prompt as longer than its context."""

    def __init__(self, message: str, attempts: Sequence[Mapping[str, Any]] = ()):
        super().__init__(message, "context_length", attempts)


def token_ids_sha256(ids: Sequence[int]) -> str:
    """SHA-256 of token ids as little-endian int64 (``serving_probe_v2.client``'s digest)."""
    return hashlib.sha256(struct.pack(f"<{len(ids)}q", *ids)).hexdigest()


def request_sha256(body: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


class UnixHTTPConnection(http.client.HTTPConnection):
    """HTTP/1.1 over a Unix-domain socket (the host part of the URL is ignored)."""

    def __init__(self, path: str, timeout: float):
        super().__init__("localhost", timeout=timeout)
        self.unix_path = path

    def connect(self) -> None:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(min(CONNECT_TIMEOUT_S, self.timeout or CONNECT_TIMEOUT_S))
        try:
            sock.connect(self.unix_path)
        except OSError:
            sock.close()
            raise
        sock.settimeout(self.timeout)
        self.sock = sock


@dataclass
class Completion:
    """One answered request, with what the step log records."""

    content: str
    finish_reason: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    cached_tokens: int | None
    prompt_ids_sha256: str | None
    prompt_id_count: int
    latency_s: float
    ttft_s: float | None
    tpot_s: float | None
    request_sha256: str
    attempts: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out.pop("content")
        return out


class _Retryable(Exception):
    pass


def parse_stream(lines: Any, clock: Callable[[], float], started: float) -> dict[str, Any]:
    """Fold an SSE stream (an iterable of raw lines) into content, usage and timings."""
    content: list[str] = []
    out: dict[str, Any] = {
        "finish_reason": None,
        "usage": None,
        "prompt_token_ids": None,
        "t_first": None,
        "t_last": None,
    }
    for raw in lines:
        line = raw.decode("utf-8", errors="replace").strip() if isinstance(raw, bytes) else raw
        if not line or not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            break
        try:
            chunk = json.loads(data)
        except json.JSONDecodeError as exc:
            raise EngineError(f"malformed stream chunk: {data[:200]}", "malformed") from exc
        if "error" in chunk and not chunk.get("choices"):
            message = json.dumps(chunk["error"])[:500]
            if CONTEXT_PATTERNS.search(message):
                raise ContextLengthError(message)
            raise EngineError(f"engine error in stream: {message}", "stream_error")
        if out["prompt_token_ids"] is None and chunk.get("prompt_token_ids") is not None:
            out["prompt_token_ids"] = [int(t) for t in chunk["prompt_token_ids"]]
        if chunk.get("usage"):
            out["usage"] = chunk["usage"]
        for choice in chunk.get("choices") or []:
            delta = choice.get("delta") or {}
            text = delta.get("content")
            if text:
                now = clock()
                if out["t_first"] is None:
                    out["t_first"] = now
                out["t_last"] = now
                content.append(text)
            if choice.get("finish_reason"):
                out["finish_reason"] = choice["finish_reason"]
    out["content"] = "".join(content)
    return out


class EngineClient:
    """Chat completions against the bridge socket, one retry policy for both harnesses."""

    def __init__(
        self,
        socket_path: str,
        model: str,
        *,
        timeout_s: float = TIMEOUT_S,
        attempts: int = ATTEMPTS,
        sleep: Callable[[float], None] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.socket_path = socket_path
        self.model = model
        self.timeout_s = timeout_s
        self.attempts = attempts
        self.sleep = sleep
        self.clock = clock

    def body(self, messages: Sequence[Mapping[str, Any]], sampling: Mapping[str, Any]) -> dict:
        allowed = {"temperature", "top_p", "top_k", "max_tokens"}
        unknown = set(sampling) - allowed
        if unknown:
            raise ValueError(f"sampling keys outside the registration: {sorted(unknown)}")
        return {
            "model": self.model,
            "messages": list(messages),
            **dict(sampling),
            "stream": True,
            "stream_options": {"include_usage": True},
            "return_token_ids": True,
        }

    def _once(self, payload: bytes, deadline: float) -> dict[str, Any]:
        remaining = deadline - self.clock()
        if remaining <= 0:
            raise EngineError("request deadline passed", "timeout")
        conn = UnixHTTPConnection(self.socket_path, timeout=remaining)
        started = self.clock()
        try:
            try:
                conn.request(
                    "POST",
                    CHAT_PATH,
                    body=payload,
                    headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
                )
                response = conn.getresponse()
            except TimeoutError as exc:
                raise EngineError(f"no response within {self.timeout_s} s", "timeout") from exc
            except (OSError, http.client.HTTPException) as exc:
                raise _Retryable(f"transport: {type(exc).__name__}: {exc}") from exc
            status = response.status
            if status != 200:
                text = response.read().decode("utf-8", errors="replace")[:1000]
                if status == 429 or status >= 500:
                    raise _Retryable(f"HTTP {status}: {text[:300]}")
                if status == 400 and CONTEXT_PATTERNS.search(text):
                    raise ContextLengthError(f"HTTP 400: {text[:500]}")
                raise EngineError(f"HTTP {status}: {text[:500]}", "bad_request")
            try:
                parsed = parse_stream(
                    _lines_until(conn, response, deadline, self.clock), self.clock, started
                )
            except TimeoutError as exc:
                raise EngineError(f"stream stalled past {self.timeout_s} s", "timeout") from exc
            except (OSError, http.client.HTTPException) as exc:
                raise _Retryable(f"stream transport: {type(exc).__name__}: {exc}") from exc
            parsed["started"] = started
            parsed["finished"] = self.clock()
            return parsed
        finally:
            conn.close()

    def chat(
        self, messages: Sequence[Mapping[str, Any]], sampling: Mapping[str, Any]
    ) -> Completion:
        body = self.body(messages, sampling)
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        digest = request_sha256(body)
        sent = self.clock()
        deadline = sent + self.timeout_s
        attempts: list[dict[str, Any]] = []
        for attempt in range(1, self.attempts + 1):
            t0 = self.clock()
            try:
                parsed = self._once(payload, deadline)
            except _Retryable as exc:
                attempts.append(
                    {"attempt": attempt, "error": str(exc)[:300], "s": self.clock() - t0}
                )
                if attempt == self.attempts:
                    raise EngineError(
                        f"engine request failed after {attempt} attempts: {exc}",
                        "transport",
                        attempts,
                    ) from exc
                (self.sleep or time.sleep)(backoff_s(attempt))
                continue
            except ContextLengthError as exc:
                attempts.append(
                    {"attempt": attempt, "error": str(exc)[:300], "s": self.clock() - t0}
                )
                raise ContextLengthError(str(exc), attempts) from exc
            except EngineError as exc:
                attempts.append(
                    {"attempt": attempt, "error": str(exc)[:300], "s": self.clock() - t0}
                )
                raise EngineError(str(exc), exc.kind, attempts) from exc
            attempts.append({"attempt": attempt, "ok": True, "s": round(self.clock() - t0, 4)})
            usage = parsed["usage"] or {}
            details = usage.get("prompt_tokens_details") or {}
            ids = parsed["prompt_token_ids"]
            completion_tokens = usage.get("completion_tokens")
            t_first, t_last = parsed["t_first"], parsed["t_last"]
            tpot = None
            if t_first is not None and t_last is not None and (completion_tokens or 0) > 1:
                tpot = (t_last - t_first) / (completion_tokens - 1)
            completion = Completion(
                finish_reason=parsed["finish_reason"],
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=completion_tokens,
                cached_tokens=details.get("cached_tokens"),
                prompt_ids_sha256=token_ids_sha256(ids) if ids is not None else None,
                prompt_id_count=len(ids) if ids is not None else 0,
                latency_s=round(parsed["finished"] - parsed["started"], 4),
                ttft_s=None if t_first is None else round(t_first - parsed["started"], 4),
                tpot_s=None if tpot is None else round(tpot, 6),
                request_sha256=digest,
                attempts=attempts,
                content=parsed["content"],
            )
            return completion
        raise AssertionError("unreachable")


def _lines_until(
    conn: http.client.HTTPConnection,
    response: http.client.HTTPResponse,
    deadline: float,
    clock: Callable[[], float],
):
    """The response's lines; a read past the request deadline raises ``TimeoutError``."""
    while True:
        remaining = deadline - clock()
        if remaining <= 0:
            raise TimeoutError("request deadline passed")
        if conn.sock is not None:
            conn.sock.settimeout(remaining)
        line = response.readline()
        if not line:
            return
        yield line


def health(socket_path: str, timeout: float = 5.0) -> bool:
    """Whether the engine answers ``GET /health`` with 200 through the socket."""
    conn = UnixHTTPConnection(socket_path, timeout=timeout)
    try:
        conn.request("GET", "/health")
        return conn.getresponse().status == 200
    except (OSError, http.client.HTTPException):
        return False
    finally:
        conn.close()
