"""Pinned public-benchmark adapters for executable memory trials.

Network access deliberately does not live in this module. A preparation command
downloads and verifies the immutable source artifact; runtime adapters accept
only a local file plus its registered digest. This keeps benchmark acquisition
separate from causal execution and makes every task source content-addressed.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from harness.memory_trials.schema import (
    EventKind,
    MemoryBudget,
    MemoryEvent,
    MemoryOracle,
    MemoryStratum,
    MemoryTask,
    seal_task,
)

LONGMEMEVAL_DATASET_ID = "xiaowu0162/longmemeval-cleaned"
LONGMEMEVAL_DATASET_REVISION = "98d7416c24c778c2fee6e6f3006e7a073259d48f"
LONGMEMEVAL_ORACLE_FILENAME = "longmemeval_oracle.json"
LONGMEMEVAL_ORACLE_SHA256 = (
    "821a2034d219ab45846873dd14c14f12cfe7776e73527a483f9dac095d38620c"
)
LONGMEMEVAL_ORACLE_SIZE = 15_388_478
LONGMEMEVAL_S_FILENAME = "longmemeval_s_cleaned.json"
LONGMEMEVAL_S_SHA256 = (
    "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442"
)
LONGMEMEVAL_S_SIZE = 277_383_467
LONGMEMEVAL_LICENSE = "MIT"
LONGMEMEVAL_ADAPTER_VERSION = "longmemeval-oracle-context-v2"
LONGMEMEVAL_RETRIEVAL_ADAPTER_VERSION = "longmemeval-full-haystack-retrieval-v3"
LONGMEMEVAL_ORACLE_ARTIFACT_ROLE = "oracle-context-qa"
LONGMEMEVAL_RETRIEVAL_ARTIFACT_ROLE = "full-haystack-retrieval"
LONGMEMEVAL_REPOSITORY_REVISION = "9e0b455f4ef0e2ab8f2e582289761153549043fc"
LONGMEMEVAL_OFFICIAL_EVALUATOR_SHA256 = (
    "ecce9c4c79dc89d99534ac17b383a5cbb5b9f0c69ee98adaf0684742e3d95251"
)
LONGMEMEVAL_FULL_TASK_MANIFEST_SHA256 = (
    "0c5a55a7aeeb492410031560ef71585e83a6f594fffdef1bd7a9b59ce1119c9d"
)
LONGMEMEVAL_SCREEN32_TASK_MANIFEST_SHA256 = (
    "c9c91ab51fb5889b8998a8df93e9d8e13cf383f374dfa7f29ea4bf3b4f892620"
)
LONGMEMEVAL_QUESTION_TYPES = (
    "single-session-user",
    "single-session-assistant",
    "single-session-preference",
    "multi-session",
    "temporal-reasoning",
    "knowledge-update",
)
LONGMEMEVAL_TRANSPORT_PANEL_VERSION = "longmemeval-transport-panel-v2"
LONGMEMEVAL_TRANSPORT_PANEL_SEED = 42
LONGMEMEVAL_TRANSPORT_PANEL_QUOTAS = (
    ("single-session-preference", False, 5),
    ("single-session-assistant", False, 5),
    ("single-session-user", True, 1),
    ("single-session-user", False, 4),
    ("knowledge-update", True, 1),
    ("knowledge-update", False, 4),
    ("multi-session", False, 6),
    ("temporal-reasoning", False, 6),
)
LONGMEMEVAL_SCREEN32_RAW_TASK_IDS = (
    "2133c1b5_abs",
    "29f2956b_abs",
    "1a1907b4",
    "75832dbd",
    "0a34ad58",
    "54026fce",
    "95228167",
    "cc539528",
    "8752c811",
    "8cf51dda",
    "c4f10528",
    "7161e7e2",
    "001be529",
    "66f24dbb",
    "58bf7951",
    "b320f3f8",
    "69fee5aa",
    "1cea1afa",
    "45dc21b6",
    "2133c1b5",
    "ba358f49",
    "2318644b",
    "60bf93ed",
    "88432d0a",
    "e3038f8c",
    "a346bb18",
    "gpt4_cd90e484",
    "gpt4_e414231e",
    "gpt4_7f6b06db",
    "8c18457d",
    "gpt4_9a159967",
    "gpt4_b0863698",
)

_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9._-]+")
_DATE_FORMAT = "%Y/%m/%d (%a) %H:%M"


class PublicMemorySourceError(ValueError):
    """Raised when a public benchmark artifact or row violates its contract."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def longmemeval_download_url(
    *,
    revision: str = LONGMEMEVAL_DATASET_REVISION,
    filename: str = LONGMEMEVAL_ORACLE_FILENAME,
) -> str:
    return (
        f"https://huggingface.co/datasets/{LONGMEMEVAL_DATASET_ID}/"
        f"resolve/{revision}/{filename}?download=true"
    )


