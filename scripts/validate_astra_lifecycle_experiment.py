#!/usr/bin/env python3
"""Fail-closed validator for ASTRA's native H100 lifecycle doctor."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments" / "memory" / "stage3-astra-native-lifecycle-doctor.yaml"
)
EXPECTED_STATUS = "BLOCKED_NATIVE_PURGE_IDEMPOTENCY_AND_PINNED_CAP"
EXPECTED_SOURCE = {
    "source_id": "astra-working-set",
    "repository": "https://github.com/cyh7789/astra",
    "revision": "644f9d4e65f4e725996025834c91531592ab6166",
    "tree": "43592dc01aa730efb263d24255b094e1f4dc24f3",
    "git_archive_tar_sha256": (
        "f283ca328a080bd6c8c7fac723d490f3d73d15a71f0b7290090bd371957f3d48"
    ),
    "license": "MIT",
    "license_sha256": (
        "f109128ffcc7d51c9f9ee414f04b7b2c6a633808b4d565138ca43e0c77dbd86a"
    ),
    "package_lock_sha256": (
        "44ffc76a024117bd76488a4878e8b372c9aab9abe1abfd9489bf17135218c2b5"
    ),
    "package_json_sha256": (
        "a45d6da6de09c5c96443f4c7ff129aed9bc99ce2c3ccc76fb56bed33cfc53a9d"
    ),
}
EXPECTED_RUNTIME = {
    "containment": "docker-under-slurm",
    "platform": "linux/amd64",
    "app_base_image": (
        "node:22.21.1-bookworm-slim@sha256:"
        "25b3eb23a00590b7499f2a2ce939322727fcce1b15fdd69754fcd09536a3ae2c"
    ),
    "app_image_acquisition": "preloaded-docker-save",
    "app_image_id": (
        "sha256:556c340f700017b8ec937ebb286f4ed1b9c4dcb652252dfd44d6eae677d04970"
    ),
    "app_image_archive_sha256": (
        "eac838215d1cdb61d1734e8bd4641863b9aeec2892cb3043824c8758951845da"
    ),
    "database_image": (
        "cockroachdb/cockroach:v26.2.3@sha256:"
        "1073844226a6291b8a44fcb9cab5cb02035bb8fea3266dcc5dd021c0b34484a0"
    ),
    "database_child_manifest": (
        "sha256:fdbcdb6eb621e0d6f17e4b8591b7acae5cad6355b41965358813e78c1b67419c"
    ),
    "acquisition_network": (
        "pinned-git-and-cached-database-digest-before-measured-phases"
    ),
    "runtime_network": "shared-container-namespace-loopback-only",
    "read_only_roots": True,
    "cap_drop_all": True,
    "no_new_privileges": True,
    "provider_secrets": "forbidden",
    "sudo": "forbidden",
    "scheduler": "slurm",
    "gpu_sku": "H100",
    "gpu_count": 1,
    "max_gpu_hours": 1,
    "cpus_per_task": 16,
    "memory_gib": 64,
    "wall_clock_minutes": 30,
    "clean_state_repeats": 2,
    "checkpoint_boundary": "completed-clean-repeat",
}


class AstraExperimentError(ValueError):
    """Raised when the registered ASTRA lifecycle contract drifts."""


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise AstraExperimentError(f"cannot load ASTRA experiment: {exc}") from exc
    if not isinstance(payload, dict):
        raise AstraExperimentError("ASTRA experiment must be a mapping")
    if (
        payload.get("schema_version") != 1
        or payload.get("name") != "stage3-astra-native-lifecycle-doctor"
        or payload.get("status") != "registered-h100-lifecycle-falsification"
        or payload.get("scientific_result") is not False
    ):
        raise AstraExperimentError("ASTRA experiment identity drifted")
    if payload.get("source") != EXPECTED_SOURCE:
        raise AstraExperimentError("ASTRA source contract drifted")
    if payload.get("runtime") != EXPECTED_RUNTIME:
        raise AstraExperimentError("ASTRA runtime contract drifted")

    capabilities = payload.get("native_capability_contract")
    if not isinstance(capabilities, dict):
        raise AstraExperimentError("ASTRA native capability contract is missing")
    if set(capabilities.get("falsified_or_absent", [])) != {
        "idempotency-keyed-write",
        "physical-user-purge",
        "hard-cap-when-all-records-pinned",
    }:
        raise AstraExperimentError("ASTRA refused capability set drifted")

    intervention = payload.get("intervention")
    if not isinstance(intervention, dict):
        raise AstraExperimentError("ASTRA intervention is missing")
    if (
        intervention.get("model_calls") != 0
        or intervention.get("external_embedding_calls") != 0
        or intervention.get("active_capacity") != 12
        or intervention.get("active_character_budget") != 1500
    ):
        raise AstraExperimentError("ASTRA intervention contract drifted")

    expected = payload.get("expected_falsification")
    if not isinstance(expected, dict) or expected.get("status") != EXPECTED_STATUS:
        raise AstraExperimentError("ASTRA expected status drifted")
    required_truths = {
        "bounded_unpinned_window",
        "evicted_memory_remains_durable",
        "retrieval_driven_readmission",
        "forced_restart_preserves_acknowledged_state",
        "user_isolation",
        "duplicate_write_creates_distinct_rows",
        "soft_deleted_plaintext_row_remains",
        "session_state_retains_soft_deleted_reference",
        "all_pinned_window_exceeds_capacity",
        "reproduced_in_two_clean_states",
    }
    if any(expected.get(field) is not True for field in required_truths):
        raise AstraExperimentError("ASTRA expected falsification truths drifted")

    admission = payload.get("admission")
    if (
        not isinstance(admission, dict)
        or admission.get("active_inactive_h100_actor")
        != "forbidden-for-this-revision"
    ):
        raise AstraExperimentError("ASTRA H100 actor admission must remain forbidden")
    return payload


def main() -> int:
    validate_experiment_contract()
    print("ASTRA native lifecycle experiment PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
