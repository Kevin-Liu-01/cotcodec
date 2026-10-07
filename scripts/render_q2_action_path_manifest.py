#!/usr/bin/env python3
"""Render one scored q2-action-path-v1 campaign manifest (acceptance, scored control or A5).

After the owner's freeze, every scored campaign of the preregistration (A1-A6, the
concurrency ladder, C1-C3) runs from a manifest that ``harness/q2/vm/manifest.py`` admits
only when the ledger freezes the preregistration and the addenda it needs. This script
fills such a manifest from a local export of the frozen commit (``--source-dir``): the
ledger's digests, the source tree digest, the realized order's session and trial counts
(``driver.acceptance_plan``, or ``driver.session_plan`` for A6) and a Slurm time limit from
the lane's own worst-case budget. It then validates the result with the ledger, exactly as
the submitter will, and refuses before the freeze. A5's boot-reset campaign is rendered as
the infrastructure validation it is (21 cold boots, 20 reset checks) at the frozen SHA.

    python3 scripts/render_q2_action_path_manifest.py A1 --seed 43 --source-dir EXPORT \\
        --git-sha SHA --out experiments/manifests/q2-action-path/a1-seed43-a1.yaml

The VM, runner and image pins come from ``TEMPLATE`` (the last development manifest at the
candidate executor), which carries the preregistration's section 2.1 pins.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.q2.vm import driver  # noqa: E402
from harness.q2.vm.manifest import (  # noqa: E402
    ADDENDA_IDS,
    CANARY_APPS,
    CRITERIA,
    PREREG_ID,
    ManifestError,
    executor_addendum,
    ladder_reps,
    ledger_paths,
    ledger_view,
    runner_cpus,
    source_tree_sha256,
    validate_manifest,
)

TEMPLATE = PROJECT_ROOT / "experiments/manifests/q2-action-path/dev-l0-fixed-v10.yaml"
PREREG_PATHS = {
    PREREG_ID: "program/preregistrations/q2-action-path-v1.md",
    ADDENDA_IDS["inputs"]: "program/preregistrations/q2-action-path-v1-inputs.md",
    ADDENDA_IDS["executor"]: "program/preregistrations/q2-action-path-v1-executor.md",
}
CELLS = "harness/q2/action_path/suite_cells.json"
VOLUME_PLAN = "harness/q2/action_path/volume_plan.json"
HOST_ROOT = "/home/kevin/cotcodec-runs/stage0/q2-action-path"
MAX_MINUTES = 1440
CHOICES = (*CRITERIA, "A6", "A5")


def ledger_rows(source_dir: Path) -> dict[str, dict[str, str]]:
    return ledger_view(str(source_dir), [])["rows"]


def _minutes(seconds: float) -> int:
    return int(math.ceil(seconds / 60.0 / 10.0) * 10)


def render(args: argparse.Namespace) -> dict[str, Any]:
    import yaml

    source_dir = Path(args.source_dir)
    template = yaml.safe_load(TEMPLATE.read_text(encoding="utf-8"))
    rows = ledger_rows(source_dir)
    if PREREG_ID not in rows:
        raise ManifestError(f"{PREREG_ID} is not frozen in the ledger of {source_dir}")
    concurrency = args.concurrency
    # Section 9: the runner CPUs are registered per concurrency, not chosen per campaign.
    cpus_for_runners = runner_cpus(concurrency) if args.runner_cpus is None else args.runner_cpus
    manifest: dict[str, Any] = {
        "schema": template["schema"],
        "name": args.name,
        "campaign_id": args.campaign_id,
        "experiment_id": PREREG_ID,
        "purpose": "infrastructure-validation" if args.criterion == "A5" else "acceptance",
        "preregistration": {
            "path": PREREG_PATHS[PREREG_ID],
            "status": "frozen",
            "sha256": rows[PREREG_ID]["sha256"],
        },
        "git_sha": args.git_sha,
        "source": {
            "host_dir": f"{HOST_ROOT}/src/{args.git_sha}",
            "tree_sha256": source_tree_sha256(str(source_dir)),
        },
        "run_root": template["run_root"],
        "slurm": {},
        "container_profile": template["container_profile"],
        "model": {
            "kind": "none",
            "reason": "scored action-path campaigns run the executor and harness parsers, no model",
        },
        "randomness": {},
        "vm": dict(copy.deepcopy(template["vm"]), concurrency=concurrency),
        "runner": dict(template["runner"], cpus=cpus_for_runners),
    }
    cells_bytes = (source_dir / CELLS).read_bytes()
    cells = json.loads(cells_bytes)
    common = {
        "boot_timeout_s": 300,
        "settle_timeout_s": 60,
        "cells_sha256": hashlib.sha256(cells_bytes).hexdigest(),
        "max_trial_s": args.max_trial_s,
    }
    if args.criterion == "A5":
        manifest["randomness"] = {"contract": "deterministic", "seeds": []}
        manifest["workload"] = {
            "kind": "boot-reset-validation",
            "cycles": 21,
            "boot_timeout_s": 300,
            "settle_timeout_s": 60,
            "hmp_input_check": True,
            "latency_reps": 3,
            "exposure_probe": False,
        }
        budget = 600 + 21 * (300 + 60 + 120)
    else:
        manifest["randomness"] = {
            "contract": "seeded",
            "seeds": [args.seed],
            "seed_binding": {"flag": "--seed"},
        }
        # The inputs addendum, and the executor addendum of this repair attempt once frozen
        # (C2 runs before the executor freeze; manifest.check_ledger enforces what each needs).
        executor_id, executor_path = executor_addendum(args.attempt)
        pins = {
            "inputs": (ADDENDA_IDS["inputs"], PREREG_PATHS[ADDENDA_IDS["inputs"]]),
            "executor": (executor_id, executor_path),
        }
        manifest["addenda"] = {
            key: {"path": path, "sha256": rows[experiment]["sha256"]}
            for key, (experiment, path) in pins.items()
            if experiment in rows
        }
        if args.criterion == "A6":
            workload = {"kind": "canary-acceptance", "apps": list(CANARY_APPS), "reps": 5}
            workload.update(common, attempt=args.attempt, session_trials=60)
            manifest["workload"] = workload
            plan = driver.session_plan(manifest, cells)
        else:
            layers, _, reps, settings, cell_set, _ = CRITERIA[args.criterion]
            layer = args.layer or layers[0]
            reps_value = ladder_reps(concurrency) if reps == "rung" else reps[0]
            workload = {
                "kind": "suite-acceptance",
                "criterion": args.criterion,
                "layer": layer,
                "reps": reps_value,
                "settings": ["screenshot", "screenshot+a11y"] if settings == "both" else [settings],
                "cells": cell_set,
                "mutant": args.mutant,
                "session_range": args.session_range,
                "attempt": args.attempt,
                "session_trials": 60,
            }
            workload.update(common)
            manifest["workload"] = workload
            volume_plan = json.loads((source_dir / VOLUME_PLAN).read_text(encoding="utf-8"))
            plan = driver.acceptance_plan(manifest, cells, volume_plan)
        manifest["workload"]["sessions"] = len(plan)
        manifest["workload"]["trials"] = sum(len(s["trials"]) for s in plan)
        budget = (
            600
            + (len(plan) * (300 + 60 + 240) + manifest["workload"]["trials"] * args.max_trial_s)
            / concurrency
        )
    minutes = _minutes(budget)
    if minutes > MAX_MINUTES:
        raise ManifestError(
            f"worst-case budget {minutes} min exceeds {MAX_MINUTES}: split with --session-range"
        )
    manifest["slurm"] = {
        "cpus": concurrency * manifest["vm"]["cpu_cores"] + cpus_for_runners,
        "memory_gb": max(12, concurrency * (manifest["vm"]["memory_gb"] + 1) + 2),
        "minutes": minutes,
    }
    ledger = None
    if manifest["purpose"] == "acceptance":
        ledger = ledger_view(str(source_dir), ledger_paths(manifest))
    return validate_manifest(manifest, ledger)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("criterion", choices=CHOICES)
    parser.add_argument("--source-dir", required=True, help="local export of the frozen commit")
    parser.add_argument("--git-sha", required=True)
    parser.add_argument("--seed", type=int, default=43)
    parser.add_argument("--layer")
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument(
        "--runner-cpus", type=int, default=None, help="default: manifest.runner_cpus(N)"
    )
    parser.add_argument("--session-range", type=int, nargs=2, default=None)
    parser.add_argument("--mutant", default=None)
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument("--max-trial-s", type=int, default=30)
    parser.add_argument("--name", default="q2ap-accept")
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.session_range is not None:
        args.session_range = list(args.session_range)
    return args


def main(argv: list[str] | None = None) -> int:
    import yaml

    args = parse_args(argv)
    try:
        manifest = render(args)
    except ManifestError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    header = (
        f"# q2-action-path-v1 {args.criterion} (seed {args.seed}, attempt {args.attempt}), "
        "rendered by scripts/render_q2_action_path_manifest.py\n"
    )
    args.out.write_text(
        header + yaml.safe_dump(manifest, sort_keys=False, width=100), encoding="utf-8"
    )
    print(json.dumps({"out": str(args.out), "sessions": manifest["workload"].get("sessions"),
                      "minutes": manifest["slurm"]["minutes"]}))  # fmt: skip
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
