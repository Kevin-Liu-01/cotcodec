#!/usr/bin/env python3
"""N1: exact numerics for the C5 Phase 0 design (CPU only, exact dyadic rationals).

Computes, with no floating-point shortcuts:
  1. the element grids (E2M1, symmetric INT4, E1M2) and their code counts;
  2. the block-scale codebooks (E8M0, UE4M3 = positive E4M3fn, two published
     UE5M3 readings, BF16) with their ranges;
  3. whether every decoded operand (element x block scale) is exactly
     representable in BF16, TF32 and FP32, per grid x scale format;
  4. how often folding an FP32 per-tensor scale into the operand is inexact
     even in FP32 (the reason the registration applies it in the GEMM epilogue);
  5. the metamorphic identity E1M2(bias 1) = INT4 / 4;
  6. storage in bits per element for every Phase 1 cell;
  7. the sample standard deviation of the five seed losses printed in Table 4
     of arXiv 2505.19115 (the only published FP4 seed-noise anchor);
  8. a tie-rounding check: true division versus multiply-by-reciprocal when
     scaling BF16 inputs by UE4M3 scales before E2M1 round-to-nearest-even.

Usage: python numerics.py <out.json>     (deterministic; seed 42 where sampling is used)
"""

from __future__ import annotations

import json
import sys
from fractions import Fraction as F

import numpy as np

# ---------------------------------------------------------------- formats

FMT = {  # precision p (significant bits incl. implicit), emin, emax (normal range), subnormals on
    "BF16": (8, -126, 127),
    "TF32": (11, -126, 127),
    "FP32": (24, -126, 127),
}


def sig_bits(v: F) -> int:
    v = abs(v)
    if v == 0:
        return 0
    n, d = v.numerator, v.denominator
    assert d & (d - 1) == 0, "non-dyadic"
    while n % 2 == 0:
        n //= 2
    return n.bit_length()


def floor_log2(v: F) -> int:
    v = abs(v)
    e = v.numerator.bit_length() - v.denominator.bit_length()
    if F(2) ** e > v:
        e -= 1
    if F(2) ** (e + 1) <= v:
        e += 1
    return e


def representable(v: F, fmt: str) -> bool:
    p, emin, emax = FMT[fmt]
    if v == 0:
        return True
    v = abs(v)
    e = floor_log2(v)
    if e > emax:
        return False
    if e < emin:  # subnormal: must be a multiple of 2^(emin-p+1)
        return (v / F(2) ** (emin - p + 1)).denominator == 1
    return sig_bits(v) <= p


def ufloat(
    ebits: int, mbits: int, bias: int, max_code: int | None = None, reserve_top_exp: bool = False
):
    vals = []
    for e in range(2**ebits):
        if reserve_top_exp and e == 2**ebits - 1:
            continue
        for m in range(2**mbits):
            code = (e << mbits) | m
            if max_code is not None and code > max_code:
                continue
            v = (
                F(m, 2**mbits) * F(2) ** (1 - bias)
                if e == 0
                else (1 + F(m, 2**mbits)) * F(2) ** (e - bias)
            )
            if v > 0:
                vals.append(v)
    return sorted(set(vals))


def bf16_positive(exp_lo: int | None = None, exp_hi: int | None = None):
    out = []
    for bits in range(1, 0x7F80):  # positive finite BF16 codes (normal and subnormal)
        e_field, m = bits >> 7, bits & 0x7F
        v = (
            F(m, 128) * F(2) ** (-126)
            if e_field == 0
            else (1 + F(m, 128)) * F(2) ** (e_field - 127)
        )
        if exp_lo is not None and not (exp_lo <= floor_log2(v) <= exp_hi):
            continue
        out.append(v)
    return out


