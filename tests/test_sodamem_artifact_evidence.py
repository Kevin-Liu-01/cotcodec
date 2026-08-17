from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.seal_sodamem_artifact_evidence import (
    DEFAULT_OUTPUT,
    SodaMemArtifactEvidenceError,
    validate_sodamem_artifact_evidence,
)
from scripts.validate_memory_sources import DEFAULT_LEDGER, load_and_validate

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_committed_sodamem_artifact_evidence_is_self_contained() -> None:
    bundle = validate_sodamem_artifact_evidence(DEFAULT_OUTPUT, project_root=PROJECT_ROOT)

    assert bundle["status"] == "SODAMEM_RELEASED_ARTIFACTS_AUDITED_NOT_REPRODUCED"
    assert bundle["scientific_result"] is False
    assert bundle["publication_ready"] is False
    assert bundle["repeat_count"] == 2
    assert bundle["repetitions_byte_identical"] is True
    assert bundle["h100_actor_admission"] == "not-granted-by-artifact-audit"

    ledger = load_and_validate(DEFAULT_LEDGER)
    assert ledger["sources"]["sodamem"]["evidence_grade"] == ("local-artifact-audited")


def test_sodamem_artifact_evidence_fails_closed_on_score_drift() -> None:
    payload = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    payload["repeat_receipts"][0]["report_file_sha256"] = "0" * 64

    with pytest.raises(SodaMemArtifactEvidenceError, match="repeat receipts drifted"):
        validate_sodamem_artifact_evidence(payload, project_root=PROJECT_ROOT)
