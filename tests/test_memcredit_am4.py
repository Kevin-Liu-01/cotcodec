"""Tests for AM4, the read-cap analysis (scripts/memcredit_am4.py): the capped rule against the
registered rule, the K = 70 check against the registered analysis run on the same toy features,
determinism, the hand-label join, the per-table crosscheck and the input digests.

No test opens a held-out or abstention input: the features here are toys built in memory."""

from __future__ import annotations

import copy
import gzip
import json
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import memcredit_am3 as am3  # noqa: E402
import memcredit_am3g as g  # noqa: E402
import memcredit_am4 as am4  # noqa: E402
import memcredit_label_free as lf  # noqa: E402

RESAMPLES = 200


# --------------------------------------------------------------------------- toy features


def _pool(qid: str, arm: str, rng: random.Random, answerable: bool) -> dict:
    ranks = rng.sample(range(8), 8)
    p_abs = rng.choice((0.1, 0.5, 0.9, 1.0))
    masks = {}
    for m in g.REQUEST_MASKS:
        abstain = rng.random() < p_abs
        if answerable:
            u1 = 0 if abstain else int(rng.random() < 0.6)
        else:
            u1 = int(abstain) if rng.random() < 0.95 else 1 - int(abstain)
        u2 = u1 if rng.random() < 0.85 else 1 - u1
        masks[m] = {"finish": "stop", "u": {"primary": u1, "secondary": u2}, "abstain": abstain,
                    "pattern": "idk" if abstain else None, "digest": g.sha256_text(f"{qid}:{m}"),
                    "hedge": rng.random() < 0.1, "n_tokens": 5}  # fmt: skip
    return {"question_id": qid, "question_type": rng.choice(("a", "b")), "arm": arm,
            "bm25_rank": ranks, "gold_mask": rng.choice((0, 3)),
            "masks": {str(m): c for m, c in masks.items()}}  # fmt: skip


