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
before the freeze). Seed 45 is C2's own order in q2-action-path-v2 (decision D40:
C2 is a reproduction test on an order seed no v1 campaign or development run used);
it is refused unless the caller names ``criterion="C2"``. Standard library only.
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
# q2-action-path-v2 (decision D40): validity control C2's order seed, for C2 only.
C2_SEED = 45
SETTINGS = ("screenshot", "screenshot+a11y")
# A3's 30 timing- and state-sensitive entries (preregistration section 7, A3).
STRESS_ENTRIES = (
    "click_double_left", "click_triple_left", "click_ctrl_left", "click_shift_left",
    "click_alt_left", "click_ctrl_shift_right", "click_burst_5", "click_double_slow",
    "drag_short", "drag_slow_small", "drag_long_diagonal", "chord_ctrl_c", "chord_ctrl_shift_t",
    "chord_ctrl_shift_arrow", "chord_shift_tab", "chord_shift_alone", "chord_ctrl_alone",
    "key_kp_enter", "key_menu", "caps_lock_roundtrip", "scroll_ctrl_down_3", "scroll_shift_down_3",
    "scroll_down_then_up_net_zero", "type_symbols_shifted", "type_unicode_bmp", "type_emoji_zwj",
    "type_combining", "type_long_500", "type_with_correction", "seq_long_mixed",
)  # fmt: skip


class OrderError(ValueError):
    """A run order that the preregistration does not allow."""


def check_seed(seed: int, acceptance: bool = False, criterion: str | None = None) -> None:
    if seed == DEVELOPMENT_SEED and not acceptance:
        return
    if seed in ACCEPTANCE_SEEDS and acceptance:
        return
    if seed == C2_SEED and criterion == "C2":
        return
    raise OrderError(
        f"seed {seed} is not allowed for {'acceptance' if acceptance else 'development'}"
        + (f" ({criterion})" if criterion else "")
    )


def shuffle_order(
    ids: list[str], seed: int, reps: int, acceptance: bool = False, criterion: str | None = None
) -> list[str]:
    check_seed(seed, acceptance, criterion)
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
    criterion: str | None = None,
) -> list[dict[str, Any]]:
    """Sessions in run order: every setting runs the same shuffle, screenshot first."""
    for setting in settings:
        if setting not in SETTINGS:
            raise OrderError(f"unknown observation setting {setting!r}")
    order = shuffle_order(ids, seed, reps, acceptance, criterion)
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
