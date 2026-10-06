from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.seal_orchvar_tool_error_transport_cpu_admission import (
    DEFAULT_OUTPUT,
    ToolErrorTransportEvidenceError,
    validate_evidence,
)


def test_tool_error_transport_cpu_evidence_validates() -> None:
    projection = validate_evidence(DEFAULT_OUTPUT)["projection"]
    assert projection["baseline_successes"] == 6
    assert projection["tool_attempt_count"] == 11
    assert projection["tool_error_count"] == 1
    assert projection["duplicate_error_observed_before_final"] is True
    assert projection["unexpected_exception_propagated"] is True


def test_tool_error_transport_cpu_evidence_tampering_fails(tmp_path: Path) -> None:
    evidence = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    tampered = deepcopy(evidence)
    tampered["projection"]["tool_error_count"] = 0
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(ToolErrorTransportEvidenceError, match="drifted"):
        validate_evidence(path)
