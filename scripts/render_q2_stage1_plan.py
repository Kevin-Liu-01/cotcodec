#!/usr/bin/env python3
"""Render the q2-stage1-rescoped-v1 (S1a) plan file from committed inputs and A0 records.

Draft mode (no ``--constants``) writes the K = 32 draw, the orders and the engine and
sampling arguments. Freeze mode reads the A0 measurements (``--constants``, a JSON object
with n_star, a0a_slot_seconds, launch_a0a_min, prefreeze_caps, anchor_available, a0a_gates
(``python -m harness.q2_stage1.plan a0a-gates``) and, when the anchor is available,
launch_a0b_min and longest_a0b_slot_min), applies the registered rules of preregistration
section 6.2 (gates, floor, K-rule) and writes the frozen constants, the base and the job
list. Nothing is submitted; the output is never overwritten.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.q2_stage1 import plan as P  # noqa: E402

SPLITS = "program/evidence/q2-mutation/splits.json"
TASKS = "program/evidence/q2-mutation/sanitized-tasks"


def load_inputs(root: Path) -> dict:
    splits_path = root / SPLITS
    splits = json.loads(splits_path.read_text(encoding="utf-8"))
    ids = list(splits["confirm"]) + list(splits["dev"])
    domain = {
        t: json.loads((root / TASKS / f"{t}.json").read_text(encoding="utf-8"))["domain"]
        for t in ids
    }
    return {
        "confirm_ids": splits["confirm"],
        "dev_ids": splits["dev"],
        "domain": domain,
        "splits_sha256": hashlib.sha256(splits_path.read_bytes()).hexdigest(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--constants", type=Path)
    parser.add_argument("--dev-setup", type=Path, help="JSON map task id -> setup ok (G0 5)")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; plan files are never overwritten")
    inputs = load_inputs(args.root)
    constants = None
    if args.constants:
        raw = json.loads(args.constants.read_text(encoding="utf-8"))
        constants = P.freeze_constants(**raw)
    dev_ok = None
    if args.dev_setup:
        dev_ok = json.loads(args.dev_setup.read_text(encoding="utf-8"))
    plan = P.render_plan(**inputs, constants=constants, dev_setup_ok=dev_ok)
    args.out.write_text(json.dumps(plan, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(plan["plan_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
