from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from scripts.validate_memforest_lifecycle_experiment import (
    DEFAULT_EXPERIMENT,
    EXPECTED_STATUS,
    MemForestLifecycleExperimentError,
    validate_experiment_contract,
)


def test_invariant_registered_memforest_lifecycle_contract_is_bounded() -> None:
    contract = validate_experiment_contract()
    assert contract["expected_falsification"]["status"] == EXPECTED_STATUS
    assert contract["runtime"]["clean_state_repeats"] == 2
    assert contract["execution"]["gpus"] == 0
    assert contract["intervention"]["external_model_calls"] == 0
    assert contract["admission"]["scientific_claim"] == "forbidden"


def test_invariant_memforest_lifecycle_contract_fails_closed_on_path_drift(
    tmp_path: Path,
) -> None:
    contract = yaml.safe_load(DEFAULT_EXPERIMENT.read_text(encoding="utf-8"))
    mutated = copy.deepcopy(contract)
    mutated["intervention"]["test_relative_user_path_confinement"] = False
    path = tmp_path / "memforest.yaml"
    path.write_text(yaml.safe_dump(mutated, sort_keys=False), encoding="utf-8")
    with pytest.raises(MemForestLifecycleExperimentError, match="intervention drifted"):
        validate_experiment_contract(path)
