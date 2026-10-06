from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_neo4j_natural_topology_evidence import (
    DEFAULT_EVIDENCE,
    EvidenceError,
    validate_evidence,
)


def test_retained_natural_topology_negative_is_valid() -> None:
    evidence = validate_evidence()
    assert evidence["result"]["true_minus_flat"] == -0.140625
    assert evidence["h100_actor_admission"] == "forbidden"


def test_evidence_rejects_favorable_metric_rewrite(tmp_path: Path) -> None:
    payload = json.loads(DEFAULT_EVIDENCE.read_text(encoding="utf-8"))
    payload["result"]["true_minus_flat"] = 0.14
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(EvidenceError, match="report result binding drifted"):
        validate_evidence(path)


def test_evidence_explicitly_records_unbound_live_source_runtime() -> None:
    evidence = validate_evidence()
    assert evidence["runtime"]["runtime_source_binding"] is False
    assert evidence["scientific_result"] is False
    assert evidence["publication_ready"] is False
