"""Preregistered budget rules for serving-throughput-probe-v1.

Pure functions over the per-point JSON the probe writes. Nothing here fits a
model or chooses a rule after seeing data: every extrapolation, fallback and
threshold is fixed in the contract and the preregistration, and every fallback
is recorded as a flag next to the number it produced.

Q2 (closed-loop computer-use episodes, one cell per rung x harness x observation):

    GPU-h_closed = g * ceil(E / V) * sum_{t=1..T} (t_env + m_r * L(t)) / 3600
    GPU-h_open   = E * T * g * m_r / r_cell / 3600
    GPU-h_cell   = max(GPU-h_closed, GPU-h_open)

Q1 (offline n=8 sampling): GPU-h = completions * sum_turns(GPU-s per completion) / 3600.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from harness.serving_probe.prompts import HarnessShape, folded_prefix, modeled_prompt_tokens

VALID_STATUSES = {"valid", "valid-flagged"}


class BudgetError(ValueError):
    """Raised when a required measurement for a projection is missing."""


def is_valid(point: Mapping[str, Any] | None) -> bool:
    return bool(point) and point.get("status") in VALID_STATUSES


def relative_delta(candidate: float, reference: float) -> float:
    if reference <= 0:
        raise BudgetError("reference must be positive")
    return abs(candidate - reference) / reference


def relative_range(values: Sequence[float]) -> float | None:
    clean = [float(value) for value in values if value is not None]
    if len(clean) < 2:
        return None
    mean = sum(clean) / len(clean)
    return (max(clean) - min(clean)) / mean if mean > 0 else None


def replay_mean_latency(point: Mapping[str, Any]) -> float:
    """Mean end-to-end step latency (s) over every completed replay request."""
    e2el = point["result"]["e2el_ms"]["mean"]
    if e2el is None:
        raise BudgetError(f"{point.get('point_id')} has no completed requests")
    return float(e2el) / 1000.0


def step_latencies(point: Mapping[str, Any]) -> dict[int, float]:
    """Mean latency per step index, only for steps every episode completed."""
    result = point["result"]
    curve = {}
    for step in result["complete_steps"]:
        mean = result["per_step"][str(step)]["latency_s"]["mean"]
        if mean is not None:
            curve[int(step)] = float(mean)
    return curve


def evaluate_x1(
    points: Mapping[str, Mapping[str, Any]],
    *,
    max_relative_delta: float,
    a1_seed_points: Sequence[str] = ("a1a", "a1b", "a1c"),
) -> dict[str, Any]:
    """Dummy-weight admissibility (control X1) from job A's points."""
    needed = ("a1a", "r1", "x1-a1", "x1-r1")
    missing = [name for name in needed if not is_valid(points.get(name))]
    seed_range = relative_range(
        [
            points[name]["result"]["request_throughput"]
            for name in a1_seed_points
            if is_valid(points.get(name))
        ]
    )
    if missing:
        return {"outcome": "not-run", "missing_or_invalid": missing, "a1_seed_range": seed_range}
    a1_delta = relative_delta(
        points["x1-a1"]["result"]["request_throughput"],
        points["a1a"]["result"]["request_throughput"],
    )
    r1_delta = relative_delta(
        replay_mean_latency(points["x1-r1"]), replay_mean_latency(points["r1"])
    )
    within = a1_delta <= max_relative_delta and r1_delta <= max_relative_delta
    if not within:
        outcome = "fail"
    elif seed_range is None or seed_range > max_relative_delta:
        outcome = "underpowered"
    else:
        outcome = "pass"
    return {
        "outcome": outcome,
        "a1_relative_delta": a1_delta,
        "r1_relative_delta": r1_delta,
        "a1_seed_range": seed_range,
        "threshold": max_relative_delta,
    }


def stability(
    points: Mapping[str, Mapping[str, Any]],
    names: Sequence[str],
    limit: float,
    metric: str = "request_throughput",
) -> dict[str, Any]:
    """Seed spread of a throughput metric; UNSTABLE above ``limit``; budget uses the minimum."""
    values = [points[name]["result"][metric] for name in names if is_valid(points.get(name))]
    spread = relative_range(values)
    return {
        "points": list(names),
        "metric": metric,
        "valid": len(values),
        "mean": (sum(values) / len(values)) if values else None,
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "relative_range": spread,
        "unstable": spread is not None and spread > limit,
        "budget_value": min(values) if values else None,
    }


