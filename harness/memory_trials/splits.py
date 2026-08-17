"""Content-addressed, family-disjoint task splits for memory studies."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Mapping
from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from harness.memory_trials.schema import canonical_json, sha256_text
from harness.memory_trials.sources import MemoryTaskSource


class SplitManifestError(ValueError):
    """Raised when a split cannot be constructed or no longer binds its source."""


class SplitName(StrEnum):
    TRAIN = "train"
    DEV = "dev"
    TEST = "test"


class FamilySplittableTaskSource(MemoryTaskSource, Protocol):
    """Source that exposes the family unit that must never cross partitions."""

    def split_family_id(self, task_id: str) -> str: ...


class SplitCounts(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    train: int = Field(ge=0)
    dev: int = Field(ge=0)
    test: int = Field(ge=0)

    @property
    def total(self) -> int:
        return self.train + self.dev + self.test


class TaskSplitEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    task_id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
    task_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    family_id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
    group_id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
    split: SplitName


class TaskSplitManifest(BaseModel):
    """Immutable split receipt that binds every task and generator family."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = Field(default="memory-task-split-v1", frozen=True)
    source_identity: str = Field(min_length=1)
    source_provenance: dict[str, JsonValue]
    source_provenance_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_task_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    split_seed: int
    requested_counts: SplitCounts
    entries: tuple[TaskSplitEntry, ...]
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_manifest(self) -> TaskSplitManifest:
        if not self.entries:
            raise ValueError("split manifest must contain tasks")
        task_ids = [entry.task_id for entry in self.entries]
        if task_ids != sorted(task_ids):
            raise ValueError("split entries must be sorted by task_id")
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("split manifest contains duplicate task ids")
        actual_counts = {
            split: sum(entry.split is split for entry in self.entries)
            for split in SplitName
        }
        if actual_counts != {
            SplitName.TRAIN: self.requested_counts.train,
            SplitName.DEV: self.requested_counts.dev,
            SplitName.TEST: self.requested_counts.test,
        }:
            raise ValueError("split counts do not match the registered counts")
        family_splits: dict[str, set[SplitName]] = defaultdict(set)
        for entry in self.entries:
            family_splits[entry.family_id].add(entry.split)
        leaked = sorted(
            family_id
            for family_id, splits in family_splits.items()
            if len(splits) != 1
        )
        if leaked:
            raise ValueError(f"families cross split boundaries: {leaked}")
        provenance_sha256 = sha256_text(canonical_json(self.source_provenance))
        if provenance_sha256 != self.source_provenance_sha256:
            raise ValueError("source provenance digest mismatch")
        task_manifest_sha256 = _task_rows_sha256(self.entries)
        if task_manifest_sha256 != self.source_task_manifest_sha256:
            raise ValueError("source task-manifest digest mismatch")
        unsigned = self.model_dump(mode="json", exclude={"manifest_sha256"})
        if sha256_text(canonical_json(unsigned)) != self.manifest_sha256:
            raise ValueError("split manifest digest mismatch")
        return self

    def task_ids(self, split: SplitName | str) -> tuple[str, ...]:
        requested = SplitName(split)
        return tuple(entry.task_id for entry in self.entries if entry.split is requested)


def _task_rows_sha256(entries: tuple[TaskSplitEntry, ...] | list[TaskSplitEntry]) -> str:
    rows = [
        {"task_id": entry.task_id, "task_sha256": entry.task_sha256}
        for entry in sorted(entries, key=lambda item: item.task_id)
    ]
    return sha256_text(canonical_json(rows))


def _ordered_families(family_ids: set[str], split_seed: int) -> list[str]:
    return sorted(
        family_ids,
        key=lambda family_id: (
            hashlib.sha256(f"{split_seed}:{family_id}".encode()).hexdigest(),
            family_id,
        ),
    )


def _exact_subset(
    family_sizes: Mapping[str, int],
    *,
    target: int,
    split_seed: int,
) -> set[str]:
    if target == 0:
        return set()
    ordered = _ordered_families(set(family_sizes), split_seed)
    reachable: dict[int, tuple[str, ...]] = {0: ()}
    for family_id in ordered:
        size = family_sizes[family_id]
        additions: dict[int, tuple[str, ...]] = {}
        for subtotal, selected in sorted(reachable.items(), reverse=True):
            candidate = subtotal + size
            if candidate <= target and candidate not in reachable and candidate not in additions:
                additions[candidate] = (*selected, family_id)
        reachable.update(additions)
        if target in reachable:
            return set(reachable[target])
    raise SplitManifestError(
        f"no family-disjoint subset has exactly {target} tasks; "
        f"family sizes={sorted(family_sizes.values())}"
    )


