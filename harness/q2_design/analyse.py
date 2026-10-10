"""The registered S1a analysis applied to simulated data of any design.

Every number comes from the frozen modules, imported unchanged: ``estimators`` (paired t
on d-bar_t, the X sign-flip test, the task-cluster bootstrap, pi_share, D_b, D_w),
``rules`` (DR1, DR2, DR5 with M = 0.13 / 0.18) and ``analysis._f`` (the report's 6-decimal
rounding of the bootstrap bounds that DR2 and DR5 read). The sequence is
``analysis.analyse_array``'s: the X sign flip draws first from the generator, the bootstrap
uses seed 42 for every data set, pi_small is the mean of pi_4B and pi_9B unless DR1 drops
4B (then pi_9B, against M_9B). ``analyse_array`` itself needs exactly two sessions (its
session-shift statistics), so for other designs the same calls are made here directly; for
a two-session design the outputs equal ``analyse_array``'s (``tests/test_q2_design.py``).

A design with only 9B reads pi_9B against M_9B (the registered DR1 case).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np

from harness.q2_stage1 import analysis as A
from harness.q2_stage1 import estimators as E
from harness.q2_stage1 import rules

STAT_NAMES = ("pi_4B", "pi_9B", "pi_mean", "delta", "D_b", "excess")


def _stats(sizes: Sequence[str], has_within: bool):
    zi = {z: i for i, z in enumerate(sizes)}

    def fn(yy: np.ndarray) -> np.ndarray:
        x = E.x_by_size(yy)
        db = E.d_between(yy)
        pis = E.pi_share(x, db)
        nan = np.full(yy.shape[:-5], np.nan)
        cols = {
            "pi_4B": pis[..., zi["4B"]] if "4B" in zi else nan,
            "pi_9B": pis[..., zi["9B"]] if "9B" in zi else nan,
            "pi_mean": np.nanmean(pis, axis=-1),
            "delta": E.delta(yy),
            "D_b": np.nanmean(db, axis=-1),
            "excess": np.nanmean(db - E.d_within(yy), axis=-1) if has_within else nan,
        }
        return np.stack([cols[n] for n in STAT_NAMES], axis=-1)

    return fn


def analyse(
    y: np.ndarray,
    sizes: Sequence[str],
    *,
    n_boot: int = A.N_BOOT,
    n_flip: int = A.N_RANDOMIZATION,
    seed: int = A.SEED,
    rng: np.random.Generator | None = None,
    batch: int = 100,
) -> dict[str, np.ndarray]:
    """DR1, DR2 and DR5 and the quantities they read, per simulated data set.

    ``y`` is (nsim, Z, K, 2, S, R). ``rng`` drives the X sign flips (default: a stream
    seeded from ``seed`` and the batch number); the bootstrap uses ``seed`` for every data
    set, as the registered report does.
    """
    y = np.asarray(y, dtype=float)
    if y.ndim != 6 or y.shape[1] != len(sizes):
        raise ValueError("y must be (nsim, Z, K, 2, S, R) with Z = len(sizes)")
    nsim, S, R = y.shape[0], y.shape[-2], y.shape[-1]
    if S < 2:
        raise ValueError("X and D_b need at least two sessions")
    fn = _stats(sizes, R >= 2)
    out: dict[str, Any] = {k: np.empty(nsim) for k in (
        "delta", "p_delta", "ci90_low", "ci90_high", "p_x", "pi_small", "pi_small_lb",
        "pi_small_ub", "pi_small_ci95_low", "pi_small_ci95_high", "delta_boot_low",
        "delta_boot_high", "D_b", "excess_ub", "drop_4b",
    )}  # fmt: skip
    out["dr2"] = np.empty(nsim, dtype=object)
    out["dr5"] = np.empty(nsim, dtype=object)
    for b0 in range(0, nsim, batch):
        yb = y[b0 : b0 + batch]
        gen = rng if rng is not None else np.random.default_rng([seed, b0 // batch])
        p_x = E.x_signflip_p(yb, n_flip, gen)
        t = E.paired_t(E.task_delta(yb), level=0.90)
        succ = E.success(yb)
        for j in range(yb.shape[0]):
            i = b0 + j
            draws = E.bootstrap(yb[j], fn, n_boot, seed)
            point = fn(yb[j])
            # DR1 reads 4B's pooled success; a design without 4B is the DR1 case.
            drop = rules.dr1(list(succ[j, list(sizes).index("4B")])) if "4B" in sizes else True
            col = STAT_NAMES.index("pi_9B" if drop else "pi_mean")
            lb, ub = (A._f(v) for v in E.one_sided_bounds(draws[:, col], 0.95))
            lo95, hi95 = E.percentile_interval(draws[:, col], 0.95)
            dlo, dhi = E.percentile_interval(draws[:, STAT_NAMES.index("delta")], 0.95)
            ci = (float(t["ci_low"][j]), float(t["ci_high"][j]))
            dr2 = rules.dr2(float(t["p"][j]), float(p_x[j]), ci, ub)
            dr5 = rules.dr5(lb, ub, drop)
            exc = draws[:, STAT_NAMES.index("excess")]
            out["delta"][i] = float(t["estimate"][j])
            out["p_delta"][i] = float(t["p"][j])
            out["ci90_low"][i], out["ci90_high"][i] = ci
            out["p_x"][i] = float(p_x[j])
            out["pi_small"][i] = float(point[col])
            out["pi_small_lb"][i], out["pi_small_ub"][i] = lb, ub
            out["pi_small_ci95_low"][i], out["pi_small_ci95_high"][i] = lo95, hi95
            out["delta_boot_low"][i], out["delta_boot_high"][i] = dlo, dhi
            out["D_b"][i] = float(point[STAT_NAMES.index("D_b")])
            out["excess_ub"][i] = (
                E.one_sided_bounds(exc, 0.95)[1] if np.isfinite(exc).any() else np.nan
            )
            out["drop_4b"][i] = drop
            out["dr2"][i] = dr2["class"]
            out["dr5"][i] = dr5["outcome"]
    return out


def summarise(res: dict[str, np.ndarray]) -> dict[str, Any]:
    """Outcome rates and the distribution of the interval widths."""
    n = len(res["dr2"])

    def q(v: np.ndarray) -> dict[str, float]:
        v = np.asarray(v, dtype=float)
        v = v[np.isfinite(v)]
        if not v.size:
            return {}
        qs = np.percentile(v, [5, 25, 50, 75, 95])
        return {"mean": float(v.mean()), "p05": qs[0], "p25": qs[1], "median": qs[2],
                "p75": qs[3], "p95": qs[4]}  # fmt: skip

    dr2 = {c: float(np.mean(res["dr2"] == c)) for c in ("Present", "Near-equivalent",
                                                         "Inconclusive")}  # fmt: skip
    dr5 = {c: float(np.mean(res["dr5"] == c)) for c in ("GO", "NO-GO", "INCONCLUSIVE")}
    return {
        "n": n,
        "DR2": dr2,
        "DR5": dr5,
        "P_DR2_decisive": dr2["Present"] + dr2["Near-equivalent"],
        "P_DR5_decisive": dr5["GO"] + dr5["NO-GO"],
        "P_both_inconclusive": float(
            np.mean((res["dr2"] == "Inconclusive") & (res["dr5"] == "INCONCLUSIVE"))
        ),
        "P_DR1_drop_4B": float(np.mean(res["drop_4b"].astype(bool))),
        "P_P1_falsified": float(np.mean(res["excess_ub"] < rules.P1_MIN_EXCESS)),
        "delta_ci90_width": q(res["ci90_high"] - res["ci90_low"]),
        "delta_boot95_width": q(res["delta_boot_high"] - res["delta_boot_low"]),
        "delta": q(res["delta"]),
        "pi_small": q(res["pi_small"]),
        "pi_small_ub": q(res["pi_small_ub"]),
        "pi_small_lb": q(res["pi_small_lb"]),
        "pi_small_bound_width": q(res["pi_small_ub"] - res["pi_small_lb"]),
        "pi_small_ci95_width": q(res["pi_small_ci95_high"] - res["pi_small_ci95_low"]),
        "D_b": q(res["D_b"]),
    }
