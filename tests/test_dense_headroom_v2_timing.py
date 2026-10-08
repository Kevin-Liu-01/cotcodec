"""The development timing job's registered order of units (torch-free)."""

from __future__ import annotations

from dataclasses import dataclass

from harness import dense_headroom_data as dhd
from harness import dense_headroom_v2 as dv2


@dataclass(frozen=True)
class _Unit:
    unit_id: str
    stage: str


def _lane_units() -> list[_Unit]:
    counts = {"A-main": 440, "B-absent": 280, "C-literal": 160, "D-nohaystack": 280}
    return [_Unit(f"{stage}-{i}", stage) for stage, n in counts.items() for i in range(n)]


def test_the_subset_is_the_first_two_chunks_of_every_stage_round_robin() -> None:
    subset, rest = dv2.timing_order(_lane_units(), dhd.STAGES)
    assert [(stage, index) for stage, index, _ in subset] == [
        ("A-main", 0), ("B-absent", 0), ("C-literal", 0), ("D-nohaystack", 0),
        ("A-main", 1), ("B-absent", 1), ("C-literal", 1), ("D-nohaystack", 1)]
    assert sum(len(chunk) for _, _, chunk in subset) == 128
    assert all(len(chunk) == 16 for _, _, chunk in subset)
    # The lane's own chunking: the subset's chunks are the lane's first chunks.
    a0 = subset[0][2]
    assert [u.unit_id for u in a0] == [f"A-main-{i}" for i in range(16)]
    every = subset + rest
    assert len(every) == 28 + 18 + 10 + 18 == 74  # job 727's chunk count (74, not 73)
    assert sorted(u.unit_id for _, _, c in every for u in c) == sorted(
        u.unit_id for u in _lane_units())
    assert rest[0][:2] == ("A-main", 2) and rest[3][:2] == ("D-nohaystack", 2)
