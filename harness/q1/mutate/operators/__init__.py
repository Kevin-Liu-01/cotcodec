"""The operator registry, in enumeration order (schema family order).

Enumeration order matters only for deduplication: when two operators produce
the same mutant, the earlier operator keeps it and the later one is recorded
as a duplicate.
"""

from __future__ import annotations

import hashlib
import json

from harness.q1.mutate.operators import (
    arithmetic,
    boundary,
    indexing,
    precision,
    semantic,
    synchronization,
)
from harness.q1.mutate.operators._base import (
    FAMILIES,
    Candidate,
    Operator,
    ScopeContext,
)

OPERATORS: tuple[Operator, ...] = (
    *arithmetic.OPERATORS,
    *indexing.OPERATORS,
    *semantic.OPERATORS,
    *boundary.OPERATORS,
    *synchronization.OPERATORS,
    *precision.OPERATORS,
)

OPERATORS_BY_NAME: dict[str, Operator] = {op.name: op for op in OPERATORS}
if len(OPERATORS_BY_NAME) != len(OPERATORS):  # pragma: no cover - import-time guard
    raise RuntimeError("duplicate operator names in the registry")


def registry_table() -> list[dict[str, object]]:
    """JSON-ready operator table (name, family, origin, rules, scopes, description)."""
    return [op.table_row() for op in OPERATORS]


def registry_fingerprint() -> str:
    """SHA-256 of the canonical operator table; changes when any operator's metadata does."""
    payload = json.dumps(registry_table(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


__all__ = [
    "FAMILIES",
    "OPERATORS",
    "OPERATORS_BY_NAME",
    "Candidate",
    "Operator",
    "ScopeContext",
    "registry_fingerprint",
    "registry_table",
]
