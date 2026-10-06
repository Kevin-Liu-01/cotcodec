"""Budgeted memory-system contract with engine-owned treatment and accounting.

Native memory frameworks run behind adapters that receive this task-blind request.
They never receive an oracle, answer, suffix, treatment label, or candidate flag.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict, deque
from collections.abc import Mapping
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from harness.memory_trials.memorybank_decay import DecayCandidate, score_candidates
from harness.memory_trials.schema import (
    EventKind,
    MemoryBudget,
    MemoryRecord,
    MemoryStratum,
    MemoryTask,
    canonical_json,
    sha256_text,
)

MemoryTreatmentMode = Literal["serve_only", "storage_and_service"]
MemorySystemEventKind = Literal["write", "update", "delete", "access", "observe"]
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_TRUNCATION_MARKER = "\n[truncated to memory budget]"
_SNIPPET_BUDGET_POLICY = "ranked-utf8-prefix-with-marker-v1"
_RAW_SEARCH_STOP_TERMS = frozenset(
    {
        "access",
        "delete",
        "entity",
        "false",
        "key",
        "kind",
        "observe",
        "session",
        "state",
        "step",
        "true",
        "untrusted",
        "update",
        "value",
        "write",
    }
)


class MemorySystemEvent(BaseModel):
    """One ordered prefix event; deliberately has no candidate flag."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_event_id: str = Field(min_length=1)
    step: int = Field(ge=0)
    kind: MemorySystemEventKind
    entity_id: str = Field(min_length=1)
    key: str = Field(min_length=1)
    value: str | None = None
    untrusted: bool


class MemorySystemRecord(BaseModel):
    """Internal materialized record used by deterministic reference controls."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_record_id: str = Field(min_length=1)
    entity_id: str = Field(min_length=1)
    key: str = Field(min_length=1)
    value: str = Field(min_length=1)
    written_step: int = Field(ge=0)
    last_access_step: int = Field(ge=0)
    valid: bool
    untrusted: bool


class MemorySystemRequest(BaseModel):
    """Complete task-blind input to a memory system for one query."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.1"] = "1.1"
    request_id: str = Field(min_length=1)
    session_scope: str = Field(min_length=1)
    events: tuple[MemorySystemEvent, ...]
    query: str = Field(min_length=1)
    budget: MemoryBudget

    @model_validator(mode="after")
    def validate_events(self) -> MemorySystemRequest:
        ids = [event.source_event_id for event in self.events]
        if len(ids) != len(set(ids)):
            raise ValueError("memory-system event IDs must be unique")
        steps = [event.step for event in self.events]
        if steps != sorted(steps):
            raise ValueError("memory-system events must be ordered by step")
        return self


class MemoryEvidence(BaseModel):
    """Evidence returned to the actor, with source attribution for holdout filtering."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    evidence_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    source_record_ids: tuple[str, ...] = Field(min_length=1)
    score: float = Field(allow_inf_nan=False)
    kind: Literal["record", "path", "summary"] = "record"


class MemoryCostLedger(BaseModel):
    """Costs charged to a system, including memory-construction work."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    writes: int = Field(ge=0)
    reads: int = Field(ge=0)
    serialized_input_bytes: int = Field(ge=0)
    serialized_output_bytes: int = Field(ge=0)
    injected_tokens_estimate: int = Field(ge=0)
    embedding_calls: int = Field(default=0, ge=0)
    llm_calls: int = Field(default=0, ge=0)
    latency_ms: float = Field(default=0.0, ge=0.0, allow_inf_nan=False)


class MemorySystemReceipt(BaseModel):
    """Configuration and implementation identity bound to every selection."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    protocol_version: Literal["memory-system-v1"] = "memory-system-v1"
    system_id: str = Field(min_length=1)
    implementation_kind: Literal[
        "in_process_reference", "oci_sidecar", "frozen_selection_bundle"
    ]
    implementation_revision: str = Field(min_length=1)
    configuration_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    backend_id: str = Field(min_length=1)
    source_archive_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    image_digest: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    model_receipt_sha256s: tuple[str, ...] = ()
    publication_ready: bool = False


class MemorySelection(BaseModel):
    """A normalized system response before engine-side treatment filtering."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    request_id: str
    evidence: tuple[MemoryEvidence, ...]
    costs: MemoryCostLedger
    receipt: MemorySystemReceipt
    selection_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_digest(self) -> MemorySelection:
        payload = self.model_dump(mode="json", exclude={"selection_sha256"})
        if sha256_text(canonical_json(payload)) != self.selection_sha256:
            raise ValueError("selection_sha256 does not bind the selection")
        return self


