from __future__ import annotations

import copy
import json

import pytest

from scripts.seal_jiuwen_memory_lifecycle_evidence import (
    DEFAULT_OUTPUT,
    JiuwenEvidenceError,
    validate_evidence,
)
from scripts.validate_memory_sources import DEFAULT_LEDGER, load_and_validate


def test_invariant_committed_jiuwen_evidence_is_self_contained() -> None:
    bundle = validate_evidence()
    assert bundle["status"] == (
        "JIUWEN_FILE_BACKEND_ADMISSION_KILLED_GLOBAL_ID_AND_MIGRATION_RESET"
    )
    assert bundle["python_hash_seeds"] == [1, 7]
    assert bundle["findings"]["migration_index_owner_depends_on_process_hash_order"] is True

    ledger = load_and_validate(DEFAULT_LEDGER)
    assert ledger["sources"]["jiuwen-memory"]["evidence_grade"] == ("local-negative-reproduced")


def test_invariant_jiuwen_evidence_fails_closed_on_finding_drift() -> None:
    payload = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    mutated = copy.deepcopy(payload)
    mutated["findings"]["duplicate_id_overwrites_sibling_tenant_index_row"] = False
    with pytest.raises(JiuwenEvidenceError, match="evidence receipt drifted"):
        validate_evidence(mutated)
