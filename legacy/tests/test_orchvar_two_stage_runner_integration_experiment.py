from __future__ import annotations

from copy import deepcopy

import pytest

from harness.yaml_utils import load_yaml_file
from scripts.validate_orchvar_two_stage_runner_integration_experiment import (
    DEFAULT_EXPERIMENT,
    RunnerIntegrationExperimentError,
    validate_experiment,
    validate_experiment_payload,
)


def test_two_stage_runner_integration_experiment_passes() -> None:
    payload = validate_experiment()
    assert payload["claim_boundary"]["h100_admission"] is False
    assert payload["expected_projection"]["tool_errors"] == 1


@pytest.mark.parametrize(
    ("section", "key", "value"),
    [
        ("tools", "unexpected_exception_policy", "observe"),
        ("actor", "external_model_calls", 1),
        ("trigger_live_negative", "live_run_complete", True),
        ("expected_projection", "safety_failures", 1),
        ("claim_boundary", "h100_admission", True),
    ],
)
def test_two_stage_runner_integration_tampering_fails(
    section: str, key: str, value: object
) -> None:
    payload = deepcopy(load_yaml_file(DEFAULT_EXPERIMENT))
    payload[section][key] = value
    with pytest.raises(RunnerIntegrationExperimentError, match="drifted"):
        validate_experiment_payload(payload)
