"""Registered budget rules of the K1 successor screen (q3-k1-localization-screen-v2).

Pure Python, no torch, so the manifest filler (run without the architecture
extra) uses the same code as the GPU entry point and the throughput probe.

v1 stopped at its smoke gate because its limits came from estimates. Here
every job limit is an explicit function of measured rates:

1. The throughput probe (``q3-k1-throughput-probe-v1``) measures ``Rates`` on
   synthetic token ids at the registered shapes with the v2 code.
2. ``derive_limits`` turns those rates into one wall-time projection per job
   and a Slurm limit ``max(5, ceil(1.2 x (1 + 0.15) x projection + 3))``
   minutes: v1's registered 1.2 margin, a 15 percent headroom for the v2
   smoke's re-measurement (the adversarial review's 10-15 percent), and the
   3-minute lead of Slurm's USR1. The limits are written into the v2 contract
   and registration before the v2 freeze.
3. The v2 smoke re-measures the rates on the registered data and passes only
   if ``1.2 x projection + 3`` fits the registered limit for the main job
   *and* for the worst-case V1 extension (``smoke_gate``).

Counting rule for the 8 GPU-hour gauntlet threshold (program decision D20),
fixed here and in both registrations before the probe measures anything: the
total is the sum of the registered caps (GPUs x limit), never expected use, of
every v2 job, with the conditional V1 extension counted at its worst-case cap
and the main job's one continuation inside the main cap, plus the cap of every
throughput-probe run (``PROBE_RUNS_GPU_HOURS``: a complete, incomplete or void
run counts in full, and a rerun under a new id adds its own cap). If that total
exceeds 8 GPU-hours, the gauntlet applies before any v2 freeze; the formula
and its factors (1.2, 1.15, the 3-minute lead, the 5-minute minimum) are never
changed after the probe to fit.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, fields
from typing import Any

# Registered layout (v1's design decisions; unchanged).
LAYERS = 28
SHARDS: tuple[tuple[int, ...], ...] = (tuple(range(0, 8)), tuple(range(8, 15)),
                                       tuple(range(15, 22)), tuple(range(22, 28)))
MAIN_GPUS = 4
BATCH = 4
INDEXERS_PER_LAYER = 18
EXTENSION_INDEXERS_PER_LAYER = 6  # worst case: both targets fail V1, frozen LR x 3 seeds each
MAIN_STEPS = 610
EXTENSION_STEPS = 1220  # epochs 2 and 3
CHECKPOINT_EVERY = 100
DEV_SEQUENCES = 64
RESUME_STOP_STEP = 40
RESUME_HOLD_STEP = 25
RESUME_CHECKPOINT_EVERY = 10

# Measurement protocol shared by the probe and the v2 smoke.
SMOKE_TRAIN_STEPS = 12
SMOKE_EXTENSION_STEPS = 6
STEADY_SKIP_STEPS = 2  # steps 0 and 1 are excluded from every steady-state step time
SMOKE_DEVKL_SEQUENCES = 4
SMOKE_UNITS_PER_KIND = 24
# Query rows of the timed selection units: the probe's synthetic units have
# exactly this many and the smoke times the development units closest to it,
# the audit mean (33.2) rounded up, so both measure at the same rows.
TIMED_UNIT_ROWS = 34
UNIT_SKIP = 1  # the first unit of each kind is excluded from per-unit times

# Limit rule.
PROJECTION_MARGIN = 1.2  # v1's registered factor
HEADROOM = 0.15  # probe projection -> registered limit, for the smoke's re-measurement
SIGNAL_LEAD_MINUTES = 3.0  # Slurm's USR1 arrives 180 s before the limit
MAIN_ALLOWANCE_S = 300.0  # v1's registered start-up allowance (staging, statistics, receipt)
LEG_ALLOWANCE_S = 120.0  # the same for the single-GPU gate jobs
MIN_LIMIT_MINUTES = 5
CONTINUATION_MIN_MINUTES = 5  # v1: a main continuation runs only if 5 minutes remain
CONCURRENT_SAVE_FACTOR = 4  # four resume workers write their shards at once (serialised bound)
GAUNTLET_GPU_HOURS = 8.0
PROBE_GPU_HOURS = 0.15  # q3-k1-throughput-probe-v1: 1 GPU x 9 minutes (D20)
# Every throughput-probe run, at its full cap, whatever its outcome. A rerun is
# a new probe id and a new entry here (with the program owner's budget line).
PROBE_RUNS_GPU_HOURS: dict[str, float] = {"q3-k1-throughput-probe-v1": PROBE_GPU_HOURS}
COUNTING_RULE = ("sum of the registered caps (GPUs x limit) of every v2 job, the conditional "
                 "extension at its worst-case cap and the main continuation inside the main "
                 "cap, plus the cap of every throughput-probe run whatever its outcome; "
                 "expected use never replaces a cap")

JOBS: tuple[tuple[str, int], ...] = (
    ("smoke", 1), ("headroom-dev", 1), ("resume-r0", 1), ("resume-r1", 1), ("resume-r2", 1),
    ("main", MAIN_GPUS), ("extension", MAIN_GPUS))


class BudgetContractError(ValueError):
    """Raised when rates or limits violate the registered budget contract."""


@dataclass(frozen=True)
class UnitMix:
    """Evaluation units of one stage (bundle metadata: roles, partitions, indices)."""

    select_only: int
    select_mc: int
    mc_only: int
    selection_rows_total: int

    @property
    def selection_units(self) -> int:
        return self.select_only + self.select_mc

    @property
    def mean_rows(self) -> float:
        return self.selection_rows_total / max(self.selection_units, 1)


# Measured from k1-bundle-v1.json (SHA-256 919d016b...) metadata only, with v1's
# plan_units: program/evidence/2026-10-07/q3-k1/smoke-452/run-root-timestamps.txt.
AUDIT_MIX = UnitMix(select_only=3650, select_mc=5060, mc_only=300, selection_rows_total=289330)
DEV_MIX = UnitMix(select_only=160, select_mc=280, mc_only=560, selection_rows_total=16968)


@dataclass(frozen=True)
class Rates:
    """Measured rates (seconds). ``concurrent_*`` exist only in the probe."""

    teacher_layer_seq_s: float  # training teacher forward per layer and sequence (batch 4)
    layer_step_s: float  # one layer and step, 18 indexers: 4 x (targets + bank), clip, Adam
    layer_step_ext_s: float  # the same with the extension's 6 trainable indexers
    step_overhead_s: float  # per step outside the teacher and the layers
    devkl_teacher_layer_seq_s: float  # stream-dev teacher forward per layer and sequence (batch 1)
    devkl_layer_seq_s: float  # one layer, one dev sequence, 18 indexers, no gradients
    save_layer_s: float  # checkpoint save per layer (18 indexers with Adam moments)
    train_startup_s: float  # training worker spawn to its first step
    eval_startup_s: float  # evaluation worker spawn to its first unit
    eval_select_s: float  # selection-only unit
    eval_select_mc_s: float  # selection plus multiple-choice unit
    eval_mc_only_s: float  # multiple-choice-only unit
    eval_rows: float  # mean query rows of the measured selection units
    capture_check_s: float  # the smoke's capture-consistency and eager check
    concurrent_step_s: float | None = None  # resume layout: slowest of 4 shards sharing one GPU
    concurrent_startup_s: float | None = None  # resume layout: worker spawn to first step

    def __post_init__(self) -> None:
        for item in fields(self):
            value = getattr(self, item.name)
            if value is None and item.name.startswith("concurrent_"):
                continue
            if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise BudgetContractError(f"{item.name} must be a finite non-negative number")
        if self.eval_rows <= 0:
            raise BudgetContractError("eval_rows must be positive")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> Rates:
        names = {item.name for item in fields(cls)}
        unknown = set(payload) - names
        if unknown:
            raise BudgetContractError(f"unknown rate fields {sorted(unknown)}")
        return cls(**{name: payload.get(name) for name in names if name in payload})


# --------------------------------------------------------------------------- #
# Projections
# --------------------------------------------------------------------------- #


def checkpoint_saves(first_step: int, last_step: int, every: int = CHECKPOINT_EVERY) -> int:
    """Periodic saves at multiples of ``every`` in ``(first_step, last_step)`` plus the final."""

    periodic = sum(1 for step in range(first_step + 1, last_step) if step % every == 0)
    return periodic + 1


def shard_step_s(rates: Rates, layers: Sequence[int], *, extension: bool = False) -> float:
    per_layer = rates.layer_step_ext_s if extension else rates.layer_step_s
    prefix = max(layers) + 1
    return (BATCH * prefix * rates.teacher_layer_seq_s + len(layers) * per_layer
            + rates.step_overhead_s)


def eval_s(rates: Rates, mix: UnitMix) -> float:
    """All units of ``mix`` on one worker; selection units scaled up (never down) by rows."""

    rows_factor = max(1.0, mix.mean_rows / rates.eval_rows)
    selection = mix.select_only * rates.eval_select_s + mix.select_mc * rates.eval_select_mc_s
    return rows_factor * selection + mix.mc_only * rates.eval_mc_only_s


def eval_load_s(rates: Rates) -> float:
    """An evaluation worker's read of the 28-layer generation, priced at the save rate.

    ``eval_startup_s`` excludes this read in the probe (it loads nothing) and in
    the smoke (which times the read apart), so both price it the same way.
    """

    return LAYERS * rates.save_layer_s


def project_main(rates: Rates) -> dict[str, float]:
    train = max(MAIN_STEPS * shard_step_s(rates, layers)
                + checkpoint_saves(0, MAIN_STEPS) * len(layers) * rates.save_layer_s
                for layers in SHARDS)
    devkl = max(DEV_SEQUENCES * ((max(layers) + 1) * rates.devkl_teacher_layer_seq_s
                                 + len(layers) * rates.devkl_layer_seq_s) for layers in SHARDS)
    evaluation = eval_s(rates, AUDIT_MIX) / MAIN_GPUS
    startups = 2 * rates.train_startup_s + rates.eval_startup_s
    load = eval_load_s(rates)
    return {"train_s": train, "devkl_s": devkl, "eval_s": evaluation, "startups_s": startups,
            "eval_load_s": load, "allowance_s": MAIN_ALLOWANCE_S,
            "wall_s": MAIN_ALLOWANCE_S + startups + load + train + devkl + evaluation}


def project_extension(rates: Rates) -> dict[str, float]:
    """Worst case: both targets fail V1, so 6 indexers per layer train epochs 2-3."""

    last = MAIN_STEPS + EXTENSION_STEPS
    train = max(EXTENSION_STEPS * shard_step_s(rates, layers, extension=True)
                + (checkpoint_saves(MAIN_STEPS, last) + 1) * len(layers) * rates.save_layer_s
                for layers in SHARDS)  # + 1: reading the main run's final generation
    evaluation = eval_s(rates, AUDIT_MIX) / MAIN_GPUS
    startups = rates.train_startup_s + rates.eval_startup_s
    load = eval_load_s(rates)
    return {"train_s": train, "eval_s": evaluation, "startups_s": startups,
            "eval_load_s": load, "allowance_s": MAIN_ALLOWANCE_S,
            "wall_s": MAIN_ALLOWANCE_S + startups + load + train + evaluation}


def project_smoke(rates: Rates) -> dict[str, float]:
    every = tuple(range(LAYERS))
    train = SMOKE_TRAIN_STEPS * shard_step_s(rates, every) + LAYERS * rates.save_layer_s
    extension = (SMOKE_EXTENSION_STEPS * shard_step_s(rates, every, extension=True)
                 + LAYERS * rates.save_layer_s)
    devkl = SMOKE_DEVKL_SEQUENCES * LAYERS * (rates.devkl_teacher_layer_seq_s
                                              + rates.devkl_layer_seq_s)
    rows_factor = max(1.0, DEV_MIX.mean_rows / rates.eval_rows)
    evaluation = SMOKE_UNITS_PER_KIND * (rows_factor * (rates.eval_select_s
                                                        + rates.eval_select_mc_s)
                                         + rates.eval_mc_only_s)
    startups = 3 * rates.train_startup_s + rates.eval_startup_s
    load = eval_load_s(rates)
    wall = (LEG_ALLOWANCE_S + rates.capture_check_s + startups + load + train + extension
            + devkl + evaluation)
    return {"train_s": train, "extension_timing_s": extension, "devkl_s": devkl,
            "eval_s": evaluation, "capture_s": rates.capture_check_s, "startups_s": startups,
            "eval_load_s": load, "allowance_s": LEG_ALLOWANCE_S, "wall_s": wall}


def project_headroom_dev(rates: Rates) -> dict[str, float]:
    """One worker, the whole development partition (dense selectors priced as with indexers)."""

    evaluation = eval_s(rates, DEV_MIX)
    return {"eval_s": evaluation, "startups_s": rates.eval_startup_s,
            "allowance_s": LEG_ALLOWANCE_S,
            "wall_s": LEG_ALLOWANCE_S + rates.eval_startup_s + evaluation}


def _concurrent(rates: Rates) -> tuple[float, float, float]:
    if rates.concurrent_step_s is None or rates.concurrent_startup_s is None:
        raise BudgetContractError("the resume legs need the probe's four-workers-per-GPU rates")
    save = CONCURRENT_SAVE_FACTOR * max(len(layers) for layers in SHARDS) * rates.save_layer_s
    return rates.concurrent_step_s, rates.concurrent_startup_s, save


def project_resume(rates: Rates, leg: str) -> dict[str, float]:
    """R0 and R2 must finish, and R1 must hold at step 25, before their USR1."""

    step, startup, save = _concurrent(rates)
    every = RESUME_CHECKPOINT_EVERY
    if leg == "resume-r0":
        steps, saves, loads = RESUME_STOP_STEP, checkpoint_saves(0, RESUME_STOP_STEP, every), 0
    elif leg == "resume-r1":
        steps = RESUME_HOLD_STEP
        saves = sum(1 for s in range(1, RESUME_HOLD_STEP + 1) if s % every == 0)
        loads = 0
    elif leg == "resume-r2":
        steps = RESUME_STOP_STEP - RESUME_HOLD_STEP
        saves = checkpoint_saves(RESUME_HOLD_STEP, RESUME_STOP_STEP, every)
        loads = 1
    else:
        raise BudgetContractError(f"unknown resume leg {leg}")
    work = steps * step + (saves + loads) * save
    return {"train_s": work, "startups_s": startup, "allowance_s": LEG_ALLOWANCE_S,
            "wall_s": LEG_ALLOWANCE_S + startup + work}


def project(rates: Rates, job: str) -> dict[str, float]:
    if job == "main":
        return project_main(rates)
    if job == "extension":
        return project_extension(rates)
    if job == "smoke":
        return project_smoke(rates)
    if job == "headroom-dev":
        return project_headroom_dev(rates)
    return project_resume(rates, job)


# --------------------------------------------------------------------------- #
# Limits, caps and the gates
# --------------------------------------------------------------------------- #


def required_minutes(wall_s: float) -> float:
    """v1's gate quantity: 1.2 x projected wall minutes + the 3-minute USR1 lead."""

    return PROJECTION_MARGIN * wall_s / 60.0 + SIGNAL_LEAD_MINUTES


