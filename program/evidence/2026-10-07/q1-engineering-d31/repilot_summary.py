"""Decision D31 evidence: one summary of the engineering pass's re-pilot (job 713) and the
recomputed Stage 0 projection. Recorded analysis script (pure Python).

    python repilot_summary.py RUN_DIR EVIDENCE_DIR

Reads the run directory (journals, summary, phases, termination record) and, from the
evidence folder, the recomputed cost card, the twin classification and the incident
count; writes ``repilot-713.json`` there.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

CAP = 8.0
SCENARIOS = (
    ("trim2-paired-concurrency", "no store (trim/2 as registered), fixed part with the re-pilot"),
    (
        "trim2-store-per-bucket-paired-concurrency",
        "store, pre-specified size-model ratio, references per bucket",
    ),
    (
        "trim2-store-per-job-paired-concurrency",
        "store, pre-specified size-model ratio, references once per job",
    ),
    (
        "trim2-store-constant-per-bucket-paired-concurrency",
        "store, post hoc constant ratio per gate, per bucket",
    ),
    (
        "trim2-store-constant-per-job-paired-concurrency",
        "store, post hoc constant ratio per gate, once per job",
    ),
    (
        "trim2-store-free-references-per-job-paired-concurrency",
        "bound of any store design: references free",
    ),
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    run, evidence = Path(sys.argv[1]), Path(sys.argv[2])
    card = json.loads((evidence / "cost-card-d31.json").read_text())
    twins = json.loads((evidence / "repilot-713-twins.json").read_text())
    incidents = json.loads((evidence / "repilot-713-incidents.json").read_text())
    slurm = (evidence / "slurm-713.txt").read_text()
    run_time = next(t for t in slurm.split() if t.startswith("RunTime="))
    h, m, s = (int(x) for x in run_time.removeprefix("RunTime=").split(":"))
    seconds = h * 3600 + m * 60 + s
    rp = card["repilot"]
    projections = []
    for name, label in SCENARIOS:
        t = next(x for x in card["trimmed"] if x["name"] == name)
        cum = {c["through"]: c for c in t["priority_cumulative_with_reserve"]}
        projections.append(
            {
                "scenario": name,
                "what": label,
                "fixed_gpu_hours": round(sum(t["fixed_gpu_hours"].values()), 3),
                "through_P3": {
                    "central": cum["P3"]["total_central"],
                    "high_uniform_scale": cum["P3"]["total_high"],
                    "high_bootstrap_direct": cum["P3"]["total_high_direct"],
                },
                "through_P7": {
                    "central": cum["P7"]["total_central"],
                    "high_uniform_scale": cum["P7"]["total_high"],
                    "high_bootstrap_direct": cum["P7"]["total_high_direct"],
                },
                "reference_items_gpu_hours": t["gpu_hours_by_role"].get("reference-items"),
                "reference_store": t.get("reference_store"),
                "stop": t["budget_stop"],
                "high_through_P3_within_8": max(
                    cum["P3"]["total_high"], cum["P3"]["total_high_direct"]
                )
                <= CAP,
            }
        )
    files = {
        name: sha(run / "q1" / "repilot" / name)
        for name in ("journal.jsonl", "references.jsonl", "items.jsonl")
    }
    files.update(
        {
            "q1/summary.json": sha(run / "q1" / "summary.json"),
            "q1/phases.json": sha(run / "q1" / "phases.json"),
            "termination.env": sha(run / "termination.env"),
            "manifest.json": sha(run / "manifest.json"),
        }
    )
    report = {
        "schema": "q1-d31-repilot/1",
        "decision": "D31",
        "label": "re-pilot, infrastructure and cost (not Stage 0 data)",
        "job": {
            "slurm_job": 713,
            "state": "COMPLETED",
            "exit": "0:0",
            "run_seconds": seconds,
            "gpus": 1,
            "gpu_hours": round(seconds / 3600, 4),
            "cap_gpu_hours": 0.5,
            "image": "cotcodec-q1-gates:8e9d2574",
            "image_build": "CPU-only Slurm job 710 from a fresh clone of the branch bundle",
            "git_sha": "8e9d2574a3332114109e6b21bd0d041a9868b471",
            "lane_termination": (run / "termination.env").read_text().splitlines()[1],
        },
        "rule": "q1-repilot/1 (harness/q1/repilot.py)",
        "problems": rp["summary"]["problems"],
        "kernels": 24,
        "items_planned": incidents["runner_summary"]["items"],
        "items_run": incidents["runner_summary"]["run"],
        "per_gate_pairs_final_in_both_arms": rp["summary"]["per_gate"],
        "constant_ratios_same_mode_pairs": rp["store_model"]["constant_ratios_same_mode_pairs"],
        "reference_items_gpu_seconds": rp["summary"]["reference_items"],
        "pairs": rp["summary"]["pairs"],
        "pairs_same_mode": rp["store_model"]["pairs_same_mode"],
        "inline_gpu_seconds_all_pairs": rp["summary"]["inline_gpu_seconds_all_pairs"],
        "store_gpu_seconds_all_pairs_with_references": rp["summary"][
            "store_gpu_seconds_all_pairs_with_references"
        ],
        "twin_rows": {k: v for k, v in twins.items() if k != "differing"},
        "incidents": incidents["totals"],
        "incidents_runner": incidents["runner_summary"],
        "projection": projections,
        "admission_under_D31": {
            "rule": "Stage 0 is admitted only if the high estimate is within 8 GPU-h",
            "high_through_P3_within_8_in_any_scenario": any(
                p["high_through_P3_within_8"] for p in projections
            ),
        },
        "run_files_sha256": files,
    }
    (evidence / "repilot-713.json").write_text(json.dumps(report, indent=1, sort_keys=True))
    for p in projections:
        print(p["scenario"], p["through_P3"], p["high_through_P3_within_8"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
