from __future__ import annotations

import copy
import json

import pytest
import yaml

from scripts.seal_memforest_artifact_evidence import (
    DEFAULT_OUTPUT,
    PROJECT_ROOT,
    MemForestArtifactEvidenceError,
    validate_memforest_artifact_evidence,
)


def test_committed_memforest_artifact_evidence_is_self_contained() -> None:
    bundle = validate_memforest_artifact_evidence(DEFAULT_OUTPUT, project_root=PROJECT_ROOT)
    ledger = yaml.safe_load(
        (PROJECT_ROOT / "research/memory-sources.yaml").read_text(encoding="utf-8")
    )
    assert bundle["scientific_result"] is False
    assert bundle["h100_actor_admission"] == "not-granted-by-artifact-audit"
    assert ledger["sources"]["memforest"]["evidence_grade"] == "local-artifact-audited"


def test_memforest_artifact_evidence_fails_closed_on_status_drift() -> None:
    payload = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    changed = copy.deepcopy(payload)
    changed["status"] = "REPRODUCED"
    with pytest.raises(MemForestArtifactEvidenceError, match="identity drifted"):
        validate_memforest_artifact_evidence(changed, project_root=PROJECT_ROOT)