@dataclass(frozen=True)
class Profile:
    """A per-step latency curve L(t) with its measured V and extrapolation shape."""

    name: str
    harness: str
    measured: dict[int, float]
    vm_per_replica: int
    shape: HarnessShape
    additive_s: float = 0.0
    flags: tuple[str, ...] = ()

    def latency(self, step: int) -> float:
        if step in self.measured:
            return self.measured[step] + self.additive_s
        if not self.measured:
            raise BudgetError(f"profile {self.name} has no measured steps")
        last = max(self.measured)
        if step < min(self.measured):
            raise BudgetError(f"profile {self.name} has no data before step {min(self.measured)}")
        if step < last:
            lower = max(key for key in self.measured if key < step)
            return self.measured[lower] + self.additive_s
        reference = self._reference_step(step)
        scale = max(
            1.0,
            modeled_prompt_tokens(self.shape, step) / modeled_prompt_tokens(self.shape, reference),
        )
        return self.measured[reference] * scale + self.additive_s

    def _reference_step(self, step: int) -> int:
        steps = sorted(self.measured)
        if self.harness == "h2" and self.shape.image_max < step:
            fold_steps = [s for s in steps if _is_fold_step(s, self.shape)]
            if _is_fold_step(step, self.shape) and fold_steps:
                return fold_steps[-1]
            plain = [s for s in steps if not _is_fold_step(s, self.shape)]
            tail = plain[-2:] if plain else steps[-2:]
            return max(tail, key=lambda s: self.measured[s])
        tail = steps[-2:]
        return max(tail, key=lambda s: self.measured[s])

    def mean_prompt_tokens(self, steps: int) -> float:
        return sum(modeled_prompt_tokens(self.shape, t) for t in range(1, steps + 1)) / steps


def _is_fold_step(step: int, shape: HarnessShape) -> bool:
    """Steps at which cua-speedrun folds another block (prefix changes, cache misses)."""
    if step <= shape.image_max:
        return False
    previous = step - 1
    return folded_prefix(step, shape.image_max, shape.fold_size) != folded_prefix(
        previous, shape.image_max, shape.fold_size
    )


def shape_from_point(point: Mapping[str, Any], image_tokens: int) -> HarnessShape:
    params = point["params"]
    return HarnessShape(
        harness=params["harness"],
        system_tokens=int(params["system_tokens"]),
        task_tokens=int(params["task_tokens"]),
        action_tokens=int(params["action_tokens"]),
        response_tokens=int(params["output_tokens"]),
        a11y_tokens=int(params["a11y_tokens"]),
        image_tokens=image_tokens,
        history_n=int(params["history_n"]),
        image_max=int(params.get("image_max", 20)),
        fold_size=int(params.get("fold_size", 10)),
    )


def closed_loop_gpu_hours(
    profile: Profile,
    *,
    steps: int,
    episodes: int,
    t_env_s: float,
    gpus: int,
    multiplier: float,
    vm_per_replica: int | None = None,
) -> float:
    vms = vm_per_replica or profile.vm_per_replica
    total = sum(t_env_s + multiplier * profile.latency(t) for t in range(1, steps + 1))
    return gpus * math.ceil(episodes / vms) * total / 3600.0


def open_loop_gpu_hours(
    *, steps: int, episodes: int, gpus: int, multiplier: float, requests_per_s: float
) -> float:
    if requests_per_s <= 0:
        raise BudgetError("open-loop request rate must be positive")
    return episodes * steps * gpus * multiplier / requests_per_s / 3600.0


def _tpot_tail_s(point: Mapping[str, Any], steps: Sequence[int]) -> float | None:
    values = []
    for step in steps:
        entry = point["result"]["per_step"].get(str(step))
        if entry and entry["tpot_ms"]["p90"] is not None:
            values.append(entry["tpot_ms"]["p90"] / 1000.0)
    return max(values) if values else None


