#!/usr/bin/env python3
"""Contained public-API lifecycle phases for the pinned legacy Letta server."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

BASE_URL = "http://127.0.0.1:8283"
DB_DSN = "dbname=letta user=letta host=127.0.0.1"
TRIGGER_NAME = "cotcodec_fail_system_message_update"
FUNCTION_NAME = "cotcodec_fail_system_message_update_fn"


class DoctorError(RuntimeError):
    """Raised when a phase cannot produce a well-formed observation."""


class ApiClient:
    """Small standard-library HTTP client with complete local call accounting."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def call(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        user_id: str | None = None,
        timeout: float = 60.0,
    ) -> tuple[int, Any]:
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload, sort_keys=True).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if user_id is not None:
            headers["user_id"] = user_id
        request = urllib.request.Request(
            BASE_URL + path,
            data=data,
            headers=headers,
            method=method,
        )
        started = time.perf_counter_ns()
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                status = response.status
                raw = response.read()
        except urllib.error.HTTPError as exc:
            status = exc.code
            raw = exc.read()
        elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
        try:
            body = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            body = raw.decode("utf-8", errors="replace")
        self.calls.append(
            {
                "method": method,
                "path": path,
                "status": status,
                "elapsed_ms": elapsed_ms,
            }
        )
        return status, body


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _require_status(status: int, expected: int, label: str, body: Any) -> None:
    if status != expected:
        raise DoctorError(f"{label} returned {status}, expected {expected}: {body!r}")


def _blocks(agent: dict[str, Any]) -> list[dict[str, Any]]:
    memory = agent.get("memory")
    if isinstance(memory, dict) and isinstance(memory.get("blocks"), list):
        return memory["blocks"]
    if isinstance(agent.get("blocks"), list):
        return agent["blocks"]
    raise DoctorError("agent response has no memory block list")


def _find_block(blocks: list[dict[str, Any]], label: str) -> dict[str, Any]:
    matches = [block for block in blocks if block.get("label") == label]
    if len(matches) != 1:
        raise DoctorError(f"expected one {label!r} block, found {len(matches)}")
    return matches[0]


def _first_passage(body: Any, label: str) -> dict[str, Any]:
    if not isinstance(body, list) or len(body) != 1 or not isinstance(body[0], dict):
        raise DoctorError(f"{label} did not return exactly one passage: {body!r}")
    return body[0]


def _connect_db():
    import psycopg2

    return psycopg2.connect(DB_DSN)


def _install_failure_trigger() -> None:
    with _connect_db() as connection, connection.cursor() as cursor:
        cursor.execute(
            f"""
                CREATE OR REPLACE FUNCTION {FUNCTION_NAME}()
                RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    IF NEW.role = 'system' THEN
                        RAISE EXCEPTION 'cotcodec injected system message update failure';
                    END IF;
                    RETURN NEW;
                END;
                $$;
                DROP TRIGGER IF EXISTS {TRIGGER_NAME} ON messages;
                CREATE TRIGGER {TRIGGER_NAME}
                BEFORE UPDATE ON messages
                FOR EACH ROW EXECUTE FUNCTION {FUNCTION_NAME}();
            """
        )


def _drop_failure_trigger() -> None:
    with _connect_db() as connection, connection.cursor() as cursor:
        cursor.execute(f"DROP TRIGGER IF EXISTS {TRIGGER_NAME} ON messages")
        cursor.execute(f"DROP FUNCTION IF EXISTS {FUNCTION_NAME}()")


def _db_scalar(query: str, parameters: tuple[Any, ...]) -> int:
    with _connect_db() as connection, connection.cursor() as cursor:
        cursor.execute(query, parameters)
        row = cursor.fetchone()
    if row is None or len(row) != 1:
        raise DoctorError("database scalar query did not return one value")
    return int(row[0])


def _system_message_contains(agent_id: str, canary: str) -> bool:
    count = _db_scalar(
        """
        SELECT count(*)
        FROM messages
        WHERE agent_id = %s
          AND role = 'system'
          AND (
            coalesce(text, '') LIKE %s
            OR coalesce(content::text, '') LIKE %s
          )
        """,
        (agent_id, f"%{canary}%", f"%{canary}%"),
    )
    return count > 0


