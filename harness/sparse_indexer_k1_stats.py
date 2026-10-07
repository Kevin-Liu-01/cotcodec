"""Statistics and decision rules of the Q3 K1 localization screen (pure NumPy).

Inputs are per-family recall tables in recall points (0-100). A *family* is one
(pair, Belebele question) cell: its MN prompt and its CX (or CS) prompt share
haystack, needle and position and differ only in the query language. Families
are clustered by Belebele passage link.

Registered statistics (preregistration ``q3-k1-localization-screen-v1``):

* ``xi_T`` = macro over pairs of the family mean of
  ``[R_ind(MN) - R_ind(CX)] - [R_T(MN) - R_T(CX)]`` with ``R_ind`` the
  seed mean at the frozen learning rate (the contract's own-target excess).
* ``xi_rel_T`` = macro over pairs of ``G(MN) - G(CX)`` where
  ``G(c) = (R_ind(c) - R_rand(c)) / (R_T(c) - R_rand(c))`` on pair condition
  means (scale-free co-statistic: the share of the target's above-chance recall
  the indexer keeps). Evaluability is decided once, on the point pair means:
  if any pair has ``R_T(c) - R_rand(c) <= 1`` point, ``xi_rel_T`` is not
  evaluable. Inside bootstrap replicates the denominator is
  ``max(R_T(c) - R_rand(c), 1)`` so a replicate never divides by a vanishing or
  negative headroom; the number of replicates in which that floor was active
  is reported (``clipped_replicates``).
* Decision interval = point +/- t_{0.995, df} * sqrt(se_cluster^2 + s_seed^2 / n_seeds),
  where se_cluster is the SD of a passage-cluster bootstrap (B = 10,000,
  NumPy seed 42, macro-averaging inside each replicate, seeds held fixed),
  s_seed is the SD of the per-seed statistics and df is the
  Welch-Satterthwaite degrees of freedom of the two variance components
  (``n_clusters - 1`` for the cluster term, ``n_seeds - 1`` for the seed term).
  With three seeds a seed-dominated interval uses df close to 2, so the
  interval keeps about 98 to 99 percent coverage when one term dominates,
  instead of the ~88 percent a normal quantile would give. When the two terms
  are comparable, a small s_seed by chance raises df toward the cluster
  term's and coverage falls to about 96.4 percent (pre-freeze audit
  simulation); the point thresholds still keep GO at a true xi of 5 or below,
  and NEGATIVE at 9 or above, near zero.
* ``final_verdict`` applies program decision D16: HOLD is terminal, and a
  V1 extension that the main read calls for is mandatory; one that was not
  run or ended void makes the final verdict INCONCLUSIVE.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy import stats

from harness.translation_supervised_indexer import pooled_seed_sd, sigma_upper_bound

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]

CONFIDENCE = 0.99
Z_99 = float(stats.norm.ppf(0.5 + CONFIDENCE / 2))
BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 42

GO_XI_POINTS = 10.0
NEGATIVE_XI_POINTS = 5.0
NEGATIVE_XI_UPPER_POINTS = 10.0
NEGATIVE_XI_REL = 0.10
NEGATIVE_XI_REL_UPPER = 0.20
MAX_HALF_WIDTH_POINTS = 5.0
H1_INTERPRET_POINTS = 10.0
H1_NEGATIVE_POINTS = 20.0
H2A_ACCURACY_POINTS = 30.0
H2B_POINTS = 5.0
V1_TOLERANCE_POINTS = 5.0
V2_TOLERANCE_POINTS = 1.0
ATTRIBUTION_POINTS = 5.0
HEADROOM_FLOOR_POINTS = 1.0


class StatsContractError(ValueError):
    """Raised when a statistics input violates the registered table contract."""


# --------------------------------------------------------------------------- #
# Tables
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class FamilyTable:
    """Per-family recalls for one target T on one set of pairs.

    ``ind_mn`` and ``ind_cx`` are ``(seeds, families)``; ``tgt_*`` and
    ``rand_*`` are ``(families,)``. ``pair`` and ``cluster`` label families.
    """

    pair: IntArray
    cluster: IntArray
    ind_mn: FloatArray
    ind_cx: FloatArray
    tgt_mn: FloatArray
    tgt_cx: FloatArray
    rand_mn: FloatArray
    rand_cx: FloatArray

    def __post_init__(self) -> None:
        pair = np.asarray(self.pair, dtype=np.int64)
        cluster = np.asarray(self.cluster, dtype=np.int64)
        if pair.ndim != 1 or cluster.shape != pair.shape or not pair.size:
            raise StatsContractError("pair and cluster must label every family")
        n = pair.size
        arrays: dict[str, np.ndarray] = {}
        for name in ("ind_mn", "ind_cx"):
            value = np.asarray(getattr(self, name), dtype=np.float64)
            if value.ndim != 2 or value.shape[1] != n or value.shape[0] < 1:
                raise StatsContractError(f"{name} must be (seeds, families)")
            arrays[name] = value
        if arrays["ind_mn"].shape != arrays["ind_cx"].shape:
            raise StatsContractError("indexer tables must share seeds")
        for name in ("tgt_mn", "tgt_cx", "rand_mn", "rand_cx"):
            value = np.asarray(getattr(self, name), dtype=np.float64)
            if value.shape != (n,):
                raise StatsContractError(f"{name} must be (families,)")
            arrays[name] = value
        for name, value in arrays.items():
            if not np.isfinite(value).all() or value.min() < 0.0 or value.max() > 100.0:
                raise StatsContractError(f"{name} must be finite recall points in [0, 100]")
        object.__setattr__(self, "pair", pair)
        object.__setattr__(self, "cluster", cluster)
        for name, value in arrays.items():
            object.__setattr__(self, name, value)

    @property
    def n_seeds(self) -> int:
        return int(self.ind_mn.shape[0])

    @property
    def n_families(self) -> int:
        return int(self.pair.size)


def _pair_cluster_sums(
    values: FloatArray, pair: IntArray, cluster: IntArray, n_pairs: int, n_clusters: int
) -> FloatArray:
    sums = np.zeros((n_clusters, n_pairs))
    np.add.at(sums, (cluster, pair), values)
    return sums


def _macro(pair_means: FloatArray) -> FloatArray:
    with np.errstate(invalid="ignore"):
        return np.nanmean(pair_means, axis=-1)


def _cluster_weights(n_clusters: int, replicates: int, seed: int) -> FloatArray:
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, n_clusters, size=(replicates, n_clusters))
    weights = np.zeros((replicates, n_clusters))
    rows = np.repeat(np.arange(replicates), n_clusters)
    np.add.at(weights, (rows, draws.ravel()), 1.0)
    return weights


@dataclass(frozen=True)
class _Design:
    pair: IntArray
    cluster: IntArray
    n_pairs: int
    n_clusters: int
    counts: FloatArray  # (clusters, pairs)

    @classmethod
    def of(cls, pair: IntArray, cluster: IntArray) -> _Design:
        _, pair_index = np.unique(pair, return_inverse=True)
        _, cluster_index = np.unique(cluster, return_inverse=True)
        n_pairs = int(pair_index.max()) + 1
        n_clusters = int(cluster_index.max()) + 1
        counts = _pair_cluster_sums(
            np.ones(pair.size), pair_index, cluster_index, n_pairs, n_clusters
        )
        return cls(pair_index, cluster_index, n_pairs, n_clusters, counts)

    def sums(self, values: FloatArray) -> FloatArray:
        return _pair_cluster_sums(values, self.pair, self.cluster, self.n_pairs, self.n_clusters)

    def pair_means(self, values: FloatArray, weights: FloatArray | None = None) -> FloatArray:
        sums = self.sums(values)
        if weights is None:
            return sums.sum(axis=0) / self.counts.sum(axis=0)
        with np.errstate(invalid="ignore", divide="ignore"):
            return (weights @ sums) / (weights @ self.counts)


# --------------------------------------------------------------------------- #
# Point statistics
# --------------------------------------------------------------------------- #


def family_excess(table: FamilyTable, seed_index: int | None = None) -> FloatArray:
    """Per-family ``[R_ind(MN) - R_ind(CX)] - [R_T(MN) - R_T(CX)]``."""

    if seed_index is None:
        ind_mn, ind_cx = table.ind_mn.mean(axis=0), table.ind_cx.mean(axis=0)
    else:
        ind_mn, ind_cx = table.ind_mn[seed_index], table.ind_cx[seed_index]
    return (ind_mn - ind_cx) - (table.tgt_mn - table.tgt_cx)


def xi_point(table: FamilyTable, seed_index: int | None = None) -> float:
    design = _Design.of(table.pair, table.cluster)
    return float(_macro(design.pair_means(family_excess(table, seed_index))))


def _retention(ind: FloatArray, tgt: FloatArray, rnd: FloatArray, *, clip: bool) -> FloatArray:
    headroom = tgt - rnd
    with np.errstate(invalid="ignore", divide="ignore"):
        if clip:
            # Bootstrap replicates: the registered floor bounds the denominator.
            return (ind - rnd) / np.maximum(headroom, HEADROOM_FLOOR_POINTS)
        return np.where(headroom > HEADROOM_FLOOR_POINTS, (ind - rnd) / headroom, np.nan)


def _xi_rel_from_means(means: Mapping[str, FloatArray], *, clip: bool = False) -> FloatArray:
    g_mn = _retention(means["ind_mn"], means["tgt_mn"], means["rand_mn"], clip=clip)
    g_cx = _retention(means["ind_cx"], means["tgt_cx"], means["rand_cx"], clip=clip)
    diff = g_mn - g_cx
    # At the point estimate a pair without target headroom makes xi_rel
    # non-evaluable (NaN), not smaller.
    return np.where(np.isnan(diff).any(axis=-1), np.nan, diff.mean(axis=-1))


def _floor_active(means: Mapping[str, FloatArray]) -> FloatArray:
    """Per replicate: whether any pair's target headroom is at or below the floor."""

    with np.errstate(invalid="ignore"):
        low_mn = means["tgt_mn"] - means["rand_mn"] <= HEADROOM_FLOOR_POINTS
        low_cx = means["tgt_cx"] - means["rand_cx"] <= HEADROOM_FLOOR_POINTS
    return (low_mn | low_cx).any(axis=-1)


