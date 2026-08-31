from __future__ import annotations

from copy import deepcopy

import pytest

from scripts.seal_mnemo_cortex_lifecycle_evidence import (
    DEFAULT_OUTPUT,
    EXPECTED_STATUS,
    MnemoCortexLifecycleEvidenceError,
    validate_evidence,
)


def test_mnemo_cortex_lifecycle_evidence_validates() -> None:
    bundle = validate_evidence(DEFAULT_OUTPUT)
    assert bundle["status"] == EXPECTED_STATUS
    assert bundle["slurm_job_id"] == "347"
    assert bundle["run_count"] == 2
    assert bundle["findings"][
        "repeated_failed_observe_creates_duplicate_pending_rows"
    ] is True
    assert bundle["findings"]["native_primary_memory_purge_absent"] is True
    assert bundle["h100_actor_admission"] == "forbidden-for-this-revision"


def test_mnemo_cortex_lifecycle_evidence_rejects_finding_drift() -> None:
    bundle = validate_evidence(DEFAULT_OUTPUT)
    tampered = deepcopy(bundle)
    tampered["findings"][
        "passport_observe_returns_server_error_after_pending_mutation"
    ] = False
    with pytest.raises(MnemoCortexLifecycleEvidenceError, match="identity drifted"):
        validate_evidence(tampered)


def test_mnemo_cortex_lifecycle_evidence_rejects_artifact_tampering() -> None:
    bundle = validate_evidence(DEFAULT_OUTPUT)
    tampered = deepcopy(bundle)
    receipt = tampered["artifact_files"]["report.json"]
    encoded = receipt["content_gzip_base64"]
    receipt["content_gzip_base64"] = ("A" if encoded[0] != "A" else "B") + encoded[1:]
    with pytest.raises(MnemoCortexLifecycleEvidenceError):
        validate_evidence(tampered)
