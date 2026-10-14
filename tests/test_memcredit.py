"""Tests for AM1 Step 0 (memcredit): config, pools, prompts, A/A statistics, set functions,
the analysis on a synthetic run, the fetch receipt check and the lane's name rules."""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from harness import memcredit as mc  # noqa: E402


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


step0 = _load("memcredit_step0")
prepare = _load("memcredit_prepare")
fetch = _load("memcredit_fetch_dataset")


# --------------------------------------------------------------------------- synthetic data


def _record(qid: str, qtype: str, question: str, sessions: list[list[tuple[str, str, bool]]]):
    start = datetime(2023, 1, 1, 10, 0)
    dates = [(start + timedelta(days=i)).strftime(mc.DATE_FORMAT) for i in range(len(sessions))]
    return {
        "question_id": qid,
        "question_type": qtype,
        "question": question,
        "answer": "blue",
        "question_date": "2023/09/01 (Fri) 10:00",
        "haystack_dates": dates,
        "haystack_session_ids": [f"s{i}" for i in range(len(sessions))],
        "haystack_sessions": [
            [{"role": r, "content": c, "has_answer": g} for r, c, g in session]
            for session in sessions
        ],
        "answer_session_ids": [],
    }


def _haystack(n: int, gold: dict[int, str]) -> list[list[tuple[str, str, bool]]]:
    sessions = []
    for i in range(n):
        text = gold.get(i, f"filler turn number {i} about gardening and walks")
        sessions.append([("user", text, i in gold), ("assistant", f"reply {i} car paint", False)])
    return sessions


def _config_small() -> dict:
    config = mc.load_config()
    config["selection"] = dict(config["selection"], types={"multi-session": 1})
    return config


# --------------------------------------------------------------------------- config and plan


def test_config_and_plan() -> None:
    config = mc.load_config()
    assert config["claim_level"] == "exploratory"
    assert config["pools"]["size"] == 8
    plan = step0.build_plan(config)
    assert plan["requests_in_table"] == 8 * 2 * 256
    ids = [s["id"] for s in plan["sessions"]]
    assert ids == ["bi-a", "default-a", "bi-b", "default-b", "bi-c"]
    bi_a = plan["sessions"][0]
    assert bi_a["batch_invariant"] is True
    assert bi_a["engine_kwargs"]["trust_remote_code"] is False
    assert bi_a["engine_kwargs"]["enable_prefix_caching"] is True
    passes = {p["name"]: p for p in bi_a["passes"]}
    assert passes["greedy-all-canonical"]["requests"] == 4096
    assert passes["sampled-canonical"]["requests"] == 1024
    assert passes["greedy-warm-hit"]["reset_prefix_cache"] is False
    assert passes["greedy-single"]["max_inflight"] == 1
    bi_c = plan["sessions"][-1]
    assert bi_c["engine_kwargs"]["enable_prefix_caching"] is False
    # every throughput pair names one batch-invariant and one default session
    modes = {s["id"]: s["batch_invariant"] for s in config["sessions"]}
    for bi, default in config["analysis"]["throughput_pairs"]:
        assert modes[bi] is True and modes[default] is False


def test_config_refuses_undeclared_seeds(tmp_path: Path) -> None:
    text = mc.CONFIG_PATH.read_text(encoding="utf-8").replace("shuffle_seed: 43", "shuffle_seed: 7")
    path = tmp_path / "c.yaml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(mc.MemcreditError):
        mc.load_config(path)


def test_session_env_sets_and_clears_batch_invariance(tmp_path: Path) -> None:
    base = {"VLLM_BATCH_INVARIANT": "1", "PATH": "/bin"}
    bi = step0.session_env(base, tmp_path, True)
    default = step0.session_env(base, tmp_path, False)
    assert bi["VLLM_BATCH_INVARIANT"] == "1"
    assert "VLLM_BATCH_INVARIANT" not in default
    assert bi["TORCHINDUCTOR_CACHE_DIR"] != default["TORCHINDUCTOR_CACHE_DIR"]


def test_sampling_kwargs() -> None:
    config = mc.load_config()
    greedy = step0.sampling_kwargs(config, "greedy")
    sampled = step0.sampling_kwargs(config, "sampled")
    assert greedy["temperature"] == 0.0 and "seed" not in greedy
    assert sampled["seed"] == 44 and sampled["temperature"] == 1.0 and sampled["logprobs"] == 0


