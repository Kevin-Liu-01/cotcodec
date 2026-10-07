"""Shared fakes for the serving-probe tests: a word tokenizer and a fake vLLM server.

Not collected by pytest (no ``test_`` prefix); test modules import it as a sibling.
"""

from __future__ import annotations

import asyncio
import json
import re
import types
from typing import Any

import httpx

IMAGE_TOKENS = 2040
WRAPPER_TOKENS = 2


class WordTokenizer:
    """Token ``i`` is the word ``w<i>``; ids below 3 are special."""

    vocab_size = 500
    all_special_ids = [0, 1, 2]

    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
        return [int(word[1:]) for word in text.split() if re.fullmatch(r"w\d+", word)]

    def decode(self, ids: list[int]) -> str:
        return " ".join(f"w{int(token)}" for token in ids)


def message_tokens(messages: list[dict[str, Any]]) -> tuple[int, int]:
    """(text tokens, images) of a chat request under :class:`WordTokenizer`."""
    tokenizer = WordTokenizer()
    text = 0
    images = 0
    for message in messages:
        for part in message["content"]:
            if part["type"] == "text":
                text += len(tokenizer.encode(part["text"])) + 1
            else:
                images += 1
    return text, images


class FakeVllm:
    """A minimal OpenAI-chat streaming server with vLLM's counters and dev endpoints."""

    def __init__(self, *, latency_s: float = 0.0, fail_every: int = 0, on_request=None) -> None:
        self.latency_s = latency_s
        self.fail_every = fail_every
        self.on_request = on_request
        self.prompt_tokens = 0
        self.generation_tokens = 0
        self.requests = 0
        self.in_flight = 0
        self.max_in_flight = 0
        self.bodies: list[dict[str, Any]] = []
        self.resets = 0
        self.alive = True

    def metrics_text(self) -> str:
        return (
            "# HELP vllm:prompt_tokens_total Prompt tokens\n"
            f'vllm:prompt_tokens_total{{model_name="probe-model"}} {float(self.prompt_tokens)}\n'
            f'vllm:generation_tokens_total{{model_name="m"}} {float(self.generation_tokens)}\n'
            'vllm:prefix_cache_queries_total{model_name="probe-model"} 100.0\n'
            'vllm:prefix_cache_hits_total{model_name="probe-model"} 25.0\n'
            'vllm:kv_cache_usage_perc{model_name="probe-model"} 0.5\n'
            'vllm:num_requests_running{model_name="probe-model"} 1.0\n'
            'vllm:num_requests_waiting{model_name="probe-model"} 0.0\n'
        )

    def _stream(self, body: dict[str, Any], prompt: int, output: int) -> bytes:
        chunks = []
        for index in range(output):
            choice = {"index": 0, "delta": {"content": f" t{index}"}}
            if body.get("return_token_ids"):
                choice["token_ids"] = [7 + (index % 5)]
            chunks.append({"choices": [choice]})
        chunks.append(
            {"choices": [], "usage": {"prompt_tokens": prompt, "completion_tokens": output}}
        )
        lines = [f"data: {json.dumps(chunk)}\n\n" for chunk in chunks] + ["data: [DONE]\n\n"]
        return "".join(lines).encode()

    async def handle(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/health":
            return httpx.Response(200)
        if path == "/metrics":
            return httpx.Response(200, text=self.metrics_text())
        if path == "/reset_prefix_cache":
            self.resets += 1
            return httpx.Response(200, json={"success": True})
        if path in {"/reset_mm_cache", "/reset_encoder_cache"}:
            return httpx.Response(200)
        if path != "/v1/chat/completions":
            return httpx.Response(404)
        body = json.loads(request.content)
        self.requests += 1
        self.bodies.append(body)
        if self.on_request is not None:
            self.on_request(self)
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            if self.latency_s:
                await asyncio.sleep(self.latency_s)
        finally:
            self.in_flight -= 1
        if self.fail_every and self.requests % self.fail_every == 0:
            return httpx.Response(400, text="maximum context length exceeded")
        text, images = message_tokens(body["messages"])
        prompt = text + images * (IMAGE_TOKENS + WRAPPER_TOKENS)
        output = int(body["max_tokens"])
        self.prompt_tokens += prompt
        self.generation_tokens += output
        return httpx.Response(
            200,
            content=self._stream(body, prompt, output),
            headers={"content-type": "text/event-stream"},
        )

    def sync_handle(self, request: httpx.Request) -> httpx.Response:
        return asyncio.run(self.handle(request))

    def async_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(self.handle), base_url="http://fake")

    def sync_client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.sync_handle), base_url="http://fake")


class _FakeLLMEngine:
    def __init__(self, llm: FakeLLM) -> None:
        self.llm = llm

    def abort_request(self, request_ids: list[str], internal: bool = False) -> None:
        assert internal is False, "the probe aborts by external request id"
        self.llm.aborted.extend(request_ids)
        if not self.llm.abort_ignored:
            for request_id in request_ids:
                self.llm.pending.pop(request_id, None)

    def has_unfinished_requests(self) -> bool:
        return bool(self.llm.pending)


class FakeLLM:
    """vLLM ``LLM``'s request bookkeeping (v0.31.0 offline_utils).

    Request ids come from ``request_counter``; ``generate`` adds its prompts, then
    finishes every unfinished request, including those an interrupted earlier call
    left behind, and returns them all sorted by id.
    """

    def __init__(self, interrupt: type[BaseException]) -> None:
        self.request_counter = types.SimpleNamespace(counter=0)
        self.pending: dict[str, dict[str, Any]] = {}
        self.interrupt = interrupt
        self.interrupt_next = False
        self.abort_ignored = False
        self.aborted: list[str] = []
        self.llm_engine = _FakeLLMEngine(self)

    @property
    def unfinished(self) -> set[str]:
        return set(self.pending)

    def generate(self, prompts, params, use_tqdm: bool = False):
        for _prompt in prompts:
            request_id = str(self.request_counter.counter)
            self.request_counter.counter += 1
            self.pending[request_id] = params
        if self.interrupt_next:
            self.interrupt_next = False
            raise self.interrupt("deadline inside generate")
        finished = sorted(self.pending.items(), key=lambda item: int(item[0]))
        self.pending = {}
        return [
            types.SimpleNamespace(
                request_id=request_id,
                outputs=[
                    types.SimpleNamespace(token_ids=[0] * int(sampling["max_tokens"]))
                    for _ in range(int(sampling["n"]))
                ],
            )
            for request_id, sampling in finished
        ]
