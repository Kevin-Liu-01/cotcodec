#!/usr/bin/env python3
"""Build the top-level results.json of g3b-long-budget-v1 (EXPLORATORY) from analysis/results.json
(scripts/analyze_g3b_long_budget.py analyze, host CPU job), the pilot sizing record and the job
records below. Text-free.
Usage (from the evidence directory): python ops/build_results.py > results.json"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
# Physical GPU-seconds: Slurm RunTime x 1 H100 (jobs/*/scontrol.txt, builds/scontrol-build-*.txt).
JOBS: dict[str, dict[str, int]] = json.loads((HERE / "ops" / "jobs-gpu-seconds.json").read_text())
CAP = 2.5


def main() -> None:
    res = json.loads((HERE / "analysis" / "results.json").read_text())
    pilot = json.loads((HERE / "pilot" / "pilot.json").read_text())
    gpu = {k: round(sum(v.values()) / 3600, 4) for k, v in JOBS.items()}
    seconds = sum(sum(v.values()) for v in JOBS.values())
    out = {
        "experiment_id": res["experiment_id"],
        "claim_level": "exploratory",
        "checker": "G3's checker v2 (harness.g3_state_precision.math_equiv)",
        "gpu_hours_physical": gpu
        | {
            "total": round(seconds / 3600, 4),
            "total_gpu_seconds": seconds,
            "sum_of_rounded_rows": round(sum(gpu.values()), 4),
            "cap": CAP,
        },
        "jobs_gpu_seconds": JOBS,
        "partial_aa": "not run (the 2.5 GPU-h cap; README)",
        "pilot": pilot,
        "analysis": res,
    }
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
