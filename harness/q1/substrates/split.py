"""Seeded calibration/evaluation split of the S1 problems (reviewed plan section 7(ii)).

The split is a pure function of the full admissible problem list and the seed,
stratified by level, and is fixed before any substrate is admitted or scored.
Problems that later fail admission drop out of whichever half they are in;
both halves' exclusions are reported. This keeps admission outcomes from
influencing which problems calibrate the audit.

Rule: for each level, sort the admissible problem ids by (level, number), shuffle
them with ``random.Random(f"{seed}:L{level}")``, and put the first
``ceil(n / 2)`` in the calibration half (``S1-cal``) and the rest in the
evaluation half (``S1-eval``). S2 substrates are always evaluation.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections.abc import Iterable

from harness.q1.schema import parse_problem_id
from harness.q1.substrates.sources import EXCLUDED_PROBLEMS, LEVELS

SPLIT_VERSION = "q1-s1-split/1"


def calibration_split(problem_ids: Iterable[str], *, seed: int = 42) -> dict[str, object]:
    ids = sorted(
        {pid for pid in problem_ids if parse_problem_id(pid)[0] in LEVELS},
        key=lambda pid: parse_problem_id(pid)[:2],
    )
    excluded = [pid for pid in ids if pid in EXCLUDED_PROBLEMS]
    admissible = [pid for pid in ids if pid not in EXCLUDED_PROBLEMS]
    calibration: list[str] = []
    evaluation: list[str] = []
    for level in LEVELS:
        members = [pid for pid in admissible if parse_problem_id(pid)[0] == level]
        rng = random.Random(f"{seed}:L{level}")
        shuffled = list(members)
        rng.shuffle(shuffled)
        cut = math.ceil(len(shuffled) / 2)
        calibration.extend(sorted(shuffled[:cut], key=lambda pid: parse_problem_id(pid)[:2]))
        evaluation.extend(sorted(shuffled[cut:], key=lambda pid: parse_problem_id(pid)[:2]))
    body = {
        "split_version": SPLIT_VERSION,
        "seed": seed,
        "rule": "per level: sorted ids, random.Random(f'{seed}:L{level}').shuffle, first "
        "ceil(n/2) -> calibration; S2 substrates are evaluation-only",
        "calibration": calibration,
        "evaluation": evaluation,
        "excluded_before_split": excluded,
    }
    digest = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    return {**body, "sha256": digest}


def half_of(problem_id: str, split: dict[str, object]) -> str:
    if problem_id in split["calibration"]:  # type: ignore[operator]
        return "calibration"
    if problem_id in split["evaluation"]:  # type: ignore[operator]
        return "evaluation"
    return "excluded"
