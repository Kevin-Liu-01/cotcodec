from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from scripts.validate_degradation_canary_experiment import (
    DEFAULT_EXPERIMENT,
    CanaryExperimentError,
    validate_experiment,
)


def test_deterministic_canary_contract_is_frozen() -> None:
    payload = validate_experiment()
    assert len(payload["tasks"]) == 6
    assert len(payload["seeds"]) == 5
    assert payload["budgets"]["external_model_calls"] == 0


def test_deterministic_canary_contract_fails_closed_on_roster_drift(
    tmp_path: Path,
) -> None:
    payload = yaml.safe_load(DEFAULT_EXPERIMENT.read_text(encoding="utf-8"))
    changed = copy.deepcopy(payload)
    changed["seeds"] = [42]
    path = tmp_path / "changed.yaml"
    path.write_text(yaml.safe_dump(changed, sort_keys=False), encoding="utf-8")
    with pytest.raises(CanaryExperimentError, match="seeds drifted"):
        validate_experiment(path)
