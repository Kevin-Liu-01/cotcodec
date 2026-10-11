"""Registered estimator and decision rules for e5-gate-fertility-decomposition-v2 (draft).

This module is the estimator as code for registration v2
(program/preregistrations/e5-gate-fertility-decomposition-v2.md). The repair's CPU
simulations S1v2 (`mech-sim-v2.py`) and S2v2 (`power-sim-v2.py`) import it, so the rules
whose operating characteristics are reported are the rules that would be read. If v2 is
frozen, this file is copied into the harness unchanged and its SHA-256 is recorded. v1's
`compute/estimator.py` is kept unedited beside it.

What changed from v1 (each change answers a wave-1 defect; see the proposal's
"Changes after wave 1"):

1. One primary load K_p, chosen on held-out smoke episodes, never pooled with K = 1.
   K = 1 with fresh foils was a presence test at ceiling and diluted v1's pooled secant.
   K_p is the smallest K in (4, 8, 16) whose canonical accuracy is at most the ceiling
   (90) and at least the floor (50); f_p is the first f in (2.7, 2.0) whose native
   accuracy at K_p is at least 30 (chance 25 plus 5: its only job is to keep NAT off
   chance; with PNIE co-primary a low NAT no longer biases the reading toward KILL, and a
   floor of 40, tried first in the repair, refused exactly the erase-dominated operating
   points where MASKED would be read, S1v2). f = 1.5 is no longer reachable (power, S2v2).
2. A 2 x 2 factorial on the decay pathway (decay mass canonical or re-segmented) and the
   passage tokens (canonical or re-segmented), so that the clamp's natural indirect effect
   (noising, TNIE) is reported beside the pure indirect effect (denoising, PNIE) and their
   difference, the decay-by-write interaction (INT), in the sense of arXiv 2606.27510,
   Prop. 3.1. The per-episode identity TE = PNIE + PNDE + INT is exact.
3. The line is stated on the guessing-corrected scale. Under the high-threshold model of
   four-alternative forced choice, FC = 25 + 0.75 p_know and exact match = p_know, so an
   exact-match effect of x points is 0.75 x forced-choice points. Estimates are raw
   forced-choice differences divided by 0.75 and by ln f_p; the line stays 3 points per
   log-f unit on that scale (2.25 raw forced-choice points per log-f unit).
4. The decision interval is the cluster-robust normal interval with articles as clusters
   (one passage per article, four episodes per article at K_p). The percentile cluster
   bootstrap is reported beside it. S2v2 checks coverage and agreement.
5. The reading conditions the kill on the pure indirect effect and on the gate ledger:
   KILL needs both TNIE and PNIE below the line and a median R_F of at least 1.5.

Arms at (K_p, f_p), paired by episode (same facts, codes, target, passage, lead-in):

    CAN    canonical passage, native decay                  writes W0, decay D0
    DEC    canonical passage, each canonical token's log-decay set (layer by layer,
           head or channel) to the sum of its pieces' log-decays in NAT  W0, D1
    CLAMP  re-segmented passage, each canonical token's pieces rescaled so their summed
           log-decay equals the token's log-decay in CAN                W1, D0
    NAT    re-segmented passage, native decay                           W1, D1

Per-episode contrasts, in raw forced-choice points (each in {-100, 0, +100} or a
difference of two such):

    TE   = CAN - NAT                      total re-segmentation cost
    TNIE = CLAMP - NAT                    noising: decay effect at re-segmented writes
    PNIE = CAN - DEC                      denoising: decay effect at canonical writes
    INT  = TNIE - PNIE                    decay-by-write interaction
    PNDE = CAN - CLAMP                    re-segmentation effect at canonical decay
    TE   = PNIE + PNDE + INT              exactly

b_X = mean_e(X) / (0.75 * ln f_p), the secant from f = 1 on the corrected scale.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

LINE = 3.0  # corrected points per unit of log fertility (2.25 raw forced-choice points)
GUESS_SCALE = 0.75  # 1 - 1/4: four-alternative forced choice
LEVEL = 0.90
Z90 = 1.6448536269514722
BOOT_B = 2000
BOOT_SEED = 42
K_LADDER = (4, 8, 16)
F_LADDER = (2.7, 2.0)
CEILING_CAN = 90.0  # held-out canonical accuracy at K_p must be at most this
FLOOR_CAN = 50.0  # ... and at least this
FLOOR_NAT = 30.0  # held-out native accuracy at (K_p, f_p) must be at least this (chance 25 + 5)
RF_MIN = 1.5  # median R_F over split tokens below this: gates self-normalise on fragments
EPISODES_PER_ARTICLE = 4
# articles (one passage each, EPISODES_PER_ARTICLE episodes each) at the selected f_p; fixed
# before any analysis episode is run, from f_p alone (which the held-out smoke sets)
N_ARTICLES_BY_F = {2.7: 2000, 2.0: 3000}

LOSS_NULL_READINGS = ("KILL", "MASKED", "SELF_NORMALIZED", "PARITY_NULL")


@dataclass(frozen=True)
class Interval:
    point: float
    lo: float
    hi: float


def select_operating_point(can_acc: dict[int, float], nat_acc: dict[tuple[int, float], float]):
    """Registered operating-point rule, evaluated on the smoke's held-out episodes only
    (never on analysis episodes). can_acc[K] and nat_acc[(K, f)] are raw forced-choice
    accuracies in points. Returns (K_p, f_p) or None (NOT_ADMISSIBLE).

    K_p is the smallest K in K_LADDER whose canonical accuracy is at most CEILING_CAN; it
    must also be at least FLOOR_CAN. f_p is the first f in F_LADDER whose native accuracy at
    K_p is at least FLOOR_NAT. Larger K cannot rescue a failed native floor (accuracy falls
    with K), so the search stops at the first K under the ceiling."""
    for k in K_LADDER:
        if can_acc.get(k, 101.0) <= CEILING_CAN:
            if can_acc[k] < FLOOR_CAN:
                return None
            for f in F_LADDER:
                if nat_acc.get((k, f), -1.0) >= FLOOR_NAT:
                    return (k, f)
            return None
    return None


def cluster_normal(values_by_cluster: list[np.ndarray], level: float = LEVEL, scale: float = 1.0) -> Interval:
    """Registered decision interval: cluster-robust (CR1, g/(g-1)) normal interval for the
    pooled episode mean of per-episode values, multiplied by scale."""
    sums = np.array([v.sum() for v in values_by_cluster], dtype=float)
    counts = np.array([v.size for v in values_by_cluster], dtype=float)
    n, g = counts.sum(), len(values_by_cluster)
    mean = sums.sum() / n
    resid = sums - mean * counts
    var = g / (g - 1) * (resid ** 2).sum() / n ** 2
    z = {0.90: Z90, 0.95: 1.959963984540054}[level]
    se = math.sqrt(var)
    return Interval(float(mean * scale), float((mean - z * se) * scale), float((mean + z * se) * scale))


def cluster_normal_matrix(x: np.ndarray, scale: float = 1.0, z: float = Z90):
    """Vectorised cluster_normal over replicates: x has shape [reps, clusters, m] (equal
    cluster sizes). Returns (point, lo, hi) arrays, each multiplied by scale. Identical to
    cluster_normal for each replicate."""
    reps, g, m = x.shape
    sums = x.sum(2)
    n = g * m
    mean = sums.sum(1) / n
    resid = sums - mean[:, None] * m
    var = g / (g - 1) * (resid ** 2).sum(1) / n ** 2
    se = np.sqrt(var)
    return mean * scale, (mean - z * se) * scale, (mean + z * se) * scale


def cluster_bootstrap_mean(values_by_cluster: list[np.ndarray], b: int = BOOT_B, seed: int = BOOT_SEED,
                           level: float = LEVEL, scale: float = 1.0) -> Interval:
    """Reported beside the decision interval: percentile cluster bootstrap of the pooled
    episode mean (resampled cluster sums over resampled cluster counts), times scale."""
    sums = np.array([d.sum() for d in values_by_cluster], dtype=float)
    counts = np.array([d.size for d in values_by_cluster], dtype=float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(sums), (b, len(sums)))
    draws = sums[idx].sum(1) / counts[idx].sum(1) * scale
    a = (1 - level) / 2
    return Interval(float(sums.sum() / counts.sum() * scale), float(np.quantile(draws, a)),
                    float(np.quantile(draws, 1 - a)))


def secant_scale(f_p: float) -> float:
    """Multiply a raw forced-choice mean difference by this to get corrected points per log-f."""
    return 1.0 / (GUESS_SCALE * math.log(f_p))


def contrasts(can: np.ndarray, dec: np.ndarray, clamp: np.ndarray, nat: np.ndarray) -> dict[str, np.ndarray]:
    """Per-episode contrasts (raw points) from the four arms' per-episode outcomes."""
    te, tnie, pnie = can - nat, clamp - nat, can - dec
    return {"TE": te, "TNIE": tnie, "PNIE": pnie, "INT": tnie - pnie, "PNDE": can - clamp}


