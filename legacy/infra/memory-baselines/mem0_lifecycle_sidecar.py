#!/usr/bin/env python3
"""Expose pinned Mem0 through the additive ``memory-lifecycle-v1`` protocol.

Mem0 is treated as a persistent inactive archive.  This adapter deliberately
does not advertise active-tier maintenance or outcome feedback: the pinned
native API does not implement either mechanism.  Checkpoint restore verifies
already-persisted native state; it never reconstructs a backend from the
checkpoint and thereby hides a restart failure.
"""

from __future__ import annotations

import contextlib
import importlib.metadata
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SIDECAR_ROOT = Path(__file__).resolve().parent
for import_root in (PROJECT_ROOT, SIDECAR_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from mem0_sidecar import (  # noqa: E402
    MEM0_REVISION,
    MEM0_SOURCE_ARCHIVE_SHA256,
    MEM0_VERSION,
    Mem0State,
    _atomic_json,
    _memory_results,
    _scope_sha256,
)
from mem0_sidecar import (  # noqa: E402
    _receipt as memory_system_receipt,
)

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

ADAPTER_REVISION = "mem0-native-lifecycle-v1"
JOURNAL_SCHEMA_VERSION = 1


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


def _crash_if_requested(command_id: str, point: str) -> None:
    """Deterministic doctor hook; never enabled in a normal adapter run."""

    requested = os.environ.get("COTCODEC_MEM0_LIFECYCLE_CRASH_HOOK")
    if requested == f"{command_id}:{point}":
        os._exit(86)


class Mem0LifecyclePort:
    """Persistent task-blind lifecycle port over Mem0's native local backend."""

    def __init__(self, root: Path) -> None:
        if importlib.metadata.version("mem0ai") != MEM0_VERSION:
            raise MemoryLifecycleError("installed Mem0 differs from the reviewed pin")
        self.root = root.resolve()
        self.state = Mem0State(self.root)
        self._begun: set[str] = set()
        self._purged: set[str] = set()
        self._volatile_receipts: dict[
            tuple[str, str], tuple[str, LifecycleOperationReceipt]
        ] = {}
        base = memory_system_receipt()
        configuration = {
            "adapter_revision": ADAPTER_REVISION,
            "backend": "qdrant-local-persistent",
            "checkpoint_semantics": "verify-native-state-never-reconstruct-v1",
            # Bind the embedding semantics, not the loopback server's ephemeral
            # TCP port.  The imported v1 receipt above still validates the
            # reviewed source context and the live Mem0 configuration.
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
            "infer": False,
            "memory_revision": MEM0_REVISION,
            "memory_version": MEM0_VERSION,
            "residency": "all-records-inactive-archive",
            "source_archive_sha256": MEM0_SOURCE_ARCHIVE_SHA256,
            "source_context_verified": base.configuration_sha256 is not None,
            "unsupported": ["feedback", "maintain", "active-tier-promotion"],
        }
        self.receipt = LifecycleSystemReceipt(
            system_id=ADAPTER_REVISION,
            implementation_kind="oci_sidecar",
            implementation_revision=MEM0_REVISION,
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
        self.state.close()

    def _scope_dir(self, scope: str) -> Path:
        return self.state._scope_dir(scope)  # noqa: SLF001

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
            raise MemoryLifecycleError("Mem0 lifecycle journal is not a regular file")
        try:
            journal = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise MemoryLifecycleError("Mem0 lifecycle journal is invalid") from exc
        if (
            not isinstance(journal, dict)
            or journal.get("schema_version") != JOURNAL_SCHEMA_VERSION
            or journal.get("scope_sha256") != _scope_sha256(scope)
            or not isinstance(journal.get("records"), dict)
            or not isinstance(journal.get("commands"), dict)
            or "pending" not in journal
        ):
            raise MemoryLifecycleError("Mem0 lifecycle journal schema drifted")
        if journal["pending"] is not None:
            raise MemoryLifecycleError(
                "Mem0 lifecycle journal contains an ambiguous interrupted operation"
            )
        return journal

    def _persist(self, scope: str, journal: dict[str, Any]) -> None:
        _atomic_json(self._journal_path(scope), journal)

    @staticmethod
    def _logical_rows(journal: dict[str, Any] | None) -> list[dict[str, Any]]:
        if journal is None:
            return []
        return [
            {
                key: value
                for key, value in record.items()
                if key != "native_memory_ids"
            }
            for _, record in sorted(journal["records"].items())
        ]

    def _native_rows(
        self, scope: str, journal: dict[str, Any] | None
    ) -> list[dict[str, Any]]:
        if journal is None:
            return []
        memory, _ = self.state._open(scope)  # noqa: SLF001
        native = self.state._all_records(memory, scope)  # noqa: SLF001
        rows: list[dict[str, Any]] = []
        for item in native:
            metadata = item.get("metadata")
            if not isinstance(metadata, dict):
                raise MemoryLifecycleError("Mem0 native record omitted metadata")
            record_id = metadata.get("lifecycle_record_id")
            lineage_json = metadata.get("source_event_ids_json")
            if not isinstance(record_id, str) or not isinstance(lineage_json, str):
                raise MemoryLifecycleError("Mem0 native record omitted lifecycle lineage")
            try:
                lineage = json.loads(lineage_json)
            except json.JSONDecodeError as exc:
                raise MemoryLifecycleError("Mem0 native lineage is malformed") from exc
            if not isinstance(lineage, list) or not all(
                isinstance(item_id, str) for item_id in lineage
            ):
                raise MemoryLifecycleError("Mem0 native lineage is malformed")
            rows.append(
                {
                    "record_id": record_id,
                    "memory": item.get("memory"),
                    "entity_id": metadata.get("entity_id"),
                    "key": metadata.get("key"),
                    "source_event_ids": lineage,
                }
            )
        rows.sort(key=lambda row: row["record_id"])
        expected = {
            row["record_id"]: row for row in self._logical_rows(journal)
        }
        native_ids = [row["record_id"] for row in rows]
        if len(rows) != len(expected):
            raise MemoryLifecycleError("Mem0 native and lifecycle record counts differ")
        if len(native_ids) != len(set(native_ids)) or set(native_ids) != set(expected):
            raise MemoryLifecycleError(
                "Mem0 native record IDs differ from lifecycle state"
            )
        for row in rows:
            logical = expected.get(row["record_id"])
            if logical is None:
                raise MemoryLifecycleError("Mem0 returned an untracked native record")
            expected_memory = canonical_json(
                {
                    "entity": logical["entity_id"],
                    "key": logical["key"],
                    "value": logical["value"],
                    "untrusted": logical["untrusted"],
                }
            )
            if (
                row["memory"] != expected_memory
                or row["entity_id"] != logical["entity_id"]
                or row["key"] != logical["key"]
                or row["source_event_ids"] != logical["source_event_ids"]
            ):
                raise MemoryLifecycleError("Mem0 native record differs from lifecycle state")
        return rows

    def _roots(
        self, scope: str, journal: dict[str, Any] | None
    ) -> tuple[str, str]:
        logical_rows = self._logical_rows(journal)
        logical = sha256_text(canonical_json(logical_rows))
        durable = sha256_text(
            canonical_json(
                {
                    "logical_records": logical_rows,
                    "normalized_native_records": self._native_rows(scope, journal),
                }
            )
        )
        return logical, durable

    @staticmethod
    def _summary(journal: dict[str, Any] | None) -> LifecycleStateSummary:
        rows = Mem0LifecyclePort._logical_rows(journal)
        archive_ids = tuple(row["record_id"] for row in rows)
        return LifecycleStateSummary(
            active_record_ids=(),
            archive_record_ids=archive_ids,
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
            for row in Mem0LifecyclePort._logical_rows(journal)
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
            **payload,
            checkpoint_sha256=sha256_text(canonical_json(payload)),
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

    def _add_native(
        self, scope: str, record: dict[str, Any]
    ) -> list[str]:
        memory, _ = self.state._open(scope)  # noqa: SLF001
        content = canonical_json(
            {
                "entity": record["entity_id"],
                "key": record["key"],
                "value": record["value"],
                "untrusted": record["untrusted"],
            }
        )
        with contextlib.redirect_stdout(sys.stderr):
            added = memory.add(
                content,
                user_id=scope,
                metadata={
                    "source_event_id": record["source_event_ids"][-1],
                    "source_event_ids_json": canonical_json(record["source_event_ids"]),
                    "lifecycle_record_id": record["record_id"],
                    "entity_id": record["entity_id"],
                    "key": record["key"],
                    "step": record["written_step"],
                },
                infer=False,
            )
        ids = [
            item["id"]
            for item in _memory_results(added)
            if isinstance(item.get("id"), str)
        ]
        if not ids:
            raise MemoryLifecycleError("Mem0 add returned no native record ID")
        return ids

    def _delete_native(self, scope: str, record: dict[str, Any]) -> int:
        memory, _ = self.state._open(scope)  # noqa: SLF001
        writes = 0
        for memory_id in record["native_memory_ids"]:
            with contextlib.redirect_stdout(sys.stderr):
                memory.delete(memory_id)
            writes += 1
        return writes

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
                            "restore checkpoint differs from already-persisted Mem0 state"
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
                raise MemoryLifecycleError("Mem0 lifecycle state disappeared")

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
                    "native_memory_ids": [],
                }
                journal["pending"] = {
                    "command_sha256": command.command_sha256,
                    "event_id": event.event_id,
                }
                self._persist(scope, journal)
                _crash_if_requested(command.command_id, "after-pending")
                record["native_memory_ids"] = self._add_native(scope, record)
                _crash_if_requested(command.command_id, "after-native")
                native_writes = len(record["native_memory_ids"])
                embedding_calls = 1
                records[event.record_id] = record
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
                native_writes += self._delete_native(scope, current)
                updated = {
                    **current,
                    "value": event.value,
                    "written_step": event.step,
                    "last_access_step": event.step,
                    "source_event_ids": [*current["source_event_ids"], event.event_id],
                    "native_memory_ids": [],
                }
                updated["native_memory_ids"] = self._add_native(scope, updated)
                _crash_if_requested(command.command_id, "after-native")
                native_writes += len(updated["native_memory_ids"])
                embedding_calls = 1
                records[event.record_id] = updated
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
                native_writes = self._delete_native(scope, current)
                _crash_if_requested(command.command_id, "after-native")
                del records[event.record_id]
            else:
                if current is None:
                    raise MemoryLifecycleError("access requires an existing record")
                if (current["entity_id"], current["key"]) != (
                    event.entity_id,
                    event.key,
                ):
                    raise MemoryLifecycleError("access entity/key differs from record")
                current["last_access_step"] = event.step
                native_reads = 1
            journal["pending"] = None
        elif command.kind == "query":
            assert command.query is not None and journal is not None
            memory, _ = self.state._open(scope)  # noqa: SLF001
            with contextlib.redirect_stdout(sys.stderr):
                searched = _memory_results(
                    memory.search(
                        command.query.text,
                        top_k=max(command.query.top_k, 1),
                        filters={"user_id": scope},
                        threshold=0.0,
                        rerank=False,
                    )
                )
            selected: list[LifecycleEvidence] = []
            archive_reads = 0
            for item in searched:
                metadata = item.get("metadata")
                if not isinstance(metadata, dict):
                    raise MemoryLifecycleError("Mem0 query result omitted metadata")
                record_id = metadata.get("lifecycle_record_id")
                if not isinstance(record_id, str):
                    raise MemoryLifecycleError("Mem0 query result omitted record ID")
                record = journal["records"].get(record_id)
                if record is None:
                    raise MemoryLifecycleError("Mem0 query returned an untracked record")
                if archive_reads >= command.query.max_archive_reads:
                    continue
                candidate = LifecycleEvidence(
                    evidence_id=f"mem0:{record_id}",
                    record_id=record_id,
                    text=str(item["memory"]),
                    source_event_ids=tuple(record["source_event_ids"]),
                    prior_residency="archive",
                    score=float(item.get("score") or 0.0),
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
            embedding_calls = 1
        elif command.kind == "checkpoint":
            assert journal is not None
            checkpoint = self._checkpoint(scope, journal)
        elif command.kind == "restore":
            assert journal is not None and command.checkpoint is not None
            if self._logical_rows(journal) != self._checkpoint_rows(command.checkpoint):
                raise MemoryLifecycleError(
                    "restore checkpoint differs from already-persisted Mem0 state"
                )
            self._native_rows(scope, journal)
            if resume_after_restore:
                self._begun.add(scope)
        elif command.kind == "purge":
            assert journal is not None
            self.state.purge(scope)
            self._begun.remove(scope)
            self._purged.add(scope)
            for cached_key in tuple(self._volatile_receipts):
                if cached_key[0] == scope:
                    del self._volatile_receipts[cached_key]
            journal = None
            native_writes = 1
        elif command.kind in {"maintain", "feedback"}:
            raise MemoryLifecycleError(
                f"pinned Mem0 does not support lifecycle operation {command.kind}"
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


def _handle(line: str, port: Mem0LifecyclePort) -> tuple[str, bool]:
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
    os.environ["MEM0_TELEMETRY"] = "false"
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
    root.mkdir(parents=True, exist_ok=True)
    os.environ["HOME"] = str(root)
    os.environ["MEM0_DIR"] = str(root / ".mem0-runtime")
    port = Mem0LifecyclePort(root)
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
