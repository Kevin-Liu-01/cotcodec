#!/usr/bin/env python3
"""Network-free exact-source Mnemo Cortex lifecycle and mechanism doctor."""

from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import json
import math
import os
import re
import shutil
from pathlib import Path
from typing import Any
from unittest.mock import patch

STATE = Path("/state")
DATA_ROOT = STATE / "agentb"
PASSPORT_ROOT = STATE / "passport"
TOKEN = os.environ["COTCODEC_RUN_TOKEN"]
PHASE = int(os.environ["COTCODEC_PHASE"])
MARKER = "COTCODEC_MNEMO_CORTEX_PHASE="
DIMENSION = 768

SMART_CANARY = f"COTMC_SMART_{TOKEN}"
RAW_CANARY = f"COTMC_RAW_{TOKEN}"
ANALYST_CANARY = f"COTMC_ANALYST_{TOKEN}"
PASSPORT_CANARY = f"COTMC_PASSPORT_{TOKEN}"


def _tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_]+", text.lower())


def _vector(text: str) -> list[float]:
    values = [0.0] * DIMENSION
    for token in _tokens(text):
        digest = hashlib.sha256(token.encode()).digest()
        index = int.from_bytes(digest[:4], "big") % DIMENSION
        values[index] += 1.0 if digest[4] & 1 else -1.0
    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return [value / norm for value in values]


class DeterministicEmbedding:
    """Local fixed-width token hashing; never opens a provider connection."""

    active_label = "cotcodec/deterministic-embedding"

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    @property
    def status(self) -> dict[str, Any]:
        return {
            "primary": "cotcodec",
            "active": "deterministic",
            "failed_over": False,
            "circuit_open": False,
            "primary_retry_in": None,
            "fallback_count": 0,
        }

    @property
    def primary(self) -> DeterministicEmbedding:
        return self

    async def embed(
        self, text: str, *, use_breaker: bool = True, task_type: str = "document"
    ) -> list[float]:
        self.calls.append({
            "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "use_breaker": use_breaker,
            "task_type": task_type,
        })
        return _vector(text)

    async def health_check(self) -> bool:
        return True


class DeterministicReasoning:
    """Schema-compatible scripted classifier and Analyst without model calls."""

    active_label = "cotcodec/deterministic-reasoning"

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    @property
    def status(self) -> dict[str, Any]:
        return {
            "primary": "cotcodec",
            "active": "deterministic",
            "failed_over": False,
            "circuit_open": False,
            "primary_retry_in": None,
            "fallback_count": 0,
        }

    async def generate(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 2048,
        *,
        use_breaker: bool = True,
    ) -> str:
        kind = "other"
        if "classify a single memory" in system:
            kind = "classification"
            reply = "decision"
        elif "silent note-taker" in system:
            kind = "analyst"
            reply = json.dumps([
                {
                    "category": "decision",
                    "summary": (
                        f"{ANALYST_CANARY} preserves the exact-source admission decision."
                    ),
                    "key_facts": [RAW_CANARY, "exact-source admission"],
                    "confidence": "high",
                }
            ])
        elif "Summarize this agent session" in system:
            kind = "session-summary"
            reply = f"Summary for {TOKEN}"
        else:
            reply = "[]"
        self.calls.append({
            "kind": kind,
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "system_sha256": hashlib.sha256(system.encode()).hexdigest(),
            "max_tokens": max_tokens,
            "use_breaker": use_breaker,
        })
        return reply

    async def health_check(self) -> bool:
        return True


def _config():
    from agentb.config import (
        AgentBConfig,
        AnalysisConfig,
        CacheConfig,
        ClassificationConfig,
        DedupConfig,
        ExpansionConfig,
        ProviderConfig,
        ResilientProviderConfig,
        ServerConfig,
    )

    provider = ResilientProviderConfig(
        primary=ProviderConfig(provider="ollama", model="offline-doctor")
    )
    return AgentBConfig(
        reasoning=provider,
        embedding=provider,
        data_dir=str(DATA_ROOT),
        server=ServerConfig(
            host="127.0.0.1", port=50099, allow_unauthenticated=True
        ),
        cache=CacheConfig(l3_similarity_threshold=-1.0),
        classification=ClassificationConfig(enabled=True),
        dedup=DedupConfig(enabled=False),
        analysis=AnalysisConfig(
            enabled=True,
            interval_cycles=12,
            max_memories_per_cycle=30,
            dedup_similarity=1.01,
        ),
        expansion=ExpansionConfig(enabled=False),
    )


