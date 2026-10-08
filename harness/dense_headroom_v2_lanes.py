"""The lanes, limits and caps of q3-dense-headroom-precheck-v2 (D36).

The lane objects are v1's (``harness.dense_headroom_data.LANES``: same models,
receipts, tokenizers, layers, profiles) with v2's minutes and caps, set from
the development timing job (Slurm 766) and from v1's job 727.

Limits (D36): each lane's minutes are at least twice its measured full-lane
evaluation time, plus its measured start-up, plus the 3-minute SIGUSR1 lead,
rounded up to whole minutes; every job of a lane (its first job, a re-run of
a void job and its one continuation) is charged against those minutes, as in
v1. The v2 cap is 1.5 GPU-h in total, the timing job included.
"""

from __future__ import annotations

import dataclasses
import math
from typing import Any

from harness import dense_headroom_data as dhd

TOTAL_CAP_GPU_HOURS = 1.5  # D36: v2 in total, the timing job included

# Measured inputs of the limits (seconds).
SMALL_LANE_V1_JOB = "727"
SMALL_LANE_MEASURED = {"evaluation_and_statistics_s": 262.0, "start_up_s": 16.0,
                       "job_s": 278.0, "source": "v1 job 727 receipt timings and job.env/"
                                                "termination.env (278 s)"}
# The development timing job (Slurm 766) ran v2's path with cuDNN's attention
# and found the cost: a new cuDNN graph per new query/key length, about 0.7 s
# of CPU per forward (a unit reusing an earlier prefill length took 0.11 s for
# its prefill instead of about 0.8 s). The fixed path (cuDNN's attention off on
# this lane) has no per-shape build; its per-unit time is taken from the units
# the timing job re-evaluated with every graph cached (0.511 and 0.517 s, v1's
# path under cProfile), for all 1,160 units, plus a 5 s statistics bound (job
# 727: 1.2 s). Because the fixed path itself was not timed, the evaluation time
# entering D36's rule is twice that projection. Start-up: the 8 s before the
# process, 19.4 s to the first unit and the first unit's 47.2 s of compiles.
LARGE_LANE_MEASURED: dict[str, Any] = {
    "timing_job": "766", "warm_unit_s": 0.52, "units": 1160, "statistics_bound_s": 5.0,
    "projected_evaluation_and_statistics_s": 0.52 * 1160 + 5.0,
    "evaluation_and_statistics_s": 2.0 * (0.52 * 1160 + 5.0),
    "start_up_s": 75.0,
    "cold_unit_median_s_with_cudnn_attention": {"A-main": 4.08, "B-absent": 3.62},
    "source": "development timing job, Slurm 766 (program/evidence/2026-10-08/"
              "q3-dense-headroom-precheck-v2-build/)"}


def limit_minutes(evaluation_s: float, start_up_s: float) -> int:
    """D36's rule: twice the full-lane evaluation, plus start-up, plus the
    3-minute SIGUSR1 lead, in whole minutes."""

    return math.ceil((2.0 * evaluation_s + start_up_s) / 60.0) + dhd.USR1_LEAD_MINUTES


def _lane(lane_id: str, minutes: int) -> dhd.Lane:
    return dataclasses.replace(dhd.LANES[lane_id], minutes=minutes,
                               cap_gpu_hours=round(minutes / 60.0, 4))


SMALL_LANE_MINUTES = limit_minutes(SMALL_LANE_MEASURED["evaluation_and_statistics_s"],
                                   SMALL_LANE_MEASURED["start_up_s"])  # 12
LARGE_LANE_MINUTES = limit_minutes(LARGE_LANE_MEASURED["evaluation_and_statistics_s"],
                                   LARGE_LANE_MEASURED["start_up_s"])  # 45

LANES: dict[str, dhd.Lane] = {
    "qwen3-0.6b-base": _lane("qwen3-0.6b-base", SMALL_LANE_MINUTES),
    "qwen3.5-4b-base": _lane("qwen3.5-4b-base", LARGE_LANE_MINUTES),
}
REGISTERED_ORDER = dhd.REGISTERED_ORDER

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
    "LARGE_LANE_MEASURED",
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
    "limit_minutes",
    "registered_caps_total",
]
