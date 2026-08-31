from __future__ import annotations

from copy import deepcopy

import pytest

from scripts.seal_infini_memory_lifecycle_evidence import (
    DEFAULT_OUTPUT,
    EXPECTED_STATUS,
    InfiniMemoryLifecycleEvidenceError,
    validate_evidence,
)


def test_infini_memory_lifecycle_evidence_validates() -> None:
    bundle = validate_evidence(DEFAULT_OUTPUT)
    assert bundle["status"] == EXPECTED_STATUS
    assert bundle["h100_actor_admission"] == "forbidden-for-this-revision"
    assert bundle["post_delete_plaintext_residue_paths"] == [
        {
            key: []
            for key in bundle["post_delete_plaintext_residue_paths"][0]
        },
        {
            key: []
            for key in bundle["post_delete_plaintext_residue_paths"][1]
        },
    ]


def test_infini_memory_lifecycle_evidence_rejects_tampered_report() -> None:
    bundle = validate_evidence(DEFAULT_OUTPUT)
    tampered = deepcopy(bundle)
    receipt = tampered["artifact_files"]["report.json"]
    encoded = receipt["content_gzip_base64"]
    receipt["content_gzip_base64"] = ("A" if encoded[0] != "A" else "B") + encoded[1:]
    with pytest.raises(InfiniMemoryLifecycleEvidenceError):
        validate_evidence(tampered)
