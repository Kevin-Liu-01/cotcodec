#!/usr/bin/env python3
"""Fail-closed validator for the pinned Memoria transactional lifecycle doctor."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments/memory/stage3-memoria-transactional-lifecycle-doctor.yaml"
)
EXPECTED_STATUS = (
    "BLOCKED_SHARED_TABLE_BRANCH_EXPOSURE_SOFT_PURGE_RESIDUE_AND_NONATOMIC_ROLLBACK"
)


class MemoriaExperimentError(ValueError):
    """Raised when the registered Memoria source/runtime contract drifts."""


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise MemoriaExperimentError(f"cannot load Memoria experiment: {exc}") from exc
    if not isinstance(payload, dict):
        raise MemoriaExperimentError("Memoria experiment must be a mapping")
    if {
        "schema_version": payload.get("schema_version"),
        "name": payload.get("name"),
        "status": payload.get("status"),
        "scientific_result": payload.get("scientific_result"),
        "publication_ready": payload.get("publication_ready"),
    } != {
        "schema_version": 1,
        "name": "stage3-memoria-transactional-lifecycle-doctor",
        "status": "registered-cpu-falsification",
        "scientific_result": False,
        "publication_ready": False,
    }:
        raise MemoriaExperimentError("Memoria experiment identity drifted")
    if payload.get("source") != {
        "source_id": "memoria-matrixorigin",
        "repository": "https://github.com/matrixorigin/Memoria",
        "revision": "efd3d6515969971dfa894737272b8317bcb643e7",
        "tree": "c07d7b427a9d664d8473b0c2139ecc0d72e229d4",
        "version": "0.4.0",
        "license": "Apache-2.0",
        "license_sha256": (
            "a6e2f408924ad44acabe43da942d149060a4e8174a8f30240a089bda10279607"
        ),
        "cargo_lock_sha256": (
            "904c09b1ba24b6c27ca8c20093b1e96de1386201fcc4a0f333a3149e0782d435"
        ),
        "git_archive_tar_sha256": (
            "a81f15ca11c616d477e929853019a2156799229f75c1d264a761fe7b42cdaa2e"
        ),
    }:
        raise MemoriaExperimentError("Memoria source contract drifted")
    if payload.get("runtime") != {
        "containment": "docker-internal-network",
        "runtime_network": "internal-only",
        "provider_secrets": "forbidden",
        "sudo": "forbidden",
        "gpu_count_inside_containers": 0,
        "matrixone_image": (
            "matrixorigin/matrixone@sha256:"
            "66e2e0123d32094bff32ef7b8ba06d6d84391983cd1c9c41329dc3f7a05a2518"
        ),
        "rust_builder_image": (
            "rust:1.85-slim@sha256:"
            "a5da637ee23946bafb8517476efe46cbc24f1d15d2099a26bd1f039c005c1a9a"
        ),
        "debian_runtime_image": (
            "debian:bookworm-slim@sha256:"
            "817e6cf99d6fc127ff4ffe8580049b60deba0adfbbb2bd65ddc3ef8fbb7aade0"
        ),
        "matrixone_restarts": 2,
        "clean_state_repeats": 2,
    }:
        raise MemoriaExperimentError("Memoria runtime contract drifted")
    if payload.get("intervention") != {
        "exact_source_crates": ["memoria-git", "memoria-storage"],
        "database_mode": "legacy-shared-database-falsifier",
        "embedding_provider": "deterministic-none",
        "provider_calls": 0,
        "model_backend_calls": 0,
        "test_snapshot_create_restore_drop": True,
        "test_branch_isolation_and_native_merge": True,
        "test_merge_idempotency": True,
        "test_cross_user_branch_visibility": True,
        "test_restart_persistence": True,
        "test_soft_purge_physical_residue": True,
        "test_nonatomic_restore_source_contract": True,
    }:
        raise MemoriaExperimentError("Memoria intervention contract drifted")
    if payload.get("expected_falsification") != {
        "status": EXPECTED_STATUS,
        "branch_snapshot_merge_positive_path": True,
        "shared_database_branch_contains_other_user_rows": True,
        "purge_leaves_inactive_memory_row": True,
        "snapshot_restore_is_delete_then_insert": True,
        "reproduced_in_two_clean_states": True,
    }:
        raise MemoriaExperimentError("Memoria falsification contract drifted")
    admission = payload.get("admission")
    if (
        not isinstance(admission, dict)
        or admission.get("h100_actor") != "forbidden-for-this-revision"
        or admission.get("scientific_claim") != "forbidden"
        or admission.get("publication_claim") != "forbidden"
        or not isinstance(admission.get("next_gate"), str)
        or not admission["next_gate"].strip()
    ):
        raise MemoriaExperimentError("Memoria admission contract drifted")
    return payload


def main() -> int:
    validate_experiment_contract()
    print("Memoria transactional lifecycle falsification contract PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
