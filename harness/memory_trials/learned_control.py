"""Leakage-bounded learned next-use comparator for memory selection.

This module intentionally implements a noncausal control.  Future task outcomes
create labels on TRAIN and choose one preregistered regularizer on DEV; the
frozen selector itself receives only task-blind prefix records and never reads a
query, oracle, stratum, candidate flag, source-quality score, or test label.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Sequence
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

from harness.memory_trials.schema import (
    MemoryStratum,
    MemoryTask,
    canonical_json,
    sha256_text,
)
from harness.memory_trials.sources import GeneratedMemoryTaskSource
from harness.memory_trials.splits import (
    SplitName,
    TaskSplitManifest,
    validate_split_manifest,
)
from harness.memory_trials.systems import (
    MemorySelection,
    MemorySystemReceipt,
    MemorySystemRecord,
    MemorySystemRequest,
    _costs,
    _fit_evidence_budget,
    _record_evidence,
    _seal_selection,
    build_memory_system_request,
    materialize_prefix_records,
    materialize_request_records,
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")
FEATURE_NAMES = (
    "age_steps",
    "steps_since_access",
    "entity_record_count",
    "key_record_count",
    "entity_key_record_count",
    "explicit_access_count",
    "value_utf8_bytes",
    "value_token_count",
    "is_latest_entity_key",
    "event_is_update",
    "event_is_observe",
    "is_untrusted",
)
FORBIDDEN_POLICY_INPUTS = (
    "candidate",
    "contradiction_count",
    "oracle",
    "proactive_hint",
    "query",
    "source_quality",
    "stratum",
    "suffix",
    "test_label",
)
LABEL_RULE_VERSION = "next-use-exact-support-v1"
TRAINING_ALGORITHM = "full-batch-logistic-gradient-descent-float64-v1"


class FrozenLearnedControlArtifact(BaseModel):
    """Sealed weights and data-lineage receipt for the learned control."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["learned-next-use-artifact-v1"] = (
        "learned-next-use-artifact-v1"
    )
    system_id: Literal["learned-next-use-memory-v1"] = "learned-next-use-memory-v1"
    label_rule_version: Literal["next-use-exact-support-v1"] = LABEL_RULE_VERSION
    training_algorithm: Literal[
        "full-batch-logistic-gradient-descent-float64-v1"
    ] = TRAINING_ALGORITHM
    feature_names: tuple[str, ...]
    forbidden_policy_inputs: tuple[str, ...]
    split_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_identity: str = Field(min_length=1)
    source_provenance_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_task_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    train_task_ids_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    dev_task_ids_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    train_family_ids: tuple[str, ...]
    dev_family_ids: tuple[str, ...]
    label_splits: tuple[Literal["train", "dev"], ...]
    train_label_rows_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    dev_label_rows_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    feature_means: tuple[float, ...]
    feature_scales: tuple[float, ...]
    coefficients: tuple[float, ...]
    intercept: float
    selected_l2: float = Field(ge=0.0, allow_inf_nan=False)
    l2_candidates: tuple[float, ...]
    dev_log_loss_by_l2: dict[str, float]
    training_iterations: int = Field(ge=1)
    learning_rate: float = Field(gt=0.0, allow_inf_nan=False)
    train_row_count: int = Field(ge=1)
    dev_row_count: int = Field(ge=1)
    train_positive_count: int = Field(ge=1)
    dev_positive_count: int = Field(ge=1)
    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_artifact(self) -> FrozenLearnedControlArtifact:
        if self.feature_names != FEATURE_NAMES:
            raise ValueError("learned-control feature schema changed")
        if self.forbidden_policy_inputs != FORBIDDEN_POLICY_INPUTS:
            raise ValueError("learned-control forbidden-input contract changed")
        if self.label_splits != ("train", "dev"):
            raise ValueError("learned-control labels must be restricted to train/dev")
        width = len(FEATURE_NAMES)
        if not all(
            len(values) == width
            for values in (self.feature_means, self.feature_scales, self.coefficients)
        ):
            raise ValueError("learned-control vector width mismatch")
        numeric = (
            *self.feature_means,
            *self.feature_scales,
            *self.coefficients,
            self.intercept,
            *self.l2_candidates,
            *self.dev_log_loss_by_l2.values(),
        )
        if not all(math.isfinite(value) for value in numeric):
            raise ValueError("learned-control artifact contains non-finite values")
        if any(scale <= 0 for scale in self.feature_scales):
            raise ValueError("learned-control feature scales must be positive")
        if any(value < 0 for value in self.l2_candidates):
            raise ValueError("learned-control L2 candidates cannot be negative")
        if tuple(sorted(set(self.train_family_ids))) != self.train_family_ids:
            raise ValueError("train family IDs must be sorted and unique")
        if tuple(sorted(set(self.dev_family_ids))) != self.dev_family_ids:
            raise ValueError("dev family IDs must be sorted and unique")
        if set(self.train_family_ids) & set(self.dev_family_ids):
            raise ValueError("train and dev families overlap")
        unsigned = self.model_dump(mode="json", exclude={"artifact_sha256"})
        if sha256_text(canonical_json(unsigned)) != self.artifact_sha256:
            raise ValueError("learned-control artifact digest mismatch")
        return self


