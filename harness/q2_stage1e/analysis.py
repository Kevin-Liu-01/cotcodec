"""The registered analysis of `q2-stage1-successor-e-v1`: S1a's estimators and rules on E's
four-session, one-rerun array.

Usage (CPU, after the last E job)::

    python -m harness.q2_stage1e.analysis report --records e.jsonl --plan plan-e.json \
        --costs costs.json --dr0 dr0-<job>.json [--dr0 ...] --out report.json
    python -m harness.q2_stage1e.analysis costs --run-dir RUN [--run-dir ...] --out costs.json
    python -m harness.q2_stage1e.analysis dr0 --run-dir RUN --plan plan-e.json
    python -m harness.q2_stage1e.analysis joint --records e.jsonl \
        --s1a-records a1.jsonl --plan plan-e.json --out joint.json
    python -m harness.q2_stage1e.analysis glmm-input --records e.jsonl --plan plan-e.json \
        --out glmm-input.csv
    python -m harness.q2_stage1e.analysis section15 --records e.jsonl --plan plan-e.json \
        --report report.json --costs costs.json --run-dir RUN [--run-dir ...] --out s15.json

Every estimand, test and rule is S1a's code of record, imported unchanged
(``harness.q2_stage1.estimators``, ``rules``, and ``analysis``' counts and cost helpers).
The frozen estimators are defined for any S >= 2 sessions and R >= 1 reruns: X_z is the mean
over ordered session pairs of d_zts * d_zts' (at S = 2 it is d_zt1 * d_zt2), D_b is the
discordance over every cross-session pair, X_c uses the variance over sessions, and the X
sign-flip test flips each task's pooled product q_t. With E's S = 4 and R = 1:

* **not estimable**: D_w, the session excess D_b - D_w (so prediction P1), the cross-block
  D_b and the common session share rho (each needs a within-session pair); the same-block
  D_b equals D_b;
* **two-session quantities by pair**: S1a's session shift (S2 - S1) with its sign-flip test,
  and the harness effect by session, are computed by the frozen two-session functions on
  each of the six session pairs per size, and reported (descriptive; no rule reads them);
  delta per session is reported too.

S1a's ``analysis.analyse_array`` cannot take S != 2 (its session-shift statistics raise), so
``analyse_array`` here makes the same calls in the same order for E's array; on an S1a-shaped
array it reproduces S1a's estimates, tests, DR2 and DR5 (``tests/test_q2_stage1e_analysis``).

The D59, D61 and D62 rules, fixed for S1a while blind, are registered here up front:

* D59 (i): the fractional-score sensitivity reads checker scores in [0, 1] through
  ``widened_check`` (the frozen check accepts only 0, 1 and NaN); nothing else is widened;
* D59 (ii), D61, D62 (incomplete data): every output is labelled ``incomplete`` when DR0
  fired for any E job or a registered job has no records; estimates are the registered
  code's on the data collected; a size with fewer than two sessions holding scored records,
  or with no task holding both harness cells in two sessions, has no X and no pi, and DR5 is
  then "not evaluable as registered" (pi_9B against both M as a description only); DR2 is
  kept with a note, or not estimable when its tests have no finite statistic; no p-value is
  read from an all-NaN statistic.

The D82 gold-defect sensitivity (registration section 9) recomputes every primary estimand,
test and rule reading without the three pool tasks whose saved gold D82's adjudication
rejected (``plan.D82_GOLD_DEFECT_TASKS``, the plan's ``gold_defect_tasks_d82``), on raw and on
checker-corrected verdicts. It is a sensitivity: it changes no primary set, rule or DR.

The joint reading with S1a (``joint_reading``) is descriptive: E is its own sample, and
no E rule, test or prediction reads S1a's sessions.
"""

from __future__ import annotations

import argparse
import contextlib
import itertools
import json
import math
import sys
import warnings
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from harness.q2_stage1 import analysis as A1
from harness.q2_stage1 import estimators as E
from harness.q2_stage1 import records as R1
from harness.q2_stage1 import rules
from harness.q2_stage1e import plan as PE
from harness.q2_stage1e import records as RE

