#!/usr/bin/env python3
"""S1v2: operating characteristics of the v2 registered decision path, end to end (Monte Carlo).

Implements registration c5-fp4-instability-v2 exactly as written (the "registered estimator"):

Phase 0, J4 (sigma-and-anchor probe; Part A): MX-like (E2M1/S1) and NV-like (E2M1/S3) at one fixed
  learning rate (4e-3, the centre of the BF16 sweep), the Phase 1 token budget, probe seeds 2001-2003
  (never used in Phase 1). RCBD on 2 configurations x 3 seed blocks (residual df 2):
    C0 = mean over seeds of L(MX) - L(NV);  sigma0 = SD of the paired differences / sqrt(2);
    SE0 = sigma0 * sqrt(2/3).
  G1 PASS iff L90(C0) > 0, i.e. C0 / SE0 > t(0.95, 2) (equivalently C0 >= 2.384 sigma0).
  Seed count n for Phase 1 = smallest n in {3, 4, 5, 6} whose 80%-power MDE for an interaction contrast
  (sum c^2 = 4, one-sided 2.5% as P2 is decided, df 9(n-1)) is at most C0: n = 3 if C0 >= 3.422 sigma0,
  4 if >= 2.907, 5 if >= 2.576, 6 if >= 2.338, else STOP_UNDERPOWERED (unreachable once G1 passes,
  since G1 needs C0 >= 2.384 sigma0; kept as a guard).
  GO = G1 PASS; otherwise STOP_UNRESOLVED_AT_35M.
Phase 1 (Part B), only after GO, on fresh seeds 42.. (independent of the probe; no gate run is reused):
  BF16 5-point LR sweep (sweep seed 1000, one extension, quadratic refinement); every FP4 cell (10) a
  3-point sweep centred on the BF16 tuned LR (up to two extensions, the same protocol for both grids);
  n fresh seeds at the tuned LR; RCBD on 10 cells x n seed blocks (residual df 9(n-1)).
  P2 (registered identified test): I_prec32 = (INT4: S1 - S5) - (E2M1: S1 - S5), SE = sigma * 2/sqrt(n).
    Decided on the 95% interval (one-sided 2.5%), not the 90% one, because per-cell LR tuning adds
    cell-level variance the seed residual cannot see (this file shows 90% intervals cover about 0.86
    in the flattest LR regime). CONFIRMED  L95 > 0;  REFUTED  U95 < 0;
    ABSENT     -C0 < L95 and U95 < C0 (95% interval inside +- the probe's anchor), not CONFIRMED/REFUTED;
    UNRESOLVED otherwise. The 90%-interval version is reported beside it (P2_at_90).
  RANGE flag (training part of the range rule): the 95% interval of I_range32 = (INT4: S4 - S5) -
    (E2M1: S4 - S5) excludes 0.
  Secondary verdict (the prior generalised), precedence:
    WITHIN_NOISE (omnibus F over 10 cell means, 9 df, p > 0.10); GRID_OR_INTERACTION
    (INTERACTION_PRESENT: 4-df grid x configuration F p < 0.05 and max |I| over {I_prec32, I_fmt16,
    I_fmt32, I_blk_E8, I_blk_UE} >= 0.5 |C_fmt_bar|; or U90(D1) < 0); PRIOR_SURVIVES (L90(D1) > 0,
    every registered |I| + t SE_I < C_fmt_bar, not INTERACTION_PRESENT);
    SCALE_DOMINATES_INTERACTION_UNRESOLVED (L90(D1) > 0 otherwise); INDETERMINATE.
    D1 = C_fmt_bar - 2 Delta_G; C_fmt_bar = mean over grids and over (S2 - S3, S1 - S4).

Truths are structural (per grid g): S1 = G + P + Bk, S2 = G + P, S3 = G + R, S4 = G + R + Bk,
S5 = G + Bk, so I_prec32 = dP, I_fmt16 = I_fmt32 = dP - dR, I_blk_E8 = I_blk_UE = dBk,
I_range32 = dR, anchor = P_E2M1 + Bk_E2M1 - R_E2M1. Scenarios:
  null, prior_additive (scale dominates, small additive grid effect), pow2 (the credited mechanism:
  power-of-two scales penalise INT4, plus a crest-factor block interaction under both scale types),
  crest_only (block interaction only; the alternative wave 1's I_blk could not exclude), range_only
  (UE4M3 range penalises INT4; the alternative wave 1's I_fmt could not exclude), pow2_plus_range,
  grid_additive, reversed (power-of-two scales penalise E2M1 more).
Learning-rate model: loss + a * (x - x_opt)^2 in log2(LR) units; BF16 optimum x_bf ~ N(0, 0.5^2)
around the sweep centre; FP4 family offset u ~ N(0, 0.5^2); per-cell spread v_c ~ N(0, 0.25^2)
(0 in the "null_no_lr_spread" row); x_opt,c = x_bf + u + v_c. The probe runs at x = 0, so its
anchor carries a(x_opt,MX^2 - x_opt,NV^2), a real difference at a common LR.
Also reported: the v1 gate-reuse estimator replayed on the same Phase 1 data (G1 computed on Phase 1's
own E2M1/S1, E2M1/S3 and BF16 fresh runs, v1's rule), to show that the bias is the estimator's.

Every distribution and effect size is an ASSUMPTION; sigma anchors: 0.00195 (arXiv 2505.19115
Table 4 recomputed, 125M, 30B tokens) and the HiF4 statement that 1B margins sit inside seed noise.

Usage: python power_sim_v2.py <out.json>     (R = 4000 per setting; seeds [42, 43, 44, j])
"""

