"""Freeze guard of r04-checker-nuisance-invariance-v1 (standard library only).

Before the freeze only the dev split runs (smoke tests). Every other split needs the staged
tree to carry this experiment's ledger row (hash chain intact, digest equal to the staged
registration), ``R04_PREREG_FROZEN`` set to the experiment id, and image IDs equal to the
registration's pins block. The host tool calls ``require_split_allowed`` before it renders
any job; the item builder calls it again inside the container.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from harness.r04_nuisance import levels

LEDGER_PATH = "program/preregistrations/ledger.jsonl"
DEV_SPLIT = "dev"
GENESIS = "0" * 64
PINS_RE = re.compile(r"```json\n(\{\n \"r04_pins\": 1.*?\n\})\n```", re.DOTALL)


class GuardError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ledger_rows(ledger: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    previous = GENESIS
    for number, line in enumerate(ledger.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        body = {k: v for k, v in row.items() if k != "hash"}
        digest = hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        if row.get("previous_hash") != previous or row.get("hash") != digest:
            raise GuardError(f"ledger line {number}: hash chain broken")
        rows.append(row)
        previous = str(row["hash"])
    return rows


def frozen_row(src: Path) -> dict[str, Any] | None:
    ledger = src / LEDGER_PATH
    prereg = src / levels.PREREG_PATH
    if not ledger.is_file():
        return None
    for row in ledger_rows(ledger):
        if row.get("experiment_id") == levels.EXPERIMENT_ID:
            if not prereg.is_file() or row.get("sha256") != _sha256(prereg):
                raise GuardError("the staged registration differs from its frozen digest")
            return row
    return None


def prereg_pins(text: str) -> dict[str, Any]:
    match = PINS_RE.search(text)
    if not match:
        raise GuardError("the registration has no r04_pins block")
    return json.loads(match.group(1))


def require_split_allowed(
    split: str, src: Path, images: dict[str, str] | None = None
) -> dict[str, Any] | None:
    """None for dev; the ledger row otherwise (or raise)."""
    if split == DEV_SPLIT:
        return None
    row = frozen_row(src)
    if row is None:
        raise GuardError(f"split {split!r} runs only after {levels.EXPERIMENT_ID} is frozen")
    if os.environ.get("R04_PREREG_FROZEN") != levels.EXPERIMENT_ID:
        raise GuardError(f"set R04_PREREG_FROZEN={levels.EXPERIMENT_ID} to run split {split!r}")
    pins = prereg_pins((src / levels.PREREG_PATH).read_text(encoding="utf-8"))
    if images is not None:
        wrong = sorted(b for b, image in images.items() if pins["images"].get(b) != image)
        if wrong:
            raise GuardError(f"image IDs differ from the registration's pins: {wrong}")
    return row
