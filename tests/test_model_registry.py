from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.fetch_open_model import (
    DEFAULT_REGISTRY,
    ModelRegistryError,
    artifact_root,
    load_registry,
    snapshot_files,
    validate_entry,
    verify_receipt,
)


def test_live_registry_is_valid_and_contains_kimi() -> None:
    registry = load_registry(DEFAULT_REGISTRY)
    assert registry["models"]["bge-small-en-v1.5"]["revision"] == (
        "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"
    )
    assert "kimi-linear-48b-a3b-base" in registry["models"]
    assert registry["models"]["kimi-linear-48b-a3b-base"]["trust_remote_code"] is True
    assert registry["models"]["kimi-linear-48b-a3b-base"]["publication_eligible"] is False


def test_huggingface_revision_must_be_immutable() -> None:
    entry = copy.deepcopy(load_registry(DEFAULT_REGISTRY)["models"]["smollm2-135m"])
    entry["revision"] = "main"
    with pytest.raises(ModelRegistryError, match="40-char commit"):
        validate_entry("smollm2-135m", entry)


def test_ollama_tag_cannot_be_publication_eligible() -> None:
    entry = copy.deepcopy(load_registry(DEFAULT_REGISTRY)["models"]["ollama-qwen3-0.6b"])
    entry["publication_eligible"] = True
    with pytest.raises(ModelRegistryError, match="cannot be publication-ready"):
        validate_entry("ollama-qwen3-0.6b", entry)


def test_receipt_detects_local_file_mutation(tmp_path: Path) -> None:
    registry = load_registry(DEFAULT_REGISTRY)
    entry = registry["models"]["smollm2-135m"]
    model_root = tmp_path / "models"
    snapshot = model_root / "smollm2-135m"
    snapshot.mkdir(parents=True)
    for required in entry["required_files"]:
        path = snapshot / required
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"fixture:{required}\n", encoding="utf-8")
    files = snapshot_files(snapshot)
    receipt_root = tmp_path / "receipts"
    receipt_root.mkdir()
    receipt = {
        "schema_version": 1,
        "model_id": "smollm2-135m",
        "backend": "huggingface",
        "revision": entry["revision"],
        "mode": "full",
        "files": files,
        "artifact_root_sha256": artifact_root(files),
    }
    (receipt_root / "smollm2-135m.json").write_text(
        json.dumps(receipt), encoding="utf-8"
    )
    verify_receipt("smollm2-135m", entry, model_root, receipt_root)

    (snapshot / "config.json").write_text("tampered\n", encoding="utf-8")
    with pytest.raises(ModelRegistryError, match="no longer match"):
        verify_receipt("smollm2-135m", entry, model_root, receipt_root)
