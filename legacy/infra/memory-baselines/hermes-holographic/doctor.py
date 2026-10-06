#!/usr/bin/env python3
"""Contained phase doctor for Hermes' native Holographic SQLite provider."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SOURCE_ROOT = Path("/opt/hermes-source")
PLUGIN_ROOT = SOURCE_ROOT / "plugins/memory/holographic"
STATE_ROOT = Path("/state")
DB_PATH = STATE_ROOT / "memory-store.db"
CANARIES = (
    "HOLOGRAPHIC_A_7F1D9A Alice owns Project Zephyr",
    "HOLOGRAPHIC_B_4C8E2B Bob chose cobalt editor",
    "HOLOGRAPHIC_C_91AA03 Carol deploys Nova",
)

sys.path[:0] = [str(PLUGIN_ROOT), str(SOURCE_ROOT)]

from retrieval import FactRetriever  # noqa: E402
from store import MemoryStore  # noqa: E402


class DoctorError(RuntimeError):
    """Raised when the native provider violates the registered phase contract."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _facts(store: MemoryStore) -> list[dict[str, Any]]:
    return [
        {
            "fact_id": row["fact_id"],
            "content": row["content"],
            "category": row["category"],
            "tags": row["tags"],
            "trust_score": row["trust_score"],
            "retrieval_count": row["retrieval_count"],
            "helpful_count": row["helpful_count"],
        }
        for row in sorted(store.list_facts(limit=100), key=lambda item: item["fact_id"])
    ]


def _snapshot(store: MemoryStore) -> dict[str, Any]:
    facts = _facts(store)
    columns = [
        row[1]
        for row in store._conn.execute("PRAGMA table_info(facts)").fetchall()  # noqa: SLF001
    ]
    snapshot = {
        "facts": facts,
        "fact_count": len(facts),
        "facts_columns": columns,
        "has_session_scope_column": any(
            name in columns for name in ("session_id", "user_id", "tenant_id")
        ),
    }
    snapshot["snapshot_sha256"] = _sha(_canonical(snapshot))
    return snapshot


def prepare() -> dict[str, Any]:
    if DB_PATH.exists():
        raise DoctorError("prepare requires a fresh database")
    store = MemoryStore(DB_PATH, default_trust=0.5, hrr_dim=64)
    try:
        first_id = store.add_fact(CANARIES[0], category="project", tags="owner")
        duplicate_id = store.add_fact(CANARIES[0], category="project", tags="owner")
        second_id = store.add_fact(CANARIES[1], category="tool", tags="editor")
        third_id = store.add_fact(CANARIES[2], category="project", tags="deploy")
        if first_id != duplicate_id or len({first_id, second_id, third_id}) != 3:
            raise DoctorError("duplicate add/idempotence contract failed")
        if not store.update_fact(second_id, content=f"{CANARIES[1]} with Vim"):
            raise DoctorError("fact update failed")
        feedback = store.record_feedback(first_id, helpful=True)
        results = FactRetriever(store, hrr_weight=0.0, hrr_dim=64).search(
            "Project Zephyr", limit=3
        )
        if not results or results[0]["fact_id"] != first_id:
            raise DoctorError("native FTS retrieval failed")
        snapshot = _snapshot(store)
        if snapshot["fact_count"] != 3 or feedback["new_trust"] != 0.55:
            raise DoctorError("prepared native state drifted")
    finally:
        store.close()
    return {
        "phase": "prepare",
        "duplicate_add_same_id": first_id == duplicate_id,
        "update_persisted": True,
        "feedback_persisted": True,
        "restart_required": True,
        "snapshot": snapshot,
        "model_calls": 0,
        "embedding_calls": 0,
        "network_calls": 0,
    }


def restart() -> dict[str, Any]:
    if not DB_PATH.is_file():
        raise DoctorError("restart database is missing")
    store = MemoryStore(DB_PATH, default_trust=0.5, hrr_dim=64)
    try:
        snapshot = _snapshot(store)
        results = FactRetriever(store, hrr_weight=0.0, hrr_dim=64).search(
            "Project Zephyr", limit=3
        )
        if snapshot["fact_count"] != 3 or not results:
            raise DoctorError("fresh-process restart did not recover native state")
        first = snapshot["facts"][0]
        second = snapshot["facts"][1]
        if (
            first["content"] != CANARIES[0]
            or first["trust_score"] != 0.55
            or first["helpful_count"] != 1
            or second["content"] != f"{CANARIES[1]} with Vim"
        ):
            raise DoctorError("update or feedback did not persist")
        session_a_visible_from_fresh_session_b = results[0]["content"] == CANARIES[0]
        if not session_a_visible_from_fresh_session_b:
            raise DoctorError("registered global-session visibility probe changed")
    finally:
        store.close()
    return {
        "phase": "restart",
        "restart_persistence_supported": True,
        "session_a_visible_from_fresh_session_b": True,
        "session_scoped_isolation_supported": False,
        "snapshot": snapshot,
        "model_calls": 0,
        "embedding_calls": 0,
        "network_calls": 0,
    }


def purge() -> dict[str, Any]:
    store = MemoryStore(DB_PATH, default_trust=0.5, hrr_dim=64)
    try:
        facts = _facts(store)
        if len(facts) != 3:
            raise DoctorError("purge input state drifted")
        for fact in facts:
            if not store.remove_fact(fact["fact_id"]):
                raise DoctorError("native logical fact removal failed")
        if _facts(store):
            raise DoctorError("logical fact rows remain after removal")
    finally:
        store.close()

    physical_hits: list[dict[str, str]] = []
    for path in sorted(STATE_ROOT.glob("memory-store.db*")):
        if not path.is_file():
            continue
        data = path.read_bytes()
        for canary in CANARIES:
            if canary.encode("utf-8") in data:
                physical_hits.append({"file": path.name, "canary_sha256": _sha(canary.encode())})
    reopened = MemoryStore(DB_PATH, default_trust=0.5, hrr_dim=64)
    try:
        logical_rows_after_restart = len(_facts(reopened))
    finally:
        reopened.close()
    if logical_rows_after_restart != 0:
        raise DoctorError("logical rows remain after fresh-process restart")
    return {
        "phase": "purge",
        "logical_rows_after_restart": logical_rows_after_restart,
        "native_session_purge_supported": False,
        "physical_zero_residue_after_logical_delete": not physical_hits,
        "physical_hits": physical_hits,
        "model_calls": 0,
        "embedding_calls": 0,
        "network_calls": 0,
    }


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"prepare", "restart", "purge"}:
        raise SystemExit("usage: doctor.py {prepare|restart|purge}")
    phase = sys.argv[1]
    result = {"prepare": prepare, "restart": restart, "purge": purge}[phase]()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