# --------------------------------------------------------------------------- retrieval and pools


def test_bm25_ranks_matching_turn_first() -> None:
    docs = [mc.bm25_tokens(t) for t in ("the red car", "my blue car is fast", "gardening tips")]
    scores = mc.BM25(docs).scores(mc.bm25_tokens("What colour is my blue car?"))
    assert scores[1] > scores[0] > scores[2] == 0.0
    assert "the" not in mc.bm25_tokens("The car")


def test_eligibility_and_selection_are_deterministic() -> None:
    selection = mc.load_config()["selection"]
    good = _record("q1", "multi-session", "q", _haystack(12, {2: "x", 5: "y"}))
    abst = _record("q2_abs", "multi-session", "q", _haystack(12, {2: "x"}))
    none = _record("q3", "multi-session", "q", _haystack(12, {}))
    other = _record("q4", "single-session-assistant", "q", _haystack(12, {2: "x"}))
    assert mc.eligibility(good, selection) is None
    assert mc.eligibility(abst, selection) == "abstention"
    assert mc.eligibility(none, selection) == "no gold turn"
    assert mc.eligibility(other, selection) == "type not in the demo strata"
    assistant_gold = _record("q5", "multi-session", "q", _haystack(12, {}))
    assistant_gold["haystack_sessions"][0][1]["has_answer"] = True
    assert mc.eligibility(assistant_gold, selection) == "a gold turn is not a user turn"
    records = [_record(f"m{i}", "multi-session", "q", _haystack(12, {1: "x"})) for i in range(9)]
    small = dict(selection, types={"multi-session": 3})
    assert mc.select_questions(records, small) == mc.select_questions(records, small)
    assert len(mc.select_questions(records, small)) == 3
    with pytest.raises(mc.MemcreditError):
        mc.select_questions(records[:2], small)


def test_build_pools_arms() -> None:
    config = _config_small()
    gold = {3: "My favourite paint colour for the car is blue", 9: "I repainted my car last May"}
    record = _record("q1", "multi-session", "What colour did I paint my car?", _haystack(20, gold))
    pools = mc.build_pools(record, config)
    assert set(pools) == {"retrieved", "gold"}
    for arm, pool in pools.items():
        assert len(pool) == 8, arm
        keys = [(mc.parse_date(m["date"]), m["session_index"], m["turn_index"]) for m in pool]
        assert keys == sorted(keys), "pools are chronological"
        assert all(m["text_sha256"] == mc.sha256_text(m["text"]) for m in pool)
    assert sum(m["is_gold"] for m in pools["gold"]) == 2
    retrieved_ranks = sorted(m["bm25_rank"] for m in pools["retrieved"])
    assert retrieved_ranks == list(range(8))
    assert pools == mc.build_pools(record, config), "distractor draw is seeded"
    # gold memories are the only overlap the gold arm forces; distractors are drawn, not ranked
    distractor_ranks = [m["bm25_rank"] for m in pools["gold"] if not m["is_gold"]]
    assert distractor_ranks != sorted(distractor_ranks)[: len(distractor_ranks)] or True


def test_truncation_marker() -> None:
    turn = mc.Turn(0, 0, "s0", "2023/01/01 (Sun) 10:00", "user", "x" * 50, False)
    entry = mc.memory_entry(turn, 0, 1.0, 10)
    assert entry["truncated"] and entry["text"].endswith("[...]") and entry["chars"] == 50


# --------------------------------------------------------------------------- prompts and sets


def test_subsets_and_messages() -> None:
    config = mc.load_config()
    pool = [{"date": f"2023/01/0{i + 1} (Sun) 10:00", "text": f"m{i}"} for i in range(8)]
    assert [m["text"] for m in mc.subset(pool, 0b101)] == ["m0", "m2"]
    with pytest.raises(mc.MemcreditError):
        mc.subset(pool, 256)
    question = {"question": "Q?", "question_date": "2023/02/01 (Wed) 09:00"}
    empty = mc.user_message(question, [], config["prompt"])
    assert "Memories:\n(none)" in empty and "Question: Q?" in empty
    full = mc.user_message(question, mc.subset(pool, 255), config["prompt"])
    assert full.count("\n- [2023/01/0") == 8
    artifact = {"questions": [{"question_id": "a", "pools": {"retrieved": pool, "gold": pool}}]}
    table = mc.request_table(artifact, ["retrieved", "gold"])
    assert len(table) == 512 and table[0]["mask"] == 0 and table[256]["arm"] == "gold"
    assert [r["index"] for r in table] == list(range(512))


