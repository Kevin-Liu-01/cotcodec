from __future__ import annotations

import asyncio
import threading
import time

from serving_probe_fakes import IMAGE_TOKENS, WRAPPER_TOKENS, FakeVllm

from harness.serving_probe.client import (
    ChatRequest,
    EpisodePlan,
    RequestResult,
    StopToken,
    aa_agreement,
    build_payload,
    percentile_summary,
    run_aa,
    run_open_loop,
    run_replay,
    stream_chat,
    summarize_replay,
    summarize_requests,
)


def _request(index: int, *, images: int = 0, tokens: int = 8) -> ChatRequest:
    content = [{"type": "text", "text": " ".join(f"w{3 + i}" for i in range(tokens))}]
    content += [{"type": "image_url", "image_url": {"url": "data:image/png;base64,AA"}}] * images
    return ChatRequest(
        [{"role": "user", "content": content}], max_tokens=5, thinking=False, tag=(index,)
    )


def _stop(deadline_s: float = 60.0) -> StopToken:
    return StopToken(deadline=time.perf_counter() + deadline_s, grace_s=0.5)


def test_payload_forces_fixed_length_greedy_streaming() -> None:
    payload = build_payload(_request(0), model="probe-model")
    assert payload["ignore_eos"] is True
    assert payload["min_tokens"] == payload["max_tokens"] == 5
    assert payload["temperature"] == 0.0
    assert payload["stream_options"] == {"include_usage": True}
    assert payload["chat_template_kwargs"] == {"enable_thinking": False}
    assert "return_token_ids" not in payload


def test_stream_chat_reads_usage_and_timing() -> None:
    server = FakeVllm()

    async def go() -> RequestResult:
        async with server.async_client() as client:
            return await stream_chat(client, _request(3, images=1), model="m", timeout_s=10)

    result = asyncio.run(go())
    assert result.ok and result.tag == (3,)
    assert result.prompt_tokens == 9 + IMAGE_TOKENS + WRAPPER_TOKENS
    assert result.completion_tokens == 5
    assert result.ttft_s is not None and result.e2el_s >= result.ttft_s
    assert len(result.itl_s) == 4
    assert result.text.startswith(" t0")


def test_http_errors_become_failed_results() -> None:
    server = FakeVllm(fail_every=1)

    async def go() -> RequestResult:
        async with server.async_client() as client:
            return await stream_chat(client, _request(0), model="m", timeout_s=10)

    result = asyncio.run(go())
    assert not result.ok and "400" in result.error


def test_open_loop_respects_concurrency_and_counts_everything() -> None:
    server = FakeVllm(latency_s=0.02)
    requests = [_request(i) for i in range(12)]

    async def go():
        async with server.async_client() as client:
            return await run_open_loop(
                client, requests, concurrency=3, model="m", timeout_s=10, stop=_stop()
            )

    results, start, end, unlaunched = asyncio.run(go())
    assert unlaunched == 0 and len(results) == 12
    assert server.max_in_flight == 3
    summary = summarize_requests(results, planned=12, start=start, end=end, expected_output=5)
    assert summary["completed"] == 12 and summary["failed"] == 0
    assert summary["output_tokens"] == 60 == server.generation_tokens
    assert summary["prompt_tokens"] == server.prompt_tokens
    assert summary["short_outputs"] == 0
    assert summary["request_throughput"] > 0
    assert summary["e2el_ms"]["p50"] >= 20


def test_open_loop_stops_launching_after_the_external_stop() -> None:
    event = threading.Event()

    def trip(server: FakeVllm) -> None:
        if server.requests == 2:
            event.set()

    server = FakeVllm(latency_s=0.01, on_request=trip)
    stop = StopToken(deadline=None, external=event, grace_s=1.0)

    async def go():
        async with server.async_client() as client:
            return await run_open_loop(
                client,
                [_request(i) for i in range(10)],
                concurrency=1,
                model="m",
                timeout_s=10,
                stop=stop,
            )

    results, _start, _end, unlaunched = asyncio.run(go())
    assert len(results) == 2 and unlaunched == 8
    assert stop.reason() == "signal"


