from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from scripts.validate_jiuwen_memory_lifecycle_experiment import (
    DEFAULT_EXPERIMENT,
    EXPECTED_STATUS,
    JiuwenExperimentError,
    validate_experiment_contract,
)


def test_invariant_registered_jiuwen_lifecycle_contract_is_bounded() -> None:
    contract = validate_experiment_contract()
    assert contract["expected_falsification"]["status"] == EXPECTED_STATUS
    assert contract["runtime"]["gpu_count"] == 0
    assert contract["runtime"]["clean_state_repeats"] == 2
    assert contract["intervention"]["model_backend_calls"] == 0
    assert contract["intervention"]["graph_subsystem_excluded"] is True
    assert contract["admission"]["h100_actor"] == "forbidden-for-this-revision"


def test_invariant_jiuwen_lifecycle_contract_fails_closed_on_tenancy_drift(
    tmp_path: Path,
) -> None:
    contract = yaml.safe_load(DEFAULT_EXPERIMENT.read_text(encoding="utf-8"))
    mutated = copy.deepcopy(contract)
    mutated["intervention"]["test_duplicate_id_tenant_isolation"] = False
    path = tmp_path / "jiuwen.yaml"
    path.write_text(yaml.safe_dump(mutated, sort_keys=False), encoding="utf-8")
    with pytest.raises(JiuwenExperimentError, match="intervention drifted"):
        validate_experiment_contract(path)