def build_profiles(
    points: Mapping[str, Mapping[str, Any]], *, image_tokens: int, unmeasured_multiplier: float
) -> dict[str, Profile]:
    """Assemble the four Q2 harness profiles from job A (rules fixed in the preregistration)."""
    for required in ("r1", "r3"):
        if not is_valid(points.get(required)):
            raise BudgetError(f"required replay point {required} is missing or invalid")
    r1, r3 = points["r1"], points["r3"]
    h1_shape = shape_from_point(r1, image_tokens)
    h2_shape = shape_from_point(r3, image_tokens)
    profiles = {
        "h1-screenshot": Profile(
            "h1-screenshot", "h1", step_latencies(r1), int(r1["params"]["episodes"]), h1_shape
        ),
        "h2-screenshot": Profile(
            "h2-screenshot", "h2", step_latencies(r3), int(r3["params"]["episodes"]), h2_shape
        ),
    }
    h1_curve = profiles["h1-screenshot"]
    r1_last = max(h1_curve.measured)
    steady_r1 = max(h1_curve.measured[s] for s in sorted(h1_curve.measured)[-2:])
    if is_valid(points.get("r2")):
        r2 = points["r2"]
        r2_curve = step_latencies(r2)
        profiles["h1-a11y"] = Profile(
            "h1-a11y",
            "h1",
            r2_curve,
            int(r2["params"]["episodes"]),
            shape_from_point(r2, image_tokens),
        )
        steady_r2 = max(r2_curve[s] for s in sorted(r2_curve)[-2:])
        a11y_penalty = max(0.0, steady_r2 - steady_r1)
        a11y_flags: tuple[str, ...] = ()
    else:
        a11y_tokens = 6144
        share = a11y_tokens / modeled_prompt_tokens(h1_shape, r1_last)
        a11y_penalty = steady_r1 * share * unmeasured_multiplier
        a11y_flags = ("a11y-unmeasured-prompt-proportional-x1.5",)
        profiles["h1-a11y"] = Profile(
            "h1-a11y",
            "h1",
            h1_curve.measured,
            h1_curve.vm_per_replica,
            h1_shape,
            additive_s=a11y_penalty,
            flags=a11y_flags,
        )

    r3_curve = profiles["h2-screenshot"]
    if is_valid(points.get("r4")):
        r4 = points["r4"]
        r4_curve = step_latencies(r4)
        if not r4_curve:
            raise BudgetError("r4 is valid but has no complete step")
        warm = max(r4_curve) if len(r4_curve) > 1 else min(r4_curve)
        if warm not in r3_curve.measured:
            raise BudgetError(f"r3 has no measured step {warm} to difference against r4")
        think_penalty = max(0.0, r4_curve[warm] - r3_curve.measured[warm])
        think_flags: tuple[str, ...] = ()
    else:
        tail = _tpot_tail_s(points["r3"], sorted(r3_curve.measured)[-6:])
        if tail is None:
            raise BudgetError("thinking penalty cannot be estimated without r4 or r3 TPOT")
        output_extra = 2048 - int(points["r3"]["params"]["output_tokens"])
        think_penalty = output_extra * tail * unmeasured_multiplier
        think_flags = ("thinking-unmeasured-tpot-p90-x1.5",)
    profiles["h2-thinking-screenshot"] = Profile(
        "h2-thinking-screenshot",
        "h2",
        r3_curve.measured,
        r3_curve.vm_per_replica,
        h2_shape,
        additive_s=think_penalty,
        flags=think_flags,
    )
    profiles["h2-thinking-a11y"] = Profile(
        "h2-thinking-a11y",
        "h2",
        r3_curve.measured,
        r3_curve.vm_per_replica,
        h2_shape,
        additive_s=think_penalty + a11y_penalty,
        flags=think_flags + a11y_flags,
    )
    return profiles


def frontend_ratio(
    job_a: Mapping[str, Mapping[str, Any]], rule: Mapping[str, Any] | None
) -> dict[str, Any]:
    """F1: PNG-over-JPEG throughput ratio; applied to the open-loop bound above the threshold."""
    if not rule:
        return {"applied": False, "ratio": None, "reason": "no rule"}
    control, reference = job_a.get(rule["point"]), job_a.get(rule["reference"])
    if not (is_valid(control) and is_valid(reference)):
        return {"applied": False, "ratio": None, "reason": "F1 or its reference is not valid"}
    ratio = control["result"]["request_throughput"] / reference["result"]["request_throughput"]
    applied = abs(ratio - 1.0) > float(rule["threshold"])
    return {"applied": applied, "ratio": ratio, "threshold": float(rule["threshold"])}


