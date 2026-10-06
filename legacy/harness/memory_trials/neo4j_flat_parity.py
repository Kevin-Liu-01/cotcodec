"""Frozen identical-tuple fixtures for the Neo4j-versus-flat traversal doctor."""

from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Any

TOKEN_RE = re.compile(r"[a-z0-9]+")
VECTOR_DIMENSIONS = 16
RRF_K = 60


@dataclass(frozen=True)
class FrozenTuple:
    case_id: str
    tuple_id: str
    subject: str
    relation: str
    object: str
    text: str
    vector: tuple[float, ...]


@dataclass(frozen=True)
class FrozenCase:
    case_id: str
    start: str
    first_relation: str
    second_relation: str
    target_tuple_id: str
    query: str
    tuples: tuple[FrozenTuple, ...]
    shuffled_objects: tuple[tuple[str, str], ...]


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(TOKEN_RE.findall(text.lower()))


def stable_vector(text: str) -> tuple[float, ...]:
    """Return a deterministic non-model vector derived only from visible text."""

    values = [0.0] * VECTOR_DIMENSIONS
    for token in _tokens(text):
        digest = hashlib.sha256(token.encode()).digest()
        index = int.from_bytes(digest[:2], "big") % VECTOR_DIMENSIONS
        sign = 1.0 if digest[2] & 1 else -1.0
        values[index] += sign * (1.0 + digest[3] / 255.0)
    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return tuple(round(value / norm, 12) for value in values)


def _tuple(
    case_id: str,
    tuple_id: str,
    subject: str,
    relation: str,
    object_: str,
) -> FrozenTuple:
    text = f"subject {subject} relation {relation} object {object_}"
    return FrozenTuple(
        case_id=case_id,
        tuple_id=tuple_id,
        subject=subject,
        relation=relation,
        object=object_,
        text=text,
        vector=stable_vector(text),
    )


def build_frozen_cases(count: int = 48) -> tuple[FrozenCase, ...]:
    if count <= 0:
        raise ValueError("case count must be positive")
    cases: list[FrozenCase] = []
    for index in range(count):
        case_id = f"case-{index:03d}"
        start = f"start-{index:03d}"
        bridge = f"bridge-{index:03d}"
        first_relation = f"route-a-{index % 6}"
        second_relation = f"route-b-{index % 6}"
        target = f"terminal-{index:03d}"
        rows = [
            _tuple(
                case_id,
                f"{case_id}-tuple-m-first",
                start,
                first_relation,
                bridge,
            ),
            _tuple(
                case_id,
                f"{case_id}-tuple-z-target",
                bridge,
                second_relation,
                target,
            ),
        ]
        # Relation-matched decoys sort before the true second hop in the flat arm.
        for decoy in range(8):
            decoy_subject = (
                f"decoy-bridge-{index:03d}-00" if decoy == 0 else start
            )
            rows.append(
                _tuple(
                    case_id,
                    f"{case_id}-tuple-a-decoy-{decoy:02d}",
                    decoy_subject,
                    second_relation,
                    f"decoy-terminal-{index:03d}-{decoy:02d}",
                )
            )
        for decoy in range(4):
            rows.append(
                _tuple(
                    case_id,
                    f"{case_id}-tuple-b-noise-{decoy:02d}",
                    start,
                    f"noise-{decoy}",
                    (
                        f"decoy-bridge-{index:03d}-00"
                        if decoy == 0
                        else f"noise-object-{index:03d}-{decoy:02d}"
                    ),
                )
            )
        rows.sort(key=lambda row: row.tuple_id)
        shuffled_by_id = {row.tuple_id: row.object for row in rows}
        first_id = f"{case_id}-tuple-m-first"
        noise_id = f"{case_id}-tuple-b-noise-00"
        shuffled_by_id[first_id], shuffled_by_id[noise_id] = (
            shuffled_by_id[noise_id],
            shuffled_by_id[first_id],
        )
        shuffled_objects = tuple(
            (row.tuple_id, shuffled_by_id[row.tuple_id]) for row in rows
        )
        query = (
            f"from {start} follow {first_relation} then {second_relation} "
            "and return the terminal evidence"
        )
        cases.append(
            FrozenCase(
                case_id=case_id,
                start=start,
                first_relation=first_relation,
                second_relation=second_relation,
                target_tuple_id=f"{case_id}-tuple-z-target",
                query=query,
                tuples=tuple(rows),
                shuffled_objects=shuffled_objects,
            )
        )
    return tuple(cases)


def canonical_tuple_payload(cases: Iterable[FrozenCase]) -> bytes:
    rows = [asdict(row) for case in cases for row in case.tuples]
    return (json.dumps(rows, sort_keys=True, separators=(",", ":")) + "\n").encode()


