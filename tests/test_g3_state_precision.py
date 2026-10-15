"""Tests for g3-state-precision-accuracy-v1 (EXPLORATORY): config and plans, paired request
seeds, the math final-answer checker, the long-context order and prompt, the judge items and
the paired bootstrap analysis. CPU only; no torch or vLLM needed."""

from __future__ import annotations

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


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


analysis = _load("analyze_g3_accuracy")


def test_config_and_pilot_plan() -> None:
    config = g3.load_config()
    assert config["seeds"] == [42, 43, 44]
    assert config["arms"] == {"fp32": "auto", "fp16": "float16", "bf16": "bfloat16"}
    plan = g3.phase_plan(config, "pilot")
    assert plan["arms"] == ["fp32"]
    assert len(plan["math_questions"]) == 48 and plan["math_questions"] == sorted(
        plan["math_questions"]
    )
    assert plan["math_seeds"] == [42, 43]
    # G2b's engine, with the task's max_model_len and the arm's state dtype.
    g2b = yaml.safe_load((ROOT / "experiments/g2/g2b-state-dtype-v1.yaml").read_text())["engine"]
    for task in g3.TASKS:
        kw = g3.engine_kwargs(config, "qwen3.5-9b", Path("/m"), "bf16", task)
        assert kw["mamba_ssm_cache_dtype"] == "bfloat16"
        for key in (
            "dtype",
            "gpu_memory_utilization",
            "max_num_seqs",
            "max_num_batched_tokens",
            "enable_prefix_caching",
            "logprobs_mode",
            "limit_mm_per_prompt",
        ):
            assert kw[key] == g2b[key], key
    # G2b's 33,536 plus room for the longest of the 134 math prompts (857 tokens, selftest 1490).
    math_len = g3.engine_kwargs(config, "qwen3.5-9b", Path("/m"), "fp32", "math")["max_model_len"]
    assert math_len == 33792 and math_len - 32768 >= 857 and g2b["max_model_len"] == 33536
    assert (
        g3.engine_kwargs(config, "qwen3.5-4b", Path("/m"), "fp32", "lme")["max_model_len"] == 131072
    )
    if "main" in config:
        main = g3.phase_plan(config, "main")
        assert main["arms"] == list(g3.ARM_NAMES)
        assert main["math_seeds"][:3] == [42, 43, 44]


def test_config_refuses_tampering(tmp_path: Path) -> None:
    raw = yaml.safe_load(g3.CONFIG_PATH.read_text(encoding="utf-8"))
    raw["arms"]["fp16"] = "bfloat16"
    path = tmp_path / "c.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(g3.G3ConfigError):
        g3.load_config(path)
    raw = yaml.safe_load(g3.CONFIG_PATH.read_text(encoding="utf-8"))
    raw["engine"]["enable_prefix_caching"] = True
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(g3.G3ConfigError):
        g3.load_config(path)


def test_math_prompts_and_paired_seeds() -> None:
    config = g3.load_config()
    prompts = g3.load_math_prompts(config)
    assert len(prompts) == 134 and all(p["level"] == 5 for p in prompts)
    g2 = [
        json.loads(line)
        for line in (ROOT / "experiments/g2/prompts-math500-l5-64.jsonl").read_text().splitlines()
    ]
    by_id = {p["unique_id"]: p for p in prompts}
    assert all(by_id[r["unique_id"]]["answer"] == r["answer"] for r in g2)
    plan = g3.phase_plan(config, "pilot")
    reqs = g3.math_requests(config, plan)
    assert len(reqs) == 96
    assert len({r["request_seed"] for r in reqs}) == len(reqs)
    assert reqs[0]["request_seed"] == 42 * g3.SEED_STRIDE + plan["math_questions"][0]
    assert g3.math_user_message(prompts[0], config).endswith("within \\boxed{}.")
    with pytest.raises(g3.G3ConfigError):
        g3.request_seed(42, g3.SEED_STRIDE)