def rung_multipliers(
    rungs: Mapping[str, Mapping[str, Any]],
    *,
    job_a: Mapping[str, Mapping[str, Any]],
    job_c: Mapping[str, Mapping[str, Any]] | None,
    x1_outcome: str,
    unmeasured_multiplier: float,
) -> dict[str, dict[str, Any]]:
    """m_r: measured open-loop ratio to the 9B where job C ran, else the active-parameter rule."""
    reference = job_a.get("a1a")
    out: dict[str, dict[str, Any]] = {}
    for name, rung in rungs.items():
        source = rung["source"]
        active_ratio = float(rung["active_params_b"]) / 9.0
        if source in {"measured", "qwen3.5-9b"}:
            out[name] = {
                "multiplier": 1.0,
                "basis": "qwen3.5-9b measured",
                "gpus": int(rung["gpus"]),
            }
            continue
        point = (job_c or {}).get(str(rung.get("open_loop_point")))
        if is_valid(point) and is_valid(reference):
            ratio = (
                reference["result"]["request_throughput"] / point["result"]["request_throughput"]
            )
            penalty = 1.0 if x1_outcome == "pass" else unmeasured_multiplier
            basis = "job-c open-loop ratio" + ("" if penalty == 1.0 else " x1.5 (X1 not passed)")
            out[name] = {"multiplier": ratio * penalty, "basis": basis, "gpus": int(rung["gpus"])}
        else:
            out[name] = {
                "multiplier": max(1.0, active_ratio) * unmeasured_multiplier,
                "basis": "unmeasured: max(1, active params / 9B) x1.5",
                "gpus": int(rung["gpus"]),
            }
    return out


def project_q2(
    budget: Mapping[str, Any],
    *,
    job_a: Mapping[str, Mapping[str, Any]],
    job_c: Mapping[str, Mapping[str, Any]] | None,
    x1_outcome: str,
) -> dict[str, Any]:
    q2 = budget["q2"]
    multiplier_unmeasured = float(q2["unmeasured_rung_multiplier"])
    profiles = build_profiles(
        job_a, image_tokens=int(q2["image_tokens"]), unmeasured_multiplier=multiplier_unmeasured
    )
    rungs = rung_multipliers(
        q2["rungs"],
        job_a=job_a,
        job_c=job_c,
        x1_outcome=x1_outcome,
        unmeasured_multiplier=multiplier_unmeasured,
    )
    reference = q2["open_loop_reference"]
    open_point = job_a.get(reference["point"])
    open_rate = open_point["result"]["request_throughput"] if is_valid(open_point) else None
    frontend = frontend_ratio(job_a, q2.get("frontend_correction"))
    if open_rate is not None and frontend["applied"]:
        open_rate *= frontend["ratio"]
    open_tokens = None
    if is_valid(open_point):
        open_tokens = open_point["result"]["prompt_tokens"] / max(
            1, open_point["result"]["completed"]
        )
    profile_for_cell = {
        ("h1", "screenshot"): "h1-screenshot",
        ("h1", "a11y"): "h1-a11y",
        ("h2", "screenshot"): "h2-thinking-screenshot",
        ("h2", "a11y"): "h2-thinking-a11y",
    }

    def total(
        steps_override: int | None, t_env: float, vm_cap: int | None
    ) -> tuple[float, list[dict[str, Any]]]:
        rows = []
        grand = 0.0
        for rung_name, rung in rungs.items():
            for (harness, observation), profile_name in profile_for_cell.items():
                profile = profiles[profile_name]
                steps = steps_override or int(q2["step_caps"][harness])
                vms = (
                    profile.vm_per_replica
                    if vm_cap is None
                    else min(vm_cap, profile.vm_per_replica)
                )
                closed = closed_loop_gpu_hours(
                    profile,
                    steps=steps,
                    episodes=int(q2["episodes_per_cell"]),
                    t_env_s=t_env,
                    gpus=rung["gpus"],
                    multiplier=rung["multiplier"],
                    vm_per_replica=vms,
                )
                opened = None
                if open_rate and open_tokens:
                    cell_rate = open_rate * open_tokens / profile.mean_prompt_tokens(steps)
                    opened = open_loop_gpu_hours(
                        steps=steps,
                        episodes=int(q2["episodes_per_cell"]),
                        gpus=rung["gpus"],
                        multiplier=rung["multiplier"],
                        requests_per_s=cell_rate,
                    )
                cell = max(closed, opened or 0.0)
                grand += cell
                rows.append(
                    {
                        "rung": rung_name,
                        "harness": harness,
                        "observation": observation,
                        "profile": profile_name,
                        "steps": steps,
                        "vm_per_replica": vms,
                        "closed_loop_gpu_hours": closed,
                        "open_loop_gpu_hours": opened,
                        "gpu_hours": cell,
                        "rung_multiplier": rung["multiplier"],
                        "flags": list(profile.flags)
                        + ([] if rung["multiplier"] == 1.0 else [rung["basis"]]),
                    }
                )
        return grand, rows

    primary_total, rows = total(None, float(q2["t_env_s"]), None)
    sensitivity = []
    for steps in q2["sensitivity"]["steps"]:
        for t_env in q2["sensitivity"]["t_env_s"]:
            for vms in q2["sensitivity"]["vm_pool"]:
                value, _ = total(int(steps), float(t_env), int(vms))
                sensitivity.append(
                    {"steps": steps, "t_env_s": t_env, "vm_cap": vms, "gpu_hours": value}
                )
    if primary_total > float(q2["rescope_above_gpu_hours"]):
        decision = "rescope-before-gauntlet"
    elif primary_total < float(q2["overestimate_below_gpu_hours"]):
        decision = "dossier-overestimated"
    else:
        decision = "within-dossier-range"
    return {
        "total_gpu_hours": primary_total,
        "decision": decision,
        "cells": rows,
        "rungs": rungs,
        "profiles": {
            name: {
                "measured_steps": sorted(profile.measured),
                "vm_per_replica": profile.vm_per_replica,
                "additive_s": profile.additive_s,
                "flags": list(profile.flags),
            }
            for name, profile in profiles.items()
        },
        "open_loop_reference_rate": open_rate,
        "frontend_correction": frontend,
        "sensitivity": sensitivity,
    }


