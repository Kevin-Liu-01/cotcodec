#!/usr/bin/env python3
"""Fail-closed validator for the TokenMizer checkpoint falsifier."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = PROJECT_ROOT / "experiments/memory/stage3-tokenmizer-checkpoint-doctor.yaml"
EXPECTED_STATUS = "TOKENMIZER_ACTIVE_INACTIVE_ADMISSION_KILLED"


class TokenMizerExperimentError(ValueError):
    """Raised when the TokenMizer experiment contract drifts."""


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TokenMizerExperimentError("TokenMizer experiment must be a mapping")
    if {
        "schema_version": payload.get("schema_version"),
        "name": payload.get("name"),
        "status": payload.get("status"),
        "scientific_result": payload.get("scientific_result"),
        "publication_ready": payload.get("publication_ready"),
    } != {
        "schema_version": 1,
        "name": "stage3-tokenmizer-checkpoint-doctor",
        "status": "registered-cpu-falsification",
        "scientific_result": False,
        "publication_ready": False,
    }:
        raise TokenMizerExperimentError("TokenMizer experiment identity drifted")
    source = payload.get("source")
    if not isinstance(source, dict) or source != {
        "source_id": "tokenmizer",
        "repository": "https://github.com/Shweta-Mishra-ai/tokenmizer",
        "revision": "131e3d1569de3e8f70c198ade4e791b47f63dc41",
        "tree": "cc5e934078e91b8265d2ac398d35bcef71cf4a3f",
        "version": "0.3.1",
        "license": "MIT",
        "license_sha256": (
            "abe0de99b2a77c4023114d7291919adebcfc99944b0efaf157a8e945980b1bb0"
        ),
        "git_archive_tar_sha256": (
            "a0f8ad511b796264c706c3df261d31c5ada04ecc14c2701b8d9f016d29682166"
        ),
        "dependency_lock": "absent-upstream",
    }:
        raise TokenMizerExperimentError("TokenMizer source contract drifted")
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
        raise TokenMizerExperimentError("TokenMizer runtime contract drifted")
    expected = payload.get("expected_falsification")
    if not isinstance(expected, dict) or expected.get("status") != EXPECTED_STATUS or not all(
        expected.get(key) is True
        for key in (
            "restart_diff_relabels_existing_nodes_as_added",
            "manual_retry_creates_duplicate_checkpoint",
            "corrupt_recovery_deletes_all_checkpoints",
            "native_scoped_purge_absent",
            "fresh_process_resume_text_preserved",
            "conversation_isolation_preserved",
        )
    ):
        raise TokenMizerExperimentError("TokenMizer falsification contract drifted")
    admission = payload.get("admission")
    if not isinstance(admission, dict) or admission != {
        "active_inactive_h100_actor": "forbidden-for-this-revision",
        "context_compaction_actor": "requires-separate-quality-contract",
        "scientific_claim": "forbidden",
        "publication_claim": "forbidden",
    }:
        raise TokenMizerExperimentError("TokenMizer admission contract drifted")
    return payload


def main() -> int:
    validate_experiment_contract()
    print("TokenMizer checkpoint falsification contract PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