GRIDS = {
    "E2M1": [F(0), F(1, 2), F(1), F(3, 2), F(2), F(3), F(4), F(6)],
    "INT4_sym": [F(i) for i in range(8)],  # {-7..7}; -8 unused
    "E1M2_bias1": [F(i, 4) for i in range(8)],  # with subnormals
}
SCALES = {
    "E8M0": [F(2) ** k for k in range(-127, 128)],  # code 0xFF is NaN
    "UE4M3": [v for v in ufloat(4, 3, 7) if v <= 448],  # E4M3fn positive, e=15 m=7 is NaN
    "UE5M3_topexp_reserved": ufloat(
        5, 3, 15, reserve_top_exp=True
    ),  # max 61,440 (2609.02846 Eq. 3)
    "UE5M3_maxcode_0xFE": ufloat(5, 3, 15, max_code=0xFE),  # max 114,688 (TE reference reading)
    "BF16_all": bf16_positive(),
    "BF16_core_exp_-60_60": bf16_positive(-60, 60),
}


def grid_values_signed(grid):
    return sorted({g for g in grid} | {-g for g in grid})


def main() -> None:
    out: dict = {
        "script": "numerics.py",
        "exact_arithmetic": "fractions.Fraction (dyadic rationals)",
    }

    # 1. grids and code counts
    out["grids"] = {
        name: {
            "magnitudes": [str(v) for v in g],
            "distinct_signed_values": len(grid_values_signed(g)),
            "q_max": str(max(g)),
        }
        for name, g in GRIDS.items()
    }
    out["grids"]["INT4_twos_complement_distinct_values"] = 16
    out["grids"]["E1M2_equals_INT4_over_4"] = all(
        a == b / 4 for a, b in zip(GRIDS["E1M2_bias1"], GRIDS["INT4_sym"], strict=True)
    )

    # 2. scale codebooks
    out["scale_codebooks"] = {
        name: {
            "n_positive_codes": len(s),
            "min": str(min(s)),
            "max": str(max(s)),
            "max_float": float(max(s)),
            "log2_range": floor_log2(max(s)) - floor_log2(min(s)),
        }
        for name, s in SCALES.items()
    }

    # 3. decoded-operand representability
    rep = {}
    for gname, grid in GRIDS.items():
        for sname, scales in SCALES.items():
            prods = [g * s for g in grid if g > 0 for s in scales]
            row = {
                "n_products": len(prods),
                "max_significant_bits": max(sig_bits(p) for p in prods),
            }
            for fmt in FMT:
                bad = sum(1 for p in prods if not representable(p, fmt))
                row[f"not_exact_in_{fmt}"] = bad
                row[f"frac_not_exact_in_{fmt}"] = round(bad / len(prods), 4)
            rep[f"{gname} x {sname}"] = row
    out["decoded_operand_representability"] = rep

    # 4. FP32 per-tensor scale folded into the operand (E2M1 x UE4M3 x s_t), s_t random FP32 in [2^-20, 2^20)
    rng = np.random.default_rng(42)
    st_bits = rng.integers(0, 2**23, size=2000)
    st_exp = rng.integers(-20, 20, size=2000)
    sts = [(1 + F(int(b), 2**23)) * F(2) ** int(e) for b, e in zip(st_bits, st_exp, strict=True)]
    ue4 = SCALES["UE4M3"]
    sample_s = [ue4[i] for i in rng.integers(0, len(ue4), size=40)]
    bad = tot = 0
    for g in GRIDS["E2M1"][1:]:
        for s in sample_s:
            for st in sts[:250]:
                tot += 1
                bad += not representable(g * s * st, "FP32")
    out["pts_folded_into_operand"] = {
        "cells": "E2M1 x UE4M3 x random FP32 tensor scale (2000 drawn, 250 used per pair, seed 42)",
        "n": tot,
        "not_exact_in_FP32": bad,
        "frac": round(bad / tot, 4),
        "rule": "apply the FP32 tensor scales in the GEMM epilogue (y = s_ta * s_tb * sum(q_a s_ba q_b s_bb)), as hardware does",
    }

    # 6. storage per Phase 1 cell
    cells = {
        "S1 E8M0/B32": (8, 32, 0),
        "S2 E8M0/B16": (8, 16, 0),
        "S3 UE4M3+FP32/B16": (8, 16, 32),
        "S4 UE5M3/B16 (deferred)": (8, 16, 0),
        "S5 BF16/B32": (16, 32, 0),
    }
    out["storage_bits_per_element"] = {
        k: {
            "block_scale_bits": sb,
            "block": b,
            "per_tensor_scale_bits": pt,
            "bits_per_element": 4 + sb / b,
            "note": "+32 bits per tensor (negligible)" if pt else "",
        }
        for k, (sb, b, pt) in cells.items()
    }
    out["storage_collinearity"] = (
        "bits/element = 4 + scale_bits / B, so at fixed storage scale width and block "
        "size move together: at 4.5 b, B16 pairs only with 8-bit scales and B32 only with 16-bit scales"
    )

    # 7. 2505.19115 Table 4
    losses = [3.03, 3.027, 3.025, 3.027, 3.029]
    out["fp4_all_the_way_table4"] = {
        "losses": losses,
        "seeds": [1337, 1234, 2345, 3456, 4567],
        "sample_sd": round(float(np.std(losses, ddof=1)), 5),
        "population_sd": round(float(np.std(losses)), 5),
        "stated_sd": 0.001,
        "note": "125M Llama, 30B tokens, FP4 recipe, training loss; the printed values give about 0.002",
    }

    # 8. tie handling: true division vs multiply-by-reciprocal (BF16 inputs x UE4M3 scales in [1/64, 64])
    e2m1 = np.array([0, 0.5, 1, 1.5, 2, 3, 4, 6], dtype=np.float64)

    def rne_e2m1(y):
        a = np.minimum(np.abs(y), 6.0)
        idx = np.clip(np.searchsorted(e2m1, a, side="right") - 1, 0, 6)
        lo, hi = e2m1[idx], e2m1[idx + 1]
        mid = (lo + hi) / 2
        r = np.where(a < mid, lo, np.where(a > mid, hi, np.where(idx % 2 == 0, lo, hi)))
        return np.sign(y) * r

    bits = np.arange(0, 1 << 16, dtype=np.uint32)
    bf = (bits << 16).view(np.float32)
    bf = bf[np.isfinite(bf) & (bf >= 2.0**-6) & (bf < 2.0**6)]
    s_list = np.array([float(v) for v in ue4 if F(1, 64) <= v <= 64], dtype=np.float32)
    tot = ties = flip_rec = flip_div = 0
    for s in s_list:
        xs = bf[(bf / s) <= 6.0]
        exact = xs.astype(np.float64) / np.float64(s)
        q_exact = rne_e2m1(exact)
        q_div = rne_e2m1((xs / np.float32(s)).astype(np.float32).astype(np.float64))
        q_rec = rne_e2m1(
            (xs * (np.float32(1.0) / np.float32(s))).astype(np.float32).astype(np.float64)
        )
        ties += int(np.isin(exact, [0.25, 0.75, 1.25, 1.75, 2.5, 3.5, 5.0]).sum())
        tot += xs.size
        flip_div += int((q_div != q_exact).sum())
        flip_rec += int((q_rec != q_exact).sum())
    out["tie_rounding_check"] = {
        "domain": "positive BF16 inputs in [2^-6, 2^6) x UE4M3 scales in [1/64, 64], in-range pairs",
        "n_pairs": tot,
        "exact_midpoint_ties": ties,
        "frac_ties": round(ties / tot, 5),
        "fl32_division_disagrees_with_exact": flip_div,
        "fl32_reciprocal_multiply_disagrees": flip_rec,
        "frac_reciprocal_disagrees": round(flip_rec / tot, 6),
    }
    with open(sys.argv[1], "w") as fh:
        json.dump(out, fh, indent=1)
    for k, v in rep.items():
        print(
            f"{k:38s} n={v['n_products']:7d} maxbits={v['max_significant_bits']:2d} "
            f"BF16 {v['frac_not_exact_in_BF16']:.4f} TF32 {v['frac_not_exact_in_TF32']:.4f} FP32 {v['frac_not_exact_in_FP32']:.4f}"
        )
    print(
        "PTS folded:",
        out["pts_folded_into_operand"]["frac"],
        "| table4 sd:",
        out["fp4_all_the_way_table4"]["sample_sd"],
        "| ties:",
        out["tie_rounding_check"],
    )


if __name__ == "__main__":
    main()
