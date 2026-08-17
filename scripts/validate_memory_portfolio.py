#!/usr/bin/env python3
"""Validate the selected memory experiment portfolio against the source matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

if __package__:
    from scripts.compile_memory_landscape import compile_landscape
    from scripts.seal_gbrain_brainbench_evidence import (
        GBrainEvidenceError,
        validate_gbrain_brainbench_evidence,
    )
    from scripts.seal_memforest_artifact_evidence import (
        MemForestArtifactEvidenceError,
        validate_memforest_artifact_evidence,
    )
    from scripts.seal_sage_wiki_artifact_evidence import (
        SageWikiArtifactEvidenceError,
        validate_sage_wiki_artifact_evidence,
    )
    from scripts.seal_sodamem_artifact_evidence import (
        SodaMemArtifactEvidenceError,
        validate_sodamem_artifact_evidence,
    )
    from scripts.validate_fidelis_zero_llm_evidence import (
        FidelisEvidenceError,
        validate_fidelis_zero_llm_evidence,
    )
    from scripts.validate_memory_sources import (
        DEFAULT_LEDGER,
        load_and_validate,
        load_unique_yaml,
    )
else:
    from compile_memory_landscape import compile_landscape
    from seal_gbrain_brainbench_evidence import (  # type: ignore[no-redef]
        GBrainEvidenceError,
        validate_gbrain_brainbench_evidence,
    )
    from seal_memforest_artifact_evidence import (  # type: ignore[no-redef]
        MemForestArtifactEvidenceError,
        validate_memforest_artifact_evidence,
    )
    from seal_sage_wiki_artifact_evidence import (  # type: ignore[no-redef]
        SageWikiArtifactEvidenceError,
        validate_sage_wiki_artifact_evidence,
    )
    from seal_sodamem_artifact_evidence import (  # type: ignore[no-redef]
        SodaMemArtifactEvidenceError,
        validate_sodamem_artifact_evidence,
    )
    from validate_fidelis_zero_llm_evidence import (  # type: ignore[no-redef]
        FidelisEvidenceError,
        validate_fidelis_zero_llm_evidence,
    )
    from validate_memory_sources import DEFAULT_LEDGER, load_and_validate, load_unique_yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PORTFOLIO = PROJECT_ROOT / "research" / "memory-experiment-portfolio.yaml"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
MODES = {
    "benchmark-adapter",
    "blocked-data",
    "blocked-license",
    "collision-reference",
    "contained-import",
    "paper-reimplementation",
}
STATUSES = {
    "blocked",
    "existing-interface-smoke",
    "existing-lifecycle-smoke",
    "mechanism-control-implemented",
    "natural-retrieval-component-passed",
    "natural-topology-escalation-killed",
    "actor-translation-killed",
    "planned",
    "candidate-image-and-sbom-built",
    "candidate-image-built-not-sbom",
    "cpu-retrieval-reproduced",
    "cpu-lifecycle-blocked",
    "runtime-contract-implemented",
    "source-adapter-implemented",
    "source-admission-blocked",
    "artifact-audited-not-reproduced",
    "source-doctor-implemented",
    "discovery-killed",
}
PRIORITIES = {"primary", "secondary", "boundary", "external-test"}
COMPUTE_CLASSES = {"contained-cpu-doctor", "contained-h100-screen", "literature-only"}
NEGATIVE_TERMINAL_STATUSES = {
    "activegraph-event-sourced-runtime": (
        "BLOCKED_ARCHIVE_ONLY_RETENTION_NO_SCOPED_PURGE_AND_SHARED_DB_ERASURE"
    ),
    "agenticow": (
        "BLOCKED_BLIND_PROMOTION_LOST_UPDATE_TOMBSTONE_RESIDUE_AND_NO_SCOPED_PURGE"
    ),
    "agent-recall": (
        "BLOCKED_CROSS_SCOPE_DESTRUCTIVE_DELETE_STALE_CHILD_BRIEFING_AND_"
        "SOFT_DELETE_RESIDUE"
    ),
    "astra-working-set": "BLOCKED_NONDETERMINISTIC_RECALL_ACCESS_ACCOUNTING",
    "all-mem": "BLOCKED_SPLIT_MERGE_RAW_EVIDENCE_RECOVERY",
    "graphiti-native-lifecycle-adapter": (
        "BLOCKED_FALKORDBLITE_ARM64_MODULE_ARCHITECTURE_MISMATCH"
    ),
    "hermes-byterover-cli": (
        "BLOCKED_OFFLINE_DAEMON_AND_PORTABLE_SESSION_LIFECYCLE_REPRODUCED"
    ),
    "hermes-holographic": (
        "BLOCKED_GLOBAL_SESSION_SCOPE_AND_NATIVE_SESSION_PURGE_REPRODUCED"
    ),
    "hermes-hindsight-native": "BLOCKED_NATIVE_PHYSICAL_PURGE_RESIDUE",
    "hermes-observational-memory": "BLOCKED_NO_PROVIDER_NATIVE_DELETE_OR_ERASURE",
    "hippo-memory": "BLOCKED_CROSS_TENANT_CONSOLIDATION_AND_PURGE_RESIDUE_REPRODUCED",
    "icarus-memory-infra": "BLOCKED_NON_IDEMPOTENT_PROMOTION_AND_NO_NATIVE_PURGE",
    "jiuwen-memory": (
        "JIUWEN_FILE_BACKEND_ADMISSION_KILLED_GLOBAL_ID_AND_MIGRATION_RESET"
    ),
    "langmem": (
        "BLOCKED_NO_FIRST_CLASS_SCOPED_PURGE_AND_POSTGRES_PLAINTEXT_RESIDUE"
    ),
    "lightmem": (
        "BLOCKED_DESTRUCTIVE_DEFAULT_REOPEN_AND_CONSOLIDATION_CONTRACT_DRIFT"
    ),
    "lightmem2": "BLOCKED_CROSS_SESSION_DISCLOSURE_ARCHIVE_COLLISION_AND_NO_NATIVE_PURGE",
    "magic-context": "BLOCKED_PORTABLE_LIFECYCLE_AND_SECURE_PURGE_REPRODUCED",
    "memorybank-siliconfriend": (
        "MEMORYBANK_CORRECTED_DECAY_PASS_NO_DECAY_KILLS_SCALING"
    ),
    "memforge": "MEMFORGE_FRESH_INSTALL_ADMISSION_KILLED",
    "memoria-matrixorigin": (
        "BLOCKED_SHARED_TABLE_BRANCH_EXPOSURE_SOFT_PURGE_RESIDUE_AND_NONATOMIC_ROLLBACK"
    ),
    "mnemon": "MNEMON_STATIC_ROUTING_KILLED",
    "mnemosyne-cognitive-os": (
        "MNEMOSYNE_COGNITIVE_ACTIVE_INACTIVE_ADMISSION_KILLED"
    ),
    "mnemosyne-oss": "BLOCKED_CONSOLIDATED_FORGET_AND_NO_REACTIVATION",
    "openviking": "BLOCKED_NATIVE_PHYSICAL_PURGE_RESIDUE",
    "palimpsest-bitemporal-memory": (
        "BLOCKED_BITEMPORAL_RESTART_AND_NO_NATIVE_PURGE"
    ),
    "past-bench": "PAST_SM01_RESTART_EQUIVALENCE_FALSIFIED",
    "recmem": "BLOCKED_NON_IDEMPOTENT_WRITE_MERGE_DATA_LOSS_AND_INCOMPLETE_LINEAGE",
    "shodh-memory": "BLOCKED_OVERLAPPING_RESIDENCY_AND_RESTART_STRANDING",
    "supermemory": "BLOCKED_ACKNOWLEDGED_WRITES_LOST_ON_SIGKILL",
    "timem": "TIMEM_CORE_RUNTIME_ADMISSION_KILLED",
    "tokenmizer": "TOKENMIZER_ACTIVE_INACTIVE_ADMISSION_KILLED",
    "total-recall-oss": "BLOCKED_NATIVE_RESTART_DEFECT_REPRODUCED",
}
HERMES_PROVIDER_ROSTER = [
    "byterover",
    "hindsight",
    "holographic",
    "honcho",
    "mem0",
    "memori",
    "openviking",
    "retaindb",
    "supermemory",
]


class MemoryPortfolioError(ValueError):
    """Raised when the experiment portfolio can overclaim or reuse unsafe code."""


def _text(owner: str, value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MemoryPortfolioError(f"{owner}: {field} must be a non-empty string")
    return value


def _bound_artifact(owner: str, path_value: Any, sha_value: Any) -> bytes:
    if (
        not isinstance(path_value, str)
        or Path(path_value).is_absolute()
        or ".." in Path(path_value).parts
    ):
        raise MemoryPortfolioError(f"{owner}: artifact path must be safe and relative")
    if not isinstance(sha_value, str) or not re.fullmatch(r"[0-9a-f]{64}", sha_value):
        raise MemoryPortfolioError(f"{owner}: artifact SHA-256 is invalid")
    artifact = PROJECT_ROOT / path_value
    if not artifact.is_file() or artifact.is_symlink():
        raise MemoryPortfolioError(f"{owner}: artifact is missing")
    data = artifact.read_bytes()
    if hashlib.sha256(data).hexdigest() != sha_value:
        raise MemoryPortfolioError(f"{owner}: artifact SHA-256 drifted")
    return data


def _validate_negative_receipt(
    owner: str,
    *,
    source_id: str,
    revision: str,
    terminal_status: str,
    data: bytes,
) -> dict[str, Any]:
    try:
        receipt = json.loads(data)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise MemoryPortfolioError(f"{owner}: negative receipt is invalid JSON") from exc
    if (
        not isinstance(receipt, dict)
        or receipt.get("schema_version") != 1
        or receipt.get("source_id") != source_id
        or receipt.get("status") != terminal_status
        or receipt.get("scientific_result") is not False
        or receipt.get("publication_ready") is not False
    ):
        raise MemoryPortfolioError(f"{owner}: negative receipt identity drifted")
    if source_id == "activegraph-event-sourced-runtime":
        if (
            receipt.get("evidence_kind")
            != "contained-native-fork-lifecycle-negative"
            or receipt.get("source_revisions", {}).get(
                "https://github.com/yoheinakajima/activegraph"
            )
            != revision
            or receipt.get("runtime_lane") != "local-arm64-docker-network-none"
            or receipt.get("run_count") != 2
            or receipt.get("stable_phase_projection_sha256")
            != "bc1be630657d7629ce35975b0387f4e34968c8eb79c3a18f7ca838fd204940a1"
            or receipt.get("findings", {}).get("parent_fork_restart_isolated")
            is not True
            or receipt.get("findings", {}).get(
                "rejected_run_plaintext_survived_restart"
            )
            is not True
            or receipt.get("findings", {}).get("native_scoped_purge_absent")
            is not True
        ):
            raise MemoryPortfolioError(
                f"{owner}: Active Graph receipt semantics drifted"
            )
    elif source_id == "agenticow":
        findings = receipt.get("findings", {})
        if (
            receipt.get("evidence_kind")
            != "contained-native-branch-lifecycle-negative"
            or receipt.get("source_revisions", {}).get(
                "https://github.com/ruvnet/agenticow"
            )
            != revision
            or receipt.get("runtime_lane") != "local-arm64-docker-network-none"
            or receipt.get("run_count") != 2
            or receipt.get("stable_phase_projection_sha256")
            != "eeb24984a901d4bcb2982eab89af6c9a85c5a07ce8db6ce8ca640e5942709571"
            or findings.get("promotion_blindly_overwrites_later_parent_update")
            is not True
            or findings.get("tombstoned_plaintext_survived_restart") is not True
            or findings.get("native_scoped_purge_absent") is not True
        ):
            raise MemoryPortfolioError(
                f"{owner}: agenticow receipt semantics drifted"
            )
    elif source_id == "astra-working-set":
        findings = receipt.get("claim_boundary", {})
        if (
            receipt.get("evidence_kind")
            != "h100-native-lifecycle-admission-negative"
            or receipt.get("source_revisions", {}).get(
                "https://github.com/cyh7789/astra"
            )
            != revision
            or receipt.get("runtime_lane")
            != "docker-under-slurm-h100-allocation-no-container-gpu"
            or receipt.get("run_count") != 2
            or receipt.get("slurm_job_id") != 269
            or receipt.get("gpu_sku") != "H100"
            or receipt.get("gpu_count") != 1
            or receipt.get("projection_without_access_count_sha256")
            != "5c947f1b251659dccbee26cab6e1f45b6911eb4d52149ed5a3ff0d8d6b1a31eb"
            or findings.get("native_restart_executed") is not True
            or findings.get("durable_readmission_executed") is not True
            or findings.get("user_isolation_executed") is not True
            or findings.get("deterministic_recall_state") is not False
            or findings.get("physical_purge_available") is not False
            or findings.get("idempotency_key_available") is not False
            or findings.get("hard_pinned_capacity_enforced") is not False
            or findings.get("h100_actor_admission")
            != "forbidden-for-this-revision"
        ):
            raise MemoryPortfolioError(
                f"{owner}: ASTRA native lifecycle receipt semantics drifted"
            )
    elif source_id == "langmem":
        findings = receipt.get("findings", {})
        if (
            receipt.get("evidence_kind")
            != "contained-native-postgres-lifecycle-negative"
            or receipt.get("source_revisions", {}).get(
                "https://github.com/langchain-ai/langmem"
            )
            != revision
            or receipt.get("runtime_lane")
            != "local-arm64-docker-internal-bridge"
            or receipt.get("run_count") != 2
            or receipt.get("stable_projection_sha256")
            != "96602010adaf5b90c706c9be759d4790464ccd7a2ee4eea302011ce76cbdac61"
            or findings.get("database_and_fresh_process_restart_passed")
            is not True
            or findings.get("first_class_namespace_purge_absent") is not True
            or findings.get("purged_plaintext_remains_in_postgresql_heap")
            is not True
            or findings.get("purged_plaintext_remains_in_postgresql_wal")
            is not True
        ):
            raise MemoryPortfolioError(
                f"{owner}: LangMem native lifecycle receipt semantics drifted"
            )
    elif source_id == "total-recall-oss":
        if (
            receipt.get("evidence_kind") != "native-negative-reproduction"
            or receipt.get("source_revisions", {}).get(
                "https://github.com/strvmarv/total-recall"
            )
            != revision
            or receipt.get("run_count") != 2
        ):
            raise MemoryPortfolioError(f"{owner}: Total Recall receipt semantics drifted")
    elif source_id == "hippo-memory":
        if (
            receipt.get("evidence_kind") != "native-negative-reproduction"
            or receipt.get("source_revisions", {}).get(
                "https://github.com/kitfunso/hippo-memory"
            )
            != revision
            or receipt.get("runtime_lane") != "local-arm64-docker-network-none"
            or receipt.get("run_count") != 2
            or receipt.get("stable_projection", {})
            .get("cross_tenant", {})
            .get("mixed_semantic_created")
            is not True
            or receipt.get("stable_projection", {})
            .get("purge", {})
            .get("plaintext_residue_reproduced")
            is not True
        ):
            raise MemoryPortfolioError(f"{owner}: Hippo receipt semantics drifted")
    elif source_id == "all-mem":
        if (
            receipt.get("evidence_kind") != "native-negative-reproduction"
            or receipt.get("source_revisions", {}).get(
                "https://github.com/LvCan926/All-Mem"
            )
            != revision
            or receipt.get("runtime_lane")
            != "local-arm64-docker-network-none"
            or receipt.get("run_count") != 2
            or receipt.get("claim_boundary", {}).get(
                "split_merge_raw_recovery_failed"
            )
            is not True
            or receipt.get("claim_boundary", {}).get("update_version_recovery_passed")
            is not True
            or receipt.get("claim_boundary", {}).get("h100_admission")
            != "forbidden-for-this-revision"
        ):
            raise MemoryPortfolioError(f"{owner}: All-Mem receipt semantics drifted")
    elif source_id == "magic-context":
        projection = receipt.get("stable_projection", {})
        if (
            receipt.get("evidence_kind") != "native-negative-reproduction"
            or receipt.get("source_revisions", {}).get(
                "https://github.com/cortexkit/magic-context"
            )
            != revision
            or receipt.get("runtime_lane") != "local-arm64-docker-network-none"
            or receipt.get("run_count") != 2
            or projection.get("alias", {}).get(
                "same_session_id_cross_harness_alias_reproduced"
            )
            is not True
            or projection.get("purge", {}).get("physical_zero_residue") is not False
            or projection.get("purge", {}).get(
                "host_row_deletion_makes_expansion_unrecoverable"
            )
            is not True
        ):
            raise MemoryPortfolioError(
                f"{owner}: Magic Context receipt semantics drifted"
            )
    elif source_id == "mnemosyne-oss":
        projection = receipt.get("stable_projection", {})
        if (
            receipt.get("evidence_kind") != "native-negative-reproduction"
            or receipt.get("source_revisions", {}).get(
                "https://github.com/mnemosyne-oss/mnemosyne"
            )
            != revision
            or receipt.get("runtime_lane") != "local-arm64-docker-network-none"
            or receipt.get("run_count") != 2
            or receipt.get("claim_boundary")
            != {
                "bidirectional_paging_demonstrated": False,
                "consolidated_source_complete_forget": False,
                "h100_actor_admission": "forbidden-for-this-revision",
                "memory_quality_measured": False,
                "one_way_consolidation_reproduced": True,
            }
            or projection.get("restart", {}).get("recall_did_not_reactivate")
            is not True
            or projection.get("purge", {}).get("logical_episodic_canary_rows") != 1
            or projection.get("purge", {}).get(
                "plaintext_canary_residue_reproduced"
            )
            is not True
        ):
            raise MemoryPortfolioError(
                f"{owner}: Mnemosyne receipt semantics drifted"
            )
    elif source_id == "icarus-memory-infra":
        projection = receipt.get("stable_projection", {})
        if (
            receipt.get("evidence_kind") != "native-negative-reproduction"
            or receipt.get("source_revisions", {}).get(
                "https://github.com/esaradev/icarus-memory-infra"
            )
            != revision
            or receipt.get("runtime_lane") != "local-arm64-docker-network-none"
            or receipt.get("run_count") != 2
            or receipt.get("claim_boundary")
            != {
                "autonomous_paging_demonstrated": False,
                "idempotent_promotion": False,
                "manual_lifecycle_reproduced": True,
                "memory_quality_measured": False,
                "native_scoped_purge": False,
            }
            or projection.get("prepare", {}).get(
                "duplicate_end_session_created_extra_summary"
            )
            is not True
            or projection.get("prepare", {}).get(
                "duplicate_end_session_created_extra_wiki_link"
            )
            is not True
            or projection.get("purge", {}).get(
                "all_canaries_remain_physically_present"
            )
            is not True
        ):
            raise MemoryPortfolioError(f"{owner}: Icarus receipt semantics drifted")
    elif source_id == "lightmem":
        if (
            receipt.get("evidence_kind")
            != "contained-exact-source-consolidation-negative"
            or receipt.get("source_revisions", {}).get(
                "https://github.com/zjunlp/LightMem"
            )
            != revision
            or receipt.get("runtime_lane") != "local-arm64-docker-network-none"
            or receipt.get("run_count") != 2
            or receipt.get("stable_projection_sha256")
            != "80a2b06c818ece9fce8319c0121d3e951b7469e456ed636b79d6d02f1aa72b56"
            or receipt.get("claim_boundary")
            != {
                "active_inactive_paging_demonstrated": False,
                "h100_actor_admission": False,
                "offline_consolidation_quality_measured": False,
                "persistent_restart_safe": False,
                "scoped_purge_available": False,
            }
        ):
            raise MemoryPortfolioError(f"{owner}: LightMem receipt semantics drifted")
    elif source_id == "lightmem2":
        projection = receipt.get("stable_projection", {})
        if (
            receipt.get("evidence_kind") != "native-negative-reproduction"
            or receipt.get("source_revisions", {}).get(
                "https://github.com/zjunlp/LightMem2"
            )
            != revision
            or receipt.get("runtime_lane") != "local-arm64-docker-network-none"
            or receipt.get("run_count") != 2
            or receipt.get("claim_boundary")
            != {
                "active_inactive_paging_demonstrated": False,
                "archive_before_pointer_stub": True,
                "collision_safe_archive_identity": False,
                "mcp_recovery_is_session_scoped": False,
                "memory_quality_measured": False,
                "native_scoped_purge": False,
                "strict_session_lookup_exists": True,
            }
            or projection.get("prepare", {}).get(
                "first_key_resolved_to_second_payload"
            )
            is not True
            or projection.get("restart", {}).get(
                "restart_unscoped_mcp_resolver_disclosed_b_to_any_caller"
            )
            is not True
            or projection.get("purge", {}).get(
                "native_scoped_purge_api_available"
            )
            is not False
        ):
            raise MemoryPortfolioError(f"{owner}: LightMem2 receipt semantics drifted")
    elif source_id == "shodh-memory":
        projection = receipt.get("stable_projection", {})
        if (
            receipt.get("evidence_kind") != "native-negative-reproduction"
            or receipt.get("source_revisions", {}).get(
                "https://github.com/varun29ankuS/shodh-memory"
            )
            != revision
            or receipt.get("runtime_lane") != "local-arm64-docker-network-none"
            or receipt.get("run_count") != 2
            or receipt.get("claim_boundary")
            != {
                "active_caches_survive_restart": False,
                "disjoint_residency_demonstrated": False,
                "h100_actor_admission": "forbidden-for-this-revision",
                "memory_quality_measured": False,
                "offline_aged_session_promotion": False,
                "physical_erasure_proven": False,
                "unique_forget_count": False,
            }
            or projection.get("checks", {}).get(
                "new_working_record_already_in_long_term_storage"
            )
            is not True
            or projection.get("checks", {}).get(
                "eligible_persisted_session_is_stranded_after_restart"
            )
            is not True
            or projection.get("observations", {}).get("forget_all_returned") != 2
        ):
            raise MemoryPortfolioError(f"{owner}: Shodh receipt semantics drifted")
    elif source_id == "palimpsest-bitemporal-memory":
        projection = receipt.get("stable_projection", {})
        if (
            receipt.get("evidence_kind") != "native-negative-reproduction"
            or receipt.get("source_revisions", {}).get(
                "https://github.com/joe51111jwd/palimpsest"
            )
            != revision
            or receipt.get("runtime_lane") != "local-arm64-docker-network-none"
            or receipt.get("run_count") != 2
            or receipt.get("claim_boundary")
            != {
                "active_inactive_paging_demonstrated": False,
                "bitemporal_durability": False,
                "bitemporal_structure_before_restart": True,
                "memory_quality_measured": False,
                "native_scoped_purge": False,
            }
            or projection.get("restart", {}).get(
                "restart_preserved_knowledge_cutoff"
            )
            is not False
            or projection.get("restart", {}).get(
                "restart_preserved_cardinality_continuation"
            )
            is not False
            or projection.get("purge", {}).get(
                "plaintext_canary_remains_in_sqlite"
            )
            is not True
        ):
            raise MemoryPortfolioError(
                f"{owner}: Palimpsest receipt semantics drifted"
            )
    elif source_id == "memorybank-siliconfriend":
        outcome = receipt.get("outcome", {})
        if (
            receipt.get("evidence_kind") != "clean-room-h100-control-screen"
            or receipt.get("evidence_grade") != "local-negative-reproduced"
            or receipt.get("source_revisions", {}).get(
                "https://github.com/zhongwanjun/MemoryBank-SiliconFriend"
            )
            != revision
            or receipt.get("runtime_lane") != "docker-under-slurm-h100-discovery"
            or receipt.get("initial_jobs")
            != {"corrected": 328, "no_decay": 330, "upstream_precedence": 329}
            or receipt.get("resume_jobs") != {"corrected": 333, "no_decay": 334}
            or receipt.get("claim_boundary")
            != {
                "larger_model_admission": "forbidden-because-no-decay-dominates",
                "memorybank_paper_reproduced": False,
                "no_decay_control_dominates_corrected": True,
                "upstream_precedence_bug_repaired": True,
            }
            or outcome.get("corrected_minus_upstream_points")
            != 10.96774193548387
            or outcome.get("corrected_minus_no_decay_points")
            != -58.38709677419355
            or outcome.get("safety_failures") != 0
            or outcome.get("valid_action_rate") != 1.0
        ):
            raise MemoryPortfolioError(
                f"{owner}: MemoryBank H100 receipt semantics drifted"
            )
    elif source_id == "graphiti-native-lifecycle-adapter":
        module = receipt.get("module_architecture", {})
        if (
            receipt.get("evidence_kind") != "native-negative-reproduction"
            or receipt.get("source_revisions", {}).get(
                "https://github.com/getzep/graphiti"
            )
            != revision
            or receipt.get("runtime_lane")
            != "local-arm64-docker-network-none"
            or receipt.get("run_count") != 2
            or receipt.get("claim_boundary", {}).get("container_lifecycle_executed")
            is not False
            or receipt.get("claim_boundary", {}).get("h100_admission")
            != "forbidden-for-this-revision-and-runtime"
            or module.get("redis-server", {}).get("e_machine") != 183
            or module.get("falkordb.so", {}).get("e_machine") != 62
        ):
            raise MemoryPortfolioError(f"{owner}: Graphiti receipt semantics drifted")
    elif source_id == "hermes-holographic":
        projection = receipt.get("stable_projection", {})
        if (
            receipt.get("evidence_kind") != "native-negative-reproduction"
            or receipt.get("source_revisions", {}).get(
                "https://github.com/NousResearch/hermes-agent"
            )
            != revision
            or receipt.get("runtime_lane") != "local-arm64-docker-network-none"
            or receipt.get("run_count") != 2
            or projection.get("restart_persistence_supported") is not True
            or projection.get("session_a_visible_from_fresh_session_b") is not True
            or projection.get("session_scoped_isolation_supported") is not False
            or projection.get("native_session_purge_supported") is not False
        ):
            raise MemoryPortfolioError(
                f"{owner}: Hermes Holographic receipt semantics drifted"
            )
    elif source_id == "hermes-observational-memory":
        revisions = receipt.get("source_revisions", {})
        if (
            receipt.get("evidence_kind")
            != "standalone-hermes-provider-lifecycle-negative"
            or revisions.get(
                "https://github.com/intertwine/hermes-observational-memory"
            )
            != revision
            or revisions.get("https://github.com/intertwine/observational-memory")
            != "6bbc16e81ad1258ee1e8ba37c9efcc6ce36a0208"
            or receipt.get("runtime_lane")
            != "docker-under-slurm-h100-allocation-no-container-gpu"
            or receipt.get("run_count") != 2
            or receipt.get("claim_boundary", {}).get("h100_actor_admission")
            != "forbidden-for-this-revision"
            or receipt.get("claim_boundary", {}).get("native_deletion_evaluated")
            is not True
            or receipt.get("claim_boundary", {}).get(
                "operator_root_deletion_is_native_erasure"
            )
            is not False
        ):
            raise MemoryPortfolioError(
                f"{owner}: Hermes Observational Memory receipt semantics drifted"
            )
    elif source_id == "hermes-byterover-cli":
        projection = receipt.get("stable_projection", {})
        if (
            receipt.get("evidence_kind") != "native-negative-reproduction"
            or receipt.get("source_revisions", {}).get(
                "https://github.com/campfirein/byterover-cli"
            )
            != revision
            or receipt.get("runtime_lane") != "local-arm64-docker-network-none"
            or receipt.get("run_count") != 2
            or projection.get("offline_search_available_under_network_none")
            is not False
            or projection.get("hermes_query_available_under_network_none")
            is not False
            or projection.get("hermes_curate_available_under_network_none")
            is not False
            or projection.get("daemon_network_fatal_reproduced") is not True
        ):
            raise MemoryPortfolioError(
                f"{owner}: Hermes ByteRover receipt semantics drifted"
            )
    elif source_id == "supermemory":
        projection = receipt.get("stable_projection", {})
        if (
            receipt.get("evidence_kind")
            != "binary-only-native-negative-reproduction"
            or receipt.get("source_revisions", {}).get(
                "https://github.com/supermemoryai/supermemory"
            )
            != revision
            or receipt.get("runtime_lane")
            != "local-arm64-docker-network-none"
            or receipt.get("run_count") != 2
            or receipt.get("claim_boundary", {}).get("binary_only") is not True
            or receipt.get("claim_boundary", {}).get("h100_admission")
            != "forbidden-for-this-release"
            or projection.get("restart", {})
            .get("checks", {})
            .get("acknowledged_tenant_a_survives_sigkill")
            is not False
            or projection.get("restart", {})
            .get("checks", {})
            .get("acknowledged_tenant_b_survives_sigkill")
            is not False
        ):
            raise MemoryPortfolioError(
                f"{owner}: Supermemory receipt semantics drifted"
            )
    elif source_id == "hermes-hindsight-native":
        source_revisions = receipt.get("source_revisions", {})
        if (
            receipt.get("evidence_kind") != "native-negative-reproduction"
            or source_revisions.get("https://github.com/vectorize-io/hindsight")
            != revision
            or receipt.get("runtime_lane")
            != "local-arm64-docker-internal-network"
            or receipt.get("run_count") != 2
            or receipt.get("operation_count") != 12
            or receipt.get("residue_file_counts") != [10, 10]
        ):
            raise MemoryPortfolioError(
                f"{owner}: Hermes Hindsight receipt semantics drifted"
            )
    elif source_id == "past-bench" and (
            receipt.get("evidence_kind") != "negative-discovery-decision-receipt"
            or receipt.get("source_revision") != revision
            or receipt.get("report_receipt_sha256")
            != "da6f5966e928787b40e63bff662add5bb06e56a4c0551ce826c17cf1aeb326b8"
            or receipt.get("mismatch_counts")
            != {"pass_fail": 2, "score": 2, "trace": 7}
    ):
        raise MemoryPortfolioError(f"{owner}: PAST receipt semantics drifted")
    return receipt


def _validate_provider_contracts(
    portfolio: dict[str, Any],
    sources: dict[str, dict[str, Any]],
) -> None:
    contracts = portfolio.get("provider_conformance_contracts")
    if not isinstance(contracts, dict) or set(contracts) != {"hermes"}:
        raise MemoryPortfolioError("portfolio: Hermes provider conformance contract is required")
    contract = contracts["hermes"]
    if not isinstance(contract, dict):
        raise MemoryPortfolioError("provider_conformance_contracts.hermes must be a mapping")
    source_id = contract.get("source_id")
    source = sources.get(source_id)
    if source is None or source["evidence_grade"] != "local-conformance-reproduced":
        raise MemoryPortfolioError("Hermes provider contract source or evidence grade drifted")
    expected = {
        "evidence_role": "cpu-provider-contract-only",
        "canonical_generation": "v2",
        "supersedes": "v1-memori-executable-absent",
        "status": "FAIL",
        "scientific_result": False,
        "publication_ready": False,
        "experiment_sha256": "1fd5f7620894fac8a4ecfcc9a56552075920747a8c815ecd8ae8b7c570300c23",
        "provider_roster": HERMES_PROVIDER_ROSTER,
        "failed_groups": ["honcho", "hindsight-strict-timeout-probe"],
        "native_followups": {
            "byterover": {
                "source_id": "hermes-byterover-cli",
                "status": (
                    "BLOCKED_OFFLINE_DAEMON_AND_PORTABLE_SESSION_LIFECYCLE_REPRODUCED"
                ),
                "evidence_path": (
                    "research/evidence/memory/hermes-byterover-offline-v1.json"
                ),
                "evidence_sha256": (
                    "4b51e2f1b63317e7ddaa596d4fb99b0bff16d8d55e5a0147c4c9ce32210ef15a"
                ),
            },
            "holographic": {
                "source_id": "hermes-holographic",
                "status": (
                    "BLOCKED_GLOBAL_SESSION_SCOPE_AND_NATIVE_SESSION_PURGE_REPRODUCED"
                ),
                "evidence_path": (
                    "research/evidence/memory/hermes-holographic-lifecycle-v1.json"
                ),
                "evidence_sha256": (
                    "a532c646f24463a30910959f70c278c816d331a36b79efb1e75980604c31451d"
                ),
            },
            "hindsight": {
                "source_id": "hermes-hindsight-native",
                "status": "BLOCKED_NATIVE_PHYSICAL_PURGE_RESIDUE",
                "evidence_path": (
                    "research/evidence/memory/hermes-hindsight-lifecycle-v1.json"
                ),
                "evidence_sha256": (
                    "68176f77d759be15497203dac3d7e449c609c76507e5d8242af88a2a62064c1b"
                ),
            },
            "openviking": {
                "source_id": "openviking",
                "status": "BLOCKED_NATIVE_PHYSICAL_PURGE_RESIDUE",
                "evidence_path": (
                    "research/evidence/memory/hermes-openviking-lifecycle-v3.json"
                ),
                "evidence_sha256": (
                    "a946df0c072cc168a01fd1ec0c3ed7004b84959587762b03618f5a7ad00eb074"
                ),
            },
        },
    }
    for field, value in expected.items():
        if contract.get(field) != value:
            raise MemoryPortfolioError(f"Hermes provider contract field {field} drifted")
    data = _bound_artifact(
        "provider_conformance_contracts.hermes",
        contract.get("evidence_path"),
        contract.get("evidence_sha256"),
    )
    receipt = source["reproduction_receipt"]
    if (
        contract["evidence_path"] != receipt["artifact_path"]
        or contract["evidence_sha256"] != receipt["receipt_sha256"]
    ):
        raise MemoryPortfolioError("Hermes provider contract differs from source receipt")
    bundle = json.loads(data)
    if (
        bundle.get("source_id") != source_id
        or bundle.get("provider_roster") != HERMES_PROVIDER_ROSTER
        or bundle.get("failed_groups") != expected["failed_groups"]
    ):
        raise MemoryPortfolioError("Hermes provider evidence bundle drifted")
    holographic_contract = contract["native_followups"]["holographic"]
    holographic_source = sources.get("hermes-holographic")
    if (
        holographic_source is None
        or holographic_source.get("evidence_grade") != "local-negative-reproduced"
    ):
        raise MemoryPortfolioError("Hermes Holographic follow-up source drifted")
    holographic_data = _bound_artifact(
        "provider_conformance_contracts.hermes.native_followups.holographic",
        holographic_contract["evidence_path"],
        holographic_contract["evidence_sha256"],
    )
    holographic_receipt = holographic_source["reproduction_receipt"]
    if (
        holographic_contract["evidence_path"]
        != holographic_receipt["artifact_path"]
        or holographic_contract["evidence_sha256"]
        != holographic_receipt["receipt_sha256"]
    ):
        raise MemoryPortfolioError(
            "Hermes Holographic follow-up differs from source receipt"
        )
    _validate_negative_receipt(
        "provider_conformance_contracts.hermes.native_followups.holographic",
        source_id="hermes-holographic",
        revision=holographic_source["repositories"][0]["revision"],
        terminal_status=holographic_contract["status"],
        data=holographic_data,
    )
    byterover_contract = contract["native_followups"]["byterover"]
    byterover_source = sources.get("hermes-byterover-cli")
    if (
        byterover_source is None
        or byterover_source.get("evidence_grade") != "local-negative-reproduced"
    ):
        raise MemoryPortfolioError("Hermes ByteRover follow-up source drifted")
    byterover_data = _bound_artifact(
        "provider_conformance_contracts.hermes.native_followups.byterover",
        byterover_contract["evidence_path"],
        byterover_contract["evidence_sha256"],
    )
    byterover_receipt = byterover_source["reproduction_receipt"]
    if (
        byterover_contract["evidence_path"] != byterover_receipt["artifact_path"]
        or byterover_contract["evidence_sha256"]
        != byterover_receipt["receipt_sha256"]
    ):
        raise MemoryPortfolioError(
            "Hermes ByteRover follow-up differs from source receipt"
        )
    _validate_negative_receipt(
        "provider_conformance_contracts.hermes.native_followups.byterover",
        source_id="hermes-byterover-cli",
        revision=byterover_source["repositories"][0]["revision"],
        terminal_status=byterover_contract["status"],
        data=byterover_data,
    )
    hindsight_contract = contract["native_followups"]["hindsight"]
    hindsight_source = sources.get("hermes-hindsight-native")
    if (
        hindsight_source is None
        or hindsight_source.get("evidence_grade") != "local-negative-reproduced"
    ):
        raise MemoryPortfolioError("Hermes Hindsight follow-up source drifted")
    hindsight_data = _bound_artifact(
        "provider_conformance_contracts.hermes.native_followups.hindsight",
        hindsight_contract["evidence_path"],
        hindsight_contract["evidence_sha256"],
    )
    hindsight_receipt = hindsight_source["reproduction_receipt"]
    if (
        hindsight_contract["evidence_path"]
        != hindsight_receipt["artifact_path"]
        or hindsight_contract["evidence_sha256"]
        != hindsight_receipt["receipt_sha256"]
    ):
        raise MemoryPortfolioError(
            "Hermes Hindsight follow-up differs from source receipt"
        )
    _validate_negative_receipt(
        "provider_conformance_contracts.hermes.native_followups.hindsight",
        source_id="hermes-hindsight-native",
        revision=hindsight_source["repositories"][0]["revision"],
        terminal_status=hindsight_contract["status"],
        data=hindsight_data,
    )
    openviking_contract = contract["native_followups"]["openviking"]
    openviking_source = sources.get("openviking")
    if (
        openviking_source is None
        or openviking_source.get("evidence_grade") != "local-negative-reproduced"
    ):
        raise MemoryPortfolioError("Hermes OpenViking follow-up source drifted")
    openviking_data = _bound_artifact(
        "provider_conformance_contracts.hermes.native_followups.openviking",
        openviking_contract["evidence_path"],
        openviking_contract["evidence_sha256"],
    )
    openviking_receipt = openviking_source["reproduction_receipt"]
    if (
        openviking_contract["evidence_path"]
        != openviking_receipt["artifact_path"]
        or openviking_contract["evidence_sha256"]
        != openviking_receipt["receipt_sha256"]
    ):
        raise MemoryPortfolioError(
            "Hermes OpenViking follow-up differs from source receipt"
        )
    _validate_negative_receipt(
        "provider_conformance_contracts.hermes.native_followups.openviking",
        source_id="openviking",
        revision=openviking_source["repositories"][0]["revision"],
        terminal_status=openviking_contract["status"],
        data=openviking_data,
    )


def _validate_native_lifecycle_contracts(
    portfolio: dict[str, Any],
    sources: dict[str, dict[str, Any]],
) -> None:
    contracts = portfolio.get("native_lifecycle_conformance_contracts")
    if not isinstance(contracts, dict) or set(contracts) != {
        "mem0_lifecycle_adapter",
        "neo4j_agent_memory",
        "supermemory_local_binary",
    }:
        raise MemoryPortfolioError(
            "portfolio: Mem0, Supermemory, and Neo4j native lifecycle contracts are required"
        )
    mem0_contract = contracts["mem0_lifecycle_adapter"]
    if not isinstance(mem0_contract, dict):
        raise MemoryPortfolioError(
            "native_lifecycle_conformance_contracts.mem0_lifecycle_adapter must be a mapping"
        )
    mem0_source = sources.get(mem0_contract.get("source_id"))
    if (
        mem0_source is None
        or mem0_source.get("evidence_grade") != "local-negative-reproduced"
    ):
        raise MemoryPortfolioError("Mem0 lifecycle adapter source or grade drifted")
    mem0_expected = {
        "candidate_source_id": "mem0",
        "evidence_role": "local-arm64-native-lifecycle-adapter-negative",
        "status": "BLOCKED_ADAPTER_CRASH_RECOVERY",
        "scientific_result": False,
        "publication_ready": False,
        "h100_admission": "blocked",
        "runtime_lane": "local-arm64-docker-network-none",
        "source_revision": "71f2ebefa3494da21550fb525216818776cde67f",
        "experiment_sha256": (
            "f9e77ea6997f1bc716240c0ec6416e54cb026a9ae78d5f8ecf479fcef25d5b42"
        ),
        "shared_image_id": (
            "sha256:cf96e7828a1e5d2697617deb3d47fcf467bb04bcf3b041347372779b6ef48f9c"
        ),
        "stable_projection_sha256": (
            "1da1b15e4fba6f2f93b61294c24a6b83a0d6be2acd2e1abf0b3a0b3d49148f98"
        ),
        "next_gate": (
            "Implement and reproduce exact interrupted-operation recovery plus "
            "crash-scope plaintext-residue clearance in two fresh contained runs "
            "before any Slurm or H100 actor cell."
        ),
    }
    for field, value in mem0_expected.items():
        if mem0_contract.get(field) != value:
            raise MemoryPortfolioError(
                f"Mem0 lifecycle adapter contract field {field} drifted"
            )
    mem0_data = _bound_artifact(
        "native_lifecycle_conformance_contracts.mem0_lifecycle_adapter",
        mem0_contract.get("evidence_path"),
        mem0_contract.get("evidence_sha256"),
    )
    mem0_receipt = mem0_source["reproduction_receipt"]
    if (
        mem0_contract["evidence_path"] != mem0_receipt["artifact_path"]
        or mem0_contract["evidence_sha256"] != mem0_receipt["receipt_sha256"]
    ):
        raise MemoryPortfolioError(
            "Mem0 lifecycle adapter contract differs from source receipt"
        )
    mem0_bundle = json.loads(mem0_data)
    if (
        mem0_bundle.get("source_id") != "mem0-lifecycle-adapter"
        or mem0_bundle.get("status") != mem0_expected["status"]
        or mem0_bundle.get("h100_admission") != "blocked"
        or mem0_bundle.get("run_count") != 2
        or mem0_bundle.get("shared_image_id") != mem0_expected["shared_image_id"]
        or mem0_bundle.get("stable_projection_sha256")
        != mem0_expected["stable_projection_sha256"]
        or mem0_bundle.get("scientific_result") is not False
        or mem0_bundle.get("publication_ready") is not False
    ):
        raise MemoryPortfolioError("Mem0 lifecycle adapter evidence bundle drifted")
    supermemory_contract = contracts["supermemory_local_binary"]
    if not isinstance(supermemory_contract, dict):
        raise MemoryPortfolioError(
            "native_lifecycle_conformance_contracts.supermemory_local_binary "
            "must be a mapping"
        )
    supermemory_source = sources.get(supermemory_contract.get("source_id"))
    if (
        supermemory_source is None
        or supermemory_source.get("evidence_grade") != "local-negative-reproduced"
    ):
        raise MemoryPortfolioError("Supermemory source or evidence grade drifted")
    supermemory_expected = {
        "candidate_source_id": "supermemory",
        "evidence_role": "local-arm64-binary-only-native-negative",
        "status": "BLOCKED_ACKNOWLEDGED_WRITES_LOST_ON_SIGKILL",
        "scientific_result": False,
        "publication_ready": False,
        "h100_admission": "blocked",
        "runtime_lane": "local-arm64-docker-network-none",
        "source_revision": "82dae50ef458139823b3bfd3ebaaaac90ffd8a7c",
        "release_revision": "39ef7e1e5ea01b34d2cdd1801d0d227d445a985d",
        "experiment_sha256": (
            "e6b6375de427aefb58f1595cb3d96631924fd89ab1699f8ef688e3fad99593aa"
        ),
        "shared_image_id": (
            "sha256:a08e414b959d30b08e781e985a4a6ab28272ae335002bd63ccae18bca41532fa"
        ),
        "manifest_root_sha256": (
            "938dd87f02aa45f9d3d9441793c6bc47661634812e1734bb683795ff6fe3ae39"
        ),
        "stable_projection_sha256": (
            "8d9f6a55e132099da9b07c9fc32a62fd88b8d04e7cc8f7523ae4d8894c2b72a0"
        ),
        "next_gate": (
            "Do not run the v0.0.3 binary on H100s. Admit only a newer immutable "
            "release or source-auditable patch that preserves acknowledged writes "
            "across SIGKILL in two fresh contained runs and provides a tenant-scoped "
            "physical purge contract."
        ),
    }
    for field, value in supermemory_expected.items():
        if supermemory_contract.get(field) != value:
            raise MemoryPortfolioError(
                f"Supermemory lifecycle contract field {field} drifted"
            )
    supermemory_data = _bound_artifact(
        "native_lifecycle_conformance_contracts.supermemory_local_binary",
        supermemory_contract.get("evidence_path"),
        supermemory_contract.get("evidence_sha256"),
    )
    supermemory_receipt = supermemory_source["reproduction_receipt"]
    if (
        supermemory_contract["evidence_path"]
        != supermemory_receipt["artifact_path"]
        or supermemory_contract["evidence_sha256"]
        != supermemory_receipt["receipt_sha256"]
    ):
        raise MemoryPortfolioError(
            "Supermemory lifecycle contract differs from source receipt"
        )
    supermemory_bundle = json.loads(supermemory_data)
    if (
        supermemory_bundle.get("source_id") != "supermemory"
        or supermemory_bundle.get("status") != supermemory_expected["status"]
        or supermemory_bundle.get("shared_image_id")
        != supermemory_expected["shared_image_id"]
        or supermemory_bundle.get("manifest_root_sha256")
        != supermemory_expected["manifest_root_sha256"]
        or supermemory_bundle.get("claim_boundary", {}).get("h100_admission")
        != "forbidden-for-this-release"
        or supermemory_bundle.get("scientific_result") is not False
        or supermemory_bundle.get("publication_ready") is not False
    ):
        raise MemoryPortfolioError("Supermemory lifecycle evidence bundle drifted")
    contract = contracts["neo4j_agent_memory"]
    if not isinstance(contract, dict):
        raise MemoryPortfolioError(
            "native_lifecycle_conformance_contracts.neo4j_agent_memory must be a mapping"
        )
    source_id = contract.get("source_id")
    source = sources.get(source_id)
    if source is None or source.get("evidence_grade") != "local-conformance-reproduced":
        raise MemoryPortfolioError(
            "Neo4j lifecycle contract source or evidence grade drifted"
        )
    expected = {
        "evidence_role": (
            "local-and-cluster-native-lifecycle-plus-designed-traversal-component"
        ),
        "status": "NEO4J_PREFERENCE_LIFECYCLE_CONFORMANCE_PASS",
        "scientific_result": False,
        "publication_ready": False,
        "runtime_lane": "cluster-amd64-slurm-h100-allocation-no-container-gpu",
        "confirmation_required": False,
        "confirmation_lane": "cluster-amd64-slurm",
        "source_revision": "231d60eac9401ab156ba194b519d89dd644dadb8",
        "experiment_sha256": "8bda38b14edbba0127f452d52ef1a7c46307e20c974d4f3e5f6b139037bc2340",
        "report_sha256": "631bf282c6c8aa8cdbb7db6312518a949a693173fe4b927edfca7151dcddcfeb",
        "manifest_file_sha256": "9b3dfc9995cc1988313670545bbc75debe241238840974504144ea5ab9620b17",
        "manifest_root_sha256": "0bb7d2d5c0d4831f0a3f08401be70f2df57cea7ed88021fb8a3ab6a0972366f6",
        "client_image_id": (
            "sha256:784063f4359191829873f4cc562226c34dbc5da169d0d9141cc6c69dcd4c6d20"
        ),
        "execution_state_roots": [
            "85d9e78ceceeea7f2a2056728078809cfe66f2ee674d423230201a7036f1ad7a",
            "15966d812bdb5ead052568da58a6d192d1ead3528a665a6148ba9eb6d637623f",
        ],
        "cluster_evidence_path": (
            "research/evidence/memory/neo4j-preference-lifecycle-h100-v1.json"
        ),
        "cluster_evidence_sha256": (
            "dfeaf75011c088d9b34c2a803798f4b237499ddbde653e3459350bdcd36b2350"
        ),
        "cluster_job_id": 303,
        "cluster_client_image_id": (
            "sha256:8ec19ef4a4acbbf81205e56148aadfa5e9798d2964175b5b4be8d8644436c382"
        ),
        "component_evidence_path": (
            "research/evidence/memory/"
            "neo4j-identical-tuple-flat-parity-h100-v1.json"
        ),
        "component_evidence_sha256": (
            "e09d16388bf084de41b6f37515befb80f111dcb14249c174292ec57f5faa2b8e"
        ),
        "component_status": "NEO4J_IDENTICAL_TUPLE_TRAVERSAL_COMPONENT_PASS",
        "component_job_id": 304,
        "component_hit_counts": {
            "flat_bm25_dense": 0,
            "zero_traversal": 0,
            "flat_sql_join": 48,
            "true_graph": 48,
            "shuffled_graph": 0,
        },
        "natural_topology_evidence_path": (
            "research/evidence/memory/"
            "longmemeval-natural-session-topology-negative-v1.json"
        ),
        "natural_topology_evidence_sha256": (
            "2d2849d1652f0e9e7dffa66e674f177b7f0a5ac8183fbb455fda34b5aa4d556f"
        ),
        "natural_topology_status": "NATURAL_SESSION_TOPOLOGY_RETRIEVAL_KILLED",
        "natural_topology_recall_all_at_4": {
            "flat_bm25_dense": 0.34375,
            "true_topology": 0.203125,
            "shuffled_topology_seed_42": 0.25,
            "shuffled_topology_seed_43": 0.203125,
            "shuffled_topology_seed_44": 0.21875,
        },
        "natural_topology_true_minus_flat": -0.140625,
        "natural_topology_true_minus_flat_bootstrap_95_ci": [
            -0.234375,
            -0.046875,
        ],
        "lifecycle_h100_admission_at_collection": (
            "blocked-pending-identical-tuple-flat-parity"
        ),
        "h100_admission": "blocked-natural-topology-retrieval-negative",
        "next_gate": (
            "Do not run the proposed Neo4j natural actor screen. On the frozen "
            "64-question LongMemEval update/temporal panel, chronological topology "
            "reduced recall-all@4 by 14.06 points versus flat BM25-dense and did "
            "not beat degree-preserving shuffles. A future actor hypothesis requires "
            "a materially different graph mechanism, a new preregistered contract, "
            "clean source, and complete controls."
        ),
    }
    for field, value in expected.items():
        if contract.get(field) != value:
            raise MemoryPortfolioError(f"Neo4j lifecycle contract field {field} drifted")
    data = _bound_artifact(
        "native_lifecycle_conformance_contracts.neo4j_agent_memory",
        contract.get("evidence_path"),
        contract.get("evidence_sha256"),
    )
    receipt = source["reproduction_receipt"]
    if (
        contract["evidence_path"] != receipt["artifact_path"]
        or contract["evidence_sha256"] != receipt["receipt_sha256"]
    ):
        raise MemoryPortfolioError(
            "Neo4j lifecycle contract differs from source receipt"
        )
    bundle = json.loads(data)
    files = bundle.get("files")
    if not isinstance(files, dict) or set(files) != {
        "experiment.yaml",
        "manifest.json",
        "report.json",
    }:
        raise MemoryPortfolioError("Neo4j lifecycle evidence file roster drifted")
    if (
        bundle.get("source_id") != source_id
        or bundle.get("evidence_kind")
        != "native-lifecycle-conformance-reproduction"
        or bundle.get("status") != expected["status"]
        or bundle.get("runtime_lane") != "local-arm64"
        or bundle.get("confirmation_required") is not True
        or bundle.get("run_count") != 2
        or bundle.get("client_image_id") != expected["client_image_id"]
        or bundle.get("execution_state_roots") != expected["execution_state_roots"]
        or bundle.get("manifest_root_sha256")
        != expected["manifest_root_sha256"]
        or files["experiment.yaml"].get("sha256") != expected["experiment_sha256"]
        or files["report.json"].get("sha256") != expected["report_sha256"]
        or files["manifest.json"].get("sha256")
        != expected["manifest_file_sha256"]
    ):
        raise MemoryPortfolioError("Neo4j lifecycle evidence bundle drifted")
    cluster_receipt = source.get("cluster_confirmation_receipt")
    if (
        not isinstance(cluster_receipt, dict)
        or contract["cluster_evidence_path"]
        != cluster_receipt.get("artifact_path")
        or contract["cluster_evidence_sha256"]
        != cluster_receipt.get("receipt_sha256")
    ):
        raise MemoryPortfolioError(
            "Neo4j cluster lifecycle contract differs from source receipt"
        )
    cluster_data = _bound_artifact(
        "native_lifecycle_conformance_contracts.neo4j_agent_memory.cluster",
        contract.get("cluster_evidence_path"),
        contract.get("cluster_evidence_sha256"),
    )
    cluster_bundle = json.loads(cluster_data)
    if (
        cluster_bundle.get("source_id") != source_id
        or cluster_bundle.get("evidence_kind")
        != "cluster-amd64-lifecycle-confirmation"
        or cluster_bundle.get("status") != expected["status"]
        or cluster_bundle.get("slurm_job_id") != expected["cluster_job_id"]
        or cluster_bundle.get("image_config_digest")
        != expected["cluster_client_image_id"]
        or cluster_bundle.get("scientific_result") is not False
        or cluster_bundle.get("publication_ready") is not False
        or cluster_bundle.get("claim_boundary", {}).get("h100_actor_admission")
        != expected["lifecycle_h100_admission_at_collection"]
    ):
        raise MemoryPortfolioError("Neo4j cluster lifecycle evidence bundle drifted")
    component_receipt = source.get("cluster_component_receipt")
    if (
        not isinstance(component_receipt, dict)
        or contract["component_evidence_path"]
        != component_receipt.get("artifact_path")
        or contract["component_evidence_sha256"]
        != component_receipt.get("receipt_sha256")
    ):
        raise MemoryPortfolioError(
            "Neo4j traversal component differs from source receipt"
        )
    component_data = _bound_artifact(
        "native_lifecycle_conformance_contracts.neo4j_agent_memory.component",
        contract.get("component_evidence_path"),
        contract.get("component_evidence_sha256"),
    )
    component_bundle = json.loads(component_data)
    if (
        component_bundle.get("source_id") != source_id
        or component_bundle.get("study")
        != "neo4j-identical-tuple-flat-parity-v1"
        or component_bundle.get("status") != expected["component_status"]
        or component_bundle.get("slurm_job_id") != expected["component_job_id"]
        or component_bundle.get("component", {}).get("hit_counts")
        != expected["component_hit_counts"]
        or component_bundle.get("scientific_result") is not False
        or component_bundle.get("publication_ready") is not False
        or component_bundle.get("container_gpu_count") != 0
        or component_bundle.get("model_calls") != 0
    ):
        raise MemoryPortfolioError("Neo4j traversal component evidence drifted")
    natural_source = sources.get("longmemeval-natural-session-topology")
    if (
        not isinstance(natural_source, dict)
        or natural_source.get("evidence_grade") != "local-negative-reproduced"
    ):
        raise MemoryPortfolioError("natural topology negative source drifted")
    natural_receipt = natural_source.get("reproduction_receipt")
    if (
        not isinstance(natural_receipt, dict)
        or contract["natural_topology_evidence_path"]
        != natural_receipt.get("artifact_path")
        or contract["natural_topology_evidence_sha256"]
        != natural_receipt.get("receipt_sha256")
    ):
        raise MemoryPortfolioError("natural topology negative differs from source receipt")
    natural_data = _bound_artifact(
        "native_lifecycle_conformance_contracts.neo4j_agent_memory.natural_topology",
        contract.get("natural_topology_evidence_path"),
        contract.get("natural_topology_evidence_sha256"),
    )
    natural_bundle = json.loads(natural_data)
    if (
        natural_bundle.get("status") != expected["natural_topology_status"]
        or natural_bundle.get("result", {}).get("recall_all_at_4")
        != expected["natural_topology_recall_all_at_4"]
        or natural_bundle.get("result", {}).get("true_minus_flat")
        != expected["natural_topology_true_minus_flat"]
        or natural_bundle.get("result", {}).get("true_minus_flat_bootstrap_95_ci")
        != expected["natural_topology_true_minus_flat_bootstrap_95_ci"]
        or natural_bundle.get("h100_actor_admission") != "forbidden"
        or natural_bundle.get("scientific_result") is not False
        or natural_bundle.get("publication_ready") is not False
    ):
        raise MemoryPortfolioError("natural topology negative evidence drifted")


def _validate_killed_revisions(
    portfolio: dict[str, Any],
    sources: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    records = portfolio.get("killed_revisions")
    if not isinstance(records, list) or not records:
        raise MemoryPortfolioError("portfolio: killed_revisions must be non-empty")
    by_source: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(records):
        owner = f"killed_revisions[{index}]"
        if not isinstance(record, dict):
            raise MemoryPortfolioError(f"{owner} must be a mapping")
        source_id = _text(owner, record.get("source_id"), "source_id")
        if source_id in by_source or source_id not in sources:
            raise MemoryPortfolioError(f"{owner}: source_id is duplicate or unknown")
        source_aliases = record.get("source_aliases", [])
        expected_aliases = (
            ["graphiti"]
            if source_id == "graphiti-native-lifecycle-adapter"
            else []
        )
        if source_aliases != expected_aliases:
            raise MemoryPortfolioError(f"{owner}: killed source aliases drifted")
        revision = _text(owner, record.get("repository_revision"), "repository_revision")
        if revision not in {
            repository["revision"] for repository in sources[source_id].get("repositories", [])
        }:
            raise MemoryPortfolioError(f"{owner}: killed revision is not in the source ledger")
        expected_status = NEGATIVE_TERMINAL_STATUSES.get(source_id)
        if expected_status is None or record.get("terminal_status") != expected_status:
            raise MemoryPortfolioError(f"{owner}: killed terminal status drifted")
        source_pairs = {
            (repository["url"].rstrip("/"), repository["revision"])
            for repository in sources[source_id].get("repositories", [])
        }
        for alias in source_aliases:
            if alias not in sources or alias == source_id:
                raise MemoryPortfolioError(f"{owner}: killed source alias is invalid")
            alias_pairs = {
                (repository["url"].rstrip("/"), repository["revision"])
                for repository in sources[alias].get("repositories", [])
            }
            if not any(
                pair in alias_pairs and pair[1] == revision for pair in source_pairs
            ):
                raise MemoryPortfolioError(
                    f"{owner}: killed source alias does not bind the same repository revision"
                )
        evidence = _bound_artifact(
            owner, record.get("evidence_path"), record.get("evidence_sha256")
        )
        _validate_negative_receipt(
            owner,
            source_id=source_id,
            revision=revision,
            terminal_status=expected_status,
            data=evidence,
        )
        if source_id in {
            "activegraph-event-sourced-runtime",
            "agenticow",
            "astra-working-set",
            "all-mem",
            "graphiti-native-lifecycle-adapter",
            "hermes-byterover-cli",
            "hermes-holographic",
            "hippo-memory",
            "icarus-memory-infra",
            "langmem",
            "lightmem",
            "lightmem2",
            "magic-context",
            "memorybank-siliconfriend",
            "mnemon",
            "mnemosyne-oss",
            "openviking",
            "palimpsest-bitemporal-memory",
            "recmem",
            "supermemory",
            "timem",
            "tokenmizer",
            "total-recall-oss",
        }:
            receipt = sources[source_id]["reproduction_receipt"]
            if (
                record["evidence_path"] != receipt["artifact_path"]
                or record["evidence_sha256"] != receipt["receipt_sha256"]
            ):
                raise MemoryPortfolioError(f"{owner}: killed evidence differs from source receipt")
        by_source[source_id] = record
    return by_source


def assert_revision_admitted(
    portfolio: dict[str, Any], source_id: str, revision: str
) -> None:
    """Fail when a job tries to re-admit a revision with sealed negative evidence."""

    for contract in portfolio.get("native_lifecycle_conformance_contracts", {}).values():
        if (
            isinstance(contract, dict)
            and source_id
            in {
                contract.get("candidate_source_id"),
                contract.get("source_id"),
            }
            and revision
            in {
                contract.get("source_revision"),
                contract.get("release_revision"),
            }
            and contract.get("h100_admission") == "blocked"
        ):
            raise MemoryPortfolioError(
                f"{source_id}@{revision} is blocked by {contract.get('status')}"
            )
    for record in portfolio.get("killed_revisions", []):
        if (
            source_id
            in {
                record.get("source_id"),
                *record.get("source_aliases", []),
            }
            and record.get("repository_revision") == revision
        ):
            raise MemoryPortfolioError(
                f"{source_id}@{revision} is blocked by {record.get('terminal_status')}"
            )


def _blocked_lifecycle_contract(
    portfolio: dict[str, Any],
    sources: dict[str, dict[str, Any]],
    *,
    source_id: str,
    revision: str | None,
    repository: tuple[str, str] | None,
) -> dict[str, Any] | None:
    """Resolve a blocked lifecycle contract through direct or repository aliases."""

    for contract in portfolio.get("native_lifecycle_conformance_contracts", {}).values():
        if not isinstance(contract, dict) or contract.get("h100_admission") != "blocked":
            continue
        blocked_source_ids = {
            candidate
            for candidate in (
                contract.get("candidate_source_id"),
                contract.get("source_id"),
            )
            if isinstance(candidate, str)
        }
        blocked_revisions = {
            candidate
            for candidate in (
                contract.get("source_revision"),
                contract.get("release_revision"),
            )
            if isinstance(candidate, str)
        }
        if source_id in blocked_source_ids and (
            revision is None or revision in blocked_revisions
        ):
            return contract
        if repository is None or repository[1] not in blocked_revisions:
            continue
        blocked_urls = {
            repo["url"].rstrip("/")
            for blocked_source_id in blocked_source_ids
            if blocked_source_id in sources
            for repo in sources[blocked_source_id].get("repositories", [])
            if isinstance(repo, dict) and isinstance(repo.get("url"), str)
        }
        if repository[0] in blocked_urls:
            return contract
    return None


def load_and_validate_portfolio(
    path: Path = DEFAULT_PORTFOLIO,
    *,
    ledger_path: Path = DEFAULT_LEDGER,
) -> dict[str, Any]:
    portfolio = load_unique_yaml(path)
    if not isinstance(portfolio, dict) or portfolio.get("schema_version") != 1:
        raise MemoryPortfolioError("portfolio must be a schema_version: 1 mapping")
    verified_at = _text("portfolio", portfolio.get("verified_at"), "verified_at")
    if not DATE_RE.fullmatch(verified_at):
        raise MemoryPortfolioError("portfolio: verified_at must use YYYY-MM-DD")
    declared_ledger = Path(_text("portfolio", portfolio.get("ledger"), "ledger"))
    if declared_ledger.is_absolute() or ".." in declared_ledger.parts:
        raise MemoryPortfolioError("portfolio: ledger path must be safe and relative")
    if (PROJECT_ROOT / declared_ledger).resolve() != ledger_path.resolve():
        raise MemoryPortfolioError("portfolio: declared ledger differs from validator input")
    rules = portfolio.get("selection_rules")
    if not isinstance(rules, list) or not rules or not all(
        isinstance(rule, str) and rule.strip() for rule in rules
    ):
        raise MemoryPortfolioError("portfolio: selection_rules must be non-empty strings")

    ledger = load_and_validate(ledger_path)
    matrix = compile_landscape(ledger)
    if portfolio.get("matrix_sha256") != matrix["matrix_sha256"]:
        raise MemoryPortfolioError("portfolio: matrix_sha256 differs from live source matrix")
    rows = {row["source_id"]: row for row in matrix["rows"]}
    sources = ledger["sources"]
    _validate_provider_contracts(portfolio, sources)
    _validate_native_lifecycle_contracts(portfolio, sources)
    killed_revisions = _validate_killed_revisions(portfolio, sources)
    waves = portfolio.get("waves")
    if not isinstance(waves, list) or not waves:
        raise MemoryPortfolioError("portfolio: waves must be a non-empty list")

    wave_ids: set[str] = set()
    candidate_count = 0
    blocked_count = 0
    wave_gpu_hour_total = 0.0
    killed_candidates_seen: set[str] = set()
    for wave_index, wave in enumerate(waves):
        owner = f"waves[{wave_index}]"
        if not isinstance(wave, dict):
            raise MemoryPortfolioError(f"{owner} must be a mapping")
        wave_id = _text(owner, wave.get("id"), "id")
        if not ID_RE.fullmatch(wave_id) or wave_id in wave_ids:
            raise MemoryPortfolioError(f"{owner}: id must be unique kebab-case")
        wave_ids.add(wave_id)
        _text(owner, wave.get("objective"), "objective")
        compute_class = _text(owner, wave.get("compute_class"), "compute_class")
        if compute_class not in COMPUTE_CLASSES:
            raise MemoryPortfolioError(f"{owner}: unsupported compute_class")
        execution_order: list[str] | None = None
        execution_capacity = 0
        if compute_class == "contained-h100-screen":
            if wave.get("containment") != "docker-under-slurm":
                raise MemoryPortfolioError(f"{owner}: H100 screens require docker-under-slurm")
            if wave.get("gpu_sku") != "H100":
                raise MemoryPortfolioError(f"{owner}: H100 screens require gpu_sku H100")
            ceiling = wave.get("max_gpu_hours_per_candidate")
            if (
                not isinstance(ceiling, (int, float))
                or isinstance(ceiling, bool)
                or not math.isfinite(ceiling)
                or not 0 < ceiling <= 8
            ):
                raise MemoryPortfolioError(f"{owner}: invalid H100 GPU-hour ceiling")
            if wave.get("checkpoint_required") is not True:
                raise MemoryPortfolioError(f"{owner}: H100 screens require checkpoints")
            if wave.get("h100_admission") != "cpu-doctor-pass-required":
                raise MemoryPortfolioError(
                    f"{owner}: H100 candidates require a CPU-doctor admission gate"
                )
            wave_ceiling = wave.get("max_wave_gpu_hours")
            if (
                not isinstance(wave_ceiling, (int, float))
                or isinstance(wave_ceiling, bool)
                or not math.isfinite(wave_ceiling)
                or not 0 < wave_ceiling <= 64
            ):
                raise MemoryPortfolioError(f"{owner}: invalid wave GPU-hour ceiling")
            wave_gpu_hour_total += float(wave_ceiling)
            execution_capacity = int(float(wave_ceiling) // float(ceiling))
            execution_order_raw = wave.get("execution_order")
            if (
                not isinstance(execution_order_raw, list)
                or not all(isinstance(item, str) and item for item in execution_order_raw)
                or len(set(execution_order_raw)) != len(execution_order_raw)
            ):
                raise MemoryPortfolioError(
                    f"{owner}: execution_order must contain unique source IDs"
                )
            execution_order = execution_order_raw
            failed_ceiling = wave.get("stop_after_failed_candidates")
            if not isinstance(failed_ceiling, int) or isinstance(failed_ceiling, bool):
                raise MemoryPortfolioError(f"{owner}: invalid failed-candidate stop")
            if not 1 <= failed_ceiling <= 3:
                raise MemoryPortfolioError(f"{owner}: invalid failed-candidate stop")

        candidates = wave.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise MemoryPortfolioError(f"{owner}: candidates must be non-empty")
        seen_in_wave: set[str] = set()
        candidate_by_id: dict[str, dict[str, Any]] = {}
        candidate_revision_by_id: dict[str, str] = {}
        candidate_repository_by_id: dict[str, tuple[str, str]] = {}
        for candidate_index, candidate in enumerate(candidates):
            candidate_owner = f"{owner}.candidates[{candidate_index}]"
            if not isinstance(candidate, dict):
                raise MemoryPortfolioError(f"{candidate_owner} must be a mapping")
            source_id = _text(candidate_owner, candidate.get("source_id"), "source_id")
            if source_id not in rows:
                raise MemoryPortfolioError(f"{candidate_owner}: unknown source_id {source_id}")
            if source_id in seen_in_wave:
                raise MemoryPortfolioError(f"{candidate_owner}: duplicate source in wave")
            seen_in_wave.add(source_id)
            candidate_by_id[source_id] = candidate
            mode = _text(candidate_owner, candidate.get("mode"), "mode")
            status = _text(candidate_owner, candidate.get("status"), "status")
            priority = _text(candidate_owner, candidate.get("priority"), "priority")
            if mode not in MODES or status not in STATUSES or priority not in PRIORITIES:
                raise MemoryPortfolioError(f"{candidate_owner}: invalid mode/status/priority")
            if source_id in killed_revisions:
                if status != "discovery-killed":
                    raise MemoryPortfolioError(
                        f"{candidate_owner}: killed revision cannot be relabelled or re-admitted"
                    )
                killed_candidates_seen.add(source_id)
            if mode == "collision-reference" and priority != "boundary":
                raise MemoryPortfolioError(
                    f"{candidate_owner}: collision-reference must use boundary priority"
                )
            _text(candidate_owner, candidate.get("scientific_role"), "scientific_role")
            _text(candidate_owner, candidate.get("next_gate"), "next_gate")

            row = rows[source_id]
            if mode in {
                "benchmark-adapter",
                "blocked-data",
                "blocked-license",
                "contained-import",
            }:
                role = _text(candidate_owner, candidate.get("repository_role"), "repository_role")
                matching = [repo for repo in row["repositories"] if repo["role"] == role]
                if len(matching) != 1:
                    raise MemoryPortfolioError(
                        f"{candidate_owner}: repository_role must resolve exactly once"
                    )
                revision = matching[0].get("revision")
                if not isinstance(revision, str) or not re.fullmatch(
                    r"[0-9a-f]{40}", revision
                ):
                    raise MemoryPortfolioError(
                        f"{candidate_owner}: repository revision must be immutable"
                    )
                candidate_revision_by_id[source_id] = revision
                candidate_repository_by_id[source_id] = (
                    matching[0]["url"].rstrip("/"),
                    revision,
                )
                is_unresolved = matching[0]["license"] == "unresolved"
                if mode == "blocked-license":
                    if not is_unresolved or status != "blocked":
                        raise MemoryPortfolioError(
                            f"{candidate_owner}: blocked-license must bind "
                            "unresolved code and blocked status"
                        )
                    if candidate.get("blocked_by") != "unresolved-license":
                        raise MemoryPortfolioError(
                            f"{candidate_owner}: blocked-license requires blocked_by"
                        )
                    blocked_count += 1
                elif mode == "blocked-data":
                    if is_unresolved or status != "blocked":
                        raise MemoryPortfolioError(
                            f"{candidate_owner}: blocked-data requires licensed code "
                            "and blocked status"
                        )
                    if candidate.get("blocked_by") != "unresolved-data-rights":
                        raise MemoryPortfolioError(
                            f"{candidate_owner}: blocked-data requires unresolved data rights"
                        )
                elif is_unresolved:
                    raise MemoryPortfolioError(
                        f"{candidate_owner}: executable mode cannot reuse unresolved-license code"
                    )
            if mode == "paper-reimplementation" and candidate.get("repository_role"):
                raise MemoryPortfolioError(
                    f"{candidate_owner}: paper-reimplementation cannot bind upstream code"
                )
            if source_id == "gbrain":
                source = sources[source_id]
                receipt = source.get("reproduction_receipt")
                if (
                    status != "source-admission-blocked"
                    or source.get("evidence_grade") != "local-conformance-reproduced"
                    or not isinstance(receipt, dict)
                    or candidate.get("evidence_path") != receipt.get("artifact_path")
                    or candidate.get("evidence_sha256") != receipt.get("receipt_sha256")
                ):
                    raise MemoryPortfolioError(
                        f"{candidate_owner}: GBrain conformance differs from source receipt"
                    )
                evidence = _bound_artifact(
                    f"{candidate_owner}.gbrain_conformance",
                    candidate.get("evidence_path"),
                    candidate.get("evidence_sha256"),
                )
                try:
                    payload = json.loads(evidence)
                    if not isinstance(payload, dict):
                        raise TypeError
                    validate_gbrain_brainbench_evidence(
                        payload,
                        project_root=PROJECT_ROOT,
                    )
                except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as exc:
                    raise MemoryPortfolioError(
                        f"{candidate_owner}: GBrain conformance evidence is invalid JSON"
                    ) from exc
                except GBrainEvidenceError as exc:
                    raise MemoryPortfolioError(f"{candidate_owner}: {exc}") from exc
            if status == "natural-retrieval-component-passed":
                source = sources[source_id]
                receipt = source.get("reproduction_receipt")
                if (
                    source_id != "gaama"
                    or source.get("evidence_grade") != "local-conformance-reproduced"
                    or not isinstance(receipt, dict)
                    or candidate.get("evidence_path") != receipt.get("artifact_path")
                    or candidate.get("evidence_sha256") != receipt.get("receipt_sha256")
                ):
                    raise MemoryPortfolioError(
                        f"{candidate_owner}: natural component differs from source receipt"
                    )
                evidence = _bound_artifact(
                    f"{candidate_owner}.natural_component",
                    candidate.get("evidence_path"),
                    candidate.get("evidence_sha256"),
                )
                bundle = json.loads(evidence)
                if (
                    bundle.get("source_id") != source_id
                    or bundle.get("evidence_kind")
                    != "natural-heldout-component-reproduction"
                    or bundle.get("status") != "GAAMA_NATURAL_GRAPH_PASS"
                    or bundle.get("scientific_result") is not False
                    or bundle.get("publication_ready") is not False
                    or bundle.get("run_count") != 2
                ):
                    raise MemoryPortfolioError(
                        f"{candidate_owner}: natural component evidence drifted"
                    )
            if status == "cpu-retrieval-reproduced":
                source = sources[source_id]
                receipt = source.get("reproduction_receipt")
                if (
                    source_id != "fidelis"
                    or source.get("evidence_grade") != "local-reproduced"
                    or not isinstance(receipt, dict)
                    or candidate.get("evidence_path") != receipt.get("artifact_path")
                    or candidate.get("evidence_sha256") != receipt.get("receipt_sha256")
                ):
                    raise MemoryPortfolioError(
                        f"{candidate_owner}: CPU retrieval evidence differs from source receipt"
                    )
                evidence = _bound_artifact(
                    f"{candidate_owner}.cpu_retrieval",
                    candidate.get("evidence_path"),
                    candidate.get("evidence_sha256"),
                )
                try:
                    payload = json.loads(evidence)
                    if not isinstance(payload, dict):
                        raise TypeError
                    validate_fidelis_zero_llm_evidence(payload)
                except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as exc:
                    raise MemoryPortfolioError(
                        f"{candidate_owner}: CPU retrieval evidence is invalid JSON"
                    ) from exc
                except FidelisEvidenceError as exc:
                    raise MemoryPortfolioError(f"{candidate_owner}: {exc}") from exc
            if status == "artifact-audited-not-reproduced":
                source = sources[source_id]
                receipt = source.get("reproduction_receipt")
                if (
                    source_id not in {"sodamem", "sage-wiki", "memforest"}
                    or source.get("evidence_grade") != "local-artifact-audited"
                    or not isinstance(receipt, dict)
                    or candidate.get("evidence_path") != receipt.get("artifact_path")
                    or candidate.get("evidence_sha256") != receipt.get("receipt_sha256")
                ):
                    raise MemoryPortfolioError(
                        f"{candidate_owner}: artifact audit differs from source receipt"
                    )
                evidence = _bound_artifact(
                    f"{candidate_owner}.artifact_audit",
                    candidate.get("evidence_path"),
                    candidate.get("evidence_sha256"),
                )
                try:
                    payload = json.loads(evidence)
                    if not isinstance(payload, dict):
                        raise TypeError
                    if source_id == "sodamem":
                        validate_sodamem_artifact_evidence(
                            payload, project_root=PROJECT_ROOT
                        )
                    elif source_id == "sage-wiki":
                        validate_sage_wiki_artifact_evidence(
                            payload, project_root=PROJECT_ROOT
                        )
                    else:
                        validate_memforest_artifact_evidence(
                            payload, project_root=PROJECT_ROOT
                        )
                except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as exc:
                    raise MemoryPortfolioError(
                        f"{candidate_owner}: artifact audit evidence is invalid JSON"
                    ) from exc
                except SodaMemArtifactEvidenceError as exc:
                    raise MemoryPortfolioError(f"{candidate_owner}: {exc}") from exc
                except SageWikiArtifactEvidenceError as exc:
                    raise MemoryPortfolioError(f"{candidate_owner}: {exc}") from exc
                except MemForestArtifactEvidenceError as exc:
                    raise MemoryPortfolioError(f"{candidate_owner}: {exc}") from exc
            if status == "actor-translation-killed":
                source = sources[source_id]
                receipt = source.get("reproduction_receipt")
                if (
                    source_id != "gaama"
                    or source.get("evidence_grade") != "local-negative-reproduced"
                    or not isinstance(receipt, dict)
                    or candidate.get("evidence_path") != receipt.get("artifact_path")
                    or candidate.get("evidence_sha256") != receipt.get("receipt_sha256")
                ):
                    raise MemoryPortfolioError(
                        f"{candidate_owner}: actor negative differs from source receipt"
                    )
                evidence = _bound_artifact(
                    f"{candidate_owner}.actor_negative",
                    candidate.get("evidence_path"),
                    candidate.get("evidence_sha256"),
                )
                bundle = json.loads(evidence)
                if (
                    bundle.get("source_id") != source_id
                    or bundle.get("evidence_kind")
                    != "h100-actor-translation-negative"
                    or bundle.get("status") != "GAAMA_H100_ACTOR_KILLED"
                    or bundle.get("scientific_result") is not False
                    or bundle.get("publication_ready") is not False
                    or bundle.get("claim_boundary", {}).get(
                        "gaama_larger_model_admission"
                    )
                    != "forbidden-by-registered-kill-screen"
                ):
                    raise MemoryPortfolioError(
                        f"{candidate_owner}: actor negative evidence drifted"
                    )
            if status == "natural-topology-escalation-killed":
                natural_source = sources.get("longmemeval-natural-session-topology")
                receipt = (
                    natural_source.get("reproduction_receipt")
                    if isinstance(natural_source, dict)
                    else None
                )
                if (
                    source_id != "neo4j-agent-memory"
                    or not isinstance(receipt, dict)
                    or candidate.get("evidence_path") != receipt.get("artifact_path")
                    or candidate.get("evidence_sha256") != receipt.get("receipt_sha256")
                ):
                    raise MemoryPortfolioError(
                        f"{candidate_owner}: topology negative differs from source receipt"
                    )
                evidence = _bound_artifact(
                    f"{candidate_owner}.natural_topology_negative",
                    candidate.get("evidence_path"),
                    candidate.get("evidence_sha256"),
                )
                bundle = json.loads(evidence)
                if (
                    bundle.get("status")
                    != "NATURAL_SESSION_TOPOLOGY_RETRIEVAL_KILLED"
                    or bundle.get("h100_actor_admission") != "forbidden"
                    or bundle.get("scientific_result") is not False
                    or bundle.get("publication_ready") is not False
                ):
                    raise MemoryPortfolioError(
                        f"{candidate_owner}: topology negative evidence drifted"
                    )
            if status == "discovery-killed":
                negative = candidate.get("negative_evidence")
                if not isinstance(negative, dict):
                    raise MemoryPortfolioError(
                        f"{candidate_owner}: discovery-killed requires negative_evidence"
                    )
                artifact_sha256 = negative.get("artifact_sha256")
                receipt_sha256 = negative.get("receipt_sha256")
                receipt_path = negative.get("receipt_path")
                artifact_path = negative.get("artifact_path")
                terminal_status = negative.get("status")
                if not isinstance(artifact_sha256, str) or not re.fullmatch(
                    r"[0-9a-f]{64}", artifact_sha256
                ):
                    raise MemoryPortfolioError(
                        f"{candidate_owner}: invalid negative artifact SHA-256"
                    )
                if not isinstance(receipt_sha256, str) or not re.fullmatch(
                    r"[0-9a-f]{64}", receipt_sha256
                ):
                    raise MemoryPortfolioError(
                        f"{candidate_owner}: invalid negative receipt SHA-256"
                    )
                if (
                    not isinstance(artifact_path, str)
                    or Path(artifact_path).is_absolute()
                    or ".." in Path(artifact_path).parts
                ):
                    raise MemoryPortfolioError(
                        f"{candidate_owner}: invalid negative artifact path"
                    )
                artifact = PROJECT_ROOT / artifact_path
                if not artifact.is_file() or artifact.is_symlink():
                    raise MemoryPortfolioError(
                        f"{candidate_owner}: negative artifact is missing"
                    )
                artifact_bytes = artifact.read_bytes()
                if hashlib.sha256(artifact_bytes).hexdigest() != artifact_sha256:
                    raise MemoryPortfolioError(
                        f"{candidate_owner}: negative artifact SHA-256 drifted"
                    )
                expected_terminal = NEGATIVE_TERMINAL_STATUSES.get(source_id)
                if expected_terminal is None or terminal_status != expected_terminal:
                    raise MemoryPortfolioError(
                        f"{candidate_owner}: negative terminal status drifted"
                    )
                if receipt_path is None:
                    raise MemoryPortfolioError(
                        f"{candidate_owner}: negative receipt_path is required"
                    )
                receipt_bytes = _bound_artifact(
                    f"{candidate_owner}.negative_evidence",
                    receipt_path,
                    receipt_sha256,
                )
                repositories = sources[source_id].get("repositories", [])
                if not repositories:
                    raise MemoryPortfolioError(
                        f"{candidate_owner}: killed source lacks a repository revision"
                    )
                _validate_negative_receipt(
                    f"{candidate_owner}.negative_evidence",
                    source_id=source_id,
                    revision=repositories[0]["revision"],
                    terminal_status=terminal_status,
                    data=receipt_bytes,
                )
            if source_id == "mnemon" and status != "discovery-killed":
                admission = candidate.get("admission_evidence")
                source = sources[source_id]
                source_receipt = source.get("reproduction_receipt")
                if not isinstance(admission, dict) or not isinstance(
                    source_receipt, dict
                ):
                    raise MemoryPortfolioError(
                        f"{candidate_owner}: Mnemon requires bound admission_evidence"
                    )
                if (
                    admission.get("receipt_path")
                    != source_receipt.get("artifact_path")
                    or admission.get("receipt_sha256")
                    != source_receipt.get("receipt_sha256")
                    or admission.get("status")
                    != "ADMITTED_STATIC_ACTIVE_SPACE_CONTROL_WITH_SOFT_DELETE_BOUNDARY"
                ):
                    raise MemoryPortfolioError(
                        f"{candidate_owner}: Mnemon admission differs from source receipt"
                    )
                evidence_bytes = _bound_artifact(
                    f"{candidate_owner}.admission_evidence",
                    admission.get("receipt_path"),
                    admission.get("receipt_sha256"),
                )
                evidence = json.loads(evidence_bytes)
                claim_boundary = evidence.get("claim_boundary")
                if (
                    evidence.get("source_id") != "mnemon"
                    or evidence.get("evidence_kind") != "native-control-admission"
                    or evidence.get("evidence_grade")
                    != "local-conformance-reproduced"
                    or evidence.get("status") != admission.get("status")
                    or evidence.get("scientific_result") is not False
                    or evidence.get("publication_ready") is not False
                    or evidence.get("h100_admission")
                    != "bounded-static-selection-cell-only"
                    or not isinstance(claim_boundary, dict)
                    or claim_boundary.get("learned_bidirectional_paging_demonstrated")
                    is not False
                    or claim_boundary.get("access_control_demonstrated") is not False
                    or claim_boundary.get("item_physical_erasure_demonstrated")
                    is not False
                ):
                    raise MemoryPortfolioError(
                        f"{candidate_owner}: Mnemon admission evidence drifted"
                    )
            candidate_count += 1

        if execution_order is not None:
            executable_sources = {
                source_id
                for source_id, candidate in candidate_by_id.items()
                if candidate["mode"] not in {"blocked-license", "collision-reference"}
                and candidate["mode"] != "blocked-data"
                and candidate["status"]
                not in {
                    "blocked",
                    "actor-translation-killed",
                    "natural-topology-escalation-killed",
                    "cpu-lifecycle-blocked",
                    "discovery-killed",
                    "source-admission-blocked",
                    "artifact-audited-not-reproduced",
                }
            }
            for source_id in sorted(executable_sources):
                revision = candidate_revision_by_id.get(source_id)
                repository = candidate_repository_by_id.get(source_id)
                blocked_contract = _blocked_lifecycle_contract(
                    portfolio,
                    sources,
                    source_id=source_id,
                    revision=revision,
                    repository=repository,
                )
                if blocked_contract is not None:
                    raise MemoryPortfolioError(
                        f"{source_id} is blocked by {blocked_contract.get('status')} "
                        "until an executable candidate binds a different immutable revision"
                    )
                if revision is not None:
                    assert_revision_admitted(portfolio, source_id, revision)
            if set(execution_order) != executable_sources:
                raise MemoryPortfolioError(
                    f"{owner}: execution_order must rank every executable candidate exactly once"
                )
            first_wave = execution_order[:execution_capacity]
            if any(candidate_by_id[source_id]["priority"] != "primary" for source_id in first_wave):
                raise MemoryPortfolioError(
                    f"{owner}: first budget-feasible candidates must have primary priority"
                )

    if killed_candidates_seen != set(killed_revisions):
        raise MemoryPortfolioError(
            "portfolio: every killed revision must remain a discovery-killed candidate"
        )

    portfolio_ceiling = portfolio.get("portfolio_max_gpu_hours")
    if (
        not isinstance(portfolio_ceiling, (int, float))
        or isinstance(portfolio_ceiling, bool)
        or not math.isfinite(portfolio_ceiling)
        or float(portfolio_ceiling) != wave_gpu_hour_total
    ):
        raise MemoryPortfolioError(
            "portfolio: portfolio_max_gpu_hours must equal the finite wave ceilings"
        )

    return {
        "schema_version": 1,
        "verified_at": verified_at,
        "matrix_sha256": matrix["matrix_sha256"],
        "wave_count": len(waves),
        "candidate_count": candidate_count,
        "blocked_license_candidate_count": blocked_count,
        "portfolio_max_gpu_hours": portfolio_ceiling,
        "portfolio": portfolio,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--portfolio", type=Path, default=DEFAULT_PORTFOLIO)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    args = parser.parse_args()
    result = load_and_validate_portfolio(args.portfolio, ledger_path=args.ledger)
    print(
        "memory experiment portfolio PASS: "
        f'{result["wave_count"]} waves, {result["candidate_count"]} candidates, '
        f'{result["blocked_license_candidate_count"]} license-blocked candidates, '
        f'{result["portfolio_max_gpu_hours"]} maximum GPU-hours, '
        f'matrix {result["matrix_sha256"]}'
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
