from __future__ import annotations

from pathlib import Path

from scripts.run_orchvar_iterative_structural_cpu_admission import run_proof


def test_structural_cpu_admission_passes_with_fresh_resume(tmp_path: Path) -> None:
    manifest = run_proof(tmp_path / "proof")
    assert manifest["task_success_count"] == 6
    assert manifest["tool_operation_count"] == 9
    assert manifest["decision_count"] == 15
    assert manifest["safety_gate_passed"] is True
    assert manifest["actual_usr1_acknowledged_cells"] == 2
    assert manifest["byte_identical_report"] is True
    assert manifest["budget_falsifier"]["code"] == "tool_budget_exhausted"
