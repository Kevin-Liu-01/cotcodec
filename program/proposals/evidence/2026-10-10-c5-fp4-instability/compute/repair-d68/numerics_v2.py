#!/usr/bin/env python3
"""N2v2 and N3: tensor-level prediction for the v2 cell set, and the identification table.

v2 cell set (registration c5-fp4-instability-v2): grids {E2M1, symmetric INT4} crossed with five
scale configurations
  S1 E8M0/B32 (4.25 b)   S2 E8M0/B16 (4.5 b)   S3 UE4M3+FP32/B16 (4.5 b)
  S4 UE4M3+FP32/B32 (4.25 b, new in v2)       S5 BF16/B32 (4.5 b)
Registered quantizer (unchanged from v1 except the E8M0 floor): block amax / q_max rounded UP to
the scale format; E8M0 exponent clamped to [-126, 127] (v1: -127, an FP32 subnormal); BF16 scales
clamped at 2^-126; UE4M3 relative to a current FP32 tensor scale s_t = amax_tensor / (q_max * 448),
block code clamped to [2^-9, 448]; RTN ties to even; exact decode, tensor scale in the epilogue.

N2v2 (prediction, report-only parts as in v1): QSNR (whole tensor, dB), per-row (per-token)
QSNR averaged over rows, UE4M3 subnormal (code < 2^-6) and clamped (code = 2^-9 from below)
block fractions, and every registered v2 contrast in QSNR units and in noise-power units relative
to the anchor.

N3 (identification): every contrast recomputed under three mechanism toggles of the quantizer:
  exact   : scale rounding removed (block scale = amax / q_max exactly) in every configuration;
            power-of-two waste and UE4M3/BF16 mantissa rounding are gone, block size and range stay
  wide    : UE4M3 keeps its 3 mantissa bits but loses its range limit (no subnormals, no clamp)
  exact+wide
A contrast identifies the scale-precision (power-of-two) mechanism if it is near zero under `exact`
and unchanged under `wide`. Wave 1's I_blk kept 58-94% of its size under exact scales (identification
refuter); the v2 P2 contrast I_prec32 compares S1 with S5, which share block size and exponent range.

Contrast sign convention: loss direction (positive = INT4 penalised relative to E2M1 in the first
named configuration). In QSNR units a loss-direction difference is minus the QSNR difference.

Usage: python numerics_v2.py <out.json>     (seeds 42, 43, 44; 1,024 x 512 values per seed and distribution)
"""

from __future__ import annotations

import json
import sys

import numpy as np

E2M1 = np.array([0, 0.5, 1, 1.5, 2, 3, 4, 6], dtype=np.float64)
QMAX = {"E2M1": 6.0, "INT4": 7.0}
CFG = {  # block size, scale family
    "S1": (32, "E8M0"),
    "S2": (16, "E8M0"),
    "S3": (16, "UE4M3"),
    "S4": (32, "UE4M3"),
    "S5": (32, "BF16"),
}
CELLS = [f"{g}/{s}" for g in ("E2M1", "INT4") for s in CFG]

UE4M3 = np.array(
    sorted(
        {(m / 8) * 2.0**-6 for m in range(1, 8)}
        | {(1 + m / 8) * 2.0 ** (e - 7) for e in range(1, 16) for m in range(8) if not (e == 15 and m == 7)}
    )
)
UE4M3_MIN_NORMAL = 2.0**-6


def round_grid(y: np.ndarray, grid: str) -> np.ndarray:
    if grid == "INT4":
        return np.clip(np.round(y), -7, 7)  # numpy rounds half to even
    a = np.minimum(np.abs(y), 6.0)
    idx = np.clip(np.searchsorted(E2M1, a, side="right") - 1, 0, 6)
    lo, hi = E2M1[idx], E2M1[idx + 1]
    mid = (lo + hi) / 2
    r = np.where(a < mid, lo, np.where(a > mid, hi, np.where(idx % 2 == 0, lo, hi)))
    return np.sign(y) * r


def round_up_e8m0(s):
    e = np.ceil(np.log2(np.maximum(s, 2.0**-140)))
    return 2.0 ** np.clip(e, -126, 127)


def round_up_bf16(s):
    f = np.maximum(s, 2.0**-126).astype(np.float32)
    u = f.view(np.uint32).astype(np.uint64)
    up = np.where((u & 0xFFFF) != 0, ((u >> 16) + 1) << 16, u)
    return up.astype(np.uint32).view(np.float32).astype(np.float64)


def round_up_ue4m3(s):
    idx = np.clip(np.searchsorted(UE4M3, s, side="left"), 0, len(UE4M3) - 1)
    return UE4M3[idx]


