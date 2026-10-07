from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("torch")
pytest.importorskip("transformers")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCTOR = PROJECT_ROOT / "scripts" / "run_sparse_indexer_k1_doctor.py"


def test_doctor_unit_cases_pass_and_refuse_overwrite(tmp_path) -> None:
    output = tmp_path / "k1-doctor.json"
    run = subprocess.run([sys.executable, str(DOCTOR), "--output", str(output),
                          "--skip-end-to-end"], capture_output=True, text=True, timeout=900,
                         check=False)
    assert run.returncode == 0, run.stdout[-2000:] + run.stderr[-2000:]
    receipt = json.loads(output.read_text())
    assert receipt["status"] == "K1_DOCTOR_PASS"
    assert receipt["numbers_are_synthetic"] is True
    assert set(receipt["case_status"]) == {"capture_vs_eager", "targets_vs_numpy",
                                           "selection_brute_force", "gradient_check",
                                           "verdict_tables", "data_objects"}
    again = subprocess.run([sys.executable, str(DOCTOR), "--output", str(output),
                            "--skip-end-to-end"], capture_output=True, text=True, timeout=300,
                           check=False)
    assert again.returncode != 0
