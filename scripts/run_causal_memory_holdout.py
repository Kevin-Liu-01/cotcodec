#!/usr/bin/env python3
"""Run the deterministic Stage-0 causal-memory holdout study."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.causal_memory_trials import (  # noqa: E402
    SymbolicTrialWorld,
    analyze_trials,
    make_symbolic_plan,
    run_trials,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--episodes", type=int, default=2_000)
    parser.add_argument("--world-seed", type=int, default=7)
    parser.add_argument("--assignment-seed", type=int, default=42)
    parser.add_argument("--audit-fraction", type=float, default=0.25)
    parser.add_argument("--propensity", type=float, default=0.5)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument(
        "--require-gates",
        action="store_true",
        help="Exit nonzero unless every registered Stage-0 gate passes.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    world = SymbolicTrialWorld.generate(args.episodes, args.world_seed)
    plan = make_symbolic_plan(
        world,
        assignment_seed=args.assignment_seed,
        audit_fraction=args.audit_fraction,
        propensity=args.propensity,
        folds=args.folds,
    )
    bundle = run_trials(plan, world, args.output_dir)
    report = analyze_trials(bundle)
    payload = report.model_dump(mode="json")
    payload["run_directory"] = str(bundle.root)
    payload["status"] = (
        "SYMBOLIC_CELL_PLUMBING_PASS"
        if all(report.gates.values())
        else "SYMBOLIC_CELL_FAIL"
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    if args.require_gates and payload["status"] != "SYMBOLIC_CELL_PLUMBING_PASS":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
