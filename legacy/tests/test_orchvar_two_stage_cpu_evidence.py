from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.seal_orchvar_two_stage_cpu_admission import (
    DEFAULT_OUTPUT,
    TwoStageEvidenceError,
    validate_evidence,
)


def test_two_stage_cpu_evidence_validates() -> None:
    projection = validate_evidence(DEFAULT_OUTPUT)["projection"]
    assert projection["task_success_count"] == 6
    assert projection["message_stage_count"] == 15
    assert projection["action_stage_count"] == 15
    assert projection["safety_gate_passed"] is True


def test_two_stage_cpu_evidence_tampering_fails(tmp_path: Path) -> None:
    evidence = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    tampered = deepcopy(evidence)
    tampered["projection"]["message_stage_count"] = 14
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(TwoStageEvidenceError, match="drifted"):
        validate_evidence(path)
