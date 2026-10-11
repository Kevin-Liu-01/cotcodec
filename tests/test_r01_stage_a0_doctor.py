"""R01 Stage A0 doctor: the records-only census reproduces its committed output."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCTOR = ROOT / "scripts/run_r01_stage_a0_doctor.py"
COMMITTED = ROOT / "program/evidence/2026-10-11/r01-stage-a0/census.json"


def test_census_reproduces_committed_output(tmp_path: Path) -> None:
    out = tmp_path / "census.json"
    proc = subprocess.run(
        [sys.executable, str(DOCTOR), "--output", str(out)], capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr
    assert "R01_A0_SUMMARY" in proc.stdout
    assert (
        hashlib.sha256(out.read_bytes()).digest() == hashlib.sha256(COMMITTED.read_bytes()).digest()
    )
    census = json.loads(out.read_text())
    assert census["status"] == "PASS"
    nat = census["A0_2_natural_replays"]
    assert (nat["identical_requests"], nat["reply_text_differs"]["k"], nat["ir_differs"]["k"]) == (
        27,
        16,
        2,
    )
    ir = census["A0_6_identical_ir_pairs"]["all"]
    assert (ir["pairs"], ir["verdict_discordant"]) == (227, 0)
