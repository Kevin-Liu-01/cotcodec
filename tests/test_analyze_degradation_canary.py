from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from harness.config import ExperimentConfig
from harness.runner import run_experiment
from scripts.analyze_degradation_canary import CanaryAnalysisError, analyze
from scripts.validate_degradation_canary_experiment import DEFAULT_EXPERIMENT


def test_completed_canary_run_passes_exact_category_analysis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("COTCODEC_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("COTCODEC_RUN_ID", "analysis-proof")
    asyncio.run(run_experiment(ExperimentConfig.from_yaml(DEFAULT_EXPERIMENT)))
    report = analyze(tmp_path, "analysis-proof")
    assert report["status"] == "PASS"
    assert report["scientific_result"] is False
    for treatment in report["treatments"].values():
        assert treatment["expected_regressions"] == treatment["observed_regressions"]
        assert treatment["fisher_expected_categories"]["is_degradation"] is True


def test_canary_analysis_rejects_trace_hash_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("COTCODEC_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("COTCODEC_RUN_ID", "tamper-proof")
    result = asyncio.run(run_experiment(ExperimentConfig.from_yaml(DEFAULT_EXPERIMENT)))
    trace = tmp_path / result["trace_artifacts"][0]["path"]
    trace.write_text(trace.read_text(encoding="utf-8") + "{}\n", encoding="utf-8")
    with pytest.raises(CanaryAnalysisError, match="hash drifted"):
        analyze(tmp_path, "tamper-proof")
