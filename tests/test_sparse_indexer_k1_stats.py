from __future__ import annotations

import math

import numpy as np
import pytest

from harness import sparse_indexer_k1_stats as k1s


def table(means: dict[str, tuple[float, float]], *, pairs: int = 14, clusters: int = 30,
          seeds: int = 3, noise: float = 1.0, seed: int = 0) -> k1s.FamilyTable:
    rng = np.random.default_rng(seed)
    pair = np.repeat(np.arange(pairs), clusters)
    cluster = np.tile(np.arange(clusters), pairs)
    n = pair.size

    def draw(mean: float, shape: tuple[int, ...]) -> np.ndarray:
        return np.clip(mean + rng.normal(0.0, noise, size=shape), 0.0, 100.0)

    return k1s.FamilyTable(
        pair=pair, cluster=cluster,
        ind_mn=draw(means["ind"][0], (seeds, n)), ind_cx=draw(means["ind"][1], (seeds, n)),
        tgt_mn=draw(means["tgt"][0], (n,)), tgt_cx=draw(means["tgt"][1], (n,)),
        rand_mn=np.full(n, means["rand"][0]), rand_cx=np.full(n, means["rand"][1]))


TARGET = {"tgt": (80.0, 70.0), "rand": (10.0, 10.0)}
GOOD = k1s.HeadroomRead(
    60.0,
    k1s.Interval(55.0, (55.0,), 0, 1, 1, 50.0, 60.0, 5, 50.0, 60.0, 2000, True),
    k1s.Interval(20.0, (20.0,), 0, 1, 1, 10.0, 30.0, 10, 10.0, 30.0, 2000, True))


def read(name: str, t: k1s.FamilyTable, ml: tuple[float, float] = (90.0, 92.0),
         integrity: bool = True) -> k1s.TargetRead:
    return k1s.TargetRead(name, k1s.xi_interval(t, replicates=1000),
                          k1s.xi_rel_interval(t, replicates=1000),
                          k1s.AdequacyRead((ml[0],) * t.n_seeds, ml[1]), integrity)


def test_xi_is_a_macro_over_pairs_of_family_means() -> None:
    pair = np.array([0, 0, 1])
    cluster = np.array([0, 1, 0])
    t = k1s.FamilyTable(pair, cluster, ind_mn=np.array([[50.0, 50.0, 60.0]]),
                        ind_cx=np.array([[30.0, 40.0, 60.0]]), tgt_mn=np.array([50.0] * 3),
                        tgt_cx=np.array([50.0] * 3), rand_mn=np.zeros(3), rand_cx=np.zeros(3))
    # pair 0 family excesses 20 and 10 (mean 15); pair 1 excess 0 -> macro 7.5, not 10.
    assert k1s.xi_point(t) == pytest.approx(7.5)


def test_uniformly_weaker_indexer_has_negative_xi_and_zero_xi_rel() -> None:
    t = table({**TARGET, "ind": (45.0, 40.0)}, noise=0.0)
    assert k1s.xi_point(t) == pytest.approx(-5.0)
    assert k1s.xi_rel_point(t) == pytest.approx(0.0, abs=1e-12)


def test_seed_variance_widens_the_decision_interval() -> None:
    calm = table({**TARGET, "ind": (78.0, 50.0)}, noise=1.0, seed=1)
    noisy_seeds = k1s.FamilyTable(
        calm.pair, calm.cluster,
        ind_mn=calm.ind_mn + np.array([[0.0], [6.0], [-6.0]]),
        ind_cx=calm.ind_cx, tgt_mn=calm.tgt_mn, tgt_cx=calm.tgt_cx,
        rand_mn=calm.rand_mn, rand_cx=calm.rand_cx)
    a, b = k1s.xi_interval(calm, replicates=500), k1s.xi_interval(noisy_seeds, replicates=500)
    assert b.s_seed > a.s_seed
    assert b.half_width > a.half_width
    assert b.half_width == pytest.approx(k1s.Z_99 * math.sqrt(b.se_cluster**2 + b.s_seed**2 / 3))


