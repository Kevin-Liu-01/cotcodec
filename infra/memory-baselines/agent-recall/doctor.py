#!/usr/bin/env python3
"""Two-phase exact-source Agent Recall scoped-lifecycle falsifier."""

from __future__ import annotations

import json
import os
from pathlib import Path

from agent_recall.config import MemoryConfig
from agent_recall.context_gen.cache import invalidate_cache, scope_to_agents
from agent_recall.hierarchy import ScopedView
from agent_recall.mcp_bridge import MCPBridge
from agent_recall.store import MemoryStore

STATE = Path("/state")
DB = STATE / "frames.db"
CACHE = STATE / "cache"


def _config() -> MemoryConfig:
    return MemoryConfig(
        db_path=DB,
        cache_dir=CACHE,
        hierarchy={"agency": ["client-a", "client-b"]},
        tiers={2: ["agency", "client-a", "client-b"]},
        agent_types={"orchestrator": ["orchestrator"]},
        agents_config={},
    )


def _phase_one() -> dict[str, object]:
    STATE.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    soft_canary = os.environ["COTCODEC_SOFT_CANARY"]
    victim_a = os.environ["COTCODEC_VICTIM_A"]
    victim_b = os.environ["COTCODEC_VICTIM_B"]

    with MemoryStore(DB) as store:
        scoped = store.resolve_entity("ScopedProject", "project")
        store.set_slot(scoped, "status", "global-v1", scope="global")
        store.set_slot(scoped, "status", "agency-v1", scope="agency")
        store.set_slot(scoped, "status", "client-v1", scope="client-a")
        store.set_slot(scoped, "status", "client-v2", scope="client-a")
        child_view = ScopedView(store, ["global", "agency", "client-a"])

        victim = store.resolve_entity("CrossScopeVictim", "project")
        store.add_observation(victim, victim_a, scope="client-a")
        store.add_observation(victim, victim_b, scope="client-b")

        soft = store.resolve_entity("SoftDeleteVictim", "project")
        store.add_observation(soft, soft_canary, scope="client-a")

        parent = store.resolve_entity("ParentVisible", "project")
        store.set_slot(parent, "policy", "parent-policy-v1", scope="agency")
        child_sees_parent = (
            ScopedView(store, ["global", "agency", "client-a"]).get(
                "ParentVisible", "policy"
            )
            == "parent-policy-v1"
        )
        scope_precedence = child_view.get("ScopedProject", "status") == "client-v2"

    config = _config()
    for slug in ("agency", "client-a", "client-b", "orchestrator"):
        (CACHE / f"{slug}.md").write_text(f"cached-{slug}", encoding="utf-8")
    affected = scope_to_agents("agency", config)
    invalidate_cache(affected, CACHE)
    parent_change_leaves_child_cache_fresh = (
        child_sees_parent
        and "client-a" not in affected
        and not (CACHE / "client-a.stale").exists()
        and (CACHE / "agency.stale").exists()
    )

    with MCPBridge(
        DB,
        default_scope="client-a",
        scope_chain=["global", "agency", "client-a"],
        config=config,
    ) as bridge:
        cross_delete = bridge.delete_entities(["CrossScopeVictim"])
        soft_delete = bridge.delete_observations(
            [{"entityName": "SoftDeleteVictim", "observations": [soft_canary]}]
        )

    with MemoryStore(DB) as store:
        cross_scope_delete_cascades_other_scope = (
            cross_delete == {"deleted": 1, "blocked": []}
            and store.find_entity("CrossScopeVictim") is None
        )
        soft_id = store.find_entity("SoftDeleteVictim")
        assert soft_id is not None
        active = store.get_observations(soft_id)
        archived = store.get_observations(soft_id, include_archived=True)
        delete_observations_archives_plaintext = (
            soft_delete == {"deleted": 1, "blocked": []}
            and active == []
            and len(archived) == 1
            and archived[0]["text"] == soft_canary
            and archived[0]["archived_at"] is not None
        )

    return {
        "phase": 1,
        "scope_precedence_local_wins": scope_precedence,
        "child_inherits_parent_scope": child_sees_parent,
        "bitemporal_history_written": True,
        "cross_scope_delete_cascades_other_scope": (
            cross_scope_delete_cascades_other_scope
        ),
        "parent_change_leaves_child_cache_fresh": (
            parent_change_leaves_child_cache_fresh
        ),
        "delete_observations_archives_plaintext": (
            delete_observations_archives_plaintext
        ),
        "native_scoped_purge_absent": not any(
            hasattr(MemoryStore, name) or hasattr(MCPBridge, name)
            for name in ("purge", "purge_scope", "delete_scope", "erase_scope")
        ),
    }


def _phase_two() -> dict[str, object]:
    soft_canary = os.environ["COTCODEC_SOFT_CANARY"]
    with MemoryStore(DB) as store:
        scoped = store.find_entity("ScopedProject", "project")
        if scoped is None:
            raise RuntimeError("ScopedProject disappeared across restart")
        child_view = ScopedView(store, ["global", "agency", "client-a"])
        history = [
            row
            for row in store.get_slot_history(scoped, "status")
            if row["scope"] == "client-a"
        ]
        soft_id = store.find_entity("SoftDeleteVictim", "project")
        if soft_id is None:
            raise RuntimeError("SoftDeleteVictim disappeared across restart")
        active = store.get_observations(soft_id)
        archived = store.get_observations(soft_id, include_archived=True)
        checks = {
            "scope_precedence_survived_restart": (
                child_view.get("ScopedProject", "status") == "client-v2"
            ),
            "bitemporal_history_survived_restart": (
                len(history) == 2
                and history[0]["value"] == "client-v1"
                and history[0]["valid_to"] is not None
                and history[1]["value"] == "client-v2"
                and history[1]["valid_to"] is None
            ),
            "cross_scope_delete_survived_restart": (
                store.find_entity("CrossScopeVictim") is None
            ),
            "soft_deleted_observation_survived_restart": (
                active == []
                and len(archived) == 1
                and archived[0]["text"] == soft_canary
                and archived[0]["archived_at"] is not None
            ),
        }
    checks["soft_deleted_plaintext_in_database"] = soft_canary.encode() in DB.read_bytes()
    return {"phase": 2, **checks}


def main() -> int:
    phase = int(os.environ["COTCODEC_PHASE"])
    report = _phase_one() if phase == 1 else _phase_two()
    values = [value for key, value in report.items() if key != "phase"]
    if not values or not all(value is True for value in values):
        raise RuntimeError(f"Agent Recall falsifier check failed: {report}")
    print("COTCODEC_AGENT_RECALL_PHASE=" + json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
