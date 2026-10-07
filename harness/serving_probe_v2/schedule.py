"""Launch-window ledger: reserved time for required points; reruns and optional points from slack.

In serving-throughput-probe-v1 an invalid point was rerun at once, and the two
reruns of r3 and r4 (about 9.8 minutes) used the real phase's launch window, so
six later points were never launched. v2 keeps a ledger instead:

* Every phase reserves its start allowance (G0.8 and the engine start) plus the
  wall caps of its required points; the contract loader refuses a job whose
  preamble and reserved phases do not fit before the soft stop.
* A phase may launch work until its bound: the soft stop minus the reserved time
  of every later phase. A required point's first attempt launches whenever the
  bound has not passed; the point is truncated at its cap or at the phase's hard
  deadline.
* Everything else (a rerun, which every point gets at most once, and an optional
  point) launches only from slack: now + its cap + the caps of the phase's
  required points still to run must fit before the bound. A rerun therefore
  never takes time a required point owns, and reruns run after every required
  first attempt of their phase.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

FIRST, RERUN, OPTIONAL = "required-first-attempt", "rerun", "optional"


@dataclass(frozen=True)
class PhaseBudget:
    phase_id: str
    start_minutes: float
    required_caps: dict[str, float]

    @property
    def reserved_minutes(self) -> float:
        return self.start_minutes + sum(self.required_caps.values())


class LaunchLedger:
    """Soft stop, per-phase bounds and the slack rule (times on ``time.perf_counter``)."""

    def __init__(
        self,
        *,
        start: float,
        allocation_minutes: float,
        soft_fraction: float,
        hard_margin_minutes: float,
        phases: Sequence[PhaseBudget],
    ) -> None:
        self.start = start
        self.soft = start + soft_fraction * allocation_minutes * 60.0
        self.hard = start + (allocation_minutes - hard_margin_minutes) * 60.0
        self.phases = list(phases)
        self.decisions: list[dict[str, Any]] = []

    def later_reserve_s(self, index: int) -> float:
        return 60.0 * sum(phase.reserved_minutes for phase in self.phases[index + 1 :])

    def bound(self, index: int) -> float:
        """No launch in phase ``index`` at or after this time."""
        return self.soft - self.later_reserve_s(index)

    def hard_deadline(self, index: int) -> float:
        """A running point of phase ``index`` is truncated here (later phases keep theirs)."""
        return self.bound(index) if self.later_reserve_s(index) > 0 else self.hard

    def required_left_s(self, index: int, pending: Sequence[str]) -> float:
        caps = self.phases[index].required_caps
        return 60.0 * sum(caps[point] for point in pending if point in caps)

    def may_launch(
        self,
        index: int,
        *,
        now: float,
        point_id: str,
        kind: str,
        cap_minutes: float,
        required_pending: Sequence[str] = (),
    ) -> bool:
        """Whether ``point_id`` may launch now; every decision is recorded.

        ``kind`` is FIRST (a required point's first attempt: before the bound),
        RERUN or OPTIONAL (from slack: its cap plus the required caps still pending
        must fit before the bound).
        """
        bound = self.bound(index)
        if kind == FIRST:
            allowed = now < bound
            needed = 0.0
        else:
            needed = 60.0 * cap_minutes + self.required_left_s(index, required_pending)
            allowed = now + needed <= bound
        self.decisions.append(
            {
                "phase": self.phases[index].phase_id,
                "point": point_id,
                "kind": kind,
                "at_s": round(now - self.start, 3),
                "bound_s": round(bound - self.start, 3),
                "needed_s": round(needed, 3),
                "launched": bool(allowed),
            }
        )
        return bool(allowed)

    def deadline(self, index: int, *, now: float, cap_minutes: float) -> float:
        return min(now + 60.0 * cap_minutes, self.hard_deadline(index))

    def describe(self) -> dict[str, Any]:
        return {
            "soft_after_start_s": self.soft - self.start,
            "hard_after_start_s": self.hard - self.start,
            "phases": [
                {
                    "phase": phase.phase_id,
                    "reserved_minutes": phase.reserved_minutes,
                    "start_minutes": phase.start_minutes,
                    "required_caps": dict(phase.required_caps),
                    "bound_after_start_s": self.bound(index) - self.start,
                    "hard_after_start_s": self.hard_deadline(index) - self.start,
                }
                for index, phase in enumerate(self.phases)
            ],
        }