CASES = [
    ("\\frac{11}{2}", "11/2", True),
    ("\\frac{11}{2}", "5.5", True),
    ("(-\\sqrt{3}, \\sqrt{3})", "(-\\sqrt3,\\sqrt3)", True),
    ("2\\sqrt{5}", "\\sqrt{20}", True),
    ("(-\\infty, 2) \\cup (3, \\infty)", "(-\\infty,2)\\cup(3,\\infty)", True),
    ("x=5", "5", True),
    ("1+2i", "1 + 2i", True),
    ("\\left(\\frac{3}{5},\\frac{8}{3}\\right]", "(\\frac35,\\frac83]", True),
    ("\\$32,\\!348", "32348", True),
    ("\\$18.90", "18.9", True),
    ("1\\frac{4}{5}", "\\frac{9}{5}", True),
    ("1\\frac{4}{5}", "1.8", True),
    ("1,-2", "-2, 1", True),
    ("1,-2", "-2", False),
    ("145^\\circ", "145", True),
    ("\\frac{270}7\\text{ degrees}", "\\frac{270}{7}", True),
    ("5.4 \\text{ cents}", "5.4", True),
    (
        "\\begin{pmatrix} 1/5 \\\\ -18/5 \\end{pmatrix}",
        "\\begin{pmatrix}\\frac{1}{5}\\\\-\\frac{18}{5}\\end{pmatrix}",
        True,
    ),
    ("y = 2x + 3", "y=2x+3", True),
    ("\\dfrac{17}{50}", "0.34", True),
    ("3 \\pm 2 \\sqrt{2}", "3\\pm2\\sqrt{2}", True),
    ("\\frac{3840}{289}", "13.29", False),
    ("17", "18", False),
    ("(3,4]", "(3,4)", False),
    ("(6,31,-1)", "(6, 31, -1)", True),
    ("\\{1\\pm\\sqrt{5},-2\\}", "1\\pm\\sqrt{5}, -2", True),
    ("\\frac{20000}{\\pi}", "6366.2", False),
    ("2", "\\sqrt[3]{8}", True),
    ("28800", "28,800", True),
    ("0", "", False),
    ("8n^2 + 4n + 1", "8n^2+4n+1", True),
    ("-\\frac{24}{25}", "-0.96", True),
]


@pytest.mark.parametrize(("reference", "prediction", "expected"), CASES)
def test_math_equiv(reference: str, prediction: str, expected: bool) -> None:
    assert g3.math_equiv(prediction, reference) is expected


def test_final_answer_scores_after_thinking() -> None:
    done = g3.final_answer("<think>\ntry \\boxed{3}\n</think>\n\nSo \\boxed{\\frac{1}{2}}.")
    assert done == {
        "thinking_closed": True,
        "answer": "\\frac{1}{2}",
        "answer_anywhere": "\\frac{1}{2}",
    }
    cut = g3.final_answer("<think>\nstill going \\boxed{4}")
    assert cut["answer"] is None and cut["answer_anywhere"] == "4" and not cut["thinking_closed"]
    assert g3.last_boxed("\\boxed{\\frac{a}{b}") is None
    assert g3.g2b_string_match("\\dfrac{1}{2}", "\\frac{1}{2}")
    assert not g3.g2b_string_match("0.5", "\\frac{1}{2}")
    assert g3.math_equiv("0.5", "\\frac{1}{2}")


def _lme_record(qid: str, qtype: str, dates: list[str]) -> dict:
    return {
        "question_id": qid,
        "question_type": qtype,
        "question": f"q {qid}?",
        "answer": "blue",
        "question_date": "2023/06/01 (Thu) 10:00",
        "haystack_dates": dates,
        "haystack_sessions": [
            [
                {"role": "user", "content": f" s{i} "},
                {"role": "assistant", "content": "ok", "has_answer": True},
            ]
            for i in range(len(dates))
        ],
        "haystack_session_ids": [f"s{i}" for i in range(len(dates))],
    }


