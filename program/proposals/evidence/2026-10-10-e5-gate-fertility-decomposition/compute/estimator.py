"""Registered estimator and decision rules for e5-gate-fertility-decomposition-v1 (draft).

This module is the estimator as code. The draft registration
(program/preregistrations/e5-gate-fertility-decomposition-v1.md) points at it;
the CPU simulations S1 (mech-sim.py) and S2 (power-sim.py) call it, so the rules
whose operating characteristics are reported are the rules that would be read.
If the registration is frozen, this file is copied into the harness unchanged
and its SHA-256 is recorded in the freeze.

Units: outcomes are per-episode forced-choice correctness in {0, 100} (percentage
points) unless stated otherwise. Fertility f is the realized token-count ratio of
the retention span to its canonical tokenization on the subject's own tokenizer.

Primary estimand per subject s (natural indirect effect of the per-token decay
clock, expressed per unit of log fertility):

    NIE_s(K, f) = mean_e [ Y_e(f, clamp) - Y_e(f, native) ]
    beta_s      = mean_{K in {1, 4}} NIE_s(K, f_p) / ln(f_p)

NIE_s(K, 1) = 0 by construction (the clamp is the identity at f = 1), so beta_s is
the secant slope from f = 1, in the dossier's unit (EM points per log-fertility
unit). The 90% interval is a percentile cluster bootstrap over retention-span
passages (each passage carries all its episodes at every K, f and arm).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

LINE = 3.0  # dossier line: 3 points per unit of log fertility
LEVEL = 0.90
BOOT_B = 2000
BOOT_SEED = 42
PRIMARY_LOADS = (1, 4)
F_LADDER = (2.7, 2.0, 1.5)  # primary fertility, then the registered fallbacks
FLOOR_NATIVE = 30.0  # native accuracy at the primary f (K = 4) must be at least this
FLOOR_CANONICAL = 50.0  # canonical accuracy at K = 4 must be at least this


@dataclass(frozen=True)
class Interval:
    point: float
    lo: float
    hi: float


def cluster_bootstrap(values_by_cluster: list[np.ndarray], stat, b: int = BOOT_B,
                      seed: int = BOOT_SEED, level: float = LEVEL) -> Interval:
    """Percentile cluster bootstrap. values_by_cluster[c] is any array for cluster c;
    stat maps a list of cluster arrays to a float."""
    rng = np.random.default_rng(seed)
    point = float(stat(values_by_cluster))
    n = len(values_by_cluster)
    draws = np.empty(b)
    for i in range(b):
        idx = rng.integers(0, n, n)
        draws[i] = stat([values_by_cluster[j] for j in idx])
    a = (1 - level) / 2
    return Interval(point, float(np.quantile(draws, a)), float(np.quantile(draws, 1 - a)))


def cluster_bootstrap_mean(diff_by_cluster: list[np.ndarray], b: int = BOOT_B, seed: int = BOOT_SEED,
                           level: float = LEVEL, scale: float = 1.0) -> Interval:
    """Registered primary interval: percentile cluster bootstrap of a pooled episode mean
    (resampled cluster sums over resampled cluster counts), multiplied by scale (1 / ln f_p
    for beta). Vectorised; identical in distribution to cluster_bootstrap with the pooled
    mean as the statistic."""
    sums = np.array([d.sum() for d in diff_by_cluster], dtype=float)
    counts = np.array([d.size for d in diff_by_cluster], dtype=float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(sums), (b, len(sums)))
    draws = sums[idx].sum(1) / counts[idx].sum(1) * scale
    a = (1 - level) / 2
    return Interval(float(sums.sum() / counts.sum() * scale), float(np.quantile(draws, a)),
                    float(np.quantile(draws, 1 - a)))


def cluster_normal(diff_by_cluster: list[np.ndarray], level: float = LEVEL) -> Interval:
    """Cluster-robust normal interval for a mean of per-episode differences (used by S2 for
    speed; S2 checks its coverage against cluster_bootstrap)."""
    sums = np.array([d.sum() for d in diff_by_cluster])
    counts = np.array([d.size for d in diff_by_cluster])
    n, g = counts.sum(), len(diff_by_cluster)
    mean = sums.sum() / n
    resid = sums - mean * counts
    var = g / (g - 1) * (resid ** 2).sum() / n ** 2
    z = {0.90: 1.6448536269514722, 0.95: 1.959963984540054}[level]
    se = math.sqrt(var)
    return Interval(float(mean), float(mean - z * se), float(mean + z * se))


def decide_subject(beta: Interval, line: float = LINE) -> str:
    """Per-subject reading of the primary estimand."""
    if beta.hi < line:
        return "KILL"
    if beta.point >= line and beta.lo > 0:
        return "MATERIAL"
    return "INCONCLUSIVE"


def no_cost(te_per_logf: Interval, line: float = LINE) -> bool:
    """NO_COST: the total re-segmentation cost per log-f unit is below the line with confidence."""
    return te_per_logf.hi < line


def decide_overall(subject_readings: dict[str, str]) -> str:
    """Readings per subject are KILL, MATERIAL, INCONCLUSIVE, NO_COST or INVALID."""
    vals = set(subject_readings.values())
    if "INVALID" in vals:
        return "INVALID"
    if vals <= {"KILL", "NO_COST"}:
        return "KILL_NO_COST" if vals == {"NO_COST"} else "KILL"
    if vals == {"MATERIAL"}:
        return "MATERIAL"
    if "MATERIAL" in vals and vals & {"KILL", "NO_COST"}:
        return "SPLIT"
    return "INCONCLUSIVE"


def primary_f(canonical_acc_k4: float, native_acc_k4: dict[float, float]) -> float | None:
    """Registered fertility ladder: the largest f whose native K = 4 accuracy clears the floor,
    provided the canonical K = 4 accuracy clears its floor; None means INVALID."""
    if canonical_acc_k4 < FLOOR_CANONICAL:
        return None
    for f in F_LADDER:
        if native_acc_k4.get(f, -1.0) >= FLOOR_NATIVE:
            return f
    return None


def secant(nie_points: float, f: float) -> float:
    return nie_points / math.log(f)
