"""Natural held-out same-node graph retrieval falsifier for GAAMA-style PPR.

The study deliberately avoids answer generation and generated semantic nodes.
It asks a narrower question: when the stored dialogue nodes and their lexical
scores are fixed, does a label-free conversation graph improve retrieval of
LoCoMo's annotated evidence turns over a flat BM25 ranking?
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.memory_trials.gaama_component import (
    FrozenEdge,
    edges_from_frozen,
    personalized_pagerank,
)

TOKEN_RE = re.compile(r"[a-z0-9]+")
SESSION_RE = re.compile(r"^session_(\d+)$")
EVIDENCE_RE = re.compile(r"^D(\d+):(\d+)$")

DEV_SAMPLE_IDS = ("conv-26", "conv-30", "conv-41")
TEST_SAMPLE_IDS = (
    "conv-42",
    "conv-43",
    "conv-44",
    "conv-47",
    "conv-48",
    "conv-49",
    "conv-50",
)
PPR_WEIGHTS = (0.0, 0.05, 0.1, 0.25, 0.5, 1.0)
SHUFFLE_SEEDS = (42, 43, 44)
PRIMARY_K = 10
BM25_K1 = 1.2
BM25_B = 0.75
PPR_ALPHA = 0.6
BOOTSTRAP_SEED = 20260814
BOOTSTRAP_DRAWS = 10_000


@dataclass(frozen=True)
class DialogueNode:
    node_id: str
    sample_id: str
    session_id: str
    session_date: str
    speaker: str
    text: str

    @property
    def indexed_text(self) -> str:
        return f"{self.session_date} {self.speaker} {self.text}".strip()


@dataclass(frozen=True)
class NaturalQuestion:
    question_id: str
    sample_id: str
    category: int
    question: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class SampleGraph:
    sample_id: str
    nodes: tuple[DialogueNode, ...]
    questions: tuple[NaturalQuestion, ...]
    true_edges: tuple[FrozenEdge, ...]
    shuffled_edges: dict[int, tuple[FrozenEdge, ...]]


def canonical_sha256(value: object) -> str:
    encoded = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    return hashlib.sha256(encoded).hexdigest()


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(TOKEN_RE.findall(text.lower()))


def _session_sort_key(name: str) -> int:
    match = SESSION_RE.fullmatch(name)
    if match is None:
        raise ValueError(f"invalid LoCoMo session key: {name}")
    return int(match.group(1))


def _evidence_node_id(sample_id: str, evidence_id: str) -> str | None:
    match = EVIDENCE_RE.fullmatch(evidence_id)
    if match is None:
        return None
    return f"{sample_id}:D{int(match.group(1))}:{int(match.group(2))}"


def _graph_edges(
    nodes: tuple[DialogueNode, ...],
    *,
    permutation_seed: int | None,
) -> tuple[FrozenEdge, ...]:
    """Create typed session-membership and adjacency edges without labels."""

    by_session: dict[str, list[DialogueNode]] = defaultdict(list)
    for node in nodes:
        by_session[node.session_id].append(node)
    edges: list[FrozenEdge] = []
    for session_id in sorted(by_session, key=_session_sort_key):
        session_node_id = f"{nodes[0].sample_id}:{session_id}:session"
        ordered = by_session[session_id]
        node_ids = [node.node_id for node in ordered]
        for node_id in node_ids:
            edges.append(FrozenEdge(node_id, session_node_id, "HAS_CONCEPT"))
        for left, right in zip(node_ids, node_ids[1:], strict=False):
            edges.append(FrozenEdge(left, right, "NEXT"))
    frozen = tuple(edges)
    if permutation_seed is None:
        return frozen
    return _degree_preserving_shuffle(frozen, permutation_seed)


def _degree_preserving_shuffle(
    edges: tuple[FrozenEdge, ...], seed: int
) -> tuple[FrozenEdge, ...]:
    """Randomize topology with typed directed double-edge swaps."""

    shuffled = list(edges)
    generator = random.Random(seed)
    for edge_type in ("HAS_CONCEPT", "NEXT"):
        indices = [
            index for index, edge in enumerate(shuffled) if edge.edge_type == edge_type
        ]
        pairs = {
            (shuffled[index].source_id, shuffled[index].target_id) for index in indices
        }
        for _ in range(max(100, 40 * len(indices))):
            left_index, right_index = generator.sample(indices, 2)
            left = shuffled[left_index]
            right = shuffled[right_index]
            old_pairs = {
                (left.source_id, left.target_id),
                (right.source_id, right.target_id),
            }
            new_pairs = {
                (left.source_id, right.target_id),
                (right.source_id, left.target_id),
            }
            if (
                len(old_pairs) != 2
                or len(new_pairs) != 2
                or any(source == target for source, target in new_pairs)
                or any(pair in pairs - old_pairs for pair in new_pairs)
            ):
                continue
            pairs.difference_update(old_pairs)
            pairs.update(new_pairs)
            shuffled[left_index] = FrozenEdge(
                left.source_id,
                right.target_id,
                edge_type,
                left.weight,
            )
            shuffled[right_index] = FrozenEdge(
                right.source_id,
                left.target_id,
                edge_type,
                right.weight,
            )
    if set(shuffled) == set(edges):
        raise ValueError("degree-preserving graph shuffle made no change")
    return tuple(shuffled)


def load_locomo_graphs(path: Path) -> tuple[SampleGraph, ...]:
    """Load the pinned LoCoMo-10 artifact and reject malformed evidence."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("LoCoMo artifact must be a list")
    graphs: list[SampleGraph] = []
    expected_samples = set(DEV_SAMPLE_IDS + TEST_SAMPLE_IDS)
    for row in payload:
        if not isinstance(row, dict) or row.get("sample_id") not in expected_samples:
            raise ValueError("LoCoMo sample identity drifted")
        sample_id = str(row["sample_id"])
        conversation = row.get("conversation")
        if not isinstance(conversation, dict):
            raise ValueError(f"{sample_id}: conversation is missing")
        session_names = sorted(
            (name for name in conversation if SESSION_RE.fullmatch(name)),
            key=_session_sort_key,
        )
        nodes: list[DialogueNode] = []
        for session_name in session_names:
            turns = conversation.get(session_name)
            date_value = conversation.get(f"{session_name}_date_time", "")
            if not isinstance(turns, list) or not isinstance(date_value, str):
                raise ValueError(f"{sample_id}: malformed {session_name}")
            for turn in turns:
                if not isinstance(turn, dict):
                    raise ValueError(f"{sample_id}: malformed dialogue turn")
                evidence_id = str(turn.get("dia_id", ""))
                node_id = _evidence_node_id(sample_id, evidence_id)
                if node_id is None:
                    raise ValueError(f"{sample_id}: invalid dialogue id {evidence_id!r}")
                nodes.append(
                    DialogueNode(
                        node_id=node_id,
                        sample_id=sample_id,
                        session_id=session_name,
                        session_date=date_value,
                        speaker=str(turn.get("speaker", "")),
                        text=str(turn.get("text", "")),
                    )
                )
        node_ids = {node.node_id for node in nodes}
        questions: list[NaturalQuestion] = []
        for index, qa in enumerate(row.get("qa", [])):
            if not isinstance(qa, dict) or qa.get("category") not in {1, 2, 3, 4}:
                continue
            raw_evidence = qa.get("evidence")
            if not isinstance(raw_evidence, list) or not raw_evidence:
                continue
            evidence_ids = tuple(
                node_id
                for value in raw_evidence
                if (node_id := _evidence_node_id(sample_id, str(value))) is not None
                and node_id in node_ids
            )
            if len(evidence_ids) != len(raw_evidence):
                continue
            questions.append(
                NaturalQuestion(
                    question_id=f"{sample_id}:q{index:04d}",
                    sample_id=sample_id,
                    category=int(qa["category"]),
                    question=str(qa.get("question", "")),
                    evidence_ids=evidence_ids,
                )
            )
        frozen_nodes = tuple(nodes)
        graphs.append(
            SampleGraph(
                sample_id=sample_id,
                nodes=frozen_nodes,
                questions=tuple(questions),
                true_edges=_graph_edges(frozen_nodes, permutation_seed=None),
                shuffled_edges={
                    seed: _graph_edges(frozen_nodes, permutation_seed=seed)
                    for seed in SHUFFLE_SEEDS
                },
            )
        )
    if {graph.sample_id for graph in graphs} != expected_samples:
        raise ValueError("LoCoMo sample roster drifted")
    return tuple(sorted(graphs, key=lambda graph: graph.sample_id))


