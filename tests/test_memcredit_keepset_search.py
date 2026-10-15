"""Tests for am1-keepset-search-v1 (scripts/memcredit_keepset_search.py): the exact order-statistic
expectation of direct search and the exact McNemar test on toy tables, H-A's per-table rules,
comparisons, bounds and verdict, H-C's stop rule, the held-out gate (refused before the freeze),
the code pins, and the development tables. No test opens a held-out file."""

from __future__ import annotations

import copy
import gzip
import importlib.util
import json
import math
import random
import sys
from fractions import Fraction
from itertools import combinations
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import memcredit_cost_curve as cc  # noqa: E402
import memcredit_keepset_search as ks  # noqa: E402
import memcredit_label_free as lf  # noqa: E402

from harness import memcredit_study as ms  # noqa: E402


@pytest.fixture(scope="module")
def dev_tables():
    return ks.load_tables("development")


def _table_with_optimal_sets(optimal: list[int]) -> list[float]:
    values = [0.0] * 256
    for m in optimal:
        values[m] = 1.0
    values[255] = 1.0  # sizes other than 4 do not enter B = 4
    return values


# --------------------------------------------------------------------------- direct search


@pytest.mark.parametrize("j", [1, 3, 15, 69])
def test_direct_search_is_the_exact_order_statistic_expectation(j):
    """With j optimal 4-subsets of 70 and 0/1 utilities, m draws without replacement all miss
    the optimum with probability C(70 - j, m) / C(70, m)."""

    rng = random.Random(j)
    optimal = rng.sample(list(ks.FOUR_SETS), j)
    values = _table_with_optimal_sets(optimal)
    curve = cc.direct_search_curve(values, 4)
    for m in range(1, 71):
        expected = Fraction(math.comb(70 - j, m), math.comb(70, m))
        assert curve[m - 1] == float(expected)


def test_direct_search_matches_brute_force_on_a_small_table():
    """k = 4, B = 2 (six sets) with graded utilities: the curve equals the average, over every
    m-subset of the six sets, of the best-read set's regret."""

    values = [0.0, 0.0, 0.0, 1.0, 0.0, 0.5, 0.0, 1.0, 0.0, 0.25, 0.5, 1.0, 0.75, 1.0, 1.0, 1.0]
    sets = ms.all_budget_sets(4, 2)
    best = max(values[s] for s in sets)
    curve = cc.direct_search_curve(values, 2)
    for m in range(1, len(sets) + 1):
        draws = list(combinations(sets, m))
        brute = sum(Fraction(best) - Fraction(max(values[s] for s in d)) for d in draws)
        assert curve[m - 1] == pytest.approx(float(brute / len(draws)), abs=1e-15)


def test_direct_search_simulation_agrees_with_the_exact_curve():
    values = _table_with_optimal_sets(random.Random(3).sample(list(ks.FOUR_SETS), 4))
    curve = cc.direct_search_curve(values, 4)
    rng = random.Random(11)
    sims = [cc.direct_search_simulated(values, 4, 9, rng) for _ in range(4000)]
    assert sum(sims) / len(sims) == pytest.approx(curve[8], abs=0.03)


# --------------------------------------------------------------------------- McNemar


@pytest.mark.parametrize(
    ("b", "c", "p"),
    [
        (4, 0, 0.125),  # AM1d: BM25 top 4 vs all 8, retrieved
        (5, 0, 0.0625),  # AM1d: nonabstain@70 vs all 8, retrieved
        (6, 0, 0.03125),
        (1, 0, 1.0),
        (0, 0, 1.0),
        (3, 3, 1.0),
        (10, 2, 158 / 4096),
        (2, 10, 158 / 4096),
    ],
)
def test_mcnemar_exact_known_values(b, c, p):
    assert ks.mcnemar_exact(b, c) == p


def test_mcnemar_exact_equals_the_two_tailed_enumeration():
    for n in range(0, 15):
        for b in range(n + 1):
            c = n - b
            pmf = [Fraction(math.comb(n, x), 2**n) for x in range(n + 1)]
            extreme = abs(Fraction(b) - Fraction(n, 2))
            brute = sum(
                p for x, p in enumerate(pmf) if abs(Fraction(x) - Fraction(n, 2)) >= extreme
            )
            assert ks.mcnemar_exact(b, c) == float(min(Fraction(1), brute) if n else 1)


def test_mcnemar_threshold_and_power():
    for nd in range(0, 40):
        k = ks.mcnemar_threshold(nd)
        assert k < nd / 2 or k == -1
        for b in range(nd + 1):
            assert (min(b, nd - b) <= k) == (ks.mcnemar_exact(b, nd - b) <= 0.05)
    # size: under no difference the exact test rejects at most alpha of the time
    assert ks.mcnemar_power(347, 0.06, 0.5) <= 0.05
    assert ks.mcnemar_power(347, 0.0, 1.0) == 0.0
    low, high = ks.mcnemar_power(347, 0.06, 0.7), ks.mcnemar_power(347, 0.06, 0.9)
    assert 0.05 < low < high <= 1.0