def _safe_id(value: str, *, fallback: str) -> str:
    rendered = _SAFE_ID_RE.sub("-", value).strip("-._")
    return rendered or fallback


def _answer_text(value: Any) -> str:
    if isinstance(value, str):
        answer = value.strip()
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and not math.isfinite(value):
            raise PublicMemorySourceError("LongMemEval answer must be finite")
        answer = str(value)
    else:
        raise PublicMemorySourceError("LongMemEval answer must be text or a number")
    if not answer:
        raise PublicMemorySourceError("LongMemEval answer must be non-empty")
    return answer


def _timestamp_key(value: str, index: int) -> tuple[int, str, int]:
    try:
        parsed = datetime.strptime(value, _DATE_FORMAT)
    except ValueError:
        return (1, value, index)
    return (0, parsed.isoformat(), index)


def derive_longmemeval_transport_panel(
    raw_rows: Sequence[Mapping[str, Any]],
    *,
    seed: int = LONGMEMEVAL_TRANSPORT_PANEL_SEED,
) -> tuple[str, ...]:
    """Derive the registered balanced transport panel without session overlap.

    This panel is an interface/safety smoke, never the scientific benchmark.
    Claim-bearing system comparisons must evaluate all 500 tasks. The derivation
    makes the former convenience sample reproducible and forces two abstention
    cases instead of relying on source order.
    """

    rows: list[Mapping[str, Any]] = []
    seen_ids: set[str] = set()
    for index, row in enumerate(raw_rows):
        raw_id = row.get("question_id")
        question_type = row.get("question_type")
        session_ids = row.get("haystack_session_ids")
        if not isinstance(raw_id, str) or not raw_id or raw_id in seen_ids:
            raise PublicMemorySourceError(
                f"panel row {index} has an invalid or duplicate question_id"
            )
        if question_type not in LONGMEMEVAL_QUESTION_TYPES:
            raise PublicMemorySourceError(
                f"panel row {index} has an unsupported question_type"
            )
        if not isinstance(session_ids, list) or not session_ids or not all(
            isinstance(value, str) and value for value in session_ids
        ):
            raise PublicMemorySourceError(
                f"panel row {index} has invalid haystack_session_ids"
            )
        seen_ids.add(raw_id)
        rows.append(row)

    buckets: list[
        tuple[int, str, bool, int, list[Mapping[str, Any]]]
    ] = []
    for question_type, abstention, quota in LONGMEMEVAL_TRANSPORT_PANEL_QUOTAS:
        eligible = [
            row
            for row in rows
            if row["question_type"] == question_type
            and ("_abs" in str(row["question_id"])) is abstention
        ]
        buckets.append((len(eligible), question_type, abstention, quota, eligible))

    selected: list[str] = []
    used_session_ids: set[str] = set()
    for _population, question_type, abstention, quota, eligible in sorted(
        buckets, key=lambda item: (item[0], item[1], item[2])
    ):
        ranked = sorted(
            eligible,
            key=lambda row: hashlib.sha256(
                (
                    f"{LONGMEMEVAL_TRANSPORT_PANEL_VERSION}:{seed}:"
                    f"{row['question_id']}"
                ).encode()
            ).hexdigest(),
        )
        accepted = 0
        for row in ranked:
            session_ids = set(row["haystack_session_ids"])
            if used_session_ids & session_ids:
                continue
            selected.append(str(row["question_id"]))
            used_session_ids.update(session_ids)
            accepted += 1
            if accepted == quota:
                break
        if accepted != quota:
            raise PublicMemorySourceError(
                "cannot satisfy LongMemEval transport panel quota for "
                f"{question_type}/abstention={abstention}: {accepted} != {quota}"
            )
    return tuple(selected)


