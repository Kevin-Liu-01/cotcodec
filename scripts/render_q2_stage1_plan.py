#!/usr/bin/env python3
"""Render the q2-stage1-rescoped-v1 (S1a) plan file from committed inputs and A0 records.

Draft mode (no ``--a0a-run-dir``) writes the K = 32 draw on the eligible pool, the orders
and the engine and sampling arguments. Freeze mode (on the host) reads A0a's records itself
(``plan.a0a_measurements``: its lane run directory and its GPU job's bridge directory),
takes N* and the action path's A1 step p95 from the accepted attempt and the list of
pre-freeze GPU jobs that ran, applies the registered rules of preregistration section 6.2
(gates, floor, K-rule) and writes the frozen constants, the measurements with the digests of
the files they came from, the base and the job list. No constant is typed by hand. Nothing
is submitted; the output is never overwritten.
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


def load_setup_records(root: Path) -> list[dict]:
    """G0 item 5's registered setup-check records (refused unless their SHA-256 matches)."""
    return P.load_setup_check(root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--a0a-run-dir", type=Path, help="A0a's lane run directory (freeze)")
    parser.add_argument("--a0a-bridge-dir", type=Path, help="A0a's GPU job bridge directory")
    parser.add_argument("--n-star", type=int, help="the accepted action-path attempt's N*")
    parser.add_argument("--action-path-step-p95", type=float,
                        help="the accepted attempt's step_p95_n1_s (seconds)")  # fmt: skip
    parser.add_argument("--prefreeze-jobs", nargs="+", default=["O1", "A0a"],
                        help="pre-freeze GPU jobs that ran, repeats listed again")  # fmt: skip
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; plan files are never overwritten")
    inputs = load_inputs(args.root)
    constants = measured = None
    if args.a0a_run_dir:
        if not (args.a0a_bridge_dir and args.n_star and args.action_path_step_p95):
            raise SystemExit("freeze mode needs --a0a-bridge-dir, --n-star, --action-path-step-p95")
        measured = P.a0a_measurements(
            args.a0a_run_dir, args.a0a_bridge_dir,
            action_path_step_p95_s=args.action_path_step_p95,
        )  # fmt: skip
        constants = P.freeze_constants(
            **P.freeze_inputs(measured, n_star=args.n_star, prefreeze_jobs=args.prefreeze_jobs)
        )
    dev_ok = P.dev_setup_ok(load_setup_records(args.root))
    plan = P.render_plan(**inputs, constants=constants, dev_setup_ok=dev_ok, measured=measured)
    args.out.write_text(json.dumps(plan, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(plan["plan_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