class BM25Index:
    """Small immutable BM25 index shared by every graph arm."""

    def __init__(self, nodes: tuple[DialogueNode, ...]) -> None:
        self.node_ids = tuple(node.node_id for node in nodes)
        self.documents = {node.node_id: _tokens(node.indexed_text) for node in nodes}
        self.lengths = {node_id: len(tokens) for node_id, tokens in self.documents.items()}
        self.average_length = sum(self.lengths.values()) / max(1, len(self.lengths))
        frequencies: Counter[str] = Counter()
        for tokens in self.documents.values():
            frequencies.update(set(tokens))
        count = len(self.documents)
        self.idf = {
            token: math.log(1 + (count - frequency + 0.5) / (frequency + 0.5))
            for token, frequency in frequencies.items()
        }

    def scores(self, query: str) -> dict[str, float]:
        query_terms = Counter(_tokens(query))
        scores: dict[str, float] = {}
        for node_id, tokens in self.documents.items():
            term_counts = Counter(tokens)
            length_norm = BM25_K1 * (
                1 - BM25_B + BM25_B * self.lengths[node_id] / self.average_length
            )
            score = 0.0
            for term, query_count in query_terms.items():
                frequency = term_counts.get(term, 0)
                if frequency:
                    score += (
                        self.idf.get(term, 0.0)
                        * frequency
                        * (BM25_K1 + 1)
                        / (frequency + length_norm)
                        * query_count
                    )
            scores[node_id] = score
        return scores


