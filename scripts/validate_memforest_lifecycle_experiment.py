#!/usr/bin/env python3
"""Validate the preregistered exact-source MemForest lifecycle doctor."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments/memory/stage3-memforest-native-lifecycle-doctor.yaml"
)
EXPECTED_STATUS = "MEMFOREST_LIFECYCLE_ADMISSION_KILLED_UNCONFINED_TENANT_PATH_AND_TORN_SNAPSHOT"


class MemForestLifecycleExperimentError(ValueError):
    """Raised when the registered MemForest lifecycle contract drifts."""


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise MemForestLifecycleExperimentError(f"MemForest lifecycle {label} drifted")


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    """Load and fail closed on every decision-bearing contract field."""
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise MemForestLifecycleExperimentError(
            f"cannot load MemForest lifecycle experiment: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise MemForestLifecycleExperimentError("MemForest lifecycle contract must be a mapping")
    _equal(
        {
            key: payload.get(key)
            for key in (
                "schema_version",
                "name",
                "status",
                "scientific_result",
                "publication_ready",
            )
        },
        {
            "schema_version": 1,
            "name": "stage3-memforest-native-lifecycle-doctor",
            "status": "registered-cpu-falsification",
            "scientific_result": False,
            "publication_ready": False,
        },
        "identity",
    )
    _equal(
        payload.get("source"),
        {
            "source_id": "memforest",
            "repository": "https://github.com/Concyclics/MemForest",
            "revision": "fb4320a84d296bf7b0752d7ef1f2ad0726ae0b22",
            "tree": "2e30793c77ef0b7fc8b36bd6d3648a1d9f2fecb2",
            "license": "MIT",
            "license_sha256": ("f91f1d776c397faf0e8f2b87e23e7e7f9bd312ec0751397ab183752b1b217efc"),
            "requirements_sha256": (
                "e596f2354b4f732fd45bd3e8f958650bf2309bd1511fbc4f69a405ab236b57f4"
            ),
            "git_archive_tar_sha256": (
                "3809857bcd1f2fb799038a604149a1354277f80dd87893c7f2e3949c743211e0"
            ),
            "exact_source_files": {
                "src/forest/memforest.py": (
                    "2823f581fc07524f088c30a083fba912f93e786854a7c837e2b866465c9263ba"
                ),
                "src/forest/user_forest.py": (
                    "aab1c22eed1558bf2bb50e4c4c6a23e6029fe4b7e63f8a7d06447acf7e0c6e9c"
                ),
                "src/forest/session_registry.py": (
                    "86323d3a9cb498f41b2454da66af61e54d3ab4cd27ae7b9070d40a7d45ea8f5d"
                ),
            },
        },
        "source",
    )
    _equal(
        payload.get("runtime"),
        {
            "containment": "docker-network-none",
            "provider_secrets": "forbidden",
            "sudo": "forbidden",
            "gpu_count": 0,
            "base_image": (
                "docker.io/library/python:3.12.11-slim-bookworm@sha256:"
                "519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7"
            ),
            "python_version": "3.12.11",
            "clean_state_repeats": 2,
            "fresh_process_restarts_per_repeat": 3,
            "dependency_install": "exact-committed-direct-requirements-no-transitive-lock",
        },
        "runtime",
    )
    _equal(
        payload.get("intervention"),
        {
            "public_api": [
                "MemForest.register_user",
                "MemForest.ingest_session",
                "MemForest.delete_session",
                "MemForest.save",
            ],
            "external_model_calls": 0,
            "provider_calls": 0,
            "deterministic_chat_double": True,
            "deterministic_embedding_double": True,
            "test_normal_tenant_crud_restart": True,
            "test_saved_session_deletion_restart": True,
            "test_relative_user_path_confinement": True,
            "test_absolute_user_path_confinement": True,
            "test_alias_equivalent_user_isolation": True,
            "test_interrupted_multifile_save_restart": True,
            "test_native_tenant_purge_surface": True,
            "test_post_delete_plaintext_residue": True,
            "matched_incremental_vs_clean_rebuild_diagnostic": True,
        },
        "intervention",
    )
    _equal(
        payload.get("expected_falsification"),
        {
            "status": EXPECTED_STATUS,
            "normal_user_survives_restart": True,
            "saved_session_delete_survives_restart": True,
            "relative_user_id_escapes_snapshot_root": True,
            "absolute_user_id_overrides_snapshot_root": True,
            "alias_equivalent_user_ids_share_storage": True,
            "interrupted_save_exposes_mixed_component_generations": True,
            "native_tenant_purge_absent": True,
            "write_path_diagnostic_completed": True,
            "reproduced_in_two_clean_states": True,
        },
        "expected falsification",
    )
    execution = payload.get("execution")
    _equal(
        execution,
        {
            "repetitions": 2,
            "external_api_calls": 0,
            "llm_calls": 0,
            "gpus": 0,
            "max_gpu_hours": 0,
            "wall_clock_limit_minutes": 20,
            "synthetic_seed_sessions": 4,
            "synthetic_incremental_sessions": 1,
        },
        "execution",
    )
    admission = payload.get("admission")
    if (
        not isinstance(admission, dict)
        or admission.get("h100_actor") != "forbidden-for-this-revision-if-falsified"
        or admission.get("scientific_claim") != "forbidden"
        or admission.get("publication_claim") != "forbidden"
        or not isinstance(admission.get("next_gate"), str)
        or not admission["next_gate"].strip()
        or not isinstance(payload.get("claim_boundary"), str)
        or not payload["claim_boundary"].strip()
    ):
        raise MemForestLifecycleExperimentError("MemForest lifecycle admission drifted")
    return payload


def main() -> int:
    validate_experiment_contract()
    print("MemForest native lifecycle contract PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
