from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.seal_sage_wiki_artifact_evidence import (
    DEFAULT_OUTPUT,
    SageWikiArtifactEvidenceError,
    validate_sage_wiki_artifact_evidence,
)
from scripts.validate_memory_sources import DEFAULT_LEDGER, load_and_validate

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_committed_sage_wiki_artifact_evidence_is_self_contained() -> None:
    bundle = validate_sage_wiki_artifact_evidence(DEFAULT_OUTPUT, project_root=PROJECT_ROOT)
    assert bundle["status"] == (
        "SAGE_WIKI_RELEASED_ARTIFACTS_AUDITED_BINARY_AND_RETRIEVAL_PROVENANCE_MISSING"
    )
    assert bundle["run_count"] == 2
    assert bundle["scientific_result"] is False
    assert bundle["publication_ready"] is False
    assert bundle["h100_actor_admission"] == "not-granted-by-artifact-audit"

    ledger = load_and_validate(DEFAULT_LEDGER)
    assert ledger["sources"]["sage-wiki"]["evidence_grade"] == "local-artifact-audited"


def test_sage_wiki_artifact_evidence_fails_closed_on_status_drift() -> None:
    payload = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    changed = copy.deepcopy(payload)
    changed["scientific_result"] = True
    with pytest.raises(SageWikiArtifactEvidenceError, match="identity drifted"):
        validate_sage_wiki_artifact_evidence(changed, project_root=PROJECT_ROOT)