def _rank(
    index: BM25Index,
    query: str,
    edges: tuple[FrozenEdge, ...],
    *,
    ppr_weight: float,
) -> tuple[str, ...]:
    lexical = index.scores(query)
    maximum_lexical = max(lexical.values(), default=0.0)
    lexical_norm = {
        node_id: score / maximum_lexical if maximum_lexical > 0 else 0.0
        for node_id, score in lexical.items()
    }
    if ppr_weight == 0:
        ppr: dict[str, float] = {}
    else:
        seeds = {
            node_id: score
            for node_id, score in sorted(
                lexical.items(), key=lambda item: (-item[1], item[0])
            )[:40]
            if score > 0
        }
        ppr = personalized_pagerank(
            seeds,
            edges_from_frozen(edges),
            alpha=PPR_ALPHA,
        )
    scored = [
        (
            lexical_norm.get(node_id, 0.0) + ppr_weight * ppr.get(node_id, 0.0),
            node_id,
        )
        for node_id in index.node_ids
    ]
    scored.sort(key=lambda item: (-item[0], item[1]))
    return tuple(node_id for _, node_id in scored)


def _question_metrics(ranking: tuple[str, ...], evidence: tuple[str, ...]) -> dict[str, float]:
    evidence_set = set(evidence)
    return {
        "any_at_5": float(bool(evidence_set & set(ranking[:5]))),
        "all_at_5": float(evidence_set <= set(ranking[:5])),
        "any_at_10": float(bool(evidence_set & set(ranking[:10]))),
        "all_at_10": float(evidence_set <= set(ranking[:10])),
        "any_at_20": float(bool(evidence_set & set(ranking[:20]))),
        "all_at_20": float(evidence_set <= set(ranking[:20])),
    }


