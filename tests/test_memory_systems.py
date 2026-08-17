from __future__ import annotations

import json
import math

import pytest
from pydantic import ValidationError

from harness.memory_trials import (
    BM25MemorySystem,
    EventKind,
    FullPrefixCeilingSystem,
    GeneratedMemoryTaskSource,
    LRUMemorySystem,
    MemoryBankDecayMemorySystem,
    MemoryBudget,
    MemoryEvent,
    MemoryOracle,
    MemoryStratum,
    MemorySystemEvent,
    MemorySystemRequest,
    NoMemorySystem,
    ProfileExpansionMemorySystem,
    RawLogRRFMemorySystem,
    RecencyMemorySystem,
    ReferenceMemorySystem,
    TemporalGraphMemorySystem,
    materialize_prefix_records,
    run_memory_system,
)
from harness.memory_trials.schema import seal_task


def test_generated_supersession_invalidates_the_stale_record() -> None:
    task = GeneratedMemoryTaskSource(seed=7, episode_count=5).load("memory-000004")
    assert any(event.kind is EventKind.UPDATE for event in task.events)
    records = materialize_prefix_records(task)
    stale = next(record for record in records if record.record_id.endswith("history-stale"))
    baseline = next(record for record in records if record.record_id.endswith("baseline"))
    assert stale.valid is False
    assert baseline.valid is True


def test_generated_deletion_recreates_only_after_invalidating_stale_state() -> None:
    task = GeneratedMemoryTaskSource(seed=7, episode_count=9).load("memory-000008")
    assert any(event.kind is EventKind.DELETE for event in task.events)
    records = materialize_prefix_records(task)
    stale = next(record for record in records if record.record_id.endswith("history-stale"))
    baseline = next(record for record in records if record.record_id.endswith("baseline"))
    assert stale.valid is False
    assert baseline.valid is True


def test_native_request_cannot_contain_oracle_candidate_or_suffix() -> None:
    task = GeneratedMemoryTaskSource(seed=7, episode_count=1).load("memory-000000")
    record = materialize_prefix_records(task)[0]
    payload = {
        "request_id": "request-1",
        "session_scope": task.session_id,
        "events": [
            {
                "source_event_id": record.record_id,
                "step": record.written_step,
                "kind": "write",
                "entity_id": record.entity_id,
                "key": record.key,
                "value": record.value,
                "untrusted": record.untrusted,
                "candidate": True,
            }
        ],
        "query": task.query,
        "budget": task.budget,
        "oracle": task.oracle.model_dump(mode="json"),
        "suffix_variant": task.suffix_variant_id,
    }
    with pytest.raises(ValidationError):
        MemorySystemRequest.model_validate(payload)


def test_native_request_normalizes_generator_only_distractor_labels() -> None:
    task = GeneratedMemoryTaskSource(seed=7, episode_count=1).load("memory-000000")

    class RequestSpy(ReferenceMemorySystem):
        seen: MemorySystemRequest | None = None

        def select(self, request: MemorySystemRequest):
            self.seen = request
            return super().select(request)

    system = RequestSpy()
    run_memory_system(
        system,
        task,
        visibility="serve",
        treatment_mode="storage_and_service",
    )
    assert system.seen is not None
    assert {event.kind for event in system.seen.events} <= {
        "write",
        "update",
        "delete",
        "access",
        "observe",
    }
    event_json = system.seen.model_dump_json()
    assert "distractor" not in event_json
    assert "candidate" not in event_json
    assert "wrong-" not in event_json
    assert "noise-" not in event_json
    assert "source_quality" not in event_json
    assert "contradiction_count" not in event_json
    assert "stratum" not in event_json
    assert "residency" not in event_json


def test_serve_only_filters_candidate_after_identical_system_selection() -> None:
    task = GeneratedMemoryTaskSource(seed=7, episode_count=2).load("memory-000001")
    system = ReferenceMemorySystem()
    served = run_memory_system(
        system,
        task,
        visibility="serve",
        treatment_mode="serve_only",
    )
    held_out = run_memory_system(
        system,
        task,
        visibility="holdout",
        treatment_mode="serve_only",
    )
    assert served.request_sha256 == held_out.request_sha256
    assert served.raw_selection_sha256 == held_out.raw_selection_sha256
    assert served.candidate_available_to_system is True
    assert held_out.candidate_available_to_system is True
    assert served.candidate_served_to_actor is True
    assert held_out.candidate_served_to_actor is False
    assert all(
        "candidate" not in source_id
        for item in held_out.evidence
        for source_id in item.source_record_ids
    )


