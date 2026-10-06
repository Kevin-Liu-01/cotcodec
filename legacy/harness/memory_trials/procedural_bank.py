"""Frozen procedural-memory bank with held-out retrieval invariants.

The bank is built from TRAIN workflow families and becomes immutable before
DEV or TEST retrieval.  It owns split enforcement, source lineage, frozen
document vectors, query-only embedding, ranking, byte/token budgeting, and
content-addressed receipts.  Provider/model execution stays behind the existing
``DenseEmbeddingPort`` seam.
"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from harness.memory_trials.dense_control import (
    BGE_QUERY_INSTRUCTION,
    DenseEmbeddingIdentity,
    DenseEmbeddingPort,
)
from harness.memory_trials.schema import canonical_json, sha256_text

REASONINGBANK_REPOSITORY = "https://github.com/google-research/reasoning-bank"
REASONINGBANK_REVISION = "ed80611788292ea739f1effd31f16c53823b8a0d"
REASONINGBANK_ARCHIVE_SHA256 = (
    "d85d169c84f82782cefc50044adc192ab1d28956f36e177de0bf213d48298e09"
)
_TRUNCATION_MARKER = "\n[truncated to procedural-memory budget]"

ProceduralOutcome = Literal["success", "failure"]
EvaluationSplit = Literal["dev", "test"]


class ProceduralTaskRef(BaseModel):
    """One task and its workflow-family identity in a frozen split."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    task_id: str = Field(min_length=1)
    workflow_family_id: str = Field(min_length=1)


class ProceduralSplitManifest(BaseModel):
    """Content-addressed, family-disjoint task split used by the bank."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["procedural-split-manifest-v1"] = (
        "procedural-split-manifest-v1"
    )
    train: tuple[ProceduralTaskRef, ...] = Field(min_length=1)
    dev: tuple[ProceduralTaskRef, ...] = Field(min_length=1)
    test: tuple[ProceduralTaskRef, ...] = Field(min_length=1)
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_manifest(self) -> ProceduralSplitManifest:
        all_task_ids: list[str] = []
        family_sets: list[set[str]] = []
        for split_name in ("train", "dev", "test"):
            rows = getattr(self, split_name)
            if tuple(sorted(rows, key=lambda row: row.task_id)) != rows:
                raise ValueError(f"{split_name} task rows must be sorted by task_id")
            task_ids = [row.task_id for row in rows]
            if len(set(task_ids)) != len(task_ids):
                raise ValueError(f"{split_name} task IDs must be unique")
            if any(
                re.search(r"(?:^|[-_])(train|dev|test)$", row.workflow_family_id, re.I)
                for row in rows
            ):
                raise ValueError(
                    "workflow family IDs must be canonical and cannot use split suffixes"
                )
            all_task_ids.extend(task_ids)
            family_sets.append({row.workflow_family_id for row in rows})
        if len(set(all_task_ids)) != len(all_task_ids):
            raise ValueError("procedural task IDs overlap across splits")
        if any(
            family_sets[left] & family_sets[right]
            for left, right in ((0, 1), (0, 2), (1, 2))
        ):
            raise ValueError("procedural workflow families overlap across splits")
        unsigned = self.model_dump(mode="json", exclude={"manifest_sha256"})
        if self.manifest_sha256 != sha256_text(canonical_json(unsigned)):
            raise ValueError("procedural split manifest digest drifted")
        return self


def seal_procedural_split_manifest(
    *,
    train: Sequence[ProceduralTaskRef],
    dev: Sequence[ProceduralTaskRef],
    test: Sequence[ProceduralTaskRef],
) -> ProceduralSplitManifest:
    """Sort and content-address one exact train/dev/test roster."""

    unsigned = {
        "schema_version": "procedural-split-manifest-v1",
        "train": [
            row.model_dump(mode="json")
            for row in sorted(train, key=lambda row: row.task_id)
        ],
        "dev": [
            row.model_dump(mode="json")
            for row in sorted(dev, key=lambda row: row.task_id)
        ],
        "test": [
            row.model_dump(mode="json")
            for row in sorted(test, key=lambda row: row.task_id)
        ],
    }
    return ProceduralSplitManifest.model_validate(
        {
            **unsigned,
            "manifest_sha256": sha256_text(canonical_json(unsigned)),
        }
    )


class ProceduralBankItemInput(BaseModel):
    """One framework-visible procedure with complete TRAIN lineage."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_task_id: str = Field(min_length=1)
    source_family_id: str = Field(min_length=1)
    source_query: str = Field(min_length=1)
    outcome: ProceduralOutcome
    procedural_text: str = Field(min_length=1)
    source_trajectory_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    correctness_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    generator_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ProceduralBankItem(ProceduralBankItemInput):
    """Content-addressed item stored in the frozen bank."""

    item_id: str = Field(pattern=r"^procedure-[0-9a-f]{20}$")

    @model_validator(mode="after")
    def validate_item_id(self) -> ProceduralBankItem:
        payload = self.model_dump(mode="json", exclude={"item_id"})
        expected = f"procedure-{sha256_text(canonical_json(payload))[:20]}"
        if self.item_id != expected:
            raise ValueError("procedural item ID does not bind its content")
        return self


