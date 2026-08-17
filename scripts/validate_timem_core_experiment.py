#!/usr/bin/env python3
"""Fail-closed validator for the TiMem core runtime falsifier."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = PROJECT_ROOT / "experiments/memory/stage3-timem-core-doctor.yaml"
EXPECTED_STATUS = "TIMEM_CORE_RUNTIME_ADMISSION_KILLED"


class TiMemExperimentError(ValueError):
    """Raised when the TiMem experiment contract drifts."""


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TiMemExperimentError("TiMem experiment must be a mapping")
    if {
        "schema_version": payload.get("schema_version"),
        "name": payload.get("name"),
        "status": payload.get("status"),
        "scientific_result": payload.get("scientific_result"),
        "publication_ready": payload.get("publication_ready"),
    } != {
        "schema_version": 1,
        "name": "stage3-timem-core-doctor",
        "status": "registered-cpu-falsification",
        "scientific_result": False,
        "publication_ready": False,
    }:
        raise TiMemExperimentError("TiMem experiment identity drifted")
    source = payload.get("source")
    if not isinstance(source, dict) or source != {
        "source_id": "timem",
        "repository": "https://github.com/TiMEM-AI/TiMEM",
        "revision": "6d279a5f5d40ee229e1995df15c182cb2062c71c",
        "tree": "24645b2c9f2c9b40e5da7762f2159afa321edd2e",
        "declared_version": "pyproject-and-package-1.0.0-readme-1.1.0-conflict",
        "license_scope": "core-engine-apache-2.0-only",
        "license_sha256": (
            "f8e7b0eb7de5c9b9b487ed04650893c196d59ce9d390f676dccda65f5f208edc"
        ),
        "git_archive_tar_sha256": (
            "44e15508366070028c6e4b79f3f94137e8bff90956c627cb0073bf2efa5e6fbe"
        ),
        "dependency_lock": "absent-upstream",
    }:
        raise TiMemExperimentError("TiMem source contract drifted")
    runtime = payload.get("runtime")
    if not isinstance(runtime, dict) or any(
        runtime.get(key) != value
        for key, value in {
            "containment": "docker-network-none",
            "runtime_network": "none",
            "read_only_root": True,
            "cap_drop_all": True,
            "no_new_privileges": True,
            "provider_secrets": "forbidden",
            "sudo": "forbidden",
            "gpu_count_inside_container": 0,
            "clean_state_repeats": 2,
        }.items()
    ):
        raise TiMemExperimentError("TiMem runtime contract drifted")
    expected = payload.get("expected_falsification")
    if (
        not isinstance(expected, dict)
        or expected.get("status") != EXPECTED_STATUS
        or not all(
            expected.get(key) is True
            for key in (
                "source_compiles",
                "l1_processor_is_misused_as_record",
                "l2_session_dataclass_rejects_runtime_fields",
                "l5_required_updated_at_is_omitted",
            )
        )
    ):
        raise TiMemExperimentError("TiMem falsification contract drifted")
    admission = payload.get("admission")
    if not isinstance(admission, dict) or admission != {
        "h100_actor": "forbidden-for-this-revision",
        "hierarchy_quality": "not-evaluated",
        "scientific_claim": "forbidden",
        "publication_claim": "forbidden",
    }:
        raise TiMemExperimentError("TiMem admission contract drifted")
    return payload


def main() -> int:
    validate_experiment_contract()
    print("TiMem core runtime falsification contract PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
