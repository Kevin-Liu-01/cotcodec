from __future__ import annotations

import hashlib
import math
import re

import pytest
from pydantic import ValidationError

from harness.memory_trials import (
    FrozenProceduralBankArtifact,
    FrozenProceduralBankRetriever,
    ProceduralBankItemInput,
    ProceduralQuery,
    ProceduralSplitManifest,
    ProceduralTaskRef,
    freeze_procedural_bank,
    seal_procedural_split_manifest,
)
from harness.memory_trials.dense_control import (
    BGE_POOLING_STRATEGY,
    DenseEmbeddingIdentity,
    InProcessDenseEmbeddingClient,
)
from harness.memory_trials.schema import canonical_json


class TokenHashEncoder:
    dimensions = 384
    maximum_tokens = 512
    pooling_strategy = BGE_POOLING_STRATEGY

    def embed(self, texts):
        vectors = []
        prompt_tokens = 0
        for text in texts:
            tokens = re.findall(r"[a-z0-9]+", text.casefold())
            prompt_tokens += len(tokens)
            row = [0.0] * self.dimensions
            for token in tokens:
                index = int.from_bytes(
                    hashlib.sha256(token.encode("utf-8")).digest()[:4], "big"
                ) % self.dimensions
                row[index] += 1.0
            norm = math.sqrt(sum(value * value for value in row))
            if norm == 0:
                row[0] = 1.0
                norm = 1.0
            vectors.append([value / norm for value in row])
        return vectors, prompt_tokens


def _identity(marker: str = "1") -> DenseEmbeddingIdentity:
    return DenseEmbeddingIdentity(
        artifact_root_sha256=marker * 64,
        model_receipt_sha256=("2" if marker == "1" else "3") * 64,
    )


def _embedding(marker: str = "1") -> InProcessDenseEmbeddingClient:
    return InProcessDenseEmbeddingClient(TokenHashEncoder(), _identity(marker))


def _item(
    task: str,
    family: str,
    query: str,
    text: str,
    outcome: str,
) -> ProceduralBankItemInput:
    marker = hashlib.sha256(task.encode("utf-8")).hexdigest()
    return ProceduralBankItemInput(
        source_task_id=task,
        source_family_id=family,
        source_query=query,
        outcome=outcome,
        procedural_text=text,
        source_trajectory_sha256=marker,
        correctness_receipt_sha256=hashlib.sha256(
            f"correct:{task}".encode()
        ).hexdigest(),
        generator_receipt_sha256=hashlib.sha256(
            f"generator:{task}".encode()
        ).hexdigest(),
    )


def _manifest():
    return seal_procedural_split_manifest(
        train=(
            ProceduralTaskRef(task_id="train-reset", workflow_family_id="admin"),
            ProceduralTaskRef(task_id="train-flight", workflow_family_id="travel"),
        ),
        dev=(
            ProceduralTaskRef(task_id="dev-reset-1", workflow_family_id="dev-admin"),
        ),
        test=(
            ProceduralTaskRef(task_id="test-reset-1", workflow_family_id="test-admin"),
            ProceduralTaskRef(task_id="test-reset-2", workflow_family_id="test-admin"),
        ),
    )


def _bank() -> FrozenProceduralBankArtifact:
    return freeze_procedural_bank(
        (
            _item(
                "train-reset",
                "admin",
                "reset postgres password safely",
                "Check the target role, rotate the credential, then verify login.",
                "failure",
            ),
            _item(
                "train-flight",
                "travel",
                "book an international flight",
                "Compare dates and fare rules before booking the flight.",
                "success",
            ),
        ),
        split_manifest=_manifest(),
        embedding=_embedding(),
    )


def test_frozen_bank_retrieves_train_procedure_for_held_out_family() -> None:
    bank = _bank()
    before = canonical_json(bank.model_dump(mode="json"))
    retriever = FrozenProceduralBankRetriever(bank, _embedding())
    query = ProceduralQuery(
        request_id="request-test-1",
        task_id="test-reset-1",
        workflow_family_id="test-admin",
        split="test",
        text="reset the postgres password",
        top_k=1,
        max_injected_tokens=128,
    )
    first = retriever.retrieve(query)
    second = retriever.retrieve(query)
    assert first == second
    assert first.hits[0].source_task_id == "train-reset"
    assert first.hits[0].outcome == "failure"
    assert first.embedding_calls == 1
    assert first.query_embedding_prompt_tokens > 0
    assert canonical_json(bank.model_dump(mode="json")) == before