def test_storage_and_service_is_a_distinct_end_to_end_estimand() -> None:
    task = GeneratedMemoryTaskSource(seed=7, episode_count=1).load("memory-000000")
    system = ReferenceMemorySystem()
    served = run_memory_system(
        system,
        task,
        visibility="serve",
        treatment_mode="storage_and_service",
    )
    held_out = run_memory_system(
        system,
        task,
        visibility="holdout",
        treatment_mode="storage_and_service",
    )
    assert served.request_sha256 != held_out.request_sha256
    assert served.raw_selection_sha256 != held_out.raw_selection_sha256
    assert served.candidate_available_to_system is True
    assert held_out.candidate_available_to_system is False
    assert held_out.candidate_served_to_actor is False


def test_no_memory_floor_has_no_evidence_or_memory_operations() -> None:
    task = GeneratedMemoryTaskSource(seed=7, episode_count=1).load("memory-000000")
    served = run_memory_system(
        NoMemorySystem(),
        task,
        visibility="serve",
        treatment_mode="storage_and_service",
    )
    held_out = run_memory_system(
        NoMemorySystem(),
        task,
        visibility="holdout",
        treatment_mode="storage_and_service",
    )
    assert served.evidence == held_out.evidence == ()
    assert served.candidate_served_to_actor is False
    assert held_out.candidate_served_to_actor is False
    for costs in (served.costs, held_out.costs):
        assert costs.reads == 0
        assert costs.writes == 0
        assert costs.serialized_input_bytes == 0
        assert costs.serialized_output_bytes == 2
        assert costs.injected_tokens_estimate == 0


def test_full_prefix_ceiling_preserves_every_ordered_event_without_truncation() -> None:
    budget = MemoryBudget(
        active_slots=4,
        max_archive_reads=0,
        retrieval_top_k=1,
        max_injected_tokens=65_536,
    )
    task = GeneratedMemoryTaskSource(
        seed=7,
        episode_count=1,
        budget=budget,
    ).load("memory-000000")
    system = FullPrefixCeilingSystem()
    served = run_memory_system(
        system,
        task,
        visibility="serve",
        treatment_mode="storage_and_service",
    )
    held_out = run_memory_system(
        system,
        task,
        visibility="holdout",
        treatment_mode="storage_and_service",
    )

    assert len(served.evidence) == len(held_out.evidence) == 1
    served_events = json.loads(served.evidence[0].text)
    held_out_events = json.loads(held_out.evidence[0].text)
    assert [event["step"] for event in served_events] == list(
        range(task.eligibility_step)
    )
    assert len(held_out_events) == len(served_events) - 1
    assert served.evidence[0].source_record_ids == tuple(
        event["source_event_id"] for event in served_events
    )
    assert served.candidate_served_to_actor is True
    assert held_out.candidate_served_to_actor is False
    assert served.costs.reads == held_out.costs.reads == 0
    assert served.costs.injected_tokens_estimate <= budget.max_injected_tokens


def test_full_prefix_ceiling_fails_instead_of_silently_truncating() -> None:
    task = GeneratedMemoryTaskSource(
        seed=7,
        episode_count=1,
        budget=MemoryBudget(
            active_slots=4,
            max_archive_reads=0,
            retrieval_top_k=1,
            max_injected_tokens=1,
        ),
    ).load("memory-000000")
    with pytest.raises(ValueError, match="exceeded max_injected_tokens"):
        run_memory_system(
            FullPrefixCeilingSystem(),
            task,
            visibility="serve",
            treatment_mode="storage_and_service",
        )


def test_temporal_graph_returns_attributed_path_under_shared_budget() -> None:
    task = GeneratedMemoryTaskSource(seed=7, episode_count=4).load("memory-000002")
    run = run_memory_system(
        TemporalGraphMemorySystem(max_hops=3),
        task,
        visibility="serve",
        treatment_mode="storage_and_service",
    )
    assert len(run.evidence) == 1
    path = run.evidence[0]
    assert path.kind == "path"
    assert run.candidate_served_to_actor is True
    assert len(path.source_record_ids) == 2
    assert run.costs.reads == 1
    assert run.costs.injected_tokens_estimate <= task.budget.max_injected_tokens