def limit_minutes(wall_s: float) -> int:
    """The registered limit for a probe projection."""

    return max(MIN_LIMIT_MINUTES, math.ceil(
        PROJECTION_MARGIN * (1.0 + HEADROOM) * wall_s / 60.0 + SIGNAL_LEAD_MINUTES - 1e-9))


def gpu_hours(gpus: int, minutes: float) -> float:
    return math.ceil(gpus * minutes / 60.0 * 100.0 - 1e-9) / 100.0


def derive_limits(rates: Rates) -> dict[str, Any]:
    """Every job's projection, registered limit and cap, and the gauntlet check."""

    jobs: dict[str, dict[str, Any]] = {}
    for job, gpus in JOBS:
        projection = project(rates, job)
        minutes = limit_minutes(projection["wall_s"])
        jobs[job] = {"gpus": gpus, "projection": projection,
                     "projected_minutes": projection["wall_s"] / 60.0, "minutes": minutes,
                     "max_gpu_hours": gpu_hours(gpus, minutes)}
    probes = sum(PROBE_RUNS_GPU_HOURS.values())
    total = round(sum(job["max_gpu_hours"] for job in jobs.values()) + probes, 2)
    return {"jobs": jobs, "total_gpu_hours_with_probe": total,
            "probe_runs_gpu_hours": dict(PROBE_RUNS_GPU_HOURS),
            "counting_rule": COUNTING_RULE,
            "gauntlet_threshold_gpu_hours": GAUNTLET_GPU_HOURS,
            "gauntlet_required": total > GAUNTLET_GPU_HOURS,
            "rule": (f"limit = max({MIN_LIMIT_MINUTES}, ceil({PROJECTION_MARGIN} x "
                     f"(1 + {HEADROOM}) x projected minutes + {SIGNAL_LEAD_MINUTES})); "
                     "cap = GPUs x limit / 60, rounded up to 0.01 GPU-h")}


