#!/usr/bin/env python3
"""G2-stream gauntlet: GPU-hour caps for the pilot and the full study (arithmetic only).

Throughput figures are assumptions until the pilot measures them. They come from the
local-frontier-moe-sweep dossier (section 4, shared assumptions) unless marked as this gauntlet's
own estimate. A cap is GPUs x Slurm time limit; a job that reaches its limit is ended by Slurm, so
the cap bounds use whatever the throughput turns out to be.

Usage: python3 caps_g2stream.py --out caps-g2stream.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def job(name, gpus, limit_h, note, expected_h=None, conditional=False):
    return {"job": name, "gpus": gpus, "limit_h": limit_h, "cap_gpu_h": round(gpus * limit_h, 3),
            "expected_gpu_h": None if expected_h is None else round(gpus * expected_h, 3),
            "conditional": conditional, "arithmetic": note}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    # Pilot token budget (registration section 5)
    sessions = 64  # 16 per workload
    prefill_tok = 16 * 2_000 + 16 * 1_000 + 16 * 12_000 + 16 * 14_000  # chat, coding, agentic, long-document
    decode_tok = sessions * 1_500  # thinking on, cap 2,048
    seeded_decode = 8 * 3 * 1_024  # 2 sessions per workload x seeds 42-44
    repass_tok = 16 * (7_500 + 1_500)  # teacher-forced re-pass of 16 sessions (context + decode)
    p2_prefill_rate = (600, 1_500)  # tokens/s, llama.cpp CUDA, 5 GPUs, layer split (gauntlet estimate)
    p2_decode_rate = (60, 150)  # tokens/s aggregate with 8 parallel slots (gauntlet estimate)
    load_min = (5, 15)  # 340.5 GB from local disk or page cache
    t_lo = (prefill_tok + repass_tok) / p2_prefill_rate[1] + (decode_tok + seeded_decode) / p2_decode_rate[1] + 60 * load_min[0]
    t_hi = (prefill_tok + repass_tok) / p2_prefill_rate[0] + (decode_tok + seeded_decode) / p2_decode_rate[0] + 60 * load_min[1]

    pilot = [
        job("P0 simulator, emulator, ds4-policy port, unit tests (Mac or host CPU)", 0, 0, "CPU only", 0),
        job("P0b llama.cpp b11669 image build and dump-tool CPU test (host CPU lane)", 0, 0, "CPU only, no GRES", 0),
        job("P1 validation traces GLM 5.3 IQ2_XXS and V4 Flash Vision-Exp MXFP4, plus 32 matched GLM sessions (host CPU lane)", 0, 0,
            "CPU only, no GRES; about 27K exact-input tokens and about 180K matched-session tokens; wall 3-12 h (unmeasured CPU rate)", 0),
        job("P1-gpu fallback: same traces on 3 GPUs if the CPU route fails to load or exceeds 12 h wall", 3, 0.65,
            "GLM 5.3 (211 GB) on 3 GPUs 0.4 h + V4 Flash (156 GB) on 3 GPUs 0.25 h", None, conditional=True),
        job("P2 Kimi K2.6 UD-Q2_K_XL traces on GPUs 1-5", 5, 1.0,
            f"prefill {prefill_tok + repass_tok:,} tokens at {p2_prefill_rate} tok/s, decode {decode_tok + seeded_decode:,} tokens at {p2_decode_rate} tok/s, load {load_min} min: wall {t_lo/3600:.2f}-{t_hi/3600:.2f} h",
            expected_h=round((t_lo + t_hi) / 2 / 3600, 3)),
        job("P3 llama.cpp GPU expert-cache fidelity check (PR #29887), experts in host RAM", 1, 0.5,
            "4 sessions x 512 decode tokens at 5-10 tok/s plus CPU-expert prefill of about 16K tokens and load", 0.3),
    ]
    cap_total = sum(j["cap_gpu_h"] for j in pilot)
    exp_total = sum(j["expected_gpu_h"] or 0 for j in pilot)

    # Full study (proposal; registered after the pilot)
    full_sessions = 256
    full_decode = full_sessions * 1_500
    full_prefill = 64 * (2_000 + 1_000 + 12_000 + 14_000)
    int4_gen = (0.075e6, 0.55e6)  # tokens per GPU-h, vLLM TP8 decode (dossier)
    int4_pre = (0.9e6, 4.5e6)  # tokens per GPU-h, prefill-only (dossier)
    tp8_load = (8 * 10 / 60, 8 * 20 / 60)  # GPU-h per TP8 load
    def rng(a, b):
        return [round(a, 2), round(b, 2)]
    full = {
        "F0 vLLM routed-experts capture smoke on Qwen3.6-35B-A3B (1 GPU)": rng(0.5, 0.5),
        "F1 INT4 TP8 generation with --enable-return-routed-experts (256 sessions)": rng(
            full_decode / int4_gen[1] + full_prefill / int4_pre[1] + 2 * tp8_load[0],
            full_decode / int4_gen[0] + full_prefill / int4_pre[0] + 2 * tp8_load[1]),
        "F2 INT4 teacher-forced re-pass of 64 sessions (decode against prefill routing)": rng(0.5e6 / int4_pre[1], 0.5e6 / int4_pre[0]),
        "F3 Q2 teacher-forced on the INT4 token sequences (INT4 against Q2 equivalence), 5 GPUs": rng(
            5 * ((full_prefill + full_decode) / 1_500 / 3600 + 5 / 60), 5 * ((full_prefill + full_decode) / 600 / 3600 + 15 / 60)),
        "F4 GLM 5.3 matched sessions for the speed ratio R, 3 GPUs (0 if on the CPU lane)": rng(
            3 * ((full_prefill) / 2_000 / 3600 + full_decode / 120 / 3600), 3 * ((full_prefill) / 800 / 3600 + full_decode / 40 / 3600)),
        "F5 Q2 decode traces at top-6 and top-4 (G5 input), 64 sessions each, 5 GPUs": rng(2 * 5 * 0.4, 2 * 5 * 0.8),
        "F6 optional Q8_K_XL numerics arm (594.5 GB download), GPUs 1-7 plus RAM": rng(1.0, 3.0),
        "F7 cache simulation, 1 against 4 streams, Belady, emulator": rng(0, 0),
    }
    full_lo = sum(v[0] for v in full.values())
    full_hi = sum(v[1] for v in full.values())
    out = {
        "pilot": {"jobs": pilot, "cap_gpu_h": round(cap_total, 3), "expected_gpu_h": round(exp_total, 3), "line": 8.0,
                  "tokens": {"sessions": sessions, "prefill": prefill_tok, "decode": decode_tok, "seeded_decode": seeded_decode, "repass": repass_tok}},
        "full": {"steps_gpu_h": full, "total_gpu_h": rng(full_lo, full_hi), "proposed_cap_gpu_h": 50,
                 "tokens": {"sessions": full_sessions, "decode": full_decode, "prefill": full_prefill}},
        "downloads_GB": {"pilot": {"GLM-5.3 IQ2_XXS (antirez/glm-5.3-gguf@1434dad1)": 211.08,
                                    "DeepSeek-V4-Flash-Vision-Exp MXFP4 (antirez/deepseek-v4-gguf@f71f23d5)": 155.98,
                                    "Kimi-K2.6 UD-Q2_K_XL (unsloth/Kimi-K2.6-GGUF@47c7cab1)": 340.48},
                         "pilot_total": round(211.08 + 155.98 + 340.48, 2),
                         "full_optional": {"Kimi-K2.6 UD-Q8_K_XL": 594.54}},
    }
    args.out.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    for j in pilot:
        print(f"{j['cap_gpu_h']:6.2f} cap  {j['expected_gpu_h']!s:>6} exp  {j['job']}")
    print("pilot cap", round(cap_total, 3), "expected", round(exp_total, 3))
    for k, v in full.items():
        print(v, k)
    print("full", rng(full_lo, full_hi))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