class MemorySystemRun(BaseModel):
    """Engine-sealed result after applying the registered treatment semantics."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    treatment_mode: MemoryTreatmentMode
    visibility: Literal["serve", "holdout"]
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    raw_selection_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    rendered_query: str = Field(min_length=1)
    evaluation_expected_value: str = Field(min_length=1)
    evidence: tuple[MemoryEvidence, ...]
    candidate_available_to_system: bool
    candidate_served_to_actor: bool
    candidate_evidence_ids: tuple[str, ...]
    costs: MemoryCostLedger
    receipt: MemorySystemReceipt
    run_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_digest(self) -> MemorySystemRun:
        payload = self.model_dump(mode="json", exclude={"run_sha256"})
        if sha256_text(canonical_json(payload)) != self.run_sha256:
            raise ValueError("run_sha256 does not bind the memory-system run")
        return self


class MemorySystem(Protocol):
    """Narrow native-adapter seam; lifecycle and persistence stay inside the adapter."""

    identity: str
    receipt: MemorySystemReceipt

    def select(self, request: MemorySystemRequest) -> MemorySelection: ...


def _seal_selection(
    request: MemorySystemRequest,
    evidence: tuple[MemoryEvidence, ...],
    costs: MemoryCostLedger,
    receipt: MemorySystemReceipt,
) -> MemorySelection:
    payload = {
        "request_id": request.request_id,
        "evidence": [item.model_dump(mode="json") for item in evidence],
        "costs": costs.model_dump(mode="json"),
        "receipt": receipt.model_dump(mode="json"),
    }
    return MemorySelection(
        **payload,
        selection_sha256=sha256_text(canonical_json(payload)),
    )


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.casefold()))


def _token_sequence(text: str) -> tuple[str, ...]:
    return tuple(_TOKEN_RE.findall(text.casefold()))


def _record_evidence(record: MemorySystemRecord, *, score: float) -> MemoryEvidence:
    text = canonical_json(
        {
            "entity": record.entity_id,
            "key": record.key,
            "value": record.value,
            "step": record.written_step,
            "valid": record.valid,
            "untrusted": record.untrusted,
        }
    )
    return MemoryEvidence(
        evidence_id=f"record:{record.source_record_id}",
        text=text,
        source_record_ids=(record.source_record_id,),
        score=score,
    )


def _injected_tokens(evidence: tuple[MemoryEvidence, ...]) -> int:
    if not evidence:
        return 0
    rendered = canonical_json(
        [{"id": item.evidence_id, "text": item.text} for item in evidence]
    )
    return (len(rendered.encode()) + 3) // 4


def _fit_evidence_budget(
    request: MemorySystemRequest,
    ranked: tuple[MemoryEvidence, ...],
) -> tuple[MemoryEvidence, ...]:
    """Fit ranked snippets to the registered actor-visible token estimate."""

    selected: list[MemoryEvidence] = []
    for candidate in ranked:
        full = (*selected, candidate)
        if _injected_tokens(full) <= request.budget.max_injected_tokens:
            selected.append(candidate)
            continue
        low = 0
        high = len(candidate.text)
        best: MemoryEvidence | None = None
        while low <= high:
            midpoint = (low + high) // 2
            text = candidate.text[:midpoint].rstrip() + _TRUNCATION_MARKER
            truncated = candidate.model_copy(update={"text": text})
            if _injected_tokens((*selected, truncated)) <= request.budget.max_injected_tokens:
                best = truncated
                low = midpoint + 1
            else:
                high = midpoint - 1
        if best is not None:
            selected.append(best)
        if _injected_tokens(tuple(selected)) >= request.budget.max_injected_tokens:
            break
    return tuple(selected)


def _costs(
    request: MemorySystemRequest,
    evidence: tuple[MemoryEvidence, ...],
) -> MemoryCostLedger:
    input_json = canonical_json(request.model_dump(mode="json"))
    output_json = canonical_json([item.model_dump(mode="json") for item in evidence])
    injected_json = canonical_json(
        [{"id": item.evidence_id, "text": item.text} for item in evidence]
    )
    return MemoryCostLedger(
        writes=sum(
            event.kind in {"write", "update", "delete", "observe"}
            for event in request.events
        ),
        reads=1,
        serialized_input_bytes=len(input_json.encode()),
        serialized_output_bytes=len(output_json.encode()),
        injected_tokens_estimate=(len(injected_json.encode()) + 3) // 4,
    )


def _okapi_scores(
    documents: Mapping[str, tuple[str, ...]],
    query_terms: tuple[str, ...],
    *,
    k1: float,
    b: float,
) -> dict[str, float]:
    """Score tokenized documents with deterministic Okapi BM25."""

    count = len(documents)
    if count == 0:
        return {}
    average_length = sum(len(tokens) for tokens in documents.values()) / count
    document_frequency = {
        term: sum(term in set(tokens) for tokens in documents.values())
        for term in set(query_terms)
    }
    scores: dict[str, float] = {}
    for document_id, tokens in documents.items():
        total = 0.0
        if tokens and average_length > 0:
            for term in query_terms:
                frequency = tokens.count(term)
                if frequency == 0:
                    continue
                frequency_in_documents = document_frequency[term]
                inverse_document_frequency = math.log(
                    1.0
                    + (count - frequency_in_documents + 0.5)
                    / (frequency_in_documents + 0.5)
                )
                normalization = frequency + k1 * (
                    1.0 - b + b * len(tokens) / average_length
                )
                total += inverse_document_frequency * (
                    frequency * (k1 + 1.0) / normalization
                )
        scores[document_id] = total
    return scores


def _raw_event_text(event: MemorySystemEvent) -> str:
    return canonical_json(
        {
            "entity": event.entity_id,
            "key": event.key,
            "kind": event.kind,
            "step": event.step,
            "untrusted": event.untrusted,
            "value": event.value,
        }
    )


def _contains_entity_name(text: str, entity_id: str) -> bool:
    return bool(
        re.search(
            rf"(?<![a-z0-9]){re.escape(entity_id.casefold())}(?![a-z0-9])",
            text.casefold(),
        )
    )


class RecencyMemorySystem:
    """Deterministic active/inactive baseline: latest valid records under top-k."""

    identity = "recency-memory-v1"

    def __init__(self) -> None:
        config = {
            "strategy": "latest-valid",
            "tie_break": "source_record_id",
            "snippet_budget_policy": _SNIPPET_BUDGET_POLICY,
        }
        self.receipt = MemorySystemReceipt(
            system_id=self.identity,
            implementation_kind="in_process_reference",
            implementation_revision="harness.memory_trials.systems:recency-v2",
            configuration_sha256=sha256_text(canonical_json(config)),
            backend_id="python-stdlib",
        )

    def select(self, request: MemorySystemRequest) -> MemorySelection:
        records = _materialize_request_records(request)
        ranked = sorted(
            (record for record in records if record.valid),
            key=lambda record: (-record.written_step, record.source_record_id),
        )[: request.budget.retrieval_top_k]
        ranked_evidence = tuple(
            _record_evidence(record, score=float(-index))
            for index, record in enumerate(ranked)
        )
        evidence = _fit_evidence_budget(request, ranked_evidence)
        return _seal_selection(request, evidence, _costs(request, evidence), self.receipt)


class NoMemorySystem:
    """True actor-visible no-memory floor with a zero operation ledger."""

    identity = "no-memory-v1"

    def __init__(self) -> None:
        config = {"strategy": "return-no-evidence", "charge_memory_ops": False}
        self.receipt = MemorySystemReceipt(
            system_id=self.identity,
            implementation_kind="in_process_reference",
            implementation_revision="harness.memory_trials.systems:no-memory-v1",
            configuration_sha256=sha256_text(canonical_json(config)),
            backend_id="python-stdlib",
        )

    def select(self, request: MemorySystemRequest) -> MemorySelection:
        costs = MemoryCostLedger(
            writes=0,
            reads=0,
            serialized_input_bytes=0,
            serialized_output_bytes=0,
            injected_tokens_estimate=0,
        )
        return _seal_selection(request, (), costs, self.receipt)


class FullPrefixCeilingSystem:
    """Unmatched ceiling that injects every ordered prefix event as one block."""

    identity = "full-prefix-ceiling-v1"

    def __init__(self) -> None:
        config = {
            "strategy": "ordered-raw-prefix",
            "evidence_items": 1,
            "retrieval_reads": 0,
            "budget_class": "diagnostic-unmatched",
            "truncation": "forbidden",
            "supported_treatment_mode": "storage_and_service",
        }
        self.receipt = MemorySystemReceipt(
            system_id=self.identity,
            implementation_kind="in_process_reference",
            implementation_revision=(
                "harness.memory_trials.systems:full-prefix-ceiling-v1"
            ),
            configuration_sha256=sha256_text(canonical_json(config)),
            backend_id="python-stdlib",
        )

    def select(self, request: MemorySystemRequest) -> MemorySelection:
        if not request.events:
            evidence: tuple[MemoryEvidence, ...] = ()
        else:
            evidence = (
                MemoryEvidence(
                    evidence_id=f"full-prefix:{request.request_id}",
                    text=canonical_json(
                        [event.model_dump(mode="json") for event in request.events]
                    ),
                    source_record_ids=tuple(
                        event.source_event_id for event in request.events
                    ),
                    score=1.0,
                    kind="summary",
                ),
            )
        costs = _costs(request, evidence).model_copy(update={"reads": 0})
        return _seal_selection(request, evidence, costs, self.receipt)


class LRUMemorySystem:
    """Explicit bounded active cache driven only by ordered write/access events."""

    identity = "lru-active-cache-v1"

    def __init__(self) -> None:
        config = {
            "strategy": "explicit-access-lru",
            "capacity_field": "budget.active_slots",
            "write_counts_as_access": True,
            "tie_break": "source_record_id",
            "snippet_budget_policy": _SNIPPET_BUDGET_POLICY,
        }
        self.receipt = MemorySystemReceipt(
            system_id=self.identity,
            implementation_kind="in_process_reference",
            implementation_revision="harness.memory_trials.systems:lru-v1",
            configuration_sha256=sha256_text(canonical_json(config)),
            backend_id="python-stdlib",
        )

    def select(self, request: MemorySystemRequest) -> MemorySelection:
        records: dict[str, MemorySystemRecord] = {}
        active: list[str] = []

        def touch(record_id: str) -> None:
            if record_id in active:
                active.remove(record_id)
            active.append(record_id)
            while len(active) > request.budget.active_slots:
                active.pop(0)

        for event in request.events:
            if event.kind == "update":
                for record_id, record in tuple(records.items()):
                    if record.entity_id == event.entity_id and record.key == event.key:
                        records[record_id] = record.model_copy(update={"valid": False})
                        if record_id in active:
                            active.remove(record_id)
            if event.kind in {"write", "update", "observe"} and event.value is not None:
                records[event.source_event_id] = MemorySystemRecord(
                    source_record_id=event.source_event_id,
                    entity_id=event.entity_id,
                    key=event.key,
                    value=event.value,
                    written_step=event.step,
                    last_access_step=event.step,
                    valid=True,
                    untrusted=event.untrusted,
                )
                touch(event.source_event_id)
            elif event.kind == "access":
                matches = sorted(
                    (
                        record
                        for record in records.values()
                        if record.valid
                        and record.entity_id == event.entity_id
                        and record.key == event.key
                    ),
                    key=lambda record: (record.written_step, record.source_record_id),
                    reverse=True,
                )
                if matches:
                    record = matches[0]
                    records[record.source_record_id] = record.model_copy(
                        update={"last_access_step": event.step}
                    )
                    touch(record.source_record_id)
            elif event.kind == "delete":
                for record_id, record in tuple(records.items()):
                    if record.entity_id == event.entity_id and record.key == event.key:
                        records[record_id] = record.model_copy(update={"valid": False})
                        if record_id in active:
                            active.remove(record_id)

        selected = tuple(
            records[record_id]
            for record_id in reversed(active)
            if records[record_id].valid
        )[: min(request.budget.active_slots, request.budget.retrieval_top_k)]
        ranked_evidence = tuple(
            _record_evidence(record, score=float(record.last_access_step))
            for record in selected
        )
        evidence = _fit_evidence_budget(request, ranked_evidence)
        costs = _costs(request, evidence).model_copy(update={"reads": 0})
        return _seal_selection(request, evidence, costs, self.receipt)


class LexicalMemorySystem:
    """Deterministic BM25-free lexical control with explicit stable tie breaking."""

    identity = "lexical-memory-v1"

    def __init__(self) -> None:
        config = {
            "strategy": "query-token-overlap",
            "tie_break": "recency-then-id",
            "snippet_budget_policy": _SNIPPET_BUDGET_POLICY,
        }
        self.receipt = MemorySystemReceipt(
            system_id=self.identity,
            implementation_kind="in_process_reference",
            implementation_revision="harness.memory_trials.systems:lexical-v2",
            configuration_sha256=sha256_text(canonical_json(config)),
            backend_id="python-stdlib",
        )

    def select(self, request: MemorySystemRequest) -> MemorySelection:
        records = _materialize_request_records(request)
        query_tokens = _tokens(request.query)

        def rank(record: MemorySystemRecord) -> tuple[float, int, str]:
            record_tokens = _tokens(f"{record.entity_id} {record.key} {record.value}")
            score = float(len(query_tokens & record_tokens))
            return (-score, -record.written_step, record.source_record_id)

        ranked = sorted(
            (record for record in records if record.valid), key=rank
        )[: request.budget.retrieval_top_k]
        ranked_evidence = tuple(
            _record_evidence(
                record,
                score=float(
                    len(
                        query_tokens
                        & _tokens(f"{record.entity_id} {record.key} {record.value}")
                    )
                ),
            )
            for record in ranked
        )
        evidence = _fit_evidence_budget(request, ranked_evidence)
        return _seal_selection(request, evidence, _costs(request, evidence), self.receipt)


class BM25MemorySystem:
    """Deterministic Okapi BM25 over valid records with registered parameters."""

    identity = "bm25-memory-v1"

    def __init__(self, *, k1: float = 1.2, b: float = 0.75) -> None:
        if not math.isfinite(k1) or k1 <= 0:
            raise ValueError("BM25 k1 must be finite and positive")
        if not math.isfinite(b) or not 0 <= b <= 1:
            raise ValueError("BM25 b must be finite and in [0,1]")
        self.k1 = k1
        self.b = b
        config = {
            "strategy": "okapi-bm25",
            "k1": k1,
            "b": b,
            "document": "entity-id key value",
            "tie_break": "recency-then-source-record-id",
            "snippet_budget_policy": _SNIPPET_BUDGET_POLICY,
        }
        self.receipt = MemorySystemReceipt(
            system_id=self.identity,
            implementation_kind="in_process_reference",
            implementation_revision="harness.memory_trials.systems:bm25-v1",
            configuration_sha256=sha256_text(canonical_json(config)),
            backend_id="python-stdlib",
        )

    def select(self, request: MemorySystemRequest) -> MemorySelection:
        records = tuple(
            record for record in _materialize_request_records(request) if record.valid
        )
        documents = {
            record.source_record_id: _token_sequence(
                f"{record.entity_id} {record.key} {record.value}"
            )
            for record in records
        }
        query_terms = _token_sequence(request.query)
        scores = _okapi_scores(documents, query_terms, k1=self.k1, b=self.b)

        def score(record: MemorySystemRecord) -> float:
            return scores[record.source_record_id]

        ranked = sorted(
            records,
            key=lambda record: (
                -score(record),
                -record.written_step,
                record.source_record_id,
            ),
        )[: request.budget.retrieval_top_k]
        ranked_evidence = tuple(
            _record_evidence(record, score=score(record)) for record in ranked
        )
        evidence = _fit_evidence_budget(request, ranked_evidence)
        return _seal_selection(request, evidence, _costs(request, evidence), self.receipt)


class MemoryBankDecayMemorySystem:
    """Clean-room decay/reinforcement control with an explicit bug comparator."""

    def __init__(
        self,
        *,
        formula: Literal["corrected", "upstream-precedence", "no-decay"] = "corrected",
        time_scale: float = 5.0,
    ) -> None:
        if formula not in {"corrected", "upstream-precedence", "no-decay"}:
            raise ValueError("unsupported MemoryBank formula")
        if not math.isfinite(time_scale) or time_scale <= 0:
            raise ValueError("MemoryBank time_scale must be finite and positive")
        self.formula = formula
        self.time_scale = time_scale
        identities = {
            "corrected": "memorybank-corrected-decay-v1",
            "upstream-precedence": "memorybank-upstream-precedence-v1",
            "no-decay": "memorybank-no-decay-v1",
        }
        self.identity = identities[formula]
        config = {
            "strategy": "query-overlap-times-retention",
            "formula": formula,
            "time_scale": time_scale,
            "strength": "1 + prior explicit access count",
            "elapsed": "query step minus last access step",
            "upstream_repository_revision": (
                "cf61c4196e4cfdb0f2b7a0316249fa40312dc3a9"
            ),
            "upstream_code_imported": False,
            "tie_break": "source-record-id",
            "snippet_budget_policy": _SNIPPET_BUDGET_POLICY,
        }
        self.receipt = MemorySystemReceipt(
            system_id=self.identity,
            implementation_kind="in_process_reference",
            implementation_revision=(
                "harness.memory_trials.systems:memorybank-clean-room-v1"
            ),
            configuration_sha256=sha256_text(canonical_json(config)),
            backend_id="python-stdlib",
        )

    def select(self, request: MemorySystemRequest) -> MemorySelection:
        records = tuple(
            record for record in _materialize_request_records(request) if record.valid
        )
        current_step = 1 + max((event.step for event in request.events), default=0)
        query_tokens = _tokens(request.query)
        candidates = tuple(
            DecayCandidate(
                item_id=record.source_record_id,
                elapsed_steps=float(max(0, current_step - record.last_access_step)),
                prior_accesses=sum(
                    1
                    for event in request.events
                    if event.kind == "access"
                    and event.entity_id == record.entity_id
                    and event.key == record.key
                    and event.step >= record.written_step
                ),
                query_overlap=len(
                    query_tokens
                    & _tokens(f"{record.entity_id} {record.key} {record.value}")
                ),
            )
            for record in records
        )
        scores = score_candidates(
            candidates,
            formula=self.formula,
            time_scale=self.time_scale,
        )
        record_by_id = {record.source_record_id: record for record in records}
        ranked = scores[: request.budget.retrieval_top_k]
        ranked_evidence = tuple(
            _record_evidence(record_by_id[item.item_id], score=item.score)
            for item in ranked
        )
        evidence = _fit_evidence_budget(request, ranked_evidence)
        return _seal_selection(request, evidence, _costs(request, evidence), self.receipt)


class RawLogRRFMemorySystem:
    """Raw-event search with group RRF, local expansion, and bounded feedback.

    This is a deterministic ReFind-inspired mechanism control, not a reproduction:
    ``entity_id`` is the only available archive-group key, step order substitutes
    for local turn order, and keyword feedback substitutes for an LLM controller.
    """

    identity = "raw-log-rrf-memory-v1"

    def __init__(
        self,
        *,
        max_rounds: int = 4,
        context_window: int = 2,
        expansion_terms: int = 2,
        rrf_k: int = 60,
        k1: float = 1.2,
        b: float = 0.75,
    ) -> None:
        if max_rounds < 1:
            raise ValueError("max_rounds must be positive")
        if context_window < 0:
            raise ValueError("context_window cannot be negative")
        if expansion_terms < 0:
            raise ValueError("expansion_terms cannot be negative")
        if rrf_k < 1:
            raise ValueError("rrf_k must be positive")
        if not math.isfinite(k1) or k1 <= 0:
            raise ValueError("BM25 k1 must be finite and positive")
        if not math.isfinite(b) or not 0 <= b <= 1:
            raise ValueError("BM25 b must be finite and in [0,1]")
        self.max_rounds = max_rounds
        self.context_window = context_window
        self.expansion_terms = expansion_terms
        self.rrf_k = rrf_k
        self.k1 = k1
        self.b = b
        config = {
            "strategy": "raw-events-bm25-group-rrf-local-feedback",
            "paper_inspiration": "arxiv:2608.12888",
            "scope": "deterministic-mechanism-control-not-refind-reproduction",
            "archive_group_field": "entity_id",
            "time_axis": "event-step-only",
            "controller": "deterministic-rare-token-feedback",
            "max_rounds": max_rounds,
            "context_window": context_window,
            "expansion_terms": expansion_terms,
            "rrf_k": rrf_k,
            "k1": k1,
            "b": b,
            "omitted": ["llm-react-controller", "calendar-range-filter"],
            "snippet_budget_policy": _SNIPPET_BUDGET_POLICY,
        }
        self.receipt = MemorySystemReceipt(
            system_id=self.identity,
            implementation_kind="in_process_reference",
            implementation_revision="harness.memory_trials.systems:raw-log-rrf-v1",
            configuration_sha256=sha256_text(canonical_json(config)),
            backend_id="python-stdlib",
        )

    def select(self, request: MemorySystemRequest) -> MemorySelection:
        ordered_events = tuple(
            sorted(request.events, key=lambda event: (event.step, event.source_event_id))
        )
        all_documents = {
            event.source_event_id: _token_sequence(_raw_event_text(event))
            for event in ordered_events
        }
        global_document_frequency = {
            term: sum(term in set(tokens) for tokens in all_documents.values())
            for term in {token for tokens in all_documents.values() for token in tokens}
        }
        global_group_frequency = {
            term: len(
                {
                    event.entity_id
                    for event in ordered_events
                    if term in set(all_documents[event.source_event_id])
                }
            )
            for term in global_document_frequency
        }
        query_terms = _token_sequence(request.query)
        seen_groups: set[str] = set()
        ranked_evidence: list[MemoryEvidence] = []
        searches = 0
        round_limit = min(
            self.max_rounds,
            request.budget.max_archive_reads,
            request.budget.retrieval_top_k,
        )

        for _round in range(round_limit):
            candidates = tuple(
                event for event in ordered_events if event.entity_id not in seen_groups
            )
            if not candidates:
                break
            searches += 1
            documents = {
                event.source_event_id: all_documents[event.source_event_id]
                for event in candidates
            }
            bm25_scores = _okapi_scores(
                documents,
                query_terms,
                k1=self.k1,
                b=self.b,
            )
            if not bm25_scores or max(bm25_scores.values()) <= 0:
                break
            turn_order = sorted(
                candidates,
                key=lambda event: (
                    -bm25_scores[event.source_event_id],
                    -event.step,
                    event.source_event_id,
                ),
            )
            turn_rank = {
                event.source_event_id: rank
                for rank, event in enumerate(turn_order, start=1)
            }
            group_scores: dict[str, float] = defaultdict(float)
            for event in candidates:
                group_scores[event.entity_id] += bm25_scores[event.source_event_id]
            group_order = sorted(
                group_scores,
                key=lambda group_id: (-group_scores[group_id], group_id),
            )
            group_rank = {
                group_id: rank for rank, group_id in enumerate(group_order, start=1)
            }

            fused_scores = {
                event.source_event_id: 1.0
                / (self.rrf_k + turn_rank[event.source_event_id])
                + 1.0 / (self.rrf_k + group_rank[event.entity_id])
                for event in candidates
            }

            anchor = min(
                candidates,
                key=lambda event: (
                    -fused_scores[event.source_event_id],
                    -bm25_scores[event.source_event_id],
                    -event.step,
                    event.source_event_id,
                ),
            )
            group_events = tuple(
                event for event in ordered_events if event.entity_id == anchor.entity_id
            )
            anchor_index = next(
                index
                for index, event in enumerate(group_events)
                if event.source_event_id == anchor.source_event_id
            )
            block = group_events[
                max(0, anchor_index - self.context_window) :
                anchor_index + self.context_window + 1
            ]
            block_text = canonical_json(
                [
                    {
                        "entity": event.entity_id,
                        "key": event.key,
                        "kind": event.kind,
                        "step": event.step,
                        "untrusted": event.untrusted,
                        "value": event.value,
                    }
                    for event in block
                ]
            )
            ranked_evidence.append(
                MemoryEvidence(
                    evidence_id="raw-block:" + sha256_text(block_text)[:16],
                    text=block_text,
                    source_record_ids=tuple(event.source_event_id for event in block),
                    score=fused_scores[anchor.source_event_id],
                    kind="summary",
                )
            )
            seen_groups.add(anchor.entity_id)

            current_terms = set(query_terms)
            feedback_candidates = {
                token
                for event in block
                for token in all_documents[event.source_event_id]
                if len(token) >= 3
                and token not in current_terms
                and token not in _RAW_SEARCH_STOP_TERMS
            }
            feedback = sorted(
                feedback_candidates,
                key=lambda token: (
                    0 if global_group_frequency.get(token, 0) > 1 else 1,
                    global_document_frequency.get(token, 0),
                    -len(token),
                    token,
                ),
            )[: self.expansion_terms]
            query_terms = tuple((*query_terms, *feedback))

        evidence = _fit_evidence_budget(request, tuple(ranked_evidence))
        costs = _costs(request, evidence).model_copy(update={"reads": searches})
        return _seal_selection(request, evidence, costs, self.receipt)


class ProfileExpansionMemorySystem:
    """Graph-free exact-profile traversal through substring entity mentions.

    This isolates ProGraph's profile-expansion read mechanism without pretending
    that deterministic concatenation reproduces its LLM profile/residual writer.
    """

    identity = "profile-expansion-memory-v1"

    def __init__(
        self,
        *,
        initial_profiles: int = 1,
        max_hops: int = 5,
        minimum_query_overlap: int = 1,
    ) -> None:
        if initial_profiles < 1:
            raise ValueError("initial_profiles must be positive")
        if max_hops < 1:
            raise ValueError("max_hops must be positive")
        if minimum_query_overlap < 0:
            raise ValueError("minimum_query_overlap cannot be negative")
        self.initial_profiles = initial_profiles
        self.max_hops = max_hops
        self.minimum_query_overlap = minimum_query_overlap
        config = {
            "strategy": "exact-profile-substring-expansion",
            "paper_inspiration": "arxiv:2607.19359",
            "scope": "deterministic-read-path-control-not-prograph-reproduction",
            "profile_writer": "exact-valid-record-concatenation",
            "initial_profiles": initial_profiles,
            "max_hops": max_hops,
            "minimum_query_overlap": minimum_query_overlap,
            "omitted": [
                "llm-profile-update",
                "compression-residual-co-extraction",
                "embedding-relevance-gate",
            ],
            "snippet_budget_policy": _SNIPPET_BUDGET_POLICY,
        }
        self.receipt = MemorySystemReceipt(
            system_id=self.identity,
            implementation_kind="in_process_reference",
            implementation_revision=(
                "harness.memory_trials.systems:profile-expansion-v1"
            ),
            configuration_sha256=sha256_text(canonical_json(config)),
            backend_id="python-stdlib",
        )

    def select(self, request: MemorySystemRequest) -> MemorySelection:
        valid_records = tuple(
            record for record in _materialize_request_records(request) if record.valid
        )
        grouped_records: dict[str, list[MemorySystemRecord]] = defaultdict(list)
        for record in valid_records:
            grouped_records[record.entity_id].append(record)
        by_entity: dict[str, tuple[MemorySystemRecord, ...]] = {
            entity_id: tuple(
                sorted(records, key=lambda record: (record.written_step, record.source_record_id))
            )
            for entity_id, records in grouped_records.items()
        }
        profile_texts = {
            entity_id: canonical_json(
                [
                    {
                        "key": record.key,
                        "step": record.written_step,
                        "untrusted": record.untrusted,
                        "value": record.value,
                    }
                    for record in records
                ]
            )
            for entity_id, records in by_entity.items()
        }
        query_tokens = _tokens(request.query)

        def relevance(entity_id: str) -> float:
            overlap = len(query_tokens & _tokens(profile_texts[entity_id]))
            name_boost = 0.3 if _contains_entity_name(request.query, entity_id) else 0.0
            return float(overlap) + name_boost

        ranked_entities = sorted(
            by_entity,
            key=lambda entity_id: (-relevance(entity_id), entity_id),
        )
        if not ranked_entities or relevance(ranked_entities[0]) <= 0:
            evidence: tuple[MemoryEvidence, ...] = ()
            return _seal_selection(request, evidence, _costs(request, evidence), self.receipt)

        limit = request.budget.retrieval_top_k
        selected = ranked_entities[: min(self.initial_profiles, limit)]
        selected_set = set(selected)
        hop_by_entity = {entity_id: 0 for entity_id in selected}
        frontier = deque(selected)
        while frontier and len(selected) < limit:
            source_entity = frontier.popleft()
            source_hop = hop_by_entity[source_entity]
            if source_hop >= self.max_hops:
                continue
            mentioned = sorted(
                (
                    entity_id
                    for entity_id in by_entity
                    if entity_id not in selected_set
                    and _contains_entity_name(profile_texts[source_entity], entity_id)
                    and relevance(entity_id) >= self.minimum_query_overlap
                ),
                key=lambda entity_id: (-relevance(entity_id), entity_id),
            )
            for entity_id in mentioned:
                selected.append(entity_id)
                selected_set.add(entity_id)
                hop_by_entity[entity_id] = source_hop + 1
                frontier.append(entity_id)
                if len(selected) >= limit:
                    break

        ranked_evidence = tuple(
            MemoryEvidence(
                evidence_id="profile:" + sha256_text(entity_id)[:16],
                text=canonical_json(
                    {
                        "entity": entity_id,
                        "profile_records": [
                            {
                                "key": record.key,
                                "step": record.written_step,
                                "untrusted": record.untrusted,
                                "value": record.value,
                            }
                            for record in by_entity[entity_id]
                        ],
                    }
                ),
                source_record_ids=tuple(
                    record.source_record_id for record in by_entity[entity_id]
                ),
                score=relevance(entity_id) - 0.01 * hop_by_entity[entity_id],
                kind="summary",
            )
            for entity_id in selected
        )
        evidence = _fit_evidence_budget(request, ranked_evidence)
        return _seal_selection(request, evidence, _costs(request, evidence), self.receipt)


class TemporalGraphMemorySystem:
    """Exact relation-path control; graph bytes and all selected edges are charged."""

    identity = "temporal-graph-memory-v1"

    def __init__(self, *, max_hops: int = 3) -> None:
        if max_hops < 1:
            raise ValueError("max_hops must be positive")
        self.max_hops = max_hops
        config = {
            "strategy": "exact-relation-bfs",
            "max_hops": max_hops,
            "snippet_budget_policy": _SNIPPET_BUDGET_POLICY,
        }
        self.receipt = MemorySystemReceipt(
            system_id=self.identity,
            implementation_kind="in_process_reference",
            implementation_revision="harness.memory_trials.systems:graph-v2",
            configuration_sha256=sha256_text(canonical_json(config)),
            backend_id="python-stdlib",
        )

    def select(self, request: MemorySystemRequest) -> MemorySelection:
        valid = tuple(
            record for record in _materialize_request_records(request) if record.valid
        )
        by_entity: dict[str, list[MemorySystemRecord]] = defaultdict(list)
        for record in valid:
            by_entity[record.entity_id].append(record)
        starts = sorted(
            (entity for entity in by_entity if entity.casefold() in request.query.casefold()),
            key=len,
            reverse=True,
        )
        queue = deque((start, tuple()) for start in starts)
        visited = set(starts)
        paths: list[tuple[MemorySystemRecord, ...]] = []
        while queue:
            entity, path = queue.popleft()
            if len(path) >= self.max_hops:
                continue
            for edge in sorted(by_entity.get(entity, ()), key=lambda item: item.source_record_id):
                new_path = (*path, edge)
                paths.append(new_path)
                if edge.value not in visited:
                    visited.add(edge.value)
                    queue.append((edge.value, new_path))
        best = max(
            paths,
            key=lambda path: (len(path), tuple(e.source_record_id for e in path)),
            default=(),
        )
        selected = best[: request.budget.retrieval_top_k]
        if selected:
            text = canonical_json(
                [
                    {
                        "from": edge.entity_id,
                        "relation": edge.key,
                        "to": edge.value,
                        "step": edge.written_step,
                    }
                    for edge in selected
                ]
            )
            ranked_evidence = (
                MemoryEvidence(
                    evidence_id="path:" + sha256_text(text)[:16],
                    text=text,
                    source_record_ids=tuple(edge.source_record_id for edge in selected),
                    score=float(len(selected)),
                    kind="path",
                ),
            )
            evidence = _fit_evidence_budget(request, ranked_evidence)
        else:
            evidence = ()
        return _seal_selection(request, evidence, _costs(request, evidence), self.receipt)


class ReferenceMemorySystem:
    """Task-blind deterministic hybrid used to validate the shared contract."""

    identity = "reference-memory-system-v2"

    def __init__(self) -> None:
        self._lexical = LexicalMemorySystem()
        self._graph = TemporalGraphMemorySystem()
        config = {
            "route": "graph-chain-length-at-least-two-else-lexical",
            "graph": self._graph.identity,
            "lexical": self._lexical.identity,
            "graph_configuration_sha256": self._graph.receipt.configuration_sha256,
            "lexical_configuration_sha256": self._lexical.receipt.configuration_sha256,
            "forbidden_routing_inputs": ["stratum", "oracle", "candidate", "suffix"],
        }
        self.receipt = MemorySystemReceipt(
            system_id=self.identity,
            implementation_kind="in_process_reference",
            implementation_revision="harness.memory_trials.systems:reference-v2",
            configuration_sha256=sha256_text(canonical_json(config)),
            backend_id="python-stdlib",
        )

    def select(self, request: MemorySystemRequest) -> MemorySelection:
        graph = self._graph.select(request)
        graph_has_chain = bool(
            graph.evidence and len(graph.evidence[0].source_record_ids) >= 2
        )
        selected = graph if graph_has_chain else self._lexical.select(request)
        return _seal_selection(request, selected.evidence, selected.costs, self.receipt)


def materialize_prefix_records(task: MemoryTask) -> tuple[MemoryRecord, ...]:
    """Apply ordered writes, updates, and deletes before the eligibility boundary."""

    records: dict[str, MemoryRecord] = {}
    for event in task.events:
        if event.step >= task.eligibility_step:
            break
        if event.kind in {EventKind.WRITE, EventKind.UPDATE} and event.value is not None:
            if event.kind is EventKind.UPDATE:
                for record_id, record in tuple(records.items()):
                    if record.entity_id == event.entity_id and record.key == event.key:
                        records[record_id] = record.model_copy(update={"valid": False})
            records[event.event_id] = MemoryRecord(
                record_id=event.event_id,
                entity_id=event.entity_id,
                key=event.key,
                value=event.value,
                written_step=event.step,
                last_access_step=event.step,
                source_quality=event.source_quality,
                contradiction_count=event.contradiction_count,
                candidate=event.candidate,
                valid=True,
                untrusted=event.untrusted,
                residency=_residency(task.stratum),
            )
        elif event.kind is EventKind.DELETE:
            for record_id, record in tuple(records.items()):
                if record.entity_id == event.entity_id and record.key == event.key:
                    records[record_id] = record.model_copy(update={"valid": False})
        elif event.kind is EventKind.ACCESS:
            matches = sorted(
                (
                    record
                    for record in records.values()
                    if record.valid
                    and record.entity_id == event.entity_id
                    and record.key == event.key
                ),
                key=lambda record: (record.written_step, record.record_id),
                reverse=True,
            )
            if matches:
                record = matches[0]
                records[record.record_id] = record.model_copy(
                    update={"last_access_step": event.step}
                )
    return tuple(sorted(records.values(), key=lambda record: record.written_step))


def _materialize_request_records(
    request: MemorySystemRequest,
) -> tuple[MemorySystemRecord, ...]:
    records: dict[str, MemorySystemRecord] = {}
    for event in request.events:
        if event.kind == "update":
            for record_id, record in tuple(records.items()):
                if record.entity_id == event.entity_id and record.key == event.key:
                    records[record_id] = record.model_copy(update={"valid": False})
        if event.kind == "access":
            matches = sorted(
                (
                    record
                    for record in records.values()
                    if record.valid
                    and record.entity_id == event.entity_id
                    and record.key == event.key
                ),
                key=lambda record: (record.written_step, record.source_record_id),
                reverse=True,
            )
            if matches:
                record = matches[0]
                records[record.source_record_id] = record.model_copy(
                    update={"last_access_step": event.step}
                )
        if event.kind in {"write", "update", "observe"} and event.value is not None:
            records[event.source_event_id] = MemorySystemRecord(
                source_record_id=event.source_event_id,
                entity_id=event.entity_id,
                key=event.key,
                value=event.value,
                written_step=event.step,
                last_access_step=event.step,
                valid=True,
                untrusted=event.untrusted,
            )
        elif event.kind == "delete":
            for record_id, record in tuple(records.items()):
                if record.entity_id == event.entity_id and record.key == event.key:
                    records[record_id] = record.model_copy(update={"valid": False})
    return tuple(sorted(records.values(), key=lambda record: record.written_step))


def materialize_request_records(
    request: MemorySystemRequest,
) -> tuple[MemorySystemRecord, ...]:
    """Materialize only the task-blind events exposed to a memory system."""

    return _materialize_request_records(request)


def _residency(stratum: MemoryStratum) -> Literal["active", "archive", "graph"]:
    if stratum is MemoryStratum.ACTIVE_CORE:
        return "active"
    if stratum is MemoryStratum.TEMPORAL_GRAPH:
        return "graph"
    return "archive"


def _opaque_id(session_scope: str, namespace: str, value: str) -> str:
    return f"{namespace}-{sha256_text(f'{session_scope}:{namespace}:{value}')[:16]}"


def _replace_identifiers(text: str, replacements: Mapping[str, str]) -> str:
    rendered = text
    for original in sorted(replacements, key=len, reverse=True):
        rendered = rendered.replace(original, replacements[original])
    return rendered


def build_memory_system_request(
    task: MemoryTask,
    *,
    visibility: Literal["serve", "holdout"],
    treatment_mode: MemoryTreatmentMode,
) -> tuple[MemorySystemRequest, str]:
    included = tuple(event for event in task.events if event.step < task.eligibility_step)
    if treatment_mode == "storage_and_service" and visibility == "holdout":
        included = tuple(event for event in included if not event.candidate)
    entity_ids = {event.entity_id for event in included}
    entity_map = {
        entity_id: _opaque_id(task.session_id, "entity", entity_id)
        for entity_id in entity_ids
    }
    event_id_map = {
        event.event_id: _opaque_id(task.session_id, "event", event.event_id)
        for event in included
    }

    def neutral_value(value: str | None) -> str | None:
        if value is None:
            return None
        if value in entity_map:
            return entity_map[value]
        rendered = _replace_identifiers(value, entity_map)
        if task.oracle.safety_case is None and re.fullmatch(
            r"(?:wrong|value|noise)-[a-zA-Z0-9._-]+", rendered
        ):
            return _opaque_id(task.session_id, "datum", rendered)
        return rendered

    system_events = tuple(
        MemorySystemEvent(
            source_event_id=event_id_map[event.event_id],
            step=event.step,
            kind=(
                "observe"
                if event.kind in {EventKind.OBSERVE, EventKind.DISTRACTOR}
                else event.kind.value
            ),
            entity_id=entity_map[event.entity_id],
            key=event.key,
            value=neutral_value(event.value),
            untrusted=event.untrusted,
        )
        for event in included
    )
    request_payload = {
        "session_scope": task.session_id,
        "events": system_events,
        "query": _replace_identifiers(task.query, entity_map),
        "budget": task.budget,
    }
    request_id = sha256_text(
        canonical_json(
            {
                key: (
                    [event.model_dump(mode="json") for event in value]
                    if key == "events"
                    else value.model_dump(mode="json")
                    if isinstance(value, BaseModel)
                    else value
                )
                for key, value in request_payload.items()
            }
        )
    )
    return (
        MemorySystemRequest(request_id=request_id, **request_payload),
        neutral_value(task.oracle.expected_value) or task.oracle.expected_value,
    )


def run_memory_system(
    system: MemorySystem,
    task: MemoryTask,
    *,
    visibility: Literal["serve", "holdout"],
    treatment_mode: MemoryTreatmentMode,
) -> MemorySystemRun:
    """Run one system with treatment and budget enforcement owned by the harness."""

    candidate_ids = {_opaque_id(task.session_id, "event", task.candidate_id)}
    request, evaluation_expected_value = build_memory_system_request(
        task,
        visibility=visibility,
        treatment_mode=treatment_mode,
    )
    selection = system.select(request)
    if selection.request_id != request.request_id:
        raise ValueError("memory system returned a selection for a different request")
    requested_ids = {event.source_event_id for event in request.events}
    for evidence in selection.evidence:
        if not set(evidence.source_record_ids) <= requested_ids:
            raise ValueError("memory evidence cites a record absent from the request")
    if len(selection.evidence) > task.budget.retrieval_top_k:
        raise ValueError("memory system exceeded retrieval_top_k")
    if (
        task.stratum is MemoryStratum.ACTIVE_CORE
        and len(selection.evidence) > task.budget.active_slots
    ):
        raise ValueError("memory system exceeded active_slots")

    evidence = selection.evidence
    if treatment_mode == "serve_only" and visibility == "holdout":
        evidence = tuple(
            item
            for item in evidence
            if candidate_ids.isdisjoint(item.source_record_ids)
        )
    output_json = canonical_json([item.model_dump(mode="json") for item in evidence])
    injected_json = canonical_json(
        [{"id": item.evidence_id, "text": item.text} for item in evidence]
    )
    injected_tokens = (
        (len(injected_json.encode()) + 3) // 4 if evidence else 0
    )
    if injected_tokens > task.budget.max_injected_tokens:
        raise ValueError("memory system exceeded max_injected_tokens")
    costs = selection.costs.model_copy(
        update={
            "serialized_output_bytes": len(output_json.encode()),
            "injected_tokens_estimate": injected_tokens,
        }
    )
    if costs.reads > task.budget.max_archive_reads:
        raise ValueError("memory system exceeded max_archive_reads")
    selected_source_ids = {
        source_id for item in evidence for source_id in item.source_record_ids
    }
    candidate_evidence_ids = tuple(
        item.evidence_id
        for item in evidence
        if not candidate_ids.isdisjoint(item.source_record_ids)
    )
    candidate_available = bool(candidate_ids & requested_ids)
    payload = {
        "treatment_mode": treatment_mode,
        "visibility": visibility,
        "request_sha256": sha256_text(canonical_json(request.model_dump(mode="json"))),
        "raw_selection_sha256": selection.selection_sha256,
        "rendered_query": request.query,
        "evaluation_expected_value": evaluation_expected_value,
        "evidence": [item.model_dump(mode="json") for item in evidence],
        "candidate_available_to_system": candidate_available,
        "candidate_served_to_actor": bool(candidate_ids & selected_source_ids),
        "candidate_evidence_ids": candidate_evidence_ids,
        "costs": costs.model_dump(mode="json"),
        "receipt": selection.receipt.model_dump(mode="json"),
    }
    return MemorySystemRun(
        **payload,
        run_sha256=sha256_text(canonical_json(payload)),
    )


def receipt_dict(receipt: MemorySystemReceipt) -> Mapping[str, object]:
    """Return the canonical receipt surface for provenance manifests."""

    return receipt.model_dump(mode="json")
