#!/usr/bin/env python3
"""G2-RL gauntlet: operating characteristics of the pilot's readouts and of the full design's
decision rules (CPU, numpy and scipy; seeds 42, 43, 44).

Blocks:

  MDE     Minimum detectable effects (alpha 0.05 two-sided, power 0.8) for a paired t on n pairs
          and a two-sample t on n runs per arm (noncentral t), and the smallest exact p-values a
          rank or sign test can reach at n = 3..8. These are why the design does not test learning
          endpoints at 3 seeds.
  MANIP   The pilot's in-loop manipulation check (P3): the bf16/fp32 k3 ratio over 3 x 256
          rollouts per arm, by a prompt-cluster bootstrap of the committed G2b seed-42 4B and 9B
          sequences cut at 16,384 tokens (the gate's thresholds 4 and 2), and the extra trainer
          noise (added to both arms' k3) at which the point ratio falls to 4 and to 2.
  GRAD    The pilot's gradient-bias readout (P3) in a Gaussian model: R = 3 gradient estimates per
          arm, noise of total variance sigma^2 spread over d_eff directions, a bias of squared norm
          kappa sigma^2, bf16 noise inflated by eta; the estimator
          kappa_hat = [D_FB - (D_FF + D_BB)/2] / (D_FF / 2) (D = mean squared distance between
          estimates), its permutation test over the 6 batches (20 splits; smallest one-sided p 0.05),
          and the TIS recovery estimator r_hat = 1 - ||b_T||^2_hat / ||b||^2_hat.
  FULL    The full design's provisional learning rule (Stage 1: 4 runs per arm, Welch on the
          per-run held-out AUC; equivalence margin 3 points by TOST; collapse by Fisher exact;
          sample-size re-estimation from the 80% upper confidence limit of the pooled SD, Browne
          1995, extending to at most 6 runs per arm) under effect, SD and collapse scenarios, with
          the probability of each reading and the expected number of runs.

Usage (repo root): uv run --locked python <this file> --mismatch <mismatch-by-cap.json dir> --out <json>
"""

from __future__ import annotations

import argparse
import json
import math
from itertools import combinations
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[5]
SEEDS = (42, 43, 44)


# --------------------------------------------------------------------------- MDE


def mde_paired(n: int, alpha: float = 0.05, power: float = 0.8) -> float:
    df = n - 1
    tcrit = stats.t.ppf(1 - alpha / 2, df)
    lo, hi = 0.01, 20.0
    for _ in range(80):
        d = (lo + hi) / 2
        nc = d * math.sqrt(n)
        pw = 1 - stats.nct.cdf(tcrit, df, nc) + stats.nct.cdf(-tcrit, df, nc)
        lo, hi = (d, hi) if pw < power else (lo, d)
    return hi


def mde_two_sample(n: int, alpha: float = 0.05, power: float = 0.8) -> float:
    df = 2 * n - 2
    tcrit = stats.t.ppf(1 - alpha / 2, df)
    lo, hi = 0.01, 20.0
    for _ in range(80):
        d = (lo + hi) / 2
        nc = d * math.sqrt(n / 2)
        pw = 1 - stats.nct.cdf(tcrit, df, nc) + stats.nct.cdf(-tcrit, df, nc)
        lo, hi = (d, hi) if pw < power else (lo, d)
    return hi


def block_mde() -> dict:
    rows = []
    for n in range(3, 11):
        rows.append(
            {
                "n": n,
                "paired_t_mde_sd_of_difference": round(mde_paired(n), 3),
                "two_sample_t_mde_cohen_d": round(mde_two_sample(n), 3),
                "rank_test_min_p_two_sided_complete_separation": round(2 / math.comb(2 * n, n), 4),
                "sign_test_min_p_two_sided": round(2 * 0.5**n, 4),
            }
        )
    return {"alpha": 0.05, "power": 0.8, "rows": rows}


# --------------------------------------------------------------------------- MANIP


def load_seq(npz: Path, arm: int, cap: int) -> tuple[np.ndarray, np.ndarray]:
    raw = np.load(npz)
    off = raw["offsets"]
    n, k3 = [], []
    for i in np.flatnonzero(raw["arm"] == arm):
        d = raw["d_dec"][off[i] : off[i + 1]][:cap].astype(np.float64)
        d = d[np.isfinite(d)]
        lw = -d
        n.append(d.size)
        k3.append((np.expm1(lw) - lw).sum())
    return np.array(n, float), np.array(k3)


