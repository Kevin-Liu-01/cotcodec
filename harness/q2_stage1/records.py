"""Episode records of `q2-stage1-rescoped-v1` (S1a) and the analysis sets built from them.

The episode driver (G0 item 3) writes one JSON object per episode attempt with the
fields below; the analysis reads nothing else. Classification follows section 7.2:

* ``status: "infrastructure"``: a transport, VM, engine, guest-server or executor-device
  fault (``INFRASTRUCTURE_TYPES``). The slot is re-queued once at the end of its block; a
  second loss leaves it missing. Only these count toward DR0.
* Agent-caused events are not infrastructure. An ``IRError`` raised from model output is
  handled in the episode under that harness's rule for an unparseable reply and counted
  in ``ir_errors``; a checker metric that raises on retrieved agent state is scored 0 in
  the primary analysis (``metric_exception: true``, ``score: 0.0``) and treated as missing
  in a sensitivity.
* ``status: "cap_truncated"``: the job's USR1 cut the episode or it was never dispatched.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

SCHEMA = "q2-stage1a-episode-v1"
SIZES = ("4B", "9B")
HARNESSES = ("H-OSW-fixed", "H-GA")
SESSIONS = ("S1", "S2")
RERUNS = (1, 2)
STATUSES = ("scored", "infrastructure", "cap_truncated")
INFRASTRUCTURE_TYPES = (
    "vm_boot",
    "task_setup",
    "guest_server_restart",
    "engine_request",
    "engine_context_fallback",
    "executor_device",
    "transport",
    "runner_crash",
    "offline_network",
)
REQUIRED = (
    "schema",
    "job",
    "size",
    "session",
    "task_id",
    "harness",
    "rerun",
    "extension_block",
    "attempt",
    "status",
)
COUNTS = (
    "steps",
    "truncated_steps",
    "truncated_no_tool_call_steps",
    "ir_errors",
    "uncertified_key_actions",
    "context_fallbacks",
)


class RecordError(ValueError):
    """Raised when an episode record does not follow the schema."""


def validate(record: Mapping[str, Any]) -> dict[str, Any]:
    """Check one record; returns a plain dict copy."""
    missing = [k for k in REQUIRED if k not in record]
    if missing:
        raise RecordError(f"record lacks {missing}")
    rec = dict(record)
    if rec["schema"] != SCHEMA:
        raise RecordError(f"schema must be {SCHEMA}")
    if rec["size"] not in SIZES or rec["harness"] not in HARNESSES:
        raise RecordError("unknown size or harness")
    if rec["session"] not in SESSIONS or rec["rerun"] not in RERUNS:
        raise RecordError("unknown session or rerun")
    if rec["attempt"] not in (1, 2):
        raise RecordError("attempt must be 1 or 2 (one re-queue)")
    ext = rec["extension_block"]
    if ext is not None and (not isinstance(ext, int) or isinstance(ext, bool) or ext < 1):
        raise RecordError("extension_block must be null (base) or a positive integer")
    status = rec["status"]
    if status not in STATUSES:
        raise RecordError(f"status must be one of {STATUSES}")
    if status == "infrastructure":
        if rec.get("infrastructure_type") not in INFRASTRUCTURE_TYPES:
            raise RecordError(f"infrastructure_type must be one of {INFRASTRUCTURE_TYPES}")
    elif rec.get("infrastructure_type") is not None:
        raise RecordError("only an infrastructure loss has an infrastructure_type")
    if status == "scored":
        score = rec.get("score")
        if not isinstance(score, (int, float)) or isinstance(score, bool) or not 0 <= score <= 1:
            raise RecordError("a scored episode needs a score in [0, 1]")
        if rec.get("metric_exception") and score != 0:
            raise RecordError("a metric exception is scored 0 in the primary analysis")
    elif rec.get("score") is not None:
        raise RecordError("only a scored episode has a score")
    for key in COUNTS:
        value = rec.get(key, 0)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise RecordError(f"{key} must be a non-negative integer")
    return rec


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        validate(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


SlotKey = tuple[str, str, str, str, int]  # (size, session, task, harness, rerun)


def slot_key(rec: Mapping[str, Any]) -> SlotKey:
    return (rec["size"], rec["session"], rec["task_id"], rec["harness"], rec["rerun"])


def final_records(records: Iterable[Mapping[str, Any]]) -> dict[SlotKey, dict[str, Any]]:
    """The last attempt of every slot (an attempt-2 record replaces attempt 1)."""
    out: dict[SlotKey, dict[str, Any]] = {}
    for rec in records:
        rec = validate(rec)
        key = slot_key(rec)
        if key not in out or rec["attempt"] > out[key]["attempt"]:
            out[key] = rec
    return out


def outcome(rec: Mapping[str, Any] | None, *, metric_exception_missing: bool = False) -> float:
    """y for one final record: 1.0 if the checker score is 1.0, else 0.0; NaN if missing."""
    if rec is None or rec["status"] != "scored":
        return float("nan")
    if metric_exception_missing and rec.get("metric_exception"):
        return float("nan")
    return 1.0 if float(rec["score"]) == 1.0 else 0.0


def outcome_array(
    finals: Mapping[SlotKey, Mapping[str, Any]],
    tasks: Sequence[str],
    *,
    sizes: Sequence[str] = SIZES,
    metric_exception_missing: bool = False,
    value: str = "binary",
    drop_truncated: bool = False,
) -> np.ndarray:
    """The (Z, K, H, S, R) array of section 9 for ``tasks`` (NaN for a missing slot).

    ``value="score"`` gives the checker score itself (the fractional-score sensitivity);
    ``value="corrected"`` the verdict of the offline rescoring with the corrected checker
    (``corrected_score``, else the live score). ``drop_truncated`` leaves out episodes with
    a truncated step (the mediator description of section 15).
    """
    if value not in ("binary", "score", "corrected"):
        raise ValueError("value must be binary, score or corrected")
    y = np.full((len(sizes), len(tasks), 2, 2, 2), np.nan)
    for zi, z in enumerate(sizes):
        for ki, t in enumerate(tasks):
            for hi, h in enumerate(HARNESSES):
                for si, s in enumerate(SESSIONS):
                    for ri, r in enumerate(RERUNS):
                        rec = finals.get((z, s, t, h, r))
                        if drop_truncated and rec is not None and rec.get("truncated_steps"):
                            continue
                        if value == "score":
                            if rec is not None and rec["status"] == "scored":
                                y[zi, ki, hi, si, ri] = float(rec["score"])
                        elif value == "corrected":
                            if rec is not None and rec["status"] == "scored":
                                c = rec.get("corrected_score")
                                c = float(rec["score"]) if c is None else float(c)
                                y[zi, ki, hi, si, ri] = 1.0 if c == 1.0 else 0.0
                        else:
                            y[zi, ki, hi, si, ri] = outcome(
                                rec, metric_exception_missing=metric_exception_missing
                            )
    return y


def _slot_final(rec: Mapping[str, Any] | None) -> bool:
    """A slot is final when scored, or lost to infrastructure after its re-queue."""
    if rec is None or rec["status"] == "cap_truncated":
        return False
    return not (rec["status"] == "infrastructure" and rec["attempt"] < 2)


def completed_extension_blocks(
    records: Iterable[Mapping[str, Any]],
    planned: Mapping[int, Sequence[str]],
    sessions: Sequence[str] = SESSIONS,
) -> list[int]:
    """Extension blocks every slot of which reached a final state in all four A1 jobs (or,
    with ``sessions=("S1",)``, in both session-1 jobs: the blocks session 2 runs, 5.6).

    A slot is final when its last attempt is scored, or is an infrastructure loss after the
    re-queue (attempt 2); a cap-truncated or undispatched slot is not.
    """
    finals = final_records(records)
    done = []
    for block, tasks in sorted(planned.items()):
        ok = True
        for z in SIZES:
            for s in sessions:
                for t in tasks:
                    for h in HARNESSES:
                        for r in RERUNS:
                            if not _slot_final(finals.get((z, s, t, h, r))):
                                ok = False
        if ok:
            done.append(block)
    return done


@dataclass(frozen=True)
class CellLoss:
    first_attempts: int
    infrastructure: int

    @property
    def share(self) -> float:
        return self.infrastructure / self.first_attempts if self.first_attempts else 0.0


def first_attempt_losses(
    records: Iterable[Mapping[str, Any]], job: str
) -> dict[tuple[str, str], CellLoss]:
    """Per (size, harness) of one job: first-attempt dispatched episodes and their
    infrastructure losses (agent-caused events are not losses)."""
    n: dict[tuple[str, str], int] = defaultdict(int)
    lost: dict[tuple[str, str], int] = defaultdict(int)
    for rec in records:
        rec = validate(rec)
        if rec["job"] != job or rec["attempt"] != 1 or rec["status"] == "cap_truncated":
            continue
        key = (rec["size"], rec["harness"])
        n[key] += 1
        if rec["status"] == "infrastructure":
            lost[key] += 1
    return {k: CellLoss(n[k], lost[k]) for k in sorted(n)}


def base_complete(
    records: Iterable[Mapping[str, Any]], job: str, size: str, session: str, base: Sequence[str]
) -> bool:
    """Every base slot of the job reached a final state (scored, or lost after re-queue)."""
    finals = final_records(r for r in records if r["job"] == job)
    return all(
        _slot_final(finals.get((size, session, t, h, r)))
        for t in base
        for h in HARNESSES
        for r in RERUNS
    )


def event_counts(records: Iterable[Mapping[str, Any]], key: str) -> dict[tuple[str, str], int]:
    """Sum of a per-episode count (``ir_errors``, ``truncated_steps``, ...) per (size,
    harness) over final records."""
    out: dict[tuple[str, str], int] = defaultdict(int)
    for rec in final_records(records).values():
        out[(rec["size"], rec["harness"])] += int(rec.get(key, 0))
    return dict(sorted(out.items()))


def metric_exception_counts(records: Iterable[Mapping[str, Any]]) -> dict[tuple[str, str], int]:
    out: dict[tuple[str, str], int] = defaultdict(int)
    for rec in final_records(records).values():
        if rec.get("metric_exception"):
            out[(rec["size"], rec["harness"])] += 1
    return dict(sorted(out.items()))


# --------------------------------------------------------------------------- anchor records

ANCHOR_SCHEMA = "q2-stage1a-anchor-v1"


def validate_anchor(record: Mapping[str, Any]) -> dict[str, Any]:
    """One ANC episode attempt: task, attempt, status, score, infrastructure type."""
    rec = dict(record)
    if rec.get("schema") != ANCHOR_SCHEMA:
        raise RecordError(f"schema must be {ANCHOR_SCHEMA}")
    if not isinstance(rec.get("task_id"), str) or rec.get("attempt") not in (1, 2):
        raise RecordError("an anchor record needs a task id and attempt 1 or 2")
    if rec.get("status") not in STATUSES:
        raise RecordError(f"status must be one of {STATUSES}")
    if rec["status"] == "scored":
        score = rec.get("score")
        if not isinstance(score, (int, float)) or isinstance(score, bool) or not 0 <= score <= 1:
            raise RecordError("a scored anchor episode needs a score in [0, 1]")
    if rec["status"] == "infrastructure" and rec.get("infrastructure_type") not in (
        INFRASTRUCTURE_TYPES
    ):
        raise RecordError(f"infrastructure_type must be one of {INFRASTRUCTURE_TYPES}")
    return rec


def anchor_finals(records: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for rec in records:
        rec = validate_anchor(rec)
        if rec["task_id"] not in out or rec["attempt"] > out[rec["task_id"]]["attempt"]:
            out[rec["task_id"]] = rec
    return out


def anchor_first_attempt_losses(records: Iterable[Mapping[str, Any]]) -> tuple[int, int]:
    """(first-attempt dispatched episodes, of which lost to infrastructure)."""
    n = lost = 0
    for rec in records:
        rec = validate_anchor(rec)
        if rec["attempt"] != 1 or rec["status"] == "cap_truncated":
            continue
        n += 1
        lost += rec["status"] == "infrastructure"
    return n, lost


# --------------------------------------------------------------------------- step logs


def first_divergence(
    steps_a: Sequence[Mapping[str, Any]], steps_b: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Where two reruns of one (size, task, harness) first part (section 9 item 11).

    Each step carries ``processed_sha256`` (the processed screenshot the model saw that
    step), ``messages_sha256`` (the whole request, text and images) and ``ir_sha256`` (the
    parsed IR). At the first step where the two runs differ:

    * the observation differs: an **environment** divergence (the screen differed before any
      action did). The guest's top-bar clock is on every screenshot, so nearly every pair
      parts here at step 1 (disclosed);
    * the observation is equal but the request differs (an earlier reply's text, thinking
      included, differed while its IR was equal), or the request is equal and the IR differs:
      a **serving** divergence (batched numerics or engine state on an identical screen).

    Equal steps throughout with different lengths is a length divergence. A step without the
    screenshot digest falls back to ``prompt_sha256``, the prompt token ids' digest, which
    cannot see an image (its tokens are image placeholders).
    """
    for i, (a, b) in enumerate(zip(steps_a, steps_b, strict=False)):
        obs_a, obs_b = a.get("processed_sha256"), b.get("processed_sha256")
        if obs_a is not None and obs_b is not None:
            if obs_a != obs_b:
                return {"kind": "environment", "step": i + 1}
            if a.get("messages_sha256") != b.get("messages_sha256"):
                return {"kind": "serving", "step": i + 1}
        elif a.get("prompt_sha256") != b.get("prompt_sha256"):
            return {"kind": "environment", "step": i + 1}
        if a["ir_sha256"] != b["ir_sha256"]:
            return {"kind": "serving", "step": i + 1}
    if len(steps_a) != len(steps_b):
        return {"kind": "length", "step": min(len(steps_a), len(steps_b)) + 1}
    return {"kind": "identical", "step": None}


def uncertified_key_actions(ir_actions: Iterable[Mapping[str, Any]], certified: set[str]) -> int:
    """Actions naming a keysym outside the certified set (keys or modifiers; section 7.3)."""
    n = 0
    for action in ir_actions:
        names = list(action.get("keys") or ()) + list(action.get("modifiers") or ())
        if any(name not in certified for name in names):
            n += 1
    return n


def certified_keysym_set() -> set[str]:
    """The 33 keysyms A1-A6 certify (action-path v2 section 4.5)."""
    from harness.q2.action_path import catalog as cat

    data = cat.load()
    return set(cat.certified_keysyms(data, cat.validate(data)["gating"]))
