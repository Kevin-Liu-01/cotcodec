from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.seal_astra_native_lifecycle_evidence import (
    DEFAULT_OUTPUT,
    PROJECT_ROOT,
    AstraEvidenceError,
    validate_astra_native_lifecycle_evidence,
)


def test_retained_astra_native_lifecycle_negative_is_self_contained() -> None:
    bundle = validate_astra_native_lifecycle_evidence(DEFAULT_OUTPUT, project_root=PROJECT_ROOT)
    assert bundle["status"] == "BLOCKED_NONDETERMINISTIC_RECALL_ACCESS_ACCOUNTING"
    assert bundle["run_count"] == 2
    assert bundle["slurm_job_id"] == 269
    assert set(bundle["files"]) == {
        "analysis.json",
        "manifest.sha256",
        "repeat-0.json",
        "repeat-1.json",
        "slurm-269.out",
        "slurm-269.scontrol.txt",
    }


def test_astra_native_lifecycle_negative_rejects_embedded_tamper() -> None:
    bundle = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    tampered = copy.deepcopy(bundle)
    tampered["files"]["analysis.json"]["content_base64"] += "A"
    with pytest.raises(AstraEvidenceError, match="invalid base64"):
        validate_astra_native_lifecycle_evidence(tampered, project_root=PROJECT_ROOT)


def test_astra_native_lifecycle_negative_does_not_read_ignored_results(
    tmp_path: Path,
) -> None:
    copied = tmp_path / DEFAULT_OUTPUT.name
    copied.write_bytes(DEFAULT_OUTPUT.read_bytes())
    validate_astra_native_lifecycle_evidence(copied, project_root=PROJECT_ROOT)
