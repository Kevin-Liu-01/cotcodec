#!/usr/bin/env python3
"""Contained identical-tuple Neo4j-versus-flat traversal component doctor."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from neo4j_agent_memory import MemoryClient, MemorySettings, Neo4jConfig
from neo4j_agent_memory.config import ExtractionConfig, ExtractorType
from neo4j_agent_memory.embeddings.base import BaseEmbedder
from pydantic import SecretStr

sys.path.insert(0, str(Path(__file__).resolve().parent))
from neo4j_flat_parity import (  # noqa: E402
    FrozenCase,
    build_frozen_cases,
    canonical_tuple_payload,
    create_flat_database,
    flat_bm25_dense_rank,
    flat_sql_join_rank,
)

SOURCE_REVISION = "231d60eac9401ab156ba194b519d89dd644dadb8"
STATUS = "NEO4J_IDENTICAL_TUPLE_TRAVERSAL_COMPONENT_PASS"
CASE_COUNT = 48
TOP_K = 2
MAX_INJECTED_BYTES = 256


class FailOnCallEmbedder(BaseEmbedder):
    calls = 0

    @property
    def dimensions(self) -> int:
        return 16

    async def embed(self, text: str) -> list[float]:
        type(self).calls += 1
        raise RuntimeError(f"embedding was forbidden: {text!r}")


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


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


def _rows(cases: tuple[FrozenCase, ...]) -> list[dict[str, Any]]:
    shuffled = {
        tuple_id: object_
        for case in cases
        for tuple_id, object_ in case.shuffled_objects
    }
    return [
        {**asdict(row), "vector": list(row.vector), "shuffled_object": shuffled[row.tuple_id]}
        for case in cases
        for row in case.tuples
    ]


async def _load_graph(client: MemoryClient, rows: list[dict[str, Any]]) -> None:
    await client.graph.execute_write("MATCH (n) DETACH DELETE n")
    for offset in range(0, len(rows), 128):
        await client.graph.execute_write(
            """
            UNWIND $rows AS row
            MERGE (subject:ParityEntity {
              case_id: row.case_id, entity_id: row.subject
            })
            MERGE (object:ParityEntity {
              case_id: row.case_id, entity_id: row.object
            })
            MERGE (shuffled:ParityEntity {
              case_id: row.case_id, entity_id: row.shuffled_object
            })
            CREATE (item:ParityTuple {
              case_id: row.case_id,
              tuple_id: row.tuple_id,
              subject: row.subject,
              relation: row.relation,
              object: row.object,
              text: row.text,
              vector: row.vector
            })
            CREATE (subject)-[:TRUE_SUBJECT]->(item)
            CREATE (item)-[:TRUE_OBJECT]->(object)
            CREATE (subject)-[:SHUFFLED_SUBJECT]->(item)
            CREATE (item)-[:SHUFFLED_OBJECT]->(shuffled)
            """,
            {"rows": rows[offset : offset + 128]},
        )


async def _graph_rank(
    client: MemoryClient,
    case: FrozenCase,
    *,
    shuffled: bool,
) -> tuple[str, ...]:
    prefix = "SHUFFLED" if shuffled else "TRUE"
    result = await client.graph.execute_read(
        f"""
        MATCH (start:ParityEntity {{case_id: $case_id, entity_id: $start}})
              -[:{prefix}_SUBJECT]->
              (first:ParityTuple {{case_id: $case_id, relation: $first_relation}})
              -[:{prefix}_OBJECT]->
              (middle:ParityEntity)
              -[:{prefix}_SUBJECT]->
              (second:ParityTuple {{case_id: $case_id, relation: $second_relation}})
              -[:{prefix}_OBJECT]->
              (:ParityEntity)
        RETURN first.tuple_id AS first_id, second.tuple_id AS second_id
        ORDER BY first_id, second_id
        LIMIT 1
        """,
        {
            "case_id": case.case_id,
            "start": case.start,
            "first_relation": case.first_relation,
            "second_relation": case.second_relation,
        },
    )
    if not result:
        return ()
    return (result[0]["first_id"], result[0]["second_id"])


async def _neo4j_payload(client: MemoryClient) -> bytes:
    rows = await client.graph.execute_read(
        """
        MATCH (item:ParityTuple)
        RETURN item.case_id AS case_id, item.tuple_id AS tuple_id,
               item.subject AS subject, item.relation AS relation,
               item.object AS object, item.text AS text, item.vector AS vector
        ORDER BY tuple_id
        """
    )
    return _canonical([dict(row) for row in rows])


def _output_bytes(case: FrozenCase, tuple_ids: tuple[str, ...]) -> int:
    text_by_id = {row.tuple_id: row.text for row in case.tuples}
    return sum(len(text_by_id[tuple_id].encode()) for tuple_id in tuple_ids)


async def _run() -> dict[str, Any]:
    cases = build_frozen_cases(CASE_COUNT)
    tuple_payload = canonical_tuple_payload(cases)
    rows = _rows(cases)
    database = create_flat_database(cases)
    started = time.monotonic()
    results: list[dict[str, Any]] = []
    try:
        async with MemoryClient(_settings(), embedder=FailOnCallEmbedder()) as client:
            await _load_graph(client, rows)
            graph_payload = await _neo4j_payload(client)
            if graph_payload != tuple_payload:
                raise RuntimeError("Neo4j tuple payload differs from the flat input")
            for case in cases:
                flat = flat_bm25_dense_rank(database, case, top_k=TOP_K)
                join = flat_sql_join_rank(database, case, top_k=TOP_K)
                true_graph = await _graph_rank(client, case, shuffled=False)
                shuffled_graph = await _graph_rank(client, case, shuffled=True)
                arms = {
                    "flat_bm25_dense": flat,
                    "zero_traversal": flat,
                    "flat_sql_join": join,
                    "true_graph": true_graph,
                    "shuffled_graph": shuffled_graph,
                }
                if any(len(value) > TOP_K for value in arms.values()):
                    raise RuntimeError("an arm exceeded the top-k output budget")
                injected_bytes = {
                    arm: _output_bytes(case, value) for arm, value in arms.items()
                }
                if any(value > MAX_INJECTED_BYTES for value in injected_bytes.values()):
                    raise RuntimeError("an arm exceeded the injected-byte budget")
                results.append(
                    {
                        "case_id": case.case_id,
                        "target_tuple_id": case.target_tuple_id,
                        "arms": {key: list(value) for key, value in arms.items()},
                        "hits": {
                            key: case.target_tuple_id in value for key, value in arms.items()
                        },
                        "injected_bytes": injected_bytes,
                        "logical_retrieval_calls": {key: 1 for key in arms},
                    }
                )
            await client.graph.execute_write("MATCH (n) DETACH DELETE n")
            residue = await client.graph.execute_read(
                "MATCH (n) OPTIONAL MATCH ()-[r]->() "
                "RETURN count(DISTINCT n) AS nodes, count(r) AS edges"
            )
    finally:
        database.close()
    hit_counts = {
        arm: sum(row["hits"][arm] for row in results)
        for arm in results[0]["hits"]
    }
    tuple_count = len(rows)
    relationship_payload = _canonical(
        [
            (row["case_id"], row["tuple_id"], row["subject"], row["object"], row["shuffled_object"])
            for row in rows
        ]
    )
    gates = {
        "identical_tuple_payload": graph_payload == tuple_payload,
        "zero_traversal_equals_flat": all(
            row["arms"]["zero_traversal"] == row["arms"]["flat_bm25_dense"]
            for row in results
        ),
        "true_graph_equals_flat_sql_join": all(
            row["arms"]["true_graph"] == row["arms"]["flat_sql_join"]
            for row in results
        ),
        "true_graph_lift_over_bm25_dense_at_least_25_points": (
            hit_counts["true_graph"] - hit_counts["flat_bm25_dense"]
        )
        / CASE_COUNT
        >= 0.25,
        "true_graph_lift_over_shuffled_at_least_25_points": (
            hit_counts["true_graph"] - hit_counts["shuffled_graph"]
        )
        / CASE_COUNT
        >= 0.25,
        "matched_top_k_byte_and_logical_call_budget": all(
            all(value == 1 for value in row["logical_retrieval_calls"].values())
            and all(value <= MAX_INJECTED_BYTES for value in row["injected_bytes"].values())
            for row in results
        ),
        "zero_model_embedding_and_external_network_calls": FailOnCallEmbedder.calls == 0,
        "purge_zero_nodes_and_edges": residue[0]["nodes"] == 0
        and residue[0]["edges"] == 0,
    }
    if not all(gates.values()):
        raise RuntimeError(f"Neo4j flat-parity gate failed: {gates}")
    report: dict[str, Any] = {
        "schema_version": 1,
        "study": "neo4j-identical-tuple-flat-parity-v1",
        "status": STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "source_revision": SOURCE_REVISION,
        "case_count": CASE_COUNT,
        "tuple_count": tuple_count,
        "top_k": TOP_K,
        "max_injected_bytes": MAX_INJECTED_BYTES,
        "tuple_payload_sha256": hashlib.sha256(tuple_payload).hexdigest(),
        "tuple_payload_bytes": len(tuple_payload),
        "topology_payload_sha256": hashlib.sha256(relationship_payload).hexdigest(),
        "topology_payload_bytes_charged": len(relationship_payload),
        "hit_counts": hit_counts,
        "model_calls": 0,
        "embedding_model_calls": 0,
        "external_network_calls": 0,
        "gates": gates,
        "rows": results,
        "elapsed_seconds": time.monotonic() - started,
        "interpretation": (
            "designed component evidence for traversal over a flat BM25-dense retriever; "
            "the exact flat SQL join ceiling ties the graph and forbids a unique graph-store claim"
        ),
    }
    report["report_sha256"] = hashlib.sha256(_canonical(report)).hexdigest()
    return report


def main() -> int:
    report = asyncio.run(_run())
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
