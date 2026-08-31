from __future__ import annotations

from copy import deepcopy

import pytest

from harness.yaml_utils import load_yaml_file
from scripts.validate_orchvar_iterative_live_experiment import IterativeLiveExperimentError
from scripts.validate_orchvar_iterative_structural_live_experiment import (
    DEFAULT_EXPERIMENT,
    validate_experiment,
    validate_experiment_payload,
)


def test_structural_live_experiment_passes() -> None:
    assert validate_experiment()["actor"]["type"].endswith("structural_json_v2")


def test_structural_live_experiment_tampering_fails() -> None:
    payload = deepcopy(load_yaml_file(DEFAULT_EXPERIMENT))
    payload["iterative_cpu_admission"]["safety_gate_passed"] = False
    with pytest.raises(IterativeLiveExperimentError, match="drifted"):
        validate_experiment_payload(payload)