def _agent_payload(name: str, core_canary: str, persona_canary: str) -> dict[str, Any]:
    return {
        "name": name,
        "memory_blocks": [
            {"label": "human", "value": core_canary, "limit": 4000},
            {"label": "persona", "value": persona_canary, "limit": 4000},
        ],
        "include_base_tools": False,
        "llm_config": {
            "model": "gpt-4o-mini",
            "model_endpoint_type": "openai",
            "model_endpoint": "http://127.0.0.1:9/v1",
            "context_window": 128000,
            "put_inner_thoughts_in_kwargs": False,
            "handle": "openai/gpt-4o-mini",
            "enable_reasoner": False,
        },
        "embedding_config": None,
    }


def phase_initial(evidence_dir: Path, repeat: int) -> int:
    client = ApiClient()
    prefix = f"COTCODEC_LETTA_R{repeat}"
    canaries = {
        "core_initial": f"{prefix}_CORE_INITIAL_81D7A1",
        "core_normal": f"{prefix}_CORE_NORMAL_17C34B",
        "core_failed": f"{prefix}_CORE_FAILED_9A51E2",
        "persona": f"{prefix}_PERSONA_73D05C",
        "archive": f"{prefix}_ARCHIVE_DUPLICATE_4F219D",
    }

    status, org_a = client.call(
        "POST", "/v1/admin/orgs/", payload={"name": f"cotcodec-a-{repeat}"}
    )
    _require_status(status, 200, "create organization A", org_a)
    status, org_b = client.call(
        "POST", "/v1/admin/orgs/", payload={"name": f"cotcodec-b-{repeat}"}
    )
    _require_status(status, 200, "create organization B", org_b)
    status, user_a = client.call(
        "POST",
        "/v1/admin/users/",
        payload={"name": f"cotcodec-a-{repeat}", "organization_id": org_a["id"]},
    )
    _require_status(status, 200, "create user A", user_a)
    status, user_b = client.call(
        "POST",
        "/v1/admin/users/",
        payload={"name": f"cotcodec-b-{repeat}", "organization_id": org_b["id"]},
    )
    _require_status(status, 200, "create user B", user_b)

    status, agent = client.call(
        "POST",
        "/v1/agents/",
        payload=_agent_payload(
            f"cotcodec-agent-{repeat}", canaries["core_initial"], canaries["persona"]
        ),
        user_id=user_a["id"],
    )
    _require_status(status, 200, "create provider-free agent", agent)
    agent_id = agent["id"]
    agent_blocks = _blocks(agent)
    human_block = _find_block(agent_blocks, "human")
    persona_block = _find_block(agent_blocks, "persona")

    status, normal_update = client.call(
        "PATCH",
        f"/v1/agents/{agent_id}/core-memory/blocks/human",
        payload={"value": canaries["core_normal"]},
        user_id=user_a["id"],
    )
    _require_status(status, 200, "normal core block update", normal_update)

    archive_payload = {"text": canaries["archive"], "tags": ["cotcodec-retry"]}
    status, first_body = client.call(
        "POST",
        f"/v1/agents/{agent_id}/archival-memory",
        payload=archive_payload,
        user_id=user_a["id"],
    )
    _require_status(status, 200, "first archival write", first_body)
    first_passage = _first_passage(first_body, "first archival write")
    status, second_body = client.call(
        "POST",
        f"/v1/agents/{agent_id}/archival-memory",
        payload=archive_payload,
        user_id=user_a["id"],
    )
    _require_status(status, 200, "retry archival write", second_body)
    second_passage = _first_passage(second_body, "retry archival write")
    status, passages = client.call(
        "GET",
        f"/v1/agents/{agent_id}/archival-memory?limit=100&ascending=true",
        user_id=user_a["id"],
    )
    _require_status(status, 200, "list archival memory", passages)
    matching_passages = [
        passage for passage in passages if passage.get("text") == canaries["archive"]
    ]

    isolation_statuses = []
    for path in (
        f"/v1/agents/{agent_id}",
        f"/v1/blocks/{human_block['id']}",
        f"/v1/archives/{first_passage['archive_id']}",
    ):
        other_status, _ = client.call("GET", path, user_id=user_b["id"])
        isolation_statuses.append(other_status)

    _install_failure_trigger()
    failed_status, failed_body = client.call(
        "PATCH",
        f"/v1/agents/{agent_id}/core-memory/blocks/human",
        payload={"value": canaries["core_failed"]},
        user_id=user_a["id"],
    )
    status, block_after_failure = client.call(
        "GET",
        f"/v1/blocks/{human_block['id']}",
        user_id=user_a["id"],
    )
    _require_status(status, 200, "read block after injected failure", block_after_failure)
    system_has_failed_canary = _system_message_contains(agent_id, canaries["core_failed"])
    _drop_failure_trigger()

    checks = {
        "provider_free_agent_creation_passes": agent.get("id") == agent_id,
        "core_block_mutation_passes": normal_update.get("value")
        == canaries["core_normal"],
        "inactive_archive_write_and_read_passes": len(matching_passages) == 2,
        "cross_organization_isolation_passes": isolation_statuses == [404, 404, 404],
        "failed_core_update_returns_server_error_after_block_mutation": (
            failed_status == 500
            and block_after_failure.get("value") == canaries["core_failed"]
            and not system_has_failed_canary
        ),
        "identical_archive_retry_creates_duplicate_rows": (
            first_passage["id"] != second_passage["id"]
            and len(matching_passages) == 2
        ),
    }
    state = {
        "repeat": repeat,
        "canaries": canaries,
        "org_a_id": org_a["id"],
        "org_b_id": org_b["id"],
        "user_a_id": user_a["id"],
        "user_b_id": user_b["id"],
        "agent_id": agent_id,
        "archive_id": first_passage["archive_id"],
        "passage_ids": [first_passage["id"], second_passage["id"]],
        "block_ids": [human_block["id"], persona_block["id"]],
        "human_block_id": human_block["id"],
    }
    _write_json(evidence_dir / "state.json", state)
    _write_json(
        evidence_dir / "phase-initial.json",
        {
            "phase": "initial",
            "repeat": repeat,
            "checks": checks,
            "isolation_statuses": isolation_statuses,
            "failed_update_status": failed_status,
            "failed_update_body": failed_body,
            "system_message_contains_failed_canary": system_has_failed_canary,
            "http_calls": client.calls,
            "http_call_count": len(client.calls),
            "external_model_calls": 0,
            "provider_calls": 0,
        },
    )
    return 0 if all(checks.values()) else 3


