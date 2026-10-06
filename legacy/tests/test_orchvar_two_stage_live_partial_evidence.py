from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.seal_orchvar_two_stage_live_partial_negative import (
    DEFAULT_OUTPUT,
    TwoStagePartialEvidenceError,
    validate_evidence,
)


def test_two_stage_partial_live_negative_validates() -> None:
    evidence = validate_evidence(DEFAULT_OUTPUT)
    projection = evidence["projection"]
    assert projection["live_run_complete"] is False
    assert projection["completed_cells"] == 2
    assert projection["task_success_count"] == 0
    assert projection["next_unjournaled_task_id"] == "canary-verbosity-sensitive-01"
    assert projection["safety_gate_evaluated"] is False
    assert (
        projection["unreceipted_failure"]["classification"]
        == "harness_tool_error_transport_gap"
    )


def test_two_stage_partial_live_negative_tampering_fails(tmp_path: Path) -> None:
    evidence = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    tampered = deepcopy(evidence)
    tampered["projection"]["completed_cells"] = 3
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(TwoStagePartialEvidenceError, match="drifted"):
        validate_evidence(path)
