#!/usr/bin/env python3
"""Fail-closed validator for the RecMem consolidation lifecycle falsifier."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments/memory/stage3-recmem-consolidation-doctor.yaml"
)
EXPECTED_STATUS = (
    "BLOCKED_NON_IDEMPOTENT_WRITE_MERGE_DATA_LOSS_AND_INCOMPLETE_LINEAGE"
)


class RecMemExperimentError(ValueError):
    """Raised when the registered RecMem falsifier drifts."""


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise RecMemExperimentError(f"cannot load RecMem experiment: {exc}") from exc
    if not isinstance(payload, dict):
        raise RecMemExperimentError("RecMem experiment must be a mapping")
    if {
        "schema_version": payload.get("schema_version"),
        "name": payload.get("name"),
        "status": payload.get("status"),
        "scientific_result": payload.get("scientific_result"),
        "publication_ready": payload.get("publication_ready"),
    } != {
        "schema_version": 1,
        "name": "stage3-recmem-consolidation-doctor",
        "status": "registered-cpu-falsification",
        "scientific_result": False,
        "publication_ready": False,
    }:
        raise RecMemExperimentError("RecMem experiment identity drifted")

    source = payload.get("source")
    expected_source = {
        "source_id": "recmem",
        "repository": "https://github.com/CaiusDai/RecMem",
        "revision": "a84252f6e5587fd4a8caac03ec9f6c732b7a7f35",
        "tree": "46d131594833547b275cf278db665976dc63b2f1",
        "version": "0.1.0",
        "license": "MIT",
        "license_sha256": (
            "761ab33482afa265a75929a9de057b5a2f7d8fd3161fc5ab85ffa62553014537"
        ),
        "git_archive_tar_sha256": (
            "274aba9567b7f1f3a738d159c873d3cbc2744bc3f6f01f857484fc01ec3076f9"
        ),
        "uv_lock_sha256": (
            "94803e92d128d5b42849fb179cff798b26a5b3fa5ff0995a05d28e24ad205c40"
        ),
    }
    if source != expected_source:
        raise RecMemExperimentError("RecMem source contract drifted")

    runtime = payload.get("runtime")
    if runtime != {
        "containment": "docker-network-none",
        "runtime_network": "none",
        "read_only_root": True,
        "cap_drop_all": True,
        "no_new_privileges": True,
        "provider_secrets": "forbidden",
        "sudo": "forbidden",
        "gpu_count_inside_container": 0,
        "clean_state_repeats": 2,
        "base_image": (
            "ghcr.io/astral-sh/uv@sha256:"
            "d1e005e6f5aac724b7554db95f1c128a77d8d35b59ebe70e188852b4bdad3a3d"
        ),
    }:
        raise RecMemExperimentError("RecMem runtime contract drifted")

    intervention = payload.get("intervention")
    if intervention != {
        "storage": "qdrant-local",
        "embedding": "deterministic-1536d-test-double",
        "llm": "deterministic-operation-test-double",
        "provider_calls": 0,
        "model_backend_calls": 0,
        "min_consolidation_count": 3,
        "minimum_relevant_score": 0.99,
        "merge_threshold": 0.99,
        "test_duplicate_retry": True,
        "test_trigger_lineage": True,
        "test_merge_failure_atomicity": True,
        "test_conversation_isolation": True,
        "test_fresh_process_restart": True,
    }:
        raise RecMemExperimentError("RecMem intervention contract drifted")

    expected = payload.get("expected_falsification")
    if expected != {
        "status": EXPECTED_STATUS,
        "duplicate_retry_creates_second_record": True,
        "triggering_message_missing_from_raw_id_lineage": True,
        "failed_replacement_embedding_deletes_prior_episode": True,
        "fresh_process_preserves_successful_consolidation": True,
        "conversation_isolation_preserved": True,
        "reproduced_in_two_clean_states": True,
    }:
        raise RecMemExperimentError("RecMem expected falsification drifted")

    admission = payload.get("admission")
    if (
        not isinstance(admission, dict)
        or admission.get("h100_actor") != "forbidden-for-this-revision"
        or admission.get("scientific_claim") != "forbidden"
        or admission.get("publication_claim") != "forbidden"
        or not isinstance(admission.get("next_gate"), str)
        or not admission["next_gate"].strip()
    ):
        raise RecMemExperimentError("RecMem admission contract drifted")
    return payload


def main() -> int:
    validate_experiment_contract()
    print("RecMem consolidation falsification contract PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
