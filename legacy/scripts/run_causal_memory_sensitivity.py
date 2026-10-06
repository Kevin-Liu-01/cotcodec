#!/usr/bin/env python3
"""Run and aggregate the three registered symbolic propensity cells."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
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

PROPENSITIES = (0.5, 0.25, 0.1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--episodes", type=int, default=2_000)
    parser.add_argument("--world-seed", type=int, default=7)
    parser.add_argument("--assignment-seed", type=int, default=42)
    parser.add_argument("--audit-fraction", type=float, default=0.25)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--require-gates", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit(f"refusing to overwrite non-empty directory: {args.output_dir}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    world = SymbolicTrialWorld.generate(args.episodes, args.world_seed)
    cells: dict[str, dict] = {}
    for propensity in PROPENSITIES:
        plan = make_symbolic_plan(
            world,
            assignment_seed=args.assignment_seed,
            audit_fraction=args.audit_fraction,
            propensity=propensity,
            folds=args.folds,
        )
        bundle = run_trials(
            plan,
            world,
            args.output_dir / f"propensity-{propensity}",
        )
        cells[str(propensity)] = analyze_trials(bundle).model_dump(mode="json")

    aipw_audit = [cell["aipw_audit_average_effect"] for cell in cells.values()]
    policy_value = [cell["learned_policy_success"] for cell in cells.values()]
    gates = {
        "every_cell_passes": all(
            all(cell["gates"].values()) for cell in cells.values()
        ),
        "aipw_audit_effect_stable": max(aipw_audit) - min(aipw_audit) <= 0.10,
        "policy_value_stable": max(policy_value) - min(policy_value) <= 0.05,
        "paired_oracle_identical": len(
            {cell["paired_oracle_average_effect"] for cell in cells.values()}
        )
        == 1,
    }
    payload = {
        "schema_version": "1.0",
        "study": "causal-memory-symbolic-propensity-sensitivity",
        "status": (
            "SYMBOLIC_SENSITIVITY_PLUMBING_PASS"
            if all(gates.values())
            else "SYMBOLIC_SENSITIVITY_FAIL"
        ),
        "episodes": args.episodes,
        "world_seed": args.world_seed,
        "assignment_seed": args.assignment_seed,
        "audit_fraction": args.audit_fraction,
        "propensities": list(PROPENSITIES),
        "cells": cells,
        "gates": gates,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload["payload_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    manifest_path = args.output_dir / "sensitivity-manifest.json"
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    with manifest_path.open("xb", buffering=0) as handle:
        handle.write(encoded)
        os.fsync(handle.fileno())
    print(json.dumps(payload, indent=2, sort_keys=True))
    if args.require_gates and payload["status"] != "SYMBOLIC_SENSITIVITY_PLUMBING_PASS":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