def block_manip(reps: int) -> dict:
    out = {}
    cap = 16384
    for model in ("qwen3.5-4b", "qwen3.5-9b"):
        npz = ROOT / f"program/evidence/2026-10-15/g2b-state-dtype/data/per-token-{model}-seed42.npz"
        nf, kf = load_seq(npz, 0, cap)
        nb, kb = load_seq(npz, 1, cap)
        point_f, point_b = kf.sum() / nf.sum(), kb.sum() / nb.sum()
        res = {"k3_fp32": point_f, "k3_bf16": point_b, "point_ratio": point_b / point_f, "by_seed": {}}
        for seed in SEEDS:
            rng = np.random.default_rng(seed)
            ratios = np.empty(reps)
            for r in range(reps):
                # 32 prompts per arm, each prompt's sequence standing for its 24 rollouts
                pf = rng.integers(0, nf.size, 32)
                pb = rng.integers(0, nb.size, 32)
                ratios[r] = (kb[pb].sum() / nb[pb].sum()) / (kf[pf].sum() / nf[pf].sum())
            res["by_seed"][str(seed)] = {
                "ratio_p2.5": float(np.quantile(ratios, 0.025)),
                "ratio_median": float(np.median(ratios)),
                "ratio_p97.5": float(np.quantile(ratios, 0.975)),
                "P_ratio_lt_4": float(np.mean(ratios < 4)),
                "P_ratio_lt_2": float(np.mean(ratios < 2)),
            }
        for target in (4.0, 2.0):
            res[f"extra_trainer_k3_for_ratio_{int(target)}"] = (point_b - target * point_f) / (target - 1)
            res[f"extra_trainer_k3_for_ratio_{int(target)}_in_fp32_floors"] = (
                (point_b - target * point_f) / (target - 1) / point_f
            )
        out[model] = res
    return {"cap": cap, "rollouts_per_arm": 768, "prompts_per_arm": 32, "reps": reps, "models": out}


# --------------------------------------------------------------------------- GRAD


def sqdist_matrix(x: np.ndarray) -> np.ndarray:
    g = x @ x.T
    d = np.diag(g)
    return d[:, None] + d[None, :] - 2 * g


def split_stat(dm: np.ndarray, a: list[int], b: list[int]) -> float:
    """D_ab - (D_aa + D_bb) / 2 from a squared-distance matrix (D = mean over distinct pairs)."""

    dab = dm[np.ix_(a, b)].mean()
    daa = dm[np.ix_(a, a)][np.triu_indices(len(a), 1)].mean()
    dbb = dm[np.ix_(b, b)][np.triu_indices(len(b), 1)].mean()
    return float(dab - (daa + dbb) / 2)


def perm_p(dm: np.ndarray, r: int) -> float:
    """One-sided exact permutation p over all splits of the 2r batches into two groups of r.
    The statistic is symmetric under swapping the groups, so the smallest attainable p is
    2 / C(2r, r): 0.10 at r = 3 and 0.029 at r = 4."""

    idx = list(range(2 * r))
    obs = split_stat(dm, idx[:r], idx[r:])
    vals = [split_stat(dm, list(a), [i for i in idx if i not in a]) for a in combinations(idx, r)]
    return float(np.mean(np.array(vals) >= obs - 1e-12))


def split_weights(r: int) -> np.ndarray:
    """Weight matrices W_s with stat_s = sum_ij dm_ij W_s,ij equal to split_stat for every split s
    of the 2r batches into two groups of r (split 0 is the observed one: the first r batches)."""

    n = 2 * r
    splits = list(combinations(range(n), r))
    w = np.zeros((len(splits), n, n))
    pairs = math.comb(r, 2)
    for k, a in enumerate(splits):
        m = np.zeros(n)
        m[list(a)] = 1.0
        wab = np.outer(m, 1 - m) / (r * r)
        waa = (np.outer(m, m) - np.diag(m)) / (2 * pairs)
        wbb = (np.outer(1 - m, 1 - m) - np.diag(1 - m)) / (2 * pairs)
        w[k] = wab - (waa + wbb) / 2
    return w


