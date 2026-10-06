#!/usr/bin/env python3
"""Fail-closed validator for the pinned Shodh tier-admission falsifier."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments/memory/stage3-shodh-tier-admission-doctor.yaml"
)
EXPECTED_STATUS = "BLOCKED_OVERLAPPING_RESIDENCY_AND_RESTART_STRANDING"
EXPECTED_SOURCE = {
    "source_id": "shodh-memory",
    "repository": "https://github.com/varun29ankuS/shodh-memory",
    "revision": "98c6e4861847a76f75eb880acf9e145d30794a46",
    "tree": "a7c6ee81b9299cfe4fd56789b1cfd76a5c46bc85",
    "git_archive_tar_sha256": (
        "e5930fc638929d98e2149452afd2d7d02c74134115e78bcd8197d7f06165ed60"
    ),
    "license": "Apache-2.0",
    "license_sha256": (
        "219672554a141ac4ba8a1cb3fecf8d1e3209515963ff1c1f946c5cda3a85d86d"
    ),
    "cargo_lock_sha256": (
        "0f3356ec80fe3b3f683fd896e2a65c23d5cc8e11fc175b3f90efc58487b03972"
    ),
    "cargo_toml_sha256": (
        "d55820c0eeba14f1478925fd50e2823425baa30193976719e73534afc92892db"
    ),
    "memory_module_sha256": (
        "bb4b9d19d343aa567b9a47a0b191324fccea3658c81ee5e391b2b7bfa604583e"
    ),
    "memory_types_sha256": (
        "f58a702a2e1ae75798f8b6835214dec5a230315e4ce4ed262605cce06ee72cbf"
    ),
}


class ShodhExperimentError(ValueError):
    """Raised when the registered Shodh falsifier drifts."""


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise ShodhExperimentError(f"cannot load Shodh experiment: {exc}") from exc
    if not isinstance(payload, dict):
        raise ShodhExperimentError("Shodh experiment must be a mapping")
    if (
        payload.get("schema_version") != 1
        or payload.get("name") != "stage3-shodh-tier-admission-doctor"
        or payload.get("status") != "registered-cpu-falsification"
        or payload.get("scientific_result") is not False
        or payload.get("publication_ready") is not False
    ):
        raise ShodhExperimentError("Shodh experiment identity drifted")
    if payload.get("source") != EXPECTED_SOURCE:
        raise ShodhExperimentError("Shodh source contract drifted")

    runtime = payload.get("runtime")
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
            "rust@sha256:867f1d1162913c401378a8504fb17fe2032c760dc316448766f150a130204aad"
        ),
        "dependency_lock": "Cargo.lock",
        "cargo_locked": True,
        "offline_simplified_embeddings": True,
    }
    if runtime != expected_runtime:
        raise ShodhExperimentError("Shodh runtime contract drifted")

    intervention = payload.get("intervention")
    required_interventions = {
        "fresh_working_record_storage_probe",
        "fresh_process_restart",
        "offline_aged_session_restart_probe",
        "real_maintenance_path",
        "public_forget_all_probe",
        "physical_plaintext_residue_probe",
    }
    if not isinstance(intervention, dict) or any(
        intervention.get(field) is not True for field in required_interventions
    ):
        raise ShodhExperimentError("Shodh intervention contract drifted")
    if any(
        intervention.get(field) != 0
        for field in ("model_calls", "embedding_provider_calls", "external_api_calls")
    ):
        raise ShodhExperimentError("Shodh intervention must remain zero-model")

    expected = payload.get("expected_falsification")
    true_fields = {
        "new_working_record_already_in_long_term_storage",
        "restart_drops_active_caches",
        "restart_preserves_stale_working_tier_label",
        "eligible_persisted_session_is_stranded_after_restart",
        "logical_forget_all_hides_record_after_restart",
        "forget_all_return_overcounts_overlapping_tiers",
        "reproduced_in_two_clean_states",
    }
    if (
        not isinstance(expected, dict)
        or expected.get("status") != EXPECTED_STATUS
        or any(expected.get(field) is not True for field in true_fields)
        or expected.get("plaintext_residue_after_forget_all") is not False
        or expected.get("plaintext_scan_is_erasure_proof") is not False
    ):
        raise ShodhExperimentError("Shodh falsification gates drifted")
    admission = payload.get("admission")
    if (
        not isinstance(admission, dict)
        or admission.get("h100_actor") != "forbidden-for-this-revision"
        or admission.get("scientific_claim") != "forbidden"
        or admission.get("publication_claim") != "forbidden"
    ):
        raise ShodhExperimentError("Shodh admission contract drifted")
    return payload


def main() -> int:
    validate_experiment_contract()
    print("Shodh tier-admission falsification contract PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
