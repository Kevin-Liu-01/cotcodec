from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness.metrics.degradation import DegradationDetector


def _trace(condition: str, *, seed: int, success: bool, category: str) -> dict:
    return {
        "experiment_id": "paired-proof",
        "benchmark": "orchvar_canary",
        "model": "deterministic-canary-v1",
        "task_id": f"task-{category}",
        "seed": seed,
        "run_group": "default",
        "condition": condition,
        "task_metadata": {"category": category},
        "outcome": {"success": success},
    }


def _write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_category_canary_detects_only_exact_paired_regression(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline"
    treatment = tmp_path / "treatment"
    baseline_rows = [
        _trace("english_only", seed=seed, success=True, category=category)
        for category in ("reasoning_depth", "safety_canary")
        for seed in range(5)
    ]
    treatment_rows = [
        _trace(
            "english_only_low_effort",
            seed=seed,
            success=category != "reasoning_depth",
            category=category,
        )
        for category in ("reasoning_depth", "safety_canary")
        for seed in range(5)
    ]
    _write(baseline / "traces.jsonl", baseline_rows)
    _write(treatment / "traces.jsonl", treatment_rows)
    report = DegradationDetector().run_canary_by_category(baseline, treatment)
    assert report["matched_pairs"] == 10
    assert report["categories"]["reasoning_depth"]["is_degradation"] is True
    assert report["categories"]["safety_canary"]["is_degradation"] is False


def test_canary_rejects_missing_and_duplicate_pair_keys(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline"
    treatment = tmp_path / "treatment"
    row = _trace("english_only", seed=1, success=True, category="reasoning_depth")
    _write(baseline / "traces.jsonl", [row, row])
    _write(
        treatment / "traces.jsonl",
        [_trace("treatment", seed=1, success=False, category="reasoning_depth")],
    )
    with pytest.raises(ValueError, match="duplicate paired trace key"):
        DegradationDetector().run_canary(baseline, treatment)

    _write(baseline / "traces.jsonl", [row])
    _write(treatment / "traces.jsonl", [])
    with pytest.raises(ValueError, match="paired trace key mismatch|no JSONL"):
        DegradationDetector().run_canary(baseline, treatment)
