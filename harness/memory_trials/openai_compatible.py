"""OpenAI-compatible completion adapter for vLLM, SGLang, Kimi, and DeepSeek."""

from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any, Literal
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator

from harness.memory_trials.models import CompletionResult, JsonCompletionMemoryActor


class OpenAICompatibleConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    base_url: str
    model_id: str = Field(min_length=2)
    api_key_env: str = Field(pattern=r"^[A-Z][A-Z0-9_]*$")
    max_completion_tokens: int = Field(default=128, ge=1, le=4096)
    timeout_seconds: float = Field(default=120.0, gt=0, le=7200)
    max_tokens_field: Literal["max_tokens", "max_completion_tokens"] = "max_tokens"
    json_mode: bool = True
    require_returned_model_match: bool = True

    @model_validator(mode="after")
    def safe_endpoint(self) -> OpenAICompatibleConfig:
        parsed = urlparse(self.base_url)
        local = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        if parsed.scheme not in ({"http", "https"} if local else {"https"}):
            raise ValueError("remote completion endpoints must use HTTPS")
        if not parsed.hostname or parsed.query or parsed.fragment or parsed.username:
            raise ValueError("base_url must be a credential-free HTTP origin/path")
        if "latest" in self.model_id.casefold():
            raise ValueError("mutable latest aliases are forbidden")
        return self


def _canonical_bytes(payload: Any) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()


class OpenAICompatibleCompletion:
    """Capture exact request/response provenance while keeping credentials out."""

    def __init__(
        self,
        config: OpenAICompatibleConfig,
        *,
        client: httpx.Client | None = None,
        api_key: str | None = None,
    ) -> None:
        self.config = config
        secret = api_key or os.environ.get(config.api_key_env)
        if not secret:
            raise ValueError(f"{config.api_key_env} is not set")
        self._owns_client = client is None
        self._client = client or httpx.Client(
            timeout=config.timeout_seconds,
            headers={"Authorization": f"Bearer {secret}"},
        )
        self._authorization = f"Bearer {secret}"

    @property
    def identity(self) -> str:
        return f"{self.config.provider}:{self.config.model_id}"

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
                "provider": self.config.provider,
                "config": self.config.model_dump(mode="json"),
            },
        )

    def preflight(self) -> dict[str, str | int | bool]:
        endpoint = self.config.base_url.rstrip("/") + "/models"
        response = self._client.get(
            endpoint,
            headers={"Authorization": self._authorization},
        )
        response.raise_for_status()
        body = response.json()
        data = body.get("data") if isinstance(body, dict) else None
        if not isinstance(data, list):
            raise ValueError("model-list response has no data array")
        model_ids = tuple(
            sorted(
                {
                    model_id
                    for item in data
                    if isinstance(item, dict)
                    and isinstance((model_id := item.get("id")), str)
                }
            )
        )
        if self.config.model_id not in model_ids:
            raise ValueError(
                f"{self.config.provider} model list does not contain "
                f"{self.config.model_id!r}"
            )
        return {
            "provider": self.config.provider,
            "endpoint": "/models",
            "requested_model": self.config.model_id,
            "available": True,
            "listed_model_count": len(model_ids),
            "model_ids_sha256": hashlib.sha256(_canonical_bytes(model_ids)).hexdigest(),
        }

    def complete(self, prompt: str) -> CompletionResult:
        payload: dict[str, Any] = {
            "model": self.config.model_id,
            "messages": [{"role": "user", "content": prompt}],
            self.config.max_tokens_field: self.config.max_completion_tokens,
            "stream": False,
        }
        if self.config.json_mode:
            payload["response_format"] = {"type": "json_object"}
        request_bytes = _canonical_bytes(payload)
        endpoint = self.config.base_url.rstrip("/") + "/chat/completions"
        started = time.perf_counter()
        response = self._client.post(
            endpoint,
            json=payload,
            headers={"Authorization": self._authorization},
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.raise_for_status()
        response_bytes = response.content
        body = response.json()
        if not isinstance(body, dict):
            raise ValueError("completion response must be an object")
        choices = body.get("choices")
        if not isinstance(choices, list) or len(choices) != 1:
            raise ValueError("completion response must contain exactly one choice")
        choice = choices[0]
        message = choice.get("message") if isinstance(choice, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str):
            raise ValueError("completion response content must be text")
        returned_model = body.get("model")
        if not isinstance(returned_model, str):
            raise ValueError("completion response must identify the returned model")
        if (
            self.config.require_returned_model_match
            and returned_model != self.config.model_id
        ):
            raise ValueError(
                f"returned model {returned_model!r} does not match "
                f"requested {self.config.model_id!r}"
            )
        usage = body.get("usage") if isinstance(body.get("usage"), dict) else {}
        prompt_details = (
            usage.get("prompt_tokens_details")
            if isinstance(usage.get("prompt_tokens_details"), dict)
            else {}
        )
        receipt: dict[str, str | int | float | bool | None] = {
            "provider": self.config.provider,
            "endpoint": "/chat/completions",
            "requested_model": self.config.model_id,
            "returned_model": returned_model,
            "response_id": body.get("id") if isinstance(body.get("id"), str) else None,
            "created": body.get("created") if isinstance(body.get("created"), int) else None,
            "finish_reason": (
                choice.get("finish_reason")
                if isinstance(choice, dict) and isinstance(choice.get("finish_reason"), str)
                else None
            ),
            "prompt_tokens": int(usage.get("prompt_tokens", 0)),
            "completion_tokens": int(usage.get("completion_tokens", 0)),
            "cached_tokens": int(prompt_details.get("cached_tokens", 0)),
            "elapsed_ms": elapsed_ms,
            "request_sha256": hashlib.sha256(request_bytes).hexdigest(),
            "response_sha256": hashlib.sha256(response_bytes).hexdigest(),
        }
        return CompletionResult(text=content, receipt=receipt)
