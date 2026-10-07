"""Streaming OpenAI-chat client, open-loop runner and closed-loop episode replay.

One client implementation serves every server-mode point, so open-loop
brackets, replays, the front-end control and the A/A check share request
construction, timing and token accounting. Timing uses ``time.perf_counter``.
Responses are kept in memory only as long as a replay needs them as assistant
history; nothing generated is written to disk except token counts and, for the
A/A check, SHA-256 digests of the generated token ids.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import threading
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

import httpx

PERCENTILES = (50, 90, 99)


class StopToken:
    """Combined deadline and external (signal) stop for a running point."""

    def __init__(
        self,
        *,
        deadline: float | None,
        external: threading.Event | None = None,
        grace_s: float = 30.0,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self.deadline = deadline
        self.external = external or threading.Event()
        self.grace_s = grace_s
        self.clock = clock

    def triggered(self) -> bool:
        if self.external.is_set():
            return True
        return self.deadline is not None and self.clock() >= self.deadline

    def reason(self) -> str | None:
        if self.external.is_set():
            return "signal"
        if self.deadline is not None and self.clock() >= self.deadline:
            return "deadline"
        return None

    async def sleep(self, seconds: float) -> bool:
        """Sleep up to ``seconds``; return False early if the stop triggers."""
        end = self.clock() + seconds
        while True:
            if self.triggered():
                return False
            remaining = end - self.clock()
            if remaining <= 0:
                return True
            await asyncio.sleep(min(0.2, remaining))


@dataclass
class ChatRequest:
    messages: list[dict[str, Any]]
    max_tokens: int
    thinking: bool
    tag: tuple[int, ...] = ()
    collect_token_ids: bool = False


@dataclass
class RequestResult:
    tag: tuple[int, ...]
    ok: bool
    error: str | None
    sent_at: float
    finished_at: float
    first_token_at: float | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    itl_s: list[float] = field(default_factory=list)
    text: str = ""
    token_ids_sha256: str | None = None
    token_id_count: int = 0

    @property
    def e2el_s(self) -> float:
        return self.finished_at - self.sent_at

    @property
    def ttft_s(self) -> float | None:
        return None if self.first_token_at is None else self.first_token_at - self.sent_at

    @property
    def tpot_s(self) -> float | None:
        if self.first_token_at is None or self.completion_tokens < 2:
            return None
        return (self.finished_at - self.first_token_at) / (self.completion_tokens - 1)


def build_payload(request: ChatRequest, *, model: str) -> dict[str, Any]:
    """Fixed-length generation: greedy, EOS and stop tokens suppressed."""
    payload: dict[str, Any] = {
        "model": model,
        "messages": request.messages,
        "max_tokens": request.max_tokens,
        "min_tokens": request.max_tokens,
        "ignore_eos": True,
        "temperature": 0.0,
        "top_p": 1.0,
        "stream": True,
        "stream_options": {"include_usage": True},
        "chat_template_kwargs": {"enable_thinking": bool(request.thinking)},
    }
    if request.collect_token_ids:
        payload["return_token_ids"] = True
    return payload


async def stream_chat(
    client: httpx.AsyncClient,
    request: ChatRequest,
    *,
    model: str,
    timeout_s: float,
    clock: Callable[[], float] = time.perf_counter,
) -> RequestResult:
    """Send one streaming chat completion and time it."""
    payload = build_payload(request, model=model)
    sent = clock()
    first: float | None = None
    last_token_at: float | None = None
    itl: list[float] = []
    texts: list[str] = []
    token_ids: list[int] = []
    usage: dict[str, Any] = {}
    try:
        async with client.stream(
            "POST", "/v1/chat/completions", json=payload, timeout=timeout_s
        ) as response:
            if response.status_code != 200:
                body = (await response.aread()).decode("utf-8", "replace")[:300]
                return RequestResult(
                    request.tag, False, f"http {response.status_code}: {body}", sent, clock()
                )
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                chunk = json.loads(data)
                if chunk.get("usage"):
                    usage = chunk["usage"]
                produced = False
                for choice in chunk.get("choices") or []:
                    delta = choice.get("delta") or {}
                    piece = (delta.get("content") or "") + (
                        delta.get("reasoning_content") or delta.get("reasoning") or ""
                    )
                    ids = choice.get("token_ids") or delta.get("token_ids") or []
                    if piece:
                        texts.append(piece)
                    if ids:
                        token_ids.extend(int(token) for token in ids)
                    produced = produced or bool(piece) or bool(ids)
                if produced:
                    now = clock()
                    if first is None:
                        first = now
                    elif last_token_at is not None:
                        itl.append(now - last_token_at)
                    last_token_at = now
    except (TimeoutError, httpx.HTTPError, json.JSONDecodeError) as exc:
        return RequestResult(
            request.tag, False, f"{type(exc).__name__}: {exc}"[:300], sent, clock()
        )
    finished = clock()
    if not usage:
        return RequestResult(request.tag, False, "stream ended without usage", sent, finished)
    digest = None
    if request.collect_token_ids:
        digest = hashlib.sha256(json.dumps(token_ids).encode()).hexdigest() if token_ids else None
    return RequestResult(
        tag=request.tag,
        ok=True,
        error=None,
        sent_at=sent,
        finished_at=finished,
        first_token_at=first,
        prompt_tokens=int(usage.get("prompt_tokens", 0)),
        completion_tokens=int(usage.get("completion_tokens", 0)),
        itl_s=itl,
        text="".join(texts),
        token_ids_sha256=digest,
        token_id_count=len(token_ids),
    )


async def _with_stop(tasks: list[asyncio.Task[Any]], stop: StopToken, poll_s: float = 0.2) -> None:
    """Wait for ``tasks``; once ``stop`` triggers, give them the grace period, then cancel."""
    pending = set(tasks)
    grace_end: float | None = None
    while pending:
        done, pending = await asyncio.wait(pending, timeout=poll_s)
        if not pending:
            break
        if stop.triggered():
            now = stop.clock()
            if grace_end is None:
                grace_end = now + stop.grace_s
            elif now >= grace_end:
                for task in pending:
                    task.cancel()
                await asyncio.gather(*pending, return_exceptions=True)
                return


async def run_open_loop(
    client: httpx.AsyncClient,
    requests: Sequence[ChatRequest],
    *,
    concurrency: int,
    model: str,
    timeout_s: float,
    stop: StopToken,
) -> tuple[list[RequestResult], float, float, int]:
    """Send ``requests`` with at most ``concurrency`` in flight (request rate unbounded).

    Returns results, start and end times, and the number never launched.
    """
    semaphore = asyncio.Semaphore(concurrency)
    results: list[RequestResult] = []
    skipped = 0

    async def one(request: ChatRequest) -> None:
        nonlocal skipped
        async with semaphore:
            if stop.triggered():
                skipped += 1
                return
            results.append(
                await stream_chat(
                    client, request, model=model, timeout_s=timeout_s, clock=stop.clock
                )
            )

    start = stop.clock()
    tasks = [asyncio.create_task(one(request)) for request in requests]
    await _with_stop(tasks, stop)
    end = stop.clock()
    cancelled = sum(1 for task in tasks if task.cancelled())
    return results, start, end, skipped + cancelled


@dataclass
class EpisodePlan:
    episode: int
    start_offset_s: float
    steps: list[int]
    prebuilt_responses: list[str]
    build: Callable[[int, list[str]], list[dict[str, Any]]]
    output_tokens: int
    thinking: bool
    t_env_s: float


@dataclass
class StepRecord:
    episode: int
    step: int
    result: RequestResult


async def run_replay(
    client: httpx.AsyncClient,
    episodes: Sequence[EpisodePlan],
    *,
    model: str,
    timeout_s: float,
    stop: StopToken,
) -> tuple[list[StepRecord], float, float, dict[int, tuple[float, float]]]:
    """Closed-loop replay: each episode waits ``t_env_s`` between its steps."""
    records: list[StepRecord] = []
    spans: dict[int, tuple[float, float]] = {}

    async def episode_task(plan: EpisodePlan) -> None:
        if plan.start_offset_s > 0 and not await stop.sleep(plan.start_offset_s):
            return
        began = stop.clock()
        responses = list(plan.prebuilt_responses)
        for index, step in enumerate(plan.steps):
            if stop.triggered():
                break
            request = ChatRequest(
                messages=plan.build(step, responses),
                max_tokens=plan.output_tokens,
                thinking=plan.thinking,
                tag=(plan.episode, step),
            )
            result = await stream_chat(
                client, request, model=model, timeout_s=timeout_s, clock=stop.clock
            )
            records.append(StepRecord(plan.episode, step, result))
            spans[plan.episode] = (began, stop.clock())
            if not result.ok:
                break
            responses.append(result.text)
            if index < len(plan.steps) - 1 and not await stop.sleep(plan.t_env_s):
                break

    start = stop.clock()
    tasks = [asyncio.create_task(episode_task(plan)) for plan in episodes]
    await _with_stop(tasks, stop)
    return records, start, stop.clock(), spans


async def run_aa(
    client: httpx.AsyncClient,
    requests: Sequence[ChatRequest],
    *,
    arms: Sequence[int],
    model: str,
    timeout_s: float,
    stop: StopToken,
    between_arms: Callable[[], Awaitable[None]],
) -> list[list[RequestResult]]:
    """Run the same requests once per concurrency arm, resetting caches between arms."""
    outcomes: list[list[RequestResult]] = []
    for index, concurrency in enumerate(arms):
        if index:
            await between_arms()
        tagged = [
            ChatRequest(r.messages, r.max_tokens, r.thinking, r.tag, collect_token_ids=True)
            for r in requests
        ]
        results, _start, _end, _skipped = await run_open_loop(
            client, tagged, concurrency=concurrency, model=model, timeout_s=timeout_s, stop=stop
        )
        outcomes.append(sorted(results, key=lambda result: result.tag))
    return outcomes


def percentile_summary(
    values: Sequence[float], *, scale: float = 1000.0
) -> dict[str, float | None]:
    """Mean and p50/p90/p99 (linear interpolation), scaled (default seconds -> ms)."""
    clean = sorted(float(value) for value in values if value is not None and math.isfinite(value))
    if not clean:
        return {"mean": None, **{f"p{p}": None for p in PERCENTILES}}
    summary: dict[str, float | None] = {"mean": scale * sum(clean) / len(clean)}
    for p in PERCENTILES:
        rank = (len(clean) - 1) * p / 100
        low = math.floor(rank)
        high = math.ceil(rank)
        value = clean[low] + (clean[high] - clean[low]) * (rank - low)
        summary[f"p{p}"] = scale * value
    return summary


def summarize_requests(
    results: Sequence[RequestResult],
    *,
    planned: int,
    start: float,
    end: float,
    expected_output: int,
) -> dict[str, Any]:
    ok = [result for result in results if result.ok]
    failed = [result for result in results if not result.ok]
    duration = max(end - start, 1e-9)
    prompt_tokens = sum(result.prompt_tokens for result in ok)
    output_tokens = sum(result.completion_tokens for result in ok)
    itl = [gap for result in ok for gap in result.itl_s]
    return {
        "planned": planned,
        "completed": len(ok),
        "failed": len(failed) + (planned - len(results)),
        "errors": sorted({str(result.error) for result in failed})[:5],
        "duration_s": duration,
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "short_outputs": sum(1 for result in ok if result.completion_tokens != expected_output),
        "request_throughput": len(ok) / duration,
        "output_throughput": output_tokens / duration,
        "total_token_throughput": (prompt_tokens + output_tokens) / duration,
        "ttft_ms": percentile_summary([r.ttft_s for r in ok if r.ttft_s is not None]),
        "tpot_ms": percentile_summary([r.tpot_s for r in ok if r.tpot_s is not None]),
        "itl_ms": percentile_summary(itl),
        "e2el_ms": percentile_summary([r.e2el_s for r in ok]),
    }


def summarize_replay(
    records: Sequence[StepRecord],
    *,
    episodes: int,
    planned_steps: Sequence[int],
    start: float,
    end: float,
    spans: dict[int, tuple[float, float]],
    expected_output: int,
) -> dict[str, Any]:
    by_step: dict[int, list[RequestResult]] = {step: [] for step in planned_steps}
    for record in records:
        by_step.setdefault(record.step, []).append(record.result)
    per_step: dict[str, Any] = {}
    complete_steps: list[int] = []
    for step in planned_steps:
        results = by_step.get(step, [])
        ok = [result for result in results if result.ok]
        if len(ok) == episodes:
            complete_steps.append(step)
        latencies = [result.e2el_s for result in ok]
        per_step[str(step)] = {
            "completed": len(ok),
            "failed": len(results) - len(ok),
            "latency_s": percentile_summary(latencies, scale=1.0),
            "max_latency_s": max(latencies) if latencies else None,
            "ttft_s": percentile_summary([r.ttft_s for r in ok if r.ttft_s is not None], scale=1.0),
            "tpot_ms": percentile_summary([r.tpot_s for r in ok if r.tpot_s is not None]),
            "mean_prompt_tokens": (sum(r.prompt_tokens for r in ok) / len(ok)) if ok else None,
            "mean_output_tokens": (sum(r.completion_tokens for r in ok) / len(ok)) if ok else None,
        }
    all_results = [record.result for record in records]
    summary = summarize_requests(
        all_results,
        planned=episodes * len(planned_steps),
        start=start,
        end=end,
        expected_output=expected_output,
    )
    active = [finish - begin for begin, finish in spans.values()]
    summary.update(
        {
            "episodes": episodes,
            "planned_steps": list(planned_steps),
            "complete_steps": complete_steps,
            "per_step": per_step,
            "wave_wall_s": end - start,
            "mean_episode_active_s": (sum(active) / len(active)) if active else None,
        }
    )
    return summary


def aa_agreement(arms: Sequence[Sequence[RequestResult]]) -> dict[str, Any]:
    """Token-id digest agreement between two concurrency arms (A/A batch invariance)."""
    if len(arms) != 2:
        raise ValueError("the A/A check compares exactly two arms")
    first = {result.tag: result for result in arms[0] if result.ok}
    second = {result.tag: result for result in arms[1] if result.ok}
    common = sorted(set(first) & set(second))
    basis = "token_ids"
    matches = 0
    for tag in common:
        a, b = first[tag], second[tag]
        if a.token_ids_sha256 is None or b.token_ids_sha256 is None:
            basis = "text"
            same = (
                hashlib.sha256(a.text.encode()).digest() == hashlib.sha256(b.text.encode()).digest()
            )
        else:
            same = a.token_ids_sha256 == b.token_ids_sha256
        matches += int(same)
    return {
        "basis": basis,
        "compared": len(common),
        "agreeing": matches,
        "agreement_rate": (matches / len(common)) if common else None,
        "digests": {
            str(list(tag)): [first[tag].token_ids_sha256, second[tag].token_ids_sha256]
            for tag in common
        },
    }
