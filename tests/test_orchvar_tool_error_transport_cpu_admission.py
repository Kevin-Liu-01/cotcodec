from __future__ import annotations

from pathlib import Path

import pytest

from scripts.run_orchvar_tool_error_transport_cpu_admission import run_proof


def test_tool_error_transport_cpu_proof(tmp_path: Path) -> None:
    manifest = run_proof(tmp_path / "proof")
    assert manifest["baseline_successes"] == 6
    assert manifest["tool_attempt_count"] == 11
    assert manifest["tool_error_count"] == 1
    assert manifest["duplicate_error_observed_before_final"] is True
    assert manifest["byte_identical_report"] is True


def test_tool_error_transport_cpu_proof_refuses_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "existing"
    output.mkdir()
    with pytest.raises(ValueError, match="already exists"):
        run_proof(output)