from __future__ import annotations

import itertools
import json
import sys

import numpy as np
from scipy import stats

CFGS = ["S1", "S2", "S3", "S4", "S5"]
CELLS = [f"{g}/{s}" for g in ("E2M1", "INT4") for s in CFGS]
KX = {c: i for i, c in enumerate(CELLS)}
BASE_E = dict(PE=0.008, BkE=0.004, RE=0.001)
SCEN = {
    "null": dict(),
    "null_no_lr_spread": dict(),
    "prior_additive": dict(PE=0.016, BkE=0.008, RE=0.004, dG=0.003),
    "pow2": dict(**BASE_E, dP=0.012, dBk=0.004, dR=0.002, dG=-0.003),
    "crest_only": dict(**BASE_E, dBk=0.010),
    "range_only": dict(**BASE_E, dR=0.010),
    "pow2_plus_range": dict(**BASE_E, dP=0.012, dBk=0.004, dR=0.010, dG=-0.003),
    "grid_additive": dict(**BASE_E, dG=0.010),
    "reversed": dict(**BASE_E, dP=-0.008),
}
T_PROBE = stats.t.ppf(0.95, 2)
N_THR = {n: (stats.t.ppf(0.975, 9 * (n - 1)) + stats.t.ppf(0.80, 9 * (n - 1))) * np.sqrt(4 / n) for n in (3, 4, 5, 6)}
NS = (3, 4, 5, 6)


def means(name: str, m: float):
    p = {k: 0.0 for k in ("PE", "BkE", "RE", "dP", "dBk", "dR", "dG")}
    p.update(SCEN[name])
    p = {k: m * v for k, v in p.items()}
    E = {"S1": p["PE"] + p["BkE"], "S2": p["PE"], "S3": p["RE"], "S4": p["RE"] + p["BkE"], "S5": p["BkE"]}
    I = {
        "S1": p["PE"] + p["dP"] + p["BkE"] + p["dBk"] + p["dG"],
        "S2": p["PE"] + p["dP"] + p["dG"],
        "S3": p["RE"] + p["dR"] + p["dG"],
        "S4": p["RE"] + p["dR"] + p["BkE"] + p["dBk"] + p["dG"],
        "S5": p["BkE"] + p["dBk"] + p["dG"],
    }
    mu = {**{f"E2M1/{s}": E[s] for s in CFGS}, **{f"INT4/{s}": I[s] for s in CFGS}}
    ref = mu["E2M1/S3"]
    mu = {k: v - ref for k, v in mu.items()}
    truth = {"I_prec32": p["dP"], "I_fmt": p["dP"] - p["dR"], "I_blk": p["dBk"], "I_range32": p["dR"],
             "anchor": p["PE"] + p["BkE"] - p["RE"], "Delta_G": float(np.mean([mu[f"INT4/{s}"] - mu[f"E2M1/{s}"] for s in CFGS]))}
    return mu, truth


