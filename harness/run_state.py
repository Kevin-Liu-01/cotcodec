"""Content-addressed append-only state for experiment checkpoint and resume."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any


class RunStateError(RuntimeError):
    """Raised when progress state is incomplete, duplicated, or drifted."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    data = (canonical_json(payload) + "\n").encode()
    with temporary.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    directory_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


class ExecutionJournal:
    """Validate and extend one contiguous experiment-plan prefix."""

    def __init__(
        self,
        root: Path,
        *,
        contract: dict[str, Any],
        plan_keys: list[dict[str, Any]],
        resume: bool,
    ):
        self.root = root
        self.contract = contract
        self.plan_keys = plan_keys
        self.contract_sha256 = sha256_json(contract)
        self.plan_sha256 = sha256_json(plan_keys)
        self.contract_path = root / "contract.json"
        self.journal_path = root / "journal.jsonl"
        self.checkpoint_path = root / "checkpoint.json"
        self.ack_path = root / "checkpoint-ack.json"
        self.rows: list[dict[str, Any]] = []
        self.journal_root_sha256 = "0" * 64

        if resume:
            self._load()
        else:
            if root.exists() and any(root.iterdir()):
                raise RunStateError("fresh run state directory is not empty")
            root.mkdir(parents=True, exist_ok=True)
            _atomic_json(self.contract_path, contract)
            self._write_checkpoint("IN_PROGRESS")

    @property
    def completed(self) -> int:
        return len(self.rows)

    def _load_json(self, path: Path, label: str) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RunStateError(f"cannot load {label}: {exc}") from exc

    def _load(self) -> None:
        if not self.root.is_dir():
            raise RunStateError("resume state directory does not exist")
        if self._load_json(self.contract_path, "run contract") != self.contract:
            raise RunStateError("resume contract drifted")
        checkpoint = self._load_json(self.checkpoint_path, "checkpoint")
        if not isinstance(checkpoint, dict):
            raise RunStateError("checkpoint must be a mapping")

        previous = "0" * 64
        seen: set[str] = set()
        rows: list[dict[str, Any]] = []
        if self.journal_path.exists():
            for line_number, line in enumerate(
                self.journal_path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise RunStateError(f"journal line {line_number} is malformed") from exc
                if not isinstance(row, dict):
                    raise RunStateError(f"journal line {line_number} is not a mapping")
                supplied_sha = row.get("row_sha256")
                body = {key: value for key, value in row.items() if key != "row_sha256"}
                if supplied_sha != sha256_json(body):
                    raise RunStateError(f"journal line {line_number} hash drifted")
                index = len(rows)
                if row.get("index") != index or index >= len(self.plan_keys):
                    raise RunStateError("journal is not a contiguous plan prefix")
                if row.get("key") != self.plan_keys[index]:
                    raise RunStateError("journal plan key drifted")
                if row.get("previous_sha256") != previous:
                    raise RunStateError("journal hash chain drifted")
                key_sha = sha256_json(row["key"])
                if key_sha in seen:
                    raise RunStateError("journal contains a duplicate plan key")
                seen.add(key_sha)
                previous = str(supplied_sha)
                rows.append(row)

        expected_checkpoint = {
            "schema_version": 1,
            "status": checkpoint.get("status"),
            "contract_sha256": self.contract_sha256,
            "plan_sha256": self.plan_sha256,
            "completed_cells": len(rows),
            "total_cells": len(self.plan_keys),
            "journal_root_sha256": previous,
        }
        if checkpoint != expected_checkpoint:
            raise RunStateError("checkpoint does not bind journal state")
        if checkpoint.get("status") not in {"IN_PROGRESS", "COMPLETE"}:
            raise RunStateError("checkpoint status is invalid")
        if checkpoint.get("status") == "COMPLETE" and len(rows) != len(self.plan_keys):
            raise RunStateError("complete checkpoint is truncated")
        self.rows = rows
        self.journal_root_sha256 = previous

    def append(self, key: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        index = self.completed
        if index >= len(self.plan_keys) or key != self.plan_keys[index]:
            raise RunStateError("append key is not the next planned cell")
        body = {
            "schema_version": 1,
            "index": index,
            "key": key,
            "payload": payload,
            "previous_sha256": self.journal_root_sha256,
        }
        row = {**body, "row_sha256": sha256_json(body)}
        encoded = (canonical_json(row) + "\n").encode()
        with self.journal_path.open("ab") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        self.rows.append(row)
        self.journal_root_sha256 = row["row_sha256"]
        self._write_checkpoint("IN_PROGRESS")
        return row

    def _write_checkpoint(self, status: str) -> None:
        _atomic_json(
            self.checkpoint_path,
            {
                "schema_version": 1,
                "status": status,
                "contract_sha256": self.contract_sha256,
                "plan_sha256": self.plan_sha256,
                "completed_cells": self.completed,
                "total_cells": len(self.plan_keys),
                "journal_root_sha256": self.journal_root_sha256,
            },
        )

    def complete(self) -> None:
        if self.completed != len(self.plan_keys):
            raise RunStateError("cannot complete a truncated execution plan")
        self._write_checkpoint("COMPLETE")

    def acknowledge_interrupt(self, signal_name: str) -> None:
        self._write_checkpoint("IN_PROGRESS")
        _atomic_json(
            self.ack_path,
            {
                "schema_version": 1,
                "signal": signal_name,
                "completed_cells": self.completed,
                "journal_root_sha256": self.journal_root_sha256,
                "checkpoint": self.checkpoint_path.name,
            },
        )

    def payloads(self) -> Iterable[dict[str, Any]]:
        for row in self.rows:
            yield row["payload"]
