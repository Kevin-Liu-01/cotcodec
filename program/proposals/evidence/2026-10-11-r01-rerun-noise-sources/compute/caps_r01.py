#!/usr/bin/env python3
"""Compute caps for R01's first step (draft registration r01-rerun-noise-sources-v1, section 10).

Standard library only. Inputs: the committed Stage A0 digests (per-step prompt and completion
tokens and latencies of S1a's 4B H-OSW-fixed episodes) and a1.jsonl (slot occupancy).

Cap rule (the Q2 design study's realized-cost rule, adopted explicitly here; S1a's registered
c_proj does not apply because Stage B runs no VMs):

    job cap (min) = ceil(3 min USR1 lead + L engine start + W work x 1.2 (DR4) x 1.05 (re-queue))

with W at the HIGH per-request price. The P0 probe measures the real price first (as D20 did); if
P0's measured price times any job's request count exceeds that job's cap, the job is not
submitted and the registration is amended before freeze-time caps are exceeded (no overrun).
The 8 GPU-h line of D20/D22 is read on the sum of the registered caps, whatever runs.

Usage: python3 caps_r01.py --out caps-r01.json
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
DIGESTS = ROOT / "program/evidence/2026-10-11/r01-stage-a0/s1a-step-digests.jsonl.gz"
A1 = ROOT / "program/evidence/2026-10-10/q2-stage1-analysis/a1.jsonl"

LEAD_MIN = 3.0
ENGINE_START_MIN = 2.0  # S1a engine start measured 95-98 s (bridge samples); rounded up
F_DR4, F_REQ = 1.2, 1.05
CORPUS_EPISODES, CORPUS_STEPS = 40, 8
N = CORPUS_EPISODES * CORPUS_STEPS  # 320 requests
PROBE_REQ, PROBE_PASSES = 40, 3
STREAMS, THINK_S = 20, 11.9  # 20 streams; think time chosen so mean in-flight is about 3.7


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    rows = [json.loads(x) for x in gzip.open(DIGESTS, "rt")]
    r4 = [r for r in rows if r["size"] == "4B" and r["harness"] == "H-OSW-fixed"]
    steps18 = [s for r in r4 if len(r["steps"]) >= CORPUS_STEPS for s in r["steps"][:CORPUS_STEPS]]
    p_tok = st.mean(s["ptok"] for s in steps18)
    c_tok = st.mean(s["ctok"] for s in steps18)
    lat = st.mean(s["lat"] for s in steps18)
    s1 = [r["steps"][0] for r in r4]
    # Prefill rate from step 1 (uncached image plus instruction, about 2.4k tokens, at median ttft)
    ttft1 = st.median(s["ttft"] for s in s1)
    rate_central = 2400 / ttft1
    price = {
        "inputs": {"corpus_mean_prompt_tokens": round(p_tok), "corpus_mean_completion_tokens": round(c_tok),
                   "corpus_mean_s1a_latency_s": round(lat, 3), "step1_median_ttft_s": ttft1,
                   "prefill_rate_central_tok_s": round(rate_central), "prefill_rate_high_tok_s": round(rate_central / 2),
                   "tpot_central_s": 0.0046, "tpot_high_s": 0.0055,
                   "episodes_with_8_or_more_steps": sum(len(r["steps"]) >= CORPUS_STEPS for r in r4)},
    }
    b1_central = p_tok / rate_central + c_tok * 0.0046
    b1_high = p_tok / (rate_central / 2) + c_tok * 0.0055
    hit_central = 0.05 + c_tok * 0.0046
    hit_high = 0.10 + c_tok * 0.0055
    lat_load_central, lat_load_high = lat, lat * 1.25
    lat_nocache_central = lat + p_tok / rate_central
    lat_nocache_high = lat * 1.25 + p_tok / (rate_central / 2)
    per_stream = N // STREAMS  # 16 requests per stream per pass

    def batched_pass(latency: float) -> float:
        return per_stream * (latency + THINK_S)

    price["per_request_s"] = {"batch1_nocache": [round(b1_central, 3), round(b1_high, 3)],
                              "batch1_cache_hit": [round(hit_central, 3), round(hit_high, 3)],
                              "loaded_cache_latency": [round(lat_load_central, 3), round(lat_load_high, 3)],
                              "loaded_nocache_latency": [round(lat_nocache_central, 3), round(lat_nocache_high, 3)]}
    jobs = []

    def job(name: str, arms: str, work_c_s: float, work_h_s: float, conditional: bool = False) -> None:
        cap = math.ceil(LEAD_MIN + ENGINE_START_MIN + (work_h_s / 60) * F_DR4 * F_REQ)
        phys_c = (work_c_s / 60 + ENGINE_START_MIN) / 60
        phys_h = (work_h_s / 60 + ENGINE_START_MIN) / 60
        jobs.append({"job": name, "arms": arms, "work_min_central": round(work_c_s / 60, 1),
                     "work_min_high": round(work_h_s / 60, 1), "cap_min": cap, "cap_gpu_h": round(cap / 60, 3),
                     "physical_gpu_h_central": round(phys_c, 3), "physical_gpu_h_high": round(phys_h, 3),
                     "conditional": conditional,
                     "arithmetic": f"ceil({LEAD_MIN} + {ENGINE_START_MIN} + {work_h_s / 60:.1f} x {F_DR4} x {F_REQ}) = {cap}"})

    job("P0 probe and bitwise self-test", f"{PROBE_REQ} requests x {PROBE_PASSES} passes, deterministic reference",
        PROBE_REQ * PROBE_PASSES * b1_central, PROBE_REQ * PROBE_PASSES * b1_high)
    job("P0' probe rerun with VLLM_BATCH_INVARIANT=1 (if P0 shows any difference)",
        f"{PROBE_REQ} requests x {PROBE_PASSES} passes", PROBE_REQ * PROBE_PASSES * b1_central,
        PROBE_REQ * PROBE_PASSES * b1_high, conditional=True)
    job("J1 deterministic session", f"B0 (2 passes), B2 clock swap, B4 mask: 4 x {N} requests interleaved",
        4 * N * b1_central, 4 * N * b1_high)
    job("J1o other-region swap (in J1's session when A1 reads MULTI_REGION)", f"B2o: {N} requests",
        N * b1_central, N * b1_high, conditional=True)
    job("J2 batch-1 prefix cache on", f"B5: {N} cold + {N} warm", N * (b1_central + hit_central), N * (b1_high + hit_high))
    job("J3 S1a configuration", "B1 (3 passes) and B3 clock swap (1 pass), 20 streams, cache reset per pass",
        4 * batched_pass(lat_load_central), 4 * batched_pass(lat_load_high))
    job("J4 batched, prefix cache off", "B6 (2 passes), 20 streams", 2 * batched_pass(lat_nocache_central),
        2 * batched_pass(lat_nocache_high))
    total_cap = sum(j["cap_min"] for j in jobs)
    total_cap_core = sum(j["cap_min"] for j in jobs if not j["conditional"])
    # CPU lane (0 GPU-h): Stage A1 captures and Stage C replays, at V = 20
    occ = [json.loads(x)["host"]["slot_occupancy_s"] for x in A1.read_text().splitlines()
           if json.loads(x)["size"] == "4B" and json.loads(x)["harness"] == "H-OSW-fixed"]
    occ_mean = st.mean(occ)
    a1_vm_h = 113 * 2 * 2 * 110 / 3600  # 113 tasks x 2 boots x 2 conditions (default, blink-off) x ~110 s
    c_vm_h = 452 * 2 * occ_mean / 3600  # every 4B H-OSW-fixed episode replayed twice
    cblink_vm_h = 113 * 2 * occ_mean / 3600  # conditional: one episode per task, two blink-off replays
    out = {"schema": "r01-caps-v1", "cap_rule": {"lead_min": LEAD_MIN, "engine_start_min": ENGINE_START_MIN,
                                                "dr4_factor": F_DR4, "requeue_factor": F_REQ,
                                                "work_priced_at": "high per-request price"},
           "price": price, "jobs": jobs,
           "total_cap_min": total_cap, "total_cap_gpu_h": round(total_cap / 60, 3),
           "total_cap_min_without_conditional": total_cap_core,
           "total_cap_gpu_h_without_conditional": round(total_cap_core / 60, 3),
           "physical_gpu_h_central": round(sum(j["physical_gpu_h_central"] for j in jobs), 3),
           "physical_gpu_h_high": round(sum(j["physical_gpu_h_high"] for j in jobs), 3),
           "d22_line_gpu_h": 8.0,
           "cpu_lane": {"slot_occupancy_mean_s": round(occ_mean, 1), "stage_A1_vm_h": round(a1_vm_h, 1),
                        "stage_C_vm_h": round(c_vm_h, 1), "stage_C_blink_conditional_vm_h": round(cblink_vm_h, 1),
                        "wall_h_at_V20": round((a1_vm_h + c_vm_h + cblink_vm_h) / 20, 1), "gpu_h": 0.0}}
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("total_cap_gpu_h", "total_cap_gpu_h_without_conditional",
                                          "physical_gpu_h_central", "physical_gpu_h_high", "cpu_lane")}, indent=1))
    for j in jobs:
        print(j["job"], j["cap_min"], j["arithmetic"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
