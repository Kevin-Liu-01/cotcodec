from __future__ import annotations

from copy import deepcopy

import pytest

from harness.yaml_utils import load_yaml_file
from scripts.validate_orchvar_two_stage_live_experiment import (
    DEFAULT_EXPERIMENT,
    TwoStageLiveExperimentError,
    validate_experiment,
    validate_experiment_payload,
)


def test_two_stage_live_experiment_passes() -> None:
    payload = validate_experiment()
    assert payload["budgets"]["max_external_model_calls"] == 66
    assert payload["compliance"]["required_message_compliance_rate"] == 1.0


@pytest.mark.parametrize(
    ("section", "key", "value"),
    [
        ("actor", "message_fallback", "empty"),
        ("budgets", "max_external_model_calls", 67),
        ("compliance", "synthesize_missing_messages", True),
        ("two_stage_cpu_admission", "safety_gate_passed", False),
        ("containment", "network", "bridge"),
    ],
)
def test_two_stage_live_experiment_tampering_fails(
    section: str, key: str, value: object
) -> None:
    payload = deepcopy(load_yaml_file(DEFAULT_EXPERIMENT))
    payload[section][key] = value
    with pytest.raises(TwoStageLiveExperimentError, match="drifted"):
        validate_experiment_payload(payload)
