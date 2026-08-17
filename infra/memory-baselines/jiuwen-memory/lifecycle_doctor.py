#!/usr/bin/env python3
"""Exercise JiuwenMemory's file backend across one fresh-process restart."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import TypeAlias

from jiuwen_memory.foundation.store.base_memory_index import MemoryDoc
from jiuwen_memory.foundation.store.index.file_index.file_memory_index import (
    FileMemoryIndex,
)
from jiuwen_memory.memory_core.migration.migrator.index_version_migrator import (
    IndexVersionMigrator,
)
from jiuwen_memory.memory_core.migration.operation.base_operation import (
    OperationMetadata,
)
from jiuwen_memory.memory_core.migration.operation.operations import (
    TransformMemoryDocFieldOperation,
)

JSONPrimitive: TypeAlias = None | bool | int | float | str
JSONValue: TypeAlias = JSONPrimitive | list["JSONValue"] | dict[str, "JSONValue"]
JSONObject: TypeAlias = dict[str, JSONValue]
MARKER = "COTCODEC_JIUWEN_PHASE="
STATE_ROOT = Path("/state")
FIXED_TIME = datetime(2026, 8, 17, 10, 0, tzinfo=UTC)
SHARED_ID = "shared-memory-id"
CANARIES = {
    "unique_a": "JIUWEN_UNIQUE_A_7f31c9d28a8846f09b6c",
    "shared_a": "JIUWEN_SHARED_A_66fbc27cfa014f1cb838",
    "unique_b": "JIUWEN_UNIQUE_B_91a4e6dc397c45fa9ae2",
    "shared_b": "JIUWEN_SHARED_B_9d45a763a337481ebbd5",
}


class DeterministicEmbedding:
    """Provide deterministic local vectors without model or provider calls."""

    @staticmethod
    def _vector(text: str) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        values = [
            float(int.from_bytes(digest[index : index + 2], "big")) for index in range(0, 16, 2)
        ]
        norm = sum(value * value for value in values) ** 0.5
        return [value / norm for value in values]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed documents deterministically.

        Args:
            texts: Document texts.

        Returns:
            Eight-dimensional vectors.

        """
        return [self._vector(text) for text in texts]

    async def embed_query(self, text: str) -> list[float]:
        """Embed one query deterministically.

        Args:
            text: Query text.

        Returns:
            Eight-dimensional vector.

        """
        return self._vector(text)


def _memory(memory_id: str, text: str) -> MemoryDoc:
    return MemoryDoc(
        id=memory_id,
        text=text,
        type="note",
        timestamp=FIXED_TIME,
        fields={"migration_count": 0},
    )


def _migration() -> TransformMemoryDocFieldOperation:
    return TransformMemoryDocFieldOperation(
        metadata=OperationMetadata(schema_version=1, description="increment marker"),
        field_name="migration_count",
        transform_func=lambda value: int(value) + 1,
    )


async def _documents(index: FileMemoryIndex, user_id: str, scope_id: str) -> list[MemoryDoc]:
    return await index.list_memories(user_id=user_id, scope_id=scope_id, limit=100)


def _ids(documents: list[MemoryDoc]) -> set[str]:
    return {document.id for document in documents}


def _migration_count(document: MemoryDoc | None) -> int | None:
    if document is None:
        return None
    value = document.fields.get("migration_count")
    return value if isinstance(value, int) else None


def _close(index: FileMemoryIndex) -> None:
    index.stop_watcher()
    index.vec_index.close()


def _validate_checks(checks: dict[str, bool], diagnostics: JSONObject | None = None) -> None:
    failed = sorted(name for name, passed in checks.items() if not passed)
    if failed:
        detail = json.dumps(diagnostics or {}, sort_keys=True, separators=(",", ":"))
        raise RuntimeError(f"JiuwenMemory lifecycle checks failed: {failed}; {detail}")


