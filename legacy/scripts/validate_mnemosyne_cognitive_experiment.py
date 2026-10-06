#!/usr/bin/env python3
"""Fail-closed validator for the Mnemosyne Cognitive lifecycle falsifier."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments/memory/stage3-mnemosyne-cognitive-lifecycle-doctor.yaml"
)
EXPECTED_STATUS = "MNEMOSYNE_COGNITIVE_ACTIVE_INACTIVE_ADMISSION_KILLED"


class MnemosyneCognitiveExperimentError(ValueError):
    """Raised when the Mnemosyne Cognitive experiment contract drifts."""


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise MnemosyneCognitiveExperimentError("experiment must be a mapping")
    if {
        "schema_version": payload.get("schema_version"),
        "name": payload.get("name"),
        "status": payload.get("status"),
        "scientific_result": payload.get("scientific_result"),
        "publication_ready": payload.get("publication_ready"),
    } != {
        "schema_version": 1,
        "name": "stage3-mnemosyne-cognitive-lifecycle-doctor",
        "status": "registered-cpu-falsification",
        "scientific_result": False,
        "publication_ready": False,
    }:
        raise MnemosyneCognitiveExperimentError("experiment identity drifted")
    if payload.get("source") != {
        "source_id": "mnemosyne-cognitive-os",
        "repository": "https://github.com/28naem-del/mnemosyne",
        "revision": "5506aae7cec9ada5523099fd5ab858a4eee593b6",
        "tree": "d5cb986483135f016d731d73baad95f2326d84bb",
        "declared_version": "1.0.1",
        "license": "MIT",
        "license_sha256": (
            "97c063041231883a482d84fe93a1ffce5183bed6ffd17bef32e40a27aeb83e08"
        ),
        "git_archive_tar_sha256": (
            "278cd0fe963854df21847fcaf6b7a650c7ad00f584a551bf48b71e6eb44e2d2e"
        ),
        "dependency_lock": "package-lock.json",
        "dependency_lock_sha256": (
            "791028b9eb8b0c918157436a41f1d4f7d675920ec39018e2b9b7364025d887b9"
        ),
        "upstream_ci_runs_tests": False,
        "explicit_upstream_tests": 62,
    }:
        raise MnemosyneCognitiveExperimentError("source contract drifted")
    runtime = payload.get("runtime")
    expected_runtime = {
        "containment": "docker-internal-network-only",
        "external_egress": "none",
        "read_only_roots": True,
        "cap_drop_all": True,
        "no_new_privileges": True,
        "provider_secrets": "forbidden",
        "sudo": "forbidden",
        "gpu_count_inside_containers": 0,
        "clean_state_repeats": 2,
        "qdrant_restarts_per_repeat": 1,
        "node_base_image": (
            "node:22.21.1-bookworm-slim@sha256:"
            "25b3eb23a00590b7499f2a2ce939322727fcce1b15fdd69754fcd09536a3ae2c"
        ),
        "qdrant_image": (
            "qdrant/qdrant@sha256:"
            "affb67e1d6f2f93d7d20b90d238a7d4b974d36351c162e73bda794e4b2e03483"
        ),
    }
    if runtime != expected_runtime:
        raise MnemosyneCognitiveExperimentError("runtime contract drifted")
    expected = payload.get("expected_falsification")
    if not isinstance(expected, dict) or expected != {
        "status": EXPECTED_STATUS,
        "dry_run_mutates_state": True,
        "repeated_consolidation_is_non_idempotent": True,
        "demotion_remains_in_serving_search": True,
        "forget_retains_plaintext": True,
        "scoped_purge_absent": True,
        "state_and_tombstones_persist_after_restart": True,
    }:
        raise MnemosyneCognitiveExperimentError("falsification contract drifted")
    if payload.get("admission") != {
        "h100_actor": "forbidden-for-this-revision",
        "active_inactive_quality": "not-evaluated",
        "graph_quality": "not-evaluated",
        "scientific_claim": "forbidden",
        "publication_claim": "forbidden",
    }:
        raise MnemosyneCognitiveExperimentError("admission contract drifted")
    return payload


def main() -> int:
    validate_experiment_contract()
    print("Mnemosyne Cognitive lifecycle falsification contract PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
