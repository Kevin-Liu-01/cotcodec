#!/usr/bin/env python3
"""Validate frozen memory-study contracts and cross-reference source/model pins."""

from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials import (  # noqa: E402
    GENERATED_MEMORY_VERSION,
    LONGMEMEVAL_FULL_TASK_MANIFEST_SHA256,
    LONGMEMEVAL_QUESTION_TYPES,
    LONGMEMEVAL_RETRIEVAL_ADAPTER_VERSION,
    LONGMEMEVAL_RETRIEVAL_ARTIFACT_ROLE,
    LONGMEMEVAL_SCREEN32_RAW_TASK_IDS,
    LONGMEMEVAL_SCREEN32_TASK_MANIFEST_SHA256,
)
from scripts import (  # noqa: E402
    compile_past_bench_sm01,
    validate_activegraph_lifecycle_experiment,
    validate_agent_recall_lifecycle_experiment,
    validate_agenticow_lifecycle_experiment,
    validate_allmem_topology_experiment,
    validate_astra_lifecycle_experiment,
    validate_gaama_actor_experiment,
    validate_gaama_graph_experiment,
    validate_gaama_natural_experiment,
    validate_gbrain_brainbench_experiment,
    validate_graphiti_lifecycle_experiment,
    validate_hermes_byterover_experiment,
    validate_hermes_hindsight_experiment,
    validate_hermes_holographic_experiment,
    validate_hermes_observational_memory_experiment,
    validate_hermes_openviking_experiment,
    validate_hermes_provider_experiment,
    validate_hippo_retention_experiment,
    validate_icarus_lifecycle_experiment,
    validate_jiuwen_memory_lifecycle_experiment,
    validate_langmem_lifecycle_experiment,
    validate_lightmem2_context_paging_experiment,
    validate_lightmem_offline_experiment,
    validate_magic_context_paging_experiment,
    validate_mem0_lifecycle_experiment,
    validate_memforest_artifact_experiment,
    validate_memforge_fresh_install_experiment,
    validate_memoria_lifecycle_experiment,
    validate_memory_lifecycle_experiment,
    validate_memorybank_decay_experiment,
    validate_memorybank_h100_experiment,
    validate_mnemon_active_space_experiment,
    validate_mnemon_actor_experiment,
    validate_mnemosyne_cognitive_experiment,
    validate_mnemosyne_lifecycle_experiment,
    validate_neo4j_flat_parity_experiment,
    validate_neo4j_preference_experiment,
    validate_palimpsest_bitemporal_experiment,
    validate_provider_models,
    validate_reasoningbank_frozen_bank_experiment,
    validate_reasoningbank_source_experiment,
    validate_recmem_consolidation_experiment,
    validate_sage_wiki_artifact_experiment,
    validate_shodh_tier_experiment,
    validate_sodamem_artifact_experiment,
    validate_supermemory_local_experiment,
    validate_timem_core_experiment,
    validate_tokenmizer_checkpoint_experiment,
    validate_total_recall_experiment,
    verify_memory_baseline_sources,
)
from scripts.validate_memory_sources import load_and_validate  # noqa: E402

