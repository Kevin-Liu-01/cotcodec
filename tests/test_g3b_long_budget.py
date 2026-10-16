"""Tests for g3b-long-budget-v1 (EXPLORATORY): the pinned questions and their derivation from
G3's committed data, plans, requests and seeds identical to G3's, the engine and sampling
settings, the no-preemption fit check against G3's recorded block pools, scoring at a shorter
cap, and score-and-analyze end to end. CPU only; no torch or vLLM needed."""

from __future__ import annotations

import copy
import gzip
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness import g3_state_precision as g3  # noqa: E402
from harness import g3b_long_budget as g3b  # noqa: E402

G3_EVIDENCE = ROOT / "program/evidence/2026-10-16/g3-state-precision-accuracy"
G3_DATA = G3_EVIDENCE / "data/per-request.jsonl.gz"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


analysis = _load("analyze_g3b_long_budget")


def test_pinned_questions_follow_from_g3_data() -> None:
    config = g3b.load_config()
    q = config["questions"]
    assert g3.sha256_file(G3_DATA) == q["source_sha256"]
    rows = g3b.read_g3_rows(G3_DATA)
    derived = g3b.capped_questions(rows)
    assert derived == q["indices"]
    assert len(derived) == 51
    assert g3b.indices_digest(derived) == q["indices_sha256"]
    # The longest of the 51 prompts (G3's prompt_len) fits max_model_len with the full budget.
    longest = max(
        r["prompt_len"]
        for r in rows
        if r["task"] == "math" and r["model"] == "qwen3.5-4b" and r["question_index"] in derived
    )
    assert longest == 857
    assert (
        longest + config["tasks"]["math"]["sampling"]["max_tokens"]
        <= config["tasks"]["math"]["max_model_len"]
    )


def test_config_refuses_tampering(tmp_path: Path) -> None:
    raw = yaml.safe_load(g3b.CONFIG_PATH.read_text())
    cases = []
    bad = copy.deepcopy(raw)
    bad["questions"]["indices"] = bad["questions"]["indices"][:-1]
    cases.append(bad)
    bad = copy.deepcopy(raw)
    bad["arms"]["bf16"] = "float16"
    cases.append(bad)
    bad = copy.deepcopy(raw)
    bad["tasks"]["math"]["rescore_caps"] = [16384]
    cases.append(bad)
    bad = copy.deepcopy(raw)
    bad["engine"]["enable_prefix_caching"] = True
    cases.append(bad)
    bad = copy.deepcopy(raw)
    bad["main"] = {"arms": ["fp32", "bf16"], "seeds": [42, 43], "gen_seconds": 10}
    cases.append(bad)
    bad = copy.deepcopy(raw)
    bad["aa"] = {"arms": ["fp32"], "seeds": [42], "gen_seconds": 10}
    cases.append(bad)
    for i, case in enumerate(cases):
        path = tmp_path / f"c{i}.yaml"
        path.write_text(yaml.safe_dump(case))
        with pytest.raises(g3b.G3bConfigError):
            g3b.load_config(path)


def test_plans_requests_and_seeds_match_g3() -> None:
    config = g3b.load_config()
    plan = g3b.phase_plan(config, "pilot")
    assert plan["arms"] == ["fp32", "bf16"]
    assert plan["math_questions"] == config["questions"]["indices"]
    reqs = g3b.math_requests(plan)
    assert len(reqs) == 153
    # G3's order (seed, then question) and G3's request ids and seeds.
    assert [r["seed"] for r in reqs[:51]] == [42] * 51
    assert reqs[0]["request_id"] == "m/q009/s42" and reqs[-1]["request_id"] == "m/q131/s44"
    g3_ids = {
        (r["request_id"], r["seed"], r["question_index"])
        for r in g3b.read_g3_rows(G3_DATA)
        if r["phase"] == "main" and r["model"] == "qwen3.5-4b" and r["arm"] == "fp32"
    }
    for r in reqs:
        assert (r["request_id"], r["seed"], r["question_index"]) in g3_ids
        assert r["request_seed"] == 100000 * r["seed"] + r["question_index"]
    main = g3b.phase_plan(config, "main")
    assert main["arms"] == ["fp32", "bf16"]
    assert g3b.math_requests(main) == reqs
    aa = g3b.phase_plan(config, "aa")
    assert aa["arms"] == ["fp32_aa"] and aa["math_seeds"] == [42]
    assert g3b.math_requests(aa) == reqs[:51]
    # A subset phase keeps the order and the seeds.
    sub = dict(
        config, aa={"arms": ["fp32_aa"], "seeds": [42], "questions": [9, 17], "gen_seconds": 5}
    )
    aa = g3b.math_requests(g3b.phase_plan(sub, "aa"))
    assert [r["request_id"] for r in aa] == ["m/q009/s42", "m/q017/s42"]


