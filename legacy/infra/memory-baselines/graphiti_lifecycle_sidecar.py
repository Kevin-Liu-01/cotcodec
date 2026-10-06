#!/usr/bin/env python3
"""Expose pinned Graphiti/FalkorDBLite through ``memory-lifecycle-v1``.

The adapter exercises Graphiti's explicit entity-edge storage and hybrid search
without an extraction LLM.  Every lifecycle session owns a separate embedded
FalkorDB file so branch isolation and physical purge are testable.  Checkpoint
restore verifies the already-persisted graph; it never reconstructs state from
the checkpoint.
"""

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
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from graphiti_core.cross_encoder.client import CrossEncoderClient  # noqa: E402
from graphiti_core.driver.falkordb_driver import FalkorDriver  # noqa: E402
from graphiti_core.edges import EntityEdge  # noqa: E402
from graphiti_core.embedder.client import EmbedderClient  # noqa: E402
from graphiti_core.graphiti import Graphiti  # noqa: E402
from graphiti_core.llm_client.client import LLMClient  # noqa: E402
from graphiti_core.nodes import EntityNode  # noqa: E402
from redislite.async_falkordb_client import AsyncFalkorDB  # noqa: E402

from harness.memory_trials.lifecycle import (  # noqa: E402
    LIFECYCLE_PROTOCOL_VERSION,
    LifecycleCapability,
    LifecycleCheckpoint,
    LifecycleCheckpointRecord,
    LifecycleCommand,
    LifecycleEvidence,
    LifecycleOperationReceipt,
    LifecyclePhase,
    LifecyclePhaseCost,
    LifecycleStateSummary,
    LifecycleSystemReceipt,
    MemoryLifecycleError,
)
from harness.memory_trials.schema import canonical_json, sha256_text  # noqa: E402

GRAPHITI_REVISION = "401c59a65bdeb22a44136901ff30231e6998a7fe"
GRAPHITI_VERSION = "0.29.3"
FALKORDBLITE_VERSION = "0.10.0"
GRAPHITI_SOURCE_ARCHIVE_SHA256 = (
    "9cfbc01e90f4e6dfbf61fefe86e7f04b15c57c08a7ff8298f873d6f5696d0303"
)
ADAPTER_REVISION = "graphiti-explicit-triplet-lifecycle-v1"
JOURNAL_SCHEMA_VERSION = 1
GRAPH_GROUP = "lifecycle"
NATIVE_FIELDS = {"edge_uuid", "source_node_uuid", "target_node_uuid"}


def _response(operation: str, *, ok: bool, result: dict[str, Any]) -> str:
    return canonical_json(
        {
            "protocol": LIFECYCLE_PROTOCOL_VERSION,
            "operation": operation,
            "ok": ok,
            "result": result,
        }
    )


def _phase(kind: str) -> LifecyclePhase:
    if kind == "apply":
        return LifecyclePhase.CONSTRUCTION
    if kind == "query":
        return LifecyclePhase.RETRIEVAL
    return LifecyclePhase.CONTROL


def _token_estimate(value: str) -> int:
    return (len(value.encode()) + 3) // 4


def _seal_operation(payload: dict[str, Any]) -> LifecycleOperationReceipt:
    sealed = dict(payload)
    sealed["operation_sha256"] = sha256_text(canonical_json(payload))
    return LifecycleOperationReceipt.model_validate(sealed)


def _stable_uuid(namespace: str, value: str) -> str:
    return str(uuid.UUID(hex=sha256_text(f"{namespace}:{value}")[:32]))


def _scope_sha256(scope: str) -> str:
    return sha256_text(f"graphiti-lifecycle-scope-v1\0{scope}")


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    payload = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(temporary, flags, 0o600)
    try:
        os.write(descriptor, payload)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _crash_if_requested(command_id: str, point: str) -> None:
    requested = os.environ.get("COTCODEC_GRAPHITI_LIFECYCLE_CRASH_HOOK")
    if requested == f"{command_id}:{point}":
        os._exit(86)


