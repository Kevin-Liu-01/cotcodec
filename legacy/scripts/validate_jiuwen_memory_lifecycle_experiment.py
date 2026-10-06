#!/usr/bin/env python3
"""Validate the pinned JiuwenMemory file-lifecycle falsification contract."""

from __future__ import annotations

from pathlib import Path
from typing import TypeAlias

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments/memory/stage3-jiuwen-memory-file-lifecycle-doctor.yaml"
)
EXPECTED_STATUS = "JIUWEN_FILE_BACKEND_ADMISSION_KILLED_GLOBAL_ID_AND_MIGRATION_RESET"
JSONPrimitive: TypeAlias = None | bool | int | float | str
JSONValue: TypeAlias = JSONPrimitive | list["JSONValue"] | dict[str, "JSONValue"]
JSONObject: TypeAlias = dict[str, JSONValue]


class JiuwenExperimentError(ValueError):
    """Raise when the registered JiuwenMemory contract drifts."""


def _load(path: Path) -> JSONObject:
    """Load one YAML mapping.

    Args:
        path: Experiment contract path.

    Returns:
        Parsed experiment mapping.

    """
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise JiuwenExperimentError(f"cannot load JiuwenMemory experiment: {exc}") from exc
    if not isinstance(payload, dict):
        raise JiuwenExperimentError("JiuwenMemory experiment must be a mapping")
    return payload


def _require_equal(actual: JSONValue, expected: JSONValue, label: str) -> None:
    """Require exact contract equality.

    Args:
        actual: Parsed contract value.
        expected: Registered value.
        label: Error context.

    Returns:
        None.

    """
    if actual != expected:
        raise JiuwenExperimentError(f"JiuwenMemory {label} drifted")


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> JSONObject:
    """Validate the complete JiuwenMemory lifecycle contract.

    Args:
        path: Experiment contract path.

    Returns:
        Validated contract.

    """
    payload = _load(path)
    _validate_identity(payload)
    _validate_source(payload)
    _validate_runtime(payload)
    _validate_intervention(payload)
    _validate_falsification(payload)
    _validate_admission(payload)
    return payload


def _validate_identity(payload: JSONObject) -> None:
    actual = {
        key: payload.get(key)
        for key in ("schema_version", "name", "status", "scientific_result", "publication_ready")
    }
    expected: JSONObject = {
        "schema_version": 1,
        "name": "stage3-jiuwen-memory-file-lifecycle-doctor",
        "status": "registered-cpu-falsification",
        "scientific_result": False,
        "publication_ready": False,
    }
    _require_equal(actual, expected, "identity")


def _validate_source(payload: JSONObject) -> None:
    expected: JSONObject = {
        "source_id": "jiuwen-memory",
        "repository": "https://github.com/openJiuwen-ai/agent-memory",
        "revision": "600432b55e480bec5948ee40089884ccf15a7c5d",
        "tree": "1b6518ba4f0d89d99cb7febd3e3d7a27b2e8347c",
        "version": "2.1.0",
        "license": "Apache-2.0",
        "license_sha256": "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30",
        "pyproject_sha256": "7dae9369fcd9a30857aa445e1f41d06932ebd6969e51ec82fa770a8272dc98db",
        "uv_lock_sha256": "e2a62926d1fd01ad9ecf4a8b305791146bace9ddac5ed941a95490ab66a85d0c",
        "git_archive_tar_sha256": (
            "38c6868fe7a707d1912c0b10a64a5661571b0ed6e341464fea65463d83842c3e"
        ),
    }
    _require_equal(payload.get("source"), expected, "source contract")


def _validate_runtime(payload: JSONObject) -> None:
    expected: JSONObject = {
        "containment": "docker-network-none",
        "provider_secrets": "forbidden",
        "sudo": "forbidden",
        "gpu_count": 0,
        "base_image": (
            "ghcr.io/astral-sh/uv:python3.13-trixie-slim@sha256:"
            "d1e005e6f5aac724b7554db95f1c128a77d8d35b59ebe70e188852b4bdad3a3d"
        ),
        "python_version": 3.13,
        "clean_state_repeats": 2,
        "fresh_process_restarts_per_repeat": 1,
        "python_hash_seeds": [1, 7],
        "frozen_lock_install": "JiuwenMemory[sqlite]",
        "disclosed_overlay": {
            "gmssl": "3.2.2",
            "pycryptodomex": "3.23.0",
            "sqlite-vec": "0.1.9",
        },
    }
    _require_equal(payload.get("runtime"), expected, "runtime contract")


def _validate_intervention(payload: JSONObject) -> None:
    expected: JSONObject = {
        "exact_source_modules": [
            "jiuwen_memory/foundation/store/index/file_index/file_memory_index.py",
            "jiuwen_memory/foundation/store/index/file_index/_vector_index.py",
            "jiuwen_memory/memory_core/migration/migrator/index_version_migrator.py",
        ],
        "model_backend_calls": 0,
        "provider_calls": 0,
        "deterministic_embedding_only": True,
        "test_unique_id_restart_control": True,
        "test_duplicate_id_tenant_isolation": True,
        "test_migration_version_restart": True,
        "test_native_user_scope_delete": True,
        "test_post_delete_plaintext_residue": True,
        "test_committed_lock_conformance": True,
        "graph_subsystem_excluded": True,
    }
    _require_equal(payload.get("intervention"), expected, "intervention")


def _validate_falsification(payload: JSONObject) -> None:
    expected: JSONObject = {
        "status": EXPECTED_STATUS,
        "unique_ids_survive_restart_and_remain_isolated": True,
        "duplicate_id_overwrites_sibling_tenant_index_row": True,
        "duplicate_id_defect_survives_restart": True,
        "migration_index_owner_depends_on_process_hash_order": True,
        "migration_version_resets_on_restart_and_replays": True,
        "native_scoped_delete_is_logically_effective": True,
        "contained_linux_plaintext_residue_scan_completed": True,
        "committed_lock_is_stale": True,
        "reproduced_in_two_clean_states": True,
    }
    _require_equal(payload.get("expected_falsification"), expected, "falsification")


def _validate_admission(payload: JSONObject) -> None:
    admission = payload.get("admission")
    if not isinstance(admission, dict):
        raise JiuwenExperimentError("JiuwenMemory admission must be a mapping")
    expected = {
        "h100_actor": "forbidden-for-this-revision",
        "scientific_claim": "forbidden",
        "publication_claim": "forbidden",
    }
    actual = {key: admission.get(key) for key in expected}
    _require_equal(actual, expected, "admission")
    next_gate = admission.get("next_gate")
    claim_boundary = payload.get("claim_boundary")
    if not isinstance(next_gate, str) or not next_gate.strip():
        raise JiuwenExperimentError("JiuwenMemory next gate is missing")
    if not isinstance(claim_boundary, str) or not claim_boundary.strip():
        raise JiuwenExperimentError("JiuwenMemory claim boundary is missing")


def main() -> int:
    """Validate the default experiment contract.

    Returns:
        Process exit code.

    """
    validate_experiment_contract()
    print("JiuwenMemory file-lifecycle falsification contract PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
