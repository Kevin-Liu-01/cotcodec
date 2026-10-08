import math

import pytest

from harness.q2_mutation import stats


def _units(spec: dict[str, list[bool]]) -> list[stats.Unit]:
    return [stats.Unit(task, event) for task, events in spec.items() for event in events]


def test_task_equal_rate_weights_tasks_not_mutants() -> None:
    groups = {"a": [True, True, True], "b": [False]}
    assert stats.task_equal_rate(groups) == pytest.approx(0.5)
    assert stats.pooled_rate(groups) == pytest.approx(0.75)


def test_cluster_bootstrap_is_seeded_and_wider_than_naive() -> None:
    spec = {f"t{i}": [i % 4 == 0] * 3 for i in range(40)}
    first = stats.cluster_bootstrap_ci(_units(spec), n_boot=2000, seed=42)
    again = stats.cluster_bootstrap_ci(_units(spec), n_boot=2000, seed=42)
    assert first == again
    assert first.n_clusters == 40 and first.n_units == 120
    assert first.low < first.estimate < first.high
    naive_low, naive_high = stats.wilson_interval(30, 120)
    assert (first.high - first.low) > (naive_high - naive_low)


def test_wilson_matches_known_value() -> None:
    low, high = stats.wilson_interval(76, 80)
    assert low == pytest.approx(0.8786, abs=1e-3)
    assert high == pytest.approx(0.9804, abs=1e-3)


def test_zero_event_bounds_and_kill_feasibility() -> None:
    assert stats.zero_event_upper_bound(1) == pytest.approx(0.95)
    n = stats.min_clusters_for_upper_bound(0.03)
    assert stats.zero_event_upper_bound(n) < 0.03 <= stats.zero_event_upper_bound(n - 1)
    assert n == 99
    assert stats.min_clusters_for_upper_bound(0.10) == 29


def test_mde_shrinks_with_more_clusters_and_grows_with_icc() -> None:
    small = stats.minimum_detectable_rate(0.0, 20, 3, 0.3)
    large = stats.minimum_detectable_rate(0.0, 80, 3, 0.3)
    correlated = stats.minimum_detectable_rate(0.0, 80, 3, 0.9)
    assert large < small
    assert correlated > large
    assert stats.design_effect(3, 0.5) == pytest.approx(2.0)


def test_normal_quantile() -> None:
    assert stats._z(0.975) == pytest.approx(1.959964, abs=1e-5)
    assert stats._z(0.8) == pytest.approx(0.841621, abs=1e-5)
    assert stats._z(0.01) == pytest.approx(-2.326348, abs=1e-5)


def test_hajek_reweights_by_inclusion_probability() -> None:
    items = [
        stats.AuditItem("i1", "t1", "agree", 0.1, True),
        stats.AuditItem("i2", "t2", "disagree", 1.0, False),
        stats.AuditItem("i3", "t3", "disagree", 1.0, False),
    ]
    # One wrong item standing for 10 agreements outweighs two certain items.
    assert stats.hajek_rate(items) == pytest.approx(10 / 12)
    interval = stats.audit_label_error(items, n_boot=500, seed=1)
    assert interval.low <= interval.estimate <= interval.high
    with pytest.raises(ValueError, match="inclusion"):
        stats.AuditItem("x", "t", "s", 0.0, True).weight()


def test_cohens_kappa() -> None:
    assert stats.cohens_kappa(["y", "n", "y", "n"], ["y", "n", "y", "n"]) == 1.0
    assert math.isclose(stats.cohens_kappa(["y", "y", "n", "n"], ["y", "n", "y", "n"]), 0.0)
    with pytest.raises(ValueError):
        stats.cohens_kappa(["y"], [])
