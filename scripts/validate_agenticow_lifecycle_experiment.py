#!/usr/bin/env python3
"""Validate the pinned agenticow branch-lifecycle falsification contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments/memory/stage3-agenticow-branch-lifecycle-doctor.yaml"
)
EXPECTED_STATUS = (
    "BLOCKED_BLIND_PROMOTION_LOST_UPDATE_TOMBSTONE_RESIDUE_AND_NO_SCOPED_PURGE"
)


class AgenticowExperimentError(ValueError):
    """Raised when the registered agenticow contract drifts."""


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise AgenticowExperimentError(f"cannot load agenticow experiment: {exc}") from exc
    if not isinstance(payload, dict):
        raise AgenticowExperimentError("agenticow experiment must be a mapping")
    if {
        "schema_version": payload.get("schema_version"),
        "name": payload.get("name"),
        "status": payload.get("status"),
        "scientific_result": payload.get("scientific_result"),
        "publication_ready": payload.get("publication_ready"),
    } != {
        "schema_version": 1,
        "name": "stage3-agenticow-branch-lifecycle-doctor",
        "status": "registered-cpu-falsification",
        "scientific_result": False,
        "publication_ready": False,
    }:
        raise AgenticowExperimentError("agenticow identity drifted")
    if payload.get("source") != {
        "source_id": "agenticow",
        "repository": "https://github.com/ruvnet/agenticow",
        "revision": "dd4f437b92d2dbbc1f40dfa00023eed6e9c3bd84",
        "tree": "b64b6fae03aac0491e3d3b78281b5c6997516ebf",
        "version": "0.2.4",
        "license": "MIT",
        "license_sha256": "631f94984f626818d42ecf717aa6e8e0afd4f9f355ca706bd2effafbd1416d06",
        "package_lock_sha256": "3a567fe53f577b56101b5410398b181c4ed2750fd29708ac36dc2f6189982129",
        "git_archive_tar_sha256": (
            "a563784a4c7645f51a45ab430c7c8d3aec77b61cad609585389173da21bdfeac"
        ),
    }:
        raise AgenticowExperimentError("agenticow source contract drifted")
    if payload.get("runtime") != {
        "containment": "docker-network-none",
        "provider_secrets": "forbidden",
        "sudo": "forbidden",
        "gpu_count": 0,
        "node_image": (
            "node:22.21.1-bookworm-slim@sha256:"
            "25b3eb23a00590b7499f2a2ce939322727fcce1b15fdd69754fcd09536a3ae2c"
        ),
        "node_version": "22.21.1",
        "rvf_node_version": "0.2.0",
        "rvf_linux_arm64_version": "0.1.7",
        "clean_state_repeats": 2,
        "fresh_process_restarts_per_repeat": 1,
    }:
        raise AgenticowExperimentError("agenticow runtime contract drifted")
    if payload.get("intervention") != {
        "exact_source_modules": ["src/index.js"],
        "model_backend_calls": 0,
        "provider_calls": 0,
        "test_parent_and_nested_branch_isolation": True,
        "test_checkpoint_rollback": True,
        "test_save_load_restart": True,
        "test_promotion_conflict": True,
        "test_repeated_promotion_idempotency": True,
        "test_tombstone_plaintext_residue": True,
        "test_native_scoped_purge_surface": True,
    }:
        raise AgenticowExperimentError("agenticow intervention drifted")
    if payload.get("expected_falsification") != {
        "status": EXPECTED_STATUS,
        "branch_checkpoint_restart_positive_path": True,
        "promotion_overwrites_later_target_update_without_conflict": True,
        "repeated_promotion_logically_idempotent": True,
        "tombstoned_plaintext_survives_restart": True,
        "native_scoped_purge_absent": True,
        "reproduced_in_two_clean_states": True,
    }:
        raise AgenticowExperimentError("agenticow falsification drifted")
    admission = payload.get("admission")
    if (
        not isinstance(admission, dict)
        or admission.get("h100_actor") != "forbidden-for-this-revision"
        or admission.get("scientific_claim") != "forbidden"
        or admission.get("publication_claim") != "forbidden"
        or not isinstance(admission.get("next_gate"), str)
        or not admission["next_gate"].strip()
    ):
        raise AgenticowExperimentError("agenticow admission drifted")
    return payload


def main() -> int:
    validate_experiment_contract()
    print("agenticow branch-lifecycle falsification contract PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