def xi_rel_point(table: FamilyTable, seed_index: int | None = None) -> float:
    design = _Design.of(table.pair, table.cluster)
    ind_mn = table.ind_mn.mean(axis=0) if seed_index is None else table.ind_mn[seed_index]
    ind_cx = table.ind_cx.mean(axis=0) if seed_index is None else table.ind_cx[seed_index]
    means = {
        "ind_mn": design.pair_means(ind_mn),
        "ind_cx": design.pair_means(ind_cx),
        "tgt_mn": design.pair_means(table.tgt_mn),
        "tgt_cx": design.pair_means(table.tgt_cx),
        "rand_mn": design.pair_means(table.rand_mn),
        "rand_cx": design.pair_means(table.rand_cx),
    }
    return float(_xi_rel_from_means(means))


# --------------------------------------------------------------------------- #
# Intervals
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Interval:
    point: float
    per_seed: tuple[float, ...]
    s_seed: float
    se_cluster: float
    se_total: float
    lower: float
    upper: float
    half_width: float
    percentile_lower: float
    percentile_upper: float
    replicates: int
    evaluable: bool
    df: float = math.inf
    quantile: float = Z_99
    clipped_replicates: int = 0

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> Interval:
        values = {name: payload[name] for name in cls.__dataclass_fields__ if name in payload}
        values["per_seed"] = tuple(float(v) for v in values.get("per_seed", ()))
        return cls(**values)


