#!/usr/bin/env python3
"""D1v2: estimability of the v2 cell set and the standard error of every registered v2 contrast.

v2 cells: {E2M1, INT4} x {S1 E8M0/B32, S2 E8M0/B16, S3 UE4M3+FP32/B16, S4 UE4M3+FP32/B32, S5 BF16/B32}.
Model: mu + grid(INT4) + block(B32) + scale family dummies (UE4M3, BF16; reference E8M0)
+ grid:block + grid:UE4M3 + grid:BF16 + block:UE4M3 + grid:block:UE4M3. (BF16 occurs only at B32, so
block:BF16 is not a separate parameter.) A coefficient is estimable iff its unit vector lies in the row
space of the design matrix. The v1 set (no S4) is checked under the same model for comparison.

Contrast SE in units of the per-run residual SD sigma with n fresh seeds per cell (RCBD, seed blocks):
SE = sigma * sqrt(sum(c^2) / n). 80%-power MDE with the RCBD residual df 9 (n - 1): for a one-sided 5%
test (t_0.95 + t_0.80) * SE, and for the one-sided 2.5% test on which P2 is decided (95% intervals,
S1v2) (t_0.975 + t_0.80) * SE.

Usage: python doe_v2.py <out.json>
"""

from __future__ import annotations

import json
import sys

import numpy as np
from scipy import stats

CFG = {"S1": (32, "E8M0"), "S2": (16, "E8M0"), "S3": (16, "UE4M3"), "S4": (32, "UE4M3"), "S5": (32, "BF16")}


def design(cfgs):
    names = ["mu", "INT4", "B32", "UE4M3", "BF16", "INT4:B32", "INT4:UE4M3", "INT4:BF16", "B32:UE4M3", "INT4:B32:UE4M3"]
    rows = []
    for g in ("E2M1", "INT4"):
        for s in cfgs:
            b, fam = CFG[s]
            gi, bi, ui, fi = float(g == "INT4"), float(b == 32), float(fam == "UE4M3"), float(fam == "BF16")
            rows.append([1, gi, bi, ui, fi, gi * bi, gi * ui, gi * fi, bi * ui, gi * bi * ui])
    X = np.array(rows)
    used = [j for j in range(len(names)) if X[:, j].any()]
    return X[:, used], [names[j] for j in used]


def estimable(X, names):
    P = np.linalg.pinv(X) @ X
    return {n: bool(np.allclose(P[:, j], np.eye(len(names))[:, j], atol=1e-8)) for j, n in enumerate(names)}


