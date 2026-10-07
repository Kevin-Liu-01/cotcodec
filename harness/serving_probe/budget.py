"""Preregistered budget rules for serving-throughput-probe-v1.

Pure functions over the per-point JSON the probe writes. Nothing here fits a
model or chooses a rule after seeing data: every extrapolation, fallback and
threshold is fixed in the contract and the preregistration, and every fallback
is recorded as a flag next to the number it produced.

Q2 (closed-loop computer-use episodes, one cell per rung x harness x observation):

    GPU-h_closed = g * ceil(E / V) * sum_{t=1..T} (t_env + m_r * L(t)) / 3600
    GPU-h_open   = E * T * g * m_r / r_cell / 3600
    r_cell       = r_ref / max(P_cell / P_ref, O_cell / O_ref)
    GPU-h_cell   = max(GPU-h_closed, GPU-h_open) * noise_A1

Q1 (offline n=8 sampling): GPU-h = completions * sum_turns(GPU-s per completion)
* x1_penalty * noise_B1 / 3600.
"""

from __future__ import annotations

import dataclasses
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


def per_request_tokens(point: Mapping[str, Any]) -> tuple[float, float]:
    """Mean (prompt, output) tokens per completed request of an open-loop point."""
    result = point["result"]
    completed = int(result["completed"])
    if completed <= 0:
        raise BudgetError(f"{point.get('point_id')} has no completed requests")
    return float(result["prompt_tokens"]) / completed, float(result["output_tokens"]) / completed


def evaluate_x1(
    points: Mapping[str, Mapping[str, Any]],
    *,
    max_relative_delta: float,
    a1_seed_points: Sequence[str] = ("a1a", "a1b", "a1c"),
) -> dict[str, Any]:
    """Dummy-weight admissibility (control X1) from job A's points.

    ``pass`` needs both deltas within the threshold and every A1 seed point valid
    with a relative range within the same threshold; anything less is not a pass.
    """
    needed = ("a1a", "r1", "x1-a1", "x1-r1")
    missing = [name for name in needed if not is_valid(points.get(name))]
    seed_values = [
        points[name]["result"]["request_throughput"]
        for name in a1_seed_points
        if is_valid(points.get(name))
    ]
    seed_range = relative_range(seed_values)
    seeds_valid = len(seed_values)
    if missing:
        return {
            "outcome": "not-run",
            "missing_or_invalid": missing,
            "a1_seed_range": seed_range,
            "a1_seeds_valid": seeds_valid,
            "threshold": max_relative_delta,
        }
    a1_delta = relative_delta(
        points["x1-a1"]["result"]["request_throughput"],
        points["a1a"]["result"]["request_throughput"],
    )
    r1_delta = relative_delta(
        replay_mean_latency(points["x1-r1"]), replay_mean_latency(points["r1"])
    )
    within = a1_delta <= max_relative_delta and r1_delta <= max_relative_delta
    reason = None
    if not within:
        outcome = "fail"
    elif seeds_valid < len(a1_seed_points):
        outcome, reason = "underpowered", "fewer than three valid A1 seed points"
    elif seed_range is None or seed_range > max_relative_delta:
        outcome, reason = "underpowered", "A1 seed range above the threshold"
    else:
        outcome = "pass"
    return {
        "outcome": outcome,
        "reason": reason,
        "a1_relative_delta": a1_delta,
        "r1_relative_delta": r1_delta,
        "a1_seed_range": seed_range,
        "a1_seeds_valid": seeds_valid,
        "threshold": max_relative_delta,
    }


def stability(
    points: Mapping[str, Mapping[str, Any]],
    names: Sequence[str],
    limit: float,
    metric: str = "request_throughput",
) -> dict[str, Any]:
    """Seed spread of a throughput metric and the noise multiplier it implies.

    Every seed valid and range <= ``limit``: multiplier 1. Range above ``limit``
    (UNSTABLE): max/min of the seeds. Fewer than all seeds valid: the larger of
    ``1 + limit`` and max/min of the valid ones.
    """
    values = [float(points[name]["result"][metric]) for name in names if is_valid(points.get(name))]
    spread = relative_range(values)
    complete = len(values) == len(names)
    unstable = spread is not None and spread > limit
    ratio = (max(values) / min(values)) if len(values) >= 2 and min(values) > 0 else None
    if complete and not unstable:
        multiplier, basis = 1.0, "stable"
    elif complete:
        multiplier, basis = float(ratio or 1.0 + limit), "unstable: max/min of the seeds"
    else:
        multiplier = max(1.0 + limit, ratio or 0.0)
        basis = f"incomplete ({len(values)} of {len(names)} valid): max(1 + limit, max/min)"
    return {
        "points": list(names),
        "metric": metric,
        "valid": len(values),
        "mean": (sum(values) / len(values)) if values else None,
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "relative_range": spread,
        "limit": limit,
        "unstable": unstable,
        "complete": complete,
        "noise_multiplier": multiplier,
        "basis": basis,
    }


