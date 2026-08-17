#!/usr/bin/env python3
"""Validate the pinned Active Graph fork-lifecycle falsification contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments/memory/stage3-activegraph-fork-lifecycle-doctor.yaml"
)
EXPECTED_STATUS = (
    "BLOCKED_ARCHIVE_ONLY_RETENTION_NO_SCOPED_PURGE_AND_SHARED_DB_ERASURE"
)


class ActiveGraphExperimentError(ValueError):
    """Raised when the registered Active Graph contract drifts."""


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise ActiveGraphExperimentError(
            f"cannot load Active Graph experiment: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise ActiveGraphExperimentError("Active Graph experiment must be a mapping")
    if {
        "schema_version": payload.get("schema_version"),
        "name": payload.get("name"),
        "status": payload.get("status"),
        "scientific_result": payload.get("scientific_result"),
        "publication_ready": payload.get("publication_ready"),
    } != {
        "schema_version": 1,
        "name": "stage3-activegraph-fork-lifecycle-doctor",
        "status": "registered-cpu-falsification",
        "scientific_result": False,
        "publication_ready": False,
    }:
        raise ActiveGraphExperimentError("Active Graph identity drifted")
    if payload.get("source") != {
        "source_id": "activegraph-event-sourced-runtime",
        "repository": "https://github.com/yoheinakajima/activegraph",
        "revision": "8aedb1866cf5dce056af97529152ffd6f468a1ed",
        "tree": "8f101d35376f5ef12f197b34a27a2c5aa80ac584",
        "version": "1.10.0",
        "license": "Apache-2.0",
        "license_sha256": (
            "fbb7ac8857b6ce4b826937908e73d96bdc20cbdbbcbad1836f20c6543266b36f"
        ),
        "pyproject_sha256": (
            "a1ee2296e45138abacb1a6c557fc2f1f9e39c7b63a2e95364d84a5fbc8f90768"
        ),
        "git_archive_tar_sha256": (
            "91e0f4099336d34fdb60aee6d9c134ba8f91a2b358d1f46548501353e448461a"
        ),
    }:
        raise ActiveGraphExperimentError("Active Graph source contract drifted")
    if payload.get("runtime") != {
        "containment": "docker-network-none",
        "provider_secrets": "forbidden",
        "sudo": "forbidden",
        "gpu_count": 0,
        "python_image": (
            "python@sha256:"
            "9bb659dc6d5218917236f3711e866a5634bb4c2f208de9d4533aa4863f57c1d3"
        ),
        "python_version": "3.12.11",
        "click_version": "8.2.1",
        "pydantic_version": "2.11.7",
        "clean_state_repeats": 2,
        "fresh_process_restarts_per_repeat": 1,
    }:
        raise ActiveGraphExperimentError("Active Graph runtime contract drifted")
    if payload.get("intervention") != {
        "exact_source_modules": [
            "core.graph",
            "runtime.runtime",
            "runtime.diff",
            "store.sqlite",
            "store.retention",
        ],
        "model_backend_calls": 0,
        "provider_calls": 0,
        "test_parent_fork_divergence": True,
        "test_nested_fork_restart": True,
        "test_run_isolation": True,
        "test_retire_idempotency": True,
        "test_rejected_branch_plaintext_residue": True,
        "test_native_scoped_purge_surface": True,
    }:
        raise ActiveGraphExperimentError("Active Graph intervention drifted")
    if payload.get("expected_falsification") != {
        "status": EXPECTED_STATUS,
        "fork_replay_restart_positive_path": True,
        "rejected_run_moves_to_archive": True,
        "rejected_run_plaintext_survives_restart": True,
        "native_scoped_purge_absent": True,
        "reproduced_in_two_clean_states": True,
    }:
        raise ActiveGraphExperimentError("Active Graph falsification drifted")
    admission = payload.get("admission")
    if (
        not isinstance(admission, dict)
        or admission.get("h100_actor") != "forbidden-for-this-revision"
        or admission.get("scientific_claim") != "forbidden"
        or admission.get("publication_claim") != "forbidden"
        or not isinstance(admission.get("next_gate"), str)
        or not admission["next_gate"].strip()
    ):
        raise ActiveGraphExperimentError("Active Graph admission drifted")
    return payload


def main() -> int:
    validate_experiment_contract()
    print("Active Graph fork-lifecycle falsification contract PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
