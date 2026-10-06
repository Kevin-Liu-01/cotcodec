#!/usr/bin/env python3
"""Validate the frozen Neo4j preference-supersession CPU doctor."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT
    / "experiments/memory/stage3-neo4j-preference-supersession-doctor.yaml"
)


def validate_experiment_contract(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("Neo4j preference experiment schema drifted")
    if payload.get("name") != "neo4j-preference-supersession-lifecycle-v1":
        raise ValueError("Neo4j preference experiment name drifted")
    if payload.get("status") != "registered-cpu-lifecycle-conformance":
        raise ValueError("Neo4j preference experiment status drifted")
    if payload.get("scientific_result") is not False:
        raise ValueError("Neo4j preference doctor cannot be a scientific result")
    source = payload.get("source")
    if source != {
        "source_id": "neo4j-agent-memory",
        "repository": "https://github.com/neo4j-labs/agent-memory",
        "revision": "231d60eac9401ab156ba194b519d89dd644dadb8",
        "tree": "73fe15a4e085a2735aa74787feda4724a8e0900d",
        "git_archive_tar_sha256": (
            "64af30347f10998250de67f867f5f036415b8cce5cc7af6c17f9cf7173a47479"
        ),
        "license": "Apache-2.0",
        "license_sha256": "bb86acebd6ee912a2cc0fab21af9861ca80813025ef5deca1f3d232059267226",
        "uv_lock_sha256": "6b9c946cab136d0adae002d31abce07ae88da1f47986621c231ff937ca945d76",
    }:
        raise ValueError("Neo4j preference source contract drifted")
    runtime = payload.get("runtime")
    if not isinstance(runtime, dict):
        raise ValueError("Neo4j preference runtime contract is missing")
    required_runtime = {
        "containment": "docker-private-internal-network",
        "default_lane": "local-arm64",
        "required_confirmation_lane": "cluster-amd64-slurm",
        "client_extras": ["nams"],
        "client_extra_reason": (
            "bolt-imports-nams-package-initializer-and-requires-httpx"
        ),
        "lanes": {
            "local-arm64": {
                "platform": "linux/arm64",
                "client_base_image": (
                    "ghcr.io/astral-sh/uv:0.11.6-python3.13-trixie@sha256:"
                    "87d40bca523b5a0e9dc25babfd93f7b485764b10fd63ca165588814035a5167a"
                ),
                "neo4j_image": (
                    "neo4j:5.26.29-community@sha256:"
                    "1184ab86519418c5a08f6abc06290afddea24a9ef86591379c33d082224cb8de"
                ),
                "evidence_role": "local-contained-conformance",
            },
            "cluster-amd64-slurm": {
                "platform": "linux/amd64",
                "client_base_image": (
                    "ghcr.io/astral-sh/uv:0.11.6-python3.13-trixie@sha256:"
                    "b52141530349f059326aea9731e576e7937c554a27393366f671db38a62fbbd8"
                ),
                "neo4j_image": (
                    "neo4j:5.26.29-community@sha256:"
                    "865213f53381e8d2ef3eec08b11741a6722d388a5e70b134135186a9b5cb27a6"
                ),
                "evidence_role": "cluster-confirmation",
            },
        },
        "runtime_network": "private-internal-only",
        "external_network": "forbidden",
        "read_only_client_root": True,
        "cap_drop_all": True,
        "server_user": "7474:7474",
        "server_capabilities": [],
        "volume_initializer_capabilities": ["CHOWN"],
        "no_new_privileges": True,
        "sudo": "forbidden",
        "gpu_count": 0,
        "max_cpu_cores": 2,
        "max_memory_gib": 4,
        "wall_clock_minutes": 15,
        "clean_volume_repeats": 2,
    }
    if any(runtime.get(key) != value for key, value in required_runtime.items()):
        raise ValueError("Neo4j preference containment or budget drifted")
    intervention = payload.get("intervention")
    if not isinstance(intervention, dict) or any(
        intervention.get(field) != value
        for field, value in {
            "input": "identical-pre-extracted-preference-tuples",
            "embedding": "fail-on-call",
            "extraction": "none",
            "llm": "none",
        }.items()
    ):
        raise ValueError("Neo4j preference no-model intervention drifted")
    required_gates = {
        "exact_source_revision",
        "zero_llm_calls",
        "zero_embedding_calls",
        "one_superseded_by_edge",
        "old_valid_until_set_once",
        "exactly_one_current_preference_for_user_a",
        "old_and_new_present_in_history",
        "old_present_in_pre_supersession_as_of_view",
        "repeated_supersession_idempotent",
        "retained_volume_restart_state_hash_exact",
        "cross_user_isolation",
        "event_lineage_complete",
        "purge_zero_nodes_and_edges_after_restart",
        "two_clean_volume_repeats_identical_semantics",
    }
    gates = payload.get("gates")
    if not isinstance(gates, dict) or set(gates) != required_gates or not all(gates.values()):
        raise ValueError("Neo4j preference gate set drifted")
    if "publication ready" not in payload.get("forbidden_claims", []):
        raise ValueError("Neo4j preference forbidden-claim boundary drifted")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, nargs="?", default=DEFAULT_EXPERIMENT)
    args = parser.parse_args()
    validate_experiment_contract(args.path.resolve())
    print("Neo4j preference lifecycle doctor contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
