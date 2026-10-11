#!/usr/bin/env python3
"""S2 v3.1 (repair after wave 1): operating characteristics of the registered Phase 1 rules, re-run.

What changed from power-v3.py (whose outputs are left as they are):

1. The stratified sharp-null randomization test uses the correct variance. Under the sharp null,
   with the stratum's successes fixed, k_rtl is hypergeometric with variance v and
   k_rtl - k_ltr = 2 k_rtl - (k_rtl + k_ltr), so Var(S) = 4 v. power-v3.py used v (it rejected in
   0.32 of replicates at the exact null; wave-1 reviewer 1, the identification refuter and the
   recorder). PRESENT_FRAGILE (census PRESENT and the sharp-null test disagree at 0.05) is reported.
2. A fifth cell, PL (placebo: the en-LTR interface with every toolbar's items in a fixed seeded
   random order; Phase 0 pilot job 1131), n_pl episodes per task (2: one per harness; 4 reported
   for comparison). Registered readings:
   * P3, total effect: D in the census frame as before, read as the net change in success under
     mirroring on these tasks, with no mechanism attached. Governing labels: CONFIRMED if
     PRESENT_HARM (PRESENT_AND_SMALL included, labelled small harm), FALSIFIED if SMALL without
     PRESENT or PRESENT_BENEFIT, OPEN otherwise.
   * Direction-specific reading (decides only whether a mechanism label may be attached): the
     mirror's excess over the matched rearrangement, E_dir = mean_t (y_enR - y_PL), in the
     population frame (t interval over tasks, df K - 1), because a direction-specific claim is
     about the mechanism and must hold beyond the idiosyncratic task-level reactions any one
     rearrangement produces. MIRROR_SPECIFIC if the 95% interval lies below 0; NO_EXCESS if the
     90% interval lies inside (-5, +5) pp; otherwise UNRESOLVED. The census-frame E_dir is reported
     beside it (a conservative variance for PL cells with one episode per harness:
     (x1 - x2)^2 / 4).
3. Intention to treat: admission (Phase 0) depends on no outcome, so the operating characteristics
   are computed on every task set Phase 0 can produce, including the realized admitted set.

Scenarios pair a mirror structure with a placebo structure. Generic (direction-free) scenarios
give the placebo the same structure as the mirror, drawn independently (matched magnitude);
mirror-specific ones give the placebo none, or less.

CPU only, deterministic given seeds [42, 43, 44] (numpy PCG64 streams [seed, stream id]).

Usage: python3 power-v4.py <a1.jsonl> <pool-v3.json> <out.json> [--admitted admitted.json] [--nrep 2000]
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
MARGIN_REL = 0.15
ALPHA = 0.05
BREAK_P = 0.01
CAL_BANK = 2000
V = 20
USR1_LEAD_MIN = 3
OVERLAY_MIN = 6
DR4_FACTOR = 1.2
REQUEUE_FACTOR = 1.05
STARTUP_S = 113.18587
DRAIN_S = 104.60958
SLOT_HIGH_S = 197.73
SLOT_P95_S = 223.6


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
        return np.where(self.obs[None, :, None], p_obs, p_new)


def apply_effect(rng, p, struct, theta, a_t, b_t):
    R, K, H = p.shape
    if struct == "none" or theta is None:
        return p
    if struct == "logit":
        return expit(logit(p) + theta)
    if struct == "prop":
        return p * (1 - theta)
    if struct == "conc25":
        z = rng.random((R, K, 1)) < 0.25
        return np.where(z, p * (1 - theta), p)
    if struct == "flip":
        z = rng.random((R, K, 1)) < theta
        return np.where(z, 0.0, p)
    if struct == "perturb":
        eps = theta + rng.standard_normal((R, K, 1))
        return expit(logit(p) + eps)
    if struct == "reshuffle":
        z = rng.random((R, K, 1)) < theta
        newp = rng.beta(a_t, b_t, size=(R, K, 1)).repeat(H, axis=2)
        return np.where(z, newp, p)
    raise ValueError(struct)


def calibrate(pool, struct, target, seed):
    if struct in ("none", "reshuffle"):
        return target if struct == "reshuffle" else None
    if target == 0 and struct != "perturb":
        return 0.0
    rng0 = np.random.Generator(np.random.PCG64([seed, 900]))
    p = pool.draw(rng0, CAL_BANK)

    def f(th):
        r = np.random.Generator(np.random.PCG64([seed, 901]))
        pr = apply_effect(r, p, struct, th, pool.a_t, pool.b_t)
        return float((pr.sum() - p.sum()) / p.sum()) - target

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
    if n not in _HYPER:
        N = 2 * n
        T = np.ones((2 * N + 1, N + 1))
        for tot in range(2 * N + 1):
            for x in range(N + 1):
                T[tot, x] = stats.hypergeom.cdf(x, 2 * N, tot, N)
        _HYPER[n] = T
    return _HYPER[n]


def decide(k, kpl, n, n_pl, p_ltr, p_rtl, p_pl):
    """k: (R, K, H, 4) successes in (en, arL, enR, arR), m = n/2 per (task, harness, cell);
    kpl: (R, K, H) placebo successes, m_pl = n_pl/2 per (task, harness)."""
    R, K, H, _ = k.shape
    m = n // 2
    m_pl = n_pl // 2
    phat = k / m
    yc = phat.mean(axis=2)
    s2 = (m / (m - 1)) * phat * (1 - phat)
    var_yc = (s2 / m).sum(axis=2) / H ** 2
    D_t = ((yc[..., 3] - yc[..., 1]) + (yc[..., 2] - yc[..., 0])) / 2
    v_t = var_yc.sum(axis=2) / 4
    D = D_t.mean(axis=1)
    se_c = np.sqrt(v_t.sum(axis=1)) / K
    yR = (yc[..., 2] + yc[..., 3]) / 2
    yL = (yc[..., 0] + yc[..., 1]) / 2
    SR, SL = yR.mean(axis=1), yL.mean(axis=1)
    vR = ((var_yc[..., 2] + var_yc[..., 3]) / 4).sum(axis=1) / K ** 2
    vL = ((var_yc[..., 0] + var_yc[..., 1]) / 4).sum(axis=1) / K ** 2
    with np.errstate(divide="ignore", invalid="ignore"):
        L = np.log(SR) - np.log(SL)
        seL_c = np.sqrt(vR / SR ** 2 + vL / SL ** 2)
    z95, z90 = stats.norm.ppf(0.975), stats.norm.ppf(0.95)
    ok = np.isfinite(L) & np.isfinite(seL_c)
    present = np.abs(D) > z95 * se_c
    lrel = -math.log(1 - MARGIN_REL)
    small = ((D - z90 * se_c > -MARGIN_ABS) & (D + z90 * se_c < MARGIN_ABS)
             & ok & (L - z90 * seL_c > -lrel) & (L + z90 * seL_c < lrel))
    tD = ((p_rtl - p_ltr).mean(axis=2)).mean(axis=1)
    tL = np.log(p_rtl.mean(axis=(1, 2))) - np.log(p_ltr.mean(axis=(1, 2)))
    cover_D = (D - z95 * se_c <= tD) & (tD <= D + z95 * se_c)
    beyond = (np.abs(tD) >= MARGIN_ABS) | (np.abs(tL) >= lrel)
    # sharp-null randomization test, corrected variance 4v
    S = np.zeros(R)
    var = np.zeros(R)
    for ltr, rtl in ((0, 2), (1, 3)):
        mm = k[..., ltr] + k[..., rtl]
        Nn = 2 * m
        v = m * (mm / Nn) * (1 - mm / Nn) * (Nn - m) / (Nn - 1)
        S += (k[..., rtl] - k[..., ltr]).sum(axis=(1, 2))
        var += 4 * v.sum(axis=(1, 2))
    with np.errstate(divide="ignore", invalid="ignore"):
        zs = np.where(var > 0, S / np.sqrt(var), 0.0)
    sharp = 2 * stats.norm.sf(np.abs(zs)) <= ALPHA
    fragile = present != sharp
    # population frame for D
    sd = D_t.std(axis=1, ddof=1)
    se_s = sd / math.sqrt(K)
    t95, t90 = stats.t.ppf(0.975, K - 1), stats.t.ppf(0.95, K - 1)
    present_pop = np.abs(D) > t95 * se_s
    # placebo readings (en level)
    ypl = (kpl / m_pl).mean(axis=2)  # (R, K)
    if m_pl >= 2:
        ph = kpl / m_pl
        var_pl = ((m_pl / (m_pl - 1)) * ph * (1 - ph) / m_pl).sum(axis=2) / H ** 2
    else:
        var_pl = ((kpl[..., 0] - kpl[..., 1]) ** 2) / 4.0
    e_t = yc[..., 2] - ypl
    E = e_t.mean(axis=1)
    sdE = e_t.std(axis=1, ddof=1)
    seE = sdE / math.sqrt(K)
    mirror_specific = (E + t95 * seE) < 0
    no_excess = (E - t90 * seE > -MARGIN_ABS) & (E + t90 * seE < MARGIN_ABS)
    seE_c = np.sqrt((var_yc[..., 2] + var_pl).sum(axis=1)) / K
    mirror_specific_c = (E + z95 * seE_c) < 0
    P_t = ypl - yc[..., 0]
    P = P_t.mean(axis=1)
    seP = P_t.std(axis=1, ddof=1) / math.sqrt(K)
    placebo_harm_pop = (P + t95 * seP) < 0
    tE = (p_rtl - p_pl).mean(axis=(1, 2))
    coverE = (E - t95 * seE <= tE) & (tE <= E + t95 * seE)
    confirmed = present & (D < 0)
    falsified = (small & ~present) | (present & (D > 0))
    return {
        "present_harm": float((present & (D < 0)).mean()),
        "present_benefit": float((present & (D > 0)).mean()),
        "small": float(small.mean()),
        "present_and_small": float((present & small).mean()),
        "inconclusive": float((~present & ~small).mean()),
        "p3_confirmed": float(confirmed.mean()),
        "p3_falsified": float(falsified.mean()),
        "p3_open": float((~confirmed & ~falsified).mean()),
        "false_small_given_census_beyond_margin": (float((small & beyond).sum() / beyond.sum()) if beyond.sum() else None),
        "cover95_census_D": float(cover_D.mean()),
        "mean_census_true_D_pp": round(float(tD.mean()) * 100, 3),
        "sd_census_true_D_pp": round(float(tD.std()) * 100, 3),
        "mean_se_census_D_pp": round(float(se_c.mean()) * 100, 3),
        "sharp_null_reject": float(sharp.mean()),
        "present_fragile": float(fragile.mean()),
        "pop_present_harm": float((present_pop & (D < 0)).mean()),
        "mirror_specific_pop": float(mirror_specific.mean()),
        "mirror_specific_census": float(mirror_specific_c.mean()),
        "no_excess_pop": float(no_excess.mean()),
        "unresolved_pop": float((~mirror_specific & ~no_excess).mean()),
        "placebo_harm_pop": float(placebo_harm_pop.mean()),
        "mean_true_E_pp": round(float(tE.mean()) * 100, 3),
        "cover95_pop_E_of_census_truth": float(coverE.mean()),
        "mean_se_pop_E_pp": round(float(seE.mean()) * 100, 3),
        "mean_se_census_E_pp": round(float(seE_c.mean()) * 100, 3),
    }


def simulate(pool, mstruct, mtheta, pstruct, ptheta, n, n_pl, R, seed):
    rng = np.random.Generator(np.random.PCG64([seed, 2, n, n_pl, pool.K]))
    p = pool.draw(rng, R)
    u = rng.normal(0, SESSION_SD, size=(R, 1, 1))
    p = expit(logit(p) + u)
    pr = apply_effect(rng, p, mstruct, mtheta, pool.a_t, pool.b_t)
    pp = apply_effect(rng, p, pstruct, ptheta, pool.a_t, pool.b_t)
    m = n // 2
    k = rng.binomial(m, np.stack([p, p, pr, pr], axis=-1))
    kpl = rng.binomial(n_pl // 2, pp)
    return decide(k, kpl, n, n_pl, p, pr, pp)


def cost(K, n, n_pl=0, slot_s=SLOT_HIGH_S):
    N = 4 * K * n + K * n_pl
    physical_h = (STARTUP_S + N * slot_s / V + DRAIN_S) / 3600
    cap_min = math.ceil(USR1_LEAD_MIN + STARTUP_S / 60 + (N * slot_s / V + DRAIN_S) * DR4_FACTOR * REQUEUE_FACTOR / 60)
    return {"episodes": N, "physical_gpu_h_high_slot": round(physical_h, 3),
            "cap_minutes_incl_overlay": cap_min + OVERLAY_MIN, "cap_gpu_h_incl_overlay": round((cap_min + OVERLAY_MIN) / 60, 3)}


SCENARIOS = [
    # name, mirror (struct, target), placebo (struct, target), kind
    ("null", ("none", 0.0), ("none", 0.0), "null"),
    ("perturb_null", ("perturb", 0.0), ("perturb", 0.0), "generic"),
    ("reshuffle_10", ("reshuffle", 0.1), ("reshuffle", 0.1), "generic"),
    ("reshuffle_30", ("reshuffle", 0.3), ("reshuffle", 0.3), "generic"),
    ("generic_uniform_15", ("logit", -0.15), ("logit", -0.15), "generic"),
    ("generic_breaks_15", ("flip", -0.15), ("flip", -0.15), "generic"),
    ("mirror_uniform_10", ("logit", -0.10), ("none", 0.0), "specific"),
    ("mirror_uniform_15", ("logit", -0.15), ("none", 0.0), "specific"),
    ("mirror_uniform_20", ("logit", -0.20), ("none", 0.0), "specific"),
    ("mirror_prop_15", ("prop", -0.15), ("none", 0.0), "specific"),
    ("mirror_quarter_15", ("conc25", -0.15), ("none", 0.0), "specific"),
    ("mirror_breaks_15", ("flip", -0.15), ("none", 0.0), "specific"),
    ("mirror_perturb_15", ("perturb", -0.15), ("none", 0.0), "specific"),
    ("mirror_uniform_15_placebo_reshuffle_10", ("logit", -0.15), ("reshuffle", 0.1), "specific"),
    ("mirror_uniform_30_placebo_uniform_15", ("logit", -0.30), ("logit", -0.15), "specific"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("a1")
    ap.add_argument("pool")
    ap.add_argument("out")
    ap.add_argument("--admitted", default=None, help="JSON list of admitted task ids (Phase 0 record)")
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
        base = {"task_id": t["task_id"], "split": t["split"], "app": t["app"]}
        if d:
            tasks.append({**base, "k_h": [sum(d[h]) for h in HARNESSES], "n_h": [len(d[h]) for h in HARNESSES]})
        else:
            tasks.append({**base, "k_h": None, "n_h": None})
    obs = [t for t in tasks if t["k_h"]]
    a_c, b_c = fit_betabinom([k for t in obs for k in t["k_h"]], 4)
    a_t, b_t = fit_betabinom([sum(t["k_h"]) for t in obs], 8)
    sets = {"census_all_106": tasks, "confirm_only_62": [t for t in tasks if t["split"] == "confirm"]}
    admitted_ids = None
    if args.admitted:
        admitted_ids = set(json.loads(Path(args.admitted).read_text()))
        sets["admitted_phase0"] = [t for t in tasks if t["task_id"] in admitted_ids]
    configs = [("census_all_106", 4, 2), ("census_all_106", 4, 4), ("confirm_only_62", 4, 2)]
    if admitted_ids is not None:
        configs.insert(1, ("admitted_phase0", 4, 2))
    results = []
    for sname, n, n_pl in configs:
        pool = Pool(sets[sname], a_c, b_c, a_t, b_t)
        for name, (ms, mt), (ps, pt), kind in SCENARIOS:
            rows, ok = [], True
            for seed in SEEDS:
                mth = calibrate(pool, ms, mt, seed)
                pth = calibrate(pool, ps, pt, seed)
                if (ms != "none" and mth is None) or (ps != "none" and pth is None):
                    ok = False
                    break
                rows.append(simulate(pool, ms, mth, ps, pth, n, n_pl, args.nrep, seed))
            if not ok:
                results.append({"set": sname, "K": pool.K, "n": n, "n_pl": n_pl, "scenario": name, "unreachable": True})
                continue
            agg = {}
            for key in rows[0]:
                vals = [r[key] for r in rows if r[key] is not None]
                agg[key] = round(float(np.mean(vals)), 4) if vals else None
                agg[key + "_by_seed"] = [None if r[key] is None else round(r[key], 4) for r in rows]
            res = {"set": sname, "K": pool.K, "n": n, "n_pl": n_pl, "scenario": name, "kind": kind,
                   "mirror": [ms, mt], "placebo": [ps, pt], **agg, "cost": cost(pool.K, n, n_pl),
                   "cost_p95_slot": cost(pool.K, n, n_pl, SLOT_P95_S)}
            results.append(res)
            print(f"{sname:18s} K={pool.K:3d} n={n} npl={n_pl} {name:40s} PH={agg['present_harm']:.3f} SM={agg['small']:.3f} "
                  f"P3c={agg['p3_confirmed']:.3f} P3f={agg['p3_falsified']:.3f} sharp={agg['sharp_null_reject']:.3f} "
                  f"frag={agg['present_fragile']:.3f} MSpop={agg['mirror_specific_pop']:.3f} MScen={agg['mirror_specific_census']:.3f} "
                  f"noEx={agg['no_excess_pop']:.3f} cov={agg['cover95_census_D']:.3f} tD={agg['mean_census_true_D_pp']}", flush=True)
    out = {
        "schema": "s2v3-power-v4",
        "inputs": {"a1_jsonl_sha256": sha256(a1), "pool_v3_json_sha256": sha256(poolp),
                   "admitted_sha256": sha256(Path(args.admitted)) if args.admitted else None},
        "seeds": list(SEEDS), "nrep_per_seed": args.nrep, "session_sd_logit": SESSION_SD,
        "margins": {"abs": MARGIN_ABS, "rel": MARGIN_REL},
        "prior": {"cell_level": {"a": a_c, "b": b_c}, "task_level": {"a": a_t, "b": b_t}},
        "sets": {k: {"K": len(v), "with_s1a_records": sum(1 for t in v if t["k_h"])} for k, v in sets.items()},
        "results": results,
        "costs": {f"K{K}_n4_npl{q}": cost(K, 4, q) for K in (62, 89, 100, 106) for q in (0, 2, 4)},
        "costs_p95": {f"K{K}_n4_npl{q}": cost(K, 4, q, SLOT_P95_S) for K in (62, 89, 100, 106) for q in (0, 2, 4)},
        "versions": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__},
        "wall_seconds": round(time.time() - t0, 1),
    }
    outp.write_text(json.dumps(out, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