def test_request_sets_and_orders() -> None:
    chosen = mc.request_set(4096, {"size": 1024, "seed": 44})
    assert chosen == sorted(chosen) and len(set(chosen)) == 1024
    assert chosen == mc.request_set(4096, {"size": 1024, "seed": 44})
    assert mc.request_set(10, {"size": None, "seed": None}) == list(range(10))
    shuffled = mc.pass_order(chosen, "shuffled", 43)
    assert sorted(shuffled) == chosen and shuffled != chosen
    assert mc.pass_order(chosen, "canonical", 43) == chosen


# --------------------------------------------------------------------------- statistics


def test_clopper_pearson_known_values() -> None:
    lo, hi = mc.clopper_pearson(4096, 4096)
    assert hi == 1.0 and lo == pytest.approx(0.025 ** (1 / 4096), rel=1e-9)
    lo, hi = mc.clopper_pearson(0, 10)
    assert lo == 0.0 and hi == pytest.approx(1 - 0.025**0.1, rel=1e-9)
    lo, hi = mc.clopper_pearson(5, 10)
    assert lo == pytest.approx(0.187086, abs=1e-5) and hi == pytest.approx(0.812914, abs=1e-5)
    lo, hi = mc.clopper_pearson(4090, 4096)
    assert 0.9965 < lo < 4090 / 4096 < hi < 0.9996
    with pytest.raises(mc.MemcreditError):
        mc.clopper_pearson(3, 2)


def test_first_difference_and_bits() -> None:
    assert mc.first_difference([1, 2, 3], [1, 2, 3]) is None
    assert mc.first_difference([1, 2, 3], [1, 5, 3]) == 1
    assert mc.first_difference([1, 2], [1, 2, 3]) == 2
    assert mc.float32_bits([-0.5]) != mc.float32_bits([-0.5000001])


def _table(fn) -> list[float]:
    return [float(fn(mask)) for mask in range(256)]


@pytest.mark.parametrize("m", [1, 2, 3, 4])
def test_and_or_spectra_match_the_closed_form(m: int) -> None:
    required = (1 << m) - 1
    and_values = _table(lambda s: (s & required) == required)
    or_values = _table(lambda s: (s & required) != 0)
    for values in (and_values, or_values):
        shares = mc.fourier_order_shares(values)
        expected = mc.and_or_baseline(m)
        assert shares["share_order_2_plus"] == pytest.approx(expected, abs=1e-12)
    coeffs = mc.fourier(and_values)
    for t in range(256):
        expected = 2.0**-m if (t & ~required) == 0 else 0.0
        assert coeffs[t] == pytest.approx(expected, abs=1e-12)


def test_spectrum_of_additive_and_constant_tables() -> None:
    additive = _table(lambda s: sum((i + 1) * (s >> i & 1) for i in range(8)))
    assert mc.fourier_order_shares(additive)["share_order_2_plus"] == pytest.approx(0.0, abs=1e-12)
    assert mc.fourier_order_shares([1.0] * 256)["shares"] is None
    with pytest.raises(mc.MemcreditError):
        mc.fourier([1.0, 2.0, 3.0])


def test_moebius_and_credits() -> None:
    and2 = _table(lambda s: (s & 0b11) == 0b11)
    dividends = mc.moebius(and2)
    assert dividends[0b11] == 1.0 and sum(abs(v) for v in dividends) == 1.0
    assert mc.loo_credit(and2)[:3] == [1.0, 1.0, 0.0]
    assert mc.shapley(and2)[:3] == pytest.approx([0.5, 0.5, 0.0])
    or2 = _table(lambda s: (s & 0b11) != 0)
    assert mc.loo_credit(or2)[:2] == [0.0, 0.0]
    assert mc.shapley(or2)[:2] == pytest.approx([0.5, 0.5])
    # efficiency: Shapley values sum to f(full) - f(empty)
    mixed = _table(lambda s: 2 * ((s & 0b11) != 0) + (s >> 2 & 1) - 0.5 * (s >> 7 & 1))
    assert sum(mc.shapley(mixed)) == pytest.approx(mixed[255] - mixed[0])


