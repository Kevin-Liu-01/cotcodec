#!/usr/bin/env python3
"""E4 gate repair (D60), CPU check S3v2: GPU-hour arithmetic for registration v2.

Same method as wave 1's `../cost-model.py` (FLOPs / (MFU x 989e12), the dense BF16
H100 peak; per-token forward FLOPs of the 1.3B config 2.597e9; an
activation-only backward through the frozen model counted as one more forward;
a 1.25 safety factor; launch-overhead factor; fixed per-job hours). No
throughput has been measured for this workload; the smoke job measures it and
the reduction ladder and the freeze rule apply exactly as in wave 1.

What changed, and why each change is arithmetic rather than hope:

1. Prompt lengths are measured, not assumed. `family-table.json` tokenizes every
   family's zero-shot probe and 8-shot prompt with the teacher's tokenizer
   (with BOS): zero-shot mean 8.5, max 13 tokens; 8-shot mean 85, max 125.
   Central uses 10 and 100, high 16 and 140 (wave 1: 12/200 and 24/400).
2. Prefix caching. The interface sites sit after blocks 6, 12, 18 and 24 of 24, so
   blocks 1-6 never see a state; their outputs for every probe are computed once
   and cached, and each oracle step runs blocks 7-24 forward and backward
   (factor 18/24). This is exact arithmetic reuse, so the cached path is
   mandatory: the smoke (I4) checks that the cached and uncached paths give the
   same logits (fp32, 1e-6), and a failure is a harness defect to fix (INFRA_FAIL
   until fixed), not a reason to run uncached. The uncached projection is still
   printed for reference.
3. Fitting probes rise from 16 to 24 per episode (the I1/I2 window, S1v2 grid),
   which raises every oracle fit's cost by 1.5x.
4. The design is re-counted (below), with the new classes (per-episode shift,
   two secondary key sets, the I6/I7 planted checks, a full-rank family
   constant and the read-subspace map B, each fitted by minibatch on the
   fitting probes of all 48 episodes, and I5 planted on all 48) and without the
   SHUF-target oracle fits, whose role the label-prior guard now takes from
   teacher SHUF predictions (a forward pass, not a fit).
5. The width-256 reference, the supervised-map arm and the in-sample ceiling run
   only after CAP_LOW, inside the conditional cap.

Usage: python cost-model-v2.py   (prints JSON to stdout)
"""

import json
import math

PEAK = 989e12
FWD_13 = 2.597e9
FWD_27 = 5.239e9
FB_13 = 2 * FWD_13
STEPS = 200
N_FIT = 24
N_SCORE = 8
PREFIX_FACTOR = 18 / 24  # blocks 7-24 only, after the smoke's cached-prefix equivalence check


def hours(flop: float, mfu: float) -> float:
    return flop / (mfu * PEAK) / 3600


def step1(prompt_tokens: int, zs_tokens: int, fams: int = 15) -> float:
    eps, queries, seeds = 25, 16, 3
    n = fams * eps * queries * seeds
    return n * (2 * prompt_tokens + zs_tokens) * FWD_13 + n * prompt_tokens * FWD_27


def per_family_units(reduced: int) -> dict:
    """Episode-fit units: one unit = STEPS Adam steps over N_FIT fitting probes of one episode."""
    u = {
        "eval: S_shift, S_span (decision key set), S_free on 32 episodes": 3 * 32,
        "eval secondaries: S_span alone keys and in-context keys (B = I) on 16 episodes": 2 * 16,
        "family constant C_f: full rank, all fitting probes of 48 episodes, 400 steps x 256-probe minibatch":
            400 * 256 / (STEPS * N_FIT),
        "B (read-subspace map) fit on the fitting probes of all 48 episodes, 800 minibatch steps of 256 probes":
            800 * 256 / (STEPS * N_FIT),
        "development: key-set choice (alone, in-context; fitted reuses the B fit) on 14 episodes": 14 * 2,
        "development: learning rate, 3 rates x 3 classes x 2 episodes": 18,
        "I2/I3: free, out-of-span and span plants, 2 episodes each, best of 3 restarts, 2 classes": 3 * 2 * 3 * 2,
        "I5: preconditioned plant on all 48 episodes, B refit as registered (800 x 256) + 4 scored x 2 classes":
            800 * 256 / (STEPS * N_FIT) + 4 * 2,
        "I6: permuted-context-key plant, 4 episodes x 2 classes": 4 * 2,
        "I7: shift-only plant, 8 episodes x 2 classes (shift, free)": 8 * 2,
        "restart sensitivity: 4 episodes x 2 restarts x 3 classes": 24,
        "site-1.0 ablation: S_free without the last site, 8 episodes": 8,
    }
    if reduced >= 1:  # the registered reduction ladder, applied in order
        u["restart sensitivity: 4 episodes x 2 restarts x 3 classes"] = 0
    if reduced >= 2:
        u["site-1.0 ablation: S_free without the last site, 8 episodes"] = 0
    if reduced >= 3:
        u["eval secondaries: S_span alone keys and in-context keys (B = I) on 16 episodes"] = 2 * 8
    if reduced >= 4:
        u["eval secondaries: S_span alone keys and in-context keys (B = I) on 16 episodes"] = 0
    return u