def tune(rng, R, x_opt, center, npts, a, sig_sweep, max_ext):
    """Vectorised LR sweep (as wave 1's power_sim.tune): returns the chosen log2 LR."""
    half = (npts - 1) // 2
    offs = np.arange(-half, half + 1, dtype=float)
    grid = center[:, None] + offs[None, :]
    loss = a * (grid - x_opt[:, None]) ** 2 + rng.normal(0, sig_sweep, grid.shape)
    for _ in range(max_ext):
        b = loss.argmin(axis=1)
        lo_edge, hi_edge = b == 0, b == grid.shape[1] - 1
        new_lo, new_hi = grid[:, 0] - 1, grid[:, -1] + 1
        nl = a * (new_lo - x_opt) ** 2 + rng.normal(0, sig_sweep, R)
        nh = a * (new_hi - x_opt) ** 2 + rng.normal(0, sig_sweep, R)
        grid = np.column_stack([np.where(lo_edge, new_lo, np.nan), grid, np.where(hi_edge, new_hi, np.nan)])
        loss = np.column_stack([np.where(lo_edge, nl, np.inf), loss, np.where(hi_edge, nh, np.inf)])
    b = np.nanargmin(np.where(np.isnan(grid), np.inf, loss), axis=1)
    rows = np.arange(R)
    xb = grid[rows, b]
    bl = np.clip(b - 1, 0, grid.shape[1] - 1)
    bh = np.clip(b + 1, 0, grid.shape[1] - 1)
    yl, y0, yh = loss[rows, bl], loss[rows, b], loss[rows, bh]
    ok = (bl != b) & (bh != b) & np.isfinite(yl) & np.isfinite(yh)
    denom = yl - 2 * y0 + yh
    shift = np.where(ok & (denom > 0), 0.5 * (yl - yh) / np.where(denom == 0, 1, denom), 0.0)
    n_ext = np.isfinite(loss).sum(axis=1) - npts
    return xb + np.clip(shift, -0.5, 0.5), n_ext


def rcbd(y):
    R, C, S = y.shape
    gm = y.mean(axis=(1, 2), keepdims=True)
    cm = y.mean(axis=2, keepdims=True)
    sm = y.mean(axis=1, keepdims=True)
    resid = y - cm - sm + gm
    df = (C - 1) * (S - 1)
    ss_res = (resid**2).sum(axis=(1, 2))
    sigma = np.sqrt(ss_res / df)
    ss_c = S * ((cm - gm) ** 2).sum(axis=(1, 2))
    p = stats.f.sf((ss_c / (C - 1)) / (ss_res / df), C - 1, df)
    return cm[..., 0], sigma, df, p


def vec(terms):
    v = np.zeros(len(CELLS))
    for k, w in terms.items():
        v[KX[k]] += w
    return v


def inter(a, b):
    return vec({f"INT4/{a}": 1, f"INT4/{b}": -1, f"E2M1/{a}": -1, f"E2M1/{b}": 1})


CV = {
    "I_prec32": inter("S1", "S5"),
    "I_fmt16": inter("S2", "S3"),
    "I_fmt32": inter("S1", "S4"),
    "I_blk_E8": inter("S1", "S2"),
    "I_blk_UE": inter("S4", "S3"),
    "I_range32": inter("S4", "S5"),
    "Delta_G": vec({**{f"INT4/{s}": 0.2 for s in CFGS}, **{f"E2M1/{s}": -0.2 for s in CFGS}}),
    "C_fmt_bar": 0.25 * vec({"E2M1/S2": 1, "INT4/S2": 1, "E2M1/S3": -1, "INT4/S3": -1, "E2M1/S1": 1, "INT4/S1": 1, "E2M1/S4": -1, "INT4/S4": -1}),
    "anchor": vec({"E2M1/S1": 1, "E2M1/S3": -1}),
}
CV["I_fmt_bar"] = 0.5 * (CV["I_fmt16"] + CV["I_fmt32"])
CV["D1"] = CV["C_fmt_bar"] - 2 * CV["Delta_G"]
REG_I = ["I_prec32", "I_fmt16", "I_fmt32", "I_blk_E8", "I_blk_UE"]


