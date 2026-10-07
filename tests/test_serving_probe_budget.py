from __future__ import annotations

import copy
import math
from pathlib import Path

import pytest

from harness.serving_probe import budget as rules
from harness.serving_probe.config import load_config
from harness.serving_probe.prompts import HarnessShape

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG = load_config(PROJECT_ROOT / "experiments" / "serving" / "serving-throughput-probe-v1.yaml")
BUDGET = CONFIG.section("budget")


def _open(rate: float, prompt_tokens: int = 9000 * 96, completed: int = 96) -> dict:
    return {
        "status": "valid",
        "result": {
            "request_throughput": rate,
            "prompt_tokens": prompt_tokens,
            "completed": completed,
        },
    }


def _replay(point_id: str, latencies: dict[int, float], *, tpot_ms: float = 20.0) -> dict:
    params = dict(CONFIG.points[point_id].params)
    per_step = {
        str(step): {"latency_s": {"mean": value}, "tpot_ms": {"p90": tpot_ms}}
        for step, value in latencies.items()
    }
    mean = sum(latencies.values()) / len(latencies)
    return {
        "point_id": point_id,
        "status": "valid",
        "params": params,
        "result": {
            "complete_steps": sorted(latencies),
            "per_step": per_step,
            "e2el_ms": {"mean": mean * 1000.0},
        },
    }


def _job_a() -> dict:
    h1 = {step: 2.0 + step for step in range(1, 7)}
    h1_a11y = {step: 4.0 + step for step in range(1, 7)}
    h2 = {step: 1.0 + 0.2 * step for step in range(1, 25)}
    h2[21] = 30.0
    return {
        "a1a": _open(2.0),
        "a1b": _open(2.1),
        "a1c": _open(2.05),
        "a2": _open(3.0, prompt_tokens=9000 * 160, completed=160),
        "r1": _replay("r1", h1),
        "r2": _replay("r2", h1_a11y),
        "r3": _replay("r3", h2),
        "r4": _replay("r4", {18: h2[18] + 50.0, 19: h2[19] + 40.0}),
        "x1-a1": _open(2.04),
        "x1-r1": _replay("x1-r1", {step: value * 1.02 for step, value in h1.items()}),
    }


def test_x1_outcomes() -> None:
    points = _job_a()
    passed = rules.evaluate_x1(points, max_relative_delta=0.05)
    assert passed["outcome"] == "pass"
    assert passed["a1_relative_delta"] == pytest.approx(0.02)
    assert passed["r1_relative_delta"] == pytest.approx(0.02)
    failing = copy.deepcopy(points)
    failing["x1-a1"]["result"]["request_throughput"] = 2.2
    assert rules.evaluate_x1(failing, max_relative_delta=0.05)["outcome"] == "fail"
    noisy = copy.deepcopy(points)
    noisy["a1b"]["result"]["request_throughput"] = 2.4
    assert rules.evaluate_x1(noisy, max_relative_delta=0.05)["outcome"] == "underpowered"
    missing = copy.deepcopy(points)
    missing["x1-r1"]["status"] = "truncated"
    result = rules.evaluate_x1(missing, max_relative_delta=0.05)
    assert result["outcome"] == "not-run" and result["missing_or_invalid"] == ["x1-r1"]


def test_stability_budgets_with_the_minimum() -> None:
    points = _job_a()
    stable = rules.stability(points, ("a1a", "a1b", "a1c"), 0.10)
    assert not stable["unstable"] and stable["budget_value"] == 2.0
    points["a1c"]["result"]["request_throughput"] = 1.5
    assert rules.stability(points, ("a1a", "a1b", "a1c"), 0.10)["unstable"]


def test_h1_profile_extrapolates_from_the_steady_window() -> None:
    profiles = rules.build_profiles(_job_a(), image_tokens=2040, unmeasured_multiplier=1.5)
    h1 = profiles["h1-screenshot"]
    assert h1.vm_per_replica == 40
    assert h1.latency(3) == 5.0
    shape = h1.shape
    from harness.serving_probe.prompts import modeled_prompt_tokens

    scale = modeled_prompt_tokens(shape, 15) / modeled_prompt_tokens(shape, 6)
    assert h1.latency(15) == pytest.approx(8.0 * scale)
    assert scale > 1.0


def test_h2_profile_uses_the_fold_step_for_later_folds() -> None:
    profiles = rules.build_profiles(_job_a(), image_tokens=2040, unmeasured_multiplier=1.5)
    h2 = profiles["h2-screenshot"]
    assert h2.vm_per_replica == 20
    assert h2.latency(21) == 30.0
    assert h2.latency(31) >= 30.0
    assert h2.latency(25) < 30.0
    think = profiles["h2-thinking-screenshot"]
    assert think.additive_s == pytest.approx(40.0)
    assert think.latency(5) == pytest.approx(h2.latency(5) + 40.0)
    a11y = profiles["h2-thinking-a11y"]
    assert a11y.additive_s == pytest.approx(40.0 + 2.0)


def test_unmeasured_thinking_and_a11y_use_conservative_fallbacks() -> None:
    points = _job_a()
    points["r4"]["status"] = "not-run"
    points["r2"]["status"] = "invalid"
    profiles = rules.build_profiles(points, image_tokens=2040, unmeasured_multiplier=1.5)
    think = profiles["h2-thinking-screenshot"]
    assert think.additive_s == pytest.approx((2048 - 300) * 0.020 * 1.5)
    assert think.flags == ("thinking-unmeasured-tpot-p90-x1.5",)
    assert profiles["h1-a11y"].flags == ("a11y-unmeasured-prompt-proportional-x1.5",)
    del points["r1"]
    with pytest.raises(rules.BudgetError, match="r1"):
        rules.build_profiles(points, image_tokens=2040, unmeasured_multiplier=1.5)


