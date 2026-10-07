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
LIMIT = 0.10
MAX_LEN = 131072
PROFILE_ARGS = dict(
    image_tokens=2040, unmeasured_multiplier=1.5, a11y_tokens=6144, thinking_output_tokens=2048
)


def _open(
    rate: float, prompt_tokens: int = 9000 * 96, completed: int = 96, output: int = 300
) -> dict:
    return {
        "status": "valid",
        "result": {
            "request_throughput": rate,
            "prompt_tokens": prompt_tokens,
            "output_tokens": output * completed,
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


def _q2(job_a: dict, **overrides) -> dict:
    kwargs = dict(job_c=None, x1_outcome="pass", unstable_limit=LIMIT, max_model_len=MAX_LEN)
    kwargs.update(overrides)
    return rules.project_q2(BUDGET, job_a=job_a, **kwargs)


def _cell(projection: dict, harness: str, observation: str, rung: str = "qwen3.5-9b") -> dict:
    return next(
        c
        for c in projection["cells"]
        if c["rung"] == rung and c["harness"] == harness and c["observation"] == observation
    )


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


def test_x1_needs_all_three_a1_seeds_to_pass() -> None:
    # Two close seeds and an invalid third used to pass (review finding).
    points = _job_a()
    points["a1c"]["status"] = "invalid"
    points["a1c"]["result"]["request_throughput"] = 0.5
    verdict = rules.evaluate_x1(points, max_relative_delta=0.05)
    assert verdict["outcome"] == "underpowered"
    assert verdict["a1_seeds_valid"] == 2
    assert verdict["reason"] == "fewer than three valid A1 seed points"


def test_stability_noise_multiplier() -> None:
    points = _job_a()
    stable = rules.stability(points, ("a1a", "a1b", "a1c"), LIMIT)
    assert not stable["unstable"] and stable["noise_multiplier"] == 1.0
    assert "budget_value" not in stable
    points["a1c"]["result"]["request_throughput"] = 1.5
    unstable = rules.stability(points, ("a1a", "a1b", "a1c"), LIMIT)
    assert unstable["unstable"] and unstable["noise_multiplier"] == pytest.approx(2.1 / 1.5)
    points["a1c"]["status"] = "invalid"
    incomplete = rules.stability(points, ("a1a", "a1b", "a1c"), LIMIT)
    assert incomplete["noise_multiplier"] == pytest.approx(1.10)
    points["a1b"]["result"]["request_throughput"] = 3.0
    wide = rules.stability(points, ("a1a", "a1b", "a1c"), LIMIT)
    assert wide["noise_multiplier"] == pytest.approx(1.5)


def test_unstable_a1_raises_every_q2_cell() -> None:
    # The UNSTABLE rule used to change no number (review finding).
    base = _q2(_job_a())
    points = _job_a()
    points["a1b"]["result"]["request_throughput"] = 1.0
    unstable = _q2(points)
    factor = 2.05 / 1.0
    assert unstable["a1_noise"]["noise_multiplier"] == pytest.approx(factor)
    assert unstable["total_gpu_hours"] == pytest.approx(base["total_gpu_hours"] * factor)
    assert all(any("a1-noise" in flag for flag in c["flags"]) for c in unstable["cells"])


def test_h1_profile_extrapolates_from_the_steady_window() -> None:
    profiles = rules.build_profiles(_job_a(), **PROFILE_ARGS)
    h1 = profiles["h1-screenshot"]
    assert h1.vm_per_replica == 40
    assert h1.latency(3) == 5.0
    shape = h1.shape
    from harness.serving_probe.prompts import modeled_prompt_tokens

    scale = modeled_prompt_tokens(shape, 15) / modeled_prompt_tokens(shape, 6)
    assert h1.latency(15) == pytest.approx(8.0 * scale)
    assert scale > 1.0


def test_h2_profile_uses_the_fold_step_for_later_folds() -> None:
    profiles = rules.build_profiles(_job_a(), **PROFILE_ARGS)
    think = profiles["h2-thinking-screenshot"]
    assert think.vm_per_replica == 20
    assert think.latency(21) == pytest.approx(30.0 + 40.0)
    assert think.latency(31) >= 70.0
    assert think.latency(25) < 70.0
    assert think.additive_s == pytest.approx(40.0)
    assert think.cell_output == 2048
    a11y = profiles["h2-thinking-a11y"]
    assert a11y.additive_s == pytest.approx(40.0 + 2.0)
    assert a11y.cell_output == 2048
    # The a11y cell is priced with its accessibility tree on every step.
    assert a11y.mean_prompt_tokens(100) - think.mean_prompt_tokens(100) == pytest.approx(6144)


def test_unmeasured_thinking_and_a11y_use_conservative_fallbacks() -> None:
    points = _job_a()
    points["r4"]["status"] = "not-run"
    points["r2"]["status"] = "invalid"
    profiles = rules.build_profiles(points, **PROFILE_ARGS)
    think = profiles["h2-thinking-screenshot"]
    assert think.additive_s == pytest.approx((2048 - 300) * 0.020 * 1.5)
    assert think.flags == ("thinking-unmeasured-tpot-p90-x1.5",)
    h1_a11y = profiles["h1-a11y"]
    assert h1_a11y.flags == ("a11y-unmeasured-prompt-proportional-x1.5",)
    assert h1_a11y.cell_shape.a11y_tokens == 6144 and h1_a11y.shape.a11y_tokens == 0
    del points["r1"]
    with pytest.raises(rules.BudgetError, match="r1"):
        rules.build_profiles(points, **PROFILE_ARGS)


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


def test_h1_screenshot_cell_by_hand() -> None:
    """Section 8's formulas, evaluated by hand for the 9B H1 screenshot cell."""
    projection = _q2(_job_a())
    cell = _cell(projection, "h1", "screenshot")

    # Modelled prompt tokens (system 1,536 + task 64; 2,040 + 2 tokens per visible
    # screenshot; window of 4 responses of 300; 16 per action outside the window).
    def prompt(t: int) -> int:
        images, responses, actions = min(t, 5), min(t - 1, 4), max(0, t - 5)
        return 1600 + 2042 * images + 300 * responses + 16 * actions

    assert [prompt(t) for t in (1, 5, 6)] == [3642, 13010, 13026]
    # L(t) = 2 + t for measured steps 1-6; later steps scale step 6 (8.0 s) by prompt.
    latency = [2.0 + t for t in range(1, 7)] + [8.0 * prompt(t) / 13026 for t in range(7, 16)]
    closed = 1 * math.ceil(360 / 40) * sum(2.5 + value for value in latency) / 3600
    assert cell["closed_loop_gpu_hours"] == pytest.approx(closed)
    assert closed == pytest.approx(0.357354, rel=1e-5)
    # Open loop: a2 runs 3.0 req/s at 9,000 prompt and 300 output tokens per request.
    mean_prompt = sum(prompt(t) for t in range(1, 16)) / 15
    assert mean_prompt == pytest.approx(172610 / 15)
    rate = 3.0 / max(mean_prompt / 9000, 300 / 300)
    opened = 360 * 15 * 1 * 1.0 / rate / 3600
    assert cell["open_loop_gpu_hours"] == pytest.approx(opened)
    assert opened == pytest.approx(0.639296, rel=1e-5)
    assert cell["binding"] == "open-loop"
    assert cell["gpu_hours"] == pytest.approx(max(closed, opened))


def test_thinking_cells_price_output_length_in_the_open_loop_bound() -> None:
    projection = _q2(_job_a())
    profiles = rules.build_profiles(_job_a(), **PROFILE_ARGS)
    for observation, profile in (
        ("screenshot", "h2-thinking-screenshot"),
        ("a11y", "h2-thinking-a11y"),
    ):
        cell = _cell(projection, "h2", observation)
        mean_prompt = profiles[profile].mean_prompt_tokens(100)
        rate = 3.0 / max(mean_prompt / 9000, 2048 / 300)
        assert cell["open_loop_rate"] == pytest.approx(rate)
        assert cell["open_loop_gpu_hours"] == pytest.approx(360 * 100 / rate / 3600)
    screenshot = _cell(projection, "h2", "screenshot")
    a11y = _cell(projection, "h2", "a11y")
    assert a11y["max_context_tokens"] == screenshot["max_context_tokens"] + 6144
    assert screenshot["max_context_tokens"] < MAX_LEN


def test_missing_a2_falls_back_to_the_slowest_a1_seed_with_a_flag() -> None:
    full = _q2(_job_a())
    points = _job_a()
    points["a2"]["status"] = "truncated"
    cut = _q2(points)
    reference = cut["open_loop_reference"]
    assert reference["point"] == "a1a" and reference["rate"] == pytest.approx(2.0)
    assert any("open-loop-reference-a1a" in flag for flag in cut["cells"][0]["flags"])
    assert cut["total_gpu_hours"] > full["total_gpu_hours"]
    for name in ("a1a", "a1b", "a1c"):
        points[name]["status"] = "invalid"
    with pytest.raises(rules.BudgetError, match="open-loop reference"):
        _q2(points)


def test_frontend_correction_only_raises_the_bound() -> None:
    points = _job_a()
    points["f1"] = _open(1.6)  # PNG 20% slower than a1a's JPEG
    slower = _q2(points)
    assert slower["frontend_correction"]["applied"] is True
    assert slower["open_loop_reference"]["rate"] == pytest.approx(3.0 * 0.8)
    points["f1"] = _open(2.6)  # PNG 30% faster: not applied
    faster = _q2(points)
    assert faster["frontend_correction"]["applied"] is False
    assert faster["open_loop_reference"]["rate"] == pytest.approx(3.0)
    assert slower["total_gpu_hours"] >= faster["total_gpu_hours"]


def test_context_check_refuses_a_budget_beyond_max_model_len() -> None:
    projection = _q2(_job_a())
    assert not any(c["exceeds_max_model_len"] for c in projection["cells"])
    assert all(row["cells_over_max_model_len"] == 0 for row in projection["sensitivity"])
    with pytest.raises(rules.BudgetError, match="max_model_len 65536"):
        _q2(_job_a(), max_model_len=65536)


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
    projection = _q2(_job_a())
    assert len(projection["cells"]) == 16
    rung_total = {
        name: sum(c["gpu_hours"] for c in projection["cells"] if c["rung"] == name)
        for name in BUDGET["q2"]["rungs"]
    }
    # Without job C: 4B and 9B at x1, 27B at 4.5 and 35B-A3B at 1.5 of the 9B cost.
    nine = rung_total["qwen3.5-9b"]
    assert rung_total["qwen3.5-4b"] == pytest.approx(nine)
    h1_cells = [c for c in projection["cells"] if c["harness"] == "h1"]
    assert all(c["steps"] == 15 and c["vm_per_replica"] == 40 for c in h1_cells)
    h2_cells = [c for c in projection["cells"] if c["harness"] == "h2"]
    assert all(c["steps"] == 100 and c["vm_per_replica"] == 20 for c in h2_cells)
    assert projection["total_gpu_hours"] == pytest.approx(sum(rung_total.values()))
    assert projection["total_gpu_hours"] > 90
    assert projection["decision"] == "rescope-before-gauntlet"
    assert len(projection["sensitivity"]) == 3 * 3 * 2


def test_q2_decision_thresholds() -> None:
    total = _q2(_job_a())["total_gpu_hours"]

    def decide(rescope: float, overestimate: float) -> str:
        budget = copy.deepcopy(dict(BUDGET))
        budget["q2"] = {
            **budget["q2"],
            "rescope_above_gpu_hours": rescope,
            "overestimate_below_gpu_hours": overestimate,
        }
        return rules.project_q2(
            budget,
            job_a=_job_a(),
            job_c=None,
            x1_outcome="pass",
            unstable_limit=LIMIT,
            max_model_len=MAX_LEN,
        )["decision"]

    assert decide(total - 1, 1) == "rescope-before-gauntlet"
    assert decide(total + 1, total - 1) == "within-dossier-range"
    assert decide(total + 2, total + 1) == "dossier-overestimated"


def _offline(duration: float, completions: int) -> dict:
    return {
        "status": "valid",
        "result": {
            "duration_s": duration,
            "completions": completions,
            "completions_per_s": completions / duration,
        },
    }


def _job_b() -> dict:
    return {
        "b1a": _offline(100.0, 64),
        "b1b": _offline(102.0, 64),
        "b1c": _offline(101.0, 64),
        "b2": _offline(90.0, 32),
        "b3": _offline(80.0, 64),
        "b6": _offline(160.0, 24),
    }


def _q1(job_b: dict, outcome: str = "pass") -> dict:
    return rules.project_q1(BUDGET, job_b=job_b, x1_outcome=outcome, unstable_limit=LIMIT)


def test_q1_projection_rules() -> None:
    job_b = _job_b()
    projection = _q1(job_b)
    per = projection["per_completion_gpu_s"]
    assert per == {
        "b2": pytest.approx(90 / 32),
        "b3": pytest.approx(80 / 64),
        "b6": pytest.approx(160 / 24),
    }
    assert projection["single_turn_gpu_hours"] == pytest.approx(2000 * 90 / 32 / 3600)
    assert projection["three_turn_gpu_hours"] == pytest.approx(2000 * sum(per.values()) / 3600)
    assert projection["decision"] == "within-cap"
    penalised = _q1(job_b, "underpowered")
    assert penalised["single_turn_gpu_hours"] == pytest.approx(
        1.5 * projection["single_turn_gpu_hours"]
    )
    del job_b["b3"]
    fallback = _q1(job_b)
    assert "b3-unmeasured-used-b6" in fallback["flags"]
    heavy = {**_job_b(), "b2": _offline(400.0, 32)}
    assert _q1(heavy)["decision"].startswith("cut")
    with pytest.raises(rules.BudgetError):
        _q1({"b3": _offline(1, 1)})


def test_q1_unstable_b1_raises_the_totals() -> None:
    stable = _q1(_job_b())
    assert stable["b1_noise"]["noise_multiplier"] == 1.0
    noisy = _job_b()
    noisy["b1b"] = _offline(150.0, 64)
    projection = _q1(noisy)
    factor = (64 / 100.0) / (64 / 150.0)
    assert projection["b1_noise"]["noise_multiplier"] == pytest.approx(factor)
    assert projection["single_turn_gpu_hours"] == pytest.approx(
        stable["single_turn_gpu_hours"] * factor
    )


def test_relative_helpers() -> None:
    assert rules.relative_range([1.0]) is None
    assert rules.relative_range([1.0, 3.0]) == pytest.approx(1.0)
    with pytest.raises(rules.BudgetError):
        rules.relative_delta(1.0, 0.0)
    assert math.isclose(rules.relative_delta(1.05, 1.0), 0.05)
