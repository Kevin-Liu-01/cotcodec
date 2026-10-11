"""The Q2 design-study simulator: registered analysis parity, model, fit pieces and cost."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from harness.q2_design import analyse as AN
from harness.q2_design import cost as C
from harness.q2_design import data as D
from harness.q2_design import fit as F
from harness.q2_design import model as M
from harness.q2_stage1 import analysis as A

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def s1a() -> D.S1aData:
    return D.load(ROOT)


def toy_params(**kw) -> M.Params:
    sp = M.SizeParams(mu=-1.5, sigma_a=4.0, c=-0.3, sigma_b=1.2, sigma_e=0.2, sigma_f=0.3,
                      omega=0.4, kappa=0.2, sigma_g=0.3, sigma_k=0.1)  # fmt: skip
    return M.Params(sizes={"4B": sp, "9B": M.SizeParams(**{**sp.__dict__, "mu": -1.0})},
                    rho_a=0.8, rho_b=0.6, **kw)  # fmt: skip


def test_s1a_arrays(s1a: D.S1aData) -> None:
    assert s1a.y_base.shape == (2, 32, 2, 2, 2)
    assert s1a.y_pool.shape == (2, 113, 2, 2, 2)
    assert np.array_equal(s1a.y_pool[:, :32], s1a.y_base)
    assert len(set(s1a.pool)) == 113
    # RESULTS.md: pooled success on the base.
    assert np.nanmean(s1a.y_base[0, :, 0]) == pytest.approx(0.2891, abs=1e-4)
    assert np.nanmean(s1a.y_base[1, :, 1]) == pytest.approx(0.2891, abs=1e-4)


def test_analyse_matches_registered_analyse_array(s1a: D.S1aData) -> None:
    """On S1a's own base array the wrapper gives analyse_array's DR2 and DR5 readings."""
    reg = A.analyse_array(s1a.y_base, n_boot=2000, n_rand=2000, label_permutation=False)
    got = AN.analyse(s1a.y_base[None], M.SIZES, n_boot=2000, n_flip=2000,
                     rng=np.random.default_rng(42))  # fmt: skip
    assert got["p_x"][0] == pytest.approx(reg["tests"]["x_signflip_p"], abs=0)
    assert got["p_delta"][0] == pytest.approx(reg["tests"]["delta_paired_t"]["p"], abs=1e-6)
    lo, hi = reg["tests"]["delta_paired_t"]["ci90_t"]
    assert got["ci90_low"][0] == pytest.approx(lo, abs=1e-6)
    assert got["ci90_high"][0] == pytest.approx(hi, abs=1e-6)
    assert [got["pi_small_lb"][0], got["pi_small_ub"][0]] == reg["estimates"]["pi_small"][
        "one_sided_95"
    ]
    assert got["dr2"][0] == reg["DR2"]["class"]
    assert got["dr5"][0] == reg["DR5"]["outcome"]


def test_analyse_reproduces_the_committed_report(s1a: D.S1aData) -> None:
    """At the registered 10,000 resamples and flips: the committed S1a readings."""
    rep = json.loads((ROOT / D.REPORT).read_text())["primary"]
    got = AN.analyse(s1a.y_base[None], M.SIZES, rng=np.random.default_rng(42))
    assert got["p_x"][0] == pytest.approx(rep["tests"]["x_signflip_p"], abs=0)
    assert [got["pi_small_lb"][0], got["pi_small_ub"][0]] == rep["estimates"]["pi_small"][
        "one_sided_95"
    ]
    assert got["dr2"][0] == rep["DR2"]["class"] == "Inconclusive"
    assert got["dr5"][0] == rep["DR5"]["outcome"] == "INCONCLUSIVE"


def test_analyse_other_designs_run() -> None:
    rng = np.random.default_rng(42)
    for design in (M.Design(K=20, S=4, R=1, tasks="srs"),
                   M.Design(K=20, S=3, R=2, sizes=("9B",), tasks="srs")):  # fmt: skip
        y, _ = M.simulate(toy_params(), design, 3, rng)
        res = AN.analyse(y, design.sizes, n_boot=200, n_flip=200)
        assert set(res["dr2"]) <= {"Present", "Near-equivalent", "Inconclusive"}
        assert set(res["dr5"]) <= {"GO", "NO-GO", "INCONCLUSIVE"}
        if design.R == 1:
            assert np.all(np.isnan(res["excess_ub"]))
        if design.sizes == ("9B",):
            assert res["drop_4b"].all()


def test_simulate_shapes_seeds_and_null() -> None:
    d = M.Design(K=16, S=3, R=2, tasks="srs")
    y1, t1 = M.simulate(toy_params(), d, 5, np.random.default_rng(43))
    y2, _ = M.simulate(toy_params(), d, 5, np.random.default_rng(43))
    assert y1.shape == (5, 2, 16, 2, 3, 2)
    assert np.array_equal(y1, y2)
    assert set(np.unique(y1)) <= {0.0, 1.0}
    # With no harness effect of any kind (sigma_f is harness-specific session noise, so it
    # is zeroed for the exact check) the realized harness difference is exactly 0.
    null = M.Scenario(name="null", c={"4B": 0.0, "9B": 0.0}, lam=0.0, kappa_scale=0.0,
                      sigma_f={"4B": 0.0, "9B": 0.0})  # fmt: skip
    _, t0 = M.simulate(toy_params(), d, 5, np.random.default_rng(44), scenario=null)
    assert np.allclose(t0["delta_realized"], 0.0)
    with pytest.raises(ValueError):
        M.simulate(toy_params(), d, 2, np.random.default_rng(42), sessions="realized")


def test_population_null_and_monotone() -> None:
    p = toy_params()
    null = M.population(p, M.Scenario.harness_null(), n_tasks=20000)
    assert null["pi_small"] == pytest.approx(0.0, abs=1e-12)
    lo = M.population(p, M.Scenario(lam=0.5), n_tasks=20000)["pi_small"]
    hi = M.population(p, M.Scenario(lam=2.0), n_tasks=20000)["pi_small"]
    assert 0 < lo < hi


def test_prob_scale_components_add_up() -> None:
    out = M.prob_scale_components(toy_params(), n_tasks=1500, n_sessions=150)
    for z in M.SIZES:
        tot = sum(out[z]["components"].values())
        assert tot == pytest.approx(out[z]["var_y"], rel=0.03)


def test_apportion_matches_the_registered_draw(s1a: D.S1aData) -> None:
    counts: dict[str, int] = {}
    for t in s1a.pool:
        counts[s1a.domains[t]] = counts.get(s1a.domains[t], 0) + 1
    alloc = M.apportion(counts, 32)
    assert alloc == {"gimp": 2, "libreoffice_calc": 8, "libreoffice_impress": 7,
                     "libreoffice_writer": 3, "multi_apps": 7, "thunderbird": 2, "vlc": 2,
                     "vs_code": 1}  # fmt: skip
    got = {d: sum(1 for t in s1a.base if s1a.domains[t] == d) for d in alloc}
    assert got == alloc


def test_pool_selection(s1a: D.S1aData) -> None:
    rng = np.random.default_rng(42)
    for tasks in ("srs", "stratified", "extend"):
        idx = M.select_pool_tasks(M.Design(K=40, tasks=tasks), s1a.pool, 32, s1a.domains, rng, 4)
        assert idx.shape == (4, 40)
        assert all(len(set(r)) == 40 for r in idx)
    ext = M.select_pool_tasks(M.Design(K=40, tasks="extend"), s1a.pool, 32, s1a.domains, rng, 1)
    assert list(ext[0]) == list(range(40))


def test_likelihood_pieces() -> None:
    g = F.Grid.default(0.5)
    p = F.bin_probs(g.u, 1.0, 3.0)
    assert p.sum() == pytest.approx(1.0) and (p >= 0).all()
    A_ = F.bvn_matrix(g.u, (0.0, 1.0), (3.0, 2.0), 0.7)
    assert A_.sum() == pytest.approx(1.0)
    tab = F.g_tables(0.0, 2)
    eta = np.array([-1.0, 0.0, 2.0])
    pr = 1 / (1 + np.exp(-eta))
    assert np.allclose(F.interp(eta, tab[(1, 2)]), pr * (1 - pr), atol=1e-5)
    k = F.e_kernel(0.8, 0.25)
    assert k.sum() == pytest.approx(1.0) and k.argmax() == k.size // 2


def test_fit_likelihood_prefers_truth_on_simulated_data() -> None:
    """The marginal log-likelihood is higher at the generating parameters than at a
    clearly wrong task SD or harness main effect."""
    truth = toy_params()
    y, _ = M.simulate(truth, M.Design(K=60, tasks="srs"), 1,
                      np.random.default_rng(42), sessions="realized")  # fmt: skip
    like = F.Likelihood(y[0], F.Grid.default(0.4))
    sizes = [{k: getattr(truth.sizes[z], k) for k in
              ("mu", "sigma_a", "c", "sigma_b", "omega", "kappa", "sigma_e", "sigma_f")}
             for z in M.SIZES]  # fmt: skip
    x = F.pack(sizes, truth.rho_a, truth.rho_b)
    ll = like.loglik(x)
    for coord, val in ((1, math.log(1.0)), (2, 3.0)):
        bad = x.copy()
        bad[coord] = val
        assert like.loglik(bad) < ll - 2


def test_session_variances_moments() -> None:
    est = [{"omega": 1.0, "kappa": 0.4}, {"omega": 0.0, "kappa": 0.0}]
    se = [{"omega": 0.0, "kappa": 0.0}, {"omega": 0.0, "kappa": 0.0}]
    sv = F.session_variances(est, se)
    assert sv["sigma_k"] == pytest.approx(math.sqrt(0.08 / 4))
    assert sv["sigma_g"] == pytest.approx(math.sqrt((0.5 - 0.02) / 2))
    assert sv["sigma_g_upper95"] > sv["sigma_g"]


def test_cost_reprices_s1a(s1a: D.S1aData) -> None:
    model, timing = C.build(ROOT, s1a)
    realized = sum(j["elapsed_s"] for j in timing.values()) / 3600
    full = model.design(M.Design(K=113, S=2, R=2, tasks="extend"))
    assert full["episodes"] == 1808
    assert full["physical_gpu_h"] == pytest.approx(realized, rel=0.02)
    assert full["cpus_per_pair"] == 122 and full["pairs_at_once"] == 1
    assert model.design(M.Design(K=32, S=2, R=2))["within_478_min"]


def test_lam_for_pi_hits_the_target() -> None:
    p = toy_params()
    lam = M.lam_for_pi(p, 0.13, n_tasks=20000)
    got = M.population(p, M.Scenario(lam=lam), n_tasks=20000)["pi_small"]
    assert got == pytest.approx(0.13, abs=1e-3)


def test_profile_bounds_interpolate() -> None:
    from harness.q2_design.study import profile_bounds

    rows = [{"value": v, "lr": (v - 1.0) ** 2 * 4} for v in (0.0, 0.5, 1.0, 1.5, 2.0)]
    b = profile_bounds(rows, 1.0)
    lo, hi = b["two_sided_95"]
    assert 0.0 < lo < 0.5 < 1.5 < hi < 2.0
    edge = [{"value": v, "lr": 3 * v} for v in (0.0, 0.5, 1.0, 2.0)]
    assert profile_bounds(edge, 0.0)["one_sided_95"] == [None, pytest.approx(2.705543 / 3)]


def test_differences_ignore_metadata_and_new_fields() -> None:
    from harness.q2_design.study import differences

    a = {"x": [1, 2, {"y": 3}], "provenance": {"git": "a"}, "seconds": 1.0}
    b = {"x": [1, 2, {"y": 3, "new": 0}], "provenance": {"git": "b"}, "seconds": 9.0, "z": 1}
    assert differences(a, b) == []
    assert differences(a, {**b, "x": [1, 2, {"y": 4}]}) == ["/x/2/y"]


@pytest.mark.parametrize(
    ("K", "S", "R", "sizes"),
    [
        (32, 2, 2, ("4B", "9B")),
        (40, 3, 1, ("4B", "9B")),
        (24, 2, 2, ("9B",)),
        (30, 4, 2, ("4B", "9B")),
    ],  # fmt: skip
)
def test_fast_analysis_equals_registered_wrapper(K: int, S: int, R: int, sizes) -> None:
    """fast.analyse reproduces analyse.analyse field by field (same flips, same resamples)."""
    from harness.q2_design import fast as FA

    des = M.Design(K=K, S=S, R=R, sizes=sizes, tasks="srs")
    y, _ = M.simulate(toy_params(), des, 8, np.random.default_rng([42, K]))
    a = AN.analyse(y, sizes, n_boot=1000, n_flip=1000, rng=np.random.default_rng([42, 12]))
    b = FA.analyse(y, sizes, n_boot=1000, n_flip=1000, rng=np.random.default_rng([42, 12]))
    for k, v in a.items():
        if k in ("dr2", "dr5"):
            assert list(v) == list(b[k])
        else:
            np.testing.assert_allclose(np.asarray(v, float), b[k], rtol=0, atol=1e-12)


def test_fast_analysis_reproduces_s1a_readings(s1a: D.S1aData) -> None:
    """S1a's committed primary and secondary readings (10,000 resamples and flips)."""
    from harness.q2_design import fast as FA

    base = FA.analyse(s1a.y_base[None], M.SIZES, rng=np.random.default_rng(42))
    assert base["p_x"][0] == pytest.approx(0.4588, abs=1e-4)
    assert [base["pi_small_lb"][0], base["pi_small_ub"][0]] == [0.0, 0.259909]
    assert (base["dr2"][0], base["dr5"][0]) == ("Inconclusive", "INCONCLUSIVE")
    pool = FA.analyse(s1a.y_pool[None], M.SIZES, rng=np.random.default_rng(42), diagnostics=True)
    assert pool["p_x"][0] == pytest.approx(0.1571, abs=1e-4)
    assert [pool["pi_small_lb"][0], pool["pi_small_ub"][0]] == [0.019608, 0.162165]
    assert (pool["qpos_4B"][0], pool["qneg_4B"][0]) == (6, 9)
    assert pool["X_4B"][0] < 0 < pool["X_9B"][0]