def step2(probe_tokens: int, prompt_tokens: int, families: int, reduced: int, prefix: bool) -> dict:
    units = per_family_units(reduced)
    per_unit = STEPS * N_FIT * probe_tokens * FB_13 * (PREFIX_FACTOR if prefix else 1.0)
    oracle = sum(units.values()) * families * per_unit
    pfit = (2000 * 512 + 2000 * 64 * 17) * FWD_13  # context-change PCA (both widths share the pass)
    # teacher targets: GOLD and SHUF 8-shot predictions for 48 episodes x 32 probes per family, plus the
    # in-context key reads (8-shot prompt, one pass per episode) and alone-encoded keys (zero-shot prompts)
    targets = families * 48 * (2 * (N_FIT + N_SCORE) * prompt_tokens + prompt_tokens + 8 * probe_tokens) * FWD_13
    # resample, random, I0 and permuted-target re-scoring: forward passes on scoring probes
    rescoring = families * 32 * 6 * N_SCORE * probe_tokens * FWD_13
    return {"units_per_family": units, "units_total": round(sum(units.values()) * families, 1),
            "flop": oracle + pfit + targets + rescoring}


def conditional(probe_tokens: int, prompt_tokens: int, prefix: bool, reduced: bool = False) -> float:
    """After CAP_LOW only: supervised P/Q on 8 episodes x up to 8 other families (400 steps), C_f and S_free
    refits on 16 evaluation episodes of at most 10 CAP_LOW families, the width-256 reference (16 episodes x 2
    classes) and the in-sample ceiling (S_free fitted on all 32 probes of 16 evaluation episodes)."""
    per_unit = STEPS * N_FIT * probe_tokens * FB_13 * (PREFIX_FACTOR if prefix else 1.0)
    ref_eps, ceil_eps = (8, 8) if reduced else (16, 16)  # conditional ladder: S_ref and the ceiling to 8 episodes
    units = 8 * 8 * 2 + 10 * (16 + 400 * 256 / (STEPS * N_FIT)) + 10 * (ref_eps * 2) + 10 * ceil_eps * (32 / 24)
    return units * per_unit


def step2_n32_branch(probe_tokens: int, prompt_tokens: int, families: int, prefix: bool) -> dict:
    """The registered high-dimension branch: 32 fitting probes when the development probe reads' d90 is above 13,
    with 24 evaluation episodes per family for the three decision classes and the full reduction ladder applied.
    Minibatch fits (C_f, B and the I5 B refit) have a fixed probe budget, so they do not scale with N_FIT."""
    units = per_family_units(4)
    fixed = {k: v for k, v in units.items() if "minibatch" in k or "800 x 256" in k}
    scaled = {k: v for k, v in units.items() if k not in fixed}
    scaled["eval: S_shift, S_span (decision key set), S_free on 32 episodes"] = 3 * 24
    per_unit24 = STEPS * N_FIT * probe_tokens * FB_13 * (PREFIX_FACTOR if prefix else 1.0)
    oracle = (sum(scaled.values()) * 32 / 24 + sum(fixed.values())) * families * per_unit24
    pfit = (2000 * 512 + 2000 * 64 * 17) * FWD_13
    targets = families * 40 * (2 * (32 + N_SCORE) * prompt_tokens + prompt_tokens + 8 * probe_tokens) * FWD_13
    rescoring = families * 24 * 6 * N_SCORE * probe_tokens * FWD_13
    return {"flop": oracle + pfit + targets + rescoring,
            "units_24_equivalent": round((sum(scaled.values()) * 32 / 24 + sum(fixed.values())) * families, 1)}


