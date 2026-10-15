"""Tests for AM1d's label-free search (scripts/memcredit_label_free.py): the fixed abstention list,
the refusal of held-out paths, the join and its validation against the committed tables (on a toy
run directory read through the harness's own join), and the search and its scoring on toy
tables."""

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

import memcredit_analyze as ma  # noqa: E402
import memcredit_cost_curve as cc  # noqa: E402
import memcredit_label_free as lf  # noqa: E402
import memcredit_study as driver  # noqa: E402

from harness import memcredit as mc  # noqa: E402
from harness import memcredit_study as ms  # noqa: E402

FULL = lf.FULL


# --------------------------------------------------------------------------- abstention


def test_abstention_pattern_list_is_pinned():
    pinned = "031bee27e934a772f3419e38f9956d33dbea01096e6657e67426fd8a399d935f"  # 7465903f
    assert lf.patterns_sha256() == pinned
    assert lf.ABSTENTION_PATTERNS_SHA256 == pinned
    assert len(lf.ABSTENTION_PATTERNS) == 4


@pytest.mark.parametrize(
    ("reply", "expected"),
    [
        ("I don't know.", (True, "i_dont_know")),
        ("I do not know which one you mean.", (True, "i_dont_know")),
        ("I cannot determine the date from the memories.", (True, "cannot_answer")),
        ("There is no information about that.", (True, "no_information")),
        ("The memories do not mention a price.", (True, "not_in_memories")),
        ("The price is not mentioned.", (True, "not_in_memories")),
        ("", (True, "empty")),
        ("   ", (True, "empty")),
        ("You bought three apples.", (False, None)),
        ("No, you didn't.", (False, None)),
        ("Your dog's name is Max.", (False, None)),
    ],
)
def test_abstention(reply, expected):
    assert lf.abstention(reply) == expected


# --------------------------------------------------------------------------- paths


@pytest.mark.parametrize(
    "path",
    [
        "program/evidence/2026-10-16/am1-confirmatory/analysis/tables.json.gz",
        "/home/x/cotcodec-runs/stage0/am1-confirmatory/runs/1458/am1",
        "/home/x/cotcodec-runs/stage0/am1-memory-credit-v1/anything",
    ],
)
def test_held_out_paths_are_refused(path):
    with pytest.raises(lf.LabelFreeError):
        lf.check_path(path)


def test_held_out_symlink_is_refused(tmp_path):
    target = tmp_path / "am1-confirmatory"
    target.mkdir()
    link = tmp_path / "innocent"
    link.symlink_to(target)
    with pytest.raises(lf.LabelFreeError):
        lf.check_path(link)


def test_development_paths_are_accepted():
    lf.check_path(ROOT / cc.DEV_TABLES)
    lf.check_path("/home/x/cotcodec-runs/stage0/am1-study/runs/main/1411/am1")


# --------------------------------------------------------------------------- toy run directory


def _memory(i: int, rank: int) -> dict:
    return {"text": f"memory {i}", "date": "2023/05/01", "bm25_rank": rank, "is_gold": i == 0}


def _toy_artifact(questions: int = 2) -> dict:
    qs = []
    for q in range(questions):
        pools = {
            "retrieved": [_memory(i, (i * 3 + q) % 8) for i in range(8)],
            "gold": [_memory(i, 10 * i + q) for i in range(8)],
        }
        placebos = {
            arm: {
                "swaps": [[{"text": f"swap {i} {v}"} for v in range(2)] for i in range(8)],
                "reorders": [list(range(8))[::-1], [1, 0, 3, 2, 5, 4, 7, 6]],
            }
            for arm in pools
        }
        qs.append({
            "question_id": f"q{q}",
            "question_type": "multi-session",
            "question": f"question {q}?",
            "question_date": "2023/06/01",
            "answer": "blue",
            "pools": pools,
            "placebos": placebos,
        })  # fmt: skip
    return {"questions": qs}


def _reply(q: int, arm: str, request: dict) -> str:
    """A deterministic toy reply: right when memories 0 and 1 are both kept (retrieved) or when
    memory 0 is kept (gold); otherwise an abstention or a wrong answer."""

    if request["kind"] != "table":
        return "It is blue."
    mask = int(request["mask"])
    need = 0b11 if arm == "retrieved" else 0b1
    if mask & need == need:
        return "It is blue." if (mask >> 5) & 1 else "Blue."
    return "I don't know." if mask % 3 else f"It is red {q}."


