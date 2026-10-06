from __future__ import annotations

import pytest
from pydantic import ValidationError

import harness.memory_trials.learned_control as learned_control
from harness.memory_trials import (
    FEATURE_NAMES,
    FORBIDDEN_POLICY_INPUTS,
    FrozenLearnedControlArtifact,
    GeneratedMemoryTaskSource,
    LearnedNextUseMemorySystem,
    MemorySystemRequest,
    SplitCounts,
    build_memory_system_request,
    fit_learned_next_use,
    make_exact_family_split,
)


@pytest.fixture(scope="module")
def fitted_control():  # type: ignore[no-untyped-def]
    source = GeneratedMemoryTaskSource(seed=7, episode_count=24)
    manifest = make_exact_family_split(
        source,
        counts=SplitCounts(train=16, dev=4, test=4),
        split_seed=42,
    )
    artifact = fit_learned_next_use(
        source,
        manifest,
        training_iterations=80,
    )
    return source, manifest, artifact


def test_artifact_binds_disjoint_train_dev_lineage(fitted_control) -> None:  # type: ignore[no-untyped-def]
    _, manifest, artifact = fitted_control
    assert artifact.label_splits == ("train", "dev")
    assert set(artifact.train_family_ids).isdisjoint(artifact.dev_family_ids)
    assert artifact.feature_names == FEATURE_NAMES
    assert artifact.forbidden_policy_inputs == FORBIDDEN_POLICY_INPUTS
    assert set(artifact.train_family_ids) == {
        entry.family_id for entry in manifest.entries if entry.split == "train"
    }
    assert set(artifact.dev_family_ids) == {
        entry.family_id for entry in manifest.entries if entry.split == "dev"
    }


def test_fitter_opens_future_labels_only_for_train_and_dev(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    source = GeneratedMemoryTaskSource(seed=7, episode_count=24)
    manifest = make_exact_family_split(
        source,
        counts=SplitCounts(train=16, dev=4, test=4),
        split_seed=42,
    )
    labeled_task_ids: list[str] = []
    original = learned_control._label_support_records

    def recording_labeler(task):  # type: ignore[no-untyped-def]
        labeled_task_ids.append(task.task_id)
        return original(task)

    monkeypatch.setattr(learned_control, "_label_support_records", recording_labeler)
    fit_learned_next_use(source, manifest, training_iterations=10)
    expected = set(manifest.task_ids("train")) | set(manifest.task_ids("dev"))
    assert set(labeled_task_ids) == expected
    assert set(labeled_task_ids).isdisjoint(manifest.task_ids("test"))


def test_frozen_policy_is_query_blind(fitted_control) -> None:  # type: ignore[no-untyped-def]
    source, manifest, artifact = fitted_control
    task = source.load(manifest.task_ids("test")[0])
    request, _ = build_memory_system_request(
        task,
        visibility="serve",
        treatment_mode="storage_and_service",
    )
    changed_query = request.model_copy(
        update={
            "request_id": "changed-query-request",
            "query": "Completely unrelated future-looking query text.",
        }
    )
    system = LearnedNextUseMemorySystem(artifact)
    first = system.select(request)
    second = system.select(changed_query)
    assert first.evidence == second.evidence
    assert first.receipt == second.receipt


def test_task_blind_request_cannot_carry_forbidden_policy_inputs() -> None:
    request_fields = set(MemorySystemRequest.model_fields)
    assert request_fields.isdisjoint(
        {
            "candidate",
            "oracle",
            "proactive_hint",
            "source_quality",
            "stratum",
            "suffix",
            "test_label",
        }
    )
    assert "query" not in FEATURE_NAMES


def test_fit_and_selection_are_deterministic(fitted_control) -> None:  # type: ignore[no-untyped-def]
    source, manifest, first = fitted_control
    second = fit_learned_next_use(
        source,
        manifest,
        training_iterations=80,
    )
    assert second == first
    task = source.load(manifest.task_ids("test")[0])
    request, _ = build_memory_system_request(
        task,
        visibility="serve",
        treatment_mode="storage_and_service",
    )
    system = LearnedNextUseMemorySystem(first)
    assert system.select(request) == system.select(request)


def test_artifact_digest_rejects_weight_tampering(fitted_control) -> None:  # type: ignore[no-untyped-def]
    _, _, artifact = fitted_control
    payload = artifact.model_dump(mode="json")
    payload["coefficients"][0] += 1.0
    with pytest.raises(ValidationError, match="artifact digest mismatch"):
        FrozenLearnedControlArtifact.model_validate(payload)
