from __future__ import annotations

import json

import httpx
import pytest

from harness.memory_trials import (
    GeneratedMemoryTaskSource,
    OpenAICompatibleCompletion,
    OpenAICompatibleConfig,
    ReplayableMemoryWorld,
)


def _config(**updates) -> OpenAICompatibleConfig:
    values = {
        "provider": "kimi",
        "base_url": "http://127.0.0.1:8000/v1",
        "model_id": "kimi-k2.6",
        "api_key_env": "TEST_KIMI_API_KEY",
        "max_completion_tokens": 128,
        "max_tokens_field": "max_completion_tokens",
    }
    values.update(updates)
    return OpenAICompatibleConfig.model_validate(values)


def test_openai_compatible_actor_binds_request_response_and_usage() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer secret-do-not-record"
        if request.url.path.endswith("/models"):
            return httpx.Response(
                200,
                json={"data": [{"id": "kimi-k2.6"}, {"id": "other-model"}]},
            )
        payload = json.loads(request.content)
        assert payload["model"] == "kimi-k2.6"
        assert payload["max_completion_tokens"] == 128
        assert payload["response_format"] == {"type": "json_object"}
        return httpx.Response(
            200,
            json={
                "id": "response-123",
                "created": 123,
                "model": "kimi-k2.6",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": '{"mode":"answer","answer":"UNKNOWN"}'
                        },
                    }
                ],
                "usage": {
                    "prompt_tokens": 50,
                    "completion_tokens": 8,
                    "prompt_tokens_details": {"cached_tokens": 10},
                },
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    backend = OpenAICompatibleCompletion(
        _config(),
        client=client,
        api_key="secret-do-not-record",
    )
    world = ReplayableMemoryWorld(
        GeneratedMemoryTaskSource(seed=7, episode_count=1),
        actor=backend.actor(),
    )
    outcome = world.continue_from(world.prepare("memory-000000"), "holdout", "8" * 64)
    receipt = json.loads(outcome.model_receipt_json)
    assert receipt["requested_model"] == "kimi-k2.6"
    assert receipt["returned_model"] == "kimi-k2.6"
    assert receipt["prompt_tokens"] == 50
    assert receipt["cached_tokens"] == 10
    assert "secret-do-not-record" not in outcome.model_receipt_json
    assert outcome.success is False
    assert backend.preflight()["available"] is True


def test_returned_model_drift_fails_closed() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200,
            json={
                "id": "response-456",
                "model": "kimi-mutated",
                "choices": [{"message": {"content": "{}"}}],
                "usage": {},
            },
        )
    )
    backend = OpenAICompatibleCompletion(
        _config(),
        client=httpx.Client(transport=transport),
        api_key="secret",
    )
    with pytest.raises(ValueError, match="does not match requested"):
        backend.complete("prompt")


def test_remote_endpoint_requires_https_and_latest_aliases_are_rejected() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        _config(base_url="http://api.example.com/v1")
    with pytest.raises(ValueError, match="latest aliases"):
        _config(model_id="kimi-latest")
