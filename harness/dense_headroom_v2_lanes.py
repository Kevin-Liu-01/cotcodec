"""The lanes, limits and caps of q3-dense-headroom-precheck-v2 (D36).

The lane objects are v1's (``harness.dense_headroom_data.LANES``: same models,
receipts, tokenizers, layers, profiles) with v2's minutes and caps.

Limits. The arithmetic is D36's: twice the full-lane evaluation time, plus
start-up, plus the 3-minute SIGUSR1 lead, rounded up to whole minutes. Only
the Qwen3-0.6B-Base lane's evaluation time is measured (v1's job 727 ran the
computation v2 reproduces). The Qwen3.5-4B-Base lane's is a projection, not a
measurement: the development timing job (Slurm 766) ran the 4B path as it was
before the fix (cuDNN's attention on), and the fixed path (cuDNN's attention
off) has not run on a GPU. Its per-unit time is taken from the timing job's
warm-shape units and the result is doubled again because it is unmeasured
(``LARGE_LANE_PROJECTED``). That departs from D36's rule, which asks for a
measurement of the fixed 4B path, so the decision that accepts the
registration has to amend that rule for the 4B lane, or authorise a timing
job of the fixed path whose measurement then replaces the projection here
(registration decisions 20 and 21). The lane completes inside its useful
window only if the fixed path averages at most about 2.1 s per unit
(``large_lane_break_even_unit_s``); above that it ends INCOMPLETE. Every job
of a lane (its first job, a re-run of a void job and its one continuation) is
charged against the lane's minutes, as in v1. The v2 cap is 1.5 GPU-h in
total, the timing job included.
"""

from __future__ import annotations

import dataclasses
import math
from typing import Any

from harness import dense_headroom_data as dhd

TOTAL_CAP_GPU_HOURS = 1.5  # D36: v2 in total, the timing job included

# The 0.6B lane's limit: measured (seconds).
SMALL_LANE_V1_JOB = "727"
SMALL_LANE_MEASURED = {"evaluation_and_statistics_s": 262.0, "start_up_s": 16.0,
                       "job_s": 278.0, "source": "v1 job 727 receipt timings and job.env/"
                                                "termination.env (278 s)"}
# The 4B lane's limit: projected, not measured (seconds). The development
# timing job (Slurm 766) ran the 4B path before the fix, with cuDNN's attention
# on (image from 71dc954), and located the cost: a new cuDNN graph per new
# query/key length, about 0.7 s of CPU per forward (a unit reusing an earlier
# prefill length took 0.11 s for its prefill instead of about 0.8 s); cold
# units took 3.6 to 4.1 s, at which the lane needs about 75 minutes. The fixed
# path (cuDNN's attention off on this lane) was not timed and has not run on a
# GPU. Its per-unit time is projected from the two units the timing job
# re-evaluated with every graph cached (0.511 and 0.517 s, v1's path under
# cProfile), for all 1,160 units, plus a 5 s statistics bound (job 727: 1.2
# s). Because that is a projection, the evaluation time entering D36's
# arithmetic is twice it. Start-up was measured on the path before the fix:
# the 8 s before the process, 19.4 s to the first unit and the first unit's
# 47.2 s of compiles.
LARGE_LANE_PROJECTED: dict[str, Any] = {
    "measured": False, "timing_job": "766",
    "timing_job_path": "before the fix: cuDNN's attention on (image from 71dc954)",
    "warm_unit_s": 0.52, "units": 1160, "statistics_bound_s": 5.0,
    "projected_evaluation_and_statistics_s": 0.52 * 1160 + 5.0,
    "evaluation_entering_rule_s": 2.0 * (0.52 * 1160 + 5.0),
    "start_up_s": 75.0,
    "cold_unit_median_s_with_cudnn_attention": {"A-main": 4.08, "B-absent": 3.62},
    "source": "development timing job, Slurm 766 (program/evidence/2026-10-08/"
              "q3-dense-headroom-precheck-v2-build/)"}


def limit_minutes(evaluation_s: float, start_up_s: float) -> int:
    """D36's arithmetic: twice the full-lane evaluation time (measured for the
    0.6B lane, a doubled projection for the 4B lane), plus start-up, plus the
    3-minute SIGUSR1 lead, in whole minutes."""

    return math.ceil((2.0 * evaluation_s + start_up_s) / 60.0) + dhd.USR1_LEAD_MINUTES


def _lane(lane_id: str, minutes: int) -> dhd.Lane:
    return dataclasses.replace(dhd.LANES[lane_id], minutes=minutes,
                               cap_gpu_hours=round(minutes / 60.0, 4))


SMALL_LANE_MINUTES = limit_minutes(SMALL_LANE_MEASURED["evaluation_and_statistics_s"],
                                   SMALL_LANE_MEASURED["start_up_s"])  # 12
LARGE_LANE_MINUTES = limit_minutes(LARGE_LANE_PROJECTED["evaluation_entering_rule_s"],
                                   LARGE_LANE_PROJECTED["start_up_s"])  # 45

LANES: dict[str, dhd.Lane] = {
    "qwen3-0.6b-base": _lane("qwen3-0.6b-base", SMALL_LANE_MINUTES),
    "qwen3.5-4b-base": _lane("qwen3.5-4b-base", LARGE_LANE_MINUTES),
}
REGISTERED_ORDER = dhd.REGISTERED_ORDER


def large_lane_break_even_unit_s() -> float:
    """The slowest mean seconds per unit at which the 4B lane's first job still
    finishes its 1,160 units inside its useful window (the limit minus the
    SIGUSR1 lead, minus the start-up and the statistics bound)."""

    basis = LARGE_LANE_PROJECTED
    useful_s = (LARGE_LANE_MINUTES - dhd.USR1_LEAD_MINUTES) * 60.0
    return (useful_s - basis["start_up_s"] - basis["statistics_bound_s"]) / basis["units"]

# The development timing job (D36): one job, 1 GPU, at most 0.1 GPU-h, on the
# 4B lane's model, container profile and inputs.
TIMING_LANE = "qwen3.5-4b-base"
TIMING_MINUTES = 6
TIMING_CAP_GPU_HOURS = 0.1


def lane_of(lane_id: str) -> dhd.Lane:
    lane = LANES.get(lane_id) or dhd.TINY_LANES.get(lane_id)
    if lane is None:
        raise dhd.DenseDataError(f"unknown lane {lane_id!r}")
    return lane


def registered_caps_total() -> float:
    return round(sum(lane.cap_gpu_hours for lane in LANES.values()) + TIMING_CAP_GPU_HOURS, 6)


__all__ = [
    "LANES",
    "LARGE_LANE_PROJECTED",
    "LARGE_LANE_MINUTES",
    "REGISTERED_ORDER",
    "SMALL_LANE_MEASURED",
    "SMALL_LANE_MINUTES",
    "SMALL_LANE_V1_JOB",
    "TIMING_CAP_GPU_HOURS",
    "TIMING_LANE",
    "TIMING_MINUTES",
    "TOTAL_CAP_GPU_HOURS",
    "lane_of",
    "large_lane_break_even_unit_s",
    "limit_minutes",
    "registered_caps_total",
]
