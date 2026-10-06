#!/usr/bin/env python3
"""Fail-closed validator for the Hippo retention falsification contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT
    / "experiments"
    / "memory"
    / "stage3-hippo-retention-cross-tenant-doctor.yaml"
)


class HippoExperimentError(ValueError):
    """Raised when the registered Hippo falsification contract drifts."""


EXPECTED_SOURCE = {
    "source_id": "hippo-memory",
    "repository": "https://github.com/kitfunso/hippo-memory",
    "revision": "4aeb04c68ff079ff1713c977ac4d2a96757cff44",
    "tree": "88d0613e1e5aaec6d1c401c200d5ad3372af0828",
    "tag": "v1.30.0",
    "git_archive_tar_sha256": (
        "d966a02bf1c811f191e94fa21317a3a2a3a9797ff7f3da93caa114a794845bb8"
    ),
    "license": "MIT",
    "license_sha256": (
        "c3e197e295e989f797bf994a98ee514179c5ea031320af0823b2bb4c8b05a09d"
    ),
    "package_lock_sha256": (
        "8faa74fa7fb588dadc67fe8579c605750f14f1bc2a8060c3c81c1de2225ff200"
    ),
}
EXPECTED_STATUS = "BLOCKED_CROSS_TENANT_CONSOLIDATION_AND_PURGE_RESIDUE_REPRODUCED"


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text())
    except (OSError, yaml.YAMLError) as exc:
        raise HippoExperimentError(f"cannot load Hippo experiment: {exc}") from exc
    if not isinstance(payload, dict):
        raise HippoExperimentError("Hippo experiment must be a mapping")
    if (
        payload.get("schema_version") != 1
        or payload.get("name") != "stage3-hippo-retention-cross-tenant-doctor"
        or payload.get("status") != "registered-cpu-falsification"
        or payload.get("scientific_result") is not False
    ):
        raise HippoExperimentError("Hippo experiment identity drifted")
    if payload.get("source") != EXPECTED_SOURCE:
        raise HippoExperimentError("Hippo source contract drifted")

    runtime = payload.get("runtime")
    if not isinstance(runtime, dict):
        raise HippoExperimentError("Hippo runtime contract is missing")
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
    }
    for field, expected in required_runtime.items():
        if runtime.get(field) != expected:
            raise HippoExperimentError(f"Hippo runtime field {field} drifted")
    image = runtime.get("local_base_image")
    if not isinstance(image, str) or "@sha256:" not in image:
        raise HippoExperimentError("Hippo local image must be digest-pinned")

    capabilities = payload.get("native_capability_contract")
    if not isinstance(capabilities, dict):
        raise HippoExperimentError("Hippo native capability contract is missing")
    refused = set(capabilities.get("refused", []))
    required_refusals = {
        "configurable-active-slots",
        "active-to-archive-transition",
        "archive-to-active-transition",
        "working-memory-flush-to-archive",
        "tenant-scoped-native-purge",
    }
    if refused != required_refusals:
        raise HippoExperimentError("Hippo capability refusals drifted")

    intervention = payload.get("intervention")
    if not isinstance(intervention, dict):
        raise HippoExperimentError("Hippo intervention is missing")
    for field in (
        "fixed_clock",
        "replay_count",
        "auto_trace_capture",
        "embeddings",
        "extraction",
        "physics",
        "memory_value_rescue",
        "model_calls",
    ):
        if field == "fixed_clock":
            expected = True
        elif field in {"replay_count", "model_calls"}:
            expected = 0
        else:
            expected = False
        if intervention.get(field) != expected:
            raise HippoExperimentError(f"Hippo intervention field {field} drifted")

    expected = payload.get("expected_falsification")
    if not isinstance(expected, dict) or expected.get("status") != EXPECTED_STATUS:
        raise HippoExperimentError("Hippo expected falsification status drifted")
    required_truths = {
        "host_wide_sleep_merges_cross_tenant_sources": True,
        "mixed_semantic_owned_by_default_tenant": True,
        "mixed_semantic_retrievable_by_default_tenant": True,
        "mixed_semantic_source_lineage_complete": False,
        "logical_delete_reaches_zero_rows": True,
        "plaintext_canary_residue_in_sqlite": True,
        "reproduced_in_two_clean_states": True,
    }
    for field, value in required_truths.items():
        if expected.get(field) is not value:
            raise HippoExperimentError(f"Hippo falsification field {field} drifted")

    admission = payload.get("admission")
    if (
        not isinstance(admission, dict)
        or admission.get("active_inactive_h100") != "forbidden-for-this-revision"
    ):
        raise HippoExperimentError("Hippo H100 admission must stay forbidden")
    return payload


def main() -> int:
    validate_experiment_contract()
    print("Hippo retention falsification contract PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