class FrozenProceduralBankArtifact(BaseModel):
    """Immutable TRAIN-only procedural bank and document index."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["frozen-procedural-bank-v1"] = "frozen-procedural-bank-v1"
    system_id: Literal["reasoningbank-frozen-procedural-v1"] = (
        "reasoningbank-frozen-procedural-v1"
    )
    source_repository: Literal[
        "https://github.com/google-research/reasoning-bank"
    ] = REASONINGBANK_REPOSITORY
    source_revision: Literal[
        "ed80611788292ea739f1effd31f16c53823b8a0d"
    ] = REASONINGBANK_REVISION
    source_archive_sha256: Literal[
        "d85d169c84f82782cefc50044adc192ab1d28956f36e177de0bf213d48298e09"
    ] = REASONINGBANK_ARCHIVE_SHA256
    split_manifest: ProceduralSplitManifest
    label_splits: tuple[Literal["train"], ...] = ("train",)
    document_text_field: Literal["procedural_text"] = "procedural_text"
    embedding_identity: DenseEmbeddingIdentity
    items: tuple[ProceduralBankItem, ...] = Field(min_length=1)
    document_vectors: tuple[tuple[float, ...], ...] = Field(min_length=1)
    construction_embedding_requests: Literal[1] = 1
    construction_embedding_inputs: int = Field(ge=1)
    construction_prompt_tokens: int = Field(ge=0)
    source_input_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_artifact(self) -> FrozenProceduralBankArtifact:
        if self.label_splits != ("train",):
            raise ValueError("procedural labels must be TRAIN-only")
        if tuple(sorted(self.items, key=lambda item: item.item_id)) != self.items:
            raise ValueError("procedural items must be sorted by item_id")
        if len({item.item_id for item in self.items}) != len(self.items):
            raise ValueError("procedural item IDs must be unique")
        train_pairs = {
            (row.task_id, row.workflow_family_id) for row in self.split_manifest.train
        }
        if any(
            (item.source_task_id, item.source_family_id) not in train_pairs
            for item in self.items
        ):
            raise ValueError("procedural item lineage escapes the TRAIN split")
        if len(self.document_vectors) != len(self.items):
            raise ValueError("document-vector count differs from procedural items")
        if self.construction_embedding_inputs != len(self.items):
            raise ValueError("construction embedding count differs from procedural items")
        dimensions = self.embedding_identity.dimensions
        for vector in self.document_vectors:
            if len(vector) != dimensions or not all(math.isfinite(value) for value in vector):
                raise ValueError("procedural document vector is invalid")
            norm = math.sqrt(sum(value * value for value in vector))
            if not math.isclose(norm, 1.0, rel_tol=1e-4, abs_tol=1e-4):
                raise ValueError("procedural document vector is not L2-normalized")
        item_payloads = [
            item.model_dump(mode="json", exclude={"item_id"}) for item in self.items
        ]
        if self.source_input_sha256 != sha256_text(canonical_json(item_payloads)):
            raise ValueError("procedural source input digest drifted")
        unsigned = self.model_dump(mode="json", exclude={"artifact_sha256"})
        if self.artifact_sha256 != sha256_text(canonical_json(unsigned)):
            raise ValueError("procedural bank artifact digest drifted")
        return self


class ProceduralQuery(BaseModel):
    """One held-out retrieval query; split fields are audit-only."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["procedural-query-v1"] = "procedural-query-v1"
    request_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    workflow_family_id: str = Field(min_length=1)
    split: EvaluationSplit
    text: str = Field(min_length=1)
    top_k: int = Field(default=1, ge=1, le=10)
    max_injected_tokens: int = Field(default=256, ge=1)


