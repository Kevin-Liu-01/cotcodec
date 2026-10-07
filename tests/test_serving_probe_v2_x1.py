"""Control X1 v2: identical prompt token sequences, thresholds from v1's measured noise."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from harness.serving_probe_v2.x1 import evaluate_x1, replay_delta_se, replay_mean_se

PROJECT_ROOT = Path(__file__).resolve().parents[1]
V1_POINTS = (
    PROJECT_ROOT
    / "program"
    / "evidence"
    / "2026-10-07"
    / "serving-throughput-probe-v1"
    / "jobs"
    / "a-442"
    / "probe"
    / "points"
)
CONTRACT = PROJECT_ROOT / "experiments" / "serving" / "serving-throughput-probe-v2.yaml"
RULE = {
    "max_open_loop_delta": 0.05,
    "max_replay_latency_delta": 0.08,
    "max_replay_delta_se": 0.05,
    "max_a1_seed_range": 0.05,
}
IDENTITY = {"basis": "prompt-token-ids", "requests": {"0:1": ["ab" * 32, 3684]}}


def _v1(name: str) -> dict[str, Any]:
    return json.loads((V1_POINTS / f"{name}.json").read_text(encoding="utf-8"))


def _opened(rate: float, identity: dict | None = None) -> dict[str, Any]:
    return {
        "status": "valid",
        "request_identity": identity or IDENTITY,
        "result": {"request_throughput": rate},
    }


def _replay(template: dict[str, Any], scale: float, identity: dict | None = None) -> dict:
    per_step = {
        step: {
            "latency_s": {
                "mean": entry["latency_s"]["mean"] * scale,
                "se": entry["latency_s"]["se"],
            }
        }
        for step, entry in template["result"]["per_step"].items()
    }
    mean = sum(entry["latency_s"]["mean"] for entry in per_step.values()) / len(per_step)
    return {
        "status": "valid",
        "request_identity": identity or IDENTITY,
        "result": {"per_step": per_step, "e2el_ms": {"mean": mean * 1000.0}},
    }


def _points(**overrides: Any) -> dict[str, Any]:
    r1 = _v1("r1")
    points = {
        "a1a": _opened(2.0),
        "a1b": _opened(2.01),
        "a1c": _opened(1.99),
        "x1-a1": _opened(2.02),
        "r1": _replay(r1, 1.0),
        "x1-r1": _replay(r1, 1.03),
    }
    points.update(overrides)
    return points


def test_contract_registers_the_thresholds() -> None:
    import yaml

    raw = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    assert raw["dummy_admissibility"] == RULE


def test_v1_noise_figures_behind_the_thresholds() -> None:
    """The figures section 7 cites: v1's identical-prompt deltas and replay SEs."""
    r1, x1 = _v1("r1"), _v1("x1-r1")
    a1a, x1a1 = _v1("a1a"), _v1("x1-a1")
    rel = lambda a, b: abs(b - a) / a  # noqa: E731
    assert rel(
        a1a["result"]["request_throughput"], x1a1["result"]["request_throughput"]
    ) == pytest.approx(0.0086, abs=5e-5)
    step1 = [p["result"]["per_step"]["1"]["latency_s"] for p in (r1, x1)]
    assert rel(step1[0]["mean"], step1[1]["mean"]) == pytest.approx(0.0301, abs=5e-5)
    se_step1 = math.sqrt(step1[0]["se"] ** 2 + step1[1]["se"] ** 2) / step1[0]["mean"]
    assert se_step1 == pytest.approx(0.0261, abs=5e-5)
    assert replay_mean_se(r1) / (r1["result"]["e2el_ms"]["mean"] / 1000) == pytest.approx(
        0.0284, abs=5e-5
    )
    assert replay_delta_se(r1, x1) == pytest.approx(0.0381, abs=5e-5)
    # v1's own X1 comparison was confounded: x1-r1's prompts were 6.6% shorter.
    tokens = [p["result"]["prompt_tokens"] / p["result"]["completed"] for p in (r1, x1)]
    assert rel(tokens[0], tokens[1]) == pytest.approx(0.0663, abs=5e-4)