def _features(population: str, n: int, seed: int) -> dict:
    rng = random.Random(seed)
    arms = g.ARMS if population == "heldout" else ("retrieved",)
    qids = (
        [f"q{i:03d}" for i in range(n)]
        if population == "heldout"
        else [f"q{i:03d}_abs" for i in range(n // 2)] + [f"z{i:03d}_abs" for i in range(n - n // 2)]
    )
    readers = {}
    for reader in g.H2_READERS:
        pools = [_pool(q, arm, rng, population == "heldout") for q in qids for arm in arms]
        readers[reader] = {"pools": pools, "step": "s", "batch_invariant": reader != "qwen3.5-9b",
                           "enforce_eager": True, "pass_sha256": {}, "requests": 0, "finish": {},
                           "missing_logprobs": 0, "pools_complete_primary": len(pools),
                           "pools_complete": len(pools)}  # fmt: skip

    def v(items: int, yes: int) -> dict:
        return {"items": items, "yes": yes, "missing": 0}

    judge_validation = {j: {"validation:reference": v(10, 10), "validation:idk": v(10, 0),
                            "validation:abs-idk": v(10, 10), "validation:abs-decoy": v(10, 0),
                            "validation:abs-explanation": v(10, 10)} for j in g.JUDGES}  # fmt: skip
    return {"experiment": g.EXPERIMENT, "population": population, "arms": list(arms),
            "artifact_sha256": "0" * 64, "question_ids_sha256": "0" * 64, "questions": len(qids),
            "code_sha256": {}, "run": {},
            "validation": {"judge_validation": judge_validation},
            "comparisons": {"anchor": {"pass": True, "r1_replies": {"pass": True},
                                       "r2_labels_vs_tables": {"pass": True}}},
            "readers": readers}  # fmt: skip


def _config() -> dict:
    config = copy.deepcopy(g.load_config())
    config["analysis"]["bootstrap"]["resamples"] = RESAMPLES
    return config


def _labels(heldout: dict, abstention: dict) -> list[dict]:
    """A label per plan item: the judge's, flipped on every seventh item; a free-text note."""

    h, a = copy.deepcopy(heldout), copy.deepcopy(abstention)
    g.int_masks(h)
    g.int_masks(a)
    plan = g.hand_plan(h, a)
    return [{"item_id": it["item_id"],
             "label": int(it["uses"][0]["judge_primary"]) ^ int(n % 7 == 0),
             "note": "PRIVATE-NOTE-TEXT"} for n, it in enumerate(plan["items"])]  # fmt: skip


@pytest.fixture(scope="module")
def toy(request):
    heldout, abstention = _features("heldout", 40, 1), _features("abstention", 12, 2)
    labels = _labels(heldout, abstention)
    config = _config()
    mp = pytest.MonkeyPatch()
    mp.setattr(g, "check_features", lambda *a, **k: None)
    registered, per_table = g.analyze_registered(copy.deepcopy(heldout),
                                                 copy.deepcopy(abstention), config, None,
                                                 labels, "x" * 64)  # fmt: skip
    registered = json.loads(json.dumps(registered))
    d = registered["descriptive"]
    headline = {
        "heldout_b_c": {r: tuple(d["cells_heldout"][r]["primary"]["retrieved"]["paired"][
            "nonabstain_bm25_vs_bm25_top4"][k] for k in ("rule_right_base_wrong",
                                                         "rule_wrong_base_right"))
            for r in g.H2_READERS},
        "abstention_b2": {r: registered["h2"]["readers"][r]["b2_top4_right_rule_wrong"]
                          for r in g.H2_READERS},
    }  # fmt: skip
    mp.setattr(am4, "REGISTERED_HEADLINE", headline)
    request.addfinalizer(mp.undo)
    return {"heldout": heldout, "abstention": abstention, "labels": labels, "config": config,
            "registered": registered, "per_table": json.loads(json.dumps(per_table))}  # fmt: skip


def _run(toy: dict, registered: dict | None = None, labels: list | None = None) -> dict:
    return am4.analyze(copy.deepcopy(toy["heldout"]), copy.deepcopy(toy["abstention"]),
                       toy["config"], registered or toy["registered"],
                       toy["labels"] if labels is None else labels, "x" * 64,
                       hand_plan_sha256=None, check_provenance=False)  # fmt: skip


# --------------------------------------------------------------------------- the capped rule


def _int_pool(seed: int) -> dict:
    pool = _pool("t", "retrieved", random.Random(seed), True)
    pool["masks"] = {int(m): c for m, c in pool["masks"].items()}
    return pool


def test_the_caps_are_d119s_plus_1_and_26():
    assert am4.CAPS == (1, 2, 4, 8, 16, 26, 70) and am4.FULL_ORDER == 70


@pytest.mark.parametrize("seed", range(40))
def test_cap_70_is_the_registered_rule_and_cap_1_is_bm25_top4(seed):
    pool = _int_pool(seed)
    rule = am3.nonabstain_bm25(pool)
    full = am4.capped_rule(pool, 70)
    assert (full["mask"], full["reads"]) == (rule["mask"], rule["reads"])
    one = am4.capped_rule(pool, 1)
    assert one["mask"] == lf.bm25_top_mask(pool["bm25_rank"]) and one["reads"] == 1


@pytest.mark.parametrize("seed", range(40))
def test_the_cap_only_removes_switches_and_reads_grow_with_it(seed):
    pool = _int_pool(seed)
    rule = am3.nonabstain_bm25(pool)
    top = am3.bm25_order(pool["bm25_rank"])[0]
    previous = 0
    for cap in range(1, 71):
        c = am4.capped_rule(pool, cap)
        assert c["mask"] in (rule["mask"], top)
        assert c["reads"] >= previous and c["reads"] <= cap
        previous = c["reads"]
        pos = rule["first_answer_position"]
        assert c["answered_within_cap"] == (pos is not None and pos <= cap)
        assert c["mask"] == (rule["mask"] if c["answered_within_cap"] else top)


@pytest.mark.parametrize("cap", [0, 71, -1])
def test_a_cap_outside_1_to_70_is_refused(cap):
    with pytest.raises(am4.Am4Error, match="cap"):
        am4.capped_rule(_int_pool(0), cap)


def test_capped_records_take_the_capped_replys_label():
    pools = [_int_pool(s) for s in range(10)]
    for i, p in enumerate(pools):
        p["question_id"] = f"t{i}"
    records = [g.table_record(p) for p in pools]
    for cap in (1, 4, 70):
        for p, r in zip(pools, am4.capped_records(pools, records, cap), strict=True):
            c = am4.capped_rule(p, cap)
            assert r["nonabstain_mask"] == c["mask"] and r["reads"] == c["reads"]
            for j in g.JUDGES:
                assert r["u"][j]["nonabstain_bm25"] == p["masks"][c["mask"]]["u"][j]
                assert r["u"][j]["bm25_top4"] == p["masks"][r["bm25_top4_mask"]]["u"][j]
    with pytest.raises(am4.Am4Error, match="aligned"):
        am4.capped_records(pools, records[::-1], 4)


# --------------------------------------------------------------------------- end to end


def test_k70_reproduces_the_registered_analysis_of_the_same_features(toy):
    results = _run(toy)
    assert results["k70_check"]["pass"] and results["k70_check"]["differences"] == []
    assert results["k70_check"]["compared"] > 100
    assert results["claim_level"] == "exploratory, post hoc"
    curve = results["curve"]
    for reader in g.H2_READERS:
        assert sorted(curve[reader], key=int) == [str(k) for k in am4.CAPS]
        one = curve[reader]["1"]
        for arm in g.ARMS:
            for j in g.JUDGES:
                e = one["heldout"][arm][j]
                assert (e["rule_right_base_wrong"], e["rule_wrong_base_right"]) == (0, 0)
            assert one["heldout"][arm]["reads"]["mean"] == 1.0
        assert one["abstention"]["retrieved"]["primary"]["b2_top4_right_rule_wrong"] == 0
        # A cap only removes switches, so gains and costs grow with K.
        bs = [curve[reader][str(k)]["heldout"]["retrieved"]["primary"]["rule_right_base_wrong"]
              for k in am4.CAPS]  # fmt: skip
        assert bs == sorted(bs)


def test_analyze_is_deterministic_and_text_free(toy):
    first, second = _run(toy), _run(toy)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    text = json.dumps(first) + am4.render_markdown(first)
    assert "PRIVATE-NOTE-TEXT" not in text
    assert "q000" not in text  # no question ids either: aggregates only
    assert am4.render_markdown(first) == am4.render_markdown(second)


def test_one_registered_difference_stops_the_analysis(toy):
    registered = copy.deepcopy(toy["registered"])
    cell = registered["descriptive"]["cells_heldout"]["qwen3.5-9b"]["secondary"]["gold"]
    cell["paired"]["nonabstain_bm25_vs_bm25_top4"]["ci95_bootstrap"][0] += 1e-9
    with pytest.raises(am4.Am4Error, match="K = 70 does not reproduce"):
        _run(toy, registered=registered)
    registered = copy.deepcopy(toy["registered"])
    registered["descriptive"]["natural_mix"]["primary"]["qwen3-8b"]["mix_rate"] += 1e-9
    with pytest.raises(am4.Am4Error, match="natural_mix.primary.qwen3-8b"):
        _run(toy, registered=registered)


def test_the_registered_headline_is_checked(toy, monkeypatch):
    headline = copy.deepcopy(am4.REGISTERED_HEADLINE)
    headline["abstention_b2"]["olmo-2-1124-7b-instruct"] += 1
    monkeypatch.setattr(am4, "REGISTERED_HEADLINE", headline)
    with pytest.raises(am4.Am4Error, match="headline.olmo-2-1124-7b-instruct.b2"):
        _run(toy)


def test_hand_labels_must_cover_the_plan_and_join_at_70(toy):
    results = _run(toy)
    hand = toy["registered"]["h1_hand_check"]
    for reader in g.H1_READERS:
        got = results["curve"][reader]["70"]["hand"]["heldout"]
        assert got["hand_rule_right_top4_wrong"] == hand["readers"][reader]["b_hand"]
        assert "heldout" not in results["curve"]["qwen3-8b"]["70"]["hand"]
        counts = [results["curve"][reader][str(k)]["hand"]["heldout"][
            "judge_discordant_questions"] for k in am4.CAPS]  # fmt: skip
        assert counts == sorted(counts) and counts[0] == 0
    with pytest.raises(am4.Am4Error, match="do not cover"):
        _run(toy, labels=toy["labels"][1:])


def test_hand_at_cap_counts_split_pairs():
    def row(q, rule, top, u_rule, u_top):
        return {"question_id": q, "arm": "retrieved", "nonabstain_mask": rule,
                "bm25_top4_mask": top,
                "u": {"primary": {"nonabstain_bm25": u_rule, "bm25_top4": u_top}}}  # fmt: skip

    index = {("heldout", "r", "a", 1): 1, ("heldout", "r", "a", 2): 0,  # split, judge agrees
             ("heldout", "r", "b", 1): 0, ("heldout", "r", "b", 2): 0,  # judge split, hand not
             ("heldout", "r", "c", 1): 1, ("heldout", "r", "c", 2): 0}  # fmt: skip
    rows = [row("a", 1, 2, 0, 0), row("b", 1, 2, 1, 0), row("c", 1, 2, 1, 0),
            row("d", 2, 2, 0, 0), row("e", 1, 2, 0, 0)]  # fmt: skip
    got = am4.hand_at_cap(rows, "heldout", "r", index)
    assert got == {"judge_discordant_questions": 2, "hand_rule_right_top4_wrong": 1,
                   "hand_rule_wrong_top4_right": 0,
                   "judge_concordant_switched_pairs_hand_labelled": 1,
                   "of_which_hand_rule_right_top4_wrong": 1,
                   "of_which_hand_rule_wrong_top4_right": 0}  # fmt: skip
    with pytest.raises(am4.Am4Error, match="lacks a hand label"):
        am4.hand_at_cap([row("f", 1, 2, 1, 0)], "heldout", "r", index)


def test_crosscheck_reaches_the_same_figures_from_the_per_table_records(toy):
    results = _run(toy)
    report = am4.crosscheck(toy["per_table"], results)
    assert report["pass"] and report["compared"] == 3 * 7 * (3 * 6 + 2 * 2)
    broken = copy.deepcopy(results)
    broken["curve"]["olmo-2-1124-7b-instruct"]["8"]["abstention"]["retrieved"]["secondary"][
        "rule_wrong_base_right"
    ] += 1
    assert not am4.crosscheck(toy["per_table"], broken)["pass"]


# --------------------------------------------------------------------------- the CLI


def test_analyze_refuses_inputs_other_than_the_registered_ones(tmp_path, capsys):
    fake = tmp_path / "results.json"
    fake.write_text("{}")
    code = am4.main(["analyze", "--heldout-features", str(fake), "--abstention-features",
                     str(fake), "--hand-labels", str(fake), "--registered-results", str(fake),
                     "--output-dir", str(tmp_path / "out")])  # fmt: skip
    assert code == 1 and "registered SHA-256" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


def test_the_registered_results_and_per_table_pins_match_the_committed_files():
    assert g.sha256_file(am4.REGISTERED_DIR / "results.json") == am4.REGISTERED_RESULTS_SHA256
    assert g.sha256_file(am4.REGISTERED_DIR / "per-table.json.gz") == (
        am4.REGISTERED_PER_TABLE_SHA256
    )
    hand = am4.REGISTERED_DIR / "hand-check"
    assert (hand / "hand-labels.sha256.txt").read_text().split()[0] == am4.HAND_LABELS_SHA256
    assert (hand / "hand-plan.sha256.txt").read_text().split()[0] == am4.HAND_PLAN_SHA256
    registered = json.loads((am4.REGISTERED_DIR / "results.json").read_text())
    assert registered["features_sha256"] == am4.FEATURES_SHA256


def test_crosscheck_cli_refuses_another_per_table(tmp_path, capsys):
    other = tmp_path / "per-table.json.gz"
    with gzip.open(other, "wt") as fh:
        json.dump([], fh)
    code = am4.main(["crosscheck", "--per-table", str(other), "--results", str(other)])
    assert code == 1 and "registered SHA-256" in capsys.readouterr().err
