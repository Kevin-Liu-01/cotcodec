"""Natural-session topology retrieval over one immutable LongMemEval panel.

The public interface deliberately freezes one source-derived panel and one set
of ranked evidence IDs.  Neo4j and SQLite adapters consume the same cases; they
do not own panel selection, lexical scoring, or the outcome definition.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

TOKEN_RE = re.compile(r"[a-z0-9]+")
VECTOR_DIMENSIONS = 64
RRF_K = 60
LONGMEMEVAL_DATASET_REVISION = "98d7416c24c778c2fee6e6f3006e7a073259d48f"
LONGMEMEVAL_S_SHA256 = (
    "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442"
)
LONGMEMEVAL_S_SIZE = 277_383_467
PANEL_SEED = 20260815
PANEL_TYPES = ("knowledge-update", "temporal-reasoning")
QUESTIONS_PER_TYPE = 32
TOP_K = 4
SEED_K = 2
SHUFFLE_SEEDS = (42, 43, 44)


@dataclass(frozen=True)
class NaturalSession:
    session_id: str
    position: int
    date: str
    text: str
    vector: tuple[float, ...]


@dataclass(frozen=True)
class NaturalCase:
    question_id: str
    question_type: str
    question: str
    answer: str
    answer_session_ids: tuple[str, ...]
    sessions: tuple[NaturalSession, ...]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(TOKEN_RE.findall(text.lower()))


def stable_vector(text: str) -> tuple[float, ...]:
    """Return a deterministic, model-free text projection for the audit lane."""

    values = [0.0] * VECTOR_DIMENSIONS
    for token in _tokens(text):
        digest = hashlib.sha256(token.encode()).digest()
        index = int.from_bytes(digest[:2], "big") % VECTOR_DIMENSIONS
        sign = 1.0 if digest[2] & 1 else -1.0
        values[index] += sign * (1.0 + digest[3] / 255.0)
    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return tuple(round(value / norm, 12) for value in values)


def _session_text(turns: Sequence[Mapping[str, Any]]) -> str:
    rendered: list[str] = []
    for turn in turns:
        role = turn.get("role")
        content = turn.get("content")
        if role not in {"user", "assistant"} or not isinstance(content, str):
            raise ValueError("LongMemEval session contains an invalid turn")
        rendered.append(f"{role}: {content.strip()}")
    if not rendered:
        raise ValueError("LongMemEval session must not be empty")
    return "\n".join(rendered)


def _answer_text(value: Any) -> str:
    if isinstance(value, str):
        rendered = value.strip()
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("LongMemEval answer must be finite")
        rendered = str(value)
    else:
        raise ValueError("LongMemEval answer must be text or numeric")
    if not rendered:
        raise ValueError("LongMemEval answer must be non-empty")
    return rendered


def _case_from_row(row: Mapping[str, Any]) -> NaturalCase:
    required_text = ("question_id", "question_type", "question")
    if any(not isinstance(row.get(key), str) or not row[key] for key in required_text):
        raise ValueError("LongMemEval row has an invalid text identity")
    session_ids = row.get("haystack_session_ids")
    session_dates = row.get("haystack_dates")
    raw_sessions = row.get("haystack_sessions")
    answer_session_ids = row.get("answer_session_ids")
    if not all(isinstance(value, list) for value in (
        session_ids,
        session_dates,
        raw_sessions,
        answer_session_ids,
    )):
        raise ValueError("LongMemEval row has malformed session arrays")
    if not session_ids or not (
        len(session_ids) == len(session_dates) == len(raw_sessions)
    ):
        raise ValueError("LongMemEval row has misaligned session arrays")
    if len(set(session_ids)) != len(session_ids):
        raise ValueError("LongMemEval row has duplicate session IDs")
    if not answer_session_ids or not all(
        isinstance(value, str) and value in session_ids for value in answer_session_ids
    ):
        raise ValueError("LongMemEval row has invalid answer-session labels")
    sessions: list[NaturalSession] = []
    for position, (session_id, date, turns) in enumerate(
        zip(session_ids, session_dates, raw_sessions, strict=True)
    ):
        if (
            not isinstance(session_id, str)
            or not session_id
            or not isinstance(date, str)
            or not isinstance(turns, list)
        ):
            raise ValueError("LongMemEval session identity is malformed")
        text = _session_text(turns)
        sessions.append(
            NaturalSession(
                session_id=session_id,
                position=position,
                date=date,
                text=text,
                vector=stable_vector(text),
            )
        )
    return NaturalCase(
        question_id=str(row["question_id"]),
        question_type=str(row["question_type"]),
        question=str(row["question"]),
        answer=_answer_text(row.get("answer")),
        answer_session_ids=tuple(answer_session_ids),
        sessions=tuple(sessions),
    )


def load_natural_panel(
    path: Path,
    *,
    expected_sha256: str = LONGMEMEVAL_S_SHA256,
    expected_size: int = LONGMEMEVAL_S_SIZE,
    seed: int = PANEL_SEED,
    questions_per_type: int = QUESTIONS_PER_TYPE,
) -> tuple[NaturalCase, ...]:
    """Load and deterministically freeze the two registered natural strata."""

    if path.is_symlink() or not path.is_file():
        raise ValueError("LongMemEval input must be a regular non-symlink file")
    if path.stat().st_size != expected_size or _sha256_file(path) != expected_sha256:
        raise ValueError("LongMemEval input size or digest drifted")
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("LongMemEval input is not valid JSON") from exc
    if not isinstance(rows, list):
        raise ValueError("LongMemEval input must be a list")
    selected: list[NaturalCase] = []
    seen: set[str] = set()
    for question_type in PANEL_TYPES:
        eligible = [
            row
            for row in rows
            if isinstance(row, dict)
            and row.get("question_type") == question_type
            and isinstance(row.get("question_id"), str)
            and not str(row["question_id"]).endswith("_abs")
        ]
        ranked = sorted(
            eligible,
            key=lambda row: hashlib.sha256(
                f"neo4j-natural-v1:{seed}:{row['question_id']}".encode()
            ).hexdigest(),
        )
        if len(ranked) < questions_per_type:
            raise ValueError(f"not enough LongMemEval rows for {question_type}")
        for row in ranked[:questions_per_type]:
            case = _case_from_row(row)
            if case.question_id in seen:
                raise ValueError("LongMemEval panel contains duplicate question IDs")
            seen.add(case.question_id)
            selected.append(case)
    return tuple(selected)


def canonical_case_payload(cases: Iterable[NaturalCase]) -> bytes:
    return (
        json.dumps(
            [asdict(case) for case in cases],
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode()


def flat_ranking(case: NaturalCase) -> tuple[str, ...]:
    """Rank every session with deterministic BM25+dense reciprocal-rank fusion."""

    query_tokens = _tokens(case.question)
    query_counts = Counter(query_tokens)
    documents = [
        (session.session_id, _tokens(session.text), session.vector)
        for session in case.sessions
    ]
    document_frequency = Counter(
        token for _, tokens, _ in documents for token in set(tokens)
    )
    average_length = sum(len(tokens) for _, tokens, _ in documents) / len(documents)
    lexical_scores: dict[str, float] = {}
    dense_scores: dict[str, float] = {}
    query_vector = stable_vector(case.question)
    for session_id, tokens, vector in documents:
        counts = Counter(tokens)
        score = 0.0
        for token, query_weight in query_counts.items():
            frequency = counts[token]
            if not frequency:
                continue
            frequency_docs = document_frequency[token]
            inverse_document_frequency = math.log(
                1.0
                + (len(documents) - frequency_docs + 0.5)
                / (frequency_docs + 0.5)
            )
            denominator = frequency + 1.2 * (
                1.0 - 0.75 + 0.75 * len(tokens) / average_length
            )
            score += (
                query_weight
                * inverse_document_frequency
                * frequency
                * 2.2
                / denominator
            )
        lexical_scores[session_id] = score
        dense_scores[session_id] = sum(
            left * right for left, right in zip(query_vector, vector, strict=True)
        )
    lexical = sorted(lexical_scores, key=lambda key: (-lexical_scores[key], key))
    dense = sorted(dense_scores, key=lambda key: (-dense_scores[key], key))
    fused = {session_id: 0.0 for session_id, _, _ in documents}
    for ranking in (lexical, dense):
        for rank, session_id in enumerate(ranking, start=1):
            fused[session_id] += 1.0 / (RRF_K + rank)
    return tuple(sorted(fused, key=lambda key: (-fused[key], key)))


def chronological_edges(case: NaturalCase) -> tuple[tuple[str, str], ...]:
    return tuple(
        (left.session_id, right.session_id)
        for left, right in zip(case.sessions, case.sessions[1:], strict=False)
    )


def shuffled_edges(case: NaturalCase, seed: int) -> tuple[tuple[str, str], ...]:
    ids = [session.session_id for session in case.sessions]
    middle = ids[1:-1]
    random.Random(f"neo4j-natural-v1:{seed}:{case.question_id}").shuffle(middle)
    ids = [ids[0], *middle, ids[-1]]
    return tuple(zip(ids, ids[1:], strict=False))


def expand_ranking(
    flat: Sequence[str],
    edges: Iterable[tuple[str, str]],
    *,
    top_k: int = TOP_K,
    seed_k: int = SEED_K,
) -> tuple[str, ...]:
    """Keep lexical seeds, then spend remaining slots on topology neighbors."""

    if top_k <= 0 or seed_k <= 0 or seed_k > top_k:
        raise ValueError("invalid topology expansion budget")
    neighbors: dict[str, set[str]] = {}
    for left, right in edges:
        neighbors.setdefault(left, set()).add(right)
        neighbors.setdefault(right, set()).add(left)
    rank = {session_id: index for index, session_id in enumerate(flat)}
    seeds = list(flat[:seed_k])
    candidates = {
        neighbor
        for seed in seeds
        for neighbor in neighbors.get(seed, ())
        if neighbor not in seeds
    }
    expanded = sorted(candidates, key=lambda session_id: (rank[session_id], session_id))
    result = seeds + expanded[: max(0, top_k - len(seeds))]
    if len(result) < top_k:
        result.extend(
            session_id
            for session_id in flat
            if session_id not in result
            for _ in (0,)
            if len(result) < top_k
        )
    return tuple(result)


def recall_all(case: NaturalCase, ranking: Sequence[str]) -> bool:
    return set(case.answer_session_ids).issubset(ranking)


def freeze_case_rankings(case: NaturalCase) -> dict[str, tuple[str, ...]]:
    flat = flat_ranking(case)
    result = {
        "flat_bm25_dense": tuple(flat[:TOP_K]),
        "true_topology": expand_ranking(flat, chronological_edges(case)),
    }
    for seed in SHUFFLE_SEEDS:
        result[f"shuffled_topology_seed_{seed}"] = expand_ranking(
            flat, shuffled_edges(case, seed)
        )
    return result