def welch_satterthwaite_df(se_cluster: float, s_seed: float, n_seeds: int,
                           n_clusters: int) -> float:
    """Degrees of freedom of ``se_cluster^2 + s_seed^2 / n_seeds``.

    The cluster term has ``n_clusters - 1`` degrees of freedom and the seed term
    ``n_seeds - 1``; a term that is zero (or has no degrees of freedom) drops out.
    """

    v_cluster = se_cluster**2
    v_seed = s_seed**2 / n_seeds if n_seeds > 0 else 0.0
    denominator = 0.0
    if v_cluster > 0.0 and n_clusters > 1:
        denominator += v_cluster**2 / (n_clusters - 1)
    if v_seed > 0.0 and n_seeds > 1:
        denominator += v_seed**2 / (n_seeds - 1)
    if denominator == 0.0:
        return math.inf
    return (v_cluster + v_seed) ** 2 / denominator


def decision_quantile(df: float) -> float:
    """Two-sided 99 percent quantile of Student t with ``df`` (normal when infinite)."""

    if not math.isfinite(df):
        return Z_99
    return float(stats.t.ppf(0.5 + CONFIDENCE / 2, df))


def _combine(point: float, per_seed: Sequence[float], boot: FloatArray, n_clusters: int,
             clipped: int = 0) -> Interval:
    finite = boot[np.isfinite(boot)]
    evaluable = (
        math.isfinite(point)
        and all(math.isfinite(v) for v in per_seed)
        and finite.size == boot.size
        and boot.size > 1
    )
    if not evaluable:
        nan = float("nan")
        return Interval(point, tuple(per_seed), nan, nan, nan, nan, nan, nan, nan, nan,
                        int(boot.size), False, nan, nan, int(clipped))
    s_seed = float(np.std(per_seed, ddof=1)) if len(per_seed) > 1 else 0.0
    se_cluster = float(np.std(finite, ddof=1))
    n_seeds = max(len(per_seed), 1)
    se_total = math.sqrt(se_cluster**2 + s_seed**2 / n_seeds)
    df = welch_satterthwaite_df(se_cluster, s_seed, n_seeds, n_clusters)
    quantile = decision_quantile(df)
    half = quantile * se_total
    lo, hi = np.percentile(finite, [0.5, 99.5])  # the 99 percent percentile interval
    return Interval(
        point=point,
        per_seed=tuple(float(v) for v in per_seed),
        s_seed=s_seed,
        se_cluster=se_cluster,
        se_total=se_total,
        lower=point - half,
        upper=point + half,
        half_width=half,
        percentile_lower=float(lo),
        percentile_upper=float(hi),
        replicates=int(boot.size),
        evaluable=True,
        df=df,
        quantile=quantile,
        clipped_replicates=int(clipped),
    )


