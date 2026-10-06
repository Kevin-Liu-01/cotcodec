from __future__ import annotations

import json
from types import SimpleNamespace

import httpx

from harness.memory_trials import (
    AnthropicMessagesCompletion,
    AnthropicMessagesConfig,
    GeminiGenerateContentCompletion,
    GeminiGenerateContentConfig,
    OpenAIResponsesCompletion,
    OpenAIResponsesConfig,
)


class FakeOpenAI:
    def __init__(self) -> None:
        self.responses = self
        self.models = self
        self.payload = None

    def list(self):
        return SimpleNamespace(data=[SimpleNamespace(id="gpt-5.6-sol")])

    def create(self, **payload):
        self.payload = payload
        return SimpleNamespace(
            id="resp-openai",
            model="gpt-5.6-sol",
            output_text='{"mode":"answer","answer":"UNKNOWN"}',
            usage=SimpleNamespace(
                input_tokens=20,
                output_tokens=5,
                input_tokens_details=SimpleNamespace(cached_tokens=3),
            ),
        )


class FakeAnthropic:
    def __init__(self) -> None:
        self.messages = self
        self.models = self
        self.payload = None

    def list(self, *, limit):
        assert limit == 1000
        return SimpleNamespace(data=[SimpleNamespace(id="claude-opus-5")])

    def create(self, **payload):
        self.payload = payload
        return SimpleNamespace(
            id="resp-anthropic",
            model="claude-opus-5",
            content=[
                SimpleNamespace(
                    type="text",
                    text='{"mode":"answer","answer":"UNKNOWN"}',
                )
            ],
            stop_reason="end_turn",
            usage=SimpleNamespace(
                input_tokens=21,
                output_tokens=6,
                cache_read_input_tokens=4,
            ),
        )


def test_openai_responses_receipt_binds_model_and_reasoning_mode() -> None:
    client = FakeOpenAI()
    backend = OpenAIResponsesCompletion(
        OpenAIResponsesConfig(model_id="gpt-5.6-sol"),
        client=client,
    )
    result = backend.complete("prompt")
    assert result.receipt["requested_model"] == "gpt-5.6-sol"
    assert result.receipt["returned_model"] == "gpt-5.6-sol"
    assert result.receipt["cached_tokens"] == 3
    assert client.payload["reasoning"] == {"effort": "none"}
    assert client.payload["text"]["format"]["strict"] is True
    assert backend.preflight()["available"] is True


def test_anthropic_messages_receipt_binds_pinned_model() -> None:
    client = FakeAnthropic()
    backend = AnthropicMessagesCompletion(
        AnthropicMessagesConfig(model_id="claude-opus-5"),
        client=client,
    )
    result = backend.complete("prompt")
    assert result.receipt["requested_model"] == "claude-opus-5"
    assert result.receipt["cache_read_input_tokens"] == 4
    assert client.payload["max_tokens"] == 128
    assert client.payload["output_config"]["format"]["type"] == "json_schema"
    assert backend.preflight()["available"] is True


def test_gemini_rest_receipt_uses_header_secret_and_records_model_version() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-goog-api-key"] == "gemini-secret"
        assert "gemini-secret" not in str(request.url)
        if request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {
                            "name": "models/gemini-3.5-flash",
                            "supportedGenerationMethods": ["generateContent"],
                        }
                    ]
                },
            )
        payload = json.loads(request.content)
        assert payload["generationConfig"]["responseJsonSchema"]["additionalProperties"] is False
        return httpx.Response(
            200,
            json={
                "modelVersion": "gemini-3.5-flash-001",
                "candidates": [
                    {
                        "finishReason": "STOP",
                        "content": {
                            "parts": [
                                {"text": '{"mode":"answer","answer":"UNKNOWN"}'}
                            ]
                        },
                    }
                ],
                "usageMetadata": {
                    "promptTokenCount": 22,
                    "candidatesTokenCount": 7,
                    "thoughtsTokenCount": 2,
                    "cachedContentTokenCount": 5,
                },
            },
        )

    backend = GeminiGenerateContentCompletion(
        GeminiGenerateContentConfig(model_id="gemini-3.5-flash"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        api_key="gemini-secret",
    )
    result = backend.complete("prompt")
    assert result.receipt["returned_model"] == "gemini-3.5-flash-001"
    assert result.receipt["thoughts_tokens"] == 2
    assert "gemini-secret" not in str(result.receipt)
    assert backend.preflight()["available"] is True