@dataclass(frozen=True)
class Profile:
    """A per-step latency curve L(t) with its measured V and extrapolation shape.

    ``shape`` describes the replay the curve was measured on and drives the
    extrapolation; ``cell_a11y_tokens`` and ``cell_output_tokens`` describe the
    cell the profile prices (its open-loop size and context check).
    """

    name: str
    harness: str
    measured: dict[int, float]
    vm_per_replica: int
    shape: HarnessShape
    additive_s: float = 0.0
    flags: tuple[str, ...] = ()
    cell_a11y_tokens: int | None = None
    cell_output_tokens: int | None = None

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

    @property
    def cell_shape(self) -> HarnessShape:
        if self.cell_a11y_tokens is None:
            return self.shape
        return dataclasses.replace(self.shape, a11y_tokens=int(self.cell_a11y_tokens))

    @property
    def cell_output(self) -> int:
        if self.cell_output_tokens is None:
            return self.shape.response_tokens
        return int(self.cell_output_tokens)

    def mean_prompt_tokens(self, steps: int) -> float:
        shape = self.cell_shape
        return sum(modeled_prompt_tokens(shape, t) for t in range(1, steps + 1)) / steps

    def max_context_tokens(self, steps: int) -> int:
        """Largest modelled prompt plus output over steps 1..``steps`` of the cell."""
        shape = self.cell_shape
        return max(modeled_prompt_tokens(shape, t) for t in range(1, steps + 1)) + self.cell_output


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


def open_loop_cell_rate(reference: Mapping[str, Any], profile: Profile, steps: int) -> float:
    """r_cell: the reference rate divided by the larger of the prompt and output ratios.

    GPU time per request grows with both its prompt and its output; the larger
    of the two ratios bounds any mix of the two from above, so the rate it gives
    is never above the reference scaled by either one alone.
    """
    prompt_ratio = profile.mean_prompt_tokens(steps) / float(reference["prompt_tokens"])
    output_ratio = profile.cell_output / float(reference["output_tokens"])
    return float(reference["rate"]) / max(prompt_ratio, output_ratio)


def _tpot_tail_s(point: Mapping[str, Any], steps: Sequence[int]) -> float | None:
    values = []
    for step in steps:
        entry = point["result"]["per_step"].get(str(step))
        if entry and entry["tpot_ms"]["p90"] is not None:
            values.append(entry["tpot_ms"]["p90"] / 1000.0)
    return max(values) if values else None


def build_profiles(
    points: Mapping[str, Mapping[str, Any]],
    *,
    image_tokens: int,
    unmeasured_multiplier: float,
    a11y_tokens: int,
    thinking_output_tokens: int,
) -> dict[str, Profile]:
    """Assemble the four Q2 harness profiles from job A (rules fixed in the preregistration)."""
    for required in ("r1", "r3"):
        if not is_valid(points.get(required)):
            raise BudgetError(f"required replay point {required} is missing or invalid")
    r1, r3 = points["r1"], points["r3"]
    h1_shape = shape_from_point(r1, image_tokens)
    h2_shape = shape_from_point(r3, image_tokens)
    h1_curve = Profile(
        "h1-screenshot", "h1", step_latencies(r1), int(r1["params"]["episodes"]), h1_shape
    )
    r3_curve = Profile(
        "h2-screenshot", "h2", step_latencies(r3), int(r3["params"]["episodes"]), h2_shape
    )
    if not h1_curve.measured or not r3_curve.measured:
        raise BudgetError("r1 or r3 has no step that every episode completed")
    profiles = {"h1-screenshot": h1_curve}
    r1_last = max(h1_curve.measured)
    steady_r1 = max(h1_curve.measured[s] for s in sorted(h1_curve.measured)[-2:])
    if is_valid(points.get("r2")):
        r2 = points["r2"]
        r2_curve = step_latencies(r2)
        if not r2_curve:
            raise BudgetError("r2 is valid but has no complete step")
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
            cell_a11y_tokens=a11y_tokens,
        )

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
        tail = _tpot_tail_s(r3, sorted(r3_curve.measured)[-6:])
        if tail is None:
            raise BudgetError("thinking penalty cannot be estimated without r4 or r3 TPOT")
        output_extra = thinking_output_tokens - int(r3["params"]["output_tokens"])
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
        cell_output_tokens=thinking_output_tokens,
    )
    profiles["h2-thinking-a11y"] = Profile(
        "h2-thinking-a11y",
        "h2",
        r3_curve.measured,
        r3_curve.vm_per_replica,
        h2_shape,
        additive_s=think_penalty + a11y_penalty,
        flags=think_flags + a11y_flags,
        cell_a11y_tokens=a11y_tokens,
        cell_output_tokens=thinking_output_tokens,
    )
    return profiles


