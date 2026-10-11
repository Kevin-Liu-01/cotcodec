#!/usr/bin/env python3
"""S2v2: operating characteristics of the whole v2 decision path, under the registered estimator.

Every replicate runs the registered path of e5-gate-fertility-decomposition-v2 end to end:

  1. operating point: held-out smoke accuracies (200 episodes per cell, binomial) for CAN at
     K in (4, 8, 16) and NAT at (K, f) for f in (2.7, 2.0) go through
     estimator_v2.select_operating_point, which returns (K_p, f_p) or NOT_ADMISSIBLE;
  2. analysis: four paired arms (CAN, DEC, CLAMP, NAT) per episode at (K_p, f_p), with
     articles as clusters (4 episodes per article), drawn from a latent probit model
     (below);
  3. estimates: b_TNIE and b_PNIE on the guessing-corrected scale per log-f unit with the
     registered cluster-robust normal interval (estimator_v2.cluster_normal_matrix, which
     equals estimator_v2.cluster_normal replicate by replicate);
  4. reading: estimator_v2.decide_subject (same rules, vectorised here and checked against
     the scalar function on the first 200 replicates of every setting).

Latent model per episode e in article a and arm j:
    m_ej = u_a + w_e + mu_j + sigma * eps_ej + [re-segmented arms] sigma_r * r_e
           + [CLAMP] tau * eta_a1 + [DEC] tau * eta_a2,          Y_ej = 100 * 1{m_ej > 0}
u_a ~ N(0, s_art), w_e ~ N(0, 1 - s_art) (article share s_art of episode difficulty), eps and
r standard normal, eta article-level effect heterogeneity. mu_j is solved so that arm j has
its scenario accuracy exactly. sigma (arm-specific noise) sets the discordance of the
paired contrasts; it is swept so that the TNIE discordance spans about 0.05 to the maximum
the accuracies allow (about 0.45 to 0.5), as the wave-1 reviewers asked. The achieved
discordances are reported for every setting.

Scenario truths are effects at the selected operating point in corrected points per log-f
unit: b_T (TNIE) and b_P (PNIE); raw shifts are b * 0.75 * ln f_p. INT = b_T - b_P.

Also reported:
  * the v1 rule's K = 1 dilution reproduced with v1's own estimator (the wave-1 defect);
  * selection probabilities near the ceiling and the floors;
  * coverage of the decision interval and of the percentile cluster bootstrap, and their
    decision agreement;
  * the probability of a decisive verdict and of the correct verdict per scenario.

All randomness is seeded. Usage: python power-sim-v2.py <out.json> [all|misc|grid0|grid1|tau|prof0|prof1]
(parts are merged by merge-power-v2.py into power-sim-v2.json)
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy import stats

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import estimator_v2 as ev2  # noqa: E402
import estimator as ev1  # noqa: E402  (wave-1 estimator, unedited)

N_HELDOUT = 200
S_ART = 0.3
SIGMA_R = 0.5  # re-segmentation-specific noise shared by NAT and CLAMP
REPS = 1000
CHUNK = 250

PROFILES = {
    # name: (CAN by K, NAT by (K, f))
    "P1_K4_admissible": ({4: 85, 8: 75, 16: 62},
                         {(4, 2.7): 60, (8, 2.7): 50, (16, 2.7): 40, (4, 2.0): 68, (8, 2.0): 58, (16, 2.0): 48}),
    "P2_K4_ceiling": ({4: 96, 8: 86, 16: 74},
                      {(4, 2.7): 78, (8, 2.7): 62, (16, 2.7): 48, (4, 2.0): 84, (8, 2.0): 70, (16, 2.0): 56}),
    "P3_K4_K8_ceiling": ({4: 98, 8: 94, 16: 84},
                         {(4, 2.7): 86, (8, 2.7): 76, (16, 2.7): 58, (4, 2.0): 90, (8, 2.0): 82, (16, 2.0): 66}),
    "P4_f_fallback": ({4: 85, 8: 75, 16: 62},
                      {(4, 2.7): 25, (8, 2.7): 25, (16, 2.7): 25, (4, 2.0): 40, (8, 2.0): 34, (16, 2.0): 30}),
    "P5_ceiling_borderline": ({4: 90, 8: 80, 16: 66},
                              {(4, 2.7): 64, (8, 2.7): 54, (16, 2.7): 42, (4, 2.0): 72, (8, 2.0): 62, (16, 2.0): 50}),
}

# (name, b_T, b_P, rf_median, correct reading or set of acceptable readings, role)
SCENARIOS = [
    ("null", 0.0, 0.0, 2.2, {"KILL"}, "no decay effect at either writes; gates do not self-normalise"),
    ("small_below_line", 1.0, 1.0, 2.2, {"KILL"}, "true effects one third of the line"),
    ("line_both", 3.0, 3.0, 2.2, {"MATERIAL", "INCONCLUSIVE"}, "true decay effect exactly at the line (wave-1 defect: must not read KILL)"),
    ("line_tnie_only", 3.0, 0.0, 2.2, {"MATERIAL", "INCONCLUSIVE"}, "oracle parity benefit at the line, no pure decay cost"),
    ("line_pnie_only", 0.0, 3.0, 2.2, {"MASKED", "PARITY_NULL"}, "pure decay at the line, fully absorbed at the re-segmented writes"),
    ("material", 6.0, 6.0, 2.2, {"MATERIAL"}, "twice the line, no interaction"),
    ("material_strong", 10.0, 14.0, 2.2, {"MATERIAL"}, "per-token clock dominant, mild negative interaction"),
    ("masked", 0.0, 8.0, 2.2, {"MASKED"}, "pure decay material, absorbed by the re-segmented writes"),
    ("masked_partial", 1.0, 12.0, 2.2, {"MASKED"}, "S1-like: pure decay large, oracle benefit small"),
    ("self_normalized", 0.0, 0.0, 1.1, {"SELF_NORMALIZED"}, "gates self-normalise on fragments (R_F near 1)"),
]

SIGMAS = (0.25, 1.0, 2.0, 4.0)
N_ARTICLES = (1000, 1500, "registered")
SIZING = ("null", "small_below_line", "line_both")
KEY_SCENARIOS = ("null", "line_both", "line_pnie_only", "material", "masked", "self_normalized")
TAUS = (0.0, 0.2)


def solve_mu(acc: float, var: float) -> float:
    return float(stats.norm.ppf(acc / 100.0) * math.sqrt(var))


def select_vectorised(rng, reps: int, profile) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Run the registered selection on held-out binomial accuracies. Returns K_p, f_p (0 when
    NOT_ADMISSIBLE) and an admissible flag, one per replicate."""
    can_true, nat_true = profile
    can_obs = {k: rng.binomial(N_HELDOUT, can_true[k] / 100.0, reps) / N_HELDOUT * 100 for k in ev2.K_LADDER}
    nat_obs = {kf: rng.binomial(N_HELDOUT, nat_true[kf] / 100.0, reps) / N_HELDOUT * 100 for kf in nat_true}
    kp = np.zeros(reps, dtype=int)
    fp = np.zeros(reps)
    for r in range(reps):
        sel = ev2.select_operating_point({k: can_obs[k][r] for k in can_obs}, {kf: nat_obs[kf][r] for kf in nat_obs})
        if sel is not None:
            kp[r], fp[r] = sel
    return kp, fp, kp > 0


