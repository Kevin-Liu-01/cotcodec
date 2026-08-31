from __future__ import annotations

from copy import deepcopy

import pytest

from harness.yaml_utils import load_yaml_file
from scripts.validate_orchvar_iterative_live_experiment import (
    DEFAULT_EXPERIMENT,
    IterativeLiveExperimentError,
    validate_experiment,
    validate_experiment_payload,
)


def test_iterative_live_experiment_passes() -> None:
    payload = validate_experiment(DEFAULT_EXPERIMENT)
    assert payload["iterative_cpu_admission"]["safety_gate_passed"] is True


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("actor", "type"), "transformers_json_v1"),
        (("budgets", "max_external_model_calls"), 31),
        (("metrics",), ["task_success_rate"]),
        (("iterative_cpu_admission", "safety_gate_passed"), False),
        (("containment", "network"), "bridge"),
        (("claim_boundary", "model_quality_claim"), True),
    ],
)
def test_iterative_live_experiment_tampering_fails_closed(
    path: tuple[str, ...], value: object
) -> None:
    payload = deepcopy(load_yaml_file(DEFAULT_EXPERIMENT))
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(IterativeLiveExperimentError, match="drifted"):
        validate_experiment_payload(payload)
