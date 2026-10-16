#!/usr/bin/env python3
"""LM1 pilot: operating characteristics of the registered decision rule, simulated before any data.

Model (superpopulation; new items every replicate):
  - two primary benchmarks b (AA-Omniscience-Public, n=600; SimpleQA-Verified, n=1000), weight 0.5 each;
  - item difficulty d_i ~ N(0, sigma_item); arm-item interaction u_ai ~ N(0, sigma_u);
  - per-sample correctness probability p_ai = logistic(sharp * (theta_ab - d_i + u_ai));
  - theta_ab is calibrated so that E[p_ai] equals the arm's target accuracy on benchmark b;
  - K = 3 seeded samples per (item, arm): count ~ Binomial(3, p_ai).
Arms: Kimi plus four resident arms. The best resident (R1) has the base accuracy; R2, R3, R4 sit
3, 6 and 15 points lower (gpt-oss-like). Kimi = R1 + delta_min (points), on both benchmarks.

Registered decision rule (registration section 7.3), applied with the analytic paired SE:
  delta_j = sum_b 0.5 * mean_i(y_Ki - y_ji);  SE_j^2 = sum_b 0.25 * var_i(y_Ki - y_ji) / n_b
  NOT_WORTH  if any j: delta_j + 2.4977 * SE_j < +5 points (Bonferroni over 4, one-sided 0.625%)
  LEADS      if all j: delta_j - 1.96 * SE_j > 0 (IUT) and min_j delta_j >= +5 points, and no SPLIT
  SPLIT      if one benchmark alone reads NOT_WORTH and the other alone reads LEADS (counted UNRESOLVED)
  UNRESOLVED otherwise
The analysis itself uses a stratified paired item bootstrap; the simulation uses the normal
approximation and reports its coverage so the substitution can be judged.

Usage: python sim_lm1.py --out sim-lm1.json [--reps 1000] [--seeds 42 43 44]
"""

from __future__ import annotations

import argparse
import json
import math
import time

import numpy as np

Z_UPPER = 2.4977  # Phi^-1(1 - 0.025/4): Bonferroni over 4 resident arms, one-sided
Z_LOWER = 1.959964
MARGIN = 0.05
N_BENCH = {"aao": 600, "sqv": 1000}
BASE_ACC = {"aao": 0.30, "sqv": 0.40}
RESIDENT_OFFSETS = [0.0, -0.03, -0.06, -0.15]
SETTINGS = {
    # name: (sigma_item, sigma_u, sharp); discordance and noise share are reported per run
    "base": (2.5, 1.5, 2.0),
    "noisy": (2.0, 1.0, 1.0),
}
DELTAS = [-0.15, -0.10, -0.05, -0.02, 0.0, 0.02, 0.05, 0.08, 0.12]
FRACTIONS = [1.0, 0.625]  # all 1,600 primary items, or the 1,000-item minimum of KC4


