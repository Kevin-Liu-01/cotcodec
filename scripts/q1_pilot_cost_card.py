#!/usr/bin/env python3
"""Write the Q1 Stage 0 pilot cost card (CPU; ``harness/q1/cost_card.py``).

    python scripts/q1_pilot_cost_card.py \\
        --smoke-job RUNS/474 --pilot-job RUNS/NNN --corpus PREP/corpus \\
        --counts stage0-counts.json --out OUT

``--smoke-job`` and ``--pilot-job`` are lane run directories (each holds the
driver's ``q1/`` tree and the lane's ``job.env``/``termination.env``).
Outputs ``cost_card.json`` and ``cost_card.md``: per-gate GPU-seconds (median,
p95) of the scored items, per-kernel cost by rung, the c/b ratio, the measured
fixed phases, and the projected Stage 0 total against the 8 GPU-h cap with a
cluster-bootstrap interval, under the drafted design and under the trimming
rule's grid of mutant caps.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.q1 import cost_card as cc  # noqa: E402

FIDELITY_GATES = (
    "a_upstream_44130946",
    "a_upstream_423217d9",
    "b_native",
    "c1_kbv_compat",
    "c1_kbv_native",
)


def _env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    pairs = (line.partition("=") for line in path.read_text().splitlines())
    return {key: value for key, sep, value in pairs if sep}


def _phase(job: dict[str, Any], name: str) -> dict[str, Any] | None:
    return next((p for p in job["phases"]["phases"] if p["phase"] == name), None)


def survival_from(corpus: Path) -> dict[str, Any]:
    manifest = json.loads((corpus / "mutants" / "manifest.json").read_text())
    distinct = sum(s["cpu_distinct"] for s in manifest["substrates"])
    eligible = sum(s["eligible"] for s in manifest["substrates"])
    return {
        "cpu_distinct": distinct,
        "compile_distinct": eligible,
        "survival": eligible / distinct if distinct else 1.0,
        "selected": manifest["totals"]["selected"],
        "compile_checked": manifest["compile_checked"],
    }


def fixed_phases(
    smoke: dict[str, Any], pilot: dict[str, Any], counts: dict[str, Any], kinds: dict[str, Any]
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    root = Path(smoke["dir"])
    admission = _phase(smoke, "admission") or {}
    codegen = (
        [
            json.loads(line)
            for line in (root / "records-cuda" / "codegen_log.jsonl").read_text().splitlines()
            if line.strip()
        ]
        if (root / "records-cuda" / "codegen_log.jsonl").exists()
        else []
    )
    hook_rows = (
        [
            json.loads(line)
            for line in (root / "substrates-built" / "admission_hook.jsonl")
            .read_text()
            .splitlines()
            if line.strip()
        ]
        if (root / "substrates-built" / "admission_hook.jsonl").exists()
        else []
    )
    problems = len([r for r in codegen if r.get("status") not in {"excluded", "exists"}]) or 1
    hooked = len({r["kernel_id"] for r in hook_rows}) or 1
    hook_seconds = sum(r["wall_seconds"] for r in hook_rows) / 2  # two rows per substrate
    all_problems = 196
    built = (
        sum(counts["totals"]["evaluation_substrates"].values())
        + counts["totals"]["calibration_substrates"]
    )
    other = max(0.0, admission.get("seconds", 0.0) - hook_seconds)
    out["admission"] = {
        "measured_seconds": admission.get("seconds"),
        "codegen_problems": problems,
        "gpu_admitted_substrates": hooked,
        "codegen_and_build_seconds_per_problem": round(other / problems, 2),
        "gpu_admission_seconds_per_substrate": round(hook_seconds / hooked, 2),
        "projected_seconds": round(
            other / problems * all_problems + hook_seconds / hooked * built, 1
        ),
    }
    spec = _phase(smoke, "specializations") or {}
    n_spec = len(list((root / "specializations").glob("*/specializations.json"))) or 1
    eval_subs = sum(counts["totals"]["evaluation_substrates"].values())
    out["specializations"] = {
        "measured_seconds": spec.get("seconds"),
        "substrates": n_spec,
        "projected_seconds": round((spec.get("seconds") or 0.0) / n_spec * eval_subs, 1),
    }
    smoke_phase = sum(p.get("seconds", 0.0) for p in smoke["phases"]["phases"])
    out["smoke_job_driver_seconds"] = round(smoke_phase, 1)
    calibration_items = [i for i in pilot["items"] if i["phase"] == "calibration" and i["final"]]
    a1 = [i["gpu_seconds"] for i in calibration_items if i["gpu_seconds"] is not None]
    out["calibration"] = {
        "measured_items": len(a1),
        "a1_gpu_seconds": cc.summarize(a1),
        "projected_seconds": round(
            (statistics.fmean(a1) if a1 else 0.0) * counts["totals"]["calibration_substrates"], 1
        ),
    }
    fidelity_items = [i for i in pilot["items"] if i["phase"] == "fidelity" and i["final"]]
    per_kernel: dict[str, float] = {}
    for item in fidelity_items:
        if item["gate"] in FIDELITY_GATES and item["gpu_seconds"] is not None:
            per_kernel[item["kernel_id"]] = (
                per_kernel.get(item["kernel_id"], 0.0) + item["gpu_seconds"]
            )
    out["fidelity"] = {
        "kernels": len(per_kernel),
        "per_gate": cc.gate_stats(fidelity_items),
        "per_kernel_gpu_seconds": cc.summarize(list(per_kernel.values())),
    }
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--smoke-job", type=Path, required=True)
    parser.add_argument("--pilot-job", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--counts", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--spent-gpu-hours",
        type=float,
        required=True,
        help="GPU-h of every Stage 0 job so far (this pass), from the lane",
    )
    parser.add_argument("--timing-floor-gpu-hours", type=float, default=0.5)
    parser.add_argument("--replay-gpu-hours", type=float, default=0.5)
    parser.add_argument("--caps", default="40,24,16,12,8,6,4")
    parser.add_argument("--resamples", type=int, default=2000)
    args = parser.parse_args(argv)
    smoke = cc.load_job(args.smoke_job / "q1")
    pilot = cc.load_job(args.pilot_job / "q1")
    counts = json.loads(args.counts.read_text())
    kinds = cc.classify(args.corpus)
    survival = survival_from(args.corpus)
    scoring_items = [i for i in pilot["items"] if i["phase"] == "scoring"]
    smoke_items = [i for i in smoke["items"] if i["phase"] == "smoke"]
    kernel_rows = cc.kernel_seed_costs(scoring_items, kinds)
    means = cc.class_means(kernel_rows)
    fixed = fixed_phases(smoke, pilot, counts, kinds)
    rung = {name: cc.summarize([row[name] for row in kernel_rows]) for name in cc.RUNGS}
    b_cum = [row["a"] + row["b_marginal"] for row in kernel_rows]
    c_cum = [row["a"] + row["b_marginal"] + row["c_marginal"] for row in kernel_rows]
    ratio = {
        "median_c_cumulative_over_b_cumulative": (
            round(statistics.median(c_cum) / statistics.median(b_cum), 3) if b_cum else None
        ),
        "median_c_marginal_over_b_marginal": (
            round(
                statistics.median([r["c_marginal"] for r in kernel_rows])
                / statistics.median([r["b_marginal"] for r in kernel_rows]),
                3,
            )
            if kernel_rows
            else None
        ),
        "c_lite_trigger_2x": None,
    }
    if ratio["median_c_cumulative_over_b_cumulative"] is not None:
        ratio["c_lite_trigger_2x"] = ratio["median_c_cumulative_over_b_cumulative"] > 2.0
    fixed_hours = {
        "already_spent_this_pass": args.spent_gpu_hours,
        "admission_full": fixed["admission"]["projected_seconds"] / 3600,
        "specializations_full": fixed["specializations"]["projected_seconds"] / 3600,
        "calibration_full": fixed["calibration"]["projected_seconds"] / 3600,
        "timing_noise_floor_estimate": args.timing_floor_gpu_hours,
        "audit_hole_replay_cap": args.replay_gpu_hours,
    }
    scenarios = []
    for cap in (int(c) for c in args.caps.split(",")):
        stage = cc.stage0_kernel_counts(counts, cap=cap, survival=survival["survival"])
        seconds, borrowed = cc.scoring_seconds(stage["per_class"], means)
        interval = cc.bootstrap_scoring(kernel_rows, stage["per_class"], resamples=args.resamples)
        # Fidelity on every evaluation substrate and control plus the first mutant of
        # every substrate (the trimmed fidelity set), at replicate 42.
        fidelity_kernels = (
            stage["per_role"].get("substrate", 0)
            + stage["per_role"].get("identity-control", 0)
            + stage["per_role"].get("adversarial-control", 0)
            + stage["per_role"].get("substrate", 0)
        )
        fidelity_mean = fixed["fidelity"]["per_kernel_gpu_seconds"]["mean"] or 0.0
        fidelity_hours = fidelity_kernels * fidelity_mean / 3600
        fixed_total = sum(fixed_hours.values()) + fidelity_hours
        witnessed_test = {
            family: round(n * 0.5 * 0.5) for family, n in stage["mutants_per_family"].items()
        }
        scenarios.append(
            {
                "cap": cap,
                "kernels_per_replicate": stage["per_class"],
                "roles": stage["per_role"],
                "mutants_per_family": stage["mutants_per_family"],
                "scoring_gpu_hours": round(seconds / 3600, 3),
                "scoring_gpu_hours_95": {
                    k: (round(v / 3600, 3) if v is not None else None) for k, v in interval.items()
                },
                "fidelity_gpu_hours": round(fidelity_hours, 3),
                "fixed_gpu_hours": round(fixed_total, 3),
                "total_gpu_hours": round(fixed_total + seconds / 3600, 3),
                "total_gpu_hours_high": (
                    round(fixed_total + interval["high"] / 3600, 3)
                    if interval["high"] is not None
                    else None
                ),
                "borrowed_classes": borrowed,
                "precision_if_half_witnessed_half_test": {
                    family: {
                        "n": n,
                        "half_width_pp": round(100 * (cc.half_width(n) or 0), 1),
                    }
                    for family, n in witnessed_test.items()
                },
            }
        )
    card = {
        "schema": "q1-pilot-cost-card/1",
        "spent_gpu_hours": args.spent_gpu_hours,
        "smoke_job": str(args.smoke_job),
        "pilot_job": str(args.pilot_job),
        "per_gate_scoring": cc.gate_stats(scoring_items),
        "per_gate_smoke_identity": cc.gate_stats(smoke_items),
        "kernel_replicates_complete": len(kernel_rows),
        "kernel_replicate_cost_by_class": {
            klass: cc.summarize([r["total"] for r in kernel_rows if r["cost_class"] == klass])
            for klass in sorted({r["cost_class"] for r in kernel_rows})
        },
        "kernel_replicate_cost_by_role": {
            role: cc.summarize([r["total"] for r in kernel_rows if r["role"] == role])
            for role in sorted({r["role"] for r in kernel_rows})
        },
        "per_kernel_rung": rung,
        "c_over_b": ratio,
        "fixed_phases": fixed,
        "fixed_gpu_hours": fixed_hours,
        "compile_filter": survival,
        "scenarios": scenarios,
        "phases": {
            "smoke": smoke["phases"],
            "pilot": pilot["phases"],
        },
        "kernel_rows": kernel_rows,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "cost_card.json").write_text(
        json.dumps(card, indent=1, sort_keys=True, default=str)
    )
    lines = ["| gate | n | median GPU-s | p95 GPU-s | mean GPU-s |", "|---|---:|---:|---:|---:|"]
    for gate, stats in card["per_gate_scoring"].items():
        g = stats["gpu_seconds"]
        lines.append(f"| {gate} | {g['n']} | {g['median']} | {g['p95']} | {g['mean']} |")
    lines += [
        "",
        "| cap | scoring GPU-h | 95% | fixed GPU-h | total GPU-h | high |",
        "|---:|---:|---|---:|---:|---:|",
    ]
    for s in scenarios:
        band = s["scoring_gpu_hours_95"]
        lines.append(
            f"| {s['cap']} | {s['scoring_gpu_hours']} | {band['low']}-{band['high']} | "
            f"{s['fixed_gpu_hours']} | {s['total_gpu_hours']} | {s['total_gpu_hours_high']} |"
        )
    (args.out / "cost_card.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