def phase_restart_and_cleanup(evidence_dir: Path, repeat: int) -> int:
    state = json.loads((evidence_dir / "state.json").read_text(encoding="utf-8"))
    if state.get("repeat") != repeat:
        raise DoctorError("repeat does not match retained state")
    client = ApiClient()
    user_a = state["user_a_id"]
    user_b = state["user_b_id"]
    agent_id = state["agent_id"]
    canaries = state["canaries"]

    status, agent = client.call("GET", f"/v1/agents/{agent_id}", user_id=user_a)
    _require_status(status, 200, "agent after restart", agent)
    status, block = client.call(
        "GET", f"/v1/blocks/{state['human_block_id']}", user_id=user_a
    )
    _require_status(status, 200, "block after restart", block)
    status, passages = client.call(
        "GET",
        f"/v1/agents/{agent_id}/archival-memory?limit=100&ascending=true",
        user_id=user_a,
    )
    _require_status(status, 200, "archive after restart", passages)
    matching = [passage for passage in passages if passage.get("text") == canaries["archive"]]

    other_status, _ = client.call("GET", f"/v1/agents/{agent_id}", user_id=user_b)
    retry_status, retry_body = client.call(
        "PATCH",
        f"/v1/agents/{agent_id}/core-memory/blocks/human",
        payload={"value": canaries["core_failed"]},
        user_id=user_a,
    )
    system_repaired = _system_message_contains(agent_id, canaries["core_failed"])

    delete_agent_status, _ = client.call("DELETE", f"/v1/agents/{agent_id}", user_id=user_a)
    missing_agent_status, _ = client.call("GET", f"/v1/agents/{agent_id}", user_id=user_a)
    archive_after_agent_delete_status, _ = client.call(
        "GET", f"/v1/archives/{state['archive_id']}", user_id=user_a
    )
    surviving_block_statuses = []
    for block_id in state["block_ids"]:
        block_status, _ = client.call("GET", f"/v1/blocks/{block_id}", user_id=user_a)
        surviving_block_statuses.append(block_status)

    passage_count_after_agent_delete = _db_scalar(
        "SELECT count(*) FROM archival_passages WHERE archive_id = %s",
        (state["archive_id"],),
    )
    for passage_id in state["passage_ids"]:
        delete_status, delete_body = client.call(
            "DELETE",
            f"/v1/archives/{state['archive_id']}/passages/{passage_id}",
            user_id=user_a,
        )
        _require_status(delete_status, 204, "delete archival passage", delete_body)
    archive_delete_status, archive_delete_body = client.call(
        "DELETE", f"/v1/archives/{state['archive_id']}", user_id=user_a
    )
    _require_status(archive_delete_status, 204, "delete archive", archive_delete_body)
    block_delete_statuses = []
    for block_id in state["block_ids"]:
        block_status, block_body = client.call(
            "DELETE", f"/v1/blocks/{block_id}", user_id=user_a
        )
        _require_status(block_status, 200, "delete block", block_body)
        block_delete_statuses.append(block_status)

    archive_missing_status, _ = client.call(
        "GET", f"/v1/archives/{state['archive_id']}", user_id=user_a
    )
    missing_block_statuses = []
    for block_id in state["block_ids"]:
        block_status, _ = client.call("GET", f"/v1/blocks/{block_id}", user_id=user_a)
        missing_block_statuses.append(block_status)
    current_passage_count = _db_scalar(
        "SELECT count(*) FROM archival_passages WHERE id = ANY(%s)",
        (state["passage_ids"],),
    )
    current_block_count = _db_scalar(
        'SELECT count(*) FROM "block" WHERE id = ANY(%s)',
        (state["block_ids"],),
    )

    checks = {
        "normal_state_survives_fresh_process": (
            agent.get("id") == agent_id
            and block.get("value") == canaries["core_failed"]
            and len(matching) == 2
        ),
        "failed_core_update_mutation_survives_fresh_process": (
            block.get("value") == canaries["core_failed"]
        ),
        "duplicate_archive_rows_survive_fresh_process": len(matching) == 2,
        "cross_organization_isolation_survives_fresh_process": other_status == 404,
        "failed_core_update_retry_repairs_compiled_prompt": (
            retry_status == 200
            and isinstance(retry_body, dict)
            and retry_body.get("value") == canaries["core_failed"]
            and system_repaired
        ),
        "deleting_agent_retains_owner_archive_and_core_blocks": (
            delete_agent_status == 200
            and missing_agent_status == 404
            and archive_after_agent_delete_status == 200
            and surviving_block_statuses == [200, 200]
            and passage_count_after_agent_delete == 2
        ),
        "explicit_archive_and_block_delete_is_logically_effective": (
            archive_missing_status == 404
            and missing_block_statuses == [404, 404]
            and current_passage_count == 0
            and current_block_count == 0
            and block_delete_statuses == [200, 200]
        ),
    }
    _write_json(
        evidence_dir / "phase-restart-cleanup.json",
        {
            "phase": "restart-cleanup",
            "repeat": repeat,
            "checks": checks,
            "http_calls": client.calls,
            "http_call_count": len(client.calls),
            "passage_count_after_agent_delete": passage_count_after_agent_delete,
            "current_passage_count": current_passage_count,
            "current_block_count": current_block_count,
            "external_model_calls": 0,
            "provider_calls": 0,
        },
    )
    return 0 if all(checks.values()) else 3