def per_completion_gpu_s(point: Mapping[str, Any], gpus: int) -> float:
    result = point["result"]
    completions = int(result["completions"])
    if completions <= 0:
        raise BudgetError(f"{point.get('point_id')} has no completions")
    return gpus * float(result["duration_s"]) / completions


def project_q1(
    budget: Mapping[str, Any], *, job_b: Mapping[str, Mapping[str, Any]], x1_outcome: str
) -> dict[str, Any]:
    q1 = budget["q1"]
    gpus = int(q1["gpus"])
    completions = int(q1["completions"])
    penalty = 1.0 if x1_outcome == "pass" else float(budget["q2"]["unmeasured_rung_multiplier"])
    flags = [] if penalty == 1.0 else [f"dummy-weights-unvalidated-x{penalty} (X1 {x1_outcome})"]
    per_turn: dict[str, float] = {}
    for name in q1["turn_points"]:
        point = job_b.get(name)
        if is_valid(point):
            per_turn[name] = per_completion_gpu_s(point, gpus)
            continue
        fallback = q1.get("turn_fallbacks", {}).get(name)
        if fallback and is_valid(job_b.get(fallback)):
            per_turn[name] = per_completion_gpu_s(job_b[fallback], gpus)
            flags.append(f"{name}-unmeasured-used-{fallback}")
            continue
        raise BudgetError(f"Q1 turn point {name} is missing or invalid and has no fallback")
    single = completions * per_turn[q1["single_turn_point"]] * penalty / 3600.0
    three = completions * sum(per_turn.values()) * penalty / 3600.0
    exceeded = single > float(q1["single_turn_cap_gpu_hours"]) or three > float(
        q1["three_turn_cap_gpu_hours"]
    )
    return {
        "per_completion_gpu_s": per_turn,
        "single_turn_gpu_hours": single,
        "three_turn_gpu_hours": three,
        "decision": "cut-turns-tokens-or-tasks-before-gauntlet" if exceeded else "within-cap",
        "flags": flags,
        "multiplier": penalty,
    }
