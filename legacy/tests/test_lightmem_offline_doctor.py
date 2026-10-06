from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml

from scripts.validate_lightmem_offline_evidence import (
    LightMemEvidenceError,
    validate_lightmem_offline_evidence,
)
from scripts.validate_lightmem_offline_experiment import (
    EXPECTED_STATUS,
    LightMemExperimentError,
    validate_experiment_contract,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_lightmem_contract_is_provider_free_and_actor_forbidden() -> None:
    payload = validate_experiment_contract()
    assert payload["runtime"]["gpu_count_inside_container"] == 0
    assert payload["intervention"]["provider_calls"] == 0
    assert payload["intervention"]["model_backend_calls"] == 0
    assert payload["expected_falsification"]["status"] == EXPECTED_STATUS
    assert payload["admission"]["h100_actor"] == "forbidden-for-this-revision"


def test_lightmem_container_contract_is_locked_down() -> None:
    dockerfile = (
        PROJECT_ROOT / "infra/memory-baselines/lightmem/Dockerfile"
    ).read_text(encoding="utf-8")
    assert "USER 65532:65532" in dockerfile
    assert 'org.cotcodec.discovery-only="true"' in dockerfile
    assert "sudo" not in dockerfile


def test_lightmem_source_drift_is_rejected(tmp_path: Path) -> None:
    source = (
        PROJECT_ROOT
        / "experiments/memory/stage3-lightmem-offline-consolidation-doctor.yaml"
    )
    target = tmp_path / source.name
    shutil.copyfile(source, target)
    payload = yaml.safe_load(target.read_text(encoding="utf-8"))
    payload["source"]["revision"] = "0" * 40
    target.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(LightMemExperimentError, match="source contract drifted"):
        validate_experiment_contract(target)


def test_lightmem_retained_evidence_is_bound() -> None:
    path = (
        PROJECT_ROOT / "research/evidence/memory/lightmem-offline-negative-v1.json"
    )
    evidence = validate_lightmem_offline_evidence(path, project_root=PROJECT_ROOT)
    assert evidence["status"] == EXPECTED_STATUS
    assert evidence["run_count"] == 2
    assert evidence["claim_boundary"]["h100_actor_admission"] is False


def test_lightmem_evidence_cannot_promote_the_h100_actor() -> None:
    path = (
        PROJECT_ROOT / "research/evidence/memory/lightmem-offline-negative-v1.json"
    )
    evidence = json.loads(path.read_text(encoding="utf-8"))
    evidence["claim_boundary"]["h100_actor_admission"] = True
    with pytest.raises(LightMemEvidenceError, match="identity drifted"):
        validate_lightmem_offline_evidence(evidence, project_root=PROJECT_ROOT)