def create_flat_database(cases: Iterable[FrozenCase]) -> sqlite3.Connection:
    database = sqlite3.connect(":memory:")
    database.execute(
        """
        CREATE TABLE tuples (
            case_id TEXT NOT NULL,
            tuple_id TEXT PRIMARY KEY,
            subject TEXT NOT NULL,
            relation TEXT NOT NULL,
            object TEXT NOT NULL,
            text TEXT NOT NULL,
            vector_json TEXT NOT NULL
        )
        """
    )
    database.executemany(
        "INSERT INTO tuples VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (
                row.case_id,
                row.tuple_id,
                row.subject,
                row.relation,
                row.object,
                row.text,
                json.dumps(row.vector, separators=(",", ":")),
            )
            for case in cases
            for row in case.tuples
        ],
    )
    database.commit()
    return database


def _cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def flat_bm25_dense_rank(
    database: sqlite3.Connection,
    case: FrozenCase,
    *,
    top_k: int = 2,
) -> tuple[str, ...]:
    """Rank one flat case with one SQLite read and deterministic BM25+dense RRF."""

    rows = database.execute(
        "SELECT tuple_id, text, vector_json FROM tuples WHERE case_id = ? ORDER BY tuple_id",
        (case.case_id,),
    ).fetchall()
    documents = [(row[0], _tokens(row[1]), tuple(json.loads(row[2]))) for row in rows]
    query_tokens = _tokens(case.query)
    query_counts = Counter(query_tokens)
    document_frequency = Counter(
        token for _, tokens, _ in documents for token in set(tokens)
    )
    average_length = sum(len(tokens) for _, tokens, _ in documents) / len(documents)
    lexical_scores: dict[str, float] = {}
    dense_scores: dict[str, float] = {}
    query_vector = stable_vector(case.query)
    for tuple_id, tokens, vector in documents:
        counts = Counter(tokens)
        score = 0.0
        for token, query_weight in query_counts.items():
            frequency = counts[token]
            if not frequency:
                continue
            frequency_docs = document_frequency[token]
            inverse_document_frequency = math.log(
                1.0 + (len(documents) - frequency_docs + 0.5) / (frequency_docs + 0.5)
            )
            denominator = frequency + 1.2 * (
                1.0 - 0.75 + 0.75 * len(tokens) / average_length
            )
            score += query_weight * inverse_document_frequency * frequency * 2.2 / denominator
        lexical_scores[tuple_id] = score
        dense_scores[tuple_id] = _cosine(query_vector, vector)
    lexical = sorted(lexical_scores, key=lambda key: (-lexical_scores[key], key))
    dense = sorted(dense_scores, key=lambda key: (-dense_scores[key], key))
    rrf = {tuple_id: 0.0 for tuple_id, _, _ in documents}
    for ranking in (lexical, dense):
        for rank, tuple_id in enumerate(ranking, start=1):
            rrf[tuple_id] += 1.0 / (RRF_K + rank)
    return tuple(sorted(rrf, key=lambda key: (-rrf[key], key))[:top_k])


def flat_sql_join_rank(
    database: sqlite3.Connection,
    case: FrozenCase,
    *,
    top_k: int = 2,
) -> tuple[str, ...]:
    """Strong flat ceiling: one relational join over the same tuple rows."""

    row = database.execute(
        """
        SELECT first.tuple_id, second.tuple_id
        FROM tuples AS first
        JOIN tuples AS second
          ON first.case_id = second.case_id AND first.object = second.subject
        WHERE first.case_id = ? AND first.subject = ?
          AND first.relation = ? AND second.relation = ?
        ORDER BY first.tuple_id, second.tuple_id
        LIMIT 1
        """,
        (case.case_id, case.start, case.first_relation, case.second_relation),
    ).fetchone()
    return tuple(row[:top_k]) if row else ()


def validate_fixture(cases: tuple[FrozenCase, ...], *, top_k: int = 2) -> dict[str, Any]:
    database = create_flat_database(cases)
    try:
        flat = [flat_bm25_dense_rank(database, case, top_k=top_k) for case in cases]
        joins = [flat_sql_join_rank(database, case, top_k=top_k) for case in cases]
    finally:
        database.close()
    flat_hits = sum(
        case.target_tuple_id in result
        for case, result in zip(cases, flat, strict=True)
    )
    join_hits = sum(
        case.target_tuple_id in result
        for case, result in zip(cases, joins, strict=True)
    )
    payload = canonical_tuple_payload(cases)
    return {
        "case_count": len(cases),
        "tuple_count": sum(len(case.tuples) for case in cases),
        "tuple_payload_bytes": len(payload),
        "tuple_payload_sha256": hashlib.sha256(payload).hexdigest(),
        "flat_hits": flat_hits,
        "flat_join_hits": join_hits,
        "top_k": top_k,
    }
