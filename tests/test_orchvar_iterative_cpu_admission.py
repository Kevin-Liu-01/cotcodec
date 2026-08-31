from __future__ import annotations

from pathlib import Path

from scripts.run_orchvar_iterative_cpu_admission import run_proof


def test_iterative_cpu_admission_survives_real_signal_and_fresh_resume(
    tmp_path: Path,
) -> None:
    manifest = run_proof(tmp_path / "proof")
    assert manifest["status"] == "ORCHVAR_ITERATIVE_TOOL_RESULT_CPU_ADMISSION_PASS"
    assert manifest["task_success_count"] == 6
    assert manifest["safety_gate_passed"] is True
    assert manifest["actual_usr1_acknowledged_cells"] == 2
    assert manifest["byte_identical_report"] is True
    assert manifest["byte_identical_journal"] is True
    assert manifest["budget_falsifier"]["code"] == "tool_budget_exhausted"
