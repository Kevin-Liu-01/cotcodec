#!/usr/bin/env python3
"""D1: estimability of the Phase 1 cell sets and the variance of every registered contrast.

Model for a cell set: mu + grid(INT4) + block(B32) + scale-type dummies (reference E8M0)
+ grid x block + grid x scale type. A coefficient is estimable iff its unit vector lies in
the row space of the design matrix (projection test). Compared:
  dossier    : {E8M0/B32, UE4M3+FP32/B16, UE5M3/B16, BF16/B32} x {E2M1, INT4}
  registered : {E8M0/B32, E8M0/B16, UE4M3+FP32/B16, BF16/B32} x {E2M1, INT4}
  extended   : registered plus UE5M3/B16 (10 cells)
Then, for the registered set with n seeds per cell, every registered contrast is written as
a coefficient vector over the 8 cell means and its standard error is reported in units of
the per-run residual SD sigma: SE = sigma * sqrt(sum(c^2) / n).

Usage: python doe.py <out.json>
"""

from __future__ import annotations

import json
import sys

import numpy as np

LEVELS = {
    "E8M0/B32": (32, "E8M0"),
    "E8M0/B16": (16, "E8M0"),
    "UE4M3+FP32/B16": (16, "UE4M3"),
    "UE5M3/B16": (16, "UE5M3"),
    "BF16/B32": (32, "BF16"),
}


def design(cells):
    scales = ["UE4M3", "UE5M3", "BF16"]
    names = ["mu", "INT4", "B32"] + scales + ["INT4:B32"] + [f"INT4:{s}" for s in scales]
    rows = []
    for g in ("E2M1", "INT4"):
        for c in cells:
            b, s = LEVELS[c]
            gi, bi = float(g == "INT4"), float(b == 32)
            sd = [float(s == x) for x in scales]
            rows.append([1, gi, bi] + sd + [gi * bi] + [gi * v for v in sd])
    X = np.array(rows)
    used = [j for j in range(len(names)) if X[:, j].any()]
    return X[:, used], [names[j] for j in used]


def estimable(X, names):
    P = np.linalg.pinv(X) @ X
    return {
        n: bool(np.allclose(P[:, j], np.eye(len(names))[:, j], atol=1e-8))
        for j, n in enumerate(names)
    }


def main() -> None:
    out = {"script": "doe.py", "cell_sets": {}}
    sets = {
        "dossier": ["E8M0/B32", "UE4M3+FP32/B16", "UE5M3/B16", "BF16/B32"],
        "registered": ["E8M0/B32", "E8M0/B16", "UE4M3+FP32/B16", "BF16/B32"],
        "extended": ["E8M0/B32", "E8M0/B16", "UE4M3+FP32/B16", "UE5M3/B16", "BF16/B32"],
    }
    for label, cells in sets.items():
        X, names = design(cells)
        est = estimable(X, names)
        out["cell_sets"][label] = {
            "cells": 2 * len(cells),
            "rank": int(np.linalg.matrix_rank(X)),
            "parameters": len(names),
            "estimable": [n for n in names if est[n]],
            "not_estimable": [n for n in names if not est[n]],
        }
        print(label, out["cell_sets"][label])

    # registered contrasts over the 8 cell means, order: E2M1 S1 S2 S3 S5, INT4 S1 S2 S3 S5
    idx = {
        f"{g}/{s}": i
        for i, (g, s) in enumerate(
            (g, s) for g in ("E2M1", "INT4") for s in ("S1", "S2", "S3", "S5")
        )
    }

    def vec(terms):
        v = np.zeros(8)
        for k, w in terms.items():
            v[idx[k]] += w
        return v

    def avg_grid(sa, sb):  # contrast (sa - sb) averaged over grids
        return vec({f"E2M1/{sa}": 0.5, f"INT4/{sa}": 0.5, f"E2M1/{sb}": -0.5, f"INT4/{sb}": -0.5})

    def inter(sa, sb):  # (INT4: sa - sb) - (E2M1: sa - sb)
        return vec({f"INT4/{sa}": 1, f"INT4/{sb}": -1, f"E2M1/{sa}": -1, f"E2M1/{sb}": 1})

    contrasts = {
        "Delta_G (INT4 - E2M1, mean over S)": vec(
            {
                **{f"INT4/{s}": 0.25 for s in ("S1", "S2", "S3", "S5")},
                **{f"E2M1/{s}": -0.25 for s in ("S1", "S2", "S3", "S5")},
            }
        ),
        "C_blk (S1 - S2: E8M0 B32 - B16)": avg_grid("S1", "S2"),
        "C_fmt (S2 - S3: E8M0 - UE4M3+PTS at B16)": avg_grid("S2", "S3"),
        "C_iso (S5 - S3: BF16/B32 - UE4M3+PTS/B16, 4.5 b)": avg_grid("S5", "S3"),
        "C_anchor (S1 - S3, E2M1 only: MX-like - NV-like)": vec({"E2M1/S1": 1, "E2M1/S3": -1}),
        "I_blk": inter("S1", "S2"),
        "I_fmt": inter("S2", "S3"),
        "I_iso": inter("S5", "S3"),
    }
    contrasts["D1 = C_fmt - 2 Delta_G"] = (
        contrasts["C_fmt (S2 - S3: E8M0 - UE4M3+PTS at B16)"]
        - 2 * contrasts["Delta_G (INT4 - E2M1, mean over S)"]
    )
    out["contrasts"] = {}
    for n_seeds in (3, 5):
        for k, c in contrasts.items():
            out["contrasts"].setdefault(
                k, {"coefficients": {kk: float(c[i]) for kk, i in idx.items() if c[i] != 0}}
            )
            out["contrasts"][k][f"SE_over_sigma_n{n_seeds}"] = round(
                float(np.sqrt((c**2).sum() / n_seeds)), 4
            )
            # 80% power, two-sided alpha 0.10 (z): MDE = (1.645 + 0.842) * SE
            out["contrasts"][k][f"MDE80_over_sigma_n{n_seeds}"] = round(
                float(2.487 * np.sqrt((c**2).sum() / n_seeds)), 3
            )
    for k, v in out["contrasts"].items():
        print(
            f"{k:52s} SE/sigma n3 {v['SE_over_sigma_n3']:.3f}  MDE80/sigma n3 {v['MDE80_over_sigma_n3']:.2f}  n5 {v['MDE80_over_sigma_n5']:.2f}"
        )
    # covariance between C_fmt and Delta_G (they share cells)
    cf, dg = (
        contrasts["C_fmt (S2 - S3: E8M0 - UE4M3+PTS at B16)"],
        contrasts["Delta_G (INT4 - E2M1, mean over S)"],
    )
    out["cov_Cfmt_DeltaG_over_sigma2_n3"] = round(float((cf * dg).sum() / 3), 5)
    with open(sys.argv[1], "w") as fh:
        json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()
