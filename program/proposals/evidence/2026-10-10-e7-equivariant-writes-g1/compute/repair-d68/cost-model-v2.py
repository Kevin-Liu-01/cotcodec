#!/usr/bin/env python3
"""S2v2: GPU-hour estimate and registered caps for the E7 G1 gate, registration v2 (D68 repair).

Same model and assumptions as wave 1's S2 (`../cost-model.py`, kept unedited), with three changes:
(1) the step-overhead probe's three repeats are priced explicitly (wave 1 priced
    200 x (1 + 3 + 2) step-equivalents once while the registration said "three
    repeats"; the feasibility refuter showed J1 would then need 42 minutes). v2
    registers 100 steps per configuration per repeat, three repeats:
    3 x 100 x (1 + 3 + 2) = 1,800 step-equivalents;
(2) the v2 diagnostics replace wave 1's (state cut on B2 and B3, v = 0 ablation on
    B3): the REACH and ISO invariance checks (64 B3 prompts x 2 each, plus 64
    uncut swaps), the relay-blocked B3 read, the fact-span write ablation on B3,
    the span-cut B2 read and the two B1 pathway reads (span cut and relay block);
(3) decoy queries share their prompt's prefix, so each costs only its query and
    candidates (about 60 tokens) under prefix caching.
The arithmetic of every job is written out in the output ("arithmetic").

The only measured base is the training throughput of the 134M GDN 3:1 hybrid
on one H100 in Slurm job 359 (282,501.4 tokens/s; eager, bf16 parameters,
random tokens, full causal attention at 2,048 tokens, batch 16; image
cotcodec-research:0b3ecef0-architecture; receipt
legacy/research/evidence/infrastructure/fla-throughput-h100-2026-09-01.json).
Everything else is an assumption listed in ASSUMPTIONS and in the output.

Caps follow the D22 counting rule: the sum of the registered caps of every job,
conditional jobs included at their caps, must be at most 8.0 GPU-h. A cap is
1.2 x the high projection, rounded up to a whole minute.

Usage: cost-model.py <output.json>
"""

from __future__ import annotations

import json
import math
import sys

R0 = 282_501.4
TOKENS_PER_STEP = 8 * 4096  # registered batch 8 x 4,096 = 32,768 tokens (same tokens per step as the measurement)
ASSUMPTIONS = {
    "train_time_multiplier": {"central": 1.25, "high": 1.5},
    "eval_forward_rate_over_R0": {"central": 2.0, "high": 1.5},
    "job_startup_s": {"central": 180, "high": 300},
    "compile_and_autotune_s": {"central": 180, "high": 300},
    "checkpoint_saves_s_per_trunk": {"central": 60, "high": 110},
    "probe_step_cost_vs_A0": {"A1_write_extraction": 3.0, "restricted_attention_aux_pass": 2.0},
    "probe_steps_per_config_per_repeat": 100,
    "probe_repeats": 3,
    "cap_factor": 1.2,
    "cap_rounding": "up to a whole minute",
}

# Evaluation tokens per seed (registration v2 "Instrument", "Reads" and "Diagnostics")
B3_PROMPTS, B3_LEN = 5000, 2950      # at most 10 cells x 500; facts ~400 + mean gap 2,500 + query ~50
B1_PROMPTS, B1_LEN = 2500, 700
B2_PROMPTS, B2_LEN = 2500, 1180
DECOYS, DECOY_LEN = 3000, 60         # one decoy query per cross prompt (at most 6 cells x 500), prefix cached
CHECK_PROMPTS = 64                   # REACH and ISO invariance checks
FULL_READ = B3_PROMPTS * B3_LEN + B1_PROMPTS * B1_LEN + B2_PROMPTS * B2_LEN + DECOYS * DECOY_LEN
EVAL_TOKENS = {
    "primary_reads_200M_branch_and_1B_all_bins_8_candidates_prefix_cached_with_decoys": 2 * FULL_READ,
    "noise_reads_960M_980M_B3_target_only": 2 * B3_PROMPTS * B3_LEN,
    "emergence_reads_100M_400M_800M_B3_and_B1": 3 * (B3_PROMPTS * B3_LEN + B1_PROMPTS * B1_LEN),
    "check_REACH_span_cut_64_pairs_plus_64_uncut_swaps": 3 * CHECK_PROMPTS * B3_LEN,
    "check_ISO_isolation_64_pairs": 2 * CHECK_PROMPTS * B3_LEN,
    "diag_B3_relay_block_all_prompts": B3_PROMPTS * B3_LEN,
    "diag_B3_fact_span_write_ablation_all_prompts": B3_PROMPTS * B3_LEN,
    "diag_B2_span_cut_all_prompts": B2_PROMPTS * B2_LEN,
    "diag_B1_span_cut_and_relay_block_all_prompts": 2 * B1_PROMPTS * B1_LEN,
    "diag_csls_writes_probes": 10_000_000,
}
EVAL_TOKENS_PER_SEED = sum(EVAL_TOKENS.values())