def limits_table(derived: Mapping[str, Any]) -> dict[str, dict[str, float]]:
    """``{job: {"minutes", "max_gpu_hours"}}``, the form the contract and filler use."""

    return {job: {"minutes": int(value["minutes"]), "max_gpu_hours": float(value["max_gpu_hours"])}
            for job, value in derived["jobs"].items()}


def check_limits(limits: Mapping[str, Mapping[str, Any]]) -> dict[str, dict[str, float]]:
    """Validate a registered limits table (every job, integer minutes, consistent caps)."""

    out: dict[str, dict[str, float]] = {}
    for job, gpus in JOBS:
        entry = limits.get(job) if isinstance(limits, Mapping) else None
        if not isinstance(entry, Mapping):
            raise BudgetContractError(f"no registered limit for {job}")
        minutes, cap = entry.get("minutes"), entry.get("max_gpu_hours")
        if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes < MIN_LIMIT_MINUTES:
            raise BudgetContractError(f"{job}: minutes must be an integer >= {MIN_LIMIT_MINUTES}")
        if not isinstance(cap, (int, float)) or cap != gpu_hours(gpus, minutes):
            raise BudgetContractError(f"{job}: max_gpu_hours must be {gpu_hours(gpus, minutes)}")
        out[job] = {"minutes": minutes, "max_gpu_hours": float(cap)}
    extra = set(limits) - {job for job, _ in JOBS}
    if extra:
        raise BudgetContractError(f"unknown jobs in the limits table: {sorted(extra)}")
    return out