def test_freeze_rejects_item_outside_train_families() -> None:
    with pytest.raises(ValidationError, match="escapes the TRAIN split"):
        freeze_procedural_bank(
            (_item("train-reset", "dev-admin", "reset password", "verify", "success"),),
            split_manifest=_manifest(),
            embedding=_embedding(),
        )


def test_freeze_rejects_overlapping_workflow_families() -> None:
    with pytest.raises(ValidationError, match="families overlap"):
        seal_procedural_split_manifest(
            train=(
                ProceduralTaskRef(task_id="train-reset", workflow_family_id="admin"),
            ),
            dev=(
                ProceduralTaskRef(task_id="dev-reset", workflow_family_id="admin"),
            ),
            test=(
                ProceduralTaskRef(
                    task_id="test-reset", workflow_family_id="test-admin"
                ),
            ),
        )


def test_split_manifest_rejects_split_suffix_family_aliases() -> None:
    with pytest.raises(ValidationError, match="cannot use split suffixes"):
        seal_procedural_split_manifest(
            train=(
                ProceduralTaskRef(
                    task_id="train-reset",
                    workflow_family_id="database-train",
                ),
            ),
            dev=(
                ProceduralTaskRef(
                    task_id="dev-reset",
                    workflow_family_id="credential-rotation",
                ),
            ),
            test=(
                ProceduralTaskRef(
                    task_id="test-reset",
                    workflow_family_id="certificate-renewal",
                ),
            ),
        )


def test_split_manifest_rejects_digest_tampering() -> None:
    payload = _manifest().model_dump(mode="json")
    payload["manifest_sha256"] = "0" * 64
    with pytest.raises(ValidationError, match="split manifest digest drifted"):
        ProceduralSplitManifest.model_validate(payload)


def test_retrieval_rejects_train_task_and_wrong_test_family() -> None:
    retriever = FrozenProceduralBankRetriever(_bank(), _embedding())
    with pytest.raises(ValueError, match="task is present in the TRAIN bank"):
        retriever.retrieve(
            ProceduralQuery(
                request_id="request-train",
                task_id="train-reset",
                workflow_family_id="test-admin",
                split="test",
                text="reset password",
            )
        )
    with pytest.raises(ValueError, match="task/family pair is not registered"):
        retriever.retrieve(
            ProceduralQuery(
                request_id="request-wrong-family",
                task_id="test-reset-2",
                workflow_family_id="unregistered-family",
                split="test",
                text="reset password",
            )
        )


def test_retriever_rejects_embedding_identity_drift() -> None:
    with pytest.raises(ValueError, match="identity differs"):
        FrozenProceduralBankRetriever(_bank(), _embedding("4"))


def test_artifact_rejects_vector_or_digest_tampering() -> None:
    bank = _bank()
    payload = bank.model_dump(mode="json")
    payload["document_vectors"][0][0] += 0.5
    with pytest.raises(ValidationError, match="not L2-normalized|artifact digest"):
        FrozenProceduralBankArtifact.model_validate(payload)


def test_document_vectors_use_actor_visible_procedural_text_not_source_query() -> None:
    original = _item(
        "train-reset",
        "admin",
        "hidden source task description",
        "Check the target role, rotate the credential, then verify login.",
        "success",
    )
    renamed_query = original.model_copy(
        update={"source_query": "unrelated hidden source description"}
    )
    base_manifest = _manifest()
    one_item_manifest = seal_procedural_split_manifest(
        train=(
            ProceduralTaskRef(
                task_id="train-reset",
                workflow_family_id="admin",
            ),
        ),
        dev=base_manifest.dev,
        test=base_manifest.test,
    )
    first = freeze_procedural_bank(
        (original,),
        split_manifest=one_item_manifest,
        embedding=_embedding(),
    )
    second = freeze_procedural_bank(
        (renamed_query,),
        split_manifest=first.split_manifest,
        embedding=_embedding(),
    )
    assert first.document_text_field == "procedural_text"
    assert first.document_vectors == second.document_vectors
    assert first.artifact_sha256 != second.artifact_sha256


def test_retrieval_truncates_to_registered_injection_budget() -> None:
    bank = _bank()
    retrieval = FrozenProceduralBankRetriever(bank, _embedding()).retrieve(
        ProceduralQuery(
            request_id="request-budget",
            task_id="dev-reset-1",
            workflow_family_id="dev-admin",
            split="dev",
            text="reset postgres password",
            top_k=2,
            max_injected_tokens=32,
        )
    )
    assert retrieval.injected_tokens_estimate <= 32
    assert retrieval.hits
    assert retrieval.hits[0].truncated is True