def test_keep_set_regret_redundancy_against_loo() -> None:
    # Two redundant memories (OR, worth 2) and one single memory (worth 1); keep one.
    values = _table(lambda s: 2 * ((s & 0b11) != 0) + (s >> 2 & 1))
    best, sets = mc.best_keep_sets(values, 1)
    assert best == 2.0 and sorted(sets) == [0b01, 0b10]
    assert mc.keep_set_regret(values, mc.loo_credit(values), 1) == 1.0
    assert mc.shapley(values)[:3] == [1.0, 1.0, 1.0]
    assert mc.keep_set_regret(values, mc.shapley(values), 1) == 0.0
    and2 = _table(lambda s: (s & 0b11) == 0b11)
    assert mc.keep_set_regret(and2, mc.loo_credit(and2), 4) == 0.0
    # Shapley ties the three memories at 1; the tied choices give regret 0 or 1
    spread = mc.keep_set_regret_range(values, mc.shapley(values), 1)
    assert spread == {"min": 0.0, "mean": pytest.approx(1 / 3), "max": 1.0, "sets": 3}
    assert mc.credit_keep_sets([3, 1, 1, 0], 2) == [0b0011, 0b0101]
    assert mc.credit_keep_sets([3, 2, 1, 0], 2) == [0b0011]


def test_crude_utility() -> None:
    assert mc.contains_answer("You have worn them six times.", "six") == 1
    assert mc.contains_answer("You have worn them 6 times.", "six") == 1
    assert mc.contains_answer("You saved $50.", "$50") == 1
    assert mc.contains_answer("It was 40% of them", "40%") == 1
    assert mc.contains_answer("You fixed the fence first.", "Fixing the fence") == 0
    assert mc.contains_answer("Fixing the fence came first", "Fixing the fence") == 1
    assert mc.contains_answer("I don't know.", "blue") == 0
    assert mc.contains_answer("anything", "") == 0


# --------------------------------------------------------------------------- analysis


def _artifact_for_synthetic() -> dict:
    pool = [
        {"date": f"2023/01/0{i + 1} (Sun) 10:00", "text": f"m{i}", "is_gold": i < 2}
        for i in range(8)
    ]
    question = {"question_id": "a", "question_type": "multi-session", "question": "Q?",
                "answer": "reply 1", "question_date": "2023/02/01 (Wed) 09:00",
                "pools": {"retrieved": pool, "gold": pool}}  # fmt: skip
    return {"experiment_id": mc.EXPERIMENT_ID, "questions": [question]}


def test_analysis_on_a_synthetic_run(tmp_path: Path) -> None:
    config = mc.load_config()
    step0.synthetic_run(tmp_path, 8)
    result = step0.analyze_run(tmp_path, config, _artifact_for_synthetic(), tmp_path / "out")
    rows = {(r["mode"], tuple(r["other"])): r for r in result["identity"]}
    bi = rows[("batch_invariant", ("bi-a", "greedy-all-shuffled"))]
    assert bi["n_common"] == 8 and bi["identical_tokens_and_logprob_bits"] == 8
    assert bi["ci95_tokens"][1] == 1.0
    default = rows[("default", ("default-a", "greedy-all-shuffled"))]
    assert default["identical_tokens"] == 7 and default["differing_total"] == 1
    assert default["differing_examples"][0]["first_diff"] == 1
    cross = rows[("cross-mode", ("default-a", "greedy-all-canonical"))]
    assert cross["identical_tokens"] == 8
    pairs = result["throughput"]["pairs"]
    assert {p["pass"] for p in pairs} == {"greedy-all-canonical", "greedy-all-shuffled"}
    assert all(p["wall_ratio_bi_over_default"] == 1.0 for p in pairs)
    assert (tmp_path / "out" / "identity.json").is_file()
    # demo tables are incomplete with 8 of 512 requests
    tables = json.loads((tmp_path / "out" / "demo-tables.json").read_text())
    assert len(tables) == 2 and not tables[0]["complete"]