N_BOOT = A1.N_BOOT
N_RANDOMIZATION = A1.N_RANDOMIZATION
SEED = A1.SEED
NOT_ANCHORED = A1.NOT_ANCHORED
INCOMPLETE = "incomplete"
DR5_NOT_EVALUABLE = "not evaluable as registered"
R1_REASON = "not estimable with one episode per session (R = 1): it needs a within-session pair"
SIZES = PE.SIZES
SESSIONS = PE.SESSIONS
SESSION_PAIRS = tuple(itertools.combinations(range(len(SESSIONS)), 2))
D80_LABEL = "adjudicated by an isolated model on the owner's instruction (D80); not human-validated"
JOINT_LABEL = (
    "descriptive joint reading of S1a and E: not registered inference; no rule, test or "
    "prediction reads it; S1a's design and E's were both fixed before their own data, but E's "
    "design and scenarios were chosen after S1a's readings"
)
_f = A1._f


def not_estimable(reason: str) -> dict[str, str]:
    return {"not_estimable": reason}


@contextlib.contextmanager
def _quiet() -> Iterator[None]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        yield


def pair_label(a: int, b: int) -> str:
    return f"{SESSIONS[a]}-{SESSIONS[b]}"


# --------------------------------------------------------------------------- D59 (i)


@contextlib.contextmanager
def widened_check() -> Iterator[None]:
    """D59 (i): the frozen ``estimators._check`` with its outcome test widened from {0, 1}
    to [0, 1] (shape checks unchanged), for the fractional-score sensitivity only. The
    frozen estimators look ``_check`` up at call time; the original is restored on exit."""
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


# --------------------------------------------------------------------------- estimands


def statistics(y: np.ndarray) -> dict[str, np.ndarray]:
    """Every bootstrapped estimand of S1a section 9 that E's array defines, by the frozen
    functions (pooled values are means over the sizes that have one, as in S1a)."""
    with _quiet():
        db = E.d_between(y)
        x = E.x_by_size(y)
        pis = E.pi_share(x, db)
        dz = E.delta_by_size(y)
        xc = E.x_centred_by_size(y)
        ds = E.delta_by_session(y)
        out: dict[str, np.ndarray] = {
            "delta": E.delta(y),
            "delta_4B": dz[..., 0],
            "delta_9B": dz[..., 1],
            "scale_screen_delta": dz[..., 0] - dz[..., 1],
            "D_b_4B": db[..., 0],
            "D_b_9B": db[..., 1],
            "D_b": np.nanmean(db, axis=-1),
            "X_4B": x[..., 0],
            "X_9B": x[..., 1],
            "X": np.nanmean(x, axis=-1),
            "X_centred_4B": xc[..., 0],
            "X_centred_9B": xc[..., 1],
            "X_bernoulli": np.nanmean(E.x_bernoulli_by_size(y), axis=-1),
            "pi_4B": pis[..., 0],
            "pi_9B": pis[..., 1],
            # pi_small is this mean unless DR1 drops 4B (then pi_9B): analyse_array applies it.
            "pi_small": np.nanmean(pis, axis=-1),
            "scale_screen_pi": pis[..., 0] - pis[..., 1],
        }
        for zi, z in enumerate(SIZES):
            for si, s in enumerate(SESSIONS[: y.shape[-2]]):
                out[f"delta_{z}_{s}"] = ds[..., zi, si]
        for a, b in SESSION_PAIRS:
            if b >= y.shape[-2]:
                continue
            shift = E.session_shift(y[..., [a, b], :])
            for zi, z in enumerate(SIZES):
                out[f"session_shift_{z}_{SESSIONS[b]}_minus_{SESSIONS[a]}"] = shift[..., zi]
    return out


def _finite_count(values: Any) -> int:
    return int(np.isfinite(np.asarray(values, dtype=float)).sum())


def pi_9b_description(estimates: Mapping[str, Any]) -> dict[str, Any]:
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


