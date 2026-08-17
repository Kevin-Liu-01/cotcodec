#!/usr/bin/env python3
"""Validate the standalone Hermes Observational Memory lifecycle contract."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT
    / "experiments/memory/stage4-hermes-observational-memory-lifecycle-doctor.yaml"
)
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_STATUS = "BLOCKED_NO_PROVIDER_NATIVE_DELETE_OR_ERASURE"
EXPECTED_BASE_IMAGE_TAG = "cotcodec-research:8c51687b-architecture"
EXPECTED_BASE_IMAGE_ID = (
    "sha256:ba360ea13ea50e77e4900cb258c4dc73156060295abd381899f90f9991cedd10"
)
EXPECTED_OPERATIONS = [
    "exact-wheel-and-plugin-install",
    "hermes-standalone-provider-discovery",
    "empty-root-startup-context",
    "tenant-a-explicit-remember",
    "tenant-a-bm25-search",
    "tenant-a-bounded-startup-context",
    "tenant-a-fresh-process-restart-search",
    "tenant-b-cannot-see-tenant-a",
    "hard-budget-writeback-refusal",
    "provider-native-delete-capability-audit",
    "operator-scoped-root-purge",
    "retained-file-plaintext-scan",
]


class HermesObservationalMemoryExperimentError(ValueError):
    """Raised when the registered standalone-provider contract drifts."""


def _mapping(payload: dict[str, Any], field: str) -> dict[str, Any]:
    value = payload.get(field)
    if not isinstance(value, dict):
        raise HermesObservationalMemoryExperimentError(
            f"Hermes Observational Memory field {field!r} must be a mapping"
        )
    return value


def _require_sha(value: Any, pattern: re.Pattern[str], field: str) -> None:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise HermesObservationalMemoryExperimentError(
            f"Hermes Observational Memory {field} is not immutable"
        )


def validate_experiment_contract(
    path: Path = DEFAULT_EXPERIMENT,
) -> dict[str, Any]:
    """Validate and return the exact planned lifecycle contract."""

    if not path.is_file() or path.is_symlink():
        raise HermesObservationalMemoryExperimentError(
            "Hermes Observational Memory experiment must be a regular YAML"
        )
    encoded = path.read_bytes()
    payload = yaml.safe_load(encoded)
    if not isinstance(payload, dict):
        raise HermesObservationalMemoryExperimentError(
            "Hermes Observational Memory experiment must be a mapping"
        )
    expected_header = {
        "schema_version": 1,
        "name": "stage4-hermes-observational-memory-lifecycle-doctor",
        "status": "registered-contained-standalone-provider-doctor",
        "scientific_result": False,
        "protocol": "hermes-standalone-memory-provider-lifecycle-v1",
    }
    if any(payload.get(key) != value for key, value in expected_header.items()):
        raise HermesObservationalMemoryExperimentError(
            "Hermes Observational Memory experiment header drifted"
        )

    sources = _mapping(payload, "sources")
    if set(sources) != {"hermes", "plugin", "core"}:
        raise HermesObservationalMemoryExperimentError(
            "Hermes Observational Memory source roster drifted"
        )
    expected_sources = {
        "hermes": {
            "repository": "https://github.com/NousResearch/hermes-agent",
            "revision": "a90d5369f76c87c98547d2e283aa26d5cfabf322",
            "tree": "963eb136bfb21fd0b296a40529cbb3575c610874",
            "archive_sha256": "2a2934d3c8379816b2e3919f4cf1191f04e93f136da6f2128246d368644a9514",
            "version": "0.20.1",
            "license": "MIT",
        },
        "plugin": {
            "repository": "https://github.com/intertwine/hermes-observational-memory",
            "revision": "90d83c1ff768d80f99f4e3ef4d76269f90e1c808",
            "tree": "5cf00ebd8f4d57673469e2e45f3954ac37d875af",
            "archive_sha256": "33d6bc75ff850fdf9140d225bc6636c3cc22f0c015f897c546ce226b7cc551c4",
            "license": "MIT",
            "license_sha256": "821556e6336796450ab852d375117b48a4887e71d255794fd6318d99982a5ab6",
            "version": "1.5.1",
        },
        "core": {
            "repository": "https://github.com/intertwine/observational-memory",
            "revision": "6bbc16e81ad1258ee1e8ba37c9efcc6ce36a0208",
            "tree": "96f4288c19b78b0bdda8568efa0c5b1435d64552",
            "archive_sha256": "0d103be2c781b0ac546a5fa16cb81c1f877513675b83ca33b06cd7fa4d8312f0",
            "license": "MIT",
            "license_sha256": "26e6e591673d6c33aff449fb7f26623b188b2c3b2c8d78bbb357024d0ed9b738",
            "version": "0.10.0",
            "wheel_sha256": "d743b32823af544468fc666621850931ae77c0225d8c162db43b878cbdb5f4e4",
        },
    }
    if sources != expected_sources:
        raise HermesObservationalMemoryExperimentError(
            "Hermes Observational Memory source contract drifted"
        )
    for source_name, source in sources.items():
        _require_sha(source["revision"], SHA40_RE, f"{source_name}.revision")
        _require_sha(source["tree"], SHA40_RE, f"{source_name}.tree")
        _require_sha(
            source["archive_sha256"], SHA256_RE, f"{source_name}.archive_sha256"
        )
        for field in ("license_sha256", "wheel_sha256"):
            if field in source:
                _require_sha(source[field], SHA256_RE, f"{source_name}.{field}")

    runtime = _mapping(payload, "runtime")
    if runtime != {
        "container_required": True,
        "base_image_tag": EXPECTED_BASE_IMAGE_TAG,
        "base_image_id": EXPECTED_BASE_IMAGE_ID,
        "base_image_role": "exact-cached-discovery-substrate-only",
        "final_image_digest_required_before_execution": True,
        "hermes_runtime_scope": "exact-source-minimal-provider-loader-slice",
        "offline_wheels": {
            "observational_memory": {
                "filename": "observational_memory-0.10.0-py3-none-any.whl",
                "sha256": "d743b32823af544468fc666621850931ae77c0225d8c162db43b878cbdb5f4e4",
            },
            "rank_bm25": {
                "filename": "rank_bm25-0.2.2-py3-none-any.whl",
                "sha256": "7bd4a95571adadfc271746fa146a4bcfd89c0cf731e49c3d1ad863290adbe8ae",
            },
            "numpy": {
                "filename": (
                    "numpy-2.4.3-cp312-cp312-manylinux_2_27_x86_64."
                    "manylinux_2_28_x86_64.whl"
                ),
                "sha256": "e7dd01a46700b1967487141a66ac1a3cf0dd8ebf1f08db37d46389401512ca97",
            },
            "pyyaml": {
                "filename": (
                    "pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64."
                    "manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl"
                ),
                "sha256": "ba1cc08a7ccde2d2ec775841541641e4548226580ab850948cbfda66a1befcdc",
            },
        },
        "acquisition_network": "build-only",
        "measured_network": "none",
        "rootfs_read_only": True,
        "cap_drop_all": True,
        "no_new_privileges": True,
        "sudo": "forbidden",
        "scheduler": "slurm",
        "partition": "research",
        "gpu_sku": "H100",
        "gpu_count": 1,
        "cpus": 16,
        "memory_gb": 64,
        "walltime_minutes": 30,
        "max_gpu_hours": 0.5,
        "container_gpu_passthrough": False,
        "model_calls": 0,
        "model_compute": "h100-only",
        "scheduler_required": True,
    }:
        raise HermesObservationalMemoryExperimentError(
            "Hermes Observational Memory containment contract drifted"
        )

    contract = _mapping(payload, "contract")
    if (
        contract.get("provider_name") != "observational_memory"
        or contract.get("provider_cohort") != "standalone"
        or contract.get("sealed_bundled_roster_unchanged") is not True
        or contract.get("search_backend") != "bm25"
        or contract.get("writeback_mode") != "off"
        or contract.get("cluster_mode") != "disabled"
        or contract.get("memory_root_count") != 2
        or contract.get("fresh_process_restarts") != 2
        or contract.get("operation_sequence") != EXPECTED_OPERATIONS
        or contract.get("require_exact_tool_roster")
        != ["om_context", "om_search", "om_remember"]
        or contract.get("require_startup_section_max_chars") != 4000
        or contract.get("require_note_max_chars") != 600
        or any(
            contract.get(field) is not True
            for field in (
                "require_no_api_credentials",
                "require_zero_external_calls",
                "require_no_silent_search_or_reindex_error",
                "require_full_file_manifest_before_and_after_purge",
            )
        )
    ):
        raise HermesObservationalMemoryExperimentError(
            "Hermes Observational Memory lifecycle contract drifted"
        )

    expected = _mapping(payload, "expected_falsification")
    if expected != {
        "status": EXPECTED_STATUS,
        "explicit_note_restart_persistence": True,
        "separate_memory_root_isolation": True,
        "provider_native_delete_or_forget_tool": False,
        "provider_native_physical_erasure_contract": False,
    }:
        raise HermesObservationalMemoryExperimentError(
            "Hermes Observational Memory falsification contract drifted"
        )
    admission = _mapping(payload, "admission")
    claims = _mapping(payload, "claims")
    if (
        admission.get("provider_contract") != "planned-negative-lifecycle-only"
        or admission.get("h100_actor_admission") != "forbidden-for-this-revision"
        or admission.get("unblock_requires")
        != [
            "exact-final-image-and-sbom-receipt",
            "native-delete-or-cryptographic-erasure-contract",
            "two-identical-contained-lifecycle-repetitions",
            "matched-all-serve-actor-cell-after-lifecycle-pass",
        ]
        or claims.get("publication_ready") is not False
    ):
        raise HermesObservationalMemoryExperimentError(
            "Hermes Observational Memory claim boundary drifted"
        )
    payload["experiment_sha256"] = hashlib.sha256(encoded).hexdigest()
    return payload


def main() -> int:
    payload = validate_experiment_contract()
    print(
        "Hermes Observational Memory experiment PASS: "
        f"{payload['experiment_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
