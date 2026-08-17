#!/usr/bin/env python3
"""Validate the exact LangMem PostgreSQL lifecycle falsification contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments/memory/stage3-langmem-native-lifecycle-doctor.yaml"
)
EXPECTED_SOURCE = {
    "source_id": "langmem",
    "repository": "https://github.com/langchain-ai/langmem",
    "revision": "29cbe41e58528f92e9efa773c12e15c47be3808c",
    "tree": "d85d1f815fb2b54bbc0a85c18453b7a7953ca38c",
    "version": "0.0.30",
    "license": "MIT",
    "license_sha256": "98af1351ea856e008c835bc89a312905960a318072f950732bf346c741027c7d",
    "git_archive_tar_sha256": (
        "24c85c514c80bb263a16626971e8ef53978fd1bc7f9319e47d8a5a0bf4956521"
    ),
}
EXPECTED_RUNTIME = {
    "app_base_image": (
        "ghcr.io/astral-sh/uv:python3.13-trixie-slim@sha256:"
        "d1e005e6f5aac724b7554db95f1c128a77d8d35b59ebe70e188852b4bdad3a3d"
    ),
    "database_image": (
        "postgres@sha256:"
        "ef257d85f76e48da1c64832459b59fcaba1a4dac97bf5d7450c77753542eee94"
    ),
    "langgraph_checkpoint_postgres": "3.1.0",
    "psycopg": "3.3.4",
    "vector_index": "disabled",
    "reason_vector_index_disabled": (
        "Lifecycle semantics do not require semantic ranking or pgvector."
    ),
}
EXPECTED_CASES = {
    "public_hot_path_create_update_delete": True,
    "deterministic_background_manager": True,
    "database_and_fresh_process_restart": True,
    "user_namespace_isolation": True,
    "first_class_namespace_purge_probe": True,
    "enumerate_then_delete_fallback": True,
    "clean_shutdown_plaintext_heap_and_wal_scan": True,
}
EXPECTED_GATES = {
    "exact_source_and_image_receipts": True,
    "acknowledged_state_survives_database_restart": True,
    "hot_path_and_background_records_survive_restart": True,
    "user_namespace_isolation": True,
    "logical_delete_succeeds": True,
    "first_class_scoped_purge_required": True,
    "no_plaintext_after_purge_and_clean_shutdown": True,
}
EXPECTED_EXECUTION = {
    "repetitions": 2,
    "runtime_network": "private-ephemeral-bridge",
    "external_network": "forbidden",
    "gpus": 0,
    "max_gpu_hours": 0,
    "cpu_time_limit_minutes": 15,
    "h100_admission": "blocked-until-all-lifecycle-and-physical-purge-gates-pass",
}
EXPECTED_CLAIM_BOUNDARY = (
    "Exact pinned LangMem public tool, deterministic background-manager transport, "
    "official PostgresStore lifecycle, logical deletion, namespace-purge surface, "
    "and physical plaintext residue; not extraction quality, semantic retrieval, "
    "procedural prompt quality, model effect, managed LangGraph service behavior, "
    "H100 actor quality, or publication evidence."
)
EXPECTED_FORBIDDEN_CLAIMS = [
    "LangMem memory quality improved",
    "semantic retrieval was evaluated",
    "deterministic extraction represents a language model",
    "managed LangGraph service purge semantics were evaluated",
    "publication ready",
]


class LangMemExperimentError(ValueError):
    """Raised when the registered LangMem lifecycle contract drifts."""


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise LangMemExperimentError(f"cannot load LangMem experiment: {exc}") from exc
    if not isinstance(payload, dict):
        raise LangMemExperimentError("LangMem experiment must be a mapping")
    if {
        "schema_version": payload.get("schema_version"),
        "name": payload.get("name"),
        "status": payload.get("status"),
        "scientific_result": payload.get("scientific_result"),
        "publication_ready": payload.get("publication_ready"),
    } != {
        "schema_version": 1,
        "name": "stage3-langmem-native-lifecycle-doctor",
        "status": "registered-native-cpu-lifecycle-doctor",
        "scientific_result": False,
        "publication_ready": False,
    }:
        raise LangMemExperimentError("LangMem experiment identity drifted")
    description = payload.get("description")
    if not isinstance(description, str) or not description.strip():
        raise LangMemExperimentError("LangMem description is missing")
    if payload.get("source") != EXPECTED_SOURCE:
        raise LangMemExperimentError("LangMem source contract drifted")
    if payload.get("runtime") != EXPECTED_RUNTIME:
        raise LangMemExperimentError("LangMem runtime contract drifted")
    if payload.get("cases") != EXPECTED_CASES:
        raise LangMemExperimentError("LangMem case roster drifted")
    if payload.get("gates") != EXPECTED_GATES:
        raise LangMemExperimentError("LangMem gate roster drifted")
    if payload.get("execution") != EXPECTED_EXECUTION:
        raise LangMemExperimentError("LangMem execution contract drifted")
    if payload.get("claim_boundary") != EXPECTED_CLAIM_BOUNDARY:
        raise LangMemExperimentError("LangMem claim boundary drifted")
    if payload.get("forbidden_claims") != EXPECTED_FORBIDDEN_CLAIMS:
        raise LangMemExperimentError("LangMem forbidden-claim roster drifted")
    return payload


def main() -> int:
    validate_experiment_contract()
    print("LangMem PostgreSQL lifecycle experiment contract PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
