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
        assert arm["chat_template_kwargs"] == {"thinking": True}
        assert arm["reasoning_effort"] == "low"
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
    bad["arms"]["gptoss120"]["ctx_per_slot"] = 30000
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
    assert p["chat_template_kwargs"] == {"thinking": True} and p["reasoning_effort"] == "low"
    assert p["max_tokens"] == 32768 and p["cache_prompt"] is False
    assert p["repeat_penalty"] == 1.0 and p["dry_multiplier"] == 0.0
    assert p["messages"][0]["content"].endswith(lm2.MATH_SUFFIX)
    q = lm2.chat_payload(plan, "qwen235-q3", "math", item, 42)
    assert q["max_tokens"] == 16384 and q["top_k"] == 20 and "chat_template_kwargs" not in q
    assert q["seed"] == p["seed"]
    g = lm2.chat_payload(plan, "gptoss120", "math", item, 42)
    assert g["reasoning_effort"] == "medium" and g["max_tokens"] == 32768


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
    assert argv[argv.index("-c") + 1] == str(64 * 36864)
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
