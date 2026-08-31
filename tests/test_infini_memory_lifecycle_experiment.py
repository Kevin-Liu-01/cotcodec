from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from scripts.validate_infini_memory_lifecycle_experiment import (
    DEFAULT_EXPERIMENT,
    EXPECTED_STATUS,
    InfiniMemoryLifecycleExperimentError,
    validate_experiment_contract,
)


def test_invariant_registered_infini_memory_lifecycle_contract_is_bounded() -> None:
    contract = validate_experiment_contract()
    assert contract["expected_falsification"]["status"] == EXPECTED_STATUS
    assert contract["runtime"]["clean_state_repeats"] == 2
    assert contract["runtime"]["dependency_install"] == "exact-committed-uv-lock-frozen"
    assert contract["execution"]["gpus"] == 0
    assert contract["intervention"]["external_model_calls"] == 0
    assert contract["admission"]["scientific_claim"] == "forbidden"


def test_invariant_infini_memory_lifecycle_contract_fails_closed_on_delete_drift(
    tmp_path: Path,
) -> None:
    contract = yaml.safe_load(DEFAULT_EXPERIMENT.read_text(encoding="utf-8"))
    mutated = copy.deepcopy(contract)
    mutated["intervention"]["test_escaped_recursive_delete_confinement"] = False
    path = tmp_path / "infini-memory.yaml"
    path.write_text(yaml.safe_dump(mutated, sort_keys=False), encoding="utf-8")
    with pytest.raises(
        InfiniMemoryLifecycleExperimentError, match="intervention drifted"
    ):
        validate_experiment_contract(path)