def xi_interval(
    table: FamilyTable, replicates: int = BOOTSTRAP_REPLICATES, seed: int = BOOTSTRAP_SEED
) -> Interval:
    design = _Design.of(table.pair, table.cluster)
    weights = _cluster_weights(design.n_clusters, replicates, seed)
    boot = _macro(design.pair_means(family_excess(table), weights))
    per_seed = [xi_point(table, s) for s in range(table.n_seeds)]
    return _combine(xi_point(table), per_seed, boot, design.n_clusters)


def xi_rel_interval(
    table: FamilyTable, replicates: int = BOOTSTRAP_REPLICATES, seed: int = BOOTSTRAP_SEED
) -> Interval:
    design = _Design.of(table.pair, table.cluster)
    weights = _cluster_weights(design.n_clusters, replicates, seed)
    means = {
        "ind_mn": design.pair_means(table.ind_mn.mean(axis=0), weights),
        "ind_cx": design.pair_means(table.ind_cx.mean(axis=0), weights),
        "tgt_mn": design.pair_means(table.tgt_mn, weights),
        "tgt_cx": design.pair_means(table.tgt_cx, weights),
        "rand_mn": design.pair_means(table.rand_mn, weights),
        "rand_cx": design.pair_means(table.rand_cx, weights),
    }
    point = xi_rel_point(table)
    per_seed = [xi_rel_point(table, s) for s in range(table.n_seeds)]
    if not math.isfinite(point):
        # Registered rule: evaluability is decided on the point pair means only.
        return _combine(point, per_seed, np.full(replicates, np.nan), design.n_clusters)
    boot = _xi_rel_from_means(means, clip=True)
    clipped = int(_floor_active(means).sum())
    return _combine(point, per_seed, boot, design.n_clusters, clipped)