def _write_pass(directory: Path, rows: dict[int, tuple[list[int], list[float], str, str]]) -> None:
    import numpy as np

    directory.mkdir(parents=True, exist_ok=True)
    indices = sorted(rows)
    offsets, tokens, logps, finishes = [0], [], [], []
    for i in indices:
        t, lp, finish, _ = rows[i]
        tokens += t
        logps += lp
        offsets.append(len(tokens))
        finishes.append(finish)
    np.savez_compressed(
        directory / "all.npz",
        request_index=np.asarray(indices, dtype=np.int32),
        offsets=np.asarray(offsets, dtype=np.int64),
        token_ids=np.asarray(tokens, dtype=np.int32),
        logprobs=np.asarray(logps, dtype=np.float32),
        num_cached=np.zeros(len(indices), dtype=np.int32),
    )
    (directory / "all.json").write_text(json.dumps({"finish_reasons": finishes}))
    with gzip.open(directory / "all.texts.jsonl.gz", "wt", encoding="utf-8") as handle:
        for i in indices:
            handle.write(json.dumps({"request_index": i, "text": rows[i][3]}) + "\n")


def _toy_run(tmp_path: Path, flip_item: int | None = None) -> tuple[Path, dict, list[dict]]:
    artifact = _toy_artifact()
    requests = ms.request_table(artifact, ["retrieved", "gold"])
    reader_rows = {}
    replies = {}
    for r in requests:
        text = _reply(r["question_index"], r["arm"], r)
        n = 2 + len(text) % 3
        tokens = [100 + j for j in range(n - 1)] + [151645]
        logps = [-0.1 * (1 + (r["index"] + j) % 5) for j in range(n)]
        reader_rows[r["index"]] = (tokens, logps, "stop", text)
        replies[r["index"]] = text
    run = tmp_path / "run"
    _write_pass(run / "sessions" / "reader-gpu0", reader_rows)
    items = ms.judge_item_table(artifact, replies, requests, [])
    (run / "judge-items.json").write_text(json.dumps(items))
    judge_rows = {}
    for item in items:
        label = "yes" if "blue" in item["response"].lower() else "no"
        if item["index"] == flip_item:
            label = "no" if label == "yes" else "yes"
        judge_rows[item["index"]] = ([7], [-0.01], "stop", label)
    _write_pass(run / "sessions" / "judge32-gpu0", judge_rows)
    return run, artifact, requests


def _expected_tables(artifact: dict) -> list[dict]:
    tables = []
    for q, question in enumerate(artifact["questions"]):
        for arm in ("retrieved", "gold"):
            values = []
            replies = set()
            for mask in range(256):
                text = _reply(q, arm, {"kind": "table", "mask": mask})
                values.append(1.0 if "blue" in text.lower() else 0.0)
                replies.add(text)
            tables.append({
                "question_id": question["question_id"],
                "arm": arm,
                "values_hex": cc.encode_values(values),
                "distinct_replies": len(replies),
            })  # fmt: skip
    return tables


def test_join_matches_the_harness_join_and_reproduces_the_tables(tmp_path):
    run, artifact, requests = _toy_run(tmp_path)
    config = {"pools": {"arms": ["retrieved", "gold"]}}
    rows_ma, items, primary, _ = ma.join_rows(run, config, artifact)
    reader = driver.load_pass(run / "sessions" / "reader-gpu0", "all")
    rows = lf.join_requests(requests, reader["rows"], items, primary)
    assert len(rows) == len(rows_ma) == len(requests)
    for a, b in zip(rows, rows_ma, strict=True):
        assert (a["index"], a["reply"], a["u"]) == (b["index"], b["reply"], b["u"])
        assert a["tokens"] == reader["rows"][a["index"]]["tokens"]
    views = ma.pool_views(rows_ma, artifact)
    index = {q["question_id"]: i for i, q in enumerate(artifact["questions"])}
    report = lf.validate_tables(views, _expected_tables(artifact), index)
    assert report["passed"] and report["values_hex_reproduced"] == 4
    assert report["distinct_replies_reproduced"] == 4