def test_engine_and_sampling_are_g3s_except_budget() -> None:
    config = g3b.load_config()
    g3c = g3.load_config()
    model_dir = Path("/m")
    for arm, g3_arm in (("fp32", "fp32"), ("bf16", "bf16"), ("fp32_aa", "fp32")):
        ours = g3b.engine_kwargs(config, model_dir, arm)
        theirs = g3.engine_kwargs(g3c, "qwen3.5-4b", model_dir, g3_arm, "math")
        assert ours["max_num_seqs"] == 23 and ours["max_model_len"] == 82944
        diff = {k for k in theirs if theirs[k] != ours[k]}
        assert diff == {"max_num_seqs", "max_model_len"}
    ours = g3b.sampling_kwargs(config, 4200009, 7)
    theirs = g3.sampling_kwargs(g3c, "math", 4200009, 7)
    assert {k for k in theirs if theirs[k] != ours[k]} == {"max_tokens"}
    assert ours["max_tokens"] == 81920
    assert g3.load_math_prompts(g3b.g3_view(config)) == g3.load_math_prompts(g3c)


def test_fit_check_against_g3_block_pools() -> None:
    # vLLM's own concurrency figure at G3's 33,792 tokens matches the formula (3 GDN groups).
    for job, arm in (("1523-main", "fp32"), ("1527-main", "bf16")):
        engine = json.loads(
            (G3_EVIDENCE / f"jobs/{job}/g3/qwen3.5-4b-{arm}-math/engine.json").read_text()
        )
        rep = g3b.fit_report(
            engine["num_gpu_blocks"], engine["block_size"], engine["max_model_len"], 55, 3,
            float(engine["cache_config_info"]["kv_cache_max_concurrency"]),
        )  # fmt: skip
        assert rep["vllm_agrees"] and rep["ok"]
    # At 82,944 tokens, 23 sequences fit both of G3's pools and 24 do not.
    for blocks, size in ((3733, 528), (7248, 272)):
        assert g3b.fit_report(blocks, size, 82944, 23, 3)["ok"]
        assert not g3b.fit_report(blocks, size, 82944, 24, 3)["ok"]
    rep = g3b.fit_report(3733, 528, 82944, 23, 3)
    assert rep["blocks_per_sequence"] == 158 + 3 and rep["blocks_needed"] == 23 * 161 <= 3732
    # A disagreeing vLLM figure fails the check.
    assert not g3b.fit_report(3733, 528, 82944, 23, 3, 30.0)["ok"]


def test_score_at_cap() -> None:
    ref = "7"
    full_ok = g3b.score_text("<think>a</think>\\boxed{7}", ref)
    assert full_ok == {"thinking_closed": True, "has_answer": True, "correct": 1}
    # Ended within the cap: unchanged.
    s = g3b.score_at_cap(1000, "stop", full_ok, None, 32768)
    assert s == {"correct": 1, "has_answer": True, "cap_hit": 0, "ended": 1, "len": 1000}
    # Longer than the cap, still thinking at the cap: no answer under the cap.
    trunc = g3b.score_text("<think>a b c", ref)
    s = g3b.score_at_cap(50000, "stop", full_ok, trunc, 32768)
    assert s == {"correct": 0, "has_answer": False, "cap_hit": 1, "ended": 0, "len": 32768}
    # Longer than the cap, answer already given before it: correct under the cap too.
    trunc = g3b.score_text("<think>a</think>\\boxed{7} and then", ref)
    assert g3b.score_at_cap(40000, "length", full_ok, trunc, 32768)["correct"] == 1
    with pytest.raises(g3b.G3bConfigError):
        g3b.score_at_cap(40000, "stop", full_ok, None, 32768)
    # Cut by the time budget before the cap: no outcome at the cap. Cut after it: scored there.
    none = g3b.score_at_cap(20000, g3b.TIME_CUT, full_ok, None, 32768)
    assert set(none.values()) == {None}
    trunc = g3b.score_text("<think>a b c", ref)
    assert g3b.score_at_cap(40000, g3b.TIME_CUT, full_ok, trunc, 32768)["cap_hit"] == 1


