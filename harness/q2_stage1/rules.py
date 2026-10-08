"""The registered decision rules of `q2-stage1-rescoped-v1` (S1a), section 11, and the
predictions P1-P5 of section 12.

Every rule reads only the quantities named in its docstring. Thresholds are constants;
changing one after the freeze is a new experiment id.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from harness.q2_stage1.plan import PRICE_HIGH

ALPHA = 0.05
# DR2: Holm over the delta test and the primary X test at family-wise 5%. "Present" needs
# at least one rejection, i.e. the smaller p-value at or below 0.025.
DR2_FAMILY = ("delta_paired_t", "x_signflip")
EQUIVALENCE_MARGIN = 0.075  # pooled delta, 90% t interval
PI_EQUIVALENCE_BOUND = 0.12  # one-sided 95% upper bound of pi_small
DR0_CELL_LOSS = 0.05
ANCHOR_LOSS = 0.10
ANCHOR_MIN_TASKS = 58
DR1_FLOOR = 0.10
# DR5: the ladder's detectable share on the pi-degree scale, frozen from
# analysis/sim_s1a_v2.json ("dr5"): the largest value over the six planning cells (two
# scenarios x three session-noise settings), so a GO means the planned ladder is powered
# in every cell (preregistration section 11). M_SMALL applies to pi_small (the 4B and 9B
# mean); M_9B to pi_9B when DR1 drops 4B.
M_SMALL = 0.13
M_9B = 0.18
P1_MIN_EXCESS = 0.01
P2_INTERVAL = (0.06, 0.20)
P5_CENTRAL = {16: 0.010948, 20: 0.009020}


# --------------------------------------------------------------------------- DR0


def dr0(
    cell_losses: Mapping[tuple[str, str], Any],
    base_complete: bool,
    gate_breach: bool = False,
) -> dict[str, Any]:
    """DR0 for one A1 job, from infrastructure records only.

    Fires if a (size, harness) cell lost more than 5% of its first-attempt episodes to
    infrastructure (agent-caused events are not losses), if the job ended without
    completing its base, or if a gate of section 3 turned out not to hold. ANC is judged
    by DR-A alone.
    """
    over = sorted(f"{z}/{h}" for (z, h), loss in cell_losses.items() if loss.share > DR0_CELL_LOSS)
    reasons = []
    if over:
        reasons.append(f"cell loss above 5%: {', '.join(over)}")
    if not base_complete:
        reasons.append("base incomplete")
    if gate_breach:
        reasons.append("a gate of section 3 did not hold")
    return {"fires": bool(reasons), "reasons": reasons}


def job_dr0(
    records: Iterable[Mapping[str, Any]],
    *,
    job: str,
    size: str,
    session: str,
    base: Sequence[str],
    receipt: Mapping[str, Any] | None = None,
    gate_breach: str | None = None,
) -> dict[str, Any]:
    """DR0 for one A1 job from its lane record file (and its lane receipt).

    The cell losses and base completion come from the records (``records.first_attempt_losses``
    and ``records.base_complete``, infrastructure only, no outcome); a lane receipt that
    holds an error (the lane refused to dispatch: an engine or Slurm check, D12) or a named
    ``gate_breach`` is a gate of section 3 that did not hold.
    """
    from harness.q2_stage1 import records as R

    rows = [R.validate(r) for r in records if r.get("job") == job]
    losses = R.first_attempt_losses(rows, job)
    complete = R.base_complete(rows, job, size, session, base)
    breaches = []
    if receipt is not None and receipt.get("error"):
        breaches.append(f"lane: {str(receipt['error'])[:200]}")
    if gate_breach:
        breaches.append(str(gate_breach)[:200])
    out = dr0(losses, complete, bool(breaches))
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


def run_dir_dr0(run_dir: Path, plan: Mapping[str, Any], gate_breach: str | None = None) -> dict:
    """DR0 for the A1 job whose lane run directory this is (``manifest.json``,
    ``episodes.jsonl``, ``lane-receipt.json``), with the files' digests."""
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    a1 = manifest.get("a1") or {}
    size, session = a1.get("size"), a1.get("session")
    job = f"A1-{size}-{session}"
    if manifest.get("purpose") != "a1":
        raise ValueError("DR0 judges A1 jobs only (ANC is judged by DR-A)")
    episodes, receipt_path = run_dir / "episodes.jsonl", run_dir / "lane-receipt.json"
    rows = [
        json.loads(line)
        for line in episodes.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    out = job_dr0(
        rows, job=job, size=size, session=session, base=plan["base"], receipt=receipt,
        gate_breach=gate_breach,
    )  # fmt: skip
    out["files"] = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (run_dir / "manifest.json", episodes, receipt_path)
    }
    return out


