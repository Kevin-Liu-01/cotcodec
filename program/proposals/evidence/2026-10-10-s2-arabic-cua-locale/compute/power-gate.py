#!/usr/bin/env python3
"""S2 power gate: analytic MDE grid, cost model, and Monte Carlo operating characteristics.

CPU only. Written by the S2 gauntlet's single synthesis owner on 2026-10-10.

What it computes
----------------
A. Anchors from S1a's episode records (q2-stage1-rescoped-v1, a1.jsonl): per
   (size, harness, task) cell success over the four reruns (raw `score` >= 1 is
   a success), the share of cells at 0 and 1, the unbiased mean within-cell
   Bernoulli variance E[p(1-p)], and a zero-inflated beta-binomial fit of the
   9B cells, which is the "S1a transport" base-rate scenario for Relay.
B. Analytic minimum detectable effects (80% power, two-sided alpha 0.05,
   paired t on task means with K - 1 df, exact noncentral t) for
     - the dossier's conditional contrast (ar-RTL minus ar-LTR, 3 cells):
       Var(task difference) = tau2 + 2 sigma2 / n;
     - the 2x2 main effect of direction (or of text):
       Var = tau2 + sigma2 / n  (each main effect averages two paired
       differences, so its sampling variance is (1/4)(4 sigma2 / n));
     - the 2x2 interaction: Var = 4 tau2 + 4 sigma2 / n;
   over K, n (episodes per task-locale cell), sigma2 and tau2; plus TOST
   power at a true effect of 0 with margin +/-5 pp.
C. Cost model (GPU-h per episode, low / central / high) from S1a's realized
   9B cost and steps and the serving probe v2 rate, and the cap formula.
D. Monte Carlo operating characteristics of the registered staged design
   (seeds 42, 43, 44): an English-only Relay pilot (18 tasks x 8 episodes)
   selects informative tasks and estimates sigma2; the registered power gate
   chooses n (or fails); the main 2x2 runs on the informative tasks with
   fresh English data; the primary decision on the direction main effect D
   is PRESENT (paired t p <= 0.05), EQUIVALENT (90% t interval inside
   +/-5 pp) or INCONCLUSIVE. Three base-rate scenarios, four true direction
   effects and three heterogeneity patterns. For comparison, the dossier's
   fixed design (conditional contrast, n = 8, all 18 tasks, no gate) is
   simulated on the same draws.

Every distribution in D is an assumption; nothing here is a Relay
measurement. The pilot exists to replace the transport.

Usage: power-gate.py <a1.jsonl> <out.json> [--nrep N]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import zlib
import sys
from pathlib import Path

import numpy as np
import scipy
from scipy import optimize, special, stats

SEEDS = [42, 43, 44]
ALPHA = 0.05
POWER = 0.80
MARGIN = 0.05  # pp/100: the dossier's ~5 pp MDE line and the TOST margin
TAU2_GATE = 0.0025  # registered: a 5 pp mean effect carried by half the tasks (0.5 * 0.5 * 0.10^2)
N_GRID = [8, 12, 16, 20, 24, 28, 32, 36, 40, 48, 56, 64]
K_ALL = 18
PILOT_N = 8  # 4 cosmetic seeds x 2 reruns, English only
PILOT_MIN_SUCCESSES = 2  # a task is informative if it succeeds in at least 2 of its 8 pilot episodes
K_INF_MIN = 12
FLOOR_BAND = (0.15, 0.85)  # dossier: English pixel success outside 15-85% -> pixel arm uninformative
CAP_CEILING = 15.0  # GPU-h, the dossier's Phase 1 envelope; any cap above it fails the gate on cost

# S1a registered readings (RESULTS.md, primary estimands table), percentage points / 100.
S1A = {"D_w_pooled": 0.1250, "D_w_9B": 0.0859, "D_w_4B": 0.1641, "D_b_pooled": 0.1133,
       "X_c_4B": 0.0084, "X_c_9B": 0.0150}

# Cost inputs (first-party measurements on this host).
STEP_CAP = 40
MEAN_STEPS = {"low": 24, "central": 24, "high": 36}
CONTEXT_FACTOR_HIGH = 1.3  # longer histories on 24-36 step Relay episodes than S1a's <= 15 steps
CAP_MARGIN = 1.2  # S1a DR4 convention
ARABIC_STEPS_ALLOWANCE = 1.25  # Stage-1b cap: 1.2 x 1.25 x the pilot-measured English GPU-h per episode
STARTUP_GPU_H = 0.10  # per GPU job: model load and warm-up (assumption; S1a jobs took about 0.05-0.1)
PROBE_V2_REQ_PER_S = (2.523 + 2.560 + 2.569) / 3  # serving probe v2 A1, 300 output tokens per request
S1A_OUTPUT_TOKENS_PER_STEP = 370  # asset cell's S1a reading; only scales the low price


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------- A. anchors
def load_cells(a1: Path):
    rows = [json.loads(line) for line in a1.read_text().splitlines() if line.strip()]
    cells: dict[tuple, list[float]] = {}
    steps_9b, gpu = [], {}
    for r in rows:
        s = r.get("score")
        y = 1.0 if (s is not None and s >= 1.0) else 0.0
        base = r["block"] in ("b1", "b2")
        cells.setdefault((r["size"], r["harness"], r["task_id"], base), []).append(y)
        if r["size"] == "9B" and isinstance(r.get("steps"), (int, float)):
            steps_9b.append(r["steps"])
    return rows, cells, steps_9b


def cell_stats(cells, size=None, base_only=None):
    vals = [v for (z, _, _, b), v in cells.items()
            if (size is None or z == size) and (base_only is None or b == base_only)]
    p = np.array([np.mean(v) for v in vals])
    n = np.array([len(v) for v in vals])
    unb = np.mean([len(v) / (len(v) - 1) * np.mean(v) * (1 - np.mean(v)) for v in vals])
    return {"cells": int(len(vals)), "reruns_per_cell": sorted(set(n.tolist())),
            "mean_success": round(float(p.mean()), 4), "share_p0": round(float((p == 0).mean()), 4),
            "share_p1": round(float((p == 1).mean()), 4),
            "mean_within_cell_var_unbiased": round(float(unb), 4)}


def fit_zibb(cells, size="9B"):
    """Zero-inflated beta-binomial MLE on (k successes of n reruns) over all cells of one size."""
    data = [(int(sum(v)), len(v)) for (z, _, _, _), v in cells.items() if z == size]
    k = np.array([d[0] for d in data]); n = np.array([d[1] for d in data])

    def nll(theta):
        pi0 = special.expit(theta[0]); a = math.exp(theta[1]); b = math.exp(theta[2])
        logbb = (special.gammaln(n + 1) - special.gammaln(k + 1) - special.gammaln(n - k + 1)
                 + special.betaln(k + a, n - k + b) - special.betaln(a, b))
        lik = (1 - pi0) * np.exp(logbb) + pi0 * (k == 0)
        return -np.sum(np.log(np.maximum(lik, 1e-300)))

    best = min((optimize.minimize(nll, x0, method="Nelder-Mead", options={"xatol": 1e-8, "fatol": 1e-10, "maxiter": 20000})
                for x0 in ([0.0, 0.0, 0.0], [1.0, -1.0, 0.5], [-1.0, 0.5, 1.0])), key=lambda r: r.fun)
    pi0 = float(special.expit(best.x[0])); a = float(math.exp(best.x[1])); b = float(math.exp(best.x[2]))
    return {"size": size, "cells": int(len(k)), "pi0_structural_zero": round(pi0, 4), "beta_a": round(a, 4),
            "beta_b": round(b, 4), "implied_mean_success": round((1 - pi0) * a / (a + b), 4),
            "implied_E_p1mp": round((1 - pi0) * a * b / ((a + b) * (a + b + 1)), 4),
            "neg_log_lik": round(float(best.fun), 4)}


# ---------------------------------------------------------------- B. analytic MDE
def power_t(delta, K, v, alpha=ALPHA):
    df = K - 1
    lam = delta / math.sqrt(v / K)
    crit = stats.t.ppf(1 - alpha / 2, df)
    pw = 1 - stats.nct.cdf(crit, df, lam) + stats.nct.cdf(-crit, df, lam)
    return 1.0 if not np.isfinite(pw) else float(pw)


def mde(K, v, alpha=ALPHA, power=POWER):
    if v <= 0:
        return 0.0
    f = lambda d: power_t(d, K, v, alpha) - power
    hi = 12 * math.sqrt(v / K)
    return float(optimize.brentq(f, 1e-9, hi, xtol=1e-8))


def tost_power_at_zero(K, v, margin=MARGIN, alpha=ALPHA):
    """P(90% t interval inside (-margin, +margin)) when the true effect is 0 (normal-theory, sigma known in df)."""
    df = K - 1
    se = math.sqrt(v / K)
    crit = stats.t.ppf(1 - alpha, df)
    # Monte Carlo-free approximation: the estimate ~ N(0, se^2) and s ~ se*sqrt(chi2/df); integrate over chi2.
    q = np.linspace(1e-4, 1 - 1e-4, 4001)
    s = se * np.sqrt(stats.chi2.ppf(q, df) / df)
    half = margin - crit * s
    p = np.where(half > 0, stats.norm.cdf(half / se) - stats.norm.cdf(-half / se), 0.0)
    return float(np.mean(p))


def var_task(design, sigma2, tau2, n):
    if design == "conditional3":
        return tau2 + 2 * sigma2 / n
    if design == "main2x2":
        return tau2 + sigma2 / n
    if design == "interaction2x2":
        return 4 * tau2 + 4 * sigma2 / n
    raise ValueError(design)


def analytic_grid(sigmas):
    out = []
    for design in ("conditional3", "main2x2", "interaction2x2"):
        for K in (18, 16, 14, 12):
            for s_name, s2 in sigmas.items():
                for tau2 in (0.0, 0.0025, 0.005, 0.01):
                    row = {"design": design, "K": K, "sigma2_name": s_name, "sigma2": s2, "tau2": tau2}
                    for n in N_GRID + [10 ** 6]:
                        v = var_task(design, s2, tau2, n)
                        row[f"mde_pp_n{n if n < 10 ** 6 else 'inf'}"] = round(100 * mde(K, v), 2)
                    out.append(row)
    return out


# ---------------------------------------------------------------- C. cost model
def cost_model(steps_9b, gpu_per_ep_9b):
    mean_steps = float(np.mean(steps_9b))
    c_central = gpu_per_ep_9b / mean_steps
    c_low = 1.0 / (PROBE_V2_REQ_PER_S * 3600) * S1A_OUTPUT_TOKENS_PER_STEP / 300
    per_ep = {"low": MEAN_STEPS["low"] * c_low, "central": MEAN_STEPS["central"] * c_central,
              "high": MEAN_STEPS["high"] * c_central * CONTEXT_FACTOR_HIGH}
    cap_per_ep = per_ep["high"] * CAP_MARGIN
    return {"s1a_9b_gpu_h_per_episode": round(gpu_per_ep_9b, 6), "s1a_9b_mean_steps": round(mean_steps, 3),
            "gpu_h_per_step": {"low_gpu_bound": round(c_low, 7), "central_s1a_realized": round(c_central, 7),
                               "high": round(c_central * CONTEXT_FACTOR_HIGH, 7)},
            "step_cap": STEP_CAP, "mean_steps_assumed": MEAN_STEPS,
            "gpu_h_per_episode": {k: round(v, 5) for k, v in per_ep.items()},
            "cap_gpu_h_per_episode": round(cap_per_ep, 5), "startup_gpu_h_per_job": STARTUP_GPU_H,
            "cap_formula": "cap = 1.2 x episodes x 36 steps x high GPU-h per step + 0.10 GPU-h per job"}, per_ep, cap_per_ep


def cap_for(episodes, cap_per_ep, jobs=1):
    return episodes * cap_per_ep + STARTUP_GPU_H * jobs


# ---------------------------------------------------------------- D. Monte Carlo
SCENARIOS = {}


def scenario_draw(name, rng, size, zibb):
    if name == "A_s1a_transport":
        pi0, a, b = zibb["pi0_structural_zero"], zibb["beta_a"], zibb["beta_b"]
    elif name == "B_mid_range":
        pi0, a, b = 0.10, 2.0, 2.0
    elif name == "C_near_floor":
        pi0, a, b = 0.50, 1.0, 4.0
    elif name == "D_near_deterministic":
        pi0, a, b = 0.15, 0.30, 0.12
    else:
        raise ValueError(name)
    p = rng.beta(a, b, size=size)
    p[rng.random(size) < pi0] = 0.0
    return p


def lg(p):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def ex(x):
    return 1.0 / (1.0 + np.exp(-x))


def calibrate(target, fn, lo=-12.0, hi=12.0, iters=32):
    """Vectorised bisection: find c (per row) with fn(c) == target; fn is increasing in c."""
    lo = np.full(target.shape, lo); hi = np.full(target.shape, hi)
    for _ in range(iters):
        mid = (lo + hi) / 2
        val = fn(mid)
        up = val > target
        hi = np.where(up, mid, hi); lo = np.where(up, lo, mid)
    return (lo + hi) / 2


def gate_choose_n(K_inf, sigma2_u80, cap_per_ep, tau2=TAU2_GATE):
    """Registered gate: smallest n in N_GRID with MDE <= 5 pp at tau2 and cap <= 15 GPU-h."""
    for n in N_GRID:
        cap = cap_for(K_inf * n * 4, cap_per_ep)
        if cap > CAP_CEILING:
            return None, "FAIL_COST"
        if mde(K_inf, var_task("main2x2", sigma2_u80, tau2, n)) <= MARGIN:
            return n, "PASS"
    return None, "FAIL_POWER"


MDE_CACHE: dict = {}


def gate_cached(K_inf, s2, cap_per_ep, tau2=TAU2_GATE):
    key = (K_inf, round(float(s2), 4), round(cap_per_ep, 6), round(float(tau2), 4))
    if key not in MDE_CACHE:
        MDE_CACHE[key] = gate_choose_n(K_inf, key[1], cap_per_ep, key[3])
    return MDE_CACHE[key]


def tau2_logit(k_inf, n_pilot=PILOT_N, target=-MARGIN):
    """Registered data-driven heterogeneity: between-task variance of the per-task probability change
    when one uniform logit shift gives a mean change of -5 pp on the informative tasks' pilot base rates
    (Jeffreys-smoothed (k + 0.5) / (n + 1))."""
    p = (np.asarray(k_inf, dtype=float) + 0.5) / (n_pilot + 1)
    b = lg(p)
    c = calibrate(np.array([target]), lambda c: np.array([np.mean(ex(b + c[0]) - p)]))[0]
    return float(np.var(ex(b + c) - p, ddof=1))


def simulate(seed, scen, delta_d, hetero, nrep, zibb, cap_per_ep, delta_t=-0.05, do_dossier=True):
    rng = np.random.default_rng([seed, zlib.crc32(f"{scen}|{delta_d:+.3f}|{hetero}".encode())])  # same draws for both prices
    blank = lambda: {"PRESENT": 0, "EQUIVALENT": 0, "PRESENT_AND_EQUIVALENT": 0, "INCONCLUSIVE": 0}
    tally = {"gate": {}, "decision_given_pass": blank(), "n_chosen": {},
             "gate_fixed_tau2": {}, "decision_given_pass_fixed_tau2": blank(), "n_chosen_fixed_tau2": {},
             "tau2_gate_values": [],
             "K_inf": [], "pooled_en": [], "realized_tau2": [], "dossier_fixed": {"PRESENT": 0, "EQUIVALENT": 0, "INCONCLUSIVE": 0}}
    frac = {"H1_uniform": 1.0, "H2_half": 0.5, "H3_quarter": 0.25}[hetero]
    for _ in range(nrep):
        p = scenario_draw(scen, rng, K_ALL, zibb)
        # dossier fixed design on all 18 tasks (conditional contrast ar-RTL - ar-LTR, n = 8), same truth model
        h_all = rng.random(K_ALL) < frac
        if not h_all.any():
            h_all[rng.integers(K_ALL)] = True
        live = p > 0
        base = lg(p)
        cT = calibrate(np.array([delta_t]), lambda c: np.array([np.mean(np.where(live, ex(base + c[0]) - p, 0.0))]))[0]
        def d_mean(c, idx):
            qa_l = np.where(live, ex(base + cT), 0.0)
            qe_r = np.where(live, ex(base + h_all * c[0]), 0.0)
            qa_r = np.where(live, ex(base + cT + h_all * c[0]), 0.0)
            d = 0.5 * ((qa_r - qa_l) + (qe_r - p))
            return np.array([np.mean(d[idx])]) if idx.any() else np.array([0.0])
        # pilot (English LTR only)
        k = rng.binomial(PILOT_N, p)
        pooled = k.sum() / (K_ALL * PILOT_N)
        inf = k >= PILOT_MIN_SUCCESSES
        K_inf = int(inf.sum())
        tally["K_inf"].append(K_inf); tally["pooled_en"].append(pooled)
        # dossier fixed design: calibrate on all live tasks of the 18
        if do_dossier:
            cD_all = calibrate(np.array([delta_d]), lambda c: d_mean(c, live)) if delta_d != 0 else np.array([0.0])
            qa_l = np.where(live, ex(base + cT), 0.0); qa_r = np.where(live, ex(base + cT + h_all * cD_all[0]), 0.0)
            dd = rng.binomial(8, qa_r) / 8 - rng.binomial(8, qa_l) / 8
            tally["dossier_fixed"][decide(dd)] += 1
        # registered gate (data-driven tau2) and, for comparison, the fixed tau2 = 0.0025 variant
        if not (FLOOR_BAND[0] <= pooled <= FLOOR_BAND[1]):
            g = gf = "FAIL_FLOOR"; n = nf = None
        elif K_inf < K_INF_MIN:
            g = gf = "FAIL_TASKS"; n = nf = None
        else:
            kk = k[inf]
            s2 = np.mean(kk * (PILOT_N - kk) / (PILOT_N * (PILOT_N - 1)))
            se = np.std(kk * (PILOT_N - kk) / (PILOT_N * (PILOT_N - 1)), ddof=1) / math.sqrt(K_inf)
            t2 = max(TAU2_GATE, tau2_logit(kk))
            tally["tau2_gate_values"].append(t2)
            n, g = gate_cached(K_inf, s2 + 0.8416 * se, cap_per_ep, t2)
            nf, gf = gate_cached(K_inf, s2 + 0.8416 * se, cap_per_ep, TAU2_GATE)
        tally["gate"][g] = tally["gate"].get(g, 0) + 1
        tally["gate_fixed_tau2"][gf] = tally["gate_fixed_tau2"].get(gf, 0) + 1
        if g != "PASS" and gf != "PASS":
            continue
        cD = calibrate(np.array([delta_d]), lambda c: d_mean(c, inf)) if delta_d != 0 else np.array([0.0])
        pe_l = p[inf]; b = base[inf]; h = h_all[inf]
        q = {"en_ltr": pe_l, "ar_ltr": ex(b + cT), "en_rtl": ex(b + h * cD[0]), "ar_rtl": ex(b + cT + h * cD[0])}
        true_d = 0.5 * ((q["ar_rtl"] - q["ar_ltr"]) + (q["en_rtl"] - q["en_ltr"]))
        tally["realized_tau2"].append(float(np.var(true_d, ddof=1)) if K_inf > 1 else 0.0)
        for verdict, nn, dkey, nkey in ((g, n, "decision_given_pass", "n_chosen"),
                                        (gf, nf, "decision_given_pass_fixed_tau2", "n_chosen_fixed_tau2")):
            if verdict != "PASS":
                continue
            tally[nkey][nn] = tally[nkey].get(nn, 0) + 1
            y = {c: rng.binomial(nn, v) / nn for c, v in q.items()}
            d_hat = 0.5 * ((y["ar_rtl"] - y["ar_ltr"]) + (y["en_rtl"] - y["en_ltr"]))
            tally[dkey][decide(d_hat, both=True)] += 1
    return tally


def decide(d, both=False):
    K = len(d)
    m = d.mean(); s = d.std(ddof=1)
    if s == 0:
        present = m != 0
        equiv = abs(m) < MARGIN
    else:
        se = s / math.sqrt(K)
        p = 2 * stats.t.sf(abs(m / se), K - 1)
        present = p <= ALPHA
        h = stats.t.ppf(1 - ALPHA, K - 1) * se
        equiv = (m - h > -MARGIN) and (m + h < MARGIN)
    if present and equiv:
        return "PRESENT_AND_EQUIVALENT" if both else "PRESENT"
    if present:
        return "PRESENT"
    if equiv:
        return "EQUIVALENT"
    return "INCONCLUSIVE"


def summarise(t, nrep):
    pass_n = t["gate"].get("PASS", 0)
    out = {"nrep": nrep, "gate": {k: round(v / nrep, 4) for k, v in sorted(t["gate"].items())},
           "p_gate_pass": round(pass_n / nrep, 4),
           "mean_K_inf": round(float(np.mean(t["K_inf"])), 2),
           "mean_pooled_english_success": round(float(np.mean(t["pooled_en"])), 4),
           "n_chosen_given_pass": {str(k): v for k, v in sorted(t["n_chosen"].items())},
           "decision_given_pass": {k: (round(v / pass_n, 4) if pass_n else None) for k, v in t["decision_given_pass"].items()},
           "decision_unconditional": {k: round(v / nrep, 4) for k, v in t["decision_given_pass"].items()},
           "mean_realized_tau2_given_any_pass": (round(float(np.mean(t["realized_tau2"])), 5) if t["realized_tau2"] else None),
           "tau2_gate_quartiles_when_computed": ([round(float(x), 5) for x in np.percentile(t["tau2_gate_values"], [25, 50, 75])]
                                                 if t["tau2_gate_values"] else None),
           "fixed_tau2_variant": {
               "gate": {k: round(v / nrep, 4) for k, v in sorted(t["gate_fixed_tau2"].items())},
               "p_gate_pass": round(t["gate_fixed_tau2"].get("PASS", 0) / nrep, 4),
               "n_chosen_given_pass": {str(k): v for k, v in sorted(t["n_chosen_fixed_tau2"].items())},
               "decision_given_pass": {k: (round(v / t["gate_fixed_tau2"]["PASS"], 4) if t["gate_fixed_tau2"].get("PASS") else None)
                                       for k, v in t["decision_given_pass_fixed_tau2"].items()}},
           "dossier_fixed_design_decision": ({k: round(v / nrep, 4) for k, v in t["dossier_fixed"].items()}
                                             if sum(t["dossier_fixed"].values()) else None)}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("a1", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--nrep", type=int, default=700)
    args = ap.parse_args()

    rows, cells, steps_9b = load_cells(args.a1)
    anchors = {
        "base_9B": cell_stats(cells, "9B", True), "base_4B": cell_stats(cells, "4B", True),
        "base_pooled": cell_stats(cells, None, True), "all_9B": cell_stats(cells, "9B", None),
        "all_pooled": cell_stats(cells, None, None),
        "registered_readings": S1A,
        "sigma2_from_D_w": {"pooled": S1A["D_w_pooled"] / 2, "9B": S1A["D_w_9B"] / 2, "4B": S1A["D_w_4B"] / 2},
        "zibb_fit_9B_all_cells": fit_zibb(cells, "9B"),
        "binarisation": "success = raw score >= 1.0 (fractional scores count as failures), as the kill-shot cell did",
    }
    zibb = anchors["zibb_fit_9B_all_cells"]
    sigmas = {"half_9B": round(S1A["D_w_9B"] / 4, 4), "9B": round(S1A["D_w_9B"] / 2, 4),
              "pooled": round(S1A["D_w_pooled"] / 2, 4)}
    grid = analytic_grid(sigmas)

    gpu9 = (0.002700 + 0.002702) / 2  # RESULTS.md 'What ran' table, A1-9B-S1 and A1-9B-S2
    cost, per_ep, cap_per_ep = cost_model(steps_9b, gpu9)
    designs = {}
    for label, episodes in {"dossier_864_pixels_and_a11y": None,
                            "pilot_1a_144_english_plus_54_smoke": None,
                            "main_2x2_K18_n16": 18 * 16 * 4, "main_2x2_K18_n24": 18 * 24 * 4,
                            "main_2x2_K16_n16": 16 * 16 * 4, "main_2x2_K18_n12": 18 * 12 * 4}.items():
        if label == "dossier_864_pixels_and_a11y":
            d = {"episodes": 864, "note": "432 pixels + 432 a11y at 1.5x per step (serving probe v2 ratio)"}
            for k in ("low", "central", "high"):
                d[k] = round((432 + 1.5 * 432) * per_ep[k], 2)
            d["cap"] = round((432 + 1.5 * 432) * cap_per_ep + STARTUP_GPU_H, 2)
        elif label.startswith("pilot"):
            smoke_steps = 54 * 3
            d = {"episodes": 144, "smoke_episodes": 54, "smoke_step_cap": 3}
            step_c = {"low": per_ep["low"] / MEAN_STEPS["low"], "central": per_ep["central"] / MEAN_STEPS["central"],
                      "high": per_ep["high"] / MEAN_STEPS["high"]}
            for k in ("low", "central", "high"):
                d[k] = round(144 * per_ep[k] + smoke_steps * step_c[k], 3)
            d["cap"] = round(144 * cap_per_ep + smoke_steps * step_c["high"] * CAP_MARGIN + STARTUP_GPU_H, 3)
        else:
            d = {"episodes": episodes}
            for k in ("low", "central", "high"):
                d[k] = round(episodes * per_ep[k], 2)
            d["cap"] = round(cap_for(episodes, cap_per_ep), 2)
        designs[label] = d
    cost["designs"] = designs

    # gate evaluated on the transported S1a inputs (what the gate says before any Relay data exists)
    prices = {"measured_central_x1.5": per_ep["central"] * CAP_MARGIN * ARABIC_STEPS_ALLOWANCE, "high_x1.2": cap_per_ep}
    transported = {}
    for price_name, cpe in prices.items():
      for s_name, s2 in sigmas.items():
          for K in (18, 16, 14, 12):
              n, verdict = gate_choose_n(K, s2, cpe)
              best_n_under_cap = max([m for m in N_GRID if cap_for(K * m * 4, cpe) <= CAP_CEILING], default=None)
              transported[f"{price_name}|{s_name}_K{K}"] = {
                  "sigma2": s2, "K_inf": K, "verdict": verdict, "n": n,
                  "largest_n_under_15_gpu_h": best_n_under_cap,
                  "mde_pp_at_that_n": (round(100 * mde(K, var_task("main2x2", s2, TAU2_GATE, best_n_under_cap)), 2) if best_n_under_cap else None),
                  "mde_pp_at_that_n_tau2_0.005": (round(100 * mde(K, var_task("main2x2", s2, 0.005, best_n_under_cap)), 2) if best_n_under_cap else None)}
    # the largest sigma2 at which the gate can pass for each K under the cap (bisection on sigma2)
    pass_region = {}
    for price_name, cpe in prices.items():
        for K in (18, 17, 16, 15, 14, 13, 12):
            n_max = max([m for m in N_GRID if cap_for(K * m * 4, cpe) <= CAP_CEILING], default=None)
            if n_max is None:
                pass_region[f"{price_name}|K{K}"] = None
                continue
            f = lambda s2: mde(K, var_task("main2x2", s2, TAU2_GATE, n_max)) - MARGIN
            s2max = float(optimize.brentq(f, 1e-6, 0.25)) if f(1e-6) < 0 < f(0.25) else (0.0 if f(1e-6) >= 0 else 0.25)
            pass_region[f"{price_name}|K{K}"] = {"n_max_under_cap": n_max, "max_sigma2_for_pass": round(s2max, 4),
                                                 "mde_pp_at_sigma2_0": round(100 * mde(K, var_task("main2x2", 0.0, TAU2_GATE, n_max)), 2)}

    tost = {}
    for K in (18, 16, 14):
        for n in (12, 16, 24):
            for s_name, s2 in sigmas.items():
                tost[f"K{K}_n{n}_{s_name}"] = round(tost_power_at_zero(K, var_task("main2x2", s2, TAU2_GATE, n)), 3)

    mc = {}
    for price_name, cpe in prices.items():
     for scen in ("A_s1a_transport", "B_mid_range", "C_near_floor", "D_near_deterministic"):
        if price_name == "high_x1.2" and scen != "D_near_deterministic":
            continue  # the gate already fails at the central price in A-C; the high price only matters where it can pass
        for hetero in ("H1_uniform", "H2_half", "H3_quarter"):
            for delta_d in (0.0, -0.03, -0.05, -0.08):
                merged = None
                per_seed = {}
                for seed in SEEDS:
                    t = simulate(seed, scen, delta_d, hetero, args.nrep, zibb, cpe, do_dossier=(price_name != "high_x1.2"))
                    per_seed[seed] = summarise(t, args.nrep)
                    if merged is None:
                        merged = t
                    else:
                        for k in ("gate", "n_chosen", "gate_fixed_tau2", "n_chosen_fixed_tau2"):
                            for kk, vv in t[k].items():
                                merged[k][kk] = merged[k].get(kk, 0) + vv
                        for k in ("decision_given_pass", "decision_given_pass_fixed_tau2", "dossier_fixed"):
                            for kk, vv in t[k].items():
                                merged[k][kk] += vv
                        for k in ("K_inf", "pooled_en", "realized_tau2", "tau2_gate_values"):
                            merged[k].extend(t[k])
                key = f"{price_name}|{scen}|{hetero}|delta_D={delta_d:+.2f}"
                mc[key] = {"pooled_over_seeds": summarise(merged, args.nrep * len(SEEDS)),
                           "p_gate_pass_by_seed": {str(s): per_seed[s]["p_gate_pass"] for s in SEEDS}}
                print(key, mc[key]["pooled_over_seeds"]["p_gate_pass"], mc[key]["pooled_over_seeds"]["decision_given_pass"], flush=True)

    out = {
        "script": "program/proposals/evidence/2026-10-10-s2-arabic-cua-locale/compute/power-gate.py",
        "inputs": {"a1_jsonl": str(args.a1), "a1_sha256": sha256(args.a1), "a1_rows": len(rows)},
        "provenance": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__,
                       "argv": sys.argv[1:], "seeds": SEEDS, "nrep_per_seed_per_cell": args.nrep},
        "registered_constants": {"alpha": ALPHA, "power": POWER, "margin_pp": 100 * MARGIN, "tau2_gate": TAU2_GATE,
                                 "n_grid": N_GRID, "pilot_n": PILOT_N, "pilot_min_successes": PILOT_MIN_SUCCESSES,
                                 "K_inf_min": K_INF_MIN, "floor_band": FLOOR_BAND, "cap_ceiling_gpu_h": CAP_CEILING,
                                 "stage_1b_cap_price": "1.2 x 1.25 x pilot-measured English GPU-h per episode (simulated at the S1a-realized central price; the transported high price is the sensitivity)",
                                 "tau2_used_by_gate": "max(0.0025, tau2_logit): the between-task variance of the probability change when one uniform logit shift gives a -5 pp mean change on the informative tasks' Jeffreys-smoothed pilot base rates; the fixed 0.0025 variant is reported for comparison",
                                 "sigma2_used_by_gate": "one-sided 80% upper bound of the pilot's mean unbiased within-task variance over informative tasks"},
        "A_anchors": anchors,
        "B_analytic_mde_grid": grid,
        "B_tost_power_at_zero_main2x2_tau2_gate": tost,
        "C_cost_model": cost,
        "gate_on_transported_s1a_inputs": transported,
        "gate_pass_region_under_15_gpu_h": pass_region,
        "D_monte_carlo": mc,
        "notes": [
            "sigma2 is the mean within-task-cell Bernoulli variance E[p(1-p)] = D_w / 2; on Relay the replicates are cosmetic seeds x reruns, so seed variance adds to it unless it is shared across locales (shared variance cancels in the paired contrast; the simulation does not credit that, so it is conservative).",
            "tau2 is the between-task variance of the true per-task effect on the probability scale. 0.0025 is a 5 pp mean effect carried entirely by half the tasks (in probability). Logit-scale effect models produce more: see mean_realized_tau2_given_any_pass and tau2_gate_quartiles_when_computed; that is why the registered gate uses max(0.0025, tau2_logit).",
            "Every base-rate scenario is assumed. Scenario A transports S1a's 9B cells (OSWorld VM tasks, 15 steps) to Relay (web app, up to 40 steps); B is mid-range; C is near the floor (frontier models passed 3 of 24 Relay pixel runs, 14 of the 19 blocked runs by connection failures).",
            "The dossier comparison simulates its fixed design (ar-RTL minus ar-LTR, n = 8 per cell, all 18 tasks, no gate) on the same truth draws; its 'PRESENT' rate under delta_D = 0 is its false-positive rate.",
        ],
    }
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
