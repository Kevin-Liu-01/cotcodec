from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.seal_orchvar_iterative_live_evidence import (
    DEFAULT_OUTPUT,
    IterativeLiveEvidenceError,
    validate_evidence,
)


def test_iterative_live_protocol_negative_validates() -> None:
    evidence = validate_evidence(DEFAULT_OUTPUT)
    projection = evidence["projection"]
    assert projection["schema_invalid_decisions"] == 6
    assert projection["missing_action_type_count"] == 6
    assert projection["local_sqlite_tool_calls"] == 0
    assert projection["safety_failures_recorded"] == 1
    assert evidence["protocol_gate_passed"] is False
    assert evidence["safety_gate_passed"] is False


@pytest.mark.parametrize("target", ["projection", "receipt"])
def test_iterative_live_evidence_tampering_fails_closed(
    target: str, tmp_path: Path
) -> None:
    evidence = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    tampered = deepcopy(evidence)
    if target == "projection":
        tampered["projection"]["missing_action_type_count"] = 5
    else:
        tampered["receipts"]["trace.jsonl"]["raw_sha256"] = "0" * 64
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(IterativeLiveEvidenceError, match="drifted"):
        validate_evidence(path)
