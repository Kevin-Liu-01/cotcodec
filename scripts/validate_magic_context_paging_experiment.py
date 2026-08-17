#!/usr/bin/env python3
"""Fail-closed validator for the Magic Context paging falsification."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments" / "memory" / "stage3-magic-context-paging-doctor.yaml"
)
EXPECTED_STATUS = "BLOCKED_PORTABLE_LIFECYCLE_AND_SECURE_PURGE_REPRODUCED"
EXPECTED_SOURCE = {
    "source_id": "magic-context",
    "repository": "https://github.com/cortexkit/magic-context",
    "revision": "13e1d4c3fa3803ba1f4595029d8c4750dc9bef98",
    "tree": "f420beb3be130544534ff7a9778a49e92fa0ed75",
    "git_archive_tar_sha256": (
        "8eb4b81542b157d55fb4c43cea523fc8297a6b360f8a90feff2a8737b8d40080"
    ),
    "license": "MIT",
    "license_sha256": (
        "0e3d1aa1cbe4aec50224fc6c91eb898d42949d6ff84fe515f9e2bb0663f5d483"
    ),
    "bun_lock_sha256": (
        "8e8bc07020c1ad17a5a560740b8ec5f108a205b9c58cce166340b99251b9cb5f"
    ),
}


class MagicContextExperimentError(ValueError):
    """Raised when the registered Magic Context contract drifts."""


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise MagicContextExperimentError(f"cannot load Magic Context experiment: {exc}") from exc
    if not isinstance(payload, dict):
        raise MagicContextExperimentError("Magic Context experiment must be a mapping")
    if (
        payload.get("schema_version") != 1
        or payload.get("name") != "stage3-magic-context-paging-doctor"
        or payload.get("status") != "registered-cpu-falsification"
        or payload.get("scientific_result") is not False
    ):
        raise MagicContextExperimentError("Magic Context experiment identity drifted")
    if payload.get("source") != EXPECTED_SOURCE:
        raise MagicContextExperimentError("Magic Context source contract drifted")

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
    }
    if not isinstance(runtime, dict):
        raise MagicContextExperimentError("Magic Context runtime contract is missing")
    for field, expected in expected_runtime.items():
        if runtime.get(field) != expected:
            raise MagicContextExperimentError(f"Magic Context runtime field {field} drifted")
    if "@sha256:" not in str(runtime.get("local_base_image", "")):
        raise MagicContextExperimentError("Magic Context base image must be digest-pinned")

    native = payload.get("native_capability_contract")
    required_refused = {
        "semantic-item-active-to-inactive-transition",
        "semantic-item-inactive-to-active-transition",
        "exact-raw-json-transcript-recovery",
        "persistent-promotion-back-into-active-context",
        "cross-harness-security-tenancy",
        "native-secure-purge",
    }
    if not isinstance(native, dict) or set(native.get("refused", [])) != required_refused:
        raise MagicContextExperimentError("Magic Context capability refusals drifted")

    intervention = payload.get("intervention")
    if not isinstance(intervention, dict):
        raise MagicContextExperimentError("Magic Context intervention is missing")
    for field in ("historian", "dreamer", "project_memory", "embeddings"):
        if intervention.get(field) is not False:
            raise MagicContextExperimentError(f"Magic Context intervention {field} drifted")
    for field in ("model_calls", "embedding_calls", "network_calls"):
        if intervention.get(field) != 0:
            raise MagicContextExperimentError(f"Magic Context intervention {field} drifted")

    expected = payload.get("expected_falsification")
    required_findings = {
        "status": EXPECTED_STATUS,
        "chronological_prompt_paging_supported": True,
        "oldest_compartment_omitted_but_stored": True,
        "supported_text_and_tool_projection_restart_stable": True,
        "reasoning_and_structural_parts_are_not_recovered": True,
        "host_raw_row_deletion_makes_expansion_unrecoverable": True,
        "same_session_id_cross_harness_alias_reproduced": True,
        "physical_zero_residue_after_logical_clear": False,
        "reproduced_in_two_clean_states": True,
    }
    if not isinstance(expected, dict) or any(
        expected.get(field) != value for field, value in required_findings.items()
    ):
        raise MagicContextExperimentError("Magic Context falsification contract drifted")
    admission = payload.get("admission")
    if (
        not isinstance(admission, dict)
        or admission.get("portable_lifecycle") != "blocked"
        or admission.get("semantic_memory_h100") != "forbidden-for-this-mechanism"
    ):
        raise MagicContextExperimentError("Magic Context admission contract drifted")
    return payload


def main() -> int:
    validate_experiment_contract()
    print("Magic Context paging falsification contract PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