def _label_support_records(task: MemoryTask) -> set[str]:
    """Return future-use support IDs for offline TRAIN/DEV labeling only."""

    valid_records = tuple(record for record in materialize_prefix_records(task) if record.valid)
    query_event = task.events[-1]
    if task.stratum is not MemoryStratum.TEMPORAL_GRAPH:
        return {
            record.record_id
            for record in valid_records
            if record.entity_id == query_event.entity_id
            and record.key == query_event.key
            and record.value == task.oracle.expected_value
        }

    positives: set[str] = set()
    first_hops = [
        record for record in valid_records if record.entity_id == query_event.entity_id
    ]
    for first_hop in first_hops:
        for second_hop in valid_records:
            if (
                second_hop.entity_id == first_hop.value
                and second_hop.value == task.oracle.expected_value
            ):
                positives.update((first_hop.record_id, second_hop.record_id))
    return positives


def _feature_vectors(
    request: MemorySystemRequest,
) -> tuple[tuple[MemorySystemRecord, tuple[float, ...]], ...]:
    records = materialize_request_records(request)
    max_step = max((event.step for event in request.events), default=0) + 1
    entity_counts = Counter(record.entity_id for record in records if record.valid)
    key_counts = Counter(record.key for record in records if record.valid)
    pair_counts = Counter(
        (record.entity_id, record.key) for record in records if record.valid
    )
    access_counts = Counter(
        (event.entity_id, event.key)
        for event in request.events
        if event.kind == "access"
    )
    event_kinds = {event.source_event_id: event.kind for event in request.events}
    latest_by_pair: dict[tuple[str, str], int] = {}
    for record in records:
        if record.valid:
            pair = (record.entity_id, record.key)
            latest_by_pair[pair] = max(
                latest_by_pair.get(pair, -1), record.written_step
            )

    rows: list[tuple[MemorySystemRecord, tuple[float, ...]]] = []
    for record in records:
        pair = (record.entity_id, record.key)
        kind = event_kinds[record.source_record_id]
        rows.append(
            (
                record,
                (
                    float(max_step - record.written_step),
                    float(max_step - record.last_access_step),
                    float(entity_counts[record.entity_id]),
                    float(key_counts[record.key]),
                    float(pair_counts[pair]),
                    float(access_counts[pair]),
                    float(len(record.value.encode())),
                    float(len(_TOKEN_RE.findall(record.value.casefold()))),
                    float(record.written_step == latest_by_pair.get(pair)),
                    float(kind == "update"),
                    float(kind == "observe"),
                    float(record.untrusted),
                ),
            )
        )
    return tuple(rows)


