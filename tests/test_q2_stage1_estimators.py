"""Registered S1a estimators and tests (harness/q2_stage1/estimators.py)."""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np
import pytest

from harness.q2_stage1 import estimators as E

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "program/proposals/evidence/2026-10-08-q2-stage1-rescoped/analysis"


def _draft_sim():
    spec = importlib.util.spec_from_file_location("sim_s1a_draft", BUNDLE / "sim_s1a.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _random_y(rng, nsim=50, z=2, k=12, s=2, r=2, p=0.3):
    return (rng.random((nsim, z, k, 2, s, r)) < p).astype(float)


def test_point_estimators_match_the_draft_simulation_code():
    sim = _draft_sim()
    y = _random_y(np.random.default_rng(1))
    np.testing.assert_allclose(E.x_by_size(y), sim.x_session_aware(y))
    db, dw = sim.discordance(y.astype(np.int8))
    np.testing.assert_allclose(E.d_between(y), db)
    np.testing.assert_allclose(E.d_within(y), dw)
    np.testing.assert_allclose(E.x_bernoulli_by_size(y), sim.x_bernoulli(y))
    np.testing.assert_allclose(E.task_delta(y), sim.delta_t(y).mean(1))


def test_discordance_by_hand():
    # One size, one task, one harness: S1 = (1, 0), S2 = (1, 1); the other harness all 0.
    y = np.zeros((1, 1, 2, 2, 2))
    y[0, 0, 1] = [[1, 0], [1, 1]]
    # GA cell: cross-session pairs (1,1)(1,1)(0,1)(0,1) -> 2 of 4; within: (1,0) (1,1) -> 1 of 2
    assert E.d_between(y)[0] == pytest.approx((0.5 + 0.0) / 2)
    assert E.d_within(y)[0] == pytest.approx((0.5 + 0.0) / 2)
    # same-block pairs (1,1) and (0,1) -> 1 of 2; cross-block (1,1) and (0,1) -> 1 of 2
    assert E.d_between_same_block(y)[0] == pytest.approx(0.25)
    assert E.d_between_cross_block(y)[0] == pytest.approx(0.25)


def test_missing_slots_leave_their_pairs_and_cells():
    y = np.zeros((1, 2, 2, 2, 2))
    y[0, 0, 1, 0, :] = 1.0  # task 0, GA, S1 both succeed; S2 fails
    y[0, 0, 1, 1, 1] = np.nan  # one S2 rerun missing
    d = E.harness_diff(y)
    assert d[0, 0].tolist() == [1.0, 0.0]
    # GA cell of task 0: cross pairs with the remaining S2 rerun only: 2 of 2 discordant.
    frac_cells = [1.0, 0.0, 0.0, 0.0]
    assert E.d_between(y)[0] == pytest.approx(np.mean(frac_cells))
    # A whole (task, harness, session) cell missing removes that task's product.
    y2 = y.copy()
    y2[0, 1, 0, 1, :] = np.nan
    q = E.x_task_products(y2)
    assert math.isnan(q[0, 1]) and q[0, 0] == pytest.approx(0.0)


def test_x_is_the_mean_squared_effect_and_the_centred_part_removes_the_main_effect():
    # Every task has the same harness difference c in both sessions: X = c^2, centred = 0.
    y = np.zeros((1, 4, 2, 2, 2))
    y[0, :, 1, :, :] = 1.0  # GA always succeeds, OSW never: c = 1
    assert E.x_by_size(y)[0] == pytest.approx(1.0)
    assert E.x_centred_by_size(y)[0] == pytest.approx(0.0)
    # Two tasks with +1 and two with -1 (pure interaction): X = 1, delta = 0, centred = 1.
    y[0, 2:, 1] = 0.0
    y[0, 2:, 0] = 1.0
    assert E.delta(y) == pytest.approx(0.0)
    assert E.x_centred_by_size(y)[0] == pytest.approx(1.0)


def test_x_centred_is_unbiased_for_the_task_variance_in_simulation():
    rng = np.random.default_rng(3)
    k, nsim = 30, 4000
    effect = np.linspace(-0.3, 0.5, k)  # per-task harness effects on the probability scale
    base = 0.4
    p = np.zeros((nsim, 1, k, 2, 2, 2))
    p[..., 0, :, :] = base
    p[..., 1, :, :] = (base + effect)[None, None, :, None, None]
    y = (rng.random(p.shape) < p).astype(float)
    target = np.mean((effect - effect.mean()) ** 2)
    assert E.x_centred_by_size(y).mean() == pytest.approx(target, abs=0.004)
    assert E.x_by_size(y).mean() == pytest.approx(np.mean(effect**2), abs=0.004)


def test_pi_share_truncates_and_defines_zero_over_zero():
    assert E.pi_share(np.array(-0.01), np.array(0.2)) == 0.0
    assert E.pi_share(np.array(0.0), np.array(0.0)) == 0.0
    assert E.pi_share(np.array(0.04), np.array(0.18)) == pytest.approx(0.01 / (0.01 + 0.09))
    assert math.isnan(float(E.pi_share(np.array(np.nan), np.array(0.1))))
    y = np.zeros((2, 3, 2, 2, 2))  # all failures: no variation anywhere
    assert E.pi_small(y) == 0.0
    assert E.pi_small(y, drop_4b=True) == 0.0


def test_success_session_shift_and_heterogeneity():
    y = np.zeros((2, 2, 2, 2, 2))
    y[0, :, :, 1, :] = 1.0  # 4B succeeds everywhere in S2 only
    y[1, :, 1, :, :] = 1.0  # 9B: GA always succeeds
    assert E.success(y).tolist() == [[0.5, 0.5], [0.0, 1.0]]
    assert E.session_shift(y).tolist() == [1.0, 0.0]
    het = E.delta_session_heterogeneity(y)
    assert het["difference"].tolist() == [0.0, 0.0]
    common = E.session_common_share(y)
    assert common["covariance"][0] == pytest.approx(0.5)


def test_paired_t_and_holm():
    t = E.paired_t(np.array([0.1, 0.2, 0.3, np.nan]), level=0.90)
    assert int(t["n"]) == 3 and float(t["estimate"]) == pytest.approx(0.2)
    assert float(t["ci_low"]) < 0.2 < float(t["ci_high"])
    assert E.holm_any([0.02, 0.9]) and not E.holm_any([0.03, 0.04])
    assert not E.holm_any([float("nan"), 0.5])


def test_signflip_p_bounds():
    rng = np.random.default_rng(0)
    p = E.signflip_p(np.full(20, 0.3), 2000, rng, "greater")
    assert p == pytest.approx(1 / 2001, abs=2e-3)
    assert E.signflip_p(np.zeros(10), 200, rng, "greater") == 1.0
    two = E.signflip_p(np.full(20, -0.3), 2000, rng, "two-sided")
    assert two < 0.01
    with pytest.raises(ValueError):
        E.signflip_p(np.zeros(3), 10, rng, "less")


def test_primary_tests_hold_size_under_a_session_excess():
    """The review's failure case: harness x task x session noise (sf = 1.5)."""
    rng = np.random.default_rng(20261008)
    nsim, k = 400, 32
    a = rng.normal(0, 3.5, (nsim, 2, k, 1, 1, 1))
    lin = -2.0 + a + rng.normal(0, 1.5, (nsim, 2, k, 2, 2, 1))
    y = (rng.random((nsim, 2, k, 2, 2, 2)) < 1 / (1 + np.exp(-lin))).astype(float)
    excess = (E.d_between(y) - E.d_within(y)).mean()
    assert excess > 0.02
    size_signflip = (E.x_signflip_p(y, 200, rng) <= 0.05).mean()
    size_session = (E.session_signflip_p(y, 200, rng) <= 0.05).mean()
    assert size_signflip <= 0.07
    assert size_session <= 0.07
    size_label = (E.x_label_permutation_p(y, 100, rng) <= 0.05).mean()
    assert size_label > size_signflip  # the sensitivity is anti-conservative here


def test_bootstrap_is_seeded_and_resamples_tasks_jointly():
    rng = np.random.default_rng(5)
    y = _random_y(rng, nsim=1)[0]
    a = E.bootstrap(y, E.delta, 50, 42)
    b = E.bootstrap(y, E.delta, 50, 42)
    np.testing.assert_array_equal(a, b)
    idx = E.task_resamples(y.shape[1], 50, 42)
    np.testing.assert_allclose(a[3], E.delta(y[:, idx[3]]))
    with pytest.raises(ValueError):
        E.bootstrap(y[None], E.delta, 5, 42)
    lo, hi = E.percentile_interval(np.arange(101.0), 0.95)
    assert (lo, hi) == pytest.approx((2.5, 97.5))
    assert E.one_sided_bounds(np.arange(101.0)) == pytest.approx((5.0, 95.0))


def test_outcomes_must_be_binary():
    with pytest.raises(ValueError):
        E.cell_means(np.full((1, 1, 2, 2, 2), 0.5))
    with pytest.raises(ValueError):
        E.cell_means(np.zeros((1, 1, 3, 2, 2)))