def analyse_array(
    y: np.ndarray,
    *,
    n_boot: int = N_BOOT,
    n_rand: int = N_RANDOMIZATION,
    seed: int = SEED,
    label_permutation: bool = True,
) -> dict[str, Any]:
    """Estimates, 95% bootstrap intervals, one-sided bounds, tests and DR1, DR2, DR5 for one
    (Z, K, H, S, R) array, in S1a's ``analysis.analyse_array`` order: the bootstrap (seed),
    then from one generator the X sign flip, the label permutation and the session tests."""
    y = np.asarray(y, dtype=float)
    point = statistics(y)
    names = list(point)

    def stacked(yy: np.ndarray) -> np.ndarray:
        values = statistics(yy)
        return np.stack([values[name] for name in names], axis=-1)

    with _quiet():
        draws = E.bootstrap(y, stacked, n_boot, seed)
        boot = {name: draws[:, i] for i, name in enumerate(names)}
        est: dict[str, Any] = {}
        for name in names:
            lo95, hi95 = E.percentile_interval(boot[name], 0.95)
            lb, ub = E.one_sided_bounds(boot[name], 0.95)
            est[name] = {
                "estimate": _f(point[name]),
                "ci95": [_f(lo95), _f(hi95)],
                "one_sided_95": [_f(lb), _f(ub)],
            }
        rng = np.random.default_rng(seed)
        dbar = E.task_delta(y)
        t = E.paired_t(dbar, level=0.90)
        per_size_d = [np.nanmean(E.harness_diff(y)[z], axis=-1) for z in range(len(SIZES))]
        t_by_size = [E.paired_t(d) for d in per_size_d]
        q = E.x_per_task_pooled(y)
        p_x = float(E.x_signflip_p(y, n_rand, rng))
        p_x_label = float(E.x_label_permutation_p(y, n_rand, rng)) if label_permutation else None
        pairs: dict[str, Any] = {}
        heterogeneity: dict[str, Any] = {}
        for a, b in SESSION_PAIRS:
            if b >= y.shape[-2]:
                continue
            yy = y[..., [a, b], :]
            label = pair_label(a, b)
            p = E.session_signflip_p(yy, n_rand, rng)
            u = E.session_task_shift(yy)
            pairs[label] = [
                _f(p[zi]) if _finite_count(u[zi]) else not_estimable(
                    f"{z}: no task holds both sessions of {label} (all-NaN u_zt)")
                for zi, z in enumerate(SIZES)
            ]  # fmt: skip
            het = E.delta_session_heterogeneity(yy)
            heterogeneity[label] = {k: _f(v) for k, v in het.items()}
        succ = E.success(y)
        by_session = [E.success(y[..., [s], :]) for s in range(y.shape[-2])]
    tests: dict[str, Any] = {
        "delta_paired_t": {
            "p": _f(t["p"]),
            "estimate": _f(t["estimate"]),
            "ci90_t": [_f(t["ci_low"]), _f(t["ci_high"])],
        },
        "delta_paired_t_by_size": [
            {"p": _f(tt["p"]), "estimate": _f(tt["estimate"])} for tt in t_by_size
        ],
        "x_signflip_p": p_x,
        "x_label_permutation_p_sensitivity": p_x_label,
        "session_signflip_p_by_pair": pairs,
        "session_signflip_holm_by_size": {
            z: rules_holm([pairs[k][zi] for k in pairs]) for zi, z in enumerate(SIZES)
        },
    }
    notes: list[str] = []
    # D59 (ii): no p-value is read from a statistic with no finite entry.
    if _finite_count(dbar) < 2:
        tests["delta_paired_t"]["p"] = not_estimable(
            "fewer than two tasks with a harness difference"
        )
        notes.append("delta paired t: not estimable")
    for zi, z in enumerate(SIZES):
        if _finite_count(per_size_d[zi]) < 2:
            tests["delta_paired_t_by_size"][zi]["p"] = not_estimable(
                f"{z}: fewer than two tasks with a harness difference"
            )
    x_missing = _finite_count(q) == 0
    if x_missing:
        reason = "no task has two sessions holding both harness cells (all-NaN q_t)"
        tests["x_signflip_p"] = not_estimable(reason)
        if p_x_label is not None:
            tests["x_label_permutation_p_sensitivity"] = not_estimable(reason)
        notes.append("X sign-flip test: not estimable")
    drop_4b: Any = rules.dr1(list(succ[0])) if _finite_count(succ[0]) == len(succ[0]) else None
    est["pi_mean_4B_9B"] = est["pi_small"]
    if drop_4b:
        est["pi_small"] = dict(est["pi_9B"])
    no_pi = [z for zi, z in enumerate(SIZES) if not np.isfinite(point[f"pi_{z}"])]
    ub = est["pi_small"]["one_sided_95"][1]
    if drop_4b is None:
        dr1_out: Any = not_estimable("4B has no scored record under a harness")
        notes.append("DR1: not estimable")
    else:
        dr1_out = drop_4b
    if x_missing or isinstance(tests["delta_paired_t"]["p"], dict) or ub is None:
        dr2: dict[str, Any] = not_estimable("DR2 reads the delta paired t, the X sign-flip "
                                            "test and the pi_small bound")  # fmt: skip
        notes.append("DR2: not estimable")
    else:
        dr2 = rules.dr2(float(t["p"]), p_x, (float(t["ci_low"]), float(t["ci_high"])), ub)
        if no_pi:
            dr2["incomplete_note"] = (
                f"{', '.join(no_pi)} has no X and no pi here; the X test and the pi_small bound "
                "come from the other size (D61 (b), D62)"
            )
    if no_pi:
        dr5: dict[str, Any] = {
            "outcome": DR5_NOT_EVALUABLE,
            "reason": f"{', '.join(no_pi)} has no pi in this set (fewer than two sessions with "
                      "both harness cells on any task; D59 (ii), D61, D62)",
            "description_only": pi_9b_description(est),
        }  # fmt: skip
        notes.append("DR5: not evaluable as registered")
    else:
        share = "pi_9B" if drop_4b else "pi_small"
        lb5, ub5 = est[share]["one_sided_95"]
        dr5 = (
            rules.dr5(lb5, ub5, bool(drop_4b))
            if lb5 is not None and ub5 is not None
            else {"outcome": DR5_NOT_EVALUABLE, "reason": "the DR5 share has no finite bound"}
        )
    return {
        "tasks": int(y.shape[1]),
        "sessions": int(y.shape[-2]),
        "reruns": int(y.shape[-1]),
        "success_by_size_harness": _f(succ),
        "success_by_session_size_harness": {SESSIONS[s]: _f(v) for s, v in enumerate(by_session)},
        "estimates": est,
        "not_estimable_at_R1": {
            name: not_estimable(R1_REASON)
            for name in (
                "D_w_4B",
                "D_w_9B",
                "D_w",
                "excess_4B",
                "excess_9B",
                "excess",
                "D_b_cross_block",
                "session_common_share",
            )
        }
        if y.shape[-1] == 1
        else {},  # fmt: skip
        "D_b_same_block": "equals D_b with one episode per session",
        "tests": tests,
        "delta_session_heterogeneity_by_pair": heterogeneity,
        "DR1_drop_4B": dr1_out,
        "pi_small_rule": "pi_9B (DR1 drops 4B)" if drop_4b else "mean of pi_4B and pi_9B",
        "pi_undefined_sizes": no_pi,
        "DR2": dr2,
        "DR5": dr5,
        "readings": notes,
    }