DEFAULT_PROVIDER_REGISTRY = validate_provider_models.DEFAULT_REGISTRY
DEFAULT_REGISTRY = PROJECT_ROOT / "models" / "registry.yaml"
DEFAULT_LEDGER = PROJECT_ROOT / "research" / "memory-sources.yaml"
DEFAULT_EXPERIMENT_DIR = PROJECT_ROOT / "experiments" / "memory"
STUDY_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
STAGES = {
    "oracle",
    "loader_smoke",
    "frozen_screen",
    "model_transport",
    "native_memory_system_reproduction",
}
STRATA = {"active_core", "inactive_archive", "temporal_graph", "proactive_tool"}
AVAILABLE_CONTROL_SYSTEMS = {
    "bm25",
    "dense-bge-retrieval",
    "full-prefix-ceiling",
    "lru",
    "no-memory",
    "profile-expansion",
    "raw-log-rrf",
    "recency",
    "lexical",
    "learned-next-use",
    "temporal-graph",
    "reference",
}
EXTERNAL_EXPERIMENT_VALIDATORS = {
    "stage3-activegraph-fork-lifecycle-doctor": (
        validate_activegraph_lifecycle_experiment.validate_experiment_contract
    ),
    "stage3-agenticow-branch-lifecycle-doctor": (
        validate_agenticow_lifecycle_experiment.validate_experiment_contract
    ),
    "stage3-agent-recall-scope-lifecycle-doctor": (
        validate_agent_recall_lifecycle_experiment.validate_experiment_contract
    ),
    "stage3-astra-native-lifecycle-doctor": (
        validate_astra_lifecycle_experiment.validate_experiment_contract
    ),
    "stage3-allmem-topology-recovery-doctor": (
        validate_allmem_topology_experiment.validate_experiment_contract
    ),
    "stage-b-past-sm01-checkpoint": compile_past_bench_sm01.validate_experiment_contract,
    "stage3-lifecycle-mechanism-screen": (
        validate_memory_lifecycle_experiment.validate_experiment_contract
    ),
    "stage4-hermes-provider-conformance": (
        validate_hermes_provider_experiment.validate_experiment_contract
    ),
    "stage3-total-recall-lifecycle-doctor": (
        validate_total_recall_experiment.validate_experiment_contract
    ),
    "neo4j-preference-supersession-lifecycle-v1": (
        validate_neo4j_preference_experiment.validate_experiment_contract
    ),
    "stage3-neo4j-identical-tuple-flat-parity": (
        validate_neo4j_flat_parity_experiment.validate_experiment_contract
    ),
    "stage3-hippo-retention-cross-tenant-doctor": (
        validate_hippo_retention_experiment.validate_experiment_contract
    ),
    "stage3-magic-context-paging-doctor": (
        validate_magic_context_paging_experiment.validate_experiment_contract
    ),
    "stage3-memforge-fresh-install-doctor": (
        validate_memforge_fresh_install_experiment.validate_experiment_contract
    ),
    "stage3-memorybank-corrected-decay-doctor": (
        validate_memorybank_decay_experiment.validate_experiment_contract
    ),
    "stage3-memorybank-corrected-decay-h100-screen": (
        validate_memorybank_h100_experiment.validate_experiment_contract
    ),
    "stage3-mem0-native-lifecycle-doctor": (
        validate_mem0_lifecycle_experiment.validate_experiment_contract
    ),
    "stage3-memforest-published-artifact-audit": (
        validate_memforest_artifact_experiment.validate_experiment_contract
    ),
    "stage3-icarus-lifecycle-doctor": (
        validate_icarus_lifecycle_experiment.validate_experiment_contract
    ),
    "stage3-jiuwen-memory-file-lifecycle-doctor": (
        validate_jiuwen_memory_lifecycle_experiment.validate_experiment_contract
    ),
    "stage3-langmem-native-lifecycle-doctor": (
        validate_langmem_lifecycle_experiment.validate_experiment_contract
    ),
    "stage3-sodamem-published-artifact-audit": (
        validate_sodamem_artifact_experiment.validate_experiment_contract
    ),
    "stage3-sage-wiki-published-artifact-audit": (
        validate_sage_wiki_artifact_experiment.validate_experiment_contract
    ),
    "stage3-lightmem2-context-paging-doctor": (
        validate_lightmem2_context_paging_experiment.validate_experiment_contract
    ),
    "stage3-lightmem-offline-consolidation-doctor": (
        validate_lightmem_offline_experiment.validate_experiment_contract
    ),
    "stage3-memoria-transactional-lifecycle-doctor": (
        validate_memoria_lifecycle_experiment.validate_experiment_contract
    ),
    "stage3-palimpsest-bitemporal-doctor": (
        validate_palimpsest_bitemporal_experiment.validate_experiment_contract
    ),
    "stage3-mnemosyne-lifecycle-doctor": (
        validate_mnemosyne_lifecycle_experiment.validate_experiment_contract
    ),
    "stage3-mnemosyne-cognitive-lifecycle-doctor": (
        validate_mnemosyne_cognitive_experiment.validate_experiment_contract
    ),
    "stage3-gaama-graph-component-doctor": (
        validate_gaama_graph_experiment.validate_experiment_contract
    ),
    "stage3-gaama-h100-actor-screen": (
        validate_gaama_actor_experiment.validate_experiment_contract
    ),
    "stage3-gaama-natural-graph-doctor": (
        validate_gaama_natural_experiment.validate_experiment_contract
    ),
    "stage3-gbrain-brainbench-conformance-doctor": (
        validate_gbrain_brainbench_experiment.validate_experiment_contract
    ),
    "stage3-graphiti-native-lifecycle-doctor": (
        validate_graphiti_lifecycle_experiment.validate_experiment_contract
    ),
    "stage3-reasoningbank-source-admission-doctor": (
        validate_reasoningbank_source_experiment.validate_experiment_contract
    ),
    "stage3-reasoningbank-frozen-bank-cpu-doctor": (
        validate_reasoningbank_frozen_bank_experiment.validate_experiment_contract
    ),
    "stage4-hermes-holographic-lifecycle-doctor": (
        validate_hermes_holographic_experiment.validate_experiment_contract
    ),
    "stage4-hermes-byterover-offline-doctor": (
        validate_hermes_byterover_experiment.validate_experiment_contract
    ),
    "stage4-hermes-hindsight-lifecycle-doctor": (
        validate_hermes_hindsight_experiment.validate_experiment_contract
    ),
    "stage4-hermes-openviking-lifecycle-doctor": (
        validate_hermes_openviking_experiment.validate_experiment_contract
    ),
    "stage4-hermes-observational-memory-lifecycle-doctor": (
        validate_hermes_observational_memory_experiment.validate_experiment_contract
    ),
    "stage4-supermemory-local-binary-doctor": (
        validate_supermemory_local_experiment.validate_experiment_contract
    ),
    "stage3-shodh-tier-admission-doctor": (
        validate_shodh_tier_experiment.validate_experiment_contract
    ),
    "stage3-mnemon-active-space-admission-doctor": (
        validate_mnemon_active_space_experiment.validate_experiment_contract
    ),
    "stage3-mnemon-static-space-h100-actor": (
        validate_mnemon_actor_experiment.validate_experiment_contract
    ),
    "stage3-recmem-consolidation-doctor": (
        validate_recmem_consolidation_experiment.validate_experiment_contract
    ),
    "stage3-tokenmizer-checkpoint-doctor": (
        validate_tokenmizer_checkpoint_experiment.validate_experiment_contract
    ),
    "stage3-timem-core-doctor": validate_timem_core_experiment.validate_experiment_contract,
}