def test_lme_order_and_message() -> None:
    dates = ["2023/05/02 (Tue) 09:00", "2023/05/01 (Mon) 09:00"]
    records = [_lme_record(f"a{i}", "single-session-user", dates) for i in range(6)]
    records += [_lme_record(f"b{i}", "multi-session", dates) for i in range(3)]
    records += [_lme_record("c_abs", "multi-session", dates)]
    order = g3.lme_order(records, 42)
    assert order == g3.lme_order(list(reversed(records)), 42)
    assert "c_abs" not in order and len(order) == 9
    first3 = order[:3]
    assert sum(q.startswith("a") for q in first3) == 2  # proportional prefix (6:3)
    config = g3.load_config()
    message = g3.lme_message(records[0], config)
    assert message.index("### Session 1 (2023/05/01") < message.index("### Session 2 (2023/05/02")
    assert "user: s1\nassistant: ok" in message and "has_answer" not in message
    assert message.rstrip().endswith('say "I don\'t know".')
    plan = {"lme_questions": 4, "lme_seeds": [42]}
    reqs = g3.lme_requests(config, plan, order)
    assert [r["question_id"] for r in reqs] == order[:4]
    assert reqs[1]["request_seed"] == 42 * g3.SEED_STRIDE + 1
    assert g3.reply_text("<think>\n\n</think>\n\nIt was blue.") == "It was blue."


def test_judge_items_dedup_and_validation() -> None:
    questions = {"a": {"question_type": "single-session-user", "question": "q?", "answer": "blue"}}
    replies = [
        {"question_id": "a", "reply": "Blue. "},
        {"question_id": "a", "reply": "Blue."},
        {"question_id": "a", "reply": "Red."},
    ]
    items = g3.judge_items(questions, replies, "I don't know.")
    assert [i["source"] for i in items] == [
        "reader",
        "reader",
        "validation:reference",
        "validation:idk",
    ]
    assert [i["index"] for i in items] == [0, 1, 2, 3]
    msg = g3.judge_message(questions["a"], "Blue.")
    assert "Correct Answer: blue" in msg and "Model Response: Blue." in msg
    assert g3.parse_judgment("Yes.") == (1, True)


def test_first_difference_and_variance() -> None:
    a = np.array([1, 2, 3, 4], dtype=np.int32)
    assert analysis.first_difference(a, a.copy()) is None
    assert analysis.first_difference(a, np.array([1, 2, 9, 4], dtype=np.int32)) == 2
    assert analysis.first_difference(a, a[:3]) == 3
    rows = [{"question_index": 0, "correct": v} for v in (1, 1, 0, 0)]
    rows += [{"question_index": 1, "correct": v} for v in (1, 1, 1, 1)]
    var = analysis.per_question_variance(rows, "correct")
    # q0: 4 of 6 pairs disagree -> 2p(1-p) = 2/3 -> 1/3; q1: 0.
    assert var["questions"] == 2 and var["mean_p_one_minus_p"] == pytest.approx(1 / 6)
    assert analysis.half_width(0.08, 134, 4) == pytest.approx(1.96 * (0.16 / 536) ** 0.5)


def test_paired_bootstrap_recovers_injected_difference() -> None:
    rng = np.random.default_rng(0)
    rows = []
    p = rng.uniform(0.2, 0.95, size=120)
    for q in range(120):
        for seed in range(6):
            for arm, shift in (("fp32", 0.0), ("fp16", 0.0), ("bf16", -0.10)):
                rows.append(
                    {
                        "question_index": q,
                        "seed": seed,
                        "arm": arm,
                        "correct": int(rng.uniform() < max(p[q] + shift, 0.0)),
                    }
                )
    out = analysis.paired_summary(rows, "correct", list(g3.ARM_NAMES), 2000, 42, 0.05)
    assert out["n_questions"] == 120
    bf = out["bf16_minus_fp32"]
    assert bf["ci95"][0] < -0.10 < bf["ci95"][1] or abs(bf["diff"] + 0.10) < 0.03
    assert bf["ci95"][1] < 0 and not bf["within_margin_95"]
    fp = out["fp16_minus_fp32"]
    assert fp["ci95"][0] < 0 < fp["ci95"][1]
    assert fp["ci90"][0] >= fp["ci95"][0] and fp["ci90"][1] <= fp["ci95"][1]
    # A question missing from one arm is dropped from every arm.
    rows.append({"question_index": 999, "seed": 0, "arm": "fp32", "correct": 1})
    assert (
        analysis.paired_summary(rows, "correct", list(g3.ARM_NAMES), 200, 42, None)["n_questions"]
        == 120
    )


