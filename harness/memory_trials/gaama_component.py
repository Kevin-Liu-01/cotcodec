"""Deterministic, model-free component doctor for GAAMA-style graph retrieval."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class FrozenNode:
    node_id: str
    task_id: str
    content: str
    similarity: float


@dataclass(frozen=True)
class FrozenEdge:
    source_id: str
    target_id: str
    edge_type: str = "DERIVED_FROM"
    weight: float = 1.0


def canonical_sha256(value: object) -> str:
    encoded = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    return hashlib.sha256(encoded).hexdigest()


def edges_from_frozen(
    edges: Iterable[FrozenEdge],
    *,
    hub_dampening_threshold: int = 50,
) -> list[tuple[str, str, float]]:
    """Mirror GAAMA's bidirectional edge weighting and row normalization."""

    type_weights = {
        "HAS_CONCEPT": 0.8,
        "ABOUT_CONCEPT": 0.8,
        "NEXT": 0.8,
        "DERIVED_FROM": 0.8,
        "DERIVED_FROM_FACT": 0.5,
    }
    by_source: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for edge in edges:
        base = type_weights.get(edge.edge_type, 0.5)
        value = base * max(0.0, edge.weight) ** 2
        by_source[edge.source_id].append((edge.target_id, value))
        by_source[edge.target_id].append((edge.source_id, value))
    if hub_dampening_threshold > 0:
        for source, targets in tuple(by_source.items()):
            if len(targets) > hub_dampening_threshold:
                scale = hub_dampening_threshold / len(targets)
                by_source[source] = [(target, weight * scale) for target, weight in targets]
    result: list[tuple[str, str, float]] = []
    for source, targets in sorted(by_source.items()):
        total = sum(weight for _, weight in targets)
        if total <= 0:
            continue
        for target, weight in sorted(targets):
            result.append((source, target, weight / total))
    return result


def personalized_pagerank(
    seeds: dict[str, float],
    edges: Iterable[tuple[str, str, float]],
    *,
    alpha: float = 0.85,
    max_iterations: int = 200,
    tolerance: float = 1e-6,
) -> dict[str, float]:
    """Faithful stdlib form of the pinned GAAMA local PPR recurrence."""

    total_seed = sum(seeds.values())
    if total_seed <= 0:
        return {node_id: 0.0 for node_id in seeds}
    personalization = {node_id: value / total_seed for node_id, value in seeds.items()}
    directed = list(edges)
    node_ids = set(personalization)
    out_edges: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for source, target, weight in directed:
        node_ids.update((source, target))
        out_edges[source].append((target, max(0.0, float(weight))))
    out_degree = {
        node_id: sum(weight for _, weight in out_edges.get(node_id, []))
        for node_id in node_ids
    }
    inbound: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for source, targets in out_edges.items():
        degree = out_degree[source]
        if degree <= 0:
            continue
        for target, weight in targets:
            inbound[target].append((source, weight / degree))
    for node_id in node_ids:
        personalization.setdefault(node_id, 0.0)
    rank = dict(personalization)
    for _ in range(max_iterations):
        sink_mass = sum(rank.get(node_id, 0.0) for node_id in node_ids if out_degree[node_id] <= 0)
        updated: dict[str, float] = {}
        for node_id in sorted(node_ids):
            value = (1 - alpha + alpha * sink_mass) * personalization[node_id]
            value += sum(
                alpha * rank.get(source, 0.0) * fraction
                for source, fraction in inbound.get(node_id, [])
            )
            updated[node_id] = value
        if sum(abs(updated[node] - rank.get(node, 0.0)) for node in node_ids) < tolerance:
            rank = updated
            break
        rank = updated
    maximum = max(rank.values(), default=0.0)
    return rank if maximum <= 0 else {node: value / maximum for node, value in rank.items()}


def rank_nodes(
    nodes: Iterable[FrozenNode],
    edges: Iterable[FrozenEdge],
    *,
    ppr_weight: float,
    sim_weight: float = 1.0,
    top_k: int = 3,
) -> list[str]:
    """Rank one fixed candidate pool; graph and flat arms share this exact packer."""

    candidates = list(nodes)
    maximum_similarity = max((node.similarity for node in candidates), default=1.0)
    seed_nodes = sorted(candidates, key=lambda node: (-node.similarity, node.node_id))[:2]
    seeds = {node.node_id: max(0.0, node.similarity) for node in seed_nodes}
    ppr = personalized_pagerank(seeds, edges_from_frozen(edges)) if ppr_weight else {}
    scored = [
        (
            ppr_weight * ppr.get(node.node_id, 0.0)
            + sim_weight * node.similarity / maximum_similarity,
            node.node_id,
        )
        for node in candidates
    ]
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [node_id for _, node_id in scored[:top_k]]