def _app():
    embedding = DeterministicEmbedding()
    reasoning = DeterministicReasoning()
    with (
        patch("agentb.server.create_resilient_embedding", return_value=embedding),
        patch("agentb.server.create_resilient_reasoning", return_value=reasoning),
    ):
        from agentb.server import create_app

        app = create_app(_config())
    return app, reasoning, embedding


def _regular_file_scan(root: Path, needles: list[str]) -> dict[str, list[str]]:
    encoded = {needle: needle.encode() for needle in needles}
    matches = {needle: [] for needle in needles}
    if not root.exists():
        return matches
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        name = path.relative_to(root).as_posix()
        for needle, raw in encoded.items():
            if raw in data:
                matches[needle].append(name)
    return matches


def _memory_rows() -> list[dict[str, Any]]:
    memory_dir = DATA_ROOT / "agents" / "alpha" / "memory"
    rows: list[dict[str, Any]] = []
    for path in sorted(memory_dir.glob("*.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        row["_path"] = path.relative_to(STATE).as_posix()
        rows.append(row)
    return rows


def _context_contains(body: dict[str, Any], needle: str) -> bool:
    return any(needle in row.get("content", "") for row in body.get("chunks", []))


def _observe_payload() -> dict[str, Any]:
    return {
        "proposed_claim": f"Prefers exact receipts named {PASSPORT_CANARY}",
        "type": "preference",
        "source_platform": "cotcodec",
        "source_session_id": f"passport-{TOKEN}",
        "evidence": [
            {"turn_ref": "turn-1", "excerpt": f"User requested {PASSPORT_CANARY}"},
            {"turn_ref": "turn-2", "excerpt": "User repeated the receipt preference"},
        ],
    }


def _dream_projection() -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location(
        "cotcodec_mnemo_dream", "/opt/mnemo/mnemo-dream.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load mnemo-dream.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    calls: list[dict[str, Any]] = []

    def fake_call(system: str, prompt: str, **_: Any) -> tuple[str, dict[str, int]]:
        kind = "rollup" if system == module.ROLLUP_SYSTEM_PROMPT else "per-agent"
        calls.append({
            "kind": kind,
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "contains_alpha": "alpha" in prompt,
            "contains_beta": "beta" in prompt,
        })
        if kind == "rollup":
            return f"JOINT_{TOKEN}", {"prompt_tokens": 11, "completion_tokens": 3}
        return f"BRIEF_{len(calls)}_{TOKEN}", {
            "prompt_tokens": 7,
            "completion_tokens": 2,
        }

    module.OPENROUTER_API_KEY = "offline-doctor-not-a-secret"
    module._call_openrouter_adaptive = fake_call
    memories = [
        {
            "agent_id": agent,
            "session_id": f"{agent}-{TOKEN}",
            "timestamp": "2026-08-26T00:00:00Z",
            "summary": f"{agent} completed {TOKEN}",
            "key_facts": [],
            "projects": [],
            "decisions": [],
        }
        for agent in ("alpha", "beta")
    ]
    result = module.synthesize(memories)
    return {"result": result, "calls": calls}


def _route_paths(app: Any) -> list[str]:
    """Collect path-bearing routes while tolerating nested framework routers."""
    pending = list(getattr(app, "routes", ()))
    seen: set[int] = set()
    paths: set[str] = set()
    while pending:
        route = pending.pop()
        identity = id(route)
        if identity in seen:
            continue
        seen.add(identity)
        path = getattr(route, "path", None)
        if isinstance(path, str):
            paths.add(path)
        nested = getattr(route, "routes", None)
        if isinstance(nested, (list, tuple)):
            pending.extend(nested)
    return sorted(paths)


def _phase_one() -> dict[str, Any]:
    from fastapi.testclient import TestClient

    app, reasoning, embedding = _app()
    with TestClient(app, raise_server_exceptions=False) as client:
        smart = client.post("/writeback", json={
            "session_id": f"smart-{TOKEN}",
            "agent_id": "alpha",
            "summary": f"Decision {SMART_CANARY}: retain exact source.",
            "key_facts": [SMART_CANARY],
            "source": "user",
            "force": True,
        })
        raw = client.post("/writeback", json={
            "session_id": f"raw-{TOKEN}",
            "agent_id": "alpha",
            "summary": f"[AUTO-CAPTURE] raw session {RAW_CANARY}",
            "key_facts": ["auto_capture_flush", RAW_CANARY],
            "source": "tool",
            "category": "session_log",
            "force": True,
        })
        default = client.post("/context", json={
            "agent_id": "alpha", "prompt": RAW_CANARY, "max_results": 10,
        })
        drill = client.post("/context", json={
            "agent_id": "alpha", "prompt": RAW_CANARY, "max_results": 10,
            "category": "session_log", "exclude_categories": [],
        })
        asyncio.run(app.state.maintenance_cycle(6))
        rows = _memory_rows()
        analyst = [row for row in rows if row.get("classified_by") == "analyst"]
        raw_rows = [row for row in rows if RAW_CANARY in row.get("summary", "")]
        dream = _dream_projection()

        first_observe = client.post("/passport/observe", json=_observe_payload())
        first_pending = client.post("/passport/pending", json={})
        second_observe = client.post("/passport/observe", json=_observe_payload())
        second_pending = client.post("/passport/pending", json={})

        routes = _route_paths(app)

    classification_calls = [
        call for call in reasoning.calls if call["kind"] == "classification"
    ]
    analyst_calls = [call for call in reasoning.calls if call["kind"] == "analyst"]
    pending_one = first_pending.json().get("items", []) if first_pending.status_code == 200 else []
    pending_two = (
        second_pending.json().get("items", [])
        if second_pending.status_code == 200
        else []
    )
    checks = {
        "smart_note_classification_passes": (
            smart.status_code == 200
            and smart.json().get("category_used") == "decision"
            and len(classification_calls) == 1
        ),
        "default_recall_hides_session_log": (
            default.status_code == 200
            and not _context_contains(default.json(), RAW_CANARY)
            and all(row.get("category") != "session_log" for row in default.json()["chunks"])
        ),
        "explicit_drilldown_recalls_session_log": (
            drill.status_code == 200 and _context_contains(drill.json(), RAW_CANARY)
        ),
        "analyst_note_has_source_lineage": (
            len(analyst) == 1
            and ANALYST_CANARY in analyst[0].get("summary", "")
            and raw.json().get("memory_id") in analyst[0].get("derived_from", [])
            and len(analyst_calls) == 1
        ),
        "analyst_retains_raw_source_log": (
            len(raw_rows) == 1
            and raw_rows[0].get("analyst_processed") is True
            and raw_rows[0].get("category") == "session_log"
        ),
        "deterministic_two_agent_rollup_passes": (
            dream["result"] == f"JOINT_{TOKEN}"
            and [row["kind"] for row in dream["calls"]]
            == ["per-agent", "per-agent", "rollup"]
            and dream["calls"][-1]["contains_alpha"]
            and dream["calls"][-1]["contains_beta"]
        ),
        "official_container_has_no_git": shutil.which("git") is None,
        "passport_observe_returns_server_error_after_pending_mutation": (
            first_observe.status_code == 500
            and len(pending_one) == 1
            and PASSPORT_CANARY in pending_one[0].get("proposed_claim", "")
        ),
        "repeated_failed_observe_creates_duplicate_pending_rows": (
            second_observe.status_code == 500
            and len(pending_two) == 2
            and len({row.get("proposed_claim") for row in pending_two}) == 1
        ),
        "native_primary_memory_purge_absent": all(
            route not in routes for route in (
                "/delete", "/forget", "/purge", "/memory/delete", "/memory/purge"
            )
        ),
    }
    return {
        "phase": 1,
        "checks": checks,
        "metrics": {
            "smart_response": smart.json(),
            "raw_response": raw.json(),
            "default_context": default.json(),
            "drill_context": drill.json(),
            "memory_rows": rows,
            "reasoning_calls": reasoning.calls,
            "embedding_call_count": len(embedding.calls),
            "dream_projection": dream,
            "passport_first_status": first_observe.status_code,
            "passport_second_status": second_observe.status_code,
            "pending_after_first": pending_one,
            "pending_after_second": pending_two,
            "routes": routes,
        },
    }


def _phase_two() -> dict[str, Any]:
    from fastapi.testclient import TestClient

    app, reasoning, embedding = _app()
    with TestClient(app, raise_server_exceptions=False) as client:
        smart = client.post("/context", json={
            "agent_id": "alpha", "prompt": SMART_CANARY, "max_results": 10,
        })
        analyst = client.post("/context", json={
            "agent_id": "alpha", "prompt": ANALYST_CANARY, "max_results": 10,
        })
        raw_default = client.post("/context", json={
            "agent_id": "alpha", "prompt": RAW_CANARY, "max_results": 10,
        })
        raw_drill = client.post("/context", json={
            "agent_id": "alpha", "prompt": RAW_CANARY, "max_results": 10,
            "category": "session_log", "exclude_categories": [],
        })
        pending = client.post("/passport/pending", json={})
        rows = _memory_rows()
        routes = _route_paths(app)

    pending_rows = pending.json().get("items", []) if pending.status_code == 200 else []
    raw_memory_ids = {
        row.get("id")
        for row in rows
        if row.get("category") == "session_log"
        and RAW_CANARY in row.get("summary", "")
        and isinstance(row.get("id"), str)
    }
    raw_default_chunks = raw_default.json().get("chunks", [])
    raw_drill_chunks = raw_drill.json().get("chunks", [])
    scan = _regular_file_scan(
        STATE, [SMART_CANARY, RAW_CANARY, ANALYST_CANARY, PASSPORT_CANARY]
    )
    checks = {
        "normal_state_survives_fresh_process": (
            smart.status_code == 200
            and analyst.status_code == 200
            and _context_contains(smart.json(), SMART_CANARY)
            and _context_contains(analyst.json(), ANALYST_CANARY)
            and len(rows) == 3
        ),
        "default_recall_hides_session_log_after_restart": (
            raw_default.status_code == 200
            and len(raw_memory_ids) == 1
            and all(
                row.get("category") != "session_log"
                and row.get("memory_id") not in raw_memory_ids
                for row in raw_default_chunks
            )
        ),
        "explicit_drilldown_recalls_session_log_after_restart": (
            raw_drill.status_code == 200
            and any(
                row.get("category") == "session_log"
                and row.get("memory_id") in raw_memory_ids
                for row in raw_drill_chunks
            )
        ),
        "duplicate_pending_rows_survive_fresh_process": (
            pending.status_code == 200
            and len(pending_rows) == 2
            and all(PASSPORT_CANARY in row.get("proposed_claim", "") for row in pending_rows)
        ),
        "native_primary_memory_purge_absent_after_restart": all(
            route not in routes for route in (
                "/delete", "/forget", "/purge", "/memory/delete", "/memory/purge"
            )
        ),
        "current_file_plaintext_residue_present": all(scan[needle] for needle in scan),
    }
    return {
        "phase": 2,
        "checks": checks,
        "metrics": {
            "smart_context": smart.json(),
            "analyst_context": analyst.json(),
            "raw_default_context": raw_default.json(),
            "raw_drill_context": raw_drill.json(),
            "raw_memory_ids": sorted(raw_memory_ids),
            "pending_after_restart": pending_rows,
            "memory_rows": rows,
            "current_file_scan": scan,
            "reasoning_call_count": len(reasoning.calls),
            "embedding_call_count": len(embedding.calls),
            "routes": routes,
        },
    }


def main() -> int:
    report = _phase_one() if PHASE == 1 else _phase_two() if PHASE == 2 else None
    if report is None:
        raise SystemExit(f"unsupported phase: {PHASE}")
    checks = report["checks"]
    print(MARKER + json.dumps(report, separators=(",", ":"), sort_keys=True))
    if not checks or not all(value is True for value in checks.values()):
        failed = sorted(key for key, value in checks.items() if value is not True)
        print(f"Mnemo Cortex doctor checks failed: {failed}")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
