#!/usr/bin/env python3
"""Validate the preregistered exact-source MemGPT/Letta lifecycle doctor."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT
    / "experiments/memory/stage3-memgpt-letta-native-lifecycle-doctor.yaml"
)
EXPECTED_STATUS = (
    "MEMGPT_LETTA_ADMISSION_KILLED_PARTIAL_CORE_UPDATE_DUPLICATE_ARCHIVE_"
    "RETRY_AGENT_DELETE_ORPHANS_AND_POSTGRES_RESIDUE"
)
REVISION = "ff19ffeafeb54bd2a7dc5d4a552f10191732a235"
TREE = "675c06071568dd48ca9b16b755041937286b7d95"
ARCHIVE_SHA256 = "68858b2315fd6a3f8f499fd5354307c22320d430a7a9b52e475523ec2d43f108"
IMAGE = (
    "docker.io/letta/letta@sha256:"
    "7bdff3a3f876b79db0b347900a392bd6f13eff5c294735eda98be1f8ecf7a7a2"
)


class MemgptLettaLifecycleExperimentError(ValueError):
    """Raised when the registered MemGPT/Letta contract drifts."""


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise MemgptLettaLifecycleExperimentError(
            f"MemGPT/Letta lifecycle {label} drifted"
        )


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    """Load and fail closed on every decision-bearing contract field."""
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise MemgptLettaLifecycleExperimentError(
            f"cannot load MemGPT/Letta lifecycle experiment: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise MemgptLettaLifecycleExperimentError(
            "MemGPT/Letta lifecycle contract must be a mapping"
        )

    _equal(
        {
            key: payload.get(key)
            for key in (
                "schema_version",
                "name",
                "status",
                "scientific_result",
                "publication_ready",
            )
        },
        {
            "schema_version": 1,
            "name": "stage3-memgpt-letta-native-lifecycle-doctor",
            "status": "registered-cpu-falsification",
            "scientific_result": False,
            "publication_ready": False,
        },
        "identity",
    )

    source = payload.get("source")
    if not isinstance(source, dict):
        raise MemgptLettaLifecycleExperimentError("MemGPT/Letta source is missing")
    _equal(
        {
            key: source.get(key)
            for key in (
                "source_id",
                "repository",
                "revision",
                "tree",
                "version",
                "license",
                "license_sha256",
                "pyproject_sha256",
                "lock_sha256",
                "upstream_dockerfile_sha256",
                "git_archive_tar_sha256",
                "git_archive_tar_bytes",
                "repository_status_at_revision",
            )
        },
        {
            "source_id": "memgpt-letta",
            "repository": "https://github.com/letta-ai/letta",
            "revision": REVISION,
            "tree": TREE,
            "version": "0.16.8",
            "license": "Apache-2.0",
            "license_sha256": (
                "984c6db99fc6609803108dfc196762118662cd94b82a456dd9217583f18f3612"
            ),
            "pyproject_sha256": (
                "ba86147a334a4900962b260d1912e263e011e8698377327b9f1a8fd943540c3e"
            ),
            "lock_sha256": (
                "7d86dc1075143b24ab8864e6f443cb2220ee3aaefc385ff3919f8ea5b52b9c75"
            ),
            "upstream_dockerfile_sha256": (
                "356e1e834b51e871a98b63a22b87113cf83661a5cb8a16c811f986ac2e1cc5e8"
            ),
            "git_archive_tar_sha256": ARCHIVE_SHA256,
            "git_archive_tar_bytes": 24_176_640,
            "repository_status_at_revision": (
                "deprecated-legacy-v1-server-maintenance-only"
            ),
        },
        "source identity",
    )
    _equal(
        source.get("exact_source_files"),
        {
            "letta/services/block_manager.py": (
                "c6d7fcec90c9108cb80414285f68609cc420f22044c9bd67ebf9300bdec136b3"
            ),
            "letta/services/passage_manager.py": (
                "db8fb6ef28b69a9e516e61bfd14ece8c63ed032f0e8a04fc7c84bd153a534c20"
            ),
            "letta/services/archive_manager.py": (
                "1b344a1af465f20d101d465b9fd4653fc675344cb76b9a086fb61c139a0a2c1a"
            ),
            "letta/services/agent_manager.py": (
                "290f458dee5fb1d14c55aa5530e93726e1d8a9337ff6f5dc5aa1b0e90bafb3e7"
            ),
            "letta/orm/sqlalchemy_base.py": (
                "ea054cc9f87436876261f5d091dc0c1ecd5c89f0670e0af8605cfffd91f8f473"
            ),
            "letta/orm/mixins.py": (
                "9a86724b87bd8171942ca36c3aa42e66b067e79225ac517b310380565ebc02ad"
            ),
            "letta/server/db.py": (
                "dcbf009b1f526e02f0c826ce3f190648e1cd3db5f146e51f5a0736fd5bd5d265"
            ),
            "letta/server/rest_api/routers/v1/archives.py": (
                "239204cc1e1c035f9535cd9915d132d0137c70efceff30833c81155f45a5bb60"
            ),
            "letta/server/rest_api/routers/v1/agents.py": (
                "55c2f9b22578a95728ba9fb1e9d94a2c54cb88dc32b819971a1c3cb5a012b38c"
            ),
            "letta/server/rest_api/routers/v1/organizations.py": (
                "55bd85b48135cbfeba11dfa545a4992859d964c8f1c1b8f2d92e473881bc0054"
            ),
            "letta/server/rest_api/routers/v1/users.py": (
                "4885671ccc68df2a8bdef2b238b4c5c182c8a1a0d7cca881798f83fbdc4f7a9c"
            ),
            "letta/server/rest_api/app.py": (
                "4948a70cd9fd194a7b9ec3ab5aca852f3e3ba87e4c1b7a052e4a4cd2373bdb0b"
            ),
            "letta/constants.py": (
                "ba3bb61167ca2ac01a34bc8b25a535dfd73a851732d4245d5933d4a3566f6ada"
            ),
        },
        "source files",
    )

    context = payload.get("current_runtime_context")
    _equal(
        context,
        {
            "repository": "https://github.com/letta-ai/letta-code",
            "revision": "a575e11753943d9a4e18373a8817eb16a5b76b47",
            "tree": "9bb2cadf097f522bdcbc09fe0268dd6dd82bb410",
            "license": "Apache-2.0",
            "license_sha256": "036e78b9d7dd33ae5b378fdda973b4aad7901c8d8371a0ae40fae1f6659a89d0",
            "package_sha256": "9bd4323b8b055c07fbfdf6755b3454e013abdbadd6049f2bc1209be228f76b00",
            "lock_sha256": "0a8cad33168b97cfd08958d29b853f683eff9a36f42d1709e761990a74adc26e",
            "git_archive_tar_sha256": (
                "d81b210456b049a09d1a98618846273c7f41aadd63e4873fa796ecab20db9bd9"
            ),
            "git_archive_tar_bytes": 50_759_680,
            "role": "provenance-context-only-different-local-memfs-mechanism",
        },
        "current runtime context",
    )

    _equal(
        payload.get("runtime"),
        {
            "containment": "official-image-under-slurm-network-none",
            "provider_secrets": "forbidden",
            "sudo": "forbidden",
            "gpu_count": 0,
            "official_image": IMAGE,
            "image_platform": "linux/amd64",
            "image_version": "0.16.8",
            "exact_image_source_hash_match_required": True,
            "dependency_install": "committed-uv-lock-inside-official-image",
            "storage": "internal-postgresql-bind-mounted-per-repeat",
            "clean_state_repeats": 2,
            "fresh_process_restarts_per_repeat": 1,
        },
        "runtime",
    )

    intervention = payload.get("intervention")
    flags = {
        "deterministic_llm_config_without_generation",
        "test_exact_image_source_match",
        "test_core_block_mutation",
        "test_inactive_archive_write_and_read",
        "test_cross_organization_isolation",
        "test_fresh_process_restart",
        "test_failed_block_rebuild_partial_mutation",
        "test_payload_equivalent_archive_retry",
        "test_agent_delete_owned_memory_retention",
        "test_explicit_logical_memory_purge",
        "test_stopped_postgres_plaintext_residue",
        "measure_http_calls",
        "measure_operation_latency",
        "measure_stopped_state_bytes",
    }
    _equal(
        intervention.get("public_api") if isinstance(intervention, dict) else None,
        [
            "POST /v1/admin/orgs/",
            "POST /v1/admin/users/",
            "POST /v1/agents/",
            "GET /v1/agents/{agent_id}/core-memory/blocks",
            "GET /v1/blocks/{block_id}",
            "PATCH /v1/agents/{agent_id}/core-memory/blocks/{block_label}",
            "POST /v1/agents/{agent_id}/archival-memory",
            "GET /v1/agents/{agent_id}/archival-memory",
            "DELETE /v1/agents/{agent_id}/archival-memory/{memory_id}",
            "DELETE /v1/agents/{agent_id}",
            "DELETE /v1/archives/{archive_id}",
            "DELETE /v1/blocks/{block_id}",
        ],
        "public API",
    )
    if (
        not isinstance(intervention, dict)
        or intervention.get("external_model_calls") != 0
        or intervention.get("provider_calls") != 0
        or any(intervention.get(flag) is not True for flag in flags)
    ):
        raise MemgptLettaLifecycleExperimentError(
            "MemGPT/Letta lifecycle intervention drifted"
        )

    expected = payload.get("expected_falsification")
    if (
        not isinstance(expected, dict)
        or expected.get("status") != EXPECTED_STATUS
        or any(value is not True for key, value in expected.items() if key != "status")
        or len(expected) != 15
    ):
        raise MemgptLettaLifecycleExperimentError(
            "MemGPT/Letta expected falsification drifted"
        )

    _equal(
        payload.get("execution"),
        {
            "repetitions": 2,
            "phases_per_repeat": 3,
            "external_api_calls": 0,
            "llm_calls": 0,
            "gpus": 0,
            "max_gpu_hours": 0,
            "wall_clock_limit_minutes": 40,
            "slurm_cpus": 4,
            "slurm_memory_gb": 16,
        },
        "execution",
    )
    admission = payload.get("admission")
    if (
        not isinstance(admission, dict)
        or admission.get("h100_actor")
        != "forbidden-for-this-revision-if-falsified"
        or admission.get("scientific_claim") != "forbidden"
        or admission.get("publication_claim") != "forbidden"
        or not isinstance(admission.get("next_gate"), str)
        or not admission["next_gate"].strip()
        or not isinstance(payload.get("claim_boundary"), str)
        or not payload["claim_boundary"].strip()
    ):
        raise MemgptLettaLifecycleExperimentError(
            "MemGPT/Letta lifecycle admission drifted"
        )
    return payload


def main() -> int:
    validate_experiment_contract()
    print("MemGPT/Letta native lifecycle contract PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
