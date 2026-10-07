"""The signal checkpoint marker of the K1 entry point (standard library only).

The discovery-lane batch script confirms a signal-triggered checkpoint only
when ``/outputs/checkpoint.ready`` is a new file version, written after it sent
the signal, that contains the line ``trigger=SIG<name>`` for that signal
(``docs/operations.md``, "Signal checkpoint contract"). The K1 parent writes
the marker only after every running worker acknowledged a completed
signal-triggered save; periodic saves never write it.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


class MarkerError(ValueError):
    """Raised when a marker would not satisfy the batch script's contract."""


def write_checkpoint_marker(path: Path, trigger: str, token: str,
                            acks: Mapping[str, Any]) -> str:
    """Atomically write the marker (temporary file in the same directory, then rename)."""

    if not trigger.startswith("SIG") or "\n" in trigger:
        raise MarkerError("the marker trigger must be a signal name such as SIGUSR1")
    lines = [
        f"trigger={trigger}",
        f"token={token}",
        f"written_at={time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
        "acks=" + json.dumps(acks, sort_keys=True, separators=(",", ":"), default=str),
    ]
    payload = ("\n".join(lines) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    with temporary.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    return hashlib.sha256(payload).hexdigest()


def read_checkpoint_marker(path: Path) -> dict[str, Any]:
    """Parse a marker into its fields, with ``acks`` decoded from JSON."""

    fields: dict[str, Any] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            fields[key] = value
    fields["acks"] = json.loads(fields.get("acks", "{}"))
    return fields


__all__ = ["MarkerError", "read_checkpoint_marker", "write_checkpoint_marker"]
