"""Streaming client for v2: prompt-token-id digests and fixed (prebuilt) replay history.

Every v2 request sets ``return_token_ids``. vLLM v0.31.0 then sends the
prompt's token ids in the first streamed chunk (``prompt_token_ids``,
``vllm/entrypoints/openai/chat_completion/serving.py`` at tag v0.31.0), and the
client keeps only their SHA-256 and count, so two points can be shown to have
sent identical token sequences request by request. Generated text is never
kept: v2 replays build every step from prebuilt history, so a step's prompt is
the same whatever the engine generated (real or dummy weights).

Timing, token accounting and summaries are v1's (``harness.serving_probe.client``).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import httpx
import numpy as np

from harness.serving_probe.client import (
    ChatRequest,
    EpisodePlan,
    RequestResult,
    StepRecord,
    StopToken,
    _with_stop,
    build_payload,
)


@dataclass
class IdentifiedResult(RequestResult):
    """v1's request result plus the digest of the prompt token ids the server reported."""

    prompt_ids_sha256: str | None = None
    prompt_id_count: int = 0


def token_ids_sha256(ids: Sequence[int]) -> str:
    """SHA-256 of the ids as little-endian int64 (independent of JSON formatting)."""
    return hashlib.sha256(np.asarray(list(ids), dtype="<i8").tobytes()).hexdigest()


def build_payload_v2(request: ChatRequest, *, model: str) -> dict[str, Any]:
    """v1's fixed-length payload with token ids returned on every request."""
    return {**build_payload(request, model=model), "return_token_ids": True}