class MemoryExperimentError(ValueError):
    """Raised when a memory-study YAML violates the registered contract."""


def _mapping(payload: dict[str, Any], field: str, study_id: str) -> dict[str, Any]:
    value = payload.get(field)
    if not isinstance(value, dict):
        raise MemoryExperimentError(f"{study_id}: {field} must be a mapping")
    return value


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise MemoryExperimentError(f"{label} must be a positive integer")
    return value


def _finite_number(value: Any, label: str, *, minimum: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MemoryExperimentError(f"{label} must be numeric")
    number = float(value)
    if not math.isfinite(number) or number < minimum:
        raise MemoryExperimentError(f"{label} must be finite and >= {minimum}")
    return number


def validate_memory_experiment(
    path: Path,
    *,
    model_ids: set[str],
    source_ids: set[str],
    provider_model_ids: set[str] | None = None,
    ledger_path: Path = DEFAULT_LEDGER,
) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise MemoryExperimentError(f"{path}: expected schema_version: 1 mapping")
    study_id = payload.get("study_id")
    if not isinstance(study_id, str) or not STUDY_ID_RE.fullmatch(study_id):
        raise MemoryExperimentError(f"{path}: invalid study_id")
    stage = payload.get("stage")
    if stage not in STAGES:
        raise MemoryExperimentError(f"{study_id}: unsupported stage {stage!r}")
    if stage == "native_memory_system_reproduction":
        try:
            contract = verify_memory_baseline_sources.load_contract(path, ledger_path)
        except verify_memory_baseline_sources.BaselineSourceError as exc:
            raise MemoryExperimentError(f"{study_id}: {exc}") from exc
        systems = contract["systems"]
        if set(systems) != {"mem0", "graphiti", "langmem", "hindsight"}:
            raise MemoryExperimentError(
                f"{study_id}: primary native roster must contain four registered systems"
            )
        unknown_sources = sorted(
            {system["source_id"] for system in systems.values()} - source_ids
        )
        if unknown_sources:
            raise MemoryExperimentError(
                f"{study_id}: unknown native system sources {unknown_sources}"
            )
        estimands = _mapping(contract, "estimands", study_id)
        if (
            estimands.get("primary", {}).get("treatment_mode")
            != "storage_and_service"
            or estimands.get("secondary", {}).get("treatment_mode") != "serve_only"
            or estimands.get("never_pool_modes") is not True
        ):
            raise MemoryExperimentError(f"{study_id}: native estimands must remain separate")
        matched = _mapping(contract, "matched_components", study_id)
        budget = _mapping(matched, "budget", study_id)
        expected_budget = {
            "active_slots": 4,
            "archive_reads": 1,
            "retrieval_top_k": 4,
            "injected_tokens": 256,
        }
        if any(budget.get(key) != value for key, value in expected_budget.items()):
            raise MemoryExperimentError(f"{study_id}: native memory budget drifted")
        if any(
            budget.get(field) is not True
            for field in (
                "charge_serialized_bytes",
                "charge_embedding_calls",
                "charge_llm_calls",
                "charge_construction_latency",
            )
        ):
            raise MemoryExperimentError(f"{study_id}: all native construction costs are charged")
        actor_matrix = _mapping(contract, "actor_matrix", study_id)
        if actor_matrix.get("freeze_memory_outputs_before_actor_comparison") is not True:
            raise MemoryExperimentError(
                f"{study_id}: memory outputs must freeze before actor comparison"
            )
        open_fields = (
            "interface_only",
            "discovery",
            "large_open_confirmation",
            "architecture_diagnostic_only",
        )
        open_ids = {
            model_id
            for field in open_fields
            for model_id in actor_matrix.get(field, [])
        }
        unknown_open = sorted(open_ids - model_ids)
        if unknown_open:
            raise MemoryExperimentError(f"{study_id}: unpinned open actors {unknown_open}")
        expected_open = {
            "discovery": {"qwen3.5-4b", "qwen3.5-9b"},
            "large_open_confirmation": {"qwen3.6-35b-a3b", "gpt-oss-120b"},
        }
        if any(
            set(actor_matrix.get(field, [])) != expected
            for field, expected in expected_open.items()
        ):
            raise MemoryExperimentError(
                f"{study_id}: registered discovery/large-open scale ladder drifted"
            )
        if provider_model_ids is None:
            raise MemoryExperimentError(f"{study_id}: provider registry is required")
        frontier_ids = {
            model_id
            for field in ("frontier_confirmation", "maximum_secondary")
            for model_id in actor_matrix.get(field, [])
        }
        unknown_frontier = sorted(frontier_ids - provider_model_ids)
        if unknown_frontier:
            raise MemoryExperimentError(
                f"{study_id}: unknown frontier actors {unknown_frontier}"
            )
        analysis = _mapping(contract, "analysis", study_id)
        if any(
            analysis.get(field) is not True
            for field in (
                "model_by_memory_policy_interaction",
                "task_family_clustered_inference",
                "never_generalize_small_model_lift_without_large_and_frontier_confirmation",
            )
        ) or analysis.get("parameter_count_trend") != "exploratory_only":
            raise MemoryExperimentError(
                f"{study_id}: model-scale interaction analysis is incomplete"
            )
        execution = _mapping(contract, "execution", study_id)
        if any(
            execution.get(field) is not True
            for field in (
                "container_required",
                "one_native_system_per_image",
                "require_digest_pinned_images",
                "require_source_archive_receipt",
                "scheduler_required_for_gpu_calls",
                "checkpoint_on_preemption",
                "require_fresh_job_resume",
                "require_frozen_selection_bundle",
            )
        ):
            raise MemoryExperimentError(f"{study_id}: native execution gates are incomplete")
        per_cell = _finite_number(
            execution.get("open_discovery_max_gpu_hours_per_cell"),
            f"{study_id}.open_discovery_max_gpu_hours_per_cell",
        )
        total = _finite_number(
            execution.get("large_open_confirmation_max_gpu_hours_total"),
            f"{study_id}.large_open_confirmation_max_gpu_hours_total",
        )
        hosted = _finite_number(
            execution.get("frontier_confirmation_max_usd_total"),
            f"{study_id}.frontier_confirmation_max_usd_total",
        )
        if not 0 < per_cell <= 8 or not 0 < total <= 128 or not 0 < hosted <= 250:
            raise MemoryExperimentError(f"{study_id}: native reproduction budget exceeds ceiling")
        seeds = execution.get("seeds")
        if not isinstance(seeds, list) or len(seeds) < 3 or not all(
            isinstance(seed, int) and not isinstance(seed, bool) for seed in seeds
        ):
            raise MemoryExperimentError(f"{study_id}: native execution requires three seeds")
        if len(set(seeds)) != len(seeds):
            raise MemoryExperimentError(f"{study_id}: native execution seeds must be distinct")
        if (
            execution.get("seed_semantics")
            != "assignment-sensitivity-not-independent-task-replication"
        ):
            raise MemoryExperimentError(f"{study_id}: seed semantics are not explicit")
        return contract

    source = _mapping(payload, "source", study_id)
    source_type = source.get("type")
    if source_type == "generated":
        if source.get("generator_version") != GENERATED_MEMORY_VERSION:
            raise MemoryExperimentError(
                f"{study_id}: generated source must use {GENERATED_MEMORY_VERSION}"
            )
        if source.get("implemented_history_modes") != [
            "plain",
            "supersession",
            "deletion-recreate",
        ]:
            raise MemoryExperimentError(
                f"{study_id}: generated CRUD history modes are incomplete"
            )
        if source.get("strata") is None or set(source["strata"]) != STRATA:
            raise MemoryExperimentError(
                f"{study_id}: source.strata must contain all four strata"
            )
        step_range = source.get("step_range")
        if (
            not isinstance(step_range, list)
            or len(step_range) != 2
            or not all(isinstance(step, int) for step in step_range)
            or step_range[0] < 1
            or step_range[0] > step_range[1]
        ):
            raise MemoryExperimentError(f"{study_id}: invalid source.step_range")
        if stage == "oracle":
            split_counts = _mapping(source, "split_counts", study_id)
            expected_counts = {"train": 1_440, "dev": 480, "test": 480}
            if split_counts != expected_counts:
                raise MemoryExperimentError(
                    f"{study_id}: registered split must be exactly 1440/480/480"
                )
            if source.get("episodes_per_propensity") != sum(expected_counts.values()):
                raise MemoryExperimentError(
                    f"{study_id}: episode count must equal the registered split total"
                )
            split_contract = _mapping(source, "split_contract", study_id)
            expected_split_contract = {
                "implementation": "exact-family-manifest-v1",
                "split_seed": 42,
                "family_id": "cross-stratum-generated-family",
                "entity_and_value_namespaces_are_family_scoped": True,
                "manifest_required_before_learned_controls": True,
            }
            if split_contract != expected_split_contract:
                raise MemoryExperimentError(
                    f"{study_id}: exact family split contract drifted"
                )
    elif source_type == "longmemeval":
        if stage != "frozen_screen":
            raise MemoryExperimentError(
                f"{study_id}: LongMemEval is currently registered only for frozen_screen"
            )
        if source.get("source_id") != "longmemeval":
            raise MemoryExperimentError(f"{study_id}: public source_id must be longmemeval")
        if source.get("strata") != ["inactive_archive"]:
            raise MemoryExperimentError(
                f"{study_id}: LongMemEval-S must use inactive_archive"
            )
        task_count = _positive_int(source.get("task_count"), f"{study_id}.task_count")
        screen_tasks = _positive_int(
            source.get("screen_tasks"), f"{study_id}.screen_tasks"
        )
        if task_count != 500 or screen_tasks != 32:
            raise MemoryExperimentError(
                f"{study_id}: LongMemEval task counts must bind the 500-task source"
            )
        if tuple(source.get("question_types", ())) != LONGMEMEVAL_QUESTION_TYPES:
            raise MemoryExperimentError(
                f"{study_id}: LongMemEval question-type coverage drifted"
            )
        if tuple(source.get("screen_raw_task_ids", ())) != (
            LONGMEMEVAL_SCREEN32_RAW_TASK_IDS
        ):
            raise MemoryExperimentError(
                f"{study_id}: LongMemEval screen task IDs drifted"
            )
        if source.get("transport_panel") != {
            "version": "longmemeval-transport-panel-v2",
            "seed": 42,
            "abstention_count": 2,
            "shared_session_count": 0,
            "claim_eligible": False,
        }:
            raise MemoryExperimentError(
                f"{study_id}: LongMemEval transport-panel derivation drifted"
            )
        if source.get("scientific_benchmark") != {
            "task_count": 500,
            "assignment": "all-serve",
            "official_semantic_judge_required": True,
            "status": "not-yet-executed",
        }:
            raise MemoryExperimentError(
                f"{study_id}: LongMemEval scientific benchmark contract drifted"
            )
        required_honesty = {
            "artifact_role": LONGMEMEVAL_RETRIEVAL_ARTIFACT_ROLE,
            "retrieval_evaluation_capable": True,
            "retrieval_claim_enabled": False,
            "graph_claim_enabled": False,
            "official_evaluation_implemented": True,
            "official_evaluation_executed": False,
            "available_evaluation": (
                "official-prompt-port-unexecuted-plus-strict-exact-diagnostic"
            ),
        }
        if any(source.get(key) != value for key, value in required_honesty.items()):
            raise MemoryExperimentError(
                f"{study_id}: LongMemEval evidence limitations are not explicit"
            )
        if not isinstance(source.get("candidate_seed"), int) or isinstance(
            source.get("candidate_seed"), bool
        ):
            raise MemoryExperimentError(f"{study_id}: candidate_seed must be an integer")
        if source["candidate_seed"] != 42:
            raise MemoryExperimentError(
                f"{study_id}: registered LongMemEval candidate seed must be 42"
            )
        for field in (
            "dataset_sha256",
            "full_task_manifest_sha256",
            "screen_task_manifest_sha256",
        ):
            if not isinstance(source.get(field), str) or not SHA256_RE.fullmatch(
                source[field]
            ):
                raise MemoryExperimentError(f"{study_id}: {field} must be immutable")
        ledger = load_and_validate(ledger_path)
        artifacts = ledger["sources"]["longmemeval"].get("artifacts", [])
        matching_artifacts = [
            artifact
            for artifact in artifacts
            if artifact.get("role") == "full-haystack-retrieval-dataset"
        ]
        if len(matching_artifacts) != 1:
            raise MemoryExperimentError(
                f"{study_id}: LongMemEval-S requires one registered retrieval artifact"
            )
        artifact = matching_artifacts[0]
        expected_public = {
            "dataset_revision": artifact["revision"],
            "dataset_sha256": artifact["sha256"],
            "dataset_size": artifact["size"],
            "dataset_license": artifact["license"],
        }
        if any(source.get(key) != value for key, value in expected_public.items()):
            raise MemoryExperimentError(
                f"{study_id}: LongMemEval artifact differs from the source ledger"
            )
        expected_adapter = {
            "adapter_version": LONGMEMEVAL_RETRIEVAL_ADAPTER_VERSION,
            "full_task_manifest_sha256": LONGMEMEVAL_FULL_TASK_MANIFEST_SHA256,
            "screen_task_manifest_sha256": LONGMEMEVAL_SCREEN32_TASK_MANIFEST_SHA256,
        }
        if any(source.get(key) != value for key, value in expected_adapter.items()):
            raise MemoryExperimentError(
                f"{study_id}: LongMemEval adapter or task manifest drifted"
            )
    else:
        raise MemoryExperimentError(f"{study_id}: unsupported source.type {source_type!r}")
    for external in source.get("sealed_external_tests", []):
        if external.get("source_id") not in source_ids:
            raise MemoryExperimentError(
                f"{study_id}: unknown external source {external.get('source_id')!r}"
            )
    if stage == "model_transport":
        _positive_int(
            source.get("safety_screen_episodes"),
            f"{study_id}.safety_screen_episodes",
        )
        safety_cases = source.get("implemented_safety_cases")
        if not isinstance(safety_cases, list) or len(set(safety_cases)) < 4:
            raise MemoryExperimentError(
                f"{study_id}: at least four implemented safety cases are required"
            )

    model = _mapping(payload, "model", study_id)
    model_id = model.get("model_id")
    if stage == "model_transport":
        if provider_model_ids is None:
            raise MemoryExperimentError(f"{study_id}: provider registry is required")
        open_roster = model.get("open_roster")
        if not isinstance(open_roster, list) or len(open_roster) < 4:
            raise MemoryExperimentError(f"{study_id}: open_roster must have at least four models")
        open_ids = [entry.get("model_id") for entry in open_roster if isinstance(entry, dict)]
        if len(open_ids) != len(open_roster) or len(set(open_ids)) != len(open_ids):
            raise MemoryExperimentError(f"{study_id}: open_roster IDs must be unique")
        unknown_open = sorted(set(open_ids) - model_ids)
        if unknown_open:
            raise MemoryExperimentError(f"{study_id}: unpinned open models {unknown_open}")
        provider_roster = model.get("provider_roster")
        if not isinstance(provider_roster, list) or len(provider_roster) < 5:
            raise MemoryExperimentError(
                f"{study_id}: provider_roster must contain at least five models"
            )
        unknown_provider = sorted(set(provider_roster) - provider_model_ids)
        if unknown_provider:
            raise MemoryExperimentError(
                f"{study_id}: unknown provider models {unknown_provider}"
            )
        secondary = model.get("maximum_capability_secondary")
        if secondary not in provider_model_ids or secondary in provider_roster:
            raise MemoryExperimentError(
                f"{study_id}: maximum capability model must be a registered secondary"
            )
        _positive_int(model.get("max_completion_tokens"), f"{study_id}.max_completion_tokens")
        transport = _mapping(payload, "memory_system_transport", study_id)
        expected_transport = {
            "protocol": "memory-system-v1",
            "actor_input": "frozen-selection-bundle",
            "primary_treatment_mode": "storage_and_service",
            "freeze_before_actor_wave": True,
            "require_exact_task_source_and_budget_match": True,
            "require_content_addressed_bundle": True,
            "forbid_native_recomputation_between_actor_models": True,
        }
        if any(transport.get(key) != value for key, value in expected_transport.items()):
            raise MemoryExperimentError(
                f"{study_id}: frozen memory-system transport contract drifted"
            )
        diagnostic_ceiling = _mapping(payload, "diagnostic_ceiling", study_id)
        expected_ceiling = {
            "control_id": "full-prefix-ceiling",
            "system_id": "full-prefix-ceiling-v1",
            "budget_class": "diagnostic-unmatched",
            "eligible_for_primary": False,
            "treatment_mode": "storage_and_service",
            "require_separate_frozen_bundle": True,
            "forbid_strongest_control_selection": True,
            "memory_budget": {
                "active_slots": 4,
                "max_archive_reads": 0,
                "retrieval_top_k": 1,
                "max_injected_tokens": 32_768,
                "charge_serialized_bytes": True,
            },
        }
        if diagnostic_ceiling != expected_ceiling:
            raise MemoryExperimentError(
                f"{study_id}: full-prefix diagnostic ceiling contract drifted"
            )
    elif stage == "oracle":
        if model_id != "deterministic-oracle":
            raise MemoryExperimentError(f"{study_id}: oracle stage must use deterministic-oracle")
    elif model_id not in model_ids:
        raise MemoryExperimentError(f"{study_id}: model_id {model_id!r} is not pinned")
    decoding = model.get("decoding")
    if stage not in {"oracle", "model_transport"}:
        if not isinstance(decoding, dict) or decoding.get("do_sample") is not False:
            raise MemoryExperimentError(f"{study_id}: model decoding must be deterministic")
        _positive_int(decoding.get("max_new_tokens"), f"{study_id}.max_new_tokens")

    budget = _mapping(payload, "memory_budget", study_id)
    if budget.get("primary_active_slots") != 4:
        raise MemoryExperimentError(f"{study_id}: primary_active_slots must be 4")
    if budget.get("max_archive_reads_per_opportunity") != 1:
        raise MemoryExperimentError(f"{study_id}: archive read budget must be exactly 1")
    if budget.get("max_retrieval_top_k") != 4:
        raise MemoryExperimentError(f"{study_id}: retrieval top-k must be exactly 4")
    if budget.get("max_injected_tokens") != 256:
        raise MemoryExperimentError(f"{study_id}: injected token cap must be exactly 256")
    if budget.get("charge_serialized_bytes") is not True:
        raise MemoryExperimentError(f"{study_id}: serialized memory bytes must be charged")

    design = _mapping(payload, "causal_design", study_id)
    propensities = (
        design.get("confirm_serve_propensities")
        if stage == "model_transport"
        else design.get("serve_propensities")
    )
    if not isinstance(propensities, list) or not propensities:
        raise MemoryExperimentError(f"{study_id}: serve_propensities must be non-empty")
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or not 0.0 < float(value) < 1.0
        for value in propensities
    ):
        raise MemoryExperimentError(f"{study_id}: propensities must be finite in (0,1)")
    audit_field = (
        "self_hosted_paired_replay_fraction"
        if stage == "model_transport"
        else "paired_replay_fraction"
    )
    audit_fraction = _finite_number(design.get(audit_field), f"{study_id}.{audit_field}")
    if audit_fraction > 1.0:
        raise MemoryExperimentError(f"{study_id}: paired_replay_fraction cannot exceed 1")
    if design.get("candidates_per_episode") != 1:
        raise MemoryExperimentError(f"{study_id}: v1 requires exactly one candidate")
    if design.get("assignment_before_continuation") is not True:
        raise MemoryExperimentError(f"{study_id}: assignment must precede continuation")
    if design.get("prefix_only_features") is not True:
        raise MemoryExperimentError(f"{study_id}: policy features must be prefix-only")

    controls = _mapping(payload, "controls", study_id)
    if controls.get("matrix_execution") is not False:
        raise MemoryExperimentError(
            f"{study_id}: current runner must not claim a control matrix"
        )
    if controls.get("primary_claim_enabled") is not False:
        raise MemoryExperimentError(
            f"{study_id}: primary memory-policy claim must remain disabled"
        )
    available_controls = controls.get("implementation_available")
    if not isinstance(available_controls, list) or set(available_controls) != (
        AVAILABLE_CONTROL_SYSTEMS
    ):
        raise MemoryExperimentError(
            f"{study_id}: available control systems must match the implemented registry"
        )
    executed_controls = controls.get("executed_by_runner")
    planned_controls = controls.get("planned_controls")
    if (
        not isinstance(executed_controls, list)
        or not executed_controls
        or not isinstance(planned_controls, list)
        or not planned_controls
        or set(executed_controls) & set(planned_controls)
    ):
        raise MemoryExperimentError(
            f"{study_id}: executed and planned controls must be explicit and disjoint"
        )
    if stage == "model_transport":
        primary = _mapping(payload, "primary_analysis", study_id)
        if (
            primary.get("enabled") is not False
            or primary.get("status")
            != "deferred-until-control-matrix-and-frozen-causal-policy-exist"
        ):
            raise MemoryExperimentError(
                f"{study_id}: primary analysis must remain explicitly deferred"
            )

    execution = _mapping(payload, "execution", study_id)
    seeds = execution.get("seeds")
    if not isinstance(seeds, list) or not seeds or not all(
        isinstance(seed, int) and not isinstance(seed, bool) for seed in seeds
    ):
        raise MemoryExperimentError(f"{study_id}: execution.seeds must contain integers")
    if len(set(seeds)) != len(seeds):
        raise MemoryExperimentError(f"{study_id}: execution.seeds must be distinct")
    if stage != "loader_smoke" and len(seeds) < 3:
        raise MemoryExperimentError(f"{study_id}: study requires three assignment seeds")
    if stage != "loader_smoke" and (
        execution.get("seed_semantics")
        != "assignment-sensitivity-not-independent-task-replication"
    ):
        raise MemoryExperimentError(f"{study_id}: seed semantics are not explicit")
    if execution.get("container_required") is not True:
        raise MemoryExperimentError(f"{study_id}: container execution is required")
    if stage == "model_transport":
        if execution.get("scheduler_required_for_open_models") is not True:
            raise MemoryExperimentError(f"{study_id}: open models require scheduler execution")
        if execution.get("require_frozen_selection_bundle_for_native_system_cells") is not True:
            raise MemoryExperimentError(
                f"{study_id}: native actor cells require frozen selections"
            )
        per_model = _finite_number(
            execution.get("open_screen_max_gpu_hours_per_model"),
            f"{study_id}.open_screen_max_gpu_hours_per_model",
        )
        total = _finite_number(
            execution.get("open_confirmation_max_gpu_hours_total"),
            f"{study_id}.open_confirmation_max_gpu_hours_total",
        )
        hosted = _finite_number(
            execution.get("hosted_confirmation_max_usd_total"),
            f"{study_id}.hosted_confirmation_max_usd_total",
        )
        hosted_screen = _finite_number(
            execution.get("hosted_screen_max_usd_per_model"),
            f"{study_id}.hosted_screen_max_usd_per_model",
        )
        if (
            not 0 < per_model <= 8
            or not 0 < total <= 128
            or not 0 < hosted <= 250
            or not 0 < hosted_screen <= 5
        ):
            raise MemoryExperimentError(f"{study_id}: model transport budget exceeds hard ceilings")
    else:
        if execution.get("scheduler_required") is not True:
            raise MemoryExperimentError(f"{study_id}: scheduler execution is required")
        if source_type == "longmemeval" and execution.get(
            "require_frozen_selection_bundle"
        ) is not True:
            raise MemoryExperimentError(
                f"{study_id}: public screen requires a frozen selection bundle"
            )
        gpu_hours = _finite_number(
            execution.get("max_gpu_hours"), f"{study_id}.max_gpu_hours"
        )
        if stage == "oracle" and gpu_hours != 0:
            raise MemoryExperimentError(f"{study_id}: oracle stage must use zero GPU-hours")
        if stage != "oracle" and not 0 < gpu_hours <= 8:
            raise MemoryExperimentError(
                f"{study_id}: discovery model stage must cap GPU-hours at 8"
            )
    if execution.get("checkpoint_on_preemption") is not True:
        raise MemoryExperimentError(f"{study_id}: checkpoint_on_preemption is required")
    if execution.get("prove_fresh_job_resume") is not True:
        raise MemoryExperimentError(f"{study_id}: fresh-job resume proof is required")
    return payload


