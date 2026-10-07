#!/usr/bin/env python3
"""Freeze and verify experiment preregistrations in a hash-chained ledger.

A preregistration is a Markdown file under ``program/preregistrations/`` that
states the metrics, decision rules, seeds and kill criteria of one experiment
before any treatment data exists. ``freeze`` appends its SHA-256 to
``program/preregistrations/ledger.jsonl``; ``verify`` refuses if the file has
changed since it was frozen. Result receipts carry the frozen digest, so a
result can always be traced to the exact rules it was read against.

A material change to a frozen preregistration is a new file with a new
experiment id, never an edit.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = PROJECT_ROOT / "program" / "preregistrations" / "ledger.jsonl"
EXPERIMENT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,79}$")
GENESIS = "0" * 64


class PreregistrationError(ValueError):
    """Raised when a preregistration cannot be frozen or does not verify."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _row_hash(row: dict[str, object]) -> str:
    payload = json.dumps(row, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _git_head(root: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    head = completed.stdout.strip()
    return head if re.fullmatch(r"[0-9a-f]{40}", head) else None


def read_ledger(ledger: Path) -> list[dict[str, object]]:
    """Return ledger rows after checking the hash chain end to end."""
    if not ledger.exists():
        return []
    rows: list[dict[str, object]] = []
    previous = GENESIS
    for number, line in enumerate(ledger.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        claimed = row.get("hash")
        body = {key: value for key, value in row.items() if key != "hash"}
        if row.get("previous_hash") != previous:
            raise PreregistrationError(f"ledger line {number}: broken previous_hash link")
        if claimed != _row_hash(body):
            raise PreregistrationError(f"ledger line {number}: row hash does not match its body")
        rows.append(row)
        previous = str(claimed)
    return rows


def _relative(path: Path, root: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise PreregistrationError("preregistration must live inside the repository") from exc


def freeze(
    prereg: Path, experiment_id: str, *, ledger: Path = DEFAULT_LEDGER, root: Path = PROJECT_ROOT
) -> dict[str, object]:
    if not EXPERIMENT_ID_RE.fullmatch(experiment_id):
        raise PreregistrationError("experiment id must be kebab-case, 3-80 characters")
    if not prereg.is_file() or prereg.is_symlink():
        raise PreregistrationError("preregistration must be a regular file")
    text = prereg.read_text(encoding="utf-8")
    if re.search(r"\bTBD\b|<[A-Za-z_ -]+>", text):
        raise PreregistrationError("preregistration still contains TBD or <placeholder> text")
    relative = _relative(prereg, root)
    digest = sha256_file(prereg)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            rows = read_ledger(ledger)
            for row in rows:
                if row["experiment_id"] == experiment_id:
                    raise PreregistrationError(
                        f"experiment id {experiment_id} is already frozen; use a new id"
                    )
                if row["path"] == relative:
                    raise PreregistrationError(f"{relative} is already frozen")
            previous = str(rows[-1]["hash"]) if rows else GENESIS
            row: dict[str, object] = {
                "experiment_id": experiment_id,
                "path": relative,
                "sha256": digest,
                "frozen_at": datetime.now(UTC).isoformat(),
                "git_head_at_freeze": _git_head(root),
                "previous_hash": previous,
            }
            row["hash"] = _row_hash(row)
            handle.seek(0, 2)
            handle.write(json.dumps(row, sort_keys=True) + "\n")
            handle.flush()
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)
    return row


def verify(
    experiment_id: str, *, ledger: Path = DEFAULT_LEDGER, root: Path = PROJECT_ROOT
) -> dict[str, object]:
    for row in read_ledger(ledger):
        if row["experiment_id"] != experiment_id:
            continue
        path = root / str(row["path"])
        if not path.is_file():
            raise PreregistrationError(f"frozen preregistration {row['path']} is missing")
        actual = sha256_file(path)
        if actual != row["sha256"]:
            raise PreregistrationError(
                f"{row['path']} changed after freezing ({actual} != {row['sha256']})"
            )
        return row
    raise PreregistrationError(f"experiment id {experiment_id} is not frozen")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    commands = parser.add_subparsers(dest="command", required=True)
    freeze_parser = commands.add_parser("freeze")
    freeze_parser.add_argument("experiment_id")
    freeze_parser.add_argument("preregistration", type=Path)
    verify_parser = commands.add_parser("verify")
    verify_parser.add_argument("experiment_id")
    commands.add_parser("check-chain")
    args = parser.parse_args(argv)
    try:
        if args.command == "freeze":
            row = freeze(args.preregistration, args.experiment_id, ledger=args.ledger)
        elif args.command == "verify":
            row = verify(args.experiment_id, ledger=args.ledger)
        else:
            rows = read_ledger(args.ledger)
            print(json.dumps({"rows": len(rows), "status": "PASS"}))
            return 0
    except PreregistrationError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(row, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
