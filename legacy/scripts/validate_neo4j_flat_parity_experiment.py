#!/usr/bin/env python3
"""Validate the frozen Neo4j identical-tuple flat-parity contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT
    / "experiments/memory/stage3-neo4j-identical-tuple-flat-parity.yaml"
)
EXPECTED_STATUS = "NEO4J_IDENTICAL_TUPLE_TRAVERSAL_COMPONENT_PASS"


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("Neo4j flat-parity experiment schema drifted")
    if (
        payload.get("name") != "stage3-neo4j-identical-tuple-flat-parity"
        or payload.get("study_id") != "neo4j-identical-tuple-flat-parity-v1"
        or payload.get("status") != "registered-cluster-component-falsifier"
        or payload.get("scientific_result") is not False
        or payload.get("publication_ready") is not False
    ):
        raise ValueError("Neo4j flat-parity claim boundary drifted")
    source = payload.get("source")
    if not isinstance(source, dict) or source != {
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
        raise ValueError("Neo4j flat-parity source contract drifted")
    runtime = payload.get("runtime")
    required_runtime = {
        "lane": "cluster-amd64-slurm",
        "platform": "linux/amd64",
        "containment": "docker-private-internal-network",
        "client_image": (
            "cotcodec-neo4j-preference-doctor:231d60e-cluster-amd64-slurm-v1"
        ),
        "client_image_id": (
            "sha256:8ec19ef4a4acbbf81205e56148aadfa5e9798d2964175b5b4be8d8644436c382"
        ),
        "neo4j_image": (
            "neo4j:5.26.29-community@sha256:"
            "865213f53381e8d2ef3eec08b11741a6722d388a5e70b134135186a9b5cb27a6"
        ),
        "network": "private-internal-only",
        "external_network": "forbidden",
        "read_only_client_root": True,
        "cap_drop_all": True,
        "no_new_privileges": True,
        "container_gpu_count": 0,
        "slurm_h100_count": 1,
        "max_h100_hours": 0.5,
        "max_cpu_cores": 16,
        "max_memory_gib": 64,
        "wall_clock_minutes": 30,
        "clean_repetitions": 2,
        "sudo": "forbidden",
    }
    if not isinstance(runtime, dict) or runtime != required_runtime:
        raise ValueError("Neo4j flat-parity runtime contract drifted")
    contract = payload.get("contract")
    required_contract = {
        "fixture_version": "neo4j-identical-tuple-fixture-v1",
        "case_count": 48,
        "tuples_per_case": 14,
        "vector_dimensions": 16,
        "vector_source": "deterministic-visible-text-hash",
        "model_calls": 0,
        "embedding_model_calls": 0,
        "external_network_calls": 0,
        "top_k": 2,
        "max_injected_bytes": 256,
        "logical_retrieval_calls_per_arm_per_case": 1,
        "arms": [
            "flat-bm25-dense",
            "zero-traversal",
            "flat-sql-join-ceiling",
            "true-graph",
            "object-degree-preserving-shuffled-graph",
        ],
        "require_identical_tuple_text_and_vector_payload": True,
        "charge_topology_bytes_separately": True,
        "require_flat_sql_join_equal_true_graph": True,
    }
    if not isinstance(contract, dict) or contract != required_contract:
        raise ValueError("Neo4j flat-parity component contract drifted")
    gates = payload.get("gates")
    if not isinstance(gates, dict) or gates != {
        "exact_two_clean_repetitions": True,
        "identical_tuple_payload": True,
        "zero_traversal_equals_flat": True,
        "true_graph_equals_flat_sql_join": True,
        "true_graph_lift_over_bm25_dense_minimum_points": 25,
        "true_graph_lift_over_shuffled_minimum_points": 25,
        "matched_top_k_byte_and_logical_call_budget": True,
        "zero_model_embedding_and_external_network_calls": True,
        "purge_zero_nodes_and_edges": True,
    }:
        raise ValueError("Neo4j flat-parity gate contract drifted")
    forbidden = payload.get("forbidden_claims")
    if not isinstance(forbidden, list) or "scientific result" not in forbidden:
        raise ValueError("Neo4j flat-parity forbidden claims drifted")
    return payload


def main() -> int:
    validate_experiment_contract()
    print("Neo4j identical-tuple flat-parity contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
