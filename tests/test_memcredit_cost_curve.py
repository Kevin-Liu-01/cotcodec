"""Tests for AM1b's cost curve (scripts/memcredit_cost_curve.py): the decoding of AM1's committed
development tables against their committed regrets, memoized call counting, and the greedy and
direct-search rules on hand-made toy tables."""

from __future__ import annotations

import copy
import json
import math
import random
import sys
from itertools import combinations
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import memcredit_cost_curve as cc  # noqa: E402

from harness import memcredit as mc  # noqa: E402
from harness import memcredit_study as ms  # noqa: E402


@pytest.fixture(scope="module")
def dev_tables():
    return cc.load_tables(ROOT / cc.DEV_TABLES, cc.DEV_TABLES_SHA256)


def _random_table(k: int, seed: int, levels=(0.0, 1.0)) -> list[float]:
    rng = random.Random(seed)
    return [rng.choice(levels) for _ in range(1 << k)]


# --------------------------------------------------------------------------- decoding


def test_decode_inverts_the_harness_encoding():
    values = _random_table(8, 1)
    hex_ = cc.encode_values(values)
    assert len(hex_) == 64
    assert cc.decode_values(hex_) == values
    # bit m of the integer is mask m: the empty set is the lowest bit, the full set the highest
    only_empty = [1.0] + [0.0] * 255
    only_full = [0.0] * 255 + [1.0]
    assert cc.encode_values(only_empty) == "0" * 63 + "1"
    assert cc.encode_values(only_full) == "8" + "0" * 63
    assert cc.decode_values("8" + "0" * 63)[255] == 1.0


def test_decode_rejects_more_than_256_bits():
    with pytest.raises(cc.CostCurveError):
        cc.decode_values("1" + "0" * 64)


def test_decoding_reproduces_committed_regrets(dev_tables):
    """Exact Shapley and leave-one-out recomputed from the decoded values give the committed
    regret (min, mean, max, sets) at B = 1..4 on every non-constant table; constant tables carry
    no regret."""

    assert len(dev_tables) == 126
    nonconstant = 0
    for t in dev_tables:
        values = cc.decode_values(t["values_hex"])
        if len(set(values)) == 1:
            assert "regret" not in t
            continue
        nonconstant += 1
        for name, credit in (("shapley_exact", mc.shapley(values)), ("loo", mc.loo_credit(values))):
            for b in (1, 2, 3, 4):
                mine = mc.keep_set_regret_range(values, credit, b)
                theirs = t["regret"][name][str(b)]
                assert mine == {key: theirs[key] for key in ("min", "mean", "max", "sets")}
    assert nonconstant == 89


def test_reversed_bit_order_does_not_reproduce_the_regrets(dev_tables):
    t = next(t for t in dev_tables if "regret" in t)
    alt = cc.decode_values_reversed(t["values_hex"])
    regrets = [mc.keep_set_regret_range(alt, mc.loo_credit(alt), b) for b in (1, 2, 3, 4)]
    committed = [t["regret"]["loo"][str(b)] for b in (1, 2, 3, 4)]
    assert regrets != committed


def test_committed_seeded_draws_are_reproduced(dev_tables):
    for t in dev_tables[:6]:
        values = cc.decode_values(t["values_hex"])
        for seed in (42, 43, 44):
            rng = cc.rule_rng(seed, t["question_id"], t["arm"], "perm_shapley_16")
            credit, calls = ms.permutation_shapley(values, 16, rng)
            assert credit == t["credits_seeded"]["perm_shapley_16"][str(seed)]["credit"]
            assert calls == t["credits_seeded"]["perm_shapley_16"][str(seed)]["calls"]
            rng = cc.rule_rng(seed, t["question_id"], t["arm"], "snipw_64")
            credit, calls = ms.snipw(values, 64, rng)
            assert credit == t["credits_seeded"]["snipw_64"][str(seed)]["credit"]
            assert calls == t["credits_seeded"]["snipw_64"][str(seed)]["calls"]


def test_validate_passes_on_the_development_tables(dev_tables):
    h2 = json.loads((ROOT / cc.DEV_H2).read_text(encoding="utf-8"))
    out = cc.validate(copy.deepcopy(dev_tables), h2)
    assert out["passed"]
    assert out["reversed_bit_order"]["reproduce_shapley_and_loo_regrets"] == 0
    assert out["am1_bootstrap"]["rows_identical"] == out["am1_bootstrap"]["rows_checked"] == 64


