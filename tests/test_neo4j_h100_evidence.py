from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_neo4j_h100_evidence import (
    EXPECTED_IMAGE_CONFIG_DIGEST,
    Neo4jH100EvidenceError,
    validate_neo4j_h100_evidence,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = (
    PROJECT_ROOT
    / "research/evidence/memory/neo4j-preference-lifecycle-h100-v1.json"
)


def _bundle() -> dict[str, object]:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_neo4j_h100_confirmation_is_fully_replayable() -> None:
    result = validate_neo4j_h100_evidence(
        _bundle(), project_root=PROJECT_ROOT
    )
    assert result["job_id"] == 303
    assert result["client_image_id"] == EXPECTED_IMAGE_CONFIG_DIGEST
    assert result["semantic_projection"]["purge_nodes"] == 0
    assert result["semantic_projection"]["model_calls"] == 0


def test_neo4j_h100_confirmation_claim_upgrade_fails_closed() -> None:
    bundle = _bundle()
    bundle["scientific_result"] = True
    with pytest.raises(Neo4jH100EvidenceError, match="top-level"):
        validate_neo4j_h100_evidence(bundle, project_root=PROJECT_ROOT)