def validate_directory(
    directory: Path = DEFAULT_EXPERIMENT_DIR,
    *,
    registry_path: Path = DEFAULT_REGISTRY,
    ledger_path: Path = DEFAULT_LEDGER,
    provider_registry_path: Path = DEFAULT_PROVIDER_REGISTRY,
) -> list[Path]:
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    ledger = yaml.safe_load(ledger_path.read_text(encoding="utf-8"))
    if not isinstance(registry, dict) or not isinstance(registry.get("models"), dict):
        raise MemoryExperimentError("model registry must contain a models mapping")
    if not isinstance(ledger, dict) or not isinstance(ledger.get("sources"), dict):
        raise MemoryExperimentError("memory source ledger must contain a sources mapping")
    models = registry["models"]
    sources = ledger["sources"]
    providers = validate_provider_models.load_provider_registry(provider_registry_path)["models"]
    paths = sorted(directory.glob("*.yaml"))
    if not paths:
        raise MemoryExperimentError(f"no memory experiment YAML files found in {directory}")
    for path in paths:
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise MemoryExperimentError(f"{path}: invalid YAML") from exc
        if not isinstance(payload, dict):
            raise MemoryExperimentError(f"{path}: experiment must be a mapping")
        external_name = payload.get("name")
        external_validator = (
            EXTERNAL_EXPERIMENT_VALIDATORS.get(external_name)
            if isinstance(external_name, str)
            else None
        )
        if external_validator is not None:
            try:
                external_validator(path)
            except ValueError as exc:
                raise MemoryExperimentError(f"{path}: {exc}") from exc
            continue
        if "study_id" in payload:
            validate_memory_experiment(
                path,
                model_ids=set(models),
                source_ids=set(sources),
                provider_model_ids=set(providers),
                ledger_path=ledger_path,
            )
            continue
        if not isinstance(external_name, str):
            raise MemoryExperimentError(
                f"{path}: unrecognized memory experiment contract"
            )
        raise MemoryExperimentError(f"{path}: unrecognized memory experiment contract")
    return paths


