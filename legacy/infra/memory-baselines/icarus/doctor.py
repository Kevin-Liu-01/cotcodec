#!/usr/bin/env python3
"""Contained lifecycle falsifier for pinned Icarus Memory Infrastructure.

The doctor uses the public three-layer and rollback APIs, then performs a
read-only residue audit over the mounted fabric. It does not patch upstream,
call a model, use embeddings, or infer delete semantics from file removal by
the orchestration wrapper.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from icarus_memory import IcarusMemory, __version__

SCHEMA_VERSION = 1
EXPECTED_VERSION = "0.3.0"
TERMINAL_STATUS = "BLOCKED_NON_IDEMPOTENT_PROMOTION_AND_NO_NATIVE_PURGE"


class DoctorError(RuntimeError):
    """Raised when an Icarus lifecycle phase is malformed."""


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _write_once(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        data = memoryview(_json_bytes(value))
        while data:
            written = os.write(descriptor, data)
            if written <= 0:
                raise DoctorError(f"short write: {path}")
            data = data[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    parent = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise DoctorError(f"expected regular JSON file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DoctorError(f"cannot read strict JSON: {path}") from exc
    if not isinstance(value, dict):
        raise DoctorError(f"expected JSON object: {path}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _base(phase: str, repeat: int) -> dict[str, Any]:
    if __version__ != EXPECTED_VERSION:
        raise DoctorError(f"Icarus version drifted: {__version__!r}")
    return {
        "schema_version": SCHEMA_VERSION,
        "phase": phase,
        "repeat": repeat,
        "icarus_version": __version__,
        "scientific_result": False,
        "publication_ready": False,
        "model_calls": 0,
        "embedding_calls": 0,
    }


def _contains(root: Path, needle: str) -> bool:
    encoded = needle.encode()
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink() and encoded in path.read_bytes():
            return True
    return False


def _session_summary_ids(memory: IcarusMemory, session_id: str) -> list[str]:
    return sorted(
        entry.id
        for entry in memory.store.iter_entries()
        if entry.type == "session_summary" and entry.session_id == session_id
    )


def prepare(state_root: Path, repeat: int) -> dict[str, Any]:
    contract_path = state_root / "contract.json"
    if contract_path.exists():
        raise DoctorError("prepare refuses an existing contract")
    fabric = state_root / "fabric"
    memory = IcarusMemory(root=fabric, enable_wiki_classification=False)
    canaries = {
        "private": f"ICARUS_PRIVATE_R{repeat}_CANARY_91F3",
        "shared": f"ICARUS_SHARED_R{repeat}_CANARY_7C2B",
        "superseded": f"ICARUS_OLD_R{repeat}_CANARY_D84E",
        "replacement": f"ICARUS_NEW_R{repeat}_CANARY_4A17",
    }

    working, first_briefing = memory.start_session(
        "agent-a", "repair checkout latency canary"
    )
    working.add_observation(canaries["private"])
    working.add_attempt("obsolete index attempt", succeeded=False)
    archived = memory.end_session(
        working,
        canaries["shared"],
        promote_to_wiki=["decisions/checkout-latency"],
    )
    first_summaries = _session_summary_ids(memory, archived.session_id)
    page_before_retry = memory.get_wiki_page("decisions/checkout-latency")
    if page_before_retry is None:
        raise DoctorError("explicit promotion did not create its wiki page")

    # Replay the same public end-session call. Upstream archives and promotes it
    # again instead of recognizing an idempotent retry.
    memory.end_session(
        working,
        canaries["shared"],
        promote_to_wiki=["decisions/checkout-latency"],
    )
    second_summaries = _session_summary_ids(memory, archived.session_id)
    page_after_retry = memory.get_wiki_page("decisions/checkout-latency")
    if page_after_retry is None:
        raise DoctorError("wiki page vanished during retry")

    old = memory.write(
        agent="agent-a",
        type="decision",
        summary=canaries["superseded"],
        body="old decision",
        classify=False,
    )
    new = memory.write_with_supersession(
        agent="agent-a",
        type="decision",
        summary=canaries["replacement"],
        body="replacement decision",
        supersedes_ids=[old.id],
    )

    verified = memory.write(
        agent="agent-a",
        type="decision",
        summary="verified rollback base",
        body="verified base",
        classify=False,
    )
    memory.verify(verified.id, verifier="doctor")
    revision = memory.write(
        agent="agent-a",
        type="decision",
        summary="bad rollback revision",
        body="bad revision",
        revises=verified.id,
        classify=False,
    )
    rollback = memory.rollback(revision.id, dry_run=False)

    agent_a = memory.get_briefing("agent-a", "checkout latency obsolete index")
    agent_b = memory.get_briefing("agent-b", "checkout latency obsolete index")
    working_file = fabric / ".icarus" / "sessions" / f"{working.session_id}.json"
    archive_file = (
        fabric / ".icarus" / "agents" / "agent-a" / "sessions" / f"{working.session_id}.json"
    )
    contract = {
        "schema_version": SCHEMA_VERSION,
        "repeat": repeat,
        "canaries": canaries,
        "session_id": working.session_id,
        "entry_ids": {
            "old": old.id,
            "new": new.id,
            "verified": verified.id,
            "revision": revision.id,
            "rollback": rollback.rollback_entry_id,
            "session_summaries": second_summaries,
        },
    }
    _write_once(contract_path, contract)

    result = _base("prepare", repeat)
    result.update(
        {
            "manual_promotion_created_shared_page": bool(page_before_retry.entries),
            "working_state_removed_after_archive": not working_file.exists(),
            "private_archive_created": archive_file.is_file(),
            "same_agent_briefing_contains_private_attempt": (
                "obsolete index attempt" in agent_a.content
            ),
            "other_agent_briefing_excludes_private_attempt": (
                "obsolete index attempt" not in agent_b.content
            ),
            "supersession_marks_old_entry": (
                memory.get(old.id).lifecycle == "superseded"
                and memory.get(old.id).superseded_by == new.id
            ),
            "rollback_is_non_destructive_and_persisted": (
                memory.get(revision.id).verified == "rolled_back"
                and rollback.rollback_entry_id is not None
                and memory.store.exists(rollback.rollback_entry_id)
            ),
            "duplicate_end_session_created_extra_summary": (
                len(first_summaries) == 1 and len(second_summaries) == 2
            ),
            "duplicate_end_session_created_extra_wiki_link": (
                len(page_after_retry.entries) > len(page_before_retry.entries)
            ),
            "first_briefing_was_empty_floor": not first_briefing.source_ids,
            "contract_sha256": _sha256(contract_path),
        }
    )
    return result


def verify_restart(state_root: Path, repeat: int) -> dict[str, Any]:
    contract = _read_json(state_root / "contract.json")
    if contract.get("repeat") != repeat:
        raise DoctorError("restart contract repeat drifted")
    fabric = state_root / "fabric"
    memory = IcarusMemory(root=fabric, enable_wiki_classification=False)
    ids = contract["entry_ids"]
    canaries = contract["canaries"]
    session = memory.archive.get("agent-a", contract["session_id"])
    page = memory.get_wiki_page("decisions/checkout-latency")
    agent_a = memory.get_briefing("agent-a", "checkout latency obsolete index")
    agent_b = memory.get_briefing("agent-b", "checkout latency obsolete index")
    result = _base("verify-restart", repeat)
    result.update(
        {
            "restart_preserved_private_archive": (
                session is not None and canaries["private"] in session.observations
            ),
            "restart_preserved_shared_wiki": (
                page is not None and len(page.entries) >= 2
            ),
            "restart_preserved_agent_isolation": (
                "obsolete index attempt" in agent_a.content
                and "obsolete index attempt" not in agent_b.content
            ),
            "restart_preserved_supersession": (
                memory.get(ids["old"]).lifecycle == "superseded"
                and memory.get(ids["old"]).superseded_by == ids["new"]
            ),
            "restart_preserved_rollback": (
                memory.get(ids["revision"]).verified == "rolled_back"
                and memory.store.exists(ids["rollback"])
            ),
            "restart_preserved_duplicate_promotions": (
                len(_session_summary_ids(memory, contract["session_id"])) == 2
            ),
        }
    )
    return result


def purge_probe(state_root: Path, repeat: int) -> dict[str, Any]:
    contract = _read_json(state_root / "contract.json")
    if contract.get("repeat") != repeat:
        raise DoctorError("purge contract repeat drifted")
    fabric = state_root / "fabric"
    memory = IcarusMemory(root=fabric, enable_wiki_classification=False)
    native_delete = any(
        callable(getattr(target, name, None))
        for target in (memory, memory.archive, memory.wiki, memory.store)
        for name in ("delete", "forget", "purge", "remove")
    )
    residue = {
        name: _contains(fabric, canary)
        for name, canary in contract["canaries"].items()
    }
    result = _base("purge-probe", repeat)
    result.update(
        {
            "status": TERMINAL_STATUS,
            "native_delete_or_purge_api_available": native_delete,
            "plaintext_residue": residue,
            "all_canaries_remain_physically_present": all(residue.values()),
            "manual_promotion_only": True,
            "h100_actor_admission": "forbidden-for-this-revision",
        }
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("prepare", "verify-restart", "purge-probe"))
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--repeat", type=int, choices=(1, 2), required=True)
    args = parser.parse_args()
    if args.phase == "prepare":
        result = prepare(args.state_root, args.repeat)
    elif args.phase == "verify-restart":
        result = verify_restart(args.state_root, args.repeat)
    else:
        result = purge_probe(args.state_root, args.repeat)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
