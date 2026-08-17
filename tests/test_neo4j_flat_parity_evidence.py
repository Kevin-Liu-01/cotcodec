from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_neo4j_flat_parity_evidence import (
    DEFAULT_EVIDENCE,
    PROJECT_ROOT,
    EvidenceError,
    validate_evidence,
)


def test_retained_neo4j_flat_parity_evidence_is_valid() -> None:
    evidence = validate_evidence()
    assert evidence["slurm_job_id"] == 304
    assert evidence["component"]["hit_counts"] == {
        "flat_bm25_dense": 0,
        "zero_traversal": 0,
        "flat_sql_join": 48,
        "true_graph": 48,
        "shuffled_graph": 0,
    }


def test_evidence_rejects_report_hash_drift(tmp_path: Path) -> None:
    payload = json.loads(DEFAULT_EVIDENCE.read_text(encoding="utf-8"))
    payload["artifact_sha256"]["parity-304/report.json"] = "0" * 64
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(EvidenceError, match="artifact digest drifted"):
        validate_evidence(path)


def test_evidence_paths_remain_project_relative() -> None:
    payload = json.loads(DEFAULT_EVIDENCE.read_text(encoding="utf-8"))
    assert (PROJECT_ROOT / payload["artifact_root"]).is_dir()
    assert payload["scientific_result"] is False
    assert payload["publication_ready"] is False
