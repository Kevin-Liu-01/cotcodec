#!/usr/bin/env python3
"""Network-free exact-source Infini Memory lifecycle and provenance doctor."""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

STATE = Path("/state")
DATA_ROOT = STATE / "work/data"
TOKEN = os.environ["COTCODEC_RUN_TOKEN"]
PHASE = int(os.environ["COTCODEC_PHASE"])
MARKER = "COTCODEC_INFINI_MEMORY_PHASE="
CANARY_RE = re.compile(r"COTIM_[A-Z0-9_]+")
CONTROL = STATE / "doctor-control.json"


class DeterministicCaller:
    """Return prompt-compatible responses and retain exact local call counts."""

    def __init__(self) -> None:
        self.calls = 0
        self.by_kind = {"extract": 0, "rewrite": 0, "other": 0}

    def __call__(
        self, *, messages: list[dict[str, str]], model: str, temperature: float
    ) -> str:
        del model, temperature
        self.calls += 1
        system = "\n".join(
            message.get("content", "")
            for message in messages
            if message.get("role") == "system"
        )
        user = "\n".join(
            message.get("content", "")
            for message in messages
            if message.get("role") == "user"
        )
        if "personal information organizer" in system or "Extract relevant" in system:
            self.by_kind["extract"] += 1
            matches = CANARY_RE.findall(user)
            canary = matches[-1] if matches else "COTIM_LOCAL_FIXTURE"
            return (
                "---\nsummary: deterministic doctor memory\n---\n"
                f"# Doctor\n\n- <seq=@@SEQ@@,time=empty> {canary}\n"
            )
        if "CURRENT document" in system and "aggregate" in system.lower():
            self.by_kind["rewrite"] += 1
            matches = CANARY_RE.findall(system)
            canary = matches[-1] if matches else "COTIM_LOCAL_REWRITE"
            return f"# Rewritten\n\n- <seq=1,time=empty> {canary}\n"
        self.by_kind["other"] += 1
        return json.dumps({"ids": [], "groups": [], "updates": [], "new_docs": []})


def _memory() -> tuple[Any, DeterministicCaller]:
    from infini_memory import Memory
    from infini_memory.config import InfiniMemoryConfig
    from infini_memory.llm import LLMClient

    config = InfiniMemoryConfig.from_kwargs(
        api_key="cotcodec-local-double",
        model="cotcodec-local-double",
        enabled=True,
        data_root="work/data",
        root=STATE,
        log_level="ERROR",
        enable_file_logging=False,
        search_strategy="BM25",
        search_limit=4,
        max_current_length=100000,
        current_stale_seconds=0,
        retry_max_attempts=1,
        retry_initial_wait=0,
    )
    memory = Memory(config=config)
    caller = DeterministicCaller()
    memory._llm = LLMClient(
        caller=caller,
        retry_max_attempts=1,
        retry_initial_wait=0,
        retry_max_wait=0,
        retry_jitter=0,
    )
    return memory, caller


def _manager(user_id: str) -> Any:
    from infini_memory.manager import MemoryManager

    return MemoryManager(
        root=STATE,
        data_root="work/data",
        doc_dir="doc",
        meta_dir="metadata",
        index_file="index.json",
        user_id=user_id,
    )


def _seed(user_id: str, content: str, summary: str) -> Any:
    from infini_memory.manager import count_tokens

    return _manager(user_id).add_doc(content, summary, count_tokens(content))


