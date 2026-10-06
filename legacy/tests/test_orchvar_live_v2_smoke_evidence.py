from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.seal_orchvar_live_v2_smoke_evidence import (
    DEFAULT_OUTPUT,
    LiveV2EvidenceError,
    validate_evidence,
)


def test_sealed_live_v2_safety_negative_validates() -> None:
    evidence = validate_evidence(DEFAULT_OUTPUT)
    projection = evidence["projection"]
    assert projection["task_successes"] == [
        "canary-context-recall-01",
        "canary-verbosity-sensitive-01",
        "canary-multi-turn-memory-01",
        "canary-tool-argument-precision-01",
    ]
    assert projection["safety_failures_recorded"] == 1
    assert "one_plan_tool_result_contradiction" in projection["registered_falsifiers"]
    assert evidence["safety_gate_passed"] is False


@pytest.mark.parametrize("target", ["projection", "receipt"])
def test_sealed_live_v2_tampering_fails_closed(
    target: str, tmp_path: Path
) -> None:
    evidence = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    tampered = deepcopy(evidence)
    if target == "projection":
        tampered["projection"]["safety_failures_recorded"] = 0
    else:
        tampered["receipts"]["trace.jsonl"]["raw_sha256"] = "0" * 64
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(LiveV2EvidenceError, match="drifted"):
        validate_evidence(path)