def make_exact_family_split(
    source: FamilySplittableTaskSource,
    *,
    counts: SplitCounts,
    split_seed: int,
) -> TaskSplitManifest:
    """Compile an exact three-way split without allowing a family to cross it."""

    source_ids = tuple(source.ids())
    if counts.total != len(source_ids):
        raise SplitManifestError(
            f"registered split total {counts.total} != source task count {len(source_ids)}"
        )
    if len(source_ids) != len(set(source_ids)):
        raise SplitManifestError("source returned duplicate task ids")

    tasks: dict[str, Any] = {}
    families: dict[str, list[str]] = defaultdict(list)
    for task_id in sorted(source_ids):
        task = source.load(task_id)
        if task.task_id != task_id:
            raise SplitManifestError(f"source returned the wrong task for {task_id}")
        family_id = source.split_family_id(task_id)
        if not family_id:
            raise SplitManifestError(f"source returned an empty family for {task_id}")
        tasks[task_id] = task
        families[family_id].append(task_id)

    family_sizes = {family_id: len(task_ids) for family_id, task_ids in families.items()}
    train_families = _exact_subset(
        family_sizes,
        target=counts.train,
        split_seed=split_seed,
    )
    remaining_sizes = {
        family_id: size
        for family_id, size in family_sizes.items()
        if family_id not in train_families
    }
    dev_families = _exact_subset(
        remaining_sizes,
        target=counts.dev,
        split_seed=split_seed + 1,
    )
    test_families = set(families) - train_families - dev_families
    if sum(family_sizes[family_id] for family_id in test_families) != counts.test:
        raise SplitManifestError("remaining families do not match the registered test count")

    family_split = {
        **{family_id: SplitName.TRAIN for family_id in train_families},
        **{family_id: SplitName.DEV for family_id in dev_families},
        **{family_id: SplitName.TEST for family_id in test_families},
    }
    entries = tuple(
        TaskSplitEntry(
            task_id=task_id,
            task_sha256=tasks[task_id].task_sha256,
            family_id=source.split_family_id(task_id),
            group_id=tasks[task_id].group_id,
            split=family_split[source.split_family_id(task_id)],
        )
        for task_id in sorted(tasks)
    )
    provenance = dict(source.provenance)
    unsigned = {
        "schema_version": "memory-task-split-v1",
        "source_identity": source.identity,
        "source_provenance": provenance,
        "source_provenance_sha256": sha256_text(canonical_json(provenance)),
        "source_task_manifest_sha256": _task_rows_sha256(entries),
        "split_seed": split_seed,
        "requested_counts": counts.model_dump(mode="json"),
        "entries": [entry.model_dump(mode="json") for entry in entries],
    }
    return TaskSplitManifest.model_validate(
        {
            **unsigned,
            "manifest_sha256": sha256_text(canonical_json(unsigned)),
        }
    )


def validate_split_manifest(
    manifest: TaskSplitManifest,
    source: FamilySplittableTaskSource,
) -> None:
    """Fail closed if a manifest no longer matches the exact source tasks."""

    if manifest.source_identity != source.identity:
        raise SplitManifestError("split manifest source identity changed")
    provenance = dict(source.provenance)
    if canonical_json(manifest.source_provenance) != canonical_json(provenance):
        raise SplitManifestError("split manifest source provenance changed")
    source_ids = tuple(sorted(source.ids()))
    if tuple(entry.task_id for entry in manifest.entries) != source_ids:
        raise SplitManifestError("split manifest task ids changed")
    for entry in manifest.entries:
        task = source.load(entry.task_id)
        if task.task_sha256 != entry.task_sha256:
            raise SplitManifestError(f"task changed after split: {entry.task_id}")
        if task.group_id != entry.group_id:
            raise SplitManifestError(f"task group changed after split: {entry.task_id}")
        if source.split_family_id(entry.task_id) != entry.family_id:
            raise SplitManifestError(f"task family changed after split: {entry.task_id}")