def frontend_ratio(
    job_a: Mapping[str, Mapping[str, Any]], rule: Mapping[str, Any] | None
) -> dict[str, Any]:
    """F1: PNG-over-JPEG request-throughput ratio at the A1 shape.

    Applied to the open-loop reference rate only when PNG is slower by more than
    the threshold (ratio < 1 - threshold); it can raise the bound, never lower it.
    """
    if not rule:
        return {"applied": False, "ratio": None, "reason": "no rule"}
    control, reference = job_a.get(rule["point"]), job_a.get(rule["reference"])
    threshold = float(rule["threshold"])
    if not (is_valid(control) and is_valid(reference)):
        return {
            "applied": False,
            "ratio": None,
            "threshold": threshold,
            "reason": "F1 or its reference is not valid",
        }
    ratio = control["result"]["request_throughput"] / reference["result"]["request_throughput"]
    return {"applied": ratio < 1.0 - threshold, "ratio": ratio, "threshold": threshold}


def open_loop_reference(
    job_a: Mapping[str, Mapping[str, Any]],
    rule: Mapping[str, Any],
    frontend: Mapping[str, Any],
) -> dict[str, Any]:
    """r_ref, P_ref, O_ref from a2; else the slowest valid fallback point; else no budget."""
    flags: list[str] = []
    point = job_a.get(rule["point"])
    if is_valid(point):
        name = str(rule["point"])
    else:
        candidates = [
            str(candidate)
            for candidate in rule.get("fallback_points", [])
            if is_valid(job_a.get(str(candidate)))
        ]
        if not candidates:
            raise BudgetError(
                f"open-loop reference {rule['point']} and every fallback point are missing "
                "or invalid"
            )
        name = min(candidates, key=lambda key: job_a[key]["result"]["request_throughput"])
        point = job_a[name]
        flags.append(f"open-loop-reference-{name}-slowest-fallback ({rule['point']} not valid)")
    prompt_tokens, output_tokens = per_request_tokens(point)
    rate = float(point["result"]["request_throughput"])
    measured_rate = rate
    if frontend.get("applied"):
        rate *= float(frontend["ratio"])
        flags.append("open-loop-rate-x-f1-ratio")
    return {
        "point": name,
        "measured_rate": measured_rate,
        "rate": rate,
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "flags": flags,
    }


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
    unstable_limit: float,
    max_model_len: int,
) -> dict[str, Any]:
    q2 = budget["q2"]
    multiplier_unmeasured = float(q2["unmeasured_rung_multiplier"])
    profiles = build_profiles(
        job_a,
        image_tokens=int(q2["image_tokens"]),
        unmeasured_multiplier=multiplier_unmeasured,
        a11y_tokens=int(q2["a11y_tokens"]),
        thinking_output_tokens=int(q2["thinking_output_tokens"]),
    )
    rungs = rung_multipliers(
        q2["rungs"],
        job_a=job_a,
        job_c=job_c,
        x1_outcome=x1_outcome,
        unmeasured_multiplier=multiplier_unmeasured,
    )
    frontend = frontend_ratio(job_a, q2.get("frontend_correction"))
    reference = open_loop_reference(job_a, q2["open_loop_reference"], frontend)
    noise = stability(job_a, tuple(q2["stability_points"]), unstable_limit)
    noise_factor = float(noise["noise_multiplier"])
    noise_flags = (
        [] if noise_factor == 1.0 else [f"a1-noise-x{noise_factor:.4f} ({noise['basis']})"]
    )
    cells = [
        (str(cell["harness"]), str(cell["observation"]), str(cell["profile"]))
        for cell in q2["cells"]
    ]
    for _harness, _observation, profile_name in cells:
        if profile_name not in profiles:
            raise BudgetError(f"cell profile {profile_name} is not a built profile")

    def total(
        steps_override: int | None, t_env: float, vm_cap: int | None, *, primary: bool
    ) -> tuple[float, list[dict[str, Any]]]:
        rows = []
        grand = 0.0
        for rung_name, rung in rungs.items():
            for harness, observation, profile_name in cells:
                profile = profiles[profile_name]
                steps = steps_override or int(q2["step_caps"][harness])
                context = profile.max_context_tokens(steps)
                if primary and context > max_model_len:
                    raise BudgetError(
                        f"cell {harness}/{observation} reaches {context} tokens by step {steps}, "
                        f"above max_model_len {max_model_len}"
                    )
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
                cell_rate = open_loop_cell_rate(reference, profile, steps)
                opened = open_loop_gpu_hours(
                    steps=steps,
                    episodes=int(q2["episodes_per_cell"]),
                    gpus=rung["gpus"],
                    multiplier=rung["multiplier"],
                    requests_per_s=cell_rate,
                )
                cell = max(closed, opened) * noise_factor
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
                        "open_loop_rate": cell_rate,
                        "binding": "open-loop" if opened > closed else "closed-loop",
                        "noise_multiplier": noise_factor,
                        "gpu_hours": cell,
                        "max_context_tokens": context,
                        "exceeds_max_model_len": context > max_model_len,
                        "rung_multiplier": rung["multiplier"],
                        "flags": list(profile.flags)
                        + list(reference["flags"])
                        + noise_flags
                        + ([] if rung["multiplier"] == 1.0 else [rung["basis"]]),
                    }
                )
        return grand, rows

    primary_total, rows = total(None, float(q2["t_env_s"]), None, primary=True)
    sensitivity = []
    for steps in q2["sensitivity"]["steps"]:
        for t_env in q2["sensitivity"]["t_env_s"]:
            for vms in q2["sensitivity"]["vm_pool"]:
                value, sens_rows = total(int(steps), float(t_env), int(vms), primary=False)
                sensitivity.append(
                    {
                        "steps": steps,
                        "t_env_s": t_env,
                        "vm_cap": vms,
                        "gpu_hours": value,
                        "cells_over_max_model_len": sum(
                            1 for row in sens_rows if row["exceeds_max_model_len"]
                        ),
                    }
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
                "cell_output_tokens": profile.cell_output,
                "cell_a11y_tokens": profile.cell_shape.a11y_tokens,
                "flags": list(profile.flags),
            }
            for name, profile in profiles.items()
        },
        "open_loop_reference": reference,
        "frontend_correction": frontend,
        "a1_noise": noise,
        "max_model_len": max_model_len,
        "sensitivity": sensitivity,
    }


