#!/usr/bin/env python3
"""Network-free exact-source MemForest lifecycle and write-path doctor."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any

STATE = Path("/state")
SNAPSHOT = STATE / "snapshot"
TORN_SNAPSHOT = STATE / "torn-snapshot"
TOKEN = os.environ["COTCODEC_RUN_TOKEN"]
PHASE = int(os.environ["COTCODEC_PHASE"])
MARKER = "COTCODEC_MEMFOREST_PHASE="
CANARY_RE = re.compile(r"COTMF_[A-Z0-9_]+")


class DeterministicChatClient:
    """Return schema-compatible local responses without provider calls."""

    def __init__(self, config: Any, **_: Any) -> None:
        self.config = config
        self.calls = 0

    def generate_json(self, *, system_prompt: str, user_prompt: str, **_: Any) -> dict[str, Any]:
        self.calls += 1
        if "memory extraction engine" in system_prompt:
            canaries = CANARY_RE.findall(user_prompt)
            fact = canaries[-1] if canaries else _digest(user_prompt)
            return {
                "cell_summary": f"deterministic-{_digest(user_prompt)}",
                "memory_items": [
                    {
                        "fact_text": fact,
                        "participants": ["user"],
                        "origin": "user",
                        "semantic_role": "state",
                        "entities": [],
                        "topics": ["doctor"],
                        "time_text": "2026-08-17",
                        "time_start": 1786924800,
                        "time_end": 1786924800,
                        "attribute_keys": ["doctor_canary"],
                        "domain_keys": ["doctor"],
                        "collection_keys": [],
                    }
                ],
            }
        if "equivalent" in system_prompt.lower():
            return {"equivalent": False, "preferred": "either"}
        return {"summary": f"deterministic-{_digest(user_prompt)}"}


class DeterministicEmbeddingClient:
    """Produce deterministic fixed-width vectors without network access."""

    def __init__(self, config: Any, **_: Any) -> None:
        self.config = config
        self.calls = 0
        self.texts = 0

    def embed_texts(self, texts: list[str], *, batch_size: int = 256) -> list[list[float]]:
        del batch_size
        self.calls += 1
        self.texts += len(texts)
        return [_vector(text, int(self.config.dimension)) for text in texts]


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def _vector(value: str, dimension: int) -> list[float]:
    seed = hashlib.sha256(value.encode()).digest()
    return [((seed[index % len(seed)] / 255.0) * 2.0) - 1.0 for index in range(dimension)]


def _patch_clients() -> None:
    import src.api.client as client

    client.OpenAIChatClient = DeterministicChatClient
    client.OpenAIEmbeddingClient = DeterministicEmbeddingClient


def _forest(root: Path):
    _patch_clients()
    from src.config.config import load_default_config
    from src.forest.memforest import MemForest

    return MemForest(root, config=load_default_config("src/config/default.yaml"), max_workers=2)


def _turns(session_id: str, canary: str) -> list[dict[str, Any]]:
    return [
        {
            "role": "user",
            "content": canary,
            "content_id": f"{session_id}-turn-1",
            "timestamp": "2026-08-17T00:00:00Z",
        }
    ]


def _facts(user_forest: Any) -> list[str]:
    return sorted(fact.fact_text for fact in user_forest._fact_manager.iter_facts())


def _active_sessions(user_forest: Any) -> list[str]:
    return sorted(user_forest._registry.list_active_sessions())


def _regular_file_scan(root: Path, needle: str) -> list[str]:
    encoded = needle.encode()
    matches: list[str] = []
    if not root.exists():
        return matches
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        try:
            if encoded in path.read_bytes():
                matches.append(path.relative_to(root).as_posix())
        except OSError:
            matches.append(f"UNREADABLE:{path.relative_to(root).as_posix()}")
    return matches


def _tree_ids(user_forest: Any) -> list[str]:
    return sorted(user_forest._tree_store.all_tree_ids())


def _component_projection(user_forest: Any) -> dict[str, Any]:
    return {
        "active_sessions": _active_sessions(user_forest),
        "facts": _facts(user_forest),
        "tree_ids": _tree_ids(user_forest),
        "cell_ids": sorted(user_forest._cell_store),
        "session_alias_map": user_forest._tree_builder.session_alias_map,
    }


def _ingest(forest: Any, user_id: str, session_id: str, canary: str) -> None:
    forest.ingest_session(user_id, session_id, _turns(session_id, canary))


def _phase_one() -> dict[str, Any]:
    normal_user = f"normal-{TOKEN}"
    normal_session = f"normal-session-{TOKEN}"
    normal_canary = f"COTMF_NORMAL_{TOKEN.upper()}"
    forest = _forest(SNAPSHOT)
    forest.register_user(normal_user, load_existing=False)
    _ingest(forest, normal_user, normal_session, normal_canary)
    forest.save(normal_user)
    normal = forest._get_user(normal_user)

    relative_id = f"../relative-{TOKEN}"
    forest.register_user(relative_id, load_existing=False)
    forest.save(relative_id)
    relative_dir = forest._get_user(relative_id)._dir

    absolute_id = f"/state/absolute-{TOKEN}"
    forest.register_user(absolute_id, load_existing=False)
    forest.save(absolute_id)
    absolute_dir = forest._get_user(absolute_id)._dir

    alias_id = f"alias-parent/../alias-target-{TOKEN}"
    canonical_id = f"alias-target-{TOKEN}"
    alias_canary = f"COTMF_ALIAS_{TOKEN.upper()}"
    forest.register_user(alias_id, load_existing=False)
    _ingest(forest, alias_id, f"alias-session-{TOKEN}", alias_canary)
    forest.save(alias_id)
    forest.register_user(canonical_id, load_existing=True)
    alias_user = forest._get_user(alias_id)
    canonical_user = forest._get_user(canonical_id)

    checks = {
        "normal_user_initial_save_complete": (
            _active_sessions(normal) == [normal_session] and normal_canary in _facts(normal)
        ),
        "relative_user_id_escapes_snapshot_root": (
            not relative_dir.resolve().is_relative_to(SNAPSHOT.resolve())
            and (relative_dir / "metadata.json").is_file()
        ),
        "absolute_user_id_overrides_snapshot_root": (
            absolute_dir.resolve() == Path(absolute_id)
            and not absolute_dir.resolve().is_relative_to(SNAPSHOT.resolve())
            and (absolute_dir / "metadata.json").is_file()
        ),
        "alias_equivalent_user_ids_share_storage": (
            alias_user._dir.resolve() == canonical_user._dir.resolve()
            and alias_canary in _facts(canonical_user)
        ),
        "native_tenant_purge_absent": (
            not hasattr(forest, "delete_user")
            and not hasattr(forest, "purge_user")
            and not hasattr(forest, "unregister_user")
        ),
    }
    return {
        "phase": 1,
        "checks": checks,
        "metrics": {
            "normal_projection": _component_projection(normal),
            "relative_user_dir": str(relative_dir),
            "relative_user_dir_resolved": str(relative_dir.resolve()),
            "absolute_user_dir": str(absolute_dir),
            "alias_user_dir_resolved": str(alias_user._dir.resolve()),
            "canonical_user_dir_resolved": str(canonical_user._dir.resolve()),
        },
    }


def _phase_two() -> dict[str, Any]:
    normal_user = f"normal-{TOKEN}"
    normal_session = f"normal-session-{TOKEN}"
    normal_canary = f"COTMF_NORMAL_{TOKEN.upper()}"
    forest = _forest(SNAPSHOT)
    forest.register_user(normal_user)
    normal = forest._get_user(normal_user)
    normal_before = _component_projection(normal)
    forest.delete_session(normal_user, normal_session)
    forest.save(normal_user)

    torn_user = f"torn-{TOKEN}"
    base_session = f"torn-base-{TOKEN}"
    new_session = f"torn-new-{TOKEN}"
    base_canary = f"COTMF_TORN_BASE_{TOKEN.upper()}"
    new_canary = f"COTMF_TORN_NEW_{TOKEN.upper()}"
    torn = _forest(TORN_SNAPSHOT)
    torn.register_user(torn_user, load_existing=False)
    _ingest(torn, torn_user, base_session, base_canary)
    torn.save(torn_user)
    _ingest(torn, torn_user, new_session, new_canary)
    torn_user_forest = torn._get_user(torn_user)

    original_save = torn_user_forest._node_index.save

    def fail_save(*_: Any, **__: Any) -> None:
        raise RuntimeError("COTCODEC_FORCED_NODE_INDEX_SAVE_FAILURE")

    torn_user_forest._node_index.save = fail_save
    interrupted = False
    try:
        torn.save(torn_user)
    except RuntimeError as exc:
        interrupted = str(exc) == "COTCODEC_FORCED_NODE_INDEX_SAVE_FAILURE"
    finally:
        torn_user_forest._node_index.save = original_save

    checks = {
        "normal_user_survives_first_restart": (
            normal_before["active_sessions"] == [normal_session]
            and normal_canary in normal_before["facts"]
        ),
        "saved_session_delete_completed_before_restart": (
            _active_sessions(normal) == [] and normal_canary not in _facts(normal)
        ),
        "interrupted_save_exception_observed": interrupted,
        "interrupted_save_in_memory_contains_new_session": (
            new_session in _active_sessions(torn_user_forest)
            and new_canary in _facts(torn_user_forest)
        ),
    }
    return {
        "phase": 2,
        "checks": checks,
        "metrics": {
            "normal_before_delete": normal_before,
            "normal_after_delete": _component_projection(normal),
            "torn_before_restart": _component_projection(torn_user_forest),
        },
    }


def _write_diagnostic() -> dict[str, Any]:
    sessions = [f"diag-session-{index}-{TOKEN}" for index in range(5)]
    canaries = [f"COTMF_DIAG_{index}_{TOKEN.upper()}" for index in range(5)]

    incremental = _forest(STATE / "diag-incremental")
    incremental.register_user("diagnostic", load_existing=False)
    for session_id, canary in zip(sessions[:4], canaries[:4], strict=True):
        _ingest(incremental, "diagnostic", session_id, canary)
    incremental.save("diagnostic")
    inc_chat_start = incremental._chat_client.calls
    inc_embed_start = incremental._embedding_client.texts
    start = time.perf_counter_ns()
    _ingest(incremental, "diagnostic", sessions[4], canaries[4])
    incremental.save("diagnostic")
    incremental_ns = time.perf_counter_ns() - start

    rebuild = _forest(STATE / "diag-rebuild")
    rebuild.register_user("diagnostic", load_existing=False)
    start = time.perf_counter_ns()
    for session_id, canary in zip(sessions, canaries, strict=True):
        _ingest(rebuild, "diagnostic", session_id, canary)
    rebuild.save("diagnostic")
    rebuild_ns = time.perf_counter_ns() - start

    incremental_user = incremental._get_user("diagnostic")
    rebuild_user = rebuild._get_user("diagnostic")
    return {
        "sessions": len(sessions),
        "incremental_elapsed_ns": incremental_ns,
        "clean_rebuild_elapsed_ns": rebuild_ns,
        "incremental_chat_calls": incremental._chat_client.calls - inc_chat_start,
        "clean_rebuild_chat_calls": rebuild._chat_client.calls,
        "incremental_embedding_texts": incremental._embedding_client.texts - inc_embed_start,
        "clean_rebuild_embedding_texts": rebuild._embedding_client.texts,
        "incremental_active_sessions": len(_active_sessions(incremental_user)),
        "clean_rebuild_active_sessions": len(_active_sessions(rebuild_user)),
        "incremental_current_bytes": _tree_bytes(STATE / "diag-incremental"),
        "clean_rebuild_current_bytes": _tree_bytes(STATE / "diag-rebuild"),
    }


def _tree_bytes(root: Path) -> int:
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def _phase_three() -> dict[str, Any]:
    normal_user = f"normal-{TOKEN}"
    normal_canary = f"COTMF_NORMAL_{TOKEN.upper()}"
    forest = _forest(SNAPSHOT)
    forest.register_user(normal_user)
    normal = forest._get_user(normal_user)
    residue = _regular_file_scan(normal._dir, normal_canary)

    torn_user = f"torn-{TOKEN}"
    base_session = f"torn-base-{TOKEN}"
    new_session = f"torn-new-{TOKEN}"
    new_canary = f"COTMF_TORN_NEW_{TOKEN.upper()}"
    torn = _forest(TORN_SNAPSHOT)
    torn.register_user(torn_user)
    torn_user_forest = torn._get_user(torn_user)
    projection = _component_projection(torn_user_forest)
    mixed = (
        projection["active_sessions"] == [base_session]
        and new_canary in projection["facts"]
        and new_session not in projection["active_sessions"]
        and len(projection["tree_ids"]) > 0
    )
    diagnostic = _write_diagnostic()

    checks = {
        "saved_session_delete_survives_restart": (
            _active_sessions(normal) == [] and normal_canary not in _facts(normal)
        ),
        "post_delete_plaintext_scan_completed": isinstance(residue, list),
        "interrupted_save_exposes_mixed_component_generations": mixed,
        "write_path_diagnostic_completed": (
            diagnostic["incremental_elapsed_ns"] > 0
            and diagnostic["clean_rebuild_elapsed_ns"] > 0
            and diagnostic["incremental_active_sessions"] == 5
            and diagnostic["clean_rebuild_active_sessions"] == 5
        ),
    }
    return {
        "phase": 3,
        "checks": checks,
        "metrics": {
            "normal_after_delete_restart": _component_projection(normal),
            "post_delete_plaintext_residue_paths": residue,
            "torn_after_restart": projection,
            "write_path_diagnostic": diagnostic,
        },
    }


def _phase_four() -> dict[str, Any]:
    torn_user = f"torn-{TOKEN}"
    base_session = f"torn-base-{TOKEN}"
    new_session = f"torn-new-{TOKEN}"
    new_canary = f"COTMF_TORN_NEW_{TOKEN.upper()}"
    torn = _forest(TORN_SNAPSHOT)
    torn.register_user(torn_user)
    torn_user_forest = torn._get_user(torn_user)
    projection = _component_projection(torn_user_forest)

    relative_dir = (SNAPSHOT / f"../relative-{TOKEN}").resolve()
    absolute_dir = Path(f"/state/absolute-{TOKEN}")
    alias_dir = (SNAPSHOT / f"alias-parent/../alias-target-{TOKEN}").resolve()
    checks = {
        "mixed_component_generations_survive_second_restart": (
            projection["active_sessions"] == [base_session]
            and new_session not in projection["active_sessions"]
            and new_canary in projection["facts"]
        ),
        "relative_escape_artifact_survives_restart": (relative_dir / "metadata.json").is_file(),
        "absolute_escape_artifact_survives_restart": (absolute_dir / "metadata.json").is_file(),
        "alias_collision_artifact_survives_restart": (alias_dir / "metadata.json").is_file(),
    }
    return {
        "phase": 4,
        "checks": checks,
        "metrics": {"torn_after_second_restart": projection},
    }


def main() -> int:
    handlers = {1: _phase_one, 2: _phase_two, 3: _phase_three, 4: _phase_four}
    if PHASE not in handlers:
        raise SystemExit(f"unsupported phase: {PHASE}")
    report = handlers[PHASE]()
    if not all(report["checks"].values()):
        raise SystemExit(json.dumps(report, sort_keys=True))
    print(MARKER + json.dumps(report, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