def batched_sqdist(x: np.ndarray) -> np.ndarray:
    g = np.einsum("rid,rjd->rij", x, x)
    d = np.einsum("rii->ri", g)
    return d[:, :, None] + d[:, None, :] - 2 * g


def selfcheck_grad() -> dict:
    """The vectorized split statistics and permutation p equal the loop reference."""

    rng = np.random.default_rng(42)
    worst = 0.0
    for r in (3, 4):
        w = split_weights(r)
        for _ in range(20):
            x = rng.normal(size=(1, 2 * r, 50))
            dm = batched_sqdist(x)
            vec = np.einsum("rij,sij->rs", dm, w)[0]
            idx = list(range(2 * r))
            ref = np.array([split_stat(dm[0], list(a), [i for i in idx if i not in a]) for a in combinations(idx, r)])
            worst = max(worst, float(np.max(np.abs(vec - ref))))
            p_vec = float(np.mean(vec >= vec[0] - 1e-12))
            assert abs(p_vec - perm_p(dm[0], r)) < 1e-12
    assert worst < 1e-9, worst
    return {"max_abs_difference_split_stat": worst, "perm_p_equal": True}


def block_grad(reps: int) -> dict:
    """Vectorized over replicates; numerically identical in method to split_stat and perm_p
    (checked by selfcheck_grad)."""

    dim = 2000
    sigma2 = 1.0
    signal = 0.25  # ||mu||^2 / sigma^2 per batch estimate (low, after Ilyas et al. 1811.02553)
    tau = 0.05  # extra variance TIS reweighting adds, as a share of sigma^2
    out = []
    for r in (3, 4):
        w = split_weights(r)
        tri = np.triu_indices(r, 1)
        for d_eff in (10, 100, 1000):
            for eta in (0.0, 0.2):
                for kappa in (0.0, 0.05, 0.1, 0.25, 0.5, 1.0):
                    for recover in ((0.0, 0.5, 1.0) if kappa >= 0.25 else (None,)):
                        kh, ps, rh = [], [], []
                        for seed in SEEDS:
                            rng = np.random.default_rng(
                                seed * 100000 + r * 10000 + d_eff + int(100 * kappa) + int(10 * eta)
                            )

                            def unit(scale: float) -> np.ndarray:
                                v = rng.normal(size=(reps, dim))
                                norms = np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-12)
                                return v * (math.sqrt(scale * sigma2) / norms)

                            def noise(scale: float) -> np.ndarray:
                                z = np.zeros((reps, r, dim))
                                z[:, :, :d_eff] = rng.normal(size=(reps, r, d_eff)) * math.sqrt(scale * sigma2 / d_eff)
                                return z

                            mu = unit(signal)[:, None, :]
                            bias = unit(kappa)[:, None, :] if kappa > 0 else np.zeros((reps, 1, dim))
                            f = mu + noise(1.0)
                            nb = noise(1.0 + eta)
                            b = mu + bias + nb
                            dm = batched_sqdist(np.concatenate([f, b], axis=1))
                            st = np.einsum("rij,sij->rs", dm, w)
                            obs = st[:, 0]
                            dff = dm[:, :r, :r][:, tri[0], tri[1]].mean(axis=1)
                            kh.extend((obs / (dff / 2)).tolist())
                            ps.extend(np.mean(st >= obs[:, None] - 1e-12, axis=1).tolist())
                            if recover is not None:
                                bt = mu + math.sqrt(1 - recover) * bias + nb + noise(tau)
                                dmt = batched_sqdist(np.concatenate([f, bt], axis=1))
                                obs_t = np.einsum("rij,ij->r", dmt, w[0])
                                with np.errstate(divide="ignore", invalid="ignore"):
                                    rh.extend(np.where(obs > 0, 1 - obs_t / obs, np.nan).tolist())
                        row = {
                            "batches_per_arm": r,
                            "d_eff": d_eff,
                            "eta_bf16_extra_noise": eta,
                            "kappa_true": kappa,
                            "kappa_hat_p5": float(np.quantile(kh, 0.05)),
                            "kappa_hat_median": float(np.median(kh)),
                            "kappa_hat_p95": float(np.quantile(kh, 0.95)),
                            "power_perm_p_le_0.05": float(np.mean(np.array(ps) <= 0.05 + 1e-9)),
                            "power_perm_p_le_0.10": float(np.mean(np.array(ps) <= 0.10 + 1e-9)),
                        }
                        if recover is not None:
                            rr = np.array(rh)
                            rr = rr[np.isfinite(rr)]
                            row.update(
                                {
                                    "tis_recovery_true": recover,
                                    "r_hat_p10": float(np.quantile(rr, 0.1)),
                                    "r_hat_median": float(np.median(rr)),
                                    "r_hat_p90": float(np.quantile(rr, 0.9)),
                                }
                            )
                        out.append(row)
    return {
        "model": "g = mu + noise (d_eff isotropic directions, total variance sigma^2) [+ bias for bf16]; r batches per arm",
        "dim": dim,
        "signal_mu_sq_over_sigma_sq": signal,
        "tis_extra_noise_share": tau,
        "reps_per_seed": reps,
        "selfcheck": selfcheck_grad(),
        "rows": out,
    }


