from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.validate_langmem_lifecycle_experiment import (
    DEFAULT_EXPERIMENT,
    LangMemExperimentError,
    validate_experiment_contract,
)


def test_registered_langmem_contract_is_bounded_and_non_scientific() -> None:
    payload = validate_experiment_contract()

    assert payload["scientific_result"] is False
    assert payload["publication_ready"] is False
    assert payload["execution"]["gpus"] == 0
    assert payload["execution"]["max_gpu_hours"] == 0
    assert payload["execution"]["external_network"] == "forbidden"
    assert payload["execution"]["h100_admission"].startswith("blocked-")


def test_registered_langmem_contract_drift_fails_closed(tmp_path: Path) -> None:
    payload = yaml.safe_load(DEFAULT_EXPERIMENT.read_text(encoding="utf-8"))
    payload["source"]["revision"] = "0" * 40
    path = tmp_path / "experiment.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    with pytest.raises(LangMemExperimentError, match="source contract drifted"):
        validate_experiment_contract(path)
