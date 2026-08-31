from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.seal_orchvar_iterative_cpu_admission import (
    DEFAULT_OUTPUT,
    IterativeAdmissionEvidenceError,
    validate_evidence,
)


def test_iterative_cpu_admission_evidence_validates() -> None:
    evidence = validate_evidence(DEFAULT_OUTPUT)
    projection = evidence["projection"]
    assert projection["task_success_count"] == 6
    assert projection["safety_gate_passed"] is True
    assert projection["actual_usr1_acknowledged_cells"] == 2
    assert projection["budget_falsifier"]["code"] == "tool_budget_exhausted"


@pytest.mark.parametrize("target", ["projection", "receipt"])
def test_iterative_cpu_admission_tampering_fails_closed(
    target: str, tmp_path: Path
) -> None:
    evidence = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    tampered = deepcopy(evidence)
    if target == "projection":
        tampered["projection"]["safety_gate_passed"] = False
    else:
        tampered["receipts"]["uninterrupted/journal.jsonl"]["raw_sha256"] = "0" * 64
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(IterativeAdmissionEvidenceError, match="drifted"):
        validate_evidence(path)
