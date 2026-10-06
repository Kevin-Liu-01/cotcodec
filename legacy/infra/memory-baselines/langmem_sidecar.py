#!/usr/bin/env python3
"""Pinned LangMem tool/store adapter for the memory-system-v1 wire protocol."""

from __future__ import annotations

import contextlib
import importlib.metadata
import json
import os
import re
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials.schema import canonical_json, sha256_text  # noqa: E402
from harness.memory_trials.systems import (  # noqa: E402
    MemoryCostLedger,
    MemoryEvidence,
    MemorySelection,
    MemorySystemReceipt,
    MemorySystemRequest,
)

LANGMEM_REVISION = "29cbe41e58528f92e9efa773c12e15c47be3808c"
LANGMEM_VERSION = "0.0.30"
LANGGRAPH_VERSION = "1.2.11"
LANGMEM_SOURCE_ARCHIVE_SHA256 = (
    "24c85c514c80bb263a16626971e8ef53978fd1bc7f9319e47d8a5a0bf4956521"
)
_MEMORY_ID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"
)


class StoredMemory(BaseModel):
    """Source-attributed payload passed through LangMem's public tool schema."""

    model_config = ConfigDict(extra="forbid")

    source_event_id: str
    entity_id: str
    key: str
    value: str
    step: int
    untrusted: bool


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"{name} is required for LangMem select")
    return value


def _receipt() -> MemorySystemReceipt:
    embedding_base_url = os.environ.get(
        "COTCODEC_MEMORY_EMBEDDING_BASE_URL", "unconfigured"
    )
    embedding_model = os.environ.get(
        "COTCODEC_MEMORY_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"
    )
    embedding_revision = os.environ.get(
        "COTCODEC_MEMORY_EMBEDDING_REVISION",
        "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a",
    )
    dimensions = int(os.environ.get("COTCODEC_MEMORY_EMBEDDING_DIMENSIONS", "384"))
    source_archive = os.environ.get("COTCODEC_MEMORY_SOURCE_ARCHIVE_SHA256")
    image_digest = os.environ.get("COTCODEC_MEMORY_IMAGE_DIGEST")
    model_receipts = tuple(
        item
        for item in os.environ.get(
            "COTCODEC_MEMORY_MODEL_RECEIPT_SHA256S", ""
        ).split(",")
        if item
    )
    if source_archive is not None and source_archive != LANGMEM_SOURCE_ARCHIVE_SHA256:
        raise ValueError("LangMem source archive receipt differs from reviewed source")
    source_context_path = Path(
        os.environ.get(
            "COTCODEC_MEMORY_SOURCE_CONTEXT_RECEIPT",
            "/opt/langmem-source/.cotcodec-source-context.json",
        )
    )
    source_context_verified = False
    if source_context_path.is_file():
        source_context = json.loads(source_context_path.read_text(encoding="utf-8"))
        expected = {
            "system_id": "langmem",
            "revision": LANGMEM_REVISION,
            "source_archive_sha256": LANGMEM_SOURCE_ARCHIVE_SHA256,
        }
        if any(source_context.get(key) != value for key, value in expected.items()):
            raise ValueError("LangMem source context receipt differs from reviewed source")
        source_context_verified = True
    publication_ready = bool(
        source_archive and image_digest and model_receipts and source_context_verified
    )
    if os.environ.get("COTCODEC_PUBLICATION_MODE") == "1" and not publication_ready:
        raise ValueError("publication mode requires source, image, and model receipts")
    config = {
        "adapter": "langmem-tools-store-v1",
        "backend": f"langgraph-in-memory-store-{LANGGRAPH_VERSION}",
        "embedding_base_url": embedding_base_url,
        "embedding_model": embedding_model,
        "embedding_revision": embedding_revision,
        "embedding_dimensions": dimensions,
        "construction_mode": "explicit-source-attributed-tool-calls",
        "background_manager": False,
        "source_context_verified": source_context_verified,
    }
    return MemorySystemReceipt(
        system_id="langmem-tools-store-v1",
        implementation_kind="oci_sidecar",
        implementation_revision=LANGMEM_REVISION,
        configuration_sha256=sha256_text(canonical_json(config)),
        backend_id=f"langgraph-in-memory-store-{LANGGRAPH_VERSION}",
        source_archive_sha256=source_archive,
        image_digest=image_digest,
        model_receipt_sha256s=model_receipts,
        publication_ready=publication_ready,
    )


def _response(operation: str, *, ok: bool, result: Mapping[str, Any]) -> str:
    return canonical_json(
        {
            "protocol": "memory-system-v1",
            "operation": operation,
            "ok": ok,
            "result": dict(result),
        }
    )


def _parse_memory_id(result: str) -> str:
    match = _MEMORY_ID_RE.search(result)
    if match is None:
        raise ValueError("LangMem manage tool omitted its memory ID")
    return match.group(0)


def _event_content(event: Any) -> dict[str, Any]:
    if event.value is None:
        raise ValueError("LangMem create/update requires an event value")
    return {
        "source_event_id": event.source_event_id,
        "entity_id": event.entity_id,
        "key": event.key,
        "value": event.value,
        "step": event.step,
        "untrusted": event.untrusted,
    }