def draw_arms(rng, reps: int, g: int, acc: dict[str, float], sigma: float, tau: float):
    """Per-episode outcomes [reps, g, 4] for each arm (points, float32)."""
    m = ev2.EPISODES_PER_ARTICLE
    f32 = np.float32
    u = rng.standard_normal((reps, g, 1), dtype=f32) * f32(math.sqrt(S_ART))
    z = u + rng.standard_normal((reps, g, m), dtype=f32) * f32(math.sqrt(1 - S_ART))
    r = rng.standard_normal((reps, g, m), dtype=f32) * f32(SIGMA_R)
    eta1 = rng.standard_normal((reps, g, 1), dtype=f32) * f32(tau)
    eta2 = rng.standard_normal((reps, g, 1), dtype=f32) * f32(tau)
    out = {}
    for arm in ("CAN", "DEC", "CLAMP", "NAT"):
        var = 1.0 + sigma ** 2
        latent = z + f32(sigma) * rng.standard_normal((reps, g, m), dtype=f32)
        if arm in ("CLAMP", "NAT"):
            var += SIGMA_R ** 2
            latent += r
        if arm == "CLAMP":
            var += tau ** 2
            latent += eta1
        if arm == "DEC":
            var += tau ** 2
            latent += eta2
        latent += f32(solve_mu(acc[arm], var))
        out[arm] = (latent > 0).astype(f32) * f32(100.0)
    return out


