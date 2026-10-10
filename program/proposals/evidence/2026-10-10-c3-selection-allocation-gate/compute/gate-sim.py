#!/usr/bin/env python3
"""S1: operating characteristics of the C3 Stage-0 gate's registered decision rules.

Simulation only. Every distribution below is ASSUMED; no Qwen3-8B trace has been
generated on this host. The script answers five design questions for the draft
registration c3-selection-allocation-gate-v1:

  I  Identification of the dossier's spread target. Is pi_mid (the share of
     questions whose TRUE pass rate lies in [0.1, 0.9]) identified from k draws
     per question? Sharp population bounds by linear programming over mixing
     distributions that reproduce the k-draw count distribution, and the
     iteration dependence of the EM path to the binomial-mixture NPMLE.
  S  Spread decision. The dossier statistic (share of questions whose empirical
     pass rate over k = 6 draws lies in [0.1, 0.9], i.e. 1 to 5 of 6 correct)
     against the registered identified estimand theta_bal (share of questions
     whose six draws are contested, 2 to 4 of 6 correct; an unbiased estimator
     of E[P(2 <= S <= 4 | p)] for six fresh draws), each with a 90%
     family-cluster bootstrap interval and a three-way rule; plus tau2 =
     E[2p(1-p)] and Var(p) (split-half covariance), both identified.
  D  Decodability (dossier line AUC 0.60): PASS if the lower 90% bound of the
     pooled within-question AUC is >= 0.60, STOP if the upper bound is < 0.60,
     else INDETERMINATE.
  F  Floor increment: paired increment of the hidden-state gate's
     within-question AUC over an output-only floor; PASS if the lower bound is
     > 0, REDUNDANT if the upper bound is < 0.02, else INDETERMINATE.
  G  Selection gain at k = 6 over majority voting (reported, with a HARM stop if
     the weighted vote's upper bound is < 0): CASE's argmax rule and a
     gate-weighted vote.

Generative model (assumed). Questions sit in families (contest instances);
family sizes are geometric with mean 6, capped at 15. Pass rates p_q come from a
scenario mixture whose component weights vary by family (Dirichlet with
concentration ALPHA times the global weights; point-mass scenarios have no
family effect; logit-normal scenarios get a N(0, 0.8^2) family shift). Each
question gets k = 6 Bernoulli(p_q) draws. Gate scores are s = a_q * y + e with
e ~ N(0, 1), so the question's true within-question AUC is Phi(a_q / sqrt 2);
a_q = a0 + 0.25 z_family + 0.35 z_question, with a0 chosen so that the
population mean of Phi(a_q / sqrt 2) equals the target (closed form
Phi(a0 / sqrt(2 + 0.25^2 + 0.35^2))). The output-only floor score is
f = b_q * y + e', corr(e, e') = rho. Wrong answers coincide on one dominant
wrong answer with probability c (pairwise collision rate c^2; 2609.32035
Table 1 reports 0.25 to 0.51 for Qwen3-8B with reasoning on), otherwise they
are unique. Majority voting breaks ties uniformly at random (expected value
used). The weighted vote sums logistic(s) over the draws sharing an answer.

Seeds: every cell is seeded from (base seed, cell key) by SHA-256 with base
seeds 42, 43 and 44; results pool the three seeds. The bootstrap resamples
families with replacement.

Usage: python gate-sim.py <out.json> [--quick]
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
import time

import numpy as np
from scipy.optimize import linprog
from scipy.stats import binom, norm

K = 6
SEEDS = (42, 43, 44)
ALPHA = 4.0
SD_F, SD_Q = 0.25, 0.35
AUC_LINE = 0.60
FLOOR_MARGIN = 0.02
THETA_LINE = 0.10
RAW_LINE = 0.20

SCENARIOS = {
    "S0_point_0957": ("every question p = 0.957 (kill-shot cell: no heterogeneity)",
                      [(1.0, ("point", 0.957))], False),
    "S1_ks_alloc": ("90% p = 1, 10% p = 0.6 (kill-shot cell: allocation helps most)",
                    [(0.9, ("point", 1.0)), (0.1, ("point", 0.6))], False),
    "S2_xd_extremes": ("60% p = 0.98, 40% p = 0.04 (cross-domain cell: no question in band)",
                       [(0.6, ("point", 0.98)), (0.4, ("point", 0.04))], False),
    "S3_mid10": ("70% Beta(30,1), 10% U[0.1,0.9], 20% Beta(1,30)",
                 [(0.7, ("beta", 30.0, 1.0)), (0.1, ("unif", 0.1, 0.9)), (0.2, ("beta", 1.0, 30.0))], True),
    "S4_mid15": ("70% Beta(30,1), 15% U[0.1,0.9], 15% Beta(1,30)",
                 [(0.7, ("beta", 30.0, 1.0)), (0.15, ("unif", 0.1, 0.9)), (0.15, ("beta", 1.0, 30.0))], True),
    "S5_mid20": ("60% Beta(30,1), 20% U[0.1,0.9], 20% Beta(1,30)",
                 [(0.6, ("beta", 30.0, 1.0)), (0.2, ("unif", 0.1, 0.9)), (0.2, ("beta", 1.0, 30.0))], True),
    "S6_xd_25": ("50% p = 0.97, 25% p = 0.03, 25% U[0.1,0.9] (cross-domain cell)",
                 [(0.5, ("point", 0.97)), (0.25, ("point", 0.03)), (0.25, ("unif", 0.1, 0.9))], True),
    "S7_mid30": ("55% Beta(30,1), 30% U[0.1,0.9], 15% Beta(1,30)",
                 [(0.55, ("beta", 30.0, 1.0)), (0.3, ("unif", 0.1, 0.9)), (0.15, ("beta", 1.0, 30.0))], True),
    "S8_mid40": ("45% Beta(30,1), 40% U[0.1,0.9], 15% Beta(1,30)",
                 [(0.45, ("beta", 30.0, 1.0)), (0.4, ("unif", 0.1, 0.9)), (0.15, ("beta", 1.0, 30.0))], True),
    "S9_logitnormal_easy": ("logit p ~ N(3.0, 2.0^2) plus a family shift N(0, 0.8^2)",
                            [(1.0, ("logitnorm", 3.0, 2.0))], True),
    "S10_logitnormal_mid": ("logit p ~ N(1.5, 2.0^2) plus a family shift N(0, 0.8^2)",
                            [(1.0, ("logitnorm", 1.5, 2.0))], True),
    "S11_edge_heavy": ("70% Beta(30,1), 20% U[0.80,0.90], 10% Beta(1,30) (in-band mass at the top edge)",
                       [(0.7, ("beta", 30.0, 1.0)), (0.2, ("unif", 0.80, 0.90)), (0.1, ("beta", 1.0, 30.0))], True),
}


def cell_rng(seed: int, *key: object) -> np.random.Generator:
    digest = hashlib.sha256(json.dumps([seed, *key], default=str).encode()).digest()
    return np.random.default_rng(int.from_bytes(digest[:8], "little"))


def make_families(rng: np.random.Generator, n_q: int) -> tuple[np.ndarray, int]:
    sizes: list[int] = []
    total = 0
    while total < n_q:
        size = min(int(min(15, rng.geometric(1.0 / 6.0))), n_q - total)
        sizes.append(size)
        total += size
    return np.repeat(np.arange(len(sizes)), sizes), len(sizes)


def draw_component(rng, comp, n, fam_shift):
    kind = comp[0]
    if kind == "point":
        return np.full(n, comp[1])
    if kind == "beta":
        return rng.beta(comp[1], comp[2], size=n)
    if kind == "unif":
        return rng.uniform(comp[1], comp[2], size=n)
    if kind == "logitnorm":
        z = comp[1] + comp[2] * rng.standard_normal(n) + (fam_shift if fam_shift is not None else 0.0)
        return 1.0 / (1.0 + np.exp(-z))
    raise ValueError(kind)


def sample_p(rng, scen, fam, n_fam):
    _, comps, clustered = SCENARIOS[scen]
    n = fam.size
    if len(comps) == 1:
        shift = 0.8 * rng.standard_normal(n_fam)[fam] if (clustered and comps[0][1][0] == "logitnorm") else None
        return draw_component(rng, comps[0][1], n, shift)
    weights = np.array([w for w, _ in comps])
    famw = rng.dirichlet(ALPHA * weights, size=n_fam) if clustered else np.tile(weights, (n_fam, 1))
    cum = np.cumsum(famw, axis=1)[fam]
    idx = np.minimum((rng.random(n)[:, None] > cum).sum(axis=1), len(comps) - 1)
    p = np.empty(n)
    for i, (_, comp) in enumerate(comps):
        sel = idx == i
        if sel.any():
            p[sel] = draw_component(rng, comp, int(sel.sum()), None)
    return p


def population(scen: str, n: int = 400_000) -> dict:
    rng = cell_rng(0, "truth", scen)
    fam, n_fam = make_families(rng, n)
    p = sample_p(rng, scen, fam, n_fam)
    pm = binom.pmf(np.arange(K + 1)[:, None], K, p[None, :])  # (K+1, n)
    return {"pi_mid": float(((p >= 0.1) & (p <= 0.9)).mean()),
            "theta_bal_k6": float(pm[2:5].sum(axis=0).mean()),
            "raw_share_k6": float(pm[1:6].sum(axis=0).mean()),
            "tau2": float((2 * p * (1 - p)).mean()), "var_p": float(p.var()), "mean_p": float(p.mean()),
            "_p": p}


# ------------------------------------------------------------ identification (I)

def identified_set(p: np.ndarray, k: int, tol: float = 3e-4) -> tuple[float, float]:
    grid = np.linspace(0.0, 1.0, 201)
    mid = ((grid >= 0.1 - 1e-9) & (grid <= 0.9 + 1e-9)).astype(float)
    lik = binom.pmf(np.arange(k + 1)[:, None], k, grid[None, :])
    marg = binom.pmf(np.arange(k + 1)[:, None], k, p[None, :]).mean(axis=1)
    a_ub = np.vstack([lik, -lik])
    b_ub = np.concatenate([marg + tol, -(marg - tol)])
    kw = dict(A_ub=a_ub, b_ub=b_ub, A_eq=np.ones((1, grid.size)), b_eq=[1.0], bounds=(0, None), method="highs")
    lo, hi = linprog(mid, **kw), linprog(-mid, **kw)
    if lo.status != 0 or hi.status != 0:
        return float("nan"), float("nan")
    return float(lo.fun), float(-hi.fun)


def em_path(p: np.ndarray, n_q: int, seed: int, iters=(100, 300, 1000, 3000, 10000)) -> list[float]:
    grid = np.linspace(0.0, 1.0, 101)
    mid = (grid >= 0.1 - 1e-9) & (grid <= 0.9 + 1e-9)
    lik = binom.pmf(np.arange(K + 1)[:, None], K, grid[None, :])
    rng = np.random.default_rng(seed)
    sub = rng.choice(p, size=n_q, replace=False)
    s = (rng.random((n_q, K)) < sub[:, None]).sum(axis=1)
    hist = np.bincount(s, minlength=K + 1).astype(float)
    w = np.full(grid.size, 1.0 / grid.size)
    out, done = [], 0
    for target in iters:
        for _ in range(target - done):
            dens = lik @ w
            w = w * (lik.T @ np.where(hist > 0, hist / np.maximum(dens, 1e-300), 0.0)) / hist.sum()
        done = target
        out.append(round(float(w[mid].sum()), 4))
    return out


# ----------------------------------------------------------------- helpers

def boot_weights(rng, n_fam, n_boot):
    return rng.multinomial(n_fam, np.full(n_fam, 1.0 / n_fam), size=n_boot).astype(float)


def interval(values):
    lo, hi = np.quantile(values, [0.05, 0.95])
    return float(lo), float(hi)


def three_way(lo, hi, line):
    if lo >= line:
        return "PASS"
    if hi < line:
        return "STOP"
    return "INDETERMINATE"


# ---------------------------------------------------------------- spread (S)

def sim_spread(scen, n_q, reps, n_boot, truth):
    reg = {"PASS": 0, "STOP": 0, "INDETERMINATE": 0}
    raw = {"PASS": 0, "STOP": 0, "INDETERMINATE": 0}
    th, rw, ta, va, cover, widths = [], [], [], [], 0, []
    for seed in SEEDS:
        rng = cell_rng(seed, "spread", scen, n_q)
        for _ in range(reps):
            fam, n_fam = make_families(rng, n_q)
            p = sample_p(rng, scen, fam, n_fam)
            y = rng.random((n_q, K)) < p[:, None]
            s = y.sum(axis=1)
            ya, yb = y[:, :3].mean(axis=1), y[:, 3:].mean(axis=1)
            fsum = lambda v: np.bincount(fam, weights=v, minlength=n_fam)  # noqa: E731
            f_th = fsum(((s >= 2) & (s <= 4)).astype(float))
            f_rw = fsum(((s >= 1) & (s <= K - 1)).astype(float))
            f_ta = fsum(s * (K - s) / (K * (K - 1) / 2))
            f_a, f_b, f_ab = fsum(ya), fsum(yb), fsum(ya * yb)
            f_n = np.bincount(fam, minlength=n_fam).astype(float)
            m = np.vstack([np.ones(n_fam), boot_weights(rng, n_fam, n_boot)])
            nb = m @ f_n
            th_b, rw_b, ta_b = (m @ f_th) / nb, (m @ f_rw) / nb, (m @ f_ta) / nb
            va_b = ((m @ f_ab) - (m @ f_a) * (m @ f_b) / nb) / (nb - 1)
            lo, hi = interval(th_b[1:])
            reg[three_way(lo, hi, THETA_LINE)] += 1
            cover += lo <= truth["theta_bal_k6"] <= hi
            widths.append(hi - lo)
            rlo, rhi = interval(rw_b[1:])
            raw[three_way(rlo, rhi, RAW_LINE)] += 1
            th.append(th_b[0]); rw.append(rw_b[0]); ta.append(ta_b[0]); va.append(va_b[0])
    total = reps * len(SEEDS)
    return {"scenario": scen, "n_heldout_questions": n_q, "replicates": total,
            "verdicts_registered_theta_bal": {k: round(v / total, 4) for k, v in reg.items()},
            "verdicts_dossier_raw_share": {k: round(v / total, 4) for k, v in raw.items()},
            "theta_bal_hat_mean": round(float(np.mean(th)), 4), "theta_bal_hat_sd": round(float(np.std(th)), 4),
            "theta_bal_interval_width_mean": round(float(np.mean(widths)), 4),
            "theta_bal_interval_coverage": round(cover / total, 4),
            "raw_share_hat_mean": round(float(np.mean(rw)), 4), "tau2_hat_mean": round(float(np.mean(ta)), 4),
            "var_p_hat_mean": round(float(np.mean(va)), 5)}


# ---------------------------------------------------------- decodability (D, F, G)

def separation_for(auc):
    return float(norm.ppf(auc) * math.sqrt(2.0 + SD_F ** 2 + SD_Q ** 2))


def within_auc(scores, y):
    pos = y[:, :, None] & ~y[:, None, :]
    gt = scores[:, :, None] > scores[:, None, :]
    eq = scores[:, :, None] == scores[:, None, :]
    num = ((gt + 0.5 * eq) * pos).sum(axis=(1, 2))
    den = pos.sum(axis=(1, 2))
    mixed = den > 0
    return np.where(mixed, num / np.maximum(den, 1), np.nan), mixed


def simulate_pool(rng, n_q, scen, auc, floor_auc, rho, collision_c):
    fam, n_fam = make_families(rng, n_q)
    p = sample_p(rng, scen, fam, n_fam)
    y = rng.random((n_q, K)) < p[:, None]
    a = separation_for(auc) + SD_F * rng.standard_normal(n_fam)[fam] + SD_Q * rng.standard_normal(n_q)
    e1 = rng.standard_normal((n_q, K))
    s = a[:, None] * y + e1
    f = None
    if floor_auc is not None:
        b = separation_for(floor_auc) + SD_F * rng.standard_normal(n_fam)[fam] + SD_Q * rng.standard_normal(n_q)
        f = b[:, None] * y + rho * e1 + math.sqrt(1 - rho ** 2) * rng.standard_normal((n_q, K))
    dom = (~y) & (rng.random((n_q, K)) < collision_c)
    c0, c1 = y.sum(axis=1), dom.sum(axis=1)
    u = (~y & ~dom).sum(axis=1)
    max_other = np.maximum(c1, (u > 0).astype(int))
    ntied = 1 + (c1 == c0) + np.where(c0 == 1, u, 0)
    mv = np.where(c0 > max_other, 1.0, np.where((c0 == max_other) & (c0 > 0), 1.0 / ntied, 0.0))
    case = y[np.arange(n_q), np.argmax(s, axis=1)].astype(float)
    g = 1.0 / (1.0 + np.exp(-s))
    w0 = (g * y).sum(axis=1)
    w1 = (g * dom).sum(axis=1)
    wu = np.where(~y & ~dom, g, 0.0).max(axis=1)
    best_other = np.maximum(w1, wu)
    wvote = np.where(w0 > best_other, 1.0, np.where(w0 == best_other, 0.5, 0.0)) * (c0 > 0)
    return fam, n_fam, y, s, f, mv, case, wvote


def sim_decode(n_q, auc, reps, n_boot, scen="S7_mid30"):
    counts = {"PASS": 0, "STOP": 0, "INDETERMINATE": 0}
    est, mixed_n, widths = [], [], []
    for seed in SEEDS:
        rng = cell_rng(seed, "decode", n_q, auc, scen)
        for _ in range(reps):
            fam, n_fam, y, s, *_ = simulate_pool(rng, n_q, scen, auc, None, 0.0, 0.6)
            auc_q, mixed = within_auc(s, y)
            fs = np.bincount(fam[mixed], weights=auc_q[mixed], minlength=n_fam)
            fm = np.bincount(fam[mixed], minlength=n_fam).astype(float)
            m = np.vstack([np.ones(n_fam), boot_weights(rng, n_fam, n_boot)])
            vals = (m @ fs) / np.maximum(m @ fm, 1)
            lo, hi = interval(vals[1:])
            counts[three_way(lo, hi, AUC_LINE)] += 1
            est.append(vals[0]); mixed_n.append(int(mixed.sum())); widths.append(hi - lo)
    total = reps * len(SEEDS)
    return {"scenario": scen, "n_heldout_questions": n_q, "true_auc": auc, "replicates": total,
            "verdicts": {k: round(v / total, 4) for k, v in counts.items()},
            "auc_hat_mean": round(float(np.mean(est)), 4), "auc_hat_sd": round(float(np.std(est)), 4),
            "interval_width_mean": round(float(np.mean(widths)), 4),
            "mixed_questions_mean": round(float(np.mean(mixed_n)), 1)}


def sim_floor(n_q, auc, floor_auc, rho, reps, n_boot, scen="S7_mid30"):
    counts = {"PASS": 0, "REDUNDANT": 0, "INDETERMINATE": 0}
    est = []
    for seed in SEEDS:
        rng = cell_rng(seed, "floor", n_q, auc, floor_auc, rho, scen)
        for _ in range(reps):
            fam, n_fam, y, s, f, *_ = simulate_pool(rng, n_q, scen, auc, floor_auc, rho, 0.6)
            a1, mixed = within_auc(s, y)
            a2, _ = within_auc(f, y)
            fs = np.bincount(fam, weights=np.where(mixed, a1 - a2, 0.0), minlength=n_fam)
            fm = np.bincount(fam[mixed], minlength=n_fam).astype(float)
            m = np.vstack([np.ones(n_fam), boot_weights(rng, n_fam, n_boot)])
            vals = (m @ fs) / np.maximum(m @ fm, 1)
            lo, hi = interval(vals[1:])
            counts["PASS" if lo > 0 else ("REDUNDANT" if hi < FLOOR_MARGIN else "INDETERMINATE")] += 1
            est.append(vals[0])
    total = reps * len(SEEDS)
    return {"n_heldout_questions": n_q, "probe_auc": auc, "floor_auc": floor_auc, "rho": rho,
            "true_increment": round(auc - floor_auc, 4), "replicates": total,
            "verdicts": {k: round(v / total, 4) for k, v in counts.items()},
            "increment_hat_mean": round(float(np.mean(est)), 4), "increment_hat_sd": round(float(np.std(est)), 4)}


def sim_selection(n_q, auc, collision_c, reps, n_boot, scen="S7_mid30"):
    rows = {"case_argmax": [], "weighted_vote": []}
    bounds = {"case_argmax": [], "weighted_vote": []}
    for seed in SEEDS:
        rng = cell_rng(seed, "select", n_q, auc, collision_c, scen)
        for _ in range(reps):
            fam, n_fam, y, s, _, mv, case, wvote = simulate_pool(rng, n_q, scen, auc, None, 0.0, collision_c)
            m = np.vstack([np.ones(n_fam), boot_weights(rng, n_fam, n_boot)])
            fn = np.bincount(fam, minlength=n_fam).astype(float)
            for name, arm in (("case_argmax", case), ("weighted_vote", wvote)):
                vals = (m @ np.bincount(fam, weights=arm - mv, minlength=n_fam)) / (m @ fn)
                rows[name].append(vals[0]); bounds[name].append(interval(vals[1:]))
    rng = cell_rng(0, "select-truth", auc, collision_c, scen)
    _, _, _, _, _, mv, case, wvote = simulate_pool(rng, 200_000, scen, auc, None, 0.0, collision_c)
    truth = {"case_argmax": float((case - mv).mean()), "weighted_vote": float((wvote - mv).mean())}
    out = {"scenario": scen, "n_heldout_questions": n_q, "true_auc": auc, "collision_c": collision_c,
           "replicates": reps * len(SEEDS), "mv_accuracy": round(float(mv.mean()), 4)}
    for name in rows:
        est = np.array(rows[name]); b = np.array(bounds[name]); se = float(est.std())
        out[name] = {"true_gain_pp": round(100 * truth[name], 3), "gain_hat_sd_pp": round(100 * se, 3),
                     "p_lower90_above_0": round(float(np.mean(b[:, 0] > 0)), 4),
                     "p_upper90_below_0": round(float(np.mean(b[:, 1] < 0)), 4),
                     "mde80_one_sided_pp": round(100 * (norm.ppf(0.95) + norm.ppf(0.80)) * se, 3)}
    return out


def interaction_mde(n, var=0.24, rho=0.7, deff=1.0):
    """80%-power two-sided 5% MDE of the 2x2 interaction contrast (1,-1,-1,1) with paired arms."""
    return (norm.ppf(0.975) + norm.ppf(0.80)) * math.sqrt(var * 4 * (1 - rho) * deff / n)


def main() -> int:
    out_path = sys.argv[1]
    quick = "--quick" in sys.argv
    reps = 20 if quick else 200
    n_boot = 200 if quick else 1000
    t0 = time.time()
    pops = {k: population(k) for k in SCENARIOS}
    truth = {k: {kk: round(vv, 5) for kk, vv in v.items() if not kk.startswith("_")} for k, v in pops.items()}
    ident = {}
    for scen, pop in pops.items():
        sub = pop["_p"][:100_000]
        ident[scen] = {f"k{k}": [round(x, 4) for x in identified_set(sub, k)] for k in (6, 8, 10, 16)}
    em = {scen: em_path(pops[scen]["_p"], 320, 42) for scen in ("S5_mid20", "S7_mid30", "S9_logitnormal_easy")}
    print("identification done", round(time.time() - t0, 1), flush=True)
    result: dict = {
        "script": "gate-sim.py", "seeds": list(SEEDS), "reps_per_seed": reps, "bootstrap_draws": n_boot,
        "k_draws": K, "alpha_family_concentration": ALPHA, "sd_family": SD_F, "sd_question": SD_Q,
        "lines": {"auc": AUC_LINE, "floor_margin": FLOOR_MARGIN, "theta_bal": THETA_LINE, "raw_share": RAW_LINE},
        "assumptions": "ASSUMED distributions; see the module docstring. No Qwen3-8B data exist.",
        "scenarios": {k: v[0] for k, v in SCENARIOS.items()},
        "truth": truth,
        "identification": {
            "pi_mid_identified_set_population": ident,
            "note": "Sharp bounds on pi_mid over mixing distributions on a 201-point grid that reproduce the population k-draw count distribution within 3e-4 per cell; nan = LP infeasible at that tolerance (an off-grid point mass).",
            "em_npmle_pi_mid_by_iteration_n320_seed42": {"iterations": [100, 300, 1000, 3000, 10000], **em},
        },
    }
    result["spread"] = [sim_spread(scen, n_q, reps, n_boot, truth[scen]) for scen in SCENARIOS for n_q in (240, 320)]
    print("spread done", round(time.time() - t0, 1), flush=True)
    result["decodability"] = [sim_decode(n_q, auc, reps, n_boot)
                              for n_q in (160, 240, 320, 400) for auc in (0.54, 0.57, 0.60, 0.63, 0.66, 0.70, 0.75)]
    result["decodability"] += [sim_decode(320, auc, reps, n_boot, scen="S5_mid20") for auc in (0.54, 0.60, 0.66, 0.70)]
    print("decode done", round(time.time() - t0, 1), flush=True)
    result["floor_increment"] = [sim_floor(n_q, 0.70, fl, rho, reps, n_boot)
                                 for n_q in (240, 320) for fl in (0.70, 0.69, 0.66, 0.62) for rho in (0.3, 0.6)]
    print("floor done", round(time.time() - t0, 1), flush=True)
    result["selection_gain"] = [sim_selection(320, auc, c, reps, n_boot)
                                for auc in (0.55, 0.60, 0.65, 0.70, 0.80) for c in (0.3, 0.6)]
    print("selection done", round(time.time() - t0, 1), flush=True)
    result["interaction_mde_pp_2x2"] = {f"n{n}_rho{r}": round(100 * interaction_mde(n, rho=r), 2)
                                        for n in (400, 1200) for r in (0.5, 0.7, 0.85)}
    result["elapsed_s"] = round(time.time() - t0, 1)
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=1)
        handle.write("\n")
    print("wrote", out_path, result["elapsed_s"], "s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