def train_s(tokens: float, case: str) -> float:
    return tokens * ASSUMPTIONS["train_time_multiplier"][case] / R0


def eval_s(tokens: float, case: str) -> float:
    return tokens / (ASSUMPTIONS["eval_forward_rate_over_R0"][case] * R0)


def overhead(case: str, autotune: bool = True) -> float:
    return ASSUMPTIONS["job_startup_s"][case] + (ASSUMPTIONS["compile_and_autotune_s"][case] if autotune else 0)


def job(name: str, train_tokens: float = 0.0, eval_tokens: float = 0.0, extra_step_equiv: float = 0.0,
        saves: bool = False, conditional: bool = False, note: str = "") -> dict:
    out = {"job": name, "conditional": conditional, "train_tokens": train_tokens, "eval_tokens": eval_tokens,
           "probe_step_equivalents": extra_step_equiv, "note": note}
    for case in ("central", "high"):
        s = train_s(train_tokens + extra_step_equiv * TOKENS_PER_STEP, case) + eval_s(eval_tokens, case) + overhead(case)
        if saves:
            s += ASSUMPTIONS["checkpoint_saves_s_per_trunk"][case]
        out[f"{case}_s"] = round(s, 1)
        out[f"{case}_gpu_h"] = round(s / 3600, 3)
    cap_s = math.ceil(ASSUMPTIONS["cap_factor"] * out["high_s"] / 60) * 60
    out["cap_s"] = cap_s
    out["cap_min"] = cap_s // 60
    out["cap_gpu_h"] = round(cap_s / 3600, 3)
    return out