def _labeled_rows(
    source: GeneratedMemoryTaskSource,
    task_ids: Sequence[str],
) -> tuple[np.ndarray, np.ndarray, str]:
    features: list[tuple[float, ...]] = []
    labels: list[float] = []
    label_receipt: list[dict[str, object]] = []
    for task_id in task_ids:
        task = source.load(task_id)
        positive_source_ids = _label_support_records(task)
        request, _ = build_memory_system_request(
            task,
            visibility="serve",
            treatment_mode="storage_and_service",
        )
        prefix_events = tuple(
            event for event in task.events if event.step < task.eligibility_step
        )
        if len(prefix_events) != len(request.events):
            raise ValueError("normalized prefix changed event cardinality")
        label_by_normalized_id = {
            normalized.source_event_id: float(original.event_id in positive_source_ids)
            for original, normalized in zip(prefix_events, request.events, strict=True)
        }
        for record, vector in _feature_vectors(request):
            label = label_by_normalized_id[record.source_record_id]
            features.append(vector)
            labels.append(label)
            label_receipt.append(
                {
                    "task_id": task_id,
                    "source_record_id": record.source_record_id,
                    "label": int(label),
                }
            )
    if not features or not any(labels):
        raise ValueError("learned control requires nonempty rows and positive labels")
    return (
        np.asarray(features, dtype=np.float64),
        np.asarray(labels, dtype=np.float64),
        sha256_text(canonical_json(label_receipt)),
    )


def _fit_logistic(
    features: np.ndarray,
    labels: np.ndarray,
    *,
    l2: float,
    iterations: int,
    learning_rate: float,
) -> tuple[np.ndarray, float]:
    coefficients = np.zeros(features.shape[1], dtype=np.float64)
    prevalence = float(np.clip(labels.mean(), 1e-6, 1.0 - 1e-6))
    intercept = math.log(prevalence / (1.0 - prevalence))
    for _ in range(iterations):
        logits = np.clip(features @ coefficients + intercept, -30.0, 30.0)
        probabilities = 1.0 / (1.0 + np.exp(-logits))
        residual = probabilities - labels
        gradient = features.T @ residual / len(labels) + l2 * coefficients
        coefficients -= learning_rate * gradient
        intercept -= learning_rate * float(residual.mean())
    return coefficients, intercept


def _log_loss(
    features: np.ndarray,
    labels: np.ndarray,
    coefficients: np.ndarray,
    intercept: float,
) -> float:
    logits = features @ coefficients + intercept
    return float(np.mean(np.logaddexp(0.0, logits) - labels * logits))


