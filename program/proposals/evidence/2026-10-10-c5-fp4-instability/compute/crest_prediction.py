#!/usr/bin/env python3
"""N2: pre-data, tensor-level prediction of the grid effect in each scale configuration.

A numpy reference quantizer (the CPU seed of Phase 0's reference) implements the
registered rules for the eight Phase 1 cells:

  grid  : E2M1 {0, .5, 1, 1.5, 2, 3, 4, 6} or symmetric INT4 {-7..7} (15 codes each)
  scale : S1 E8M0/B32, S2 E8M0/B16, S3 UE4M3+FP32 tensor scale/B16, S5 BF16/B32
  rule  : block scale = amax / q_max rounded UP to the scale format (no element saturates);
          S3: tensor scale s_t = amax_tensor / (q_max * 448), block scale rounded up in UE4M3
          relative to s_t, s_t applied after decoding (epilogue)
  round : round-to-nearest, ties to even code (the forward-pass rule)

It reports, on synthetic block data with block crest factors in the range measured on
Llama-3.1-8B tensors by arXiv 2510.25602 (Table 2), the quantization signal-to-noise ratio
(QSNR, dB), the block crest factor, and the relative magnitude bias (toward-zero shrinkage),
with and without a randomized Hadamard rotation (RHT, 32-point, applied before quantization).
The predicted grid effect per scale configuration is QSNR(E2M1) - QSNR(INT4) in dB
(positive: E2M1 better). This is a numerics prediction, not a training result; Phase 0
recomputes it on tensors captured from the BF16 model and freezes it before Phase 1.

Usage: python crest_prediction.py <out.json>     (seeds 42, 43, 44)
"""

from __future__ import annotations

import json
import sys

import numpy as np

E2M1 = np.array([0, 0.5, 1, 1.5, 2, 3, 4, 6], dtype=np.float64)
QMAX = {"E2M1": 6.0, "INT4": 7.0}


def round_grid(y: np.ndarray, grid: str) -> np.ndarray:
    if grid == "INT4":
        return np.clip(np.round(y), -7, 7)  # numpy rounds half to even
    a = np.minimum(np.abs(y), 6.0)
    idx = np.clip(np.searchsorted(E2M1, a, side="right") - 1, 0, 6)
    lo, hi = E2M1[idx], E2M1[idx + 1]
    mid = (lo + hi) / 2
    r = np.where(a < mid, lo, np.where(a > mid, hi, np.where(idx % 2 == 0, lo, hi)))
    return np.sign(y) * r


def round_up_e8m0(s: np.ndarray) -> np.ndarray:
    e = np.ceil(np.log2(np.maximum(s, 2.0**-127)))
    return 2.0 ** np.clip(e, -127, 127)


UE4M3 = np.array(
    sorted(
        {(m / 8) * 2.0**-6 for m in range(1, 8)}
        | {
            (1 + m / 8) * 2.0 ** (e - 7)
            for e in range(1, 16)
            for m in range(8)
            if not (e == 15 and m == 7)
        }
    )
)


def round_up_codebook(s: np.ndarray, book: np.ndarray) -> np.ndarray:
    idx = np.clip(np.searchsorted(book, s, side="left"), 0, len(book) - 1)
    return book[idx]


def round_up_bf16(s: np.ndarray) -> np.ndarray:
    f = s.astype(np.float32)
    u = f.view(np.uint32).astype(np.uint64)
    up = np.where((u & 0xFFFF) != 0, ((u >> 16) + 1) << 16, u)
    return up.astype(np.uint32).view(np.float32).astype(np.float64)


