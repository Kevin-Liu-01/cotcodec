#!/usr/bin/env python3
"""Write or check the code table of the K2 addendum (``q2-evaluator-mutation-v1-k2``).

The table between the ``k2-code-table`` markers of section 2 lists the SHA-256 of every file
of the K2 executor. ``--check`` exits 1 when the table differs from the tree; ``--write``
rewrites it (before the freeze only: a frozen file is never edited).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRATION = ROOT / "program/preregistrations/q2-evaluator-mutation-v1-k2.md"
LEDGER = ROOT / "program/preregistrations/ledger.jsonl"
FILES = (
    "harness/q2_mutation_k2/__init__.py",
    "harness/q2_mutation_k2/candidates.py",
    "harness/q2_mutation_k2/executor.py",
    "harness/q2_mutation_k2/guest/k2_guest.py",
    "harness/q2_mutation_k2/lane.py",
    "harness/q2_mutation_k2/report.py",
    "harness/q2_mutation_k2/rules.py",
    "infra/slurm/host-single-node/q2m-k2-vm.sbatch",
)
START, END = "<!-- k2-code-table start -->", "<!-- k2-code-table end -->"


def table(root: Path = ROOT) -> str:
    rows = ["| File | SHA-256 |", "|---|---|"]
    for rel in FILES:
        digest = hashlib.sha256((root / rel).read_bytes()).hexdigest()
        rows.append(f"| `{rel}` | `{digest}` |")
    return "\n".join(rows)


def declared(text: str) -> str:
    match = re.search(re.escape(START) + r"\n(.*?)\n" + re.escape(END), text, re.DOTALL)
    if match is None:
        raise SystemExit("the registration has no k2-code-table markers")
    return match.group(1)


def frozen() -> bool:
    if not LEDGER.is_file():
        return False
    return any(
        json.loads(line).get("experiment_id") == "q2-evaluator-mutation-v1-k2"
        for line in LEDGER.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    text = REGISTRATION.read_text(encoding="utf-8")
    current = table()
    if args.check:
        ok = declared(text) == current
        print(json.dumps({"code_table": "PASS" if ok else "FAIL"}))
        return 0 if ok else 1
    if frozen():
        raise SystemExit("the addendum is frozen: a code change is a new experiment id")
    updated = text.replace(declared(text), current, 1)
    REGISTRATION.write_text(updated, encoding="utf-8")
    print(json.dumps({"code_table": "written", "files": len(FILES)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
