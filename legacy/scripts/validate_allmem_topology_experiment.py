#!/usr/bin/env python3
"""Validate the exact All-Mem topology-recovery falsification contract."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT
    / "experiments"
    / "memory"
    / "stage3-allmem-topology-recovery-doctor.yaml"
)
EXPECTED_STATUS = "BLOCKED_SPLIT_MERGE_RAW_EVIDENCE_RECOVERY"
EXPECTED_SOURCE = {
    "source_id": "all-mem",
    "repository": "https://github.com/LvCan926/All-Mem",
    "revision": "f5d6912717b0d6c65a19ba2660fb9b6637d4d50e",
    "tree": "1c13ee386fe416eeb51e64b26c221fd1e4b84b66",
    "git_archive_tar_sha256": (
        "2e46c0afe667ff6656f1adf6c1f66b61d67abe3d015c144661ef38ba8180f298"
    ),
    "license": "MIT",
    "license_sha256": (
        "77aed0526cdc2e6a51c7b837c907828bb238d0ea704a458c1d24e486f666e27d"
    ),
    "requirements_sha256": (
        "f12326a89eb7b10b04dda1b21af8a9a11920566125efc4e5d29b885cce9d077c"
    ),
    "core_sha256": (
        "9f2a9fb638b44b229b9a618437f44490d5721084621b461ed7dabe8b2f76da75"
    ),
    "llm_sha256": (
        "d3303b4d4ab5526835483b587dbaf0bd84ba21844428512654ec04064e69037c"
    ),
}


class AllMemExperimentError(ValueError):
    """Raised when the All-Mem doctor contract drifts."""


def _mapping(payload: dict[str, Any], name: str) -> dict[str, Any]:
    value = payload.get(name)
    if not isinstance(value, dict):
        raise AllMemExperimentError(f"{name} must be a mapping")
    return value


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise AllMemExperimentError("expected schema_version: 1 mapping")
    if payload.get("name") != "stage3-allmem-topology-recovery-doctor":
        raise AllMemExperimentError("experiment name drifted")
    if payload.get("status") != "registered-cpu-falsification":
        raise AllMemExperimentError("experiment status drifted")
    if payload.get("scientific_result") is not False:
        raise AllMemExperimentError("doctor cannot be a scientific result")

    source = _mapping(payload, "source")
    if source != EXPECTED_SOURCE:
        raise AllMemExperimentError("source contract drifted")
    for field in (
        "revision",
        "tree",
        "git_archive_tar_sha256",
        "license_sha256",
        "requirements_sha256",
        "core_sha256",
        "llm_sha256",
    ):
        width = 40 if field in {"revision", "tree"} else 64
        if not re.fullmatch(rf"[0-9a-f]{{{width}}}", str(source[field])):
            raise AllMemExperimentError(f"source {field} is malformed")

    runtime = _mapping(payload, "runtime")
    required_runtime = {
        "containment": "docker-network-none",
        "platform": "linux/arm64",
        "base_image": (
            "docker.io/library/python@sha256:"
            "ecb0ac954790dd64a0d518d699b9c61a91780c42b0d877c802dbaffd04db66f9"
        ),
        "base_image_label": "docker.io/library/python:3.11.15-slim-bookworm",
        "runtime_network": "none",
        "read_only_root": True,
        "cap_drop_all": True,
        "no_new_privileges": True,
        "provider_secrets": "forbidden",
        "sudo": "forbidden",
        "gpu_count": 0,
        "max_gpu_hours": 0,
        "max_cpu_cores": 1,
        "max_memory_mib": 1024,
        "wall_clock_minutes": 20,
        "clean_state_repeats": 2,
    }
    if runtime != required_runtime:
        raise AllMemExperimentError("runtime contract drifted")

    expected = _mapping(payload, "expected_falsification")
    exact_expected = {
        "status": EXPECTED_STATUS,
        "update_has_typed_path_to_archived_source": True,
        "split_has_typed_path_to_archived_source": False,
        "merge_has_typed_path_to_archived_sources": False,
        "derived_nodes_keep_source_ids_without_raw_node_path": True,
        "query_can_expand_archived_update_version": True,
        "persistence_format": "pickle",
        "native_scoped_purge": False,
        "external_model_calls": 0,
        "reproduced_in_two_clean_states": True,
        "fresh_restart_semantic_projection_stable": True,
        "exact_equal_content_tie_order_is_not_required": True,
    }
    if expected != exact_expected:
        raise AllMemExperimentError("expected falsification contract drifted")

    admission = _mapping(payload, "admission")
    if (
        admission.get("active_inactive_h100") != "forbidden-for-this-revision"
        or admission.get("graph_quality_h100") != "forbidden-for-this-revision"
        or not isinstance(admission.get("unblock_requires"), list)
        or len(admission["unblock_requires"]) < 5
    ):
        raise AllMemExperimentError("H100 admission contract drifted")
    if payload.get("forbidden_claims") != [
        "memory quality improvement",
        "graph efficacy",
        "bidirectional active inactive paging",
        "compliant deletion",
        "publication ready",
    ]:
        raise AllMemExperimentError("forbidden claims drifted")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, default=DEFAULT_EXPERIMENT)
    args = parser.parse_args()
    validate_experiment_contract(args.experiment)
    print("All-Mem topology-recovery experiment contract PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