def test_outcomes() -> None:
    assert evaluate_x1(_points(), RULE)["outcome"] == "pass"
    missing = evaluate_x1(_points(r1={"status": "invalid"}), RULE)
    assert missing["outcome"] == "not-run" and missing["missing_or_invalid"] == ["r1"]
    assert evaluate_x1(_points(**{"x1-a1": _opened(2.2)}), RULE)["outcome"] == "fail"
    r1 = _v1("r1")
    assert evaluate_x1(_points(**{"x1-r1": _replay(r1, 1.09)}), RULE)["outcome"] == "fail"
    underpowered = evaluate_x1(_points(a1c={"status": "truncated"}), RULE)
    assert underpowered["outcome"] == "underpowered"
    assert underpowered["reason"] == "fewer than three valid A1 seeds"
    spread = evaluate_x1(_points(a1c=_opened(1.85)), RULE)
    assert spread["reason"] == "A1 seed range above its limit"
    noisy = _replay(r1, 1.0)
    for entry in noisy["result"]["per_step"].values():
        entry["latency_s"]["se"] *= 2.0
    assert evaluate_x1(_points(r1=noisy), RULE)["reason"] == "replay delta SE above its limit"


def test_same_engine_replicate_checks_the_noise_model() -> None:
    """r1b (r1's requests again on real weights) is X1's measured run-to-run replay check."""
    r1 = _v1("r1")
    verdict = evaluate_x1(_points(r1b=_replay(r1, 1.03)), RULE)
    replicate = verdict["same_engine_replicate"]
    assert verdict["outcome"] == "pass" and replicate["used"] is True
    assert replicate["relative_delta"] == pytest.approx(0.03, abs=1e-9)
    assert replicate["within_replay_threshold"] is True
    noisy = evaluate_x1(_points(r1b=_replay(r1, 1.09)), RULE)
    assert noisy["outcome"] == "underpowered"
    assert noisy["reason"].startswith("the same-engine replicate r1b differs from r1")
    # Not run, not valid or not comparable: not used, and X1 says it rests on the model.
    for r1b in (None, {"status": "truncated"}):
        points = _points() if r1b is None else _points(r1b=r1b)
        verdict = evaluate_x1(points, RULE)
        assert verdict["outcome"] == "pass"
        assert verdict["same_engine_replicate"]["used"] is False
        assert "noise model is not checked" in verdict["same_engine_replicate"]["reason"]
    other = {"basis": "prompt-token-ids", "requests": {"0:1": ["cd" * 32, 3684]}}
    verdict = evaluate_x1(_points(r1b=_replay(r1, 1.09, other)), RULE)
    assert verdict["outcome"] == "pass" and verdict["same_engine_replicate"]["used"] is False
    # A fail stays a fail whatever the replicate shows.
    assert (
        evaluate_x1(_points(**{"x1-r1": _replay(r1, 1.09)}, r1b=_replay(r1, 1.2)), RULE)["outcome"]
        == "fail"
    )
    # The output records that the thresholds and the noise model are post hoc and modelled.
    notes = " ".join(verdict["notes"])
    assert "set after v1's X1 result" in notes and "model-based" in notes


