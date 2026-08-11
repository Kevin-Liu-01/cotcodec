#!/usr/bin/env python3
"""Append one hash-chained JSON record to a Research Gauntlet audit log."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

REQUIRED_FIELDS = {
    "wave",
    "score",
    "best_score",
    "run_id",
    "candidate_sha256",
    "queries",
    "wall_minutes",
    "tokens",
    "dollars",
    "gpu_hours",
    "termination_reason",
}


def _row_hash(row: dict[str, object]) -> str:
    payload = json.dumps(row, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def append_record(log_path: Path, record_path: Path) -> dict[str, object]:
    record = json.loads(record_path.read_text(encoding="utf-8"))
    if not isinstance(record, dict):
        raise ValueError("record must be a JSON object")
    missing = sorted(REQUIRED_FIELDS - record.keys())
    if missing:
        raise ValueError(f"record lacks required fields: {', '.join(missing)}")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        handle.seek(0)
        previous = "0" * 64
        for line in handle:
            if line.strip():
                previous = json.loads(line)["hash"]
        row = dict(record)
        row.setdefault("timestamp", datetime.now(UTC).isoformat())
        row["previous_hash"] = previous
        row["hash"] = _row_hash(row)
        handle.seek(0, 2)
        handle.write(json.dumps(row, sort_keys=True) + "\n")
        handle.flush()
        fcntl.flock(handle, fcntl.LOCK_UN)
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("record", type=Path)
    args = parser.parse_args()
    print(json.dumps(append_record(args.log, args.record), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
