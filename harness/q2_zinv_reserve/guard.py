"""Freeze guard of ``q2-zinv-reserve-validation-v1`` (standard library only; host and containers).

Every split: the staged code of record must be the registration's: the code table of section 3
(the SHA-256 of every file of this package and of the host tool), the reused files at their
pinned digests (``harness/q2_stage1/zinv.py``, ``rescore.py``, ``__init__.py``) and the
parent's code tree (``campaign.code_tree_sha256``, which also covers the operators, the save
stage, the scorer and the CPU lane) equal to the parent's frozen pin. The dev split (the
rehearsal) needs nothing more. The reserve split, the only registered one, also needs this
experiment's ledger row in the staged tree (hash chain intact, digest equal to the staged
registration), the parent's frozen row, and ``Q2ZR_PREREG_FROZEN`` set to the experiment id.

``infra/q2-zinv-reserve/run/zr_host.py`` calls ``require_split_allowed`` before it plans or
submits any step; steps 1, 3 and 4 call it again inside their containers (``check``).

    python -m harness.q2_zinv_reserve.guard check --split reserve --src /src
    python -m harness.q2_zinv_reserve.guard code-table --check      # or --write (draft only)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):  # run as a file on the host: make the staged tree importable
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from harness.q2_mutation import campaign  # noqa: E402  (standard library at import time)

EXPERIMENT_ID = "q2-zinv-reserve-validation-v1"
REGISTRATION = "program/preregistrations/q2-zinv-reserve-validation-v1.md"
LEDGER = "program/preregistrations/ledger.jsonl"
FROZEN_ENV = "Q2ZR_PREREG_FROZEN"
DEV_SPLIT = "dev"
REGISTERED_SPLIT = "reserve"
GENESIS = "0" * 64

# The code of record of this addendum, in the registration's code table (section 3).
CODE_FILES = (
    "harness/q2_zinv_reserve/__init__.py",
    "harness/q2_zinv_reserve/guard.py",
    "harness/q2_zinv_reserve/rules.py",
    "harness/q2_zinv_reserve/run.py",
    "infra/q2-zinv-reserve/run/zr_host.py",
)
# Reused unchanged; pinned by q2-stage1-rescoped-v1 section 20.
REUSED = {
    "harness/q2_stage1/__init__.py": (
        "0e2190149cf640fac07dab26332a26f696374ff4400c23aab82e8cf766f3b334"
    ),
    "harness/q2_stage1/rescore.py": (
        "d240db03e969c8aa5bb97403c5005cd4c9e96016599a78f70e97850415893737"
    ),
    "harness/q2_stage1/zinv.py": (
        "64899d5056f4791008c2a10c38a7b0fbb94fbe912d20a702ec74851a0ca7f655"
    ),
}
PARENT_CODE_TREE_SHA256 = "58bee0190c0c7eb5d44f36e27c0f1e0daab82c1c48716009a9066777c69a0721"
TABLE_START = "<!-- q2zr-code-table start -->"
TABLE_END = "<!-- q2zr-code-table end -->"


class GuardError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def code_table(root: Path) -> str:
    rows = ["| File | SHA-256 |", "|---|---|"]
    for rel in CODE_FILES:
        path = root / rel
        if not path.is_file():
            raise GuardError(f"code of record {rel} is missing from {root}")
        rows.append(f"| `{rel}` | `{_sha256(path)}` |")
    return "\n".join(rows)


def declared_code_table(text: str) -> str:
    pattern = re.escape(TABLE_START) + r"\n(.*?)\n" + re.escape(TABLE_END)
    match = re.search(pattern, text, re.DOTALL)
    if match is None:
        raise GuardError("the registration has no code table markers")
    return match.group(1)


def check_code(src: Path) -> dict[str, Any]:
    """Refuse a staged tree whose code differs from the code of record."""
    registration = src / REGISTRATION
    if not registration.is_file():
        raise GuardError(f"{REGISTRATION} is missing from {src}")
    if declared_code_table(registration.read_text(encoding="utf-8")) != code_table(src):
        raise GuardError("the staged code differs from the registration's code table")
    wrong = sorted(
        rel
        for rel, digest in REUSED.items()
        if not (src / rel).is_file() or _sha256(src / rel) != digest
    )
    if wrong:
        raise GuardError(f"reused files differ from their pins: {wrong}")
    tree = campaign.code_tree_sha256(src)
    parent_pin = campaign.prereg_pins((src / campaign.PREREG_PATH).read_text(encoding="utf-8"))
    if tree != PARENT_CODE_TREE_SHA256 or parent_pin.get("code_tree_sha256") != tree:
        raise GuardError("the parent's code tree differs from its frozen pin")
    return {"code_table": "ok", "reused": "ok", "parent_code_tree_sha256": tree}


def ledger_rows(ledger: Path) -> list[dict[str, Any]]:
    """Ledger rows after checking the hash chain end to end (``scripts/preregister.py``)."""
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
    """This experiment's ledger row in the staged tree, if the staged registration matches it."""
    ledger = src / LEDGER
    if not ledger.is_file():
        return None
    for row in ledger_rows(ledger):
        if row.get("experiment_id") == EXPERIMENT_ID:
            registration = src / REGISTRATION
            if (
                row.get("path") != REGISTRATION
                or not registration.is_file()
                or row.get("sha256") != _sha256(registration)
            ):
                raise GuardError("the staged registration differs from its frozen digest")
            return row
    return None