def round_up_m3_unlimited(s):
    """3 mantissa bits, unlimited exponent range (UE4M3's precision without its range)."""
    e = np.floor(np.log2(s))
    m = np.ceil(s / 2.0**e * 8 - 1e-12) / 8
    return m * 2.0**e


def quantize(x: np.ndarray, grid: str, cfg: str, mode: str = "registered"):
    """x: (n, K), blocks along K. Returns (decoded tensor, diagnostics dict)."""
    B, fam = CFG[cfg]
    n, K = x.shape
    xb = x.reshape(n, K // B, B)
    amax = np.abs(xb).max(axis=2, keepdims=True)
    q = QMAX[grid]
    exact = "exact" in mode
    wide = "wide" in mode
    diag = {}
    if exact:
        s_eff = np.maximum(amax / q, 1e-300)
    elif fam == "E8M0":
        s_eff = round_up_e8m0(amax / q)
    elif fam == "BF16":
        s_eff = round_up_bf16(amax / q)
    else:  # UE4M3 with a current FP32 tensor scale
        s_t = np.abs(x).max() / (q * 448.0)
        rel = np.maximum(amax / (q * s_t), 1e-300)
        if wide:
            s_b = round_up_m3_unlimited(rel)
        else:
            s_b = round_up_ue4m3(np.maximum(rel, UE4M3[0]))
            nz = amax[..., 0] > 0
            diag = {
                "subnormal_block_fraction": float(((s_b[..., 0] < UE4M3_MIN_NORMAL) & nz).mean()),
                "clamped_block_fraction": float(((rel[..., 0] < UE4M3[0]) & nz).mean()),
            }
        s_eff = s_b * s_t
    y = round_grid(xb / s_eff, grid)
    return (y * s_eff).reshape(n, K), diag


def hadamard(n: int) -> np.ndarray:
    h = np.array([[1.0]])
    while h.shape[0] < n:
        h = np.block([[h, h], [h, -h]])
    return h / np.sqrt(n)


def make_data(dist: str, rng: np.random.Generator, n: int = 1024, K: int = 512) -> np.ndarray:
    if dist == "gaussian":
        x = rng.standard_normal((n, K))
    elif dist == "laplace":
        x = rng.laplace(size=(n, K))
    elif dist == "student_t3":
        x = rng.standard_t(3, size=(n, K))
    elif dist == "gaussian_channel_outliers":
        x = rng.standard_normal((n, K))
        cols = rng.choice(K, size=K // 50, replace=False)
        x[:, cols] *= 8.0
    elif dist == "lognormal_rows_1.5":  # wave 1's gradient-like rows
        x = rng.standard_normal((n, K)) * np.exp(rng.normal(0, 1.5, size=(n, 1)))
    elif dist == "lognormal_rows_2.5":  # identification refuter's wide per-token spread
        x = rng.standard_normal((n, K)) * np.exp(rng.normal(0, 2.5, size=(n, 1)))
    elif dist == "lognormal_rows_3.5":
        x = rng.standard_normal((n, K)) * np.exp(rng.normal(0, 3.5, size=(n, 1)))
    else:
        raise ValueError(dist)
    return x * 1e-3


def qsnr(x, xh):
    return 10 * np.log10((x**2).sum() / ((xh - x) ** 2).sum())


def qsnr_rows(x, xh):
    s = (x**2).sum(axis=1)
    e = ((xh - x) ** 2).sum(axis=1)
    ok = (s > 0) & (e > 0)
    return float(np.mean(10 * np.log10(s[ok] / e[ok])))


def contrasts(q: dict) -> dict:
    """q: cell -> QSNR (dB). Returns loss-direction contrasts in dB and noise-power ratios to the anchor."""
    L = {c: -v for c, v in q.items()}  # loss direction
    N = {c: 10 ** (-v / 10) for c, v in q.items()}

    def inter(d, a, b):
        return (d[f"INT4/{a}"] - d[f"INT4/{b}"]) - (d[f"E2M1/{a}"] - d[f"E2M1/{b}"])

    defs = {
        "I_prec32 (S1-S5)": ("S1", "S5"),
        "I_fmt16 (S2-S3)": ("S2", "S3"),
        "I_fmt32 (S1-S4)": ("S1", "S4"),
        "I_blk_E8 (S1-S2)": ("S1", "S2"),
        "I_blk_UE (S4-S3)": ("S4", "S3"),
        "I_range32 (S4-S5)": ("S4", "S5"),
    }
    out = {k: {"dB": round(inter(L, a, b), 3)} for k, (a, b) in defs.items()}
    out["I3 (I_fmt32-I_fmt16)"] = {"dB": round(out["I_fmt32 (S1-S4)"]["dB"] - out["I_fmt16 (S2-S3)"]["dB"], 3)}
    anchor_db = L["E2M1/S1"] - L["E2M1/S3"]
    anchor_n = N["E2M1/S1"] - N["E2M1/S3"]
    for k, (a, b) in defs.items():
        out[k]["noise_power_over_anchor"] = round(inter(N, a, b) / anchor_n, 3) if anchor_n > 0 else None
    out["anchor E2M1 S1-S3"] = {"dB": round(anchor_db, 3), "noise_power": float(anchor_n)}
    out["grid_effect_dB_by_cfg (E2M1 - INT4 QSNR)"] = {s: round(q[f"E2M1/{s}"] - q[f"INT4/{s}"], 3) for s in CFG}
    return out


def main() -> None:
    dists = ["gaussian", "laplace", "student_t3", "gaussian_channel_outliers",
             "lognormal_rows_1.5", "lognormal_rows_2.5", "lognormal_rows_3.5"]
    modes = ["registered", "exact", "wide", "exact+wide"]
    out = {"script": "numerics_v2.py", "seeds": [42, 43, 44], "cells": CELLS, "results": {}}
    H = hadamard(32)
    for dist in dists:
        for rht in (False, True):
            if rht and dist.startswith("lognormal_rows_") and dist != "lognormal_rows_1.5":
                continue
            key = f"{dist}{'+RHT' if rht else ''}"
            res = {}
            for mode in (modes if not rht else ["registered"]):
                qw, qr, dg = {}, {}, {}
                for seed in (42, 43, 44):
                    rng = np.random.default_rng(seed)
                    x = make_data(dist, rng)
                    if rht:
                        signs = rng.choice([-1.0, 1.0], size=32)
                        x = ((x.reshape(x.shape[0], -1, 32) * signs) @ H).reshape(x.shape)
                    for c in CELLS:
                        g, s = c.split("/")
                        xh, d = quantize(x, g, s, mode)
                        qw.setdefault(c, []).append(qsnr(x, xh))
                        qr.setdefault(c, []).append(qsnr_rows(x, xh))
                        for kk, vv in d.items():
                            dg.setdefault(c, {}).setdefault(kk, []).append(vv)
                qwm = {c: float(np.mean(v)) for c, v in qw.items()}
                qrm = {c: float(np.mean(v)) for c, v in qr.items()}
                res[mode] = {
                    "qsnr_whole_dB": {c: round(v, 3) for c, v in qwm.items()},
                    "qsnr_per_row_dB": {c: round(v, 3) for c, v in qrm.items()},
                    "contrasts_whole": contrasts(qwm),
                    "contrasts_per_row": contrasts(qrm),
                    "ue4m3_diagnostics": {c: {k: round(float(np.mean(v)), 4) for k, v in d.items()} for c, d in dg.items()},
                }
            out["results"][key] = res
            r = res["registered"]["contrasts_whole"]
            print(f"{key:30s} " + " ".join(f"{k.split()[0]}:{v['dB']:+.2f}" for k, v in r.items() if "dB" in v and k.startswith("I")))
            if not rht:
                for mode in modes[1:]:
                    rr = res[mode]["contrasts_whole"]
                    print(f"   {mode:12s} " + " ".join(f"{k.split()[0]}:{v['dB']:+.2f}" for k, v in rr.items() if k.startswith("I")))
    # identification summary: share of each contrast that survives each toggle (whole-tensor dB)
    ident = {}
    for key, res in out["results"].items():
        if "+RHT" in key:
            continue
        reg = res["registered"]["contrasts_whole"]
        row = {}
        for k in reg:
            if not k.startswith("I"):
                continue
            v0 = reg[k]["dB"]
            row[k] = {
                "registered_dB": v0,
                "exact_dB": res["exact"]["contrasts_whole"][k]["dB"],
                "wide_dB": res["wide"]["contrasts_whole"][k]["dB"],
                "exact_wide_dB": res["exact+wide"]["contrasts_whole"][k]["dB"],
                "share_surviving_exact": round(res["exact"]["contrasts_whole"][k]["dB"] / v0, 3) if abs(v0) > 0.05 else None,
                "per_row_registered_dB": res["registered"]["contrasts_per_row"][k]["dB"],
            }
        ident[key] = row
    out["identification_table"] = ident
    with open(sys.argv[1], "w") as fh:
        json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()