def test_validate_stops_on_a_tampered_table(dev_tables):
    tables = copy.deepcopy(dev_tables)
    t = next(t for t in tables if "regret" in t and t["regret"]["loo"]["4"]["mean"] > 0)
    values = cc.decode_values(t["values_hex"])
    values[(1 << 8) - 1] = 1.0 - values[(1 << 8) - 1]  # flip u(full)
    t["values_hex"] = cc.encode_values(values)
    with pytest.raises(cc.CostCurveError, match="validation failed"):
        cc.validate(tables, None)


def test_loader_refuses_confirmatory_paths_before_opening():
    path = Path("program/evidence/2026-10-16/am1-confirmatory/analysis/does-not-exist.json.gz")
    with pytest.raises(cc.CostCurveError, match="development tables only"):
        cc.load_tables(path, None)


def test_loader_checks_the_digest(tmp_path):
    path = tmp_path / "tables.json.gz"
    path.write_bytes(b"not the tables")
    with pytest.raises(cc.CostCurveError, match="SHA-256"):
        cc.load_tables(path, cc.DEV_TABLES_SHA256)


# --------------------------------------------------------------------------- call counting


def test_counting_table_counts_distinct_subsets_once():
    table = cc.CountingTable(_random_table(3, 2))
    for _ in range(5):
        table[3]
    table[-1]
    table[7]
    assert table.calls == 2
    assert table.seen == {3, 7}
    full_read = cc.CountingTable(_random_table(3, 2))
    assert list(full_read) == _random_table(3, 2)
    assert full_read.calls == 8  # iteration stops at 8 without counting it


def test_call_counts_of_the_deterministic_rules():
    values = _random_table(8, 3)
    for fn, calls in (
        (mc.loo_credit, 9),
        (ms.leave_one_in, 9),
        (cc.loo_plus_loi, 18),
        (mc.shapley, 256),
        (ms.banzhaf, 256),
    ):
        table = cc.CountingTable(values)
        assert fn(table) == fn(values)
        assert table.calls == calls


def test_call_counts_of_the_sampled_rules_match_the_harness():
    values = _random_table(8, 4)
    for draws in (1, 4, 16):
        table = cc.CountingTable(values)
        credit, calls = ms.permutation_shapley(table, draws, random.Random(draws))
        assert table.calls == calls <= 1 + 7 * draws + 1
        assert credit == ms.permutation_shapley(values, draws, random.Random(draws))[0]
    for exposures in (8, 64):
        table = cc.CountingTable(values)
        _, calls = ms.snipw(table, exposures, random.Random(exposures))
        assert table.calls == calls <= exposures
    for subsets in (8, 32, 256):
        table = cc.CountingTable(values)
        cc.msr_banzhaf(table, subsets, random.Random(subsets))
        assert table.calls == subsets


def test_kernelshap_reads_empty_full_and_its_distinct_coalitions():
    values = _random_table(8, 5)
    rng = random.Random(7)
    table = cc.CountingTable(values)
    cc.kernel_shap(table, 16, rng)
    assert {0, 255} <= table.seen
    assert table.calls <= 2 + 16


def test_msr_over_every_subset_is_exact_banzhaf():
    values = _random_table(5, 6, levels=(0.0, 0.5, 1.0))
    assert cc.msr_banzhaf(values, 1 << 5, random.Random(0)) == pytest.approx(ms.banzhaf(values))


def test_kernel_solve_with_exact_kernel_weights_is_exact_shapley():
    k = 5
    values = _random_table(k, 8, levels=(0.0, 0.25, 1.0))
    weights = {
        m: (k - 1) / (math.comb(k, mc.popcount(m)) * mc.popcount(m) * (k - mc.popcount(m)))
        for m in range(1, (1 << k) - 1)
    }
    phi = cc.kernel_solve(values, weights, ridge=0.0)
    assert phi == pytest.approx(mc.shapley(values), abs=1e-8)
    assert sum(phi) == pytest.approx(values[-1] - values[0], abs=1e-8)


def test_shapley_kernel_size_weights():
    w = cc.shapley_kernel_size_weights(8)
    assert sum(w) == pytest.approx(1.0)
    assert w[0] == w[-1] > w[3]  # sizes 1 and 7 are the most likely


# --------------------------------------------------------------------------- greedy and search


def _toy_and_or_single() -> list[float]:
    """k = 4: u = 1 iff the set holds both memories 0 and 1, or is exactly {2}."""

    return [1.0 if (m & 0b0011) == 0b0011 or m == 0b0100 else 0.0 for m in range(16)]


def test_greedy_forward_is_trapped_by_a_single_memory():
    values = _toy_and_or_single()
    priority = [0.0, -1.0, -2.0, -3.0]  # memory 0 has the best retrieval rank
    table = cc.CountingTable(values)
    mask = cc.greedy_forward(table, 2, priority)
    assert mask == 0b0101  # {2} first, then a three-way tie at 0 goes to memory 0
    assert cc.set_regret(values, mask, 2) == 1.0
    assert table.calls == cc.greedy_calls(4, 2, forward=True) == 4 + 3
    assert cc.greedy_tie_mean_regret(values, 2, forward=True) == 1.0


