from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.seal_orchvar_iterative_structural_cpu_admission import (
    DEFAULT_OUTPUT,
    validate_evidence,
)


def test_structural_cpu_evidence_validates() -> None:
    evidence = validate_evidence(DEFAULT_OUTPUT)
    assert evidence["projection"]["task_success_count"] == 6
    assert evidence["projection"]["safety_gate_passed"] is True


def test_structural_cpu_evidence_tampering_fails(tmp_path: Path) -> None:
    evidence = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    tampered = deepcopy(evidence)
    tampered["projection"]["task_success_count"] = 5
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(ValueError, match="drifted"):
        validate_evidence(path)
