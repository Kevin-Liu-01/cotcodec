from __future__ import annotations

from pathlib import Path

import pytest

from scripts.run_orchvar_two_stage_runner_integration_cpu import run_proof


def test_two_stage_runner_integration_cpu_proof(tmp_path: Path) -> None:
    manifest = run_proof(tmp_path / "proof")
    assert manifest["completed_cells"] == 6
    assert manifest["benchmark_successes"] == 5
    assert manifest["tool_attempts"] == 10
    assert manifest["tool_errors"] == 1
    assert manifest["duplicate_error_observed_before_final"] is True
    assert manifest["unexpected_runtime_exception_aborts_before_append"] is True
    assert manifest["budget_exhaustion_aborts_before_append"] is True
    assert manifest["byte_identical_trace"] is True
    assert manifest["h100_admission"] is False


def test_two_stage_runner_integration_refuses_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "existing"
    output.mkdir()
    with pytest.raises(ValueError, match="already exists"):
        run_proof(output)
