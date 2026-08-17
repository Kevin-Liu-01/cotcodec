#!/usr/bin/env python3
"""Fail-closed validator for the Supermemory binary lifecycle doctor."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT
    / "experiments"
    / "memory"
    / "stage4-supermemory-local-binary-doctor.yaml"
)
EXPECTED_STATUS = "BLOCKED_ACKNOWLEDGED_WRITES_LOST_ON_SIGKILL"
EXPECTED_BASE_IMAGE = (
    "python@sha256:"
    "7e6269297b5711841583c4d018ca3b151f299fc8e707bd0188c1397f466f377f"
)

EXPECTED_SOURCE = {
    "source_id": "supermemory",
    "repository": "https://github.com/supermemoryai/supermemory",
    "documentation_revision": "82dae50ef458139823b3bfd3ebaaaac90ffd8a7c",
    "documentation_tree": "5c58a2b231ea606683bf7b258d16f0155de31f8c",
    "documentation_archive_tar_sha256": (
        "367af62b9353b89aea57942def25e20acad7a4eae8a2434b3e209a9a1d932667"
    ),
    "license": "MIT",
    "license_sha256": (
        "9ce388a89cce6a2dc109579d044f7f16e1397d8ee6fdb1f3bd3b980d365a07ae"
    ),
    "readme_sha256": (
        "16d7a458a77c8cb5ff8b400eed4328d4e76e672b7b0db144050a86e5e8002617"
    ),
    "configuration_doc_sha256": (
        "a357a6b74160cb048ce70430a84415712294e2b3f020b6e8aee61cc1d5a51b65"
    ),
    "memory_operations_doc_sha256": (
        "cfa4b6b98fdec926af654582d2081603f9c27ec4bbb1aabec24977b83f8fa369"
    ),
    "release_tag": "server-v0.0.3",
    "release_revision": "39ef7e1e5ea01b34d2cdd1801d0d227d445a985d",
    "release_tree": "ca1cf46027d94fe3307bbf063a2ddb635d6b7b88",
    "release_archive_tar_sha256": (
        "f515205dede24fc7f2402ef9d6b34c8002d8fee5d81331ace363f4d73803faf9"
    ),
    "release_tree_path_list_sha256": (
        "85226b9fd290c6965c9e1c71653638afc0b062abb1b546c50834b5b26ca22483"
    ),
    "local_server_source_in_release_tree": False,
    "binary_artifact": {
        "url": (
            "https://github.com/supermemoryai/supermemory/releases/download/"
            "server-v0.0.3/supermemory-server-linux-arm64"
        ),
        "manifest_url": (
            "https://github.com/supermemoryai/supermemory/releases/download/"
            "server-v0.0.3/manifest.json"
        ),
        "manifest_sha256": (
            "2b05221afcc6936a25a97cf2602aedf1a51775f8181348f18c66711a6cc6e0e9"
        ),
        "sha256": (
            "167f595afdb6fba3f6ef12e23b31aa99d177684b188376072d4b46f60d3b4d8e"
        ),
        "bytes": 214_510_741,
        "format": "elf-linux-arm64-dynamically-linked",
    },
}

EXPECTED_MODEL = {
    "repository": "https://huggingface.co/Xenova/bge-base-en-v1.5",
    "revision": "4d6cd88e18e51a5e020c2c305726d76ada9c03cf",
    "dimensions": 768,
    "files": {
        "Xenova/bge-base-en-v1.5/config.json": (
            "d83c21fa7366994560727112ef0a31d8a2ec1c280c2a3e66326fdb877f64c91e"
        ),
        "Xenova/bge-base-en-v1.5/onnx/model_quantized.onnx": (
            "c9729cc84cbd0e9fecc759505d2be65916c9fe05222d7ea26c65fcb3382af38d"
        ),
        "Xenova/bge-base-en-v1.5/tokenizer.json": (
            "d241a60d5e8f04cc1b2b3e9ef7a4921b27bf526d9f6050ab90f9267a1f9e5c66"
        ),
        "Xenova/bge-base-en-v1.5/tokenizer_config.json": (
            "9261e7d79b44c8195c1cada2b453e55b00aeb81e907a6664974b4d7776172ab3"
        ),
    },
}


class SupermemoryExperimentError(ValueError):
    """Raised when the registered binary-only contract drifts."""


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise SupermemoryExperimentError(
            f"cannot load Supermemory experiment: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise SupermemoryExperimentError("Supermemory experiment must be a mapping")
    if (
        payload.get("schema_version") != 1
        or payload.get("name") != "stage4-supermemory-local-binary-doctor"
        or payload.get("status") != "registered-cpu-black-box-conformance"
        or payload.get("scientific_result") is not False
    ):
        raise SupermemoryExperimentError("Supermemory experiment identity drifted")
    if payload.get("source") != EXPECTED_SOURCE:
        raise SupermemoryExperimentError("Supermemory source contract drifted")
    if payload.get("embedding_model") != EXPECTED_MODEL:
        raise SupermemoryExperimentError("Supermemory model contract drifted")

    runtime = payload.get("runtime")
    if not isinstance(runtime, dict):
        raise SupermemoryExperimentError("Supermemory runtime contract is missing")
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
            raise SupermemoryExperimentError(
                f"Supermemory runtime field {field} drifted"
            )
    if runtime.get("local_base_image") != EXPECTED_BASE_IMAGE:
        raise SupermemoryExperimentError("Supermemory base image drifted")

    capabilities = payload.get("native_capability_contract")
    if not isinstance(capabilities, dict):
        raise SupermemoryExperimentError("Supermemory capabilities are missing")
    refused = set(capabilities.get("refused", []))
    if refused != {
        "source-auditable-local-server",
        "tenant-scoped-native-physical-purge",
        "hard-delete-memory",
        "custom-embedding-provider-at-v0.0.3",
    }:
        raise SupermemoryExperimentError("Supermemory capability refusals drifted")

    intervention = payload.get("intervention")
    if (
        not isinstance(intervention, dict)
        or intervention.get("model_calls") != 0
        or intervention.get("provider_calls") != 0
        or intervention.get("crash_injection")
        != "sigkill-after-committed-versioned-update"
    ):
        raise SupermemoryExperimentError("Supermemory intervention drifted")
    expected = payload.get("expected_outcome")
    if not isinstance(expected, dict) or expected.get("status") != EXPECTED_STATUS:
        raise SupermemoryExperimentError("Supermemory outcome contract drifted")
    required_outcomes = {
        "acknowledged_writes_survive_sigkill": False,
        "version_history_survives_sigkill": False,
        "graceful_restart_persists_acknowledged_pair": True,
        "cross_tenant_plaintext_disclosure": False,
        "soft_forget_excludes_normal_search": True,
        "provider_plaintext_at_rest_detected": False,
        "native_tenant_scoped_physical_purge_available": False,
        "reproduced_in_two_clean_states": True,
    }
    for field, value in required_outcomes.items():
        if expected.get(field) is not value:
            raise SupermemoryExperimentError(
                f"Supermemory expected field {field} drifted"
            )
    admission = payload.get("admission")
    if (
        not isinstance(admission, dict)
        or admission.get("memory_lifecycle_h100") != "forbidden-for-this-release"
        or admission.get("publication_reproduction") != "forbidden"
    ):
        raise SupermemoryExperimentError("Supermemory admission contract drifted")
    return payload


def main() -> int:
    validate_experiment_contract()
    print("Supermemory binary lifecycle contract PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
