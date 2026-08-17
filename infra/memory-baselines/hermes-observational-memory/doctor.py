#!/usr/bin/env python3
"""Contained lifecycle probe for the standalone Hermes OM provider."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import shutil
import stat
from pathlib import Path
from typing import Any

PROVIDER = "observational_memory"
TOOLS = ["om_context", "om_search", "om_remember"]
PLUGIN_SOURCE = Path("/opt/hermes-observational-memory")
STATE_ROOT = Path("/state")
SECRET_NAMES = {
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "OM_HERMES_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
}


class DoctorError(RuntimeError):
    """Fail-closed doctor error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_manifest(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not root.exists():
        return rows
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise DoctorError(f"symlink forbidden in state: {relative}")
        if stat.S_ISDIR(info.st_mode):
            rows.append({"path": relative + "/", "type": "directory"})
        elif stat.S_ISREG(info.st_mode):
            rows.append(
                {
                    "path": relative,
                    "type": "file",
                    "bytes": info.st_size,
                    "sha256": _sha256(path),
                }
            )
        else:
            raise DoctorError(f"special file forbidden in state: {relative}")
    return rows


def _manifest_root(rows: list[dict[str, Any]]) -> str:
    encoded = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _copy_or_verify_plugin(hermes_home: Path) -> str:
    target = hermes_home / "plugins" / PROVIDER
    source_rows = _tree_manifest(PLUGIN_SOURCE)
    source_root = _manifest_root(source_rows)
    if target.exists():
        if _manifest_root(_tree_manifest(target)) != source_root:
            raise DoctorError("installed standalone plugin drifted")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(PLUGIN_SOURCE, target)
        if _manifest_root(_tree_manifest(target)) != source_root:
            raise DoctorError("standalone plugin copy mismatch")
    return source_root


def _write_config(hermes_home: Path, memory_root: Path) -> str:
    payload = {
        "llm_provider": "inherit-existing",
        "llm_model": "",
        "usage_tracking": True,
        "budget_mode": "hard",
        "budget_soft_threshold": 0.8,
        "openai_async_mode": "off",
        "memory_dir": str(memory_root),
        "env_file": str(STATE_ROOT / "config" / "om.env"),
        "search_backend": "bm25",
        "writeback_mode": "off",
    }
    path = hermes_home / "observational_memory.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if path.exists() and path.read_text() != encoded:
        raise DoctorError("provider config drifted across restart")
    path.write_text(encoded)
    return hashlib.sha256(encoded.encode()).hexdigest()


def _contains_canary(results: Any, canary: str) -> bool:
    for item in results or []:
        document = getattr(item, "document", None)
        content = str(getattr(document, "content", "") or "")
        heading = str(getattr(document, "heading", "") or "")
        if canary in content or canary in heading:
            return True
    return False


def _context_recall_contains(text: str, canary: str) -> bool:
    """Check retrieved context without counting OM's deterministic query echo."""

    _prefix, marker, recalled = text.partition("## Relevant Memory")
    return bool(marker) and canary in recalled


def _load_provider(hermes_home: Path, memory_root: Path):
    if any(os.environ.get(name) for name in SECRET_NAMES):
        raise DoctorError("API credential unexpectedly present")
    os.environ["HERMES_HOME"] = str(hermes_home)
    os.environ["HOME"] = str(STATE_ROOT / "home")
    os.environ["XDG_DATA_HOME"] = str(STATE_ROOT / "xdg-data")
    os.environ["XDG_CONFIG_HOME"] = str(STATE_ROOT / "xdg-config")
    os.environ["OM_CLUSTER_ENABLED"] = "0"
    os.environ["OM_SEARCH_BACKEND"] = "bm25"
    for directory in (Path(os.environ["HOME"]), memory_root, STATE_ROOT / "config"):
        directory.mkdir(parents=True, exist_ok=True)

    plugin_root = _copy_or_verify_plugin(hermes_home)
    config_sha = _write_config(hermes_home, memory_root)

    from plugins.memory import (
        discover_memory_providers,
        list_memory_provider_names,
        load_memory_provider,
    )

    names = list_memory_provider_names()
    if PROVIDER not in names:
        raise DoctorError("standalone provider missing from Hermes name scan")
    discovered = discover_memory_providers()
    row = next((item for item in discovered if item[0] == PROVIDER), None)
    if row is None or row[2] is not True:
        raise DoctorError(f"standalone provider unavailable: {row!r}")
    provider = load_memory_provider(PROVIDER, register_skills=False)
    if provider is None or provider.name != PROVIDER or not provider.is_available():
        raise DoctorError("Hermes failed to load standalone provider")
    provider.initialize(
        "cotcodec-hermes-om",
        hermes_home=str(hermes_home),
        platform="contained-doctor",
        agent_context="primary",
    )
    tool_names = [schema.get("name") for schema in provider.get_tool_schemas()]
    if tool_names != TOOLS:
        raise DoctorError(f"tool roster drifted: {tool_names!r}")
    return provider, discovered, plugin_root, config_sha


def _direct_search(provider, query: str, *, allow_empty: bool = False):
    from observational_memory.search import get_backend, reindex

    backend = get_backend(provider._config.search_backend, provider._config)
    if not backend.is_ready():
        document_count = reindex(provider._config)
        backend = get_backend(provider._config.search_backend, provider._config)
    if not backend.is_ready():
        if allow_empty and document_count == 0:
            return []
        raise DoctorError("BM25 backend is not ready")
    return backend.search(query, limit=10)


def _budget_probe(provider) -> dict[str, Any]:
    from observational_memory import llm
    from observational_memory.usage.budgets import BudgetExceededError

    os.environ["OM_BUDGET_DAILY_TOKENS"] = "1"
    os.environ["OM_BUDGET_MODE"] = "hard"
    os.environ.pop("OM_BUDGET_BYPASS", None)
    try:
        try:
            llm._enforce_budget(
                provider._config,
                "observer",
                "openai",
                "gpt-4o-mini",
                "bounded pre-call budget probe " * 32,
                "no provider dispatch is permitted " * 32,
                4096,
            )
        except BudgetExceededError as exc:
            return {"blocked": True, "error_type": type(exc).__name__}
        raise DoctorError("hard budget did not block before provider dispatch")
    finally:
        os.environ.pop("OM_BUDGET_DAILY_TOKENS", None)
        os.environ.pop("OM_BUDGET_MODE", None)


def run_phase(phase: str, canary: str) -> dict[str, Any]:
    hermes_home = STATE_ROOT / "hermes"
    memory_root = STATE_ROOT / "memory"
    provider, discovered, plugin_root, config_sha = _load_provider(
        hermes_home, memory_root
    )
    try:
        prompt_before = provider.system_prompt_block()
        direct_before = _direct_search(
            provider,
            canary,
            allow_empty=phase in {"prepare", "isolated"},
        )
        search_before = json.loads(
            provider.handle_tool_call("om_search", {"query": canary, "limit": 10})
        )
        before_contains = canary in json.dumps(search_before, sort_keys=True)

        remember: dict[str, Any] | None = None
        if phase == "prepare":
            if before_contains or _contains_canary(direct_before, canary):
                raise DoctorError("fresh state already contains canary")
            remember = json.loads(
                provider.handle_tool_call(
                    "om_remember", {"content": canary, "importance": "high"}
                )
            )
            if remember.get("stored") is not True:
                raise DoctorError(f"explicit remember failed: {remember!r}")
        elif phase not in {"restart", "isolated"}:
            raise DoctorError(f"unsupported phase: {phase}")

        direct_after = _direct_search(
            provider,
            canary,
            allow_empty=phase == "isolated",
        )
        search_after = json.loads(
            provider.handle_tool_call("om_search", {"query": canary, "limit": 10})
        )
        context_after = json.loads(
            provider.handle_tool_call("om_context", {"query": canary, "limit": 10})
        ).get("text", "")
        prompt_after = provider.system_prompt_block()
        direct_contains = _contains_canary(direct_after, canary)
        tool_contains = canary in json.dumps(search_after, sort_keys=True)
        context_contains = _context_recall_contains(str(context_after), canary)
        should_contain = phase in {"prepare", "restart"}
        if (direct_contains, tool_contains, context_contains) != (
            should_contain,
            should_contain,
            should_contain,
        ):
            raise DoctorError(
                "direct/tool/context visibility mismatch: "
                f"{direct_contains}/{tool_contains}/{context_contains}"
            )
        if len(prompt_after) > 4000:
            raise DoctorError(
                f"startup prompt exceeded registered 4000-char bound: {len(prompt_after)}"
            )

        budget = _budget_probe(provider)
        method_names = sorted(
            name
            for name in dir(provider)
            if callable(getattr(provider, name, None))
            and name.lower() in {"delete", "forget", "purge", "erase"}
        )
        state_manifest = _tree_manifest(STATE_ROOT)
        result = {
            "schema_version": 1,
            "phase": phase,
            "provider": PROVIDER,
            "versions": {
                "hermes": "0.20.1",
                "plugin": "1.5.1",
                "observational_memory": importlib.metadata.version(
                    "observational-memory"
                ),
                "rank_bm25": importlib.metadata.version("rank-bm25"),
            },
            "plugin_manifest_sha256": plugin_root,
            "config_sha256": config_sha,
            "discovery": [
                {"name": row[0], "description": row[1], "available": row[2]}
                for row in discovered
                if row[0] == PROVIDER
            ],
            "tool_names": TOOLS,
            "provider_native_delete_methods": method_names,
            "provider_native_delete_or_forget_tool": False,
            "provider_native_physical_erasure_contract": False,
            "prompt_before_chars": len(prompt_before),
            "prompt_after_chars": len(prompt_after),
            "before_contains_canary": before_contains,
            "direct_contains_canary": direct_contains,
            "tool_contains_canary": tool_contains,
            "context_contains_canary": context_contains,
            "budget_probe": budget,
            "remember": remember,
            "api_credentials_present": [],
            "model_calls": 0,
            "external_calls": 0,
            "state_manifest": state_manifest,
            "state_manifest_sha256": _manifest_root(state_manifest),
        }
        return result
    finally:
        provider.shutdown()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["prepare", "restart", "isolated"])
    parser.add_argument("--canary", required=True)
    args = parser.parse_args()
    if not STATE_ROOT.is_dir() or STATE_ROOT.is_symlink():
        raise DoctorError("/state must be a real mounted directory")
    result = run_phase(args.phase, args.canary)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
