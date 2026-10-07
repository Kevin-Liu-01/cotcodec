"""Control X1 v2: dummy against real weights on identical prompt token sequences.

In serving-throughput-probe-v1, x1-r1's history carried the dummy engine's
outputs, which re-tokenised to other lengths: its mean prompt was 6.6% shorter
than r1's, and its 5.89% latency delta failed the 5% threshold without
comparing like with like. In v2 every replay uses prebuilt history and every
request returns its prompt token ids, so a1a/x1-a1 and r1/x1-r1 must have sent
the same token sequence for every request, at forced output lengths, before any
delta is read.

Thresholds (contract ``dummy_admissibility``):

* open loop: |x1-a1 - a1a| / a1a request throughput <= ``max_open_loop_delta``;
* replay: |mean latency of x1-r1 - that of r1| / that of r1 <= ``max_replay_latency_delta``;
* power: the replay delta's standard error (from both points' per-step standard
  errors) <= ``max_replay_delta_se``, and a1a, a1b, a1c valid with a relative
  range <= ``max_a1_seed_range``.

Outcomes, in this order: ``not-run`` (a1a, r1, x1-a1 or x1-r1 not valid),
``not-comparable`` (the prompt token sequences differ), ``fail`` (a delta above
its threshold), ``underpowered`` (deltas within thresholds but the power
conditions do not hold), ``pass``.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from harness.serving_probe.budget import (
    is_valid,
    relative_delta,
    relative_range,
    replay_mean_latency,
)
from harness.serving_probe_v2.client import compare_identity

PAIRS = (("a1a", "x1-a1"), ("r1", "x1-r1"))


def replay_mean_se(point: Mapping[str, Any]) -> float | None:
    """Standard error (s) of a replay's mean latency from its per-step standard errors.

    Every step of a valid replay has the same number of requests, so the mean
    over all requests is the mean of the step means, and its SE is
    sqrt(sum of squared step SEs) / number of steps.
    """
    per_step = point["result"]["per_step"]
    ses = [entry["latency_s"]["se"] for entry in per_step.values()]
    if not ses or any(se is None for se in ses):
        return None
    return math.sqrt(sum(float(se) ** 2 for se in ses)) / len(ses)


def replay_delta_se(reference: Mapping[str, Any], control: Mapping[str, Any]) -> float | None:
    """Relative standard error of the difference of two replay mean latencies."""
    first, second = replay_mean_se(reference), replay_mean_se(control)
    if first is None or second is None:
        return None
    return math.sqrt(first**2 + second**2) / replay_mean_latency(reference)


def evaluate_x1(
    points: Mapping[str, Mapping[str, Any]],
    rule: Mapping[str, Any],
    *,
    a1_seed_points: Sequence[str] = ("a1a", "a1b", "a1c"),
) -> dict[str, Any]:
    """Dummy-weight admissibility from job A's points (module docstring)."""
    open_limit = float(rule["max_open_loop_delta"])
    replay_limit = float(rule["max_replay_latency_delta"])
    se_limit = float(rule["max_replay_delta_se"])
    range_limit = float(rule["max_a1_seed_range"])
    seeds = [
        float(points[name]["result"]["request_throughput"])
        for name in a1_seed_points
        if is_valid(points.get(name))
    ]
    seed_range = relative_range(seeds)
    base: dict[str, Any] = {
        "thresholds": {
            "open_loop": open_limit,
            "replay_latency": replay_limit,
            "replay_delta_se": se_limit,
            "a1_seed_range": range_limit,
        },
        "a1_seed_range": seed_range,
        "a1_seeds_valid": len(seeds),
    }
    missing = [name for pair in PAIRS for name in pair if not is_valid(points.get(name))]
    if missing:
        return {**base, "outcome": "not-run", "missing_or_invalid": missing}
    identity = {
        f"{reference}/{control}": compare_identity(
            points[reference].get("request_identity"), points[control].get("request_identity")
        )
        for reference, control in PAIRS
    }
    base["identity"] = identity
    if not all(verdict["identical"] for verdict in identity.values()):
        return {**base, "outcome": "not-comparable", "reason": "prompt token sequences differ"}
    open_delta = relative_delta(
        points["x1-a1"]["result"]["request_throughput"],
        points["a1a"]["result"]["request_throughput"],
    )
    replay_delta = relative_delta(
        replay_mean_latency(points["x1-r1"]), replay_mean_latency(points["r1"])
    )
    delta_se = replay_delta_se(points["r1"], points["x1-r1"])
    out = {
        **base,
        "open_loop_relative_delta": open_delta,
        "replay_relative_delta": replay_delta,
        "replay_delta_se": delta_se,
        "replay_delta_z": None if not delta_se else replay_delta / delta_se,
        "reason": None,
    }
    if open_delta > open_limit or replay_delta > replay_limit:
        return {**out, "outcome": "fail"}
    if delta_se is None or delta_se > se_limit:
        return {**out, "outcome": "underpowered", "reason": "replay delta SE above its limit"}
    if len(seeds) < len(a1_seed_points):
        return {**out, "outcome": "underpowered", "reason": "fewer than three valid A1 seeds"}
    if seed_range is None or seed_range > range_limit:
        return {**out, "outcome": "underpowered", "reason": "A1 seed range above its limit"}
    return {**out, "outcome": "pass"}
