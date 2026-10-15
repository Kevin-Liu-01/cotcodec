"""Tests for the AM1 study (memcredit-study-v1): config, split, placebo arms, request table,
the judge's official prompt and label rule, estimators, structure census, statistics, the GPU
driver's pure helpers and the lane's name rules."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import math
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from harness import memcredit as mc  # noqa: E402
from harness import memcredit_study as ms  # noqa: E402


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


prepare = _load("memcredit_study_prepare")
driver = _load("memcredit_study")


# --------------------------------------------------------------------------- synthetic data


def _record(qid: str, qtype: str, sessions, answer: str = "blue", question: str = "my car color"):
    start = datetime(2023, 1, 1, 10, 0)
    dates = [(start + timedelta(days=i)).strftime(mc.DATE_FORMAT) for i in range(len(sessions))]
    return {
        "question_id": qid,
        "question_type": qtype,
        "question": f"What is {question}?",
        "answer": answer,
        "question_date": "2023/09/01 (Fri) 10:00",
        "haystack_dates": dates,
        "haystack_session_ids": [f"{qid}-s{i}" for i in range(len(sessions))],
        "haystack_sessions": [
            [{"role": r, "content": c, "has_answer": g} for r, c, g in session]
            for session in sessions
        ],
        "answer_session_ids": [],
    }


def _haystack(n: int, gold: dict[int, str]) -> list:
    sessions = []
    for i in range(n):
        text = gold.get(i, f"filler turn {i} about gardening walks and " + "x" * (i % 7) * 9)
        sessions.append([("user", text, i in gold), ("assistant", f"reply {i}", False)])
    return sessions


def _records() -> list[dict]:
    out = []
    types = ["temporal-reasoning", "multi-session", "knowledge-update", "single-session-user"]
    for t, qtype in enumerate(types):
        for j in range(7):
            gold = (
                {3: "my car color is blue", 9: "I painted my car blue again"}
                if j % 2
                else {5: "my car color is blue now"}
            )
            out.append(_record(f"q{t}{j}", qtype, _haystack(24, gold)))
    out.append(_record("q_abs_abs", "multi-session", _haystack(24, {2: "x car"})))
    bad = _record("qbad", "single-session-user", _haystack(24, {}))
    out.append(bad)
    return out


@pytest.fixture(scope="module")
def config() -> dict:
    return ms.load_config()


@pytest.fixture(scope="module")
def artifact(config: dict) -> dict:
    records = _records()
    split = ms.make_split(records, config)
    return prepare.build_artifact(records, config, split, "development")


# --------------------------------------------------------------------------- config and split


def test_config_loads_and_refuses_bad_seeds(config: dict, tmp_path: Path) -> None:
    assert config["experiment_id"] == ms.EXPERIMENT_ID and config["seeds"] == [42, 43, 44]
    text = ms.CONFIG_PATH.read_text().replace("reorder_seed: 43", "reorder_seed: 7")
    bad = tmp_path / "c.yaml"
    bad.write_text(text)
    with pytest.raises(ms.StudyError):
        ms.load_config(bad)


def test_split_is_deterministic_stratified_and_disjoint(config: dict) -> None:
    records = _records()
    a = ms.make_split(records, config)
    b = ms.make_split(list(reversed(records)), config)
    assert a["development"] == b["development"] and a["heldout"] == b["heldout"]
    assert not set(a["development"]) & set(a["heldout"])
    assert a["counts"]["usable"] == 28
    assert a["reasons"]["abstention"] == 1 and a["reasons"]["no gold turn"] == 1
    for qtype, row in a["per_type"].items():
        assert row["development"] == ms.round_half_up(0.15 * row["usable"]), qtype
    assert ms.round_half_up(0.5) == 1 and ms.round_half_up(4.5) == 5 and ms.round_half_up(0.75) == 1


def test_load_split_checks_digests(config: dict, tmp_path: Path) -> None:
    split = ms.make_split(_records(), config)
    path = tmp_path / "split.json"
    path.write_text(json.dumps(split))
    assert ms.load_split(path, config)["counts"] == split["counts"]
    split["heldout"] = split["heldout"][1:]
    path.write_text(json.dumps(split))
    with pytest.raises(ms.StudyError):
        ms.load_split(path, config)


def test_heldout_needs_a_frozen_registration(tmp_path: Path) -> None:
    reg = tmp_path / "r.md"
    reg.write_text("draft")
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text(json.dumps({"experiment_id": "other", "sha256": ms.sha256_file(reg)}) + "\n")
    assert not ms.registration_frozen(ledger, reg)
    ledger.write_text(json.dumps({"experiment_id": ms.REGISTRATION_ID,
                                  "sha256": ms.sha256_file(reg)}) + "\n")  # fmt: skip
    assert ms.registration_frozen(ledger, reg)
    reg.write_text("edited")
    assert not ms.registration_frozen(ledger, reg)


def test_the_committed_split_matches_the_config(config: dict) -> None:
    path = ROOT / config["split"]["path"]
    if not path.is_file():
        pytest.skip("split file not written yet")
    split = ms.load_split(path, config)
    assert split["counts"]["usable"] == 416
    assert split["census_check"]["usable_equals_census_eligible"] is True
    assert split["seed"] == 42 and split["development_fraction"] == 0.15


# --------------------------------------------------------------------------- pools and placebos


def test_artifact_pools_and_placebos(artifact: dict, config: dict) -> None:
    assert artifact["split"] == "development"
    for q in artifact["questions"]:
        for arm, pool in q["pools"].items():
            assert len(pool) == 8
            keys = {(m["session_index"], m["turn_index"]) for m in pool}
            placebo = q["placebos"][arm]
            assert len(placebo["swaps"]) == 8 and all(len(s) == 2 for s in placebo["swaps"])
            all_pool_keys = {(m["session_index"], m["turn_index"])
                             for p in q["pools"].values() for m in p}  # fmt: skip
            for slot in placebo["swaps"]:
                for s in slot:
                    assert (s["session_index"], s["turn_index"]) not in all_pool_keys
                    assert not any(s["text"] == m["text"] for m in pool)
                assert slot[0]["text"] != slot[1]["text"]
            assert sorted(placebo["reorders"][0]) == list(range(8))
            assert placebo["reorders"][0] == list(range(8))[::-1]
            assert placebo["reorders"][1] not in (list(range(8)), list(range(8))[::-1])
            assert keys


def test_match_swaps_prefers_length_then_rank() -> None:
    memory = {"text": "a" * 100, "bm25_rank": 5}
    cands = [
        {"text": "b" * 300, "bm25_rank": 5, "session_index": 0, "turn_index": 0},
        {"text": "c" * 110, "bm25_rank": 20, "session_index": 1, "turn_index": 0},
        {"text": "d" * 95, "bm25_rank": 9, "session_index": 2, "turn_index": 0},
        {"text": "e" * 120, "bm25_rank": 6, "session_index": 3, "turn_index": 0},
    ]
    chosen, tol = ms.match_swaps(memory, cands, 2, [math.log(1.25), math.log(1.5)])
    assert tol == pytest.approx(math.log(1.25))
    assert [c["text"][0] for c in chosen] == ["e", "d"]
    chosen, tol = ms.match_swaps(memory, cands[:2], 2, [math.log(1.25)])
    assert tol is None and [c["text"][0] for c in chosen] == ["b", "c"]


def test_request_table_and_messages(artifact: dict, config: dict) -> None:
    requests = ms.request_table(artifact, config["pools"]["arms"])
    per_pool = 256 + 16 + 2
    assert len(requests) == len(artifact["questions"]) * 2 * per_pool
    assert [r["index"] for r in requests] == list(range(len(requests)))
    q = artifact["questions"][0]
    swap = next(r for r in requests if r["kind"] == "swap" and r["slot"] == 3 and r["variant"] == 1)
    memories = ms.request_memories(artifact, swap)
    assert memories[3]["text"] == q["placebos"][swap["arm"]]["swaps"][3][1]["text"]
    assert memories[3]["date"] == q["pools"][swap["arm"]][3]["date"]
    assert [m["text"] for i, m in enumerate(memories) if i != 3] == [
        m["text"] for i, m in enumerate(q["pools"][swap["arm"]]) if i != 3
    ]
    reorder = next(r for r in requests if r["kind"] == "reorder" and r["variant"] == 0)
    texts = [m["text"] for m in ms.request_memories(artifact, reorder)]
    assert texts == [m["text"] for m in q["pools"][reorder["arm"]]][::-1]
    full = next(r for r in requests if r["kind"] == "table" and r["mask"] == 255)
    message = ms.request_message(artifact, full, config["prompt"])
    for m in q["pools"][full["arm"]]:
        assert ms.memory_line(m) in message
    empty = next(r for r in requests if r["kind"] == "table" and r["mask"] == 0)
    assert config["prompt"]["no_memories"] in ms.request_message(artifact, empty, config["prompt"])


def test_public_summary_has_no_text(artifact: dict) -> None:
    summary = prepare.public_summary(artifact, "0" * 64)
    blob = json.dumps(summary)
    for q in artifact["questions"]:
        for pool in q["pools"].values():
            for m in pool:
                assert m["text"] not in blob
    assert "filler turn" not in blob and "car color" not in blob


# --------------------------------------------------------------------------- judge


def _legacy_prompt_function():
    source = (ROOT / "legacy/harness/memory_trials/longmemeval_judge.py").read_text()
    tree = ast.parse(source)
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                and n.name == "official_answer_check_prompt")  # fmt: skip
    namespace: dict = {"LongMemEvalJudgeError": ValueError}
    exec(compile(ast.Module(body=[node], type_ignores=[]), "legacy", "exec"), namespace)  # noqa: S102
    return namespace["official_answer_check_prompt"]


@pytest.mark.parametrize("qtype", sorted(ms.JUDGE_TEMPLATES))
def test_judge_prompt_is_the_archived_official_port(qtype: str) -> None:
    legacy = _legacy_prompt_function()
    args = ("Q? {x}", "A {0}", "R }")
    assert ms.judge_prompt(qtype, *args) == legacy(qtype, *args, abstention=False)


def test_parse_judgment_official_rule() -> None:
    assert ms.parse_judgment("yes") == (1, True)
    assert ms.parse_judgment("No.") == (0, True)
    assert ms.parse_judgment("Yes, because") == (1, False)
    assert ms.parse_judgment("no, not yesterday") == (1, False)  # official substring rule


def test_validation_items_and_judge_table(artifact: dict, config: dict) -> None:
    validation = ms.validation_items(artifact, config["judge"]["validation"])
    n = len(artifact["questions"])
    assert sum(v["source"] == "validation:reference" for v in validation) == n
    assert sum(v["source"] == "validation:idk" for v in validation) == n
    for v in validation:
        if v["source"] == "validation:other-answer":
            assert (
                v["other_question_id"] != artifact["questions"][v["question_index"]]["question_id"]
            )
    requests = ms.request_table(artifact, config["pools"]["arms"])
    replies = {r["index"]: (" blue " if r["index"] % 2 else "I don't know.") for r in requests}
    items = ms.judge_item_table(artifact, replies, requests, validation)
    reader = [i for i in items if i["source"] == "reader"]
    assert len(reader) == 2 * n
    assert [i["index"] for i in items] == list(range(len(items)))
    assert ms.judge_message(artifact, reader[0]).startswith("I will give you a question")


# --------------------------------------------------------------------------- estimators


def _table(fn, k: int = 8) -> list[float]:
    return [float(fn(m)) for m in range(1 << k)]


def test_banzhaf_leave_one_in_and_permutation_shapley() -> None:
    and2 = _table(lambda m: (m & 0b11) == 0b11)
    assert ms.banzhaf(and2)[:2] == [0.5, 0.5] and ms.banzhaf(and2)[2:] == [0.0] * 6
    assert ms.leave_one_in(and2) == [0.0] * 8
    or2 = _table(lambda m: bool(m & 0b11))
    assert ms.leave_one_in(or2)[:2] == [1.0, 1.0]
    phi, seen = ms.permutation_shapley(and2, 4000, random.Random(42))
    assert phi[0] == pytest.approx(0.5, abs=0.03) and abs(phi[5]) < 1e-12
    assert seen <= 256
    exact = mc.shapley(and2)
    assert sum(exact) == pytest.approx(and2[-1] - and2[0])


def test_snipw_matches_banzhaf_in_the_limit() -> None:
    fn = _table(lambda m: (m & 1) and not (m & 4))
    credit, distinct = ms.snipw(fn, 20000, random.Random(43))
    assert credit[0] == pytest.approx(ms.banzhaf(fn)[0], abs=0.03)
    assert credit[2] == pytest.approx(ms.banzhaf(fn)[2], abs=0.03)
    assert distinct == 256


def test_random_regret_and_structure_classes() -> None:
    single = _table(lambda m: m & 1)
    assert ms.structure_class(single) == "single"
    assert ms.structure_class(_table(lambda m: (m & 3) == 3)) == "and"
    assert ms.structure_class(_table(lambda m: bool(m & 3))) == "or"
    assert ms.structure_class(_table(lambda m: bool(m & 1) or (m & 6) == 6)) == "monotone-mixed"
    assert ms.structure_class(_table(lambda m: not m & 8)) == "negative"
    assert ms.structure_class(_table(lambda m: bool(m & 1) and not m & 8)) == "non-monotone"
    assert ms.structure_class(_table(lambda m: 0)) == "constant-0"
    # B = 1 on a single-memory table: 7 of 8 singletons miss.
    assert ms.random_regret(single, 1) == pytest.approx(7 / 8)
    summary = ms.table_summary(_table(lambda m: (m & 3) == 3), 0b11)
    assert summary["relevant_gold"] == [0, 1] and summary["relevant_nongold"] == []
    assert summary["fourier_share_order_2_plus"] == pytest.approx(1 / 3)
    assert summary["and_or_baseline"] == pytest.approx(1 / 3)
    assert summary["best_by_budget"][1] == 0.0 and summary["best_by_budget"][2] == 1.0


def test_loo_fails_under_redundancy_and_regret_ranges() -> None:
    # Two redundant gold memories and a distractor that hurts: LOO gives the gold 0.
    fn = _table(lambda m: bool(m & 3) and not m & 4)
    loo = mc.loo_credit(fn)
    assert loo[0] == 0.0 and loo[1] == 0.0 and loo[2] == -1.0
    regret = mc.keep_set_regret_range(fn, loo, 1)
    assert regret["max"] == 1.0
    assert mc.keep_set_regret_range(fn, mc.shapley(fn), 1)["max"] == 0.0


# --------------------------------------------------------------------------- statistics


def test_kappa_auroc_spearman_bootstrap() -> None:
    assert ms.cohen_kappa([1, 0, 1, 0], [1, 0, 1, 0]) == pytest.approx(1.0)
    assert ms.cohen_kappa([1, 1, 0, 0], [1, 0, 1, 0]) == pytest.approx(0.0)
    assert ms.auroc([0.9, 0.8, 0.1, 0.2], [1, 1, 0, 0]) == 1.0
    assert ms.auroc([0.5, 0.5], [1, 0]) == 0.5
    assert ms.auroc([1.0], [1]) is None
    assert ms.spearman([1, 2, 3], [10, 20, 30]) == pytest.approx(1.0)
    assert ms.spearman([1, 1, 1], [1, 2, 3]) is None
    clusters = {"a": [1.0, 1.0], "b": [0.0], "c": [0.0, 1.0]}
    one = ms.cluster_bootstrap(clusters, 500, 42)
    two = ms.cluster_bootstrap(clusters, 500, 42)
    assert one == two and one["mean"] == pytest.approx(0.6) and one["clusters"] == 3
    assert one["ci"][0] <= one["mean"] <= one["ci"][1]


# --------------------------------------------------------------------------- driver helpers


def test_driver_refuses_heldout_artifacts(tmp_path: Path, artifact: dict) -> None:
    path = tmp_path / "a.json"
    path.write_text(json.dumps(dict(artifact, split="heldout")))
    with pytest.raises(ms.StudyError):
        driver.load_artifact(path, None)
    path.write_text(json.dumps(artifact))
    assert driver.load_artifact(path, None)["split"] == "development"


def test_driver_plan_env_and_orders(artifact: dict, config: dict, tmp_path: Path) -> None:
    plan = driver.build_plan(config, artifact)
    assert plan["by_kind"] == {"table": plan["pools"] * 256, "swap": plan["pools"] * 16,
                               "reorder": plan["pools"] * 2}  # fmt: skip
    reader = driver.worker_spec(config, "reader-gpu1")
    env = driver.worker_env({"VLLM_BATCH_INVARIANT": "0"}, tmp_path, reader)
    assert env["VLLM_BATCH_INVARIANT"] == "1" and env["CUDA_VISIBLE_DEVICES"] == "1"
    attention = driver.worker_spec(config, "attention-gpu1")
    assert "VLLM_BATCH_INVARIANT" not in driver.worker_env({}, tmp_path, attention)
    assert driver.order_indices(5, "canonical", 43) == [0, 1, 2, 3, 4]
    assert sorted(driver.order_indices(50, "shuffled", 43)) == list(range(50))
    kwargs = driver.engine_kwargs(config["judge"]["primary"], 42)
    assert kwargs["model"].endswith("qwen3-32b") and kwargs["trust_remote_code"] is False


def test_memory_token_spans() -> None:
    memories = [{"date": "d1", "text": "alpha beta"}, {"date": "d2", "text": "gamma"}]
    rendered = "<s>user\nMemories:\n- [d1] alpha beta\n- [d2] gamma\nQ?<e>"
    # one token per character
    offsets = [(i, i + 1) for i in range(len(rendered))]
    spans = driver.memory_token_spans(rendered, offsets, memories)
    a = rendered.find("- [d1]")
    assert spans[0] == (a, a + len("- [d1] alpha beta"))
    assert spans[1][0] > spans[0][1]
    with pytest.raises(ms.StudyError):
        driver.memory_token_spans("nothing", [(0, 7)], memories)


def test_lane_admits_the_study_commands() -> None:
    submit = _load("submit_docker_research_job")
    for command in (
        ["python", "scripts/memcredit_study.py", "run", "--seeds", "42", "43", "44",
         "--output-dir", "/outputs/am1", "--allocation-minutes", "40", "--evidence",
         "/inputs/study-artifact.json", "--expected-evidence-sha256", "a" * 64],
        ["python", "scripts/memcredit_study.py", "worker", "--worker", "judge32-gpu0"],
        ["python", "scripts/memcredit_analyze.py", "analyze"],
    ):  # fmt: skip
        assert all(submit.archived_memory_reference(arg) is None for arg in command), command


# --------------------------------------------------------------------------- analysis (synthetic)


analysis = _load("memcredit_analyze")
step0 = _load("memcredit_step0")


def _save(run: Path, worker: str, texts: list[str]) -> None:
    out = run / "sessions" / worker
    out.mkdir(parents=True, exist_ok=True)
    indices = list(range(len(texts)))
    ids = [f"{worker}/all/{i}" for i in indices]
    state = {}
    for ours, text in zip(ids, texts, strict=True):
        st = step0.new_state()
        st["token_ids"] = [7, len(text)]
        st["logp"] = [-0.5, -0.25]
        st["text"] = [text]
        st["finished"] = True
        st["finish_reason"] = "stop"
        st["num_cached_tokens"] = 0
        state[ours] = st
    record = {"session": worker, "name": "all", "requests": len(texts), "status": "complete",
              "info": {"wall_s": 1.0, "finished": len(texts), "unmatched": 0}}  # fmt: skip
    step0.save_pass(out, "all", indices, ids, state, [10] * len(texts), record)
    (out / "session.json").write_text(json.dumps({"gpu": {"uuid": worker}}))


def test_analysis_on_a_synthetic_run(tmp_path: Path, artifact: dict, config: dict) -> None:
    requests = ms.request_table(artifact, config["pools"]["arms"])
    replies = []
    for r in requests:
        memories = ms.request_memories(artifact, r)
        replies.append("Your car is blue." if any("blue" in m["text"] for m in memories)
                       else "I don't know.")  # fmt: skip
    _save(tmp_path, analysis.READER, replies)
    _save(tmp_path, analysis.READER_AA, replies)
    validation = ms.validation_items(artifact, config["judge"]["validation"])
    items = ms.judge_item_table(artifact, dict(enumerate(replies)), requests, validation)
    (tmp_path / "judge-items.json").write_text(json.dumps(items))
    verdicts = ["yes" if "blue" in i["response"] else "no" for i in items]
    for worker in (analysis.JUDGE, analysis.JUDGE_AA, analysis.JUDGE2):
        _save(tmp_path, worker, verdicts)
    out = tmp_path / "analysis"
    config = dict(
        config, analysis=dict(config["analysis"], bootstrap={"resamples": 200, "seed": 42})
    )
    result = analysis.analyze(tmp_path, config, artifact, out, None, tmp_path / "private")
    tables = json.loads((out / "tables.json").read_text())
    assert all(t["complete"] for t in tables)
    ident = result["headline"]["identity"]["reader_cross_gpu"]
    assert ident["identical_tokens"] == ident["n_common"] == len(requests)
    for t in tables:
        s = t["summary"]
        if t["arm"] == "gold":
            expected = "single" if s["gold_in_pool"] == 1 else "or"
            assert s["structure"] == expected, (t["question_id"], s["structure"])
        if s["structure"] == "or":
            # LOO gives two redundant gold memories 0: the B = 1 keep set is a coin toss.
            assert t["regret"]["loo"]["1"]["mean"] > 0
            assert t["regret"]["shapley_exact"]["1"]["mean"] == 0
        if not s["constant"]:
            assert t["regret"]["random"]["1"]["mean"] > 0
            assert set(t["regret"]) >= {"loo", "perm_shapley_16", "snipw_64", "swap_mean"}
            # deleting a gold memory and swapping it for filler agree here
            p = t["placebo"]
            assert p["reorder_ok"]
    judge = json.loads((out / "judge.json").read_text())
    assert judge["validation"]["validation:reference"]["primary"]["accuracy"] == 1.0
    assert judge["validation"]["validation:idk"]["primary"]["accuracy"] == 1.0
    h2 = json.loads((out / "h2.json").read_text())
    assert h2["gold"]["4"]["shapley_exact"]["mean_regret"]["mean"] == 0.0
    assert (out / "tables.md").read_text().startswith("# AM1 development pilot")
    blob = (out / "tables.json").read_text() + (out / "headline.json").read_text()
    assert "car is blue" not in blob and "filler turn" not in blob
    assert (tmp_path / "private" / "rows.jsonl.gz").is_file()
    sample = analysis.hand_sample(tmp_path, config, artifact)
    assert len(sample) == len({(i["question_index"], i["response"]) for i in items
                               if i["source"] == "reader"})  # fmt: skip
    assert all("label" not in s for s in sample)
    pw = analysis.power(
        out,
        dict(config, analysis=dict(config["analysis"], power={"simulations": 20, "seed": 43})),
        50,
    )
    assert pw["heldout_questions"] == 50 and pw["statistics"]


# --------------------------------------------------------------------------- A/A diagnostic config


def test_aa_config_and_phase_readers() -> None:
    aa = ms.load_config(ms.AA_CONFIG_PATH)
    assert aa["experiment_id"] == "memcredit-study-v1-aa"
    phases = {p["id"]: p for p in aa["job"]["phases"]}
    assert driver.phase_readers(phases["fresh"]) == []
    assert len(driver.phase_readers(phases["judge"])) == 6
    main = ms.load_config()
    main_phases = {p["id"]: p for p in main["job"]["phases"]}
    assert driver.phase_readers(main_phases["judge"]) == ["reader-gpu0"]
    assert driver.phase_readers(main_phases["extra"]) == ["reader-gpu0"]
    worker = driver.worker_spec(aa, "rd-eager-gpu1")
    assert driver.engine_kwargs(aa["reader"], 42, worker["enforce_eager"])["enforce_eager"]
    assert "enforce_eager" not in driver.engine_kwargs(aa["reader"], 42)


def test_aa_config_refuses_bad_cache_source(tmp_path: Path) -> None:
    text = ms.AA_CONFIG_PATH.read_text().replace("cache_from: rd-fresh-gpu0",
                                                 "cache_from: rd-later")  # fmt: skip
    bad = tmp_path / "aa.yaml"
    bad.write_text(text)
    with pytest.raises(ms.StudyError):
        ms.load_config(bad)


def test_copy_cache_and_union_judge_items(tmp_path: Path, artifact: dict, config: dict) -> None:
    (tmp_path / "cache" / "a" / "triton").mkdir(parents=True)
    (tmp_path / "cache" / "a" / "triton" / "k.bin").write_bytes(b"x" * 10)
    (tmp_path / "cache" / "a" / "rpc").mkdir()
    (tmp_path / "cache" / "a" / "rpc" / "sock").write_bytes(b"s")
    info = driver.copy_cache(tmp_path, "a", "b")
    assert info["files"] == 1 and (tmp_path / "cache" / "b" / "triton" / "k.bin").is_file()
    assert not (tmp_path / "cache" / "b" / "rpc").exists()
    with pytest.raises(ms.StudyError):
        driver.copy_cache(tmp_path, "a", "b")
    requests = ms.request_table(artifact, config["pools"]["arms"])
    _save(tmp_path, "r1", ["blue." if r["index"] % 3 else "no idea" for r in requests])
    _save(tmp_path, "r2", ["blue." if r["index"] % 3 else "other" for r in requests])
    items = driver.write_judge_items(config, artifact, tmp_path, ["r1", "r2"])
    reader = {(i["question_index"], i["response"]) for i in items if i["source"] == "reader"}
    n = len(artifact["questions"])
    assert len(reader) == 3 * n
    assert json.loads((tmp_path / "judge-items.json").read_text()) == items


def test_aa_report_counts_utility_flips(tmp_path: Path, artifact: dict, config: dict) -> None:
    requests = ms.request_table(artifact, config["pools"]["arms"])
    a = ["blue." if r["index"] % 2 else "I don't know." for r in requests]
    b = list(a)
    b[1] = "I don't know."  # one reply differs and flips its utility
    b[3] = "blue!!"  # one differs without a utility flip
    run = tmp_path / "run"
    _save(run, "ra", a)
    _save(run, "rb", b)
    items = driver.write_judge_items(config, artifact, run, ["ra", "rb"])
    _save(run, analysis.JUDGE, ["yes" if "blue" in i["response"] else "no" for i in items])
    report = analysis.aa_report({"x": run}, [("x:ra", "x:rb")], config, artifact)
    pair = report["pairs"][0]
    assert pair["n_common"] == len(requests) and pair["differing_total"] == 2
    assert pair["utility_flips"] == 1 and pair["utility_covered"] == len(requests)
    assert pair["pools_with_a_utility_flip"] == 1


# --------------------------------------------------------------------------- the draft registration


def test_registration_config_and_judge_prompt_pin() -> None:
    reg = ms.load_config(ms.REGISTRATION_CONFIG_PATH)
    assert reg["experiment_id"] == ms.REGISTRATION_ID and reg["claim_level"] == "confirmatory"
    assert ms.artifact_rule(reg) == (ms.REGISTRATION_ID, "heldout")
    assert ms.artifact_rule(ms.load_config()) == (ms.EXPERIMENT_ID, "development")
    main = ms.load_config()
    for key in ("source", "usable", "split", "retriever", "pools", "placebo", "prompt", "reader",
                "judge", "internal", "analysis", "seeds"):  # fmt: skip
        assert reg[key] == main[key], key
    warm = driver.worker_spec(reg, "reader-warm")
    assert warm["passes"] == ["smoke"]
    assert driver.worker_spec(reg, "reader-gpu1")["cache_from"] == "reader-warm"
    blob = json.dumps(ms.JUDGE_TEMPLATES, sort_keys=True, ensure_ascii=False).encode()
    assert hashlib.sha256(blob).hexdigest() == (
        "2e27234d4c7d50a1fd99da3e8d3c97704a1f10cc9d52185924b6d8ece3ef71d4"
    )


def test_passes_option_is_checked(tmp_path: Path) -> None:
    text = ms.REGISTRATION_CONFIG_PATH.read_text().replace("passes: [smoke]", "passes: [all]")
    bad = tmp_path / "r.yaml"
    bad.write_text(text)
    with pytest.raises(ms.StudyError):
        ms.load_config(bad)


def test_heldout_artifact_needs_the_frozen_registration(
    tmp_path: Path, artifact: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    reg = ms.load_config(ms.REGISTRATION_CONFIG_PATH)
    held = tmp_path / "held.json"
    held.write_text(json.dumps(dict(artifact, experiment_id=ms.REGISTRATION_ID, split="heldout")))
    with pytest.raises(ms.StudyError):
        driver.load_artifact(held, None)  # the pilot's config never runs held-out data
    registration = tmp_path / "reg.md"
    registration.write_text("frozen text")
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text("")
    monkeypatch.setattr(ms, "REGISTRATION_PATH", registration)
    monkeypatch.setattr(ms, "LEDGER_PATH", ledger)
    with pytest.raises(ms.StudyError):
        driver.load_artifact(held, None, reg)
    ledger.write_text(json.dumps({"experiment_id": ms.REGISTRATION_ID,
                                  "sha256": ms.sha256_file(registration)}) + "\n")  # fmt: skip
    assert driver.load_artifact(held, None, reg)["split"] == "heldout"
    dev = tmp_path / "dev.json"
    dev.write_text(json.dumps(artifact))
    with pytest.raises(ms.StudyError):
        driver.load_artifact(dev, None, reg)  # the registration never runs development data


def test_eager_check_config() -> None:
    eager = ms.load_config(ms.EAGER_CONFIG_PATH)
    assert eager["experiment_id"] == "memcredit-study-v1-eager"
    workers = [w for p in eager["job"]["phases"] for w in p["workers"]]
    assert all(w.get("enforce_eager") for w in workers)
    assert driver.worker_spec(eager, "rd-eager-gpu0")["passes"] == ["smoke", "all", "replicate"]
    assert ms.artifact_rule(eager) == (ms.EXPERIMENT_ID, "development")