def test_one_flipped_label_stops_the_validation(tmp_path):
    artifact = _toy_artifact()
    requests = ms.request_table(artifact, ["retrieved", "gold"])
    replies = {r["index"]: _reply(r["question_index"], r["arm"], r) for r in requests}
    items = ms.judge_item_table(artifact, replies, requests, [])
    target = next(i["index"] for i in items if i["response"] == "Blue.")
    run, artifact, _ = _toy_run(tmp_path, flip_item=target)
    rows_ma, _, _, _ = ma.join_rows(run, {"pools": {"arms": ["retrieved", "gold"]}}, artifact)
    views = ma.pool_views(rows_ma, artifact)
    index = {q["question_id"]: i for i, q in enumerate(artifact["questions"])}
    with pytest.raises(lf.LabelFreeError, match="do not reproduce values_hex"):
        lf.validate_tables(views, _expected_tables(artifact), index)


def test_a_missing_reply_stops_the_validation(tmp_path):
    run, artifact, requests = _toy_run(tmp_path)
    rows_ma, items, primary, _ = ma.join_rows(
        run, {"pools": {"arms": ["retrieved", "gold"]}}, artifact
    )
    reader = driver.load_pass(run / "sessions" / "reader-gpu0", "all")
    reader["rows"][5]["finish"] = "not-finished"
    rows = lf.join_requests(requests, reader["rows"], items, primary)
    views = ma.pool_views(rows, artifact)
    index = {q["question_id"]: i for i, q in enumerate(artifact["questions"])}
    with pytest.raises(lf.LabelFreeError, match="incomplete"):
        lf.validate_tables(views, _expected_tables(artifact), index)


def test_features_from_the_toy_run(tmp_path):
    run, artifact, requests = _toy_run(tmp_path)
    rows_ma, items, primary, _ = ma.join_rows(
        run, {"pools": {"arms": ["retrieved", "gold"]}}, artifact
    )
    reader = driver.load_pass(run / "sessions" / "reader-gpu0", "all")
    rows = lf.join_requests(requests, reader["rows"], items, primary)
    features = lf.build_features(rows, artifact, 151645)
    assert len(features) == 4
    for pool in features:
        assert all(pool["eot"])
        for m in range(256):
            text = _reply(int(pool["question_id"][1:]), pool["arm"], {"kind": "table", "mask": m})
            assert pool["abstain"][m] == (text == "I don't know.")
            assert pool["u"][m] == int("blue" in text.lower())
            same = mc.normalize_answer(text) == mc.normalize_answer(_reply(0, pool["arm"], {
                "kind": "table", "mask": FULL}))  # fmt: skip
            assert (pool["cls"][m] == pool["cls"][FULL]) == same
        assert pool["mean_lp"][3] == pytest.approx(pool["sum_lp"][3] / pool["n_tokens"][3])
    # "It is blue." and "Blue." are different normalized replies
    assert features[0]["classes"] == len({mc.normalize_answer(r) for r in [
        "It is blue.", "Blue.", "I don't know.", "It is red 0."]})  # fmt: skip


def test_logprob_summary_rejects_nan():
    import numpy as np

    bits = np.asarray([-0.5, float("nan")], dtype="<f4").tobytes()
    with pytest.raises(lf.LabelFreeError):
        lf.logprob_summary([1, 2], bits)
    ok = np.asarray([-0.5, -0.25], dtype="<f4").tobytes()
    assert lf.logprob_summary([1, 2], ok) == (2, -0.75, -0.375)


# --------------------------------------------------------------------------- search on toy pools


def _toy_pool(values, ranks=None, mean_lp=None, cls=None, abstain=None, qid="t", arm="retrieved"):
    n = len(values)
    mean_lp = mean_lp or [0.0] * n
    return {
        "question_id": qid,
        "question_type": "toy",
        "arm": arm,
        "bm25_rank": ranks or list(range(8)),
        "u": [int(v) for v in values],
        "mean_lp": mean_lp,
        "sum_lp": [3 * x for x in mean_lp],
        "cls": cls or [0] * n,
        "abstain": abstain or [False] * n,
    }


UTIL = {u.name: u for u in lf.UTILITIES}


