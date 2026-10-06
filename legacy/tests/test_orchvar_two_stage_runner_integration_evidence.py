from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.seal_orchvar_two_stage_runner_integration_evidence import (
    DEFAULT_OUTPUT,
    RunnerIntegrationEvidenceError,
    validate_evidence,
)


def test_two_stage_runner_integration_evidence_validates() -> None:
    projection = validate_evidence(DEFAULT_OUTPUT)["projection"]
    assert projection["benchmark_successes"] == 5
    assert projection["tool_attempts"] == 10
    assert projection["tool_errors"] == 1
    assert projection["safety_task_reached_and_passed"] is True
    assert projection["h100_admission"] is False


def test_two_stage_runner_integration_evidence_tampering_fails(
    tmp_path: Path,
) -> None:
    evidence = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    tampered = deepcopy(evidence)
    tampered["projection"]["h100_admission"] = True
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(RunnerIntegrationEvidenceError, match="drifted"):
        validate_evidence(path)
