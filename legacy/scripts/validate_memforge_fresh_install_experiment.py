#!/usr/bin/env python3
"""Fail-closed validator for the exact MemForge fresh-install falsifier."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments/memory/stage3-memforge-fresh-install-doctor.yaml"
)
EXPECTED_STATUS = "MEMFORGE_FRESH_INSTALL_ADMISSION_KILLED"
EXPECTED_SOURCE = {
    "source_id": "memforge",
    "repository": "https://github.com/salishforge/memforge",
    "revision": "16e2f15c5881a38911f64ca81b3dc0b25d6207ec",
    "tree": "97411a5c0318c3f4b1d273ab0696b915184fca3a",
    "declared_version": "3.7.0",
    "license": "MIT",
    "license_sha256": (
        "dac7f81d95c038f342d1afd54d48527ac370ed03bb20b008dfefb68f1d6fd6b3"
    ),
    "git_archive_tar_sha256": (
        "e2f588676aa06e95cb07cc20224e336a1ce7ff1b9b5757fa808f57323b4b0b93"
    ),
    "dependency_lock": "package-lock.json",
    "dependency_lock_sha256": (
        "15c4f6a7e24ea93042b608143eae9c698dca7ccf57180f2d18e1309cb8cc32c9"
    ),
    "canonical_schema_sha256": (
        "95ee46167dcbaf7617669e7720680978f640f6ae7cf4b37cad32f5d5db82779f"
    ),
}
EXPECTED_RUNTIME = {
    "containment": "docker-network-none",
    "read_only_root": True,
    "cap_drop_all": True,
    "no_new_privileges": True,
    "provider_secrets": "forbidden",
    "sudo": "forbidden",
    "gpu_count_inside_containers": 0,
    "clean_state_repeats": 2,
    "official_compose_postgres_image": (
        "postgres@sha256:cf78e76683b9ca8c5733cbbdce6c9262b45b6767934dd0a95e671f9a0fc20685"
    ),
    "pgvector_control_image": (
        "pgvector/pgvector@sha256:ccc6e83d6e35e931dc7c5def2022729d5a6c370318d099181995567ff1fb4d6b"
    ),
}


class MemForgeExperimentError(ValueError):
    """Raised when the registered MemForge falsifier drifts."""


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise MemForgeExperimentError("experiment must be a mapping")
    if {
        "schema_version": payload.get("schema_version"),
        "name": payload.get("name"),
        "status": payload.get("status"),
        "scientific_result": payload.get("scientific_result"),
        "publication_ready": payload.get("publication_ready"),
    } != {
        "schema_version": 1,
        "name": "stage3-memforge-fresh-install-doctor",
        "status": "registered-cpu-falsification",
        "scientific_result": False,
        "publication_ready": False,
    }:
        raise MemForgeExperimentError("experiment identity drifted")
    if payload.get("source") != EXPECTED_SOURCE:
        raise MemForgeExperimentError("source contract drifted")
    if payload.get("runtime") != EXPECTED_RUNTIME:
        raise MemForgeExperimentError("runtime contract drifted")
    if payload.get("intervention") != {
        "subsystem": "exact-canonical-schema-fresh-install",
        "provider_calls": 0,
        "model_backend_calls": 0,
        "official_compose_image_trial": True,
        "pgvector_enabled_control_trial": True,
        "schema_patch_applied": False,
    }:
        raise MemForgeExperimentError("intervention contract drifted")
    if payload.get("expected_falsification") != {
        "status": EXPECTED_STATUS,
        "official_compose_image_lacks_vector_extension": True,
        "canonical_schema_references_warm_tier_before_creation": True,
        "exact_revision_lifecycle_not_executable": True,
    }:
        raise MemForgeExperimentError("falsification contract drifted")
    if payload.get("admission") != {
        "h100_actor": "forbidden-for-this-revision",
        "hot_warm_cold_lifecycle": "not-evaluated",
        "graph_quality": "not-evaluated",
        "memory_quality": "not-evaluated",
        "repair_arm": "requires-separate-contract",
        "scientific_claim": "forbidden",
        "publication_claim": "forbidden",
    }:
        raise MemForgeExperimentError("admission contract drifted")
    return payload


def main() -> int:
    validate_experiment_contract()
    print("MemForge fresh-install falsification contract PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