def macro_mean_interval(
    values: FloatArray,
    pair: IntArray,
    cluster: IntArray,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> Interval:
    """Macro-over-pairs mean with a percentile cluster-bootstrap 99% interval (no seed term)."""

    values = np.asarray(values, dtype=np.float64)
    if values.shape != np.asarray(pair).shape or not np.isfinite(values).all():
        raise StatsContractError("values must be finite and label-aligned")
    design = _Design.of(np.asarray(pair), np.asarray(cluster))
    weights = _cluster_weights(design.n_clusters, replicates, seed)
    point = float(_macro(design.pair_means(values)))
    boot = _macro(design.pair_means(values, weights))
    interval = _combine(point, [point], boot, design.n_clusters)
    # Without a seed term the decision interval is the percentile interval.
    return Interval(
        point=interval.point,
        per_seed=interval.per_seed,
        s_seed=0.0,
        se_cluster=interval.se_cluster,
        se_total=interval.se_cluster,
        lower=interval.percentile_lower,
        upper=interval.percentile_upper,
        half_width=(interval.percentile_upper - interval.percentile_lower) / 2.0,
        percentile_lower=interval.percentile_lower,
        percentile_upper=interval.percentile_upper,
        replicates=interval.replicates,
        evaluable=interval.evaluable,
        df=interval.df,
        quantile=interval.quantile,
    )


def se_cluster_of_macro(
    values: FloatArray, pair: IntArray, cluster: IntArray,
    replicates: int = BOOTSTRAP_REPLICATES, seed: int = BOOTSTRAP_SEED,
) -> float:
    return macro_mean_interval(values, pair, cluster, replicates, seed).se_cluster


# --------------------------------------------------------------------------- #
# Gates and the verdict
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class AdequacyRead:
    """English literal (ML) recall of each seed's indexer against its target."""

    indexer_ml_by_seed: tuple[float, ...]
    target_ml: float

    def as_dict(self) -> dict[str, Any]:
        return {"indexer_ml_by_seed": list(self.indexer_ml_by_seed), "target_ml": self.target_ml}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> AdequacyRead:
        return cls(tuple(float(v) for v in payload["indexer_ml_by_seed"]),
                   float(payload["target_ml"]))

    @property
    def v1_pass(self) -> bool:
        return all(v >= self.target_ml - V1_TOLERANCE_POINTS for v in self.indexer_ml_by_seed)

    @property
    def v2_bug_tell(self) -> bool:
        return any(v > self.target_ml + V2_TOLERANCE_POINTS for v in self.indexer_ml_by_seed)


@dataclass(frozen=True)
class HeadroomRead:
    h1_points: float  # max over T of macro [R_T(CX) - R_rand(CX)]
    h2a: Interval  # dense CX MC acc_norm accuracy, points
    h2b: Interval  # needle-present minus needle-absent CX accuracy, points

    @property
    def h1_interpretable(self) -> bool:
        return self.h1_points >= H1_INTERPRET_POINTS

    @property
    def h1_negative_ready(self) -> bool:
        return self.h1_points >= H1_NEGATIVE_POINTS

    @property
    def h2a_pass(self) -> bool:
        return self.h2a.evaluable and self.h2a.lower > H2A_ACCURACY_POINTS

    @property
    def h2b_pass(self) -> bool:
        return self.h2b.evaluable and self.h2b.lower > 0.0 and self.h2b.point >= H2B_POINTS

    def as_dict(self) -> dict[str, Any]:
        return {"h1_points": self.h1_points, "h2a": self.h2a.as_dict(),
                "h2b": self.h2b.as_dict()}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> HeadroomRead:
        return cls(float(payload["h1_points"]), Interval.from_dict(payload["h2a"]),
                   Interval.from_dict(payload["h2b"]))


@dataclass(frozen=True)
class TargetRead:
    target: str
    xi: Interval
    xi_rel: Interval
    adequacy: AdequacyRead
    integrity_ok: bool

    @property
    def go(self) -> bool:
        return (
            self.xi.evaluable
            and self.xi_rel.evaluable
            and self.xi.point >= GO_XI_POINTS
            and self.xi.lower > 0.0
            and self.xi_rel.lower > 0.0
        )

    @property
    def negative(self) -> bool:
        return (
            self.xi.evaluable
            and self.xi_rel.evaluable
            and self.xi.point <= NEGATIVE_XI_POINTS
            and self.xi.upper < NEGATIVE_XI_UPPER_POINTS
            and self.xi.half_width <= MAX_HALF_WIDTH_POINTS
            and self.xi_rel.point <= NEGATIVE_XI_REL
            and self.xi_rel.upper < NEGATIVE_XI_REL_UPPER
        )

    def as_dict(self) -> dict[str, Any]:
        return {"target": self.target, "xi": self.xi.as_dict(), "xi_rel": self.xi_rel.as_dict(),
                "adequacy": self.adequacy.as_dict(), "integrity_ok": self.integrity_ok}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetRead:
        return cls(str(payload["target"]), Interval.from_dict(payload["xi"]),
                   Interval.from_dict(payload["xi_rel"]),
                   AdequacyRead.from_dict(payload["adequacy"]), bool(payload["integrity_ok"]))


@dataclass(frozen=True)
class Verdict:
    verdict: str
    reasons: tuple[str, ...]
    per_target: dict[str, dict[str, Any]] = field(default_factory=dict)


def k1_verdict(reads: Sequence[TargetRead], headroom: HeadroomRead, *,
               after_extension: bool = False) -> Verdict:
    """Apply the registered K1-screen rules in their registered order.

    Order: VOID (any V3 failure), HOLD (any V2 bug tell), UNINTERPRETABLE
    (H1 below 10, H2a or H2b failing), then V1_EXTENSION_REQUIRED when no target
    passes V1, then GO from any target that passes V1, then NEGATIVE (every
    target passes V1 and is in the NEGATIVE region, and H1 >= 20), else
    INCONCLUSIVE. ``after_extension=True`` is the combined read after the one
    registered V1 extension: a target still failing V1 cannot request another
    extension, so V1_EXTENSION_REQUIRED becomes INCONCLUSIVE.
    """

    if not reads:
        raise StatsContractError("the verdict needs at least one target read")
    reasons: list[str] = []
    per_target = {
        read.target: {
            "go": read.go,
            "negative": read.negative,
            "v1_pass": read.adequacy.v1_pass,
            "v2_bug_tell": read.adequacy.v2_bug_tell,
            "integrity_ok": read.integrity_ok,
            "xi": read.xi.as_dict(),
            "xi_rel": read.xi_rel.as_dict(),
        }
        for read in reads
    }
    if not all(read.integrity_ok for read in reads):
        return Verdict("VOID", ("V3 integrity failed",), per_target)
    if any(read.adequacy.v2_bug_tell for read in reads):
        return Verdict("HOLD", ("V2 bug tell: an indexer beat its target on English ML",),
                       per_target)
    if not headroom.h1_interpretable:
        reasons.append(f"H1 {headroom.h1_points:.2f} below {H1_INTERPRET_POINTS}")
    if not headroom.h2a_pass:
        reasons.append("H2a dense CX accuracy lower bound not above 30")
    if not headroom.h2b_pass:
        reasons.append("H2b needle-present minus needle-absent gate failed")
    if reasons:
        return Verdict("UNINTERPRETABLE", tuple(reasons), per_target)
    adequate = [read for read in reads if read.adequacy.v1_pass]
    if not adequate:
        if after_extension:
            return Verdict("INCONCLUSIVE",
                           ("V1 failed for every target after the registered extension",),
                           per_target)
        return Verdict("V1_EXTENSION_REQUIRED", ("V1 failed for every target",), per_target)
    go_targets = [read.target for read in adequate if read.go]
    if go_targets:
        return Verdict("GO", (f"xi >= {GO_XI_POINTS} with both lower bounds above 0 for "
                              + ", ".join(go_targets),), per_target)
    if (
        len(adequate) == len(reads)
        and all(read.negative for read in reads)
        and headroom.h1_negative_ready
    ):
        return Verdict("NEGATIVE", ("equivalence-style K1-screen negative for every target",),
                       per_target)
    failing_v1 = [read.target for read in reads if not read.adequacy.v1_pass]
    if failing_v1:
        if after_extension:
            reasons.append("V1 still failed for " + ", ".join(failing_v1)
                           + " after the registered extension")
        else:
            reasons.append("V1 failed for " + ", ".join(failing_v1)
                           + "; the registered extension applies")
    if not headroom.h1_negative_ready:
        reasons.append(f"H1 {headroom.h1_points:.2f} below {H1_NEGATIVE_POINTS} blocks NEGATIVE")
    for read in reads:
        if read.xi.half_width > MAX_HALF_WIDTH_POINTS:
            reasons.append(f"{read.target}: half-width {read.xi.half_width:.2f} over 5 points")
        go_side_disagrees = read.xi.point >= GO_XI_POINTS and not read.xi_rel.lower > 0.0
        negative_side_disagrees = read.xi.point <= NEGATIVE_XI_POINTS and not (
            read.xi_rel.point <= NEGATIVE_XI_REL
        )
        if go_side_disagrees or negative_side_disagrees:
            reasons.append(f"{read.target}: xi and xi_rel classifications disagree")
    return Verdict("INCONCLUSIVE", tuple(reasons) or ("no registered region reached",), per_target)


EXTENSION_ELIGIBLE_VERDICTS = ("V1_EXTENSION_REQUIRED", "INCONCLUSIVE")


def extension_targets(verdict: Verdict, reads: Sequence[TargetRead]) -> list[str]:
    """Targets the registered V1 extension retrains and re-reads (possibly none).

    The extension runs only after a main read whose verdict is
    V1_EXTENSION_REQUIRED, or INCONCLUSIVE with at least one target failing V1.
    It covers exactly the targets that failed V1; a target that passed V1 keeps
    its main read and is never re-read.
    """

    if verdict.verdict not in EXTENSION_ELIGIBLE_VERDICTS:
        return []
    return [read.target for read in reads if not read.adequacy.v1_pass]


def combine_after_extension(main_reads: Sequence[TargetRead],
                            extension_reads: Sequence[TargetRead]) -> list[TargetRead]:
    """Main reads for targets that passed V1, extension reads for the rest (main order)."""

    by_target = {read.target: read for read in extension_reads}
    expected = {read.target for read in main_reads if not read.adequacy.v1_pass}
    if set(by_target) != expected:
        raise StatsContractError(
            f"the extension must re-read exactly the V1-failing targets {sorted(expected)}, "
            f"not {sorted(by_target)}")
    return [by_target.get(read.target, read) for read in main_reads]


def final_verdict(main: Verdict, main_reads: Sequence[TargetRead],
                  extension: Verdict | None) -> Verdict:
    """The experiment's final verdict (preregistration decision rules, program decision D16).

    A main read that does not call for the V1 extension is final; HOLD among
    them is terminal for the experiment id. When the main read calls for the
    extension, the extension is mandatory and its combined verdict is final,
    except that an extension that was not run (``extension`` is None) or ended
    void makes the final verdict INCONCLUSIVE; no second extension runs.
    """

    if not extension_targets(main, main_reads):
        if extension is not None:
            raise StatsContractError(
                f"the main read ({main.verdict}) does not call for the V1 extension")
        return main
    if extension is None or extension.verdict == "VOID":
        return Verdict("INCONCLUSIVE",
                       ("the registered V1 extension was not run or ended void",),
                       extension.per_target if extension is not None else main.per_target)
    if extension.verdict == "V1_EXTENSION_REQUIRED":
        raise StatsContractError("the extension's combined read must be read with "
                                 "after_extension=True, never as V1_EXTENSION_REQUIRED")
    return extension


def attribution_label(xi_cx: float, xi_cs: float) -> str:
    """Descriptive: 'cross-script' only if xi_CX - xi_CS >= 5 points."""

    if not (math.isfinite(xi_cx) and math.isfinite(xi_cs)):
        return "not-evaluable"
    if xi_cx - xi_cs >= ATTRIBUTION_POINTS:
        return "cross-script"
    return "cross-lingual excess on cross-script pairs"


def seed_noise_report(cx_recall_by_target_and_seed: Mapping[str, Sequence[float]]) -> dict:
    """Pooled within-target seed SD of macro CX recall with honest df and its 80% bound."""

    pooled = pooled_seed_sd(cx_recall_by_target_and_seed)
    return {
        "sigma_hat": pooled.sigma_hat,
        "degrees_of_freedom": pooled.degrees_of_freedom,
        "configurations": pooled.configurations,
        "sigma_upper_80": sigma_upper_bound(pooled.sigma_hat, pooled.degrees_of_freedom, 0.80)
        if pooled.sigma_hat > 0
        else 0.0,
        "note": "init-only variance: seeds vary indexer initialisation, the stream is shared",
        "per_target_sd": {
            name: float(np.std(values, ddof=1))
            for name, values in cx_recall_by_target_and_seed.items()
        },
    }


__all__ = [
    "BOOTSTRAP_REPLICATES",
    "BOOTSTRAP_SEED",
    "AdequacyRead",
    "FamilyTable",
    "HeadroomRead",
    "Interval",
    "StatsContractError",
    "TargetRead",
    "Verdict",
    "attribution_label",
    "combine_after_extension",
    "decision_quantile",
    "extension_targets",
    "family_excess",
    "final_verdict",
    "k1_verdict",
    "macro_mean_interval",
    "se_cluster_of_macro",
    "seed_noise_report",
    "welch_satterthwaite_df",
    "xi_interval",
    "xi_point",
    "xi_rel_interval",
    "xi_rel_point",
]
