#!/usr/bin/env python3
"""Validate the frozen Total Recall native restart-negative experiment."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT
    / "experiments"
    / "memory"
    / "stage3-total-recall-lifecycle-doctor.yaml"
)


def validate_experiment_contract(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Total Recall experiment must be a mapping")
    if payload.get("schema_version") != 1:
        raise ValueError("Total Recall experiment schema drifted")
    if payload.get("name") != "stage3-total-recall-lifecycle-doctor":
        raise ValueError("Total Recall experiment name drifted")
    if payload.get("status") != "registered-native-negative-cpu-doctor":
        raise ValueError("Total Recall experiment status drifted")
    if payload.get("scientific_result") is not False:
        raise ValueError("Total Recall doctor cannot be a scientific result")

    source = payload.get("source")
    expected_source = {
        "source_id": "total-recall-oss",
        "repository": "https://github.com/strvmarv/total-recall",
        "revision": "a2630f671be9b12df8b8ac78df9d26f7053d2fa9",
        "git_tree": "6d62153e3db4026d2146a80251146f9bc3efca68",
        "git_archive_sha256": (
            "19c7e803e6887c740b841043d6a86980f59947b51e6b282a155c477fc37a1338"
        ),
        "license": "MIT",
        "license_sha256": (
            "d97ac8afe40f62ed6f5bffe8dd941a1fac3543b6c68475f6f4e5923f7c128f15"
        ),
        "release": "v4.0.4",
    }
    if source != expected_source:
        raise ValueError("Total Recall source contract drifted")

    execution = payload.get("execution")
    if not isinstance(execution, dict):
        raise ValueError("Total Recall execution contract is missing")
    required_true = {
        "container_required",
        "read_only_root",
        "cap_drop_all",
        "no_new_privileges",
    }
    if any(execution.get(field) is not True for field in required_true):
        raise ValueError("Total Recall containment contract drifted")
    if (
        execution.get("runtime_network") != "none"
        or execution.get("sudo") != "forbidden"
        or execution.get("gpus") != 0
        or execution.get("max_gpu_hours") != 0
        or execution.get("platform") != "linux/arm64"
        or execution.get("nuget_lock_sha256")
        != "615a3f37e6d494f6fae7e293dd6fefdd2464780701ef318fa02cbb694ab10d67"
        or execution.get("nuget_restore") != "locked-mode"
    ):
        raise ValueError("Total Recall CPU execution contract drifted")
    for image_field in ("dotnet_image", "node_image"):
        image = execution.get(image_field)
        if not isinstance(image, str) or "@sha256:" not in image:
            raise ValueError(f"Total Recall {image_field} is not digest pinned")

    expected = payload.get("expected_negative_finding")
    if not isinstance(expected, dict) or expected.get("status") != (
        "BLOCKED_NATIVE_RESTART_DEFECT_REPRODUCED"
    ):
        raise ValueError("Total Recall expected negative finding drifted")
    required_counts = {
        "automatic_content_before_restart": 1,
        "automatic_vectors_before_restart": 0,
        "automatic_content_after_restart": 0,
        "control_content_before_restart": 1,
        "control_vectors_before_restart": 1,
        "control_content_after_restart": 1,
        "control_vectors_after_restart": 1,
    }
    if any(expected.get(key) != value for key, value in required_counts.items()):
        raise ValueError("Total Recall expected row counts drifted")
    if payload.get("next_gate", {}).get("required_before_h100") is not True:
        raise ValueError("Total Recall H100 admission gate is missing")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, nargs="?", default=DEFAULT_EXPERIMENT)
    args = parser.parse_args()
    validate_experiment_contract(args.path.resolve())
    print("Total Recall lifecycle doctor contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
