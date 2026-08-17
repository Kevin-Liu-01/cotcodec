"""Provider-specific text completion adapters with credential-free receipts."""

from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field

from harness.memory_trials.models import (
    MEMORY_ACTION_JSON_SCHEMA,
    CompletionResult,
    JsonCompletionMemoryActor,
)


def _json_default(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "__dict__"):
        return {
            name: item
            for name, item in vars(value).items()
            if not name.startswith("_")
        }
    raise TypeError(f"cannot serialize {type(value).__name__}")


def _canonical_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        default=_json_default,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()


def _value(item: Any, name: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


def _response_bytes(response: Any) -> bytes:
    if hasattr(response, "model_dump_json"):
        return response.model_dump_json().encode()
    if isinstance(response, dict):
        return _canonical_bytes(response)
    public = {
        name: value
        for name, value in vars(response).items()
        if not name.startswith("_")
    }
    return _canonical_bytes(public)


def _listed_model_ids(response: Any) -> tuple[str, ...]:
    data = _value(response, "data", [])
    if not isinstance(data, (list, tuple)):
        try:
            data = list(data)
        except TypeError as error:
            raise ValueError("model-list response has no iterable data") from error
    identifiers = {
        identifier
        for item in data
        if isinstance((identifier := _value(item, "id")), str)
    }
    return tuple(sorted(identifiers))


def _model_list_receipt(
    *,
    provider: str,
    endpoint: str,
    requested_model: str,
    model_ids: tuple[str, ...],
) -> dict[str, str | int | bool]:
    available = requested_model in model_ids
    if not available:
        raise ValueError(f"{provider} model list does not contain {requested_model!r}")
    return {
        "provider": provider,
        "endpoint": endpoint,
        "requested_model": requested_model,
        "available": available,
        "listed_model_count": len(model_ids),
        "model_ids_sha256": hashlib.sha256(_canonical_bytes(model_ids)).hexdigest(),
    }


class OpenAIResponsesConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    model_id: str = Field(min_length=2)
    api_key_env: str = Field(default="OPENAI_API_KEY", pattern=r"^[A-Z][A-Z0-9_]*$")
    max_output_tokens: int = Field(default=128, ge=1, le=4096)
    reasoning_effort: str = Field(default="none", pattern=r"^(none|low|medium|high|xhigh|max)$")


class OpenAIResponsesCompletion:
    def __init__(
        self,
        config: OpenAIResponsesConfig,
        *,
        client: Any | None = None,
        api_key: str | None = None,
    ) -> None:
        if "latest" in config.model_id.casefold():
            raise ValueError("mutable latest aliases are forbidden")
        self.config = config
        if client is None:
            secret = api_key or os.environ.get(config.api_key_env)
            if not secret:
                raise ValueError(f"{config.api_key_env} is not set")
            from openai import OpenAI

            client = OpenAI(api_key=secret)
        self._client = client

    @property
    def identity(self) -> str:
        return f"openai:{self.config.model_id}"

    def actor(self) -> JsonCompletionMemoryActor:
        return JsonCompletionMemoryActor(
            identity=self.identity,
            complete=self.complete,
            contract={
                "schema_version": 1,
                "identity": self.identity,
                "provider": "openai-responses",
                "config": self.config.model_dump(mode="json"),
            },
        )

    def preflight(self) -> dict[str, str | int | bool]:
        response = self._client.models.list()
        return _model_list_receipt(
            provider="openai",
            endpoint="/models",
            requested_model=self.config.model_id,
            model_ids=_listed_model_ids(response),
        )

    def complete(self, prompt: str) -> CompletionResult:
        payload = {
            "model": self.config.model_id,
            "input": prompt,
            "max_output_tokens": self.config.max_output_tokens,
            "reasoning": {"effort": self.config.reasoning_effort},
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "memory_action",
                    "strict": True,
                    "schema": MEMORY_ACTION_JSON_SCHEMA,
                }
            },
        }
        started = time.perf_counter()
        response = self._client.responses.create(**payload)
        elapsed_ms = (time.perf_counter() - started) * 1000
        text = _value(response, "output_text")
        returned_model = _value(response, "model")
        if not isinstance(text, str):
            raise ValueError("OpenAI response output_text must be text")
        if returned_model != self.config.model_id:
            raise ValueError("OpenAI returned model does not match the requested model")
        usage = _value(response, "usage", {})
        input_details = _value(usage, "input_tokens_details", {})
        receipt: dict[str, str | int | float | bool | None] = {
            "provider": "openai",
            "endpoint": "/responses",
            "requested_model": self.config.model_id,
            "returned_model": returned_model,
            "response_id": _value(response, "id"),
            "input_tokens": int(_value(usage, "input_tokens", 0)),
            "output_tokens": int(_value(usage, "output_tokens", 0)),
            "cached_tokens": int(_value(input_details, "cached_tokens", 0)),
            "reasoning_effort": self.config.reasoning_effort,
            "elapsed_ms": elapsed_ms,
            "request_sha256": hashlib.sha256(_canonical_bytes(payload)).hexdigest(),
            "response_sha256": hashlib.sha256(_response_bytes(response)).hexdigest(),
        }
        return CompletionResult(text=text, receipt=receipt)


class AnthropicMessagesConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    model_id: str = Field(min_length=2)
    api_key_env: str = Field(default="ANTHROPIC_API_KEY", pattern=r"^[A-Z][A-Z0-9_]*$")
    max_tokens: int = Field(default=128, ge=1, le=4096)


class AnthropicMessagesCompletion:
    def __init__(
        self,
        config: AnthropicMessagesConfig,
        *,
        client: Any | None = None,
        api_key: str | None = None,
    ) -> None:
        if "latest" in config.model_id.casefold():
            raise ValueError("mutable latest aliases are forbidden")
        self.config = config
        if client is None:
            secret = api_key or os.environ.get(config.api_key_env)
            if not secret:
                raise ValueError(f"{config.api_key_env} is not set")
            from anthropic import Anthropic

            client = Anthropic(api_key=secret)
        self._client = client

    @property
    def identity(self) -> str:
        return f"anthropic:{self.config.model_id}"

    def actor(self) -> JsonCompletionMemoryActor:
        return JsonCompletionMemoryActor(
            identity=self.identity,
            complete=self.complete,
            contract={
                "schema_version": 1,
                "identity": self.identity,
                "provider": "anthropic-messages",
                "config": self.config.model_dump(mode="json"),
            },
        )

    def preflight(self) -> dict[str, str | int | bool]:
        response = self._client.models.list(limit=1000)
        return _model_list_receipt(
            provider="anthropic",
            endpoint="/models",
            requested_model=self.config.model_id,
            model_ids=_listed_model_ids(response),
        )

    def complete(self, prompt: str) -> CompletionResult:
        payload = {
            "model": self.config.model_id,
            "max_tokens": self.config.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "output_config": {
                "format": {
                    "type": "json_schema",
                    "schema": MEMORY_ACTION_JSON_SCHEMA,
                }
            },
        }
        started = time.perf_counter()
        response = self._client.messages.create(**payload)
        elapsed_ms = (time.perf_counter() - started) * 1000
        returned_model = _value(response, "model")
        if returned_model != self.config.model_id:
            raise ValueError("Anthropic returned model does not match the requested model")
        blocks = _value(response, "content", [])
        text_parts = [
            _value(block, "text")
            for block in blocks
            if _value(block, "type") == "text" and isinstance(_value(block, "text"), str)
        ]
        if not text_parts:
            raise ValueError("Anthropic response contains no text block")
        usage = _value(response, "usage", {})
        receipt: dict[str, str | int | float | bool | None] = {
            "provider": "anthropic",
            "endpoint": "/messages",
            "requested_model": self.config.model_id,
            "returned_model": returned_model,
            "response_id": _value(response, "id"),
            "stop_reason": _value(response, "stop_reason"),
            "input_tokens": int(_value(usage, "input_tokens", 0)),
            "output_tokens": int(_value(usage, "output_tokens", 0)),
            "cache_read_input_tokens": int(
                _value(usage, "cache_read_input_tokens", 0)
            ),
            "elapsed_ms": elapsed_ms,
            "request_sha256": hashlib.sha256(_canonical_bytes(payload)).hexdigest(),
            "response_sha256": hashlib.sha256(_response_bytes(response)).hexdigest(),
        }
        return CompletionResult(text="".join(text_parts), receipt=receipt)


class GeminiGenerateContentConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    model_id: str = Field(min_length=2)
    api_key_env: str = Field(default="GEMINI_API_KEY", pattern=r"^[A-Z][A-Z0-9_]*$")
    max_output_tokens: int = Field(default=128, ge=1, le=4096)
    timeout_seconds: float = Field(default=120.0, gt=0, le=7200)


class GeminiGenerateContentCompletion:
    def __init__(
        self,
        config: GeminiGenerateContentConfig,
        *,
        client: httpx.Client | None = None,
        api_key: str | None = None,
    ) -> None:
        if "latest" in config.model_id.casefold():
            raise ValueError("mutable latest aliases are forbidden")
        self.config = config
        secret = api_key or os.environ.get(config.api_key_env)
        if not secret:
            raise ValueError(f"{config.api_key_env} is not set")
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=config.timeout_seconds)
        self._api_key = secret

    @property
    def identity(self) -> str:
        return f"google:{self.config.model_id}"

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def actor(self) -> JsonCompletionMemoryActor:
        return JsonCompletionMemoryActor(
            identity=self.identity,
            complete=self.complete,
            contract={
                "schema_version": 1,
                "identity": self.identity,
                "provider": "google-generate-content",
                "config": self.config.model_dump(mode="json"),
            },
        )

    def preflight(self) -> dict[str, str | int | bool]:
        response = self._client.get(
            "https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000",
            headers={"x-goog-api-key": self._api_key},
        )
        response.raise_for_status()
        body = response.json()
        models = body.get("models") if isinstance(body, dict) else None
        if not isinstance(models, list):
            raise ValueError("Gemini model-list response has no models array")
        model_ids = tuple(
            sorted(
                {
                    name.removeprefix("models/")
                    for item in models
                    if isinstance(item, dict)
                    and isinstance((name := item.get("name")), str)
                    and "generateContent" in item.get("supportedGenerationMethods", [])
                }
            )
        )
        return _model_list_receipt(
            provider="google",
            endpoint="/v1beta/models",
            requested_model=self.config.model_id,
            model_ids=model_ids,
        )

    def complete(self, prompt: str) -> CompletionResult:
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": self.config.max_output_tokens,
                "responseMimeType": "application/json",
                "responseJsonSchema": MEMORY_ACTION_JSON_SCHEMA,
                "temperature": 0,
            },
        }
        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.config.model_id}:generateContent"
        )
        started = time.perf_counter()
        response = self._client.post(
            endpoint,
            json=payload,
            headers={"x-goog-api-key": self._api_key},
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.raise_for_status()
        body = response.json()
        candidates = body.get("candidates") if isinstance(body, dict) else None
        if not isinstance(candidates, list) or len(candidates) != 1:
            raise ValueError("Gemini response must contain exactly one candidate")
        candidate = candidates[0]
        content = candidate.get("content") if isinstance(candidate, dict) else None
        parts = content.get("parts") if isinstance(content, dict) else None
        if not isinstance(parts, list):
            raise ValueError("Gemini candidate has no content parts")
        text_parts = [part.get("text") for part in parts if isinstance(part, dict)]
        if not text_parts or not all(isinstance(text, str) for text in text_parts):
            raise ValueError("Gemini response contains non-text output")
        usage = body.get("usageMetadata") if isinstance(body.get("usageMetadata"), dict) else {}
        returned_model = body.get("modelVersion")
        receipt: dict[str, str | int | float | bool | None] = {
            "provider": "google",
            "endpoint": "/v1beta/models/{model}:generateContent",
            "requested_model": self.config.model_id,
            "returned_model": returned_model if isinstance(returned_model, str) else None,
            "finish_reason": candidate.get("finishReason"),
            "input_tokens": int(usage.get("promptTokenCount", 0)),
            "output_tokens": int(usage.get("candidatesTokenCount", 0)),
            "thoughts_tokens": int(usage.get("thoughtsTokenCount", 0)),
            "cached_tokens": int(usage.get("cachedContentTokenCount", 0)),
            "elapsed_ms": elapsed_ms,
            "request_sha256": hashlib.sha256(_canonical_bytes(payload)).hexdigest(),
            "response_sha256": hashlib.sha256(response.content).hexdigest(),
        }
        return CompletionResult(text="".join(text_parts), receipt=receipt)