@pytest.mark.parametrize(
    ("means", "noise", "headroom", "expected"),
    [
        ({**TARGET, "ind": (78.0, 50.0)}, 1.0, GOOD, "GO"),
        ({**TARGET, "ind": (77.0, 67.0)}, 1.0, GOOD, "NEGATIVE"),
        ({**TARGET, "ind": (52.0, 34.0)}, 1.0, GOOD, "INCONCLUSIVE"),
        ({**TARGET, "ind": (77.0, 67.0)}, 60.0, GOOD, "INCONCLUSIVE"),
        ({**TARGET, "ind": (77.0, 67.0)}, 1.0,
         k1s.HeadroomRead(5.0, GOOD.h2a, GOOD.h2b), "UNINTERPRETABLE"),
    ],
)
def test_verdict_regions(means, noise, headroom, expected) -> None:
    reads = [read(t, table(means, noise=noise, seed=i)) for i, t in enumerate(("hs", "mp"))]
    assert k1s.k1_verdict(reads, headroom).verdict == expected


def test_negative_needs_h1_of_twenty() -> None:
    reads = [read("hs", table({**TARGET, "ind": (77.0, 67.0)}))]
    middling = k1s.HeadroomRead(15.0, GOOD.h2a, GOOD.h2b)
    verdict = k1s.k1_verdict(reads, middling)
    assert verdict.verdict == "INCONCLUSIVE"
    assert any("blocks NEGATIVE" in reason for reason in verdict.reasons)


def test_bug_tell_holds_and_integrity_voids_before_anything_else() -> None:
    t = table({**TARGET, "ind": (78.0, 50.0)})
    assert k1s.k1_verdict([read("hs", t, ml=(95.0, 92.0))], GOOD).verdict == "HOLD"
    assert k1s.k1_verdict([read("hs", t, integrity=False)], GOOD).verdict == "VOID"


def test_v1_failure_requests_the_extension() -> None:
    t = table({**TARGET, "ind": (78.0, 50.0)})
    verdict = k1s.k1_verdict([read("hs", t, ml=(70.0, 92.0))], GOOD)
    assert verdict.verdict == "V1_EXTENSION_REQUIRED"


def test_xi_rel_is_not_evaluable_without_target_headroom_in_a_pair() -> None:
    t = table({"tgt": (80.0, 10.5), "rand": (10.0, 10.0), "ind": (77.0, 10.2)}, noise=0.0)
    assert math.isnan(k1s.xi_rel_point(t))
    interval = k1s.xi_rel_interval(t, replicates=200)
    assert not interval.evaluable
    assert not read("hs", t).negative


def test_macro_mean_interval_is_percentile_without_seed_term() -> None:
    values = np.r_[np.full(50, 40.0), np.full(50, 60.0)]
    interval = k1s.macro_mean_interval(values, np.zeros(100, dtype=int), np.arange(100),
                                       replicates=500)
    assert interval.point == pytest.approx(50.0)
    assert interval.s_seed == 0.0
    assert interval.lower < 50.0 < interval.upper


def test_attribution_label() -> None:
    assert k1s.attribution_label(15.0, 5.0) == "cross-script"
    assert k1s.attribution_label(15.0, 12.0).startswith("cross-lingual excess")
    assert k1s.attribution_label(float("nan"), 1.0) == "not-evaluable"


def test_family_table_rejects_bad_inputs() -> None:
    with pytest.raises(k1s.StatsContractError):
        k1s.FamilyTable(np.array([0]), np.array([0]), np.array([[101.0]]), np.array([[1.0]]),
                        np.array([1.0]), np.array([1.0]), np.array([0.0]), np.array([0.0]))
    with pytest.raises(k1s.StatsContractError):
        k1s.FamilyTable(np.array([0, 1]), np.array([0]), np.zeros((1, 2)), np.zeros((1, 2)),
                        np.zeros(2), np.zeros(2), np.zeros(2), np.zeros(2))


def test_seed_noise_report_has_df_four_for_two_targets() -> None:
    report = k1s.seed_noise_report({"hs": [50.0, 51.0, 49.0], "mp": [40.0, 42.0, 41.0]})
    assert report["degrees_of_freedom"] == 4
    assert report["sigma_upper_80"] > report["sigma_hat"] > 0
