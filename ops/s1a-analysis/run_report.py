"""D59 (i) and (ii): the registered S1a report through a widened outcome check, and a guard
for incomplete data. An operator script, not code of record.

Usage (host, from the read-only export of the freeze commit)::

    python3 -E -s -B run_report.py --export X --records a1.jsonl --plan plan-a0a.json \
        --costs costs.json --dr0 dr0-1045.json [--dr0 ...] --out-dir DIR

Writes three files into DIR (each written once, never overwritten):

* ``report.json``: ``analysis.main`` of the export, run unchanged except that
  ``estimators._check`` accepts outcomes in [0, 1] (and NaN) instead of {0, 1} (D59 (i)).
  Every array the report builds is binary except the fractional-score sensitivity's
  (``R.outcome_array(..., value="score")``), so with no fractional score the file is
  byte-identical to the registered CLI's, and with fractional scores only
  ``fractional_score`` and the ``fractional_scores`` counts differ from the same data scored
  0. When the frozen report raises (no size holds two sessions: bug B2), no ``report.json``
  is written and the error is recorded.
* ``guard.json``: the completeness of the data (DR0 per job, the jobs present, the sessions
  per size) and every reading the guard changed (D59 (ii)).
* ``report-guarded.json``: the report the operator reads. With complete data it is
  ``report.json`` plus a ``guard`` block. With incomplete data every output is labelled
  ``incomplete``, a single-session size's session test is not estimable, DR1 is read on the
  sessions present, DR5 is "not evaluable as registered" (pi_9B shown against both M values
  as a description only), and no p-value is surfaced from an all-NaN statistic. When no
  size holds two sessions it is a delta-only report built from the registered functions:
  delta (estimates, bootstrap intervals and the paired t), the descriptive and
  infrastructure counts, and D_b, D_w, X, pi, the X test, DR2, DR5, P1 and P2 (and the
  session test and P3, which read them) marked not estimable.

The anchor is UNAVAILABLE in S1a (the registration's "anchor unavailable before A0b"
branch), so ``--anchor`` and ``--public`` are not offered.
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import json
import sys
import warnings
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s1a_ops as O  # noqa: E402

# The order in which ``analysis.report`` calls ``analyse_array`` (one call per set).
SET_ORDER = (
    "primary",
    "sensitivity_metric_exception_missing",
    "sensitivity_postconfig_server_error_missing",
    "sensitivity_flagged_tasks_excluded",
    "secondary_base_plus_completed_extension",
    "checker_corrected",
)
INCOMPLETE = "incomplete"
DR5_NOT_EVALUABLE = "not evaluable as registered"
DELTA_NAMES = ("delta", "delta_4B", "delta_9B", "scale_screen_delta")
# Read only from two sessions of a size (D59 (ii)): not estimable when no size has two.
NEEDS_TWO_SESSIONS = (
    "D_b",
    "D_w",
    "excess (D_b - D_w)",
    "D_b same-block and cross-block",
    "X, X_c and the Bernoulli X",
    "pi (pi_4B, pi_9B, pi_small) and the pi scale screen",
    "the X sign-flip test and the X label-permutation sensitivity",
    "the session shift and its sign-flip test",
    "the harness effect by session and the common session share",
    "DR2",
    "DR5",
    "P1",
    "P2",
    "P3 (reads DR2)",
)


def not_estimable(reason: str) -> dict[str, str]:
    return {"not_estimable": reason}


@contextlib.contextmanager
def _quiet() -> Iterator[None]:
    """numpy's empty-slice warnings on all-NaN cells (the frozen estimators expect them)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        yield


# --------------------------------------------------------------------------- D59 (i)


@contextlib.contextmanager
def widened_check() -> Iterator[None]:
    """D59 (i): ``estimators._check`` with the outcome test widened from {0, 1} to [0, 1].

    Everything else (the shape checks, the returned float array) is the frozen function's.
    The frozen estimators look ``_check`` up in their module at call time, so swapping the
    module attribute is the whole change; it is restored on exit."""
    E = O.frozen("estimators")
    original = E._check

    def check(y: Any) -> np.ndarray:
        y = np.asarray(y, dtype=float)
        if y.ndim < 5:
            raise ValueError("y must have shape (..., Z, K, H, S, R)")
        if y.shape[E.AXIS_H] != 2:
            raise ValueError("y must hold exactly two harnesses")
        finite = y[np.isfinite(y)]
        if finite.size and not np.all((finite >= 0.0) & (finite <= 1.0)):
            raise ValueError("outcomes must lie in [0, 1] or be NaN")
        return y

    E._check = check
    try:
        yield
    finally:
        E._check = original