async def _phase_one() -> JSONObject:
    if any(STATE_ROOT.iterdir()):
        raise RuntimeError("phase one requires an empty state volume")
    index = FileMemoryIndex(str(STATE_ROOT), DeterministicEmbedding())
    await index.add_memories(
        "user-a",
        "scope-a",
        [
            _memory("unique-a", CANARIES["unique_a"]),
            _memory(SHARED_ID, CANARIES["shared_a"]),
        ],
    )
    await index.add_memories(
        "user-b",
        "scope-b",
        [
            _memory("unique-b", CANARIES["unique_b"]),
            _memory(SHARED_ID, CANARIES["shared_b"]),
        ],
    )
    documents_a = await _documents(index, "user-a", "scope-a")
    documents_b = await _documents(index, "user-b", "scope-b")
    shared_a = await index.get_by_id("user-a", "scope-a", SHARED_ID)
    shared_b = await index.get_by_id("user-b", "scope-b", SHARED_ID)
    chunk_row = index.vec_index.conn.execute(
        "SELECT user_id, scope_id, text FROM chunks WHERE mem_id=?", (SHARED_ID,)
    ).fetchone()
    secure_delete = index.vec_index.conn.execute("PRAGMA secure_delete").fetchone()[0]
    migrated = await IndexVersionMigrator().try_migrate(index, [_migration()])
    migrated_a = await index.get_by_id("user-a", "scope-a", SHARED_ID)
    migrated_b = await index.get_by_id("user-b", "scope-b", SHARED_ID)
    migrated_unique_a = await index.get_by_id("user-a", "scope-a", "unique-a")
    migrated_unique_b = await index.get_by_id("user-b", "scope-b", "unique-b")
    migrated_documents_a = await _documents(index, "user-a", "scope-a")
    migrated_documents_b = await _documents(index, "user-b", "scope-b")
    migrated_chunk_row = index.vec_index.conn.execute(
        "SELECT user_id, scope_id, text FROM chunks WHERE mem_id=?", (SHARED_ID,)
    ).fetchone()
    checks = {
        "unique_id_controls_visible_before_restart": _ids(documents_a) == {"unique-a"}
        and _ids(documents_b) == {"unique-b", SHARED_ID},
        "duplicate_id_overwrites_sibling_tenant_index_row": chunk_row
        == ("user-b", "scope-b", CANARIES["shared_b"]),
        "tenant_a_markdown_survives_index_collision": shared_a is not None
        and shared_a.text == CANARIES["shared_a"],
        "tenant_b_duplicate_id_is_visible": shared_b is not None
        and shared_b.text == CANARIES["shared_b"],
        "migration_version_set_before_restart": migrated and index.get_schema_version() == 1,
        "migration_preserves_exactly_one_duplicate_index_owner": (
            SHARED_ID in _ids(migrated_documents_a)
        )
        != (SHARED_ID in _ids(migrated_documents_b))
        and migrated_chunk_row
        in {
            ("user-a", "scope-a", CANARIES["shared_a"]),
            ("user-b", "scope-b", CANARIES["shared_b"]),
        },
        "duplicate_markdown_copies_survive_migration": migrated_a is not None
        and migrated_a.text == CANARIES["shared_a"]
        and migrated_b is not None
        and migrated_b.text == CANARIES["shared_b"],
    }
    diagnostics: JSONObject = {
        "migrated_ids_a": sorted(_ids(migrated_documents_a)),
        "migrated_ids_b": sorted(_ids(migrated_documents_b)),
        "migrated_chunk_row": list(migrated_chunk_row) if migrated_chunk_row else None,
        "migration_count_a": _migration_count(migrated_a),
        "migration_count_b": _migration_count(migrated_b),
        "migration_count_unique_a": _migration_count(migrated_unique_a),
        "migration_count_unique_b": _migration_count(migrated_unique_b),
        "sqlite_secure_delete": secure_delete,
    }
    _validate_checks(checks, diagnostics)
    _close(index)
    return {
        "schema_version": 1,
        "phase": 1,
        "checks": checks,
        "metrics": diagnostics,
    }


def _proof_windows() -> list[JSONObject]:
    proofs: list[JSONObject] = []
    for path in sorted(STATE_ROOT.rglob("*")):
        if not path.is_file():
            continue
        data = path.read_bytes()
        for name, canary in CANARIES.items():
            needle = canary.encode()
            offset = data.find(needle)
            if offset < 0:
                continue
            start = max(0, offset - 64)
            end = min(len(data), offset + len(needle) + 64)
            proofs.append(
                {
                    "canary": name,
                    "file": path.relative_to(STATE_ROOT).as_posix(),
                    "needle_sha256": hashlib.sha256(needle).hexdigest(),
                    "offset": offset,
                    "window_base64": base64.b64encode(data[start:end]).decode(),
                    "window_sha256": hashlib.sha256(data[start:end]).hexdigest(),
                    "window_start": start,
                }
            )
    return proofs


