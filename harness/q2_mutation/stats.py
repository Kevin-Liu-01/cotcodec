"""Task-clustered inference and design-weighted audit estimators for Q2 mutation.

Mutants inside one task share checker code paths, so they are not independent.
Every pooled or family rate here treats the task as the unit of resampling:

* ``task_equal_rate``: the estimand. Within a family, each task's rate is the
  share of its admitted mutants with the event (pass for should-fail labels,
  non-pass for should-pass labels); the family rate is the unweighted mean
  over tasks (tasks weighted equally, at most three mutants per task and
  operator by design).
* ``cluster_bootstrap_ci``: percentile interval from resampling tasks with
  replacement (10,000 resamples by default, seeded).
* ``wilson_interval``: only for task-level proportions (one Bernoulli per task).
* ``zero_event_upper_bound`` / ``min_clusters_for_upper_bound``: what a
  kill criterion of the form "upper bound below x" needs in tasks, so a
  criterion that can never fire is caught before the freeze.
* ``hajek_rate`` / ``audit_label_error``: the audit sample is stratified with
  known inclusion probabilities; label error is estimated with inverse-
  probability (Hajek) weights and a task-cluster bootstrap that keeps each
  item's design weight.
* ``cohens_kappa``: rater agreement.

All functions are pure and deterministic given their seed.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from collections.abc import Callable, Hashable, Iterable, Mapping, Sequence
from dataclasses import dataclass

Z95 = 1.959963984540054


@dataclass(frozen=True)
class Unit:
    """One admitted mutant: its task cluster and whether the event happened."""

    task_id: str
    event: bool


@dataclass(frozen=True)
class Interval:
    estimate: float
    low: float
    high: float
    n_clusters: int
    n_units: int
    method: str


def group_by_task(units: Iterable[Unit]) -> dict[str, list[bool]]:
    groups: dict[str, list[bool]] = defaultdict(list)
    for unit in units:
        groups[unit.task_id].append(bool(unit.event))
    return dict(groups)


def task_equal_rate(groups: Mapping[str, Sequence[bool]]) -> float:
    """Mean over tasks of the per-task event share (tasks weighted equally)."""
    rates = [sum(events) / len(events) for events in groups.values() if events]
    if not rates:
        raise ValueError("no task has any admitted unit")
    return sum(rates) / len(rates)


def pooled_rate(groups: Mapping[str, Sequence[bool]]) -> float:
    total = sum(len(events) for events in groups.values())
    if total == 0:
        raise ValueError("no admitted unit")
    return sum(sum(events) for events in groups.values()) / total


def cluster_bootstrap_ci(
    units: Iterable[Unit],
    *,
    statistic: Callable[[Mapping[str, Sequence[bool]]], float] = task_equal_rate,
    n_boot: int = 10_000,
    seed: int = 42,
    alpha: float = 0.05,
) -> Interval:
    """Percentile CI from resampling tasks with replacement."""
    groups = group_by_task(units)
    if not groups:
        raise ValueError("no units")
    keys = sorted(groups)
    estimate = statistic(groups)
    rng = random.Random(seed)
    draws: list[float] = []
    for _ in range(n_boot):
        sample = {f"{i}:{key}": groups[key] for i, key in enumerate(rng.choices(keys, k=len(keys)))}
        draws.append(statistic(sample))
    draws.sort()
    low = _quantile(draws, alpha / 2)
    high = _quantile(draws, 1 - alpha / 2)
    return Interval(
        estimate=estimate,
        low=low,
        high=high,
        n_clusters=len(keys),
        n_units=sum(len(v) for v in groups.values()),
        method=f"task-cluster percentile bootstrap, {n_boot} resamples, seed {seed}",
    )


def _quantile(sorted_values: Sequence[float], q: float) -> float:
    if not sorted_values:
        raise ValueError("empty")
    position = q * (len(sorted_values) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def wilson_interval(successes: int, n: int, z: float = Z95) -> tuple[float, float]:
    if n <= 0:
        raise ValueError("n must be positive")
    if not 0 <= successes <= n:
        raise ValueError("successes must be in [0, n]")
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def zero_event_upper_bound(n_clusters: int, alpha: float = 0.05) -> float:
    """Exact one-sided (1 - alpha) upper bound for a rate with 0 events in n."""
    if n_clusters <= 0:
        raise ValueError("n must be positive")
    return 1.0 - alpha ** (1.0 / n_clusters)


def min_clusters_for_upper_bound(target: float, alpha: float = 0.05) -> int:
    """Smallest n with zero_event_upper_bound(n) < target (exact, 0 events)."""
    if not 0 < target < 1:
        raise ValueError("target must be in (0, 1)")
    n = math.ceil(math.log(alpha) / math.log(1 - target))
    while zero_event_upper_bound(n, alpha) >= target:
        n += 1
    return n


def design_effect(mean_cluster_size: float, icc: float) -> float:
    return 1.0 + max(0.0, mean_cluster_size - 1.0) * icc


def minimum_detectable_rate(
    p0: float,
    n_clusters: int,
    mean_cluster_size: float,
    icc: float,
    *,
    alpha: float = 0.05,
    power: float = 0.8,
) -> float:
    """Smallest true rate p > p0 that a one-sided test of H0: rate = p0 detects.

    Normal approximation with the cluster design effect:
    ``p - p0 >= (z_{1-a} sqrt(p0 (1-p0)) + z_{power} sqrt(p (1-p))) sqrt(deff / (n m))``.
    """
    if not 0 <= p0 < 1:
        raise ValueError("p0 must be in [0, 1)")
    scale = math.sqrt(design_effect(mean_cluster_size, icc) / (n_clusters * mean_cluster_size))
    z_a, z_b = _z(1 - alpha), _z(power)
    p = p0
    while p < 1.0:
        p = min(1.0, p + 1e-4)
        if p - p0 >= (z_a * math.sqrt(p0 * (1 - p0)) + z_b * math.sqrt(p * (1 - p))) * scale:
            return p
    return 1.0


def _z(q: float) -> float:
    """Inverse standard normal CDF (Acklam's rational approximation)."""
    if not 0 < q < 1:
        raise ValueError("q must be in (0, 1)")
    a = [
        -39.69683028665376,
        220.9460984245205,
        -275.9285104469687,
        138.3577518672690,
        -30.66479806614716,
        2.506628277459239,
    ]
    b = [
        -54.47609879822406,
        161.5858368580409,
        -155.6989798598866,
        66.80131188771972,
        -13.28068155288572,
    ]
    c = [
        -0.007784894002430293,
        -0.3223964580411365,
        -2.400758277161838,
        -2.549732539343734,
        4.374664141464968,
        2.938163982698783,
    ]
    d = [0.007784695709041462, 0.3224671290700398, 2.445134137142996, 3.754408661907416]
    low, high = 0.02425, 1 - 0.02425
    if q < low:
        t = math.sqrt(-2 * math.log(q))
        return (((((c[0] * t + c[1]) * t + c[2]) * t + c[3]) * t + c[4]) * t + c[5]) / (
            (((d[0] * t + d[1]) * t + d[2]) * t + d[3]) * t + 1
        )
    if q > high:
        return -_z(1 - q)
    t = q - 0.5
    r = t * t
    return (
        (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5])
        * t
        / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
    )


