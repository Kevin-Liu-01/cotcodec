#!/usr/bin/env python3
"""Validate the preregistered exact-source Infini Memory lifecycle doctor."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments/memory/stage3-infini-memory-lifecycle-provenance-doctor.yaml"
)
EXPECTED_STATUS = (
    "INFINI_MEMORY_ADMISSION_KILLED_UNCONFINED_USER_PATH_"
    "DESTRUCTIVE_DELETE_AND_NONATOMIC_INDEX"
)


class InfiniMemoryLifecycleExperimentError(ValueError):
    """Raised when the registered Infini Memory lifecycle contract drifts."""


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise InfiniMemoryLifecycleExperimentError(
            f"Infini Memory lifecycle {label} drifted"
        )


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    """Load and fail closed on every decision-bearing contract field."""
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise InfiniMemoryLifecycleExperimentError(
            f"cannot load Infini Memory lifecycle experiment: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise InfiniMemoryLifecycleExperimentError(
            "Infini Memory lifecycle contract must be a mapping"
        )
    _equal(
        {key: payload.get(key) for key in (
            "schema_version", "name", "status", "scientific_result", "publication_ready"
        )},
        {
            "schema_version": 1,
            "name": "stage3-infini-memory-lifecycle-provenance-doctor",
            "status": "registered-cpu-falsification",
            "scientific_result": False,
            "publication_ready": False,
        },
        "identity",
    )
    _equal(
        payload.get("source"),
        {
            "source_id": "infini-memory",
            "repository": "https://github.com/infinigence/Infini-Memory",
            "revision": "ddac08ec468e0382e4f14239d94991ab19ae981a",
            "tree": "6cb81be142780eaf7cce36bcd8a64e20ca582042",
            "license": "Apache-2.0",
            "license_sha256": "4309c5d4903cb324a4e6920eb83f5958e86f8270d3fd6ce3e83d7f1db9935aeb",
            "pyproject_sha256": "7eb0deb0fed8b8e70358760c5b72a4e6a85f74159b4d037c62c3f6c5561df789",
            "uv_lock_sha256": "e9bd321ddab3fbe925b81d8ccf2467dcce42256028ad75091adb36e44c77247f",
            "git_archive_tar_sha256": (
                "9da66f63e1c60230d74c2da320fa711c1afe759bbd28058032c8fc78b51bb506"
            ),
            "exact_source_files": {
                "src/infini_memory/manager.py": (
                    "e5387ecc866cd966cbd7020e7ea43330ee81687c4e47274950a4c322b4a8b5d5"
                ),
                "src/infini_memory/convenience.py": (
                    "bb267dba8dfa9b97c1f149060035498da62c9dec9a77bdbd249ede66fb005f43"
                ),
                "src/infini_memory/memory.py": (
                    "57f20cd4caa06a7c9f895d0883df0f235ba4f831dc2c1c9c8fd5c1872995f0cd"
                ),
                "src/infini_memory/config.py": (
                    "3752b35fc0470d5a335dcbcff044a30d47caa5baa447807984d5b3a772b5528b"
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
                "ghcr.io/astral-sh/uv:python3.13-trixie-slim@sha256:"
                "d1e005e6f5aac724b7554db95f1c128a77d8d35b59ebe70e188852b4bdad3a3d"
            ),
            "python_version": "3.13",
            "clean_state_repeats": 2,
            "fresh_process_restarts_per_repeat": 3,
            "dependency_install": "exact-committed-uv-lock-frozen",
            "upstream_test_preflight": "38-passed",
        },
        "runtime",
    )
    _equal(
        payload.get("intervention"),
        {
            "public_api": [
                "Memory.add", "Memory.search", "Memory.get", "Memory.list",
                "Memory.update", "Memory.delete", "Memory.delete_all",
                "Memory.list_users", "Memory.delete_user", "Memory.reset",
            ],
            "fixture_and_fault_seam": ["MemoryManager.add_doc", "MemoryManager._save_index"],
            "external_model_calls": 0,
            "provider_calls": 0,
            "deterministic_llm_double": True,
            "test_normal_crud_restart": True,
            "test_document_and_user_delete_restart": True,
            "test_relative_user_path_confinement": True,
            "test_absolute_user_path_confinement": True,
            "test_alias_equivalent_user_isolation": True,
            "test_escaped_recursive_delete_confinement": True,
            "test_interrupted_update_restart": True,
            "test_interrupted_delete_restart": True,
            "test_truncated_index_restart": True,
            "test_post_delete_current_file_plaintext_residue": True,
            "charge_rewrite_and_retrieval_calls": True,
            "matched_bm25_vs_direct_markdown_diagnostic": True,
        },
        "intervention",
    )
    _equal(
        payload.get("expected_falsification"),
        {
            "status": EXPECTED_STATUS,
            "normal_user_survives_restart": True,
            "normal_document_delete_survives_restart": True,
            "normal_user_delete_survives_restart": True,
            "relative_user_id_escapes_data_root": True,
            "absolute_user_id_overrides_data_root": True,
            "alias_equivalent_user_ids_share_storage": True,
            "escaped_delete_user_removes_path_outside_data_root": True,
            "interrupted_update_exposes_markdown_index_mismatch": True,
            "interrupted_delete_exposes_dangling_index_entry": True,
            "truncated_index_silently_loads_empty_with_markdown_present": True,
            "rewrite_and_retrieval_accounting_completed": True,
            "reproduced_in_two_clean_states": True,
        },
        "expected falsification",
    )
    _equal(
        payload.get("execution"),
        {
            "repetitions": 2,
            "external_api_calls": 0,
            "provider_calls": 0,
            "gpus": 0,
            "max_gpu_hours": 0,
            "wall_clock_limit_minutes": 20,
            "max_deterministic_llm_calls_per_repeat": 16,
            "synthetic_bm25_documents": 4,
            "synthetic_queries": 3,
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
        raise InfiniMemoryLifecycleExperimentError(
            "Infini Memory lifecycle admission drifted"
        )
    return payload


def main() -> int:
    validate_experiment_contract()
    print("Infini Memory lifecycle contract PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