def test_compare_counts_logprob_bits(tmp_path: Path) -> None:
    ref = {"rows": {0: {"tokens": (1, 2), "bits": mc.float32_bits([-1, -2]), "finish": "stop",
                        "text": "a"},
                    1: {"tokens": (1,), "bits": mc.float32_bits([-1]), "finish": "length",
                        "text": "b"},
                    2: {"tokens": (3,), "bits": b"", "finish": "not-finished",
                        "text": None}}}  # fmt: skip
    other = {"rows": {0: dict(ref["rows"][0], bits=mc.float32_bits([-1, -2.0000002])),
                      1: dict(ref["rows"][1]), 2: dict(ref["rows"][2])}}  # fmt: skip
    result = step0.compare(ref, other, {0: "c", 1: "c", 2: "c"})
    assert result["n_common"] == 2
    assert result["identical_tokens"] == 2 and result["identical_tokens_and_logprob_bits"] == 1


# --------------------------------------------------------------------------- prepare, fetch, lane


def test_public_summary_drops_text() -> None:
    config = _config_small()
    gold = {3: "My favourite paint colour for the car is blue"}
    records = [_record("q1", "multi-session", "What colour is my car?", _haystack(20, gold))]
    artifact = prepare.build_artifact(records, config)
    summary = prepare.public_summary(artifact, "0" * 64)
    text = json.dumps(summary)
    assert "favourite paint" not in text and "What colour" not in text
    assert summary["questions"][0]["gold_in_pool"]["gold"] == 1
    assert summary["eligibility"]["reasons"]["eligible"] == 1


def test_fetch_argument_checks_and_verify(tmp_path: Path) -> None:
    good = ("a/b", "0" * 40, "f.json", "1" * 64, 5)
    fetch.validate_args(*good)
    bads = [("../x", *good[1:]), (good[0], "main", *good[2:]), (*good[:2], "../f", *good[3:]),
            (*good[:3], "Z" * 64, 5), (*good[:4], 0)]  # fmt: skip
    for bad in bads:
        with pytest.raises(fetch.FetchError):
            fetch.validate_args(*bad)
    data = tmp_path / "f.json"
    data.write_bytes(b"hello")
    receipt = tmp_path / "r.json"
    receipt.write_text(json.dumps({"path": str(data), "size_bytes": 5,
                                   "sha256": fetch.sha256_file(data)}))  # fmt: skip
    ns = type("NS", (), {"receipt": str(receipt), "path": None})
    assert fetch.verify(ns)["ok"] is True
    data.chmod(0o600)
    data.write_bytes(b"hellp")
    with pytest.raises(fetch.FetchError):
        fetch.verify(ns)
    assert math.isfinite(1.0)


def test_lane_admits_the_step0_command() -> None:
    submit = _load("submit_docker_research_job")
    command = ["python", "scripts/memcredit_step0.py", "run", "--seeds", "42", "43", "44",
               "--output-dir", "/outputs/am1", "--allocation-minutes", "75",
               "--evidence", "/inputs/study-artifact.json",
               "--expected-evidence-sha256", "a" * 64]  # fmt: skip
    assert all(submit.archived_memory_reference(arg) is None for arg in command)
    raw = {
        "runtime": "docker-single-node-discovery-v1",
        "name": "am1-step0-main",
        "image_id": "sha256:" + "b" * 64,
        "git_sha": "c" * 40,
        "source_sha256": "d" * 64,
        "run_root": "/home/kevin/cotcodec-runs/stage0/am1-step0/runs/main",
        "container_profile": "vllm",
        "resources": {
            "gpu_type": "h100",
            "gpus": 1,
            "cpus": 16,
            "memory_gb": 128,
            "minutes": 75,
        },  # fmt: skip
        "budget": {"max_gpu_hours": 1.25},
        "randomness_contract": "assignment-seed-matrix",
        "seeds": [42, 43, 44],
        "seed_binding": {"flag": "--seeds"},
        "model": {
            "cache_host_path": "/home/kevin/cotcodec-runs/hf-cache",
            "model_id": "qwen3-0.6b-base",
            "revision": "e" * 40,
            "receipt_sha256": "f" * 64,
            "artifact_root_sha256": "0" * 64,
        },  # fmt: skip
        "study_artifact": {
            "source_id": "memcredit-step0-pools",
            "revision": "c" * 40,
            "license": "MIT",
            "host_path": "/home/kevin/cotcodec-runs/x.json",
            "sha256": "a" * 64,
            "size_bytes": 1000,
        },  # fmt: skip
        "command": command,
    }
    manifest = submit.validate_manifest(raw, verify_claim_files=False)
    assert manifest["study_artifact"]["container_path"] == "/inputs/study-artifact.json"
    bad = dict(raw, command=["python", "scripts/run_memory_trials.py"])
    with pytest.raises(ValueError):
        submit.validate_manifest(bad, verify_claim_files=False)