def main() -> int:
    out_path = sys.argv[1]
    smoke_steps = 300
    probe = (ASSUMPTIONS["probe_repeats"] * ASSUMPTIONS["probe_steps_per_config_per_repeat"]
             * (1.0 + ASSUMPTIONS["probe_step_cost_vs_A0"]["A1_write_extraction"]
                + ASSUMPTIONS["probe_step_cost_vs_A0"]["restricted_attention_aux_pass"]))
    lr_tokens = 3 * 50_000_000
    trunk_tokens = 1_000_000_000 + 40_000_000
    jobs = [
        job("J1 smoke, step-overhead probe, cached-candidate equivalence, then LR sweep (3 x 50M tokens, seed 42)",
            train_tokens=smoke_steps * TOKENS_PER_STEP + lr_tokens, extra_step_equiv=probe,
            note="smoke gates must pass before the sweep starts in the same job"),
        job("J2 fresh-job resume test (100 steps from the J1 step-200 checkpoint)", train_tokens=100 * TOKENS_PER_STEP),
        job("J3 conditional LR extension (one value beyond the grid edge, 50M tokens)", train_tokens=50_000_000, conditional=True,
            note="runs only if the selected LR is at a grid edge"),
    ]
    for seed in (42, 43, 44):
        jobs.append(job(f"T{seed} trunk to 1B tokens with a 40M-token decay branch at 160M, then all reads (seed {seed})",
                        train_tokens=trunk_tokens, eval_tokens=EVAL_TOKENS_PER_SEED, saves=True,
                        note="seeds 43 and 44 are skipped if seed 42 meets the futility rule; their caps still count"))
    cap_sum = round(sum(j["cap_s"] for j in jobs) / 3600, 3)
    central_all = round(sum(j["central_gpu_h"] for j in jobs if not j["conditional"]), 3)
    high_all = round(sum(j["high_gpu_h"] for j in jobs), 3)
    central_futility = round(sum(j["central_gpu_h"] for j in jobs[:2]) + jobs[3]["central_gpu_h"], 3)
    # Throughput gate: the smoke-measured training rate r must make the trunk fit its cap with 10% margin,
    # with the evaluation forward rate taken as 1.2 x r (conservative) and high overheads.
    trunk = jobs[3]
    fixed = overhead("high") + ASSUMPTIONS["checkpoint_saves_s_per_trunk"]["high"]
    r_min = (trunk_tokens + EVAL_TOKENS_PER_SEED / 1.2) / (trunk["cap_s"] / 1.1 - fixed)
    one_seed_dossier = {
        "dossier_estimate_gpu_h": 2.5,
        "this_model_one_seed_central_gpu_h": round(jobs[0]["central_gpu_h"] + jobs[1]["central_gpu_h"] + trunk["central_gpu_h"], 3),
        "this_model_one_seed_caps_gpu_h": round(jobs[0]["cap_gpu_h"] + jobs[1]["cap_gpu_h"] + jobs[2]["cap_gpu_h"] + trunk["cap_gpu_h"], 3),
    }
    arithmetic = []
    for j in jobs:
        tt = j["train_tokens"] + j["probe_step_equivalents"] * TOKENS_PER_STEP
        arithmetic.append(
            f"{j['job'].split(' ')[0]}: high = {tt:,.0f} train-token-equivalents x 1.5 / {R0:,.1f} tok/s"
            f" + {j['eval_tokens']:,.0f} eval tokens / (1.5 x {R0:,.1f}) + 300 s start-up + 300 s compile"
            f"{' + 110 s checkpoints' if 'trunk' in j['job'] else ''} = {j['high_s']:,.1f} s;"
            f" cap = ceil(1.2 x {j['high_s']:,.1f} / 60) = {j['cap_min']} min = {j['cap_gpu_h']} GPU-h")
    res = {
        "script": "cost-model-v2.py",
        "arithmetic": arithmetic,
        "measured_base": {"tokens_per_s": R0, "slurm_job": 359, "mode": "eager, bf16 params, random tokens, full causal attention, seq 2048 x batch 16",
                          "image": "127.0.0.1:5000/cotcodec-research@sha256:02965f3d696d4e516a7cd6d5c03434e9098139738748ae778ed967215db7be6d"},
        "assumptions": ASSUMPTIONS,
        "tokens_per_step": TOKENS_PER_STEP,
        "eval_tokens_per_seed": EVAL_TOKENS,
        "eval_tokens_per_seed_total": EVAL_TOKENS_PER_SEED,
        "jobs": jobs,
        "cap_sum_gpu_h_D22": cap_sum,
        "cap_sum_within_8": cap_sum <= 8.0,
        "central_gpu_h_all_seeds_no_extension": central_all,
        "high_gpu_h_all_jobs": high_all,
        "central_gpu_h_if_futility_stop_after_seed_42": central_futility,
        "throughput_gate_min_training_tokens_per_s": round(r_min),
        "throughput_gate_as_share_of_R0": round(r_min / R0, 3),
        "one_seed_comparison": one_seed_dossier,
        "raw_gpu_h_per_1B_tokens_at_R0": round(1e9 / R0 / 3600, 4),
    }
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
        fh.write("\n")
    for j in jobs:
        print(f"{j['cap_min']:5d} min cap  {j['central_gpu_h']:.3f} central  {j['high_gpu_h']:.3f} high  {j['job'][:70]}")
    print("cap sum", cap_sum, "central", central_all, "futility path", central_futility, "r_min", round(r_min))
    return 0


if __name__ == "__main__":
    sys.exit(main())
