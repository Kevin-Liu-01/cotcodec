#!/usr/bin/env python3
"""Exact-source LangMem/Postgres lifecycle phase probe.

The background manager uses deterministic extraction so this doctor measures
LangMem's store plumbing and lifecycle semantics, not model quality.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any
from unittest.mock import patch

from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableLambda
from langgraph.store.postgres import PostgresStore
from langmem import (
    create_manage_memory_tool,
    create_memory_store_manager,
    create_search_memory_tool,
)
from langmem.knowledge.extraction import ExtractedMemory, Memory

MARKER = "COTCODEC_LANGMEM_PHASE="
UUID_RE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"{name} is required")
    return value


def _contents(serialized: str) -> list[str]:
    rows = json.loads(serialized)
    if not isinstance(rows, list):
        raise ValueError("LangMem search did not return a JSON list")
    values: list[str] = []
    for row in rows:
        value = row.get("value", {}) if isinstance(row, dict) else {}
        content = value.get("content") if isinstance(value, dict) else None
        if isinstance(content, str):
            values.append(content)
        elif isinstance(content, dict) and isinstance(content.get("content"), str):
            values.append(content["content"])
    return values


def _tools(store: PostgresStore, namespace: tuple[str, ...]):
    return (
        create_manage_memory_tool(namespace, store=store),
        create_search_memory_tool(namespace, store=store, response_format="content"),
    )


def _search(search: Any, query: str) -> list[str]:
    return _contents(search.invoke({"query": query, "limit": 20}))


def _memory_id(result: str) -> str:
    match = UUID_RE.search(result)
    if match is None:
        raise ValueError("LangMem manage tool omitted its generated memory ID")
    return match.group(0)


def _background_manager(store: PostgresStore, canary: str):
    deterministic = RunnableLambda(
        lambda _input: [
            ExtractedMemory(
                "deterministic-background-record",
                Memory(content=canary),
            )
        ]
    )
    fake_model = FakeListChatModel(responses=["unused deterministic transport"])
    with patch(
        "langmem.knowledge.extraction.create_memory_manager",
        return_value=deterministic,
    ):
        return create_memory_store_manager(
            fake_model,
            namespace=("cotcodec", "background", "user-a"),
            store=store,
            query_limit=4,
        )


def _prepare(store: PostgresStore) -> dict[str, Any]:
    store.setup()
    original = _required("COTCODEC_ORIGINAL_CANARY")
    updated = _required("COTCODEC_UPDATED_CANARY")
    isolated = _required("COTCODEC_ISOLATED_CANARY")
    background = _required("COTCODEC_BACKGROUND_CANARY")
    manage_a, search_a = _tools(store, ("cotcodec", "hot", "user-a"))
    manage_b, search_b = _tools(store, ("cotcodec", "hot", "user-b"))

    memory_a = _memory_id(manage_a.invoke({"content": original, "action": "create"}))
    memory_b = _memory_id(manage_b.invoke({"content": isolated, "action": "create"}))
    manage_a.invoke({"id": memory_a, "content": updated, "action": "update"})

    manager = _background_manager(store, background)
    puts = manager.invoke(
        {
            "messages": [HumanMessage(content="deterministic lifecycle transport")],
            "max_steps": 1,
        }
    )
    user_a = _search(search_a, "updated")
    user_b = _search(search_b, "isolated")
    background_rows = store.search(("cotcodec", "background", "user-a"), limit=20)
    checks = {
        "hot_path_create_update_uses_public_tool": (updated in user_a and original not in user_a),
        "user_namespace_isolation": (
            isolated not in user_a and updated not in user_b and isolated in user_b
        ),
        "background_manager_persisted_deterministic_extraction": (
            len(puts) == 1
            and len(background_rows) == 1
            and background_rows[0].value == {"kind": "Memory", "content": {"content": background}}
        ),
    }
    if not all(checks.values()):
        raise RuntimeError(f"prepare checks failed: {checks}")
    return {"phase": "prepare", "memory_a": memory_a, "memory_b": memory_b, **checks}


def _restart(store: PostgresStore) -> dict[str, Any]:
    updated = _required("COTCODEC_UPDATED_CANARY")
    isolated = _required("COTCODEC_ISOLATED_CANARY")
    background = _required("COTCODEC_BACKGROUND_CANARY")
    memory_a = _required("COTCODEC_MEMORY_A")
    memory_b = _required("COTCODEC_MEMORY_B")
    manage_a, search_a = _tools(store, ("cotcodec", "hot", "user-a"))
    _, search_b = _tools(store, ("cotcodec", "hot", "user-b"))
    user_a = _search(search_a, "updated")
    user_b = _search(search_b, "isolated")
    background_rows = store.search(("cotcodec", "background", "user-a"), limit=20)
    before_delete = store.get(("cotcodec", "hot", "user-a"), memory_a)
    isolated_item = store.get(("cotcodec", "hot", "user-b"), memory_b)
    manage_a.invoke({"id": memory_a, "action": "delete"})
    checks = {
        "database_and_fresh_process_restart_preserve_acknowledged_state": (
            before_delete is not None
            and isolated_item is not None
            and updated in user_a
            and isolated in user_b
            and len(background_rows) == 1
            and background_rows[0].value["content"]["content"] == background
        ),
        "public_tool_logical_delete_succeeds": (
            store.get(("cotcodec", "hot", "user-a"), memory_a) is None
            and updated not in _search(search_a, "updated")
        ),
    }
    if not all(checks.values()):
        raise RuntimeError(f"restart checks failed: {checks}")
    return {"phase": "restart", **checks}


def _purge(store: PostgresStore) -> dict[str, Any]:
    namespaces = (
        ("cotcodec", "hot", "user-a"),
        ("cotcodec", "hot", "user-b"),
        ("cotcodec", "background", "user-a"),
    )
    first_class = callable(getattr(store, "delete_namespace", None))
    deleted = 0
    for namespace in namespaces:
        for item in store.search(namespace, limit=100):
            store.delete(namespace, item.key)
            deleted += 1
    empty = all(not store.search(namespace, limit=100) for namespace in namespaces)
    checks = {
        "first_class_namespace_purge_available": first_class,
        "enumerate_then_delete_logically_clears_scopes": empty and deleted == 2,
    }
    if first_class or not checks["enumerate_then_delete_logically_clears_scopes"]:
        raise RuntimeError(f"purge checks failed: {checks}")
    return {"phase": "purge", "deleted_records": deleted, **checks}


def main() -> int:
    phase = _required("COTCODEC_PHASE")
    database_url = _required("COTCODEC_DATABASE_URL")
    with PostgresStore.from_conn_string(database_url, index=None) as store:
        if phase == "prepare":
            result = _prepare(store)
        elif phase == "restart":
            result = _restart(store)
        elif phase == "purge":
            result = _purge(store)
        else:
            raise ValueError(f"unknown lifecycle phase: {phase}")
    print(MARKER + json.dumps(result, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
