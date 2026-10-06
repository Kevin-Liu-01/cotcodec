#!/usr/bin/env python3
"""Validate the preregistered exact-source Mnemo Cortex lifecycle doctor."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments/memory/stage3-mnemo-cortex-native-lifecycle-doctor.yaml"
)
EXPECTED_STATUS = (
    "MNEMO_CORTEX_ADMISSION_KILLED_NO_GIT_PARTIAL_WRITES_"
    "NO_NATIVE_PURGE_AND_UNPINNED_DEPS"
)
REVISION = "8a0cff9492f010f73d722688924b09938b2dd682"
TREE = "5a87d92d70052717a928c3c109b138da4d8af723"
ARCHIVE_SHA256 = "6b6e7709a85f9f949f2a7820ee4c2a7e60112671297fa5229919a266f014c113"
BASE_IMAGE = (
    "docker.io/library/python:3.12.11-slim-bookworm@sha256:"
    "519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7"
)


class MnemoCortexLifecycleExperimentError(ValueError):
    """Raised when the registered Mnemo Cortex contract drifts."""


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise MnemoCortexLifecycleExperimentError(
            f"Mnemo Cortex lifecycle {label} drifted"
        )


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    """Load and fail closed on every decision-bearing contract field."""
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise MnemoCortexLifecycleExperimentError(
            f"cannot load Mnemo Cortex lifecycle experiment: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise MnemoCortexLifecycleExperimentError(
            "Mnemo Cortex lifecycle contract must be a mapping"
        )

    _equal(
        {key: payload.get(key) for key in (
            "schema_version", "name", "status", "scientific_result", "publication_ready"
        )},
        {
            "schema_version": 1,
            "name": "stage3-mnemo-cortex-native-lifecycle-doctor",
            "status": "registered-cpu-falsification",
            "scientific_result": False,
            "publication_ready": False,
        },
        "identity",
    )

    source = payload.get("source")
    if not isinstance(source, dict):
        raise MnemoCortexLifecycleExperimentError("Mnemo Cortex source is missing")
    _equal(
        {key: source.get(key) for key in (
            "source_id", "repository", "revision", "tree", "license",
            "license_sha256", "pyproject_sha256", "upstream_dockerfile_sha256",
            "git_archive_tar_sha256", "git_archive_tar_bytes",
        )},
        {
            "source_id": "mnemo-cortex",
            "repository": "https://github.com/GuyMannDude/mnemo-cortex",
            "revision": REVISION,
            "tree": TREE,
            "license": "MIT",
            "license_sha256": "df032f3c7f49dd0beadea14663257ba3714450a06f6314d6274bc5afb2309233",
            "pyproject_sha256": "b3fed8d9348ca5612a79cb6d2ea552563941651f55cc21440847a038a8df192e",
            "upstream_dockerfile_sha256": (
                "f565b1ed62e47b0124786f58f8ff7c9e73e7d47129f3fd0c83bcc16b256087d7"
            ),
            "git_archive_tar_sha256": ARCHIVE_SHA256,
            "git_archive_tar_bytes": 18810880,
        },
        "source identity",
    )
    expected_files = {
        "agentb/classify.py": "f600c7c797f561987a4558de8161cff9b4b6bbe12554b6a6e6a5a298c71e57d4",
        "agentb/analyst.py": "eb9d355234931eedbdb7f0a909ecb12d813e082c27b8b319a4538333fbb5b6fd",
        "agentb/server.py": "62cc55798590f2229a004f927d477b91e1e9c44974260a3892491ee5f822e8ca",
        "agentb/config.py": "c75326bb1c8e1fc4b9c8fdf719297b21b67578dd44238ef47c0492771a109711",
        "agentb/sessions.py": "72bbd9ef837a5880eec28c938f485718e6e3a44b8909927d257cf9651bb8d5cc",
        "passport/api.py": "c3b934065baaa08b854183b1176dfb4e740a20daa93419b34da3841adb9ec73e",
        "passport/promotion.py": "3540b97448f5fd7ddf139ec1b1ca66b318b1ed9894df65542f9b505ed49b52d4",
        "passport/override.py": "7928b9109374ab203ae1d0a3a05bc22a2336a4b49897b46499f342e5a0e2a4f5",
        "passport/storage.py": "1a19fab2faba8d298519344febb4821e5f43b43d601a510d11d1d22170457b9a",
        "mnemo-dream.py": "5f94151c917a7de0b6ca9d11aad921df85b1f80e622c618ebacb282edb426b9f",
    }
    _equal(source.get("exact_source_files"), expected_files, "source files")

    _equal(
        payload.get("runtime"),
        {
            "containment": "docker-under-slurm-network-none",
            "provider_secrets": "forbidden",
            "sudo": "forbidden",
            "gpu_count": 0,
            "base_image": BASE_IMAGE,
            "python_version": "3.12.11",
            "clean_state_repeats": 2,
            "fresh_process_restarts_per_repeat": 1,
            "dependency_install": "exact-pyproject-lower-bounds-no-transitive-lock",
            "official_container_git_install": "absent",
        },
        "runtime",
    )

    intervention = payload.get("intervention")
    expected_flags = {
        "deterministic_reasoning_double",
        "deterministic_embedding_double",
        "test_smart_note_classification",
        "test_default_session_log_hiding",
        "test_explicit_session_log_drilldown",
        "test_analyst_derived_from_lineage",
        "test_cross_agent_map_reduce",
        "test_fresh_process_restart",
        "test_native_primary_memory_purge_surface",
        "test_passport_missing_git_partial_write",
        "test_passport_failed_retry_idempotency",
        "test_current_file_plaintext_residue",
    }
    if (
        not isinstance(intervention, dict)
        or intervention.get("public_api") != [
            "POST /writeback", "POST /context", "POST /passport/observe",
            "POST /passport/pending",
        ]
        or intervention.get("executable_mechanism_seams") != [
            "app.state.maintenance_cycle", "mnemo-dream.synthesize"
        ]
        or intervention.get("external_model_calls") != 0
        or intervention.get("provider_calls") != 0
        or any(intervention.get(flag) is not True for flag in expected_flags)
    ):
        raise MnemoCortexLifecycleExperimentError(
            "Mnemo Cortex lifecycle intervention drifted"
        )

    expected = payload.get("expected_falsification")
    if (
        not isinstance(expected, dict)
        or expected.get("status") != EXPECTED_STATUS
        or any(value is not True for key, value in expected.items() if key != "status")
        or len(expected) != 15
    ):
        raise MnemoCortexLifecycleExperimentError(
            "Mnemo Cortex expected falsification drifted"
        )

    _equal(
        payload.get("execution"),
        {
            "repetitions": 2,
            "phases_per_repeat": 2,
            "external_api_calls": 0,
            "llm_calls": 0,
            "simulated_reasoning_stage_calls": 5,
            "gpus": 0,
            "max_gpu_hours": 0,
            "wall_clock_limit_minutes": 30,
            "slurm_cpus": 4,
            "slurm_memory_gb": 16,
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
        raise MnemoCortexLifecycleExperimentError(
            "Mnemo Cortex lifecycle admission drifted"
        )
    return payload


def main() -> int:
    validate_experiment_contract()
    print("Mnemo Cortex native lifecycle contract PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
