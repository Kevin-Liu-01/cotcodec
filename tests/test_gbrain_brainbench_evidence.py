from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.seal_gbrain_brainbench_evidence import (
    DEFAULT_OUTPUT,
    GBrainEvidenceError,
    validate_gbrain_brainbench_evidence,
)
from scripts.validate_memory_sources import DEFAULT_LEDGER, load_and_validate

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_committed_gbrain_brainbench_evidence_is_self_contained() -> None:
    bundle = validate_gbrain_brainbench_evidence(DEFAULT_OUTPUT, project_root=PROJECT_ROOT)

    assert bundle["status"] == ("GBRAIN_BRAINBENCH_CONFORMANCE_PASS_PULL_COMPARISON_MISSING")
    assert bundle["scientific_result"] is False
    assert bundle["publication_ready"] is False
    assert bundle["run_count"] == 2
    assert bundle["semantic_repetitions_identical"] is True
    assert bundle["h100_actor_admission"] == "not-granted-matched-pull-arm-missing"

    ledger = load_and_validate(DEFAULT_LEDGER)
    assert ledger["sources"]["gbrain"]["evidence_grade"] == ("local-conformance-reproduced")


def test_gbrain_brainbench_evidence_fails_closed_on_seam_drift() -> None:
    payload = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    payload["runtime"]["bun_version"] = "latest"

    with pytest.raises(GBrainEvidenceError, match="runtime drifted"):
        validate_gbrain_brainbench_evidence(payload, project_root=PROJECT_ROOT)