def require_split_allowed(split: str, src: Path) -> dict[str, Any] | None:
    """None for dev; this experiment's ledger row for reserve; raise otherwise."""
    check_code(src)
    if split == DEV_SPLIT:
        return None
    if split != REGISTERED_SPLIT:
        raise GuardError(
            f"this addendum registers the {REGISTERED_SPLIT} split only, not {split!r}"
        )
    row = frozen_row(src)
    if row is None:
        raise GuardError(f"split {split!r} runs only after {EXPERIMENT_ID} is frozen")
    if os.environ.get(FROZEN_ENV) != EXPERIMENT_ID:
        raise GuardError(f"set {FROZEN_ENV}={EXPERIMENT_ID} to run split {split!r}")
    try:
        parent = campaign.frozen_ledger_row(src)
    except campaign.CampaignError as exc:
        raise GuardError(str(exc)) from exc
    if parent is None:
        raise GuardError(f"the parent {campaign.EXPERIMENT_ID} is not frozen in the staged tree")
    return row


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    chk = sub.add_parser("check", help="refuse an unregistered split or code (host, containers)")
    chk.add_argument("--split", required=True)
    chk.add_argument("--src", type=Path, required=True)
    tab = sub.add_parser("code-table", help="check or (draft only) write the code table")
    mode = tab.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    tab.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            row = require_split_allowed(args.split, args.src)
            print(json.dumps({"split": args.split, "frozen": row is not None,
                              "ledger_hash": (row or {}).get("hash")}, sort_keys=True))  # fmt: skip
            return 0
        path = args.root / REGISTRATION
        text = path.read_text(encoding="utf-8")
        current = code_table(args.root)
        if args.check:
            ok = declared_code_table(text) == current
            print(json.dumps({"code_table": "PASS" if ok else "FAIL"}))
            return 0 if ok else 1
        if (args.root / LEDGER).is_file() and any(
            r.get("experiment_id") == EXPERIMENT_ID for r in ledger_rows(args.root / LEDGER)
        ):
            raise GuardError("the registration is frozen: a code change is a new experiment id")
        path.write_text(text.replace(declared_code_table(text), current, 1), encoding="utf-8")
        print(json.dumps({"code_table": "written", "files": len(CODE_FILES)}))
        return 0
    except (GuardError, campaign.CampaignError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
