"""A4 volume plan: per-action-class certification with a family-wise bound.

Review finding: zero failures in 6,020 trials spread uniformly over the 86
gating entries bounds only the *uniform-mixture* per-trial failure rate
(0.05%). It bounds each entry only at about 4% (70 trials), it says nothing
about the Stage-1 action mix, and trials in one VM boot are not independent.

This plan makes the claim distribution-free over the Stage-1 action mix:

* Every device-reaching IR action in a gating entry belongs to one of seven
  classes (``CLASSES``). With zero failures, each class's executed actions
  bound that class's per-action failure rate. Each class gets at least
  ``ACTIONS_PER_CLASS`` executed actions, so all seven class bounds and the
  per-boot bound (eight statements) hold together at family-wise 95%
  (Bonferroni, alpha 0.05 / 8 each): every class rate is at most
  ``P_ACTION`` = 5e-4, whatever mix of classes a Stage-1 episode uses.
* Trials run in sessions of at most ``SESSION_TRIALS`` consecutive trials,
  each session a cold boot of a new VM container, and there are at least
  ``MIN_SESSIONS`` sessions. Zero failing sessions bounds the per-boot failure
  rate (a failure mode that strikes once per boot) at ``P_BOOT`` = 0.5%.
* A Stage-1 episode of at most 20 device actions then loses at most
  20 x 5e-4 + 0.5% = 1.5 percentage points to the action path (union bound).

Within a class the bound is on the catalog's own instances, weighted as the
plan weights them (each pure entry of the class gets the same number of
repetitions); it is not a bound on any one entry, and the per-entry bounds are
listed in the plan. Every gating entry keeps at least ``MIN_REPS`` repetitions.

Standard library only; ``build_plan`` is deterministic and its output is
committed as ``volume_plan.json`` (a test checks it), with the SHA-256 of the
realized session order computed by ``sessions`` with ``random.Random(43)``.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from typing import Any

from harness.q2.action_path.catalog import validate
from harness.q2.action_path.ir import EFFECT_FREE, Action, parse_sequence

CLASSES = ("click_left", "click_other", "move", "drag", "scroll", "type", "key")
P_ACTION = 5e-4
P_BOOT = 5e-3
FAMILY_ALPHA = 0.05
STATEMENTS = len(CLASSES) + 1  # seven class bounds and one per-boot bound
ALPHA_EACH = FAMILY_ALPHA / STATEMENTS
MIN_REPS = 70
SESSION_TRIALS = 60
SETTINGS = ("screenshot", "screenshot+a11y")
ORDER_SEED = 43


def zero_failure_n(p: float, alpha: float) -> int:
    """Smallest n with (1 - p)^n <= alpha: zero failures in n bounds the rate at p."""
    return math.ceil(math.log(alpha) / math.log1p(-p))


def upper_bound(n: int, alpha: float = 0.05) -> float | None:
    """One-sided upper confidence bound on a rate after zero failures in n trials."""
    return None if n <= 0 else 1.0 - alpha ** (1.0 / n)


ACTIONS_PER_CLASS = zero_failure_n(P_ACTION, ALPHA_EACH)
MIN_SESSIONS = zero_failure_n(P_BOOT, ALPHA_EACH)


def action_class(action: Action) -> str | None:
    """The Stage-1 device-action class of one IR action (None if it reaches no device)."""
    if action.op in EFFECT_FREE:
        return None
    if action.op == "click":
        plain = action.button == 1 and action.count == 1 and not action.modifiers
        return "click_left" if plain else "click_other"
    if action.op in ("move", "drag", "scroll", "type", "key"):
        return action.op
    raise ValueError(f"{action.op} has no Stage-1 class; it cannot be in a gating entry")


def entry_classes(actions: list[Action]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for action in actions:
        name = action_class(action)
        if name is not None:
            counts[name] = counts.get(name, 0) + 1
    return counts


def _even(n: int) -> int:
    return n + (n % 2)


def build_plan(data: dict[str, Any]) -> dict[str, Any]:
    gating = validate(data)["gating"]
    entries = {e["id"]: parse_sequence(e["actions"]) for e in data["entries"]}
    counts = {entry_id: entry_classes(entries[entry_id]) for entry_id in gating}
    reps = {entry_id: MIN_REPS for entry_id in gating}
    pure = {name: [e for e in gating if set(counts[e]) == {name}] for name in CLASSES}
    for name in CLASSES:
        if not pure[name]:
            raise ValueError(f"class {name} has no pure gating entry")
        mixed = sum(reps[e] * counts[e].get(name, 0) for e in reps if e not in pure[name])
        per_round = sum(counts[e][name] for e in pure[name])
        needed = max(0, ACTIONS_PER_CLASS - mixed)
        common = _even(max(MIN_REPS, math.ceil(needed / per_round)))
        for entry_id in pure[name]:
            reps[entry_id] = common
    totals = {name: 0 for name in CLASSES}
    for entry_id, n in reps.items():
        for name, k in counts[entry_id].items():
            totals[name] += n * k
    trials = sum(reps.values())
    per_setting = {s: trials // 2 for s in SETTINGS}
    sessions_per_setting = {
        s: max(math.ceil(MIN_SESSIONS / len(SETTINGS)), math.ceil(n / SESSION_TRIALS))
        for s, n in per_setting.items()
    }
    plan: dict[str, Any] = {
        "schema": "cotcodec-q2-volume-plan-v1",
        "layer": "L0-fixed",
        "rule": {
            "classes": list(CLASSES),
            "p_action": P_ACTION,
            "p_boot": P_BOOT,
            "family_alpha": FAMILY_ALPHA,
            "statements": STATEMENTS,
            "alpha_each": ALPHA_EACH,
            "actions_per_class_min": ACTIONS_PER_CLASS,
            "min_reps_per_entry": MIN_REPS,
            "session_trials_max": SESSION_TRIALS,
            "sessions_min": MIN_SESSIONS,
            "order_seed": ORDER_SEED,
            "settings": list(SETTINGS),
            "episode_actions": 20,
            "episode_loss_bound_pp": round(100 * (20 * P_ACTION + P_BOOT), 3),
        },
        "entries": {
            entry_id: {
                "reps": reps[entry_id],
                "classes": counts[entry_id],
                "pure_class": next((c for c in CLASSES if entry_id in pure[c]), None),
                "entry_upper_bound_95": round(upper_bound(reps[entry_id]) or 0.0, 6),
            }
            for entry_id in sorted(reps)
        },
        "class_actions": totals,
        "class_upper_bound_family_95": {
            name: round(upper_bound(n, ALPHA_EACH) or 0.0, 7) for name, n in totals.items()
        },
        "trials": trials,
        "trials_per_setting": per_setting,
        "sessions_per_setting": sessions_per_setting,
        "sessions": sum(sessions_per_setting.values()),
        "boot_upper_bound_family_95": round(
            upper_bound(sum(sessions_per_setting.values()), ALPHA_EACH) or 0.0, 6
        ),
    }
    plan["order_sha256"] = order_sha256(plan)
    return plan


def sessions(plan: dict[str, Any], seed: int = ORDER_SEED) -> dict[str, list[list[str]]]:
    """The realized A4 order: per setting, shuffled trials cut into near-equal sessions.

    One ``random.Random(seed)`` serves both settings, screenshot first. Each
    entry's repetitions are split evenly between the settings.
    """
    rng = random.Random(seed)
    out: dict[str, list[list[str]]] = {}
    for setting in SETTINGS:
        trials = [
            entry_id
            for entry_id, row in sorted(plan["entries"].items())
            for _ in range(row["reps"] // 2)
        ]
        rng.shuffle(trials)
        count = plan["sessions_per_setting"][setting]
        size, extra = divmod(len(trials), count)
        cut, start = [], 0
        for index in range(count):
            end = start + size + (1 if index < extra else 0)
            cut.append(trials[start:end])
            start = end
        out[setting] = cut
    return out


def order_sha256(plan: dict[str, Any]) -> str:
    payload = json.dumps(sessions(plan), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
