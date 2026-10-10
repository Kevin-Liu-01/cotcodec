#!/usr/bin/env python3
"""E4 gate, CPU check S3: GPU-hour estimate and caps for the draft registration.

Method (as the asset-cost discovery cell): FLOPs / (MFU x 989e12), where 989
TFLOP/s is the dense BF16 H100 peak the repository's fla throughput receipt
uses. No throughput has been measured for this workload; the smoke job sets
the real limits before any freeze (D20 and D22 pattern). Per-token forward
FLOPs come from the checkpoint configs (asset-cost cell): 1.3B 2.597e9,
2.7B 5.239e9; activation-only backward counted as one more forward.

Probe prompts are the zero-shot template "input: X\noutput:" (about 8 tokens);
central assumes 12 and high 24. Eight-shot prompts are about 100 tokens for
these families; central assumes 200 and high 400.

Usage: python cost-model.py   (prints JSON to stdout)
"""

import json
import math

PEAK = 989e12
FWD_13 = 2.597e9
FWD_27 = 5.239e9
FB_13 = 2 * FWD_13  # forward plus activation-only backward through the frozen model


def hours(flop: float, mfu: float) -> float:
    return flop / (mfu * PEAK) / 3600


def step1(prompt_tokens: int, zs_tokens: int) -> float:
    fams, eps, queries, seeds = 14, 25, 16, 3
    n = fams * eps * queries * seeds  # 16,800 prompts per condition
    flop13 = n * (2 * prompt_tokens + zs_tokens) * FWD_13  # gold + shuffled + zero-shot
    flop27 = n * prompt_tokens * FWD_27  # 2.7B gold only (disagreement, secondary)
    return flop13 + flop27


def step2(probe_tokens: int, steps: int, families: int = 11, reduced: bool = False) -> dict:
    per_family = {
        "eval_episodes_x3_variants (span_B, span_I, free64)": 32 * 3,
        "B_fit_episodes_joint (14 development episodes, T doubled)": 14 * 2,
        "family_constant (4 fitting probes from each of 48 episodes = 12 episode-equivalents)": 12,
        "width256_reference (16 episodes)": 16,
        "site_1.0_ablation (8 episodes)": 8,
        "shuffled_target_secondary (free64 + constant, 16 episodes)": 16 + 16,
        "planted_recovery (2 types x 2 episodes x 3 restarts x 2 classes)": 24,
        "restart_sensitivity (4 episodes x 2 restarts x 3 variants)": 24,
        "learning_rate_selection (3 rates x 3 classes x 2 development episodes)": 18,
        "planted_preconditioner_check I5 (B fit on 4 planted episodes x 2, scored on 2 x 2)": 12,
    }
    if reduced:  # the registration's predeclared reduction ladder, applied in order
        per_family["shuffled_target_secondary (free64 + constant, 16 episodes)"] = 0
        per_family["restart_sensitivity (4 episodes x 2 restarts x 3 variants)"] = 0
        per_family["site_1.0_ablation (8 episodes)"] = 0
        per_family["width256_reference (16 episodes)"] = 8
    ep_variants = sum(per_family.values()) * families
    per_ep = steps * 16 * probe_tokens * FB_13  # 16 fitting probes per episode
    oracle = ep_variants * per_ep
    pfit = (2000 * 512 + 2000 * 64 * 17) * FWD_13  # context-change PCA, two widths share the pass
    targets = families * (48 + 16) * 24 * 200 * FWD_13  # 24 probes per episode, 8-shot prompts
    # conditional arm: P and Q trained jointly with states on 8 development episodes of up to 8 other
    # families (400 steps), then constant and free refits on at most 9 CAP_LOW families' 32 episodes
    oracle_p = (8 * 8 * 2 + 9 * (32 + 12)) * per_ep
    # families: all eligible episode-specific families (at most 9) plus at most 2 fixed-function ones
    return {"per_family_episode_variants": per_family, "episode_variants": ep_variants,
            "flop_main": oracle + pfit + targets, "flop_oracle_p_conditional": oracle_p}


def main() -> None:
    central = {"mfu": 0.25, "prompt": 200, "zs": 20, "probe": 12, "steps": 200, "launch": 1.0, "fixed_h": 0.05}
    high = {"mfu": 0.125, "prompt": 400, "zs": 40, "probe": 24, "steps": 200, "launch": 1.5, "fixed_h": 0.10}
    out = {}
    for name, c in (("central", central), ("high", high)):
        s1 = hours(step1(c["prompt"], c["zs"]), c["mfu"]) * c["launch"] * 1.25 + c["fixed_h"]
        s2 = step2(c["probe"], c["steps"])
        s2_main = hours(s2["flop_main"], c["mfu"]) * c["launch"] * 1.25 + c["fixed_h"]
        s2_p = hours(s2["flop_oracle_p_conditional"], c["mfu"]) * c["launch"] * 1.25 + c["fixed_h"]
        s2r = step2(c["probe"], c["steps"], reduced=True)
        s2_red = hours(s2r["flop_main"], c["mfu"]) * c["launch"] * 1.25 + c["fixed_h"]
        out[name] = {"assumptions": c, "step1_gpu_h": round(s1, 3), "step2_main_gpu_h": round(s2_main, 3),
                     "step2_oracle_p_conditional_gpu_h": round(s2_p, 3),
                     "step2_main_after_reduction_ladder_gpu_h": round(s2_red, 3),
                     "episode_variants": s2["episode_variants"],
                     "per_family_episode_variants": s2["per_family_episode_variants"]}
    caps = {"S0_smoke": 0.17, "S1_eligibility": 0.75, "S2_oracle_main": 4.0, "S2_oracle_p_conditional": 1.5}
    out["registered_caps_gpu_h"] = caps
    out["sum_of_caps_gpu_h"] = round(sum(caps.values()), 2)
    out["d22_reading"] = ("caps, not expected use, count; the sum of caps is below the 8 GPU-h threshold, "
                          "so D24 is not triggered; the gauntlet's own 0.3 GPU-h (reviewer inference) is separate")
    out["integer_ceiling_for_doctor"] = math.ceil(sum(caps.values()))
    print(json.dumps(out, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
