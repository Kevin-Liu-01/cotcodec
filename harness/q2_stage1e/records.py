"""E's episode records: S1a's schema with E's session labels, and the arrays built from them.

The driver writes S1a's record (``harness.q2_stage1.records``, schema
``q2-stage1a-episode-v1``) unchanged. E's records differ only in two label values: the
session is ``E1``-``E4`` and the rerun is always 1 (no extension block). ``validate`` checks
those labels and then applies S1a's ``validate`` to everything else, so the status,
infrastructure types, scores and counts follow S1a's section 7.2 exactly. S1a's own
``validate`` refuses an E record (its sessions are S1 and S2), so no S1a tool can read E's
records into S1a's analysis by accident; the joint reading with S1a is a separate,
descriptive step (``analysis.joint_reading``).

The outcome array is S1a's ``(Z, K, H, S, R)`` with S = 4 sessions and R = 1 rerun.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from harness.q2_stage1 import records as R1
from harness.q2_stage1 import rules
from harness.q2_stage1e.plan import RERUN, SESSIONS

SIZES = R1.SIZES
HARNESSES = R1.HARNESSES
RERUNS = (RERUN,)
SCHEMA = R1.SCHEMA
RecordError = R1.RecordError
SlotKey = R1.SlotKey


def _as_s1a(record: Mapping[str, Any]) -> dict[str, Any]:
    """A copy with S1a's labels (session S1, rerun 1), for S1a's label-blind functions."""
    return {**record, "session": R1.SESSIONS[0], "rerun": R1.RERUNS[0]}


def validate(record: Mapping[str, Any]) -> dict[str, Any]:
    """E's labels (session E1-E4, rerun 1, no extension block), then S1a's ``validate``
    on everything else; returns a plain dict copy with E's labels."""
    missing = [k for k in R1.REQUIRED if k not in record]
    if missing:
        raise RecordError(f"record lacks {missing}")
    if record["session"] not in SESSIONS:
        raise RecordError(f"an E record's session is one of {SESSIONS}")
    if record["rerun"] != RERUN or isinstance(record["rerun"], bool):
        raise RecordError(f"an E record's rerun is {RERUN} (one episode per session)")
    if record["extension_block"] is not None:
        raise RecordError("E has no extension blocks")
    R1.validate(_as_s1a(record))
    return dict(record)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        validate(json.loads(line))
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def slot_key(rec: Mapping[str, Any]) -> SlotKey:
    return R1.slot_key(rec)


def final_records(records: Iterable[Mapping[str, Any]]) -> dict[SlotKey, dict[str, Any]]:
    """The last attempt of every slot (S1a's rule: attempt 2 replaces attempt 1)."""
    out: dict[SlotKey, dict[str, Any]] = {}
    for rec in records:
        rec = validate(rec)
        key = slot_key(rec)
        if key not in out or rec["attempt"] > out[key]["attempt"]:
            out[key] = rec
    return out


def outcome_array(
    finals: Mapping[SlotKey, Mapping[str, Any]],
    tasks: Sequence[str],
    *,
    sizes: Sequence[str] = SIZES,
    sessions: Sequence[str] = SESSIONS,
    metric_exception_missing: bool = False,
    value: str = "binary",
    drop_truncated: bool = False,
) -> np.ndarray:
    """The (Z, K, H, S, R) array for ``tasks`` with S = len(sessions), R = 1 (NaN where a
    slot is missing). ``value`` and ``drop_truncated`` are S1a's
    (``records.outcome_array``): ``score`` the checker score, ``corrected`` the offline
    corrected verdict (else the live score), ``drop_truncated`` leaves out episodes with a
    truncated step."""
    if value not in ("binary", "score", "corrected"):
        raise ValueError("value must be binary, score or corrected")
    y = np.full((len(sizes), len(tasks), len(HARNESSES), len(sessions), len(RERUNS)), np.nan)
    for zi, z in enumerate(sizes):
        for ki, t in enumerate(tasks):
            for hi, h in enumerate(HARNESSES):
                for si, s in enumerate(sessions):
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
                            y[zi, ki, hi, si, ri] = R1.outcome(
                                rec, metric_exception_missing=metric_exception_missing
                            )
    return y


def _slot_final(rec: Mapping[str, Any] | None) -> bool:
    """S1a's rule: final when scored, or lost to infrastructure after its re-queue."""
    if rec is None or rec["status"] == "cap_truncated":
        return False
    return not (rec["status"] == "infrastructure" and rec["attempt"] < 2)


def first_attempt_losses(records: Iterable[Mapping[str, Any]], job: str):
    """S1a's ``first_attempt_losses`` (per (size, harness) of one job: first-attempt
    dispatched episodes and their infrastructure losses), on E's records."""
    rows = [_as_s1a(validate(r)) for r in records]
    return R1.first_attempt_losses(rows, job)


def job_complete(
    records: Iterable[Mapping[str, Any]], job: str, size: str, session: str, tasks: Sequence[str]
) -> bool:
    """Every slot of the job reached a final state (S1a's ``base_complete``; an E job's
    slots are all its base)."""
    finals = final_records(r for r in records if r["job"] == job)
    return all(
        _slot_final(finals.get((size, session, t, h, RERUN))) for t in tasks for h in HARNESSES
    )