class ProceduralHit(BaseModel):
    """Actor-visible procedure plus immutable TRAIN lineage."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    item_id: str = Field(pattern=r"^procedure-[0-9a-f]{20}$")
    procedural_text: str = Field(min_length=1)
    outcome: ProceduralOutcome
    source_task_id: str = Field(min_length=1)
    source_family_id: str = Field(min_length=1)
    source_trajectory_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    correctness_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    generator_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    score: float = Field(allow_inf_nan=False)
    truncated: bool


class ProceduralRetrieval(BaseModel):
    """Content-addressed retrieval receipt with no mutable bank state."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    request_id: str = Field(min_length=1)
    query_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    bank_artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    embedding_model_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    hits: tuple[ProceduralHit, ...]
    serialized_input_bytes: int = Field(ge=0)
    serialized_output_bytes: int = Field(ge=0)
    injected_tokens_estimate: int = Field(ge=0)
    embedding_calls: Literal[1] = 1
    query_embedding_prompt_tokens: int = Field(ge=0)
    retrieval_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_retrieval(self) -> ProceduralRetrieval:
        unsigned = self.model_dump(mode="json", exclude={"retrieval_sha256"})
        if self.retrieval_sha256 != sha256_text(canonical_json(unsigned)):
            raise ValueError("procedural retrieval digest mismatch")
        return self


def _seal_item(item: ProceduralBankItemInput) -> ProceduralBankItem:
    payload = item.model_dump(mode="json")
    return ProceduralBankItem(
        **payload,
        item_id=f"procedure-{sha256_text(canonical_json(payload))[:20]}",
    )


def freeze_procedural_bank(
    items: Sequence[ProceduralBankItemInput],
    *,
    split_manifest: ProceduralSplitManifest,
    embedding: DenseEmbeddingPort,
) -> FrozenProceduralBankArtifact:
    """Freeze TRAIN procedures and source-query vectors into one artifact."""

    if not items:
        raise ValueError("procedural bank requires at least one item")
    sealed_items = tuple(
        sorted((_seal_item(item) for item in items), key=lambda item: item.item_id)
    )
    batch = embedding.embed([item.procedural_text for item in sealed_items])
    unsigned = {
        "schema_version": "frozen-procedural-bank-v1",
        "system_id": "reasoningbank-frozen-procedural-v1",
        "source_repository": REASONINGBANK_REPOSITORY,
        "source_revision": REASONINGBANK_REVISION,
        "source_archive_sha256": REASONINGBANK_ARCHIVE_SHA256,
        "split_manifest": split_manifest.model_dump(mode="json"),
        "label_splits": ["train"],
        "document_text_field": "procedural_text",
        "embedding_identity": embedding.identity.model_dump(mode="json"),
        "items": [item.model_dump(mode="json") for item in sealed_items],
        "document_vectors": [list(vector) for vector in batch.vectors],
        "construction_embedding_requests": batch.request_count,
        "construction_embedding_inputs": batch.input_count,
        "construction_prompt_tokens": batch.prompt_tokens,
        "source_input_sha256": sha256_text(
            canonical_json(
                [
                    item.model_dump(mode="json", exclude={"item_id"})
                    for item in sealed_items
                ]
            )
        ),
    }
    return FrozenProceduralBankArtifact.model_validate(
        {
            **unsigned,
            "artifact_sha256": sha256_text(canonical_json(unsigned)),
        }
    )


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    return float(sum(a * b for a, b in zip(left, right, strict=True)))