# --------------------------------------------------------------------------- FULL


def welch(a: np.ndarray, b: np.ndarray) -> tuple[float, float, float]:
    """Difference b - a, its SE and Welch df."""

    va, vb = a.var(ddof=1) / a.size, b.var(ddof=1) / b.size
    se = math.sqrt(va + vb)
    df = (va + vb) ** 2 / (va**2 / (a.size - 1) + vb**2 / (b.size - 1))
    return float(b.mean() - a.mean()), se, df


def read_learning(f: np.ndarray, b: np.ndarray, margin: float) -> str:
    diff, se, df = welch(f, b)
    t95 = stats.t.ppf(0.975, df)
    t90 = stats.t.ppf(0.95, df)
    if abs(diff) > t95 * se:
        return "CHANGES"
    if abs(diff) + t90 * se < margin:
        return "NO_CHANGE_AT_MARGIN"
    return "INCONCLUSIVE"


def selfcheck_full() -> dict:
    """read_vec equals the scalar reference read_learning."""

    rng = np.random.default_rng(42)
    f, b = rng.normal(0, 2, (300, 5)), rng.normal(-2, 2, (300, 5))
    vec = read_vec(f, b, 3.0)
    names = ("CHANGES", "NO_CHANGE_AT_MARGIN", "INCONCLUSIVE")
    ref = [read_learning(f[i], b[i], 3.0) for i in range(300)]
    assert all(names[v] == r for v, r in zip(vec, ref, strict=True))
    return {"rows_checked": 300, "equal": True}


def block_full(reps: int) -> dict:
    return {
        "selfcheck": selfcheck_full(),
        "designs": [block_full_design(reps, n1, nmax) for n1, nmax in ((4, 6), (5, 5), (5, 8))],
    }


def fisher_table(n: int) -> np.ndarray:
    """Two-sided Fisher exact p for collapse counts (cb of n in B, cf of n in F)."""

    t = np.ones((n + 1, n + 1))
    for cb in range(n + 1):
        for cf in range(n + 1):
            t[cb, cf] = stats.fisher_exact([[cb, n - cb], [cf, n - cf]])[1]
    return t


def read_vec(f: np.ndarray, b: np.ndarray, margin: float) -> np.ndarray:
    """Vectorized read_learning over rows: 0 CHANGES, 1 NO_CHANGE_AT_MARGIN, 2 INCONCLUSIVE."""

    n_f, n_b = f.shape[1], b.shape[1]
    va, vb = f.var(axis=1, ddof=1) / n_f, b.var(axis=1, ddof=1) / n_b
    se = np.sqrt(va + vb)
    df = (va + vb) ** 2 / (va**2 / (n_f - 1) + vb**2 / (n_b - 1))
    diff = b.mean(axis=1) - f.mean(axis=1)
    t95, t90 = stats.t.ppf(0.975, df), stats.t.ppf(0.95, df)
    out = np.full(f.shape[0], 2)
    out[np.abs(diff) + t90 * se < margin] = 1
    out[np.abs(diff) > t95 * se] = 0
    return out


