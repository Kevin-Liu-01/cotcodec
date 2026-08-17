#!/usr/bin/env python3
"""Contained Neo4j Agent Memory preference-supersession lifecycle doctor."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from datetime import UTC, datetime
from typing import Any

from neo4j_agent_memory import MemoryClient, MemorySettings, Neo4jConfig
from neo4j_agent_memory.config import ExtractionConfig, ExtractorType
from neo4j_agent_memory.embeddings.base import BaseEmbedder
from pydantic import SecretStr

SOURCE_REVISION = "231d60eac9401ab156ba194b519d89dd644dadb8"
USER_A = "cotcodec-neo4j-a"
USER_B = "cotcodec-neo4j-b"


class FailOnCallEmbedder(BaseEmbedder):
    """Proves that the registered no-embedding path never calls a model."""

    calls = 0

    @property
    def dimensions(self) -> int:
        return 8

    async def embed(self, text: str) -> list[float]:
        type(self).calls += 1
        raise RuntimeError(f"embedding was forbidden: {text!r}")


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


async def _state(client: MemoryClient) -> dict[str, Any]:
    nodes = await client.graph.execute_read(
        """
        MATCH (u:User)-[:HAS_PREFERENCE]->(p:Preference)
        RETURN u.identifier AS user, p.id AS id, p.category AS category,
               p.preference AS preference, p.metadata AS metadata,
               toString(p.valid_from) AS valid_from,
               toString(p.valid_until) AS valid_until,
               EXISTS { (p)-[:SUPERSEDED_BY]->(:Preference) } AS superseded
        ORDER BY user, id
        """
    )
    edges = await client.graph.execute_read(
        """
        MATCH (old:Preference)-[:SUPERSEDED_BY]->(new:Preference)
        RETURN old.id AS old_id, new.id AS new_id
        ORDER BY old_id, new_id
        """
    )
    projection = {
        "nodes": [dict(row) for row in nodes],
        "supersession_edges": [dict(row) for row in edges],
    }
    projection["state_sha256"] = hashlib.sha256(_canonical(projection)).hexdigest()
    return projection


def _settings() -> MemorySettings:
    return MemorySettings(
        backend="bolt",
        neo4j=Neo4jConfig(
            uri=os.environ["NEO4J_URI"],
            username="neo4j",
            password=SecretStr(os.environ["NEO4J_PASSWORD"]),
        ),
        extraction=ExtractionConfig(extractor_type=ExtractorType.NONE),
        llm=None,
    )


async def _establish() -> dict[str, Any]:
    embedder = FailOnCallEmbedder()
    async with MemoryClient(_settings(), embedder=embedder) as client:
        await client.graph.execute_write("MATCH (n) DETACH DELETE n")
        old = await client.long_term.add_preference(
            "consultants",
            "Prefer junior consultants",
            generate_embedding=False,
            metadata={"event_id": "event-001", "step": 1, "source": "pre-extracted"},
            user_identifier=USER_A,
        )
        await asyncio.sleep(0.05)
        as_of = datetime.now(UTC)
        await asyncio.sleep(0.05)
        new = await client.long_term.add_preference(
            "consultants",
            "Prefer senior consultants",
            generate_embedding=False,
            metadata={"event_id": "event-002", "step": 2, "source": "pre-extracted"},
            user_identifier=USER_A,
        )
        other = await client.long_term.add_preference(
            "format",
            "Prefer concise output",
            generate_embedding=False,
            metadata={"event_id": "event-003", "step": 1, "source": "pre-extracted"},
            user_identifier=USER_B,
        )
        await client.long_term.supersede_preference(old.id, new.id)
        await client.long_term.supersede_preference(old.id, new.id)
        active = await client.long_term.get_preferences_for(USER_A, active_only=True)
        history = await client.long_term.get_preferences_for(USER_A, active_only=False)
        past = await client.long_term.get_preferences_for(
            USER_A, active_only=False, as_of=as_of
        )
        tenant_b = await client.long_term.get_preferences_for(USER_B, active_only=False)
        state = await _state(client)
    expected = {
        "active_ids": [str(new.id)],
        "all_ids": sorted([str(old.id), str(new.id)]),
        "as_of_ids": [str(old.id)],
        "tenant_b_ids": [str(other.id)],
    }
    observed = {
        "active_ids": sorted(str(item.id) for item in active),
        "all_ids": sorted(str(item.id) for item in history),
        "as_of_ids": sorted(str(item.id) for item in past),
        "tenant_b_ids": sorted(str(item.id) for item in tenant_b),
    }
    if observed != expected:
        raise RuntimeError(f"pre-restart lifecycle semantics drifted: {observed}")
    if len(state["supersession_edges"]) != 1:
        raise RuntimeError("idempotent supersession produced a duplicate or missing edge")
    if FailOnCallEmbedder.calls != 0:
        raise RuntimeError("the no-embedding doctor called an embedding model")
    return {
        "schema_version": 1,
        "phase": "establish",
        "source_revision": SOURCE_REVISION,
        "model_calls": 0,
        "as_of": as_of.isoformat(),
        "expected": expected,
        "state": state,
    }


async def _verify_and_purge(expected: dict[str, Any]) -> dict[str, Any]:
    embedder = FailOnCallEmbedder()
    async with MemoryClient(_settings(), embedder=embedder) as client:
        state = await _state(client)
        if state != expected["state"]:
            raise RuntimeError("retained-volume restart changed the native state")
        active = await client.long_term.get_preferences_for(USER_A, active_only=True)
        history = await client.long_term.get_preferences_for(USER_A, active_only=False)
        past = await client.long_term.get_preferences_for(
            USER_A,
            active_only=False,
            as_of=datetime.fromisoformat(expected["as_of"]),
        )
        observed = {
            "active_ids": sorted(str(item.id) for item in active),
            "all_ids": sorted(str(item.id) for item in history),
            "as_of_ids": sorted(str(item.id) for item in past),
        }
        for key in ("active_ids", "all_ids", "as_of_ids"):
            if observed[key] != expected["expected"][key]:
                raise RuntimeError(f"post-restart {key} drifted")
        await client.graph.execute_write("MATCH (n) DETACH DELETE n")
        residue = await client.graph.execute_read(
            "MATCH (n) RETURN count(n) AS nodes"
        )
        if residue[0]["nodes"] != 0:
            raise RuntimeError("purge left graph residue")
    if FailOnCallEmbedder.calls != 0:
        raise RuntimeError("the post-restart doctor called an embedding model")
    return {
        "schema_version": 1,
        "phase": "verify-purge",
        "source_revision": SOURCE_REVISION,
        "model_calls": 0,
        "state_sha256": state["state_sha256"],
        "purge_nodes": 0,
    }


async def _verify_empty() -> dict[str, Any]:
    async with MemoryClient(_settings(), embedder=FailOnCallEmbedder()) as client:
        rows = await client.graph.execute_read(
            "MATCH (n) OPTIONAL MATCH ()-[r]->() "
            "RETURN count(DISTINCT n) AS nodes, count(r) AS edges"
        )
    if rows[0]["nodes"] != 0 or rows[0]["edges"] != 0:
        raise RuntimeError("purged graph state returned after restart")
    return {
        "schema_version": 1,
        "phase": "verify-empty",
        "source_revision": SOURCE_REVISION,
        "nodes": 0,
        "edges": 0,
        "model_calls": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase",
        choices=("establish", "verify-purge", "verify-empty"),
        required=True,
    )
    parser.add_argument("--expected-json")
    args = parser.parse_args()
    if args.phase == "establish":
        result = asyncio.run(_establish())
    elif args.phase == "verify-purge":
        if not args.expected_json:
            raise SystemExit("--expected-json is required")
        result = asyncio.run(_verify_and_purge(json.loads(args.expected_json)))
    else:
        result = asyncio.run(_verify_empty())
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
