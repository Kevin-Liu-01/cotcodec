from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from scripts.validate_mnemo_cortex_lifecycle_experiment import (
    DEFAULT_EXPERIMENT,
    MnemoCortexLifecycleExperimentError,
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
        ("source", "git_archive_tar_sha256", "0" * 64),
        ("runtime", "official_container_git_install", "present"),
        ("execution", "llm_calls", 1),
        ("expected_falsification", "native_primary_memory_purge_absent", False),
        ("admission", "h100_actor", "admitted"),
    ],
)
def test_contract_tamper_fails(
    tmp_path: Path, section: str, field: str, replacement: object
) -> None:
    payload = yaml.safe_load(DEFAULT_EXPERIMENT.read_text(encoding="utf-8"))
    drifted = copy.deepcopy(payload)
    drifted[section][field] = replacement
    with pytest.raises(MnemoCortexLifecycleExperimentError):
        validate_experiment_contract(_write(tmp_path, drifted))