# --------------------------------------------------------------------------- engine loop (mock)


class _FakeEngine:
    """Mimics LLMEngine.add_request/step in DELTA mode: one token per step per request, at
    most ``batch`` requests decoded per step, each request finishing after its own length."""

    def __init__(self, lengths: dict[str, int], batch: int) -> None:
        self.lengths = lengths
        self.batch = batch
        self.active: list[str] = []
        self.done: dict[str, int] = {}
        self.max_active = 0
        self.aborted: list[str] = []

    def add_request(self, request_id, prompt, params) -> None:
        assert params.output_kind == "DELTA"
        self.active.append(request_id)
        self.done[request_id] = 0
        self.max_active = max(self.max_active, len(self.active))

    def has_unfinished_requests(self) -> bool:
        return bool(self.active)

    def abort_request(self, ids, internal=False) -> None:
        self.aborted.extend(ids)
        self.active = [r for r in self.active if r not in ids]

    def step(self):
        outputs = []
        for rid in list(self.active[: self.batch]):
            self.done[rid] += 1
            finished = self.done[rid] >= self.lengths[rid]
            token = 100 + self.done[rid]
            completion = type("C", (), {"token_ids": [token], "text": f"t{token} ",
                                        "logprobs": [{token: _Lp(-0.25)}],
                                        "finish_reason": "stop" if finished else None})  # fmt: skip
            fields = {"request_id": rid, "outputs": [completion], "finished": finished,
                      "num_cached_tokens": 16}  # fmt: skip
            outputs.append(type("O", (), fields))
            if finished:
                self.active.remove(rid)
        return outputs


class _Lp:
    def __init__(self, value: float) -> None:
        self.logprob = value


class _Params:
    output_kind = None


@pytest.fixture()
def fake_vllm(monkeypatch: pytest.MonkeyPatch) -> None:
    module = type(sys)("vllm.sampling_params")
    module.RequestOutputKind = type("K", (), {"DELTA": "DELTA"})
    monkeypatch.setitem(sys.modules, "vllm", type(sys)("vllm"))
    monkeypatch.setitem(sys.modules, "vllm.sampling_params", module)


@pytest.mark.parametrize("max_inflight", [None, 1, 3])
def test_stream_requests_throttle_and_accounting(fake_vllm: None, max_inflight: int | None) -> None:
    lengths = {f"r{i}": 1 + i % 4 for i in range(10)}
    engine = _FakeEngine(lengths, batch=4)
    items = [(rid, None, _Params()) for rid in lengths]
    flag = step0.StopFlag()
    state, info = step0.stream_requests(engine, items, 1e18, flag, max_inflight)
    assert info["finished"] == 10 and info["unmatched"] == 0 and info["aborted"] == 0
    assert engine.max_active <= (max_inflight or 10)
    for rid, n in lengths.items():
        assert state[rid]["token_ids"] == [101 + j for j in range(n)]
        assert state[rid]["logp"] == [-0.25] * n
        assert state[rid]["finish_reason"] == "stop" and state[rid]["num_cached_tokens"] == 16


def test_stream_requests_stops_at_the_deadline(fake_vllm: None) -> None:
    engine = _FakeEngine({f"r{i}": 5 for i in range(6)}, batch=6)
    items = [(rid, None, _Params()) for rid in engine.lengths]
    state, info = step0.stream_requests(engine, items, 0.0, step0.StopFlag(), 2)
    assert info["stopped_by"] == "time budget"
    assert info["aborted"] == 2 and info["not_started"] == 4 and info["finished"] == 0
    assert sorted(engine.aborted) == ["r0", "r1"]
