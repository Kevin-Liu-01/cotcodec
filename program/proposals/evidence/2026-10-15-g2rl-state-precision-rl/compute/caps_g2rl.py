#!/usr/bin/env python3
"""G2-RL gauntlet: compute caps with their arithmetic (CPU, standard library only).

Two parts:

  pilot  The draft registration's jobs (g2rl-state-precision-rl-v1): GPUs x Slurm limit for every
         GPU job, summed (the cap), and the expected physical GPU-h from the step model.
  full   The full design (proposal level, registered after the pilot): GPU-h per run from a
         step model, per stage, central / low / high.

Step model (estimates, about +/-35%; the pilot measures them). Basis: the asset planner's
model for the lean configuration (Qwen3.5-4B, 4 GPUs, verl colocated FSDP2, 32 prompts x 8
rollouts = 256 per step, 16,384-token cap), anchored on this program's G2b phase R timings
(72 rollouts of up to 32K on one H100: 384 s for the 4B with fp32 state) and the training FLOPs
(3.2M tokens per step x about 4.7e10 FLOP per token at 20-35% MFU):
  generation 175 s (140-220), training 127 s (110-190), overhead 48 s (20-60)
  => 350 s per step (270-470) on 4 GPUs.

Usage: python3 caps_g2rl.py --out caps-g2rl.json
"""

from __future__ import annotations

import argparse
import json

STEP_S = {"central": 350.0, "low": 270.0, "high": 470.0}
GPUS_PER_RUN = 4
# one checkpoint evaluation with the common fp32-state evaluator: 256 held-out prompts x 4,
# MATH-500 x 1, AIME 2024 and 2025 x 8 (about 2,000 rollouts, about 22M tokens) on 4 GPUs
EVAL_GPU_H = {"central": 1.0, "low": 0.8, "high": 1.4}
# checkpoint saves every 25 steps and one fresh-job resume per run (the lane's 64 GPU-h per-job
# ceiling forces at least two jobs per run)
OVERHEAD_GPU_H = {"central": 1.6, "low": 1.2, "high": 2.4}


def pilot() -> dict:
    jobs = [
        # (id, what, gpus, limit_minutes, expected_minutes)
        ("P0a", "CPU: hash-pinned wheel and source fetch under D1 (pip download --require-hashes)", 0, 60, 20),
        ("P0b", "CPU: offline overlay build FROM the vLLM 0.31.0 overlay (verl, ray, FLA 0.5.2, Math-Verify; flash-attn from source or the torch varlen patch)", 0, 120, 60),
        ("P0c", "CPU: selftests (imports; Hydra resolves rollout.engine_kwargs.vllm.mamba_ssm_cache_dtype into the vllm serve argv; gradient-dump hook unit test)", 0, 20, 5),
        ("P1", "trainer anchor: verl FSDP2 compute_log_prob on G2b's 48 seed-42 4B rollouts (942,608 tokens) against G2b's host-kept r1/r2 and decode log-probs", 1, 15, 8),
        ("P2a", "smoke: fp32 3 GRPO steps (checkpoint after step 2, step-3 batch saved), bf16 and fp16 2 steps each; 8 prompts x 4 at a 4,096 cap; engine-logged state dtype", 2, 35, 20),
        ("P2b", "resume: fresh job loads the step-2 checkpoint, replays the saved step-3 batch, compares parameters with P2a's step 3; SIGUSR1 save-on-signal test", 2, 15, 14),
        ("P3a", "calibration fp32: lr 0, R = 4 replicate batches (32 prompts x 8, 16,384 cap, sampling seeds 42-45), per-token in-loop log-probs, full-gradient dumps", 4, 40, 30),
        ("P3b", "calibration bf16: as P3a, plus a second backward on every batch with token-TIS weights (C = 2), both gradients dumped", 4, 50, 41),
        ("P4", "CPU: in-loop mismatch tables, gradient Gram matrix, readouts", 0, 60, 20),
    ]
    rows = []
    cap = 0.0
    expected = 0.0
    for jid, what, gpus, limit, exp_min in jobs:
        c = gpus * limit / 60.0
        e = gpus * exp_min / 60.0
        cap += c
        expected += e
        rows.append(
            {
                "job": jid,
                "what": what,
                "gpus": gpus,
                "limit_min": limit,
                "cap_gpu_h": round(c, 4),
                "expected_min": exp_min,
                "expected_gpu_h": round(e, 4),
                "arithmetic": f"{gpus} x {limit} min / 60 = {c:.4f}",
            }
        )
    # P3 per-batch arithmetic behind the limits
    p3 = {
        "per_batch_s_fp32": "generation 175 + old-log-prob recompute 42 + backward 127 + dump 30 = 374",
        "per_batch_s_bf16_dual": "374 + second backward 127 + dump 30 = 531",
        "startup_s": "Ray, model load, vLLM start with CUDA graphs: about 300",
        "P3a_expected_s": 4 * 374 + 300,
        "P3b_expected_s": 4 * 531 + 300,
        "P3a_high_s": 4 * (470 + 42 + 30) + 300,
        "P3b_high_s": 4 * (470 + 42 + 30 + 190 + 30) + 300,
        "rule": "a P3 job cut before its fourth batch reports R = 3 and its gradient readout is estimation only",
    }
    return {
        "jobs": rows,
        "cap_gpu_h": round(cap, 4),
        "expected_gpu_h": round(expected, 4),
        "line_8_gpu_h": 8.0,
        "under_line": cap <= 8.0,
        "p3_arithmetic": p3,
        "gradient_dump_storage_gb": {
            "per_dump_fp32": "about 4.3e9 language-model parameters x 4 bytes = about 17 GB",
            "dumps": "P3a 4 + P3b 8 = 12",
            "total_gb": 12 * 17,
            "deleted_after": "P4 writes the Gram matrix; the dumps are deleted after the readouts are committed",
        },
    }