def _token_estimate(hits: Sequence[ProceduralHit]) -> int:
    payload = [
        {"item_id": hit.item_id, "procedural_text": hit.procedural_text}
        for hit in hits
    ]
    return (len(canonical_json(payload).encode("utf-8")) + 3) // 4


def _fit_budget(
    ranked: Sequence[ProceduralHit],
    *,
    max_tokens: int,
) -> tuple[ProceduralHit, ...]:
    selected: list[ProceduralHit] = []
    for candidate in ranked:
        if _token_estimate((*selected, candidate)) <= max_tokens:
            selected.append(candidate)
            continue
        low = 0
        high = len(candidate.procedural_text)
        best: ProceduralHit | None = None
        while low <= high:
            midpoint = (low + high) // 2
            text = candidate.procedural_text[:midpoint].rstrip() + _TRUNCATION_MARKER
            truncated = candidate.model_copy(
                update={"procedural_text": text, "truncated": True}
            )
            if _token_estimate((*selected, truncated)) <= max_tokens:
                best = truncated
                low = midpoint + 1
            else:
                high = midpoint - 1
        if best is not None:
            selected.append(best)
        break
    return tuple(selected)


class FrozenProceduralBankRetriever:
    """Query-only retriever over a sealed TRAIN bank."""

    identity = "reasoningbank-frozen-procedural-v1"

    def __init__(
        self,
        artifact: FrozenProceduralBankArtifact,
        embedding: DenseEmbeddingPort,
    ) -> None:
        if embedding.identity != artifact.embedding_identity:
            raise ValueError("query embedder identity differs from frozen bank")
        self.artifact = artifact
        self._embedding = embedding

    def retrieve(self, query: ProceduralQuery) -> ProceduralRetrieval:
        train_task_ids = {row.task_id for row in self.artifact.split_manifest.train}
        if query.task_id in train_task_ids:
            raise ValueError("held-out query task is present in the TRAIN bank")
        registered_rows = getattr(self.artifact.split_manifest, query.split)
        registered_pairs = {
            (row.task_id, row.workflow_family_id) for row in registered_rows
        }
        if (query.task_id, query.workflow_family_id) not in registered_pairs:
            raise ValueError("query task/family pair is not registered for its split")
        batch = self._embedding.embed((BGE_QUERY_INSTRUCTION + query.text,))
        query_vector = batch.vectors[0]
        ranked_pairs = sorted(
            zip(self.artifact.items, self.artifact.document_vectors, strict=True),
            key=lambda pair: (
                -_cosine(query_vector, pair[1]),
                pair[0].item_id,
            ),
        )[: query.top_k]
        ranked = tuple(
            ProceduralHit(
                item_id=item.item_id,
                procedural_text=item.procedural_text,
                outcome=item.outcome,
                source_task_id=item.source_task_id,
                source_family_id=item.source_family_id,
                source_trajectory_sha256=item.source_trajectory_sha256,
                correctness_receipt_sha256=item.correctness_receipt_sha256,
                generator_receipt_sha256=item.generator_receipt_sha256,
                score=_cosine(query_vector, vector),
                truncated=False,
            )
            for item, vector in ranked_pairs
        )
        hits = _fit_budget(ranked, max_tokens=query.max_injected_tokens)
        input_bytes = len(canonical_json(query.model_dump(mode="json")).encode("utf-8"))
        output_bytes = len(
            canonical_json([hit.model_dump(mode="json") for hit in hits]).encode("utf-8")
        )
        unsigned = {
            "request_id": query.request_id,
            "query_sha256": sha256_text(canonical_json(query.model_dump(mode="json"))),
            "bank_artifact_sha256": self.artifact.artifact_sha256,
            "embedding_model_receipt_sha256": (
                self.artifact.embedding_identity.model_receipt_sha256
            ),
            "hits": [hit.model_dump(mode="json") for hit in hits],
            "serialized_input_bytes": input_bytes,
            "serialized_output_bytes": output_bytes,
            "injected_tokens_estimate": _token_estimate(hits),
            "embedding_calls": 1,
            "query_embedding_prompt_tokens": batch.prompt_tokens,
        }
        return ProceduralRetrieval.model_validate(
            {
                **unsigned,
                "retrieval_sha256": sha256_text(canonical_json(unsigned)),
            }
        )