# --- audit ------------------------------------------------------------------


@dataclass(frozen=True)
class AuditItem:
    """One audited mutant with its known inclusion probability."""

    item_id: str
    task_id: str
    stratum: str
    inclusion_probability: float
    label_wrong: bool

    def weight(self) -> float:
        if not 0 < self.inclusion_probability <= 1:
            raise ValueError(f"{self.item_id}: inclusion probability must be in (0, 1]")
        return 1.0 / self.inclusion_probability


def hajek_rate(items: Sequence[AuditItem]) -> float:
    """Inverse-probability-weighted (Hajek) share of items whose label is wrong."""
    if not items:
        raise ValueError("no audited items")
    total = sum(item.weight() for item in items)
    return sum(item.weight() for item in items if item.label_wrong) / total


def audit_label_error(
    items: Sequence[AuditItem], *, n_boot: int = 10_000, seed: int = 42, alpha: float = 0.05
) -> Interval:
    """Hajek label-error estimate with a task-cluster bootstrap CI."""
    if not items:
        raise ValueError("no audited items")
    by_task: dict[str, list[AuditItem]] = defaultdict(list)
    for item in items:
        by_task[item.task_id].append(item)
    keys = sorted(by_task)
    rng = random.Random(seed)
    draws = []
    for _ in range(n_boot):
        sample = [item for key in rng.choices(keys, k=len(keys)) for item in by_task[key]]
        draws.append(hajek_rate(sample))
    draws.sort()
    return Interval(
        estimate=hajek_rate(items),
        low=_quantile(draws, alpha / 2),
        high=_quantile(draws, 1 - alpha / 2),
        n_clusters=len(keys),
        n_units=len(items),
        method=f"Hajek IPW, task-cluster bootstrap {n_boot}, seed {seed}",
    )


def cohens_kappa(first: Sequence[Hashable], second: Sequence[Hashable]) -> float:
    if len(first) != len(second) or not first:
        raise ValueError("ratings must be non-empty and paired")
    n = len(first)
    categories = sorted(set(first) | set(second), key=str)
    observed = sum(a == b for a, b in zip(first, second, strict=True)) / n
    expected = sum(
        (sum(a == c for a in first) / n) * (sum(b == c for b in second) / n) for c in categories
    )
    if expected == 1.0:
        return 1.0
    return (observed - expected) / (1.0 - expected)
