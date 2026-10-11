"""Freeze guard of r04-checker-nuisance-invariance-v1 (standard library only).

Before the freeze only the dev split runs (smoke tests). Every other split needs the staged
tree to carry this experiment's ledger row (hash chain intact, digest equal to the staged
registration), ``R04_PREREG_FROZEN`` set to the experiment id, a code tree whose digest
(``code_tree_sha256`` over ``CODE_TREE_ROOTS``) equals the one the registration's pins block
names, and image IDs equal to the pins block's. The host tool calls ``require_splits_allowed``
before it renders any job; the item builder calls it again inside the container.
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

# The code of record whose digest the freeze fills in the pins block (registration section
# 3): R04's own code, image recipes, host tool and tests, and, unchanged, the reused code of
# the checker-mutation study (all of harness/q2_mutation, as its own code tree pins it) and
# of S1a (the capture rescorer, the corrected comparator and the task loader), and the lane.
CODE_TREE_ROOTS = (
    "harness/r04_nuisance",
    "infra/r04-nuisance",
    "tests/test_r04_nuisance.py",
    "harness/q2_mutation",
    "harness/q2_stage1/__init__.py",
    "harness/q2_stage1/rescore.py",
    "harness/q2_stage1/zinv.py",
    "harness/q2_stage1/osworld_live.py",
    "infra/slurm/host-single-node/q2-mutation-cpu.sbatch",
)
DOC_FILES = frozenset({"README.md", "SKILL.md"})


class GuardError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_files(root: Path, entry: str) -> list[Path]:
    path = root / entry
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise GuardError(f"code of record {entry} is missing from {root}")
    return sorted(
        p
        for p in path.rglob("*")
        if p.is_file()
        and "__pycache__" not in p.parts
        and p.suffix != ".pyc"
        and p.name not in DOC_FILES
    )


def code_tree_sha256(root: Path) -> str:
    """SHA-256 over (relative path, file SHA-256) of every file of the code of record, README
    and SKILL files and Python caches excepted (``campaign.code_tree_sha256``'s rule)."""
    digest = hashlib.sha256()
    for entry in CODE_TREE_ROOTS:
        for path in _tree_files(root, entry):
            digest.update(path.relative_to(root).as_posix().encode("utf-8") + b"\0")
            digest.update(_sha256(path).encode("ascii") + b"\n")
    return digest.hexdigest()


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
    declared = pins.get("code_tree_sha256")
    if not declared or declared != code_tree_sha256(src):
        raise GuardError("the staged code of record differs from the registration's code tree")
    if images is not None:
        wrong = sorted(b for b, image in images.items() if pins["images"].get(b) != image)
        if wrong:
            raise GuardError(f"image IDs differ from the registration's pins: {wrong}")
    return row


def require_splits_allowed(
    splits: list[str] | tuple[str, ...], src: Path, images: dict[str, str] | None = None
) -> dict[str, Any] | None:
    """The registered split set only (dev alone, or confirm and reserve); every split of it
    must be allowed. None for dev; the ledger row otherwise."""
    try:
        chosen = levels.check_split_set(splits)
    except ValueError as exc:
        raise GuardError(str(exc)) from exc
    rows = [require_split_allowed(split, src, images) for split in chosen]
    return rows[0]
