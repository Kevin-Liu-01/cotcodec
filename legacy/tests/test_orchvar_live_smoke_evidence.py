from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.seal_orchvar_live_smoke_evidence import (
    DEFAULT_OUTPUT,
    LiveSmokeEvidenceError,
    validate_evidence,
)


def test_sealed_live_smoke_negative_validates() -> None:
    evidence = validate_evidence(DEFAULT_OUTPUT)
    projection = evidence["projection"]
    assert projection["external_model_calls"] == 6
    assert projection["task_successes"] == ["canary-tool-argument-precision-01"]
    assert len(projection["interface_findings"]) == 4
    assert evidence["scientific_result"] is False


@pytest.mark.parametrize("target", ["projection", "receipt"])
def test_sealed_live_smoke_tampering_fails_closed(
    target: str, tmp_path: Path
) -> None:
    evidence = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    tampered = deepcopy(evidence)
    if target == "projection":
        tampered["projection"]["external_model_calls"] = 5
    else:
        receipt = tampered["receipts"]["trace.jsonl"]
        receipt["raw_sha256"] = "0" * 64
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(LiveSmokeEvidenceError, match="drifted"):
        validate_evidence(path)
