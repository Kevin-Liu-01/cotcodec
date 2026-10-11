#!/usr/bin/env python3
"""Operating characteristics of every threshold in the R01 draft registration (v1).

CPU only; numpy and scipy. Seeds 42, 43 and 44 (each block runs once per seed and the
seed-level results are reported beside the pooled ones). Inputs: S1a's committed a1.jsonl
(4B, H-OSW-fixed per-task success counts) and the committed Stage A0 census output.

Blocks:

  B_det   Stage B gate on the deterministic reference (batch 1, prefix cache off): exact
          binomial, and a beta-binomial by episode, at n = 320 replica pairs.
  B_read  Stage B request-level readings (SUFFICIENT / PARTIAL / INERT) for a hazard measured
          on 40 episodes x 8 requests with episode heterogeneity, read by an episode-cluster
          percentile bootstrap, at the text level (0.20 / 0.05) and the IR level (0.02 / 0.01).
  A1_cen  Stage A1 region census (CLOCK_ONLY / MULTI_REGION) on 113 task pairs.
  C_env   Stage C environment verdict noise (ENV_MATERIAL / ENV_BOUNDED / ENV_UNRESOLVED) on
          452 replayed episodes (113 tasks x 4) with task-clustered events.
  K6      The dossier's sixth kill criterion as a prediction: the width of a K = 113 two-arm
          contrast under live against frozen (deterministic) rerun noise.
  CL      The closed-loop A0/A1 design the slate proposed (R = 3, K = 113, live serving) under
          no masking effect and under the redundancy prediction: how often each slate reading
          fires. This is why the closed loop is not in this first step.
  PRED    Registered closed-loop predictions for a later Stage D from the step-kick model and
          S1a's records.

Usage (from the worktree root):

    python power_r01.py --a1 program/evidence/2026-10-10/q2-stage1-analysis/a1.jsonl \
        --census program/evidence/2026-10-11/r01-stage-a0/census.json --out power-r01.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

SEEDS = (42, 43, 44)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cp_lower_one_sided(k: int, n: int, alpha: float = 0.05) -> float:
    return 0.0 if k == 0 else float(stats.beta.ppf(alpha, k, n - k + 1))


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


# --------------------------------------------------------------------------- B_det
def block_b_det(n: int = 320, clusters: int = 40, reps: int = 20000) -> dict:
    kstar = next(k for k in range(n + 1) if cp_lower_one_sided(k, n) > 0.01)
    out = {"n_pairs": n, "rule": {"DET_OK": "0 of n replica pairs differ in reply text (exact one-sided 95% upper bound "
                                            f"{1 - 0.05 ** (1 / n):.4f})",
                                  "DET_UNATTAINABLE": f"one-sided 95% Clopper-Pearson lower bound above 1%, i.e. k >= {kstar}",
                                  "DET_NEAR": f"1 <= k <= {kstar - 1}"},
           "k_star": kstar, "exact_binomial": [], "beta_binomial_by_episode": []}
    for p in (0.0, 0.001, 0.0025, 0.005, 0.01, 0.02, 0.03, 0.05):
        pk = stats.binom.pmf(np.arange(n + 1), n, p) if p > 0 else np.r_[1.0, np.zeros(n)]
        out["exact_binomial"].append({"p": p, "P_DET_OK": round(float(pk[0]), 4),
                                      "P_DET_UNATTAINABLE": round(float(pk[kstar:].sum()), 4),
                                      "P_DET_NEAR": round(float(pk[1:kstar].sum()), 4)})
    m = n // clusters
    for rho in (0.2, 0.5):
        rows = []
        for p in (0.001, 0.0025, 0.005, 0.01, 0.02, 0.03, 0.05):
            res = []
            for seed in SEEDS:
                rng = np.random.default_rng(seed)
                a = p * (1 - rho) / rho
                b = (1 - p) * (1 - rho) / rho
                pc = rng.beta(a, b, size=(reps, clusters))
                k = rng.binomial(m, pc).sum(axis=1)
                res.append(((k == 0).mean(), (k >= kstar).mean()))
            r = np.mean(res, axis=0)
            rows.append({"p": p, "icc": rho, "P_DET_OK": round(float(r[0]), 4), "P_DET_UNATTAINABLE": round(float(r[1]), 4)})
        out["beta_binomial_by_episode"].extend(rows)
    return out


# --------------------------------------------------------------------------- B_read
def cluster_boot_bounds(k: np.ndarray, m: int, rng, nboot: int) -> tuple[np.ndarray, np.ndarray]:
    """k: (reps, clusters) events per cluster, m per cluster. Percentile 95% bounds of the mean."""
    reps, c = k.shape
    lo = np.empty(reps)
    hi = np.empty(reps)
    for i in range(reps):
        idx = rng.integers(0, c, size=(nboot, c))
        means = k[i][idx].sum(axis=1) / (c * m)
        lo[i], hi[i] = np.quantile(means, [0.025, 0.975])
    return lo, hi


def block_b_read(reps: int = 400, nboot: int = 600) -> dict:
    clusters, m = 40, 8
    out = {"design": "40 episodes x 8 requests (steps 1-8), episode-cluster percentile bootstrap",
           "text_level": {"SUFFICIENT": "lower bound of h - floor above 0.20", "INERT": "upper bound below 0.05"},
           "ir_level": {"SUFFICIENT": "lower bound above 0.02", "INERT": "upper bound below 0.01"},
           "floor_assumed": 0.0, "rows": []}
    for level, (suf, inert), grid in (("text", (0.20, 0.05), (0.0, 0.01, 0.03, 0.05, 0.10, 0.20, 0.30, 0.40, 0.60)),
                                      ("ir", (0.02, 0.01), (0.0, 0.002, 0.005, 0.01, 0.02, 0.03, 0.05, 0.08))):
        for sd in (0.5, 1.0):
            for h in grid:
                agg = []
                for seed in SEEDS:
                    rng = np.random.default_rng(seed)
                    if h == 0:
                        pc = np.zeros((reps, clusters))
                    else:
                        mu = math.log(h / (1 - h))
                        pc = 1 / (1 + np.exp(-(mu + sd * rng.standard_normal((reps, clusters)))))
                        pc *= h / pc.mean()  # keep the mean hazard at h
                        pc = np.clip(pc, 0, 1)
                    k = rng.binomial(m, pc)
                    lo, hi = cluster_boot_bounds(k, m, rng, nboot)
                    agg.append(((lo > suf).mean(), (hi < inert).mean()))
                a = np.mean(agg, axis=0)
                out["rows"].append({"level": level, "episode_logit_sd": sd, "true_h": h,
                                    "P_SUFFICIENT": round(float(a[0]), 3), "P_INERT": round(float(a[1]), 3),
                                    "P_PARTIAL": round(float(1 - a[0] - a[1]), 3)})
    return out


# --------------------------------------------------------------------------- A1_cen
def block_a1(n: int = 113) -> dict:
    rows = []
    for s in (0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50):
        pk = stats.binom.pmf(np.arange(n + 1), n, s)
        multi = sum(pk[k] for k in range(n + 1) if wilson(k, n)[0] > 0.20)
        clock = sum(pk[k] for k in range(n + 1) if wilson(k, n)[1] < 0.20)
        rows.append({"true_non_clock_share": s, "P_MULTI_REGION": round(float(multi), 4),
                     "P_CLOCK_ONLY": round(float(clock), 4), "P_UNRESOLVED": round(float(1 - multi - clock), 4)})
    return {"n_task_pairs": n, "statistic": "share of differing cross-boot step-1 pairs with any differing pixel outside the clock box",
            "rule": {"MULTI_REGION": "Wilson 95% lower bound above 0.20", "CLOCK_ONLY": "Wilson 95% upper bound below 0.20"},
            "records_prior": "A0.7: 10 of 25 clearly same-minute within-session pairs differ (0.40, Wilson 0.23-0.59)",
            "rows": rows}


# --------------------------------------------------------------------------- C_env
def block_c(tasks: int = 113, per: int = 4, reps: int = 2000, nboot: int = 600) -> dict:
    exact_task_ub = 1 - 0.05 ** (1 / tasks)
    out = {"design": f"{tasks} tasks x {per} recorded episodes, replay r1 against replay r2 (binarized verdict)",
           "rule": {"zero_events": f"ENV_BOUNDED (exact one-sided task-level 95% upper bound {exact_task_ub:.4f} < 0.03)",
                    "ENV_MATERIAL": "task-cluster bootstrap 95% lower bound above 0.02",
                    "ENV_BOUNDED": "upper bound below 0.03", "ENV_UNRESOLVED": "otherwise"},
           "rows": []}
    for pattern in ("homogeneous", "concentrated_10pct_tasks"):
        for e in (0.0, 0.005, 0.01, 0.02, 0.03, 0.05, 0.08):
            agg = []
            for seed in SEEDS:
                rng = np.random.default_rng(seed)
                if pattern == "homogeneous":
                    pt = np.full((reps, tasks), e)
                else:
                    flaky = rng.random((reps, tasks)) < 0.10
                    pt = np.where(flaky, min(1.0, e / 0.10), 0.0)
                k = rng.binomial(per, pt)
                tot = k.sum(axis=1)
                mat = np.zeros(reps, bool)
                bnd = np.zeros(reps, bool)
                for i in range(reps):
                    if tot[i] == 0:
                        bnd[i] = True
                        continue
                    idx = rng.integers(0, tasks, size=(nboot, tasks))
                    means = k[i][idx].sum(axis=1) / (tasks * per)
                    lo, hi = np.quantile(means, [0.025, 0.975])
                    mat[i] = lo > 0.02
                    bnd[i] = hi < 0.03
                agg.append((mat.mean(), bnd.mean()))
            a = np.mean(agg, axis=0)
            out["rows"].append({"pattern": pattern, "true_e": e, "P_ENV_MATERIAL": round(float(a[0]), 3),
                                "P_ENV_BOUNDED": round(float(a[1]), 3), "P_ENV_UNRESOLVED": round(float(1 - a[0] - a[1]), 3)})
    return out


# --------------------------------------------------------------------------- shared S1a inputs
def s1a_counts(a1: Path) -> np.ndarray:
    cells = defaultdict(list)
    for line in a1.read_text().splitlines():
        r = json.loads(line)
        if r["size"] == "4B" and r["harness"] == "H-OSW-fixed":
            cells[r["task_id"]].append(1 if float(r["score"]) == 1.0 else 0)
    assert len(cells) == 113 and all(len(v) == 4 for v in cells.values())
    return np.array([sum(v) for _, v in sorted(cells.items())])


def fit_beta_binomial(k: np.ndarray, n: int = 4) -> tuple[float, float]:
    from scipy.optimize import minimize
    from scipy.special import betaln, gammaln

    def nll(x):
        a, b = np.exp(x)
        return -np.sum(gammaln(n + 1) - gammaln(k + 1) - gammaln(n - k + 1) + betaln(k + a, n - k + b) - betaln(a, b))
    res = minimize(nll, np.log([0.3, 0.6]), method="Nelder-Mead")
    a, b = np.exp(res.x)
    return float(a), float(b)


# --------------------------------------------------------------------------- K6
def block_k6(counts: np.ndarray, reps: int = 4000) -> dict:
    a, b = fit_beta_binomial(counts)
    K = len(counts)
    out = {"propensity_model": {"beta_a": round(a, 4), "beta_b": round(b, 4),
                                "note": "beta-binomial fitted to S1a 4B H-OSW-fixed per-task counts (4 reruns, 113 tasks)"},
           "rows": []}
    for R in (1, 2, 4):
        wl, wf, vl, vf = [], [], [], []
        for seed in SEEDS:
            rng = np.random.default_rng(seed)
            p = rng.beta(a, b, size=(reps, K))
            # live: R independent reruns per arm; frozen: one draw per (task, arm) repeated R times
            live = rng.binomial(R, p) / R - rng.binomial(R, p) / R
            frozen = rng.binomial(1, p) - rng.binomial(1, p)
            for d, wbuf, vbuf in ((live, wl, vl), (frozen, wf, vf)):
                se = d.std(axis=1, ddof=1) / math.sqrt(K)
                wbuf.append(np.mean(2 * stats.t.ppf(0.95, K - 1) * se))
                vbuf.append(np.mean(d.var(axis=1, ddof=1)))
        w_l, w_f = float(np.mean(wl)), float(np.mean(wf))
        out["rows"].append({"reruns_per_arm": R, "width90_live_pp": round(100 * w_l, 2), "width90_frozen_pp": round(100 * w_f, 2),
                            "frozen_over_live": round(w_f / w_l, 3), "shrink_share": round(1 - w_f / w_l, 3),
                            "var_task_diff_live": round(float(np.mean(vl)), 4), "var_task_diff_frozen": round(float(np.mean(vf)), 4)})
    out["reading"] = ("A frozen (deterministic) stack gives each (task, arm) one fixed draw. Two arms with different prompts cannot "
                      "share it, so at one rerun per arm the width does not shrink (K6 fires by construction) and at R > 1 the "
                      "frozen design is wider: extra reruns add nothing. Registered as prediction P-K6, not as a kill.")
    return out


# --------------------------------------------------------------------------- CL
def block_cl(counts: np.ndarray, reps: int = 3000, nboot: int = 500) -> dict:
    a, b = fit_beta_binomial(counts)
    K = len(counts)
    out = {"design": "slate Stage C: arms A0 (live) and A1 (clock masked), R = 3 each, K = 113, live S1a serving",
           "readings": {"CLOCK_DOMINANT": "reduction D_w(A0) - D_w(A1) >= D_w(A0)/2 with lower bound > 0",
                        "NOT_CLOCK (slate)": "one-sided 95% upper bound of the reduction below 2 pp",
                        "NOT_CLOCK (restated, half)": "upper bound below D_w(A0)/2"},
           "rows": []}
    pairs = [(0, 1), (0, 2), (1, 2)]
    for label, frac in (("no masking effect (redundancy)", 0.0), ("true 50% reduction", 0.5), ("true 100% reduction", 1.0)):
        res = []
        for seed in SEEDS:
            rng = np.random.default_rng(seed)
            dom = slate_nc = half_nc = 0
            for _ in range(reps):
                p = rng.beta(a, b, size=K)
                y0 = rng.binomial(1, np.repeat(p[:, None], 3, axis=1))
                if frac == 0.0:
                    y1 = rng.binomial(1, np.repeat(p[:, None], 3, axis=1))
                else:
                    # a fraction of tasks become rerun-identical (frozen) under the mask
                    frz = rng.random(K) < frac
                    y1 = rng.binomial(1, np.repeat(p[:, None], 3, axis=1))
                    y1[frz] = np.repeat(rng.binomial(1, p[frz])[:, None], 3, axis=1)
                d0 = np.mean([(y0[:, i] != y0[:, j]) for i, j in pairs], axis=0)
                d1 = np.mean([(y1[:, i] != y1[:, j]) for i, j in pairs], axis=0)
                idx = rng.integers(0, K, size=(nboot, K))
                red = d0[idx].mean(axis=1) - d1[idx].mean(axis=1)
                est = d0.mean() - d1.mean()
                lo95_2s = np.quantile(red, 0.025)
                ub1 = np.quantile(red, 0.95)
                if est >= d0.mean() / 2 and lo95_2s > 0:
                    dom += 1
                if ub1 < 0.02:
                    slate_nc += 1
                if ub1 < d0.mean() / 2:
                    half_nc += 1
            res.append((dom / reps, slate_nc / reps, half_nc / reps))
        r = np.mean(res, axis=0)
        out["rows"].append({"truth": label, "P_CLOCK_DOMINANT": round(float(r[0]), 3), "P_NOT_CLOCK_slate": round(float(r[1]), 3),
                            "P_NOT_CLOCK_half": round(float(r[2]), 3)})
    out["reading"] = ("Under live serving the records predict no masking effect (A0.5: 2 of 19 identical-start pairs discordant against "
                      "90 of 885). Then the slate's design reads PARTIAL most of the time and its NOT_CLOCK fires by chance, while "
                      "the restated NOT_CLOCK fires reliably but means 'clock not necessary given live serving', not 'no clock "
                      "effect'. The closed loop is therefore deferred to a Stage D crossed with deterministic serving.")
    return out


# --------------------------------------------------------------------------- PRED
def block_pred(census: dict) -> dict:
    a5 = census["A0_5_outcome_discordance"]
    a4 = census["A0_4_survival_within"]["share_identical_through_step_k"]["ir"]
    never_all = census["A0_4_survival_within"]["share_identical_through_step_k"]["ir"]["never"]
    within = a5["within_all"]
    q = within["k"] / (within["n"] - never_all)  # discordance among pairs whose IR diverged (identical-IR pairs: 0 events)
    rows = []
    for arm, n_never, src in (
            ("S1a (live clock, live serving)", never_all / within["n"], "records A0.4"),
            ("clock masked, live serving", a5["within_identical_step1_never_ir_divergent"] / a5["within_identical_step1_request"]["n"],
             "records: identical-start pairs never IR-divergent (2 of 19)"),
            ("live clock, deterministic serving", None, "1 - Stage B h_c(IR) per step compounded; not yet measured"),
            ("clock masked, deterministic serving", None, "Stage C masked-observation identity per step compounded; not yet measured")):
        if n_never is None:
            rows.append({"arm": arm, "P_never_diverge": None, "D_w_pred": None, "source": src})
        else:
            rows.append({"arm": arm, "P_never_diverge": round(n_never, 4), "D_w_pred": round((1 - n_never) * q, 4), "source": src})
    grid = []
    for s in (0.90, 0.95, 0.98, 0.99, 0.995, 1.0):
        n_never = s ** 12.5
        grid.append({"per_step_identity": s, "P_never_diverge_12.5_steps": round(n_never, 4), "D_w_pred": round((1 - n_never) * q, 4)})
    return {"model": "D_w(arm) = (1 - N_arm) * q + e, N_arm = P(IR sequences never diverge); q = verdict discordance among IR-diverged pairs",
            "q_within_all_sizes": round(q, 4), "e_assumed": 0.0, "rows": rows, "frozen_regime_grid": grid}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--a1", type=Path, required=True)
    ap.add_argument("--census", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    counts = s1a_counts(args.a1)
    census = json.loads(args.census.read_text())
    f = 0.25 if args.quick else 1.0
    out = {"schema": "r01-power-v1", "seeds": list(SEEDS),
           "inputs": {"a1_jsonl_sha256": sha(args.a1), "census_sha256": sha(args.census),
                      "s1a_4b_osw_counts_hist": {str(i): int((counts == i).sum()) for i in range(5)}},
           "B_det": block_b_det(reps=int(20000 * f)),
           "B_read": block_b_read(reps=int(400 * f)),
           "A1_cen": block_a1(),
           "C_env": block_c(reps=int(2000 * f)),
           "K6": block_k6(counts, reps=int(4000 * f)),
           "CL": block_cl(counts, reps=int(3000 * f)),
           "PRED": block_pred(census)}
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: (v if k in ("inputs",) else "ok") for k, v in out.items() if k != "schema"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
