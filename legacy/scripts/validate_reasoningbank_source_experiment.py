#!/usr/bin/env python3
"""Fail-closed validator for the ReasoningBank source-admission contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT
    / "experiments"
    / "memory"
    / "stage3-reasoningbank-source-admission-doctor.yaml"
)

EXPECTED_SOURCE = {
    "source_id": "reasoningbank",
    "repository": "https://github.com/google-research/reasoning-bank",
    "revision": "ed80611788292ea739f1effd31f16c53823b8a0d",
    "tree": "7cc5e6e08ee8035cde81f1fb9fd871d32423a3e3",
    "git_archive_tar_sha256": (
        "d85d169c84f82782cefc50044adc192ab1d28956f36e177de0bf213d48298e09"
    ),
    "license": "Apache-2.0",
    "license_sha256": (
        "58d1e17ffe5109a7ae296caafcadfdbe6a7d176f0bc4ab01e12a689b0499d8bd"
    ),
    "pyproject_sha256": (
        "8d2b9f61b5cae47ed7a83e61e4893f9c0a2c1035fe37ef64006748ab4934cfbe"
    ),
    "uv_lock_sha256": (
        "6835cc5149faf4ddd573cae98851bbd5db6844a1bed567fe8a85525d862d77fa"
    ),
    "critical_file_sha256s": {
        "WebArena/run.py": (
            "f9edcac62cc612f48db9859c60f71b7479aa126beda802437dd82d81030817b3"
        ),
        "WebArena/memory_management.py": (
            "35b8b800180024f3446c4a295fe9d7c19d4aa2cddd0b2f2a44b6680e4d6bc4f9"
        ),
        "WebArena/pipeline_memory.py": (
            "e0bab83fb7d6e4abc3ea01d1b1f545f9c2730c1719c2bda6d73e54023a80bb96"
        ),
        "WebArena/induce_memory.py": (
            "97d7da3fe5bd3e37d05e4aa07c050b1154334951cc2cad20619774ae77e0912c"
        ),
        "WebArena/pipeline_scaling.py": (
            "6df79d99f42b9900a83ed10bea2225183e3d894e30bd293f62ffce8ee2ef4494"
        ),
        "WebArena/induce_scaling.py": (
            "bb7399af96a674fc36de61665b91d87748aeef7f972df8757ce42869d12f30be"
        ),
        "third_party/src/minisweagent/run/extra/swebench.py": (
            "8365112cd2dd2f3dbd74eff611b5d166530c6ddac4b09b674ae384da96531951"
        ),
        "third_party/src/minisweagent/memory/memory_management.py": (
            "fe71285a878920d501013ab86b58ef12c9c08071ee0e690061774d5ff5588955"
        ),
    },
}

EXPECTED_FINDINGS = {
    "import_time_cloud_clients": True,
    "mutable_unrevisioned_embedding_models": True,
    "webarena_query_cache_mutates_during_evaluation": True,
    "webarena_bank_mutates_after_each_evaluation_task": True,
    "swebench_query_cache_mutates_during_evaluation": True,
    "swebench_bank_mutates_after_each_evaluation_task": True,
    "swebench_shared_bank_and_cache_used_by_worker_threads": True,
    "trajectory_pickle_is_trusted_input": True,
    "trajectory_extraction_swallows_exceptions": True,
    "induction_temperature_is_unseeded": True,
    "scaling_reads_only_final_trial_directory": True,
    "scaling_reward_label_is_inverted": True,
}


class ReasoningBankSourceExperimentError(ValueError):
    """Raised when the registered ReasoningBank contract drifts."""


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ReasoningBankSourceExperimentError(
            f"cannot load ReasoningBank source experiment: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise ReasoningBankSourceExperimentError(
            "ReasoningBank source experiment must be a mapping"
        )
    if (
        payload.get("schema_version") != 1
        or payload.get("name") != "stage3-reasoningbank-source-admission-doctor"
        or payload.get("status") != "registered-source-admission-doctor"
        or payload.get("scientific_result") is not False
        or payload.get("protocol") != "procedural-bank-source-admission-v1"
    ):
        raise ReasoningBankSourceExperimentError("ReasoningBank identity drifted")
    if payload.get("source") != EXPECTED_SOURCE:
        raise ReasoningBankSourceExperimentError("ReasoningBank source contract drifted")
    if payload.get("release_findings") != EXPECTED_FINDINGS:
        raise ReasoningBankSourceExperimentError("ReasoningBank findings drifted")
    scope = payload.get("mechanism_scope")
    if (
        not isinstance(scope, dict)
        or scope.get("residency") != "immutable-inactive-bank-after-training"
        or scope.get("lifecycle_provider_claim") != "forbidden"
        or scope.get("active_inactive_paging_claim") != "forbidden"
        or scope.get("causal_credit_claim") != "forbidden"
    ):
        raise ReasoningBankSourceExperimentError("ReasoningBank scope drifted")
    patch_arm = payload.get("required_patch_arm")
    if (
        not isinstance(patch_arm, dict)
        or patch_arm.get("freeze_bank_before_dev_and_test") is not True
        or patch_arm.get("freeze_retrieval_index_before_dev_and_test") is not True
        or patch_arm.get("disjoint_workflow_families") != ["train", "dev", "test"]
        or patch_arm.get("offline_pinned_embedder") is not True
        or patch_arm.get("no_import_time_provider_client") is not True
        or patch_arm.get("no_pickle_input") is not True
        or patch_arm.get("atomic_idempotent_artifacts") is not True
        or patch_arm.get("matched_controls")
        != [
            "no-memory",
            "raw-success-trajectory",
            "raw-failure-trajectory",
            "success-only-procedural-items",
            "failure-only-procedural-items",
            "shuffled-procedural-items",
            "reasoningbank-success-and-failure",
        ]
    ):
        raise ReasoningBankSourceExperimentError("ReasoningBank patch arm drifted")
    if payload.get("execution") != {
        "source_checkout_only": True,
        "runtime_import_forbidden": True,
        "network": "none",
        "api_calls": 0,
        "gpus": 0,
        "max_gpu_hours": 0,
        "cpu_time_limit_minutes": 2,
        "sudo": "forbidden",
    }:
        raise ReasoningBankSourceExperimentError("ReasoningBank execution drifted")
    if payload.get("admission") != {
        "status": "BLOCKED_MUTABLE_EVALUATION_AND_UNPINNED_RETRIEVAL",
        "h100_admission": "forbidden-for-this-release-driver",
        "next_gate": "reviewed-frozen-bank-patch-arm-and-contained-cpu-retrieval-doctor",
        "publication_ready": False,
    }:
        raise ReasoningBankSourceExperimentError("ReasoningBank admission drifted")
    return payload


def main() -> int:
    validate_experiment_contract()
    print("ReasoningBank source-admission contract PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