def per_completion_gpu_s(point: Mapping[str, Any], gpus: int) -> float:
    result = point["result"]
    completions = int(result["completions"])
    if completions <= 0:
        raise BudgetError(f"{point.get('point_id')} has no completions")
    return gpus * float(result["duration_s"]) / completions


def project_q1(
    budget: Mapping[str, Any],
    *,
    job_b: Mapping[str, Mapping[str, Any]],
    x1_outcome: str,
    unstable_limit: float,
) -> dict[str, Any]:
    q1 = budget["q1"]
    gpus = int(q1["gpus"])
    completions = int(q1["completions"])
    penalty = 1.0 if x1_outcome == "pass" else float(budget["q2"]["unmeasured_rung_multiplier"])
    flags = [] if penalty == 1.0 else [f"dummy-weights-unvalidated-x{penalty} (X1 {x1_outcome})"]
    noise = stability(
        job_b, tuple(q1["stability_points"]), unstable_limit, metric="completions_per_s"
    )
    noise_factor = float(noise["noise_multiplier"])
    if noise_factor != 1.0:
        flags.append(f"b1-noise-x{noise_factor:.4f} ({noise['basis']})")
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
    scale = penalty * noise_factor / 3600.0
    single = completions * per_turn[q1["single_turn_point"]] * scale
    three = completions * sum(per_turn.values()) * scale
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
        "b1_noise": noise,
    }