def test_greedy_backward_finds_the_pair_and_never_reads_the_full_set():
    values = _toy_and_or_single()
    priority = [0.0, -1.0, -2.0, -3.0]
    table = cc.CountingTable(values)
    mask = cc.greedy_backward(table, 2, priority)
    # removing 2 or 3 both leave u = 1; the tie drops the worse-ranked memory 3, then 2
    assert mask == 0b0011
    assert cc.set_regret(values, mask, 2) == 0.0
    assert table.calls == cc.greedy_calls(4, 2, forward=False) == 4 + 3
    assert 0b1111 not in table.seen
    assert cc.greedy_tie_mean_regret(values, 2, forward=False) == 0.0


def test_greedy_ties_follow_the_priority_and_tiemean_averages_them():
    # k = 3, B = 2: every singleton is 0, only {0, 1} is 1
    values = [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0]
    assert cc.set_regret(values, cc.greedy_forward(values, 2, [0.0, -1.0, -2.0]), 2) == 0.0
    assert cc.set_regret(values, cc.greedy_forward(values, 2, [-2.0, -1.0, 0.0]), 2) == 1.0
    # uniform ties: memory 2 first with probability 1/3, and then both pairs with it are 0
    dist = cc.greedy_tie_distribution(values, 2, forward=True)
    assert sum(dist.values()) == 1
    assert cc.greedy_tie_mean_regret(values, 2, forward=True) == pytest.approx(1 / 3)


def test_greedy_call_formula_at_the_headline_budget():
    assert cc.greedy_calls(8, 4, forward=True) == 8 + 7 + 6 + 5
    assert cc.greedy_calls(8, 4, forward=False) == 8 + 7 + 6 + 5
    assert cc.greedy_calls(8, 1, forward=True) == 8
    assert cc.greedy_calls(8, 1, forward=False) == 8 + 7 + 6 + 5 + 4 + 3 + 2


def _direct_brute_force(values: list[float], budget: int, m: int) -> float:
    k = mc.check_table(values)
    sets = ms.all_budget_sets(k, budget)
    draws = list(combinations(sets, m))
    best = mc.best_keep_sets(values, budget)[0]
    return sum(best - max(values[s] for s in draw) for draw in draws) / len(draws)


@pytest.mark.parametrize("levels", [(0.0, 1.0), (0.0, 0.5, 1.0)])
def test_direct_search_curve_is_the_exact_expectation(levels):
    values = _random_table(4, 9, levels=levels)
    for budget in (1, 2, 3):
        curve = cc.direct_search_curve(values, budget)
        assert len(curve) == math.comb(4, budget)
        for m, regret in enumerate(curve, start=1):
            assert regret == pytest.approx(_direct_brute_force(values, budget, m))
        assert curve[0] == pytest.approx(ms.random_regret(values, budget))
        assert curve[-1] == 0.0


def test_direct_search_simulation_agrees_with_the_curve():
    values = _toy_and_or_single()
    curve = cc.direct_search_curve(values, 2)  # one optimal pair among six
    assert curve[1] == pytest.approx(math.comb(5, 2) / math.comb(6, 2))
    rng = random.Random(11)
    sims = [cc.direct_search_simulated(values, 2, 2, rng) for _ in range(4000)]
    assert sum(sims) / len(sims) == pytest.approx(curve[1], abs=0.03)


def test_direct_search_ties_cannot_change_the_regret():
    # three optimal pairs of equal value: whichever best-read set is kept, the regret is 0
    values = [0.0] * 16
    for m in (0b0011, 0b0101, 0b1001):
        values[m] = 1.0
    sets = ms.all_budget_sets(4, 2)
    best_read = [s for s in sets if values[s] == 1.0]
    assert {cc.set_regret(values, s, 2) for s in best_read} == {0.0}


def test_matched_direct_search():
    curve = [0.5, 0.25, 0.0]
    assert cc.matched_direct(curve, 0, 0.7) == 0.7  # no calls: a random keep set
    assert cc.matched_direct(curve, 2, 0.7) == 0.25
    assert cc.matched_direct(curve, 9, 0.7) == 0.0  # more calls than B-subsets: exhaustive


def test_set_regret_uses_the_harness_and_checks_the_size():
    values = _toy_and_or_single()
    assert cc.set_regret(values, 0b0011, 2) == 0.0
    assert cc.set_regret(values, 0b1100, 2) == 1.0
    with pytest.raises(cc.CostCurveError):
        cc.set_regret(values, 0b0111, 2)
