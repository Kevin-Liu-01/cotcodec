from __future__ import annotations

from copy import deepcopy

import pytest

from harness.yaml_utils import load_yaml_file
from scripts.validate_orchvar_live_v2_smoke_experiment import (
    DEFAULT_EXPERIMENT,
    LiveV2ExperimentError,
    validate_experiment,
    validate_experiment_payload,
)


def test_registered_live_v2_smoke_passes() -> None:
    payload = validate_experiment(DEFAULT_EXPERIMENT)
    assert payload["task_variant"] == "live_self_contained_v2"
    assert payload["claim_boundary"]["model_quality_claim"] is False


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("task_variant",), "legacy_v1"),
        (("task_manifest_sha256",), "0" * 64),
        (("interface_admission", "external_model_calls"), 1),
        (("budgets", "external_model_calls"), 7),
        (("claim_boundary", "model_quality_claim"), True),
    ],
)
def test_live_v2_smoke_tampering_fails_closed(
    path: tuple[str, ...], value: object
) -> None:
    payload = deepcopy(load_yaml_file(DEFAULT_EXPERIMENT))
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(LiveV2ExperimentError, match="drifted"):
        validate_experiment_payload(payload)
