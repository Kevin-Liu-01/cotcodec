#!/usr/bin/env python3
"""Validate the frozen Hermes/OpenViking native lifecycle falsifier."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT
    / "experiments/memory/stage4-hermes-openviking-lifecycle-doctor.yaml"
)
EXPECTED_STATUS = "BLOCKED_NATIVE_PHYSICAL_PURGE_RESIDUE"
OPENVIKING_REVISION = "eeff5a497360aa4481cf32e18a0d9376f4412f4c"
HERMES_REVISION = "a90d5369f76c87c98547d2e283aa26d5cfabf322"
EXPECTED_OPERATIONS = [
    "tenant-a-write",
    "tenant-a-restart-search",
    "tenant-b-cannot-see-a",
    "tenant-b-write",
    "tenant-a-cannot-see-b",
    "tenant-a-restart-read",
    "tenant-a-forget",
    "tenant-b-forget",
    "tenant-a-delete-survives-restart",
    "tenant-b-delete-survives-restart",
]
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
IMAGE_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
EXPECTED_IMAGES = {
    "openviking": "sha256:4b917e25cce8d71a35f6a50f67ff235f0805c179f786c72b71601f26050bca51",
    "model_stub": "sha256:6136cd68a7bed538b224756278fb15344e79e2c19b9640d9b942e41170ade440",
    "hermes_adapter": "sha256:ac1f3e164a6751ee42f225456880231b392ac383b071b71c22c989ea5292274d",
}
EXPECTED_CONTROL_HASHES = {
    "openviking_config_sha256": (
        "afa7f0e0f089801b4a78c6adc80a229002bfb5a51da1ba05be685cc254eab741"
    ),
    "model_stub_sha256": (
        "6952793d45d1891b7c1739a5d53a8779c126f32032405dab8b7af4ff8a1702ab"
    ),
    "adapter_doctor_sha256": (
        "a3f1c0d34f2b1355d47de5f6b7e103814d2cdca636de50e509eb5e56f90e36c1"
    ),
    "source_dockerfile_sha256": (
        "4d3bab26fc53b675968e79f96e75c9a639c5f77eada3d327490df69bf6665c64"
    ),
    "stub_dockerfile_sha256": (
        "4a933ff98460c36ed89f718d4cf046ca5ec0da8831ca4b5bcddbf896a79c4366"
    ),
    "adapter_dockerfile_sha256": (
        "d9832dd0e617ba32efc97be96650bc24e42420f4df8d80f0fce1e027ac409f3a"
    ),
    "doctor_sha256": (
        "1a1508e69bf1dd9b999938a2d4ccfdc48ef79d476f9773a1b701db5dd3bd252a"
    ),
}


class OpenVikingExperimentError(ValueError):
    """Raised when the registered OpenViking contract drifts."""


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise OpenVikingExperimentError("OpenViking experiment must be schema_version 1")
    if payload.get("name") != "stage4-hermes-openviking-lifecycle-doctor":
        raise OpenVikingExperimentError("OpenViking experiment name drifted")
    sources = payload.get("sources")
    if not isinstance(sources, dict) or set(sources) != {"openviking", "hermes"}:
        raise OpenVikingExperimentError("OpenViking source roster drifted")
    if (
        sources["openviking"].get("revision") != OPENVIKING_REVISION
        or sources["hermes"].get("revision") != HERMES_REVISION
    ):
        raise OpenVikingExperimentError("OpenViking source revisions drifted")
    for source_id, fields in {
        "openviking": (
            "git_archive_tar_sha256",
            "license_sha256",
            "pyproject_sha256",
            "uv_lock_sha256",
        ),
        "hermes": ("git_archive_tar_sha256", "provider_sha256"),
    }.items():
        for field in fields:
            value = sources[source_id].get(field)
            if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
                raise OpenVikingExperimentError(
                    f"OpenViking source {source_id}.{field} is not SHA-256"
                )
    runtime = payload.get("runtime")
    images = runtime.get("images") if isinstance(runtime, dict) else None
    if (
        not isinstance(runtime, dict)
        or runtime.get("network") != "internal-only"
        or runtime.get("external_api_access") is not False
        or runtime.get("rootfs_read_only") is not True
        or runtime.get("cap_drop_all") is not True
        or runtime.get("no_new_privileges") is not True
        or runtime.get("gpu_count") != 0
        or not isinstance(images, dict)
        or images != EXPECTED_IMAGES
        or any(not IMAGE_RE.fullmatch(value) for value in images.values())
    ):
        raise OpenVikingExperimentError("OpenViking containment contract drifted")
    controls = runtime.get("controls")
    if not isinstance(controls, dict):
        raise OpenVikingExperimentError("OpenViking control receipts are missing")
    if any(controls.get(field) != value for field, value in EXPECTED_CONTROL_HASHES.items()):
        raise OpenVikingExperimentError("OpenViking runtime control hashes drifted")
    contract = payload.get("contract")
    if (
        not isinstance(contract, dict)
        or contract.get("provider_path") != "exact-hermes-openviking-provider"
        or contract.get("tenant_count") != 2
        or contract.get("restart_count") != 2
        or contract.get("operation_sequence") != EXPECTED_OPERATIONS
        or contract.get("require_prompt_integration_active") is not True
        or contract.get("require_restart_persistence") is not True
        or contract.get("require_tenant_isolation") is not True
        or contract.get("require_logical_delete_survives_restart") is not True
        or contract.get("scan_all_retained_files_for_plaintext") is not True
        or contract.get("model_calls") != 0
        or contract.get("external_network_calls") != 0
    ):
        raise OpenVikingExperimentError("OpenViking lifecycle contract drifted")
    expected = payload.get("expected_falsification")
    if expected != {
        "status": EXPECTED_STATUS,
        "restart_persistence_supported": True,
        "tenant_isolation_supported": True,
        "logical_delete_survives_restart": True,
        "physical_zero_plaintext_residue": False,
    }:
        raise OpenVikingExperimentError("OpenViking falsification contract drifted")
    admission = payload.get("admission")
    claims = payload.get("claims")
    if (
        not isinstance(admission, dict)
        or admission.get("memory_quality_h100") != "forbidden-for-this-revision"
        or not isinstance(claims, dict)
        or claims.get("scientific_result") is not False
        or claims.get("publication_ready") is not False
    ):
        raise OpenVikingExperimentError("OpenViking claim boundary drifted")
    payload["experiment_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return payload


def main() -> int:
    payload = validate_experiment_contract()
    print(f"Hermes OpenViking experiment PASS: {payload['experiment_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