def test_system_receipts_and_runs_are_hash_bound() -> None:
    task = GeneratedMemoryTaskSource(seed=7, episode_count=2).load("memory-000001")
    run = run_memory_system(
        ReferenceMemorySystem(),
        task,
        visibility="serve",
        treatment_mode="serve_only",
    )
    with pytest.raises(ValidationError, match="run_sha256"):
        type(run).model_validate(
            run.model_copy(update={"candidate_served_to_actor": False}).model_dump()
        )


def test_true_lru_uses_explicit_access_and_differs_from_recency() -> None:
    events = (
        MemoryEvent(
            event_id="old-accessed",
            step=0,
            kind=EventKind.WRITE,
            entity_id="old-entity",
            key="state",
            value="alpha",
            candidate=True,
        ),
        MemoryEvent(
            event_id="new-unaccessed",
            step=1,
            kind=EventKind.WRITE,
            entity_id="new-entity",
            key="state",
            value="beta",
        ),
        MemoryEvent(
            event_id="access-old",
            step=2,
            kind=EventKind.ACCESS,
            entity_id="old-entity",
            key="state",
        ),
        MemoryEvent(
            event_id="newest-write",
            step=3,
            kind=EventKind.WRITE,
            entity_id="newest-entity",
            key="state",
            value="gamma",
        ),
        MemoryEvent(
            event_id="ready",
            step=4,
            kind=EventKind.OBSERVE,
            entity_id="system",
            key="status",
            value="ready",
        ),
        MemoryEvent(
            event_id="query",
            step=5,
            kind=EventKind.QUERY,
            entity_id="old-entity",
            key="state",
        ),
    )
    task = seal_task(
        {
            "schema_version": "1.0",
            "source_schema_version": "lru-contract-v1",
            "task_id": "lru-contract-task",
            "group_id": "lru-contract-group",
            "session_id": "lru-contract-session",
            "stratum": MemoryStratum.ACTIVE_CORE,
            "events": events,
            "candidate_id": "old-accessed",
            "write_step": 0,
            "eligibility_step": 4,
            "total_steps": len(events),
            "query": "What is the state of old-entity?",
            "oracle": MemoryOracle(
                mode="answer",
                lookup_key="state",
                expected_value="alpha",
            ),
            "budget": MemoryBudget(active_slots=2, retrieval_top_k=2),
            "suffix_variant_id": "primary",
        }
    )
    lru = run_memory_system(
        LRUMemorySystem(),
        task,
        visibility="serve",
        treatment_mode="storage_and_service",
    )
    recency = run_memory_system(
        RecencyMemorySystem(),
        task,
        visibility="serve",
        treatment_mode="storage_and_service",
    )
    lru_values = {json.loads(item.text)["value"] for item in lru.evidence}
    recency_values = {json.loads(item.text)["value"] for item in recency.evidence}
    assert lru_values == {"alpha", "gamma"}
    assert recency_values == {"beta", "gamma"}
    assert lru.costs.reads == 0


def test_bm25_control_is_deterministic_and_hash_bound() -> None:
    task = GeneratedMemoryTaskSource(seed=7, episode_count=2).load("memory-000001")
    system = BM25MemorySystem(k1=1.2, b=0.75)
    first = run_memory_system(
        system,
        task,
        visibility="serve",
        treatment_mode="storage_and_service",
    )
    repeated = run_memory_system(
        system,
        task,
        visibility="serve",
        treatment_mode="storage_and_service",
    )
    assert first == repeated
    assert first.receipt.system_id == "bm25-memory-v1"
    assert first.costs.reads == 1
    assert all(math.isfinite(item.score) for item in first.evidence)


