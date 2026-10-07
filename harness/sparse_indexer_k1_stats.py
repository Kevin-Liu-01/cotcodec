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
  the indexer keeps).
* Decision interval = point +/- z_{0.995} * sqrt(se_cluster^2 + s_seed^2 / n_seeds),
  where se_cluster is the SD of a passage-cluster bootstrap (B = 10,000,
  NumPy seed 42, macro-averaging inside each replicate, seeds held fixed) and
  s_seed is the SD of the per-seed statistics.
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

Z_99 = float(stats.norm.ppf(0.995))
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


def _retention(ind: FloatArray, tgt: FloatArray, rnd: FloatArray) -> FloatArray:
    headroom = tgt - rnd
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(headroom > HEADROOM_FLOOR_POINTS, (ind - rnd) / headroom, np.nan)


def _xi_rel_from_means(means: Mapping[str, FloatArray]) -> FloatArray:
    g_mn = _retention(means["ind_mn"], means["tgt_mn"], means["rand_mn"])
    g_cx = _retention(means["ind_cx"], means["tgt_cx"], means["rand_cx"])
    diff = g_mn - g_cx
    # A pair without target headroom makes xi_rel non-evaluable (NaN), not smaller.
    return np.where(np.isnan(diff).any(axis=-1), np.nan, diff.mean(axis=-1))


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

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _combine(point: float, per_seed: Sequence[float], boot: FloatArray) -> Interval:
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
                        int(boot.size), False)
    s_seed = float(np.std(per_seed, ddof=1)) if len(per_seed) > 1 else 0.0
    se_cluster = float(np.std(finite, ddof=1))
    se_total = math.sqrt(se_cluster**2 + s_seed**2 / max(len(per_seed), 1))
    half = Z_99 * se_total
    lo, hi = np.percentile(finite, [0.5, 99.5])
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
    )


def xi_interval(
    table: FamilyTable, replicates: int = BOOTSTRAP_REPLICATES, seed: int = BOOTSTRAP_SEED
) -> Interval:
    design = _Design.of(table.pair, table.cluster)
    weights = _cluster_weights(design.n_clusters, replicates, seed)
    boot = _macro(design.pair_means(family_excess(table), weights))
    per_seed = [xi_point(table, s) for s in range(table.n_seeds)]
    return _combine(xi_point(table), per_seed, boot)


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
    boot = _xi_rel_from_means(means)
    per_seed = [xi_rel_point(table, s) for s in range(table.n_seeds)]
    return _combine(xi_rel_point(table), per_seed, boot)


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
    interval = _combine(point, [point], boot)
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


@dataclass(frozen=True)
class Verdict:
    verdict: str
    reasons: tuple[str, ...]
    per_target: dict[str, dict[str, Any]] = field(default_factory=dict)


def k1_verdict(reads: Sequence[TargetRead], headroom: HeadroomRead) -> Verdict:
    """Apply the registered K1-screen rules in their registered order."""

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
        reasons.append("V1 failed for " + ", ".join(failing_v1) + "; extension rule applies")
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
    "family_excess",
    "k1_verdict",
    "macro_mean_interval",
    "se_cluster_of_macro",
    "seed_noise_report",
    "xi_interval",
    "xi_point",
    "xi_rel_interval",
    "xi_rel_point",
]
