"""The registered S1a analysis (``analyse.analyse``) rearranged for speed, plus diagnostics.

Every bootstrapped statistic of the registered analysis is a task mean: X_z (of the per-task
session products), D_b,z and D_w,z (of the per-task discordance, averaged over the two
harness cells), and delta (of d-bar_t). A task-cluster resample is therefore
``counts @ per-task values / K``, where ``counts`` holds how often each task appears in each
of the registered resamples (``estimators.task_resamples(K, n_boot, seed)``, the indices
``estimators.bootstrap`` uses). pi_share, the percentile bounds, the report's rounding
(``analysis._f``), the paired t, the X sign flip (``estimators.x_signflip_p``, called on the
same batches with the same generator as ``analyse.analyse``) and DR1, DR2 and DR5 are the
frozen functions. ``tests/test_q2_design.py`` checks equality with ``analyse.analyse``.

``diagnostics`` adds the quantities the posterior-predictive check reads (per-size X, pi,
D_b, D_w, counts of non-constant tasks, of tasks with a non-zero harness difference in two
sessions, and of positive and negative session products).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np

from harness.q2_stage1 import analysis as A
from harness.q2_stage1 import estimators as E
from harness.q2_stage1 import rules

_COUNTS: dict[tuple[int, int, int], np.ndarray] = {}


def resample_counts(K: int, n_boot: int = A.N_BOOT, seed: int = A.SEED) -> np.ndarray:
    """(n_boot, K): how often each task appears in each registered resample."""
    key = (K, n_boot, seed)
    if key not in _COUNTS:
        idx = E.task_resamples(K, n_boot, seed)
        c = np.zeros((n_boot, K))
        np.add.at(c, (np.repeat(np.arange(n_boot), K), idx.ravel()), 1.0)
        if len(_COUNTS) > 16:
            _COUNTS.clear()
        _COUNTS[key] = c
    return _COUNTS[key]


def per_task(y: np.ndarray) -> dict[str, np.ndarray]:
    """Per-task quantities of complete data y (n, Z, K, 2, S, R), with the frozen functions."""
    q = E.x_task_products(y)  # (n, Z, K)
    S, R = y.shape[-2], y.shape[-1]
    c = y.sum(-1)  # (n, Z, K, H, S) successes per cell
    disc_b = np.zeros(c.shape[:-1])
    for s1 in range(S):
        for s2 in range(s1 + 1, S):
            disc_b += c[..., s1] * (R - c[..., s2]) + c[..., s2] * (R - c[..., s1])
    db = (disc_b / (S * (S - 1) / 2 * R * R)).mean(-1)  # (n, Z, K)
    if R >= 2:
        dw = ((c * (R - c)).sum(-1) / (S * R * (R - 1) / 2)).mean(-1)
    else:
        dw = np.full(db.shape, np.nan)
    return {"q": q, "db": db, "dw": dw, "dbar": E.task_delta(y), "succ": E.success(y),
            "d": E.harness_diff(y)}  # fmt: skip


def analyse(
    y: np.ndarray,
    sizes: Sequence[str],
    *,
    n_boot: int = A.N_BOOT,
    n_flip: int = A.N_RANDOMIZATION,
    seed: int = A.SEED,
    rng: np.random.Generator | None = None,
    batch: int = 100,
    diagnostics: bool = False,
) -> dict[str, np.ndarray]:
    """``analyse.analyse``'s outputs (same keys, same values), computed from task means."""
    y = np.asarray(y, dtype=float)
    if y.ndim != 6 or y.shape[1] != len(sizes):
        raise ValueError("y must be (nsim, Z, K, 2, S, R) with Z = len(sizes)")
    if np.isnan(y).any():
        raise ValueError("the fast path takes complete data; use analyse.analyse")
    nsim, K, S, R = y.shape[0], y.shape[2], y.shape[-2], y.shape[-1]
    if S < 2:
        raise ValueError("X and D_b need at least two sessions")
    zi = {z: i for i, z in enumerate(sizes)}
    pt = per_task(y)
    C = resample_counts(K, n_boot, seed)
    p_x = np.empty(nsim)
    for b0 in range(0, nsim, batch):
        gen = rng if rng is not None else np.random.default_rng([seed, b0 // batch])
        p_x[b0 : b0 + batch] = E.x_signflip_p(y[b0 : b0 + batch], n_flip, gen)
    t = E.paired_t(pt["dbar"], level=0.90)
    keys = ("delta", "p_delta", "ci90_low", "ci90_high", "p_x", "pi_small", "pi_small_lb",
            "pi_small_ub", "pi_small_ci95_low", "pi_small_ci95_high", "delta_boot_low",
            "delta_boot_high", "D_b", "excess_ub", "drop_4b")  # fmt: skip
    out: dict[str, Any] = {k: np.empty(nsim) for k in keys}
    out["dr2"] = np.empty(nsim, dtype=object)
    out["dr5"] = np.empty(nsim, dtype=object)
    for i in range(nsim):
        xb = C @ pt["q"][i].T / K  # (B, Z)
        dbb = C @ pt["db"][i].T / K
        pib = E.pi_share(xb, dbb)
        x0, db0 = pt["q"][i].mean(-1), pt["db"][i].mean(-1)
        pi0 = E.pi_share(x0, db0)
        drop = rules.dr1(list(pt["succ"][i, zi["4B"]])) if "4B" in zi else True
        if drop:
            draws, point = pib[:, zi["9B"]], float(pi0[zi["9B"]])
        else:
            draws, point = np.nanmean(pib, axis=-1), float(np.nanmean(pi0))
        lb, ub = (A._f(v) for v in E.one_sided_bounds(draws, 0.95))
        lo95, hi95 = E.percentile_interval(draws, 0.95)
        dlo, dhi = E.percentile_interval(C @ pt["dbar"][i] / K, 0.95)
        ci = (float(t["ci_low"][i]), float(t["ci_high"][i]))
        out["delta"][i] = float(t["estimate"][i])
        out["p_delta"][i] = float(t["p"][i])
        out["ci90_low"][i], out["ci90_high"][i] = ci
        out["p_x"][i] = float(p_x[i])
        out["pi_small"][i] = point
        out["pi_small_lb"][i], out["pi_small_ub"][i] = lb, ub
        out["pi_small_ci95_low"][i], out["pi_small_ci95_high"][i] = lo95, hi95
        out["delta_boot_low"][i], out["delta_boot_high"][i] = dlo, dhi
        out["D_b"][i] = float(np.nanmean(db0))
        if R >= 2:
            exc = np.nanmean(dbb - C @ pt["dw"][i].T / K, axis=-1)
            out["excess_ub"][i] = E.one_sided_bounds(exc, 0.95)[1]
        else:
            out["excess_ub"][i] = np.nan
        out["drop_4b"][i] = drop
        out["dr2"][i] = rules.dr2(float(t["p"][i]), float(p_x[i]), ci, ub)["class"]
        out["dr5"][i] = rules.dr5(lb, ub, drop)["outcome"]
    if diagnostics:
        out.update(diagnose(y, sizes, pt))
    return out


def diagnose(
    y: np.ndarray, sizes: Sequence[str], pt: dict[str, np.ndarray] | None = None
) -> dict[str, np.ndarray]:
    """Per-size structure statistics of each data set (point values, no resampling)."""
    pt = pt or per_task(y)
    out: dict[str, np.ndarray] = {}
    tot = y.sum(axis=(-3, -2, -1))  # (n, Z, K)
    n_ep = y.shape[-3] * y.shape[-2] * y.shape[-1]
    nz = (pt["d"] != 0).sum(-1)  # (n, Z, K): sessions with a non-zero harness difference
    for i, z in enumerate(sizes):
        q = pt["q"][:, i]
        out[f"X_{z}"] = q.mean(-1)
        out[f"pi_{z}"] = E.pi_share(q.mean(-1), pt["db"][:, i].mean(-1))
        out[f"D_b_{z}"] = pt["db"][:, i].mean(-1)
        out[f"D_w_{z}"] = pt["dw"][:, i].mean(-1)
        out[f"nonconst_{z}"] = ((tot[:, i] > 0) & (tot[:, i] < n_ep)).sum(-1).astype(float)
        out[f"both_nonzero_{z}"] = (nz[:, i] >= 2).sum(-1).astype(float)
        out[f"qpos_{z}"] = (q > 0).sum(-1).astype(float)
        out[f"qneg_{z}"] = (q < 0).sum(-1).astype(float)
        out[f"qmax_{z}"] = q.max(-1)
    return out


def size_signflip_p(
    y: np.ndarray, sizes: Sequence[str], n_flip: int, rng: np.random.Generator, batch: int = 100
) -> dict[str, np.ndarray]:
    """Per size, the X sign-flip p on that size's products alone (a diagnostic, no rule)."""
    out = {}
    for i, z in enumerate(sizes):
        p = np.empty(y.shape[0])
        for b0 in range(0, y.shape[0], batch):
            p[b0 : b0 + batch] = E.x_signflip_p(y[b0 : b0 + batch, i : i + 1], n_flip, rng)
        out[f"p_x_{z}"] = p
    return out
