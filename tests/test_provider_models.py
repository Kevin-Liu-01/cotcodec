from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from scripts.validate_provider_models import (
    ProviderRegistryError,
    load_provider_registry,
)


def test_live_provider_registry_is_cross_provider_and_valid() -> None:
    payload = load_provider_registry()
    assert len({entry["provider"] for entry in payload["models"].values()}) >= 5
    assert "kimi-k2.6" in payload["models"]
    assert "gpt-5.6-sol" in payload["models"]
    assert payload["models"]["gpt-4o-2024-08-06"] == {
        "provider": "openai",
        "model_id": "gpt-4o-2024-08-06",
        "endpoint": "chat-completions",
        "api_key_env": "OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1",
        "max_tokens_field": "max_tokens",
        "availability": "verify-at-run",
        "version_semantics": "provider-versioned-id",
        "official_url": "https://developers.openai.com/api/docs/models/gpt-4o",
        "pricing_url": "https://openai.com/api/pricing/",
        "pricing_usd_per_million": {
            "input_cache_miss": 2.5,
            "input_cache_hit": 1.25,
            "output": 10.0,
        },
        "role": "longmemeval-official-judge",
    }


def test_latest_alias_is_rejected(tmp_path: Path) -> None:
    payload = copy.deepcopy(load_provider_registry())
    entry = payload["models"].pop("gpt-5.6-sol")
    entry["model_id"] = "gpt-latest"
    payload["models"]["gpt-latest"] = entry
    path = tmp_path / "providers.yaml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(ProviderRegistryError, match="latest aliases"):
        load_provider_registry(path)


def test_self_authored_provider_domain_is_rejected(tmp_path: Path) -> None:
    payload = copy.deepcopy(load_provider_registry())
    payload["models"]["kimi-k2.6"]["official_url"] = "https://example.com/kimi"
    path = tmp_path / "providers.yaml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(ProviderRegistryError, match="official domain"):
        load_provider_registry(path)
