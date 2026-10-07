from __future__ import annotations

import math

import numpy as np
import pytest
from scipy import stats

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
    se_total = math.sqrt(b.se_cluster**2 + b.s_seed**2 / 3)
    df = k1s.welch_satterthwaite_df(b.se_cluster, b.s_seed, 3, 30)
    assert b.df == pytest.approx(df)
    assert b.half_width == pytest.approx(stats.t.ppf(0.995, df) * se_total)


def test_welch_satterthwaite_df_tracks_the_dominant_term() -> None:
    # Seed-dominated: close to the seed term's 2 degrees of freedom.
    assert k1s.welch_satterthwaite_df(0.01, 2.0, 3, 122) == pytest.approx(2.0, rel=1e-3)
    # Cluster-dominated: close to n_clusters - 1.
    assert k1s.welch_satterthwaite_df(2.0, 0.01, 3, 122) == pytest.approx(121.0, rel=1e-3)
    assert k1s.welch_satterthwaite_df(0.0, 0.0, 3, 122) == math.inf
    assert k1s.decision_quantile(math.inf) == pytest.approx(k1s.Z_99)
    assert k1s.decision_quantile(2.0) == pytest.approx(9.925, abs=1e-3)


def _seed_dominated(rng: np.random.Generator, seed_sd: float) -> k1s.FamilyTable:
    """True xi = 0; the indexer's CX recall carries a per-seed offset (init variance)."""

    pairs, clusters = 14, 20
    pair = np.repeat(np.arange(pairs), clusters)
    cluster = np.tile(np.arange(clusters), pairs)
    n = pair.size
    tgt_mn = 60.0 + rng.normal(0.0, 2.0, n)
    tgt_cx = 50.0 + rng.normal(0.0, 2.0, n)
    seed_effect = rng.normal(0.0, seed_sd, size=(3, 1))
    ind_mn = tgt_mn + rng.normal(0.0, 0.5, (3, n))
    ind_cx = tgt_cx - seed_effect + rng.normal(0.0, 0.5, (3, n))
    return k1s.FamilyTable(pair, cluster, ind_mn, ind_cx, tgt_mn, tgt_cx,
                           np.full(n, 12.5), np.full(n, 12.5))


def test_decision_interval_keeps_99_percent_coverage_when_seeds_dominate() -> None:
    # Review finding: z = 2.576 with a df-2 seed SD under-covers (about 12 percent
    # misses). The Welch-Satterthwaite t interval must hold close to 1 percent.
    rng = np.random.default_rng(11)
    reps, t_miss, z_miss = 300, 0, 0
    for _ in range(reps):
        interval = k1s.xi_interval(_seed_dominated(rng, 3.0), replicates=200)
        t_miss += not (interval.lower <= 0.0 <= interval.upper)
        z_miss += abs(interval.point) > k1s.Z_99 * interval.se_total
    assert t_miss / reps <= 0.03
    assert z_miss / reps >= 0.06  # the normal quantile this replaces would not


def test_xi_rel_evaluability_is_decided_on_the_point_means_only() -> None:
    # Review finding: one pair whose point headroom (about 1.4 points) is above
    # the registered 1-point floor must not make xi_rel non-evaluable just
    # because some bootstrap replicates dip below the floor.
    rng = np.random.default_rng(7)
    pairs, clusters = 14, 60
    pair = np.repeat(np.arange(pairs), clusters)
    cluster = np.tile(np.arange(clusters), pairs)
    n = pair.size
    rand = np.full(n, 12.5)
    tgt_mn = np.clip(60.0 + rng.normal(0.0, 4.0, n), 0, 100)
    cx_mean = np.where(pair == pairs - 1, 12.5 + 1.4, 40.0)
    tgt_cx = np.clip(cx_mean + rng.normal(0.0, 4.0, n), 0, 100)
    ind_mn = np.clip(rand + 0.95 * (tgt_mn - rand) + rng.normal(0.0, 1.0, (3, n)), 0, 100)
    ind_cx = np.clip(rand + 0.3 * (tgt_cx - rand) + rng.normal(0.0, 1.0, (3, n)), 0, 100)
    t = k1s.FamilyTable(pair, cluster, ind_mn, ind_cx, tgt_mn, tgt_cx, rand, rand.copy())
    low_pair = t.tgt_cx[t.pair == pairs - 1].mean() - 12.5
    assert 1.0 < low_pair < 2.0
    rel = k1s.xi_rel_interval(t, replicates=1000)
    assert rel.evaluable and math.isfinite(rel.lower)
    assert rel.clipped_replicates > 0  # the floor was active in some replicates
    read_ = k1s.TargetRead("mp", k1s.xi_interval(t, replicates=1000), rel,
                           k1s.AdequacyRead((90.0,) * 3, 91.0), True)
    assert read_.xi.point >= 10.0 and read_.go


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
    reads = [read("hs", t, ml=(70.0, 92.0))]
    verdict = k1s.k1_verdict(reads, GOOD)
    assert verdict.verdict == "V1_EXTENSION_REQUIRED"
    assert k1s.extension_targets(verdict, reads) == ["hs"]
    after = k1s.k1_verdict(reads, GOOD, after_extension=True)
    assert after.verdict == "INCONCLUSIVE"
    assert "after the registered extension" in after.reasons[0]


