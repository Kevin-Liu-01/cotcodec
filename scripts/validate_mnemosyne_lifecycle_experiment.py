#!/usr/bin/env python3
"""Fail-closed validator for the Mnemosyne lifecycle falsification."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT
    / "experiments"
    / "memory"
    / "stage3-mnemosyne-lifecycle-doctor.yaml"
)
EXPECTED_STATUS = "BLOCKED_CONSOLIDATED_FORGET_AND_NO_REACTIVATION"
EXPECTED_SOURCE = {
    "source_id": "mnemosyne-oss",
    "repository": "https://github.com/mnemosyne-oss/mnemosyne",
    "revision": "a0e14243e04dbe3fc29287e58126ff5dc0e02b35",
    "tree": "31237041cfca8cbac932c9a589d6133e07927873",
    "version": "3.16.0",
    "git_archive_tar_sha256": (
        "789ad4b0d531bd7e399a9158f05d37ee663713725a3fbdf561c00ffd03a721cd"
    ),
    "license": "MIT",
    "license_sha256": (
        "f391a152fdd56e2f1ab85539ea29ca9a7c6a5ece217fa9ea37309737506199e0"
    ),
    "uv_lock_sha256": (
        "17114e8eeba15ff50b99c92c77effc259ddf98577184e0eb5b7fdde871dd4071"
    ),
}


class MnemosyneExperimentError(ValueError):
    """Raised when the registered Mnemosyne experiment drifts."""


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise MnemosyneExperimentError(
            f"cannot load Mnemosyne experiment: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise MnemosyneExperimentError("Mnemosyne experiment must be a mapping")
    if (
        payload.get("schema_version") != 1
        or payload.get("name") != "stage3-mnemosyne-lifecycle-doctor"
        or payload.get("status") != "registered-cpu-falsification"
        or payload.get("scientific_result") is not False
        or payload.get("publication_ready") is not False
    ):
        raise MnemosyneExperimentError("Mnemosyne experiment identity drifted")
    if payload.get("source") != EXPECTED_SOURCE:
        raise MnemosyneExperimentError("Mnemosyne source contract drifted")

    runtime = payload.get("runtime")
    if not isinstance(runtime, dict):
        raise MnemosyneExperimentError("Mnemosyne runtime contract is missing")
    expected_runtime = {
        "containment": "docker-network-none",
        "local_platform": "linux/arm64",
        "runtime_network": "none",
        "read_only_root": True,
        "cap_drop_all": True,
        "no_new_privileges": True,
        "provider_secrets": "forbidden",
        "sudo": "forbidden",
        "gpu_count": 0,
        "max_gpu_hours": 0,
        "clean_state_repeats": 2,
        "base_image": (
            "ghcr.io/astral-sh/uv@sha256:"
            "d1e005e6f5aac724b7554db95f1c128a77d8d35b59ebe70e188852b4bdad3a3d"
        ),
        "base_image_version": "0.12.5-python3.13-trixie-slim",
    }
    if runtime != expected_runtime:
        raise MnemosyneExperimentError("Mnemosyne runtime contract drifted")

    intervention = payload.get("intervention")
    if not isinstance(intervention, dict):
        raise MnemosyneExperimentError("Mnemosyne intervention is missing")
    if intervention.get("sessions") != ["tenant-a", "tenant-b"]:
        raise MnemosyneExperimentError("Mnemosyne session roster drifted")
    expected_intervention = {
        "storage": "sqlite",
        "embeddings": False,
        "model_calls": 0,
        "external_api_calls": 0,
        "force_sleep": True,
        "fresh_process_phases": ["prepare", "verify-restart", "purge"],
        "test_duplicate_retry": True,
        "test_session_isolation": True,
        "test_restart": True,
        "test_recall_reactivation": True,
        "test_documented_forget": True,
        "test_plaintext_residue": True,
    }
    for field, expected in expected_intervention.items():
        if intervention.get(field) != expected:
            raise MnemosyneExperimentError(
                f"Mnemosyne intervention field {field} drifted"
            )

    expected = payload.get("expected_falsification")
    required_expected = {
        "status": EXPECTED_STATUS,
        "working_to_episodic_consolidation": True,
        "consolidated_source_hidden_from_active_context": True,
        "consolidated_memory_recallable_after_restart": True,
        "recall_promotes_to_active_context": False,
        "documented_forget_removes_episodic_summary": False,
        "native_session_scoped_purge_available": False,
        "plaintext_canary_residue_after_documented_forget": True,
        "reproduced_in_two_clean_states": True,
    }
    if expected != required_expected:
        raise MnemosyneExperimentError(
            "Mnemosyne expected falsification contract drifted"
        )

    admission = payload.get("admission")
    if (
        not isinstance(admission, dict)
        or admission.get("h100_actor") != "forbidden-for-this-revision"
        or admission.get("scientific_claim") != "forbidden"
        or admission.get("publication_claim") != "forbidden"
        or not isinstance(admission.get("next_gate"), str)
        or not admission["next_gate"].strip()
    ):
        raise MnemosyneExperimentError("Mnemosyne admission contract drifted")
    return payload


def main() -> int:
    validate_experiment_contract()
    print("Mnemosyne lifecycle falsification contract PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