def test_memorybank_corrected_and_precedence_arms_change_the_winner() -> None:
    events = [
        MemorySystemEvent(
            source_event_id="old",
            step=0,
            kind="write",
            entity_id="old-entity",
            key="state",
            value="alpha",
            untrusted=False,
        )
    ]
    events.extend(
        MemorySystemEvent(
            source_event_id=f"access-{step}",
            step=step,
            kind="access",
            entity_id="old-entity",
            key="state",
            value=None,
            untrusted=False,
        )
        for step in range(1, 8)
    )
    events.extend(
        MemorySystemEvent(
            source_event_id=f"wait-{step}",
            step=step,
            kind="observe",
            entity_id="clock",
            key="tick",
            value=None,
            untrusted=False,
        )
        for step in range(8, 20)
    )
    events.append(
        MemorySystemEvent(
            source_event_id="recent",
            step=20,
            kind="write",
            entity_id="distractor",
            key="noise",
            value="beta",
            untrusted=False,
        )
    )
    request = MemorySystemRequest(
        request_id="memorybank-contract",
        session_scope="memorybank-session",
        events=tuple(events),
        query="What is old-entity state alpha?",
        budget=MemoryBudget(active_slots=4, retrieval_top_k=1),
    )
    corrected = MemoryBankDecayMemorySystem().select(request)
    upstream = MemoryBankDecayMemorySystem(formula="upstream-precedence").select(
        request
    )
    no_decay = MemoryBankDecayMemorySystem(formula="no-decay").select(request)
    assert corrected.evidence[0].source_record_ids == ("old",)
    assert no_decay.evidence[0].source_record_ids == ("old",)
    assert upstream.evidence[0].source_record_ids == ("recent",)
    assert corrected == MemoryBankDecayMemorySystem().select(request)
    assert corrected.receipt.system_id == "memorybank-corrected-decay-v1"


def test_raw_log_rrf_uses_local_context_and_bounded_keyword_feedback() -> None:
    request = MemorySystemRequest(
        request_id="raw-log-contract",
        session_scope="raw-log-session",
        events=(
            MemorySystemEvent(
                source_event_id="a0",
                step=0,
                kind="write",
                entity_id="session-a",
                key="residence",
                value="Alice lives with Bob",
                untrusted=True,
            ),
            MemorySystemEvent(
                source_event_id="a1",
                step=1,
                kind="observe",
                entity_id="session-a",
                key="context",
                value="They moved after graduation",
                untrusted=True,
            ),
            MemorySystemEvent(
                source_event_id="b0",
                step=2,
                kind="write",
                entity_id="session-b",
                key="instrument",
                value="Bob plays piano",
                untrusted=True,
            ),
            MemorySystemEvent(
                source_event_id="c0",
                step=3,
                kind="write",
                entity_id="session-c",
                key="weather",
                value="The forecast is rainy",
                untrusted=True,
            ),
        ),
        query="Where does Alice live?",
        budget=MemoryBudget(
            max_archive_reads=2,
            retrieval_top_k=2,
            max_injected_tokens=256,
        ),
    )
    system = RawLogRRFMemorySystem(context_window=1, expansion_terms=1)
    first = system.select(request)
    repeated = system.select(request)
    assert first == repeated
    assert first.receipt.system_id == "raw-log-rrf-memory-v1"
    assert first.costs.reads == 2
    assert first.evidence[0].source_record_ids == ("a0", "a1")
    assert first.evidence[1].source_record_ids == ("b0",)
    assert first.costs.injected_tokens_estimate <= 256


def test_profile_expansion_crosses_entity_mentions_without_explicit_graph() -> None:
    request = MemorySystemRequest(
        request_id="profile-expansion-contract",
        session_scope="profile-expansion-session",
        events=(
            MemorySystemEvent(
                source_event_id="alice-profile",
                step=0,
                kind="write",
                entity_id="alice",
                key="relationship",
                value="Alice's roommate is Bob",
                untrusted=True,
            ),
            MemorySystemEvent(
                source_event_id="bob-profile",
                step=1,
                kind="write",
                entity_id="bob",
                key="instrument",
                value="piano",
                untrusted=True,
            ),
            MemorySystemEvent(
                source_event_id="carol-profile",
                step=2,
                kind="write",
                entity_id="carol",
                key="instrument",
                value="violin",
                untrusted=True,
            ),
        ),
        query="What instrument does Alice's roommate play?",
        budget=MemoryBudget(retrieval_top_k=2, max_injected_tokens=256),
    )
    expanded = ProfileExpansionMemorySystem(initial_profiles=1).select(request)
    explicit_graph = TemporalGraphMemorySystem(max_hops=3).select(request)
    expanded_sources = {
        source_id
        for evidence in expanded.evidence
        for source_id in evidence.source_record_ids
    }
    graph_sources = {
        source_id
        for evidence in explicit_graph.evidence
        for source_id in evidence.source_record_ids
    }
    assert expanded.receipt.system_id == "profile-expansion-memory-v1"
    assert expanded_sources == {"alice-profile", "bob-profile"}
    assert "bob-profile" not in graph_sources
    assert expanded.costs.reads == 1
    assert expanded.costs.injected_tokens_estimate <= 256