def test_prompt_token_sequences_must_be_identical() -> None:
    other = {"basis": "prompt-token-ids", "requests": {"0:1": ["cd" * 32, 3684]}}
    verdict = evaluate_x1(_points(**{"x1-r1": _replay(_v1("r1"), 1.0, other)}), RULE)
    assert verdict["outcome"] == "not-comparable"
    assert verdict["identity"]["r1/x1-r1"]["differing"] == ["0:1"]
    # v1's case: same ids impossible, the dummy history re-tokenised shorter.
    shorter = {"basis": "prompt-token-count", "requests": {"0:1": [None, 3500]}}
    verdict = evaluate_x1(_points(**{"x1-a1": _opened(2.0, shorter)}), RULE)
    assert verdict["outcome"] == "not-comparable"
    # Counts alone may stand in when the server returned no ids, and say so.
    counts = {"basis": "prompt-token-count", "requests": {"0:1": [None, 3684]}}
    verdict = evaluate_x1(
        _points(a1a=_opened(2.0, counts), **{"x1-a1": _opened(2.0, counts)}), RULE
    )
    assert verdict["outcome"] == "pass"
    assert verdict["identity"]["a1a/x1-a1"]["basis"] == "prompt-token-count"
    missing = evaluate_x1(_points(**{"x1-a1": {**_opened(2.0), "request_identity": None}}), RULE)
    assert missing["outcome"] == "not-comparable"


def _p_pass(
    rng, *, cv: float, d_open: float, d_replay: float, draws: int, replicate: bool = False
) -> dict[str, float]:
    r1 = _v1("r1")
    se = replay_mean_se(r1) / (r1["result"]["e2el_ms"]["mean"] / 1000.0)
    counts: dict[str, int] = {}
    for _ in range(draws):
        e = rng.normal(0.0, cv, 4)
        z = rng.normal(0.0, se, 3)
        extra = {"r1b": _replay(r1, 1 + z[2])} if replicate else {}
        points = _points(
            **extra,
            a1a=_opened(2.0 * (1 + e[0])),
            a1b=_opened(2.0 * (1 + e[1])),
            a1c=_opened(2.0 * (1 + e[2])),
            **{
                "x1-a1": _opened(2.0 * (1 + d_open) * (1 + e[3])),
                "x1-r1": _replay(r1, (1 + d_replay) * (1 + z[1])),
            },
            r1=_replay(r1, 1 + z[0]),
        )
        outcome = evaluate_x1(points, RULE)["outcome"]
        counts[outcome] = counts.get(outcome, 0) + 1
    return {key: value / draws for key, value in counts.items()}


def test_operating_characteristics_match_the_preregistration() -> None:
    """Section 7's X1 figures, by Monte Carlo through evaluate_x1 itself.

    Replay means carry v1's measured standard error (2.84% per point, from r1's
    per-step SEs); open-loop throughputs a run-to-run CV. These are model-based:
    within-run spread stands in for run-to-run noise (r1b is the measured check).
    """
    rng = np.random.default_rng(20261007)
    draws = 2500
    stated_replay = {0.0: 0.95, 0.05: 0.76, 0.08: 0.50, 0.10: 0.33, 0.12: 0.18, 0.15: 0.06}
    for d_replay, stated in stated_replay.items():
        p = _p_pass(rng, cv=0.01, d_open=0.0, d_replay=d_replay, draws=draws)
        assert p.get("pass", 0.0) == pytest.approx(stated, abs=0.035), d_replay
    stated_cv = {0.02: 0.74, 0.03: 0.41}
    for cv, stated in stated_cv.items():
        p = _p_pass(rng, cv=cv, d_open=0.0, d_replay=0.0, draws=draws)
        assert p.get("pass", 0.0) == pytest.approx(stated, abs=0.035), cv
    p = _p_pass(rng, cv=0.01, d_open=0.08, d_replay=0.0, draws=draws)
    assert p.get("pass", 0.0) <= 0.04
    # With the same-engine replicate r1b valid (drawn from the same noise model).
    stated_with_r1b = {0.0: 0.91, 0.05: 0.72, 0.10: 0.31, 0.15: 0.05}
    for d_replay, stated in stated_with_r1b.items():
        p = _p_pass(rng, cv=0.01, d_open=0.0, d_replay=d_replay, draws=draws, replicate=True)
        assert p.get("pass", 0.0) == pytest.approx(stated, abs=0.035), d_replay
