"""Run order and sessions (preregistration sections 7 and 10).

For shuffle seed ``s``: ``rng = random.Random(s)``; for each repetition the
cell IDs in their frozen order are shuffled with ``rng`` and appended. The
order is cut into sessions of at most ``SESSION_TRIALS`` consecutive trials,
near-equal in size (``ceil(n / 60)`` sessions; the first ``n mod k`` sessions
take one extra trial). Each session is a cold boot of a new VM in one
observation setting.

Seed 42 is development (never evidence); seeds 43 and 44 are acceptance and
are refused here unless the caller passes ``acceptance=True``, which only the
acceptance workloads may do once ``manifest.py`` admits them (it refuses them
before the freeze). Standard library only.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from typing import Any

SESSION_TRIALS = 60
DEVELOPMENT_SEED = 42
ACCEPTANCE_SEEDS = (43, 44)
SETTINGS = ("screenshot", "screenshot+a11y")


class OrderError(ValueError):
    """A run order that the preregistration does not allow."""


def check_seed(seed: int, acceptance: bool = False) -> None:
    if seed == DEVELOPMENT_SEED and not acceptance:
        return
    if seed in ACCEPTANCE_SEEDS and acceptance:
        return
    raise OrderError(
        f"seed {seed} is not allowed for {'acceptance' if acceptance else 'development'}"
    )


def shuffle_order(ids: list[str], seed: int, reps: int, acceptance: bool = False) -> list[str]:
    check_seed(seed, acceptance)
    rng = random.Random(seed)
    out: list[str] = []
    for _ in range(reps):
        batch = list(ids)
        rng.shuffle(batch)
        out += batch
    return out


def cut_sessions(order: list[Any], max_trials: int = SESSION_TRIALS) -> list[list[Any]]:
    if not order:
        return []
    count = math.ceil(len(order) / max_trials)
    size, extra = divmod(len(order), count)
    out, start = [], 0
    for index in range(count):
        end = start + size + (1 if index < extra else 0)
        out.append(order[start:end])
        start = end
    return out


def plan(
    ids: list[str],
    seed: int,
    reps: int,
    settings: list[str],
    max_trials: int = SESSION_TRIALS,
    acceptance: bool = False,
) -> list[dict[str, Any]]:
    """Sessions in run order: every setting runs the same shuffle, screenshot first."""
    for setting in settings:
        if setting not in SETTINGS:
            raise OrderError(f"unknown observation setting {setting!r}")
    order = shuffle_order(ids, seed, reps, acceptance)
    sessions = []
    for setting in settings:
        for index, chunk in enumerate(cut_sessions(order, max_trials)):
            sessions.append(
                {
                    "setting": setting,
                    "index": index,
                    "trials": [[seq, cell] for seq, cell in enumerate(chunk)],
                }
            )
    return sessions


def order_sha256(sessions: list[dict[str, Any]]) -> str:
    payload = json.dumps(sessions, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