def _evaluate(
    graphs: tuple[SampleGraph, ...],
    *,
    ppr_weight: float,
    graph_kind: str,
    shuffle_seed: int | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for graph in graphs:
        index = BM25Index(graph.nodes)
        if graph_kind == "flat":
            edges: tuple[FrozenEdge, ...] = ()
        elif graph_kind == "true":
            edges = graph.true_edges
        elif graph_kind == "shuffled" and shuffle_seed in graph.shuffled_edges:
            edges = graph.shuffled_edges[int(shuffle_seed)]
        else:
            raise ValueError("invalid natural graph arm")
        for question in graph.questions:
            ranking = _rank(index, question.question, edges, ppr_weight=ppr_weight)
            rows.append(
                {
                    "question_id": question.question_id,
                    "sample_id": question.sample_id,
                    "category": question.category,
                    "metrics": _question_metrics(ranking, question.evidence_ids),
                    "top_20": list(ranking[:20]),
                    "evidence_ids": list(question.evidence_ids),
                }
            )
    return rows


def _mean_metric(rows: list[dict[str, Any]], metric: str) -> float:
    return sum(float(row["metrics"][metric]) for row in rows) / max(1, len(rows))


def _paired_rows(
    left: list[dict[str, Any]], right: list[dict[str, Any]], metric: str
) -> dict[str, list[float]]:
    right_by_id = {row["question_id"]: row for row in right}
    paired: dict[str, list[float]] = defaultdict(list)
    if set(right_by_id) != {row["question_id"] for row in left}:
        raise ValueError("natural graph arms have different question rosters")
    for row in left:
        paired[row["sample_id"]].append(
            float(row["metrics"][metric])
            - float(right_by_id[row["question_id"]]["metrics"][metric])
        )
    return dict(paired)


def _paired_mean_controls(
    treated: list[dict[str, Any]],
    controls: tuple[list[dict[str, Any]], ...],
    metric: str,
) -> dict[str, list[float]]:
    control_maps = [
        {row["question_id"]: row for row in control} for control in controls
    ]
    treated_ids = {row["question_id"] for row in treated}
    if not controls or any(set(control) != treated_ids for control in control_maps):
        raise ValueError("natural graph controls have different question rosters")
    paired: dict[str, list[float]] = defaultdict(list)
    for row in treated:
        question_id = row["question_id"]
        control_mean = sum(
            float(control[question_id]["metrics"][metric]) for control in control_maps
        ) / len(control_maps)
        paired[row["sample_id"]].append(
            float(row["metrics"][metric]) - control_mean
        )
    return dict(paired)


def _edge_degree_signature(edges: tuple[FrozenEdge, ...]) -> tuple[object, ...]:
    typed_degree: Counter[tuple[str, str, str]] = Counter()
    for edge in edges:
        typed_degree[("out", edge.edge_type, edge.source_id)] += 1
        typed_degree[("in", edge.edge_type, edge.target_id)] += 1
    return (
        len(edges),
        tuple(sorted((*identity, count) for identity, count in typed_degree.items())),
    )


def _graph_structure_matches(graph: SampleGraph) -> bool:
    node_ids = {node.node_id for node in graph.nodes}
    session_ids = {
        f"{graph.sample_id}:{node.session_id}:session" for node in graph.nodes
    }
    allowed = node_ids | session_ids
    true_edges = set(graph.true_edges)
    true_signature = _edge_degree_signature(graph.true_edges)
    if not graph.true_edges or any(
        edge.source_id not in allowed or edge.target_id not in allowed
        for edge in graph.true_edges
    ):
        return False
    for seed in SHUFFLE_SEEDS:
        shuffled = graph.shuffled_edges.get(seed, ())
        if (
            _edge_degree_signature(shuffled) != true_signature
            or set(shuffled) == true_edges
            or any(
                edge.source_id not in allowed or edge.target_id not in allowed
                for edge in shuffled
            )
        ):
            return False
    return True


def _clustered_interval(paired: dict[str, list[float]]) -> tuple[float, float]:
    groups = sorted(paired)
    group_means = {
        group: sum(paired[group]) / len(paired[group]) for group in groups
    }
    generator = random.Random(BOOTSTRAP_SEED)
    values: list[float] = []
    for _ in range(BOOTSTRAP_DRAWS):
        sampled = [generator.choice(groups) for _ in groups]
        values.append(sum(group_means[group] for group in sampled) / len(sampled))
    values.sort()
    return values[int(0.025 * len(values))], values[int(0.975 * len(values)) - 1]


def _cluster_mean(paired: dict[str, list[float]]) -> float:
    group_means = [sum(values) / len(values) for values in paired.values()]
    return sum(group_means) / len(group_means)


def _sign_randomization_p(paired: dict[str, list[float]]) -> float:
    group_means = [sum(values) / len(values) for _, values in sorted(paired.items())]
    observed = sum(group_means) / len(group_means)
    exceed = 0
    total = 1 << len(group_means)
    for mask in range(total):
        value = sum(
            score if mask & (1 << index) else -score
            for index, score in enumerate(group_means)
        ) / len(group_means)
        if value >= observed - 1e-15:
            exceed += 1
    return exceed / total


def _arm_summary(rows: list[dict[str, Any]]) -> dict[str, float | int]:
    return {
        "questions": len(rows),
        **{
            metric: _mean_metric(rows, metric)
            for metric in (
                "any_at_5",
                "all_at_5",
                "any_at_10",
                "all_at_10",
                "any_at_20",
                "all_at_20",
            )
        },
    }


def run_natural_holdout(dataset_path: Path) -> dict[str, Any]:
    """Run the complete preregistered dev-selection and sealed-test study."""

    graphs = load_locomo_graphs(dataset_path)
    dev = tuple(graph for graph in graphs if graph.sample_id in DEV_SAMPLE_IDS)
    test = tuple(graph for graph in graphs if graph.sample_id in TEST_SAMPLE_IDS)
    dev_scores: dict[str, float] = {}
    dev_rows: dict[str, list[dict[str, Any]]] = {}
    for weight in PPR_WEIGHTS:
        rows = _evaluate(dev, ppr_weight=weight, graph_kind="true")
        dev_rows[str(weight)] = rows
        dev_scores[str(weight)] = _mean_metric(rows, "all_at_10")
    selected_weight = min(
        PPR_WEIGHTS,
        key=lambda weight: (-dev_scores[str(weight)], weight),
    )

    flat = _evaluate(test, ppr_weight=0.0, graph_kind="flat")
    zero = _evaluate(test, ppr_weight=0.0, graph_kind="true")
    true = _evaluate(test, ppr_weight=selected_weight, graph_kind="true")
    shuffled = {
        seed: _evaluate(
            test,
            ppr_weight=selected_weight,
            graph_kind="shuffled",
            shuffle_seed=seed,
        )
        for seed in SHUFFLE_SEEDS
    }
    paired = _paired_rows(true, flat, "all_at_10")
    interval = _clustered_interval(paired)
    true_score = _mean_metric(true, "all_at_10")
    flat_score = _mean_metric(flat, "all_at_10")
    shuffled_scores = {
        str(seed): _mean_metric(rows, "all_at_10") for seed, rows in shuffled.items()
    }
    mean_shuffled = sum(shuffled_scores.values()) / len(shuffled_scores)
    shuffled_paired = _paired_mean_controls(
        true,
        tuple(shuffled[seed] for seed in SHUFFLE_SEEDS),
        "all_at_10",
    )
    shuffled_interval = _clustered_interval(shuffled_paired)
    shuffled_p = _sign_randomization_p(shuffled_paired)
    true_minus_flat = _cluster_mean(paired)
    true_minus_mean_shuffled = _cluster_mean(shuffled_paired)
    graph_gates = {
        "selected_nonzero_weight": selected_weight > 0,
        "true_minus_flat_at_least_one_point": true_minus_flat >= 0.01,
        "clustered_ci_excludes_zero": interval[0] > 0,
        "true_minus_mean_shuffled_at_least_one_point": (
            true_minus_mean_shuffled >= 0.01
        ),
        "one_sided_sign_randomization_below_0_05": _sign_randomization_p(paired) < 0.05,
        "shuffled_clustered_ci_excludes_zero": shuffled_interval[0] > 0,
        "shuffled_one_sided_sign_randomization_below_0_05": shuffled_p < 0.05,
    }
    integrity_gates = {
        "zero_weight_lexical_a_a_exact": flat == zero,
        "graph_candidate_and_degree_contract": all(
            _graph_structure_matches(graph) for graph in graphs
        ),
        "dev_test_disjoint": not set(DEV_SAMPLE_IDS) & set(TEST_SAMPLE_IDS),
        "test_roster_exact": {graph.sample_id for graph in test} == set(TEST_SAMPLE_IDS),
        "model_calls_zero": True,
        "embedding_calls_zero": True,
        "network_calls_zero": True,
    }
    graph_pass = all(graph_gates.values())
    report: dict[str, Any] = {
        "schema_version": 1,
        "study": "gaama-natural-heldout-graph-retrieval-v1",
        "status": (
            "GAAMA_NATURAL_GRAPH_PASS" if graph_pass else "GAAMA_NATURAL_GRAPH_KILLED"
        ),
        "scientific_result": False,
        "publication_ready": False,
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "dev_sample_ids": list(DEV_SAMPLE_IDS),
        "test_sample_ids": list(TEST_SAMPLE_IDS),
        "dev_questions": sum(len(graph.questions) for graph in dev),
        "test_questions": len(flat),
        "dialogue_nodes": sum(len(graph.nodes) for graph in graphs),
        "primary_metric": "evidence_recall_all_at_10",
        "dev_weight_scores": dev_scores,
        "selected_ppr_weight": selected_weight,
        "arm_summaries": {
            "flat": _arm_summary(flat),
            "ppr_weight_zero": _arm_summary(zero),
            "true_graph": _arm_summary(true),
            **{
                f"shuffled_graph_seed_{seed}": _arm_summary(rows)
                for seed, rows in shuffled.items()
            },
        },
        "primary_comparison": {
            "true_minus_flat": true_minus_flat,
            "clustered_bootstrap_95_ci": list(interval),
            "conversation_sign_randomization_p_one_sided": _sign_randomization_p(paired),
            "true_minus_mean_shuffled": true_minus_mean_shuffled,
            "true_minus_mean_shuffled_clustered_bootstrap_95_ci": list(
                shuffled_interval
            ),
            "true_minus_mean_shuffled_sign_randomization_p_one_sided": shuffled_p,
            "pooled_question_true_minus_flat": true_score - flat_score,
            "pooled_question_true_minus_mean_shuffled": true_score - mean_shuffled,
        },
        "integrity_gates": integrity_gates,
        "graph_gates": graph_gates,
        "model_calls": 0,
        "embedding_calls": 0,
        "network_calls": 0,
        "h100_admission": "eligible-for-separate-design-review" if graph_pass else "blocked",
        "dev_rows": dev_rows,
        "rows": {
            "flat": flat,
            "ppr_weight_zero": zero,
            "true_graph": true,
            **{f"shuffled_graph_seed_{seed}": rows for seed, rows in shuffled.items()},
        },
    }
    if not all(integrity_gates.values()):
        report["status"] = "FAIL"
        report["h100_admission"] = "blocked"
    report["report_sha256"] = canonical_sha256(
        {key: value for key, value in report.items() if key != "report_sha256"}
    )
    return report
