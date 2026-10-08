"""Torch-free gate outcome records, conjunction rule, seeds and watchdog phases.

Split from ``common.py`` so the runner, journal, ``b_native`` and tests can
use them without importing torch.
"""

from __future__ import annotations

import contextlib
import math
import os
import traceback
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from harness.q1.schema import make_verdict_row

PHASE_FD_ENV = "Q1_PHASE_FD"
PHASES = ("compile", "correctness", "timing")


def report_phase(name: str) -> None:
    """Tell the runner's watchdog which phase this worker entered.

    Writes ``<name>\\n`` to the file descriptor in ``Q1_PHASE_FD`` when set
    (a pipe owned by the runner). Phases only move forward; the runner caps
    each at its own timeout, so a candidate that forges a phase message can at
    most move to a later phase with a bounded limit.
    """
    if name not in PHASES:
        raise ValueError(f"unknown phase {name}")
    fd = os.environ.get(PHASE_FD_ENV)
    if fd is None:
        return
    with contextlib.suppress(OSError):
        os.write(int(fd), f"{name}\n".encode())


def channel_seed(base: int, replicate_seed: int, index: int) -> int:
    """Seed for input draw ``index`` of a gate or audit channel.

    ``base`` is the channel's seed at replicate 42 and index 0 (c1: 1042, c2:
    2042, c3: 3042, A2: 4042, A3: 5042, A1 native draws: 6042, A5: 7042).
    Replicates 43 and 44 shift by 100, so draws never collide while index < 100.
    """
    if not 0 <= index < 100:
        raise ValueError("channel draw index must be in [0, 100)")
    return base + index + 100 * (replicate_seed - 42)


@dataclass
class GateOutcome:
    gate: str
    config_id: str
    verdict: str
    max_abs_err: float | None = None
    max_rel_err: float | None = None
    tolerance: float | None = None
    details: dict[str, Any] = field(default_factory=dict)
    wall_seconds: float = 0.0

    def to_row(
        self,
        kernel_id: str,
        *,
        tf32_policy: str = "torch-default",
        gpu_seconds: float | None = None,
        **optional: Any,
    ) -> dict[str, Any]:
        return make_verdict_row(
            kernel_id=kernel_id,
            gate=self.gate,
            config_id=self.config_id,
            verdict=self.verdict,
            tf32_policy=tf32_policy,
            max_abs_err=self.max_abs_err,
            max_rel_err=self.max_rel_err,
            tolerance=self.tolerance,
            gpu_seconds=self.wall_seconds if gpu_seconds is None else gpu_seconds,
            wall_seconds=self.wall_seconds,
            details=self.details,
            **optional,
        )


def worst(values: Sequence[float | None]) -> float | None:
    finite = [v for v in values if v is not None]
    if any(v is not None and math.isinf(v) for v in values):
        return math.inf
    return max(finite) if finite else None


def combine(gate: str, config_id: str, parts: Sequence[GateOutcome]) -> GateOutcome:
    """Conjunction of component outcomes.

    Order of precedence: any ``reject`` rejects; otherwise any ``timeout``
    times out; otherwise any ``error`` errors; otherwise any ``refuse``
    refuses; otherwise accept.
    """
    verdicts = [part.verdict for part in parts]
    for verdict in ("reject", "timeout", "error", "refuse"):
        if verdict in verdicts:
            break
    else:
        verdict = "accept"
    return GateOutcome(
        gate=gate,
        config_id=config_id,
        verdict=verdict,
        max_abs_err=worst([part.max_abs_err for part in parts]),
        max_rel_err=worst([part.max_rel_err for part in parts]),
        tolerance=None,
        details={"components": {part.gate: part.verdict for part in parts}},
        wall_seconds=sum(part.wall_seconds for part in parts),
    )


def exception_details(exc: BaseException, limit: int = 2000) -> dict[str, str]:
    text = "".join(traceback.format_exception_only(type(exc), exc)).strip()
    return {
        "error_name": f"{type(exc).__module__}.{type(exc).__name__}",
        "error": text[:limit],
    }
