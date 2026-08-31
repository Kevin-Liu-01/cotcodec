from __future__ import annotations

from copy import deepcopy

import pytest

from scripts.seal_memgpt_letta_lifecycle_evidence import (
    DEFAULT_OUTPUT,
    EXPECTED_STATUS,
    MemgptLettaLifecycleEvidenceError,
    validate_evidence,
)


def test_memgpt_letta_lifecycle_evidence_validates() -> None:
    bundle = validate_evidence(DEFAULT_OUTPUT)
    assert bundle["status"] == EXPECTED_STATUS
    assert bundle["slurm_job_id"] == "351"
    assert bundle["run_count"] == 2
    assert bundle["findings"][
        "failed_core_update_returns_server_error_after_block_mutation"
    ] is True
    assert bundle["findings"][
        "identical_archive_retry_creates_duplicate_rows"
    ] is True
    assert bundle["findings"][
        "deleting_agent_retains_owner_archive_and_core_blocks"
    ] is True
    assert bundle["h100_actor_admission"] == "forbidden-for-this-revision"


def test_memgpt_letta_lifecycle_evidence_rejects_finding_drift() -> None:
    bundle = validate_evidence(DEFAULT_OUTPUT)
    tampered = deepcopy(bundle)
    tampered["findings"][
        "stopped_postgres_plaintext_residue_present"
    ] = False
    with pytest.raises(MemgptLettaLifecycleEvidenceError, match="identity drifted"):
        validate_evidence(tampered)


def test_memgpt_letta_lifecycle_evidence_rejects_artifact_tampering() -> None:
    bundle = validate_evidence(DEFAULT_OUTPUT)
    tampered = deepcopy(bundle)
    receipt = tampered["artifact_files"]["report.json"]
    encoded = receipt["content_gzip_base64"]
    receipt["content_gzip_base64"] = ("A" if encoded[0] != "A" else "B") + encoded[1:]
    with pytest.raises(MemgptLettaLifecycleEvidenceError):
        validate_evidence(tampered)
