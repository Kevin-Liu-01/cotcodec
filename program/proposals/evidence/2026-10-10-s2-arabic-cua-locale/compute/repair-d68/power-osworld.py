#!/usr/bin/env python3
"""S2 repair under D68: the OSWorld 2x2, sized from S1a's records under the registered estimator.

What it does (CPU only, deterministic given the seeds):

1. Task screen. From S1a's 113-task pool (``a1.jsonl``, ``plan-a0a.json``) it keeps the
   applications whose interfaces exist in Arabic and whose layout direction can be switched
   separately (LibreOffice Calc, Impress, Writer; Thunderbird; GIMP), and classes every task:
   ``excluded_coordinate_setup`` (a setup step clicks at screen coordinates, which a mirrored
   layout would send to another control), ``conditional_config_checker`` (the checker reads an
   application configuration file, so the task enters only if Phase 0's config-invariance
   probe passes), or ``strict``. A task is informative if Qwen3.5-9B succeeded in at least 1 of
   its 8 S1a episodes (2 harnesses x 2 sessions x 2 reruns). Selection uses S1a's episodes
   only; Phase 1 re-measures English, so selection cannot bias the paired contrasts.
2. Propensity model. A beta-binomial prior over (task, harness) cells is fitted by maximum
   marginal likelihood on every candidate cell (4 trials per cell, zeros included), checked
   against S1a's observed k-histogram and rerun discordance, and each selected cell's success
   probability is drawn from its posterior Beta(a + k, b + 4 - k).
3. Phase 1 simulation under the registered estimator: 4 cells (en, ar-LTR, en-RTL, ar-RTL) x
   K tasks x n episodes per task-cell split equally over the two certified harnesses
   (H-OSW-fixed, H-GA), one serving session (a common logit shift u ~ N(0, 0.3^2) applied to
   every cell). D_t = ((y_arR - y_arL) + (y_enR - y_en)) / 2; paired t on the K task-level D_t
   (df K - 1): PRESENT if two-sided p <= 0.05 (PRESENT_FRAGILE if the sign-flip test, 2,000
   seeded sign vectors, disagrees); SMALL if the 90% t interval lies inside (-5, +5) pp;
   otherwise INCONCLUSIVE. Effect structures: uniform logit shift, proportional reduction,
   concentrated (half or a quarter of the tasks carry a proportional reduction), flip (a
   random subset of tasks breaks completely), and a heterogeneous-sign perturbation. The
   targets are superpopulation means over the posterior draws (calibrated by bisection on a
   fixed calibration bank); T (the Arabic-text main effect) is -5 pp with the same structure.
   A secondary finite-task test (a stratified randomization test of the sharp null of no
   direction effect on any episode distribution) is reported beside it.
4. Cost with the Q2 design study's rule (realized slot occupancy at V = 20, cap per job
   ceil(3 + L/60 + (N s / V + drain) x 1.2 x 1.05 / 60) minutes, a 6-minute overlay reserve).
5. Analytic cross-check: exact noncentral-t MDE for the 2x2 main effect.

Usage:
    python power-osworld.py <a1.jsonl> <plan-a0a.json> <out.json> [--nrep 1000]
Seeds: [42, 43, 44]; every stream is numpy PCG64 seeded [seed, stream id].
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import scipy
from scipy import optimize, special, stats

SEEDS = (42, 43, 44)
APPS = ("libreoffice_calc", "libreoffice_impress", "libreoffice_writer", "thunderbird", "gimp")
LO_APPS = ("libreoffice_calc", "libreoffice_impress", "libreoffice_writer")
CONFIG_FILES = ("registrymodifications.xcu", "prefs.js", "xulstore.json", "gimprc", "vlcrc")
CELLS = ("en", "arL", "enR", "arR")  # (text, layout): (en, LTR), (ar, LTR), (en, RTL), (ar, RTL)
A_TEXT = np.array([0, 1, 0, 1])  # Arabic interface text
B_DIR = np.array([0, 0, 1, 1])  # mirrored layout
HARNESSES = ("H-OSW-fixed", "H-GA")
MARGIN = 0.05
ALPHA = 0.05
POWER = 0.80
SESSION_SD = 0.30  # logit; S1a's 9B session shift was +5.5 pp at ~30% success
N_FLIPS = 2000
CAL_BANK = 1000
N_GRID = (8, 12, 16)  # v0 also ran n = 4 (power-osworld-v0-partial.json)
BREAK_DT = -0.25  # a "large drop": D_t at most -0.25 (v1 used -0.5; power-osworld-v1-break050.json)
N_MAX_BY_K = ((35, 16), (43, 12))  # registered n: 16 if K <= 35, else 12 (caps <= 8 GPU-h at the high slot price)
TARGETS_ALT = (-0.03, -0.05, -0.08)
T_TARGET = -0.05

# Q2 design study cost rule (stage0/q2-design-study 79096f8, harness/q2_design/cost.py)
V = 20
USR1_LEAD_MIN = 3
OVERLAY_MIN = 6
DR4_FACTOR = 1.2
REQUEUE_FACTOR = 1.05
STARTUP_S = 113.18587  # max 9B start-up L (cost-model.json startup_s_max)
DRAIN_S = 104.60958  # max 9B drain (cost-model.json by_size.9B.drain_s)
BUDGET_GPU_H = 8.0


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expit(x):
    return special.expit(x)


def logit(p):
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return np.log(p) - np.log1p(-p)


# ----------------------------------------------------------------------------------------
# 1. Task screen


def task_screen(a1: Path, plan_path: Path):
    plan = json.loads(plan_path.read_text())
    dom = plan["task_domains"]
    flagged = set(plan["flagged_tasks"])
    base = set(plan["base"])
    by = defaultdict(list)
    for line in a1.open():
        r = json.loads(line)
        by[r["task_id"]].append(r)
    rows = []
    for t, rs in sorted(by.items()):
        d = dom[t]
        if d not in APPS:
            continue
        inputs, coord, setup_types = set(), False, set()
        for r in rs:
            inputs.update(r["checker_input_sha256"].keys())
            for s in r["setup"]["config_steps"]:
                setup_types.add(s["type"])
                argv = " ".join(s.get("argv") or [])
                if s["type"] in ("execute", "command") and "pyautogui.click" in argv:
                    coord = True
        cfg = sorted(p for p in inputs if any(c in p for c in CONFIG_FILES))
        r9 = [r for r in rs if r["size"] == "9B"]
        r4 = [r for r in rs if r["size"] == "4B"]
        k_h = {h: int(sum(1 for r in r9 if r["harness"] == h and r["score"] == 1.0)) for h in HARNESSES}
        n_h = {h: int(sum(1 for r in r9 if r["harness"] == h)) for h in HARNESSES}
        if coord:
            cls = "excluded_coordinate_setup"
        elif cfg:
            cls = "conditional_config_checker"
        else:
            cls = "strict"
        rows.append(
            {
                "task_id": t,
                "domain": d,
                "class": cls,
                "config_checker_inputs": cfg,
                "checker_inputs": sorted(inputs),
                "setup_step_types": sorted(setup_types),
                "flagged_s1a": t in flagged,
                "s1a_base": t in base,
                "k9": int(sum(k_h.values())),
                "n9": int(sum(n_h.values())),
                "k9_by_harness": k_h,
                "n9_by_harness": n_h,
                "k4": int(sum(1 for r in r4 if r["score"] == 1.0)),
                "n4": len(r4),
                "fractional_9b": int(sum(1 for r in r9 if 0 < (r["score"] or 0) < 1)),
                "slot9_mean_s": float(np.mean([r["host"]["slot_occupancy_s"] for r in r9])),
                "steps9_mean": float(np.mean([r["steps"] for r in r9])),
                "slot9_cap_episodes_s": [float(r["host"]["slot_occupancy_s"]) for r in r9 if r["steps"] >= 15],
            }
        )
    return rows


def task_sets(rows):
    inf = lambda r: r["k9"] >= 1
    sets = {
        "LO_strict": [r for r in rows if r["domain"] in LO_APPS and r["class"] == "strict" and inf(r)],
        "LO_TB_strict": [r for r in rows if r["domain"] != "gimp" and r["class"] == "strict" and inf(r)],
        "LO_TB": [r for r in rows if r["domain"] != "gimp" and r["class"] != "excluded_coordinate_setup" and inf(r)],
        "LO_TB_GIMP": [r for r in rows if r["class"] != "excluded_coordinate_setup" and inf(r)],
    }
    return sets


# ----------------------------------------------------------------------------------------
# 2. Beta-binomial prior over (task, harness) cells


def fit_betabinom(ks, n):
    ks = np.asarray(ks)

    def nll(theta):
        a, b = np.exp(theta)
        return -float(np.sum(stats.betabinom.logpmf(ks, n, a, b)))

    best = None
    for a0 in (0.1, 0.3, 1.0):
        for b0 in (0.1, 0.3, 1.0):
            res = optimize.minimize(nll, np.log([a0, b0]), method="Nelder-Mead", options={"xatol": 1e-8, "fatol": 1e-10, "maxiter": 4000})
            if best is None or res.fun < best.fun:
                best = res
    a, b = np.exp(best.x)
    return float(a), float(b), float(best.fun)


def validate_prior(a, b, ks_obs, n, rng, nsim=20000):
    p = rng.beta(a, b, size=nsim)
    k = rng.binomial(n, p)
    hist_sim = np.bincount(k, minlength=n + 1) / nsim
    hist_obs = np.bincount(np.asarray(ks_obs), minlength=n + 1) / len(ks_obs)
    # pairwise discordance among the n episodes of a cell: k(n-k) / C(n,2)
    pairs = n * (n - 1) / 2
    disc_obs = float(np.mean([kk * (n - kk) / pairs for kk in ks_obs]))
    disc_sim = float(np.mean(k * (n - k) / pairs))
    return {
        "k_hist_observed": [round(x, 4) for x in hist_obs.tolist()],
        "k_hist_model": [round(x, 4) for x in hist_sim.tolist()],
        "pair_discordance_observed": round(disc_obs, 4),
        "pair_discordance_model": round(disc_sim, 4),
        "mean_success_observed": round(float(np.mean(ks_obs)) / n, 4),
        "mean_success_model": round(float(np.mean(k)) / n, 4),
    }


# ----------------------------------------------------------------------------------------
# 3. Effect structures


def cell_probs(p0, struct, theta_d, theta_t, carriers_d, carriers_t, eps_d=None):
    """p0: (R, K, H) base probabilities (English, LTR). Returns (R, K, H, 4) cell probabilities."""
    a = A_TEXT[None, None, None, :]
    b = B_DIR[None, None, None, :]
    P = p0[..., None]
    if struct == "logit":
        return expit(logit(P) + theta_t * a + theta_d * b)
    if struct == "perturb":
        # direction effect: task-specific logit perturbation eps_t ~ N(theta_d, 1); text: uniform logit shift
        e = eps_d[:, :, None, None]
        return expit(logit(P) + theta_t * a + e * b)
    if struct in ("prop", "conc50", "conc25", "flip"):
        zd = carriers_d[:, :, None, None]
        zt = carriers_t[:, :, None, None]
        return P * (1 - theta_t * a * zt) * (1 - theta_d * b * zd)
    raise ValueError(struct)


STRUCT_FRAC = {"prop": 1.0, "conc50": 0.5, "conc25": 0.25}


def draw_carriers(rng, struct, R, K, theta_frac):
    if struct in STRUCT_FRAC:
        f = STRUCT_FRAC[struct]
    elif struct == "flip":
        f = theta_frac
    else:
        return np.ones((R, K))
    return (rng.random((R, K)) < f).astype(float)


def true_effects(pc):
    """Mean over harnesses then the 2x2 contrasts per task: returns D_t, T_t (R, K)."""
    m = pc.mean(axis=2)  # (R, K, 4)
    en, arL, enR, arR = m[..., 0], m[..., 1], m[..., 2], m[..., 3]
    D = ((arR - arL) + (enR - en)) / 2
    T = ((arL - en) + (arR - enR)) / 2
    return D, T


def calibrate(struct, target_d, target_t, bank_p0, rng_seed):
    """Find the effect parameters so the bank's expected mean D and T hit the targets.

    logit: uniform logit shifts (theta_d, theta_t); perturb: direction is a task-specific logit
    perturbation eps_t ~ N(theta_d, 1), text a uniform logit shift theta_t; prop/conc50/conc25:
    proportional reductions (theta_d, theta_t) in [0, 1] on carrier tasks (all, half, a quarter);
    flip: carrier fractions (frac_d, frac_t) with a complete break (reduction 1).
    """
    R, K, H = bank_p0.shape
    rng = np.random.Generator(np.random.PCG64([rng_seed, 900]))
    u_d = rng.random((R, K))
    u_t = rng.random((R, K))
    z_eps = rng.standard_normal((R, K))

    L0 = logit(bank_p0)[..., None]
    P0 = bank_p0[..., None]
    a = A_TEXT[None, None, None, :]
    b = B_DIR[None, None, None, :]

    def effects(pd, pt):
        if struct == "flip":
            zd = (u_d < pd).astype(float)[:, :, None, None]
            zt = (u_t < pt).astype(float)[:, :, None, None]
            pc = P0 * (1 - a * zt) * (1 - b * zd)
        elif struct in STRUCT_FRAC:
            f = STRUCT_FRAC[struct]
            zd = (u_d < f).astype(float)[:, :, None, None]
            zt = (u_t < f).astype(float)[:, :, None, None]
            pc = P0 * (1 - pt * a * zt) * (1 - pd * b * zd)
        elif struct == "perturb":
            pc = expit(L0 + pt * a + (pd + z_eps)[:, :, None, None] * b)
        else:
            pc = expit(L0 + pt * a + pd * b)
        D, T = true_effects(pc)
        return float(D.mean()), float(T.mean())

    bounded = struct in STRUCT_FRAC or struct == "flip"
    lo, hi = (0.0, 1.0) if bounded else (-8.0, 8.0)

    def solve(fn, target):
        flo, fhi = fn(lo) - target, fn(hi) - target
        if flo * fhi > 0:
            return None
        a, b = lo, hi
        x0, x1 = lo, hi
        for _ in range(32):
            mid = (x0 + x1) / 2
            fm = fn(mid) - target
            if flo * fm <= 0:
                x1 = mid
            else:
                x0, flo = mid, fm
        return (x0 + x1) / 2

    pd, pt = 0.0, 0.0
    for _ in range(3):
        pt = 0.0 if target_t == 0 else solve(lambda x: effects(pd, x)[1], target_t)
        if pt is None:
            return None
        if target_d == 0 and struct != "perturb":
            pd = 0.0
        else:
            pd = solve(lambda x: effects(x, pt)[0], target_d)
            if pd is None:
                return None
    D, T = effects(pd, pt)
    key_d, key_t = ("frac_d", "frac_t") if struct == "flip" else ("theta_d", "theta_t")
    out = {key_d: pd, key_t: pt, "bank_mean_D": D, "bank_mean_T": T}
    if struct == "flip":
        out.update(theta_d=1.0, theta_t=1.0)
    return out


# ----------------------------------------------------------------------------------------
# 4. Simulation of Phase 1 under the registered estimator


def decide(D_t, flips, en_mean):
    """Registered decision on task-level D_t (R, K); en_mean is the en cell's mean success (R,).

    SMALL carries the rare-break qualifier: with B tasks at D_t <= -0.25 (a large drop), U is the exact one-sided
    95% upper bound on the share of broken tasks (Clopper-Pearson); if U x en_mean >= 5 pp, a
    mirror effect of 5 pp made of rare complete breaks is not excluded and the label is
    SMALL_RARE_BREAKS_NOT_EXCLUDED, not SMALL. (v1 counted D_t <= -0.5 and let unqualified SMALL through
    in up to 0.087 of replicates at a true -5 pp made of complete breaks at K = 43.)
    """
    R, K = D_t.shape
    est = D_t.mean(axis=1)
    sd = D_t.std(axis=1, ddof=1)
    se = sd / math.sqrt(K)
    df = K - 1
    with np.errstate(divide="ignore", invalid="ignore"):
        tstat = np.where(se > 0, est / se, np.where(est == 0, 0.0, np.inf * np.sign(est)))
    p = 2 * stats.t.sf(np.abs(tstat), df)
    q95 = stats.t.ppf(0.975, df)
    q90 = stats.t.ppf(0.95, df)
    lo90, hi90 = est - q90 * se, est + q90 * se
    lo95, hi95 = est - q95 * se, est + q95 * se
    present = p <= ALPHA
    small = (lo90 > -MARGIN) & (hi90 < MARGIN)
    # sign-flip: statistic = |mean|; p = share of flips with |mean| >= observed (observed included)
    obs = np.abs(est)
    flipped = np.abs(D_t @ flips.T) / K  # (R, N_FLIPS)
    p_sf = (1 + np.sum(flipped >= obs[:, None] - 1e-12, axis=1)) / (1 + flips.shape[0])
    fragile = present & (p_sf > ALPHA)
    B = (D_t <= BREAK_DT + 1e-12).sum(axis=1)
    U = np.where(B < K, stats.beta.ppf(0.95, B + 1, np.maximum(K - B, 1)), 1.0)
    implied = U * en_mean
    small_unq = small & (implied < MARGIN)
    return {
        "breaks": B,
        "break_upper": U,
        "small_unqualified": small_unq,
        "small_qualified": small & ~small_unq,
        "est": est,
        "p": p,
        "p_signflip": p_sf,
        "present": present,
        "present_harm": present & (est < 0),
        "present_benefit": present & (est > 0),
        "fragile": fragile,
        "small": small,
        "inconclusive": ~present & ~small,
        "lo95": lo95,
        "hi95": hi95,
    }


def sharp_null_test(k, n_h):
    """Stratified randomization test of 'no direction effect on any episode distribution'.

    k: (R, K, H, 4) success counts with n_h episodes per (task, harness, cell). Within each
    (task, harness, text level) stratum the layout labels are exchangeable under the sharp
    null; S = sum (k_RTL - k_LTR); exact hypergeometric mean 0 and variance, normal reference.
    """
    out = []
    S = np.zeros(k.shape[0])
    var = np.zeros(k.shape[0])
    for ltr, rtl in ((0, 2), (1, 3)):
        m = k[..., ltr] + k[..., rtl]  # successes in the stratum (2 n_h episodes)
        N = 2 * n_h
        # k_rtl ~ Hypergeometric(N, m, n_h): var = n_h * (m/N) * (1 - m/N) * (N - n_h)/(N - 1)
        v = n_h * (m / N) * (1 - m / N) * (N - n_h) / (N - 1)
        S += (k[..., rtl] - k[..., ltr]).sum(axis=(1, 2))
        var += (4 * v).sum(axis=(1, 2))
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.where(var > 0, S / np.sqrt(var), 0.0)
    return 2 * stats.norm.sf(np.abs(z)) <= ALPHA


def flip_matrix(seed, K):
    """Seeded sign vectors for the sign-flip test (N_FLIPS x K, entries -1 or +1)."""
    return (np.random.Generator(np.random.PCG64([seed, 3, K])).integers(0, 2, size=(N_FLIPS, K)) * 2 - 1).astype(float)


def simulate_cell(seed, post_a, post_b, struct, cal, n, nrep, flips):
    K, H = post_a.shape
    rng = np.random.Generator(np.random.PCG64([seed, 1]))
    p0 = rng.beta(np.broadcast_to(post_a, (nrep, K, H)), np.broadcast_to(post_b, (nrep, K, H)))
    u = rng.normal(0.0, SESSION_SD, size=(nrep, 1, 1))
    p0s = expit(logit(p0) + u)
    if struct == "flip":
        cd = (rng.random((nrep, K)) < cal["frac_d"]).astype(float)
        ct = (rng.random((nrep, K)) < cal["frac_t"]).astype(float)
        pc = cell_probs(p0s, "flip", 1.0, 1.0, cd, ct)
    elif struct in STRUCT_FRAC:
        f = STRUCT_FRAC[struct]
        cd = (rng.random((nrep, K)) < f).astype(float)
        ct = (rng.random((nrep, K)) < f).astype(float)
        pc = cell_probs(p0s, struct, cal["theta_d"], cal["theta_t"], cd, ct)
    elif struct == "perturb":
        eps = cal["theta_d"] + rng.standard_normal((nrep, K))
        pc = cell_probs(p0s, "perturb", 0.0, cal["theta_t"], None, None, eps_d=eps)
    else:
        pc = cell_probs(p0s, "logit", cal["theta_d"], cal["theta_t"], None, None)
    n_h = n // 2
    k = rng.binomial(n_h, pc)  # (R, K, H, 4)
    y = k.sum(axis=2) / n  # (R, K, 4)
    D_t = ((y[..., 3] - y[..., 1]) + (y[..., 2] - y[..., 0])) / 2
    trueD, _ = true_effects(pc)
    dec = decide(D_t, flips, y[..., 0].mean(axis=1))
    sharp = sharp_null_test(k, n_h)
    target = cal["target_d"]
    finite = trueD.mean(axis=1)
    return {
        "present_harm": float(dec["present_harm"].mean()),
        "present_benefit": float(dec["present_benefit"].mean()),
        "present_fragile": float(dec["fragile"].mean()),
        "small": float(dec["small"].mean()),
        "small_unqualified": float(dec["small_unqualified"].mean()),
        "small_rare_breaks_not_excluded": float(dec["small_qualified"].mean()),
        "mean_breaks": float(dec["breaks"].mean()),
        "mean_break_upper": float(dec["break_upper"].mean()),
        "present_and_small": float((dec["present"] & dec["small"]).mean()),
        "inconclusive": float(dec["inconclusive"].mean()),
        "decisive": float((dec["present"] | dec["small"]).mean()),
        "cover95_target": float(((dec["lo95"] <= target) & (target <= dec["hi95"])).mean()),
        "cover95_finite": float(((dec["lo95"] <= finite) & (finite <= dec["hi95"])).mean()),
        "mean_est": float(dec["est"].mean()),
        "mean_finite_true_D": float(finite.mean()),
        "sd_finite_true_D": float(finite.std()),
        "sharp_null_reject": float(sharp.mean()),
        "nrep": int(nrep),
    }


# ----------------------------------------------------------------------------------------
# 5. Cost and 6. analytic MDE


def cost(K, n, slot_s):
    N = 4 * K * n
    physical_h = (STARTUP_S + N * slot_s / V + DRAIN_S) / 3600
    cap_min = math.ceil(USR1_LEAD_MIN + STARTUP_S / 60 + (N * slot_s / V + DRAIN_S) * DR4_FACTOR * REQUEUE_FACTOR / 60)
    total_cap_h = (cap_min + OVERLAY_MIN) / 60
    return {
        "episodes": N,
        "physical_gpu_h": round(physical_h, 3),
        "job_cap_min": cap_min,
        "registered_caps_gpu_h_incl_overlay": round(total_cap_h, 3),
        "under_8_gpu_h": total_cap_h <= BUDGET_GPU_H,
        "wall_h_one_job": round(N * slot_s / V / 3600, 2),
    }


def power_t(delta, K, v, alpha=ALPHA):
    df = K - 1
    se = math.sqrt(v / K)
    crit = stats.t.ppf(1 - alpha / 2, df)
    nc = delta / se
    val = float(stats.nct.sf(crit, df, nc) + stats.nct.cdf(-crit, df, nc))
    if not math.isfinite(val):  # scipy's nct is unstable far in the tail; power there is ~1
        val = 1.0
    return val


def mde(K, v):
    if v <= 0:
        return 0.0
    f = lambda d: power_t(d, K, v) - POWER
    return float(optimize.brentq(f, 1e-9, 8 * math.sqrt(v / K), xtol=1e-9))


# ----------------------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("a1", type=Path)
    ap.add_argument("plan", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--nrep", type=int, default=1000)
    ap.add_argument("--sets", default="LO_strict,LO_TB_strict,LO_TB,LO_TB_GIMP")
    args = ap.parse_args()

    rows = task_screen(args.a1, args.plan)
    sets = task_sets(rows)
    out = {
        "schema": "s2-repair-d68-power-osworld-v1",
        "inputs": {str(args.a1): sha256(args.a1), str(args.plan): sha256(args.plan)},
        "script_sha256": sha256(Path(__file__)),
        "provenance": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__, "argv": sys.argv[1:]},
        "seeds": list(SEEDS),
        "constants": {
            "session_sd_logit": SESSION_SD,
            "margin_pp": MARGIN * 100,
            "alpha": ALPHA,
            "n_signflips": N_FLIPS,
            "V": V,
            "startup_s": STARTUP_S,
            "drain_s": DRAIN_S,
            "cap_rule": "ceil(3 + L/60 + (N*slot/V + drain)*1.2*1.05/60) min per job, plus a 6 min overlay reserve (Q2 design study)",
        },
    }

    # task screen summary
    cls_counts = Counter((r["domain"], r["class"]) for r in rows)
    out["task_screen"] = {
        "pool_tasks_in_apps": len(rows),
        "by_domain_and_class": {f"{d}|{c}": v for (d, c), v in sorted(cls_counts.items())},
        "excluded_coordinate_setup": [r["task_id"] for r in rows if r["class"] == "excluded_coordinate_setup"],
        "conditional_config_checker": {r["task_id"]: r["config_checker_inputs"] for r in rows if r["class"] == "conditional_config_checker"},
        "rows": rows,
        "sets": {
            name: {
                "K": len(s),
                "by_domain": dict(Counter(r["domain"] for r in s)),
                "task_ids": [r["task_id"] for r in s],
                "k9_hist_of_8": dict(sorted(Counter(r["k9"] for r in s).items())),
                "mean_9b_success": round(float(np.mean([r["k9"] / r["n9"] for r in s])), 4),
                "mean_4b_success": round(float(np.mean([r["k4"] / r["n4"] for r in s])), 4),
                "s1a_base_members": int(sum(r["s1a_base"] for r in s)),
                "s1a_flagged": int(sum(r["flagged_s1a"] for r in s)),
            }
            for name, s in sets.items()
        },
    }

    # prior: every candidate (task, harness) cell with 4 trials (zeros included; coordinate-setup tasks excluded)
    cand = [r for r in rows if r["class"] != "excluded_coordinate_setup"]
    ks = [r["k9_by_harness"][h] for r in cand for h in HARNESSES]
    assert all(r["n9_by_harness"][h] == 4 for r in cand for h in HARNESSES)
    a, b, nll = fit_betabinom(ks, 4)
    val = validate_prior(a, b, ks, 4, np.random.Generator(np.random.PCG64([42, 7])))
    # selected cells only (descriptive; the model draws them from their posteriors)
    out["prior"] = {"family": "beta-binomial over (task, harness) cells, 4 trials, 9B", "a": a, "b": b, "nll": nll, "cells": len(ks), "validation_all_candidate_cells": val}

    # per-episode variance on the selected sets under the posterior mean (descriptive input to the analytic MDE)
    sim = {}
    structs_alt = ("logit", "prop", "conc50", "conc25", "flip")
    scenarios = [("null_logit", "logit", 0.0), ("null_perturb", "perturb", 0.0)]
    scenarios += [(f"{st}_{int(-t*100)}pp", st, t) for st in structs_alt for t in TARGETS_ALT]
    analytic = {}
    for name in args.sets.split(","):
        s = sets[name]
        K = len(s)
        post_a = np.array([[a + r["k9_by_harness"][h] for h in HARNESSES] for r in s])
        post_b = np.array([[b + 4 - r["k9_by_harness"][h] for h in HARNESSES] for r in s])
        pm = post_a / (post_a + post_b)
        sigma2_episode = float(np.mean(pm * (1 - pm)))
        # calibration bank (seed 42 stream 800): CAL_BANK posterior draws with the session shift
        rngc = np.random.Generator(np.random.PCG64([42, 800]))
        bank = rngc.beta(np.broadcast_to(post_a, (CAL_BANK, K, 2)), np.broadcast_to(post_b, (CAL_BANK, K, 2)))
        bank = expit(logit(bank) + rngc.normal(0, SESSION_SD, size=(CAL_BANK, 1, 1)))
        cal_by = {}
        for scen, st, td in scenarios:
            c = calibrate(st, td, T_TARGET, bank, 42)
            if c is None:
                cal_by[scen] = None
                continue
            c["target_d"] = td
            c["target_t"] = T_TARGET
            cal_by[scen] = c
        analytic[name] = {
            f"tau2={t2}": {f"n{n}": round(100 * mde(K, t2 + sigma2_episode / n), 2) for n in N_GRID} | {"n_inf": round(100 * mde(K, t2), 2) if t2 > 0 else 0.0}
            for t2 in (0.0, 0.0025, 0.006, 0.012, 0.03)
        }
        res = {}
        for n in N_GRID:
            for scen, st, td in scenarios:
                c = cal_by[scen]
                if c is None:
                    res[f"n{n}|{scen}"] = {"infeasible": True}
                    continue
                per_seed = [simulate_cell(sd * 1000 + n, post_a, post_b, st, c, n, args.nrep, flip_matrix(sd, K)) for sd in SEEDS]
                keys = [k for k in per_seed[0] if k != "nrep"]
                pooled = {k: round(float(np.mean([p[k] for p in per_seed])), 4) for k in keys}
                pooled["per_seed_present_harm"] = [round(p["present_harm"], 4) for p in per_seed]
                pooled["per_seed_small"] = [round(p["small"], 4) for p in per_seed]
                pooled["per_seed_small_unqualified"] = [round(p["small_unqualified"], 4) for p in per_seed]
                pooled["nrep_total"] = int(sum(p["nrep"] for p in per_seed))
                res[f"n{n}|{scen}"] = pooled
            print(f"[{name}] K={K} n={n} done", flush=True)
        slot_central = float(np.mean([r["slot9_mean_s"] for r in s]))
        cap_slots = [x for r in rows for x in r["slot9_cap_episodes_s"] if r["class"] != "excluded_coordinate_setup"]
        slot_high = float(np.mean(cap_slots))
        n_reg = next(nn for kmax, nn in N_MAX_BY_K if K <= kmax)
        sim[name] = {
            "K": K,
            "registered_n": n_reg,
            "posterior_mean_success": round(float(pm.mean()), 4),
            "sigma2_episode_posterior_mean": round(sigma2_episode, 5),
            "calibration": cal_by,
            "results": res,
            "cost": {
                "slot_central_s": round(slot_central, 2),
                "slot_high_s_cap_length_episodes": round(slot_high, 2),
                "n_cap_length_episodes": len(cap_slots),
                "by_n": {f"n{n}": {"central": cost(K, n, slot_central), "high": cost(K, n, slot_high)} for n in N_GRID},
            },
        }
        out["simulation"] = sim
        out["analytic_mde_pp"] = {"note": "2x2 main effect, v = tau2 + sigma2_episode/n (sigma2 at the posterior mean), 80% power, two-sided 0.05, paired t with K-1 df, exact noncentral t", "by_set": analytic}
        args.out.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")  # checkpoint after each set
    out["simulation"] = sim
    out["analytic_mde_pp"] = {
        "note": "2x2 main effect, v = tau2 + sigma2_episode/n (sigma2 at the posterior mean), 80% power, two-sided 0.05, paired t with K-1 df, exact noncentral t",
        "by_set": analytic,
    }
    args.out.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
