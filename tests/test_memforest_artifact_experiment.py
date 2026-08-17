from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.validate_memforest_artifact_experiment import (
    DEFAULT_EXPERIMENT,
    MemForestArtifactExperimentError,
    validate_experiment_contract,
)


def test_memforest_artifact_contract_is_bounded_and_non_scientific() -> None:
    payload = validate_experiment_contract()
    assert payload["execution"] == {
        "repetitions": 2,
        "external_api_calls": 0,
        "llm_calls": 0,
        "gpus": 0,
        "max_gpu_hours": 0,
        "cpu_time_limit_minutes": 5,
        "h100_admission": "not-granted-by-artifact-audit",
    }
    assert payload["gates"]["independent_rejudge_completed"] is False
    assert payload["gates"]["retrieval_or_construction_reproduced"] is False


def test_memforest_artifact_contract_fails_closed_on_coverage_drift(tmp_path: Path) -> None:
    payload = yaml.safe_load(DEFAULT_EXPERIMENT.read_text(encoding="utf-8"))
    payload["gates"]["submitted_evermemos_30b_longmemeval_total"] = 500
    path = tmp_path / DEFAULT_EXPERIMENT.name
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(MemForestArtifactExperimentError, match="gates contract drifted"):
        validate_experiment_contract(path)
