from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest
import yaml

from scripts.run_allmem_topology_doctor import (
    AllMemDoctorError,
    _semantic_projection_sha256,
    _validate_phase,
)
from scripts.seal_memory_evidence import EvidenceError, validate_allmem_files
from scripts.validate_allmem_topology_experiment import (
    DEFAULT_EXPERIMENT,
    AllMemExperimentError,
    validate_experiment_contract,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_allmem_experiment_is_exact_and_cpu_only() -> None:
    payload = validate_experiment_contract()
    assert payload["runtime"]["gpu_count"] == 0
    assert payload["runtime"]["runtime_network"] == "none"
    assert payload["admission"]["active_inactive_h100"] == (
        "forbidden-for-this-revision"
    )


@pytest.mark.parametrize(
    ("section", "field", "value", "message"),
    [
        ("source", "revision", "0" * 40, "source contract drifted"),
        ("runtime", "runtime_network", "bridge", "runtime contract drifted"),
        (
            "expected_falsification",
            "split_has_typed_path_to_archived_source",
            True,
            "expected falsification contract drifted",
        ),
        ("admission", "active_inactive_h100", "allowed", "H100 admission"),
    ],
)
def test_allmem_experiment_drift_fails_closed(
    tmp_path: Path, section: str, field: str, value: object, message: str
) -> None:
    payload = yaml.safe_load(DEFAULT_EXPERIMENT.read_text())
    payload[section][field] = value
    path = tmp_path / "experiment.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False))
    with pytest.raises(AllMemExperimentError, match=message):
        validate_experiment_contract(path)


def _valid_phase() -> dict[str, object]:
    projection = {
        "recovery": {
            "update": True,
            "split": False,
            "merge_a": False,
            "merge_b": False,
        },
        "derived_source_labels_without_raw_path": True,
        "native_scoped_purge": False,
        "persistence_format": "pickle",
        "query": {"update_old_recovered": True, "update_new_recovered": True},
        "nodes": [],
        "edges": [],
        "active_count": 1,
        "archived_count": 1,
    }
    canonical = json.dumps(projection, separators=(",", ":"), sort_keys=True).encode()
    import hashlib

    projection["sha256"] = hashlib.sha256(canonical).hexdigest()
    return {
        "phase": "prepare",
        "status": "BLOCKED_SPLIT_MERGE_RAW_EVIDENCE_RECOVERY",
        "scientific_result": False,
        "publication_ready": False,
        "external_model_calls": 0,
        "projection": projection,
    }


def test_allmem_phase_validation_rejects_false_recovery() -> None:
    payload = _valid_phase()
    _validate_phase(payload, "prepare")
    payload["projection"]["recovery"]["split"] = True  # type: ignore[index]
    with pytest.raises(AllMemDoctorError, match="falsifier drifted"):
        _validate_phase(payload, "prepare")


def test_allmem_semantic_projection_normalizes_only_equal_content_ties() -> None:
    base = {
        "nodes": [
            {"source_id": "a", "content_sha256": "same"},
            {"source_id": "b", "content_sha256": "same"},
            {"source_id": "c", "content_sha256": "different"},
        ],
        "query": {"ranked_source_ids": ["c", "a", "b"]},
        "sha256": "0" * 64,
    }
    tied = json.loads(json.dumps(base))
    tied["query"]["ranked_source_ids"] = ["c", "b", "a"]
    meaningful = json.loads(json.dumps(base))
    meaningful["query"]["ranked_source_ids"] = ["a", "c", "b"]
    assert _semantic_projection_sha256(base) == _semantic_projection_sha256(tied)
    assert _semantic_projection_sha256(base) != _semantic_projection_sha256(meaningful)


def test_allmem_container_is_nonroot_and_uses_pinned_source_contract() -> None:
    dockerfile = (
        PROJECT_ROOT / "infra/memory-baselines/all-mem/Dockerfile"
    ).read_text()
    doctor = (PROJECT_ROOT / "infra/memory-baselines/all-mem/doctor.py").read_text()
    assert "USER 65532:65532" in dockerfile
    assert "org.cotcodec.publication-ready=\"false\"" in dockerfile
    assert "RECOVERY_EDGE_TYPES" in doctor
    assert "OPENAI_API_KEY" in doctor
    assert "external_model_calls" in doctor


def _decoded_allmem_evidence() -> dict[str, bytes]:
    evidence = json.loads(
        (PROJECT_ROOT / "research/evidence/memory/allmem-topology-v1.json").read_text()
    )
    return {
        name: base64.b64decode(receipt["content_base64"])
        for name, receipt in evidence["files"].items()
    }


def test_allmem_evidence_recomputes_from_embedded_files() -> None:
    verified = validate_allmem_files(_decoded_allmem_evidence())
    assert verified["stable_semantic_projection_sha256"] == (
        "798f3c3240dcfa95dea5185f2c5542ae56066d2c82f93946fb67709364928093"
    )
    assert len(verified["execution_identity_sha256s"]) == 2


def test_allmem_evidence_rejects_tampered_recovery_projection() -> None:
    files = _decoded_allmem_evidence()
    payload = json.loads(files["run-1/prepare.json"])
    payload["projection"]["recovery"]["split"] = True
    files["run-1/prepare.json"] = json.dumps(payload).encode()
    with pytest.raises(EvidenceError, match="manifest receipt drifted"):
        validate_allmem_files(files)
