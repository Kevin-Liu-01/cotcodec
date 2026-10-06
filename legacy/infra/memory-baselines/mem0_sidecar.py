#!/usr/bin/env python3
"""Pinned Mem0 raw-retrieval adapter for the memory-system-v1 wire protocol."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.metadata
import json
import os
import shutil
import sys
import tempfile
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

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

MEM0_REVISION = "71f2ebefa3494da21550fb525216818776cde67f"
MEM0_VERSION = "2.0.18"
MEM0_SOURCE_ARCHIVE_SHA256 = "c577ecf9a460b0fa581032037ccbfd887f7a7d0afa0fc091d13fd8b692089b12"


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"{name} is required for Mem0 select")
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
        part
        for part in os.environ.get(
            "COTCODEC_MEMORY_MODEL_RECEIPT_SHA256S", ""
        ).split(",")
        if part
    )
    if source_archive is not None and source_archive != MEM0_SOURCE_ARCHIVE_SHA256:
        raise ValueError("Mem0 source archive receipt differs from the reviewed source")
    source_context_path = Path(
        os.environ.get(
            "COTCODEC_MEMORY_SOURCE_CONTEXT_RECEIPT",
            "/opt/mem0-source/.cotcodec-source-context.json",
        )
    )
    source_context_verified = False
    if source_context_path.is_file():
        source_context = json.loads(source_context_path.read_text(encoding="utf-8"))
        expected = {
            "system_id": "mem0",
            "revision": MEM0_REVISION,
            "source_archive_sha256": MEM0_SOURCE_ARCHIVE_SHA256,
        }
        if any(source_context.get(key) != value for key, value in expected.items()):
            raise ValueError("Mem0 source context receipt differs from reviewed source")
        source_context_verified = True
    publication_ready = bool(
        source_archive and image_digest and model_receipts and source_context_verified
    )
    if os.environ.get("COTCODEC_PUBLICATION_MODE") == "1" and not publication_ready:
        raise ValueError("publication mode requires source, image, and model receipts")
    config = {
        "adapter": "mem0-raw-retrieval-v2",
        "backend": "qdrant-local-persistent",
        "embedding_base_url": embedding_base_url,
        "embedding_model": embedding_model,
        "embedding_revision": embedding_revision,
        "embedding_dimensions": dimensions,
        "source_context_verified": source_context_verified,
        "infer": False,
        "rerank": False,
    }
    return MemorySystemReceipt(
        system_id="mem0-raw-retrieval-v2",
        implementation_kind="oci_sidecar",
        implementation_revision=MEM0_REVISION,
        configuration_sha256=sha256_text(canonical_json(config)),
        backend_id="qdrant-local-persistent",
        source_archive_sha256=source_archive,
        image_digest=image_digest,
        model_receipt_sha256s=model_receipts,
        publication_ready=publication_ready,
    )


def _response(operation: str, *, ok: bool, result: Mapping[str, Any]) -> str:
    payload: dict[str, Any] = {
        "protocol": "memory-system-v1",
        "operation": operation,
        "ok": ok,
        "result": dict(result),
    }
    return canonical_json(payload)


def _content(event: Any) -> str:
    return canonical_json(
        {
            "entity": event.entity_id,
            "key": event.key,
            "value": event.value,
            "step": event.step,
            "untrusted": event.untrusted,
        }
    )


def _extract_source_id(result: Mapping[str, Any]) -> str:
    metadata = result.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("Mem0 result omitted source metadata")
    source_id = metadata.get("source_event_id")
    if not isinstance(source_id, str) or not source_id:
        raise ValueError("Mem0 result omitted source_event_id")
    return source_id


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    encoded = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    with temporary.open("xb", buffering=0) as handle:
        handle.write(encoded)
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    _fsync_directory(path.parent)


def _scope_sha256(session_scope: str) -> str:
    if not session_scope:
        raise ValueError("session_scope must be non-empty")
    return hashlib.sha256(session_scope.encode()).hexdigest()


def _close_memory(memory: Any) -> None:
    with contextlib.suppress(Exception):
        memory.db.close()
    client = getattr(getattr(memory, "vector_store", None), "client", None)
    close = getattr(client, "close", None)
    if callable(close):
        with contextlib.suppress(Exception):
            close()


def _memory_results(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        value = value.get("results", [])
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError("Mem0 returned malformed records")
    return value


class Mem0State:
    """Persistent, session-scoped Mem0 state with an idempotent event journal."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        _fsync_directory(self.root.parent)
        self._memories: dict[str, Any] = {}

    def _scope_dir(self, session_scope: str) -> Path:
        return self.root / f"scope-{_scope_sha256(session_scope)}"

    def _config(self, scope_dir: Path) -> dict[str, Any]:
        embedding_base_url = _required_env("COTCODEC_MEMORY_EMBEDDING_BASE_URL")
        embedding_model = os.environ.get(
            "COTCODEC_MEMORY_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"
        )
        dimensions = int(os.environ.get("COTCODEC_MEMORY_EMBEDDING_DIMENSIONS", "384"))
        return {
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "collection_name": "cotcodec_memory",
                    "embedding_model_dims": dimensions,
                    "path": str(scope_dir / "qdrant"),
                    "on_disk": True,
                },
            },
            "embedder": {
                "provider": "openai",
                "config": {
                    "model": embedding_model,
                    "api_key": os.environ.get(
                        "COTCODEC_MEMORY_EMBEDDING_API_KEY", "local"
                    ),
                    "openai_base_url": embedding_base_url,
                },
            },
            "llm": {
                "provider": "openai",
                "config": {
                    "model": "unused-in-infer-false",
                    "api_key": "unused",
                    "openai_base_url": "http://127.0.0.1:1/v1",
                },
            },
            "history_db_path": str(scope_dir / "history.db"),
        }

    def _open(self, session_scope: str) -> tuple[Any, Path]:
        scope_hash = _scope_sha256(session_scope)
        scope_dir = self._scope_dir(session_scope)
        memory = self._memories.get(scope_hash)
        if memory is not None:
            return memory, scope_dir
        scope_dir.mkdir(parents=True, exist_ok=True)
        marker = scope_dir / "scope.json"
        expected = {"schema_version": 1, "scope_sha256": scope_hash}
        if marker.exists():
            if json.loads(marker.read_text(encoding="utf-8")) != expected:
                raise ValueError("Mem0 scope marker differs from the requested session")
        else:
            _atomic_json(marker, expected)
        from mem0 import Memory

        with contextlib.redirect_stdout(sys.stderr):
            memory = Memory.from_config(self._config(scope_dir))
        self._memories[scope_hash] = memory
        return memory, scope_dir

    @staticmethod
    def _empty_journal(scope_hash: str) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "scope_sha256": scope_hash,
            "prefix_event_ids": [],
            "events": {},
            "active_by_key": {},
        }

    def _load_journal(self, scope_dir: Path, scope_hash: str) -> dict[str, Any]:
        path = scope_dir / "event-journal.json"
        if not path.exists():
            journal = self._empty_journal(scope_hash)
            _atomic_json(path, journal)
            return journal
        journal = json.loads(path.read_text(encoding="utf-8"))
        if (
            not isinstance(journal, dict)
            or journal.get("schema_version") != 1
            or journal.get("scope_sha256") != scope_hash
        ):
            raise ValueError("Mem0 event journal is invalid")
        return journal

    @staticmethod
    def _all_records(memory: Any, session_scope: str) -> list[dict[str, Any]]:
        return _memory_results(
            memory.get_all(filters={"user_id": session_scope}, top_k=100_000)
        )

    def select(self, request: MemorySystemRequest) -> tuple[list[dict[str, Any]], int]:
        memory, scope_dir = self._open(request.session_scope)
        scope_hash = _scope_sha256(request.session_scope)
        journal_path = scope_dir / "event-journal.json"
        journal = self._load_journal(scope_dir, scope_hash)
        requested_ids = [event.source_event_id for event in request.events]
        committed_prefix = list(journal["prefix_event_ids"])
        if requested_ids[: len(committed_prefix)] != committed_prefix:
            raise ValueError(
                "session prefix diverged from persistent state; use an isolated scope"
            )
        for event in request.events[: len(committed_prefix)]:
            entry = journal["events"].get(event.source_event_id)
            event_digest = sha256_text(
                canonical_json(event.model_dump(mode="json"))
            )
            if (
                not isinstance(entry, dict)
                or entry.get("status") != "committed"
                or entry.get("event_sha256") != event_digest
            ):
                raise ValueError(
                    "committed source event was reused with different bytes"
                )
        embedding_calls = 0
        for event in request.events[len(committed_prefix) :]:
            event_payload = event.model_dump(mode="json")
            event_digest = sha256_text(canonical_json(event_payload))
            key = canonical_json([event.entity_id, event.key])
            entry = journal["events"].get(event.source_event_id)
            if entry is not None and entry.get("event_sha256") != event_digest:
                raise ValueError("source event ID was reused with different bytes")
            previous_ids = list(journal["active_by_key"].get(key, []))
            if entry is None:
                entry = {
                    "event_sha256": event_digest,
                    "status": "pending",
                    "kind": event.kind,
                    "key_sha256": sha256_text(key),
                    "previous_memory_ids": previous_ids,
                    "memory_ids": [],
                }
                journal["events"][event.source_event_id] = entry
                _atomic_json(journal_path, journal)
            native = self._all_records(memory, request.session_scope)
            native_ids = {
                str(item["id"])
                for item in native
                if isinstance(item.get("id"), str)
            }
            if event.kind in {"update", "delete"}:
                for memory_id in entry["previous_memory_ids"]:
                    if memory_id in native_ids:
                        memory.delete(memory_id)
            memory_ids: list[str] = []
            if event.kind in {"write", "update", "observe"} and event.value is not None:
                native = self._all_records(memory, request.session_scope)
                memory_ids = [
                    str(item["id"])
                    for item in native
                    if isinstance(item.get("id"), str)
                    and isinstance(item.get("metadata"), dict)
                    and item["metadata"].get("source_event_id")
                    == event.source_event_id
                ]
                if not memory_ids:
                    added = memory.add(
                        _content(event),
                        user_id=request.session_scope,
                        metadata={
                            "source_event_id": event.source_event_id,
                            "entity_id": event.entity_id,
                            "key": event.key,
                            "step": event.step,
                        },
                        infer=False,
                    )
                    embedding_calls += 1
                    memory_ids = [
                        item["id"]
                        for item in _memory_results(added)
                        if isinstance(item.get("id"), str)
                    ]
            if event.kind == "delete":
                journal["active_by_key"].pop(key, None)
            elif event.kind == "update":
                journal["active_by_key"][key] = memory_ids
            elif event.kind in {"write", "observe"}:
                journal["active_by_key"][key] = previous_ids + memory_ids
            entry["memory_ids"] = memory_ids
            entry["status"] = "committed"
            journal["prefix_event_ids"].append(event.source_event_id)
            _atomic_json(journal_path, journal)
        searched = memory.search(
            request.query,
            top_k=request.budget.retrieval_top_k,
            filters={"user_id": request.session_scope},
            threshold=0.0,
            rerank=False,
        )
        return _memory_results(searched), embedding_calls + 1

    def inspect(self, session_scope: str) -> dict[str, Any]:
        scope_hash = _scope_sha256(session_scope)
        scope_dir = self._scope_dir(session_scope)
        if not scope_dir.exists():
            return {
                "scope_sha256": scope_hash,
                "state_exists": False,
                "native_memory_count": 0,
                "committed_event_count": 0,
            }
        memory, _ = self._open(session_scope)
        records = self._all_records(memory, session_scope)
        journal = self._load_journal(scope_dir, scope_hash)
        return {
            "scope_sha256": scope_hash,
            "state_exists": True,
            "native_memory_count": len(records),
            "committed_event_count": sum(
                entry.get("status") == "committed"
                for entry in journal["events"].values()
            ),
            "journal_sha256": sha256_text(canonical_json(journal)),
        }

    def purge(self, session_scope: str) -> dict[str, Any]:
        scope_hash = _scope_sha256(session_scope)
        scope_dir = self._scope_dir(session_scope)
        memory = self._memories.pop(scope_hash, None)
        if scope_dir.exists():
            if memory is None:
                memory, _ = self._open(session_scope)
                self._memories.pop(scope_hash, None)
            with contextlib.redirect_stdout(sys.stderr):
                memory.delete_all(user_id=session_scope)
                memory.reset()
            if self._all_records(memory, session_scope):
                raise ValueError("Mem0 native records remain after reset")
            _close_memory(memory)
            shutil.rmtree(scope_dir)
        if scope_dir.exists():
            raise ValueError("Mem0 scoped state directory remains after purge")
        return {
            "purged": True,
            "scope_sha256": scope_hash,
            "state_dir_removed": True,
            "native_memory_count_after": 0,
            "journal_removed": True,
        }

    def close(self) -> None:
        for memory in self._memories.values():
            _close_memory(memory)
        self._memories.clear()