async def stream_chat_identified(
    client: httpx.AsyncClient,
    request: ChatRequest,
    *,
    model: str,
    timeout_s: float,
    clock: Callable[[], float] = time.perf_counter,
) -> IdentifiedResult:
    """Send one streaming chat completion, time it and digest its prompt token ids."""
    payload = build_payload_v2(request, model=model)
    sent = clock()
    first: float | None = None
    last_token_at: float | None = None
    itl: list[float] = []
    prompt_ids: list[int] | None = None
    usage: dict[str, Any] = {}
    try:
        async with client.stream(
            "POST", "/v1/chat/completions", json=payload, timeout=timeout_s
        ) as response:
            if response.status_code != 200:
                body = (await response.aread()).decode("utf-8", "replace")[:300]
                return IdentifiedResult(
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
                if prompt_ids is None and chunk.get("prompt_token_ids") is not None:
                    prompt_ids = [int(token) for token in chunk["prompt_token_ids"]]
                produced = False
                for choice in chunk.get("choices") or []:
                    delta = choice.get("delta") or {}
                    piece = (delta.get("content") or "") + (
                        delta.get("reasoning_content") or delta.get("reasoning") or ""
                    )
                    ids = choice.get("token_ids") or delta.get("token_ids") or []
                    produced = produced or bool(piece) or bool(ids)
                if produced:
                    now = clock()
                    if first is None:
                        first = now
                    elif last_token_at is not None:
                        itl.append(now - last_token_at)
                    last_token_at = now
    except (TimeoutError, httpx.HTTPError, json.JSONDecodeError, ValueError) as exc:
        return IdentifiedResult(
            request.tag, False, f"{type(exc).__name__}: {exc}"[:300], sent, clock()
        )
    finished = clock()
    if not usage:
        return IdentifiedResult(request.tag, False, "stream ended without usage", sent, finished)
    return IdentifiedResult(
        tag=request.tag,
        ok=True,
        error=None,
        sent_at=sent,
        finished_at=finished,
        first_token_at=first,
        prompt_tokens=int(usage.get("prompt_tokens", 0)),
        completion_tokens=int(usage.get("completion_tokens", 0)),
        itl_s=itl,
        prompt_ids_sha256=None if prompt_ids is None else token_ids_sha256(prompt_ids),
        prompt_id_count=0 if prompt_ids is None else len(prompt_ids),
    )


async def run_open_loop(
    client: httpx.AsyncClient,
    requests: Sequence[ChatRequest],
    *,
    concurrency: int,
    model: str,
    timeout_s: float,
    stop: StopToken,
) -> tuple[list[IdentifiedResult], float, float, int]:
    """v1's open loop (at most ``concurrency`` in flight) with identified results."""
    semaphore = asyncio.Semaphore(concurrency)
    results: list[IdentifiedResult] = []
    skipped = 0

    async def one(request: ChatRequest) -> None:
        nonlocal skipped
        async with semaphore:
            if stop.triggered():
                skipped += 1
                return
            results.append(
                await stream_chat_identified(
                    client, request, model=model, timeout_s=timeout_s, clock=stop.clock
                )
            )

    start = stop.clock()
    tasks = [asyncio.create_task(one(request)) for request in requests]
    await _with_stop(tasks, stop)
    end = stop.clock()
    cancelled = sum(1 for task in tasks if task.cancelled())
    return results, start, end, skipped + cancelled


async def run_fixed_replay(
    client: httpx.AsyncClient,
    episodes: Sequence[EpisodePlan],
    *,
    model: str,
    timeout_s: float,
    stop: StopToken,
) -> tuple[list[StepRecord], float, float, dict[int, tuple[float, float]]]:
    """Closed-loop replay whose history is the plan's prebuilt responses, never generated text.

    Each episode waits ``t_env_s`` between its steps, as in v1; ``plan.build`` is
    called with the prebuilt responses only.
    """
    records: list[StepRecord] = []
    spans: dict[int, tuple[float, float]] = {}

    async def episode_task(plan: EpisodePlan) -> None:
        if plan.start_offset_s > 0 and not await stop.sleep(plan.start_offset_s):
            return
        began = stop.clock()
        history = list(plan.prebuilt_responses)
        for index, step in enumerate(plan.steps):
            if stop.triggered():
                break
            request = ChatRequest(
                messages=plan.build(step, history),
                max_tokens=plan.output_tokens,
                thinking=plan.thinking,
                tag=(plan.episode, step),
            )
            result = await stream_chat_identified(
                client, request, model=model, timeout_s=timeout_s, clock=stop.clock
            )
            records.append(StepRecord(plan.episode, step, result))
            spans[plan.episode] = (began, stop.clock())
            if not result.ok:
                break
            if index < len(plan.steps) - 1 and not await stop.sleep(plan.t_env_s):
                break

    start = stop.clock()
    tasks = [asyncio.create_task(episode_task(plan)) for plan in episodes]
    await _with_stop(tasks, stop)
    return records, start, stop.clock(), spans


def request_key(tag: Sequence[int]) -> str:
    return ":".join(str(int(part)) for part in tag)


def request_identity(results: Sequence[RequestResult]) -> dict[str, Any]:
    """Per completed request: prompt-token-id SHA-256 (or None) and prompt tokens.

    ``basis`` is ``prompt-token-ids`` when the server returned the ids for every
    completed request, else ``prompt-token-count``.
    """
    ok = [result for result in results if result.ok]
    entries = {
        request_key(result.tag): [
            getattr(result, "prompt_ids_sha256", None),
            int(result.prompt_tokens),
        ]
        for result in ok
    }
    every_id = bool(ok) and all(entry[0] is not None for entry in entries.values())
    return {
        "basis": "prompt-token-ids" if every_id else "prompt-token-count",
        "requests": entries,
    }


def compare_identity(
    reference: Mapping[str, Any] | None, control: Mapping[str, Any] | None
) -> dict[str, Any]:
    """Whether two points sent identical prompt token sequences, request by request."""
    if not reference or not control:
        return {"identical": False, "reason": "a point has no request identity record"}
    first, second = reference.get("requests") or {}, control.get("requests") or {}
    if set(first) != set(second) or not first:
        missing = sorted(set(first) ^ set(second))[:5]
        return {"identical": False, "reason": f"request sets differ (e.g. {missing})"}
    by_ids = all(first[key][0] is not None and second[key][0] is not None for key in first)
    differing = [
        key
        for key in sorted(first)
        if first[key][1] != second[key][1] or (by_ids and first[key][0] != second[key][0])
    ]
    return {
        "identical": not differing,
        "basis": "prompt-token-ids" if by_ids else "prompt-token-count",
        "requests": len(first),
        "differing": differing[:10],
        "reason": None if not differing else f"{len(differing)} requests differ",
    }