def lr_draws(rng, R, spread):
    x_bf = rng.normal(0, 0.5, R)
    u = rng.normal(0, 0.5, R)
    x_opt = {c: x_bf + u + rng.normal(0, spread, R) for c in CELLS}
    return x_bf, x_opt


def probe(rng, R, mu, x_opt, sigma, rho, a):
    sb, se = sigma * np.sqrt(rho), sigma * np.sqrt(1 - rho)
    seeds = rng.normal(0, sb, (R, 3))
    y = {c: mu[c] + a * x_opt[c][:, None] ** 2 + seeds + rng.normal(0, se, (R, 3)) for c in ("E2M1/S1", "E2M1/S3")}
    d = y["E2M1/S1"] - y["E2M1/S3"]
    c0 = d.mean(axis=1)
    sd = d.std(axis=1, ddof=1)
    s0 = sd / np.sqrt(2)
    se0 = sd / np.sqrt(3)
    g1 = c0 - T_PROBE * se0 > 0
    ratio = np.where(s0 > 0, c0 / np.where(s0 > 0, s0, 1), np.inf)
    n = np.where(ratio >= N_THR[3], 3, np.where(ratio >= N_THR[4], 4, np.where(ratio >= N_THR[5], 5, np.where(ratio >= N_THR[6], 6, 0))))
    go = g1 & (n > 0)
    return {"go": go, "g1": g1, "n": np.where(go, n, 0), "c0": c0, "s0": s0}