def read_vectorised(arms, f_p: np.ndarray, rf: float):
    """Registered estimates and readings per replicate (f_p per replicate)."""
    scale = 1.0 / (ev2.GUESS_SCALE * np.log(f_p))
    tnie = arms["CLAMP"] - arms["NAT"]
    pnie = arms["CAN"] - arms["DEC"]
    pt, lt, ht = ev2.cluster_normal_matrix(tnie)
    pp, lp, hp = ev2.cluster_normal_matrix(pnie)
    pi, li, hi = ev2.cluster_normal_matrix(tnie - pnie)
    pt, lt, ht, pp, lp, hp, pi, li, hi = (x * scale for x in (pt, lt, ht, pp, lp, hp, pi, li, hi))
    L = ev2.LINE
    mat_t = (pt >= L) & (lt > 0)
    below_t = ht < L
    mat_p = (pp >= L) & (lp > 0)
    below_p = hp < L
    reading = np.full(pt.shape, "INCONCLUSIVE", dtype=object)
    reading[below_t & ~below_p & ~mat_p] = "PARITY_NULL"
    reading[below_t & below_p] = "KILL" if rf >= ev2.RF_MIN else "SELF_NORMALIZED"
    if rf < ev2.RF_MIN:
        reading[below_t & ~mat_p] = "SELF_NORMALIZED"
    reading[below_t & mat_p] = "MASKED"
    reading[mat_t] = "MATERIAL"
    d_t = (tnie != 0).mean((1, 2))
    d_p = (pnie != 0).mean((1, 2))
    return reading, dict(pt=pt, lt=lt, ht=ht, pp=pp, lp=lp, hp=hp, pi=pi, li=li, hi=hi, d_t=d_t, d_p=d_p)


def check_against_scalar(reading, est, rf, n_check=200):
    """The vectorised reading must equal estimator_v2.decide_subject replicate by replicate."""
    bad = 0
    for i in range(min(n_check, len(reading))):
        bt = ev2.Interval(est["pt"][i], est["lt"][i], est["ht"][i])
        bp = ev2.Interval(est["pp"][i], est["lp"][i], est["hp"][i])
        bad += int(ev2.decide_subject(bt, bp, rf) != reading[i])
    return bad