def test_draw_order_is_a_seeded_permutation_of_the_70_sets():
    a = lf.draw_order("q", "retrieved", 42)
    assert sorted(a) == sorted(lf.FOUR_SETS) and len(set(a)) == 70
    assert a == lf.draw_order("q", "retrieved", 42)
    assert a != lf.draw_order("q", "retrieved", 43)
    assert a != lf.draw_order("q", "gold", 42)
    assert all(mc.popcount(m) == 4 for m in a)


def test_ties_go_to_the_lower_bm25_rank_sum():
    ranks = [5, 0, 7, 1, 6, 2, 4, 3]
    pool = _toy_pool([0.0] * 256, ranks=ranks)
    for name in lf.UTILITY_NAMES:
        assert lf.select(pool, list(lf.FOUR_SETS), UTIL[name]) == lf.bm25_top_mask(ranks)
    # equal rank sums ({0,1,2,7} and {0,1,3,6} both sum 10): the smaller sorted ranks win
    ranks = list(range(8))
    pool = _toy_pool([0.0] * 256, ranks=ranks)
    a = 0b10000111  # ranks 0, 1, 2, 7
    b = 0b01001011  # ranks 0, 1, 3, 6
    assert lf.select(pool, [b, a], UTIL["conf_mean"]) == a
    assert lf.select(pool, [a, b], UTIL["conf_mean"]) == a


def test_confidence_and_nonabstention():
    mean_lp = [0.0] * 256
    abstain = [False] * 256
    hi, lo = 0b00001111, 0b11110000
    mean_lp[hi], abstain[hi] = -0.1, True
    mean_lp[lo] = -0.5
    pool = _toy_pool([0.0] * 256, mean_lp=mean_lp, abstain=abstain)
    queried = [hi, lo]
    assert lf.select(pool, queried, UTIL["conf_mean"]) == hi
    assert lf.select(pool, queried, UTIL["conf_sum"]) == hi
    assert lf.select(pool, queried, UTIL["nonabstain"]) == lo
    assert lf.select(pool, queried, UTIL["nonabstain_conf_mean"]) == lo


def test_vote_prefers_the_majority_then_confidence():
    sets = list(lf.FOUR_SETS[:5])
    cls = [9] * 256
    mean_lp = [0.0] * 256
    for m, c, lp in zip(sets, [0, 0, 1, 1, 1], [-0.1, -0.2, -0.9, -0.3, -0.5], strict=True):
        cls[m], mean_lp[m] = c, lp
    pool = _toy_pool([0.0] * 256, cls=cls, mean_lp=mean_lp)
    assert lf.select(pool, sets, UTIL["vote"]) == sets[3]
    # equal counts: the more confident reply wins
    assert lf.select(pool, sets[:4], UTIL["vote"]) == sets[0]
    # non-abstention first: an abstaining majority loses to a non-abstaining minority
    abstain = [False] * 256
    for m in sets[2:]:
        abstain[m] = True
    pool["abstain"] = abstain
    assert lf.select(pool, sets, UTIL["nonabstain_vote"]) == sets[0]


def test_agreement_with_the_full_pool_costs_one_more_call():
    cls = [1] * 256
    cls[FULL] = 0
    agree = 0b11000011
    cls[agree] = 0
    pool = _toy_pool([0.0] * 256, cls=cls)
    assert lf.select(pool, list(lf.FOUR_SETS), UTIL["agree_full"]) == agree
    assert lf.row_calls("agree_full@8") == 9 and lf.row_calls("conf_mean@8") == 8
    assert lf.row_calls("oracle_search@70") == 70
    assert lf.row_calls("bm25_top4") == lf.row_calls("all_8") == lf.row_calls("random_4") == 1


