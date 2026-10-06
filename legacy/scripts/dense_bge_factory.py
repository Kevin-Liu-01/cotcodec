"""Build the pinned dense-BGE control from verified local model artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from harness.memory_trials.dense_control import (
    BGE_POOLING_STRATEGY,
    BGE_SMALL_EN_V15_REGISTRY_ID,
    DenseBGERetrievalMemorySystem,
    DenseEmbeddingIdentity,
    DenseEmbeddingPort,
    DenseVectorEncoder,
    InProcessDenseEmbeddingClient,
)
from scripts.fetch_open_model import (
    DEFAULT_MODEL_ROOT,
    DEFAULT_RECEIPT_ROOT,
    DEFAULT_REGISTRY,
    load_registry,
    receipt_path,
    sha256_file,
    verify_receipt,
)


def build_dense_bge_embedding(
    *,
    registry_path: Path = DEFAULT_REGISTRY,
    model_root: Path = DEFAULT_MODEL_ROOT,
    receipt_root: Path = DEFAULT_RECEIPT_ROOT,
    model_id: str = BGE_SMALL_EN_V15_REGISTRY_ID,
    encoder: DenseVectorEncoder | None = None,
) -> DenseEmbeddingPort:
    """Verify the immutable BGE snapshot and return its embedding port."""

    registry_path = registry_path.resolve()
    model_root = model_root.resolve()
    receipt_root = receipt_root.resolve()
    registry = load_registry(registry_path)
    entry = registry["models"].get(model_id)
    if model_id != BGE_SMALL_EN_V15_REGISTRY_ID or not isinstance(entry, dict):
        raise ValueError("dense retrieval requires the registered BGE small v1.5 model")
    if (
        entry.get("backend") != "huggingface"
        or entry.get("repo_id") != "BAAI/bge-small-en-v1.5"
        or entry.get("trust_remote_code") is not False
        or entry.get("publication_eligible") is not True
    ):
        raise ValueError("dense BGE registry entry is not publication eligible")
    receipt = verify_receipt(model_id, entry, model_root, receipt_root)
    if (
        receipt.get("mode") != "full"
        or receipt.get("publication_eligible") is not True
        or receipt.get("revision") != entry["revision"]
    ):
        raise ValueError("dense BGE requires a full publication-eligible receipt")
    identity = DenseEmbeddingIdentity(
        model=entry["repo_id"],
        registry_model_id=model_id,
        revision=entry["revision"],
        artifact_root_sha256=receipt["artifact_root_sha256"],
        model_receipt_sha256=sha256_file(receipt_path(receipt_root, model_id)),
        dimensions=384,
        maximum_tokens=512,
        pooling_strategy=BGE_POOLING_STRATEGY,
        publication_eligible=True,
    )
    if encoder is None:
        from scripts.run_hf_embedding_server import TransformersEmbeddingBackend

        encoder = TransformersEmbeddingBackend(
            model_root / model_id,
            maximum_tokens=identity.maximum_tokens,
        )
    return InProcessDenseEmbeddingClient(encoder, identity)


def build_dense_bge_system(
    *,
    registry_path: Path = DEFAULT_REGISTRY,
    model_root: Path = DEFAULT_MODEL_ROOT,
    receipt_root: Path = DEFAULT_RECEIPT_ROOT,
    model_id: str = BGE_SMALL_EN_V15_REGISTRY_ID,
    encoder: DenseVectorEncoder | None = None,
) -> DenseBGERetrievalMemorySystem:
    """Verify the immutable BGE snapshot and return the matched dense control."""

    embedding = build_dense_bge_embedding(
        registry_path=registry_path,
        model_root=model_root,
        receipt_root=receipt_root,
        model_id=model_id,
        encoder=encoder,
    )
    return DenseBGERetrievalMemorySystem(embedding)


def dense_system_receipt(
    *,
    registry_path: Path = DEFAULT_REGISTRY,
    model_root: Path = DEFAULT_MODEL_ROOT,
    receipt_root: Path = DEFAULT_RECEIPT_ROOT,
    encoder: DenseVectorEncoder | None = None,
) -> dict[str, Any]:
    """Small doctor surface used by tests and launch preflights."""

    return build_dense_bge_system(
        registry_path=registry_path,
        model_root=model_root,
        receipt_root=receipt_root,
        encoder=encoder,
    ).receipt.model_dump(mode="json")
