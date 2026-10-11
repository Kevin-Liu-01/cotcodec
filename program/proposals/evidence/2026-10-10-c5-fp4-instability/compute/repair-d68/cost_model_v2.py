#!/usr/bin/env python3
"""S2v2: GPU-hour arithmetic for v2 (D22 counting: caps, never expected use).

Phase 0 (Part A) fixed caps J0-J3 are 1.2 x the high case, rounded up to 0.05 GPU-h, each derived
from its own registered workload (wave 1 copied J0 from another job; J0 is now derived). J4, the
sigma-and-anchor probe, has a formula cap set from J1's measurement and runs only if the Phase 0 sum
of caps stays at or below 8.0 GPU-h (D20/D22); otherwise PROBE_OVER_LINE and the probe goes to Kevin
with Part B. Phase 1 (Part B) caps follow the registered formula
    GPU-seconds per run = [T / (0.9 r) + E / (3 x 0.9 r) + o] / k
with T the training tokens per run, E the evaluation tokens per run, r the J1 median per-process tok/s
of that run type at the adopted packing k (k = 2 only if J1's measured aggregate gain is >= 1.2), and o
J1's startup plus compile time; cap = 1.2 x the sum over the maximum run counts at the probe's seed
count n. Wave 1's table omitted the 0.9 factor that its own formula contains; the corrected wave-1
values are printed for the record.

Nothing here is measured for this model on this host. Anchors: the 134M GDN hybrid's 282,501 tok/s
(Slurm 359), about 10 s start-up per arm (K1 probe 543), a GPU unit-test job of 0.0044 GPU-h (job 516),
H100 SXM FP64 tensor-core peak 67 TFLOPS (vendor datasheet; host nvidia-smi reports H100 80GB HBM3 at
700 W per the wave-1 feasibility refuter). GPU-h = allocated GPUs x wall time.

Usage: python cost_model_v2.py <out.json>
"""

from __future__ import annotations

import json
import math
import sys

TOK_STEP = 64 * 1024
STEPS = 9_155
T = STEPS * TOK_STEP  # 599,982,080 training tokens per Phase 1 run and per probe run
E = 9 * 2_000_000 + 15_000_000 + 15_000_000  # periodic evals (steps 1,000..9,000), final own-forward, final BF16-forward
STARTUP = 10.0
CASES = {  # BF16 tok/s per process; F total (BF16 / emulated, compiled); F_tf32 (BF16 / TF32-operand baseline);
    # F_bf16path (control path); model compile s; quantizer-only compile s (J0); eager F; 2-process aggregate gain
    "low": dict(bf16=850e3, F=1.2, F_tf32=1.1, F_bf16path=1.1, compile=60, qcompile=15, F_eager=2.5, eta2=1.7),
    "central": dict(bf16=600e3, F=2.0, F_tf32=1.4, F_bf16path=1.6, compile=120, qcompile=30, F_eager=3.0, eta2=1.5),
    "high": dict(bf16=400e3, F=4.0, F_tf32=2.0, F_bf16path=2.5, compile=300, qcompile=60, F_eager=6.0, eta2=1.0),
}
N_FP4_CELLS = 10
FP64_PEAK, FP64_EFF = 67e12, 0.5


def ceil05(x: float) -> float:
    return math.ceil(x * 20 - 1e-9) / 20


def r3(x: float) -> float:
    return round(x, 3)


def gemm_flops_per_set() -> float:
    """Distinct (M, K, N) GEMM shapes of one transformer block's quantized linears at 65,536 tokens."""
    layers = [(384, 1152), (384, 384), (384, 1024), (1024, 384)]  # (in, out): QKV, attn-out, gate/up, down
    shapes = set()
    for din, dout in layers:
        shapes.add((TOK_STEP, din, dout))  # Fprop  X W^T
        shapes.add((TOK_STEP, dout, din))  # Dgrad  dY W
        shapes.add((din, TOK_STEP, dout))  # Wgrad  X^T dY
    return float(sum(2 * m * k * n for m, k, n in shapes)), len(shapes)