def test_table_results_on_a_toy_table():
    """u(S) = 1 iff memory 0 is kept, and confidence is higher exactly then: confidence search
    is right iff some queried set holds memory 0; at m = 70 it is exact."""

    values = [float(m & 1) for m in range(256)]
    mean_lp = [-0.1 if m & 1 else -1.0 for m in range(256)]
    ranks = [7, 0, 1, 2, 3, 4, 5, 6]  # BM25's top 4 leaves memory 0 out
    pool = _toy_pool(values, ranks=ranks, mean_lp=mean_lp, qid="toy")
    seeds = list(range(42, 52))
    result = lf.table_results(pool, values, seeds)
    rows = result["rows"]
    assert result["opt4"] == 1.0 and result["nonconstant"]
    assert rows["bm25_top4"]["u"] == 0.0 and rows["all_8"]["u"] == 1.0
    assert rows["random_4"]["u"] == pytest.approx(0.5)
    for m in lf.SEARCH_CALLS:
        expected = [
            int(any(s & 1 for s in lf.draw_order("toy", "retrieved", seed)[:m])) for seed in seeds
        ]
        assert rows[f"conf_mean@{m}"]["u_by_seed"] == "".join(map(str, expected))
        assert rows[f"conf_mean@{m}"]["regret"] == pytest.approx(1 - sum(expected) / len(seeds))
        direct = cc.direct_search_curve(values, 4)[m - 1]
        assert rows[f"oracle_search@{m}"]["u"] == pytest.approx(1 - direct)
    assert rows["conf_mean@70"]["u"] == 1.0 and rows["conf_mean@70"]["mask"] & 1
    # every utility that cannot see u ties everywhere and falls back to the BM25 order
    assert rows["nonabstain@70"]["mask"] == lf.bm25_top_mask(ranks)


def test_table_results_refuses_features_that_differ_from_the_table():
    values = [float(m & 1) for m in range(256)]
    pool = _toy_pool(values)
    other = list(values)
    other[FULL] = 0.0
    with pytest.raises(lf.LabelFreeError):
        lf.table_results(pool, other, [42])


def test_regret_is_the_harness_keep_set_regret():
    rng = random.Random(7)
    values = [float(rng.random() < 0.3) for _ in range(256)]
    opt = mc.best_keep_sets(values, 4)[0]
    for s in lf.FOUR_SETS:
        assert opt - values[s] == cc.set_regret(values, s, 4)


def test_bm25_top4_is_am1b_retrieval_rank_on_the_dev_tables():
    tables = cc.load_tables(ROOT / cc.DEV_TABLES, cc.DEV_TABLES_SHA256)
    am1b = json.loads(gzip.decompress(
        (ROOT / "program/evidence/2026-10-15/am1b-cost-curve/per-table.json.gz").read_bytes()
    ))  # fmt: skip
    am1b_regret = {(p["question_id"], p["arm"]): p["rules"]["retrieval_rank"]["4"]["regret"]
                   for p in am1b}  # fmt: skip
    checked = 0
    for t in tables:
        values = cc.decode_values(t["values_hex"])
        credit = [float(x) for x in t["credits"]["retrieval_rank"]]
        ranks = [int(-c) for c in credit]
        mask = lf.bm25_top_mask(ranks)
        r = mc.keep_set_regret_range(values, credit, 4)
        assert r["sets"] == 1 and r["mean"] == mc.best_keep_sets(values, 4)[0] - values[mask]
        if (t["question_id"], t["arm"]) in am1b_regret:
            assert am1b_regret[(t["question_id"], t["arm"])] == r["mean"]
            checked += 1
    assert checked == 89


def test_bm25_ordered_stop_rule_reaches_the_nonabstain_choice():
    ranks = [5, 0, 7, 1, 6, 2, 4, 3]
    order = sorted(lf.FOUR_SETS, key=lambda m: lf.rank_key(m, ranks), reverse=True)
    assert order[0] == lf.bm25_top_mask(ranks)
    abstain = [False] * 256
    for m in order[:11]:
        abstain[m] = True
    values = [0.0] * 256
    values[order[11]] = 1.0
    pool = _toy_pool(values, ranks=ranks, abstain=abstain)
    out = lf.bm25_ordered_nonabstain(pool, values)
    assert out["first_answer_position"] == 12
    rows = out["rows"]
    assert rows["bm25_ordered_nonabstain@8"] == {"u": 0.0, "calls": 8}
    assert rows["bm25_ordered_nonabstain@16"] == {"u": 1.0, "calls": 12}
    assert lf.select(pool, list(lf.FOUR_SETS), UTIL["nonabstain"]) == order[11]
    # nothing answers: BM25 top 4 after reading m subsets
    pool["abstain"] = [True] * 256
    out = lf.bm25_ordered_nonabstain(pool, values)
    assert out["first_answer_position"] is None
    assert out["rows"]["bm25_ordered_nonabstain@26"] == {"u": 0.0, "calls": 26}