def phase_scan(evidence_dir: Path, repeat: int, scan_root: Path) -> int:
    state = json.loads((evidence_dir / "state.json").read_text(encoding="utf-8"))
    if state.get("repeat") != repeat:
        raise DoctorError("repeat does not match retained state")
    canaries = state["canaries"]
    hits: dict[str, list[str]] = {name: [] for name in canaries}
    file_count = 0
    total_bytes = 0
    for path in sorted(scan_root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        file_count += 1
        total_bytes += path.stat().st_size
        try:
            data = path.read_bytes()
        except OSError:
            continue
        relative = str(path.relative_to(scan_root))
        for name, canary in canaries.items():
            if canary.encode("utf-8") in data:
                hits[name].append(relative)
    checks = {
        "stopped_postgres_plaintext_residue_present": any(hits.values()),
    }
    _write_json(
        evidence_dir / "phase-scan.json",
        {
            "phase": "scan",
            "repeat": repeat,
            "checks": checks,
            "plaintext_hits": hits,
            "scanned_file_count": file_count,
            "stopped_state_bytes": total_bytes,
        },
    )
    return 0 if all(checks.values()) else 3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase",
        choices=("initial", "restart-cleanup", "scan"),
        required=True,
    )
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--repeat", type=int, choices=(1, 2), required=True)
    parser.add_argument("--scan-root", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.phase == "initial":
        return phase_initial(args.evidence_dir, args.repeat)
    if args.phase == "restart-cleanup":
        return phase_restart_and_cleanup(args.evidence_dir, args.repeat)
    if args.scan_root is None:
        raise DoctorError("--scan-root is required for the scan phase")
    return phase_scan(args.evidence_dir, args.repeat, args.scan_root)


if __name__ == "__main__":
    raise SystemExit(main())