def phase0_fixed(c: dict) -> dict:
    t_bf = TOK_STEP / c["bf16"]
    t_q, t_tf, t_qb = t_bf * c["F"], t_bf * c["F_tf32"], t_bf * c["F_bf16path"]
    flops_set, n_shapes = gemm_flops_per_set()
    # J0: start-up; quantizer compile per cell; conformance vectors (about 0.8e9 quantize evaluations, eager and
    # compiled, launch-bound: 60 s high, 30 central, 15 low); GEMM bound: 50 random GEMMs per distinct shape
    # and cell against FP64, value and |a||b| (2 x the FLOPs) at 50% of FP64 peak
    vectors = {"low": 15, "central": 30, "high": 60}[next(k for k, v in CASES.items() if v is c)]
    gemm = 50 * N_FP4_CELLS * flops_set * 2 / (FP64_PEAK * FP64_EFF)
    j0 = STARTUP + N_FP4_CELLS * c["qcompile"] + vectors + gemm + 30  # 30 s operand generation and copies
    # J1: 13 compiled configurations (BF16, TF32-operand baseline, 10 FP4 cells, control path), 120 steps each;
    # eager BF16 and NV-like, 60 steps; NV-like packed 2 per GPU, 120 steps each
    per = lambda t: STARTUP + c["compile"] + 120 * t  # noqa: E731
    j1 = per(t_bf) + per(t_tf) + N_FP4_CELLS * per(t_q) + per(t_qb)
    j1 += (STARTUP + 60 * t_bf) + (STARTUP + 60 * t_bf * c["F_eager"])
    j1 += STARTUP + c["compile"] + 120 * t_q * 2 / c["eta2"]
    # J2: uninterrupted 200 steps against 100 + checkpoint + fresh-job resume 100, three processes
    j2 = 3 * (STARTUP + c["compile"]) + 400 * t_q
    # J3: BF16 capture, 3,000 steps, tensors at steps 500, 1,000, 2,000, 3,000 (60 s of I/O)
    j3 = STARTUP + c["compile"] + 3000 * t_bf + 60
    return {"J0_s": r3(j0), "J0_gemm_check_s": r3(gemm), "gemm_flops_per_shape_set": flops_set, "distinct_gemm_shapes": n_shapes,
            "J1_s": r3(j1), "J2_s": r3(j2), "J3_s": r3(j3), "sum_gpu_h": r3((j0 + j1 + j2 + j3) / 3600)}


def run_gpu_s(r: float, o: float, k: int = 1, factor: float = 0.9, tokens: int = T, evals: int = E) -> float:
    return (tokens / (factor * r) + evals / (3 * factor * r) + o) / k


def rates(c: dict, k: int) -> dict:
    eta = 1.0 if k == 1 else c["eta2"]
    return {"bf16": c["bf16"] * eta / k, "fp4": c["bf16"] / c["F"] * eta / k, "ctrl": c["bf16"] / c["F_bf16path"] * eta / k}


def probe_cap(c: dict, k: int = 1) -> float:
    o = STARTUP + c["compile"]
    return 1.2 * 6 * run_gpu_s(rates(c, k)["fp4"], o, k) / 3600


def phase1(c: dict, n: int, k: int = 1) -> dict:
    o = STARTUP + c["compile"]
    r = rates(c, k)
    g = {name: run_gpu_s(r[name], o, k) / 3600 for name in r}
    counts_max = {"bf16": 5 + 1 + n, "fp4": N_FP4_CELLS * (3 + 2) + N_FP4_CELLS * n, "ctrl": n}
    counts_noext = {"bf16": 5 + n, "fp4": N_FP4_CELLS * 3 + N_FP4_CELLS * n, "ctrl": n}
    tot_max = sum(counts_max[x] * g[x] for x in g)
    tot_noext = sum(counts_noext[x] * g[x] for x in g)
    return {"n": n, "pack_k": k, "per_run_gpu_h": {x: r3(v) for x, v in g.items()}, "run_counts_max": counts_max,
            "total_no_extensions_gpu_h": r3(tot_noext), "total_max_gpu_h": r3(tot_max), "cap_gpu_h": r3(1.2 * tot_max)}


def wave1_corrected(c: dict, k: int) -> dict:
    """Wave 1's Phase 1 formula (1.2B tokens, 8-cell design, Stage 1a/1b/1c counts) with and without its 0.9 factor."""
    tok1, ev1 = 18_311 * TOK_STEP, 19 * 2_000_000 + 15_000_000
    o = STARTUP + c["compile"]
    r = rates(c, k)
    out = {}
    for f in (1.0, 0.9):
        bf = run_gpu_s(r["bf16"], o, k, f, tok1, ev1)
        q = run_gpu_s(r["fp4"], o, k, f, tok1, ev1)
        qb = run_gpu_s(r["ctrl"], o, k, f, tok1, ev1)
        tot = 9 * bf + 18 * q + 48 * q + 3 * qb + 8 * q  # 1a: 8 BF16 + 16 FP4 + 3 ext (1 BF16, 2 FP4); 1b 36 + 12; control 3; 1c 8
        out["factor_" + str(f)] = {"total_max_gpu_h": r3(tot / 3600), "cap_gpu_h": r3(1.2 * tot / 3600)}
    return out