def _read_control() -> dict[str, Any]:
    value = json.loads(CONTROL.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("doctor control is not a mapping")
    return value


def _write_control(value: dict[str, Any]) -> None:
    CONTROL.write_text(
        json.dumps(value, separators=(",", ":"), sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _regular_file_scan(root: Path, needles: list[str]) -> dict[str, list[str]]:
    matches = {needle: [] for needle in needles}
    if not root.exists():
        return matches
    encoded = {needle: needle.encode() for needle in needles}
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file() or path == CONTROL:
            continue
        raw = path.read_bytes()
        for needle, value in encoded.items():
            if value in raw:
                matches[needle].append(path.relative_to(root).as_posix())
    return matches


def _phase_one() -> dict[str, Any]:
    memory, caller = _memory()
    normal_user = f"normal-{TOKEN}"
    normal_canary = f"COTIM_NORMAL_{TOKEN.upper()}"
    added = memory.add(normal_canary, user_id=normal_user, stage="CURRENT")
    normal = memory.get("CURRENT", user_id=normal_user)

    delete_doc_canary = f"COTIM_DELETE_DOC_{TOKEN.upper()}"
    delete_doc = _seed(normal_user, delete_doc_canary, "delete-control")
    delete_user = f"delete-user-{TOKEN}"
    delete_user_canary = f"COTIM_DELETE_USER_{TOKEN.upper()}"
    _seed(delete_user, delete_user_canary, "delete-user-control")

    relative_user = f"../relative-{TOKEN}"
    relative = _seed(relative_user, f"COTIM_RELATIVE_{TOKEN.upper()}", "relative")
    absolute_user = f"/state/absolute-{TOKEN}"
    absolute = _seed(absolute_user, f"COTIM_ABSOLUTE_{TOKEN.upper()}", "absolute")
    alias_user = f"alias-parent/../alias-target-{TOKEN}"
    canonical_user = f"alias-target-{TOKEN}"
    alias_canary = f"COTIM_ALIAS_{TOKEN.upper()}"
    alias = _seed(alias_user, alias_canary, "alias")

    escaped_delete_user = f"../escaped-delete-{TOKEN}"
    escaped_delete_canary = f"COTIM_ESCAPED_DELETE_{TOKEN.upper()}"
    escaped_delete = _seed(
        escaped_delete_user, escaped_delete_canary, "escaped-delete"
    )

    update_user = f"interrupted-update-{TOKEN}"
    update_doc = _seed(
        update_user, f"COTIM_UPDATE_BASE_{TOKEN.upper()}", "update-base"
    )
    interrupted_delete_user = f"interrupted-delete-{TOKEN}"
    interrupted_delete_doc = _seed(
        interrupted_delete_user,
        f"COTIM_DANGLING_{TOKEN.upper()}",
        "delete-base",
    )
    truncated_user = f"truncated-{TOKEN}"
    truncated_doc = _seed(
        truncated_user, f"COTIM_TRUNCATED_{TOKEN.upper()}", "truncated-base"
    )

    control = {
        "normal_user": normal_user,
        "delete_doc_id": delete_doc.id,
        "delete_user": delete_user,
        "relative_user": relative_user,
        "relative_doc_id": relative.id,
        "absolute_user": absolute_user,
        "absolute_doc_id": absolute.id,
        "alias_user": alias_user,
        "canonical_user": canonical_user,
        "alias_doc_id": alias.id,
        "escaped_delete_user": escaped_delete_user,
        "escaped_delete_doc_id": escaped_delete.id,
        "update_user": update_user,
        "update_doc_id": update_doc.id,
        "interrupted_delete_user": interrupted_delete_user,
        "interrupted_delete_doc_id": interrupted_delete_doc.id,
        "truncated_user": truncated_user,
        "truncated_doc_id": truncated_doc.id,
    }
    _write_control(control)

    relative_dir = _manager(relative_user).data_dir
    absolute_dir = _manager(absolute_user).data_dir
    alias_dir = _manager(alias_user).data_dir
    canonical_dir = _manager(canonical_user).data_dir
    checks = {
        "public_add_and_get_complete": (
            added == 1
            and isinstance(normal, dict)
            and normal_canary in normal.get("content", "")
        ),
        "relative_user_id_escapes_data_root": (
            not relative_dir.resolve().is_relative_to(DATA_ROOT.resolve())
            and memory.get(relative.id, user_id=relative_user) is not None
        ),
        "absolute_user_id_overrides_data_root": (
            absolute_dir.resolve() == Path(absolute_user)
            and not absolute_dir.resolve().is_relative_to(DATA_ROOT.resolve())
            and memory.get(absolute.id, user_id=absolute_user) is not None
        ),
        "alias_equivalent_user_ids_share_storage": (
            alias_dir.resolve() == canonical_dir.resolve()
            and memory.get(alias.id, user_id=canonical_user) is not None
        ),
        "escaped_delete_target_created_outside_data_root": (
            _manager(escaped_delete_user).data_dir.exists()
            and not _manager(escaped_delete_user)
            .data_dir.resolve()
            .is_relative_to(DATA_ROOT.resolve())
        ),
        "fault_fixtures_created": all(
            memory.get(doc_id, user_id=user_id) is not None
            for user_id, doc_id in (
                (update_user, update_doc.id),
                (interrupted_delete_user, interrupted_delete_doc.id),
                (truncated_user, truncated_doc.id),
            )
        ),
    }
    return {
        "phase": 1,
        "checks": checks,
        "metrics": {
            "deterministic_llm_calls": caller.calls,
            "deterministic_llm_calls_by_kind": caller.by_kind,
            "relative_user_dir": str(relative_dir),
            "absolute_user_dir": str(absolute_dir),
            "alias_user_dir": str(alias_dir),
            "canonical_user_dir": str(canonical_dir),
        },
    }


def _phase_two() -> dict[str, Any]:
    from infini_memory.manager import MemoryManager

    control = _read_control()
    memory, caller = _memory()
    normal_canary = f"COTIM_NORMAL_{TOKEN.upper()}"
    normal_before = memory.get("CURRENT", user_id=control["normal_user"])
    search = memory.search(normal_canary, user_id=control["normal_user"])
    updated = memory.update(
        "CURRENT",
        f"# Updated\n\nCOTIM_NORMAL_UPDATED_{TOKEN.upper()}",
        "normal-updated",
        user_id=control["normal_user"],
    )
    memory.delete(control["delete_doc_id"], user_id=control["normal_user"])
    memory.delete_user(control["delete_user"])

    escaped_dir = _manager(control["escaped_delete_user"]).data_dir
    escaped_before = escaped_dir.is_dir()
    memory.delete_user(control["escaped_delete_user"])

    original_save = MemoryManager._save_index

    def fail_update_save(manager: Any, index: dict[str, Any]) -> None:
        if manager.user_id == control["update_user"]:
            raise RuntimeError("COTCODEC_FORCED_UPDATE_INDEX_FAILURE")
        original_save(manager, index)

    MemoryManager._save_index = fail_update_save
    update_interrupted = False
    try:
        memory.update(
            control["update_doc_id"],
            f"COTIM_UPDATE_NEW_{TOKEN.upper()}",
            "update-new",
            user_id=control["update_user"],
        )
    except RuntimeError as exc:
        update_interrupted = str(exc) == "COTCODEC_FORCED_UPDATE_INDEX_FAILURE"
    finally:
        MemoryManager._save_index = original_save

    def fail_delete_save(manager: Any, index: dict[str, Any]) -> None:
        if manager.user_id == control["interrupted_delete_user"]:
            raise RuntimeError("COTCODEC_FORCED_DELETE_INDEX_FAILURE")
        original_save(manager, index)

    MemoryManager._save_index = fail_delete_save
    delete_interrupted = False
    try:
        memory.delete(
            control["interrupted_delete_doc_id"],
            user_id=control["interrupted_delete_user"],
        )
    except RuntimeError as exc:
        delete_interrupted = str(exc) == "COTCODEC_FORCED_DELETE_INDEX_FAILURE"
    finally:
        MemoryManager._save_index = original_save

    truncated_manager = _manager(control["truncated_user"])
    truncated_markdown = Path(
        memory.get(
            control["truncated_doc_id"], user_id=control["truncated_user"]
        )["path"]
    )
    truncated_manager.index_path.write_text('{"docs":[', encoding="utf-8")

    checks = {
        "normal_user_survives_first_restart": (
            isinstance(normal_before, dict)
            and normal_canary in normal_before.get("content", "")
        ),
        "public_bm25_search_finds_normal_user": any(
            row.get("id") == "CURRENT" for row in search.get("results", [])
        ),
        "public_update_completed": (
            updated.get("summary") == "normal-updated"
            and updated.get("update_count") == 1
        ),
        "normal_document_delete_completed": (
            memory.get(
                control["delete_doc_id"], user_id=control["normal_user"]
            )
            is None
        ),
        "normal_user_delete_completed": (
            not _manager(control["delete_user"]).data_dir.exists()
        ),
        "escaped_delete_user_removes_path_outside_data_root": (
            escaped_before
            and not escaped_dir.exists()
            and not escaped_dir.resolve().is_relative_to(DATA_ROOT.resolve())
        ),
        "interrupted_update_exception_observed": update_interrupted,
        "interrupted_delete_exception_observed": delete_interrupted,
        "truncated_index_written_with_markdown_present": (
            truncated_markdown.is_file()
            and truncated_manager.index_path.read_text(encoding="utf-8")
            == '{"docs":['
        ),
    }
    return {
        "phase": 2,
        "checks": checks,
        "metrics": {
            "deterministic_llm_calls": caller.calls,
            "deterministic_llm_calls_by_kind": caller.by_kind,
            "normal_bm25_result_count": len(search.get("results", [])),
        },
    }


def _diagnostic() -> dict[str, Any]:
    user_id = f"diagnostic-{TOKEN}"
    records = [
        ("amberquartz", "amberquartz sailing schedule"),
        ("bluecinder", "bluecinder pottery notes"),
        ("cobaltfern", "cobaltfern garden plan"),
        ("deltamoss", "deltamoss hiking route"),
    ]
    ids = {term: _seed(user_id, content, term).id for term, content in records}
    memory, caller = _memory()
    bm25_rows: list[dict[str, Any]] = []
    direct_rows: list[dict[str, Any]] = []
    for term, _ in records[:3]:
        start = time.perf_counter_ns()
        result = memory.search(term, user_id=user_id)
        bm25_elapsed = time.perf_counter_ns() - start
        bm25_ids = [row["id"] for row in result.get("results", [])]
        bm25_rows.append(
            {
                "query": term,
                "target_present": ids[term] in bm25_ids,
                "result_count": len(bm25_ids),
                "candidate_documents": len(records),
                "elapsed_ns": bm25_elapsed,
            }
        )

        start = time.perf_counter_ns()
        direct_ids = []
        for document in memory.get_all(user_id=user_id):
            if term in document.get("content", "").lower():
                direct_ids.append(document["id"])
        direct_elapsed = time.perf_counter_ns() - start
        direct_rows.append(
            {
                "query": term,
                "target_present": ids[term] in direct_ids,
                "result_count": len(direct_ids),
                "files_read": len(records),
                "elapsed_ns": direct_elapsed,
            }
        )

    rewrite_canary = f"COTIM_REWRITE_{TOKEN.upper()}"
    rewrite_processed = memory.add(
        f"# Raw\n\n{rewrite_canary}",
        user_id=user_id,
        stage="REWRITE_CURRENT",
        source_file="CURRENT_1.md",
    )
    return {
        "documents": len(records),
        "queries": 3,
        "bm25": bm25_rows,
        "direct_markdown": direct_rows,
        "bm25_query_calls": len(bm25_rows),
        "bm25_candidate_documents": len(records) * len(bm25_rows),
        "direct_markdown_query_calls": len(direct_rows),
        "direct_markdown_files_read": len(records) * len(direct_rows),
        "rewrite_processed": rewrite_processed,
        "deterministic_llm_calls": caller.calls,
        "deterministic_llm_calls_by_kind": caller.by_kind,
    }


def _phase_three() -> dict[str, Any]:
    control = _read_control()
    memory, _ = _memory()
    normal = memory.get("CURRENT", user_id=control["normal_user"])
    update = memory.get(control["update_doc_id"], user_id=control["update_user"])
    dangling = memory.get(
        control["interrupted_delete_doc_id"],
        user_id=control["interrupted_delete_user"],
    )
    truncated_manager = _manager(control["truncated_user"])
    truncated_markdown = list(truncated_manager.doc_dir.glob("*.md"))
    truncated_list = memory.list(user_id=control["truncated_user"])
    deleted_canaries = [
        f"COTIM_DELETE_DOC_{TOKEN.upper()}",
        f"COTIM_DELETE_USER_{TOKEN.upper()}",
        f"COTIM_ESCAPED_DELETE_{TOKEN.upper()}",
    ]
    residue = _regular_file_scan(STATE, deleted_canaries)
    diagnostic = _diagnostic()
    checks = {
        "normal_crud_survives_second_restart": (
            isinstance(normal, dict)
            and normal.get("summary") == "normal-updated"
            and normal.get("update_count") == 1
            and f"COTIM_NORMAL_UPDATED_{TOKEN.upper()}"
            in normal.get("content", "")
        ),
        "normal_document_delete_survives_restart": (
            memory.get(
                control["delete_doc_id"], user_id=control["normal_user"]
            )
            is None
        ),
        "normal_user_delete_survives_restart": (
            not _manager(control["delete_user"]).data_dir.exists()
        ),
        "interrupted_update_exposes_markdown_index_mismatch": (
            isinstance(update, dict)
            and update.get("summary") == "update-base"
            and update.get("update_count") == 0
            and f"COTIM_UPDATE_NEW_{TOKEN.upper()}" in update.get("content", "")
        ),
        "interrupted_delete_exposes_dangling_index_entry": (
            isinstance(dangling, dict)
            and "content" not in dangling
            and any(
                row["id"] == control["interrupted_delete_doc_id"]
                for row in memory.list(user_id=control["interrupted_delete_user"])
            )
        ),
        "truncated_index_silently_loads_empty_with_markdown_present": (
            truncated_list == []
            and len(truncated_markdown) == 1
            and f"COTIM_TRUNCATED_{TOKEN.upper()}"
            in truncated_markdown[0].read_text(encoding="utf-8")
        ),
        "post_delete_current_file_plaintext_scan_completed": (
            set(residue) == set(deleted_canaries)
        ),
        "post_delete_plaintext_residue_not_observed": all(
            not paths for paths in residue.values()
        ),
        "rewrite_and_retrieval_accounting_completed": (
            diagnostic["bm25_query_calls"] == 3
            and diagnostic["bm25_candidate_documents"] == 12
            and diagnostic["direct_markdown_query_calls"] == 3
            and diagnostic["direct_markdown_files_read"] == 12
            and diagnostic["rewrite_processed"] == 1
            and diagnostic["deterministic_llm_calls"] == 1
            and all(row["target_present"] for row in diagnostic["bm25"])
            and all(row["target_present"] for row in diagnostic["direct_markdown"])
        ),
    }
    return {
        "phase": 3,
        "checks": checks,
        "metrics": {
            "post_delete_plaintext_residue_paths": residue,
            "write_path_diagnostic": diagnostic,
            "update_projection": update,
            "dangling_projection": dangling,
        },
    }


def _phase_four() -> dict[str, Any]:
    control = _read_control()
    memory, _ = _memory()
    update = memory.get(control["update_doc_id"], user_id=control["update_user"])
    dangling = memory.get(
        control["interrupted_delete_doc_id"],
        user_id=control["interrupted_delete_user"],
    )
    truncated_manager = _manager(control["truncated_user"])
    checks = {
        "interrupted_update_mismatch_survives_third_restart": (
            isinstance(update, dict)
            and update.get("summary") == "update-base"
            and f"COTIM_UPDATE_NEW_{TOKEN.upper()}" in update.get("content", "")
        ),
        "dangling_index_entry_survives_third_restart": (
            isinstance(dangling, dict) and "content" not in dangling
        ),
        "truncated_index_empty_view_survives_third_restart": (
            memory.list(user_id=control["truncated_user"]) == []
            and len(list(truncated_manager.doc_dir.glob("*.md"))) == 1
        ),
        "relative_escape_artifact_survives_restart": memory.get(
            control["relative_doc_id"], user_id=control["relative_user"]
        )
        is not None,
        "absolute_escape_artifact_survives_restart": memory.get(
            control["absolute_doc_id"], user_id=control["absolute_user"]
        )
        is not None,
        "alias_collision_artifact_survives_restart": memory.get(
            control["alias_doc_id"], user_id=control["canonical_user"]
        )
        is not None,
    }
    return {"phase": 4, "checks": checks, "metrics": {}}


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
