from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts.run_neo4j_preference_lifecycle_doctor import (
    DOCKERFILE,
    DOCTOR,
    PROJECT_ROOT,
    DoctorError,
    run_doctor,
)
from scripts.validate_neo4j_preference_experiment import (
    DEFAULT_EXPERIMENT,
    validate_experiment_contract,
)


def test_registered_neo4j_preference_contract_is_valid() -> None:
    payload = validate_experiment_contract(DEFAULT_EXPERIMENT)
    assert payload["source"]["revision"] == (
        "231d60eac9401ab156ba194b519d89dd644dadb8"
    )
    assert payload["runtime"]["runtime_network"] == "private-internal-only"
    assert payload["runtime"]["external_network"] == "forbidden"
    assert payload["runtime"]["gpu_count"] == 0
    assert payload["runtime"]["server_capabilities"] == []
    assert payload["runtime"]["volume_initializer_capabilities"] == ["CHOWN"]
    assert payload["runtime"]["client_extras"] == ["nams"]
    assert set(payload["runtime"]["lanes"]) == {
        "local-arm64",
        "cluster-amd64-slurm",
    }
    assert payload["scientific_result"] is False


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        ("source.revision", "0" * 40, "source contract drifted"),
        ("runtime.gpu_count", 1, "containment or budget drifted"),
        ("intervention.embedding", "local-model", "no-model intervention drifted"),
    ],
)
def test_neo4j_preference_contract_drift_fails_closed(
    tmp_path: Path,
    field: str,
    replacement: object,
    message: str,
) -> None:
    payload = yaml.safe_load(DEFAULT_EXPERIMENT.read_text(encoding="utf-8"))
    section, key = field.split(".")
    payload[section][key] = replacement
    path = tmp_path / "experiment.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        validate_experiment_contract(path)


def test_doctor_sources_enforce_no_model_and_containment() -> None:
    assert DOCKERFILE.is_file() and not DOCKERFILE.is_symlink()
    assert DOCTOR.is_file() and not DOCTOR.is_symlink()
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    doctor = DOCTOR.read_text(encoding="utf-8")
    runner = (
        PROJECT_ROOT / "scripts/run_neo4j_preference_lifecycle_doctor.py"
    ).read_text(encoding="utf-8")

    assert "ARG BASE_IMAGE" in dockerfile
    assert "--extra nams" in dockerfile
    assert "USER 65532:65532" in dockerfile
    assert "FailOnCallEmbedder" in doctor
    assert "generate_embedding=False" in doctor
    assert "ExtractorType.NONE" in doctor
    assert "SUPERSEDED_BY" in doctor
    assert '"--network",\n            network' in runner
    assert '"--internal", network' in runner
    assert '"--cap-drop",\n            "ALL"' in runner
    assert '"--user",\n            "7474:7474"' in runner
    assert '"--entrypoint",\n            "/bin/chown"' in runner
    assert '"no-new-privileges"' in runner
    assert '["sudo"' not in runner


def test_direct_script_entrypoint_loads_without_package_install() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts/run_neo4j_preference_lifecycle_doctor.py"),
            "--help",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "--output-dir" in completed.stdout
    assert "--prebuilt-client-image" in completed.stdout
    assert "--expected-client-image-id" in completed.stdout


@pytest.mark.parametrize(
    ("image", "image_id", "message"),
    [
        ("example:tag", None, "must be supplied together"),
        (None, "sha256:" + "0" * 64, "must be supplied together"),
        ("example:tag", "sha256:not-a-digest", "immutable SHA-256 ID"),
    ],
)
def test_prebuilt_client_contract_fails_closed_before_work(
    tmp_path: Path,
    image: str | None,
    image_id: str | None,
    message: str,
) -> None:
    with pytest.raises(DoctorError, match=message):
        run_doctor(
            tmp_path / "result",
            lane="cluster-amd64-slurm",
            prebuilt_client_image=image,
            expected_client_image_id=image_id,
        )
