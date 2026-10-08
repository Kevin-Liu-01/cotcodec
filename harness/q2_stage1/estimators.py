"""The registered estimators and randomization tests of `q2-stage1-rescoped-v1` (S1a).

Array convention
----------------
``y`` has shape ``(..., Z, K, H, S, R)``:

* ``Z`` sizes, in the order (4B, 9B);
* ``K`` tasks of the analysis set;
* ``H`` harnesses, index 0 = H-OSW-fixed and 1 = H-GA;
* ``S`` serving sessions (S1, S2);
* ``R`` within-session reruns (block 1, block 2).

Values are 1.0 (the checker score is 1.0), 0.0 or NaN (a missing slot). Leading
dimensions are batch dimensions (simulated data sets or bootstrap resamples), so the
same functions serve the analysis and the operating-characteristics simulation.

Every quantity is conditional on the sessions that ran (preregistration section 9):
the bootstrap resamples tasks, never sessions.
"""

from __future__ import annotations

import math
import warnings
from collections.abc import Callable

import numpy as np
from scipy import stats

OSW, GA = 0, 1
AXIS_Z, AXIS_K, AXIS_H, AXIS_S, AXIS_R = -5, -4, -3, -2, -1


def _nanmean(a: np.ndarray, axis=None) -> np.ndarray:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        return np.nanmean(a, axis=axis)


def _check(y: np.ndarray) -> np.ndarray:
    y = np.asarray(y, dtype=float)
    if y.ndim < 5:
        raise ValueError("y must have shape (..., Z, K, H, S, R)")
    if y.shape[AXIS_H] != 2:
        raise ValueError("y must hold exactly two harnesses")
    finite = y[np.isfinite(y)]
    if finite.size and not np.all((finite == 0.0) | (finite == 1.0)):
        raise ValueError("outcomes must be 0, 1 or NaN")
    return y


# --------------------------------------------------------------------------- cells


def cell_means(y: np.ndarray) -> np.ndarray:
    """m_zths: the mean of the available within-session reruns; shape (..., Z, K, H, S)."""
    return _nanmean(_check(y), axis=-1)


def harness_diff(y: np.ndarray) -> np.ndarray:
    """d_zts = m_zt,GA,s - m_zt,OSW,s; shape (..., Z, K, S)."""
    m = cell_means(y)
    return m[..., GA, :] - m[..., OSW, :]


def success(y: np.ndarray) -> np.ndarray:
    """Pooled success per size and harness (mean over tasks of the task's mean); (..., Z, H)."""
    y = _check(y)
    per_task = _nanmean(y.reshape(*y.shape[:-2], -1), axis=-1)  # (..., Z, K, H)
    return _nanmean(per_task, axis=-2)


# --------------------------------------------------------------------------- harness effect


def task_delta(y: np.ndarray) -> np.ndarray:
    """d-bar_t: the mean over available (size, session) cells of d_zts; shape (..., K)."""
    d = harness_diff(y)  # (..., Z, K, S)
    d = np.moveaxis(d, -3, -2)  # (..., K, Z, S)
    return _nanmean(d.reshape(*d.shape[:-2], -1), axis=-1)


def delta(y: np.ndarray) -> np.ndarray:
    """Pooled delta = mean_t d-bar_t (H-GA minus H-OSW-fixed); shape (...)."""
    return _nanmean(task_delta(y), axis=-1)


def delta_by_size(y: np.ndarray) -> np.ndarray:
    """delta_z = mean_t mean_s d_zts; shape (..., Z)."""
    return _nanmean(_nanmean(harness_diff(y), axis=-1), axis=-1)


def delta_by_session(y: np.ndarray) -> np.ndarray:
    """delta_zs = mean_t d_zts; shape (..., Z, S)."""
    return _nanmean(harness_diff(y), axis=-2)


