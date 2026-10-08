"""The dense headroom pre-check's GPU entry point, run on CPU with tiny models."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from harness import dense_headroom_data as dhd
from scripts import run_dense_headroom_precheck as entry

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCTOR = PROJECT_ROOT / "scripts" / "run_dense_headroom_precheck_doctor.py"


def test_tabled_code_parser() -> None:
    text = ("| File | SHA-256 |\n|---|---|\n"
            f"| harness/dense_headroom_data.py | {'a' * 64} |\n"
            f"| experiments/x.yaml | {'b' * 64} |\n| not a row | x |\n")
    assert entry.tabled_code(text) == {"harness/dense_headroom_data.py": "a" * 64,
                                       "experiments/x.yaml": "b" * 64}


def test_code_files_are_the_preregistrations_table() -> None:
    prereg = (PROJECT_ROOT / "program" / "preregistrations"
              / f"{dhd.EXPERIMENT_ID}.md").read_text(encoding="utf-8")
    assert set(entry.CODE_FILES) <= set(entry.tabled_code(prereg))


def test_seed_option_cannot_be_abbreviated() -> None:
    with pytest.raises(SystemExit):
        entry.parse_args(["--lane", "x", "--output-dir", "o", "--evidence", "e",
                          "--expected-evidence-sha256", "0", "--model-dir", "m",
                          "--receipt", "r", "--expected-receipt-sha256", "0",
                          "--preregistration", "p", "--expected-preregistration-sha256", "0",
                          "--seeds", "42", "43", "44", "--see", "7"])


def test_end_to_end_on_cpu(tmp_path) -> None:
    pytest.importorskip("torch")
    pytest.importorskip("transformers")
    from scripts import run_dense_headroom_precheck_doctor as doctor

    result = doctor.case_end_to_end(tmp_path)
    assert result["status"] == "PASS", result["failures"]
    for lane in ("tiny-attention", "tiny-hybrid"):
        assert result[lane]["units"] > 0


def test_doctor_unit_cases_pass_and_refuse_overwrite(tmp_path) -> None:
    pytest.importorskip("torch")
    pytest.importorskip("transformers")
    output = tmp_path / "doctor.json"
    run = subprocess.run([sys.executable, str(DOCTOR), "--output", str(output),
                          "--skip-end-to-end"], capture_output=True, text=True, timeout=1800,
                         check=False)
    assert run.returncode == 0, run.stdout[-2000:] + run.stderr[-2000:]
    receipt = json.loads(output.read_text())
    assert receipt["status"] == "DENSE_DOCTOR_PASS"
    assert receipt["numbers_are_synthetic"] is True
    assert set(receipt["case_status"]) == {"codecs", "features", "derive", "statistics",
                                           "selectors", "multiple_choice"}
    again = subprocess.run([sys.executable, str(DOCTOR), "--output", str(output),
                            "--skip-end-to-end"], capture_output=True, text=True, timeout=300,
                           check=False)
    assert again.returncode != 0