class _HttpEmbedder(EmbedderClient):
    def __init__(self) -> None:
        self.calls = 0
        self.base_url = os.environ["COTCODEC_MEMORY_EMBEDDING_BASE_URL"].rstrip("/")
        self.model = os.environ.get(
            "COTCODEC_MEMORY_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"
        )
        self.dimensions = int(
            os.environ.get("COTCODEC_MEMORY_EMBEDDING_DIMENSIONS", "384")
        )
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
            raise TypeError("Graphiti lifecycle embeddings accept text only")
        result = await self.create_batch(inputs)
        if len(result) != 1:
            raise MemoryLifecycleError("Graphiti expected one embedding")
        return result[0]

    async def create_batch(self, input_data_list: list[str]) -> list[list[float]]:
        response = await self.client.post(
            f"{self.base_url}/embeddings",
            json={
                "model": self.model,
                "input": input_data_list,
                "dimensions": self.dimensions,
            },
        )
        response.raise_for_status()
        data = sorted(response.json()["data"], key=lambda item: item["index"])
        self.calls += len(input_data_list)
        return [[float(value) for value in item["embedding"]] for item in data]


class _ForbiddenLLM(LLMClient):
    def __init__(self) -> None:
        super().__init__(config=None, cache=False)

    async def _generate_response(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        raise MemoryLifecycleError("explicit-triplet Graphiti lifecycle forbids LLM calls")


class _ForbiddenReranker(CrossEncoderClient):
    async def rank(
        self, query: str, passages: list[str]
    ) -> list[tuple[str, float]]:
        raise MemoryLifecycleError("Graphiti lifecycle disables cross-encoder reranking")


async def _close_embedded(client: AsyncFalkorDB) -> None:
    """Work around redislite 0.10.0's async close path not stopping its server."""

    async_client = client.client
    with contextlib.suppress(Exception):
        await async_client._client.aclose()  # noqa: SLF001
    sync_client = async_client._sync_client  # noqa: SLF001
    sync_client._async_managed = False  # noqa: SLF001
    sync_client._cleanup()  # noqa: SLF001


class GraphitiLifecyclePort:
    """Persistent task-blind lifecycle port over one FalkorDBLite file per scope."""

    def __init__(self, root: Path) -> None:
        if importlib.metadata.version("graphiti-core") != GRAPHITI_VERSION:
            raise MemoryLifecycleError("installed Graphiti differs from the reviewed pin")
        if importlib.metadata.version("falkordblite") != FALKORDBLITE_VERSION:
            raise MemoryLifecycleError("installed FalkorDBLite differs from the lock")
        self.root = root.resolve()
        if self.root.is_symlink():
            raise MemoryLifecycleError("Graphiti lifecycle root cannot be a symlink")
        self.root.mkdir(parents=True, exist_ok=True)
        self._begun: set[str] = set()
        self._purged: set[str] = set()
        self._volatile_receipts: dict[
            tuple[str, str], tuple[str, LifecycleOperationReceipt]
        ] = {}
        configuration = {
            "adapter_revision": ADAPTER_REVISION,
            "backend": "falkordblite-per-scope-persistent",
            "checkpoint_semantics": "verify-native-state-never-reconstruct-v1",
            "construction": "explicit-triplet-no-extraction-llm",
            "embedding_dimensions": int(
                os.environ.get("COTCODEC_MEMORY_EMBEDDING_DIMENSIONS", "384")
            ),
            "embedding_model": os.environ.get(
                "COTCODEC_MEMORY_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"
            ),
            "embedding_revision": os.environ.get(
                "COTCODEC_MEMORY_EMBEDDING_REVISION",
                "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a",
            ),
            "graphiti_revision": GRAPHITI_REVISION,
            "graphiti_version": GRAPHITI_VERSION,
            "falkordblite_version": FALKORDBLITE_VERSION,
            "redislite_close_policy": "explicit-sync-save-and-shutdown-v1",
            "residency": "all-records-inactive-archive",
            "source_archive_sha256": GRAPHITI_SOURCE_ARCHIVE_SHA256,
            "unsupported": ["feedback", "maintain", "active-tier-promotion"],
        }
        self.receipt = LifecycleSystemReceipt(
            system_id=ADAPTER_REVISION,
            implementation_kind="oci_sidecar",
            implementation_revision=GRAPHITI_REVISION,
            configuration_sha256=sha256_text(canonical_json(configuration)),
            capabilities=(
                LifecycleCapability.APPLY,
                LifecycleCapability.QUERY,
                LifecycleCapability.CHECKPOINT,
                LifecycleCapability.RESTORE,
                LifecycleCapability.INSPECT,
                LifecycleCapability.PURGE,
            ),
            publication_ready=False,
        )

    def close(self) -> None:
        return None

    def _scope_dir(self, scope: str) -> Path:
        return self.root / _scope_sha256(scope)

    def _db_path(self, scope: str) -> Path:
        return self._scope_dir(scope) / "graphiti.rdb"

    def _journal_path(self, scope: str) -> Path:
        return self._scope_dir(scope) / "lifecycle-journal.json"

    @staticmethod
    def _empty_journal(scope: str) -> dict[str, Any]:
        return {
            "schema_version": JOURNAL_SCHEMA_VERSION,
            "scope_sha256": _scope_sha256(scope),
            "records": {},
            "commands": {},
            "pending": None,
        }

    def _load_journal(
        self, scope: str, *, create: bool = False
    ) -> dict[str, Any] | None:
        path = self._journal_path(scope)
        if not path.exists():
            if not create:
                return None
            self._scope_dir(scope).mkdir(parents=True, exist_ok=True)
            journal = self._empty_journal(scope)
            _atomic_json(path, journal)
            return journal
        if not path.is_file() or path.is_symlink():
            raise MemoryLifecycleError("Graphiti lifecycle journal is not regular")
        try:
            journal = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise MemoryLifecycleError("Graphiti lifecycle journal is invalid") from exc
        if (
            not isinstance(journal, dict)
            or journal.get("schema_version") != JOURNAL_SCHEMA_VERSION
            or journal.get("scope_sha256") != _scope_sha256(scope)
            or not isinstance(journal.get("records"), dict)
            or not isinstance(journal.get("commands"), dict)
            or "pending" not in journal
        ):
            raise MemoryLifecycleError("Graphiti lifecycle journal schema drifted")
        if journal["pending"] is not None:
            raise MemoryLifecycleError(
                "Graphiti lifecycle journal contains an ambiguous interrupted operation"
            )
        return journal

    def _persist(self, scope: str, journal: dict[str, Any]) -> None:
        _atomic_json(self._journal_path(scope), journal)

    @staticmethod
    def _logical_rows(journal: dict[str, Any] | None) -> list[dict[str, Any]]:
        if journal is None:
            return []
        return [
            {key: value for key, value in record.items() if key not in NATIVE_FIELDS}
            for _, record in sorted(journal["records"].items())
        ]

    async def _open_driver(
        self, scope: str
    ) -> tuple[AsyncFalkorDB, FalkorDriver]:
        self._scope_dir(scope).mkdir(parents=True, exist_ok=True)
        client = AsyncFalkorDB(dbfilename=str(self._db_path(scope)))
        driver = FalkorDriver(falkor_db=client, database=GRAPH_GROUP)
        await driver.build_indices_and_constraints()
        return client, driver

    async def _native_rows_async(self, scope: str) -> list[dict[str, Any]]:
        if not self._db_path(scope).exists():
            return []
        client, driver = await self._open_driver(scope)
        try:
            records, _, _ = await driver.execute_query(
                """
                MATCH (source:Entity)-[e:RELATES_TO]->(target:Entity)
                RETURN e.fact AS fact
                ORDER BY e.uuid
                """
            )
            rows: list[dict[str, Any]] = []
            for native in records:
                try:
                    fact = json.loads(native["fact"])
                except json.JSONDecodeError as exc:
                    raise MemoryLifecycleError(
                        "Graphiti native edge fact is not canonical JSON"
                    ) from exc
                if not isinstance(fact, dict):
                    raise MemoryLifecycleError("Graphiti native edge fact is malformed")
                rows.append(
                    {
                        "record_id": fact.get("record_id"),
                        "entity_id": fact.get("entity_id"),
                        "key": fact.get("key"),
                        "value": fact.get("value"),
                        "written_step": fact.get("written_step"),
                        "last_access_step": fact.get("last_access_step"),
                        "source_event_ids": fact.get("source_event_ids"),
                        "untrusted": fact.get("untrusted"),
                    }
                )
            return sorted(rows, key=lambda row: str(row["record_id"]))
        finally:
            await _close_embedded(client)

    def _native_rows(
        self, scope: str, journal: dict[str, Any] | None
    ) -> list[dict[str, Any]]:
        logical = self._logical_rows(journal)
        native = asyncio.run(self._native_rows_async(scope))
        if native != logical:
            raise MemoryLifecycleError("Graphiti native graph differs from lifecycle state")
        return native

    async def _group_filter_probe_async(self, scope: str) -> dict[str, int]:
        if not self._db_path(scope).exists():
            return {"unfiltered": 0, "literal_group_filter": 0}
        client, driver = await self._open_driver(scope)
        try:
            unfiltered, _, _ = await driver.execute_query(
                "MATCH (source:Entity)-[e:RELATES_TO]->(target:Entity) "
                "RETURN e.uuid AS uuid"
            )
            filtered, _, _ = await driver.execute_query(
                """
                MATCH (source:Entity)-[e:RELATES_TO]->(target:Entity)
                WHERE e.group_id = 'lifecycle'
                RETURN e.uuid AS uuid
                """
            )
            return {
                "unfiltered": len(unfiltered),
                "literal_group_filter": len(filtered),
            }
        finally:
            await _close_embedded(client)

    def group_filter_probe(self, scope: str) -> dict[str, int]:
        return asyncio.run(self._group_filter_probe_async(scope))

    def _roots(
        self, scope: str, journal: dict[str, Any] | None
    ) -> tuple[str, str]:
        logical = self._logical_rows(journal)
        return (
            sha256_text(canonical_json(logical)),
            sha256_text(
                canonical_json(
                    {
                        "logical_records": logical,
                        "normalized_native_records": self._native_rows(scope, journal),
                    }
                )
            ),
        )

    @staticmethod
    def _summary(journal: dict[str, Any] | None) -> LifecycleStateSummary:
        rows = GraphitiLifecyclePort._logical_rows(journal)
        return LifecycleStateSummary(
            active_record_ids=(),
            archive_record_ids=tuple(row["record_id"] for row in rows),
            active_bytes=0,
            archive_bytes=sum(len(canonical_json(row).encode()) for row in rows),
            lineage=tuple(
                (row["record_id"], tuple(row["source_event_ids"])) for row in rows
            ),
        )

    @staticmethod
    def _checkpoint(scope: str, journal: dict[str, Any]) -> LifecycleCheckpoint:
        records = tuple(
            LifecycleCheckpointRecord(
                record_id=row["record_id"],
                entity_id=row["entity_id"],
                key=row["key"],
                value=row["value"],
                written_step=row["written_step"],
                last_access_step=row["last_access_step"],
                residency="archive",
                source_event_ids=tuple(row["source_event_ids"]),
                utility=0.0,
                untrusted=row["untrusted"],
            )
            for row in GraphitiLifecyclePort._logical_rows(journal)
        )
        state_sha = sha256_text(
            canonical_json([record.model_dump(mode="json") for record in records])
        )
        payload = {
            "session_scope": scope,
            "records": [record.model_dump(mode="json") for record in records],
            "state_sha256": state_sha,
        }
        return LifecycleCheckpoint(
            **payload, checkpoint_sha256=sha256_text(canonical_json(payload))
        )

    @staticmethod
    def _checkpoint_rows(checkpoint: LifecycleCheckpoint) -> list[dict[str, Any]]:
        return [
            {
                "record_id": record.record_id,
                "entity_id": record.entity_id,
                "key": record.key,
                "value": record.value,
                "written_step": record.written_step,
                "last_access_step": record.last_access_step,
                "source_event_ids": list(record.source_event_ids),
                "untrusted": record.untrusted,
            }
            for record in checkpoint.records
        ]

    @staticmethod
    def _fact(record: dict[str, Any]) -> str:
        return canonical_json(
            {key: value for key, value in record.items() if key not in NATIVE_FIELDS}
        )

    async def _add_native_async(
        self, scope: str, record: dict[str, Any]
    ) -> int:
        client, driver = await self._open_driver(scope)
        embedder = _HttpEmbedder()
        try:
            created_at = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(
                seconds=record["written_step"]
            )
            source = EntityNode(
                uuid=record["source_node_uuid"],
                name=record["entity_id"],
                group_id=GRAPH_GROUP,
                labels=["Entity"],
                created_at=created_at,
                summary="",
                attributes={"lifecycle_entity_id": record["entity_id"]},
            )
            target = EntityNode(
                uuid=record["target_node_uuid"],
                name=record["value"],
                group_id=GRAPH_GROUP,
                labels=["Entity"],
                created_at=created_at,
                summary="",
                attributes={"lifecycle_record_id": record["record_id"]},
            )
            await source.generate_name_embedding(embedder)
            await target.generate_name_embedding(embedder)
            edge = EntityEdge(
                uuid=record["edge_uuid"],
                group_id=GRAPH_GROUP,
                source_node_uuid=source.uuid,
                target_node_uuid=target.uuid,
                name=record["key"],
                fact=self._fact(record),
                created_at=created_at,
                valid_at=created_at,
                attributes={"lifecycle_record_id": record["record_id"]},
            )
            await edge.generate_embedding(embedder)
            await source.save(driver)
            await target.save(driver)
            await edge.save(driver)
            return embedder.calls
        finally:
            await embedder.client.aclose()
            await _close_embedded(client)

    async def _delete_native_async(self, scope: str, record: dict[str, Any]) -> None:
        client, driver = await self._open_driver(scope)
        try:
            edge_uuid = str(uuid.UUID(record["edge_uuid"]))
            target_uuid = str(uuid.UUID(record["target_node_uuid"]))
            edges, _, _ = await driver.execute_query(
                "MATCH ()-[e:RELATES_TO]->() RETURN id(e) AS id, e.uuid AS uuid"
            )
            edge_ids = [row["id"] for row in edges if row.get("uuid") == edge_uuid]
            if len(edge_ids) != 1 or not isinstance(edge_ids[0], int):
                raise MemoryLifecycleError("Graphiti native edge identity drifted")
            await driver.execute_query(
                f"""
                MATCH ()-[e:RELATES_TO]->()
                WHERE id(e) = {edge_ids[0]}
                DELETE e
                """
            )
            nodes, _, _ = await driver.execute_query(
                "MATCH (n:Entity) RETURN id(n) AS id, n.uuid AS uuid"
            )
            target_ids = [row["id"] for row in nodes if row.get("uuid") == target_uuid]
            if len(target_ids) != 1 or not isinstance(target_ids[0], int):
                raise MemoryLifecycleError("Graphiti native target identity drifted")
            await driver.execute_query(
                f"""
                MATCH (n:Entity)
                WHERE id(n) = {target_ids[0]}
                DETACH DELETE n
                """
            )
        finally:
            await _close_embedded(client)

    def _add_native(self, scope: str, record: dict[str, Any]) -> int:
        return asyncio.run(self._add_native_async(scope, record))

    def _delete_native(self, scope: str, record: dict[str, Any]) -> None:
        asyncio.run(self._delete_native_async(scope, record))

    async def _query_native_async(
        self, scope: str, query: str, limit: int
    ) -> tuple[list[EntityEdge], int]:
        if not self._db_path(scope).exists():
            return [], 0
        client, driver = await self._open_driver(scope)
        embedder = _HttpEmbedder()
        graphiti = Graphiti(
            graph_driver=driver,
            llm_client=_ForbiddenLLM(),
            embedder=embedder,
            cross_encoder=_ForbiddenReranker(),
            store_raw_episode_content=False,
        )
        try:
            edges = await graphiti.search(
                query, group_ids=None, num_results=max(limit, 1)
            )
            return edges, embedder.calls
        finally:
            await embedder.client.aclose()
            await _close_embedded(client)

    def execute(self, command: LifecycleCommand) -> LifecycleOperationReceipt:
        scope = command.session_scope
        key = (scope, command.idempotency_key)
        prior_volatile = self._volatile_receipts.get(key)
        if prior_volatile is not None:
            prior_sha, receipt = prior_volatile
            if prior_sha != command.command_sha256:
                raise MemoryLifecycleError("idempotency key reused with different bytes")
            return receipt

        journal = self._load_journal(scope)
        if journal is not None:
            prior = journal["commands"].get(command.idempotency_key)
            if prior is not None:
                if prior.get("command_sha256") != command.command_sha256:
                    raise MemoryLifecycleError(
                        "idempotency key reused with different bytes"
                    )
                receipt = LifecycleOperationReceipt.model_validate(prior["receipt"])
                if command.kind == "restore" and scope not in self._begun:
                    assert command.checkpoint is not None
                    if self._logical_rows(journal) != self._checkpoint_rows(
                        command.checkpoint
                    ):
                        raise MemoryLifecycleError(
                            "restore checkpoint differs from persisted Graphiti state"
                        )
                    self._native_rows(scope, journal)
                    self._begun.add(scope)
                self._volatile_receipts[key] = (command.command_sha256, receipt)
                return receipt

        resume_after_restore = False
        if command.kind == "begin":
            if scope in self._begun or scope in self._purged or journal is not None:
                raise MemoryLifecycleError("begin cannot reuse this lifecycle session")
            journal = self._load_journal(scope, create=True)
            assert journal is not None
            self._begun.add(scope)
        elif command.kind == "restore" and scope not in self._begun:
            if journal is None:
                raise MemoryLifecycleError("restore requires persisted lifecycle state")
            resume_after_restore = True
        elif command.kind == "inspect" and scope in self._purged:
            journal = None
        else:
            if scope not in self._begun:
                raise MemoryLifecycleError("lifecycle command requires begin")
            if journal is None:
                raise MemoryLifecycleError("Graphiti lifecycle state disappeared")

        pre_logical, pre_durable = self._roots(scope, journal)
        started = time.perf_counter()
        evidence: tuple[LifecycleEvidence, ...] = ()
        checkpoint: LifecycleCheckpoint | None = None
        native_writes = 0
        native_reads = 0
        embedding_calls = 0

        if command.kind == "apply":
            assert command.event is not None and journal is not None
            event = command.event
            records = journal["records"]
            current = records.get(event.record_id)
            if event.kind in {"write", "observe"}:
                if current is not None:
                    raise MemoryLifecycleError("write cannot replace an existing record")
                record = {
                    "record_id": event.record_id,
                    "entity_id": event.entity_id,
                    "key": event.key,
                    "value": event.value,
                    "written_step": event.step,
                    "last_access_step": event.step,
                    "source_event_ids": [event.event_id],
                    "untrusted": event.untrusted,
                    "source_node_uuid": _stable_uuid("entity", event.entity_id),
                    "target_node_uuid": _stable_uuid("record", event.record_id),
                    "edge_uuid": _stable_uuid("edge", event.record_id),
                }
                journal["pending"] = {
                    "command_sha256": command.command_sha256,
                    "event_id": event.event_id,
                }
                self._persist(scope, journal)
                _crash_if_requested(command.command_id, "after-pending")
                embedding_calls = self._add_native(scope, record)
                _crash_if_requested(command.command_id, "after-native")
                records[event.record_id] = record
                native_writes = 3
            elif event.kind == "update":
                if current is None:
                    raise MemoryLifecycleError("update requires an existing record")
                if (current["entity_id"], current["key"]) != (
                    event.entity_id,
                    event.key,
                ):
                    raise MemoryLifecycleError("update entity/key differs from record")
                journal["pending"] = {
                    "command_sha256": command.command_sha256,
                    "event_id": event.event_id,
                }
                self._persist(scope, journal)
                _crash_if_requested(command.command_id, "after-pending")
                self._delete_native(scope, current)
                updated = {
                    **current,
                    "value": event.value,
                    "written_step": event.step,
                    "last_access_step": event.step,
                    "source_event_ids": [*current["source_event_ids"], event.event_id],
                }
                embedding_calls = self._add_native(scope, updated)
                _crash_if_requested(command.command_id, "after-native")
                records[event.record_id] = updated
                native_writes = 5
            elif event.kind == "delete":
                if current is None:
                    raise MemoryLifecycleError("delete requires an existing record")
                if (current["entity_id"], current["key"]) != (
                    event.entity_id,
                    event.key,
                ):
                    raise MemoryLifecycleError("delete entity/key differs from record")
                journal["pending"] = {
                    "command_sha256": command.command_sha256,
                    "event_id": event.event_id,
                }
                self._persist(scope, journal)
                _crash_if_requested(command.command_id, "after-pending")
                self._delete_native(scope, current)
                _crash_if_requested(command.command_id, "after-native")
                del records[event.record_id]
                native_writes = 2
            else:
                if current is None:
                    raise MemoryLifecycleError("access requires an existing record")
                if (current["entity_id"], current["key"]) != (
                    event.entity_id,
                    event.key,
                ):
                    raise MemoryLifecycleError("access entity/key differs from record")
                journal["pending"] = {
                    "command_sha256": command.command_sha256,
                    "event_id": event.event_id,
                }
                self._persist(scope, journal)
                self._delete_native(scope, current)
                current["last_access_step"] = event.step
                embedding_calls = self._add_native(scope, current)
                native_reads = 1
                native_writes = 5
            journal["pending"] = None
        elif command.kind == "query":
            assert command.query is not None and journal is not None
            searched, embedding_calls = asyncio.run(
                self._query_native_async(
                    scope, command.query.text, command.query.top_k
                )
            )
            selected: list[LifecycleEvidence] = []
            archive_reads = 0
            for index, edge in enumerate(searched):
                try:
                    record_id = json.loads(edge.fact)["record_id"]
                except (json.JSONDecodeError, KeyError, TypeError) as exc:
                    raise MemoryLifecycleError(
                        "Graphiti query returned an unattributed edge"
                    ) from exc
                record = journal["records"].get(record_id)
                if record is None:
                    raise MemoryLifecycleError(
                        "Graphiti query returned an untracked record"
                    )
                if archive_reads >= command.query.max_archive_reads:
                    continue
                candidate = LifecycleEvidence(
                    evidence_id=f"graphiti:{record_id}",
                    record_id=record_id,
                    text=edge.fact,
                    source_event_ids=tuple(record["source_event_ids"]),
                    prior_residency="archive",
                    score=1.0 / (index + 1),
                )
                rendered = canonical_json(
                    [entry.model_dump(mode="json") for entry in (*selected, candidate)]
                )
                if _token_estimate(rendered) > command.query.max_injected_tokens:
                    continue
                selected.append(candidate)
                archive_reads += 1
                if len(selected) >= command.query.top_k:
                    break
            evidence = tuple(selected)
            native_reads = 1
        elif command.kind == "checkpoint":
            assert journal is not None
            checkpoint = self._checkpoint(scope, journal)
        elif command.kind == "restore":
            assert journal is not None and command.checkpoint is not None
            if self._logical_rows(journal) != self._checkpoint_rows(command.checkpoint):
                raise MemoryLifecycleError(
                    "restore checkpoint differs from persisted Graphiti state"
                )
            self._native_rows(scope, journal)
            if resume_after_restore:
                self._begun.add(scope)
        elif command.kind == "purge":
            assert journal is not None
            scope_dir = self._scope_dir(scope)
            if scope_dir.parent != self.root or not scope_dir.is_dir():
                raise MemoryLifecycleError("Graphiti purge scope is invalid")
            shutil.rmtree(scope_dir)
            if scope_dir.exists():
                raise MemoryLifecycleError("Graphiti scope remains after purge")
            self._begun.remove(scope)
            self._purged.add(scope)
            for cached_key in tuple(self._volatile_receipts):
                if cached_key[0] == scope:
                    del self._volatile_receipts[cached_key]
            journal = None
            native_writes = 1
        elif command.kind in {"maintain", "feedback"}:
            raise MemoryLifecycleError(
                f"pinned Graphiti does not support lifecycle operation {command.kind}"
            )
        elif command.kind not in {"begin", "inspect"}:
            raise MemoryLifecycleError(f"unsupported lifecycle operation {command.kind}")

        post_logical, post_durable = self._roots(scope, journal)
        summary = self._summary(journal)
        rendered_evidence = canonical_json(
            [entry.model_dump(mode="json") for entry in evidence]
        )
        output_projection = canonical_json(
            {
                "checkpoint": checkpoint.model_dump(mode="json")
                if checkpoint is not None
                else None,
                "evidence": [entry.model_dump(mode="json") for entry in evidence],
                "summary": summary.model_dump(mode="json"),
            }
        )
        cost = LifecyclePhaseCost(
            phase=_phase(command.kind),
            writes=native_writes,
            reads=native_reads,
            serialized_input_bytes=len(
                canonical_json(command.model_dump(mode="json")).encode()
            ),
            serialized_output_bytes=len(output_projection.encode()),
            injected_tokens_estimate=(
                _token_estimate(rendered_evidence) if evidence else 0
            ),
            embedding_calls=embedding_calls,
            llm_calls=0,
            latency_ms=(time.perf_counter() - started) * 1000,
        )
        payload = {
            "command_id": command.command_id,
            "command_sha256": command.command_sha256,
            "pre_logical_state_sha256": pre_logical,
            "post_logical_state_sha256": post_logical,
            "pre_durable_state_sha256": pre_durable,
            "post_durable_state_sha256": post_durable,
            "evidence": [entry.model_dump(mode="json") for entry in evidence],
            "summary": summary.model_dump(mode="json"),
            "checkpoint": checkpoint.model_dump(mode="json")
            if checkpoint is not None
            else None,
            "cost": cost.model_dump(mode="json"),
        }
        receipt = _seal_operation(payload)
        self._volatile_receipts[key] = (command.command_sha256, receipt)
        if journal is not None:
            journal["commands"][command.idempotency_key] = {
                "command_sha256": command.command_sha256,
                "receipt": receipt.model_dump(mode="json"),
            }
            self._persist(scope, journal)
        return receipt


def _handle(line: str, port: GraphitiLifecyclePort) -> tuple[str, bool]:
    operation = "unknown"
    try:
        envelope = json.loads(line)
        if not isinstance(envelope, dict):
            raise ValueError("request envelope must be an object")
        if envelope.get("protocol") != LIFECYCLE_PROTOCOL_VERSION:
            raise ValueError("unsupported protocol")
        operation = envelope.get("operation")
        payload = envelope.get("payload", {})
        if not isinstance(operation, str) or not isinstance(payload, dict):
            raise ValueError("invalid lifecycle request envelope")
        if operation == "handshake":
            result = {"receipt": port.receipt.model_dump(mode="json")}
        elif operation == "execute":
            command = LifecycleCommand.model_validate(payload.get("command"))
            result = {"receipt": port.execute(command).model_dump(mode="json")}
        elif operation == "shutdown":
            port.close()
            result = {"shutdown": True}
        else:
            raise ValueError(f"unsupported operation: {operation}")
    except Exception as exc:
        return _response(operation, ok=False, result={"error": str(exc)}), False
    return _response(operation, ok=True, result=result), operation == "shutdown"


def main() -> int:
    configured_root = os.environ.get("COTCODEC_MEMORY_STATE_ROOT")
    if not configured_root:
        print(
            _response(
                "handshake",
                ok=False,
                result={"error": "COTCODEC_MEMORY_STATE_ROOT is required"},
            ),
            flush=True,
        )
        return 2
    root = Path(configured_root)
    if not root.is_absolute():
        print(
            _response(
                "handshake",
                ok=False,
                result={"error": "COTCODEC_MEMORY_STATE_ROOT must be absolute"},
            ),
            flush=True,
        )
        return 2
    os.environ["EMBEDDING_DIM"] = os.environ.get(
        "COTCODEC_MEMORY_EMBEDDING_DIMENSIONS", "384"
    )
    port = GraphitiLifecyclePort(root)
    try:
        for line in sys.stdin:
            if not line.strip():
                continue
            response, shutdown = _handle(line, port)
            print(response, flush=True)
            if shutdown:
                return 0
    finally:
        port.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
