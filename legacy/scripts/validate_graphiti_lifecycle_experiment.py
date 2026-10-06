#!/usr/bin/env python3
"""Fail-closed validator for the Graphiti native lifecycle doctor."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT
    / "experiments"
    / "memory"
    / "stage3-graphiti-native-lifecycle-doctor.yaml"
)

EXPECTED_SOURCE = {
    "source_id": "graphiti",
    "repository": "https://github.com/getzep/graphiti",
    "revision": "401c59a65bdeb22a44136901ff30231e6998a7fe",
    "version": "0.29.3",
    "git_archive_tar_sha256": (
        "9cfbc01e90f4e6dfbf61fefe86e7f04b15c57c08a7ff8298f873d6f5696d0303"
    ),
    "adapter": "graphiti-explicit-triplet-lifecycle-v1",
    "construction": "explicit-triplet-no-extraction-llm",
    "backend": "falkordblite-0.10.0-per-scope-persistent",
    "embedding": "deterministic-loopback-interface-doctor-v1",
}


class GraphitiLifecycleExperimentError(ValueError):
    """Raised when the registered Graphiti contract drifts."""


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise GraphitiLifecycleExperimentError(
            f"cannot load Graphiti lifecycle experiment: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise GraphitiLifecycleExperimentError("Graphiti experiment must be a mapping")
    if (
        payload.get("schema_version") != 1
        or payload.get("name") != "stage3-graphiti-native-lifecycle-doctor"
        or payload.get("status") != "registered-native-cpu-lifecycle-doctor"
        or payload.get("scientific_result") is not False
        or payload.get("protocol") != "memory-lifecycle-v1"
    ):
        raise GraphitiLifecycleExperimentError("Graphiti experiment identity drifted")
    if payload.get("source") != EXPECTED_SOURCE:
        raise GraphitiLifecycleExperimentError("Graphiti source contract drifted")
    scope = payload.get("mechanism_scope")
    if (
        not isinstance(scope, dict)
        or scope.get("supported_operations")
        != ["apply", "query", "checkpoint", "restore", "inspect", "purge"]
        or scope.get("unsupported_operations") != ["maintain", "feedback"]
        or scope.get("native_shared-database-group-isolation")
        != "diagnostic-only"
    ):
        raise GraphitiLifecycleExperimentError("Graphiti mechanism scope drifted")
    diagnostic = payload.get("expected_diagnostic")
    if (
        not isinstance(diagnostic, dict)
        or diagnostic.get(
            "falkordblite_literal_group_filter_matches_unfiltered_after_restart"
        )
        is not False
    ):
        raise GraphitiLifecycleExperimentError("Graphiti diagnostic contract drifted")
    execution = payload.get("execution")
    expected_execution = {
        "container_required": True,
        "runtime_network": "none",
        "loopback_embedding_server_only": True,
        "gpus": 0,
        "max_gpu_hours": 0,
        "cpu_time_limit_minutes": 15,
        "clean_state_repetitions": 2,
        "sudo": "forbidden",
        "h100_admission": (
            "blocked-until-contained-evidence-crash-recovery-and-group-filter-resolution"
        ),
    }
    if execution != expected_execution:
        raise GraphitiLifecycleExperimentError("Graphiti execution contract drifted")
    claims = set(payload.get("forbidden_claims", []))
    if {
        "native shared-database group isolation passed",
        "crash-safe continuation passed",
        "publication ready",
    } - claims:
        raise GraphitiLifecycleExperimentError("Graphiti forbidden claims drifted")
    return payload


def main() -> int:
    validate_experiment_contract()
    print("Graphiti native lifecycle contract PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
