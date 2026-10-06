#!/usr/bin/env python3
"""Pinned Hindsight chunk-retain/recall adapter for memory-system-v1."""

from __future__ import annotations

import asyncio
import contextlib
import importlib.metadata
import json
import os
import shutil
import sys
import time
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

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

HINDSIGHT_REVISION = "5781d28d8fcc717a15818330b12250b311957000"
HINDSIGHT_VERSION = "0.9.0"
PG0_VERSION = "0.15.1"
HINDSIGHT_SOURCE_ARCHIVE_SHA256 = (
    "993a015782322ab0fd336b6ab457d895d74d941390e36ebfd562dec9790bdf9c"
)
HINDSIGHT_EXCLUDED_UNSAFE_ARCHIVE_PATHS = [
    "hindsight-integrations/coding-agents/node_modules"
]


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"{name} is required for Hindsight select")
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
    if source_archive is not None and source_archive != HINDSIGHT_SOURCE_ARCHIVE_SHA256:
        raise ValueError("Hindsight source archive receipt differs from reviewed source")
    source_context_path = Path(
        os.environ.get(
            "COTCODEC_MEMORY_SOURCE_CONTEXT_RECEIPT",
            "/opt/hindsight-source/.cotcodec-source-context.json",
        )
    )
    source_context_verified = False
    if source_context_path.is_file():
        source_context = json.loads(source_context_path.read_text(encoding="utf-8"))
        expected = {
            "system_id": "hindsight",
            "revision": HINDSIGHT_REVISION,
            "source_archive_sha256": HINDSIGHT_SOURCE_ARCHIVE_SHA256,
            "excluded_unsafe_archive_paths": HINDSIGHT_EXCLUDED_UNSAFE_ARCHIVE_PATHS,
        }
        if any(source_context.get(key) != value for key, value in expected.items()):
            raise ValueError("Hindsight source context receipt differs from reviewed source")
        source_context_verified = True
    publication_ready = bool(
        source_archive and image_digest and model_receipts and source_context_verified
    )
    if os.environ.get("COTCODEC_PUBLICATION_MODE") == "1" and not publication_ready:
        raise ValueError("publication mode requires source, image, and model receipts")
    config = {
        "adapter": "hindsight-chunk-recall-v1",
        "backend": f"pg0-embedded-{PG0_VERSION}",
        "embedding_base_url": embedding_base_url,
        "embedding_model": embedding_model,
        "embedding_revision": embedding_revision,
        "embedding_dimensions": dimensions,
        "retain_extraction_mode": "chunks",
        "llm_provider": "none",
        "reranker": "rrf-passthrough",
        "reflect": False,
        "source_context_verified": source_context_verified,
    }
    return MemorySystemReceipt(
        system_id="hindsight-chunk-recall-v1",
        implementation_kind="oci_sidecar",
        implementation_revision=HINDSIGHT_REVISION,
        configuration_sha256=sha256_text(canonical_json(config)),
        backend_id=f"pg0-embedded-{PG0_VERSION}",
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


def _embedding_input_count(stats_url: str) -> int:
    response = httpx.get(stats_url, timeout=10.0)
    response.raise_for_status()
    value = response.json().get("input_count")
    if not isinstance(value, int) or value < 0:
        raise ValueError("embedding stats endpoint omitted input_count")
    return value


def _document_id(entity_id: str, key: str) -> str:
    return "cotcodec-" + sha256_text(f"{entity_id}\0{key}")[:32]


def _event_content(event: Any) -> str:
    if event.value is None:
        raise ValueError("Hindsight retain requires an event value")
    return canonical_json(
        {
            "source_event_id": event.source_event_id,
            "entity_id": event.entity_id,
            "key": event.key,
            "value": event.value,
            "step": event.step,
            "untrusted": event.untrusted,
        }
    )


def _cleanup_profile(profile: str) -> None:
    from hindsight_embed.profile_manager import ProfileManager

    manager = ProfileManager()
    paths = manager.resolve_profile_paths(profile)
    if manager.profile_exists(profile):
        manager.delete_profile(profile)
    else:
        for path in (paths.config, paths.lock, paths.log):
            path.unlink(missing_ok=True)
    instance_root = (Path.home() / ".pg0" / "instances").resolve()
    database = (instance_root / f"hindsight-embed-{profile}").resolve()
    if database.parent != instance_root or not database.name.startswith(
        "hindsight-embed-cotcodec-"
    ):
        raise ValueError("refusing to remove an unscoped Hindsight database")
    if database.is_dir():
        shutil.rmtree(database)


def _selection(request: MemorySystemRequest) -> MemorySelection:
    expected_packages = {
        "hindsight-all": HINDSIGHT_VERSION,
        "hindsight-api-slim": HINDSIGHT_VERSION,
        "hindsight-client": HINDSIGHT_VERSION,
        "hindsight-embed": HINDSIGHT_VERSION,
        "pg0-embedded": PG0_VERSION,
    }
    for package, expected in expected_packages.items():
        if importlib.metadata.version(package) != expected:
            raise ValueError(f"installed {package} version differs from reviewed runtime")

    embedding_base_url = _required_env("COTCODEC_MEMORY_EMBEDDING_BASE_URL").rstrip("/")
    embedding_model = os.environ.get(
        "COTCODEC_MEMORY_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"
    )
    dimensions = int(os.environ.get("COTCODEC_MEMORY_EMBEDDING_DIMENSIONS", "384"))
    stats_url = _required_env("COTCODEC_MEMORY_EMBEDDING_STATS_URL")
    os.environ.update(
        {
            "HINDSIGHT_API_EMBEDDINGS_PROVIDER": "openai",
            "HINDSIGHT_API_EMBEDDINGS_OPENAI_API_KEY": os.environ.get(
                "COTCODEC_MEMORY_EMBEDDING_API_KEY", "local"
            ),
            "HINDSIGHT_API_EMBEDDINGS_OPENAI_MODEL": embedding_model,
            "HINDSIGHT_API_EMBEDDINGS_OPENAI_BASE_URL": embedding_base_url,
            "HINDSIGHT_API_EMBEDDINGS_OPENAI_DIMENSIONS": str(dimensions),
            "HINDSIGHT_API_RERANKER_PROVIDER": "rrf",
            "HINDSIGHT_API_LOG_LEVEL": "warning",
        }
    )

    from hindsight import HindsightEmbedded

    started = time.perf_counter()
    embedding_before = _embedding_input_count(stats_url)
    profile = "cotcodec-" + uuid.uuid4().hex
    bank_id = "bank-" + sha256_text(request.session_scope)[:24]
    client = HindsightEmbedded(
        profile=profile,
        llm_provider="none",
        llm_model="none",
        idle_timeout=0,
        log_level="warning",
    )
    active_documents: set[tuple[str, str]] = set()
    try:
        for event in request.events:
            key = (event.entity_id, event.key)
            document_id = _document_id(*key)
            if event.kind == "delete":
                if key in active_documents:
                    asyncio.run(
                        client.documents.delete_document(
                            bank_id=bank_id,
                            document_id=document_id,
                        )
                    )
                    active_documents.discard(key)
                continue
            if event.kind in {"write", "update", "observe"}:
                timestamp = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(
                    seconds=event.step
                )
                client.retain(
                    bank_id=bank_id,
                    content=_event_content(event),
                    timestamp=timestamp,
                    context="cotcodec source-attributed prefix event",
                    document_id=document_id,
                    metadata={
                        "source_event_id": event.source_event_id,
                        "entity_id": event.entity_id,
                        "key": event.key,
                    },
                    update_mode="replace",
                )
                active_documents.add(key)
        recalled = client.recall(
            bank_id=bank_id,
            query=request.query,
            types=["world"],
            max_tokens=request.budget.max_injected_tokens,
            budget="low",
        )
        results = recalled.results[: request.budget.retrieval_top_k]
        embedding_after = _embedding_input_count(stats_url)
        client.delete_bank(bank_id)
    finally:
        client.close(stop_daemon=True)
        _cleanup_profile(profile)

    evidence_items: list[MemoryEvidence] = []
    for index, item in enumerate(results):
        metadata = item.metadata or {}
        source_id = metadata.get("source_event_id")
        if not isinstance(source_id, str) or not source_id:
            try:
                source_id = json.loads(item.text).get("source_event_id")
            except (AttributeError, json.JSONDecodeError):
                source_id = None
        if not isinstance(source_id, str) or not source_id:
            raise ValueError("Hindsight result omitted source_event_id attribution")
        score = item.scores.final if item.scores is not None else 1.0 / (index + 1)
        evidence_items.append(
            MemoryEvidence(
                evidence_id="hindsight:"
                + sha256_text(f"{source_id}\0{item.text}")[:24],
                text=item.text,
                source_record_ids=(source_id,),
                score=float(score),
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
        embedding_calls=embedding_after - embedding_before,
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
