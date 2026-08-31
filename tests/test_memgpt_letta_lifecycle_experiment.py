from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from scripts.validate_memgpt_letta_lifecycle_experiment import (
    DEFAULT_EXPERIMENT,
    MemgptLettaLifecycleExperimentError,
    validate_experiment_contract,
)


def _write(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "experiment.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def test_registered_contract_passes() -> None:
    payload = validate_experiment_contract()
    assert payload["execution"]["gpus"] == 0
    assert payload["admission"]["h100_actor"].startswith("forbidden")


@pytest.mark.parametrize(
    ("section", "field", "replacement"),
    [
        ("source", "revision", "0" * 40),
        ("source", "lock_sha256", "0" * 64),
        ("current_runtime_context", "role", "runtime-under-test"),
        ("runtime", "exact_image_source_hash_match_required", False),
        ("execution", "llm_calls", 1),
        (
            "expected_falsification",
            "failed_core_update_returns_server_error_after_block_mutation",
            False,
        ),
        ("admission", "h100_actor", "admitted"),
    ],
)
def test_contract_tamper_fails(
    tmp_path: Path, section: str, field: str, replacement: object
) -> None:
    payload = yaml.safe_load(DEFAULT_EXPERIMENT.read_text(encoding="utf-8"))
    drifted = copy.deepcopy(payload)
    drifted[section][field] = replacement
    with pytest.raises(MemgptLettaLifecycleExperimentError):
        validate_experiment_contract(_write(tmp_path, drifted))
