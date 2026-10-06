#!/usr/bin/env python3
"""Fail-closed validator for the pinned Mnemon active-space admission cell."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT
    / "experiments/memory/stage3-mnemon-active-space-admission-doctor.yaml"
)
EXPECTED_STATUS = "ADMITTED_STATIC_ACTIVE_SPACE_CONTROL_WITH_SOFT_DELETE_BOUNDARY"
EXPECTED_SOURCES = {
    "mnemon": {
        "source_id": "mnemon",
        "repository": "https://github.com/mnemon-dev/mnemon",
        "revision": "88d2981edeb18a5ebe048af472f6f96527615454",
        "tree": "056fd6d91cf391aaf7667990fdfcef784c670fc1",
        "git_archive_tar_sha256": (
            "a7dba5eea43bc727b0360ba598312067eb2e599525eded3f929fb942ebb781c6"
        ),
        "license": "Apache-2.0",
        "license_sha256": (
            "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4"
        ),
        "go_mod_sha256": (
            "e51be8227e2f6c1ad566c802d8b5fb1b473cbfb2cb80d89cc59f16be4092d47b"
        ),
        "go_sum_sha256": (
            "5b7fbc2805e1e04a5f86287027c0b0bfffc9e5e06805143253a17a944808db16"
        ),
    },
    "dsh_mnemon": {
        "source_id": "dsh-mnemon",
        "repository": "https://github.com/omdsh-dev/dsh-mnemon",
        "revision": "1889c68400e52a391ee9a6eedf15bf44bc39dd06",
        "tree": "87024a203721069a5dbb01b013dcca9475df3328",
        "git_archive_tar_sha256": (
            "6d168ff938b4fcf5bac27e4a7b753f18b987cefb2ce45cdb7795cc7231cc5027"
        ),
        "license": "MIT",
        "license_sha256": (
            "0bc72d9f737802b30a7e43d1b59912e81698e75948759ba07c276732aba0c7a2"
        ),
        "package_json_sha256": (
            "7c65168075572f0181694cd96d9116013773346926e77a92f8517bb902ba16e0"
        ),
        "pnpm_lock_sha256": (
            "fe13b83ab54345dfa8e7b95726a533310112458920a334eb1099458390aa0daf"
        ),
    },
}


class MnemonExperimentError(ValueError):
    """Raised when the registered Mnemon admission contract drifts."""


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise MnemonExperimentError(f"cannot load Mnemon experiment: {exc}") from exc
    if not isinstance(payload, dict):
        raise MnemonExperimentError("Mnemon experiment must be a mapping")
    if (
        payload.get("schema_version") != 1
        or payload.get("name") != "stage3-mnemon-active-space-admission-doctor"
        or payload.get("status") != "registered-cpu-admission"
        or payload.get("scientific_result") is not False
        or payload.get("publication_ready") is not False
    ):
        raise MnemonExperimentError("Mnemon experiment identity drifted")
    if payload.get("sources") != EXPECTED_SOURCES:
        raise MnemonExperimentError("Mnemon source contract drifted")

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
        "go_base_image": (
            "golang@sha256:ab1d1823abb55a9504d2e3e003b75b36dbeb1cbcc4c92593d85a84ee46becc6c"
        ),
        "node_base_image": (
            "node@sha256:0711b541c1c33a8a530ac4f0d391baa9a15b3d804695b1b24a47daa5fb60e74d"
        ),
        "go_dependency_lock": "go.sum",
        "node_dependency_lock": "pnpm-lock.yaml",
    }
    if payload.get("runtime") != expected_runtime:
        raise MnemonExperimentError("Mnemon runtime contract drifted")

    intervention = payload.get("intervention")
    required = {
        "real_mnemon_cli",
        "real_dsh_mnemon_service",
        "create_two_named_stores",
        "active_set_recall_probe",
        "inactive_explicit_read_probe",
        "targeted_write_activation_probe",
        "fresh_service_restart",
        "soft_forget_residue_probe",
        "whole_space_delete_probe",
    }
    if not isinstance(intervention, dict) or any(
        intervention.get(field) is not True for field in required
    ):
        raise MnemonExperimentError("Mnemon intervention contract drifted")
    if any(
        intervention.get(field) != 0
        for field in ("model_calls", "embedding_provider_calls", "external_api_calls")
    ):
        raise MnemonExperimentError("Mnemon admission must remain zero-model")

    gates = payload.get("admission_gates")
    if (
        not isinstance(gates, dict)
        or gates.get("expected_status") != EXPECTED_STATUS
        or gates.get("require_two_clean_states") is not True
        or gates.get("require_distinct_native_databases") is not True
        or gates.get("require_inactive_recall_exclusion") is not True
        or gates.get("require_restart_persistence") is not True
        or gates.get("require_soft_delete_boundary") is not True
        or gates.get("require_whole_space_delete") is not True
        or gates.get("learned_bidirectional_paging_claim") != "forbidden"
        or gates.get("physical_item_erasure_claim") != "forbidden"
        or gates.get("access_control_claim") != "forbidden"
    ):
        raise MnemonExperimentError("Mnemon admission gates drifted")
    admission = payload.get("admission")
    if (
        not isinstance(admission, dict)
        or admission.get("h100_actor")
        != "bounded-static-selection-cell-after-sealed-pass"
        or admission.get("scientific_claim") != "forbidden"
        or admission.get("publication_claim") != "forbidden"
    ):
        raise MnemonExperimentError("Mnemon admission boundary drifted")
    return payload


def main() -> int:
    validate_experiment_contract()
    print("Mnemon active-space admission contract PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