def test_replay_feeds_responses_back_and_waits_between_steps() -> None:
    server = FakeVllm()

    def build(step: int, responses: list[str]) -> list[dict]:
        history = [
            {"role": "assistant", "content": [{"type": "text", "text": r}]} for r in responses
        ]
        user = {"role": "user", "content": [{"type": "text", "text": f"w{10 + step}"}]}
        return [*history, user]

    plans = [
        EpisodePlan(
            episode=e,
            start_offset_s=0.01 * e,
            steps=[3, 4, 5],
            prebuilt_responses=["w4 w5"] * 2,
            build=build,
            output_tokens=5,
            thinking=False,
            t_env_s=0.01,
        )
        for e in range(3)
    ]

    async def go():
        async with server.async_client() as client:
            return await run_replay(client, plans, model="m", timeout_s=10, stop=_stop())

    records, start, end, spans = asyncio.run(go())
    assert len(records) == 9
    last_body = [b for b in server.bodies if len(b["messages"]) == 5]
    assert last_body and last_body[0]["messages"][2]["content"][0]["text"].startswith(" t0")
    summary = summarize_replay(
        records,
        episodes=3,
        planned_steps=[3, 4, 5],
        start=start,
        end=end,
        spans=spans,
        expected_output=5,
    )
    assert summary["complete_steps"] == [3, 4, 5]
    assert summary["per_step"]["3"]["completed"] == 3
    assert summary["per_step"]["5"]["latency_s"]["mean"] > 0
    assert summary["planned"] == 9 and summary["failed"] == 0
    assert summary["mean_episode_active_s"] >= 0.02


def test_replay_stops_an_episode_after_a_failed_step() -> None:
    server = FakeVllm(fail_every=2)
    plan = EpisodePlan(
        0, 0.0, [1, 2, 3], [], lambda s, r: [{"role": "user", "content": []}], 5, False, 0.0
    )

    async def go():
        async with server.async_client() as client:
            return await run_replay(client, [plan], model="m", timeout_s=10, stop=_stop())

    records, start, end, spans = asyncio.run(go())
    assert [r.result.ok for r in records] == [True, False]
    summary = summarize_replay(
        records,
        episodes=1,
        planned_steps=[1, 2, 3],
        start=start,
        end=end,
        spans=spans,
        expected_output=5,
    )
    assert summary["complete_steps"] == [1]
    assert summary["failed"] == 2


def test_aa_resets_between_arms_and_compares_token_digests() -> None:
    server = FakeVllm()
    resets = []

    async def go():
        async def between() -> None:
            resets.append(1)

        async with server.async_client() as client:
            return await run_aa(
                client,
                [_request(i) for i in range(4)],
                arms=[1, 4],
                model="m",
                timeout_s=10,
                stop=_stop(),
                between_arms=between,
            )

    arms = asyncio.run(go())
    assert resets == [1]
    assert all(body.get("return_token_ids") for body in server.bodies)
    agreement = aa_agreement(arms)
    assert agreement == {
        **agreement,
        "basis": "token_ids",
        "compared": 4,
        "agreeing": 4,
        "agreement_rate": 1.0,
    }
    arms[1][0].token_ids_sha256 = "0" * 64
    assert aa_agreement(arms)["agreeing"] == 3


def test_percentiles_are_linear_and_scaled() -> None:
    summary = percentile_summary([1.0, 2.0, 3.0, 4.0])
    assert summary["mean"] == 2500.0
    assert summary["p50"] == 2500.0
    assert abs(summary["p90"] - 3700.0) < 1e-9
    assert percentile_summary([]) == {"mean": None, "p50": None, "p90": None, "p99": None}


def test_stop_token_sleep_returns_early() -> None:
    event = threading.Event()
    token = StopToken(deadline=None, external=event)
    event.set()
    assert asyncio.run(token.sleep(5.0)) is False
    assert asyncio.run(StopToken(deadline=None).sleep(0.01)) is True
