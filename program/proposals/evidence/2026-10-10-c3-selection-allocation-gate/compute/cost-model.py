#!/usr/bin/env python3
"""S2: GPU-hour estimate and registered caps for the C3 Stage-0 gate (Qwen3-8B, thinking mode).

Measured inputs (repository evidence, read from the committed point files):
  serving-throughput-probe-v1 job B (Slurm 446, 2026-10-07): Qwen3-8B config with
  vLLM DUMMY weights on one H100 in the cu129 overlay of
  vllm/vllm-openai@sha256:b18abb2d..., gpu_memory_utilization 0.9,
  max_model_len 32768, max_num_batched_tokens 16384, max_num_seqs 256, prefix
  caching on, bf16; engine facts weights 15.27 GiB, KV 53.34 GiB = 388,384 tokens
  (README line 77). Points b1a/b1b/b1c (8 prompts x n=8, 1,152 in, 4,096 out),
  b2 (4 x 8, 1,152 in, 8,192 out), b3 (8 x 8, 4,096 in, 4,096 out), b6 (3 x 8,
  16,384 in, 8,192 out); fixed lengths.
  Real-weight Qwen3-8B throughput has NEVER been measured on this host; real
  versus dummy equivalence was shown only for Qwen3.5-9B (probe v2, Slurm 466).

Model (assumption, stated): decode is bound by HBM reads. One engine step reads
the weights once plus the KV of every active token and costs a fixed time per
active sequence: t = (W + KV_active * kv) / BW + n * tau. Under a full queue
vLLM keeps the KV pool at occupancy occ of capacity C. Then the GPU time of a
trace of L generated tokens with prompt P is additive over traces:

    gpu_s(L) = tau * L + (P * L + L^2 / 2) * (W / (occ * C) + kv) / BW,

times (1 + preemption recompute), plus fixed per-job overhead (engine start,
CUDA graph capture, drain tail). So cost scales with E[L^2], not with tokens.
The HF prefill that extracts answer-token states costs
(2 * N_nonemb * T + 4 * layers * heads * head_dim * T^2 / 2) / (MFU * 989 TFLOP/s)
per trace, T = P + L, plus a load overhead. Lengths are gamma with mean m and
coefficient of variation cv, truncated at the 32,768-token cap.

Central: BW and tau fitted to b1a/b1b/b1c/b2 (short shared prompts, the
regime closest to C3's short prompts), occ 0.92, preemption 5%, overhead
0.15 GPU-h per decode job, prefill MFU 40%. High: BW from b3 (2.18 TB/s,
the slower long-context point) with the same tau, occ 0.85, preemption 12%,
overhead 0.25 GPU-h, prefill MFU 25%.

Registered cap formula (fixed before P0 runs, D22): cap = 1.2 x high estimate
for each G job; smoke 0.25 and P0 1.0 are fixed caps. Admission requires the sum
of all caps <= 8.0 GPU-h (D20/D22/D24).

Usage: python cost-model.py [<out.json>]
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.stats import gamma

ROOT = Path(__file__).resolve().parents[5]
POINTS = ROOT / "program/evidence/2026-10-07/serving-throughput-probe-v1/jobs/b-446/probe/points"

GIB = 2 ** 30
W_BYTES = 15.27 * GIB                     # engine fact, job B
KV_CAP = 388_384                          # tokens, engine fact, job B
KV_PER_TOKEN = 36 * 8 * 128 * 2 * 2       # layers x KV heads x head_dim x (K,V) x bf16 = 147,456 B
N_NONEMB = 6.95e9                         # Qwen3-8B non-embedding parameters (36 x 193M)
ATTN_COEF = 2 * 36 * 32 * 128             # FLOPs per T^2 for causal attention: 294,912
PEAK = 989e12                             # H100 SXM dense BF16
CAP_TOKENS = 32_768
PROMPT = 250                              # math problem plus chat template (assumed)
DRAWS = 6


def load_points() -> dict:
    pts = {}
    for name in ("b1a", "b1b", "b1c", "b2", "b3", "b6"):
        rec = json.loads((POINTS / f"{name}.json").read_text())
        par, res = rec["params"], rec["result"]
        n = par["prompts"] * par["n"]
        step = n / res["output_throughput"]
        kv_avg = par["prompts"] * par["input_tokens"] + n * par["output_tokens"] / 2  # prompt KV shared across n
        pts[name] = {"n_seqs": n, "input": par["input_tokens"], "output": par["output_tokens"],
                     "tok_s": res["output_throughput"], "step_ms": 1e3 * step,
                     "bytes_per_step": W_BYTES + kv_avg * KV_PER_TOKEN,
                     "bw_single_param_TBps": (W_BYTES + kv_avg * KV_PER_TOKEN) / step / 1e12}
    return pts


def fit_bw_tau(pts: dict) -> tuple[float, float]:
    rows = [pts[k] for k in ("b1a", "b1b", "b1c", "b2")]
    a = np.array([[r["bytes_per_step"], r["n_seqs"]] for r in rows])
    t = np.array([r["step_ms"] / 1e3 for r in rows])
    coef, *_ = np.linalg.lstsq(a, t, rcond=None)
    return 1.0 / coef[0], coef[1]


def length_moments(mean: float, cv: float) -> tuple[float, float, float]:
    """E[min(L,cap)], E[min(L,cap)^2], P(L >= cap) for gamma(mean, cv)."""
    shape = 1.0 / cv ** 2
    dist = gamma(shape, scale=mean / shape)
    xs = np.linspace(0, CAP_TOKENS, 20001)
    pdf = dist.pdf(xs)
    tail = dist.sf(CAP_TOKENS)
    m1 = np.trapezoid(xs * pdf, xs) + CAP_TOKENS * tail
    m2 = np.trapezoid(xs ** 2 * pdf, xs) + CAP_TOKENS ** 2 * tail
    return float(m1), float(m2), float(tail)


def decode_gpu_h(traces: int, mean: float, cv: float, case: dict) -> float:
    m1, m2, _ = length_moments(mean, cv)
    per_kv_token_step = (W_BYTES / (case["occ"] * KV_CAP) + KV_PER_TOKEN) / case["bw"]
    per_trace = case["tau"] * m1 + (PROMPT * m1 + m2 / 2.0) * per_kv_token_step
    return traces * per_trace * (1 + case["preempt"]) / 3600.0 + case["overhead_h"]


def prefill_gpu_h(traces: int, mean: float, cv: float, case: dict) -> float:
    m1, m2, _ = length_moments(mean, cv)
    t1 = PROMPT + m1
    t2 = PROMPT ** 2 + 2 * PROMPT * m1 + m2
    flops = 2 * N_NONEMB * t1 + ATTN_COEF * t2
    return traces * flops / (case["mfu"] * PEAK) / 3600.0 + case["load_h"]


def caps_for(n_q: int, mean: float, cv: float, high: dict) -> dict:
    traces = n_q * DRAWS
    dec = round(1.2 * decode_gpu_h(traces, mean, cv, high), 2)
    pre = round(1.2 * prefill_gpu_h(traces, mean, cv, high), 2)
    total = round(0.25 + 1.0 + dec + pre, 2)
    return {"smoke": 0.25, "P0": 1.0, "G_decode": dec, "G_prefill": pre, "sum": total}


def n_rule(mean: float, cv: float, high: dict, n_max: int = 800, n_min: int = 560, step: int = 40) -> int | None:
    n = n_max
    while n >= n_min:
        if caps_for(n, mean, cv, high)["sum"] <= 8.0:
            return n
        n -= step
    return None


def main() -> int:
    pts = load_points()
    bw, tau = fit_bw_tau(pts)
    central = {"bw": bw, "tau": tau, "occ": 0.92, "preempt": 0.05, "overhead_h": 0.15, "mfu": 0.40, "load_h": 0.03}
    high = {"bw": pts["b3"]["bw_single_param_TBps"] * 1e12, "tau": tau, "occ": 0.85, "preempt": 0.12,
            "overhead_h": 0.25, "mfu": 0.25, "load_h": 0.05}
    # check: predicted versus measured step time for every job-B point
    check = {}
    for name, r in pts.items():
        pred = r["bytes_per_step"] / bw + r["n_seqs"] * tau
        check[name] = {"measured_ms": round(r["step_ms"], 3), "predicted_ms_central_fit": round(1e3 * pred, 3),
                       "bw_single_param_TBps": round(r["bw_single_param_TBps"], 3)}
    grid = []
    for mean in (4000, 5000, 6000, 6500, 7000, 8000, 9000, 10000, 12000):
        for cv in (0.6, 0.75, 0.9):
            m1, m2, tail = length_moments(mean, cv)
            row = {"mean_L": mean, "cv": cv, "E_min_L_cap": round(m1), "P_cap": round(tail, 4)}
            for label, case in (("central", central), ("high", high)):
                row[f"G800_decode_{label}"] = round(decode_gpu_h(800 * DRAWS, mean, cv, case), 2)
                row[f"G800_prefill_{label}"] = round(prefill_gpu_h(800 * DRAWS, mean, cv, case), 2)
            row["caps_N800"] = caps_for(800, mean, cv, high)
            row["N_rule"] = n_rule(mean, cv, high)
            grid.append(row)
    p0 = {}
    for mean in (6000, 9000, 12000, 15000):
        p0[f"mean{mean}_cv0.75"] = {
            "central": round(decode_gpu_h(240, mean, 0.75, central) + prefill_gpu_h(32, mean, 0.75, central), 3),
            "high": round(decode_gpu_h(240, mean, 0.75, high) + prefill_gpu_h(32, mean, 0.75, high), 3)}
    out = {
        "script": "cost-model.py",
        "measured_inputs": {"source": "program/evidence/2026-10-07/serving-throughput-probe-v1/jobs/b-446/probe/points/*.json (DUMMY weights)",
                            "weights_GiB": 15.27, "kv_capacity_tokens": KV_CAP, "kv_bytes_per_token": KV_PER_TOKEN,
                            "points": {k: {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in v.items()}
                                       for k, v in pts.items()}},
        "fit": {"bw_TBps_central": round(bw / 1e12, 3), "tau_ms_per_seq_step": round(1e3 * tau, 4),
                "bw_TBps_high": round(high["bw"] / 1e12, 3), "step_time_check": check},
        "cases": {"central": {k: (round(v, 6) if isinstance(v, float) else v) for k, v in central.items()},
                  "high": {k: (round(v, 6) if isinstance(v, float) else v) for k, v in high.items()}},
        "assumptions": {"prompt_tokens": PROMPT, "draws_per_question": DRAWS, "length_cap": CAP_TOKENS,
                        "length_distribution": "gamma(mean, cv), truncated at the cap (capped traces cost the cap)",
                        "prefill_flops": "2 * 6.95e9 * T + 294,912 * T^2 (lm_head skipped)",
                        "not_measured": "real-weight Qwen3-8B decode, unshared variable-length traffic at KV saturation, preemption, HF prefill MFU"},
        "P0_120q_x2_plus_32_prefill": p0,
        "G_grid": grid,
        "cap_formula": "cap(job) = 1.2 x high estimate for G decode and G prefill; smoke 0.25 and P0 1.0 fixed; admission iff sum <= 8.0 GPU-h; N_q = largest multiple of 40 in [560, 800] that admits, else not frozen",
    }
    text = json.dumps(out, indent=1) + "\n"
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(text, encoding="utf-8")
    print(json.dumps(out["fit"], indent=1))
    for row in grid:
        if row["cv"] == 0.75:
            print(row["mean_L"], row["P_cap"], "dec c/h", row["G800_decode_central"], row["G800_decode_high"],
                  "pre c/h", row["G800_prefill_central"], row["G800_prefill_high"], "caps", row["caps_N800"]["sum"],
                  "N_rule", row["N_rule"])
    print({k: {kk: float(vv) for kk, vv in v.items()} for k, v in p0.items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
