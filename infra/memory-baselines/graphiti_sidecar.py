#!/usr/bin/env python3
"""Pinned Graphiti explicit-triplet adapter for memory-system-v1."""

from __future__ import annotations

import asyncio
import contextlib
import importlib.metadata
import json
import os
import re
import sys
import tempfile
import time
import uuid
from collections.abc import Iterable, Mapping
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

GRAPHITI_REVISION = "401c59a65bdeb22a44136901ff30231e6998a7fe"
GRAPHITI_VERSION = "0.29.3"
GRAPHITI_SOURCE_ARCHIVE_SHA256 = (
    "9cfbc01e90f4e6dfbf61fefe86e7f04b15c57c08a7ff8298f873d6f5696d0303"
)


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"{name} is required for Graphiti select")
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
    if source_archive is not None and source_archive != GRAPHITI_SOURCE_ARCHIVE_SHA256:
        raise ValueError("Graphiti source archive receipt differs from reviewed source")
    source_context_path = Path(
        os.environ.get(
            "COTCODEC_MEMORY_SOURCE_CONTEXT_RECEIPT",
            "/opt/graphiti-source/.cotcodec-source-context.json",
        )
    )
    source_context_verified = False
    if source_context_path.is_file():
        source_context = json.loads(source_context_path.read_text(encoding="utf-8"))
        expected = {
            "system_id": "graphiti",
            "revision": GRAPHITI_REVISION,
            "source_archive_sha256": GRAPHITI_SOURCE_ARCHIVE_SHA256,
        }
        if any(source_context.get(key) != value for key, value in expected.items()):
            raise ValueError("Graphiti source context receipt differs from reviewed source")
        source_context_verified = True
    publication_ready = bool(
        source_archive and image_digest and model_receipts and source_context_verified
    )
    if os.environ.get("COTCODEC_PUBLICATION_MODE") == "1" and not publication_ready:
        raise ValueError("publication mode requires source, image, and model receipts")
    config = {
        "adapter": "graphiti-explicit-triplet-v1",
        "backend": "falkordblite-ephemeral",
        "embedding_base_url": embedding_base_url,
        "embedding_model": embedding_model,
        "embedding_revision": embedding_revision,
        "embedding_dimensions": dimensions,
        "construction_mode": "explicit-triplet-deterministic-dedup-fixture",
        "reranker": False,
        "source_context_verified": source_context_verified,
    }
    return MemorySystemReceipt(
        system_id="graphiti-explicit-triplet-v1",
        implementation_kind="oci_sidecar",
        implementation_revision=GRAPHITI_REVISION,
        configuration_sha256=sha256_text(canonical_json(config)),
        backend_id="falkordblite-0.10.0-ephemeral",
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


def _stable_uuid(namespace: str, value: str) -> str:
    digest = sha256_text(f"{namespace}:{value}")[:32]
    return str(uuid.UUID(hex=digest))


async def _select_async(request: MemorySystemRequest) -> MemorySelection:
    if importlib.metadata.version("graphiti-core") != GRAPHITI_VERSION:
        raise ValueError("installed Graphiti package version differs from reviewed source")
    if importlib.metadata.version("falkordblite") != "0.10.0":
        raise ValueError("installed FalkorDBLite version differs from the reviewed lock")
    embedding_base_url = _required_env("COTCODEC_MEMORY_EMBEDDING_BASE_URL").rstrip("/")
    embedding_model = os.environ.get(
        "COTCODEC_MEMORY_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"
    )
    dimensions = int(os.environ.get("COTCODEC_MEMORY_EMBEDDING_DIMENSIONS", "384"))
    os.environ["EMBEDDING_DIM"] = str(dimensions)

    from graphiti_core.cross_encoder.client import CrossEncoderClient
    from graphiti_core.driver.falkordb_driver import FalkorDriver
    from graphiti_core.edges import EntityEdge
    from graphiti_core.embedder.client import EmbedderClient
    from graphiti_core.graphiti import Graphiti
    from graphiti_core.llm_client.client import LLMClient
    from graphiti_core.nodes import EntityNode
    from redislite.async_falkordb_client import AsyncFalkorDB

    class HttpEmbedder(EmbedderClient):
        def __init__(self) -> None:
            self.calls = 0
            self.client = httpx.AsyncClient(timeout=30.0)

        async def create(
            self,
            input_data: str | list[str] | Iterable[int] | Iterable[Iterable[int]],
        ) -> list[float]:
            if isinstance(input_data, str):
                inputs = [input_data]
            elif isinstance(input_data, list) and all(
                isinstance(item, str) for item in input_data
            ):
                inputs = input_data
            else:
                raise TypeError("Graphiti embedding adapter accepts text only")
            response = await self.client.post(
                f"{embedding_base_url}/embeddings",
                json={
                    "model": embedding_model,
                    "input": inputs,
                    "dimensions": dimensions,
                },
            )
            response.raise_for_status()
            data = response.json()["data"]
            self.calls += len(inputs)
            if len(data) != 1:
                raise ValueError("Graphiti create expected one embedding")
            return [float(item) for item in data[0]["embedding"]]

        async def create_batch(self, input_data_list: list[str]) -> list[list[float]]:
            response = await self.client.post(
                f"{embedding_base_url}/embeddings",
                json={
                    "model": embedding_model,
                    "input": input_data_list,
                    "dimensions": dimensions,
                },
            )
            response.raise_for_status()
            data = sorted(response.json()["data"], key=lambda item: item["index"])
            self.calls += len(input_data_list)
            return [[float(value) for value in item["embedding"]] for item in data]

    class DeterministicResolver(LLMClient):
        def __init__(self) -> None:
            super().__init__(config=None, cache=False)
            self.fixture_calls = 0

        async def _generate_response(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
            self.fixture_calls += 1
            response_model = args[1] if len(args) > 1 else kwargs.get("response_model")
            response_name = getattr(response_model, "__name__", "unstructured")
            if response_name == "NodeResolutions":
                messages = args[0]
                content = messages[-1].content
                match = re.search(
                    r"<ENTITIES>\s*(\[.*?\])\s*</ENTITIES>",
                    content,
                    flags=re.DOTALL,
                )
                if match is None:
                    raise RuntimeError("cannot parse Graphiti node-resolution fixture")
                entities = json.loads(match.group(1))
                return {
                    "entity_resolutions": [
                        {
                            "id": int(entity["id"]),
                            "name": str(entity["name"]),
                            "duplicate_candidate_id": -1,
                        }
                        for entity in entities
                    ]
                }
            if response_name == "EdgeDuplicate":
                return {"duplicate_facts": [], "contradicted_facts": []}
            if response_name == "EdgeTimestamps":
                return {"valid_at": None, "invalid_at": None}
            raise RuntimeError(
                "explicit-triplet fixture forbids unregistered Graphiti LLM call: "
                f"{response_name}"
            )

    class ForbiddenReranker(CrossEncoderClient):
        async def rank(
            self, query: str, passages: list[str]
        ) -> list[tuple[str, float]]:
            raise RuntimeError("primary Graphiti cell disables cross-encoder reranking")

    started = time.perf_counter()
    embedder = HttpEmbedder()
    llm = DeterministicResolver()
    with tempfile.TemporaryDirectory(prefix="cotcodec-graphiti-") as temporary:
        db_path = str(Path(temporary) / "falkordblite.db")
        client = AsyncFalkorDB(dbfilename=db_path)
        group_id = "g-" + sha256_text(request.session_scope)[:20]
        driver = FalkorDriver(falkor_db=client, database=group_id)
        graphiti = Graphiti(
            graph_driver=driver,
            llm_client=llm,
            embedder=embedder,
            cross_encoder=ForbiddenReranker(),
            store_raw_episode_content=False,
        )
        active_edges: dict[tuple[str, str], EntityEdge] = {}
        try:
            await graphiti.build_indices_and_constraints()
            for event in request.events:
                key = (event.entity_id, event.key)
                old_edge = active_edges.pop(key, None)
                if event.kind in {"update", "delete"} and old_edge is not None:
                    await old_edge.delete(graphiti.driver)
                if event.kind not in {"write", "update", "observe"} or event.value is None:
                    continue
                created_at = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(
                    seconds=event.step
                )
                source_node = EntityNode(
                    uuid=_stable_uuid("entity", event.entity_id),
                    name=event.entity_id,
                    group_id=group_id,
                    labels=["Entity"],
                    created_at=created_at,
                )
                target_node = EntityNode(
                    uuid=_stable_uuid("value", f"{event.entity_id}:{event.key}:{event.value}"),
                    name=event.value,
                    group_id=group_id,
                    labels=["Entity"],
                    created_at=created_at,
                )
                edge = EntityEdge(
                    uuid=_stable_uuid("edge", event.source_event_id),
                    group_id=group_id,
                    source_node_uuid=source_node.uuid,
                    target_node_uuid=target_node.uuid,
                    name=event.key,
                    fact=canonical_json(
                        {
                            "entity": event.entity_id,
                            "key": event.key,
                            "value": event.value,
                            "step": event.step,
                            "untrusted": event.untrusted,
                            "source_event_id": event.source_event_id,
                        }
                    ),
                    created_at=created_at,
                    valid_at=created_at,
                    attributes={"source_event_id": event.source_event_id},
                )
                result = await graphiti.add_triplet(source_node, edge, target_node)
                active_edges[key] = result.edges[0]
            searched = await graphiti.search(
                request.query,
                group_ids=[group_id],
                num_results=request.budget.retrieval_top_k,
            )
        finally:
            await graphiti.close()
            await embedder.client.aclose()
            with contextlib.suppress(Exception):
                await client.close()

    evidence_items: list[MemoryEvidence] = []
    for index, edge in enumerate(searched):
        source_id = edge.attributes.get("source_event_id")
        if not isinstance(source_id, str) or not source_id:
            try:
                source_id = json.loads(edge.fact).get("source_event_id")
            except (AttributeError, json.JSONDecodeError):
                source_id = None
        if not isinstance(source_id, str) or not source_id:
            raise ValueError("Graphiti edge omitted source_event_id attribution")
        evidence_items.append(
            MemoryEvidence(
                evidence_id="graphiti:" + sha256_text(f"{edge.uuid}\0{edge.fact}")[:24],
                text=edge.fact,
                source_record_ids=(source_id,),
                score=1.0 / (index + 1),
                kind="path",
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


def _selection(request: MemorySystemRequest) -> MemorySelection:
    with contextlib.redirect_stdout(sys.stderr):
        return asyncio.run(_select_async(request))


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