def smoke_gate(rates: Rates, limits: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """The v2 smoke gate: the main job and the worst-case extension both fit."""

    table = check_limits(limits)
    out: dict[str, Any] = {"rule": (f"{PROJECTION_MARGIN} x projected wall minutes + "
                                    f"{SIGNAL_LEAD_MINUTES} <= the registered limit, for the "
                                    "main job and for the worst-case V1 extension")}
    passed = True
    for job in ("main", "extension"):
        projection = project(rates, job)
        required = required_minutes(projection["wall_s"])
        fits = required <= table[job]["minutes"]
        passed &= fits
        out[job] = {"projection": projection, "wall_minutes": projection["wall_s"] / 60.0,
                    "required_limit_minutes": required, "limit_minutes": table[job]["minutes"],
                    "fits": fits}
    out["passed"] = passed
    return out


def continuation_minutes(main_limit: int, minutes_used: int) -> int | None:
    """The main job's one continuation: what is left of the main limit, if at least 5."""

    remaining = int(main_limit) - int(minutes_used)
    return remaining if remaining >= CONTINUATION_MIN_MINUTES else None


# --------------------------------------------------------------------------- #
# Scenarios of the design analysis (for the registration's sensitivity table)
# --------------------------------------------------------------------------- #

# Per-unit costs from v1 smoke job 452 (receipt and run-root timestamps): teacher
# 2.96 ms per layer and sequence; save 3.99 GB for 28 layers in 13.4 s; worker
# start-up 12 s (training) and 15.7 s (evaluation); parent start-up plus the
# capture check 30 s; v1 single-GPU steps for four workers 15.07 s. The three
# engineering scenarios are the design analysis's (indexer ms per indexer, layer
# and sequence; targets ms per layer and sequence; seconds per selection unit).
SCENARIO_INPUTS: dict[str, dict[str, float]] = {
    "central": {"indexer_ms": 1.3, "targets_ms": 10.0, "select_s": 0.16},
    "conservative": {"indexer_ms": 2.8, "targets_ms": 16.0, "select_s": 0.30},
    "batching-only": {"indexer_ms": 3.2, "targets_ms": 20.0, "select_s": 0.30},
}


def scenario_rates(name: str) -> Rates:
    """Rates of one design-analysis scenario (estimates, not measurements)."""

    inputs = SCENARIO_INPUTS[name]
    teacher = 0.00296
    layer = BATCH * (inputs["targets_ms"] + INDEXERS_PER_LAYER * inputs["indexer_ms"]) / 1000.0
    layer_ext = BATCH * (inputs["targets_ms"]
                         + EXTENSION_INDEXERS_PER_LAYER * inputs["indexer_ms"]) / 1000.0
    devkl = (inputs["targets_ms"] + INDEXERS_PER_LAYER * inputs["indexer_ms"] / 3.0) / 1000.0
    partial = Rates(teacher_layer_seq_s=teacher, layer_step_s=layer, layer_step_ext_s=layer_ext,
                    step_overhead_s=0.02, devkl_teacher_layer_seq_s=teacher,
                    devkl_layer_seq_s=devkl, save_layer_s=13.4 / 28, train_startup_s=12.0,
                    eval_startup_s=15.7, eval_select_s=inputs["select_s"],
                    eval_select_mc_s=inputs["select_s"] + 0.04, eval_mc_only_s=0.13,
                    eval_rows=AUDIT_MIX.mean_rows, capture_check_s=30.0)
    # Four shards on one GPU: the GPU serialises them, so the slowest worker's
    # step is about the sum of the solo steps (v1: 15.07 s against 15.06 s).
    concurrent = sum(shard_step_s(partial, layers) for layers in SHARDS)
    return Rates(**{**partial.as_dict(), "concurrent_step_s": concurrent,
                    "concurrent_startup_s": 20.0})


__all__ = [
    "AUDIT_MIX",
    "DEV_MIX",
    "JOBS",
    "SHARDS",
    "BudgetContractError",
    "Rates",
    "UnitMix",
    "check_limits",
    "continuation_minutes",
    "derive_limits",
    "eval_load_s",
    "gpu_hours",
    "limit_minutes",
    "limits_table",
    "project",
    "required_minutes",
    "scenario_rates",
    "smoke_gate",
]