class LongMemEvalTaskSource:
    """Convert one pinned LongMemEval artifact into one-candidate trials.

    Candidate selection is uniform over all non-empty historical turns using a
    committed seed and question ID. It never reads the future question, answer,
    ``has_answer`` labels, or ``answer_session_ids``. Those labels remain useful
    for separate retrieval analysis but cannot define the population for a
    past-only write/retention policy. Artifact role is explicit: the compact
    oracle-context file cannot be used to support retrieval or graph claims.
    """

    def __init__(
        self,
        path: Path,
        *,
        expected_sha256: str = LONGMEMEVAL_ORACLE_SHA256,
        expected_size: int = LONGMEMEVAL_ORACLE_SIZE,
        dataset_revision: str = LONGMEMEVAL_DATASET_REVISION,
        candidate_seed: int = 42,
        budget: MemoryBudget | None = None,
        limit: int | None = None,
        task_ids: Sequence[str] | None = None,
        artifact_role: str = LONGMEMEVAL_ORACLE_ARTIFACT_ROLE,
        session_order: Literal["chronological", "source"] = "chronological",
        text_normalization: Literal["strip", "verbatim"] = "strip",
    ) -> None:
        if artifact_role not in {
            LONGMEMEVAL_ORACLE_ARTIFACT_ROLE,
            LONGMEMEVAL_RETRIEVAL_ARTIFACT_ROLE,
        }:
            raise PublicMemorySourceError(
                f"unsupported LongMemEval artifact_role: {artifact_role}"
            )
        if session_order not in {"chronological", "source"}:
            raise PublicMemorySourceError(
                f"unsupported LongMemEval session_order: {session_order}"
            )
        if text_normalization not in {"strip", "verbatim"}:
            raise PublicMemorySourceError(
                "unsupported LongMemEval text_normalization: "
                f"{text_normalization}"
            )
        self.artifact_role = artifact_role
        self.session_order = session_order
        self.text_normalization = text_normalization
        if artifact_role == LONGMEMEVAL_RETRIEVAL_ARTIFACT_ROLE:
            self.identity = "longmemeval-cleaned-full-haystack-v1"
            self.adapter_version = LONGMEMEVAL_RETRIEVAL_ADAPTER_VERSION
            self.stratum = MemoryStratum.INACTIVE_ARCHIVE
            retrieval_evaluation_capable = True
        else:
            self.identity = "longmemeval-cleaned-oracle-v2"
            self.adapter_version = LONGMEMEVAL_ADAPTER_VERSION
            self.stratum = MemoryStratum.ORACLE_CONTEXT
            retrieval_evaluation_capable = False
        self.path = path.resolve()
        if not self.path.is_file():
            raise PublicMemorySourceError(f"LongMemEval artifact is missing: {self.path}")
        if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
            raise PublicMemorySourceError("expected_sha256 must be lowercase SHA-256")
        if expected_size < 1:
            raise PublicMemorySourceError("expected_size must be positive")
        if limit is not None and limit < 1:
            raise PublicMemorySourceError("limit must be positive")
        if limit is not None and task_ids is not None:
            raise PublicMemorySourceError("limit and task_ids are mutually exclusive")
        actual_size = self.path.stat().st_size
        if actual_size != expected_size:
            raise PublicMemorySourceError(
                f"LongMemEval artifact size mismatch: {actual_size} != {expected_size}"
            )
        actual_sha256 = sha256_file(self.path)
        if actual_sha256 != expected_sha256:
            raise PublicMemorySourceError(
                f"LongMemEval artifact digest mismatch: {actual_sha256}"
            )
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PublicMemorySourceError("cannot parse LongMemEval artifact") from exc
        if not isinstance(raw, list) or not raw:
            raise PublicMemorySourceError("LongMemEval artifact must be a non-empty list")
        raw_by_id: dict[str, tuple[int, dict[str, Any]]] = {}
        for index, row in enumerate(raw):
            if not isinstance(row, dict):
                raise PublicMemorySourceError(f"LongMemEval row {index} must be an object")
            raw_id = row.get("question_id")
            if not isinstance(raw_id, str) or not raw_id.strip():
                raise PublicMemorySourceError(f"LongMemEval row {index} has no question_id")
            if raw_id in raw_by_id:
                raise PublicMemorySourceError(f"duplicate raw question ID: {raw_id}")
            raw_by_id[raw_id] = (index, row)
        if task_ids is not None:
            if not task_ids or len(set(task_ids)) != len(task_ids):
                raise PublicMemorySourceError("task_ids must be non-empty and unique")
            unknown = [task_id for task_id in task_ids if task_id not in raw_by_id]
            if unknown:
                raise PublicMemorySourceError(
                    f"unknown LongMemEval task_ids: {unknown[:3]}"
                )
            selected = [raw_by_id[task_id] for task_id in task_ids]
            selection = "explicit-raw-question-ids"
        else:
            selected = list(raw_by_id.values())
            if limit is not None:
                selected = selected[:limit]
            selection = "source-order-prefix" if limit is not None else "all-tasks"
        self.budget = budget or MemoryBudget()
        self.dataset_revision = dataset_revision
        self.candidate_seed = candidate_seed
        self._rows: dict[str, dict[str, Any]] = {}
        self._raw_ids: dict[str, str] = {}
        question_type_counts: dict[str, int] = {}
        for index, row in selected:
            raw_id = row["question_id"]
            task_id = f"longmemeval-{_safe_id(raw_id, fallback=f'row-{index:04d}')}"
            if task_id in self._rows:
                raise PublicMemorySourceError(f"duplicate normalized task ID: {task_id}")
            self._validate_row(row, index=index)
            self._rows[task_id] = row
            self._raw_ids[task_id] = raw_id
            question_type = row["question_type"]
            question_type_counts[question_type] = (
                question_type_counts.get(question_type, 0) + 1
            )
        self._ids = tuple(self._rows)
        self.provenance = {
            "source": self.identity,
            "dataset_id": LONGMEMEVAL_DATASET_ID,
            "dataset_revision": dataset_revision,
            "dataset_filename": self.path.name,
            "dataset_sha256": actual_sha256,
            "dataset_size": actual_size,
            "dataset_license": LONGMEMEVAL_LICENSE,
            "adapter_version": self.adapter_version,
            "candidate_policy": "uniform-prefix-turn-with-committed-seed",
            "candidate_seed": candidate_seed,
            "candidate_forbidden_inputs": [
                "question",
                "answer",
                "has_answer",
                "answer_session_ids",
            ],
            "raw_rows": len(raw),
            "task_count": len(self._ids),
            "task_selection": selection,
            "selected_raw_task_ids_sha256": hashlib.sha256(
                json.dumps(list(self._raw_ids.values()), separators=(",", ":")).encode()
            ).hexdigest(),
            "question_type_counts": dict(sorted(question_type_counts.items())),
            "artifact_role": self.artifact_role,
            "session_order": self.session_order,
            "text_normalization": self.text_normalization,
            "retrieval_evaluation_capable": retrieval_evaluation_capable,
            "graph_claim_enabled": False,
            "official_evaluation_implemented": True,
            "official_evaluation_executed": False,
            "available_evaluation": (
                "official-prompt-port-unexecuted-plus-strict-exact-diagnostic"
            ),
        }

    @staticmethod
    def _validate_row(row: dict[str, Any], *, index: int) -> None:
        for field in ("question", "question_type", "question_date"):
            value = row.get(field)
            if not isinstance(value, str) or not value.strip():
                raise PublicMemorySourceError(
                    f"LongMemEval row {index} has invalid {field}"
                )
        _answer_text(row.get("answer"))
        sessions = row.get("haystack_sessions")
        session_ids = row.get("haystack_session_ids")
        session_dates = row.get("haystack_dates")
        if not all(isinstance(value, list) for value in (sessions, session_ids, session_dates)):
            raise PublicMemorySourceError(
                f"LongMemEval row {index} has invalid haystack arrays"
            )
        if not sessions or not (len(sessions) == len(session_ids) == len(session_dates)):
            raise PublicMemorySourceError(
                f"LongMemEval row {index} has misaligned haystack arrays"
            )
        non_empty_turns = 0
        for session_index, session in enumerate(sessions):
            if not isinstance(session_ids[session_index], str) or not isinstance(
                session_dates[session_index], str
            ):
                raise PublicMemorySourceError(
                    f"LongMemEval row {index} has invalid session identity"
                )
            if not isinstance(session, list):
                raise PublicMemorySourceError(
                    f"LongMemEval row {index} session {session_index} must be a list"
                )
            for turn in session:
                if not isinstance(turn, dict) or turn.get("role") not in {
                    "user",
                    "assistant",
                }:
                    raise PublicMemorySourceError(
                        f"LongMemEval row {index} has an invalid turn"
                    )
                content = turn.get("content")
                if not isinstance(content, str):
                    raise PublicMemorySourceError(
                        f"LongMemEval row {index} has non-text turn content"
                    )
                non_empty_turns += int(bool(content.strip()))
        if non_empty_turns == 0:
            raise PublicMemorySourceError(
                f"LongMemEval row {index} has no candidate-eligible turns"
            )

    def ids(self) -> tuple[str, ...]:
        return self._ids

    def load(self, task_id: str) -> MemoryTask:
        try:
            row = self._rows[task_id]
            raw_id = self._raw_ids[task_id]
        except KeyError as exc:
            raise KeyError(f"unknown LongMemEval task id: {task_id}") from exc
        return self._convert(task_id, raw_id, row)

    def evaluation_reference(self, task_id: str) -> dict[str, str | bool]:
        """Return the sealed benchmark-side fields needed by offline evaluation.

        This method is deliberately separate from :meth:`load`: the causal runtime
        receives only the sealed ``MemoryTask``.  Judge preparation happens after
        collection and may read the future question, reference answer, and native
        question type without making them available to a memory policy.
        """

        try:
            row = self._rows[task_id]
            raw_id = self._raw_ids[task_id]
        except KeyError as exc:
            raise KeyError(f"unknown LongMemEval task id: {task_id}") from exc
        return {
            "question_id": raw_id,
            "question_type": row["question_type"],
            "question": row["question"].strip(),
            "answer": _answer_text(row["answer"]),
            "abstention": "_abs" in raw_id,
        }

    def transport_panel_receipt(self) -> dict[str, Any]:
        """Seal derivation diagnostics for the non-claiming 32-task smoke panel."""

        if self.artifact_role != LONGMEMEVAL_RETRIEVAL_ARTIFACT_ROLE:
            raise PublicMemorySourceError(
                "transport panel must be derived from the full-haystack artifact"
            )
        if self.provenance["task_selection"] != "all-tasks":
            raise PublicMemorySourceError(
                "transport panel derivation requires the complete source artifact"
            )
        derived = derive_longmemeval_transport_panel(tuple(self._rows.values()))
        if derived != LONGMEMEVAL_SCREEN32_RAW_TASK_IDS:
            raise PublicMemorySourceError(
                "registered transport panel differs from deterministic derivation"
            )
        selected = [
            self._rows[
                f"longmemeval-{_safe_id(raw_id, fallback='unreachable')}"
            ]
            for raw_id in derived
        ]
        question_type_counts = Counter(row["question_type"] for row in selected)
        session_counts: Counter[str] = Counter()
        for row in selected:
            session_counts.update(set(row["haystack_session_ids"]))
        return {
            "version": LONGMEMEVAL_TRANSPORT_PANEL_VERSION,
            "seed": LONGMEMEVAL_TRANSPORT_PANEL_SEED,
            "purpose": "transport-and-safety-smoke-not-scientific-benchmark",
            "task_count": len(derived),
            "raw_task_ids": list(derived),
            "raw_task_ids_sha256": hashlib.sha256(
                json.dumps(list(derived), separators=(",", ":")).encode()
            ).hexdigest(),
            "question_type_counts": dict(sorted(question_type_counts.items())),
            "abstention_count": sum("_abs" in value for value in derived),
            "shared_session_count": sum(count > 1 for count in session_counts.values()),
            "quotas": [
                {
                    "question_type": question_type,
                    "abstention": abstention,
                    "count": count,
                }
                for question_type, abstention, count in LONGMEMEVAL_TRANSPORT_PANEL_QUOTAS
            ],
        }

    def _candidate_position(self, raw_id: str, count: int) -> int:
        digest = hashlib.sha256(
            (
                f"{self.adapter_version}:{self.dataset_revision}:"
                f"{self.candidate_seed}:{raw_id}"
            ).encode()
        ).digest()
        return int.from_bytes(digest[:8], "big") % count

    def _convert(
        self,
        task_id: str,
        raw_id: str,
        row: dict[str, Any],
    ) -> MemoryTask:
        sessions = [
            (source_index, session_id, session_date, session)
            for source_index, (session_id, session_date, session) in enumerate(
                zip(
                    row["haystack_session_ids"],
                    row["haystack_dates"],
                    row["haystack_sessions"],
                    strict=True,
                )
            )
        ]
        if self.session_order == "chronological":
            sessions = sorted(
                sessions,
                key=lambda item: _timestamp_key(item[2], item[0]),
            )
        session_id_counts = Counter(row["haystack_session_ids"])
        turns: list[tuple[str, str, str, str, str]] = []
        candidate_eligible_positions: list[int] = []
        for source_index, session_id, session_date, session in sessions:
            occurrence_identity = session_id
            if session_id_counts[session_id] > 1:
                occurrence_identity = f"{session_id}\0{session_date}\0{source_index}"
            entity_id = (
                "session-"
                f"{hashlib.sha256(occurrence_identity.encode()).hexdigest()[:16]}"
            )
            for turn in session:
                raw_content = turn["content"]
                candidate_eligible = bool(raw_content.strip())
                preserve_empty_user_turn = (
                    self.text_normalization == "verbatim"
                    and turn["role"] == "user"
                )
                if candidate_eligible or preserve_empty_user_turn:
                    content = (
                        raw_content
                        if self.text_normalization == "verbatim"
                        else raw_content.strip()
                    )
                    if candidate_eligible:
                        candidate_eligible_positions.append(len(turns))
                    turns.append(
                        (session_id, session_date, entity_id, turn["role"], content)
                    )
        candidate_position = candidate_eligible_positions[
            self._candidate_position(raw_id, len(candidate_eligible_positions))
        ]
        task_digest = hashlib.sha256(raw_id.encode()).hexdigest()[:16]
        events: list[MemoryEvent] = []
        for step, (session_id, session_date, entity_id, role, content) in enumerate(
            turns
        ):
            event_id = f"lme-{task_digest}-{step:04d}"
            events.append(
                MemoryEvent(
                    event_id=event_id,
                    step=step,
                    kind=EventKind.WRITE,
                    entity_id=entity_id,
                    key=role,
                    value=content,
                    source_quality=0.5,
                    contradiction_count=0,
                    record_cost=max(1, math.ceil(len(content.encode()) / 4)),
                    graph_degree=0,
                    proactive_hint=False,
                    candidate=step == candidate_position,
                    untrusted=True,
                    metadata={
                        "role": role,
                        "session_date": session_date,
                        "source_session_sha256": hashlib.sha256(
                            session_id.encode()
                        ).hexdigest(),
                    },
                )
            )
        query_step = len(events)
        events.append(
            MemoryEvent(
                event_id=f"lme-{task_digest}-query",
                step=query_step,
                kind=EventKind.QUERY,
                entity_id="benchmark-question",
                key="question",
                metadata={
                    "question_type": row["question_type"],
                    "question_date": row["question_date"],
                    "dataset_question_sha256": hashlib.sha256(raw_id.encode()).hexdigest(),
                },
            )
        )
        question_type = row["question_type"]
        stratum = self.stratum
        source_family = hashlib.sha256(
            "\n".join(sorted(row["haystack_session_ids"])).encode()
        ).hexdigest()[:12]
        group_type = _safe_id(question_type, fallback="unknown").lower()
        payload = {
            "schema_version": "1.0",
            "source_schema_version": self.adapter_version,
            "task_id": task_id,
            "group_id": f"longmemeval-{group_type}-{source_family}",
            "session_id": f"longmemeval-{task_digest}",
            "stratum": stratum,
            "events": tuple(events),
            "candidate_id": events[candidate_position].event_id,
            "write_step": candidate_position,
            "eligibility_step": query_step,
            "total_steps": len(events),
            "query": row["question"].strip(),
            "oracle": MemoryOracle(
                mode="answer",
                lookup_key="answer",
                expected_value=_answer_text(row["answer"]),
            ),
            "budget": self.budget,
            "suffix_variant_id": "primary",
        }
        return seal_task(payload)
