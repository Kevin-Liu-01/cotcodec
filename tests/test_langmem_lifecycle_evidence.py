from __future__ import annotations

import json
from pathlib import Path

from scripts.seal_langmem_native_lifecycle_evidence import (
    PROJECTION_SHA256,
    STATUS,
    validate_langmem_native_lifecycle_evidence,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = PROJECT_ROOT / "research/evidence/memory/langmem-native-lifecycle-negative-v1.json"


def test_langmem_native_lifecycle_evidence_is_self_contained() -> None:
    bundle = validate_langmem_native_lifecycle_evidence(EVIDENCE)
    assert bundle["status"] == STATUS
    assert bundle["stable_projection_sha256"] == PROJECTION_SHA256
    assert bundle["run_count"] == 2
    assert bundle["h100_actor_admission"] == "forbidden-for-this-revision"


def test_langmem_negative_keeps_quality_claims_out_of_scope() -> None:
    bundle = json.loads(EVIDENCE.read_text())
    assert bundle["scientific_result"] is False
    assert bundle["publication_ready"] is False
    assert "not extraction quality" in bundle["claim_boundary"]
    assert bundle["findings"]["first_class_namespace_purge_absent"] is True
    assert bundle["findings"]["purged_plaintext_remains_in_postgresql_heap"] is True
    assert bundle["findings"]["purged_plaintext_remains_in_postgresql_wal"] is True
