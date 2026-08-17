#!/usr/bin/env python3
"""Contained lifecycle falsifier for pinned Mnemosyne OSS.

The doctor deliberately uses only the public Mnemosyne API plus read-only SQL
inspection.  It does not patch the upstream package or use an LLM/embedding
backend.  Each phase runs in a fresh container process against one persistent
SQLite state directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from mnemosyne.core.memory import Mnemosyne

SCHEMA_VERSION = 1
EXPECTED_VERSION = "3.16.0"
TERMINAL_STATUS = "BLOCKED_CONSOLIDATED_FORGET_AND_NO_REACTIVATION"


class DoctorError(RuntimeError):
    """Raised when the lifecycle probe is malformed or internally inconsistent."""


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _write_once(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        data = memoryview(_json_bytes(value))
        while data:
            written = os.write(descriptor, data)
            if written <= 0:
                raise DoctorError(f"short write: {path}")
            data = data[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise DoctorError(f"expected regular JSON file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DoctorError(f"cannot read strict JSON: {path}") from exc
    if not isinstance(value, dict):
        raise DoctorError(f"expected JSON object: {path}")
    return value


def _sha_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _contents(rows: list[dict[str, Any]]) -> list[str]:
    return [str(row.get("content", "")) for row in rows]


def _query_rows(db_path: Path, sql: str, parameters: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in connection.execute(sql, parameters).fetchall()]
    finally:
        connection.close()


def _close_memories(*memories: Mnemosyne) -> None:
    connections: list[sqlite3.Connection] = []
    seen: set[int] = set()
    for memory in memories:
        for connection in (memory.conn, memory.beam.conn):
            if id(connection) not in seen:
                seen.add(id(connection))
                connections.append(connection)
    for connection in connections:
        connection.commit()
    for connection in reversed(connections):
        connection.close()


def _canaries(repeat: int) -> dict[str, str]:
    return {
        "a_primary": f"MNEMOSYNE_A_R{repeat}_CANARY_91F3",
        "a_secondary": f"MNEMOSYNE_A_R{repeat}_CANARY_7C2B",
        "b_private": f"MNEMOSYNE_B_R{repeat}_CANARY_D84E",
    }


def _base_result(phase: str, repeat: int) -> dict[str, Any]:
    import mnemosyne

    version = getattr(mnemosyne, "__version__", None)
    if version != EXPECTED_VERSION:
        raise DoctorError(f"Mnemosyne version drifted: {version!r}")
    return {
        "schema_version": SCHEMA_VERSION,
        "phase": phase,
        "repeat": repeat,
        "mnemosyne_version": version,
        "scientific_result": False,
        "publication_ready": False,
        "model_calls": 0,
        "embedding_calls": 0,
    }


def prepare(state_root: Path, repeat: int) -> dict[str, Any]:
    contract_path = state_root / "contract.json"
    if contract_path.exists():
        raise DoctorError("prepare refuses an existing contract")
    state_root.mkdir(parents=True, exist_ok=True)
    db_path = state_root / "mnemosyne.db"
    canaries = _canaries(repeat)

    tenant_a = Mnemosyne(session_id="tenant-a", db_path=db_path)
    tenant_b = Mnemosyne(session_id="tenant-b", db_path=db_path)
    a_primary_id = tenant_a.remember(
        canaries["a_primary"], source="cotcodec-lifecycle", importance=0.9
    )
    duplicate_id = tenant_a.remember(
        canaries["a_primary"], source="cotcodec-lifecycle", importance=0.9
    )
    a_secondary_id = tenant_a.remember(
        canaries["a_secondary"], source="cotcodec-lifecycle", importance=0.8
    )
    b_private_id = tenant_b.remember(
        canaries["b_private"], source="cotcodec-lifecycle", importance=0.9
    )
    if not all(isinstance(value, str) and value for value in (
        a_primary_id,
        duplicate_id,
        a_secondary_id,
        b_private_id,
    )):
        raise DoctorError("Mnemosyne returned an invalid memory ID")

    a_context_before = _contents(tenant_a.get_context(limit=20))
    b_context_before = _contents(tenant_b.get_context(limit=20))
    duplicate_count = _query_rows(
        db_path,
        "SELECT count(*) AS n FROM working_memory WHERE id = ?",
        (a_primary_id,),
    )[0]["n"]

    sleep = tenant_a.sleep(force=True)
    episodic_rows = _query_rows(
        db_path,
        "SELECT id, content, summary_of, session_id FROM episodic_memory "
        "WHERE session_id = ? ORDER BY rowid",
        ("tenant-a",),
    )
    source_rows = _query_rows(
        db_path,
        "SELECT id, content, consolidated_at FROM working_memory "
        "WHERE session_id = ? ORDER BY id",
        ("tenant-a",),
    )
    a_context_after_sleep = _contents(tenant_a.get_context(limit=20))
    a_recall_after_sleep = _contents(
        tenant_a.recall(canaries["a_primary"], top_k=20)
    )
    b_recall_a_after_sleep = _contents(
        tenant_b.recall(canaries["a_primary"], top_k=20)
    )

    first_forget = tenant_a.forget(a_primary_id)
    second_forget = tenant_a.forget(a_primary_id)
    a_recall_after_forget = _contents(
        tenant_a.recall(canaries["a_primary"], top_k=20)
    )
    source_after_forget = _query_rows(
        db_path,
        "SELECT count(*) AS n FROM working_memory WHERE id = ?",
        (a_primary_id,),
    )[0]["n"]
    episodic_after_forget = _query_rows(
        db_path,
        "SELECT id, content, summary_of, session_id FROM episodic_memory "
        "WHERE session_id = ? ORDER BY rowid",
        ("tenant-a",),
    )

    contract = {
        "schema_version": SCHEMA_VERSION,
        "repeat": repeat,
        "canaries": canaries,
        "memory_ids": {
            "a_primary": a_primary_id,
            "a_secondary": a_secondary_id,
            "b_private": b_private_id,
            "episodic": [str(row["id"]) for row in episodic_after_forget],
        },
        "expected_episodic_count": len(episodic_after_forget),
    }
    _write_once(contract_path, contract)
    _close_memories(tenant_a, tenant_b)

    result = _base_result("prepare", repeat)
    result.update(
        {
            "duplicate_retry_idempotent": duplicate_id == a_primary_id
            and duplicate_count == 1,
            "session_isolation_before_sleep": canaries["a_primary"] in a_context_before
            and canaries["b_private"] not in a_context_before
            and canaries["b_private"] in b_context_before
            and canaries["a_primary"] not in b_context_before,
            "sleep": sleep,
            "source_rows_marked_consolidated": bool(source_rows)
            and all(row["consolidated_at"] for row in source_rows),
            "episodic_summary_created": bool(episodic_rows),
            "consolidated_removed_from_active_context": canaries["a_primary"]
            not in a_context_after_sleep
            and canaries["a_secondary"] not in a_context_after_sleep,
            "consolidated_recallable": any(
                canaries["a_primary"] in content for content in a_recall_after_sleep
            ),
            "cross_session_recall_blocked": not any(
                canaries["a_primary"] in content for content in b_recall_a_after_sleep
            ),
            "documented_forget_deleted_source": first_forget is True
            and second_forget is False
            and source_after_forget == 0,
            "episodic_summary_survived_source_forget": bool(episodic_after_forget),
            "forgotten_canary_still_recallable": any(
                canaries["a_primary"] in content for content in a_recall_after_forget
            ),
            "contract_sha256": _sha_path(contract_path),
        }
    )
    return result


def verify_restart(state_root: Path, repeat: int) -> dict[str, Any]:
    contract = _read_json(state_root / "contract.json")
    if contract.get("repeat") != repeat or contract.get("canaries") != _canaries(repeat):
        raise DoctorError("restart contract drifted")
    db_path = state_root / "mnemosyne.db"
    canaries = contract["canaries"]
    tenant_a = Mnemosyne(session_id="tenant-a", db_path=db_path)
    tenant_b = Mnemosyne(session_id="tenant-b", db_path=db_path)

    recalled_a = _contents(tenant_a.recall(canaries["a_primary"], top_k=20))
    recalled_b = _contents(tenant_b.recall(canaries["a_primary"], top_k=20))
    active_after_recall = _contents(tenant_a.get_context(limit=20))
    source_rows = _query_rows(
        db_path,
        "SELECT id, consolidated_at FROM working_memory WHERE session_id = ?",
        ("tenant-a",),
    )
    episodic_rows = _query_rows(
        db_path,
        "SELECT id, summary_of FROM episodic_memory WHERE session_id = ? ORDER BY rowid",
        ("tenant-a",),
    )
    _close_memories(tenant_a, tenant_b)

    result = _base_result("verify-restart", repeat)
    result.update(
        {
            "restart_preserved_episodic_summary": len(episodic_rows)
            == contract["expected_episodic_count"],
            "restart_preserved_recall": any(
                canaries["a_primary"] in content for content in recalled_a
            ),
            "restart_preserved_session_isolation": not any(
                canaries["a_primary"] in content for content in recalled_b
            ),
            "recall_did_not_reactivate": canaries["a_primary"] not in active_after_recall
            and canaries["a_secondary"] not in active_after_recall
            and all(row["consolidated_at"] for row in source_rows),
            "episodic_source_lineage_present": bool(episodic_rows)
            and all(str(row["summary_of"]).strip() for row in episodic_rows),
            "database_sha256": _sha_path(db_path),
        }
    )
    _write_once(state_root / "restart.json", result)
    return result


def purge(state_root: Path, repeat: int) -> dict[str, Any]:
    contract = _read_json(state_root / "contract.json")
    restart = _read_json(state_root / "restart.json")
    if contract.get("repeat") != repeat or restart.get("repeat") != repeat:
        raise DoctorError("purge contract drifted")
    db_path = state_root / "mnemosyne.db"
    canaries = contract["canaries"]
    memory_ids = contract["memory_ids"]
    tenant_a = Mnemosyne(session_id="tenant-a", db_path=db_path)

    remaining_source_forget = tenant_a.forget(memory_ids["a_secondary"])
    episodic_forget_results = [
        tenant_a.forget(memory_id) for memory_id in memory_ids["episodic"]
    ]
    native_scoped_purge_available = callable(getattr(tenant_a, "purge", None))
    _close_memories(tenant_a)

    logical_rows: dict[str, int] = {}
    for table in ("working_memory", "episodic_memory", "memories"):
        count = _query_rows(
            db_path,
            f"SELECT count(*) AS n FROM {table} WHERE content LIKE ?",
            (f"%{canaries['a_primary']}%",),
        )[0]["n"]
        logical_rows[table] = int(count)

    physical_hits: list[str] = []
    for path in sorted(state_root.glob("mnemosyne.db*")):
        if path.is_file() and not path.is_symlink():
            data = path.read_bytes()
            if canaries["a_primary"].encode() in data:
                physical_hits.append(path.name)

    blocked = (
        remaining_source_forget is True
        and episodic_forget_results
        and not any(episodic_forget_results)
        and logical_rows["episodic_memory"] > 0
        and bool(physical_hits)
        and native_scoped_purge_available is False
        and restart.get("recall_did_not_reactivate") is True
    )
    result = _base_result("purge", repeat)
    result.update(
        {
            "status": TERMINAL_STATUS if blocked else "INCONCLUSIVE_LIFECYCLE_RESULT",
            "remaining_source_forget": remaining_source_forget,
            "episodic_forget_results": episodic_forget_results,
            "native_session_scoped_purge_available": native_scoped_purge_available,
            "logical_canary_rows_after_documented_forget": logical_rows,
            "plaintext_canary_residue_reproduced": bool(physical_hits),
            "physical_hit_files": physical_hits,
            "archive_to_active_transition_available": False,
            "h100_actor_admission": "forbidden-for-this-revision",
            "database_sha256": _sha_path(db_path),
        }
    )
    _write_once(state_root / "purge.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("prepare", "verify-restart", "purge"))
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--repeat", type=int, choices=(1, 2), required=True)
    args = parser.parse_args()
    if args.phase == "prepare":
        result = prepare(args.state_root, args.repeat)
    elif args.phase == "verify-restart":
        result = verify_restart(args.state_root, args.repeat)
    else:
        result = purge(args.state_root, args.repeat)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