def test_closed_and_open_loop_formulas() -> None:
    shape = HarnessShape("h1", 1536, 64, 16, 300, 0, 2040, 4)
    profile = rules.Profile("p", "h1", {1: 10.0, 2: 10.0}, 40, shape)
    closed = rules.closed_loop_gpu_hours(
        profile, steps=2, episodes=360, t_env_s=2.5, gpus=1, multiplier=2.0
    )
    assert closed == pytest.approx(9 * (2 * (2.5 + 20.0)) / 3600)
    opened = rules.open_loop_gpu_hours(
        steps=15, episodes=360, gpus=1, multiplier=2.0, requests_per_s=3.0
    )
    assert opened == pytest.approx(360 * 15 * 2.0 / 3.0 / 3600)
    with pytest.raises(rules.BudgetError):
        rules.open_loop_gpu_hours(steps=1, episodes=1, gpus=1, multiplier=1, requests_per_s=0)


def test_rung_multipliers_measured_and_unmeasured() -> None:
    rungs = BUDGET["q2"]["rungs"]
    job_a = _job_a()
    job_c = {"c27-a1": _open(0.5), "c35-a1": _open(4.0)}
    measured = rules.rung_multipliers(
        rungs, job_a=job_a, job_c=job_c, x1_outcome="pass", unmeasured_multiplier=1.5
    )
    assert measured["qwen3.5-27b"]["multiplier"] == pytest.approx(4.0)
    assert measured["qwen3.5-35b-a3b"]["multiplier"] == pytest.approx(0.5)
    assert measured["qwen3.5-4b"]["multiplier"] == 1.0
    penalised = rules.rung_multipliers(
        rungs, job_a=job_a, job_c=job_c, x1_outcome="fail", unmeasured_multiplier=1.5
    )
    assert penalised["qwen3.5-27b"]["multiplier"] == pytest.approx(6.0)
    absent = rules.rung_multipliers(
        rungs, job_a=job_a, job_c=None, x1_outcome="pass", unmeasured_multiplier=1.5
    )
    assert absent["qwen3.5-27b"]["multiplier"] == pytest.approx(3.0 * 1.5)
    assert absent["qwen3.5-35b-a3b"]["multiplier"] == pytest.approx(1.5)


def test_q2_projection_totals_and_decision() -> None:
    projection = rules.project_q2(BUDGET, job_a=_job_a(), job_c=None, x1_outcome="pass")
    assert len(projection["cells"]) == 16
    total = sum(cell["gpu_hours"] for cell in projection["cells"])
    assert projection["total_gpu_hours"] == pytest.approx(total)
    assert all(cell["gpu_hours"] >= cell["closed_loop_gpu_hours"] for cell in projection["cells"])
    expected = (
        "rescope-before-gauntlet"
        if total > 90
        else "dossier-overestimated"
        if total < 15
        else "within-dossier-range"
    )
    assert projection["decision"] == expected
    assert len(projection["sensitivity"]) == 3 * 3 * 2
    h2_cells = [c for c in projection["cells"] if c["harness"] == "h2"]
    assert all(c["steps"] == 100 and c["vm_per_replica"] == 20 for c in h2_cells)


def _offline(duration: float, completions: int) -> dict:
    return {"status": "valid", "result": {"duration_s": duration, "completions": completions}}


def test_q1_projection_rules() -> None:
    job_b = {"b2": _offline(90.0, 32), "b3": _offline(80.0, 64), "b6": _offline(160.0, 24)}
    projection = rules.project_q1(BUDGET, job_b=job_b, x1_outcome="pass")
    per = projection["per_completion_gpu_s"]
    assert per == {
        "b2": pytest.approx(90 / 32),
        "b3": pytest.approx(80 / 64),
        "b6": pytest.approx(160 / 24),
    }
    assert projection["single_turn_gpu_hours"] == pytest.approx(2000 * 90 / 32 / 3600)
    assert projection["three_turn_gpu_hours"] == pytest.approx(2000 * sum(per.values()) / 3600)
    assert projection["decision"] == "within-cap"
    penalised = rules.project_q1(BUDGET, job_b=job_b, x1_outcome="underpowered")
    assert penalised["single_turn_gpu_hours"] == pytest.approx(
        1.5 * projection["single_turn_gpu_hours"]
    )
    del job_b["b3"]
    fallback = rules.project_q1(BUDGET, job_b=job_b, x1_outcome="pass")
    assert "b3-unmeasured-used-b6" in fallback["flags"]
    heavy = {"b2": _offline(400.0, 32), "b3": _offline(80.0, 64), "b6": _offline(160.0, 24)}
    assert rules.project_q1(BUDGET, job_b=heavy, x1_outcome="pass")["decision"].startswith("cut")
    with pytest.raises(rules.BudgetError):
        rules.project_q1(BUDGET, job_b={"b3": _offline(1, 1)}, x1_outcome="pass")


def test_relative_helpers() -> None:
    assert rules.relative_range([1.0]) is None
    assert rules.relative_range([1.0, 3.0]) == pytest.approx(1.0)
    with pytest.raises(rules.BudgetError):
        rules.relative_delta(1.0, 0.0)
    assert math.isclose(rules.relative_delta(1.05, 1.0), 0.05)