def quantize(x: np.ndarray, grid: str, cfg: str) -> np.ndarray:
    """x: (n, K) with blocks along K. Returns the decoded tensor (exact decode, epilogue tensor scale)."""
    B = 32 if cfg in ("S1", "S5") else 16
    n, K = x.shape
    xb = x.reshape(n, K // B, B)
    amax = np.abs(xb).max(axis=2, keepdims=True)
    q = QMAX[grid]
    if cfg in ("S1", "S2"):
        s_eff = round_up_e8m0(np.maximum(amax / q, 1e-300))
    elif cfg == "S5":
        s_eff = round_up_bf16(np.maximum(amax / q, 1e-38))
    elif cfg == "S3":
        s_t = np.abs(x).max() / (q * 448.0)
        s_b = round_up_codebook(np.maximum(amax / (q * s_t), UE4M3[0]), UE4M3)
        s_eff = s_b * s_t
    else:
        raise ValueError(cfg)
    y = round_grid(xb / s_eff, grid)
    return (y * s_eff).reshape(n, K)


def hadamard(n: int) -> np.ndarray:
    h = np.array([[1.0]])
    while h.shape[0] < n:
        h = np.block([[h, h], [h, -h]])
    return h / np.sqrt(n)


def make_data(dist: str, rng: np.random.Generator, n: int = 4096, K: int = 512) -> np.ndarray:
    if dist == "gaussian":
        x = rng.standard_normal((n, K))
    elif dist == "laplace":
        x = rng.laplace(size=(n, K))
    elif dist == "student_t3":
        x = rng.standard_t(3, size=(n, K))
    elif (
        dist == "gaussian_channel_outliers"
    ):  # 2% of columns scaled x8 (activation-like outlier channels)
        x = rng.standard_normal((n, K))
        cols = rng.choice(K, size=K // 50, replace=False)
        x[:, cols] *= 8.0
    elif dist == "lognormal_row_scales":  # gradient-like: per-row magnitudes spread over ~3 decades
        x = rng.standard_normal((n, K)) * np.exp(rng.normal(0, 1.5, size=(n, 1)))
    else:
        raise ValueError(dist)
    return (
        x * 1e-3
    )  # absolute magnitude irrelevant except for range-limited scales; S3 uses a tensor scale


def crest(x: np.ndarray, B: int) -> np.ndarray:
    xb = x.reshape(x.shape[0], -1, B)
    return (np.abs(xb).max(axis=2) / np.sqrt((xb**2).mean(axis=2))).ravel()


def main() -> None:
    dists = [
        "gaussian",
        "laplace",
        "student_t3",
        "gaussian_channel_outliers",
        "lognormal_row_scales",
    ]
    cfgs = ["S1", "S2", "S3", "S5"]
    out = {"script": "crest_prediction.py", "seeds": [42, 43, 44], "results": {}}
    H = hadamard(32)
    for dist in dists:
        for rht in (False, True):
            rows = {}
            for seed in (42, 43, 44):
                rng = np.random.default_rng(seed)
                x = make_data(dist, rng)
                if rht:
                    signs = rng.choice([-1.0, 1.0], size=32)
                    xr = x.reshape(x.shape[0], -1, 32) * signs
                    x = (xr @ H).reshape(x.shape)
                for grid in ("E2M1", "INT4"):
                    for cfg in cfgs:
                        xh = quantize(x, grid, cfg)
                        err = xh - x
                        qsnr = 10 * np.log10((x**2).sum() / (err**2).sum())
                        shrink = float(
                            ((np.abs(xh) - np.abs(x)) * (x != 0)).mean() / np.sqrt((x**2).mean())
                        )
                        rows.setdefault((grid, cfg), []).append((qsnr, shrink))
            k16, k32 = crest(x, 16), crest(x, 32)
            res = {
                "crest_B16_median": round(float(np.median(k16)), 3),
                "crest_B16_q75": round(float(np.quantile(k16, 0.75)), 3),
                "crest_B32_median": round(float(np.median(k32)), 3),
                "crest_B32_q75": round(float(np.quantile(k32, 0.75)), 3),
                "cells": {},
                "predicted_grid_effect_dB": {},
            }
            for (grid, cfg), vals in rows.items():
                v = np.array(vals)
                res["cells"][f"{grid}/{cfg}"] = {
                    "qsnr_dB_mean": round(float(v[:, 0].mean()), 3),
                    "qsnr_dB_sd_over_seeds": round(float(v[:, 0].std(ddof=1)), 4),
                    "rel_magnitude_bias": round(float(v[:, 1].mean()), 5),
                }
            for cfg in cfgs:
                res["predicted_grid_effect_dB"][cfg] = round(
                    res["cells"][f"E2M1/{cfg}"]["qsnr_dB_mean"]
                    - res["cells"][f"INT4/{cfg}"]["qsnr_dB_mean"],
                    3,
                )
            out["results"][f"{dist}{'+RHT' if rht else ''}"] = res
            print(
                f"{dist:28s} RHT={int(rht)} crest16 {res['crest_B16_median']:.2f} crest32 {res['crest_B32_median']:.2f} "
                "| E2M1-INT4 dB "
                + " ".join(f"{c}:{res['predicted_grid_effect_dB'][c]:+.2f}" for c in cfgs)
                + " | E2M1 qsnr "
                + " ".join(f"{c}:{res['cells'][f'E2M1/{c}']['qsnr_dB_mean']:.2f}" for c in cfgs)
            )
    with open(sys.argv[1], "w") as fh:
        json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()
