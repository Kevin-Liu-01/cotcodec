from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_mnemosyne_cognitive_evidence import (
    EXPECTED_STATUS,
    MnemosyneCognitiveEvidenceError,
    validate_mnemosyne_cognitive_evidence,
)

ROOT = Path(__file__).resolve().parents[1]


def test_doctor_identity_and_falsifiers_are_frozen() -> None:
    text = (
        ROOT / "infra/memory-baselines/mnemosyne-cognitive/doctor.mjs"
    ).read_text(encoding="utf-8")
    assert "5506aae7cec9ada5523099fd5ab858a4eee593b6" in text
    assert "MNEMOSYNE_COGNITIVE_ACTIVE_INACTIVE_ADMISSION_KILLED" in text
    assert "consolidate({ dryRun: true })" in text
    assert "forgotten_point_physically_resident" in text
    assert "demoted_memory_remains_in_serving_search" in text
    assert 'typeof memory.purge !== "function"' in text


def test_dockerfile_is_digest_pinned_and_nonroot() -> None:
    text = (
        ROOT / "infra/memory-baselines/mnemosyne-cognitive/Dockerfile"
    ).read_text(encoding="utf-8")
    assert "node:22.21.1-bookworm-slim@sha256:" in text
    assert "USER 65534:65534" in text
    assert "org.cotcodec.discovery-only" in text
    assert "apt-get" not in text


def test_retained_mnemosyne_cognitive_negative_is_valid() -> None:
    evidence = validate_mnemosyne_cognitive_evidence(
        ROOT
        / "research/evidence/memory/mnemosyne-cognitive-lifecycle-negative-v1.json",
        project_root=ROOT,
    )
    assert evidence["status"] == EXPECTED_STATUS


def test_retained_mnemosyne_cognitive_negative_rejects_tampering() -> None:
    path = (
        ROOT
        / "research/evidence/memory/mnemosyne-cognitive-lifecycle-negative-v1.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["claim_boundary"]["active_inactive_quality_evaluated"] = True
    with pytest.raises(MnemosyneCognitiveEvidenceError, match="identity drifted"):
        validate_mnemosyne_cognitive_evidence(payload, project_root=ROOT)
