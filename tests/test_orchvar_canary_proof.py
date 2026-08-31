from __future__ import annotations

from pathlib import Path

from scripts.run_orchvar_canary_proof import run_proof


def test_orchvar_canary_proof_reproduces_across_usr1_resume(tmp_path: Path) -> None:
    manifest = run_proof(tmp_path / "proof")
    assert manifest["status"] == "PASS"
    assert manifest["planned_cells"] == 120
    assert manifest["byte_identical_scientific_outputs"] is True
    assert 0 < manifest["usr1_acknowledged_cells"] < 120
    assert len(manifest["output_sha256"]) == 6
