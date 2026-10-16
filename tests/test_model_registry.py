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


def _gguf_entry() -> dict:
    entry = copy.deepcopy(load_registry(DEFAULT_REGISTRY)["models"]["smollm2-135m"])
    entry["metadata_files"] = ["README.md"]
    entry["required_files"] = ["README.md", "Q2/model-00001-of-00002.gguf"]
    entry["allow_patterns"] = ["README.md", "Q2/*"]
    return entry


def test_allow_patterns_must_cover_every_required_file() -> None:
    entry = _gguf_entry()
    validate_entry("subset", entry)
    entry["allow_patterns"] = ["README.md", "Q4/*"]
    with pytest.raises(ModelRegistryError, match="exclude required files"):
        validate_entry("subset", entry)


@pytest.mark.parametrize("patterns", [[], "Q2/*", ["Q2/*", ""], ["Q2/* "], [3]])
def test_allow_patterns_must_be_a_nonempty_string_list(patterns: object) -> None:
    entry = _gguf_entry()
    entry["allow_patterns"] = patterns
    with pytest.raises(ModelRegistryError, match="allow_patterns"):
        validate_entry("subset", entry)


def test_full_fetch_downloads_only_the_allowed_subset_and_records_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sys
    import types

    from scripts.fetch_open_model import fetch_huggingface

    entry = _gguf_entry()
    calls: list[dict] = []

    class FakeApi:
        def model_info(self, repo_id: str, revision: str) -> types.SimpleNamespace:
            return types.SimpleNamespace(sha=revision)

    def fake_snapshot_download(**kwargs: object) -> None:
        calls.append(kwargs)
        root = Path(str(kwargs["local_dir"]))
        for name in ("README.md", "Q2/model-00001-of-00002.gguf"):
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            (root / name).write_text(f"fixture:{name}\n", encoding="utf-8")

    fake = types.ModuleType("huggingface_hub")
    fake.HfApi = FakeApi  # type: ignore[attr-defined]
    fake.snapshot_download = fake_snapshot_download  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "huggingface_hub", fake)

    registry_path = tmp_path / "registry.yaml"
    registry_path.write_text("schema_version: 1\n", encoding="utf-8")
    receipt = fetch_huggingface(
        "subset", entry, registry_path, tmp_path / "models", tmp_path / "receipts", False
    )
    assert calls[0]["allow_patterns"] == ["README.md", "Q2/*"]
    assert receipt["allow_patterns"] == ["README.md", "Q2/*"]
    assert receipt["mode"] == "full"
    assert [item["path"] for item in receipt["files"]] == [
        "Q2/model-00001-of-00002.gguf",
        "README.md",
    ]

    metadata = fetch_huggingface(
        "subset", entry, registry_path, tmp_path / "models2", tmp_path / "receipts2", True
    )
    assert calls[1]["allow_patterns"] == entry["metadata_files"]
    assert "allow_patterns" not in metadata


def test_unfiltered_full_fetch_keeps_the_original_receipt_shape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sys
    import types

    from scripts.fetch_open_model import fetch_huggingface

    entry = copy.deepcopy(load_registry(DEFAULT_REGISTRY)["models"]["smollm2-135m"])
    calls: list[dict] = []

    class FakeApi:
        def model_info(self, repo_id: str, revision: str) -> types.SimpleNamespace:
            return types.SimpleNamespace(sha=revision)

    def fake_snapshot_download(**kwargs: object) -> None:
        calls.append(kwargs)
        root = Path(str(kwargs["local_dir"]))
        for name in entry["required_files"]:
            (root / name).write_text("x\n", encoding="utf-8")

    fake = types.ModuleType("huggingface_hub")
    fake.HfApi = FakeApi  # type: ignore[attr-defined]
    fake.snapshot_download = fake_snapshot_download  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "huggingface_hub", fake)
    registry_path = tmp_path / "registry.yaml"
    registry_path.write_text("schema_version: 1\n", encoding="utf-8")
    receipt = fetch_huggingface(
        "smollm2-135m", entry, registry_path, tmp_path / "m", tmp_path / "r", False
    )
    assert calls[0]["allow_patterns"] is None
    assert "allow_patterns" not in receipt