# --------------------------------------------------------------------------- DR-A


def anchor_reading_set(
    order: Sequence[str], finals: Mapping[str, Mapping[str, Any]]
) -> tuple[list[str], list[str]]:
    """The longest prefix of the anchor's dispatch order in which every episode completed.

    ``finals`` maps task id to the episode's final record. The prefix ends at the first
    task that was cut at the cap or never dispatched; a task lost to infrastructure after
    its re-queue stays inside the prefix but out of the reading (it counts toward DR-A's
    loss share). Returns (tasks read, tasks lost inside the prefix).
    """
    read, lost = [], []
    for task in order:
        rec = finals.get(task)
        if rec is None or rec["status"] == "cap_truncated":
            break
        if rec["status"] == "infrastructure":
            lost.append(task)
        else:
            read.append(task)
    return read, lost


def dr_anchor(
    ours: Sequence[float],
    public: Sequence[Sequence[float]],
    *,
    first_attempts: int,
    infrastructure_losses: int,
    available: bool = True,
) -> dict[str, Any]:
    """DR-A on the reading set: kill if our mean score lies more than 2 SE outside
    [min, max] of the three public runs' mean scores on the same tasks.

    SE is the task-level SE of (ours minus the public mean). The rule assumes no session
    variance between our run and the public runs (their spread is 3.2 pp on 359 tasks).
    """
    if not available:
        return {"outcome": "ANCHOR-UNAVAILABLE"}
    loss_share = infrastructure_losses / first_attempts if first_attempts else 1.0
    n = len(ours)
    if n < ANCHOR_MIN_TASKS or loss_share > ANCHOR_LOSS:
        return {
            "outcome": "ANCHOR-INCOMPLETE",
            "tasks_read": n,
            "infrastructure_loss_share": round(loss_share, 4),
        }
    o = np.asarray(ours, dtype=float)
    p = np.asarray(public, dtype=float)
    if p.shape != (3, n):
        raise ValueError("public must hold three runs on the tasks read")
    dt = o - p.mean(0)
    se = float(dt.std(ddof=1) / math.sqrt(n))
    runs = p.mean(1)
    low, high = float(runs.min() - 2 * se), float(runs.max() + 2 * se)
    ours_mean = float(o.mean())
    kill = ours_mean < low or ours_mean > high
    return {
        "outcome": "ANCHOR-FAIL" if kill else "ANCHOR-PASS",
        "tasks_read": n,
        "ours": ours_mean,
        "public_runs": [float(v) for v in runs],
        "se": se,
        "band": [low, high],
        "infrastructure_loss_share": round(loss_share, 4),
    }


# --------------------------------------------------------------------------- DR1-DR5


def dr1(success_4b_by_harness: Sequence[float]) -> bool:
    """True (S1b would drop 4B) if 4B's pooled success is below 10% under both harnesses."""
    return all(s < DR1_FLOOR for s in success_4b_by_harness)