def phase1(rng, R, mu, x_bf, x_opt, sigma, rho, a, n, c0, truth):
    sb, se = sigma * np.sqrt(rho), sigma * np.sqrt(1 - rho)
    c_bf, _ = tune(rng, R, x_bf, np.zeros(R), 5, a, sigma, 1)
    chosen, n_ext = {}, {}
    for c in CELLS:
        chosen[c], n_ext[c] = tune(rng, R, x_opt[c], c_bf, 3, a, sigma, 2)
    seed_eff = rng.normal(0, sb, (R, n))
    y = np.stack([mu[c] + (a * (chosen[c] - x_opt[c]) ** 2)[:, None] + seed_eff + rng.normal(0, se, (R, n)) for c in CELLS], axis=1)
    y_bf = (a * (c_bf - x_bf) ** 2)[:, None] - 0.05 + seed_eff + rng.normal(0, se, (R, n))
    cm, s_hat, df, p_omni = rcbd(y)
    t95 = stats.t.ppf(0.95, df)
    t975 = stats.t.ppf(0.975, df)
    est = {k: cm @ v for k, v in CV.items()}
    se_ = {k: s_hat * np.sqrt((v**2).sum() / n) for k, v in CV.items()}
    lo = {k: est[k] - t95 * se_[k] for k in CV}
    hi = {k: est[k] + t95 * se_[k] for k in CV}
    lo2 = est["I_prec32"] - t975 * se_["I_prec32"]
    hi2 = est["I_prec32"] + t975 * se_["I_prec32"]
    conf = lo2 > 0
    ref = hi2 < 0
    absent = ~conf & ~ref & (lo2 > -c0) & (hi2 < c0)
    unres = ~conf & ~ref & ~absent
    conf90, ref90 = lo["I_prec32"] > 0, hi["I_prec32"] < 0
    # secondary verdict
    mg = np.stack([cm[:, [KX[f"{g}/{s}"] for s in CFGS]] for g in ("E2M1", "INT4")], axis=1)
    ss_int = n * ((mg - mg.mean(axis=2, keepdims=True) - mg.mean(axis=1, keepdims=True) + mg.mean(axis=(1, 2), keepdims=True)) ** 2).sum(axis=(1, 2))
    p_int = stats.f.sf((ss_int / 4) / s_hat**2, 4, df)
    max_i = np.max(np.abs(np.stack([est[k] for k in REG_I])), axis=0)
    ip = (p_int < 0.05) & (max_i >= 0.5 * np.abs(est["C_fmt_bar"]))
    noise = p_omni > 0.10
    small = est["C_fmt_bar"] > 0
    for k in REG_I:
        small &= (np.abs(est[k]) + t95 * se_[k]) < est["C_fmt_bar"]
    grid_v = ~noise & (ip | (hi["D1"] < 0))
    prior_v = ~noise & ~grid_v & (lo["D1"] > 0) & small
    sdiu = ~noise & ~grid_v & ~prior_v & (lo["D1"] > 0)
    indet = ~noise & ~grid_v & ~prior_v & ~sdiu
    lo_r = est["I_range32"] - t975 * se_["I_range32"]
    hi_r = est["I_range32"] + t975 * se_["I_range32"]
    range_flag = (lo_r > 0) | (hi_r < 0)
    # v1-style gate on the same Phase 1 data (reuse): RCBD of E2M1/S1, E2M1/S3, BF16 fresh runs (n = 3 only)
    ya = np.stack([y[:, KX["E2M1/S1"]], y[:, KX["E2M1/S3"]], y_bf], axis=1)
    cma, sa, dfa, _ = rcbd(ya)
    ca = cma[:, 0] - cma[:, 1]
    g1_v1 = (ca - stats.t.ppf(0.95, dfa) * sa * np.sqrt(2 / n) > 0) & (ca >= 2.5 * sa)
    tb = np.concatenate([a * (chosen[c] - x_opt[c]) ** 2 for c in CELLS])
    return {
        "P2": {"CONFIRMED": conf, "REFUTED": ref, "ABSENT": absent, "UNRESOLVED": unres},
        "P2_at_90": {"CONFIRMED": conf90, "REFUTED": ref90},
        "cover95_I_prec32": (lo2 <= truth["I_prec32"]) & (truth["I_prec32"] <= hi2),
        "verdict": {"WITHIN_NOISE": noise, "GRID_OR_INTERACTION": grid_v, "PRIOR_SURVIVES": prior_v,
                    "SCALE_DOMINATES_INTERACTION_UNRESOLVED": sdiu, "INDETERMINATE": indet},
        "RANGE_FLAG": range_flag,
        "cover_I_prec32": (lo["I_prec32"] <= truth["I_prec32"]) & (truth["I_prec32"] <= hi["I_prec32"]),
        "cover_anchor": (lo["anchor"] <= truth["anchor"]) & (truth["anchor"] <= hi["anchor"]),
        "err_I_prec32": est["I_prec32"] - truth["I_prec32"],
        "err_anchor": est["anchor"] - truth["anchor"],
        "g1_v1_reuse": g1_v1,
        "fp4_extensions": np.stack([n_ext[c] for c in CELLS], axis=1).sum(axis=1),
        "tuning_bias_mean": float(tb.mean()),
        "tuning_bias_p95": float(np.quantile(tb, 0.95)),
    }


def frac(x, mask=None):
    if mask is None:
        return round(float(np.mean(x)), 4)
    return round(float(np.mean(x[mask])), 4) if mask.any() else None


