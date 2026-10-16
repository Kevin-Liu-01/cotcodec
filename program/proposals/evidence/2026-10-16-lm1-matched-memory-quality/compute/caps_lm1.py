#!/usr/bin/env python3
"""LM1: compute-cap arithmetic for the pilot (registration section 12) and the full study (proposal).

GPU-h per job = n_gpus * wall_h, wall_h = (prefill_tokens / prefill_tps + decode_tokens / decode_tps) * tail
+ fixed overhead (load, the 3-minute batched-bench preflight, drain). Throughputs are aggregate
(all slots of one llama-server) and are ESTIMATES with about 3x uncertainty (asset cell; smoke
test job 1582 single-stream x 2.5-8; DGX Spark batching shape 4.4-5.2x from B=1 to B=32). The
pilot's preflight measures them; the guards (Slurm --time x GPUs) are what bind.

Usage: python caps_lm1.py --out caps-lm1.json
"""

from __future__ import annotations

import argparse
import json

SEEDS = 3
PRIMARY_ITEMS = 1600       # AA-Omniscience-Public 600 + SimpleQA-Verified 1000
SECONDARY_ITEMS = 400      # SuperGPQA: 200 is_calculation=False + 200 True
PRIMARY_PROMPT = 220       # tokens: instruction + question + chat template (estimate)
SECONDARY_PROMPT = 480     # tokens: question + 10 options + template (estimate)
TAIL = 1.15
OVERHEAD_H = 0.10          # load (15-93 s in the smoke test) + 3-min preflight + drain

# aggregate throughput, tokens/s, low-high (estimates)
ARMS = {
    #            gpus  prefill(lo,hi)    decode(lo,hi)   out_primary(lo,hi) out_secondary(lo,hi)  guard_gpu_h
    "kimi_k3":   (3, (600, 1500),   (100, 450),   (15, 80),   (40, 400),  3.30),
    "v4f_q2":    (2, (1500, 3000),  (240, 500),   (10, 60),   (30, 300),  0.90),
    "v4f_iq3":   (2, (1500, 3000),  (240, 500),   (10, 60),   (30, 300),  0.90),
    "qwen_q3":   (2, (2000, 4000),  (240, 500),   (10, 60),   (30, 300),  0.90),
    "gptoss_lo": (1, (3000, 6000),  (600, 1500),  (120, 500), (200, 800), 0.60),
}
# The V4 Flash UD-Q8_K_XL reference (3 GPUs) is a full-study arm (G4 decomposition), not a pilot arm.
JUDGE = {"gpus": 1, "guard_gpu_h": 0.30, "grades_per_arm": PRIMARY_ITEMS * SEEDS,
         "unique_prompt_tokens": 120, "shared_prefix_tokens": 1400, "prefill_tps": (8000, 20000)}
P2 = {"gpus": 2, "guard_gpu_h": 0.70, "items": 600, "seeds": 1, "out": (300, 1500),
      "decode_tps": (240, 500), "budget_tokens": 4096}


