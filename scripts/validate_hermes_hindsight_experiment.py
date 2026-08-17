#!/usr/bin/env python3
"""Validate the frozen Hermes/Hindsight native lifecycle falsifier."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments/memory/stage4-hermes-hindsight-lifecycle-doctor.yaml"
)
EXPECTED_STATUS = "BLOCKED_NATIVE_PHYSICAL_PURGE_RESIDUE"
HINDSIGHT_REVISION = "5781d28d8fcc717a15818330b12250b311957000"
HERMES_REVISION = "a90d5369f76c87c98547d2e283aa26d5cfabf322"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
IMAGE_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
EXPECTED_IMAGES = {
    "hindsight_backend": "sha256:91ddf1da2ac339c4b44f2a837c1536965a3cf41f2fe7b332416b65e29b4b424e",
    "postgres_pgvector": "sha256:78bf48b801e792f99e3ac62b5036fd3876e9be48afda16c1e331af1c75ceb2ff",
    "model_stub": "sha256:6136cd68a7bed538b224756278fb15344e79e2c19b9640d9b942e41170ade440",
    "hermes_adapter": "sha256:0ae493490c0539a08343eec995865fdb0651562896f58cfd8fc0ae720b6d9c06",
}
EXPECTED_CONTROL_HASHES = {
    "backend_dockerfile_sha256": (
        "f367f49d3b75e84b7ab0e4f25ebcaf773f4ff0221e3c0d133e2acca7b6ee1290"
    ),
    "adapter_dockerfile_sha256": (
        "b771259bb8d8b18c1722ce1ea352cd5c8565908b9dbd3801411257d2efc4ba02"
    ),
    "adapter_doctor_sha256": (
        "37ca1e3282fee036a78f502be022fe1d401b8302ad2f84856137af033118b093"
    ),
    "model_stub_sha256": (
        "6952793d45d1891b7c1739a5d53a8779c126f32032405dab8b7af4ff8a1702ab"
    ),
    "doctor_sha256": (
        "36392411d6d1bb9151631b35b66215e3784f37a9ae1135781d351b22b8ec726f"
    ),
}
POSTGRES_REPO_DIGEST = (
    "pgvector/pgvector@sha256:"
    "78bf48b801e792f99e3ac62b5036fd3876e9be48afda16c1e331af1c75ceb2ff"
)
EXPECTED_OPERATIONS = [
    "tenant-a-tool-retain",
    "tenant-a-prefetch",
    "tenant-b-cannot-see-a",
    "tenant-b-sync-turn-retain",
    "tenant-b-search-own",
    "tenant-a-cannot-see-b",
    "tenant-a-full-restart-search",
    "tenant-b-full-restart-search",
    "tenant-a-admin-delete",
    "tenant-b-admin-delete",
    "tenant-a-delete-survives-full-restart",
    "tenant-b-delete-survives-full-restart",
]


class HindsightExperimentError(ValueError):
    """Raised when the registered Hindsight contract drifts."""


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise HindsightExperimentError("Hindsight experiment must be schema_version 1")
    if payload.get("name") != "stage4-hermes-hindsight-lifecycle-doctor":
        raise HindsightExperimentError("Hindsight experiment name drifted")

    sources = payload.get("sources")
    if not isinstance(sources, dict) or set(sources) != {"hindsight", "hermes"}:
        raise HindsightExperimentError("Hindsight source roster drifted")
    if (
        sources["hindsight"].get("revision") != HINDSIGHT_REVISION
        or sources["hermes"].get("revision") != HERMES_REVISION
    ):
        raise HindsightExperimentError("Hindsight source revisions drifted")
    for source_id, fields in {
        "hindsight": (
            "git_archive_tar_sha256",
            "license_sha256",
            "root_pyproject_sha256",
            "uv_lock_sha256",
            "api_pyproject_sha256",
            "client_pyproject_sha256",
        ),
        "hermes": (
            "git_archive_tar_sha256",
            "license_sha256",
            "provider_sha256",
            "plugin_manifest_sha256",
            "lazy_dependencies_sha256",
        ),
    }.items():
        for field in fields:
            value = sources[source_id].get(field)
            if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
                raise HindsightExperimentError(
                    f"Hindsight source {source_id}.{field} is not SHA-256"
                )

    runtime = payload.get("runtime")
    images = runtime.get("images") if isinstance(runtime, dict) else None
    if (
        not isinstance(runtime, dict)
        or runtime.get("platform") != "linux/arm64"
        or runtime.get("network") != "internal-only"
        or runtime.get("external_api_access") is not False
        or runtime.get("rootfs_read_only") is not True
        or runtime.get("cap_drop_all") is not True
        or runtime.get("no_new_privileges") is not True
        or runtime.get("gpu_count") != 0
        or runtime.get("database_mode") != "external-postgresql-pgvector"
        or runtime.get("database_data_checksums") is not True
        or runtime.get("stable_worker_id")
        != "cotcodec-hermes-hindsight-doctor"
        or not isinstance(images, dict)
        or images != EXPECTED_IMAGES
        or any(not IMAGE_RE.fullmatch(value) for value in images.values())
    ):
        raise HindsightExperimentError("Hindsight containment contract drifted")
    controls = runtime.get("controls")
    if (
        not isinstance(controls, dict)
        or controls.get("embedding")
        != "deterministic-16-dimensional-token-hash"
        or controls.get("postgres_repo_digest")
        != POSTGRES_REPO_DIGEST
        or any(
            controls.get(field) != value
            for field, value in EXPECTED_CONTROL_HASHES.items()
        )
    ):
        raise HindsightExperimentError("Hindsight runtime control hashes drifted")

    contract = payload.get("contract")
    if (
        not isinstance(contract, dict)
        or contract.get("provider_path") != "exact-hermes-hindsight-provider"
        or contract.get("hermes_client_version") != "0.6.1"
        or contract.get("native_service_version") != "0.9.0"
        or contract.get("tenant_count") != 2
        or contract.get("full_stack_restart_count") != 2
        or contract.get("operation_sequence") != EXPECTED_OPERATIONS
        or contract.get("require_prompt_integration_active") is not True
        or contract.get("require_auto_prefetch") is not True
        or contract.get("require_session_end_auto_retain") is not True
        or contract.get("require_restart_persistence") is not True
        or contract.get("require_tenant_isolation") is not True
        or contract.get("require_logical_delete_survives_restart") is not True
        or contract.get("require_hermes_purge_tool") is not False
        or contract.get("scan_all_retained_files_for_plaintext") is not True
        or contract.get("model_calls") != 0
        or contract.get("external_network_calls") != 0
    ):
        raise HindsightExperimentError("Hindsight lifecycle contract drifted")

    if payload.get("expected_falsification") != {
        "status": EXPECTED_STATUS,
        "restart_persistence_supported": True,
        "tenant_isolation_supported": True,
        "logical_delete_survives_restart": True,
        "hermes_purge_tool_exposed": False,
        "physical_zero_plaintext_residue": False,
    }:
        raise HindsightExperimentError("Hindsight falsification contract drifted")
    admission = payload.get("admission")
    claims = payload.get("claims")
    if (
        not isinstance(admission, dict)
        or admission.get("memory_quality_h100") != "forbidden-for-this-revision"
        or not isinstance(claims, dict)
        or claims.get("scientific_result") is not False
        or claims.get("publication_ready") is not False
    ):
        raise HindsightExperimentError("Hindsight claim boundary drifted")
    payload["experiment_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return payload


def main() -> int:
    payload = validate_experiment_contract()
    print(f"Hermes Hindsight experiment PASS: {payload['experiment_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