def material(b: Interval, line: float = LINE) -> bool:
    return b.point >= line and b.lo > 0


def below_line(b: Interval, line: float = LINE) -> bool:
    return b.hi < line


def decide_subject(b_tnie: Interval, b_pnie: Interval, rf_median: float, line: float = LINE) -> str:
    """Per-subject reading at (K_p, f_p), after the instrument gates and the operating-point
    rule have passed (INVALID and NOT_ADMISSIBLE are decided upstream).

    1. MATERIAL: TNIE at least the line with its lower end above 0 (restoring canonical
       decay mass at the re-segmented writes recovers a material share of recall).
    2. TNIE's upper end below the line (the oracle decay-parity benefit is below the line):
       a. MASKED if PNIE is material: pure decay costs recall at canonical writes, but the
          re-segmented writes absorb it (negative decay-by-write interaction);
       b. SELF_NORMALIZED if the median R_F is below 1.5: the gates charge fragments less
          than 1.5 x canonical decay, so both decay contrasts are near the identity and the
          step does not test whether excess decay mass costs recall;
       c. KILL if PNIE's upper end is also below the line;
       d. PARITY_NULL otherwise (oracle benefit below the line, pure decay undetermined).
    3. INCONCLUSIVE otherwise."""
    if material(b_tnie, line):
        return "MATERIAL"
    if below_line(b_tnie, line):
        if material(b_pnie, line):
            return "MASKED"
        if rf_median < RF_MIN:
            return "SELF_NORMALIZED"
        if below_line(b_pnie, line):
            return "KILL"
        return "PARITY_NULL"
    return "INCONCLUSIVE"


