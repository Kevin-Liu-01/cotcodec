#!/usr/bin/env python3
"""S2: operating characteristics of every registered threshold of e5-gate-fertility-decomposition-v1.

The primary estimand beta (estimator.py) is a mean of paired per-episode differences
Y(clamp) - Y(native) in {-100, 0, +100}, pooled over K = 1 and K = 4 and divided by
ln(f_p). Under the paired design only two numbers set its sampling distribution: the
mean shift delta and the discordance d = P(Y(clamp) != Y(native)). Clustering enters
through retention-span passages: each passage carries c episodes at each of the two
loads (2c per cluster), and the per-passage shift varies with SD tau.

Reported, for n episodes per load in {600, 1000, 1500} (c = 4):
  1. P(KILL), P(MATERIAL), P(INCONCLUSIVE) per subject over true beta x d x tau, and the
     joint two-subject probabilities under independence;
  2. the NO_COST rule (total cost per log-f unit, upper bound below 3) over true TE and
     its discordance;
  3. coverage of the cluster-robust normal interval used here against the registered
     percentile cluster bootstrap (B = 2,000) at four settings;
  4. misclassification probabilities of the floor gates (canonical K = 4 accuracy at
     least 50; native accuracy at the primary f at least 30) at n = 1000.

All randomness is seeded (42, 43, 44 for the three blocks of replicates). The
discordance values are assumptions, not measurements: the kill-shot cell's 0.1 to 0.3
range for r-arm discordance, extended down to 0.05 because the clamp changes decay mass
only on the retention span.

Usage: python power-sim.py <out.json>
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estimator as est  # noqa: E402

FP = 2.7
LNF = math.log(FP)
C = 4  # episodes per passage per load
NS = (600, 1000, 1500)
BETAS = (0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0)
DISC = (0.05, 0.10, 0.20, 0.30)
TAUS = (0.0, 0.02)
REPS = 4000
SEEDS = (42, 43, 44)


def simulate_diffs(rng, reps: int, n_per_load: int, delta: float, d: float, tau: float) -> np.ndarray:
    """Return per-episode paired differences [reps, clusters, 2C] in points."""
    g = n_per_load // C
    dc = delta + tau * rng.standard_normal((reps, g, 1))
    p01 = np.clip((d + dc) / 2, 0, d)
    p10 = d - p01
    u = rng.random((reps, g, 2 * C))
    return np.where(u < p01, 100.0, np.where(u < p01 + p10, -100.0, 0.0))


def cluster_normal_batch(diffs: np.ndarray, z: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    reps, g, m = diffs.shape
    sums = diffs.sum(2)
    n = g * m
    mean = sums.sum(1) / n
    resid = sums - mean[:, None] * m
    var = g / (g - 1) * (resid ** 2).sum(1) / n ** 2
    se = np.sqrt(var)
    return mean, mean - z * se, mean + z * se


def oc_primary() -> list[dict]:
    z = stats.norm.ppf(0.95)
    rows = []
    for n in NS:
        for beta in BETAS:
            delta = beta * LNF / 100.0
            for d in DISC:
                if delta > d:
                    continue
                for tau in TAUS:
                    kill = mat = 0
                    for s_i, seed in enumerate(SEEDS):
                        rng = np.random.default_rng([seed, n, int(beta * 10), int(d * 100), int(tau * 100)])
                        reps = REPS // len(SEEDS) + (1 if s_i < REPS % len(SEEDS) else 0)
                        diffs = simulate_diffs(rng, reps, n, delta, d, tau)
                        mean, lo, hi = cluster_normal_batch(diffs, z)
                        b, bl, bh = mean / LNF, lo / LNF, hi / LNF
                        kill += int((bh < est.LINE).sum())
                        mat += int(((b >= est.LINE) & (bl > 0) & ~(bh < est.LINE)).sum())
                    pk, pm = kill / REPS, mat / REPS
                    rows.append({"n_per_load": n, "beta_true": beta, "discordance": d, "tau": tau,
                                 "P_KILL": pk, "P_MATERIAL": pm, "P_INCONCLUSIVE": 1 - pk - pm,
                                 "joint_both_KILL": pk ** 2, "joint_both_MATERIAL": pm ** 2})
    return rows


def oc_no_cost() -> list[dict]:
    z = stats.norm.ppf(0.95)
    rows = []
    for n in (1000,):
        for te in (0.0, 1.0, 2.0, 3.0, 5.0, 10.0, 20.0):
            delta = te * LNF / 100.0
            for d in (0.10, 0.30, 0.50):
                if delta > d:
                    continue
                rng = np.random.default_rng([43, int(te * 10), int(d * 100)])
                diffs = simulate_diffs(rng, REPS, n, delta, d, 0.02)
                _, _, hi = cluster_normal_batch(diffs, z)
                rows.append({"n_per_load": n, "te_true_per_logf": te, "discordance": d,
                             "P_NO_COST": float((hi / LNF < est.LINE).mean())})
    return rows


def coverage_check() -> list[dict]:
    rows = []
    z = stats.norm.ppf(0.95)
    for n, beta, d, tau in ((1000, 0.0, 0.10, 0.02), (1000, 3.0, 0.20, 0.02),
                            (600, 3.0, 0.30, 0.0), (1000, 5.0, 0.10, 0.02)):
        delta = beta * LNF / 100.0
        rng = np.random.default_rng([44, n, int(beta * 10), int(d * 100)])
        reps = 400
        diffs = simulate_diffs(rng, reps, n, delta, d, tau)
        mean, lo, hi = cluster_normal_batch(diffs, z)
        cov_norm = float(((lo <= delta * 100) & (hi >= delta * 100)).mean())
        cov_boot, agree = 0, 0
        for r in range(reps):
            clusters = [diffs[r, j] for j in range(diffs.shape[1])]
            iv = est.cluster_bootstrap_mean(clusters, seed=est.BOOT_SEED + r)
            cov_boot += int(iv.lo <= delta * 100 <= iv.hi)
            agree += int((iv.hi / LNF < est.LINE) == (hi[r] / LNF < est.LINE))
        rows.append({"n_per_load": n, "beta_true": beta, "discordance": d, "tau": tau, "reps": reps,
                     "coverage_cluster_normal_90": cov_norm, "coverage_cluster_bootstrap_90": cov_boot / reps,
                     "kill_decision_agreement": agree / reps})
    return rows


def floor_gates() -> list[dict]:
    rows = []
    n = 1000
    for floor, name in ((est.FLOOR_CANONICAL, "canonical_K4_at_least_50"), (est.FLOOR_NATIVE, "native_fp_K4_at_least_30")):
        for true in (floor - 6, floor - 3, floor, floor + 3, floor + 6):
            p = true / 100.0
            # design effect 1.3 for passage clustering (assumed)
            se = math.sqrt(p * (1 - p) / n * 1.3) * 100
            pass_prob = 1 - stats.norm.cdf((floor - true) / se)
            rows.append({"gate": name, "true_accuracy": true, "P_pass": float(pass_prob), "se_points": se})
    return rows


def main() -> int:
    t0 = time.time()
    out = {"params": dict(FP=FP, C=C, NS=NS, BETAS=BETAS, DISC=DISC, TAUS=TAUS, REPS=REPS, SEEDS=SEEDS,
                          LINE=est.LINE, LEVEL=est.LEVEL),
           "primary_oc": oc_primary()}
    print("primary done", round(time.time() - t0, 1), flush=True)
    out["no_cost_oc"] = oc_no_cost()
    out["coverage"] = coverage_check()
    print("coverage done", round(time.time() - t0, 1), flush=True)
    out["floor_gates"] = floor_gates()
    out["elapsed_s"] = round(time.time() - t0, 1)
    Path(sys.argv[1]).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    for r in out["primary_oc"]:
        if r["n_per_load"] == 1000 and r["tau"] == 0.02:
            print(r["beta_true"], r["discordance"], round(r["P_KILL"], 3), round(r["P_MATERIAL"], 3))
    print(json.dumps(out["coverage"], indent=0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