def fit_learned_next_use(
    source: GeneratedMemoryTaskSource,
    split_manifest: TaskSplitManifest,
    *,
    l2_candidates: tuple[float, ...] = (0.0, 0.01, 0.1, 1.0),
    training_iterations: int = 250,
    learning_rate: float = 0.1,
) -> FrozenLearnedControlArtifact:
    """Fit on TRAIN labels and choose L2 on DEV without opening TEST labels."""

    validate_split_manifest(split_manifest, source)
    if not l2_candidates or any(
        not math.isfinite(value) or value < 0 for value in l2_candidates
    ):
        raise ValueError("L2 candidate grid must contain finite nonnegative values")
    if len(set(l2_candidates)) != len(l2_candidates):
        raise ValueError("L2 candidate grid contains duplicates")
    if training_iterations < 1:
        raise ValueError("training_iterations must be positive")
    if not math.isfinite(learning_rate) or learning_rate <= 0:
        raise ValueError("learning_rate must be finite and positive")

    train_ids = split_manifest.task_ids(SplitName.TRAIN)
    dev_ids = split_manifest.task_ids(SplitName.DEV)
    if not train_ids or not dev_ids:
        raise ValueError("learned control requires nonempty train and dev splits")
    train_features, train_labels, train_label_sha256 = _labeled_rows(source, train_ids)
    dev_features, dev_labels, dev_label_sha256 = _labeled_rows(source, dev_ids)
    means = train_features.mean(axis=0)
    scales = train_features.std(axis=0)
    scales = np.where(scales < 1e-12, 1.0, scales)
    normalized_train = (train_features - means) / scales
    normalized_dev = (dev_features - means) / scales

    losses: dict[str, float] = {}
    models: dict[float, tuple[np.ndarray, float]] = {}
    for l2 in l2_candidates:
        model = _fit_logistic(
            normalized_train,
            train_labels,
            l2=l2,
            iterations=training_iterations,
            learning_rate=learning_rate,
        )
        models[l2] = model
        losses[format(l2, ".17g")] = _log_loss(
            normalized_dev,
            dev_labels,
            *model,
        )
    selected_l2 = min(
        l2_candidates,
        key=lambda value: (losses[format(value, ".17g")], value),
    )
    coefficients, intercept = models[selected_l2]

    entries_by_id = {entry.task_id: entry for entry in split_manifest.entries}
    train_families = tuple(sorted({entries_by_id[item].family_id for item in train_ids}))
    dev_families = tuple(sorted({entries_by_id[item].family_id for item in dev_ids}))
    unsigned = {
        "schema_version": "learned-next-use-artifact-v1",
        "system_id": "learned-next-use-memory-v1",
        "label_rule_version": LABEL_RULE_VERSION,
        "training_algorithm": TRAINING_ALGORITHM,
        "feature_names": list(FEATURE_NAMES),
        "forbidden_policy_inputs": list(FORBIDDEN_POLICY_INPUTS),
        "split_manifest_sha256": split_manifest.manifest_sha256,
        "source_identity": split_manifest.source_identity,
        "source_provenance_sha256": split_manifest.source_provenance_sha256,
        "source_task_manifest_sha256": split_manifest.source_task_manifest_sha256,
        "train_task_ids_sha256": sha256_text(canonical_json(list(train_ids))),
        "dev_task_ids_sha256": sha256_text(canonical_json(list(dev_ids))),
        "train_family_ids": list(train_families),
        "dev_family_ids": list(dev_families),
        "label_splits": ["train", "dev"],
        "train_label_rows_sha256": train_label_sha256,
        "dev_label_rows_sha256": dev_label_sha256,
        "feature_means": [float(value) for value in means],
        "feature_scales": [float(value) for value in scales],
        "coefficients": [float(value) for value in coefficients],
        "intercept": float(intercept),
        "selected_l2": selected_l2,
        "l2_candidates": list(l2_candidates),
        "dev_log_loss_by_l2": losses,
        "training_iterations": training_iterations,
        "learning_rate": learning_rate,
        "train_row_count": len(train_labels),
        "dev_row_count": len(dev_labels),
        "train_positive_count": int(train_labels.sum()),
        "dev_positive_count": int(dev_labels.sum()),
    }
    return FrozenLearnedControlArtifact.model_validate(
        {
            **unsigned,
            "artifact_sha256": sha256_text(canonical_json(unsigned)),
        }
    )


class LearnedNextUseMemorySystem:
    """Frozen query-blind prefix selector trained from next-use labels."""

    identity = "learned-next-use-memory-v1"

    def __init__(self, artifact: FrozenLearnedControlArtifact) -> None:
        self.artifact = artifact
        config = {
            "artifact_sha256": artifact.artifact_sha256,
            "split_manifest_sha256": artifact.split_manifest_sha256,
            "feature_names": list(artifact.feature_names),
            "forbidden_policy_inputs": list(artifact.forbidden_policy_inputs),
            "label_rule_version": artifact.label_rule_version,
            "ranking": "descending-logit-recency-id",
        }
        self.receipt = MemorySystemReceipt(
            system_id=self.identity,
            implementation_kind="in_process_reference",
            implementation_revision=(
                "harness.memory_trials.learned_control:learned-next-use-v1"
            ),
            configuration_sha256=sha256_text(canonical_json(config)),
            backend_id="python-numpy-float64",
        )

    def _score(self, vector: tuple[float, ...]) -> float:
        normalized = (
            (np.asarray(vector, dtype=np.float64) - self.artifact.feature_means)
            / self.artifact.feature_scales
        )
        return float(
            normalized @ np.asarray(self.artifact.coefficients, dtype=np.float64)
            + self.artifact.intercept
        )

    def select(self, request: MemorySystemRequest) -> MemorySelection:
        ranked = sorted(
            (
                (record, self._score(vector))
                for record, vector in _feature_vectors(request)
                if record.valid
            ),
            key=lambda item: (-item[1], -item[0].written_step, item[0].source_record_id),
        )[: request.budget.retrieval_top_k]
        ranked_evidence = tuple(
            _record_evidence(record, score=score) for record, score in ranked
        )
        evidence = _fit_evidence_budget(request, ranked_evidence)
        return _seal_selection(
            request,
            evidence,
            _costs(request, evidence),
            self.receipt,
        )
