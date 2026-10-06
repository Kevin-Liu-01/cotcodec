#!/usr/bin/env python3
"""Contained source-runtime admission doctor for TiMem's core memory levels."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.util
import json
import sys
import types
from pathlib import Path
from typing import Any

EXPECTED_REVISION = "6d279a5f5d40ee229e1995df15c182cb2062c71c"
EXPECTED_STATUS = "TIMEM_CORE_RUNTIME_ADMISSION_KILLED"


class _Logger:
    def __getattr__(self, _name: str) -> Any:
        return lambda *_args, **_kwargs: None


def _sha(value: Any) -> str:
    encoded = json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def _module(name: str, **values: Any) -> types.ModuleType:
    module = types.ModuleType(name)
    for key, value in values.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _load(name: str, path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _source_compiles(root: Path) -> bool:
    for path in sorted(root.rglob("*.py")):
        compile(path.read_bytes(), str(path), "exec")
    return True


def _base_stubs() -> None:
    for name in tuple(sys.modules):
        if name == "timem" or name.startswith(("timem.", "llm", "langchain_core")):
            sys.modules.pop(name, None)
    timem = _module("timem")
    timem.__path__ = []  # type: ignore[attr-defined]
    utils = _module("timem.utils")
    utils.__path__ = []  # type: ignore[attr-defined]
    timem.utils = utils  # type: ignore[attr-defined]
    _module("timem.utils.logging", get_logger=lambda _name: _Logger())


def _l1_constructor_failure(source_root: Path) -> str:
    _base_stubs()

    class _TextProcessor:
        pass

    time_utils = _module(
        "timem.utils.time_utils",
        get_current_timestamp=lambda: __import__("datetime").datetime(2026, 8, 16),
    )
    sys.modules["timem.utils"].time_utils = time_utils  # type: ignore[attr-defined]
    _module("timem.utils.text_processing", LLMTextProcessor=_TextProcessor)
    _module(
        "timem.utils.config_manager",
        get_importance_scoring_config=lambda: {"enabled": False},
        get_app_config=lambda: {"memory": {"historical_memory_limit": 3}},
    )
    llm = _module("llm")
    llm.__path__ = []  # type: ignore[attr-defined]
    _module("llm.llm_manager", get_llm=lambda: object())
    module = _load(
        "timem.memory.l1_fragment_memory",
        source_root / "timem/memory/l1_fragment_memory.py",
    )
    processor = object.__new__(module.L1FragmentMemory)

    async def _summary(_content: str, _index: int) -> str:
        return "summary"

    async def _entities(_content: str) -> list[str]:
        return []

    async def _importance(
        _content: str, _keywords: list[str], _entities_value: list[str]
    ) -> float:
        return 0.5

    processor._generate_fragment_summary = _summary
    processor._extract_entities = _entities
    processor._calculate_importance = _importance
    processor.text_processor = types.SimpleNamespace(
        extract_keywords=lambda _text: asyncio.sleep(0, result=[])
    )
    processor.logger = _Logger()
    dialogue = module.DialogueRecord(
        speaker="user",
        content="retain this source event",
        timestamp=__import__("datetime").datetime(2026, 8, 16),
        metadata={},
    )
    try:
        asyncio.run(processor._create_fragment([dialogue], 0))
    except TypeError as exc:
        return str(exc)
    raise RuntimeError("TiMem L1 unexpectedly constructed a fragment record")


def _l2_constructor_failure(source_root: Path) -> str:
    _base_stubs()
    prompts = _module("langchain_core.prompts", PromptTemplate=object)
    documents = _module("langchain_core.documents", Document=object)
    langchain = _module("langchain_core")
    langchain.__path__ = []  # type: ignore[attr-defined]
    langchain.prompts = prompts  # type: ignore[attr-defined]
    langchain.documents = documents  # type: ignore[attr-defined]
    _module("llm", get_llm=lambda: object())
    models = _module("timem.models")
    models.__path__ = []  # type: ignore[attr-defined]
    _module(
        "timem.models.memory",
        Memory=object,
        SessionMemory=object,
        MemoryLevel=types.SimpleNamespace(L2="L2"),
    )
    memory_pkg = _module("timem.memory")
    memory_pkg.__path__ = []  # type: ignore[attr-defined]
    _module("timem.memory.l1_fragment_memory", L1FragmentMemory=object)

    class _Generator:
        async def generate_l2_content(self, _summaries: list[str]) -> str:
            return "session summary"

    _module("timem.memory.memory_generator", MemoryGenerator=_Generator)
    _module("timem.utils.config_manager", get_prompts_config=lambda: {})
    time_utils = _module("timem.utils.time_utils", ensure_iso_string=str)
    sys.modules["timem.utils"].time_utils = time_utils  # type: ignore[attr-defined]
    module = _load(
        "timem.memory.l2_session_memory",
        source_root / "timem/memory/l2_session_memory.py",
    )
    processor = module.L2SessionMemory(None, None)
    fragment = types.SimpleNamespace(id="event-1", summary="source summary")
    result = asyncio.run(processor.summarize([fragment], "user", "expert", "session"))
    if result is not None:
        raise RuntimeError("TiMem L2 unexpectedly constructed a session record")
    return "summarize-returned-none-after-unsupported-SessionMemory-fields"


def _l5_constructor_failure(source_root: Path) -> str:
    _base_stubs()
    _module("numpy")
    time_utils = _module("timem.utils.time_utils")
    sys.modules["timem.utils"].time_utils = time_utils  # type: ignore[attr-defined]
    _module("timem.utils.text_processing", LLMTextProcessor=object)
    module = _load(
        "timem.memory.l5_high_level_memory",
        source_root / "timem/memory/l5_high_level_memory.py",
    )
    processor = module.L5HighLevelMemory({})
    try:
        asyncio.run(processor.generate_high_level_memory("user", []))
    except TypeError as exc:
        return str(exc)
    raise RuntimeError("TiMem L5 unexpectedly constructed a high-level record")


def run(source_root: Path) -> dict[str, Any]:
    required = {
        "LICENSE",
        "pyproject.toml",
        "timem/memory/l1_fragment_memory.py",
        "timem/memory/l2_session_memory.py",
        "timem/memory/l5_high_level_memory.py",
    }
    if source_root.is_symlink() or not source_root.is_dir():
        raise RuntimeError("source root is invalid")
    missing = sorted(name for name in required if not (source_root / name).is_file())
    if missing:
        raise RuntimeError(f"TiMem source is incomplete: {missing}")
    compile_ok = _source_compiles(source_root / "timem")
    failures = {
        "l1_fragment_constructor": _l1_constructor_failure(source_root),
        "l2_session_constructor": _l2_constructor_failure(source_root),
        "l5_high_level_constructor": _l5_constructor_failure(source_root),
    }
    checks = {
        "source_compiles": compile_ok,
        "l1_processor_is_misused_as_record": "unexpected keyword argument 'id'"
        in failures["l1_fragment_constructor"],
        "l2_session_dataclass_rejects_runtime_fields": failures[
            "l2_session_constructor"
        ]
        == "summarize-returned-none-after-unsupported-SessionMemory-fields",
        "l5_required_updated_at_is_omitted": "updated_at" in failures[
            "l5_high_level_constructor"
        ],
    }
    if not all(checks.values()):
        raise RuntimeError(f"TiMem core runtime semantics drifted: {checks} {failures}")
    projection = {"checks": checks, "failures": failures}
    return {
        "schema_version": 1,
        "source_revision": EXPECTED_REVISION,
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run(args.source_root)
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(encoded, end="")
    else:
        args.output.write_text(encoded, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