def run_setting(seed_key, profile_name, scen, sigma, n_art, tau, reps=REPS):
    name, b_t, b_p, rf, correct, _ = scen
    profile = PROFILES[profile_name]
    rng = np.random.default_rng(seed_key)
    counts = {}
    est_acc = {k: [] for k in ("pt", "pp", "pi", "d_t", "d_p")}
    sel_counts = {}
    mismatches = 0
    cover_t = cover_p = n_adm = 0
    for start in range(0, reps, CHUNK):
        rr = min(CHUNK, reps - start)
        kp, fp, adm = select_vectorised(rng, rr, profile)
        for k_, f_ in zip(kp, fp):
            key = "NOT_ADMISSIBLE" if k_ == 0 else f"K{k_}_f{f_}"
            sel_counts[key] = sel_counts.get(key, 0) + 1
        counts["NOT_ADMISSIBLE"] = counts.get("NOT_ADMISSIBLE", 0) + int((~adm).sum())
        # group replicates by selected point so each draw uses that point's accuracies
        for key in sorted({(int(a), float(b)) for a, b in zip(kp[adm], fp[adm])}):
            idx = np.flatnonzero(adm & (kp == key[0]) & (fp == key[1]))
            k_, f_ = key
            can = profile[0][k_]
            nat = profile[1][(k_, f_)]
            sh_t = b_t * ev2.GUESS_SCALE * math.log(f_)
            sh_p = b_p * ev2.GUESS_SCALE * math.log(f_)
            acc = {"CAN": can, "DEC": can - sh_p, "NAT": nat, "CLAMP": min(nat + sh_t, 99.5)}
            g_art = ev2.N_ARTICLES_BY_F[f_] if n_art == "registered" else n_art
            arms = draw_arms(rng, len(idx), g_art, acc, sigma, tau)
            reading, est = read_vectorised(arms, np.full(len(idx), f_), rf)
            if start == 0:
                mismatches += check_against_scalar(reading, est, rf)
            for rd in reading:
                counts[rd] = counts.get(rd, 0) + 1
            for k in est_acc:
                est_acc[k].extend(est[k].tolist())
            cover_t += int(((est["lt"] <= b_t) & (est["ht"] >= b_t)).sum())
            cover_p += int(((est["lp"] <= b_p) & (est["hp"] >= b_p)).sum())
            n_adm += len(idx)
    probs = {k: v / reps for k, v in sorted(counts.items())}
    p_correct = sum(probs.get(c, 0.0) for c in correct)
    decisive = sum(probs.get(c, 0.0) for c in ("KILL", "MASKED", "SELF_NORMALIZED", "MATERIAL"))
    return {
        "profile": profile_name, "scenario": name, "b_T": b_t, "b_P": b_p, "rf_median": rf,
        "sigma": sigma, "n_articles": n_art,
        "n_episodes": "4 x N_ARTICLES_BY_F[f_p]" if n_art == "registered" else n_art * ev2.EPISODES_PER_ARTICLE, "tau": tau,
        "reps": reps, "P": probs, "P_correct": p_correct, "P_decisive": decisive,
        "P_KILL": probs.get("KILL", 0.0),
        "selection": {k: v / reps for k, v in sorted(sel_counts.items())},
        "discordance_TNIE_mean": float(np.mean(est_acc["d_t"])) if est_acc["d_t"] else None,
        "discordance_PNIE_mean": float(np.mean(est_acc["d_p"])) if est_acc["d_p"] else None,
        "mean_b_TNIE": float(np.mean(est_acc["pt"])) if est_acc["pt"] else None,
        "mean_b_PNIE": float(np.mean(est_acc["pp"])) if est_acc["pp"] else None,
        "coverage_TNIE_90": cover_t / n_adm if n_adm else None,
        "coverage_PNIE_90": cover_p / n_adm if n_adm else None,
        "vectorised_vs_scalar_mismatches": mismatches,
    }


def v1_dilution():
    """The wave-1 defect reproduced with v1's own estimator: K = 1 at ceiling (shift 0,
    discordance 0.02), K = 4 true secant b4 at discordance d, 1,500 episodes per load,
    375 passages x 4 episodes per load, between-passage SD 2 points, f_p = 2.7. The decision
    is computed vectorised and checked against ev1.cluster_normal and ev1.decide_subject on
    the first 100 replicates of every row."""
    rows = []
    lnf = math.log(2.7)
    for b4 in (3.0, 4.0):
        for d in (0.1, 0.2, 0.3):
            rng = np.random.default_rng([7, int(b4 * 10), int(d * 100)])
            reps, g, c = 2000, 375, 4
            def diffs(delta, disc):
                dc = delta + 0.02 * rng.standard_normal((reps, g, 1))
                p01 = np.clip((disc + dc) / 2, 0, disc)
                p10 = disc - p01
                u = rng.random((reps, g, c))
                return np.where(u < p01, 100.0, np.where(u < p01 + p10, -100.0, 0.0))
            x = np.concatenate([diffs(0.0, 0.02), diffs(b4 * lnf / 100.0, d)], axis=2)
            pt, lo, hi = ev2.cluster_normal_matrix(x, scale=1.0 / lnf)
            kill_vec = hi < ev1.LINE
            mism = 0
            for r in range(100):
                iv = ev1.cluster_normal([x[r, j] for j in range(g)])
                beta = ev1.Interval(iv.point / lnf, iv.lo / lnf, iv.hi / lnf)
                mism += int((ev1.decide_subject(beta) == "KILL") != bool(kill_vec[r]))
            rows.append({"rule": "v1 pooled K in {1, 4}", "true_K4_secant": b4, "K4_discordance": d,
                         "P_KILL": float(kill_vec.mean()), "check_mismatches_first_100": mism})
    return rows