def block_full_design(reps: int, n1: int, nmax: int) -> dict:
    """Vectorized over replicates; the same rule as read_learning, the Fisher collapse test and the
    80% upper-confidence-limit re-estimation (each replicate's extra runs are its next draws)."""

    margin, delta_star = 3.0, 4.0
    names = ("CHANGES", "NO_CHANGE_AT_MARGIN", "INCONCLUSIVE")
    fisher = {n: fisher_table(n) for n in range(n1, nmax + 1)}
    mde = {n: mde_two_sample(n) for n in range(2, 13)}
    dfp = 2 * n1 - 2
    ucl_factor = math.sqrt(dfp / stats.chi2.ppf(0.2, dfp))
    scenarios = []
    for sd in (1.5, 2.0, 3.0):
        for effect in (0.0, -2.0, -4.0, -6.0):
            scenarios.append({"sd": sd, "effect": effect, "collapse_b": 0.0})
        scenarios.append({"sd": sd, "effect": -2.0, "collapse_b": 0.75})
    table = []
    for sc in scenarios:
        counts = np.zeros(3)
        runs = []
        for seed in SEEDS:
            rng = np.random.default_rng(
                seed * 1000 + n1 * 100 + int(10 * sc["sd"]) + int(-10 * sc["effect"]) + int(100 * sc["collapse_b"])
            )

            def draw(mean: float, pc: float) -> tuple[np.ndarray, np.ndarray]:
                y = rng.normal(mean, sc["sd"], (reps, nmax))
                col = rng.random((reps, nmax)) < pc
                return np.where(col, y - 15.0, y), col

            f, cf = draw(0.0, 0.02)
            b, cb = draw(sc["effect"], sc["collapse_b"])

            def reading(n: int, rows: np.ndarray) -> np.ndarray:
                p = fisher[n][cb[rows, :n].sum(axis=1), cf[rows, :n].sum(axis=1)]
                r = read_vec(f[rows, :n], b[rows, :n], margin)
                r[p < 0.05] = 0
                return r

            all_rows = np.arange(reps)
            res = reading(n1, all_rows)
            used = np.full(reps, n1)
            inc = np.flatnonzero(res == 2)
            if inc.size:
                pooled = np.sqrt((f[inc, :n1].var(axis=1, ddof=1) + b[inc, :n1].var(axis=1, ddof=1)) / 2)
                ucl = pooled * ucl_factor
                need = np.full(inc.size, 13)
                for n in range(12, 1, -1):
                    need[mde[n] * ucl <= delta_star] = n
                for n in range(n1 + 1, nmax + 1):
                    rows = inc[need == n]
                    if rows.size:
                        res[rows] = reading(n, rows)
                        used[rows] = n
            counts += np.bincount(res, minlength=3)
            runs.extend((2 * used).tolist())
        total = counts.sum()
        table.append(
            {
                **sc,
                **{names[k]: round(float(counts[k] / total), 3) for k in range(3) if counts[k] > 0},
                "expected_runs_F_and_B": round(float(np.mean(runs)), 2),
            }
        )
    return {
        "endpoint": "per-run held-out pass@1 AUC (points), common fp32-state evaluator",
        "stage1_runs_per_arm": n1,
        "max_runs_per_arm": nmax,
        "equivalence_margin_points": margin,
        "reestimation_target_effect_points": delta_star,
        "collapse_model": "a collapsed run loses 15 points; F collapses with probability 0.02",
        "reps_per_seed": reps,
        "rows": table,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--reps", type=int, default=2000)
    ap.add_argument("--grad-reps", type=int, default=150)
    args = ap.parse_args()
    result = {
        "seeds": list(SEEDS),
        "MDE": block_mde(),
        "MANIP": block_manip(args.reps),
        "GRAD": block_grad(args.grad_reps),
        "FULL": block_full(args.reps),
    }
    args.out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    for row in result["MDE"]["rows"]:
        print("MDE", row)
    for m, r in result["MANIP"]["models"].items():
        print("MANIP", m, round(r["point_ratio"], 2), r["by_seed"]["42"],
              {k: round(v, 6) for k, v in r.items() if k.startswith("extra")})
    for row in result["GRAD"]["rows"]:
        print("GRAD", row)
    for design in result["FULL"]["designs"]:
        for row in design["rows"]:
            print("FULL", design["stage1_runs_per_arm"], design["max_runs_per_arm"], row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
