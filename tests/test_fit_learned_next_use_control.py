from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness.memory_trials import (
    FrozenLearnedControlArtifact,
    FrozenMemorySystem,
    GeneratedMemoryTaskSource,
    SplitCounts,
    TaskSplitManifest,
)
from scripts.fit_learned_next_use_control import compile_learned_control_artifacts
from scripts.freeze_memory_control_matrix import freeze_control_matrix


def test_learned_control_artifacts_publish_atomically_and_freeze(tmp_path: Path) -> None:
    source = GeneratedMemoryTaskSource(seed=7, episode_count=24)
    artifact_dir = tmp_path / "learned"
    manifest = compile_learned_control_artifacts(
        artifact_dir,
        source=source,
        counts=SplitCounts(train=16, dev=4, test=4),
        split_seed=42,
        training_iterations=20,
    )
    assert manifest["status"] == "FROZEN_LEARNED_CONTROL"
    assert manifest["scientific_result"] is False
    assert manifest["fit"]["test_labels_opened"] is False
    split = TaskSplitManifest.model_validate_json(
        (artifact_dir / "split-manifest.json").read_text(encoding="utf-8")
    )
    artifact = FrozenLearnedControlArtifact.model_validate_json(
        (artifact_dir / "learned-next-use-artifact.json").read_text(encoding="utf-8")
    )
    assert manifest["split_manifest_sha256"] == split.manifest_sha256
    assert manifest["learned_artifact_sha256"] == artifact.artifact_sha256

    matrix_dir = tmp_path / "matrix"
    matrix = freeze_control_matrix(
        matrix_dir,
        source=source,
        system_ids=("no-memory", "learned-next-use"),
        learned_artifact=artifact,
    )
    controls = {item["control_id"]: item for item in matrix["controls"]}
    assert controls["learned-next-use"]["eligible_for_primary"] is True
    assert controls["learned-next-use"]["training_artifact_sha256"] == (
        artifact.artifact_sha256
    )
    frozen = FrozenMemorySystem(
        matrix_dir / controls["learned-next-use"]["bundle_path"]
    )
    assert frozen.receipt.system_id == "learned-next-use-memory-v1"

    with pytest.raises(ValueError, match="refusing to overwrite"):
        compile_learned_control_artifacts(
            artifact_dir,
            source=source,
            counts=SplitCounts(train=16, dev=4, test=4),
            split_seed=42,
            training_iterations=20,
        )


def test_matrix_refuses_unfrozen_learned_control(tmp_path: Path) -> None:
    source = GeneratedMemoryTaskSource(seed=7, episode_count=4)
    with pytest.raises(ValueError, match="requires a frozen learned artifact"):
        freeze_control_matrix(
            tmp_path / "matrix",
            source=source,
            system_ids=("learned-next-use",),
        )


def test_artifact_file_is_canonical_json(tmp_path: Path) -> None:
    source = GeneratedMemoryTaskSource(seed=7, episode_count=24)
    output = tmp_path / "learned"
    compile_learned_control_artifacts(
        output,
        source=source,
        counts=SplitCounts(train=16, dev=4, test=4),
        split_seed=42,
        training_iterations=10,
    )
    payload = json.loads(
        (output / "learned-next-use-artifact.json").read_text(encoding="utf-8")
    )
    assert payload["label_splits"] == ["train", "dev"]
    assert "test_task_ids_sha256" not in payload
    assert "test_label_rows_sha256" not in payload
