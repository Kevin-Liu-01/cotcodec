from __future__ import annotations

from pathlib import Path

from scripts.run_orchvar_two_stage_cpu_admission import run_proof


def test_two_stage_cpu_proof_passes_and_resumes(tmp_path: Path) -> None:
    manifest = run_proof(tmp_path / "proof")
    assert manifest["task_success_count"] == 6
    assert manifest["tool_operation_count"] == 9
    assert manifest["message_stage_count"] == 15
    assert manifest["action_stage_count"] == 15
    assert manifest["separate_stage_receipt_count"] == 30
    assert manifest["safety_gate_passed"] is True
    assert manifest["actual_usr1_acknowledged_cells"] == 2
    assert manifest["falsifiers"]["missing_message"]["action_calls"] == 0