def run(scn, m, sigma, rho, a, R, seed_j):
    rng = np.random.default_rng([42, 43, 44, seed_j])
    mu, truth = means(scn, m)
    spread = 0.0 if scn == "null_no_lr_spread" else 0.25
    x_bf, x_opt = lr_draws(rng, R, spread)
    pr = probe(rng, R, mu, x_opt, sigma, rho, a)
    ph = {n: phase1(rng, R, mu, x_bf, x_opt, sigma, rho, a, n, pr["c0"], truth) for n in NS}
    go = pr["go"]
    pick = lambda key, sub=None: np.select(  # noqa: E731  per-replicate Phase 1 at the probe's n
        [pr["n"] == n for n in NS],
        [ph[n][key][sub] if sub else ph[n][key] for n in NS], default=False)
    p2 = {k: pick("P2", k) for k in ("CONFIRMED", "REFUTED", "ABSENT", "UNRESOLVED")}
    vd = {k: pick("verdict", k) for k in ph[3]["verdict"]}
    rf = pick("RANGE_FLAG")
    cov_i = pick("cover_I_prec32")
    cov_i95 = pick("cover95_I_prec32")
    p290 = {k: pick("P2_at_90", k) for k in ("CONFIRMED", "REFUTED")}
    cov_a = pick("cover_anchor")
    err_i = np.select([pr["n"] == n for n in NS], [ph[n]["err_I_prec32"] for n in NS], default=np.nan)
    ext = np.select([pr["n"] == n for n in NS], [ph[n]["fp4_extensions"] for n in NS], default=0)
    p3 = ph[3]
    v1 = p3["g1_v1_reuse"]
    out = {
        "truth": {k: round(v, 5) for k, v in truth.items()},
        "probe": {"P_GO": frac(go), "P_n3": frac(pr["n"] == 3), "P_n4": frac(pr["n"] == 4), "P_n5": frac(pr["n"] == 5), "P_n6": frac(pr["n"] == 6),
                  "mean_n_given_GO": round(float(pr["n"][go].mean()), 3) if go.any() else None,
                  "P_STOP_UNRESOLVED": frac(~pr["g1"]), "P_STOP_UNDERPOWERED": frac(pr["g1"] & ~go),
                  "sigma0_median_over_sigma": round(float(np.median(pr["s0"]) / sigma), 3)},
        "phase1_given_GO": {
            "P2": {k: frac(v, go) for k, v in p2.items()},
            "P2_at_90": {k: frac(v, go) for k, v in p290.items()},
            "coverage95_I_prec32": frac(cov_i95, go),
            "verdict": {k: frac(v, go) for k, v in vd.items()},
            "RANGE_FLAG": frac(rf, go),
            "coverage90_I_prec32": frac(cov_i, go),
            "coverage90_anchor": frac(cov_a, go),
            "mean_error_I_prec32": round(float(np.nanmean(err_i[go])), 5) if go.any() else None,
            "mean_fp4_extension_runs": round(float(ext[go].mean()), 2) if go.any() else None,
            "max_fp4_extension_runs": int(ext[go].max()) if go.any() else None,
        },
        "end_to_end": {f"P_GO_and_P2_{k}": frac(go & v) for k, v in p2.items()},
        "phase1_n3_unconditional": {"P2": {k: frac(v) for k, v in p3["P2"].items()},
                                    "P2_at_90": {k: frac(v) for k, v in p3["P2_at_90"].items()},
                                    "coverage95_I_prec32": frac(p3["cover95_I_prec32"]),
                                    "verdict": {k: frac(v) for k, v in p3["verdict"].items()},
                                    "RANGE_FLAG": frac(p3["RANGE_FLAG"]),
                                    "coverage90_I_prec32": frac(p3["cover_I_prec32"]),
                                    "tuning_bias_mean": round(p3["tuning_bias_mean"], 5),
                                    "tuning_bias_p95": round(p3["tuning_bias_p95"], 5)},
        "gate_reuse_check_n3": {
            "note": "Both rows use Phase 1 at n = 3 and P2 read on the 90% interval (wave 1's rule), so they compare like with like.",
            "v2_independent_probe": {"P2_REFUTED": frac(p3["P2_at_90"]["REFUTED"], go), "P2_CONFIRMED": frac(p3["P2_at_90"]["CONFIRMED"], go),
                                     "coverage90_I_prec32": frac(p3["cover_I_prec32"], go), "coverage90_anchor": frac(p3["cover_anchor"], go),
                                     "mean_error_anchor": round(float(p3["err_anchor"][go].mean()), 5) if go.any() else None},
            "v1_reuse_gate_on_phase1_runs": {"P_gate": frac(v1), "P2_REFUTED": frac(p3["P2_at_90"]["REFUTED"], v1),
                                             "P2_CONFIRMED": frac(p3["P2_at_90"]["CONFIRMED"], v1),
                                             "coverage90_I_prec32": frac(p3["cover_I_prec32"], v1),
                                             "coverage90_anchor": frac(p3["cover_anchor"], v1),
                                             "mean_error_anchor": round(float(p3["err_anchor"][v1].mean()), 5) if v1.any() else None},
        },
    }
    return out


