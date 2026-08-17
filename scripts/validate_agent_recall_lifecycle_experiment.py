#!/usr/bin/env python3
"""Validate the pinned Agent Recall scoped-lifecycle falsification contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments/memory/stage3-agent-recall-scope-lifecycle-doctor.yaml"
)
EXPECTED_STATUS = (
    "BLOCKED_CROSS_SCOPE_DESTRUCTIVE_DELETE_STALE_CHILD_BRIEFING_AND_"
    "SOFT_DELETE_RESIDUE"
)


class AgentRecallExperimentError(ValueError):
    """Raised when the registered Agent Recall contract drifts."""


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise AgentRecallExperimentError(
            f"cannot load Agent Recall experiment: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise AgentRecallExperimentError("Agent Recall experiment must be a mapping")
    if {
        "schema_version": payload.get("schema_version"),
        "name": payload.get("name"),
        "status": payload.get("status"),
        "scientific_result": payload.get("scientific_result"),
        "publication_ready": payload.get("publication_ready"),
    } != {
        "schema_version": 1,
        "name": "stage3-agent-recall-scope-lifecycle-doctor",
        "status": "registered-cpu-falsification",
        "scientific_result": False,
        "publication_ready": False,
    }:
        raise AgentRecallExperimentError("Agent Recall identity drifted")
    if payload.get("source") != {
        "source_id": "agent-recall",
        "repository": "https://github.com/mnardit/agent-recall",
        "revision": "dcf21b5cc9691e1371299917e2e474fb82e07cab",
        "tree": "1c0395b24d2d9f45d04443f7f187b026ce41f43b",
        "version": "0.4.0",
        "license": "MIT",
        "license_sha256": (
            "0c51e5594c40bfe9e039ff0925d3efff5cb83402f21e5d466250958e724ff6c6"
        ),
        "pyproject_sha256": (
            "9272395436cbcba0b6e537bf26d45c4cbe7593560bfb83309c46fb963acfc70f"
        ),
        "git_archive_tar_sha256": (
            "f1412268b653e971df41c730bd4d1aa19cb0e20e79f358c4c41c8ec80350a06a"
        ),
    }:
        raise AgentRecallExperimentError("Agent Recall source contract drifted")
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
        "pyyaml_version": "6.0.2",
        "clean_state_repeats": 2,
        "fresh_process_restarts_per_repeat": 1,
    }:
        raise AgentRecallExperimentError("Agent Recall runtime contract drifted")
    if payload.get("intervention") != {
        "exact_source_modules": [
            "store",
            "hierarchy",
            "mcp_bridge",
            "context_gen.cache",
        ],
        "model_backend_calls": 0,
        "provider_calls": 0,
        "test_scope_precedence": True,
        "test_bitemporal_correction_restart": True,
        "test_cross_scope_entity_delete": True,
        "test_parent_scope_cache_invalidation": True,
        "test_soft_observation_delete_residue": True,
        "test_native_scoped_purge_surface": True,
    }:
        raise AgentRecallExperimentError("Agent Recall intervention drifted")
    if payload.get("expected_falsification") != {
        "status": EXPECTED_STATUS,
        "scope_precedence_and_restart_positive_path": True,
        "cross_scope_delete_cascades_other_scope": True,
        "parent_change_leaves_child_cache_fresh": True,
        "delete_observations_retains_plaintext": True,
        "native_scoped_purge_absent": True,
        "reproduced_in_two_clean_states": True,
    }:
        raise AgentRecallExperimentError("Agent Recall falsification drifted")
    admission = payload.get("admission")
    if (
        not isinstance(admission, dict)
        or admission.get("h100_actor") != "forbidden-for-this-revision"
        or admission.get("scientific_claim") != "forbidden"
        or admission.get("publication_claim") != "forbidden"
        or not isinstance(admission.get("next_gate"), str)
        or not admission["next_gate"].strip()
    ):
        raise AgentRecallExperimentError("Agent Recall admission drifted")
    return payload


def main() -> int:
    validate_experiment_contract()
    print("Agent Recall scoped-lifecycle falsification contract PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
