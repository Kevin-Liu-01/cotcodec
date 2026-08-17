from __future__ import annotations

import hashlib
from pathlib import Path

from scripts.validate_hermes_hindsight_experiment import (
    DEFAULT_EXPERIMENT,
    EXPECTED_STATUS,
    validate_experiment_contract,
)

PROJECT_ROOT = DEFAULT_EXPERIMENT.parents[2]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_registered_hindsight_contract_is_negative_and_cpu_only() -> None:
    payload = validate_experiment_contract()
    assert payload["expected_falsification"]["status"] == EXPECTED_STATUS
    assert payload["runtime"]["gpu_count"] == 0
    assert payload["admission"]["memory_quality_h100"] == (
        "forbidden-for-this-revision"
    )
    assert payload["claims"] == {
        "scientific_result": False,
        "publication_ready": False,
        "supports": (
            "exact Hermes retain, recall, prefetch, and session-end retention "
            "transport; native restart persistence; logical tenant isolation; "
            "logical deletion"
        ),
        "does_not_support": (
            "a Hermes purge tool, physical erasure, memory quality, agent "
            "improvement, H100 admission, or publication claims"
        ),
    }


def test_registered_hindsight_runtime_hashes_match_live_files() -> None:
    payload = validate_experiment_contract()
    controls = payload["runtime"]["controls"]
    paths = {
        "backend_dockerfile_sha256": (
            PROJECT_ROOT
            / "infra/memory-baselines/hermes-hindsight/Dockerfile.backend-doctor"
        ),
        "adapter_dockerfile_sha256": (
            PROJECT_ROOT
            / "infra/memory-baselines/hermes-hindsight/Dockerfile.adapter-doctor"
        ),
        "adapter_doctor_sha256": (
            PROJECT_ROOT / "infra/memory-baselines/hermes-hindsight/adapter_doctor.py"
        ),
        "model_stub_sha256": (
            PROJECT_ROOT / "infra/memory-baselines/hermes-openviking/model_stub.py"
        ),
        "doctor_sha256": PROJECT_ROOT / "scripts/run_hermes_hindsight_doctor.py",
    }
    assert {field: _sha256(path) for field, path in paths.items()} == {
        field: controls[field] for field in paths
    }


def test_hindsight_images_are_nonroot_and_do_not_install_with_sudo() -> None:
    backend = (
        PROJECT_ROOT
        / "infra/memory-baselines/hermes-hindsight/Dockerfile.backend-doctor"
    ).read_text(encoding="utf-8")
    adapter = (
        PROJECT_ROOT
        / "infra/memory-baselines/hermes-hindsight/Dockerfile.adapter-doctor"
    ).read_text(encoding="utf-8")
    doctor = (PROJECT_ROOT / "scripts/run_hermes_hindsight_doctor.py").read_text(
        encoding="utf-8"
    )
    assert "USER 65532:65532" in backend
    assert "USER 65532:65532" in adapter
    assert "hindsight-client==0.6.1" in adapter
    assert "sudo" not in backend
    assert "sudo" not in adapter
    assert '"--read-only"' in doctor
    assert '"--cap-drop",\n            "ALL"' in doctor
    assert '"no-new-privileges"' in doctor