def spearman_crit(n_cells: int = 10):
    """Exact one-sided null distribution of Spearman's rho for n_cells (all permutations, chunked)."""
    base = np.arange(n_cells)
    counts = {}
    it = itertools.permutations(range(n_cells))
    while True:
        chunk = list(itertools.islice(it, 200000))
        if not chunk:
            break
        d2 = ((np.array(chunk, dtype=np.int16) - base) ** 2).sum(axis=1)
        u, c = np.unique(d2, return_counts=True)
        for a, b in zip(u.tolist(), c.tolist()):
            counts[a] = counts.get(a, 0) + b
    tot = sum(counts.values())
    rho = {d: 1 - 6 * d / (n_cells * (n_cells**2 - 1)) for d in counts}
    res = {}
    for alpha in (0.05, 0.025):
        for d in sorted(counts):  # ascending d2 = descending rho
            tail = sum(cnt for dd, cnt in counts.items() if dd <= d) / tot
            if tail > alpha:
                break
            res[f"one_sided_{alpha}"] = {"rho_critical": round(rho[d], 4), "exact_p": round(tail, 5)}
    return {"n_cells": n_cells, "n_permutations": tot, **res}


def main() -> None:
    R = 4000
    out = {"script": "power_sim_v2.py", "replicates_per_setting": R, "seeds": "[42, 43, 44, j] per setting j",
           "assumptions": __doc__, "n_rule_thresholds": {str(k): round(float(v), 3) for k, v in N_THR.items()},
           "probe_t_crit_df2": round(float(T_PROBE), 4), "grid": []}
    j = 0
    for scn in SCEN:
        for m in ((1.0,) if scn.startswith("null") else (0.5, 1.0, 2.0)):
            for sigma in (0.002, 0.004, 0.008):
                for rho in (0.0, 0.5):
                    for a in (0.005, 0.02):
                        res = run(scn, m, sigma, rho, a, R, j)
                        out["grid"].append({"scenario": scn, "effect_multiplier": m, "sigma": sigma, "rho_seed": rho, "lr_curvature_a": a, **res})
                        if rho == 0.5 and a == 0.02 and sigma == 0.004:
                            pg, p2 = res["probe"], res["phase1_given_GO"]["P2"]
                            print(f"{scn:18s} m={m} s={sigma} GO {pg['P_GO']:.2f} n3/4/5/6 {pg['P_n3']:.2f}/{pg['P_n4']:.2f}/{pg['P_n5']:.2f}/{pg['P_n6']:.2f} | "
                                  f"P2|GO C {p2['CONFIRMED']} R {p2['REFUTED']} A {p2['ABSENT']} U {p2['UNRESOLVED']} | "
                                  f"cov {res['phase1_given_GO']['coverage90_I_prec32']} | reuse REF v2 {res['gate_reuse_check_n3']['v2_independent_probe']['P2_REFUTED']} "
                                  f"v1 {res['gate_reuse_check_n3']['v1_reuse_gate_on_phase1_runs']['P2_REFUTED']}", flush=True)
                        j += 1
    V, Kd = 4096, 2**16
    out["sr_unbiasedness_test"] = {"values_per_grid": V, "draws_per_value": Kd, "aggregate_SE_max_ulp": 0.5 / np.sqrt(V * Kd),
                                   "detectable_bias_ulp_at_power_0.999": round(float((stats.norm.ppf(0.9995) + stats.norm.ppf(0.999)) * 0.5 / np.sqrt(V * Kd)), 6)}
    out["spearman_exact"] = spearman_crit(10)
    print("spearman n=10:", out["spearman_exact"], flush=True)
    with open(sys.argv[1], "w") as fh:
        json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()
