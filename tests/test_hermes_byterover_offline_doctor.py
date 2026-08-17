from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml

from scripts.validate_hermes_byterover_experiment import (
    DEFAULT_EXPERIMENT,
    ByteRoverExperimentError,
    validate_experiment_contract,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_registered_byterover_contract_is_cpu_only_and_source_pinned() -> None:
    contract = validate_experiment_contract()
    assert contract["sources"]["byterover"]["license"] == "Elastic-2.0"
    assert contract["runtime"]["gpu_count"] == 0
    assert contract["admission"]["memory_lifecycle_h100"] == (
        "forbidden-for-this-revision"
    )

    tarball = (
        PROJECT_ROOT
        / "raw/baselines/byterover-cli/byterover-cli-3.16.1.tgz"
    )
    assert hashlib.sha256(tarball.read_bytes()).hexdigest() == (
        contract["sources"]["byterover"]["npm_tarball_sha256"]
    )
    provider = (
        PROJECT_ROOT
        / "raw/baselines/hermes-agent/plugins/memory/byterover/__init__.py"
    )
    assert hashlib.sha256(provider.read_bytes()).hexdigest() == (
        contract["sources"]["hermes"]["provider_sha256"]
    )


def test_byterover_h100_admission_drift_fails_closed(tmp_path: Path) -> None:
    payload = yaml.safe_load(DEFAULT_EXPERIMENT.read_text(encoding="utf-8"))
    payload["admission"]["memory_lifecycle_h100"] = "allowed"
    path = tmp_path / DEFAULT_EXPERIMENT.name
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(ByteRoverExperimentError, match="claim boundary drifted"):
        validate_experiment_contract(path)


def test_byterover_container_and_doctor_are_fail_closed() -> None:
    dockerfile = (
        PROJECT_ROOT / "infra/memory-baselines/hermes-byterover/Dockerfile"
    ).read_text(encoding="utf-8")
    doctor = (
        PROJECT_ROOT / "infra/memory-baselines/hermes-byterover/doctor.mjs"
    ).read_text(encoding="utf-8")
    assert "USER node:node" in dockerfile
    assert "npm install --global --ignore-scripts" in dockerfile
    assert "byterover-cli-3.16.1.tgz" in dockerfile
    assert "timeout = 7_000" in doctor
    assert "['search', 'Who owns Project Zephyr?', '--format', 'json']" in doctor
    assert "['query', '--', 'Who owns Project Zephyr?']" in doctor
    assert "['curate', '--', `${canary} Alice owns Project Zephyr`]" in doctor