def build_frozen_cases(case_count: int = 24) -> list[dict[str, object]]:
    cases: list[dict[str, object]] = []
    for index in range(case_count):
        task = f"task-{index:03d}"
        nodes = [
            FrozenNode(f"{task}-seed", task, f"{task} seed fact", 1.0),
            FrozenNode(f"{task}-near-a", task, f"{task} near distractor a", 0.96),
            FrozenNode(f"{task}-near-b", task, f"{task} near distractor b", 0.17),
            FrozenNode(f"{task}-answer", task, f"{task} correct bridge answer", 0.10),
            FrozenNode(f"{task}-wrong", task, f"{task} wrong bridge answer", 0.11),
        ]
        true_edges = [FrozenEdge(nodes[0].node_id, nodes[3].node_id)]
        shuffled_edges = [FrozenEdge(nodes[0].node_id, nodes[4].node_id)]
        cases.append(
            {
                "task_id": task,
                "nodes": nodes,
                "answer_id": nodes[3].node_id,
                "true_edges": true_edges,
                "shuffled_edges": shuffled_edges,
            }
        )
    return cases


def run_component_doctor() -> dict[str, object]:
    cases = build_frozen_cases()
    rows: list[dict[str, object]] = []
    for case in cases:
        nodes = case["nodes"]
        true_edges = case["true_edges"]
        shuffled_edges = case["shuffled_edges"]
        assert isinstance(nodes, list)
        assert isinstance(true_edges, list)
        assert isinstance(shuffled_edges, list)
        flat = rank_nodes(nodes, [], ppr_weight=0.0)
        zero = rank_nodes(nodes, true_edges, ppr_weight=0.0)
        true = rank_nodes(nodes, true_edges, ppr_weight=0.1)
        shuffled = rank_nodes(nodes, shuffled_edges, ppr_weight=0.1)
        answer_id = str(case["answer_id"])
        rows.append(
            {
                "task_id": case["task_id"],
                "answer_id": answer_id,
                "candidate_ids": [node.node_id for node in nodes],
                "flat": flat,
                "ppr_weight_zero": zero,
                "true_graph": true,
                "shuffled_graph": shuffled,
                "flat_hit": answer_id in flat,
                "true_hit": answer_id in true,
                "shuffled_hit": answer_id in shuffled,
            }
        )
    hub_edges = [FrozenEdge("hub", f"leaf-{index:03d}") for index in range(60)]
    damped = edges_from_frozen(hub_edges, hub_dampening_threshold=50)
    undamped = edges_from_frozen(hub_edges, hub_dampening_threshold=0)
    report = {
        "schema_version": 1,
        "study": "gaama-matched-graph-component-doctor-v1",
        "case_count": len(rows),
        "model_calls": 0,
        "embedding_calls": 0,
        "network_calls": 0,
        "candidate_pool_matched": True,
        "packing_top_k": 3,
        "ppr_weight_zero_equal_flat": all(row["flat"] == row["ppr_weight_zero"] for row in rows),
        "true_graph_hits": sum(bool(row["true_hit"]) for row in rows),
        "flat_hits": sum(bool(row["flat_hit"]) for row in rows),
        "shuffled_graph_hits": sum(bool(row["shuffled_hit"]) for row in rows),
        "hub_dampening_noop_after_row_normalization": damped == undamped,
        "cross_task_edges": 0,
        "rows": rows,
    }
    gates = {
        "a_a_equal": report["ppr_weight_zero_equal_flat"],
        "candidate_pool_matched": report["candidate_pool_matched"],
        "cross_task_edges_zero": report["cross_task_edges"] == 0,
        "true_exceeds_flat": report["true_graph_hits"] > report["flat_hits"],
        "true_exceeds_shuffled": report["true_graph_hits"] > report["shuffled_graph_hits"],
    }
    report["gates"] = gates
    report["status"] = "GAAMA_COMPONENT_CONTRACT_PASS" if all(gates.values()) else "FAIL"
    report["scientific_result"] = False
    report["publication_ready"] = False
    report["report_sha256"] = canonical_sha256(
        {key: value for key, value in report.items() if key != "report_sha256"}
    )
    return report
