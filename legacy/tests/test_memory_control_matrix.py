from __future__ import annotations

import hashlib
from collections.abc import Sequence
from pathlib import Path

import pytest

from harness.memory_trials import (
    DenseBGERetrievalMemorySystem,
    DenseEmbeddingIdentity,
    FrozenMemorySystem,
    GeneratedMemoryTaskSource,
    InProcessDenseEmbeddingClient,
    MemoryBudget,
    task_manifest_sha256,
)
from scripts.freeze_memory_control_matrix import freeze_control_matrix


class _MatrixEncoder:
    dimensions = 384
    maximum_tokens = 512
    pooling_strategy = "cls-l2-normalized-v1"

    def embed(self, texts: Sequence[str]) -> tuple[list[list[float]], int]:
        return [[1.0, *([0.0] * 383)] for _ in texts], len(texts)


def _dense_system() -> DenseBGERetrievalMemorySystem:
    identity = DenseEmbeddingIdentity(
        artifact_root_sha256="a" * 64,
        model_receipt_sha256="b" * 64,
    )
    return DenseBGERetrievalMemorySystem(
        InProcessDenseEmbeddingClient(_MatrixEncoder(), identity)
    )


def test_control_matrix_freezes_one_exact_source_atomically(tmp_path: Path) -> None:
    source = GeneratedMemoryTaskSource(
        seed=7,
        episode_count=8,
        budget=MemoryBudget(active_slots=4, retrieval_top_k=4),
    )
    output = tmp_path / "matrix"
    manifest = freeze_control_matrix(
        output,
        source=source,
        system_ids=(
            "no-memory",
            "lru",
            "bm25",
            "raw-log-rrf",
            "profile-expansion",
            "reference",
        ),
    )
    assert manifest["status"] == "FROZEN_CONTROL_MATRIX"
    assert manifest["scientific_result"] is False
    assert manifest["event_kind_counts"]["access"] == 2
    assert manifest["task_source"]["task_manifest_sha256"] == task_manifest_sha256(
        source
    )
    controls = {item["control_id"]: item for item in manifest["controls"]}
    assert controls["lru"]["eligible_for_primary"] is True
    assert controls["raw-log-rrf"]["eligible_for_primary"] is True
    assert controls["profile-expansion"]["eligible_for_primary"] is True
    assert controls["reference"]["eligible_for_primary"] is False
    assert controls["reference"]["ineligibility_reason"] == (
        "task-blind-hybrid-diagnostic-only"
    )
    for control in controls.values():
        frozen = FrozenMemorySystem(output / control["bundle_path"])
        assert frozen.bundle_sha256 == control["bundle_sha256"]
        assert frozen.bundle_sha256 == control["bundle_semantic_sha256"]
        assert hashlib.sha256(
            (output / control["bundle_path"]).read_bytes()
        ).hexdigest() == control["bundle_file_sha256"]
        frozen.require_compatible(
            source_provenance=source.provenance,
            budget=source.budget.model_dump(mode="json"),
            treatment_mode="storage_and_service",
            exact_task_manifest_sha256=task_manifest_sha256(source),
        )
    with pytest.raises(ValueError, match="refusing to overwrite"):
        freeze_control_matrix(
            output,
            source=source,
            system_ids=("no-memory",),
        )


def test_control_matrix_rejects_duplicate_controls(tmp_path: Path) -> None:
    source = GeneratedMemoryTaskSource(seed=7, episode_count=4)
    with pytest.raises(ValueError, match="non-empty and unique"):
        freeze_control_matrix(
            tmp_path / "matrix",
            source=source,
            system_ids=("bm25", "bm25"),
        )


def test_control_matrix_freezes_dense_bge_only_with_a_verified_adapter(
    tmp_path: Path,
) -> None:
    source = GeneratedMemoryTaskSource(seed=7, episode_count=2)
    with pytest.raises(ValueError, match="requires a verified BGE model"):
        freeze_control_matrix(
            tmp_path / "missing-model",
            source=source,
            system_ids=("dense-bge-retrieval",),
        )

    manifest = freeze_control_matrix(
        tmp_path / "dense",
        source=source,
        system_ids=("dense-bge-retrieval",),
        dense_system=_dense_system(),
    )
    control = manifest["controls"][0]
    assert control["control_id"] == "dense-bge-retrieval"
    assert control["system_id"] == "dense-bge-retrieval-v1"
    assert control["eligible_for_primary"] is True


def test_control_matrix_rejects_mempalace_without_equivalence_evidence(
    tmp_path: Path,
) -> None:
    source = GeneratedMemoryTaskSource(seed=7, episode_count=2)
    with pytest.raises(ValueError, match="verified equivalence control"):
        freeze_control_matrix(
            tmp_path / "mempalace",
            source=source,
            system_ids=("mempalace-raw-session",),
        )


def test_full_prefix_ceiling_is_an_unmatched_diagnostic(tmp_path: Path) -> None:
    source = GeneratedMemoryTaskSource(
        seed=7,
        episode_count=1,
        budget=MemoryBudget(
            active_slots=4,
            max_archive_reads=0,
            retrieval_top_k=1,
            max_injected_tokens=65_536,
        ),
    )
    output = tmp_path / "full-prefix"
    manifest = freeze_control_matrix(
        output,
        source=source,
        system_ids=("full-prefix-ceiling",),
    )
    control = manifest["controls"][0]
    assert control["control_id"] == "full-prefix-ceiling"
    assert control["budget_class"] == "diagnostic-unmatched"
    assert control["eligible_for_primary"] is False
    assert control["ineligibility_reason"] == "unmatched-full-prefix-ceiling"
    assert FrozenMemorySystem(output / control["bundle_path"]).bundle_sha256 == (
        control["bundle_sha256"]
    )