def _paired(b, c, n=40):
    rule, base = {}, {}
    for i in range(n):
        q = f"q{i:02d}"
        if i < b:
            rule[q], base[q] = 1.0, 0.0
        elif i < b + c:
            rule[q], base[q] = 0.0, 1.0
        else:
            rule[q] = base[q] = float(i % 2)
    return rule, base


@pytest.mark.parametrize(
    ("b", "c", "reading"),
    [(6, 0, "HELPS"), (0, 6, "HURTS"), (5, 0, "NONE"), (9, 2, "NONE"), (12, 2, "HELPS")],
)
def test_paired_reading(b, c, reading):
    rule, base = _paired(b, c)
    out = ks.paired_reading(rule, base, ("HELPS", "HURTS", "NONE"), 500, 42)
    assert out["reading"] == reading
    assert (out["rule_right_base_wrong"], out["rule_wrong_base_right"]) == (b, c)
    assert out["difference"] == (b - c) / 40
    lo, hi = out["ci95_exact_conditional"]
    assert lo <= out["difference"] <= hi


def test_exact_conditional_interval_inverts_the_test():
    for b in range(0, 26):
        for c in range(0, 26):
            if b + c == 0:
                continue
            rule, base = _paired(b, c, n=60)
            out = ks.paired_reading(rule, base, ("H", "L", "N"), 200, 42)
            lo, hi = out["ci95_exact_conditional"]
            assert (lo > 0 or hi < 0) == (out["p_exact_mcnemar"] <= 0.05), (b, c)


def test_paired_reading_needs_binary_outcomes_and_the_same_questions():
    with pytest.raises(ks.KeepsetError):
        ks.paired_reading({"a": 0.5}, {"a": 1.0}, ("H", "L", "N"), 100, 42)
    with pytest.raises(ks.KeepsetError):
        ks.paired_reading({"a": 1.0}, {"b": 1.0}, ("H", "L", "N"), 100, 42)


# --------------------------------------------------------------------------- H-A per table


def test_ha_table_on_a_pair_table():
    """u(S) = 1 iff memories 0 and 1 are both kept. Leave-one-out and greedy backward find a
    keep set with both (regret 0); direct search misses all 15 such sets with probability
    C(55, m) / C(70, m), so here every difference (direct minus rule) is positive."""

    values = [float(m & 0b11 == 0b11) for m in range(256)]
    ranks = [3, 6, 1, 2, 4, 5, 7, 8]
    ha = ks.ha_table(values, "toy", "retrieved", ranks, [42, 43, 44])
    rules = ha["rules"]
    assert rules["loo"]["calls"] == [9] and rules["loo"]["regret"] == [0.0]
    assert rules["greedy_backward"]["calls"] == [26] and rules["greedy_backward"]["regret"] == [0.0]
    # greedy keeps 0 and 1 and, among the rest, the two best BM25 ranks (memories 2 and 3)
    assert rules["greedy_backward"]["mask"] == 0b1111
    assert rules["msr_banzhaf_64"]["calls"] == [64, 64, 64]
    assert all(c <= 64 for c in rules["snipw_64"]["calls"])
    assert all(c <= 2 + 7 * 16 for c in rules["perm_shapley_16"]["calls"])
    for m in range(1, 71):
        assert ha["direct"][m - 1] == float(Fraction(math.comb(55, m), math.comb(70, m)))
    assert ha["diffs"]["A1"] == [ha["direct"][8] - 0.0]
    assert ha["diffs"]["A7"] == [ha["direct"][25] - 0.0]
    assert ha["diffs"]["A3"] == [ha["direct"][25] - r for r in rules["snipw_64"]["regret"]]
    assert ha["diffs"]["A4"] == [ha["direct"][63] - r for r in rules["msr_banzhaf_64"]["regret"]]
    for d, r, c in zip(ha["diffs"]["A2"], rules["snipw_64"]["regret"], rules["snipw_64"]["calls"],
                       strict=True):  # fmt: skip
        assert d == ha["direct"][c - 1] - r
    assert len(ha["diffs"]["A6"]) == 3 and all(d > 0 for d in ha["diffs"]["A1"])


def test_ha_table_where_credit_fails():
    """u(S) = 1 iff exactly one of memories 0 and 1 is kept (XOR): leave-one-out gives both 0
    credit (the full pool is wrong, removing either makes it right: -1 each), so its top 4 drops
    both and loses; direct search does not depend on credit."""

    values = [float(((m & 1) ^ (m >> 1 & 1)) == 1) for m in range(256)]
    ha = ks.ha_table(values, "xor", "retrieved", list(range(8)), [42])
    assert ha["rules"]["loo"]["regret"] == [1.0]
    assert ha["diffs"]["A1"][0] < 0


