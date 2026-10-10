#!/usr/bin/env python3
"""S2: GPU-hour arithmetic for Phase 0 caps and Phase 1 projections (D22 counting: caps, not expected use).

Nothing here is measured on this host for this model: the 35M Llama's BF16 throughput and the
fake-quant slowdown F are the main uncertainties, which is why Phase 0 measures them and Phase 1's
caps are set by the registered formula from that measurement. Anchors: the 134M GDN hybrid's
282,501 tok/s at 243 TFLOPS achieved (fla throughput doctor, Slurm 359,
legacy/research/evidence/infrastructure/fla-throughput-h100-2026-09-01.json); startup about 10 s
per arm (K1 probe 543 receipt); a GPU unit-test job at 0.0044 GPU-h (job 516). GPU-h = allocated
GPUs x wall time (scripts/submit_docker_research_job.py convention).

Usage: python cost_model.py <out.json>
"""

from __future__ import annotations

import json
import math
import sys

TOK_STEP = 64 * 1024  # 65,536 tokens per optimizer step
TRAIN_TOKENS = 18_311 * TOK_STEP  # 1,200,029,696 tokens per Phase 1 run

CASES = {  # BF16 tok/s per process, F (BF16/emulated, compiled, exact TF32 path), F_bf16path, compile s,
    # eager F, packing gain eta_2 / eta_4 (aggregate throughput of k processes on one GPU / one process)
    "low": dict(bf16=850e3, F=1.2, F_bf16path=1.1, compile=60, F_eager=2.5, eta2=1.7, eta4=2.4),
    "central": dict(
        bf16=600e3, F=2.0, F_bf16path=1.6, compile=120, F_eager=3.0, eta2=1.5, eta4=2.0
    ),
    "high": dict(bf16=400e3, F=4.0, F_bf16path=2.5, compile=300, F_eager=6.0, eta2=1.0, eta4=1.0),
}
STARTUP = 10.0


def r2(x: float) -> float:
    return round(x, 3)


def ceil05(x: float) -> float:
    return math.ceil(x * 20 - 1e-9) / 20


def phase0(c: dict) -> dict:
    t_bf = TOK_STEP / c["bf16"]
    t_q = t_bf * c["F"]
    t_q_bfpath = t_bf * c["F_bf16path"]
    comp = c["compile"]
    j0 = (
        0.0044 * 3600 * 3
    )  # three times the job-516 unit-test anchor (eager + compiled + GEMM checks)
    # J1: 10 configs x 200 compiled steps (BF16, 8 FP4 cells, NV-like on the BF16 path)
    j1 = (
        (STARTUP + comp + 200 * t_bf)
        + 8 * (STARTUP + comp + 200 * t_q)
        + (STARTUP + comp + 200 * t_q_bfpath)
    )
    j1 += (STARTUP + 60 * t_bf) + (
        STARTUP + 60 * t_bf * c["F_eager"]
    )  # eager arms: BF16 and NV-like, 60 steps
    for k, eta in (
        (2, c["eta2"]),
        (4, c["eta4"]),
    ):  # concurrency arms: k processes on one GPU, 200 steps each
        j1 += (STARTUP + comp + 200 * t_bf * k / eta) + (STARTUP + comp + 200 * t_q * k / eta)
    # J2: resume equivalence on the NV-like SR cell: 300 uninterrupted vs 150 + fresh-job resume 150
    j2 = 3 * (STARTUP + comp) + 600 * t_q
    # J3: BF16 capture run, 3,000 steps, tensors captured at steps 500, 1000, 2000, 3000
    j3 = STARTUP + comp + 3000 * t_bf + 60
    return {
        "J0_gpu_conformance_s": r2(j0),
        "J1_throughput_smoke_s": r2(j1),
        "J2_resume_s": r2(j2),
        "J3_capture_s": r2(j3),
        "total_gpu_h": r2((j0 + j1 + j2 + j3) / 3600),
    }