def logistic(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def calibrate_theta(target: float, sigma_item: float, sigma_u: float, sharp: float) -> float:
    """theta such that E[logistic(sharp*(theta - d + u))] = target (fixed quadrature sample)."""
    g = np.random.default_rng(12345)  # calibration sample only; not an experimental seed
    z = g.normal(0.0, math.sqrt(sigma_item**2 + sigma_u**2), 200_000)
    lo, hi = -15.0, 15.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if logistic(sharp * (mid - z)).mean() < target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def run_setting(rng: np.random.Generator, setting: str, delta: float, frac: float, reps: int) -> dict:
    """Vectorized over replicates: arrays of shape (reps, arms, items)."""
    sigma_item, sigma_u, sharp = SETTINGS[setting]
    n_b = {b: int(round(n * frac)) for b, n in N_BENCH.items()}
    diffs = {}
    disc = psi = None
    for b, n in n_b.items():
        targets = [min(max(BASE_ACC[b] + o, 0.02), 0.98) for o in RESIDENT_OFFSETS]
        kimi_t = min(max(BASE_ACC[b] + delta, 0.02), 0.98)
        thetas = np.array([calibrate_theta_cached(t, sigma_item, sigma_u, sharp) for t in [kimi_t, *targets]])
        d = rng.normal(0.0, sigma_item, (reps, 1, n))
        u = rng.normal(0.0, sigma_u, (reps, 5, n))
        p = logistic(sharp * (thetas[None, :, None] - d + u))
        y = rng.binomial(3, p) / 3.0
        diffs[b] = y[:, :1, :] - y[:, 1:, :]  # (reps, 4, n)
        if b == "sqv":
            pk, pr = p[:, 0, :], p[:, 1, :]
            disc = float(np.mean(pk * (1 - pr) + pr * (1 - pk)))
            vpk = np.mean(pk * (1 - pk))
            psi = float(vpk / (vpk + np.var(pk)))
    est = sum(0.5 * diffs[b].mean(axis=2) for b in n_b)  # (reps, 4)
    se = np.sqrt(sum(0.25 * diffs[b].var(axis=2, ddof=1) / n_b[b] for b in n_b))
    not_worth = np.any(est + Z_UPPER * se < MARGIN, axis=1)
    leads = np.all(est - Z_LOWER * se > 0, axis=1) & (est.min(axis=1) >= MARGIN)
    nw_b, ld_b = [], []
    for b, n in n_b.items():
        e_b = diffs[b].mean(axis=2)
        s_b = diffs[b].std(axis=2, ddof=1) / math.sqrt(n)
        nw = np.any(e_b + Z_UPPER * s_b < MARGIN, axis=1)
        ld = np.all(e_b - Z_LOWER * s_b > 0, axis=1) & (e_b.min(axis=1) >= MARGIN) & ~nw
        nw_b.append(nw)
        ld_b.append(ld)
    split = (nw_b[0] & ld_b[1]) | (nw_b[1] & ld_b[0])
    nw_final = not_worth & ~split
    ld_final = leads & ~split
    unres = ~(nw_final | ld_final)
    cover = (est[:, 0] - Z_LOWER * se[:, 0] <= delta) & (delta <= est[:, 0] + Z_LOWER * se[:, 0])
    return {
        "setting": setting, "delta_min_points": round(delta * 100, 1), "primary_items": sum(n_b.values()),
        "P_NOT_WORTH": float(nw_final.mean()), "P_LEADS": float(ld_final.mean()),
        "P_UNRESOLVED": float(unres.mean()), "P_SPLIT": float(split.mean()),
        "coverage_95_kimi_minus_R1": float(cover.mean()),
        "mean_se_points": round(100 * float(se[:, 0].mean()), 3),
        "mean_delta_hat_points": round(100 * float(est[:, 0].mean()), 3),
        "discordance_single_sample_sqv": round(disc, 3),
        "prediction_noise_share_sqv": round(psi, 3),
    }


_THETA_CACHE: dict = {}


def calibrate_theta_cached(t: float, si: float, su: float, sh: float) -> float:
    key = (round(t, 6), si, su, sh)
    if key not in _THETA_CACHE:
        _THETA_CACHE[key] = calibrate_theta(t, si, su, sh)
    return _THETA_CACHE[key]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--reps", type=int, default=1000)
    ap.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44])
    args = ap.parse_args()
    t0 = time.time()
    results = []
    for seed in args.seeds:
        rng = np.random.default_rng(seed)
        for setting in SETTINGS:
            for frac in FRACTIONS:
                for delta in DELTAS:
                    r = run_setting(rng, setting, delta, frac, args.reps)
                    r["seed"] = seed
                    results.append(r)
                    print(json.dumps(r), flush=True)
    # seed-averaged table
    summary = {}
    for r in results:
        key = f'{r["setting"]}|{r["primary_items"]}|{r["delta_min_points"]}'
        s = summary.setdefault(key, {k: [] for k in ("P_NOT_WORTH", "P_LEADS", "P_UNRESOLVED", "P_SPLIT",
                                                      "coverage_95_kimi_minus_R1", "mean_se_points")})
        for k in s:
            s[k].append(r[k])
    table = []
    for key, s in summary.items():
        setting, n, d = key.split("|")
        row = {"setting": setting, "primary_items": int(n), "delta_min_points": float(d)}
        for k, v in s.items():
            row[k] = round(float(np.mean(v)), 4)
            row[k + "_seed_range"] = [round(float(min(v)), 4), round(float(max(v)), 4)]
        table.append(row)
    out = {
        "script": "compute/sim_lm1.py",
        "model": __doc__.split("Usage")[0].strip(),
        "constants": {"Z_UPPER": Z_UPPER, "Z_LOWER": Z_LOWER, "margin_points": 100 * MARGIN,
                      "n_bench": N_BENCH, "base_acc": BASE_ACC, "resident_offsets_points": [100 * o for o in RESIDENT_OFFSETS],
                      "settings": {k: dict(zip(("sigma_item", "sigma_u", "sharp"), v)) for k, v in SETTINGS.items()},
                      "deltas_points": [100 * d for d in DELTAS], "fractions": FRACTIONS, "K_samples": 3},
        "seeds": args.seeds, "reps_per_cell_per_seed": args.reps,
        "per_seed": results, "seed_mean_table": table,
        "runtime_s": round(time.time() - t0, 1),
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
        fh.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
