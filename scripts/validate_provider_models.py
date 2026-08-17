#!/usr/bin/env python3
"""Validate the current hosted-model roster without treating aliases as snapshots."""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = PROJECT_ROOT / "models" / "provider-registry.yaml"
MODEL_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ENV_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
VERSION_SEMANTICS = {
    "pinned-model-id",
    "provider-versioned-id",
    "stable-model-id",
    "mutable-service-id",
}
PROVIDER_DOMAINS = {
    "openai": "openai.com",
    "anthropic": "claude.com",
    "google": "google.dev",
    "deepseek": "deepseek.com",
    "moonshot": "kimi.ai",
}


class ProviderRegistryError(ValueError):
    """Raised when a hosted-model roster is not auditable."""


def load_provider_registry(path: Path = DEFAULT_REGISTRY) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ProviderRegistryError("provider registry must be a schema_version: 1 mapping")
    if not isinstance(payload.get("verified_at"), str) or not DATE_RE.fullmatch(
        payload["verified_at"]
    ):
        raise ProviderRegistryError("verified_at must be an ISO date")
    models = payload.get("models")
    if not isinstance(models, dict) or not models:
        raise ProviderRegistryError("provider registry must contain models")

    providers: set[str] = set()
    for key, entry in models.items():
        if not isinstance(entry, dict):
            raise ProviderRegistryError(f"{key}: entry must be a mapping")
        model_id = entry.get("model_id")
        if key != model_id or not isinstance(model_id, str) or not MODEL_ID_RE.fullmatch(model_id):
            raise ProviderRegistryError(f"{key}: key and model_id must match exactly")
        if "latest" in model_id.lower():
            raise ProviderRegistryError(f"{key}: mutable latest aliases are forbidden")
        provider = entry.get("provider")
        if provider not in PROVIDER_DOMAINS:
            raise ProviderRegistryError(f"{key}: unsupported provider {provider!r}")
        providers.add(provider)
        if entry.get("version_semantics") not in VERSION_SEMANTICS:
            raise ProviderRegistryError(f"{key}: invalid version_semantics")
        for field in ("endpoint", "availability", "role"):
            if not isinstance(entry.get(field), str) or not entry[field].strip():
                raise ProviderRegistryError(f"{key}: {field} must be nonempty")
        api_key_env = entry.get("api_key_env")
        if not isinstance(api_key_env, str) or not ENV_RE.fullmatch(api_key_env):
            raise ProviderRegistryError(f"{key}: api_key_env must name an environment variable")
        if entry["endpoint"] == "chat-completions":
            base_url = entry.get("base_url")
            base = urlparse(base_url) if isinstance(base_url, str) else None
            if base is None or base.scheme != "https" or not base.hostname:
                raise ProviderRegistryError(f"{key}: chat-completions requires HTTPS base_url")
            if entry.get("max_tokens_field") not in {
                "max_tokens",
                "max_completion_tokens",
            }:
                raise ProviderRegistryError(f"{key}: invalid max_tokens_field")
        official_url = entry.get("official_url")
        parsed = urlparse(official_url) if isinstance(official_url, str) else None
        expected_domain = PROVIDER_DOMAINS[provider]
        if (
            parsed is None
            or parsed.scheme != "https"
            or parsed.hostname is None
            or not parsed.hostname.endswith(expected_domain)
        ):
            raise ProviderRegistryError(
                f"{key}: official_url must use the provider's official domain"
            )
        pricing_url = entry.get("pricing_url")
        price_page = urlparse(pricing_url) if isinstance(pricing_url, str) else None
        if (
            price_page is None
            or price_page.scheme != "https"
            or price_page.hostname is None
            or not price_page.hostname.endswith(expected_domain)
        ):
            raise ProviderRegistryError(
                f"{key}: pricing_url must use the provider's official domain"
            )
        pricing = entry.get("pricing_usd_per_million")
        if not isinstance(pricing, dict) or set(pricing) != {
            "input_cache_miss",
            "input_cache_hit",
            "output",
        }:
            raise ProviderRegistryError(f"{key}: pricing fields are incomplete")
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or float(value) < 0
            for value in pricing.values()
        ):
            raise ProviderRegistryError(f"{key}: pricing must be finite and nonnegative")

    if len(providers) < 5:
        raise ProviderRegistryError("frontier transport requires at least five providers")
    runtime = payload.get("runtime_verification")
    if not isinstance(runtime, dict) or not runtime or not all(
        value is True for value in runtime.values()
    ):
        raise ProviderRegistryError("every runtime verification control must be enabled")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    args = parser.parse_args()
    payload = load_provider_registry(args.registry)
    providers = {entry["provider"] for entry in payload["models"].values()}
    print(
        f"provider model registry PASS: {len(payload['models'])} models, "
        f"{len(providers)} providers"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
