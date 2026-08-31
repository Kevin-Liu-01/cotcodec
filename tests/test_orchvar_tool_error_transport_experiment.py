from __future__ import annotations

from copy import deepcopy

import pytest

from harness.yaml_utils import load_yaml_file
from scripts.validate_orchvar_tool_error_transport_experiment import (
    DEFAULT_EXPERIMENT,
    ToolErrorTransportExperimentError,
    validate_experiment,
    validate_experiment_payload,
)


def test_tool_error_transport_experiment_passes() -> None:
    payload = validate_experiment()
    assert payload["budgets"]["external_model_calls"] == 0
    assert payload["selected_design"]["unexpected_exception_policy"] == "propagate"


@pytest.mark.parametrize(
    ("section", "key", "value"),
    [
        ("selected_design", "no_implicit_retry", False),
        ("selected_design", "unexpected_exception_policy", "observe"),
        ("cpu_admission", "required_duplicate_errors", 0),
        ("budgets", "max_gpu_hours", 1),
        ("trigger_evidence", "safety_gate_evaluated", True),
    ],
)
def test_tool_error_transport_experiment_tampering_fails(
    section: str, key: str, value: object
) -> None:
    payload = deepcopy(load_yaml_file(DEFAULT_EXPERIMENT))
    payload[section][key] = value
    with pytest.raises(ToolErrorTransportExperimentError, match="drifted"):
        validate_experiment_payload(payload)