def main() -> None:
    out = {"script": "cost_model_v2.py", "tokens_per_run": T, "steps_per_run": STEPS, "eval_tokens_per_run": E, "cases": CASES,
           "phase0_fixed": {}, "phase0_registered_caps_gpu_h": {}, "probe_J4": {}, "phase1": {}, "wave1_phase1_corrected": {}}
    for name, c in CASES.items():
        out["phase0_fixed"][name] = phase0_fixed(c)
    hi = out["phase0_fixed"]["high"]
    caps = {j: ceil05(1.2 * hi[f"{j}_s"] / 3600) for j in ("J0", "J1", "J2", "J3")}
    caps["sum_fixed"] = r3(sum(caps.values()))
    out["phase0_registered_caps_gpu_h"] = caps
    room = 8.0 - caps["sum_fixed"]
    for name, c in CASES.items():
        cap1 = probe_cap(c, 1)
        out["probe_J4"][name] = {"cap_k1_gpu_h": r3(cap1), "phase0_total_k1": r3(caps["sum_fixed"] + cap1), "fits_k1": cap1 <= room}
        if c["eta2"] >= 1.2:
            cap2 = probe_cap(c, 2)
            out["probe_J4"][name].update({"cap_k2_gpu_h": r3(cap2), "phase0_total_k2": r3(caps["sum_fixed"] + cap2), "fits_k2": cap2 <= room})
    # break-even per-process emulated throughput for the probe at k = 1 (o = start-up + compile)
    out["probe_J4"]["room_gpu_h"] = r3(room)
    out["probe_J4"]["break_even_fp4_tok_per_s"] = {
        f"compile_{cmp}s": round((T / 0.9 + E / 2.7) / (room * 3600 / (1.2 * 6) - (STARTUP + cmp))) for cmp in (60, 120, 300)}
    for name, c in CASES.items():
        out["phase1"][name] = {f"n{n}_k1": phase1(c, n, 1) for n in (3, 4, 5, 6)}
        if c["eta2"] >= 1.2:
            out["phase1"][name].update({f"n{n}_k2": phase1(c, n, 2) for n in (3, 4, 5, 6)})
        out["wave1_phase1_corrected"][name] = {f"k{k}": wave1_corrected(c, k) for k in (1, 2)}
    # worked example for the proposal (central, n = 3, k = 1)
    c = CASES["central"]
    r = rates(c, 1)
    o = STARTUP + c["compile"]
    out["worked_example_central_n3_k1"] = {
        "fp4_run": f"[{T:,} / (0.9 x {r['fp4']:,.0f}) + {E:,} / (3 x 0.9 x {r['fp4']:,.0f}) + {o:.0f}] = "
                   f"{T / (0.9 * r['fp4']):,.0f} + {E / (2.7 * r['fp4']):,.0f} + {o:.0f} = {run_gpu_s(r['fp4'], o):,.0f} s = {run_gpu_s(r['fp4'], o) / 3600:.3f} GPU-h",
        "bf16_run": f"{run_gpu_s(r['bf16'], o):,.0f} s = {run_gpu_s(r['bf16'], o) / 3600:.3f} GPU-h",
        "control_run": f"{run_gpu_s(r['ctrl'], o):,.0f} s = {run_gpu_s(r['ctrl'], o) / 3600:.3f} GPU-h",
    }
    with open(sys.argv[1], "w") as fh:
        json.dump(out, fh, indent=1)
    print("Phase 0 fixed (s):", json.dumps(out["phase0_fixed"]))
    print("Phase 0 caps:", caps, "room for J4:", r3(room))
    print("J4:", json.dumps(out["probe_J4"]))
    for name in CASES:
        for key, p in out["phase1"][name].items():
            print(f"Phase 1 {name:7s} {key}: per-run {p['per_run_gpu_h']} total(no ext) {p['total_no_extensions_gpu_h']} max {p['total_max_gpu_h']} cap {p['cap_gpu_h']}")
    print("wave 1 corrected:", json.dumps(out["wave1_phase1_corrected"]))
    print(json.dumps(out["worked_example_central_n3_k1"], indent=1))


if __name__ == "__main__":
    main()
