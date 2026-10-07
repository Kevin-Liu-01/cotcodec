"""Worker: a harness fault after the candidate ran is an infrastructure error, not a verdict.

Pure Python: the gate run and the row builder are replaced, so no torch is needed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness.q1 import worker
from harness.q1.gates.outcome import GateOutcome
from harness.q1.runner import is_infra_failure
from harness.q1.schema import SchemaError, read_verdict_rows


def _item(tmp_path: Path) -> Path:
    item = {
        "kernel_id": "k1",
        "kernel_path": str(tmp_path / "kernel.py"),
        "problem_id": "L1/19_ReLU",
        "gate": "c",
        "seed": 42,
        "options": {},
        "item_key": "k1|c|seed-42",
        "run_id": "r1",
        "attempt": 1,
    }
    path = tmp_path / "item.json"
    path.write_text(json.dumps(item))
    return path


def test_row_failure_becomes_one_error_row(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Review finding: SchemaError while building rows made the worker exit non-zero after
    the candidate loaded, and the runner recorded a candidate rejection."""
    outcome = GateOutcome("c3", "c3/U1/input_shape[0]/D1/seed-3046", "accept")
    monkeypatch.setattr(worker, "_outcomes_for", lambda item: ([outcome], {}, "cpu"))

    def broken(*args, **kwargs):
        raise SchemaError("verdict.config_id 'c3/U1/input_shape[0]/D1/seed-3046' is not valid")

    monkeypatch.setattr(worker, "_rows_from", broken)
    out = tmp_path / "rows.jsonl"
    assert worker.main([str(_item(tmp_path)), str(out)]) == 0
    (row,) = read_verdict_rows(out)
    assert row["verdict"] == "error" and row["config_id"] == "item/seed-42"
    assert row["details"]["reason"] == worker.HARNESS_ROW_FAILURE
    assert row["details"]["outcomes"] == 1 and "SchemaError" in row["details"]["error_name"]
    assert is_infra_failure([row])


def test_candidate_phase_exceptions_still_propagate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only row building is caught; a failure while gates run candidate code is the
    runner's to attribute by phase."""

    def raising(item):
        raise RuntimeError("candidate raised outside the gate's own handlers")

    monkeypatch.setattr(worker, "_outcomes_for", raising)
    with pytest.raises(RuntimeError):
        worker.main([str(_item(tmp_path)), str(tmp_path / "rows.jsonl")])