def coverage_bootstrap_check():
    """Coverage of the registered cluster-normal interval and of the percentile cluster
    bootstrap (B = 2,000) for b_TNIE, and agreement of their below-line decisions."""
    rows = []
    for sigma, tau, n_art in ((0.25, 0.1, 2000), (2.0, 0.2, 2000), (4.0, 0.2, 2000)):
        rng = np.random.default_rng([44, int(sigma * 10), int(tau * 10), n_art])
        f_p, reps, b_t = 2.7, 200, 1.0
        sh = b_t * ev2.GUESS_SCALE * math.log(f_p)
        acc = {"CAN": 85, "DEC": 85, "NAT": 60, "CLAMP": 60 + sh}
        arms = draw_arms(rng, reps, n_art, acc, sigma, tau)
        x = arms["CLAMP"] - arms["NAT"]
        s = ev2.secant_scale(f_p)
        pt, lt, ht = ev2.cluster_normal_matrix(x, scale=s)
        cov_n = float(((lt <= b_t) & (ht >= b_t)).mean())
        cov_b = agree = 0
        for r in range(reps):
            iv = ev2.cluster_bootstrap_mean([x[r, j] for j in range(n_art)], seed=ev2.BOOT_SEED + r, scale=s)
            cov_b += int(iv.lo <= b_t <= iv.hi)
            agree += int((iv.hi < ev2.LINE) == (ht[r] < ev2.LINE))
        rows.append({"sigma": sigma, "tau": tau, "n_articles": n_art, "b_T_true": b_t, "reps": reps,
                     "discordance": float((x != 0).mean()),
                     "coverage_cluster_normal_90": cov_n, "coverage_cluster_bootstrap_90": cov_b / reps,
                     "below_line_decision_agreement": agree / reps})
    return rows


def selection_table():
    rows = []
    rng = np.random.default_rng(45)
    for can4 in (84, 87, 90, 93, 96):
        prof = ({4: can4, 8: can4 - 10, 16: can4 - 24},
                {(4, 2.7): 60, (8, 2.7): 50, (16, 2.7): 40, (4, 2.0): 68, (8, 2.0): 58, (16, 2.0): 48})
        kp, fp, adm = select_vectorised(rng, 4000, prof)
        rows.append({"true_CAN_K4": can4, "P_select_K4": float((kp == 4).mean()), "P_select_K8": float((kp == 8).mean()),
                     "P_not_admissible": float((~adm).mean())})
    for nat in (24, 27, 30, 33, 36):
        prof = ({4: 85, 8: 75, 16: 62},
                {(4, 2.7): nat, (8, 2.7): nat - 10, (16, 2.7): nat - 20, (4, 2.0): nat + 10, (8, 2.0): nat, (16, 2.0): nat - 10})
        kp, fp, adm = select_vectorised(rng, 4000, prof)
        rows.append({"true_NAT_K4_f2.7": nat, "P_f2.7": float((fp == 2.7).mean()), "P_f2.0": float((fp == 2.0).mean()),
                     "P_not_admissible": float((~adm).mean())})
    return rows