def _worker(
    root: Path,
    arm: str,
    rows: list[tuple[dict, dict, list[int]]],
    phase: str,
    phase_start: str | None = None,
) -> Path:
    path = root / f"qwen3.5-4b-{arm}-math"
    path.mkdir(parents=True)
    if phase_start:
        (path / "worker-progress.jsonl").write_text(
            json.dumps({"event": "phase-start", "utc": phase_start}) + "\n"
        )
    (path / "records.json").write_text(
        json.dumps(
            {
                "phase": phase,
                "model_id": "qwen3.5-4b",
                "arm": arm,
                "task": "math",
                "requests": [r for r, _, _ in rows],
            }
        )
    )
    with gzip.open(path / "texts.jsonl.gz", "wt") as handle:
        for r, entry, _ in rows:
            handle.write(json.dumps({"request_id": r["request_id"], **entry}) + "\n")
    lens = [len(t) for _, _, t in rows]
    np.savez_compressed(
        path / "tokens.npz",
        offsets=np.concatenate([[0], np.cumsum(lens)]),
        token_ids=np.asarray([x for _, _, t in rows for x in t], dtype=np.int32),
    )
    out_tokens = sum(r["completion_len"] for r, _, _ in rows)
    (path / "summary.json").write_text(
        json.dumps(
            {
                "model": "qwen3.5-4b",
                "arm": arm,
                "task": "math",
                "phase_name": phase,
                "engine": {
                    "num_gpu_blocks": 3733,
                    "block_size": 528,
                    "mamba_ssm_cache_dtype": arm,
                    "max_num_seqs": 23,
                    "max_model_len": 82944,
                    "fit": g3b.fit_report(3733, 528, 82944, 23, 3),
                },
                "phase": {
                    "wall_s": 100.0,
                    "output_tokens": out_tokens,
                    "output_tok_per_s": out_tokens / 100.0,
                    "requests": len(rows),
                    "finished": sum(1 for r, _, _ in rows if r["finish_reason"] != g3b.TIME_CUT),
                    "mean_running": 2.0,
                    "peak_running": 4,
                    "preemptions_delta": 0.0,
                    "peak_kv_usage": 0.5,
                    "info": {"aborted": 0, "stopped_by": None},
                },
            }
        )
    )
    return path


