from __future__ import annotations

import copy
import json

import pytest

from scripts.seal_memforest_lifecycle_evidence import (
    DEFAULT_OUTPUT,
    EXPECTED_STATUS,
    MemForestLifecycleEvidenceError,
    validate_evidence,
)


def test_invariant_committed_memforest_lifecycle_evidence_is_self_contained() -> None:
    bundle = validate_evidence()
    assert bundle["status"] == EXPECTED_STATUS
    assert bundle["run_count"] == 2
    assert bundle["fresh_process_restart_count_per_run"] == 3
    assert bundle["findings"]["relative_user_id_escapes_snapshot_root"] is True
    assert bundle["findings"]["interrupted_save_exposes_mixed_component_generations"] is True
    assert bundle["post_delete_plaintext_residue_paths"] == [[], []]


def test_invariant_memforest_lifecycle_evidence_fails_closed_on_finding_drift() -> None:
    payload = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    mutated = copy.deepcopy(payload)
    mutated["findings"]["alias_equivalent_user_ids_share_storage"] = False
    with pytest.raises(MemForestLifecycleEvidenceError, match="identity drifted"):
        validate_evidence(mutated)
