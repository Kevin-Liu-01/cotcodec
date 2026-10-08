"""The lanes, limits and caps of q3-dense-headroom-precheck-v2 (D36, D42).

The lane objects are v1's (``harness.dense_headroom_data.LANES``: same models,
receipts, tokenizers, layers, profiles) with v2's minutes and caps.

Limits. The arithmetic is D36's: twice the measured full-lane evaluation
time, plus start-up, plus the 3-minute SIGUSR1 lead, rounded up to whole
minutes. Both lanes' inputs are measurements. The Qwen3-0.6B-Base lane's come
from v1's job 727, which ran the computation v2 reproduces. The
Qwen3.5-4B-Base lane's come from the second development timing job (Slurm
810, D42 (ii)), which ran the fixed 4B path (cuDNN's attention off) at the
code head on the GPU, starting with the lane's own start-up and its
``attention_backend_check``. It replaces the projection that the first timing
job (Slurm 766, the path before the fix) had left: 45 minutes from a doubled
warm-shape projection. The lane completes inside its useful window if it
averages at most about 1.3 s per unit (``large_lane_break_even_unit_s``)
against the 0.16 to 0.43 s per unit measured. Every job of a lane (its first
job, a re-run of a void job and its one continuation) is charged against the
lane's minutes, as in v1. The v2 cap is 1.5 GPU-h in total, both development
timing jobs included (D36, D42).
"""

from __future__ import annotations

import dataclasses
import math
from typing import Any

from harness import dense_headroom_data as dhd

TOTAL_CAP_GPU_HOURS = 1.5  # D36: v2 in total, both timing jobs included (D42)

# The 0.6B lane's limit: measured (seconds).
SMALL_LANE_V1_JOB = "727"
SMALL_LANE_MEASURED = {"evaluation_and_statistics_s": 262.0, "start_up_s": 16.0,
                       "job_s": 278.0, "source": "v1 job 727 receipt timings and job.env/"
                                                "termination.env (278 s)"}
# The 4B lane's limit: measured on the fixed path (seconds), by the second
# development timing job, Slurm 810 (image from 87242fa; cuDNN's attention off,
# PyTorch's memory-efficient attention in the torch profiles). It ran 159
# first evaluations of units in all four stages (the registered subset and one
# further chunk of A-main and B-absent, the latter two under cProfile).
# Per stage, the mean of those units, leaving out one-off first-use compiles
# (a unit over five times its stage's median: the first selection-only prefill
# and the first prefill above 8,192 tokens, 7.4 and 7.6 s), is scaled up by the
# ratio of the lane's mean token length in that stage to the measured units'
# (the subset's contexts are shorter than the lane's; never scaled down), times
# the stage's units. The compiles are then added at their observed rate (2 in
# 159 units) over all 1,160 units at the larger one's extra cost, plus a 5 s
# statistics bound (job 727: 1.2 s). Start-up is everything before the first
# unit: 2 s from Slurm's start to job.env, 9.7 s of the job outside the
# workload process (container creation and the epilogue) and 67.0 s in the
# process (start-up checks, derivation, model load and the 47.4 s
# attention_backend_check with the first-use compiles).
LARGE_LANE_TIMING_JOB = "810"
LARGE_LANE_STAGES: dict[str, dict[str, float]] = {
    # stage: units in the lane, measured mean seconds per unit (compiles left
    # out), length ratio (lane mean tokens / measured mean tokens, at least 1)
    "A-main": {"units": 440, "measured_unit_s": 0.4346, "length_ratio": 1.7744},
    "B-absent": {"units": 280, "measured_unit_s": 0.4160, "length_ratio": 1.5805},
    "C-literal": {"units": 160, "measured_unit_s": 0.1562, "length_ratio": 1.5918},
    "D-nohaystack": {"units": 280, "measured_unit_s": 0.3387, "length_ratio": 1.0},
}
LARGE_LANE_MEASURED: dict[str, Any] = {
    "measured": True, "timing_job": LARGE_LANE_TIMING_JOB,
    "timing_job_path": "the fixed path: cuDNN's attention off (image from 87242fa)",
    "units": sum(int(s["units"]) for s in LARGE_LANE_STAGES.values()),
    "stage_evaluation_s": {name: s["units"] * s["measured_unit_s"] * s["length_ratio"]
                           for name, s in LARGE_LANE_STAGES.items()},
    "compile_allowance_s": 106.1, "statistics_bound_s": 5.0,
    "start_up_s": 78.7,
    "replaced_projection": {"timing_job": "766", "minutes": 45,
                            "path": "before the fix: cuDNN's attention on (image from 71dc954)"},
    "source": "second development timing job, Slurm 810 (program/evidence/2026-10-08/"
              "q3-dense-headroom-precheck-v2-build/timing-2/timing-810/analysis.json)"}
