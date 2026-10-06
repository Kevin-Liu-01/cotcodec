"""Clean-room MemoryBank decay and retrieval-strengthening control.

The historical implementation writes ``exp(-t / 5 * strength)``. Python
evaluates that as ``exp(-(t / 5) * strength)``, so increasing strength makes a
memory decay faster. This module preregisters the intended monotonic formula,
``exp(-t / (5 * strength))``, and retains the upstream-precedence expression as
an explicit negative control. It imports no upstream code.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

DecayFormula = Literal["corrected", "upstream-precedence", "no-decay"]


@dataclass(frozen=True, slots=True)
class DecayCandidate:
    """Past-only candidate features used by the deterministic control."""

    item_id: str
    elapsed_steps: float
    prior_accesses: int
    query_overlap: int

    def __post_init__(self) -> None:
        if not self.item_id:
            raise ValueError("item_id cannot be empty")
        if not math.isfinite(self.elapsed_steps) or self.elapsed_steps < 0:
            raise ValueError("elapsed_steps must be finite and nonnegative")
        if self.prior_accesses < 0:
            raise ValueError("prior_accesses must be nonnegative")
        if self.query_overlap < 0:
            raise ValueError("query_overlap must be nonnegative")

    @property
    def strength(self) -> float:
        return float(1 + self.prior_accesses)


@dataclass(frozen=True, slots=True)
class ScoredDecayCandidate:
    item_id: str
    retention_probability: float
    strength: float
    score: float


def retention_probability(
    elapsed_steps: float,
    strength: float,
    *,
    time_scale: float = 5.0,
    formula: DecayFormula = "corrected",
) -> float:
    """Return an exact finite retention weight in ``[0, 1]``."""

    if not math.isfinite(elapsed_steps) or elapsed_steps < 0:
        raise ValueError("elapsed_steps must be finite and nonnegative")
    if not math.isfinite(strength) or strength <= 0:
        raise ValueError("strength must be finite and positive")
    if not math.isfinite(time_scale) or time_scale <= 0:
        raise ValueError("time_scale must be finite and positive")
    if formula == "corrected":
        exponent = -elapsed_steps / (time_scale * strength)
    elif formula == "upstream-precedence":
        exponent = -(elapsed_steps / time_scale) * strength
    elif formula == "no-decay":
        exponent = 0.0
    else:
        raise ValueError(f"unsupported decay formula: {formula}")
    return math.exp(exponent)


def score_candidates(
    candidates: tuple[DecayCandidate, ...],
    *,
    formula: DecayFormula = "corrected",
    time_scale: float = 5.0,
) -> tuple[ScoredDecayCandidate, ...]:
    """Rank past-only candidates by relevance times retention, stably by ID."""

    if len({candidate.item_id for candidate in candidates}) != len(candidates):
        raise ValueError("candidate item IDs must be unique")
    scored = []
    for candidate in candidates:
        retention = retention_probability(
            candidate.elapsed_steps,
            candidate.strength,
            time_scale=time_scale,
            formula=formula,
        )
        scored.append(
            ScoredDecayCandidate(
                item_id=candidate.item_id,
                retention_probability=retention,
                strength=candidate.strength,
                score=float(1 + candidate.query_overlap) * retention,
            )
        )
    return tuple(sorted(scored, key=lambda item: (-item.score, item.item_id)))