def delta_session_heterogeneity(y: np.ndarray) -> dict[str, np.ndarray]:
    """Per size, delta_S1 - delta_S2 on tasks with both sessions, with its task-paired SE.

    Reported, not tested (section 10.1): it shows whether the harness effect moved with the
    realized session, which the delta test (conditional on the sessions) cannot.
    """
    d = harness_diff(y)
    if d.shape[-1] != 2:
        raise ValueError("the heterogeneity check needs exactly two sessions")
    h = d[..., 0] - d[..., 1]  # (..., Z, K)
    n = np.sum(np.isfinite(h), axis=-1)
    mean = _nanmean(h, axis=-1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        sd = np.nanstd(h, axis=-1, ddof=1)
        se = np.where(n > 1, sd / np.sqrt(np.maximum(n, 1)), np.nan)
    return {"difference": mean, "se": se, "n_tasks": n}


# --------------------------------------------------------------------------- per-task harness term


def x_task_products(y: np.ndarray) -> np.ndarray:
    """Per size and task, the mean over ordered session pairs s != s' of d_zts * d_zts'.

    With two sessions this is d_zt1 * d_zt2. A task with fewer than two sessions holding
    both harness cells is NaN. Shape (..., Z, K).
    """
    d = harness_diff(y)  # (..., Z, K, S)
    ok = np.isfinite(d)
    n = ok.sum(axis=-1)
    dz = np.where(ok, d, 0.0)
    total = dz.sum(axis=-1) ** 2 - (dz**2).sum(axis=-1)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = total / (n * (n - 1))
    return np.where(n >= 2, out, np.nan)


def x_by_size(y: np.ndarray) -> np.ndarray:
    """X_z = mean_t of the session products: the mean squared per-task harness effect.

    It is unbiased for mean_t Delta_t^2 = delta_z^2 + Var_t(Delta_t) when the sessions are
    independent given the task, so it carries the main effect as well as the task-specific
    part (it is not an interaction statistic). Shape (..., Z).
    """
    return _nanmean(x_task_products(y), axis=-1)


def x_pooled(y: np.ndarray) -> np.ndarray:
    """X pooled over sizes (mean of the available sizes); shape (...)."""
    return _nanmean(x_by_size(y), axis=-1)


def x_per_task_pooled(y: np.ndarray) -> np.ndarray:
    """q_t: the mean over sizes of the per-task session products; shape (..., K).

    The primary X test flips the sign of each q_t (section 10.1).
    """
    q = x_task_products(y)  # (..., Z, K)
    return _nanmean(np.moveaxis(q, -2, -1), axis=-1)


def x_centred_by_size(y: np.ndarray) -> np.ndarray:
    """The task x harness interaction part: X_z - (delta_z^2 - Var-hat(delta_z)).

    On the tasks with at least two sessions holding both harness cells,
    Var-hat(delta_z) = (1/K^2) sum_t var_s(d_zts) / n_s, so the statistic is unbiased for
    the variance over tasks of the per-task harness effect (divisor K). Shape (..., Z).
    """
    d = harness_diff(y)
    ok = np.isfinite(d)
    n = ok.sum(axis=-1)
    use = n >= 2
    dz = np.where(ok, d, 0.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        dbar = dz.sum(axis=-1) / n
        var = (np.where(ok, (d - dbar[..., None]) ** 2, 0.0)).sum(axis=-1) / (n - 1) / n
    q = x_task_products(y)
    k = use.sum(axis=-1)
    dbar = np.where(use, dbar, 0.0)
    var = np.where(use, var, 0.0)
    q = np.where(use, q, 0.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        x = q.sum(axis=-1) / k
        dz_mean = dbar.sum(axis=-1) / k
        vhat = var.sum(axis=-1) / k**2
    return np.where(k > 0, x - dz_mean**2 + vhat, np.nan)


def x_bernoulli_by_size(y: np.ndarray) -> np.ndarray:
    """Secondary: (p-hat_GA - p-hat_OSW)^2 minus Bernoulli variances, pooling every rerun."""
    y = _check(y)
    flat = y.reshape(*y.shape[:-2], -1)  # (..., Z, K, H, S*R)
    n = np.sum(np.isfinite(flat), axis=-1)
    ph = _nanmean(flat, axis=-1)
    with np.errstate(invalid="ignore", divide="ignore"):
        v = np.where(n > 1, ph * (1 - ph) / (n - 1), np.nan)
    term = (ph[..., GA] - ph[..., OSW]) ** 2 - v[..., GA] - v[..., OSW]
    return _nanmean(term, axis=-1)


# --------------------------------------------------------------------------- rerun discordance


def _pair_fraction(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    valid = np.isfinite(a) & np.isfinite(b)
    disc = np.where(valid, (a != b).astype(float), 0.0)
    return disc, valid.astype(float)


def _discordance(y: np.ndarray, kind: str) -> np.ndarray:
    """Mean over (t, h) of each cell's discordant share among its pairs of ``kind``; (..., Z)."""
    y = _check(y)
    S, R = y.shape[-2], y.shape[-1]
    disc = np.zeros(y.shape[:-2])
    count = np.zeros(y.shape[:-2])
    for s1 in range(S):
        for s2 in range(S):
            for j1 in range(R):
                for j2 in range(R):
                    if kind == "within":
                        if s1 != s2 or j2 <= j1:
                            continue
                    else:
                        if s2 <= s1:
                            continue
                        if kind == "between_same_block" and j1 != j2:
                            continue
                        if kind == "between_cross_block" and j1 == j2:
                            continue
                    dd, vv = _pair_fraction(y[..., s1, j1], y[..., s2, j2])
                    disc += dd
                    count += vv
    with np.errstate(invalid="ignore", divide="ignore"):
        frac = np.where(count > 0, disc / np.maximum(count, 1), np.nan)  # (..., Z, K, H)
    frac = frac.reshape(*frac.shape[:-2], -1)
    return _nanmean(frac, axis=-1)


def d_between(y: np.ndarray) -> np.ndarray:
    """D_b,z: discordance over cross-session pairs; shape (..., Z)."""
    return _discordance(y, "between")


def d_within(y: np.ndarray) -> np.ndarray:
    """D_w,z: discordance over within-session pairs; shape (..., Z)."""
    return _discordance(y, "within")


def d_between_same_block(y: np.ndarray) -> np.ndarray:
    """D_b on cross-session pairs from the same block (block 1 with 1, 2 with 2)."""
    return _discordance(y, "between_same_block")


def d_between_cross_block(y: np.ndarray) -> np.ndarray:
    """D_b on cross-session pairs from different blocks (block 1 with block 2)."""
    return _discordance(y, "between_cross_block")


# --------------------------------------------------------------------------- harness share


def pi_share(x: np.ndarray, db: np.ndarray) -> np.ndarray:
    """pi = (X+/4) / (X+/4 + D_b/2), X+ = max(X, 0); 0 when the denominator is 0.

    A negative moment estimate of X is truncated at 0 (a share cannot be negative); the
    untruncated X is reported beside it. 0/0 (no variation at all) is defined as 0, also
    inside bootstrap resamples.
    """
    x = np.asarray(x, dtype=float)
    db = np.asarray(db, dtype=float)
    xp = np.maximum(x, 0.0)
    den = xp / 4 + db / 2
    with np.errstate(invalid="ignore", divide="ignore"):
        out = np.where(den > 0, (xp / 4) / np.where(den > 0, den, 1.0), 0.0)
    return np.where(np.isfinite(x) & np.isfinite(db), out, np.nan)


def pi_by_size(y: np.ndarray) -> np.ndarray:
    """pi_z on the between-session floor; shape (..., Z)."""
    return pi_share(x_by_size(y), d_between(y))


def pi_small(y: np.ndarray, drop_4b: bool = False) -> np.ndarray:
    """The mean of pi_4B and pi_9B, or pi_9B alone when DR1 drops 4B; shape (...)."""
    p = pi_by_size(y)
    if drop_4b:
        return p[..., 1]
    return _nanmean(p, axis=-1)


# --------------------------------------------------------------------------- sessions


def session_deviation(y: np.ndarray) -> np.ndarray:
    """w_zth = m_zth,S2 - m_zth,S1; shape (..., Z, K, H)."""
    m = cell_means(y)
    if m.shape[-1] != 2:
        raise ValueError("the session shift needs exactly two sessions")
    return m[..., 1] - m[..., 0]


def session_task_shift(y: np.ndarray) -> np.ndarray:
    """u_zt = the mean over harnesses of (m_zth,S2 - m_zth,S1); shape (..., Z, K)."""
    return _nanmean(session_deviation(y), axis=-1)


def session_shift(y: np.ndarray) -> np.ndarray:
    """Per size, mean_t u_zt (S2 minus S1); shape (..., Z)."""
    return _nanmean(session_task_shift(y), axis=-1)


def session_common_share(y: np.ndarray) -> dict[str, np.ndarray]:
    """The part of the session excess common to both harnesses (reported for S1b, DR3).

    C_z = mean_t w_zt,GA * w_zt,OSW / 2 estimates the cross-harness covariance of session
    deviations (Bernoulli noise is independent across harness cells, so it does not bias
    C_z); V_z = (D_b,z - D_w,z) / 2 estimates the session variance per cell; the share
    rho_z = C_z / V_z is truncated to [0, 1] (NaN when V_z <= 0).
    """
    w = session_deviation(y)
    c = _nanmean(w[..., GA] * w[..., OSW], axis=-1) / 2
    v = (d_between(y) - d_within(y)) / 2
    with np.errstate(invalid="ignore", divide="ignore"):
        rho = np.where(v > 0, np.clip(c / np.where(v > 0, v, 1.0), 0.0, 1.0), np.nan)
    return {"covariance": c, "session_variance": v, "common_share": rho}


# --------------------------------------------------------------------------- tests


def paired_t(x: np.ndarray, level: float = 0.90) -> dict[str, np.ndarray]:
    """Two-sided paired t over the last axis (NaN entries dropped) and its t interval."""
    x = np.asarray(x, dtype=float)
    n = np.sum(np.isfinite(x), axis=-1)
    mean = _nanmean(x, axis=-1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        sd = np.nanstd(x, axis=-1, ddof=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        se = sd / np.sqrt(n)
        t = np.where(se > 0, mean / np.where(se > 0, se, 1.0), 0.0)
    df = np.maximum(n - 1, 1)
    p = np.where(n > 1, 2 * stats.t.sf(np.abs(t), df), np.nan)
    q = stats.t.ppf(0.5 + level / 2, df)
    return {
        "estimate": mean,
        "se": se,
        "p": p,
        "ci_low": mean - q * se,
        "ci_high": mean + q * se,
        "n": n,
    }


def signflip_p(
    values: np.ndarray,
    nflip: int,
    rng: np.random.Generator,
    alternative: str = "greater",
    chunk: int = 250,
) -> np.ndarray:
    """Sign-flip randomization p-value of the mean over the last axis (NaN entries dropped).

    Each entry's sign is flipped independently with probability 1/2; p = (1 + #{T* >= T}) /
    (1 + nflip) for ``greater`` and the same on |T| for ``two-sided``.
    """
    if alternative not in ("greater", "two-sided"):
        raise ValueError("alternative must be 'greater' or 'two-sided'")
    v = np.asarray(values, dtype=float)
    obs = _nanmean(v, axis=-1)
    count = np.zeros(obs.shape)
    done = 0
    while done < nflip:
        m = min(chunk, nflip - done)
        sgn = np.where(rng.random((m, *v.shape)) < 0.5, -1.0, 1.0)
        star = _nanmean(sgn * v, axis=-1)  # (m, ...)
        if alternative == "greater":
            count += np.sum(star >= obs - 1e-12, axis=0)
        else:
            count += np.sum(np.abs(star) >= np.abs(obs) - 1e-12, axis=0)
        done += m
    return (count + 1) / (nflip + 1)


def x_signflip_p(y: np.ndarray, nflip: int, rng: np.random.Generator) -> np.ndarray:
    """Primary X test: one-sided sign flip of the per-task products q_t (pooled over sizes).

    Flipping d_zts swaps the two harness cells of a whole (size, task, session) cell, which
    is exchangeable under no harness effect whatever the session structure; flipping both
    sizes' sessions of a task together flips q_t.
    """
    return signflip_p(x_per_task_pooled(y), nflip, rng, "greater")


def session_signflip_p(y: np.ndarray, nflip: int, rng: np.random.Generator) -> np.ndarray:
    """Session-shift test per size: two-sided sign flip over tasks of u_zt; shape (..., Z)."""
    u = session_task_shift(y)  # (..., Z, K)
    return signflip_p(u, nflip, rng, "two-sided")


def x_label_permutation_p(y: np.ndarray, nperm: int, rng: np.random.Generator) -> np.ndarray:
    """Sensitivity: permute harness labels of the H x R episodes within each (z, t, s).

    Valid only when the episodes of a (task, session) cell are exchangeable, which a
    session excess breaks (section 10.2), so it is not the primary test.
    """
    y = _check(y)
    obs = x_pooled(y)
    ep = np.moveaxis(y, AXIS_H, -2)  # (..., Z, K, S, H, R)
    shape = ep.shape
    flat = ep.reshape(*shape[:-2], shape[-2] * shape[-1])
    count = np.zeros(obs.shape)
    for _ in range(nperm):
        idx = np.argsort(rng.random(flat.shape), axis=-1)
        perm = np.take_along_axis(flat, idx, -1).reshape(shape)
        count += x_pooled(np.moveaxis(perm, -2, AXIS_H)) >= obs - 1e-12
    return (count + 1) / (nperm + 1)


def session_label_permutation_p(y: np.ndarray, nperm: int, rng: np.random.Generator) -> np.ndarray:
    """The draft's session test (kept for the record in the simulation only).

    It permutes session labels within (task, harness), which a session excess breaks.
    """
    y = _check(y)
    S, R = y.shape[-2], y.shape[-1]
    flat = y.reshape(*y.shape[:-2], S * R)

    def stat(v: np.ndarray) -> np.ndarray:
        a = _nanmean(v[..., R:], axis=-1)
        b = _nanmean(v[..., :R], axis=-1)
        return _nanmean((a - b).reshape(*a.shape[:-2], -1), axis=-1)

    obs = stat(flat)
    count = np.zeros(obs.shape)
    for _ in range(nperm):
        idx = np.argsort(rng.random(flat.shape), axis=-1)
        count += np.abs(stat(np.take_along_axis(flat, idx, -1))) >= np.abs(obs) - 1e-12
    return (count + 1) / (nperm + 1)


def holm_any(p_values: list[float], alpha: float = 0.05) -> bool:
    """Holm's procedure over the family: does any hypothesis reject at family-wise alpha?"""
    ps = sorted(p for p in p_values if p is not None and math.isfinite(p))
    return bool(ps) and ps[0] <= alpha / len(p_values)


# --------------------------------------------------------------------------- bootstrap


def task_resamples(n_tasks: int, n_boot: int, seed: int) -> np.ndarray:
    """Task-cluster bootstrap indices, (n_boot, n_tasks), from numpy's PCG64 with ``seed``."""
    return np.random.default_rng(seed).integers(0, n_tasks, size=(n_boot, n_tasks))


def bootstrap(
    y: np.ndarray, fn: Callable[[np.ndarray], np.ndarray], n_boot: int, seed: int
) -> np.ndarray:
    """fn over task-cluster resamples of ``y`` (tasks resampled jointly over sizes,
    harnesses, sessions and reruns); returns shape (n_boot, *fn(y).shape)."""
    y = _check(y)
    if y.ndim != 5:
        raise ValueError("bootstrap takes one data set of shape (Z, K, H, S, R)")
    idx = task_resamples(y.shape[1], n_boot, seed)
    out = []
    for lo in range(0, n_boot, 1000):
        part = np.moveaxis(y[:, idx[lo : lo + 1000]], 1, 0)  # (b, Z, K, H, S, R)
        out.append(np.asarray(fn(part)))
    return np.concatenate(out, axis=0)


def percentile_interval(draws: np.ndarray, level: float = 0.95) -> tuple[float, float]:
    lo, hi = np.nanpercentile(draws, [50 * (1 - level), 50 * (1 + level)])
    return float(lo), float(hi)


def one_sided_bounds(draws: np.ndarray, level: float = 0.95) -> tuple[float, float]:
    """(one-sided lower bound, one-sided upper bound) at ``level`` each."""
    lo, hi = np.nanpercentile(draws, [100 * (1 - level), 100 * level])
    return float(lo), float(hi)