def main() -> None:
    out = {"script": "doe_v2.py", "cell_sets": {}}
    for label, cfgs in {"v1 (S1, S2, S3, S5)": ["S1", "S2", "S3", "S5"],
                        "v2 (S1, S2, S3, S4, S5)": ["S1", "S2", "S3", "S4", "S5"]}.items():
        X, names = design(cfgs)
        est = estimable(X, names)
        out["cell_sets"][label] = {"cells": 2 * len(cfgs), "rank": int(np.linalg.matrix_rank(X)), "parameters": len(names),
                                   "estimable": [n for n in names if est[n]], "not_estimable": [n for n in names if not est[n]]}
        print(label, out["cell_sets"][label])
    cells = [f"{g}/{s}" for g in ("E2M1", "INT4") for s in CFG]
    idx = {c: i for i, c in enumerate(cells)}

    def vec(t):
        v = np.zeros(len(cells))
        for k, w in t.items():
            v[idx[k]] += w
        return v

    def inter(a, b):
        return vec({f"INT4/{a}": 1, f"INT4/{b}": -1, f"E2M1/{a}": -1, f"E2M1/{b}": 1})

    def avg(a, b):
        return vec({f"E2M1/{a}": .5, f"INT4/{a}": .5, f"E2M1/{b}": -.5, f"INT4/{b}": -.5})

    C = {
        "Delta_G (INT4 - E2M1, mean over the 5 configurations)": vec({**{f"INT4/{s}": .2 for s in CFG}, **{f"E2M1/{s}": -.2 for s in CFG}}),
        "C_fmt_bar (E8M0 - UE4M3, mean over grids and B16/B32)": 0.5 * (avg("S2", "S3") + avg("S1", "S4")),
        "C_prec32 (S1 - S5: E8M0 - BF16 scale at B32)": avg("S1", "S5"),
        "C_blk_bar (B32 - B16, mean over E8M0 and UE4M3)": 0.5 * (avg("S1", "S2") + avg("S4", "S3")),
        "C_anchor (E2M1/S1 - E2M1/S3, MX-like - NV-like)": vec({"E2M1/S1": 1, "E2M1/S3": -1}),
        "I_prec32 (P2: (INT4 S1-S5) - (E2M1 S1-S5))": inter("S1", "S5"),
        "I_fmt16 ((INT4 S2-S3) - (E2M1 S2-S3))": inter("S2", "S3"),
        "I_fmt32 ((INT4 S1-S4) - (E2M1 S1-S4))": inter("S1", "S4"),
        "I_fmt_bar (mean of I_fmt16 and I_fmt32)": 0.5 * (inter("S2", "S3") + inter("S1", "S4")),
        "I_blk_E8 ((INT4 S1-S2) - (E2M1 S1-S2))": inter("S1", "S2"),
        "I_blk_UE ((INT4 S4-S3) - (E2M1 S4-S3))": inter("S4", "S3"),
        "I3 (I_fmt32 - I_fmt16)": inter("S1", "S4") - inter("S2", "S3"),
        "I_range32 ((INT4 S4-S5) - (E2M1 S4-S5))": inter("S4", "S5"),
    }
    C["D1 = C_fmt_bar - 2 Delta_G"] = C["C_fmt_bar (E8M0 - UE4M3, mean over grids and B16/B32)"] - 2 * C["Delta_G (INT4 - E2M1, mean over the 5 configurations)"]
    out["contrasts"] = {}
    for k, c in C.items():
        row = {"coefficients": {cc: float(c[i]) for cc, i in idx.items() if abs(c[i]) > 1e-12}, "sum_c2": float((c**2).sum())}
        for n in (3, 4, 5, 6):
            df = 9 * (n - 1)
            se = float(np.sqrt((c**2).sum() / n))
            row[f"SE_over_sigma_n{n}"] = round(se, 4)
            row[f"MDE80_one_sided5_over_sigma_n{n}"] = round(float((stats.t.ppf(.95, df) + stats.t.ppf(.80, df)) * se), 3)
            row[f"MDE80_one_sided2.5_over_sigma_n{n}"] = round(float((stats.t.ppf(.975, df) + stats.t.ppf(.80, df)) * se), 3)
        out["contrasts"][k] = row
        print(f"{k:62s} SE n3 {row['SE_over_sigma_n3']:.3f} MDE80(2.5%) n3/4/5/6 " + "/".join(f"{row[f'MDE80_one_sided2.5_over_sigma_n{n}']:.2f}" for n in (3, 4, 5, 6)))
    # n rule of the probe: MDE80 (one-sided 2.5%) of an interaction contrast (sum_c2 = 4) at n seeds, sigma units
    out["n_rule_thresholds_ratio_C_over_sigma"] = {
        str(n): round(float((stats.t.ppf(.975, 9 * (n - 1)) + stats.t.ppf(.80, 9 * (n - 1))) * np.sqrt(4 / n)), 3) for n in (3, 4, 5, 6)}
    out["probe_G1_min_ratio_df2"] = round(float(stats.t.ppf(.95, 2) * np.sqrt(2 / 3)), 3)
    print("n rule thresholds", out["n_rule_thresholds_ratio_C_over_sigma"], "G1 min ratio", out["probe_G1_min_ratio_df2"])
    with open(sys.argv[1], "w") as fh:
        json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()