def test_sampled_rules_reuse_am1b_definitions_and_seeds(dev_tables):
    """Seeds 42-61 reproduce AM1b's per-seed regrets on development tables (same rule names, so
    the same random.Random(f'{seed}:{qid}:{arm}:{rule}') draws)."""

    am1b = json.loads(gzip.decompress((ROOT / ks.AM1B_DIR / "per-table.json.gz").read_bytes()))
    by_key = {(t["question_id"], t["arm"]): t for t in dev_tables}
    checked = 0
    for p in am1b[:: max(1, len(am1b) // 6)][:6]:
        t = by_key[(p["question_id"], p["arm"])]
        values = cc.decode_values(t["values_hex"])
        ha = ks.ha_table(values, p["question_id"], p["arm"], ks.bm25_ranks(t), list(range(42, 62)))
        for name in ks.SAMPLED_RULES:
            assert ha["rules"][name]["regret"] == p["rules"][name]["4"]["regret_by_seed"]
        for name in ("loo", "greedy_backward"):
            assert ha["rules"][name]["regret"] == [p["rules"][name]["4"]["regret"]]
        assert ha["direct"] == p["direct_search"]["4"]
        checked += 1
    assert checked == 6


def test_comparisons_are_the_registered_family():
    assert ks.COMPARISON_IDS == ("A1", "A2", "A3", "A4", "A5", "A6", "A7")
    spec = {c.id: (c.rule, c.calls) for c in ks.COMPARISONS}
    assert spec == {
        "A1": ("loo", None), "A2": ("snipw_64", None), "A3": ("snipw_64", 26),
        "A4": ("msr_banzhaf_64", None), "A5": ("msr_banzhaf_64", 26),
        "A6": ("perm_shapley_16", 26), "A7": ("greedy_backward", None),
    }  # fmt: skip
    assert ks.N_SEEDS >= 200 and ks.BOOTSTRAP_RESAMPLES >= 10_000
    assert ks.ALPHA_A == 0.05 and ks.MC_SE_MARGIN == 3.0 and ks.ALPHA_PAIRED == 0.05


# --------------------------------------------------------------------------- bounds and verdict


def test_bounds_are_the_one_sided_bonferroni_order_statistics():
    import numpy as np

    rng = random.Random(5)
    clusters = {f"q{i}": [rng.uniform(-0.3, 0.1)] for i in range(50)}
    alpha_one = 0.05 / 7
    out = ks._bounds(clusters, 2000, 42, alpha_one)
    keys = sorted(clusters)
    x = np.array([clusters[k][0] for k in keys])
    draws = np.random.default_rng(42).integers(0, len(keys), size=(2000, len(keys)))
    means = np.sort(x[draws].mean(axis=1))
    assert out["lower"] == float(means[int(math.floor(alpha_one * 1999))])
    assert out["upper"] == float(means[int(math.ceil((1 - alpha_one) * 1999))])
    assert out["mean"] == pytest.approx(float(x.mean()))
    assert out["lower"] <= out["ci95"][0] <= out["ci95"][1] <= out["upper"]


def _entry(lower, upper, mc_se=0.0):
    return {"lower": lower, "upper": upper, "mc_se": mc_se}


def test_classification_and_the_family_verdict():
    assert ks.classify(_entry(-0.2, -0.05)) == "SEARCH_BETTER"
    assert ks.classify(_entry(0.01, 0.2)) == "RULE_BETTER"
    assert ks.classify(_entry(-0.1, 0.02)) == "NOT_SEPARATED"
    # a bound must clear 0 by more than 3 Monte Carlo standard errors
    assert ks.classify(_entry(-0.1, -0.002, mc_se=0.001)) == "NOT_SEPARATED"
    assert ks.classify(_entry(-0.1, -0.004, mc_se=0.001)) == "SEARCH_BETTER"
    assert ks.classify(_entry(0.002, 0.1, mc_se=0.001)) == "NOT_SEPARATED"

    def comps(classes):
        out = {}
        for cid, cls in zip(ks.COMPARISON_IDS, classes, strict=True):
            e = {"SB": _entry(-0.2, -0.1), "RB": _entry(0.1, 0.2), "NS": _entry(-0.1, 0.1)}[cls]
            out[cid] = dict(e, classification=ks.classify(e))
        return out

    assert ks.ha_verdict(comps(["SB"] * 7))["verdict"] == "SEARCH_DOMINATES"
    v = ks.ha_verdict(comps(["SB"] * 6 + ["NS"]))
    assert v["verdict"] == "INCONCLUSIVE" and v["not_separated"] == ["A7"]
    # a rule beating search at equal calls (A1, A2, A4, A7)
    for i, cid in ((0, "A1"), (1, "A2"), (3, "A4"), (6, "A7")):
        classes = ["SB"] * 7
        classes[i] = "RB"
        v = ks.ha_verdict(comps(classes))
        assert v["verdict"] == "RULE_BEATS_SEARCH" and v["rule_better_at_equal_calls"] == [cid]
    # a rule beating search only where it read more calls (A3, A5, A6) is a separate label that
    # blocks SEARCH_DOMINATES and licenses nothing at equal calls
    for i, cid in ((2, "A3"), (4, "A5"), (5, "A6")):
        classes = ["SB"] * 7
        classes[i] = "RB"
        v = ks.ha_verdict(comps(classes))
        assert v["verdict"] == "RULE_AT_MORE_CALLS_BETTER"
        assert v["rule_better_at_more_calls"] == [cid] and v["rule_better_at_equal_calls"] == []
    v = ks.ha_verdict(comps(["RB", "SB", "NS", "SB", "RB", "SB", "NS"]))
    assert v["verdict"] == "RULE_BEATS_SEARCH"
    assert v["rule_better_at_equal_calls"] == ["A1"] and v["rule_better_at_more_calls"] == ["A5"]
    assert [c.id for c in ks.COMPARISONS if c.matched] == ["A1", "A2", "A4", "A7"]


# --------------------------------------------------------------------------- H-C


def _pool(values, ranks, abstain):
    return {"question_id": "t", "question_type": "toy", "arm": "retrieved", "bm25_rank": ranks,
            "u": [int(v) for v in values], "abstain": abstain, "mean_lp": [0.0] * 256,
            "sum_lp": [0.0] * 256, "cls": [0] * 256}  # fmt: skip


def test_stop_rule_reads_in_bm25_rank_sum_order_and_falls_back_to_top4():
    ranks = [5, 0, 7, 1, 6, 2, 4, 3]
    order = sorted(ks.FOUR_SETS, key=lambda m: lf.rank_key(m, ranks), reverse=True)
    # ascending rank sum, then the lexicographically smaller sorted ranks
    keys = [sorted(ranks[i] for i in range(8) if m >> i & 1) for m in order]
    assert keys == sorted(keys, key=lambda r: (sum(r), r))
    assert order[0] == lf.bm25_top_mask(ranks)
    abstain = [False] * 256
    for m in order[:11]:
        abstain[m] = True
    values = [0.0] * 256
    values[order[11]] = 1.0
    choice = ks.nonabstain_choice(_pool(values, ranks, abstain), values)
    assert choice == {**choice, "mask": order[11], "u": 1.0, "first_answer_position": 12,
                      "reads": 12}  # fmt: skip
    nothing = ks.nonabstain_choice(_pool(values, ranks, [True] * 256), values)
    assert nothing["mask"] == order[0] and nothing["reads"] == 70
    assert nothing["first_answer_position"] is None and nothing["u"] == 0.0
    first = ks.nonabstain_choice(_pool(values, ranks, [False] * 256), values)
    assert first["mask"] == order[0] and first["reads"] == 1


def test_reads_summary():
    s = ks.reads_summary([1, 1, 2, 70, 8, 9, 1, 1, 1, 16])
    assert s["mean"] == 11.0 and s["max"] == 70 and s["at_1"] == 5
    assert s["at_most_8"] == 7 and s["at_most_16"] == 9 and s["p90"] == 16


# --------------------------------------------------------------------------- gates and pins


def _scratch_freeze(tmp_path, frozen: bool):
    """A scratch copy of the registration and a scratch ledger (with or without its row); the
    real ledger is never read, so these tests hold before and after the real freeze."""

    reg = tmp_path / "registration.md"
    reg.write_bytes((ROOT / ks.REGISTRATION).read_bytes())
    ledger = tmp_path / "ledger.jsonl"
    row = {"experiment_id": ks.EXPERIMENT, "sha256": ks.sha256_file(reg)}
    ledger.write_text(json.dumps(row) + "\n" if frozen else "")
    return reg, ledger


def test_heldout_is_refused_without_a_ledger_row(tmp_path, monkeypatch):
    """With a scratch ledger that lacks the row, every held-out entry point refuses at the gate,
    before any held-out file is opened. load_tables is given a scratch path, never the real held-out
    tables, and Path.read_bytes is made to fail so a read would be caught."""

    reg, ledger = _scratch_freeze(tmp_path, frozen=False)
    monkeypatch.setattr(ks, "LEDGER", ledger)
    monkeypatch.setattr(ks, "REGISTRATION", reg)
    with pytest.raises(ks.KeepsetError, match="after the freeze"):
        ks.gate("heldout")
    with pytest.raises(ks.KeepsetError, match="after the freeze"):
        ks.gate("heldout", ledger=ledger, registration=reg)

    def no_read(self):
        raise AssertionError(f"read before the gate: {self}")

    dummy = tmp_path / "tables.json.gz"
    dummy.write_bytes(b"")
    monkeypatch.setattr(Path, "read_bytes", no_read)
    with pytest.raises(ks.KeepsetError, match="after the freeze"):
        ks.load_tables("heldout", dummy)
    monkeypatch.undo()
    monkeypatch.setattr(ks, "LEDGER", ledger)
    monkeypatch.setattr(ks, "REGISTRATION", reg)
    for argv in (
        ["analyze", "--split", "heldout", "--h-c-void", "x", "--output-dir", str(tmp_path / "o")],
        ["extract", "--split", "heldout", "--run-dir", str(tmp_path), "--evidence",
         str(dummy), "--private-dir", str(tmp_path / "p")],
    ):  # fmt: skip
        assert ks.main(argv) == 1
    assert not (tmp_path / "o").exists() and not (tmp_path / "p").exists()


def test_the_gate_opens_with_a_ledger_row_and_matching_pins(tmp_path):
    """With a scratch ledger row for a scratch copy of the registration, the gate passes (its
    code pins match the working tree) and records it; no held-out file is touched."""

    reg, ledger = _scratch_freeze(tmp_path, frozen=True)
    assert ks.registration_frozen(ledger, reg)
    record = ks.gate("heldout", ledger=ledger, registration=reg)
    assert record["registration_frozen"] and record["pins"]["all_match"]
    tampered = tmp_path / "tampered.md"
    good = ks.code_pins(reg)["harness/memcredit.py"]
    tampered.write_text(reg.read_text().replace(good, "0" * 64))
    ledger.write_text(json.dumps({"experiment_id": ks.EXPERIMENT,
                                  "sha256": ks.sha256_file(tampered)}) + "\n")  # fmt: skip
    with pytest.raises(ks.KeepsetError, match="pins"):
        ks.gate("heldout", ledger=ledger, registration=tampered)


def test_registration_frozen_reads_a_scratch_ledger(tmp_path):
    reg = tmp_path / "reg.md"
    reg.write_text("x")
    ledger = tmp_path / "ledger.jsonl"
    digest = ks.sha256_file(reg)
    ledger.write_text(json.dumps({"experiment_id": ks.EXPERIMENT, "sha256": digest}) + "\n")
    assert ks.registration_frozen(ledger, reg)
    ledger.write_text(json.dumps({"experiment_id": "other", "sha256": digest}) + "\n")
    assert not ks.registration_frozen(ledger, reg)
    ledger.write_text(json.dumps({"experiment_id": ks.EXPERIMENT, "sha256": "0" * 64}) + "\n")
    assert not ks.registration_frozen(ledger, reg)


def test_registration_freezes_on_a_scratch_ledger(tmp_path):
    """The freeze command accepts the file (no TBD or angle-bracket placeholder); run against an
    empty scratch ledger, never the real one."""

    spec = importlib.util.spec_from_file_location("preregister", ROOT / "scripts/preregister.py")
    prereg = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(prereg)
    ledger = tmp_path / "ledger.jsonl"
    row = prereg.freeze(ROOT / ks.REGISTRATION, ks.EXPERIMENT, ledger=ledger, root=ROOT)
    assert row["sha256"] == ks.sha256_file(ROOT / ks.REGISTRATION)
    assert ks.registration_frozen(ledger, ROOT / ks.REGISTRATION)


def test_code_pins_parse_and_match_the_working_tree():
    """Section 16 of the registration pins this script, these tests and the code they reuse;
    every pin must match (a code change means re-pinning before the freeze)."""

    pins = ks.code_pins()
    for path in ("scripts/memcredit_keepset_search.py", "tests/test_memcredit_keepset_search.py",
                 "scripts/memcredit_cost_curve.py", "scripts/memcredit_label_free.py",
                 "scripts/memcredit_analyze.py", "harness/memcredit.py",
                 "harness/memcredit_study.py"):  # fmt: skip
        assert path in pins
    assert ks.check_code_pins()["all_match"]


def test_code_pins_detect_a_change(tmp_path):
    reg = tmp_path / "reg.md"
    good = ks.sha256_file(ROOT / "harness/memcredit.py")
    row = f"| `harness/memcredit.py` | x | `{good}` |"
    reg.write_text(f"{ks.CODE_SECTION}\n\n{row}\n\n## 17. Next\n")
    assert ks.check_code_pins(reg)["files"] == 1
    reg.write_text(f"{ks.CODE_SECTION}\n\n| `harness/memcredit.py` | x | `{'0' * 64}` |\n")
    with pytest.raises(ks.KeepsetError, match="differs"):
        ks.check_code_pins(reg)


@pytest.mark.parametrize(
    "path",
    [
        "program/evidence/2026-10-16/am1-confirmatory/analysis/tables.json.gz",
        "/home/x/cotcodec-runs/stage0/am1-memory-credit-v1/runs/main/1458/am1",
    ],
)
def test_development_refuses_heldout_paths(path, tmp_path):
    with pytest.raises(ks.KeepsetError):
        ks.check_development_path(path)
    target = tmp_path / "am1-confirmatory"
    target.mkdir()
    link = tmp_path / "innocent"
    link.symlink_to(target)
    with pytest.raises(ks.KeepsetError):
        ks.check_development_path(link)


def test_heldout_pins_are_the_committed_records():
    """The pinned held-out digests equal the SHA-256 records AM1 committed (text files only)."""

    spec = ks.SPLITS["heldout"]
    base = ROOT / ks.HELDOUT_DIR
    records = {}
    for worker in ("reader-gpu0", "judge32-gpu0", "judge8-gpu0"):
        for line in (base / f"jobs/1458-main/am1/sessions/{worker}/raw-sha256.txt").read_text(
        ).splitlines():  # fmt: skip
            digest, name = line.split()
            records[f"sessions/{worker}/{name[2:]}"] = digest
    for key, digest in spec["pass"]["sha256"].items():
        if key in records:
            assert records[key] == digest
    items = (base / "jobs/1458-main/am1/judge-items.sha256.txt").read_text().split()[0]
    assert spec["pass"]["sha256"]["judge-items.json"] == items
    assert spec["artifact_sha256"] == (base / "jobs/1458-main/study-artifact.sha256").read_text(
    ).strip()  # fmt: skip
    outputs = dict(
        reversed(line.split())
        for line in (base / "analysis/logs/outputs.sha256").read_text().splitlines()  # fmt: skip
    )
    assert spec["tables_json_sha256"] == outputs["./tables.json"]
    assert ks.sha256_file(ROOT / spec["tables"]) == spec["tables_sha256"]  # a digest, not a read
    config = ms.load_config(ms.REGISTRATION_CONFIG_PATH)
    assert config["confirmatory_set"]["question_ids_sha256"] == spec["question_ids_sha256"]


def test_abstention_list_is_am1d_s():
    assert (
        lf.patterns_sha256()
        == lf.ABSTENTION_PATTERNS_SHA256
        == ("031bee27e934a772f3419e38f9956d33dbea01096e6657e67426fd8a399d935f")
    )


# --------------------------------------------------------------------------- development tables


def test_development_tables_load_and_validate(dev_tables, tmp_path):
    report = ks.validate_tables(dev_tables, "development")
    assert report["nonconstant"] == {"gold": 51, "retrieved": 38} and report["questions"] == 63
    tampered = tmp_path / "tables.json.gz"
    tampered.write_bytes(gzip.compress(b"[]", mtime=0))
    with pytest.raises(ks.KeepsetError, match="SHA-256"):
        ks.load_tables("development", tampered)
    broken = copy.deepcopy(dev_tables)
    broken[0]["summary"]["constant"] = not broken[0]["summary"]["constant"]
    with pytest.raises(ks.KeepsetError, match="VOID"):
        ks.validate_tables(broken, "development")


def test_hb_on_the_development_tables_reproduces_am1d(dev_tables):
    """BM25 top 4 vs all 8 over the 63 development questions: 4 vs 0 (exact p = 0.125) on the
    retrieved arm and 2 vs 3 on the gold arm, as AM1d's README states."""

    results, _ = ks.analyze(dev_tables, None, "development", n_seeds=1, resamples=500)
    hb = results["h_b_descriptive"]
    assert hb["decides"] is False and "H-B" not in results["verdicts"]
    assert hb["retrieved"]["description"] == "NO_DETECTED_DIFFERENCE"
    assert "reading" not in hb["retrieved"]
    assert (hb["retrieved"]["rule_right_base_wrong"], hb["retrieved"]["rule_wrong_base_right"]) == (
        4, 0)  # fmt: skip
    assert hb["retrieved"]["p_exact_mcnemar"] == 0.125
    assert (hb["gold"]["rule_right_base_wrong"], hb["gold"]["rule_wrong_base_right"]) == (2, 3)
    assert results["h_a"]["retrieved"]["tables"] == 38
    am1b = json.loads((ROOT / ks.AM1B_DIR / "results.json").read_text())
    for name in ("loo", "greedy_backward"):
        assert (
            results["h_a"]["retrieved"]["rules"][name]["mean"]
            == (am1b["curve"]["retrieved"]["4"][name]["mean_regret"])
        )


# --------------------------------------------------------------------------- end to end


def _synthetic(questions: int = 6, seed: int = 3):
    rng = random.Random(seed)
    tables, pools = [], []
    for q in range(questions):
        for arm in ks.ARMS:
            constant = q == 0
            values = [0.0 if constant else float(rng.random() < 0.4) for _ in range(256)]
            values[0] = 0.0
            ranks = rng.sample(range(1, 30), 8)
            cls = [rng.randrange(4) for _ in range(256)]
            tables.append({
                "question_id": f"q{q}", "question_type": "multi-session" if q % 2 else "temporal",
                "arm": arm, "complete": True, "values_hex": cc.encode_values(values),
                "summary": {"constant": constant},
                "credits": {"retrieval_rank": [-float(r) for r in ranks]},
            })  # fmt: skip
            pools.append({
                "question_id": f"q{q}", "question_type": "multi-session" if q % 2 else "temporal",
                "arm": arm, "bm25_rank": ranks, "u": [int(v) for v in values],
                "mean_lp": [round(rng.uniform(-2, 0), 6) for _ in range(256)],
                "sum_lp": [0.0] * 256, "cls": cls, "abstain": [c == 3 for c in cls],
                "pattern": ["i_dont_know" if c == 3 else None for c in cls],
                "n_tokens": [3] * 256, "finish": ["stop"] * 256, "eot": [True] * 256,
            })  # fmt: skip
    return tables, {"pass": {"name": "synthetic"}, "validation": {"passed": True}, "pools": pools}


def test_analyze_end_to_end_is_deterministic():
    tables, features = _synthetic()
    outs = []
    for _ in range(2):
        results, records = ks.analyze(
            copy.deepcopy(tables), copy.deepcopy(features), "development", n_seeds=4,
            resamples=300, check_counts=False,
        )  # fmt: skip
        outs.append((ks.canonical(results), ks.canonical(records), ks.render_markdown(results)))
    assert outs[0] == outs[1]
    assert results["h_a"]["retrieved"]["tables"] == 5
    assert set(results["verdicts"]) == {"H-A", "H-C"}
    assert results["h_c"]["status"] == "READ" and results["h_b_descriptive"]["decides"] is False
    assert "## H-B (descriptive, D116; no decision)" in outs[0][2]
    assert "Description (not a decision)" in outs[0][2]
    assert results["verdicts"]["H-A"]["verdict"] in ("SEARCH_DOMINATES", "RULE_BEATS_SEARCH",
                                                     "RULE_AT_MORE_CALLS_BETTER",
                                                     "INCONCLUSIVE")  # fmt: skip
    for cid in ks.COMPARISON_IDS:
        c = results["h_a"]["retrieved"]["comparisons"][cid]
        assert c["lower"] <= c["mean"] <= c["upper"]
        if c["seeds"] == 1:
            assert c["mc_se"] == 0.0
    desc = results["descriptive"]["retrieved"]
    assert set(desc) == {"all", "multi-session", "temporal"}
    assert desc["all"]["questions"] == 6 and desc["all"]["abstention"]["four_subset_replies"] == 420
    assert results["h_c"]["retrieved"]["reads"]["all_questions"]["pools"] == 6
    assert "## H-A, retrieved arm" in outs[0][2] and "## H-C" in outs[0][2]
    # the oracle ceiling is at least every rule's accuracy
    acc = desc["all"]["accuracy"]
    for name in ("bm25_top4", "all_8", "nonabstain_bm25"):
        assert acc[name]["mean"] <= acc["oracle_ceiling"]["mean"] + 1e-12 or name == "all_8"


def test_features_from_another_pass_split_or_code_are_refused():
    payload = {
        "experiment": ks.EXPERIMENT, "split": "development",
        "pass": {"sha256": dict(ks.SPLITS["development"]["pass"]["sha256"]),
                 "study_artifact_sha256": ks.SPLITS["development"]["artifact_sha256"]},
        "abstention_patterns_sha256": lf.ABSTENTION_PATTERNS_SHA256,
        "code_sha256": ks.code_digests(),
    }  # fmt: skip
    ks.check_features(payload, "development")
    for mutate in (
        lambda p: p.update(split="heldout"),
        lambda p: p["pass"]["sha256"].update({"judge-items.json": "0" * 64}),
        lambda p: p.update(abstention_patterns_sha256="0" * 64),
        lambda p: p["code_sha256"].update({"harness/memcredit.py": "0" * 64}),
    ):
        bad = copy.deepcopy(payload)
        mutate(bad)
        with pytest.raises(ks.KeepsetError, match=r"VOID \(H-C, V5\)"):
            ks.check_features(bad, "development")


# --------------------------------------------------------------------------- the H-C void path


def test_h_c_void_path_runs_h_a_and_h_b_from_the_tables(tmp_path):
    """Registration section 8: when an H-C input fails (V3 or V5), analyze runs with --h-c-void
    and the named error; H-A, H-B and the descriptive outputs come from the tables alone."""

    out = tmp_path / "out"
    reason = "VOID (H-C, V3): the features file is unreadable or incomplete: EOFError: test"
    argv = ["analyze", "--split", "development", "--h-c-void", reason, "--output-dir", str(out),
            "--seeds", "1", "--resamples", "200"]  # fmt: skip
    assert ks.main(argv) == 0
    results = json.loads((out / "results.json").read_text())
    assert results["h_c"] == {"status": "VOID", "reason": reason}
    assert results["verdicts"]["H-C"] == {"arm": "retrieved", "reading": "VOID", "reason": reason}
    assert results["verdicts"]["H-A"]["verdict"] in ("SEARCH_DOMINATES", "INCONCLUSIVE",
                                                     "RULE_BEATS_SEARCH",
                                                     "RULE_AT_MORE_CALLS_BETTER")  # fmt: skip
    assert results["h_a"]["retrieved"]["tables"] == 38
    assert results["h_b_descriptive"]["retrieved"]["rule_right_base_wrong"] == 4
    assert "abstention" not in results["descriptive"]["retrieved"]["all"]
    assert f"**VOID**: {reason}" in (out / "tables.md").read_text()
    both = ["analyze", "--split", "development", "--h-c-void", "x", "--features", "f",
            "--output-dir", str(tmp_path / "o2")]  # fmt: skip
    assert ks.main(both) == 1


def test_unreadable_features_are_a_named_h_c_void(tmp_path, capsys):
    whole = gzip.compress(json.dumps({"pools": [], "experiment": ks.EXPERIMENT}).encode(), mtime=0)
    cases = {
        "truncated.json.gz": whole[: len(whole) // 2],
        "not-gzip.json.gz": b"plain text",
        "no-pools.json.gz": gzip.compress(b"[1, 2]", mtime=0),
    }
    for name, blob in cases.items():
        path = tmp_path / name
        path.write_bytes(blob)
        with pytest.raises(ks.KeepsetError, match=r"VOID \(H-C, V3\): the features file"):
            ks.load_features(path, "development")
        argv = ["analyze", "--split", "development", "--features", str(path), "--output-dir",
                str(tmp_path / "o"), "--seeds", "1", "--resamples", "100"]  # fmt: skip
        assert ks.main(argv) == 1
        assert "VOID (H-C, V3)" in capsys.readouterr().err
    with pytest.raises(ks.KeepsetError, match="unreadable or incomplete: FileNotFoundError"):
        ks.load_features(tmp_path / "absent.json.gz", "development")
    # readable, but from another pass: the V5 void
    other = tmp_path / "other.json.gz"
    ks.write_gz_json(other, {"experiment": ks.EXPERIMENT, "split": "development", "pools": [],
                             "pass": {"sha256": {}, "study_artifact_sha256": "0"}})  # fmt: skip
    with pytest.raises(ks.KeepsetError, match=r"VOID \(H-C, V5\)"):
        ks.load_features(other, "development")
    assert not list(tmp_path.glob("*.partial"))


def test_a_missing_or_changed_pass_file_is_a_named_h_c_void(tmp_path, capsys):
    with pytest.raises(ks.KeepsetError, match=r"VOID \(H-C, V3\): judge-items.json is missing"):
        ks.check_digests(tmp_path, {"judge-items.json": "0" * 64})
    (tmp_path / "judge-items.json").write_text("[]")
    with pytest.raises(ks.KeepsetError, match=r"VOID \(H-C, V3\): judge-items.json: SHA-256"):
        ks.check_digests(tmp_path, {"judge-items.json": "0" * 64})
    # end to end on the development split: the tables pass V1 and V2, then the pass is missing
    argv = ["extract", "--split", "development", "--run-dir", str(tmp_path / "run"),
            "--evidence", str(tmp_path / "artifact.json"), "--private-dir",
            str(tmp_path / "private")]  # fmt: skip
    assert ks.main(argv) == 1
    err = capsys.readouterr().err
    assert "VOID (H-C, V3)" in err and "missing or unreadable" in err and "Traceback" not in err
    assert not (tmp_path / "private").exists()


def test_features_that_do_not_match_the_tables_are_a_named_h_c_void():
    tables, features = _synthetic()
    assert len(ks.match_features(features, tables)) == len(tables)
    for mutate in (
        lambda f: f["pools"].pop(),
        lambda f: f["pools"][1]["u"].__setitem__(255, 1 - f["pools"][1]["u"][255]),
        lambda f: f["pools"][2]["bm25_rank"].reverse(),
        lambda f: f["pools"][3].update(question_type="other"),
        lambda f: f["pools"][4]["abstain"].pop(),
        lambda f: f["pools"][5].pop("u"),
    ):
        bad = copy.deepcopy(features)
        mutate(bad)
        with pytest.raises(ks.KeepsetError, match=r"VOID \(H-C, V3\)"):
            ks.match_features(bad, tables)
        with pytest.raises(ks.KeepsetError, match=r"VOID \(H-C, V3\)"):
            ks.analyze(tables, bad, "development", n_seeds=1, resamples=50, check_counts=False)


def test_the_feature_code_is_the_whole_import_closure():
    """V5 records the SHA-256 of this script and every repository module extract imports (checked
    in a fresh interpreter, so other tests' imports do not count)."""

    import subprocess

    code = (
        "import sys, pathlib; root = pathlib.Path(sys.argv[1]).resolve(); "
        "sys.path[:0] = [str(root), str(root / 'scripts')]; "
        "import memcredit_keepset_search, memcredit_analyze, memcredit_study; "
        "print('\\n'.join(sorted(str(pathlib.Path(m.__file__).resolve().relative_to(root)) "
        "for m in list(sys.modules.values()) if getattr(m, '__file__', None) "
        "and pathlib.Path(m.__file__).resolve().is_relative_to(root))))"
    )
    out = subprocess.run([sys.executable, "-I", "-c", code, str(ROOT)], capture_output=True,
                         text=True, check=True, cwd=ROOT)  # fmt: skip
    assert sorted(ks.FEATURE_CODE) == out.stdout.split()
    pins = ks.code_pins()
    assert all(path in pins for path in ks.FEATURE_CODE)
