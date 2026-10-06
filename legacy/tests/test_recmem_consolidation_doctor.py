from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from scripts.validate_recmem_consolidation_evidence import (
    RecMemEvidenceError,
    validate_recmem_consolidation_evidence,
)
from scripts.validate_recmem_consolidation_experiment import (
    EXPECTED_STATUS,
    RecMemExperimentError,
    validate_experiment_contract,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_recmem_contract_is_provider_free_and_actor_forbidden() -> None:
    payload = validate_experiment_contract()
    assert payload["runtime"]["gpu_count_inside_container"] == 0
    assert payload["intervention"]["provider_calls"] == 0
    assert payload["intervention"]["model_backend_calls"] == 0
    assert payload["expected_falsification"]["status"] == EXPECTED_STATUS
    assert payload["admission"]["h100_actor"] == "forbidden-for-this-revision"


def test_recmem_container_contract_is_locked_down() -> None:
    dockerfile = (
        PROJECT_ROOT / "infra/memory-baselines/recmem/Dockerfile"
    ).read_text(encoding="utf-8")
    assert "USER 65532:65532" in dockerfile
    assert 'org.cotcodec.discovery-only="true"' in dockerfile
    assert "sudo" not in dockerfile


def test_recmem_source_drift_is_rejected(tmp_path: Path) -> None:
    source = (
        PROJECT_ROOT / "experiments/memory/stage3-recmem-consolidation-doctor.yaml"
    )
    target = tmp_path / source.name
    shutil.copyfile(source, target)
    target.write_text(
        target.read_text(encoding="utf-8").replace(
            "a84252f6e5587fd4a8caac03ec9f6c732b7a7f35",
            "0" * 40,
        ),
        encoding="utf-8",
    )
    with pytest.raises(RecMemExperimentError, match="source contract drifted"):
        validate_experiment_contract(target)


def test_retained_recmem_negative_is_valid() -> None:
    evidence = validate_recmem_consolidation_evidence(
        PROJECT_ROOT / "research/evidence/memory/recmem-consolidation-negative-v1.json",
        project_root=PROJECT_ROOT,
    )
    assert evidence["status"] == EXPECTED_STATUS


def test_retained_recmem_negative_rejects_tampering() -> None:
    path = PROJECT_ROOT / "research/evidence/memory/recmem-consolidation-negative-v1.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["claim_boundary"]["duplicate_retry_non_idempotent"] = False
    with pytest.raises(RecMemEvidenceError, match="identity drifted"):
        validate_recmem_consolidation_evidence(payload, project_root=PROJECT_ROOT)
