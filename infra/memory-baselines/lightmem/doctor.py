#!/usr/bin/env python3
"""Exact-source component falsifier for pinned LightMem 0.1.0."""

from __future__ import annotations

import argparse
import ast
import concurrent.futures as _concurrent_futures  # noqa: F401
import hashlib
import importlib.util
import json
import sys
import tempfile
import types
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

SOURCE_REVISION = "8fc9a9179f9170c4a40fc653fcb410375900f26e"
EXPECTED_STATUS = (
    "BLOCKED_DESTRUCTIVE_DEFAULT_REOPEN_AND_CONSOLIDATION_CONTRACT_DRIFT"
)


class DoctorError(RuntimeError):
    """Raised when an exact-source probe cannot establish its registered fact."""


class NullLogger:
    def debug(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    def info(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    def warning(self, *_args: Any, **_kwargs: Any) -> None:
        pass


def _sha(value: Any) -> str:
    data = json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(data).hexdigest()


def _module(name: str, **members: Any) -> types.ModuleType:
    module = types.ModuleType(name)
    for key, value in members.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _install_lightmem_import_stubs() -> None:
    class Placeholder:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            pass

    class ValidationError(Exception):
        pass

    _module("pydantic", ValidationError=ValidationError)
    _module("lightmem")
    _module("lightmem.configs")
    _module("lightmem.configs.base", BaseMemoryConfigs=Placeholder)
    _module("lightmem.factory")
    _module("lightmem.factory.pre_compressor")
    _module("lightmem.factory.pre_compressor.factory", PreCompressorFactory=Placeholder)
    _module("lightmem.factory.topic_segmenter")
    _module("lightmem.factory.topic_segmenter.factory", TopicSegmenterFactory=Placeholder)
    _module("lightmem.factory.memory_manager")
    _module("lightmem.factory.memory_manager.factory", MemoryManagerFactory=Placeholder)
    _module("lightmem.factory.text_embedder")
    _module("lightmem.factory.text_embedder.factory", TextEmbedderFactory=Placeholder)
    _module("lightmem.factory.retriever")
    _module("lightmem.factory.retriever.contextretriever")
    _module(
        "lightmem.factory.retriever.contextretriever.factory",
        ContextRetrieverFactory=Placeholder,
    )
    _module("lightmem.factory.retriever.embeddingretriever")
    _module(
        "lightmem.factory.retriever.embeddingretriever.factory",
        EmbeddingRetrieverFactory=Placeholder,
    )
    _module(
        "lightmem.factory.retriever.embeddingretriever.qdrant",
        QdrantConfig=Placeholder,
    )
    _module("lightmem.factory.memory_buffer")
    _module(
        "lightmem.factory.memory_buffer.sensory_memory",
        SenMemBufferManager=Placeholder,
    )
    _module(
        "lightmem.factory.memory_buffer.short_term_memory",
        ShortMemBufferManager=Placeholder,
    )
    _module("lightmem.memory")
    _module(
        "lightmem.memory.utils",
        save_memory_entries=lambda *_args, **_kwargs: None,
        strip_tags=lambda value: value,
        filter_by_tags=lambda **kwargs: (kwargs["results"], {"status": "stub"}),
        resolve_tags=lambda **_kwargs: ([], None),
        tag_text=lambda text, _tags: text,
    )
    _module(
        "lightmem.memory.prompts",
        METADATA_GENERATE_PROMPT="metadata",
        UPDATE_PROMPT="update",
    )
    _module("lightmem.configs.logging")
    _module("lightmem.configs.logging.utils", get_logger=lambda _name: NullLogger())


def _load_exact_lightmemory(source_root: Path) -> type:
    _install_lightmem_import_stubs()
    source = source_root / "src/lightmem/memory/lightmem.py"
    spec = importlib.util.spec_from_file_location("cotcodec_exact_lightmem", source)
    if spec is None or spec.loader is None:
        raise DoctorError("cannot load exact LightMem module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.LightMemory


class FakeEmbedder:
    def embed(self, text: str) -> list[float]:
        return [float(len(text)), 1.0]


class FakeRetriever:
    def __init__(self, entries: list[dict[str, Any]] | None = None):
        self.entries = {
            entry["id"]: deepcopy(entry) for entry in (entries or [])
        }

    def exists(self, record_id: str) -> bool:
        return record_id in self.entries

    def insert(self, vectors: list, payloads: list, ids: list) -> None:
        for vector, payload, record_id in zip(vectors, payloads, ids, strict=True):
            self.entries[record_id] = {
                "id": record_id,
                "vector": deepcopy(vector),
                "payload": deepcopy(payload),
            }

    def get_all(self) -> list[dict[str, Any]]:
        return [deepcopy(self.entries[key]) for key in sorted(self.entries)]

    def search(
        self,
        *,
        query_vector: list[float],
        limit: int,
        filters: dict[str, Any] | None = None,
        **_kwargs: Any,
    ) -> list[dict[str, Any]]:
        upper = ((filters or {}).get("float_time_stamp") or {}).get("lte", float("inf"))
        rows = [
            {"id": row["id"], "score": 0.99, "payload": deepcopy(row["payload"])}
            for row in self.entries.values()
            if row["payload"].get("float_time_stamp", 0) <= upper
        ]
        return sorted(rows, key=lambda row: row["id"])[:limit]

    def update(self, vector_id: str, vector: list, payload: dict[str, Any]) -> None:
        self.entries[vector_id] = {
            "id": vector_id,
            "vector": deepcopy(vector),
            "payload": deepcopy(payload),
        }

    def delete(self, vector_id: str) -> None:
        self.entries.pop(vector_id, None)


class UpdatingManager:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    def _call_update_llm(
        self,
        _prompt: str,
        target: dict[str, Any],
        sources: list[dict[str, Any]],
    ) -> dict[str, Any]:
        self.calls.append((target["id"], tuple(row["id"] for row in sources)))
        return {
            "action": "update",
            "new_memory": "corrected canonical fact",
            "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
        }


def _memory_entry(record_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=record_id,
        time_stamp="2026-08-16T00:00:00",
        float_time_stamp=1.0,
        weekday="Sun",
        topic_id=1,
        topic_summary="",
        category="",
        subcategory="",
        memory_class="",
        memory="original fact",
        original_memory="original fact",
        compressed_memory="",
        speaker_id="tenant-a",
        speaker_name="Tenant A",
        consolidated=False,
        bam_tags=[],
    )


def _test_lightmemory_methods(lightmemory: type) -> dict[str, bool]:
    online = lightmemory.__new__(lightmemory)
    marker = ["unchanged"]
    online_result = online.online_update(marker)

    trigger = lightmemory.__new__(lightmemory)
    trigger.logger = NullLogger()
    trigger.config = SimpleNamespace(index_strategy="embedding")
    trigger.text_embedder = FakeEmbedder()
    trigger.embedding_retriever = FakeRetriever()
    trigger.manager = UpdatingManager()
    trigger.token_stats = {"update_calls": 0, "update_prompt_tokens": 0,
                           "update_completion_tokens": 0, "update_total_tokens": 0}
    trigger_error = ""
    try:
        trigger.offline_update([_memory_entry("trigger")], offline_update_trigger=True)
    except TypeError as exc:
        trigger_error = str(exc)

    old_vector = [7.0, 3.0]
    entries = [
        {
            "id": "old",
            "vector": old_vector,
            "payload": {"float_time_stamp": 1.0, "memory": "old fact"},
        },
        {
            "id": "new",
            "vector": [8.0, 4.0],
            "payload": {"float_time_stamp": 2.0, "memory": "new correction"},
        },
    ]
    consolidation = lightmemory.__new__(lightmemory)
    consolidation.logger = NullLogger()
    consolidation.embedding_retriever = FakeRetriever(entries)
    consolidation.manager = UpdatingManager()
    consolidation.token_stats = {"update_calls": 0, "update_prompt_tokens": 0,
                                  "update_completion_tokens": 0, "update_total_tokens": 0}
    consolidation.construct_update_queue_all_entries(max_workers=1)
    old_queue = consolidation.embedding_retriever.entries["old"]["payload"].get(
        "update_queue", []
    )
    new_queue = consolidation.embedding_retriever.entries["new"]["payload"].get(
        "update_queue", []
    )
    consolidation.offline_update_all_entries(score_threshold=0.8, max_workers=1)
    updated_old = consolidation.embedding_retriever.entries["old"]

    context = lightmemory.__new__(lightmemory)
    context.logger = NullLogger()
    context.context_retriever = object()
    context_error = ""
    try:
        context.retrieve("query", limit=1)
    except AttributeError as exc:
        context_error = str(exc)

    public_methods = {
        name for name, value in vars(lightmemory).items()
        if callable(value) and not name.startswith("_")
    }
    return {
        "online_update_is_noop": online_result is None and marker == ["unchanged"],
        "automatic_offline_trigger_raises_keyword_typeerror": (
            "update_sim_threshold" in trigger_error
        ),
        "update_queue_points_later_source_to_earlier_target": (
            old_queue == []
            and [item["id"] for item in new_queue] == ["old"]
            and consolidation.manager.calls == [("old", ("new",))]
        ),
        "offline_update_leaves_embedding_stale": (
            updated_old["payload"]["memory"] == "corrected canonical fact"
            and updated_old["vector"] == old_vector
        ),
        "context_only_retrieval_is_broken": "text_embedder" in context_error,
        "native_scoped_purge_absent": not public_methods.intersection(
            {"purge", "delete", "forget", "erase"}
        ),
    }


class FakeQdrantClient:
    def __init__(self, **kwargs: Any):
        self.kwargs = kwargs

    def get_collections(self) -> SimpleNamespace:
        return SimpleNamespace(collections=[])

    def create_collection(self, **_kwargs: Any) -> None:
        pass


def _install_qdrant_stubs() -> None:
    class ModelStub:
        def __init__(self, *_args: Any, **kwargs: Any) -> None:
            self.__dict__.update(kwargs)

    _module("qdrant_client", QdrantClient=FakeQdrantClient)
    model_names = [
        "Distance",
        "FieldCondition",
        "Filter",
        "MatchValue",
        "PointIdsList",
        "PointStruct",
        "Range",
        "VectorParams",
        "MatchAny",
    ]
    members = {name: ModelStub for name in model_names}
    members["Distance"] = SimpleNamespace(COSINE="cosine")
    _module("qdrant_client.models", **members)
    _module("lightmem.configs.retriever.embeddingretriever.qdrant", QdrantConfig=object)


def _test_qdrant_reopen(source_root: Path, state_root: Path) -> bool:
    _install_qdrant_stubs()
    source = source_root / "src/lightmem/factory/retriever/embeddingretriever/qdrant.py"
    spec = importlib.util.spec_from_file_location("cotcodec_exact_lightmem_qdrant", source)
    if spec is None or spec.loader is None:
        raise DoctorError("cannot load exact LightMem Qdrant module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not state_root.is_dir() or state_root.is_symlink():
        raise DoctorError("state root must be a regular directory")
    with tempfile.TemporaryDirectory(dir=state_root) as root:
        store = Path(root) / "persistent-store"
        store.mkdir()
        (store / "canary.txt").write_text("must survive reopen", encoding="utf-8")
        config = SimpleNamespace(
            client=None, api_key=None, url=None, host=None, port=None,
            path=str(store), on_disk=False, collection_name="lightmem",
            embedding_model_dims=2,
        )
        module.Qdrant(config)
        return not store.exists()


def _source_contract_checks(source_root: Path) -> dict[str, bool]:
    offline_script = source_root / "experiments/longmemeval/offline_update.py"
    parsed = ast.parse(offline_script.read_text(encoding="utf-8"))
    dict_keys = {
        key.value
        for node in ast.walk(parsed)
        if isinstance(node, ast.Dict)
        for key in node.keys
        if isinstance(key, ast.Constant) and isinstance(key.value, str)
    }
    utils_tree = ast.parse(
        (source_root / "src/lightmem/memory/utils.py").read_text(encoding="utf-8")
    )
    memory_fields: set[str] = set()
    for node in utils_tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "MemoryEntry":
            memory_fields = {
                child.target.id
                for child in node.body
                if isinstance(child, ast.AnnAssign)
                and isinstance(child.target, ast.Name)
            }
    root_license = (source_root / "LICENSE").read_text(encoding="utf-8")
    pyproject = (source_root / "pyproject.toml").read_text(encoding="utf-8")
    return {
        "official_offline_script_omits_persistence_flag": "on_disk" not in dict_keys,
        "source_lineage_absent": not memory_fields.intersection(
            {"source_id", "source_ids", "source_event_id", "source_event_ids"}
        ),
        "root_dependency_lock_absent": not any(
            (source_root / name).exists()
            for name in ("uv.lock", "poetry.lock", "Pipfile.lock", "requirements.lock")
        ),
        "license_metadata_conflicts_root_license": (
            "MIT License" in root_license and 'license = {text = "Apache-2.0"}' in pyproject
        ),
    }


def run(source_root: Path, state_root: Path) -> dict[str, Any]:
    if not source_root.is_dir() or source_root.is_symlink():
        raise DoctorError("source root must be a regular directory")
    checks = _source_contract_checks(source_root)
    checks["default_qdrant_reopen_deletes_existing_state"] = _test_qdrant_reopen(
        source_root, state_root
    )
    lightmemory = _load_exact_lightmemory(source_root)
    checks.update(_test_lightmemory_methods(lightmemory))
    if not checks or not all(checks.values()):
        raise DoctorError(f"registered LightMem falsification did not reproduce: {checks}")
    projection = {
        "checks": dict(sorted(checks.items())),
        "claim_boundary": {
            "active_inactive_paging_demonstrated": False,
            "offline_consolidation_quality_measured": False,
            "persistent_restart_safe": False,
            "scoped_purge_available": False,
            "h100_actor_admission": False,
        },
    }
    return {
        "schema_version": 1,
        "source_revision": SOURCE_REVISION,
        "status": EXPECTED_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "h100_actor_admission": False,
        "provider_calls": 0,
        "model_backend_calls": 0,
        "projection": projection,
        "projection_sha256": _sha(projection),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=Path("/opt/lightmem/source"))
    parser.add_argument("--state-root", type=Path, default=Path("/state"))
    args = parser.parse_args()
    report = run(args.source_root, args.state_root)
    print("COTCODEC_LIGHTMEM_REPORT=" + json.dumps(report, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
