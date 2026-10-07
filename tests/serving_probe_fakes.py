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


def write_job_dir(
    directory: Any,
    config: Any,
    job_id: str,
    points: dict[str, dict[str, Any]],
    *,
    status: str = "complete",
    exit_code: int = 0,
    termination: dict[str, Any] | None = None,
    lane_finished: bool = True,
) -> Any:
    """Write one job's lane run directory as the lane and the driver leave it.

    ``directory`` is the lane's run directory (mounted at /outputs). The driver's
    point files and finished summary.json go to ``directory / "probe"``, and the
    lane's termination.env to ``directory`` unless ``lane_finished`` is false. Its
    fields default to the batch script's own for the driver's ``exit_code``
    (``completed`` for 0, else ``workload_failed``); ``termination`` overrides
    them. ``points`` maps point ids to partial records (``status`` and
    ``result``); the identity fields the projection checks are filled in here.
    Returns the probe output directory.
    """
    import hashlib
    from pathlib import Path

    from harness.serving_probe import budget
    from scripts import run_vllm_throughput_probe as probe

    run_dir = Path(directory)
    if lane_finished:
        run_dir.mkdir(parents=True, exist_ok=True)
        fields = {
            "job_id": "1234",
            "reason": "completed" if exit_code == 0 else "workload_failed",
            "exit_code": exit_code,
            "finished_at": "2026-10-07T00:00:00Z",
            "checkpoint_ready": "false",
            "checkpoint_marker_present": "false",
            **(termination or {}),
        }
        (run_dir / probe.LANE_TERMINATION_FILE).write_text(
            "".join(f"{key}={value}\n" for key, value in fields.items()), encoding="utf-8"
        )
    directory = run_dir / "probe"
    (directory / "points").mkdir(parents=True, exist_ok=True)
    shas = {}
    for point_id, record in points.items():
        full = {
            "experiment_id": config.experiment_id,
            "config_sha256": config.sha256,
            "job": job_id,
            "point_id": point_id,
            **record,
        }
        path = directory / "points" / f"{point_id}.json"
        path.write_text(json.dumps(full), encoding="utf-8")
        shas[point_id] = hashlib.sha256(path.read_bytes()).hexdigest()
    summary: dict[str, Any] = {
        "experiment_id": config.experiment_id,
        "job": job_id,
        "config_sha256": config.sha256,
        "gates": {gate: {"pass": True} for gate in ("G0.0", "G0.1", "G0.2", "G0.3", "G0.4")},
        "status": status,
        "exit_code": exit_code,
        "points": {name: record.get("status") for name, record in points.items()},
        "point_sha256": shas,
        "eager": False,
        "image_variant": "cu129",
    }
    # The seed stability the driver records in a finished summary (_finalize).
    limit = float(config.section("validity")["unstable_relative_range"])
    if job_id == "a":
        summary["a1_stability"] = budget.stability(points, ("a1a", "a1b", "a1c"), limit)
    if job_id == "b":
        summary["b1_stability"] = budget.stability(
            points, ("b1a", "b1b", "b1c"), limit, metric="completions_per_s"
        )
    summary["acceptance"] = probe.job_acceptance(summary)
    (directory / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    return directory


def x1_passing_job_a_points() -> dict[str, dict[str, Any]]:
    """The six job A points control X1 reads, valid and within every threshold."""

    def opened(rate: float) -> dict[str, Any]:
        return {
            "status": "valid",
            "result": {"request_throughput": rate, "prompt_tokens": 960, "completed": 96},
        }

    def replay(latency_s: float) -> dict[str, Any]:
        return {
            "status": "valid",
            "result": {
                "e2el_ms": {"mean": latency_s * 1000.0},
                "prompt_tokens": 2400,
                "completed": 240,
                "per_step": {"1": {"mean_prompt_tokens": 10.0}},
            },
        }

    return {
        "a1a": opened(2.0),
        "a1b": opened(2.02),
        "a1c": opened(2.01),
        "x1-a1": opened(2.03),
        "r1": replay(5.0),
        "x1-r1": replay(5.05),
    }
