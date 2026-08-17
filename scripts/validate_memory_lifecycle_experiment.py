#!/usr/bin/env python3
"""Validate the exact registered ``memory-lifecycle-v1`` CPU contract."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml

EXPECTED_CONTRACT: dict[str, Any] = {
    "schema_version": 1,
    "name": "stage3-lifecycle-mechanism-screen",
    "status": "registered-cpu-transport-and-mechanism-contract",
    "scientific_result": False,
    "protocol": "memory-lifecycle-v1",
    "study_version": "memory-lifecycle-study-v1",
    "description": (
        "Prove the additive task-blind lifecycle spine before importing native memory "
        "systems or spending model compute. The reference sidecar exercises active "
        "and archive residency, update/delete, deterministic consolidation, "
        "receipt-bound feedback, fresh-process checkpoint continuation, isolation, "
        "cost accounting, and purge. Passing is transport and mechanism evidence "
        "only; it is not a memory-quality or native-system result."
    ),
    "source": {
        "generator": "memory-lifecycle-episodes-v1",
        "seed": 42,
        "episodes_per_active_slot_cell": 64,
        "total_trace_count": 192,
        "families": [
            "active_archive",
            "update_delete",
            "consolidation",
            "feedback",
        ],
        "cases_per_family_per_cell": 16,
        "queries_per_episode": 2,
        "one_session_per_episode": True,
        "task_blind_event_streams": True,
        "future_oracle_fields_in_commands": False,
    },
    "budget": {
        "primary_active_slots": 4,
        "diagnostic_active_slots": [2, 8],
        "retrieval_top_k_max": 4,
        "archive_reads_per_query_max": 1,
        "injected_tokens_per_query_max": 256,
        "charge_serialized_input_bytes": True,
        "charge_serialized_output_bytes": True,
        "charge_reads_and_writes": True,
        "charge_embedding_calls": True,
        "charge_llm_calls": True,
        "charge_phase_latency": True,
    },
    "operations": [
        "begin",
        "apply",
        "query",
        "maintain",
        "feedback",
        "checkpoint",
        "restore",
        "inspect",
        "purge",
    ],
    "systems": {
        "executed": {
            "system_id": "reference-active-archive-lifecycle-v1",
            "implementation": "deterministic-reference-sidecar-v1",
            "subprocess_required": True,
            "publication_ready": False,
        },
        "planned_not_executed": [
            "no-memory-lifecycle-control",
            "bm25-flat-lifecycle-control",
            "same-facts-temporal-graph-control",
            "fixed-tier-lru-active-archive-control",
            "fixed-schedule-dedupe-consolidation-control",
            "receipt-bound-procedural-rule-control",
            "native-oss-lifecycle-adapters",
        ],
    },
    "gates": {
        "exact_case_and_family_counts": True,
        "exactly_two_queries_per_episode": True,
        "active_slot_archive_read_top_k_and_token_budgets": True,
        "active_archive_promotes_then_serves_active": True,
        "update_visible_before_delete_and_absent_after_delete": True,
        "consolidation_preserves_transitive_source_lineage": True,
        "receipt_bound_feedback_changes_equal_overlap_ranking": True,
        "logical_and_durable_state_chains_complete": True,
        "phase_cost_totals_recompute_exactly": True,
        "fresh_process_suffix_operation_receipts_byte_equal": True,
        "cross_session_canary_visibility_zero": True,
        "purge_leaves_zero_records_and_blocks_session_reuse": True,
        "all_artifacts_content_addressed_and_no_overwrite": True,
    },
    "execution": {
        "container_required": True,
        "runtime_network": "none",
        "scheduler_required_for_gpu_calls": True,
        "gpus": 0,
        "max_gpu_hours": 0,
        "cpu_time_limit_minutes": 30,
        "sudo": "forbidden",
        "one_persistent_sidecar_per_active_slot_cell": True,
        "fresh_sidecar_per_checkpoint_restore": True,
        "host_development_run_is_scientific_evidence": False,
        "h100_actor_wave_status": "blocked-until-reference-and-publication-gates-pass",
    },
    "future_actor_pilot": {
        "status": "not-executed",
        "model": "qwen3.6-35b-a3b",
        "gpus": 2,
        "gpu": "H100",
        "max_gpu_hours": 2,
        "held_out_episodes": 32,
        "intervention": "frozen-lifecycle-bundles-only",
    },
    "artifacts": [
        "experiment.yaml",
        "plans.jsonl",
        "traces.jsonl",
        "restore-traces.jsonl",
        "case-results.jsonl",
        "checkpoint-audit.json",
        "isolation-purge-audit.json",
        "costs-by-phase.json",
        "report.json",
        "manifest.json",
    ],
    "forbidden_claims": [
        "native memory system reproduced",
        "memory quality improved",
        "active inactive paging beats a matched control",
        "graph memory beats flat memory",
        "consolidation or feedback improves agent outcomes",
        "publication ready",
    ],
}


def load_and_validate_experiment(path: Path) -> tuple[dict[str, Any], str]:
    """Load one exact contract and return its payload and byte digest."""

    if not path.is_file() or path.is_symlink():
        raise ValueError("lifecycle experiment must be a regular non-symlink YAML file")
    encoded = path.read_bytes()
    try:
        payload = yaml.safe_load(encoded)
    except yaml.YAMLError as exc:
        raise ValueError("lifecycle experiment YAML is invalid") from exc
    if payload != EXPECTED_CONTRACT:
        raise ValueError("lifecycle experiment scientific contract drifted")
    return payload, hashlib.sha256(encoded).hexdigest()


def validate_experiment_contract(path: Path) -> str:
    """Validate and return the exact registered lifecycle YAML digest."""

    _, digest = load_and_validate_experiment(path)
    return digest
