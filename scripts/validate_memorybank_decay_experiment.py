#!/usr/bin/env python3
"""Fail-closed validator for the clean-room MemoryBank decay control."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments/memory/stage3-memorybank-corrected-decay-doctor.yaml"
)
EXPECTED_STATUS = "MEMORYBANK_CORRECTED_DECAY_CONTRACT_PASS"
EXPECTED_IMAGE = (
    "docker.io/library/python:3.12.11-slim-bookworm@sha256:"
    "519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7"
)


class MemoryBankExperimentError(ValueError):
    """Raised when the clean-room decay contract drifts."""


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise MemoryBankExperimentError("experiment must be a mapping")
    if {
        "schema_version": payload.get("schema_version"),
        "name": payload.get("name"),
        "status": payload.get("status"),
        "scientific_result": payload.get("scientific_result"),
        "publication_ready": payload.get("publication_ready"),
    } != {
        "schema_version": 1,
        "name": "stage3-memorybank-corrected-decay-doctor",
        "status": "registered-cpu-control",
        "scientific_result": False,
        "publication_ready": False,
    }:
        raise MemoryBankExperimentError("experiment identity drifted")
    if payload.get("source") != {
        "source_id": "memorybank-siliconfriend",
        "paper": "arXiv:2305.10250",
        "repository": "https://github.com/zhongwanjun/MemoryBank-SiliconFriend",
        "revision": "cf61c4196e4cfdb0f2b7a0316249fa40312dc3a9",
        "license": "MIT",
        "implementation_mode": "clean-room-reimplementation",
        "upstream_code_imported": False,
    }:
        raise MemoryBankExperimentError("source contract drifted")
    if payload.get("method") != {
        "corrected_formula": "exp(-elapsed / (5 * strength))",
        "upstream_precedence_negative": "exp(-(elapsed / 5) * strength)",
        "strength": "1 + prior_access_count",
        "ranking": "(1 + query_token_overlap) * retention_probability",
        "online_features": [
            "elapsed_steps",
            "prior_access_count",
            "query_token_overlap",
        ],
        "stochastic_deletion": False,
        "future_fields": "forbidden",
    }:
        raise MemoryBankExperimentError("method contract drifted")
    if payload.get("runtime") != {
        "containment": "docker-network-none",
        "image": EXPECTED_IMAGE,
        "architecture": "arm64",
        "clean_state_repeats": 2,
        "read_only_root": True,
        "cap_drop_all": True,
        "no_new_privileges": True,
        "nonroot_uid": 65534,
        "gpu_count": 0,
        "provider_calls": 0,
        "model_calls": 0,
    }:
        raise MemoryBankExperimentError("runtime contract drifted")
    if payload.get("expected") != {
        "status": EXPECTED_STATUS,
        "corrected_monotonic_time": True,
        "corrected_monotonic_strength": True,
        "upstream_precedence_reverses_strength": True,
        "ranking_falsifier_changes_winner": True,
    }:
        raise MemoryBankExperimentError("expected contract drifted")
    if payload.get("admission") != {
        "h100_actor": "blocked-pending-frozen-system-integration",
        "quality_claim": "forbidden",
        "upstream_reproduction_claim": "forbidden",
        "next_gate": "frozen matched corrected-vs-upstream-vs-no-decay system contract",
    }:
        raise MemoryBankExperimentError("admission contract drifted")
    return payload


def main() -> int:
    validate_experiment_contract()
    print("MemoryBank corrected-decay experiment contract PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
