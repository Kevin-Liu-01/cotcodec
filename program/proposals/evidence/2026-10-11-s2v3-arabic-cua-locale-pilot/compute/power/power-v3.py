#!/usr/bin/env python3
"""S2 v3: operating characteristics of the registered Phase 1 decision rules on the enlarged pool.

CPU only, deterministic given the seeds [42, 43, 44] (numpy PCG64 streams [seed, stream id]).

Inputs: S1a's per-episode records (a1.jsonl) and the frozen pool (pool-v3.json, 106 tasks:
62 with S1a Qwen3.5-9B records, 44 without).

Propensity model. Two beta-binomial fits on S1a's 9B episodes of the 62 pool tasks with records
(zeros included), by maximum marginal likelihood: a cell-level fit over the 124 (task, harness)
cells with 4 trials each, whose posterior gives each observed cell's success probability (as in
S2 v2's power-osworld.py), and a task-level fit over the 62 tasks with 8 trials each, from which
the 44 tasks without records draw one probability shared by both harnesses (no S1a data exist
for them; harness heterogeneity is ignored for them, and S1a measured task-by-harness variance
at 3-4% of outcome variance). One serving session: a common logit shift u ~ N(0, 0.3^2) on every
cell (it cancels within tasks).

Effect structures on the layout factor (the text factor is null unless stated): uniform logit
shift; proportional reduction on every task; proportional reduction on a random quarter of the
tasks; complete breaks (p_RTL = 0) on a random share of tasks; task-specific logit
perturbations eps_t ~ N(theta, 1) (mixed sign); and a reshuffle in which a random share q of
tasks get an RTL probability redrawn from the task-level propensity distribution (a
decorrelating perturbation without direction). Targets are relative effects on the census
scale, RD = sum_t (p_RTL,t - p_LTR,t) / sum_t p_LTR,t, calibrated by bisection on a fixed bank
(expected RD over the bank); 0 for the nulls.

Registered estimators (registration v3, Decision rules):
  census frame ("these tasks"): D = mean_t D_t with D_t = ((y_arR - y_arL) + (y_enR - y_en)) / 2,
    its variance the sum of within-task episode variances (unbiased per (task, cell, harness)
    from m = n/2 episodes) over K^2; log ratio L = log(S_R / S_L) with S_x the mean over tasks of
    the two x-layout cells, delta-method variance from the same within-task variances.
    PRESENT if the 95% normal interval of D excludes 0. SMALL if the 90% interval of D lies in
    (-5, +5) pp and the 90% interval of L lies in (log 0.85, -log 0.85).
  population frame ("tasks like these", reported, not decision-bearing): t interval over tasks
    for D (df K - 1) and a task-level delta-method interval for L; SMALL_POP additionally needs
    the concentration guard: B = tasks whose one-sided Fisher exact test (RTL against LTR
    successes, 2n against 2n episodes) gives p <= 0.01, U the Clopper-Pearson 95% upper bound on
    B / K, and U x S_L < 5 pp and U < 0.15.
  v2's rule for comparison: paired t, TOST at +/-5 pp and the rare-break bound with a break at
    D_t <= -0.25 times the en mean.

Usage: python3 power-v3.py <a1.jsonl> <pool-v3.json> <out.json> [--nrep 2000]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import scipy
from scipy import optimize, stats

SEEDS = (42, 43, 44)
HARNESSES = ("H-OSW-fixed", "H-GA")
SESSION_SD = 0.30
MARGIN_ABS = 0.05
MARGIN_REL = 0.15  # registered: ratio inside (0.85, 1/0.85)
MARGIN_REL_ALT = 0.10  # reported alternative
ALPHA = 0.05
BREAK_P = 0.01
V2_BREAK_DT = -0.25
CAL_BANK = 2000
# cost (Q2 design study rule; as S2 v2)
V = 20
USR1_LEAD_MIN = 3
OVERLAY_MIN = 6
DR4_FACTOR = 1.2
REQUEUE_FACTOR = 1.05
STARTUP_S = 113.18587
DRAIN_S = 104.60958
SLOT_HIGH_S = 197.73  # mean slot of S1a 9B episodes that ran to the 15-step cap (S2 v2's high price)
SLOT_P95_S = 223.6  # LibreOffice cap-length p95 (asset cell)


def expit(x):
    return 1.0 / (1.0 + np.exp(-x))


def logit(p):
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return np.log(p) - np.log1p(-p)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fit_betabinom(ks, n):
    ks = np.asarray(ks)

    def nll(theta):
        a, b = np.exp(theta)
        return -float(np.sum(stats.betabinom.logpmf(ks, n, a, b)))

    best = None
    for a0 in (0.1, 0.3, 1.0):
        for b0 in (0.1, 0.3, 1.0):
            res = optimize.minimize(nll, np.log([a0, b0]), method="Nelder-Mead",
                                    options={"xatol": 1e-8, "fatol": 1e-10, "maxiter": 4000})
            if best is None or res.fun < best.fun:
                best = res
    a, b = np.exp(best.x)
    return float(a), float(b)


def check_fit(a, b, ks, n, rng, nsim=40000):
    p = rng.beta(a, b, size=nsim)
    k = rng.binomial(n, p)
    pairs = n * (n - 1) / 2
    return {"k_hist_observed": np.round(np.bincount(ks, minlength=n + 1) / len(ks), 4).tolist(),
            "k_hist_model": np.round(np.bincount(k, minlength=n + 1) / nsim, 4).tolist(),
            "discordance_observed": round(float(np.mean([x * (n - x) / pairs for x in ks])), 4),
            "discordance_model": round(float(np.mean(k * (n - k) / pairs)), 4),
            "mean_observed": round(float(np.mean(ks)) / n, 4), "mean_model": round(float(np.mean(k)) / n, 4)}


# ------------------------------------------------------------------------------------------


class Pool:
    def __init__(self, tasks, a_c, b_c, a_t, b_t):
        self.tasks = tasks
        self.K = len(tasks)
        self.obs = np.array([t["k_h"] is not None for t in tasks])
        k = np.array([t["k_h"] if t["k_h"] is not None else [0, 0] for t in tasks], dtype=float)
        nn = np.array([t["n_h"] if t["n_h"] is not None else [0, 0] for t in tasks], dtype=float)
        self.post_a = a_c + k
        self.post_b = b_c + nn - k
        self.a_t, self.b_t = a_t, b_t

    def draw(self, rng, R):
        K = self.K
        p_obs = rng.beta(np.broadcast_to(self.post_a, (R, K, 2)), np.broadcast_to(self.post_b, (R, K, 2)))
        p_new = rng.beta(self.a_t, self.b_t, size=(R, K, 1)).repeat(2, axis=2)
        p = np.where(self.obs[None, :, None], p_obs, p_new)
        return p  # (R, K, 2): English LTR probability per harness


def apply_effect(rng, p, struct, theta, a_t, b_t):
    """Returns RTL probabilities (R, K, H) for the layout factor."""
    R, K, H = p.shape
    if struct == "logit":
        return expit(logit(p) + theta)
    if struct == "prop":
        return p * (1 - theta)
    if struct == "conc25":
        z = (rng.random((R, K, 1)) < 0.25)
        return np.where(z, p * (1 - theta), p)
    if struct == "flip":
        z = (rng.random((R, K, 1)) < theta)
        return np.where(z, 0.0, p)
    if struct == "perturb":
        eps = theta + rng.standard_normal((R, K, 1))
        return expit(logit(p) + eps)
    if struct == "reshuffle":
        z = (rng.random((R, K, 1)) < theta)
        newp = rng.beta(a_t, b_t, size=(R, K, 1)).repeat(H, axis=2)
        return np.where(z, newp, p)
    raise ValueError(struct)


def rel_effect(p, pr):
    return float((pr.sum() - p.sum()) / p.sum())


def calibrate(pool, struct, target, seed):
    if struct == "reshuffle":
        return None  # parameter is the share q; no target
    if target == 0 and struct not in ("perturb",):
        return 0.0
    rng0 = np.random.Generator(np.random.PCG64([seed, 900]))
    p = pool.draw(rng0, CAL_BANK)
    state = rng0.bit_generator.state

    def f(th):
        r = np.random.Generator(np.random.PCG64([seed, 901]))
        return rel_effect(p, apply_effect(r, p, struct, th, pool.a_t, pool.b_t)) - target

    lo, hi = {"logit": (-8, 8), "perturb": (-8, 8), "prop": (0, 1), "conc25": (0, 1), "flip": (0, 1)}[struct]
    flo, fhi = f(lo), f(hi)
    if flo * fhi > 0:
        return None
    for _ in range(40):
        mid = (lo + hi) / 2
        fm = f(mid)
        if flo * fm <= 0:
            hi = mid
        else:
            lo, flo = mid, fm
    return (lo + hi) / 2


_HYPER = {}


def hyper_table(n):
    """One-sided Fisher exact p (fewer RTL successes) for 2n RTL against 2n LTR episodes: T[total, x_RTL]."""
    if n not in _HYPER:
        N = 2 * n
        T = np.ones((2 * N + 1, N + 1))
        for tot in range(2 * N + 1):
            for x in range(N + 1):
                T[tot, x] = stats.hypergeom.cdf(x, 2 * N, tot, N)
        _HYPER[n] = T
    return _HYPER[n]


def decide(k, n, p_true_ltr, p_true_rtl):
    """k: (R, K, H, 4) successes, cells (en, arL, enR, arR); m = n/2 episodes per (task, harness, cell)."""
    R, K, H, _ = k.shape
    m = n // 2
    phat = k / m
    yc = phat.mean(axis=2)  # (R, K, 4) cell means, harnesses equally weighted
    s2 = (m / (m - 1)) * phat * (1 - phat)  # unbiased p(1-p) per (t, h, c)
    var_yc = (s2 / m).sum(axis=2) / H**2  # (R, K, 4)
    D_t = ((yc[..., 3] - yc[..., 1]) + (yc[..., 2] - yc[..., 0])) / 2
    v_t = var_yc.sum(axis=2) / 4
    D = D_t.mean(axis=1)
    se_c = np.sqrt(v_t.sum(axis=1)) / K
    yR = (yc[..., 2] + yc[..., 3]) / 2
    yL = (yc[..., 0] + yc[..., 1]) / 2
    SR, SL = yR.mean(axis=1), yL.mean(axis=1)
    vR = ((var_yc[..., 2] + var_yc[..., 3]) / 4).sum(axis=1) / K**2
    vL = ((var_yc[..., 0] + var_yc[..., 1]) / 4).sum(axis=1) / K**2
    with np.errstate(divide="ignore", invalid="ignore"):
        L = np.log(SR) - np.log(SL)
        seL_c = np.sqrt(vR / SR**2 + vL / SL**2)
    z95, z90 = stats.norm.ppf(0.975), stats.norm.ppf(0.95)
    ok = np.isfinite(L) & np.isfinite(seL_c)
    present_c = np.abs(D) > z95 * se_c
    small_abs_c = (D - z90 * se_c > -MARGIN_ABS) & (D + z90 * se_c < MARGIN_ABS)
    lrel, lrel_alt = -math.log(1 - MARGIN_REL), -math.log(1 - MARGIN_REL_ALT)
    small_rel_c = ok & (L - z90 * seL_c > -lrel) & (L + z90 * seL_c < lrel)
    small_rel_alt_c = ok & (L - z90 * seL_c > -lrel_alt) & (L + z90 * seL_c < lrel_alt)
    small_c = small_abs_c & small_rel_c
    small_c_alt = small_abs_c & small_rel_alt_c
    # census truth
    tD = ((p_true_rtl - p_true_ltr).mean(axis=2)).mean(axis=1)
    tL = np.log(p_true_rtl.mean(axis=(1, 2))) - np.log(p_true_ltr.mean(axis=(1, 2)))
    cover_D = (D - z95 * se_c <= tD) & (tD <= D + z95 * se_c)
    cover_L = ok & (L - z95 * seL_c <= tL) & (tL <= L + z95 * seL_c)
    # population frame
    sd = D_t.std(axis=1, ddof=1)
    se_s = sd / math.sqrt(K)
    t95, t90 = stats.t.ppf(0.975, K - 1), stats.t.ppf(0.95, K - 1)
    present_s = np.abs(D) > t95 * se_s
    small_abs_s = (D - t90 * se_s > -MARGIN_ABS) & (D + t90 * se_s < MARGIN_ABS)
    cRR = ((yR - SR[:, None]) ** 2).sum(axis=1) / (K - 1)
    cLL = ((yL - SL[:, None]) ** 2).sum(axis=1) / (K - 1)
    cRL = ((yR - SR[:, None]) * (yL - SL[:, None])).sum(axis=1) / (K - 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        seL_s = np.sqrt(np.maximum(cRR / SR**2 + cLL / SL**2 - 2 * cRL / (SR * SL), 0) / K)
    small_rel_s = ok & (L - t90 * seL_s > -lrel) & (L + t90 * seL_s < lrel)
    xR = k[..., 2:].sum(axis=(2, 3))
    xL = k[..., :2].sum(axis=(2, 3))
    N = 2 * n
    tot = xR + xL
    p_drop = hyper_table(n)[tot, xR]
    B = (p_drop <= BREAK_P).sum(axis=1)
    U = np.where(B < K, stats.beta.ppf(0.95, B + 1, np.maximum(K - B, 1)), 1.0)
    guard = (U * SL < MARGIN_ABS) & (U < MARGIN_REL)
    small_pop = small_abs_s & small_rel_s & guard
    # v2's rule
    Bv2 = (D_t <= V2_BREAK_DT + 1e-12).sum(axis=1)
    Uv2 = np.where(Bv2 < K, stats.beta.ppf(0.95, Bv2 + 1, np.maximum(K - Bv2, 1)), 1.0)
    small_v2 = small_abs_s & (Uv2 * yc[..., 0].mean(axis=1) < MARGIN_ABS)
    # sharp-null randomization test (stratified by task, harness and text level)
    S = np.zeros(R)
    var = np.zeros(R)
    for ltr, rtl in ((0, 2), (1, 3)):
        mm = k[..., ltr] + k[..., rtl]
        Nn = 2 * m
        v = m * (mm / Nn) * (1 - mm / Nn) * (Nn - m) / (Nn - 1)
        S += (k[..., rtl] - k[..., ltr]).sum(axis=(1, 2))
        var += v.sum(axis=(1, 2))
    with np.errstate(divide="ignore", invalid="ignore"):
        zs = np.where(var > 0, S / np.sqrt(var), 0.0)
    sharp = 2 * stats.norm.sf(np.abs(zs)) <= ALPHA
    beyond = (np.abs(tD) >= MARGIN_ABS) | (np.abs(tL) >= lrel)
    within = (np.abs(tD) < MARGIN_ABS) & (np.abs(tL) < lrel)
    return {
        "present_harm": float((present_c & (D < 0)).mean()),
        "present_benefit": float((present_c & (D > 0)).mean()),
        "small": float(small_c.mean()),
        "small_abs_only": float(small_abs_c.mean()),
        "small_rel10_variant": float(small_c_alt.mean()),
        "inconclusive": float((~present_c & ~small_c).mean()),
        "present_and_small": float((present_c & small_c).mean()),
        "false_small_given_census_beyond_margin": (float((small_c & beyond).sum() / beyond.sum()) if beyond.sum() else None),
        "share_replicates_census_beyond_margin": float(beyond.mean()),
        "small_given_census_within_margin": (float((small_c & within).sum() / within.sum()) if within.sum() else None),
        "cover95_census_D": float(cover_D.mean()),
        "cover95_census_logratio": float(cover_L.mean()),
        "mean_census_true_D_pp": round(float(tD.mean()) * 100, 3),
        "sd_census_true_D_pp": round(float(tD.std()) * 100, 3),
        "mean_census_true_RD": round(float(np.expm1(tL).mean()), 4),
        "mean_se_census_D_pp": round(float(se_c.mean()) * 100, 3),
        "mean_en_success": round(float(yc[..., 0].mean()), 4),
        "pop_present_harm": float((present_s & (D < 0)).mean()),
        "pop_small_mean_only": float((small_abs_s & small_rel_s).mean()),
        "pop_small_with_guard": float(small_pop.mean()),
        "pop_mean_breaks_B": round(float(B.mean()), 3),
        "pop_mean_se_D_pp": round(float(se_s.mean()) * 100, 3),
        "v2_rule_small_unqualified": float(small_v2.mean()),
        "sharp_null_reject": float(sharp.mean()),
    }


def simulate(pool, struct, theta, n, R, seed):
    rng = np.random.Generator(np.random.PCG64([seed, 1, n, pool.K]))
    p = pool.draw(rng, R)
    u = rng.normal(0, SESSION_SD, size=(R, 1, 1))
    p = expit(logit(p) + u)
    pr = apply_effect(rng, p, struct, theta, pool.a_t, pool.b_t)
    m = n // 2
    cells = np.stack([p, p, pr, pr], axis=-1)  # text factor null
    k = rng.binomial(m, cells)
    return decide(k, n, p, pr)


def cost(K, n, slot_s=SLOT_HIGH_S, cells=4):
    N = cells * K * n
    physical_h = (STARTUP_S + N * slot_s / V + DRAIN_S) / 3600
    cap_min = math.ceil(USR1_LEAD_MIN + STARTUP_S / 60 + (N * slot_s / V + DRAIN_S) * DR4_FACTOR * REQUEUE_FACTOR / 60)
    return {"episodes": N, "physical_gpu_h_high_slot": round(physical_h, 3),
            "cap_minutes_incl_overlay": cap_min + OVERLAY_MIN, "cap_gpu_h_incl_overlay": round((cap_min + OVERLAY_MIN) / 60, 3)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("a1")
    ap.add_argument("pool")
    ap.add_argument("out")
    ap.add_argument("--nrep", type=int, default=2000)
    args = ap.parse_args()
    t0 = time.time()
    a1, poolp, outp = Path(args.a1), Path(args.pool), Path(args.out)
    poolj = json.loads(poolp.read_text())
    adm = [t for t in poolj["tasks"] if t["class"] != "excluded"]
    s1a = defaultdict(lambda: defaultdict(list))
    for line in a1.open():
        r = json.loads(line)
        if r["size"] == "9B":
            s1a[r["task_id"]][r["harness"]].append(1 if r["score"] == 1.0 else 0)
    tasks = []
    for t in adm:
        d = s1a.get(t["task_id"])
        if d:
            tasks.append({"task_id": t["task_id"], "split": t["split"], "app": t["app"],
                          "k_h": [sum(d[h]) for h in HARNESSES], "n_h": [len(d[h]) for h in HARNESSES]})
        else:
            tasks.append({"task_id": t["task_id"], "split": t["split"], "app": t["app"], "k_h": None, "n_h": None})
    obs = [t for t in tasks if t["k_h"]]
    cell_ks = [k for t in obs for k in t["k_h"]]
    assert all(nn == 4 for t in obs for nn in t["n_h"]), "expected 4 S1a 9B episodes per (task, harness)"
    task_ks = [sum(t["k_h"]) for t in obs]
    a_c, b_c = fit_betabinom(cell_ks, 4)
    a_t, b_t = fit_betabinom(task_ks, 8)
    rngc = np.random.Generator(np.random.PCG64([42, 7]))
    prior = {"cell_level": {"a": a_c, "b": b_c, "cells": len(cell_ks), "check": check_fit(a_c, b_c, np.array(cell_ks), 4, rngc)},
             "task_level": {"a": a_t, "b": b_t, "tasks": len(task_ks), "check": check_fit(a_t, b_t, np.array(task_ks), 8, rngc),
                            "mean": a_t / (a_t + b_t)}}
    sets = {
        "census_all_106": tasks,
        "without_dev_89": [t for t in tasks if t["split"] != "dev"],
        "confirm_only_62": [t for t in tasks if t["split"] == "confirm"],
        "v2_K26_like_confirm_informative": [t for t in obs if sum(t["k_h"]) >= 1 and t["split"] == "confirm"][:26],
    }
    scen = [("logit", 0.0), ("perturb", 0.0), ("reshuffle", 0.1), ("reshuffle", 0.3)]
    for struct in ("logit", "prop", "conc25", "flip"):
        for tgt in (-0.10, -0.15, -0.20, -0.30):
            scen.append((struct, tgt))
    scen += [("perturb", -0.15), ("perturb", -0.30)]
    n_grid = {"census_all_106": (4, 6, 8), "without_dev_89": (4,), "confirm_only_62": (4, 8), "v2_K26_like_confirm_informative": (16,)}
    results = []
    for sname, ts in sets.items():
        pool = Pool(ts, a_c, b_c, a_t, b_t)
        for n in n_grid[sname]:
            for struct, tgt in scen:
                rows = []
                thetas = []
                for seed in SEEDS:
                    theta = tgt if struct == "reshuffle" else calibrate(pool, struct, tgt, seed)
                    thetas.append(theta)
                    if theta is None:
                        rows = None
                        break
                    rows.append(simulate(pool, struct, theta, n, args.nrep, seed))
                if rows is None:
                    results.append({"set": sname, "K": pool.K, "n": n, "struct": struct, "target_RD": tgt, "unreachable": True})
                    continue
                agg = {}
                for key in rows[0]:
                    vals = [r[key] for r in rows if r[key] is not None]
                    agg[key] = round(float(np.mean(vals)), 4) if vals else None
                    agg[key + "_by_seed"] = [None if r[key] is None else round(r[key], 4) for r in rows]
                res = {"set": sname, "K": pool.K, "n": n, "struct": struct,
                       "target_RD": tgt if struct != "reshuffle" else None,
                       "reshuffle_q": tgt if struct == "reshuffle" else None,
                       "theta_by_seed": [round(x, 5) for x in thetas], **agg, "cost": cost(pool.K, n),
                       "cost_p95_slot": cost(pool.K, n, SLOT_P95_S)}
                results.append(res)
                print(f"{sname:34s} K={pool.K:3d} n={n:2d} {struct:9s} {str(tgt):6s} PH={agg['present_harm']:.3f} "
                      f"SM={agg['small']:.3f} INC={agg['inconclusive']:.3f} fS|beyond={agg['false_small_given_census_beyond_margin']} "
                      f"popSMg={agg['pop_small_with_guard']:.3f} v2SM={agg['v2_rule_small_unqualified']:.3f} "
                      f"cov={agg['cover95_census_D']:.3f} trueD={agg['mean_census_true_D_pp']} se={agg['mean_se_census_D_pp']}", flush=True)
    out = {
        "schema": "s2v3-power-v1",
        "inputs": {"a1_jsonl_sha256": sha256(a1), "pool_v3_json_sha256": sha256(poolp)},
        "seeds": list(SEEDS), "nrep_per_seed": args.nrep, "session_sd_logit": SESSION_SD,
        "margins": {"abs": MARGIN_ABS, "rel": MARGIN_REL, "rel_alt_reported": MARGIN_REL_ALT},
        "prior": prior,
        "sets": {k: {"K": len(v), "with_s1a_records": sum(1 for t in v if t["k_h"])} for k, v in sets.items()},
        "results": results,
        "costs": {f"K{K}_n{n}": cost(K, n) for K in (62, 89, 106, 140) for n in (4, 6, 8)},
        "cost_placebo_fifth_cell_K106_n4": cost(106, 4, cells=5),
        "versions": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__},
        "wall_seconds": round(time.time() - t0, 1),
    }
    outp.write_text(json.dumps(out, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
