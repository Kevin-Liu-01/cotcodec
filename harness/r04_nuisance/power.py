"""Operating characteristics of R04's cell and arm readings (standard library only, exact).

Model, per cell, against the control:

* golds: ``N_GOLD`` independent items, each truly discordant with probability ``r_gold``;
* S1a pass states: the registered population's tasks with their state counts
  (``S1A_PASS_STATES_PER_TASK``, from S1a's committed records); a task is susceptible with
  probability ``r_task`` and each of its states is then discordant with probability ``q``
  (states of one task share the task's checker and document, so effects cluster); the
  reading counts tasks with at least one confirmed discordant state;
* harness noise: an item shows a spurious discordance in a run with probability ``p0``,
  independently across runs; a discordance counts only if both confirmation rounds
  reproduce it, so a spurious one counts with probability ``p0 ** 3``, while a true one (a
  deterministic effect of the nuisance factor) always reproduces.

Readings (``analysis.cell_reading``): DRIFT if at least ``DRIFT_MIN`` confirmed discordant
golds or S1a tasks, INVARIANT if none, MINOR otherwise. The gold count is binomial and the
task count Poisson-binomial (computed exactly), and the two are independent, so every
probability here is exact; nothing is simulated.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from harness.q2_mutation.stats import binomial_cdf, exact_upper_bound, zero_event_upper_bound

DRIFT_MIN = 3
N_GOLD = 92
# Distinct office-exposed pass states per task in S1a's A1 records (a1.jsonl, 2026-10-10):
# 270 states on 32 tasks.
S1A_PASS_STATES_PER_TASK = (
    1, 1, 1, 2, 3, 3, 3, 3, 3, 4, 4, 4, 5, 5, 7, 7,
    8, 10, 10, 12, 12, 12, 13, 14, 14, 14, 15, 16, 16, 16, 16, 16,
)  # fmt: skip
R_GOLD = (0.0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.075, 0.10)
R_TASK = (0.0, 0.03, 0.05, 0.075, 0.10, 0.15, 0.20)
Q_STATE = (0.1, 0.5, 1.0)
P0 = (0.0, 0.01, 0.05, 0.10)
PRIMARY_CELLS = 11


def gold_counts(r: float, p0: float, n: int = N_GOLD) -> list[float]:
    """P(k = 0), P(k = 1 or 2), P(k >= DRIFT_MIN) confirmed discordant golds."""
    p = r + (1 - r) * p0**3
    zero = binomial_cdf(0, n, p)
    upto = binomial_cdf(DRIFT_MIN - 1, n, p)
    return [zero, upto - zero, 1 - upto]


def gold_probs(r: float, p0: float, n: int = N_GOLD) -> dict[str, float]:
    zero, mid, drift = gold_counts(r, p0, n)
    return {"p_item": r + (1 - r) * p0**3, "zero": zero, "one_or_two": mid, "drift": drift}


def task_hit_probability(m: int, r_task: float, q: float, p0: float) -> float:
    s = p0**3
    miss = (1 - r_task) * (1 - s) ** m + r_task * ((1 - q) * (1 - s)) ** m
    return 1 - miss


def poisson_binomial(probs: list[float]) -> list[float]:
    dist = [1.0]
    for p in probs:
        nxt = [0.0] * (len(dist) + 1)
        for k, mass in enumerate(dist):
            nxt[k] += mass * (1 - p)
            nxt[k + 1] += mass * p
        dist = nxt
    return dist


def task_counts(r_task: float, q: float, p0: float) -> list[float]:
    dist = poisson_binomial(
        [task_hit_probability(m, r_task, q, p0) for m in S1A_PASS_STATES_PER_TASK]
    )
    zero = dist[0]
    upto = sum(dist[:DRIFT_MIN])
    return [zero, upto - zero, 1 - upto]


def cell_oc(r_gold: float, r_task: float, q: float, p0: float) -> dict[str, Any]:
    g0, g12, gd = gold_counts(r_gold, p0)
    t0, t12, td = task_counts(r_task, q, p0)
    invariant = g0 * t0
    drift = 1 - (g0 + g12) * (t0 + t12)
    return {
        "r_gold": r_gold, "r_task": r_task, "q": q, "p0": p0,
        "gold_drift": gd, "gold_zero": g0, "s1a_drift": td, "s1a_zero": t0,
        "p_invariant": invariant, "p_drift": drift, "p_minor": 1 - invariant - drift,
    }  # fmt: skip


def rate_for_power(power: float, n: int = N_GOLD) -> float:
    low, high = 0.0, 1.0
    for _ in range(100):
        mid = (low + high) / 2
        if 1 - binomial_cdf(DRIFT_MIN - 1, n, mid) < power:
            low = mid
        else:
            high = mid
    return high


def task_rate_for_power(power: float, q: float) -> float:
    low, high = 0.0, 1.0
    for _ in range(60):
        mid = (low + high) / 2
        if task_counts(mid, q, 0.0)[2] < power:
            low = mid
        else:
            high = mid
    return high


def run() -> dict[str, Any]:
    grid = [
        cell_oc(r_gold, r_task, q, p0)
        for p0 in P0
        for q in Q_STATE
        for r_gold in R_GOLD
        for r_task in R_TASK
    ]
    familywise = {}
    for p0 in P0:
        row = cell_oc(0.0, 0.0, 0.5, p0)
        familywise[str(p0)] = {
            "per_cell_false_drift": row["p_drift"],
            "per_cell_false_not_invariant": 1 - row["p_invariant"],
            "false_drift_any_of_11": 1 - (1 - row["p_drift"]) ** PRIMARY_CELLS,
            "false_not_invariant_any_of_11": 1 - row["p_invariant"] ** PRIMARY_CELLS,
        }
    tasks = len(S1A_PASS_STATES_PER_TASK)
    return {
        "schema": "r04-power-v2",
        "model": __doc__,
        "drift_min": DRIFT_MIN,
        "n_gold": N_GOLD,
        "s1a_pass_tasks": tasks,
        "s1a_pass_states": sum(S1A_PASS_STATES_PER_TASK),
        "bounds": {
            "gold_zero_event_upper95": zero_event_upper_bound(N_GOLD),
            "gold_one_event_upper95": exact_upper_bound(1, N_GOLD),
            "gold_two_event_upper95": exact_upper_bound(2, N_GOLD),
            "s1a_task_zero_event_upper95": zero_event_upper_bound(tasks),
            "s1a_task_two_event_upper95": exact_upper_bound(2, tasks),
            "gold_rate_for_drift_power_0_8": rate_for_power(0.8),
            "gold_rate_for_drift_power_0_9": rate_for_power(0.9),
            "task_rate_for_drift_power_0_8": {str(q): task_rate_for_power(0.8, q) for q in Q_STATE},
        },
        "grid": grid,
        "familywise_under_null": familywise,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    result = run()
    args.out.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result["bounds"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
