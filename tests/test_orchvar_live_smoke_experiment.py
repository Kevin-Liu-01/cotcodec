from __future__ import annotations

from copy import deepcopy

import pytest

from harness.yaml_utils import load_yaml_file
from scripts.validate_orchvar_live_smoke_experiment import (
    DEFAULT_EXPERIMENT,
    LiveCanaryExperimentError,
    validate_experiment,
    validate_experiment_payload,
)


def test_registered_live_smoke_contract_passes() -> None:
    payload = validate_experiment(DEFAULT_EXPERIMENT)
    assert payload["claim_boundary"]["scientific_claim"] is False


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("conditions",), ["internal_chinese"]),
        (("actor", "revision"), "0" * 40),
        (("budgets", "external_model_calls"), 7),
        (("containment", "network"), "bridge"),
        (("claim_boundary", "scientific_claim"), True),
    ],
)
def test_live_smoke_contract_tampering_fails_closed(
    path: tuple[str, ...], value: object
) -> None:
    payload = deepcopy(load_yaml_file(DEFAULT_EXPERIMENT))
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(LiveCanaryExperimentError, match="drifted"):
        validate_experiment_payload(payload)
