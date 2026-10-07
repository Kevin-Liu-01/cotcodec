from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("torch")
pytest.importorskip("transformers")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCTOR = PROJECT_ROOT / "scripts" / "run_sparse_indexer_k1_v2_doctor.py"


def test_v2_doctor_unit_cases_pass_and_refuse_overwrite(tmp_path) -> None:
    output = tmp_path / "k1-v2-doctor.json"
    run = subprocess.run([sys.executable, str(DOCTOR), "--output", str(output),
                          "--skip-end-to-end"], capture_output=True, text=True, timeout=900,
                         check=False)
    assert run.returncode == 0, run.stdout[-2000:] + run.stderr[-2000:]
    receipt = json.loads(output.read_text())
    assert receipt["status"] == "K1_V2_DOCTOR_PASS"
    assert receipt["numbers_are_synthetic"] is True
    assert set(receipt["case_status"]) == {"bank_equivalence", "slot_independence",
                                           "selection_equivalence", "eval_unit_vs_v1"}
    assert receipt["cases"]["bank_equivalence"]["gates"]["registered-shape:adam_bitwise"]
    again = subprocess.run([sys.executable, str(DOCTOR), "--output", str(output),
                            "--skip-end-to-end"], capture_output=True, text=True, timeout=300,
                           check=False)
    assert again.returncode != 0