def _selection(request: MemorySystemRequest, state: Mem0State) -> MemorySelection:
    os.environ["MEM0_TELEMETRY"] = "false"
    if importlib.metadata.version("mem0ai") != MEM0_VERSION:
        raise ValueError("installed Mem0 package version differs from the reviewed source")

    started = time.perf_counter()
    with contextlib.redirect_stdout(sys.stderr):
        searched, embedding_calls = state.select(request)

    evidence_items: list[MemoryEvidence] = []
    for item in searched:
        text = str(item["memory"])
        source_id = _extract_source_id(item)
        evidence_items.append(
            MemoryEvidence(
                evidence_id="mem0:" + sha256_text(f"{source_id}\0{text}")[:24],
                text=text,
                source_record_ids=(source_id,),
                score=float(item.get("score") or 0.0),
            )
        )
    evidence = tuple(evidence_items)
    input_json = canonical_json(request.model_dump(mode="json"))
    output_json = canonical_json([item.model_dump(mode="json") for item in evidence])
    injected_json = canonical_json(
        [{"id": item.evidence_id, "text": item.text} for item in evidence]
    )
    costs = MemoryCostLedger(
        writes=sum(
            event.kind in {"write", "update", "delete", "observe"}
            for event in request.events
        ),
        reads=1,
        serialized_input_bytes=len(input_json.encode()),
        serialized_output_bytes=len(output_json.encode()),
        injected_tokens_estimate=(len(injected_json.encode()) + 3) // 4,
        embedding_calls=embedding_calls,
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


def _handle(line: str, state: Mem0State) -> tuple[str, bool, int]:
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
            result = {"selection": _selection(request, state).model_dump(mode="json")}
        elif operation == "inspect":
            if not isinstance(payload.get("session_scope"), str):
                raise ValueError("inspect requires session_scope")
            result = state.inspect(payload["session_scope"])
        elif operation == "purge":
            if not isinstance(payload.get("session_scope"), str):
                raise ValueError("purge requires session_scope")
            result = state.purge(payload["session_scope"])
        elif operation == "shutdown":
            state.close()
            result = {"shutdown": True}
        else:
            raise ValueError(f"unsupported operation: {operation}")
    except Exception as exc:
        operation = locals().get("operation", "unknown")
        return _response(operation, ok=False, result={"error": str(exc)}), False, 2
    return _response(operation, ok=True, result=result), operation == "shutdown", 0


def main() -> int:
    os.environ["MEM0_TELEMETRY"] = "false"
    persistent = os.environ.get("COTCODEC_MEMORY_PERSISTENT_PROTOCOL") == "1"
    configured_root = os.environ.get("COTCODEC_MEMORY_STATE_ROOT")
    temporary: tempfile.TemporaryDirectory[str] | None = None
    if configured_root is None:
        if persistent:
            print(
                _response(
                    "handshake",
                    ok=False,
                    result={"error": "COTCODEC_MEMORY_STATE_ROOT is required"},
                )
            )
            return 2
        temporary = tempfile.TemporaryDirectory(prefix="cotcodec-mem0-")
        configured_root = temporary.name
    state_root = Path(configured_root)
    if not state_root.is_absolute():
        print(
            _response(
                "handshake",
                ok=False,
                result={"error": "COTCODEC_MEMORY_STATE_ROOT must be absolute"},
            )
        )
        return 2
    state_root.mkdir(parents=True, exist_ok=True)
    # The contained runtime deliberately supplies no passwd entry or inherited
    # HOME to sidecars.  Mem0 otherwise leaves expanduser("~") unresolved and
    # tries to create a literal `~/.mem0` beneath the read-only worktree.
    os.environ["HOME"] = str(state_root)
    os.environ["MEM0_DIR"] = str(state_root / ".mem0-runtime")
    state = Mem0State(state_root)
    try:
        for line in sys.stdin:
            if not line.strip():
                continue
            response, shutdown, returncode = _handle(line, state)
            print(response, flush=True)
            if returncode or shutdown or not persistent:
                return returncode
        return 0
    finally:
        state.close()
        if temporary is not None:
            temporary.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