LARGE_LANE_MEASURED["evaluation_and_statistics_s"] = (
    sum(LARGE_LANE_MEASURED["stage_evaluation_s"].values())
    + LARGE_LANE_MEASURED["compile_allowance_s"] + LARGE_LANE_MEASURED["statistics_bound_s"])


def limit_minutes(evaluation_s: float, start_up_s: float) -> int:
    """D36's arithmetic: twice the measured full-lane evaluation time, plus
    start-up, plus the 3-minute SIGUSR1 lead, in whole minutes."""

    return math.ceil((2.0 * evaluation_s + start_up_s) / 60.0) + dhd.USR1_LEAD_MINUTES


def _lane(lane_id: str, minutes: int) -> dhd.Lane:
    return dataclasses.replace(dhd.LANES[lane_id], minutes=minutes,
                               cap_gpu_hours=round(minutes / 60.0, 4))


SMALL_LANE_MINUTES = limit_minutes(SMALL_LANE_MEASURED["evaluation_and_statistics_s"],
                                   SMALL_LANE_MEASURED["start_up_s"])  # 12
LARGE_LANE_MINUTES = limit_minutes(LARGE_LANE_MEASURED["evaluation_and_statistics_s"],
                                   LARGE_LANE_MEASURED["start_up_s"])  # 30

LANES: dict[str, dhd.Lane] = {
    "qwen3-0.6b-base": _lane("qwen3-0.6b-base", SMALL_LANE_MINUTES),
    "qwen3.5-4b-base": _lane("qwen3.5-4b-base", LARGE_LANE_MINUTES),
}
REGISTERED_ORDER = dhd.REGISTERED_ORDER


def large_lane_break_even_unit_s() -> float:
    """The slowest mean seconds per unit at which the 4B lane's first job still
    finishes its 1,160 units inside its useful window (the limit minus the
    SIGUSR1 lead, minus the start-up and the statistics bound)."""

    basis = LARGE_LANE_MEASURED
    useful_s = (LARGE_LANE_MINUTES - dhd.USR1_LEAD_MINUTES) * 60.0
    return (useful_s - basis["start_up_s"] - basis["statistics_bound_s"]) / basis["units"]

# The development timing jobs: D36's (Slurm 766, the path before the fix) and
# D42's (the fixed path), each 1 GPU, at most 0.1 GPU-h, on the 4B lane's model,
# container profile and inputs, each in its own run root.
TIMING_LANE = "qwen3.5-4b-base"
TIMING_MINUTES = 6
TIMING_CAP_GPU_HOURS = 0.1
TIMING_JOBS = 2


def lane_of(lane_id: str) -> dhd.Lane:
    lane = LANES.get(lane_id) or dhd.TINY_LANES.get(lane_id)
    if lane is None:
        raise dhd.DenseDataError(f"unknown lane {lane_id!r}")
    return lane


def registered_caps_total() -> float:
    """The lanes' caps plus both timing jobs' (D22's counting rule; D36's 1.5 holds them all)."""

    return round(sum(lane.cap_gpu_hours for lane in LANES.values())
                 + TIMING_JOBS * TIMING_CAP_GPU_HOURS, 6)


__all__ = [
    "LANES",
    "LARGE_LANE_MEASURED",
    "LARGE_LANE_MINUTES",
    "LARGE_LANE_STAGES",
    "LARGE_LANE_TIMING_JOB",
    "REGISTERED_ORDER",
    "SMALL_LANE_MEASURED",
    "SMALL_LANE_MINUTES",
    "SMALL_LANE_V1_JOB",
    "TIMING_CAP_GPU_HOURS",
    "TIMING_JOBS",
    "TIMING_LANE",
    "TIMING_MINUTES",
    "TOTAL_CAP_GPU_HOURS",
    "lane_of",
    "large_lane_break_even_unit_s",
    "limit_minutes",
    "registered_caps_total",
]
