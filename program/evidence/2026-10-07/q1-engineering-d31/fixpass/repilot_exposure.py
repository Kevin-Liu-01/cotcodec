#!/usr/bin/env python3
"""Exposure ledger entry for the D31 re-pilot (Slurm 713): which kernels it scored and
which split half they belong to (D31 review, finding 6). CPU only.

    python program/evidence/2026-10-07/q1-engineering-d31/fixpass/repilot_exposure.py \\
        --items RUN713/q1/repilot/items.jsonl --out repilot-713-exposure.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from harness.q1 import controls, problems, trim  # noqa: E402
from harness.q1.substrates import s2_catalog  # noqa: E402
from harness.q1.substrates import split as s1_split  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--items", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    planned = [json.loads(x) for x in args.items.read_text().splitlines() if x.strip()]
    kernels = sorted(
        {
            (i["kernel_id"].removesuffix(".store"), i["problem_id"])
            for i in planned
            if not i["gate"].startswith("ref_")
        }
    )
    split = s1_split.calibration_split(problems.list_problem_ids(include_excluded=True), seed=42)
    calibration, evaluation = set(split["calibration"]), set(split["evaluation"])
    s2 = {e.problem_id for e in s2_catalog.CATALOG}
    identity = set(controls.identity_problems())
    exposed = trim.load_exposed()
    exposed_text = json.dumps(exposed)
    rows = []
    for kernel_id, problem_id in kernels:
        rows.append(
            {
                "kernel_id": kernel_id,
                "problem_id": problem_id,
                "s1_half": "calibration"
                if problem_id in calibration
                else "evaluation"
                if problem_id in evaluation
                else None,
                "problem_has_s2_substrate": problem_id in s2,
                "problem_has_identity_control_in_frame": problem_id in identity,
                "in_pilot_exposed": kernel_id in exposed_text or problem_id in exposed_text,
            }
        )
    record = {
        "schema": "q1-exposure-ledger-entry/1",
        "job": 713,
        "rule": "q1-repilot/1",
        "replicate": 42,
        "what": "every scoring gate and audit channel, inline and through the reference store",
        "items_sha256": hashlib.sha256(args.items.read_bytes()).hexdigest(),
        "s1_split_sha256": split["sha256"],
        "kernels": rows,
        "summary": {
            "kernels": len(rows),
            "problems": len({r["problem_id"] for r in rows}),
            "s1_calibration": sum(1 for r in rows if r["s1_half"] == "calibration"),
            "s1_evaluation": sum(1 for r in rows if r["s1_half"] == "evaluation"),
            "with_s2_substrate": sum(1 for r in rows if r["problem_has_s2_substrate"]),
            "in_pilot_exposed": sum(1 for r in rows if r["in_pilot_exposed"]),
        },
        "consequence": (
            "No evaluation unit was scored. The S1 calibration substrates of these eight "
            "problems now have known verdicts under the full stack at replicate 42; Stage 0's "
            "audit calibration (section 6.1) runs on S1-cal substrates, so its report lists "
            "these eight as re-pilot-exposed. Mutants of S1-cal parents stay unscored in "
            "Stage 0 (sections 3.3 and 3.5)."
        ),
    }
    args.out.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    print(json.dumps(record["summary"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