async def _phase_two() -> JSONObject:
    index = FileMemoryIndex(str(STATE_ROOT), DeterministicEmbedding())
    version_after_restart = index.get_schema_version()
    documents_a = await _documents(index, "user-a", "scope-a")
    documents_b = await _documents(index, "user-b", "scope-b")
    shared_a_before = await index.get_by_id("user-a", "scope-a", SHARED_ID)
    shared_b_before = await index.get_by_id("user-b", "scope-b", SHARED_ID)
    changes_before = index.vec_index.conn.total_changes
    replayed = await IndexVersionMigrator().try_migrate(index, [_migration()])
    changes_after = index.vec_index.conn.total_changes
    unique_a = await index.get_by_id("user-a", "scope-a", "unique-a")
    unique_b = await index.get_by_id("user-b", "scope-b", "unique-b")
    shared_a = await index.get_by_id("user-a", "scope-a", SHARED_ID)
    shared_b = await index.get_by_id("user-b", "scope-b", SHARED_ID)
    await index.delete_by_user_and_scope("user-b", "scope-b")
    b_empty = not await _documents(index, "user-b", "scope-b")
    a_after_b_delete = await _documents(index, "user-a", "scope-a")
    shared_a_after_b_delete = await index.get_by_id("user-a", "scope-a", SHARED_ID)
    await index.delete_by_user_and_scope("user-a", "scope-a")
    logical_empty = not await _documents(index, "user-a", "scope-a")
    logical_empty = logical_empty and not await _documents(index, "user-b", "scope-b")
    logical_empty = logical_empty and not await index.list_user_scopes()
    _close(index)
    proofs = _proof_windows()
    markdown_files = list(STATE_ROOT.rglob("*.md"))
    residue_names = {proof["canary"] for proof in proofs}
    indexed_by_a = SHARED_ID in _ids(documents_a)
    indexed_by_b = SHARED_ID in _ids(documents_b)
    checks = {
        "unique_id_controls_survive_restart": "unique-a" in _ids(documents_a)
        and "unique-b" in _ids(documents_b),
        "duplicate_id_defect_survives_restart": shared_a_before is not None
        and shared_a_before.text == CANARIES["shared_a"]
        and shared_b_before is not None
        and shared_b_before.text == CANARIES["shared_b"]
        and indexed_by_a != indexed_by_b,
        "migration_version_resets_on_restart": version_after_restart == 0,
        "migration_replays_after_restart": replayed and changes_after > changes_before,
        "sibling_scope_delete_preserves_unique_control": "unique-a" in _ids(a_after_b_delete),
        "sibling_scope_delete_preserves_other_markdown_copy": shared_a_after_b_delete is not None
        and shared_a_after_b_delete.text == CANARIES["shared_a"],
        "native_scoped_delete_is_logically_effective": b_empty and logical_empty,
        "deleted_markdown_sources_are_absent": not markdown_files,
        "post_delete_plaintext_residue_scan_completed": True,
    }
    diagnostics: JSONObject = {
        "indexed_owner_before_restart": "user-a" if indexed_by_a else "user-b",
        "migration_count_unique_a": _migration_count(unique_a),
        "migration_count_unique_b": _migration_count(unique_b),
        "migration_count_shared_a": _migration_count(shared_a),
        "migration_count_shared_b": _migration_count(shared_b),
        "proof_window_count": len(proofs),
        "residue_canaries": sorted(residue_names),
    }
    _validate_checks(checks, diagnostics)
    return {
        "schema_version": 1,
        "phase": 2,
        "checks": checks,
        "metrics": diagnostics,
        "proof_windows": proofs,
    }


async def _run() -> JSONObject:
    phase = int(os.environ.get("COTCODEC_PHASE", "0"))
    if phase == 1:
        return await _phase_one()
    if phase == 2:
        return await _phase_two()
    raise ValueError("COTCODEC_PHASE must be 1 or 2")


def main() -> int:
    """Run one lifecycle phase.

    Returns:
        Process exit code.

    """
    report = asyncio.run(_run())
    print(f"{MARKER}{json.dumps(report, sort_keys=True, separators=(',', ':'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
