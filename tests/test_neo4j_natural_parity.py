from __future__ import annotations

from collections import Counter
from dataclasses import replace

from harness.memory_trials.neo4j_natural_parity import (
    LONGMEMEVAL_DATASET_REVISION,
    LONGMEMEVAL_S_SHA256,
    LONGMEMEVAL_S_SIZE,
    NaturalCase,
    NaturalSession,
    chronological_edges,
    expand_ranking,
    freeze_case_rankings,
    recall_all,
    shuffled_edges,
    stable_vector,
)
from harness.memory_trials.public_sources import (
    LONGMEMEVAL_DATASET_REVISION as PUBLIC_REVISION,
)
from harness.memory_trials.public_sources import LONGMEMEVAL_S_SHA256 as PUBLIC_SHA256
from harness.memory_trials.public_sources import LONGMEMEVAL_S_SIZE as PUBLIC_SIZE


def test_pure_contract_constants_match_the_public_source_adapter() -> None:
    assert LONGMEMEVAL_DATASET_REVISION == PUBLIC_REVISION
    assert LONGMEMEVAL_S_SHA256 == PUBLIC_SHA256
    assert LONGMEMEVAL_S_SIZE == PUBLIC_SIZE


def _session(session_id: str, position: int, text: str) -> NaturalSession:
    return NaturalSession(
        session_id=session_id,
        position=position,
        date=f"2026/01/{position + 1:02d}",
        text=text,
        vector=stable_vector(text),
    )


def _case() -> NaturalCase:
    sessions = (
        _session("s0", 0, "I started a new job at Acme."),
        _session("s1", 1, "The office is in Trenton."),
        _session("s2", 2, "My title changed to research engineer."),
        _session("s3", 3, "A completely unrelated cooking discussion."),
        _session("s4", 4, "Another unrelated travel discussion."),
    )
    return NaturalCase(
        question_id="q1",
        question_type="knowledge-update",
        question="What title did my job change to?",
        answer="research engineer",
        answer_session_ids=("s2",),
        sessions=sessions,
    )


def test_true_and_shuffled_topology_are_deterministic_and_degree_matched() -> None:
    case = _case()
    true_edges = chronological_edges(case)
    shuffled = shuffled_edges(case, 42)
    assert shuffled == shuffled_edges(case, 42)
    assert true_edges != shuffled
    assert Counter(
        value for edge in true_edges for value in edge
    ) == Counter(
        value for edge in shuffled for value in edge
    )


def test_expand_ranking_preserves_seeds_and_obeys_top_k() -> None:
    flat = ("s0", "s4", "s3", "s2", "s1")
    expanded = expand_ranking(flat, (("s0", "s1"), ("s1", "s2"), ("s2", "s3"), ("s3", "s4")))
    assert expanded == ("s0", "s4", "s3", "s1")
    assert len(expanded) == 4


def test_freeze_case_rankings_uses_identical_roster_and_labels_only_for_scoring() -> None:
    case = _case()
    rankings = freeze_case_rankings(case)
    assert set(rankings) == {
        "flat_bm25_dense",
        "true_topology",
        "shuffled_topology_seed_42",
        "shuffled_topology_seed_43",
        "shuffled_topology_seed_44",
    }
    assert all(len(value) == 4 for value in rankings.values())
    changed = replace(case, answer_session_ids=("s3",))
    assert freeze_case_rankings(changed) == rankings
    assert recall_all(changed, rankings["flat_bm25_dense"]) is not recall_all(
        case, rankings["flat_bm25_dense"]
    )
