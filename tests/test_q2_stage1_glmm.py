"""The GLMM's input writer, synthetic acceptance data and the registered formula (G0 12)."""

from __future__ import annotations

import csv
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from harness.q2_stage1 import glmm
from harness.q2_stage1.records import final_records

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "program/preregistrations/q2-stage1-rescoped-v1.md"
SCRIPT = ROOT / "harness/q2_stage1/glmm.R"


def terms(formula: str) -> set[str]:
    return {t.strip().replace(" ", "") for t in formula.split("~", 1)[1].split("+")}


def test_glmm_script_fits_the_registered_formula():
    registered = re.search(r"`(y ~ size\*harness[^`]+)`", PREREG.read_text()).group(1)
    script = SCRIPT.read_text()
    full = re.search(r"full_formula <- (y ~[^\n]+(?:\n\s+[^\n]+)*?)\nreduced", script).group(1)
    full = " ".join(full.split())
    assert terms(full) == terms(registered)
    reduced = re.search(r"reduced_formula <- (y ~[^\n]+(?:\n\s+[^\n]+)*?)\n\n", script).group(1)
    reduced = " ".join(reduced.split())
    assert terms(full) - terms(reduced) == {"(1|task:harness)"}
    assert "(1|task:harness:session)" in terms(reduced)


def record(size, session, task, harness, rerun, status="scored", score=1.0):
    return {"schema": "q2-stage1a-episode-v1", "job": "j", "size": size, "session": session,
            "task_id": task, "harness": harness, "rerun": rerun, "extension_block": None,
            "attempt": 1, "status": status, "score": score if status == "scored" else None,
            "infrastructure_type": "transport" if status == "infrastructure" else None}  # fmt: skip


def test_rows_from_records_nest_sessions_and_drop_missing(tmp_path):
    recs = [record("9B", "S1", "a", "H-GA", 1), record("9B", "S2", "a", "H-GA", 2, score=0.5),
            record("4B", "S1", "a", "H-OSW-fixed", 1, status="infrastructure")]  # fmt: skip
    rows = glmm.rows_from_records(final_records(recs), ["a"])
    assert rows == [
        {"y": 1, "size": "9B", "harness": "H-GA", "task": "a", "session": "9B:S1", "rerun": 1},
        {"y": 0, "size": "9B", "harness": "H-GA", "task": "a", "session": "9B:S2", "rerun": 2},
    ]
    path = tmp_path / "e.csv"
    glmm.write_csv(rows, path)
    with path.open() as handle:
        assert list(csv.DictReader(handle))[0]["session"] == "9B:S1"


def test_synthetic_data_has_the_design_shape():
    rows = glmm.synthetic(k=8, seed=1)
    assert len(rows) == 2 * 8 * 2 * 2 * 2
    assert {r["session"] for r in rows} == {"4B:S1", "4B:S2", "9B:S1", "9B:S2"}
    assert 0 < sum(r["y"] for r in rows) < len(rows)
    assert glmm.synthetic(k=8, seed=1) == rows


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="R runs in the pinned container")
def test_glmm_runs_where_r_is_installed(tmp_path):  # pragma: no cover - host container check
    path = tmp_path / "s.csv"
    glmm.write_csv(glmm.synthetic(k=16, seed=3), path)
    out = tmp_path / "out.json"
    done = subprocess.run(["Rscript", str(SCRIPT), str(path), str(out), "0", "42"])
    assert done.returncode == 0 and out.exists()