def job(gpus: int, prefill: float, decode: float, ptps: float, dtps: float) -> float:
    return gpus * ((prefill / ptps + decode / dtps) / 3600.0 * TAIL + OVERHEAD_H)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    rows = []
    for name, (g, ptps, dtps, op, osd, guard) in ARMS.items():
        # prompt cache: the 3 seeds of an item go to one slot, so the prompt is prefilled once (low);
        # without reuse it is prefilled 3 times (high)
        pre_lo = PRIMARY_ITEMS * PRIMARY_PROMPT + SECONDARY_ITEMS * SECONDARY_PROMPT
        pre_hi = SEEDS * pre_lo
        dec_lo = SEEDS * (PRIMARY_ITEMS * op[0] + SECONDARY_ITEMS * osd[0])
        dec_hi = SEEDS * (PRIMARY_ITEMS * op[1] + SECONDARY_ITEMS * osd[1])
        lo = job(g, pre_lo, dec_lo, ptps[1], dtps[1])
        hi = job(g, pre_hi, dec_hi, ptps[0], dtps[0])
        # share of the pre-registered order completed inside the guard in the pessimistic case
        frac_hi = min(1.0, max(0.0, (guard - g * OVERHEAD_H) / max(hi - g * OVERHEAD_H, 1e-9)))
        pp_hi = SEEDS * PRIMARY_ITEMS * PRIMARY_PROMPT
        pp_mid = PRIMARY_ITEMS * PRIMARY_PROMPT
        dp_hi = SEEDS * PRIMARY_ITEMS * op[1]
        prim_h = (pp_hi / ptps[0] + dp_hi / dtps[0]) / 3600.0 * TAIL
        prim_h_reuse = (pp_mid / ptps[0] + dp_hi / dtps[0]) / 3600.0 * TAIL
        avail_h = guard / g - OVERHEAD_H
        prim_share = min(1.0, avail_h / prim_h)
        prim_share_reuse = min(1.0, avail_h / prim_h_reuse)
        rows.append({"job": f"P1-{name}", "gpus": g, "prefill_tokens": [pre_lo, pre_hi],
                     "primary_items_done_if_pessimistic": [int(PRIMARY_ITEMS * prim_share), int(PRIMARY_ITEMS * prim_share_reuse)],
                     "decode_tokens": [dec_lo, dec_hi], "gpu_h": [round(lo, 3), round(hi, 3)],
                     "guard_gpu_h": guard, "wall_limit_min": round(60 * guard / g),
                     "share_of_order_done_if_pessimistic": round(frac_hi, 3)})
    n_grades = JUDGE["grades_per_arm"] * len(ARMS)
    j_lo = JUDGE["gpus"] * (n_grades * JUDGE["unique_prompt_tokens"] / JUDGE["prefill_tps"][1] / 3600 * TAIL + OVERHEAD_H)
    j_hi = JUDGE["gpus"] * (n_grades * (JUDGE["unique_prompt_tokens"] + 0.1 * JUDGE["shared_prefix_tokens"])
                            / JUDGE["prefill_tps"][0] / 3600 * TAIL + OVERHEAD_H)
    rows.append({"job": "J-judge (Qwen3-32B, vLLM, prefix cache)", "gpus": 1, "grades": n_grades,
                 "gpu_h": [round(j_lo, 3), round(j_hi, 3)], "guard_gpu_h": JUDGE["guard_gpu_h"],
                 "wall_limit_min": round(60 * JUDGE["guard_gpu_h"])})
    p2_lo = job(P2["gpus"], P2["items"] * PRIMARY_PROMPT, P2["items"] * P2["out"][0], 3000, P2["decode_tps"][1])
    p2_hi = job(P2["gpus"], P2["items"] * PRIMARY_PROMPT, P2["items"] * P2["out"][1], 1500, P2["decode_tps"][0])
    rows.append({"job": "P2-thinking-time-matched (conditional)", "gpus": 2, "gpu_h": [round(p2_lo, 3), round(p2_hi, 3)],
                 "guard_gpu_h": P2["guard_gpu_h"], "wall_limit_min": 21, "budget_tokens": P2["budget_tokens"]})
    guards = sum(r["guard_gpu_h"] for r in rows)
    guards_uncond = guards - P2["guard_gpu_h"]
    exp_lo = sum(r["gpu_h"][0] for r in rows if not r["job"].startswith("P2"))
    exp_hi = sum(min(r["gpu_h"][1], r["guard_gpu_h"]) for r in rows if not r["job"].startswith("P2"))

    # Mac-time matching for P2 (registration 6.4): Kimi on the M5 Max, 220-token prompt, ~30-token answer
    kimi_pool_gb = 239.5 - 7.0      # routed pool ~ file minus ~7 GB spine (dossier K3 row: 4.98 routed of 11.98 GB/token)
    t_prefill = [kimi_pool_gb / b for b in (10.6, 3.4)]   # a short prompt touches nearly every expert once per layer
    t_decode = 30 / 2.2
    t_kimi = [t_prefill[0] + t_decode, t_prefill[1] + t_decode]
    v4f_tokens = [39.35 * t for t in t_kimi]

    # Full study (proposal): per-branch arithmetic at the same throughput assumptions
    tierT_tokens_per_arm = 63 * 3 * 14000 + 150 * 3 * 12000 + 400 * 3 * 3000 + 400 * 3 * 6000  # math, code, tool, sgpqa-hard
    full = {
        "tier_T_generated_tokens_per_arm": tierT_tokens_per_arm,
        "tokens_per_gpu_h": {"kimi_k4": [0.135e6, 0.405e6], "two_gpu_arm": [0.43e6, 0.90e6],
                             "q8_three_gpu": [0.26e6, 0.53e6], "gptoss": [2.2e6, 5.4e6], "qwen38_27b_one_gpu": [0.6e6, 2.0e6]},
    }
    t = tierT_tokens_per_arm
    arm_cost = {
        "kimi_k26_iq1m": [t / 0.405e6, t / 0.135e6],
        "kimi_k26_int4_vllm_tp8": [t / 0.55e6, t / 0.075e6],
        "v4f_q2": [t / 0.90e6, t / 0.43e6], "v4f_iq3": [t / 0.90e6, t / 0.43e6],
        "v4f_q8": [t / 0.53e6, t / 0.26e6], "gptoss_high": [t / 5.4e6, t / 2.2e6],
        "qwen38_27b": [t / 2.0e6, t / 0.6e6], "qwen_235b_thinking_q3": [t / 0.90e6, t / 0.43e6],
    }
    arm_cost = {k: [round(v[0], 1), round(v[1], 1)] for k, v in arm_cost.items()}
    knowledge_block = {"k26_iq1m_primary": [0.6, 3.3], "qwen38_27b_primary": [0.2, 0.6], "kernel_path_cuda_vs_cpu": [0.5, 1.5],
                       "kimi_top4_primary": [0.6, 3.3], "k26_int4_reference_primary": [1.0, 6.0]}
    branches = {
        "NOT_WORTH": {"arms_tier_T": ["v4f_q2", "v4f_iq3", "v4f_q8", "gptoss_high", "qwen38_27b", "qwen_235b_thinking_q3"],
                      "knowledge_extras": ["k26_iq1m_primary", "qwen38_27b_primary", "kernel_path_cuda_vs_cpu"]},
        "UNRESOLVED": {"arms_tier_T": ["kimi_k26_iq1m", "v4f_q2", "v4f_iq3", "v4f_q8", "gptoss_high", "qwen38_27b"],
                       "knowledge_extras": ["k26_iq1m_primary", "qwen38_27b_primary", "kernel_path_cuda_vs_cpu"]},
        "LEADS": {"arms_tier_T": ["kimi_k26_iq1m", "kimi_k26_int4_vllm_tp8", "v4f_q2", "v4f_iq3", "v4f_q8", "gptoss_high", "qwen38_27b"],
                  "knowledge_extras": ["k26_iq1m_primary", "qwen38_27b_primary", "kernel_path_cuda_vs_cpu",
                                       "kimi_top4_primary", "k26_int4_reference_primary"]},
    }
    for b in branches.values():
        lo = sum(arm_cost[a][0] for a in b["arms_tier_T"]) + sum(knowledge_block[k][0] for k in b["knowledge_extras"])
        hi = sum(arm_cost[a][1] for a in b["arms_tier_T"]) + sum(knowledge_block[k][1] for k in b["knowledge_extras"])
        b["gpu_h"] = [round(lo, 1), round(hi, 1)]
        b["setup_gpu_h"] = [3, 8]
    full["arm_cost_gpu_h"] = arm_cost
    full["knowledge_block_gpu_h"] = knowledge_block
    full["branches"] = branches

    out = {
        "script": "compute/caps_lm1.py",
        "assumptions": {"seeds": SEEDS, "primary_items": PRIMARY_ITEMS, "secondary_items": SECONDARY_ITEMS,
                        "prompt_tokens": {"primary": PRIMARY_PROMPT, "secondary": SECONDARY_PROMPT},
                        "tail": TAIL, "overhead_h_per_job": OVERHEAD_H, "arms": {k: list(map(str, v)) for k, v in ARMS.items()}},
        "pilot": {"jobs": rows, "sum_of_guards_gpu_h": round(guards, 2),
                  "sum_of_guards_without_conditional_P2": round(guards_uncond, 2),
                  "expected_unconditional_gpu_h": [round(exp_lo, 2), round(exp_hi, 2)], "line_gpu_h": 8.0},
        "p2_mac_time_matching": {"kimi_pool_gb": kimi_pool_gb, "prefill_s_at_10.6_and_3.4_GBps": [round(x, 1) for x in t_prefill],
                                 "decode_s_30_tokens_at_2.2": round(t_decode, 1), "kimi_mac_s_per_item": [round(x, 1) for x in t_kimi],
                                 "v4f_q2_tokens_in_same_time_at_39.35": [round(x) for x in v4f_tokens],
                                 "registered_budget_tokens": P2["budget_tokens"]},
        "full_study": full,
        "reviewer_lane_gpu_h": 0.5,
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
        fh.write("\n")
    print(json.dumps(out["pilot"], indent=1))
    print(json.dumps(out["p2_mac_time_matching"], indent=1))
    print(json.dumps({k: v["gpu_h"] for k, v in branches.items()}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