def test_extension_rereads_only_v1_failing_targets_and_never_after_go() -> None:
    hs_fail = read("hs", table({**TARGET, "ind": (77.0, 67.0)}, seed=0), ml=(70.0, 92.0))
    go_mp = read("mp", table({**TARGET, "ind": (78.0, 50.0)}, seed=1))
    neg_mp = read("mp", table({**TARGET, "ind": (77.0, 67.0)}, seed=1))
    go = k1s.k1_verdict([hs_fail, go_mp], GOOD)
    assert go.verdict == "GO" and k1s.extension_targets(go, [hs_fail, go_mp]) == []
    waiting = k1s.k1_verdict([hs_fail, neg_mp], GOOD)
    assert waiting.verdict == "INCONCLUSIVE"
    assert k1s.extension_targets(waiting, [hs_fail, neg_mp]) == ["hs"]
    # mp keeps its main read; only hs is replaced by its extension read.
    hs_ext = read("hs", table({**TARGET, "ind": (77.0, 67.0)}, seed=0))
    combined = k1s.combine_after_extension([hs_fail, neg_mp], [hs_ext])
    assert combined[1] is neg_mp and combined[0] is hs_ext
    assert k1s.k1_verdict(combined, GOOD, after_extension=True).verdict == "NEGATIVE"
    with pytest.raises(k1s.StatsContractError):
        k1s.combine_after_extension([hs_fail, neg_mp], [hs_ext, neg_mp])
    for verdict in ("VOID", "HOLD", "UNINTERPRETABLE", "NEGATIVE", "GO"):
        assert k1s.extension_targets(k1s.Verdict(verdict, ()), [hs_fail, neg_mp]) == []


def test_hold_is_terminal_and_never_followed_by_the_extension() -> None:
    # Pre-freeze audit, blocking defect 1: a HOLD had no registered resolution.
    t = table({**TARGET, "ind": (78.0, 50.0)})
    reads = [read("hs", t, ml=(95.0, 92.0)), read("mp", t, ml=(70.0, 92.0))]
    hold = k1s.k1_verdict(reads, GOOD)
    assert hold.verdict == "HOLD" and k1s.extension_targets(hold, reads) == []
    assert k1s.final_verdict(hold, reads, None).verdict == "HOLD"
    with pytest.raises(k1s.StatsContractError, match="does not call for"):
        k1s.final_verdict(hold, reads, k1s.Verdict("GO", ()))


def test_called_for_extension_is_mandatory_and_a_void_one_is_inconclusive() -> None:
    # Pre-freeze audit, blocking defect 2: the final verdict was undefined when the
    # extension was not run or ended void.
    hs_fail = read("hs", table({**TARGET, "ind": (77.0, 67.0)}, seed=0), ml=(70.0, 92.0))
    neg_mp = read("mp", table({**TARGET, "ind": (77.0, 67.0)}, seed=1))
    main = k1s.k1_verdict([hs_fail, neg_mp], GOOD)
    assert main.verdict == "INCONCLUSIVE"
    for extension in (None, k1s.Verdict("VOID", ("V3 integrity failed",))):
        final = k1s.final_verdict(main, [hs_fail, neg_mp], extension)
        assert final.verdict == "INCONCLUSIVE"
        assert "not run or ended void" in final.reasons[0]
    hs_ext = read("hs", table({**TARGET, "ind": (77.0, 67.0)}, seed=0))
    combined = k1s.k1_verdict(k1s.combine_after_extension([hs_fail, neg_mp], [hs_ext]), GOOD,
                              after_extension=True)
    assert k1s.final_verdict(main, [hs_fail, neg_mp], combined) is combined
    held = k1s.Verdict("HOLD", ("V2 bug tell",))
    assert k1s.final_verdict(main, [hs_fail, neg_mp], held) is held  # HOLD stays terminal
    nothing_failed = k1s.k1_verdict([neg_mp], GOOD)
    assert k1s.final_verdict(nothing_failed, [neg_mp], None) is nothing_failed
    with pytest.raises(k1s.StatsContractError, match="V1_EXTENSION_REQUIRED"):
        k1s.final_verdict(main, [hs_fail, neg_mp],
                          k1s.Verdict("V1_EXTENSION_REQUIRED", ()))


def test_reads_round_trip_through_json() -> None:
    import json

    t = table({**TARGET, "ind": (78.0, 50.0)})
    original = read("hs", t, ml=(70.0, 92.0))
    again = k1s.TargetRead.from_dict(json.loads(json.dumps(original.as_dict())))
    assert again == original
    headroom = k1s.HeadroomRead.from_dict(json.loads(json.dumps(GOOD.as_dict())))
    assert headroom == GOOD
    nan_read = read("hs", table({"tgt": (80.0, 10.5), "rand": (10.0, 10.0),
                                 "ind": (77.0, 10.2)}, noise=0.0))
    restored = k1s.TargetRead.from_dict(json.loads(json.dumps(nan_read.as_dict())))
    assert not restored.xi_rel.evaluable and math.isnan(restored.xi_rel.point)


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