def per_run(steps: int, evals: int, own_dtype_eval: bool, level: str) -> float:
    train = steps * STEP_S[level] * GPUS_PER_RUN / 3600.0
    return train + evals * EVAL_GPU_H[level] + OVERHEAD_GPU_H[level] + (EVAL_GPU_H[level] if own_dtype_eval else 0.0)


def full() -> dict:
    steps, evals = 150, 3
    stage0 = {
        "what": "learnable pool: 1,536 deduplicated DAPO-Math-17k prompts x 8 at 16,384 with fp32 state (about 135M tokens) plus base-checkpoint evaluation",
        "central": 7.3,
        "low": 5.5,
        "high": 10.0,
        "arithmetic": "12,288 rollouts x about 11K tokens / (4 GPUs x about 6K tok/s) = about 6.3 GPU-h, plus 1.0 evaluation",
    }
    out = {"steps_per_run": steps, "evals_per_run": evals, "stage0": stage0, "levels": {}}
    for level in ("low", "central", "high"):
        f_run = per_run(steps, evals, False, level)
        b_run = per_run(steps, evals, True, level)
        stage1 = 5 * f_run + 5 * b_run
        stage2_bt = 5 * per_run(steps, evals, True, level)
        stage2_h = 3 * per_run(steps, evals, True, level)
        s0 = stage0[level]
        out["levels"][level] = {
            "step_s": STEP_S[level],
            "gpu_h_per_step": round(STEP_S[level] * GPUS_PER_RUN / 3600.0, 4),
            "run_F": round(f_run, 1),
            "run_B_or_BT_or_H": round(b_run, 1),
            "stage0": s0,
            "stage1_F5_B5": round(stage1, 1),
            "stage2_BT5": round(stage2_bt, 1),
            "stage2_H3": round(stage2_h, 1),
            "path_null_or_no_change": round(s0 + stage1, 1),
            "path_changes": round(s0 + stage1 + stage2_bt + stage2_h, 1),
        }
    out["proposed_full_cap_gpu_h"] = 1600
    out["note"] = (
        "The full design is registered after the pilot, with its per-step time replaced by P3's measurement; "
        "if the measured step exceeds 1.5 x 350 s, the design is re-sized (fewer steps or an 8,192 cap) before "
        "registration. Admission is Kevin's (D24, D92)."
    )
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    res = {"pilot": pilot(), "full": full()}
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
        fh.write("\n")
    p = res["pilot"]
    print("pilot cap", p["cap_gpu_h"], "expected", p["expected_gpu_h"])
    for row in p["jobs"]:
        print(" ", row["job"], row["arithmetic"], "expected", row["expected_gpu_h"])
    for level, v in res["full"]["levels"].items():
        print("full", level, v)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
