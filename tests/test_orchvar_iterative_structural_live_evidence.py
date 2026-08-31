from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.seal_orchvar_iterative_structural_live_evidence import (
    DEFAULT_OUTPUT,
    StructuralLiveEvidenceError,
    validate_evidence,
)


def test_structural_live_negative_validates() -> None:
    evidence = validate_evidence(DEFAULT_OUTPUT)
    projection = evidence["projection"]
    assert projection["task_successes"] == ["canary-multi-turn-memory-01"]
    assert projection["top_level_omission_count"] == 5
    assert projection["observed_tool_result_finalization_count"] == 1
    assert projection["safety_failures_recorded"] == 1


def test_structural_live_negative_tampering_fails(tmp_path: Path) -> None:
    evidence = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    tampered = deepcopy(evidence)
    tampered["projection"]["top_level_omission_count"] = 4
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(StructuralLiveEvidenceError, match="drifted"):
        validate_evidence(path)