def decide_overall(subject_readings: dict[str, str]) -> str:
    """Readings per subject: MATERIAL, KILL, MASKED, SELF_NORMALIZED, PARITY_NULL,
    INCONCLUSIVE, NOT_ADMISSIBLE or INVALID."""
    vals = set(subject_readings.values())
    if "INVALID" in vals:
        return "INVALID"
    if "NOT_ADMISSIBLE" in vals:
        return "NOT_ADMISSIBLE"
    if len(vals) == 1:
        return vals.pop()
    if "MATERIAL" in vals and vals - {"MATERIAL"} <= set(LOSS_NULL_READINGS):
        return "SPLIT"
    if vals <= set(LOSS_NULL_READINGS):
        return "LOSS_NULL_MIXED"
    return "INCONCLUSIVE"


def read_subject(can: np.ndarray, dec: np.ndarray, clamp: np.ndarray, nat: np.ndarray, article: np.ndarray,
                 f_p: float, rf_median: float) -> dict:
    """Full registered computation for one subject from per-episode arm outcomes (points) and
    each episode's article id. Returns every contrast's estimate and interval and the reading."""
    c = contrasts(can, dec, clamp, nat)
    order = np.argsort(article, kind="stable")
    art_sorted = article[order]
    cuts = np.flatnonzero(np.diff(art_sorted)) + 1
    s = secant_scale(f_p)
    est = {}
    for name, x in c.items():
        groups = np.split(x[order], cuts)
        est[name] = cluster_normal(groups, scale=s)
    reading = decide_subject(est["TNIE"], est["PNIE"], rf_median)
    return {"estimates": {k: v.__dict__ for k, v in est.items()}, "reading": reading, "f_p": f_p,
            "rf_median": rf_median}
