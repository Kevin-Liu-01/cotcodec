from __future__ import annotations

import pytest
from pydantic import ValidationError

from harness.memory_trials import (
    GENERATED_MEMORY_VERSION,
    GeneratedMemoryTaskSource,
    SplitCounts,
    SplitManifestError,
    SplitName,
    TaskSplitManifest,
    make_exact_family_split,
    validate_split_manifest,
)


class _ReversedSource:
    def __init__(self, source: GeneratedMemoryTaskSource) -> None:
        self._source = source
        self.identity = source.identity
        self.provenance = source.provenance
        self.budget = source.budget

    def ids(self) -> tuple[str, ...]:
        return tuple(reversed(self._source.ids()))

    def load(self, task_id: str):  # type: ignore[no-untyped-def]
        return self._source.load(task_id)

    def split_family_id(self, task_id: str) -> str:
        return self._source.split_family_id(task_id)


@pytest.fixture(scope="module")
def registered_manifest() -> TaskSplitManifest:
    source = GeneratedMemoryTaskSource(seed=7, episode_count=2_400)
    return make_exact_family_split(
        source,
        counts=SplitCounts(train=1_440, dev=480, test=480),
        split_seed=42,
    )


def test_registered_split_has_exact_counts_and_no_family_overlap(
    registered_manifest: TaskSplitManifest,
) -> None:
    assert len(registered_manifest.task_ids(SplitName.TRAIN)) == 1_440
    assert len(registered_manifest.task_ids(SplitName.DEV)) == 480
    assert len(registered_manifest.task_ids(SplitName.TEST)) == 480
    family_splits: dict[str, set[SplitName]] = {}
    for entry in registered_manifest.entries:
        family_splits.setdefault(entry.family_id, set()).add(entry.split)
    assert all(len(splits) == 1 for splits in family_splits.values())
    assert len({entry.task_id for entry in registered_manifest.entries}) == 2_400


def test_cross_stratum_variants_of_a_family_stay_together(
    registered_manifest: TaskSplitManifest,
) -> None:
    source = GeneratedMemoryTaskSource(seed=7, episode_count=2_400)
    for family_id in {entry.family_id for entry in registered_manifest.entries}:
        family_entries = [
            entry for entry in registered_manifest.entries if entry.family_id == family_id
        ]
        assert len({entry.split for entry in family_entries}) == 1
        assert len({source.load(entry.task_id).stratum for entry in family_entries}) == 4


def test_generator_v2_namespaces_are_disjoint_across_splits(
    registered_manifest: TaskSplitManifest,
) -> None:
    source = GeneratedMemoryTaskSource(seed=7, episode_count=2_400)
    assert source.provenance["generator_version"] == GENERATED_MEMORY_VERSION
    identifiers: dict[SplitName, set[str]] = {split: set() for split in SplitName}
    for entry in registered_manifest.entries:
        task = source.load(entry.task_id)
        for event in task.events:
            identifiers[entry.split].add(event.entity_id)
            if event.value is not None:
                identifiers[entry.split].add(event.value)
    assert identifiers[SplitName.TRAIN].isdisjoint(identifiers[SplitName.DEV])
    assert identifiers[SplitName.TRAIN].isdisjoint(identifiers[SplitName.TEST])
    assert identifiers[SplitName.DEV].isdisjoint(identifiers[SplitName.TEST])


def test_split_is_deterministic_and_independent_of_source_id_order(
    registered_manifest: TaskSplitManifest,
) -> None:
    source = GeneratedMemoryTaskSource(seed=7, episode_count=2_400)
    reversed_manifest = make_exact_family_split(
        _ReversedSource(source),
        counts=SplitCounts(train=1_440, dev=480, test=480),
        split_seed=42,
    )
    assert reversed_manifest == registered_manifest


def test_split_seed_changes_family_assignment() -> None:
    source = GeneratedMemoryTaskSource(seed=7, episode_count=240)
    counts = SplitCounts(train=144, dev=48, test=48)
    first = make_exact_family_split(source, counts=counts, split_seed=42)
    second = make_exact_family_split(source, counts=counts, split_seed=43)
    assert first.manifest_sha256 != second.manifest_sha256
    assert first.task_ids(SplitName.TRAIN) != second.task_ids(SplitName.TRAIN)


def test_impossible_family_count_is_rejected() -> None:
    source = GeneratedMemoryTaskSource(seed=7, episode_count=8)
    with pytest.raises(SplitManifestError, match="no family-disjoint subset"):
        make_exact_family_split(
            source,
            counts=SplitCounts(train=3, dev=1, test=4),
            split_seed=42,
        )


def test_source_drift_invalidates_manifest(registered_manifest: TaskSplitManifest) -> None:
    changed_source = GeneratedMemoryTaskSource(seed=8, episode_count=2_400)
    with pytest.raises(SplitManifestError, match="source provenance changed"):
        validate_split_manifest(registered_manifest, changed_source)


def test_manifest_digest_rejects_tampering(registered_manifest: TaskSplitManifest) -> None:
    payload = registered_manifest.model_dump(mode="json")
    payload["entries"][0]["split"] = "dev"
    with pytest.raises(ValidationError):
        TaskSplitManifest.model_validate(payload)


def test_registered_manifest_revalidates_against_exact_source(
    registered_manifest: TaskSplitManifest,
) -> None:
    source = GeneratedMemoryTaskSource(seed=7, episode_count=2_400)
    validate_split_manifest(registered_manifest, source)