def dr2(
    p_delta: float, p_x: float, delta_ci90: tuple[float, float], pi_small_ub95: float
) -> dict[str, Any]:
    """DR2, a classification of the harness pair for the realized sessions.

    Present: Holm over the delta paired t and the X sign-flip test rejects at family-wise
    5% (min p <= 0.025). Near-equivalent: not present, the 90% t interval of pooled delta
    within +/-7.5 pp and the one-sided 95% upper bound of pi_small below 0.12.
    """
    present = min(p_delta, p_x) <= ALPHA / len(DR2_FAMILY)
    lo, hi = delta_ci90
    near = (
        not present
        and lo > -EQUIVALENCE_MARGIN
        and hi < EQUIVALENCE_MARGIN
        and pi_small_ub95 < PI_EQUIVALENCE_BOUND
    )
    cls = "Present" if present else ("Near-equivalent" if near else "Inconclusive")
    return {"class": cls, "holm_threshold": ALPHA / len(DR2_FAMILY)}


def dr4(realized: Mapping[str, tuple[float, int]]) -> dict[str, Any]:
    """DR4: per job (GPU-h per episode, V), whether it exceeds the high price at its V."""
    over = {job: c for job, (c, v) in realized.items() if c > PRICE_HIGH[v]}
    return {"exceeds_high": bool(over), "jobs": sorted(over)}


def dr5(lb95: float, ub95: float, drop_4b: bool) -> dict[str, Any]:
    """DR5: GO if the one-sided 95% lower bound of the share exceeds M, NO-GO if the
    one-sided 95% upper bound is below M, INCONCLUSIVE otherwise.

    The share is pi_small with M_SMALL, or pi_9B with M_9B when DR1 drops 4B. Only GO lets
    the harness scale ladder (S1b) go to the gauntlet (D47).
    """
    m = M_9B if drop_4b else M_SMALL
    if lb95 > m:
        outcome = "GO"
    elif ub95 < m:
        outcome = "NO-GO"
    else:
        outcome = "INCONCLUSIVE"
    return {"outcome": outcome, "M": m, "share": "pi_9B" if drop_4b else "pi_small"}


# --------------------------------------------------------------------------- predictions


def predictions(
    *,
    excess_ub95: float,
    db_ci95: tuple[float, float],
    dr2_class: str,
    dr1_fires: bool,
    dr4_exceeds: bool,
) -> dict[str, dict[str, Any]]:
    """P1-P5 of section 12, each read by its registered falsifier (for these sessions)."""
    lo, hi = db_ci95
    return {
        "P1": {"falsified": excess_ub95 < P1_MIN_EXCESS, "read": "one-sided 95% UB of D_b-D_w"},
        "P2": {
            "falsified": hi < P2_INTERVAL[0] or lo > P2_INTERVAL[1],
            "read": "95% interval of pooled D_b vs [6%, 20%]",
        },
        "P3": {"falsified": dr2_class == "Present", "read": "DR2"},
        "P4": {"falsified": dr1_fires, "read": "DR1"},
        "P5": {"falsified": dr4_exceeds, "read": "DR4"},
    }


# --------------------------------------------------------------------------- command line


def main(argv: list[str] | None = None) -> int:
    """``dr0``: DR0 for one A1 job from its lane run directory and the frozen plan; exits 3
    when it fires (no further job may start, section 11)."""
    parser = argparse.ArgumentParser(description="S1a decision rules")
    sub = parser.add_subparsers(dest="command", required=True)
    cmd = sub.add_parser("dr0", help="DR0 of one A1 job (infrastructure records only)")
    cmd.add_argument("--run-dir", type=Path, required=True)
    cmd.add_argument("--plan", type=Path, required=True)
    cmd.add_argument("--gate-breach", help="a gate of section 3 that did not hold (recorded)")
    args = parser.parse_args(argv)
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    out = run_dir_dr0(args.run_dir, plan, args.gate_breach)
    print(json.dumps(out, indent=1, sort_keys=True))
    return 3 if out["fires"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