def _worker(root: Path, arm: str, task: str, rows: list[tuple[dict, str, list[int]]]) -> Path:
    import gzip

    path = root / f"qwen3.5-4b-{arm}-{task}"
    path.mkdir(parents=True)
    requests = [r for r, _, _ in rows]
    (path / "records.json").write_text(
        json.dumps(
            {
                "phase": "main",
                "model_id": "qwen3.5-4b",
                "arm": arm,
                "task": task,
                "requests": requests,
            }
        )
    )
    with gzip.open(path / "texts.jsonl.gz", "wt") as handle:
        for r, text, _ in rows:
            handle.write(json.dumps({"request_id": r["request_id"], "text": text}) + "\n")
    lens = [len(t) for _, _, t in rows]
    np.savez_compressed(
        path / "tokens.npz",
        offsets=np.concatenate([[0], np.cumsum(lens)]),
        token_ids=np.asarray([x for _, _, t in rows for x in t], dtype=np.int32),
    )
    (path / "summary.json").write_text(
        json.dumps(
            {
                "model": "qwen3.5-4b",
                "arm": arm,
                "task": task,
                "phase_name": "main",
                "engine": {"num_gpu_blocks": 10, "block_size": 528, "mamba_ssm_cache_dtype": arm},
                "phase": {
                    "wall_s": 10.0,
                    "output_tokens": 100,
                    "output_tok_per_s": 10.0,
                    "prompt_tokens": 50,
                    "prompt_tok_per_s": 5.0,
                    "requests": len(rows),
                    "finished": len(rows),
                    "mean_running": 2.0,
                    "preemptions_delta": 0.0,
                    "peak_kv_usage": 0.5,
                },
            }
        )
    )
    return path


def test_score_and_analyze_end_to_end(tmp_path: Path) -> None:
    prompts = g3.load_math_prompts(g3.load_config())
    workers = []
    for arm in g3.ARM_NAMES:
        math_rows, lme_rows = [], []
        for q in range(4):
            for seed in (42, 43):
                ok = not (arm == "bf16" and q == 0)
                answer = prompts[q]["answer"] if ok else "wrong"
                text = f"<think>\nwork\n</think>\n\n\\boxed{{{answer}}}"
                req = {
                    "request_id": f"m/q{q:03d}/s{seed}",
                    "question_index": q,
                    "seed": seed,
                    "prompt_len": 5,
                    "completion_len": 3,
                    "sum_logp": -1.0,
                    "finish_reason": "stop" if q != 3 else "length",
                }
                tokens = [1, 2, 3] if arm == "fp32" or q != 1 else [1, 9, 3]
                math_rows.append((req, text, tokens))
            req = {
                "request_id": f"l/x{q}/s42",
                "question_id": f"x{q}",
                "question_index": q,
                "seed": 42,
                "prompt_len": 9,
                "completion_len": 2,
                "sum_logp": -1.0,
                "finish_reason": "stop",
            }
            lme_rows.append((req, "<think>\n\n</think>\n\nIt was blue.", [5, 6]))
        workers.append(_worker(tmp_path, arm, "math", math_rows))
        workers.append(_worker(tmp_path, arm, "lme", lme_rows))
    rows = analysis.score_workers(workers)
    lme = {
        f"x{q}": {"answer": "blue", "question_type": "single-session-user", "question": "?"}
        for q in range(4)
    }
    analysis.add_containment(rows, workers, lme)
    assert len(rows) == 3 * (8 + 4)
    fp16_q1 = [
        r for r in rows if r["arm"] == "fp16" and r["task"] == "math" and r["question_index"] == 1
    ]
    assert all(r["first_diff_vs_fp32"] == 1 and not r["identical_to_fp32"] for r in fp16_q1)
    results = analysis.analyze(rows, None, analysis.worker_summaries([tmp_path]), 500, 42, 0.02)
    cell = results["cells"]["qwen3.5-4b/math"]
    assert cell["correct"]["fp32"]["mean"] == 1.0
    assert cell["correct"]["bf16_minus_fp32"]["diff"] == pytest.approx(-0.25)
    assert cell["cap_hit"]["fp32"]["mean"] == pytest.approx(0.25)
    assert cell["vs_fp32_tokens"]["fp16"]["identical"] == 6
    assert results["cells"]["qwen3.5-4b/lme"]["contains_answer"]["fp16_minus_fp32"]["diff"] == 0
    text = analysis.tables_md(results)
    assert "| qwen3.5-4b | math | correct | 4 | 100.0 | 100.0 | 75.0 |" in text
    assert len(results["throughput"]) == 6