def test_score_and_analyze_end_to_end(tmp_path: Path) -> None:
    config = g3b.load_config()
    prompts = g3.load_math_prompts(g3b.g3_view(config))
    qs = config["questions"]["indices"][:6]
    workers = []
    for arm, phase in (("fp32", "main"), ("bf16", "main"), ("fp32_aa", "aa")):
        rows = []
        for q in qs:
            for seed in (42, 43, 44):
                answer = prompts[q]["answer"]
                ok = f"<think>\nwork\n</think>\n\n\\boxed{{{answer}}}"
                # bf16: q0 runs past 32,768 and answers correctly only after it; q1 is wrong.
                if arm == "bf16" and q == qs[0]:
                    req_len, finish = 40000, "stop"
                    entry = {"text": ok, "text_at_32768": "<think>\nstill working"}
                elif arm == "bf16" and q == qs[1]:
                    req_len, finish = 2000, "stop"
                    entry = {"text": "<think>\nw\n</think>\n\n\\boxed{wrong}"}
                elif arm == "fp32" and q == qs[2] and seed == 42:
                    req_len, finish = 81920, "length"
                    entry = {"text": "<think>\nforever", "text_at_32768": "<think>\nforever"}
                elif arm == "bf16" and q == qs[4] and seed == 44:
                    # Cut by the time budget before 32,768 tokens: unknown at both budgets.
                    req_len, finish = 20000, g3b.TIME_CUT
                    entry = {"text": "<think>\nworking"}
                elif arm == "bf16" and q == qs[5] and seed == 44:
                    # Cut after 32,768 tokens without an answer: unsolved at 32,768.
                    req_len, finish = 40000, g3b.TIME_CUT
                    entry = {"text": "<think>\nworking", "text_at_32768": "<think>\nworking"}
                else:
                    req_len, finish = 1000, "stop"
                    entry = {"text": ok}
                req = {
                    "request_id": f"m/q{q:03d}/s{seed}",
                    "question_index": q,
                    "seed": seed,
                    "prompt_len": 5,
                    "completion_len": req_len,
                    "sum_logp": -1.0,
                    "finish_reason": finish,
                    "first_token_s": float(seed - 42),
                    "finished_s": 10.0,
                }
                tokens = [1, 2, 3] if arm != "bf16" or q != qs[3] else [1, 2, 9]
                rows.append((req, entry, tokens))
        start = "2026-10-16T02:58:53Z" if arm == "bf16" else None
        workers.append(_worker(tmp_path / arm, arm, rows, phase, start))
    scored = analysis.score_workers(workers)
    assert len(scored) == 3 * 18
    q0 = [r for r in scored if r["arm"] == "bf16" and r["question_index"] == qs[0]]
    assert all(r["correct"] == 1 and r["c32768_correct"] == 0 and r["c32768_cap_hit"] for r in q0)
    q3 = [r for r in scored if r["arm"] == "bf16" and r["question_index"] == qs[3]]
    assert all(r["first_diff_vs_fp32"] == 2 for r in q3)
    aa = [r for r in scored if r["arm"] == "fp32_aa"]
    assert all("identical_to_fp32" in r for r in aa)
    g3_rows = g3b.read_g3_rows(G3_DATA)
    summaries = analysis.worker_summaries([tmp_path / a for a in ("fp32", "bf16", "fp32_aa")])
    window = {"start_utc": "2026-10-16T02:59:00Z", "end_utc": "2026-10-16T02:59:30Z", "note": "x"}
    results = analysis.analyze(scored, summaries, g3_rows, 500, 42, timing_windows=[window])
    p = results["paired"]
    assert results["arms"] == ["fp32", "bf16", "fp32_aa"]
    # fp32: 17 of 18 correct (q2 seed 42 capped without an answer); bf16: q1 wrong everywhere,
    # and two seed-44 rollouts cut by the time budget (q4 before 32,768 tokens, q5 after).
    assert p["correct"]["fp32"]["mean"] == pytest.approx(1 - 1 / 18)
    assert p["correct"]["bf16_minus_fp32"]["diff"] == pytest.approx(-4 / 18)
    assert p["correct_upper"]["bf16_minus_fp32"]["diff"] == pytest.approx(-2 / 18)
    assert p["correct_complete"]["pairs"] == 16 and p["correct_complete"]["pairs_dropped"] == 2
    assert p["correct_complete"]["bf16_minus_fp32"]["diff"] == pytest.approx((-1 + 1 / 3) / 6)
    # Rescored at 32,768: bf16 also loses q0 and q5 seed 44; q4 seed 44 is unknown (dropped).
    assert p["c32768_correct"]["pairs"] == 17
    assert p["c32768_correct"]["bf16_minus_fp32"]["diff"] == pytest.approx(-1 / 3)
    assert p["c32768_correct_lower"]["pairs"] == 18
    assert p["cap_hit"]["fp32"]["mean"] == pytest.approx(1 / 18)
    assert p["correct"]["fp32_aa_minus_fp32"]["diff"] == pytest.approx(1 / 18)
    ba = results["by_arm"]["bf16"]
    assert ba["past_cap"] == 4 and ba["past_cap_ended"] == 3 and ba["past_cap_correct"] == 3
    assert ba["time_cut"] == 2 and ba["undetermined_at_cap"] == 1
    assert [x["tokens_at_cut"] for x in ba["time_cut_rollouts"]] == [20000, 40000]
    het = results["seed_heterogeneity"]["correct_complete"]
    # q4 and q5 lose seed 44 and leave the contrast; fp32 lost q2 at seed 42 only.
    assert het["n_questions"] == 4
    assert het["contrast"] == pytest.approx(1 / 4)
    assert results["preemptions_total"] == 0
    assert results["g3b_vs_g3"]["at_32768"]["n_questions"] == 6
    assert results["g3_same_questions"]["correct"]["n_questions"] == 51
    flags = {e["arm"]: e["timing_affected_by"] for e in results["engines"]}
    assert flags == {"fp32": [], "bf16": ["x"], "fp32_aa": []}
    text = analysis.tables_md(results)
    assert "## Seed order" in text and "| 81,920 (complete pairs) | 42 |" in text
    assert "affected: x" in text and "| bf16 | m/q" in text
    assert "## Engines" in text