def phase1(c: dict, pack_k: int = 1) -> dict:
    eta = {1: 1.0, 2: c["eta2"], 4: c["eta4"]}[pack_k]
    r_bf = c["bf16"] * eta / pack_k  # per-process tok/s when k share a GPU
    r_q = c["bf16"] / c["F"] * eta / pack_k
    r_qb = c["bf16"] / c["F_bf16path"] * eta / pack_k
    evals_tokens = (
        19 * 2_000_000 + 15_000_000
    )  # periodic evals every 1,000 steps on 2M tokens + final on 15M

    def run_s(r):  # wall seconds of one process; GPU-seconds = wall / pack_k
        return TRAIN_TOKENS / r + evals_tokens / (3 * r) + STARTUP + c["compile"]

    bf, q, qb = run_s(r_bf) / pack_k, run_s(r_q) / pack_k, run_s(r_qb) / pack_k
    s1a = 8 * bf + 16 * q
    s1a_ext = 1 * bf + 2 * q  # at most one extension point per Stage-1a configuration
    s1b = 36 * q
    s1b_ext = 12 * q  # at most two extension points per Stage-1b cell
    emu = 3 * qb
    s1c = 8 * q  # conditional Stage 1c: seeds 45, 46 on the four decisive cells
    return {
        "pack_k": pack_k,
        "bf16_run_gpu_h": r2(bf / 3600),
        "fp4_run_gpu_h": r2(q / 3600),
        "stage1a_gpu_h": r2(s1a / 3600),
        "stage1a_max_gpu_h": r2((s1a + s1a_ext) / 3600),
        "stage1b_gpu_h": r2(s1b / 3600),
        "stage1b_max_gpu_h": r2((s1b + s1b_ext) / 3600),
        "emulation_control_gpu_h": r2(emu / 3600),
        "stage1c_conditional_gpu_h": r2(s1c / 3600),
        "total_no_extensions_gpu_h": r2((s1a + s1b + emu) / 3600),
        "total_max_gpu_h": r2((s1a + s1a_ext + s1b + s1b_ext + emu + s1c) / 3600),
        "registered_cap_formula_value_gpu_h": r2(
            1.2 * (s1a + s1a_ext + s1b + s1b_ext + emu + s1c) / 3600
        ),
    }


def main() -> None:
    out = {
        "script": "cost_model.py",
        "tokens_per_step": TOK_STEP,
        "train_tokens_per_run": TRAIN_TOKENS,
        "cases": CASES,
        "phase0": {},
        "phase1": {},
    }
    for name, c in CASES.items():
        out["phase0"][name] = phase0(c)
        out["phase1"][name] = {f"pack{k}": phase1(c, k) for k in (1, 2)}
    hi = out["phase0"]["high"]
    caps = {
        "J0": 0.10,
        "J1": ceil05(1.2 * hi["J1_throughput_smoke_s"] / 3600),
        "J2": ceil05(1.2 * hi["J2_resume_s"] / 3600),
        "J3": ceil05(1.2 * hi["J3_capture_s"] / 3600),
    }
    caps["sum"] = r2(sum(caps.values()))
    out["phase0_registered_caps_gpu_h"] = caps
    out["phase0_cap_rule"] = (
        "cap = 1.2 x the high case, rounded up to 0.05 GPU-h; J0 fixed at 0.10 (about 7.6x three job-516 anchors)"
    )
    with open(sys.argv[1], "w") as fh:
        json.dump(out, fh, indent=1)
    print("Phase 0:", json.dumps(out["phase0"]))
    print("Phase 0 caps:", caps)
    for name in CASES:
        for k in ("pack1", "pack2"):
            p = out["phase1"][name][k]
            print(
                f"Phase 1 {name:7s} {k}: 1a {p['stage1a_gpu_h']:.1f} (max {p['stage1a_max_gpu_h']:.1f}) 1b {p['stage1b_gpu_h']:.1f} "
                f"(max {p['stage1b_max_gpu_h']:.1f}) emu {p['emulation_control_gpu_h']:.1f} 1c {p['stage1c_conditional_gpu_h']:.1f} total {p['total_no_extensions_gpu_h']:.1f} "
                f"max {p['total_max_gpu_h']:.1f} cap-formula {p['registered_cap_formula_value_gpu_h']:.1f}"
            )


if __name__ == "__main__":
    main()
