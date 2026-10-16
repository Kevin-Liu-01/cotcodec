"""LM2 (D129, exploratory): plan, order, prompts, scoring, sandbox grader and driver helpers."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness import lm2_resident_eval as lm2  # noqa: E402
from scripts import lm2_code_grader as grader  # noqa: E402
from scripts import lm2_score as score  # noqa: E402
from scripts import run_lm2_eval as drv  # noqa: E402
from scripts.fetch_open_model import DEFAULT_REGISTRY, load_registry  # noqa: E402


@pytest.fixture(scope="module")
def plan() -> dict:
    return lm2.load_plan()


def test_plan_is_exploratory_and_arms_match_the_registry(plan: dict) -> None:
    assert plan["status"] == "EXPLORATORY"
    registry = load_registry(DEFAULT_REGISTRY)["models"]
    for arm_id, arm in plan["arms"].items():
        entry = registry[arm["model_id"]]
        assert entry["runtime"] == "llama.cpp" and entry["trust_remote_code"] is False, arm_id
        files = entry["required_files"]
        assert arm["gguf"] in files or any(
            pattern.endswith("/*") and arm["gguf"].startswith(pattern[:-1]) for pattern in files
        ), arm_id
    assert plan["reference_arm"] == "v4f-q8"
    assert set(plan["arms"]) == {"v4f-q8", "v4f-iq3", "v4f-q2", "qwen235-q3", "gptoss120"}


def test_the_v4_arms_share_one_pinned_template(plan: dict) -> None:
    v4 = [a for a in plan["arms"].values() if a["family"] == "deepseek-v4-flash-0731"]
    assert len(v4) == 3
    for arm in v4:
        path = ROOT / arm["chat_template_file"]
        assert lm2.sha256_file(path) == arm["chat_template_sha256"]
        assert arm["chat_template_kwargs"] == {"thinking": False}
        assert "reasoning_effort" not in arm and arm["thinking"] is False
        assert arm["sampling"] == {"temperature": 1.0, "top_p": 1.0, "top_k": 0, "min_p": 0.0}
    # The template adds no effort prefix for "low", and opens the reasoning block.
    text = (ROOT / v4[0]["chat_template_file"]).read_text()
    assert "reasoning_effort == 'high'" in text and "reasoning_effort == 'max'" in text


def test_plan_validation_rejects_tampering(plan: dict) -> None:
    bad = copy.deepcopy(plan)
    bad["status"] = "CONFIRMATORY"
    with pytest.raises(lm2.LM2Error):
        lm2.validate_plan(bad)
    bad = copy.deepcopy(plan)
    bad["arms"]["gptoss120"]["ctx_per_slot"] = 16000
    with pytest.raises(lm2.LM2Error):
        lm2.validate_plan(bad)
    bad = copy.deepcopy(plan)
    del bad["arms"]["v4f-q2"]["sampling"]["min_p"]
    with pytest.raises(lm2.LM2Error):
        lm2.validate_plan(bad)


def _items(task: str, n: int, **extra) -> list[dict]:
    return [{"id": f"{task}/{i}", "source": task, **extra} for i in range(n)]


def test_order_is_item_major_alternating_and_prefix_closed() -> None:
    per_task = {"math": _items("math", 3), "code": _items("code", 5)}
    order = lm2.request_order(per_task, ["math", "code"], [42, 43, 44], 42)
    assert len(order) == (3 + 5) * 3
    # Seeds of an item are adjacent and in plan order.
    assert [o[3] for o in order[:3]] == [42, 43, 44]
    assert len({o[1]["id"] for o in order[:3]}) == 1
    # Tasks alternate while both have items.
    tasks = [o[0] for o in order[::3]]
    assert tasks[:6] == ["math", "code"] * 3 and tasks[6:] == ["code", "code"]
    # A cap is a prefix of the same permutation.
    capped = lm2.request_order(per_task, ["math", "code"], [42, 43, 44], 42, {"code": 2})
    full_code = [o[1]["id"] for o in order if o[0] == "code"]
    capped_code = [o[1]["id"] for o in capped if o[0] == "code"]
    assert capped_code == full_code[: 2 * 3]
    # Deterministic.
    again = lm2.request_order(per_task, ["math", "code"], [42, 43, 44], 42)
    assert [(o[0], o[1]["id"], o[3]) for o in again] == [(o[0], o[1]["id"], o[3]) for o in order]


def test_request_seed_is_shared_by_arms_and_differs_by_seed() -> None:
    a = lm2.request_seed(42, "aime_2026/1")
    assert a == lm2.request_seed(42, "aime_2026/1")
    assert a != lm2.request_seed(43, "aime_2026/1")
    assert 0 <= a < 2**31


def test_select_items_numeric_filter_and_date_window(plan: dict) -> None:
    math_items = [
        {"id": "aime_2026/1", "source": "aime_2026", "answer": "277"},
        {"id": "arxivmath_0626/1", "source": "arxivmath_0626", "answer": "\\frac{1}{4}"},
        {"id": "arxivmath_0626/2", "source": "arxivmath_0626", "answer": "n(2^{n-1}-1)+1"},
        {"id": "other/1", "source": "other", "answer": "1"},
    ]
    got = [i["id"] for i in lm2.select_items("math", plan["tasks"]["math"], math_items)]
    assert got == ["aime_2026/1", "arxivmath_0626/1"]
    code_items = [
        {"id": "lcb_v6/a", "source": "lcb_v6", "contest_date": "2024-12-31T00:00:00"},
        {"id": "lcb_v6/b", "source": "lcb_v6", "contest_date": "2025-02-01T00:00:00"},
        {"id": "lcb_v6/c", "source": "lcb_v6", "contest_date": "2025-05-01T00:00:00"},
    ]
    got = [i["id"] for i in lm2.select_items("code", plan["tasks"]["code"], code_items)]
    assert got == ["lcb_v6/b"]


def test_payloads_set_every_sampler_and_the_mode(plan: dict) -> None:
    item = {"id": "aime_2026/1", "problem": "Find x."}
    p = lm2.chat_payload(plan, "v4f-q2", "math", item, 42)
    assert p["temperature"] == 1.0 and p["top_k"] == 0 and p["min_p"] == 0.0
    assert p["chat_template_kwargs"] == {"thinking": False} and "reasoning_effort" not in p
    assert p["max_tokens"] == 16384 and p["cache_prompt"] is False
    assert p["repeat_penalty"] == 1.0 and p["dry_multiplier"] == 0.0
    assert p["messages"][0]["content"].endswith(lm2.MATH_SUFFIX)
    q = lm2.chat_payload(plan, "qwen235-q3", "math", item, 42)
    assert q["max_tokens"] == 16384 and q["top_k"] == 20 and "chat_template_kwargs" not in q
    assert q["seed"] == p["seed"]
    g = lm2.chat_payload(plan, "gptoss120", "math", item, 42)
    assert g["reasoning_effort"] == "low" and g["max_tokens"] == 16384


def test_code_prompt_follows_livecodebench() -> None:
    stdin = lm2.code_prompt({"question_content": "Q", "starter_code": ""})
    assert "Read the inputs from stdin" in stdin and "# YOUR CODE HERE" in stdin
    func = lm2.code_prompt({"question_content": "Q", "starter_code": "class Solution:\n    pass"})
    assert "starter code" in func and "class Solution" in func
    assert stdin.startswith(lm2.LCB_SYSTEM)


def test_extract_code_takes_the_last_fenced_block() -> None:
    text = "x\n```python\nprint(1)\n```\nthen\n```python\nprint(2)\n```\n"
    assert lm2.extract_code(text) == "print(2)"
    assert lm2.extract_code("no code") == ""


def test_math_scoring_uses_checker_v2() -> None:
    assert lm2.score_math("so \\boxed{\\frac{7}{2}}", "\\frac{7}{2}")["correct"]
    assert lm2.score_math("so \\boxed{3.5}", "\\frac{7}{2}")["correct"]
    assert not lm2.score_math("so \\boxed{4}", "\\frac{7}{2}")["correct"]
    assert lm2.score_math(None, "1") == {"has_answer": False, "correct": False}


def test_multiple_choice_takes_the_last_answer_line() -> None:
    assert lm2.mc_answer("Answer: B\nwait\nAnswer: D") == "D"
    assert lm2.score_knowledge("**Answer: C**", "C")["correct"]
    assert lm2.mc_answer("none") is None


def test_final_text_requires_closed_reasoning_for_thinking_arms() -> None:
    sep = {"content": "\\boxed{1}", "reasoning_content": "think"}
    assert score.final_text(sep, True) == ("\\boxed{1}", "separated")
    cut = {"content": "", "reasoning_content": "still thinking", "finish_reason": "length"}
    assert score.final_text(cut, True)[0] is None
    raw = {"content": "a</think>b \\boxed{2}", "reasoning_content": ""}
    assert score.final_text(raw, True) == ("b \\boxed{2}", "think_tag")
    unclosed = {"content": "thinking \\boxed{3} more", "reasoning_content": ""}
    assert score.final_text(unclosed, True)[0] is None
    assert score.final_text(unclosed, False)[0] == unclosed["content"]


def test_stdio_and_functional_comparisons() -> None:
    assert lm2.stdio_match("1 2\n3\n", "1 2\n3")
    assert lm2.stdio_match("1  2 \n", "1 2")
    assert lm2.stdio_match("0.50\n", "0.5")
    assert not lm2.stdio_match("1\n2\n", "1\n")
    assert not lm2.stdio_match("Yes", "No")
    assert lm2.functional_match("[1, 2]", "[1, 2]")
    assert lm2.functional_match("[[1, 2]]", "[1, 2]")
    assert not lm2.functional_match("3", "4")
    assert not lm2.functional_match("not json", "4")


def test_cluster_bootstrap_is_deterministic_and_brackets_the_point() -> None:
    a = [1.0, 1.0, 0.0, 1.0, 2 / 3, 0.0, 1.0, 1.0]
    b = [1.0, 0.0, 0.0, 1.0, 1 / 3, 0.0, 0.0, 1.0]
    r1 = lm2.cluster_bootstrap_diff(a, b, draws=2000)
    r2 = lm2.cluster_bootstrap_diff(a, b, draws=2000)
    assert r1 == r2
    assert r1["ci95"][0] <= r1["diff"] <= r1["ci95"][1]
    assert r1["diff"] == pytest.approx(100 * (sum(a) - sum(b)) / len(a), abs=0.01)
    assert r1["items_a_better"] == 3 and r1["items_b_better"] == 0


def test_paired_rows_use_common_keys_only() -> None:
    rows_a = [
        {"item_id": "x", "seed": 42, "correct": True},
        {"item_id": "x", "seed": 43, "correct": False},
        {"item_id": "y", "seed": 42, "correct": True},
    ]
    rows_b = [{"item_id": "x", "seed": 42, "correct": False}]
    assert lm2.paired_rows(rows_a, rows_b) == ([1.0], [0.0])


def _grade(row: dict) -> dict:
    return grader.grade_one(row, timeout_s=3.0, mem_bytes=1 << 30)


def test_grader_stdin_programs() -> None:
    tests = [{"input": "1 2\n", "output": "3\n"}, {"input": "5 6\n", "output": "11\n"}]
    ok = {
        "key": "k",
        "item_id": "i",
        "testtype": "stdin",
        "func_name": None,
        "tests": tests,
        "code": "a, b = map(int, input().split())\nprint(a + b)",
    }
    assert _grade(ok)["passed"]
    wrong = dict(ok, code="a, b = map(int, input().split())\nprint(a - b)")
    v = _grade(wrong)
    assert not v["passed"] and v["failure"] == "wrong_answer" and v["passed_tests"] == 0
    crash = dict(ok, code="raise SystemExit(3)")
    assert _grade(crash)["failure"] == "runtime_error"
    assert _grade(dict(ok, code=""))["failure"] == "no_code"


def test_grader_timeout_and_functional() -> None:
    loop = {
        "key": "k",
        "item_id": "i",
        "testtype": "stdin",
        "func_name": None,
        "tests": [{"input": "", "output": "1"}],
        "code": "while True:\n    pass",
    }
    v = grader.grade_one(loop, timeout_s=1.0, mem_bytes=1 << 30)
    assert v["failure"] == "timeout" and v["elapsed_s"] < 10
    func = {
        "key": "k",
        "item_id": "i",
        "testtype": "functional",
        "func_name": "twoSum",
        "tests": [{"input": "[2, 7, 11]\n9", "output": "[0, 1]"}],
        "code": (
            "class Solution:\n"
            "    def twoSum(self, nums: List[int], target: int) -> List[int]:\n"
            "        print('noise')\n"
            "        seen = {}\n"
            "        for i, x in enumerate(nums):\n"
            "            if target - x in seen:\n"
            "                return [seen[target - x], i]\n"
            "            seen[x] = i\n"
        ),
    }
    assert _grade(func)["passed"]
    assert not _grade(dict(func, tests=[{"input": "[2, 7]\n10", "output": "[0, 1]"}]))["passed"]


def test_driver_helpers(plan: dict, tmp_path: Path) -> None:
    argv = drv.server_argv(plan, "v4f-q2", Path("/m/x.gguf"), 18941, 16)
    assert argv[:2] == [plan["llama_server"], "-m"]
    for flag in ("-ngl", "all", "--split-mode", "layer", "-fit", "off", "--jinja", "--metrics"):
        assert flag in argv
    assert argv[argv.index("-np") + 1] == "64"
    assert argv[argv.index("-c") + 1] == str(64 * 20480)
    assert argv[argv.index("--chat-template-file") + 1].endswith(
        "deepseek-v4-flash-0731-unsloth.jinja"
    )
    assert "--chat-template-file" not in drv.server_argv(plan, "qwen235-q3", Path("/m"), 1, 1)
    metrics = drv.parse_metrics(
        "# HELP x\nllamacpp:tokens_predicted_total 123\nllamacpp:n_decode_total 4\n"
    )
    assert metrics == {"tokens_predicted_total": 123.0, "n_decode_total": 4.0}
    slots = [
        {"is_processing": True, "next_token": [{"n_decoded": 7}]},
        {"is_processing": False, "next_token": [{"n_decoded": 99}]},
        {"is_processing": True, "next_token": {"n_decoded": 3}},
    ]
    assert drv.slots_snapshot(slots) == {"busy_slots": 2, "inflight_decoded": 10}
    path = tmp_path / "responses-1.jsonl"
    path.write_text(
        json.dumps({"key": "a", "status": "ok"})
        + "\n"
        + json.dumps({"key": "b", "status": "error"})
        + "\n{broken"
    )
    assert set(drv.completed_keys([path])) == {"a"}


def test_driver_rejects_owned_flags_and_diag_mode_outside_diag(plan: dict, tmp_path: Path) -> None:
    args = drv.build_parser().parse_args(
        [
            "run",
            "--plan",
            str(lm2.PLAN_PATH),
            "--arm",
            "v4f-q2",
            "--phase",
            "main",
            "--seeds",
            "42",
            "--output-dir",
            str(tmp_path),
            "--allocation-minutes",
            "5",
            "--diag-chat-mode",
        ]
    )
    runner = drv.Runner(args)
    with pytest.raises(lm2.LM2Error):
        runner.setup()


def test_analysis_on_synthetic_grades(tmp_path: Path) -> None:
    from scripts import analyze_lm2 as ana

    rows = []
    for arm, acc in (
        ("v4f-q8", 1.0),
        ("v4f-q2", 0.5),
        ("v4f-iq3", 1.0),
        ("qwen235-q3", 0.0),
        ("gptoss120", 1.0),
    ):
        for i in range(6):
            for seed in (42, 43, 44):
                correct = (i % 2 == 0) or acc == 1.0 if acc else False
                rows.append(
                    {
                        "arm": arm,
                        "task": "math",
                        "item_id": f"m/{i}",
                        "source": "aime_2026",
                        "seed": seed,
                        "rank": i,
                        "correct": correct,
                        "has_answer": True,
                        "finish_reason": "stop",
                        "completion_tokens": 100 + i,
                    }
                )
    grades = tmp_path / "grades.jsonl"
    grades.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    caps = tmp_path / "caps.json"
    caps.write_text(json.dumps({"math": 4}))
    out_json, out_md = tmp_path / "r.json", tmp_path / "t.md"
    assert (
        ana.main(
            [
                "--grades",
                str(grades),
                "--caps",
                str(caps),
                "--out-json",
                str(out_json),
                "--out-md",
                str(out_md),
            ]
        )
        == 0
    )
    result = json.loads(out_json.read_text())
    assert result["accuracy"]["v4f-q8"]["math"]["items"] == 4
    assert result["accuracy"]["v4f-q2"]["math"]["accuracy"] == 50.0
    g4 = result["paired"]["g4"]["v4f-q2 - v4f-q8"]["math"]
    assert g4["diff"] == -50.0 and g4["n_items"] == 4
    assert result["arms"]["v4f-q2"]["fit"]["tier_at_32k"] == "Yes"
    assert result["arms"]["v4f-q8"]["fit"]["tier_at_32k"] == "No"
    assert "EXPLORATORY" in out_md.read_text()


def _jsonl(path: Path, rows: list[dict]) -> Path:
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return path


def test_finalize_censored_original_overrides_rerun(tmp_path: Path) -> None:
    base = {"arm": "v4f-q2", "task": "math", "source": "aime_2026", "rank": 0, "has_answer": True}
    pre = _jsonl(
        tmp_path / "pre.jsonl",
        [
            # Re-run of key a (later run id) that finished correctly within the budget.
            {
                **base,
                "key": "v4f-q2|math|m/0|42",
                "item_id": "m/0",
                "seed": 42,
                "job_id": "20261016T081313Z-1",
                "correct": True,
                "completion_tokens": 900,
            },
            # Re-run of key b whose original was cancelled below the budget (undetermined).
            {
                **base,
                "key": "v4f-q2|math|m/0|43",
                "item_id": "m/0",
                "seed": 43,
                "job_id": "20261016T081313Z-1",
                "correct": True,
                "completion_tokens": 800,
            },
        ],
    )
    censored = _jsonl(
        tmp_path / "c.jsonl",
        [
            {
                **base,
                "key": "v4f-q2|math|m/0|42",
                "item_id": "m/0",
                "seed": 42,
                "censored": True,
                "job_id": "20261016T064613Z-1",
                "min_tokens": 6574,
                "correct": False,
                "has_answer": False,
            },
            {
                **base,
                "key": "v4f-q2|math|m/0|43",
                "item_id": "m/0",
                "seed": 43,
                "censored": True,
                "job_id": "20261016T064613Z-1",
                "min_tokens": 3993,
                "correct": False,
                "has_answer": False,
            },
        ],
    )
    verdicts = _jsonl(tmp_path / "v.jsonl", [])
    out = tmp_path / "grades.jsonl"
    assert (
        score.main(
            [
                "finalize",
                "--pre",
                str(pre),
                "--verdicts",
                str(verdicts),
                "--censored",
                str(censored),
                "--analysis-cap",
                "5120",
                "--out",
                str(out),
            ]
        )
        == 0
    )
    rows = {r["key"]: r for r in map(json.loads, out.read_text().splitlines())}
    assert rows["v4f-q2|math|m/0|42"]["censored"] is True
    assert rows["v4f-q2|math|m/0|42"]["correct"] is False
    assert rows["v4f-q2|math|m/0|42"]["overrides_job_ids"] == ["20261016T081313Z-1"]
    # Below the budget the original is undetermined, so the re-run stands.
    assert rows["v4f-q2|math|m/0|43"]["correct"] is True
    assert "censored" not in rows["v4f-q2|math|m/0|43"]


def test_outcomes_at_budget_uses_the_earliest_determined_attempt() -> None:
    graded = [
        {
            "key": "k1",
            "job_id": "b",
            "correct": True,
            "completion_tokens": 3000,
            "finish_reason_raw": "stop",
        },
        {
            "key": "k2",
            "job_id": "a",
            "correct": True,
            "completion_tokens": 6000,
            "finish_reason_raw": "stop",
        },
        {
            "key": "k3",
            "job_id": "b",
            "correct": True,
            "completion_tokens": 5120,
            "finish_reason_raw": "length",
        },
    ]
    censored = [{"key": "k1", "job_id": "a", "min_tokens": 4000, "censored": True}]
    at = lambda b: {r["key"]: r["correct"] for r in lm2.outcomes_at_budget(graded, censored, b)}  # noqa: E731
    assert at(3500) == {"k1": False, "k2": False, "k3": False}  # k1: original past 3,500
    assert at(5120) == {"k1": True, "k2": False, "k3": False}  # original undetermined at 5,120
    assert at(8192) == {"k1": True, "k2": True, "k3": False}


def test_item_means_do_not_depend_on_row_order() -> None:
    rows = [{"item_id": f"i{n % 7}", "seed": 42 + n % 3, "correct": n % 5 == 0} for n in range(40)]
    a = lm2.item_means(rows)
    b = lm2.item_means(list(reversed(rows)))
    assert list(a) == sorted(a) and a == b and list(a.values()) == list(b.values())
    assert lm2.bootstrap_mean(list(a.values()), draws=500) == lm2.bootstrap_mean(
        list(b.values()), draws=500
    )


def test_task_mean_bootstrap_and_mdd() -> None:
    pairs = {"math": ([1.0, 0.0, 1.0, 1.0], [0.0, 0.0, 1.0, 0.0]), "code": ([0.0, 1.0], [0.0, 1.0])}
    r = lm2.task_mean_bootstrap(pairs, draws=2000)
    assert r["diff"] == pytest.approx(100 * (0.5 + 0.0) / 2, abs=0.01)
    assert r["ci95"][0] <= r["diff"] <= r["ci95"][1] and r["mdd80"] > 0
    d = lm2.cluster_bootstrap_diff([1.0, 0.0, 1.0], [0.0, 0.0, 1.0], draws=2000)
    assert d["mdd80"] == pytest.approx(lm2.MDD_FACTOR * d["se"], abs=0.1)


def test_censor_tasks_maps_open_tasks_by_prompt_length_and_task_order(tmp_path: Path) -> None:
    pre = _jsonl(
        tmp_path / "pre.jsonl",
        [
            {
                "arm": "v4f-q8",
                "item_id": "c/1",
                "task": "code",
                "rank": 0,
                "source": "lcb_v6",
                "seed": s,
                "prompt_tokens": 611,
                "job_id": "x",
            }
            for s in (42, 43, 44)
        ]
        + [
            {
                "arm": "v4f-q2",
                "item_id": "c/1",
                "task": "code",
                "rank": 0,
                "source": "lcb_v6",
                "seed": 43,
                "prompt_tokens": 611,
                "job_id": "20261016T064613Z-1",
            },
        ],
    )
    tasks = _jsonl(
        tmp_path / "tasks.jsonl",
        [
            {"task": 7, "prompt_tokens": 611, "n_gen": 5403, "released": False, "cancelled": True},
            {"task": 3, "prompt_tokens": 611, "n_gen": 6000, "released": False, "cancelled": True},
            {"task": 5, "prompt_tokens": 611, "n_gen": 900, "released": True, "cancelled": False},
            {"task": 9, "prompt_tokens": 99, "n_gen": 7000, "released": False, "cancelled": True},
        ],
    )
    out = tmp_path / "c.jsonl"
    assert (
        score.main(
            [
                "censor-tasks",
                "--pre",
                str(pre),
                "--tasks",
                str(tasks),
                "--arm",
                "v4f-q2",
                "--run-id",
                "20261016T064613Z-1",
                "--job",
                "1842",
                "--cap",
                "code=1",
                "--max-tokens",
                "16384",
                "--length-arms",
                "v4f-q8",
                "--out",
                str(out),
            ]
        )
        == 0
    )
    rows = [json.loads(line) for line in out.read_text().splitlines()]
    assert [(r["seed"], r["min_tokens"], r["server_task"]) for r in rows] == [
        (42, 6000, 3),
        (44, 5403, 7),
    ]
    assert all(r["censored"] and r["job_id"] == "20261016T064613Z-1" for r in rows)