def validate_experiment_path(
    path: Path,
    *,
    registry_path: Path = DEFAULT_REGISTRY,
    ledger_path: Path = DEFAULT_LEDGER,
    provider_registry_path: Path = DEFAULT_PROVIDER_REGISTRY,
) -> Path:
    """Validate exactly one selected experiment without opening unrelated studies.

    Runtime jobs use this boundary because a source-only container intentionally
    omits historical result bundles needed by other registered experiments. The
    selected contract still cross-references the complete model, source, and
    provider registries; only unrelated experiment validation is excluded.
    """

    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    ledger = yaml.safe_load(ledger_path.read_text(encoding="utf-8"))
    if not isinstance(registry, dict) or not isinstance(registry.get("models"), dict):
        raise MemoryExperimentError("model registry must contain a models mapping")
    if not isinstance(ledger, dict) or not isinstance(ledger.get("sources"), dict):
        raise MemoryExperimentError("memory source ledger must contain a sources mapping")
    providers = validate_provider_models.load_provider_registry(provider_registry_path)[
        "models"
    ]
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise MemoryExperimentError(f"{path}: invalid YAML") from exc
    if not isinstance(payload, dict):
        raise MemoryExperimentError(f"{path}: experiment must be a mapping")
    external_name = payload.get("name")
    external_validator = (
        EXTERNAL_EXPERIMENT_VALIDATORS.get(external_name)
        if isinstance(external_name, str)
        else None
    )
    if external_validator is not None:
        try:
            external_validator(path)
        except ValueError as exc:
            raise MemoryExperimentError(f"{path}: {exc}") from exc
        return path
    if "study_id" in payload:
        validate_memory_experiment(
            path,
            model_ids=set(registry["models"]),
            source_ids=set(ledger["sources"]),
            provider_model_ids=set(providers),
            ledger_path=ledger_path,
        )
        return path
    raise MemoryExperimentError(f"{path}: unrecognized memory experiment contract")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=DEFAULT_EXPERIMENT_DIR)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--providers", type=Path, default=DEFAULT_PROVIDER_REGISTRY)
    args = parser.parse_args()
    paths = validate_directory(
        args.directory,
        registry_path=args.registry,
        ledger_path=args.ledger,
        provider_registry_path=args.providers,
    )
    print(f"memory experiment contracts PASS: {len(paths)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