def rules_holm(p_values: Sequence[Any], alpha: float = 0.05) -> dict[str, Any]:
    """Holm over a size's six pairwise session tests (descriptive; no rule reads it)."""
    finite = [float(p) for p in p_values if isinstance(p, int | float)]
    return {
        "tests": len(finite),
        "any_reject_familywise_5pct": E.holm_any(finite, alpha) if finite else None,
    }


# --------------------------------------------------------------------------- completeness


def completeness(
    records: Sequence[Mapping[str, Any]],
    plan: Mapping[str, Any],
    dr0: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Which E jobs ran, whether DR0 fired for any (the given ``dr0`` outputs, receipts
    included, and DR0 recomputed from the records alone), and the sessions each size holds."""
    order = list(plan["job_order"])
    tasks = list(plan["tasks"])
    for rec in records:
        size, session = PE.parse_job(rec["job"])
        if (rec["size"], rec["session"]) != (size, session):
            raise ValueError(
                f"record {rec.get('slot')!r}: job {rec['job']} is not its size/session"
            )
    present = [job for job in order if any(r["job"] == job for r in records)]
    given = {}
    for item in dr0:
        job = item.get("job")
        if job not in order or job in given:
            raise ValueError(f"a DR0 output names an unknown or repeated job {job!r}")
        given[job] = item
    jobs: dict[str, Any] = {}
    for job in order:
        size, session = PE.parse_job(job)
        again = RE.job_dr0(records, job=job, size=size, session=session, tasks=tasks) if (
            job in present) else None  # fmt: skip
        item = given.get(job) or {}
        jobs[job] = {
            "records": job in present,
            "dr0_fires": bool(item.get("fires")),
            "dr0_reasons": list(item.get("reasons") or []),
            "dr0_from_records_fires": bool(again and again["fires"]),
            "dr0_from_records_reasons": list((again or {}).get("reasons") or []),
        }
    fired = [j for j, v in jobs.items() if v["dr0_fires"] or v["dr0_from_records_fires"]]
    absent = [job for job in order if job not in present]
    held = RE.sessions_with_scored(RE.final_records(records), tasks)
    short = [z for z in SIZES if len(held[z]) < len(SESSIONS)]
    reasons = []
    if fired:
        reasons.append(f"DR0 fired for {', '.join(fired)}")
    if absent:
        reasons.append(f"no records from {', '.join(absent)}")
    if short:
        reasons.append(f"{', '.join(short)} holds fewer than four sessions of scored records")
    return {
        "registered_job_order": order,
        "jobs_present": present,
        "jobs_absent": absent,
        "jobs": jobs,
        "dr0_fired": fired,
        "sessions_by_size": held,
        "sizes_with_two_sessions": [z for z in SIZES if len(held[z]) >= 2],
        "incomplete": bool(reasons),
        "reasons": reasons,
    }


# --------------------------------------------------------------------------- the report


def per_domain(
    finals: Mapping[R1.SlotKey, Mapping[str, Any]],
    tasks: Sequence[str],
    domains: Mapping[str, str],
) -> dict[str, Any]:
    """Descriptive: tasks, success by size and harness, and delta per domain."""
    out: dict[str, Any] = {}
    with _quiet():
        for domain in sorted({domains[t] for t in tasks}):
            ts = [t for t in tasks if domains[t] == domain]
            y = RE.outcome_array(finals, ts)
            out[domain] = {
                "tasks": len(ts),
                "success_by_size_harness": _f(E.success(y)),
                "delta": _f(E.delta(y)),
            }
    return out


def predictions(primary: Mapping[str, Any], dr4_exceeds: bool | None) -> dict[str, Any]:
    """P1-P5 (S1a section 12) read once on the primary set. P1 reads D_b - D_w, which needs
    a within-session pair, so it is not estimable in E."""
    est = primary["estimates"]
    db = est["D_b"]["ci95"]
    dr2, dr1 = primary["DR2"], primary["DR1_drop_4B"]
    base = rules.predictions(
        excess_ub95=math.nan,
        db_ci95=(
            db[0] if db[0] is not None else math.nan,
            db[1] if db[1] is not None else math.nan,
        ),
        dr2_class=str(dr2.get("class")),
        dr1_fires=bool(dr1) if not isinstance(dr1, dict) else False,
        dr4_exceeds=bool(dr4_exceeds),
    )
    out = dict(base)
    out["P1"] = {**not_estimable(R1_REASON), "read": base["P1"]["read"]}
    if None in db:
        out["P2"] = {**not_estimable("pooled D_b has no interval"), "read": base["P2"]["read"]}
    if "not_estimable" in dr2:
        out["P3"] = {**not_estimable("P3 reads DR2"), "read": "DR2"}
    if isinstance(dr1, dict):
        out["P4"] = {**not_estimable("P4 reads DR1"), "read": "DR1"}
    if dr4_exceeds is None:
        out["P5"] = {**not_estimable("P5 reads DR4, which needs the cost file"), "read": "DR4"}
    return out


def report(
    records: Sequence[Mapping[str, Any]],
    plan: Mapping[str, Any],
    *,
    costs: Mapping[str, Any] | None = None,
    dr0: Sequence[Mapping[str, Any]] = (),
    n_boot: int = N_BOOT,
    n_rand: int = N_RANDOMIZATION,
    step_logs: Mapping[R1.SlotKey, Sequence[Mapping[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Primary (all 113 tasks, raw verdicts), sensitivities, the registered secondary set
    (S1a's 32 base tasks), the counts of S1a section 15, DR0-DR5, DR-A and P1-P5."""
    recs = [RE.validate(r) for r in records]
    finals = RE.final_records(recs)
    tasks = list(plan["tasks"])
    flagged = list(plan.get("flagged_tasks", []))
    gold_defect = list(plan["gold_defect_tasks_d82"])
    without_gold_defect = [t for t in tasks if t not in gold_defect]
    comp = completeness(recs, plan, dr0)

    def run(task_list: Sequence[str], on: Mapping[R1.SlotKey, Any] = finals, **kw: Any) -> dict:
        y = RE.outcome_array(on, list(task_list), **kw)
        return analyse_array(y, n_boot=n_boot, n_rand=n_rand)

    missing = A1.postconfig_missing(finals)
    without_postconfig_errors = {k: r for k, r in finals.items() if k not in missing}
    task_set = set(tasks)
    counts = A1.infrastructure_counts(recs, finals)
    with widened_check(), _quiet():  # D59 (i): scores in [0, 1], this one sensitivity only
        fractional = _f(E.delta(RE.outcome_array(finals, tasks, value="score")))
    out: dict[str, Any] = {
        "experiment_id": PE.EXPERIMENT_ID,
        "primary": run(tasks),
        "sensitivity_metric_exception_missing": run(tasks, metric_exception_missing=True),
        "sensitivity_postconfig_server_error_missing": {
            "episodes_missing": sum(1 for key in missing if key[2] in task_set),
            **run(tasks, without_postconfig_errors),
        },
        "sensitivity_flagged_tasks_excluded": run([t for t in tasks if t not in flagged]),
        "sensitivity_d82_gold_defect_tasks_excluded": {
            "tasks_excluded": gold_defect,
            "label": D80_LABEL,
            "reading": "sensitivity (section 9): it changes no primary set, rule or DR",
            **run(without_gold_defect),
            "checker_corrected": run(without_gold_defect, value="corrected"),
        },
        "secondary_s1a_base": run(plan["s1a_base"]),
        "fractional_score": fractional,
        "cells": counts["final_records"]["size_harness"],
        "cells_by_size_session": counts["final_records"]["size_session"],
        "cells_by_size_harness_session": counts["final_records"]["size_harness_session"],
        "attempts": counts["attempts"],
        "truncation": A1.truncation_labels(finals),
        "uncertified_exposure": A1.exposure_strata(finals, tasks),
        "checker_noise": A1.checker_noise(finals),
    }
    with _quiet():
        out["delta_by_exposure_stratum"] = {
            name: (_f(E.delta(RE.outcome_array(finals, ts))) if ts else None)
            for name, ts in out["uncertified_exposure"].items()
        }
        out["truncation"]["delta_without_truncated_episodes_mediator_description"] = _f(
            E.delta(RE.outcome_array(finals, tasks, drop_truncated=True))
        )
    out["checker_corrected"] = {
        **run(tasks, value="corrected"),
        "flips_per_task": A1.corrected_flips(finals, tasks),
    }
    if "task_domains" in plan:
        out["per_domain"] = per_domain(finals, tasks, plan["task_domains"])
    if step_logs is not None:
        out["first_divergence"] = A1.divergence_summary(step_logs)
    exceeds: bool | None = None
    if costs:
        dr4 = rules.dr4({job: (c["gpu_h_per_episode"], c["V"]) for job, c in costs.items()})
        out["DR4"] = dr4
        out["cost_card"] = {"jobs": dict(costs), "by_size": A1.costs_by_size(costs)}
        exceeds = bool(dr4["exceeds_high"])
    out["predictions"] = predictions(out["primary"], exceeds)
    out["completeness"] = comp
    out["labels"] = {
        "incomplete": INCOMPLETE if comp["incomplete"] else None,
        "incomplete_reasons": list(comp["reasons"]),
        "external_anchor": NOT_ANCHORED,
    }
    out["conditional_on"] = "E's realized sessions (tasks resampled, sessions fixed)"
    out["external_anchor"] = {"outcome": "ANCHOR-UNAVAILABLE", "label": NOT_ANCHORED}
    out["not_pooled_with_s1a"] = (
        "E is its own sample: no estimate, test, rule or prediction here reads S1a's sessions; "
        "the joint reading is a separate descriptive output (joint.json)"
    )
    return out


# --------------------------------------------------------------------------- joint reading

JOINT_NAMES = ("delta", "delta_4B", "delta_9B", "D_b_4B", "D_b_9B", "D_b",
               "X_4B", "X_9B", "X", "pi_4B", "pi_9B", "pi_mean_4B_9B")  # fmt: skip


def _joint_stats(y: np.ndarray) -> np.ndarray:
    with _quiet():
        db = E.d_between(y)
        x = E.x_by_size(y)
        pis = E.pi_share(x, db)
        dz = E.delta_by_size(y)
        cols = [E.delta(y), dz[..., 0], dz[..., 1], db[..., 0], db[..., 1],
                np.nanmean(db, axis=-1), x[..., 0], x[..., 1], np.nanmean(x, axis=-1),
                pis[..., 0], pis[..., 1], np.nanmean(pis, axis=-1)]  # fmt: skip
    return np.stack(cols, axis=-1)


def joint_reading(
    e_records: Sequence[Mapping[str, Any]],
    s1a_records: Sequence[Mapping[str, Any]],
    tasks: Sequence[str],
    *,
    n_boot: int = N_BOOT,
    seed: int = SEED,
) -> dict[str, Any]:
    """S1a and E side by side on the same tasks, their difference (E minus S1a) and the six
    sessions together, each with a task-cluster bootstrap that resamples the tasks jointly
    for both samples (seed 42). Descriptive only (``JOINT_LABEL``)."""
    fe = RE.final_records(e_records)
    fs = R1.final_records(s1a_records)
    ye = RE.outcome_array(fe, list(tasks))  # (Z, K, H, 4, 1)
    ys = R1.outcome_array(fs, list(tasks))  # (Z, K, H, 2, 2)
    n_s1a = ys.shape[-2]
    yj = np.full((*ys.shape[:3], n_s1a + ye.shape[-2], ys.shape[-1]), np.nan)
    yj[..., :n_s1a, :] = ys
    yj[..., n_s1a:, :1] = ye
    k = len(JOINT_NAMES)

    def fn(y: np.ndarray) -> np.ndarray:
        s1a = _joint_stats(y[..., :n_s1a, :])
        e = _joint_stats(y[..., n_s1a:, :1])
        both = _joint_stats(y)
        return np.concatenate([s1a, e, e - s1a, both], axis=-1)

    point = fn(yj)
    with _quiet():
        draws = E.bootstrap(yj, fn, n_boot, seed)
    out: dict[str, Any] = {"label": JOINT_LABEL, "tasks": len(tasks)}
    for part, offset in (("s1a", 0), ("e", k), ("e_minus_s1a", 2 * k), ("six_sessions", 3 * k)):
        block = {}
        for i, name in enumerate(JOINT_NAMES):
            column = draws[:, offset + i]
            lo, hi = E.percentile_interval(column, 0.95) if np.isfinite(column).any() else (
                math.nan, math.nan)  # fmt: skip
            block[name] = {"estimate": _f(point[offset + i]), "ci95": [_f(lo), _f(hi)]}
        out[part] = block
    out["designs"] = {
        "s1a": "2 sessions x 2 reruns per size (q2-stage1-rescoped-v1, its 113-task secondary set)",
        "e": "4 sessions x 1 rerun per size (q2-stage1-successor-e-v1)",
        "six_sessions": "both, cell means over the reruns each session holds; D_b pools every "
                        "cross-session pair, S1a's with E's included",
    }  # fmt: skip
    return out


# --------------------------------------------------------------------------- costs, DR0


def costs_main(argv: Sequence[str]) -> int:
    """Realized cost per E job (S1a section 9 item 10, ``analysis.realized_costs`` and
    ``gpu_elapsed`` unchanged): the GPU job's Slurm elapsed hours over the job's episodes."""
    parser = argparse.ArgumentParser(description="E realized cost per job (DR4, P5)")
    parser.add_argument("--run-dir", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(list(argv))
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; cost files are never overwritten")
    out: dict[str, Any] = {}
    for run_dir in args.run_dir:
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("purpose") != "e":
            raise SystemExit(f"{run_dir} is not an E job's run directory")
        e = manifest.get("e") or {}
        job = PE.job_name(str(e.get("size")), str(e.get("session")))
        receipt = json.loads((run_dir / "lane-receipt.json").read_text(encoding="utf-8"))
        rows = RE.read_jsonl(run_dir / "episodes.jsonl")
        stopped_path = Path(str(receipt.get("bridge_dir") or "")) / "stopped.json"
        stopped = (
            json.loads(stopped_path.read_text(encoding="utf-8"))
            if receipt.get("bridge_dir") and stopped_path.is_file()
            else None
        )
        elapsed = A1.gpu_elapsed(receipt, stopped)
        out[job] = {
            **A1.realized_costs(rows, job=job, v=int(manifest["vm"]["concurrency"]),
                                gpu_elapsed_s=elapsed["gpu_elapsed_s"]),
            "gpu_elapsed_source": elapsed["source"],
        }  # fmt: skip
    args.out.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return 0


def run_dir_dr0(run_dir: Path, plan: Mapping[str, Any], gate_breach: str | None = None) -> dict:
    """DR0 for the E job whose lane run directory this is, with the files' digests."""
    import hashlib

    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("purpose") != "e":
        raise ValueError("DR0 judges E jobs only")
    e = manifest.get("e") or {}
    size, session = str(e.get("size")), str(e.get("session"))
    job = PE.job_name(size, session)
    episodes, receipt_path = run_dir / "episodes.jsonl", run_dir / "lane-receipt.json"
    rows = [json.loads(x) for x in episodes.read_text(encoding="utf-8").splitlines() if x.strip()]
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    out = RE.job_dr0(rows, job=job, size=size, session=session, tasks=plan["tasks"],
                     receipt=receipt, gate_breach=gate_breach)  # fmt: skip
    out["files"] = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (run_dir / "manifest.json", episodes, receipt_path)
    }
    return out


def main(argv: Sequence[str] | None = None) -> int:
    raw = list(argv) if argv is not None else sys.argv[1:]
    if raw[:1] == ["costs"]:
        return costs_main(raw[1:])
    if raw[:1] == ["glmm-synthetic"]:
        from harness.q2_stage1 import glmm as G

        syn = argparse.ArgumentParser(description="E-shaped synthetic GLMM input (pre-freeze)")
        syn.add_argument("--out", type=Path, required=True)
        syn.add_argument("--k", type=int, default=113)
        syn.add_argument("--seed", type=int, default=42)
        a = syn.parse_args(raw[1:])
        if a.out.exists():
            raise SystemExit(f"{a.out} exists; outputs are never overwritten")
        rows = RE.glmm_synthetic(a.k, a.seed)
        G.write_csv(rows, a.out)
        meta = {"rows": len(rows), "k": a.k, "seed": a.seed, "truth": G.SYNTHETIC_TRUTH}
        a.out.with_suffix(".truth.json").write_text(json.dumps(meta, indent=1, sort_keys=True))
        print(json.dumps({"rows": len(rows)}))
        return 0
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    rep = sub.add_parser("report", help="the registered report")
    rep.add_argument("--records", type=Path, required=True)
    rep.add_argument("--plan", type=Path, required=True)
    rep.add_argument("--costs", type=Path)
    rep.add_argument("--dr0", type=Path, action="append", default=[])
    rep.add_argument("--out", type=Path, required=True)
    dr0 = sub.add_parser("dr0", help="DR0 of one E job (infrastructure records only)")
    dr0.add_argument("--run-dir", type=Path, required=True)
    dr0.add_argument("--plan", type=Path, required=True)
    dr0.add_argument("--gate-breach")
    joint = sub.add_parser("joint", help="the descriptive joint reading with S1a")
    joint.add_argument("--records", type=Path, required=True)
    joint.add_argument("--s1a-records", type=Path, required=True)
    joint.add_argument("--plan", type=Path, required=True)
    joint.add_argument("--out", type=Path, required=True)
    glmm = sub.add_parser("glmm-input", help="the secondary GLMM's input (S1a's columns)")
    glmm.add_argument("--records", type=Path, required=True)
    glmm.add_argument("--plan", type=Path, required=True)
    glmm.add_argument("--out", type=Path, required=True)
    s15 = sub.add_parser("section15", help="the descriptive items of S1a section 15 (D59 (iii))")
    s15.add_argument("--records", type=Path, required=True)
    s15.add_argument("--plan", type=Path, required=True)
    s15.add_argument("--report", type=Path, required=True, help="report.json: its labels")
    s15.add_argument("--costs", type=Path)
    s15.add_argument("--run-dir", type=Path, action="append", default=[])
    s15.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(raw)
    plan = PE.load_plan(args.plan)
    if args.command == "dr0":
        out = run_dir_dr0(args.run_dir, plan, args.gate_breach)
        print(json.dumps(out, indent=1, sort_keys=True))
        return 3 if out["fires"] else 0
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; outputs are never overwritten")
    if args.command == "glmm-input":
        from harness.q2_stage1 import glmm as G

        rows = RE.glmm_rows(RE.final_records(RE.read_jsonl(args.records)), plan["tasks"])
        G.write_csv(rows, args.out)
        print(json.dumps({"rows": len(rows)}))
        return 0
    if args.command == "section15":
        from harness.q2_stage1e import section15 as S15

        labels = json.loads(args.report.read_text(encoding="utf-8"))["labels"]
        costs = json.loads(args.costs.read_text(encoding="utf-8")) if args.costs else None
        result = S15.assemble(RE.read_jsonl(args.records), plan, labels=labels, costs=costs,
                              runs=S15.run_dirs_by_job(args.run_dir))  # fmt: skip
    elif args.command == "joint":
        result = joint_reading(RE.read_jsonl(args.records), R1.read_jsonl(args.s1a_records),
                               plan["tasks"])  # fmt: skip
    else:
        costs = json.loads(args.costs.read_text(encoding="utf-8")) if args.costs else None
        dr0_items = [json.loads(p.read_text(encoding="utf-8")) for p in args.dr0]
        result = report(RE.read_jsonl(args.records), plan, costs=costs, dr0=dr0_items)
    args.out.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