def job_dr0(
    records: Iterable[Mapping[str, Any]],
    *,
    job: str,
    size: str,
    session: str,
    tasks: Sequence[str],
    receipt: Mapping[str, Any] | None = None,
    gate_breach: str | None = None,
) -> dict[str, Any]:
    """DR0 for one E job (S1a section 11, ``rules.dr0`` unchanged): a (size, harness) cell
    lost more than 5% of its first-attempt episodes to infrastructure, the job ended without
    completing its slots, or a gate did not hold (a lane receipt with an error, or a named
    breach). Infrastructure records only; no outcome is read."""
    rows = [validate(r) for r in records if r.get("job") == job]
    losses = first_attempt_losses(rows, job)
    complete = job_complete(rows, job, size, session, tasks)
    breaches = []
    if receipt is not None and receipt.get("error"):
        breaches.append(f"lane: {str(receipt['error'])[:200]}")
    if gate_breach:
        breaches.append(str(gate_breach)[:200])
    out = rules.dr0(losses, complete, bool(breaches))
    out["reasons"] += breaches
    out.update(
        job=job,
        base_complete=complete,
        cell_losses={
            f"{z}/{h}": {"first_attempts": c.first_attempts, "infrastructure": c.infrastructure}
            for (z, h), c in losses.items()
        },
    )
    return out


def glmm_rows(
    finals: Mapping[SlotKey, Mapping[str, Any]], tasks: Sequence[str]
) -> list[dict[str, Any]]:
    """S1a's GLMM input rows (``glmm.rows_from_records``' columns: y, size, harness, task,
    session nested in size as ``"9B:E1"``, rerun) for E's sessions; one row per final scored
    slot. ``glmm.write_csv`` writes them and ``glmm.R`` fits them, both unchanged."""
    out = []
    for size in SIZES:
        for task in tasks:
            for harness in HARNESSES:
                for session in SESSIONS:
                    rec = finals.get((size, session, task, harness, RERUN))
                    y = R1.outcome(rec)
                    if np.isnan(y):
                        continue
                    out.append({"y": int(y), "size": size, "harness": harness, "task": task,
                                "session": f"{size}:{session}", "rerun": RERUN})  # fmt: skip
    return out


def glmm_synthetic(k: int = 113, seed: int = 42) -> list[dict[str, Any]]:
    """GLMM input rows of E's shape (two sizes, two harnesses, four sessions per size, one
    rerun) from S1a's synthetic generative model (``glmm.SYNTHETIC_TRUTH``: task, task x size,
    task x harness, session, harness x session, task x session and task x harness x session
    effects on the logit scale, Bernoulli outcomes), for the pre-freeze run of the unchanged
    ``glmm.R`` on data of E's shape."""
    from harness.q2_stage1 import glmm as G

    t = dict(G.SYNTHETIC_TRUTH)
    n_s = len(SESSIONS)
    rng = np.random.default_rng(seed)
    task = rng.normal(0, t["sd_task"], k)
    task_size = rng.normal(0, t["sd_task_size"], (k, 2))
    task_harness = rng.normal(0, t["sd_task_harness"], (k, 2))
    task_size_harness = rng.normal(0, t["sd_task_size_harness"], (k, 2, 2))
    session = rng.normal(0, t["sd_session"], (2, n_s))
    harness_session = rng.normal(0, t["sd_harness_session"], (2, 2, n_s))
    task_session = rng.normal(0, t["sd_task_session"], (k, 2, n_s))
    task_harness_session = rng.normal(0, t["sd_task_harness_session"], (k, 2, 2, n_s))
    rows = []
    for zi, size in enumerate(SIZES):
        for ti in range(k):
            for hi, harness in enumerate(HARNESSES):
                for si, sess in enumerate(SESSIONS):
                    eta = (t["intercept"] + t["size_9B"] * (size == "9B")
                           + t["harness_GA"] * (harness == "H-GA") + task[ti]
                           + task_size[ti, zi] + task_harness[ti, hi]
                           + task_size_harness[ti, zi, hi] + session[zi, si]
                           + harness_session[zi, hi, si] + task_session[ti, zi, si]
                           + task_harness_session[ti, zi, hi, si])  # fmt: skip
                    p = 1 / (1 + np.exp(-eta))
                    rows.append({"y": int(rng.random() < p), "size": size, "harness": harness,
                                 "task": f"t{ti:03d}", "session": f"{size}:{sess}",
                                 "rerun": RERUN})  # fmt: skip
    return rows


def sessions_with_scored(
    finals: Mapping[SlotKey, Mapping[str, Any]], tasks: Sequence[str]
) -> dict[str, list[str]]:
    """Per size, the sessions holding at least one scored final record on ``tasks``."""
    task_set = set(tasks)
    held: dict[str, set[str]] = defaultdict(set)
    for (z, s, t, _h, _r), rec in finals.items():
        if t in task_set and rec["status"] == "scored":
            held[z].add(s)
    return {z: [s for s in SESSIONS if s in held[z]] for z in SIZES}
