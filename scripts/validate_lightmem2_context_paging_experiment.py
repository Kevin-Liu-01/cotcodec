#!/usr/bin/env python3
"""Fail-closed validator for the LightMem2 context-paging falsifier."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT
    / "experiments/memory/stage3-lightmem2-context-paging-doctor.yaml"
)
EXPECTED_STATUS = (
    "BLOCKED_CROSS_SESSION_DISCLOSURE_ARCHIVE_COLLISION_AND_NO_NATIVE_PURGE"
)
EXPECTED_SOURCE = {
    "source_id": "lightmem2",
    "repository": "https://github.com/zjunlp/LightMem2",
    "revision": "dfc67e8bc9373ca5b31bb412298565c9d65b29b6",
    "tree": "559fbe66aec30fc8920a8d1217712f5673837116",
    "version": "0.1.0-beta.1",
    "git_archive_tar_sha256": (
        "973b68b4cf35dcf7fcc29f2c813e8d61f820d71decb391bae9b0bde314f58169"
    ),
    "license": "MIT",
    "license_sha256": (
        "82ae945b07c46324863ffea0c5b269d2cebf724bbb3377e2b2786219430bd02d"
    ),
    "package_json_sha256": (
        "c2f6ab4250b3bd2ce6b2e464c94d649bbc35c270536c77d690f3033ae749160a"
    ),
    "pnpm_lock_sha256": (
        "c4f920b7aca698dc3b922ec0e4be4a8f5f91a6a1ab49530a73c7bace8fa16235"
    ),
    "archive_source_sha256": (
        "a7a812e00a0ca67fcfafea04d5296972318e0ae97e950271073f72b5aded5061"
    ),
    "mcp_source_sha256": (
        "58be265fa07a3fbbe586fe2856778e36dc6f1fd9352becb66129aa51991fb568"
    ),
    "eviction_source_sha256": (
        "ce6782b5285da06c56e2a49ef44bccb97a7637b8ad42d16cfe0a9dfdf737e698"
    ),
}


class LightMem2ExperimentError(ValueError):
    """Raised when the registered LightMem2 contract drifts."""


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise LightMem2ExperimentError(
            f"cannot load LightMem2 experiment: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise LightMem2ExperimentError("LightMem2 experiment must be a mapping")
    if (
        payload.get("schema_version") != 1
        or payload.get("name") != "stage3-lightmem2-context-paging-doctor"
        or payload.get("status") != "registered-cpu-falsification"
        or payload.get("scientific_result") is not False
        or payload.get("publication_ready") is not False
    ):
        raise LightMem2ExperimentError("LightMem2 experiment identity drifted")
    if payload.get("source") != EXPECTED_SOURCE:
        raise LightMem2ExperimentError("LightMem2 source contract drifted")

    runtime = payload.get("runtime")
    required_runtime = {
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
        "dependency_lock": "pnpm-lock.yaml",
        "node_version": "24.19.0",
        "package_manager": "pnpm@10.32.1",
    }
    if not isinstance(runtime, dict) or any(
        runtime.get(field) != expected for field, expected in required_runtime.items()
    ):
        raise LightMem2ExperimentError("LightMem2 runtime contract drifted")

    suite = payload.get("upstream_relevant_suite")
    if not isinstance(suite, dict) or {
        field: suite.get(field) for field in ("tests", "passed", "failed", "skipped")
    } != {"tests": 49, "passed": 47, "failed": 2, "skipped": 0}:
        raise LightMem2ExperimentError("LightMem2 upstream-suite contract drifted")

    intervention = payload.get("intervention")
    if (
        not isinstance(intervention, dict)
        or intervention.get("phases") != ["prepare", "verify-restart", "purge-probe"]
        or any(
            intervention.get(field) != 0
            for field in ("model_calls", "embedding_model_calls", "external_api_calls")
        )
    ):
        raise LightMem2ExperimentError("LightMem2 intervention contract drifted")

    expected = payload.get("expected_falsification")
    if not isinstance(expected, dict) or expected.get("status") != EXPECTED_STATUS:
        raise LightMem2ExperimentError("LightMem2 expected status drifted")
    true_fields = {
        "archive_before_stub_succeeded",
        "strict_session_lookup_rejected_other_session",
        "unscoped_mcp_resolver_recovered_other_session",
        "archive_filename_collision_reused_path",
        "first_key_resolved_to_second_payload",
        "restart_preserved_session_a_archive",
        "restart_unscoped_mcp_resolver_disclosed_b_to_any_caller",
        "plaintext_a_remains",
        "plaintext_b_remains",
        "reproduced_in_two_clean_states",
    }
    false_fields = {
        "recovery_api_accepts_session_scope",
        "native_scoped_purge_api_available",
    }
    if any(expected.get(field) is not True for field in true_fields) or any(
        expected.get(field) is not False for field in false_fields
    ):
        raise LightMem2ExperimentError("LightMem2 falsification gates drifted")
    admission = payload.get("admission")
    if (
        not isinstance(admission, dict)
        or admission.get("h100_actor") != "forbidden-for-this-revision"
    ):
        raise LightMem2ExperimentError("LightMem2 H100 admission drifted")
    return payload


def main() -> int:
    validate_experiment_contract()
    print("LightMem2 context-paging falsification contract PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