def main() -> int:
    out_path = Path(sys.argv[1])
    part = sys.argv[2] if len(sys.argv) > 2 else "all"
    t0 = time.time()
    res = {"part": part, "params": dict(N_HELDOUT=N_HELDOUT, S_ART=S_ART, SIGMA_R=SIGMA_R, REPS=REPS, SIGMAS=SIGMAS,
                          N_ARTICLES=N_ARTICLES, TAUS=TAUS, LINE=ev2.LINE, GUESS_SCALE=ev2.GUESS_SCALE,
                          CEILING_CAN=ev2.CEILING_CAN, FLOOR_CAN=ev2.FLOOR_CAN, FLOOR_NAT=ev2.FLOOR_NAT,
                          RF_MIN=ev2.RF_MIN, K_LADDER=ev2.K_LADDER, F_LADDER=ev2.F_LADDER,
                          N_ARTICLES_BY_F={str(k): v for k, v in ev2.N_ARTICLES_BY_F.items()},
                          EPISODES_PER_ARTICLE=ev2.EPISODES_PER_ARTICLE, profiles={k: [v[0], {f"{a}|{b}": c for (a, b), c in v[1].items()}] for k, v in PROFILES.items()},
                          scenarios=[dict(name=s[0], b_T=s[1], b_P=s[2], rf_median=s[3], correct=sorted(s[4]), role=s[5]) for s in SCENARIOS])}
    if part in ("all", "misc"):
        res["v1_dilution_reproduced"] = v1_dilution()
        print("v1 dilution", [(r["true_K4_secant"], r["K4_discordance"], r["P_KILL"]) for r in res["v1_dilution_reproduced"]], round(time.time() - t0), flush=True)
        res["selection"] = selection_table()
        res["coverage"] = coverage_bootstrap_check()
        print("coverage", res["coverage"], round(time.time() - t0), flush=True)
    if part.startswith("grid") or part == "all":
        # grid parts: grid0 = first half of the scenarios, grid1 = second half
        scen_idx = range(len(SCENARIOS)) if part in ("all", "grid") else (range(0, 5) if part == "grid0" else range(5, len(SCENARIOS)))
        grid = []
        for si in scen_idx:
            scen = SCENARIOS[si]
            for sigma in SIGMAS:
                # the n sweep is run for the sizing scenarios; the others at the registered n only
                for n_art in (N_ARTICLES if scen[0] in SIZING else ("registered",)):
                    nkey = 0 if n_art == "registered" else n_art
                    grid.append(run_setting([42, si, int(sigma * 100), nkey, 10], "P1_K4_admissible", scen, sigma, n_art, 0.1))
            print(scen[0], [(r["sigma"], r["n_articles"], round(r["discordance_TNIE_mean"], 3), round(r["P_correct"], 3), round(r["P_KILL"], 3)) for r in grid if r["scenario"] == scen[0]], round(time.time() - t0), flush=True)
        res["grid_P1"] = grid
    if part in ("all", "tau"):
        tau_rows = []
        for si, scen in enumerate(SCENARIOS):
            if scen[0] not in KEY_SCENARIOS:
                continue
            for tau in TAUS:
                for sigma in (1.0,):
                    tau_rows.append(run_setting([43, si, int(sigma * 100), int(tau * 100)], "P1_K4_admissible", scen, sigma, "registered", tau))
        res["tau_sensitivity"] = tau_rows
        print("tau done", round(time.time() - t0), flush=True)
    if part.startswith("prof") or part == "all":
        names = ("P2_K4_ceiling", "P3_K4_K8_ceiling", "P4_f_fallback", "P5_ceiling_borderline")
        if part == "prof0":
            names = names[:2]
        elif part == "prof1":
            names = names[2:]
        prof_rows = []
        for pname in names:
            pi_ = ("P2_K4_ceiling", "P3_K4_K8_ceiling", "P4_f_fallback", "P5_ceiling_borderline").index(pname)
            for si, scen in enumerate(SCENARIOS):
                if scen[0] not in KEY_SCENARIOS:
                    continue
                for sigma in (0.25, 2.0):
                    prof_rows.append(run_setting([46, si, int(sigma * 100), pi_], pname, scen, sigma, "registered", 0.1))
            print(pname, "done", round(time.time() - t0), flush=True)
        res["profiles"] = prof_rows
    res["elapsed_s"] = round(time.time() - t0, 1)
    out_path.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