def test_auroc_among_nonabstaining_ignores_abstentions():
    values = [0.0] * 256
    mean_lp = [-1.0] * 256
    abstain = [False] * 256
    sets = list(lf.FOUR_SETS)
    for m in sets[:10]:
        abstain[m], mean_lp[m] = True, -0.01  # confident abstentions
    for m in sets[10:20]:
        values[m], mean_lp[m] = 1.0, -0.5
    pool = _toy_pool(values, mean_lp=mean_lp, abstain=abstain)
    out = lf.auroc_among_nonabstaining(pool)
    assert out["conf_mean"] == 1.0
    assert lf.within_table_auroc(pool)["conf_mean"] < 1.0


def test_crossfit_picks_a_dominant_candidate():
    per_table = []
    for q in range(10):
        per_table.append({
            "question_id": f"q{q}",
            "arm": "retrieved",
            "nonconstant": True,
            "rows": {"bm25_top4": {"u": 0.0}, "a@8": {"u": 0.0}, "b@8": {"u": 1.0}},
        })  # fmt: skip
    cf = lf.crossfit_selection(per_table, "retrieved", ["a@8", "b@8"], 20, 42)
    assert cf["chosen"] == {"b@8": 40}
    assert cf["held_out_gain_mean"] == 1.0


# --------------------------------------------------------------------------- end to end


def _synthetic(questions: int = 6, seed: int = 3) -> tuple[dict, list[dict]]:
    rng = random.Random(seed)
    pools, tables = [], []
    for q in range(questions):
        for arm in lf.ARMS:
            constant = q == 0
            values = [0.0 if constant else float(rng.random() < 0.4) for _ in range(256)]
            values[0] = 0.0
            cls = [rng.randrange(4) for _ in range(256)]
            pool = _toy_pool(
                values,
                ranks=rng.sample(range(20), 8),
                mean_lp=[round(rng.uniform(-2, 0), 6) for _ in range(256)],
                cls=cls,
                abstain=[c == 3 for c in cls],
                qid=f"q{q}",
                arm=arm,
            )
            pool.update(
                n_tokens=[3] * 256, finish=["stop"] * 256, eot=[True] * 256,
                pattern=["i_dont_know" if c == 3 else None for c in cls],
            )  # fmt: skip
            pools.append(pool)
            tables.append({
                "question_id": f"q{q}",
                "arm": arm,
                "values_hex": cc.encode_values(values),
                "summary": {"constant": len(set(values)) == 1},
            })  # fmt: skip
    features = {"pass": {"name": "synthetic"}, "validation": {"passed": True}, "pools": pools}
    return features, tables


def test_analyze_end_to_end_is_deterministic():
    features, tables = _synthetic()
    eager = {
        "pass": {"name": "synthetic eager"},
        "comparison": {},
        "pools": copy.deepcopy([p for p in features["pools"] if p["question_id"] in ("q1", "q2")]),
    }
    outs = []
    for _ in range(2):
        results, per_table = lf.analyze(
            copy.deepcopy(features), tables, copy.deepcopy(eager), 5, 42, 200, 42, 10
        )
        outs.append((lf.canonical(results), lf.canonical(per_table), lf.render_markdown(results)))
    assert outs[0] == outs[1]
    cells = results["aggregate"]["retrieved"]["nonconstant"]
    assert cells["bm25_top4"]["tables"] == 5
    assert results["aggregate"]["retrieved"]["all"]["bm25_top4"]["tables"] == 6
    assert cells["bm25_top4"]["minus_bm25_top4"]["mean"] == 0.0
    assert cells["all_8"]["minus_all_8"]["mean"] == 0.0
    assert cells["oracle_search@70"]["regret"]["mean"] == 0.0
    for name in lf.UTILITY_NAMES:
        assert cells[f"{name}@70"]["seed_mc_se"] == 0.0
        assert cells[f"{name}@8"]["regret"]["mean"] >= 0.0
    # the eager rows on identical pools equal the compiled rows on those pools
    e = results["eager_sensitivity"]["rules"]["retrieved"]["rows"]
    for name in lf.row_names():
        assert e[name]["compiled"] == e[name]["eager"]
    assert "| conf_mean@70 |" in outs[0][2]
