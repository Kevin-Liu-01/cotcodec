"""Append-only verdict journal with kill-and-resume semantics.

The journal is one JSONL file of schema verdict rows. Writing rules:

- rows are only ever appended (``O_APPEND``), each batch in a single
  ``os.write`` followed by ``fsync``; nothing is rewritten or truncated;
- a work item's rows carry ``details.item_key`` and the optional schema keys
  ``run_id`` and ``attempt``; its last row carries ``details.item_final =
  true``. An item is complete only when a final row exists;
- on open, a file that does not end in a newline (a torn write from a killed
  process) gets a newline appended, so the fragment becomes its own invalid
  line. Readers skip and count invalid lines; they never hide them.

Resume: items with a final row are skipped; any other item reruns with
``attempt`` one higher than the highest attempt already journaled. Analyses
use, for each item, the rows of its final attempt only.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from harness.q1.schema import SchemaError, canonical_json, validate_verdict_row


def item_key(kernel_id: str, gate: str, seed: int) -> str:
    return f"{kernel_id}|{gate}|seed-{seed}"


class Journal:
    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists() and self.path.stat().st_size > 0:
            with self.path.open("rb") as handle:
                handle.seek(-1, os.SEEK_END)
                last = handle.read(1)
            if last != b"\n":
                self._write_bytes(b"\n")

    def _write_bytes(self, data: bytes) -> None:
        fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            view = memoryview(data)
            while view:
                written = os.write(fd, view)
                view = view[written:]
            os.fsync(fd)
        finally:
            os.close(fd)

    def append(self, rows: Iterable[Mapping[str, Any]]) -> int:
        lines = [canonical_json(validate_verdict_row(row)) + "\n" for row in rows]
        if lines:
            self._write_bytes("".join(lines).encode("utf-8"))
        return len(lines)

    def read(self) -> tuple[list[dict[str, Any]], int]:
        """All valid rows in order, and the number of invalid (torn) lines skipped."""
        if not self.path.exists():
            return [], 0
        rows: list[dict[str, Any]] = []
        invalid = 0
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rows.append(validate_verdict_row(json.loads(line)))
            except (json.JSONDecodeError, SchemaError):
                invalid += 1
        return rows, invalid

    def status(self) -> dict[str, dict[str, Any]]:
        """Per item: highest attempt seen and whether that attempt finished."""
        rows, _ = self.read()
        items: dict[str, dict[str, Any]] = {}
        for row in rows:
            key = row["details"].get("item_key")
            if key is None:
                continue
            attempt = int(row.get("attempt", 1))
            entry = items.setdefault(key, {"attempt": 0, "final": False})
            if attempt > entry["attempt"]:
                entry["attempt"], entry["final"] = attempt, False
            if attempt == entry["attempt"] and row["details"].get("item_final"):
                entry["final"] = True
        return items

    def final_rows(self) -> list[dict[str, Any]]:
        """Rows of each item's final, completed attempt."""
        rows, _ = self.read()
        status = self.status()
        return [
            row
            for row in rows
            if (key := row["details"].get("item_key")) in status
            and status[key]["final"]
            and int(row.get("attempt", 1)) == status[key]["attempt"]
        ]