def _selection(request: MemorySystemRequest) -> MemorySelection:
    if importlib.metadata.version("langmem") != LANGMEM_VERSION:
        raise ValueError("installed LangMem package version differs from reviewed source")
    if importlib.metadata.version("langgraph") != LANGGRAPH_VERSION:
        raise ValueError("installed LangGraph package version differs from reviewed lock")

    embedding_base_url = _required_env("COTCODEC_MEMORY_EMBEDDING_BASE_URL").rstrip("/")
    embedding_model = os.environ.get(
        "COTCODEC_MEMORY_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"
    )
    dimensions = int(os.environ.get("COTCODEC_MEMORY_EMBEDDING_DIMENSIONS", "384"))

    from langchain_core.embeddings import Embeddings
    from langgraph.store.memory import InMemoryStore
    from langmem import create_manage_memory_tool, create_search_memory_tool

    class HttpEmbeddings(Embeddings):
        def __init__(self) -> None:
            self.calls = 0
            self.client = httpx.Client(timeout=30.0)

        def _embed(self, texts: list[str]) -> list[list[float]]:
            response = self.client.post(
                f"{embedding_base_url}/embeddings",
                json={
                    "model": embedding_model,
                    "input": texts,
                    "dimensions": dimensions,
                },
            )
            response.raise_for_status()
            data = sorted(response.json()["data"], key=lambda item: item["index"])
            self.calls += len(texts)
            return [[float(value) for value in item["embedding"]] for item in data]

        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            return self._embed(texts)

        def embed_query(self, text: str) -> list[float]:
            return self._embed([text])[0]

    started = time.perf_counter()
    embedder = HttpEmbeddings()
    namespace = ("cotcodec", request.session_scope)
    store = InMemoryStore(index={"dims": dimensions, "embed": embedder})
    manage = create_manage_memory_tool(
        namespace,
        schema=StoredMemory,
        actions_permitted=("create", "update", "delete"),
        store=store,
    )
    search = create_search_memory_tool(
        namespace,
        store=store,
        response_format="content",
    )
    active_ids: dict[tuple[str, str], list[str]] = {}
    try:
        for event in request.events:
            key = (event.entity_id, event.key)
            existing = active_ids.get(key, [])
            if event.kind == "delete":
                for memory_id in existing:
                    manage.invoke({"id": memory_id, "action": "delete"})
                active_ids.pop(key, None)
                continue
            if event.kind == "update" and existing:
                primary_id, *duplicates = existing
                manage.invoke(
                    {
                        "id": primary_id,
                        "content": _event_content(event),
                        "action": "update",
                    }
                )
                for memory_id in duplicates:
                    manage.invoke({"id": memory_id, "action": "delete"})
                active_ids[key] = [primary_id]
                continue
            if event.kind in {"write", "update", "observe"}:
                result = manage.invoke(
                    {"content": _event_content(event), "action": "create"}
                )
                active_ids.setdefault(key, []).append(_parse_memory_id(result))
        serialized = search.invoke(
            {"query": request.query, "limit": request.budget.retrieval_top_k}
        )
        searched = json.loads(serialized)
    finally:
        embedder.client.close()

    evidence_items: list[MemoryEvidence] = []
    for index, item in enumerate(searched):
        value = item.get("value")
        content = value.get("content") if isinstance(value, dict) else None
        if not isinstance(content, dict):
            raise ValueError("LangMem search result omitted structured content")
        source_id = content.get("source_event_id")
        if not isinstance(source_id, str) or not source_id:
            raise ValueError("LangMem search result omitted source_event_id attribution")
        text = canonical_json(content)
        score = item.get("score")
        evidence_items.append(
            MemoryEvidence(
                evidence_id="langmem:" + sha256_text(f"{source_id}\0{text}")[:24],
                text=text,
                source_record_ids=(source_id,),
                score=float(score) if isinstance(score, int | float) else 1.0 / (index + 1),
            )
        )
    evidence = tuple(evidence_items)
    input_json = canonical_json(request.model_dump(mode="json"))
    output_json = canonical_json([item.model_dump(mode="json") for item in evidence])
    injected_json = canonical_json(
        [{"id": item.evidence_id, "text": item.text} for item in evidence]
    )
    costs = MemoryCostLedger(
        writes=len(request.events),
        reads=1,
        serialized_input_bytes=len(input_json.encode()),
        serialized_output_bytes=len(output_json.encode()),
        injected_tokens_estimate=(len(injected_json.encode()) + 3) // 4,
        embedding_calls=embedder.calls,
        llm_calls=0,
        latency_ms=(time.perf_counter() - started) * 1000,
    )
    receipt = _receipt()
    payload = {
        "request_id": request.request_id,
        "evidence": [item.model_dump(mode="json") for item in evidence],
        "costs": costs.model_dump(mode="json"),
        "receipt": receipt.model_dump(mode="json"),
    }
    return MemorySelection(
        **payload,
        selection_sha256=sha256_text(canonical_json(payload)),
    )


def main() -> int:
    line = sys.stdin.readline()
    try:
        envelope = json.loads(line)
        if envelope.get("protocol") != "memory-system-v1":
            raise ValueError("unsupported protocol")
        operation = envelope["operation"]
        payload = envelope.get("payload", {})
        if operation == "handshake":
            result = {"receipt": _receipt().model_dump(mode="json")}
        elif operation == "select":
            request = MemorySystemRequest.model_validate(payload)
            with contextlib.redirect_stdout(sys.stderr):
                result = {"selection": _selection(request).model_dump(mode="json")}
        elif operation == "purge":
            if not isinstance(payload.get("session_scope"), str):
                raise ValueError("purge requires session_scope")
            result = {"purged": True}
        else:
            raise ValueError(f"unsupported operation: {operation}")
    except Exception as exc:
        operation = locals().get("operation", "unknown")
        print(_response(operation, ok=False, result={"error": str(exc)}))
        return 2
    print(_response(operation, ok=True, result=result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