@contextlib.contextmanager
def captured_arrays(sink: list[np.ndarray]) -> Iterator[None]:
    """Record the y array of every ``analysis.analyse_array`` call (the result unchanged),
    so the guard reads the same arrays the report did."""
    A = O.frozen("analysis")
    real = A.analyse_array

    def spy(y: np.ndarray, **kwargs: Any) -> dict[str, Any]:
        sink.append(np.array(y, dtype=float, copy=True))
        return real(y, **kwargs)

    A.analyse_array = spy
    try:
        yield
    finally:
        A.analyse_array = real


def registered_report(argv: Sequence[str], arrays: list[np.ndarray]) -> str | None:
    """``analysis.main(argv)`` under the widened check; returns the error, or None."""
    A = O.frozen("analysis")
    with widened_check(), captured_arrays(arrays):
        try:
            A.main(list(argv))
        except Exception as exc:  # noqa: BLE001 - recorded; the guard decides what follows
            return f"{type(exc).__name__}: {exc}"
    return None


# --------------------------------------------------------------------------- completeness


def completeness(
    records: Sequence[Mapping[str, Any]],
    plan: Mapping[str, Any],
    dr0: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Which A1 jobs ran, whether DR0 fired for any, and the sessions each size holds.

    A session counts for a size when it has at least one scored final record on a base task.
    DR0 is read from each job's ``rules dr0`` output (receipt included) and recomputed from
    the records alone (``rules.job_dr0``, no receipt) as a cross-check; either firing counts.
    """
    R, P, rules = O.frozen("records"), O.frozen("plan"), O.frozen("rules")
    order = P.a1_job_order()
    known = {P.a1_job(z, s): (z, s) for z in R.SIZES for s in R.SESSIONS}
    for rec in records:
        job = rec.get("job")
        if known.get(job) != (rec.get("size"), rec.get("session")):
            raise O.OpsError(f"record {rec.get('slot')!r}: job {job!r} is not its size/session")
    base = list(plan["base"])
    base_set = set(base)
    present = [job for job in order if any(rec["job"] == job for rec in records)]
    by_job: dict[str, Mapping[str, Any]] = {}
    for item in dr0:
        job = item.get("job")
        if job not in known:
            raise O.OpsError(f"a DR0 output names an unknown job {job!r}")
        if job in by_job:
            raise O.OpsError(f"two DR0 outputs for {job}")
        by_job[job] = item
    lacking = [job for job in present if job not in by_job]
    if lacking:
        raise O.OpsError(f"no DR0 output (rules dr0) for {lacking}")
    recomputed = {
        job: rules.job_dr0(records, job=job, size=known[job][0], session=known[job][1], base=base)
        for job in present
    }
    jobs: dict[str, Any] = {}
    for job in order:
        if job not in by_job and job not in recomputed:
            continue
        given = by_job.get(job) or {}
        again = recomputed.get(job) or {}
        jobs[job] = {
            "records": job in present,
            "dr0_fires": bool(given.get("fires")),
            "dr0_reasons": list(given.get("reasons") or []),
            "dr0_from_records_fires": bool(again.get("fires")),
            "dr0_from_records_reasons": list(again.get("reasons") or []),
        }
    fired = [job for job, j in jobs.items() if j["dr0_fires"] or j["dr0_from_records_fires"]]
    finals = R.final_records(records)
    sizes: dict[str, Any] = {}
    for z in R.SIZES:
        tasks_by_session = {
            s: {
                key[2]
                for key, rec in finals.items()
                if key[0] == z and key[1] == s and key[2] in base_set and rec["status"] == "scored"
            }
            for s in R.SESSIONS
        }
        sessions = [s for s in R.SESSIONS if tasks_by_session[s]]
        sizes[z] = {
            "sessions": sessions,
            "two_sessions": len(sessions) == len(R.SESSIONS),
            "base_tasks_scored_by_session": {s: len(v) for s, v in tasks_by_session.items()},
            "base_tasks_scored_in_both_sessions": len(set.intersection(*tasks_by_session.values())),
        }
    absent = [job for job in order if job not in present]
    single = [z for z in R.SIZES if not sizes[z]["two_sessions"]]
    two = [z for z in R.SIZES if sizes[z]["two_sessions"]]
    reasons = []
    if fired:
        reasons.append(f"DR0 fired for {', '.join(fired)}")
    if absent:
        reasons.append(f"no records from {', '.join(absent)}")
    if single:
        reasons.append(f"{', '.join(single)} without two sessions of scored base records")
    return {
        "registered_job_order": order,
        "jobs_present": present,
        "jobs_absent": absent,
        "jobs": jobs,
        "dr0_fired": fired,
        "sizes": sizes,
        "sizes_with_two_sessions": two,
        "sizes_without_two_sessions": single,
        "incomplete": bool(reasons),
        "reasons": reasons,
    }


# --------------------------------------------------------------------------- guard


def _finite_count(values: np.ndarray) -> int:
    return int(np.isfinite(np.asarray(values, dtype=float)).sum())


def mask_block(block: Mapping[str, Any], y: np.ndarray, comp: Mapping[str, Any]) -> tuple:
    """One ``analyse_array`` result with its incomplete-data readings (D59 (ii)).

    Returns (guarded block, readings). A test whose statistic has no finite entry, or a
    session test of a size without two sessions, is replaced by ``not_estimable``; DR2 is
    not estimable when either of its tests is; DR5 is not evaluable as registered when a
    size lacks two sessions."""
    E, R, rules = O.frozen("estimators"), O.frozen("records"), O.frozen("rules")
    out = copy.deepcopy(dict(block))
    notes: list[str] = []
    tests = out["tests"]
    single = list(comp["sizes_without_two_sessions"])
    two = list(comp["sizes_with_two_sessions"])
    with _quiet():
        n_delta = _finite_count(E.task_delta(y))
        per_size_delta = [np.nanmean(E.harness_diff(y)[zi], axis=-1) for zi in range(len(R.SIZES))]
        q = E.x_per_task_pooled(y)
        u = E.session_task_shift(y)
    if n_delta < 2:
        tests["delta_paired_t"]["p"] = not_estimable(
            "fewer than two tasks with a harness difference"
        )
        notes.append("delta paired t: not estimable")
    for zi, z in enumerate(R.SIZES):
        if _finite_count(per_size_delta[zi]) < 2:
            tests["delta_paired_t_by_size"][zi]["p"] = not_estimable(
                f"{z}: fewer than two tasks with a harness difference"
            )
            notes.append(f"delta paired t ({z}): not estimable")
    x_missing = _finite_count(q) == 0
    if x_missing:
        reason = "no task has two sessions holding both harness cells (all-NaN statistic)"
        tests["x_signflip_p"] = not_estimable(reason)
        if tests.get("x_label_permutation_p_sensitivity") is not None:
            tests["x_label_permutation_p_sensitivity"] = not_estimable(reason)
        notes.append("X sign-flip test and label permutation: not estimable (all-NaN q_t)")
    sessions = list(tests["session_signflip_p"])
    for zi, z in enumerate(R.SIZES):
        if z in single or _finite_count(u[zi]) == 0:
            sessions[zi] = not_estimable(f"{z} does not hold two sessions (all-NaN u_zt)")
            notes.append(f"session sign-flip test ({z}): not estimable")
    tests["session_signflip_p"] = sessions
    for name in ("delta_session_heterogeneity", "session_common_share"):
        part = out.get(name) or {}
        for key, values in list(part.items()):
            if isinstance(values, list):
                part[key] = [
                    not_estimable(f"{z} does not hold two sessions") if z in single else v
                    for z, v in zip(R.SIZES, values, strict=True)
                ]
    delta_p = tests["delta_paired_t"]["p"]
    if x_missing or isinstance(delta_p, dict):
        out["DR2"] = not_estimable("DR2 reads the delta paired t and the X sign-flip test")
        notes.append("DR2: not estimable")
    elif single:
        out["DR2"]["incomplete_note"] = (
            f"read on incomplete data: the X test and the pi_small bound here come from "
            f"{', '.join(two)} alone (the registered two-size pi_small is undefined unless DR1 "
            f"drops 4B); the Near-equivalent branch reads that bound"
        )
    if single:
        out["pi_small_rule_note"] = (
            f"{', '.join(single)} lacks two sessions, so pi_small (the registered mean of pi_4B "
            f"and pi_9B) is undefined; the value shown is the mean over {', '.join(two) or 'none'}"
        )
        out["pooled_over_sizes"] = two
        out["DR5"] = {
            "outcome": DR5_NOT_EVALUABLE,
            "reason": f"{', '.join(single)} does not hold two sessions (D59 (ii))",
            "description_only": pi_9b_description(out["estimates"], rules),
        }
        notes.append("DR5: not evaluable as registered; pi_9B against both M as a description")
        sessions_4b = comp["sizes"]["4B"]["sessions"]
        if not sessions_4b:
            out["DR1_drop_4B"] = not_estimable("4B has no scored base record")
            notes.append("DR1: not estimable")
        else:
            out["DR1_read_on_sessions"] = sessions_4b
            notes.append(f"DR1: read on {', '.join(sessions_4b)} only")
        out["read_on_one_session"] = {z: comp["sizes"][z]["sessions"] for z in single}
    return out, notes


def pi_9b_description(estimates: Mapping[str, Any], rules: Any) -> dict[str, Any]:
    pi = estimates.get("pi_9B") or {}
    lb, ub = (pi.get("one_sided_95") or [None, None])[:2]
    if pi.get("estimate") is None or lb is None or ub is None:
        return not_estimable("pi_9B is not estimable")
    return {
        "pi_9B": pi,
        "against_M": {
            name: {"M": m, "lower_bound_above_M": lb > m, "upper_bound_below_M": ub < m}
            for name, m in (("M_SMALL", rules.M_SMALL), ("M_9B", rules.M_9B))
        },
        "reading": "description only (D59 (ii)); no DR5 outcome is read",
    }


def mask_predictions(
    predictions: Mapping[str, Any], primary: Mapping[str, Any], comp: Mapping[str, Any], costs: bool
) -> tuple:
    out = copy.deepcopy(dict(predictions))
    notes: list[str] = []
    single = list(comp["sizes_without_two_sessions"])
    two = list(comp["sizes_with_two_sessions"])
    if single:
        for name in ("P1", "P2"):
            if name in out and isinstance(out[name], dict):
                out[name]["incomplete_note"] = f"pooled over {', '.join(two)} only"
    if isinstance(primary.get("DR2"), dict) and "not_estimable" in primary["DR2"]:
        out["P3"] = not_estimable("P3 reads DR2")
        notes.append("P3: not estimable")
    dr1 = primary.get("DR1_drop_4B")
    if isinstance(dr1, dict) and "not_estimable" in dr1:
        out["P4"] = not_estimable("P4 reads DR1")
        notes.append("P4: not estimable")
    elif primary.get("DR1_read_on_sessions"):
        out["P4"]["incomplete_note"] = (
            f"DR1 read on {', '.join(primary['DR1_read_on_sessions'])} only"
        )
    if not costs:
        out["P5"] = not_estimable("P5 reads DR4, which needs --costs (bug B8)")
        notes.append("P5: not evaluated (no costs)")
    return out, notes


def guard_registered(
    report: Mapping[str, Any], arrays: Sequence[np.ndarray], comp: Mapping[str, Any], costs: bool
) -> tuple:
    """The registered report with every incomplete-data reading applied."""
    if len(arrays) != len(SET_ORDER):
        raise O.OpsError(f"the report built {len(arrays)} analysis arrays, not {len(SET_ORDER)}")
    out = copy.deepcopy(dict(report))
    readings: list[str] = []
    for name, y in zip(SET_ORDER, arrays, strict=True):
        if out[name]["tasks"] != y.shape[1]:
            raise O.OpsError(f"{name}: the captured array does not match the report")
        guarded, notes = mask_block(out[name], y, comp)
        out[name] = guarded
        readings += [f"{name}: {note}" for note in notes]
    out["predictions"], notes = mask_predictions(out["predictions"], out["primary"], comp, costs)
    readings += [f"predictions: {note}" for note in notes]
    if comp["incomplete"]:
        out["label"] = INCOMPLETE
    return out, readings


# --------------------------------------------------------------------------- delta-only report


def delta_block(y: np.ndarray, comp: Mapping[str, Any]) -> dict[str, Any]:
    """Delta, its bootstrap intervals and paired t tests, success and DR1, from the
    registered functions, for data in which no size holds two sessions."""
    A, E, rules = O.frozen("analysis"), O.frozen("estimators"), O.frozen("rules")

    def stacked(yy: np.ndarray) -> np.ndarray:
        by_size = E.delta_by_size(yy)
        return np.stack(
            [E.delta(yy), by_size[..., 0], by_size[..., 1], by_size[..., 0] - by_size[..., 1]],
            axis=-1,
        )

    with _quiet():
        point = stacked(y)
        draws = E.bootstrap(y, stacked, A.N_BOOT, A.SEED)
        est: dict[str, Any] = {}
        for i, name in enumerate(DELTA_NAMES):
            lo95, hi95 = E.percentile_interval(draws[:, i], 0.95)
            lb, ub = E.one_sided_bounds(draws[:, i], 0.95)
            est[name] = {
                "estimate": A._f(point[..., i]),
                "ci95": [A._f(lo95), A._f(hi95)],
                "one_sided_95": [A._f(lb), A._f(ub)],
            }
        t = E.paired_t(E.task_delta(y), level=0.90)
        t_by_size = [E.paired_t(np.nanmean(E.harness_diff(y)[z], axis=-1)) for z in range(2)]
        succ = E.success(y)
    tests: dict[str, Any] = {
        "delta_paired_t": {
            "p": A._f(t["p"]),
            "estimate": A._f(t["estimate"]),
            "ci90_t": [A._f(t["ci_low"]), A._f(t["ci_high"])],
        },
        "delta_paired_t_by_size": [
            {"p": A._f(tt["p"]), "estimate": A._f(tt["estimate"])} for tt in t_by_size
        ],
    }
    if int(t["n"]) < 2:
        tests["delta_paired_t"]["p"] = not_estimable(
            "fewer than two tasks with a harness difference"
        )
    for zi, tt in enumerate(t_by_size):
        if int(tt["n"]) < 2:
            tests["delta_paired_t_by_size"][zi]["p"] = not_estimable("fewer than two tasks")
    out: dict[str, Any] = {
        "tasks": int(y.shape[1]),
        "success_by_size_harness": A._f(succ),
        "estimates": est,
        "tests": tests,
        "not_estimable": {
            name: "no size holds two sessions (D59 (ii))" for name in NEEDS_TWO_SESSIONS
        },
    }
    sessions_4b = comp["sizes"]["4B"]["sessions"]
    if sessions_4b:
        out["DR1_drop_4B"] = rules.dr1(list(succ[0]))
        out["DR1_read_on_sessions"] = sessions_4b
    else:
        out["DR1_drop_4B"] = not_estimable("4B has no scored base record")
    return out


def delta_only_report(
    records: Sequence[Mapping[str, Any]],
    plan: Mapping[str, Any],
    costs: Mapping[str, Any] | None,
    comp: Mapping[str, Any],
) -> dict[str, Any]:
    """The guarded report when no size holds two sessions: ``analysis.report``'s sets, counts
    and descriptions, with every estimand that needs two sessions marked not estimable."""
    A, E, R, rules = (O.frozen(n) for n in ("analysis", "estimators", "records", "rules"))
    recs = [R.validate(r) for r in records]
    finals = R.final_records(recs)
    base = list(plan["base"])
    blocks = {int(k): v for k, v in plan.get("extension_blocks", {}).items()}
    done = R.completed_extension_blocks(recs, blocks)
    secondary_tasks = base + [t for b in done for t in blocks[b]]
    flagged = list(plan.get("flagged_tasks", []))

    def run(tasks: Sequence[str], on: Mapping[Any, Any] = finals, **kw: Any) -> dict[str, Any]:
        return delta_block(R.outcome_array(on, tasks, **kw), comp)

    missing = A.postconfig_missing(finals)
    without = {k: r for k, r in finals.items() if k not in missing}
    base_set = set(base)
    counts = A.infrastructure_counts(recs, finals)
    with widened_check(), _quiet():
        fractional = A._f(E.delta(R.outcome_array(finals, base, value="score")))
    out: dict[str, Any] = {
        "label": INCOMPLETE,
        "primary": run(base),
        "sensitivity_metric_exception_missing": run(base, metric_exception_missing=True),
        "sensitivity_postconfig_server_error_missing": {
            "episodes_missing": sum(1 for key in missing if key[2] in base_set),
            **run(base, without),
        },
        "sensitivity_flagged_tasks_excluded": run([t for t in base if t not in flagged]),
        "secondary_base_plus_completed_extension": {"blocks": done, **run(secondary_tasks)},
        "fractional_score": fractional,
        "cells": counts["final_records"]["size_harness"],
        "cells_by_size_session": counts["final_records"]["size_session"],
        "cells_by_size_harness_session": counts["final_records"]["size_harness_session"],
        "attempts": counts["attempts"],
        "truncation": A.truncation_labels(finals),
        "uncertified_exposure": A.exposure_strata(finals, base),
        "checker_noise": A.checker_noise(finals),
    }
    with _quiet():
        out["delta_by_exposure_stratum"] = {
            name: (A._f(E.delta(R.outcome_array(finals, tasks))) if tasks else None)
            for name, tasks in out["uncertified_exposure"].items()
        }
        out["checker_corrected"] = {
            **run(base, value="corrected"),
            "flips_per_task": A.corrected_flips(finals, base),
        }
        mediator = R.outcome_array(finals, base, drop_truncated=True)
        out["truncation"]["delta_without_truncated_episodes_mediator_description"] = A._f(
            E.delta(mediator)
        )
        if "task_domains" in plan:
            out["per_domain"] = A.per_domain(finals, base, plan["task_domains"])
    predictions: dict[str, Any] = {
        "P1": not_estimable("no size holds two sessions (D59 (ii))"),
        "P2": not_estimable("no size holds two sessions (D59 (ii))"),
        "P3": not_estimable("P3 reads DR2, which is not estimable"),
    }
    dr1 = out["primary"]["DR1_drop_4B"]
    if isinstance(dr1, dict):
        predictions["P4"] = not_estimable("P4 reads DR1, which is not estimable")
    else:
        predictions["P4"] = {
            "falsified": dr1,
            "read": "DR1",
            "incomplete_note": "DR1 read on "
            f"{', '.join(out['primary']['DR1_read_on_sessions'])} only",
        }
    if costs:
        dr4 = rules.dr4({job: (c["gpu_h_per_episode"], c["V"]) for job, c in costs.items()})
        out["DR4"] = dr4
        out["cost_card"] = {"jobs": dict(costs), "by_size": A.costs_by_size(costs)}
        predictions["P5"] = {"falsified": dr4["exceeds_high"], "read": "DR4"}
    else:
        predictions["P5"] = not_estimable("P5 reads DR4, which needs --costs (bug B8)")
    out["predictions"] = predictions
    out["conditional_on"] = "the realized sessions (tasks resampled, sessions fixed)"
    anchor_runs = bool((plan.get("constants") or {}).get("anchor_runs")) and bool(
        plan.get("anchor_tasks")
    )
    out["external_anchor"] = (
        {"outcome": "pending ANC", "label": None}
        if anchor_runs
        else {"outcome": "ANCHOR-UNAVAILABLE", "label": A.NOT_ANCHORED}
    )
    return out


def guarded_analysis(y: np.ndarray, comp: Mapping[str, Any]) -> tuple:
    """``analyse_array`` on one set with the guard applied (for the operator's extra sets,
    such as the secondary set under corrected verdicts); a delta-only block when no size
    holds two sessions."""
    A = O.frozen("analysis")
    if not comp["sizes_with_two_sessions"]:
        return delta_block(y, comp), ["no size holds two sessions: delta-only block"]
    with widened_check():
        block = A.analyse_array(y, n_boot=A.N_BOOT, n_rand=A.N_RANDOMIZATION)
    return mask_block(block, y, comp)


def fractional_base_scores(records: Sequence[Mapping[str, Any]], base: Sequence[str]) -> int:
    R = O.frozen("records")
    base_set = set(base)
    return sum(
        1
        for key, rec in R.final_records(records).items()
        if key[2] in base_set and rec["status"] == "scored" and 0 < float(rec["score"]) < 1
    )


# --------------------------------------------------------------------------- command line


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--export", type=Path, required=True, help="export of the freeze commit")
    parser.add_argument("--records", type=Path, required=True, help="merged A1 records (a1.jsonl)")
    parser.add_argument("--plan", type=Path, required=True, help="the frozen plan")
    parser.add_argument("--costs", type=Path, help="costs.json (analysis costs)")
    parser.add_argument(
        "--dr0", type=Path, action="append", required=True,
        help="a job's 'rules dr0' output (one per A1 job that ran)",
    )  # fmt: skip
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    O.use_export(args.export)
    R = O.frozen("records")
    out_dir = args.out_dir
    for name in ("report.json", "guard.json", "report-guarded.json"):
        if (out_dir / name).exists():
            raise O.OpsError(f"{out_dir / name} exists; operator outputs are never overwritten")
    out_dir.mkdir(parents=True, exist_ok=True)
    registered_argv = ["--records", str(args.records), "--plan", str(args.plan)]
    if args.costs:
        registered_argv += ["--costs", str(args.costs)]
    registered_argv += ["--out", str(out_dir / "report.json")]
    records = R.read_jsonl(args.records)
    plan = O.read_json(args.plan)
    dr0 = [O.read_json(path) for path in args.dr0]
    costs = O.read_json(args.costs) if args.costs else None
    comp = completeness(records, plan, dr0)  # refuses bad inputs before anything is written
    arrays: list[np.ndarray] = []
    error = registered_report(registered_argv, arrays)
    report_path = out_dir / "report.json"
    guard: dict[str, Any] = {
        "schema": O.SCHEMA + "-guard",
        "d59": "(i) estimators._check widened to [0, 1] and NaN; (ii) incomplete-data guard",
        "inputs": {
            "records": O.sha256_file(args.records),
            "plan": O.sha256_file(args.plan),
            "costs": O.sha256_file(args.costs) if args.costs else None,
            "dr0": {
                item.get("job"): O.sha256_file(p) for item, p in zip(dr0, args.dr0, strict=True)
            },
        },
        "registered_report": {
            "argv": [
                "python3",
                "-E",
                "-s",
                "-B",
                "-m",
                "harness.q2_stage1.analysis",
                *registered_argv,
            ],
            "written": report_path.is_file(),
            "sha256": O.sha256_file(report_path) if report_path.is_file() else None,
            "error": error,
        },
        "fractional_base_scores": fractional_base_scores(records, plan["base"]),
        "completeness": comp,
        "label": INCOMPLETE if comp["incomplete"] else None,
    }
    if not comp["sizes_with_two_sessions"]:
        guarded = delta_only_report(records, plan, costs, comp)
        readings = [
            "no size holds two sessions: delta-only report; "
            + ", ".join(NEEDS_TWO_SESSIONS)
            + " not estimable (D59 (ii))"
        ]
        kind = "delta-only report (no size holds two sessions)"
    elif error is None:
        report = O.read_json(report_path)
        guarded, readings = guard_registered(report, arrays, comp, costs is not None)
        kind = "registered report with the guard's readings"
    else:
        guard["readings"] = []
        O.write_new(out_dir / "guard.json", O.dumps(guard))
        raise O.OpsError(f"the registered report failed with complete-enough data: {error}")
    if comp["incomplete"]:
        readings.insert(0, f"every output labelled {INCOMPLETE}: {'; '.join(comp['reasons'])}")
    guard["readings"] = readings
    guard["guarded_report"] = {"path": "report-guarded.json", "kind": kind}
    guarded["guard"] = {
        "label": guard["label"],
        "completeness": comp,
        "readings": readings,
        "registered_report_sha256": guard["registered_report"]["sha256"],
    }
    guarded_path = O.write_new(out_dir / "report-guarded.json", O.dumps(guarded))
    guard["guarded_report"]["sha256"] = O.sha256_file(guarded_path)
    O.write_new(out_dir / "guard.json", O.dumps(guard))
    print(json.dumps({"label": guard["label"], "registered_report_written": report_path.is_file(),
                      "error": error, "kind": kind}))  # fmt: skip
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