def main() -> None:
    fams_main = 11  # all eligible ES families (at most 10) plus 1 fixed-function family as a constant control
    central = {"mfu": 0.25, "prompt": 100, "zs": 12, "probe": 10, "launch": 1.0, "fixed_h": 0.05}
    high = {"mfu": 0.125, "prompt": 140, "zs": 16, "probe": 16, "launch": 1.5, "fixed_h": 0.10}
    wave1_high_probe = {"mfu": 0.125, "prompt": 400, "zs": 40, "probe": 24, "launch": 1.5, "fixed_h": 0.10}
    out = {}
    for name, c in (("central", central), ("high", high), ("high_with_wave1_prompt_lengths", wave1_high_probe)):
        f = lambda flop: hours(flop, c["mfu"]) * c["launch"] * 1.25 + c["fixed_h"]
        row = {"assumptions": c}
        row["step1_gpu_h"] = round(f(step1(c["prompt"], c["zs"])), 3)
        for prefix in (True, False):
            tag = "prefix_cached" if prefix else "no_prefix_cache"
            s2 = step2(c["probe"], c["prompt"], fams_main, 0, prefix)
            row[f"step2_main_gpu_h_{tag}"] = round(f(s2["flop"]), 3)
            for rung in (1, 2, 3, 4):
                row[f"step2_main_after_ladder_rung{rung}_gpu_h_{tag}"] = round(f(step2(c["probe"], c["prompt"], fams_main, rung, prefix)["flop"]), 3)
            s2r = step2(c["probe"], c["prompt"], fams_main, 4, prefix)
            row[f"conditional_gpu_h_{tag}"] = round(f(conditional(c["probe"], c["prompt"], prefix)), 3)
            b32 = step2_n32_branch(c["probe"], c["prompt"], fams_main, prefix)
            row[f"step2_main_n32_branch_gpu_h_{tag}"] = round(f(b32["flop"]), 3)
            row["n32_branch_units_24_equivalent"] = b32["units_24_equivalent"]
            row[f"conditional_after_ladder_gpu_h_{tag}"] = round(f(conditional(c["probe"], c["prompt"], prefix, True)), 3)
            row["units_total"] = s2["units_total"]
            row["units_total_after_ladder"] = s2r["units_total"]
        out[name] = row
    out["units_per_family"] = per_family_units(0)
    caps = {"S0_smoke": 0.17, "S1_eligibility": 0.55, "S2_oracle_main": 5.5, "S2_conditional": 1.5}
    out["registered_caps_gpu_h"] = caps
    out["sum_of_caps_gpu_h"] = round(sum(caps.values()), 2)
    out["d22_reading"] = ("caps, not expected use, count (D22); the sum is below D20's 8 GPU-h line, so D24 is not "
                          "triggered; the gauntlet's own 0.3 GPU-h for reviewer inference is separate")
    out["integer_ceiling_for_doctor"] = math.ceil(sum(caps.values()))
    out["fit_against_caps"] = {
        name: {"step1_under_cap": out[name]["step1_gpu_h"] <= caps["S1_eligibility"],
               "step2_main_under_cap_prefix_cached": out[name]["step2_main_gpu_h_prefix_cached"] <= caps["S2_oracle_main"],
               "step2_n32_branch_under_cap_prefix_cached": out[name]["step2_main_n32_branch_gpu_h_prefix_cached"] <= caps["S2_oracle_main"],
               "step2_main_after_full_ladder_under_cap_prefix_cached": out[name]["step2_main_after_ladder_rung4_gpu_h_prefix_cached"] <= caps["S2_oracle_main"],
               "step2_main_after_full_ladder_under_cap_no_prefix_cache": out[name]["step2_main_after_ladder_rung4_gpu_h_no_prefix_cache"] <= caps["S2_oracle_main"],
               "conditional_under_cap_prefix_cached": out[name]["conditional_gpu_h_prefix_cached"] <= caps["S2_conditional"],
               "conditional_after_ladder_under_cap_no_prefix_cache": out[name]["conditional_after_ladder_gpu_h_no_prefix_cache"] <= caps["S2_conditional"]}
        for name in ("central", "high", "high_with_wave1_prompt_lengths")}
    print(json.dumps(out, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
