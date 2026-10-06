from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness.memory_trials import (
    GeneratedMemoryTaskSource,
    QualityCollectionError,
    ReplayableMemoryWorld,
    collect_all_serve,
    load_quality_outcomes,
)
from harness.memory_trials.models import JsonCompletionMemoryActor


def test_all_serve_collection_covers_every_task_and_resumes(tmp_path: Path) -> None:
    source = GeneratedMemoryTaskSource(seed=7, episode_count=8)
    world = ReplayableMemoryWorld(source)
    root = tmp_path / "quality"
    first = collect_all_serve(world, source.ids(), root, stop_after=3)
    assert first.status == "CHECKPOINTED"
    assert first.completed_tasks == 3
    completed = collect_all_serve(world, source.ids(), root, resume=True)
    assert completed.status == "COMPLETE"
    assert completed.completed_tasks == 8
    assert completed.bundle_root is not None
    outcomes = load_quality_outcomes(completed.bundle_root)
    assert len(outcomes) == 8
    assert all(outcome.visibility == "serve" for outcome in outcomes)
    assert all(outcome.candidate_visible for outcome in outcomes)


def test_all_serve_collection_rejects_contract_and_bundle_drift(tmp_path: Path) -> None:
    source = GeneratedMemoryTaskSource(seed=7, episode_count=4)
    root = tmp_path / "quality"
    result = collect_all_serve(ReplayableMemoryWorld(source), source.ids(), root)
    assert result.bundle_root is not None
    with pytest.raises(QualityCollectionError, match="resume contract changed"):
        collect_all_serve(
            ReplayableMemoryWorld(source),
            tuple(reversed(source.ids())),
            root,
            resume=True,
        )
    observed = result.bundle_root / "observed_trials.jsonl"
    observed.write_text(observed.read_text() + "{}\n")
    with pytest.raises(QualityCollectionError, match="hash verification"):
        load_quality_outcomes(result.bundle_root)


def test_all_serve_resume_binds_publication_admission(tmp_path: Path) -> None:
    source = GeneratedMemoryTaskSource(seed=7, episode_count=4)
    root = tmp_path / "quality-admission"
    first = collect_all_serve(
        ReplayableMemoryWorld(source),
        source.ids(),
        root,
        stop_after=2,
        admission_contract={"wave_sha256": "a" * 64, "control_id": "bm25"},
    )
    assert first.status == "CHECKPOINTED"
    with pytest.raises(QualityCollectionError, match="resume contract changed"):
        collect_all_serve(
            ReplayableMemoryWorld(source),
            source.ids(),
            root,
            resume=True,
            admission_contract={"wave_sha256": "b" * 64, "control_id": "bm25"},
        )
    complete = collect_all_serve(
        ReplayableMemoryWorld(source),
        source.ids(),
        root,
        resume=True,
        admission_contract={"wave_sha256": "a" * 64, "control_id": "bm25"},
    )
    assert complete.bundle_root is not None
    manifest = json.loads((complete.bundle_root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["admission_contract"]["wave_sha256"] == "a" * 64


def test_all_serve_resume_rejects_same_identity_with_changed_actor_contract(
    tmp_path: Path,
) -> None:
    source = GeneratedMemoryTaskSource(seed=7, episode_count=4)
    root = tmp_path / "actor-contract"

    def actor(contract_version: str) -> JsonCompletionMemoryActor:
        return JsonCompletionMemoryActor(
            identity="same-actor-identity",
            complete=lambda _prompt: '{"mode":"answer","answer":"UNKNOWN"}',
            contract={
                "identity": "same-actor-identity",
                "contract_version": contract_version,
            },
        )

    collect_all_serve(
        ReplayableMemoryWorld(source, actor=actor("first")),
        source.ids(),
        root,
        stop_after=2,
    )
    with pytest.raises(QualityCollectionError, match="resume contract changed"):
        collect_all_serve(
            ReplayableMemoryWorld(source, actor=actor("second")),
            source.ids(),
            root,
            resume=True,
        )
