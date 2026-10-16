#!/usr/bin/env python3
"""Build the top-level results.json of g3-state-precision-accuracy-v1 (EXPLORATORY) from
analysis/results.json (checker v2), analysis/extras.json, analysis/posthoc.json, the checker-v1
outputs and the job records below. Text-free.
Usage (from the evidence directory): python ops/build_results.py > results.json"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ARMS = ("fp32", "fp16", "bf16")
# Physical GPU-seconds: Slurm RunTime x 1 H100 (1527: the lane interval plus 2 s, its Slurm
# record expired before capture; the other jobs' RunTime is the lane interval plus 1-2 s).
JOBS = {
    "builds": {"1489": 66, "1493": 66, "1508": 65, "1529": 88},
    "pilot": {"1498": 588, "1500": 674},
    "main": {"1517": 2023, "1519": 2050, "1521": 2256, "1523": 1592, "1525": 1592, "1527": 1719},
    "lme_extra": {"1536": 291, "1538": 291, "1540": 288},
    "judge": {"1546": 170},
}
# Judge-label changes against fp32 on the same question (computed on the host from labels.json
# and the host-only judge input; ops/jobs.log).
LME_JUDGE_CHANGES = {
    "qwen3.5-4b": {"fp16": {"replies_differing": 3, "gained": 0, "lost": 0},
                   "bf16": {"replies_differing": 2, "gained": 1, "lost": 0}},
    "qwen3.5-9b": {"fp16": {"replies_differing": 6, "gained": 1, "lost": 0},
                   "bf16": {"replies_differing": 12, "gained": 1, "lost": 0}},
}  # fmt: skip


def pct(x: float) -> float:
    return round(100 * x, 2)


def main() -> None:
    res = json.loads((HERE / "analysis" / "results.json").read_text())
    post = json.loads((HERE / "analysis" / "posthoc.json").read_text())
    gpu = {k: round(sum(v.values()) / 3600, 4) for k, v in JOBS.items()}
    seconds = sum(sum(v.values()) for v in JOBS.values())
    extras = json.loads((HERE / "analysis" / "extras.json").read_text())
    v1 = json.loads((HERE / "checker-v1" / "analysis" / "results.json").read_text())
    out = {
        "experiment_id": res["experiment_id"],
        "claim_level": "exploratory",
        "checker": "v2 (harness.g3_state_precision.math_equiv; v1 outputs in checker-v1/)",
        "gpu_hours_physical": gpu
        | {
            "total": round(seconds / 3600, 4),
            "total_gpu_seconds": seconds,
            "sum_of_rounded_rows": round(sum(gpu.values()), 4),
            "cap": 4.0,
        },
        "jobs_gpu_seconds": JOBS,
        "bootstrap": res["bootstrap"],
        "equivalence_margin_points": 100 * res["equivalence_margin"],
        "judge_validation": res["judge_validation"],
        "cells": {},
        "throughput": res["throughput"],
        "posthoc_paired_lengths": post,
        "pooled_math_over_models": res.get("pooled_math"),
        "pilot_partial_aa": extras["aa_math"],
        "lme_pilot_aa": extras["aa_lme"],
        "capped_rollout_repetition": extras["repetition"],
        "checker_v1_math_accuracy_pct": {
            name: {a: pct(c["correct"][a]["mean"]) for a in ARMS}
            | {f"{a}_minus_fp32": pct(c["correct"][f"{a}_minus_fp32"]["diff"]) for a in ARMS[1:]}
            for name, c in v1["cells"].items()
            if name.endswith("/math")
        },
        "lme_judge_changes_vs_fp32": LME_JUDGE_CHANGES,
    }
    for name, cell in res["cells"].items():
        task = name.split("/")[1]
        scores = ["correct", "correct_g2b"] if task == "math" else ["judge_correct", "contains_answer"]
        entry: dict = {"accuracy_pct": {}, "shifts": {}}
        for key in scores:
            c = cell[key]
            entry["accuracy_pct"][key] = {"n_questions": c["n_questions"]} | {
                a: {"mean": pct(c[a]["mean"]), "ci95": [pct(x) for x in c[a]["ci95"]]} for a in ARMS
            } | {
                f"{a}_minus_fp32": {
                    "diff": pct(c[f"{a}_minus_fp32"]["diff"]),
                    "ci95": [pct(x) for x in c[f"{a}_minus_fp32"]["ci95"]],
                    "ci90": [pct(x) for x in c[f"{a}_minus_fp32"]["ci90"]],
                    "ci98_75_bonferroni_4": [pct(x) for x in c[f"{a}_minus_fp32"]["ci98_75"]],
                    "within_2pt_90": c[f"{a}_minus_fp32"].get("within_margin_90"),
                    "within_2pt_95": c[f"{a}_minus_fp32"].get("within_margin_95"),
                } for a in ARMS[1:]
            }  # fmt: skip
        for key in ("completion_len", "cap_hit", "time_cut", "has_answer", "says_idk"):
            c = cell.get(key) or {}
            if not c.get("n_questions"):
                continue
            entry["shifts"][key] = {a: round(c[a]["mean"], 4) for a in ARMS} | {
                f"{a}_minus_fp32": {"diff": round(c[f"{a}_minus_fp32"]["diff"], 4),
                                    "ci95": [round(x, 4) for x in c[f"{a}_minus_fp32"]["ci95"]]}
                for a in ARMS[1:]
            }  # fmt: skip
        entry["vs_fp32_tokens"] = cell["vs_fp32_tokens"]
        for extra in ("by_arm", "by_cap", "by_seed", "seed_heterogeneity"):
            if extra in cell:
                entry[extra] = cell[extra]
        out["cells"][name] = entry
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
