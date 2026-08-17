#!/usr/bin/env python3
"""Contained restart and erasure falsifier for pinned Palimpsest.

The doctor uses deterministic hashing embeddings and static claims. It exercises
the native interval ledger and SQLite persistence without a model, network,
provider secret, benchmark answer, or orchestration-side state repair.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
from palimpsest.persist import SQLiteStore
from palimpsest.store import Memory
from palimpsest.types import Claim

SCHEMA_VERSION = 1
TERMINAL_STATUS = "BLOCKED_BITEMPORAL_RESTART_AND_NO_NATIVE_PURGE"
T0 = datetime(2024, 1, 1, 12, 0)


class DoctorError(RuntimeError):
    """Raised when a doctor phase or artifact is malformed."""


class HashEmbedder:
    """Small deterministic embedder that performs no model or network access."""

    dim = 32
    backend = "cotcodec-hash-v1"

    def embed(self, texts: list[str]) -> np.ndarray:
        rows = [self.embed_one(text) for text in texts]
        return np.stack(rows) if rows else np.zeros((0, self.dim), dtype=np.float32)

    def embed_one(self, text: str) -> np.ndarray:
        vector = np.zeros(self.dim, dtype=np.float32)
        for token in text.lower().split():
            digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
            vector[int.from_bytes(digest[:4], "little") % self.dim] += (
                1.0 if digest[4] & 1 else -1.0
            )
        norm = float(np.linalg.norm(vector))
        return vector if norm == 0 else vector / norm


def d(days: int) -> datetime:
    return T0 + timedelta(days=days)


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _write_once(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        view = memoryview(_json_bytes(value))
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise DoctorError(f"short write: {path}")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    parent = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)


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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _memory() -> Memory:
    return Memory(embedder=HashEmbedder(), index_messages=False)


def _apply(
    memory: Memory,
    predicate: str,
    value: str,
    tx_day: int,
    *,
    valid_day: int | None = None,
    cardinality: str = "single",
    source_id: str,
) -> None:
    claim = Claim(
        entity="user",
        predicate=predicate,
        value=value,
        cardinality=cardinality,
        valid_from=d(valid_day) if valid_day is not None else None,
        source_text=f"{predicate}={value}",
        source_id=source_id,
    )
    memory.ledger.apply(claim, tx_time=d(tx_day), default_valid_from=d(tx_day))


def _seed(canary: str) -> Memory:
    memory = _memory()
    _apply(memory, "city", "Austin", 0, source_id="city-austin")
    _apply(memory, "city", "Boston", 30, valid_day=10, source_id="city-boston")
    _apply(memory, "goal", "alpha", 0, source_id="goal-alpha")
    _apply(
        memory,
        "goal",
        "beta",
        1,
        cardinality="multi",
        source_id="goal-beta",
    )
    _apply(memory, "goal", "gamma", 2, source_id="goal-gamma")
    _apply(memory, "private_note", canary, 3, source_id="private-canary")
    return memory


def _values(memory: Memory, predicate: str, when: int, known_at: int | None = None) -> list[str]:
    entity_id = memory.canon.lookup_entity("user")
    predicate_id = memory.canon.lookup_predicate(predicate)
    if entity_id is None or predicate_id is None:
        return []
    return [
        atom.value
        for atom in memory.ledger.at(
            entity_id,
            predicate_id,
            d(when),
            known_at=d(known_at) if known_at is not None else None,
        )
    ]


def _base(phase: str, repeat: int) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "phase": phase,
        "repeat": repeat,
        "scientific_result": False,
        "publication_ready": False,
        "model_calls": 0,
        "embedding_model_calls": 0,
        "external_api_calls": 0,
    }


def prepare(state_root: Path, repeat: int) -> dict[str, Any]:
    contract_path = state_root / "contract.json"
    database_path = state_root / "palimpsest.db"
    if contract_path.exists() or database_path.exists():
        raise DoctorError("prepare refuses existing state")
    canary = f"PALIMPSEST_PRIVATE_R{repeat}_CANARY_7F21"
    memory = _seed(canary)
    city_id = memory.canon.lookup_predicate("city")
    if city_id is None:
        raise DoctorError("city predicate was not canonicalized")
    city_chain = memory.ledger.chain(0, city_id)
    contract = {
        "schema_version": SCHEMA_VERSION,
        "repeat": repeat,
        "canary": canary,
        "pre_restart": {
            "valid_time_day_5": _values(memory, "city", 5),
            "valid_time_day_20": _values(memory, "city", 20),
            "known_at_day_15": _values(memory, "city", 15, known_at=15),
            "goal_current": _values(memory, "goal", 50),
            "city_closed_tx": city_chain[0].closed_tx.isoformat(),
        },
    }
    store = SQLiteStore(database_path)
    first = store.save(memory)
    second = store.save(memory)
    store.close()
    _write_once(contract_path, contract)
    result = _base("prepare", repeat)
    result.update(
        {
            "ordinary_valid_time_correct": (
                contract["pre_restart"]["valid_time_day_5"] == ["Austin"]
                and contract["pre_restart"]["valid_time_day_20"] == ["Boston"]
            ),
            "pre_restart_knowledge_cutoff_correct": (
                contract["pre_restart"]["known_at_day_15"] == ["Austin"]
            ),
            "pre_restart_cardinality_vote_correct": (
                contract["pre_restart"]["goal_current"] == ["gamma"]
            ),
            "native_save_is_row_count_idempotent": first == second,
            "database_sha256": _sha256(database_path),
            "contract_sha256": _sha256(contract_path),
        }
    )
    return result


def verify_restart(state_root: Path, repeat: int) -> dict[str, Any]:
    contract = _read_json(state_root / "contract.json")
    if contract.get("repeat") != repeat:
        raise DoctorError("restart repeat drifted")
    database_path = state_root / "palimpsest.db"
    restored = _memory()
    store = SQLiteStore(database_path)
    store.load(restored)

    control = _seed(contract["canary"])
    _apply(
        control,
        "goal",
        "delta",
        4,
        cardinality="multi",
        source_id="goal-delta",
    )
    _apply(
        restored,
        "goal",
        "delta",
        4,
        cardinality="multi",
        source_id="goal-delta",
    )
    control_goal = _values(control, "goal", 50)
    restored_goal = _values(restored, "goal", 50)
    city_id = restored.canon.lookup_predicate("city")
    if city_id is None:
        raise DoctorError("restored city predicate is missing")
    restored_city = restored.ledger.chain(0, city_id)
    store.save(restored)
    store.close()

    result = _base("verify-restart", repeat)
    result.update(
        {
            "restart_preserved_ordinary_valid_time": (
                _values(restored, "city", 5) == ["Austin"]
                and _values(restored, "city", 20) == ["Boston"]
            ),
            "restart_preserved_current_value": _values(restored, "city", 50) == ["Boston"],
            "restart_preserved_knowledge_cutoff": (
                _values(restored, "city", 15, known_at=15) == ["Austin"]
            ),
            "restart_preserved_closed_tx": restored_city[0].closed_tx == d(30),
            "uninterrupted_goal_after_continuation": control_goal,
            "restored_goal_after_continuation": restored_goal,
            "restart_preserved_cardinality_continuation": restored_goal == control_goal,
            "status": TERMINAL_STATUS,
        }
    )
    return result


def purge_probe(state_root: Path, repeat: int) -> dict[str, Any]:
    contract = _read_json(state_root / "contract.json")
    if contract.get("repeat") != repeat:
        raise DoctorError("purge repeat drifted")
    database_path = state_root / "palimpsest.db"
    memory = _memory()
    store = SQLiteStore(database_path)
    store.load(memory)
    corrected = memory.correct("user", "private_note", contract["canary"])
    store.save(memory)
    store.close()
    residue = contract["canary"].encode() in database_path.read_bytes()
    public_methods = set(dir(memory)) | set(dir(SQLiteStore))
    native_purge = bool(public_methods & {"delete", "forget", "purge", "erase"})
    result = _base("purge-probe", repeat)
    result.update(
        {
            "status": TERMINAL_STATUS,
            "correction_hides_canary_from_current_facts": (
                corrected == 1
                and contract["canary"] not in {fact.value for fact in memory.facts()}
            ),
            "native_delete_or_purge_api_available": native_purge,
            "plaintext_canary_remains_in_sqlite": residue,
            "append_only_design_declared": True,
            "h100_actor_admission": "forbidden-for-this-revision",
        }
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("prepare", "verify-restart", "purge-probe"))
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--repeat", type=int, required=True)
    args = parser.parse_args()
    args.state_root.mkdir(parents=True, exist_ok=True)
    function = {
        "prepare": prepare,
        "verify-restart": verify_restart,
        "purge-probe": purge_probe,
    }[args.phase]
    print(json.dumps(function(args.state_root, args.repeat), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
