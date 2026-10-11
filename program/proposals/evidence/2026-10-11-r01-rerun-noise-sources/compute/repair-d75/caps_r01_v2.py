#!/usr/bin/env python3
"""Registered caps for r01-rerun-noise-sources-v2 (section 11), repriced from S1a's realized costs.

Every price is arithmetic on S1a's own per-step records (the committed A0 digest table, 4B
H-OSW-fixed, steps 1 and 2) through ``harness.r01.caps``; loaded passes are simulated as the
maximum over 20 lanes (95th percentile of 20,000 draws, seed 42), not one lane's mean. The
corpus counts are the registration's: 113 tasks, 226 step-1 pairs (two A1 boot pairs per task)
and 113 step-2 pairs (one per task); probe items 40 step-1 and 20 step-2.

Usage (worktree root): uv run --locked python <this> --out caps-r01-v2.json
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path

from harness.r01 import caps

ROOT = Path(__file__).resolve().parents[6]
DIGESTS = ROOT / "program/evidence/2026-10-11/r01-stage-a0/s1a-step-digests.jsonl.gz"
A1 = ROOT / "program/evidence/2026-10-10/q2-stage1-analysis/a1.jsonl"
P1, P2 = 226, 113  # step-1 and step-2 request pairs
PROBE1, PROBE2 = 40, 20


def jobs() -> list[caps.Job]:
    return [
        caps.Job(
            "P0",
            "E-det, then E-s1a",
            "self-test: probe x 3 passes + 1 without logprobs (E-det); one loaded pass (E-s1a)",
            engine_starts=2,
            batch1={1: 4 * PROBE1, 2: 4 * PROBE2},
            loaded_counts={1: PROBE1, 2: PROBE2},
            loaded_passes=1,
        ),
        caps.Job(
            "P0'",
            "E-det + VLLM_BATCH_INVARIANT=1",
            "self-test repeated (if P0 shows any difference)",
            conditional=True,
            batch1={1: 4 * PROBE1, 2: 4 * PROBE2},
        ),
        caps.Job(
            "J1",
            "E-det",
            "step 1: R, R' (replica), C, O, X on 226 pairs; step 2: R2, R2', C2, O2, X2 on 113 pairs",
            batch1={1: 5 * P1, 2: 5 * P2},
        ),
        caps.Job(
            "J1b",
            "E-det",
            "blink-off non-clock cell (if A1 reads MULTI_REGION with caret-like components >= half): R', O' on 113 pairs",
            conditional=True,
            batch1={1: 2 * P2},
        ),
        caps.Job(
            "J2",
            "E-c1",
            "cache channel: R cold + warm on 226 step-1 pairs",
            batch1={1: P1},
            warm={1: P1},
        ),
        caps.Job(
            "J3",
            "E-s1a",
            "5 loaded passes: R+R2, R+R2, C+C2, O+O2, X+X2 (226 step-1 + 113 step-2 items each)",
            loaded_counts={1: P1, 2: P2},
            loaded_passes=5,
        ),
        caps.Job(
            "J4",
            "E-nc",
            "batch channel: 2 loaded passes of R+R2",
            loaded_counts={1: P1, 2: P2},
            loaded_passes=2,
        ),
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    with gzip.open(DIGESTS, "rt") as handle:
        rows = [json.loads(x) for x in handle]
    costs = caps.step_costs(rows, (1, 2))
    table = [j.row(costs) for j in jobs()]
    # overrun probability at the registered cap for the purely loaded jobs (high latency scale)
    for job, row in zip(jobs(), table, strict=True):
        if job.loaded_passes and not job.batch1 and not job.warm:
            sim = caps.simulate_loaded(
                costs, job.loaded_counts, job.loaded_passes, scale=caps.HIGH_LATENCY_SCALE, seed=43
            )
            avail = (
                row["cap_min"] - caps.LEAD_MIN - caps.ENGINE_START_MIN * job.engine_starts
            ) * 60
            row["overrun_probability_at_cap_high_latency"] = float((sim > avail).mean())
            row["work_available_s_at_cap"] = avail
            row["sim_check_seed43_high"] = {
                "mean_s": round(float(sim.mean()), 1),
                "max_s": round(float(sim.max()), 1),
            }
    total = sum(r["cap_min"] for r in table)
    core = sum(r["cap_min"] for r in table if not r["conditional"])
    recs = [json.loads(x) for x in A1.read_text().splitlines()]
    r4 = [r for r in recs if r["size"] == "4B" and r["harness"] == "H-OSW-fixed"]
    import numpy as np

    overhead = np.array(
        [
            r["host"]["slot_occupancy_s"]
            - r["timings"].get("steps_s", 0)
            - r["timings"].get("settle_before_eval_s", 0)
            - r["timings"].get("evaluate_s", 0)
            - r["timings"].get("capture_s", 0)
            for r in r4
        ]
    )
    occ = np.array([r["host"]["slot_occupancy_s"] for r in r4])
    step1_lat = costs[1].latency_mean_s
    # A1: 678 boots. Every boot: S1a's realized overhead to the first observation (boot, setup,
    # warm-up, 60 s settle, container start and teardown) + 1.2 s of frames; b3 adds the 61 s
    # late frame; b1/b2 add one open-loop step (step-1 latency + execute + screenshot + 0.6 s f1).
    boots = {
        "default_b1_b2": 2 * 113,
        "default_b3": 113,
        "default_b4": 113,
        "blink_off_b5_b6": 2 * 113,
    }
    extra = {
        "default_b1_b2": 1.2 + step1_lat + 1.5 + 0.6,
        "default_b3": 1.2 + 61.0,
        "default_b4": 1.2,
        "blink_off_b5_b6": 1.2 + 2.0,
    }
    a1_c = sum(n * (overhead.mean() + extra[k]) for k, n in boots.items()) / 3600
    a1_h = sum(n * (overhead.max() + extra[k]) for k, n in boots.items()) / 3600
    c_c, c_h = 452 * 2 * occ.mean() / 3600, 452 * 2 * np.quantile(occ, 0.95) / 3600
    cb_c = 113 * 2 * occ.mean() / 3600
    out = {
        "schema": "r01-caps-v2",
        "inputs": {
            "digests_sha256": hashlib.sha256(DIGESTS.read_bytes()).hexdigest(),
            "a1_jsonl_sha256": hashlib.sha256(A1.read_bytes()).hexdigest(),
            "step_costs": {
                k: {
                    "prompt_tokens_mean": round(c.prompt_tokens_mean, 1),
                    "latency_mean_s": round(c.latency_mean_s, 4),
                    "latency_p95_s": round(c.latency_p95_s, 4),
                    "n": len(c.latencies_s),
                    "batch1_central_s": round(c.batch1(False), 4),
                    "batch1_high_s": round(c.batch1(True), 4),
                    "warm_central_s": round(c.warm(False), 4),
                    "warm_high_s": round(c.warm(True), 4),
                }
                for k, c in costs.items()
            },
            "think_mean_s_J3": round(caps.think_mean(costs, {1: P1, 2: P2}), 3),
        },
        "cap_rule": {
            "lead_min": caps.LEAD_MIN,
            "engine_start_min": caps.ENGINE_START_MIN,
            "dr4": caps.F_DR4,
            "requeue": caps.F_REQ,
            "reset_s_per_request": caps.RESET_S,
            "reset_s_per_pass": caps.PASS_RESET_S,
            "prefill_central_tok_s": caps.PREFILL_CENTRAL_TOK_S,
            "high_latency_scale_loaded": caps.HIGH_LATENCY_SCALE,
            "loaded_quantile": 0.95,
            "sim_draws": caps.SIM_DRAWS,
            "sim_seed": caps.SIM_SEED,
        },
        "jobs": table,
        "total_cap_min": total,
        "total_cap_gpu_h": round(total / 60, 3),
        "total_cap_min_without_conditional": core,
        "total_cap_gpu_h_without_conditional": round(core / 60, 3),
        "physical_gpu_h_central": round(sum(r["physical_gpu_h_central"] for r in table), 3),
        "d22_line_gpu_h": 8.0,
        "wave1_comparison": {
            "J3_wave1_cap_min": 26,
            "J3_wave1_rule": "one lane's mean (16 x (latency + 11.9 s)) x 4 passes",
            "wave1_total_cap_gpu_h": 4.217,
        },
        "cpu_lane": {
            "a1_boots": sum(boots.values()),
            "a1_vm_h_central": round(a1_c, 2),
            "a1_vm_h_high": round(a1_h, 2),
            "stage_c_vm_h_central": round(c_c, 2),
            "stage_c_vm_h_high": round(c_h, 2),
            "stage_c_blink_conditional_vm_h": round(cb_c, 2),
            "overhead_to_first_observation_s": {
                "mean": round(float(overhead.mean()), 1),
                "max": round(float(overhead.max()), 1),
            },
            "wall_h_at_V20_high": round((a1_h + c_h + cb_c) / 20, 2),
            "gpu_h": 0.0,
        },
    }
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    for r in table:
        print(f"{r['job']:5s} cap {r['cap_min']:4d} min  {r['arithmetic']}")
    print(
        "total",
        total,
        "min =",
        round(total / 60, 3),
        "GPU-h; without conditional",
        core,
        "=",
        round(core / 60, 3),
    )
    print(json.dumps(out["cpu_lane"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
