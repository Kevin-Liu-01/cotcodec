"""Family-stratified per-substrate cap, and the frozen dev/test split.

Cap (default 40 per substrate). Distinct mutants are stratified by family and,
within a family, by operator. Slots are allocated by water-filling: every
present family gets an equal share, capped at what it has; unused slots are
redistributed equally among families that still have mutants; the same is
done across operators inside a family. Inside an operator stratum the kept
mutants are a simple random sample drawn with a seeded RNG over the
content-sorted stratum. The inclusion probability of a mutant is therefore
exactly ``k_op / n_op``, and its Horvitz-Thompson weight ``n_op / k_op``
recovers the natural (uncapped) family mix in pooled rates.

Split. Each kept mutant is assigned to ``dev`` or ``test`` by one bit of
``sha256("q1-mutant-split/v1/seed=<seed>/<substrate_id>/<dedup_hash>")``. The
assignment depends only on the mutant's content and the declared seed, never
on which other mutants exist, so adding a substrate never moves a mutant
between halves. A secondary problem-level split uses the same construction
on ``problem_id``.
"""

from __future__ import annotations

import hashlib
import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TypeVar

from harness.q1.mutate.operators._base import FAMILIES

T = TypeVar("T")

DEFAULT_CAP = 40
DEFAULT_SEED = 42
SPLIT_VERSION = "v1"
#: The split is frozen at seed 42 whatever cap seed draws the sample, so a
#: mutant kept by the seed-43 or seed-44 alternate sample has the same half.
SPLIT_SEED = 42


def waterfill(capacities: Sequence[int], total: int) -> list[int]:
    """Equal shares capped by capacity; leftovers go to the largest remaining capacity.

    Deterministic: ties are broken by position.
    """
    alloc = [0] * len(capacities)
    remaining = min(total, sum(capacities))
    while remaining > 0:
        open_slots = [i for i, cap in enumerate(capacities) if alloc[i] < cap]
        share = remaining // len(open_slots)
        if share == 0:
            spare = sorted(open_slots, key=lambda i: (-(capacities[i] - alloc[i]), i))
            for i in spare[:remaining]:
                alloc[i] += 1
            break
        for i in open_slots:
            give = min(share, capacities[i] - alloc[i])
            alloc[i] += give
            remaining -= give
    return alloc


def _rng(*parts: object) -> random.Random:
    digest = hashlib.sha256("/".join(map(str, parts)).encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


@dataclass(frozen=True)
class Selection:
    """A kept mutant with its sampling metadata."""

    item: object
    family: str
    operator: str
    n_operator_stratum: int
    k_operator_stratum: int

    @property
    def inclusion_probability(self) -> float:
        return self.k_operator_stratum / self.n_operator_stratum

    @property
    def weight(self) -> float:
        return self.n_operator_stratum / self.k_operator_stratum


def stratified_cap(
    items: Sequence[T],
    *,
    family: Callable[[T], str],
    operator: Callable[[T], str],
    content_key: Callable[[T], str],
    substrate_id: str,
    cap: int = DEFAULT_CAP,
    seed: int = DEFAULT_SEED,
) -> list[Selection]:
    """Keep at most ``cap`` items, stratified by family then operator."""
    if cap < 1:
        raise ValueError("cap must be positive")
    by_family: dict[str, dict[str, list[T]]] = {}
    for item in items:
        fam = family(item)
        if fam not in FAMILIES:
            raise ValueError(f"unknown family {fam!r}")
        by_family.setdefault(fam, {}).setdefault(operator(item), []).append(item)
    families = [f for f in FAMILIES if f in by_family]
    family_sizes = [sum(len(v) for v in by_family[f].values()) for f in families]
    family_alloc = waterfill(family_sizes, cap)
    selected: list[Selection] = []
    for fam, slots in zip(families, family_alloc, strict=True):
        operators = sorted(by_family[fam])
        sizes = [len(by_family[fam][op]) for op in operators]
        for op, k, n in zip(operators, waterfill(sizes, slots), sizes, strict=True):
            if k == 0:
                continue
            stratum = sorted(by_family[fam][op], key=content_key)
            kept = _rng("q1-mutant-cap", seed, substrate_id, fam, op).sample(stratum, k)
            kept.sort(key=content_key)
            selected.extend(Selection(item, fam, op, n, k) for item in kept)
    return selected


def split_of(substrate_id: str, dedup_hash: str, seed: int = SPLIT_SEED) -> str:
    """Frozen mutant-level dev/test assignment."""
    key = f"q1-mutant-split/{SPLIT_VERSION}/seed={seed}/{substrate_id}/{dedup_hash}"
    return "dev" if hashlib.sha256(key.encode()).digest()[0] & 1 == 0 else "test"


def problem_split_of(problem_id: str, seed: int = SPLIT_SEED) -> str:
    """Secondary problem-level dev/test assignment (all mutants of a problem together)."""
    key = f"q1-problem-split/{SPLIT_VERSION}/seed={seed}/{problem_id}"
    return "dev" if hashlib.sha256(key.encode()).digest()[0] & 1 == 0 else "test"
