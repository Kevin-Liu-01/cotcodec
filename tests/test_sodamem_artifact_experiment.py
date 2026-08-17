from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.validate_sodamem_artifact_experiment import (
    DEFAULT_EXPERIMENT,
    SodaMemArtifactExperimentError,
    validate_experiment_contract,
)


def test_sodamem_artifact_contract_is_bounded_and_non_scientific() -> None:
    payload = validate_experiment_contract()

    assert payload["scientific_result"] is False
    assert payload["publication_ready"] is False
    assert payload["execution"]["external_api_calls"] == 0
    assert payload["execution"]["llm_calls"] == 0
    assert payload["execution"]["gpus"] == 0
    assert payload["execution"]["max_gpu_hours"] == 0
    assert payload["execution"]["h100_admission"] == ("not-granted-by-artifact-audit")
    assert payload["gates"]["answer_rows_with_evidence_id_lists"] == 0
    assert payload["gates"]["answer_rows_with_boolean_evidence_sentinel"] == 500


def test_sodamem_artifact_contract_fails_closed_on_score_drift(
    tmp_path: Path,
) -> None:
    payload = yaml.safe_load(DEFAULT_EXPERIMENT.read_text(encoding="utf-8"))
    payload["gates"]["stored_self_judge_correct"] = 465
    path = tmp_path / DEFAULT_EXPERIMENT.name
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    with pytest.raises(SodaMemArtifactExperimentError, match="gates contract drifted"):
        validate_experiment_contract(path)
