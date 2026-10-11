"""Registered constants and rule of ``q2-zinv-reserve-validation-v1`` (sections 3, 6 and 7).

Pure functions over rescored rows; no I/O. A row is one item the ``rescore`` step scored twice
(the original ``compare_pptx_files`` and ``compare_pptx_files_zinv``): an evaluable mutant of
a reserve pptx target, or a saved gold or do-nothing state of a reserve task, each checked by
``compare_pptx_files`` alone. Its keys: ``id``, ``task_id``, ``kind`` (``mutant``, ``gold``,
``initial``), ``operator``, ``label``, ``stored`` (the registered lock-exact score of the
frozen pipeline), ``raw`` and ``zinv`` (the rescoring's scores, None when the scoring raised),
``raw_error``/``zinv_error``, ``raw_infra``/``zinv_infra`` (no result within the timeout),
``files_sha256`` (a path-independent digest of the job's files: each VM path with the SHA-256
of its local file) and ``files_unchanged`` (that digest taken again after both scorings is
the same and no file is missing). The parent's ``scored_sha256`` is kept in the rows for the
record but never compared: it hashes the scorer's temporary path, so it differs between any
two scorings of the same files.

The rule (section 6), as the dossier asks it: zinv accepts at least 95% of the held-out z-order
equivalence mutants (condition A) while accepting no violation mutant the original rejects
(condition B). Below 20 z-order mutants or 8 tasks the reading is descriptive (dossier O4).
"""

from __future__ import annotations

import random
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from harness.q2_mutation import stats
from harness.q2_mutation.schema import verdict_for_score

EXPERIMENT_ID = "q2-zinv-reserve-validation-v1"
REGISTRATION = "program/preregistrations/q2-zinv-reserve-validation-v1.md"
PARENT_ID = "q2-evaluator-mutation-v1"
SPLIT = "reserve"
TARGET_FAMILY = "pptx"
# The reserve split's pptx targets, one per task, counted before this draft from task configs
# only (program/evidence/q2-mutation/integration/prefreeze-counts-v2/counts.json); each task is
# checked by compare_pptx_files alone. ``select-targets`` refuses any other reserve selection.
RESERVE_PPTX_TASKS = (
    "05dd4c1d-c489-4c85-8389-a7836c4f0567",
    "39be0d19-634d-4475-8768-09c130f5425d",
    "7dbc52a6-11e0-4c9a-a2cb-1e36cfda80d8",
    "841b50aa-df53-47bd-a73a-22d3a9f73160",
    "8979838c-54a5-4454-a2b8-3d135a1a5c8f",
    "986fc832-6af2-417c-8845-9272b3a1528b",
    "c82632a4-56b6-4db4-9dd1-3820ee3388e4",
    "f23acfd2-c485-4b7c-a1e7-d4303ddfe864",
)
ZORDER = "pptx.eq.zorder_nonoverlap"
FAMILY = "compare_pptx_files"
EQUIV = "should_pass_equiv"
VIOLATION = "should_fail_violation"
EXTRA = "should_fail_extra_change"

# Condition A: accepted * ACCEPT_DEN >= ACCEPT_NUM * n (95%, in integers so 19 of 20 passes).
ACCEPT_NUM, ACCEPT_DEN = 95, 100
# Dossier O4: descriptive below 20 z-order mutants or 8 tasks.
MIN_MUTANTS = 20
MIN_TASKS = 8
N_BOOT = 10_000
SEED = 42
ALPHA = 0.05

# Code reused unchanged (each pinned elsewhere; section 3).
ZINV_SHA256 = "64899d5056f4791008c2a10c38a7b0fbb94fbe912d20a702ec74851a0ca7f655"
RESCORE_SHA256 = "d240db03e969c8aa5bb97403c5005cd4c9e96016599a78f70e97850415893737"
STAGE1_INIT_SHA256 = "0e2190149cf640fac07dab26332a26f696374ff4400c23aab82e8cf766f3b334"
PARENT_CODE_TREE_SHA256 = "58bee0190c0c7eb5d44f36e27c0f1e0daab82c1c48716009a9066777c69a0721"
# The parent's reserve control run (Slurm 791-793): the saved golds and do-nothing states.
RESERVE_CONTROLS_RUN = "reserve-controls-v1"
RESERVE_CONTROLS = {
    "jobs-saved-mounted.jsonl": "595f31c3ac3ec4eb06dacb0855ec3fad868943a75023d4866c7a60eb23dcee7f",
    "saved-verdicts-lock.jsonl": "a9dea13f32917e4f0d6f5c06904b18d03ceb7daaf0ad988b43cb3c7117723159",
}
RESERVE_CONTROLS_SUMMARY_SHA256 = "1da426424339678c35847380f63ba9bae9983cc4a88beaed19171b118c55bb9b"
# Evaluable z-order mutants per evaluable compare_pptx_files target of the confirm campaign
# (released outcomes, targets sorted by task id; section 4): the expected-size model.
CONFIRM_ZORDER_YIELDS = (3, 3, 3, 0, 3, 3, 3, 3, 2, 2, 3, 2, 3, 1, 2, 3)

OUTCOMES = ("PASS", "PASS_A_ONLY", "FAIL", "NOT_TESTABLE", "INCOMPLETE")
STATUSES = ("descriptive", "registered_rule")
# What each reading licenses (section 7); written into the judgement.
LICENSES = {
    "PASS": {
        "descriptive": (
            "Descriptive: zinv accepted at least 95% of the held-out z-order mutants and newly "
            "accepted no violation mutant, on fewer than 20 mutants or 8 tasks. It licenses "
            "'the correction held on reserve documents it was not developed on, at this size', "
            "with the exact lower bound stated; not a claim that zinv accepts 95% of z-order "
            "equivalents in general."
        ),
        "registered_rule": (
            "The registered rule passed at the registered size (at least 20 mutants on 8 "
            "tasks). It licenses 'the correction generalizes to held-out reserve documents at "
            "the observed rate', with the exact and task-level lower bounds stated; the rule "
            "is a point-estimate rule, so the population claim is the lower bound, not 95%."
        ),
    },
    "PASS_A_ONLY": {
        status: (
            "Condition A held but no evaluable violation mutant existed, so condition B is "
            "untested; only the acceptance half of the question is answered."
        )
        for status in STATUSES
    },
    "FAIL": {
        status: (
            "An existence result at any size: zinv rejected a held-out z-order mutant beyond "
            "the 5% allowance or accepted a violation mutant the original rejects. The note "
            "reports zinv as validated on its development split only; zinv is not changed "
            "under this registration."
        )
        for status in STATUSES
    },
    "NOT_TESTABLE": {
        status: "No evaluable held-out z-order mutant exists; nothing is licensed."
        for status in STATUSES
    },
    "INCOMPLETE": {
        status: (
            "A decision item failed a validity check (infrastructure, a rescoring that does "
            "not reproduce the registered verdict, or scored files that differ); no outcome."
        )
        for status in STATUSES
    },
}


def verdict(score: float | None) -> str:
    """``pass``, ``fail`` or ``error`` (None), as the parent's schema maps a score."""
    return verdict_for_score(score)


def is_pass(score: float | None) -> bool:
    return verdict(score) == "pass"


def in_z(row: Mapping[str, Any]) -> bool:
    """A held-out z-order equivalence mutant (condition A's population)."""
    return (
        row.get("kind") == "mutant" and row.get("operator") == ZORDER and row.get("label") == EQUIV
    )


def in_v(row: Mapping[str, Any]) -> bool:
    """A violation mutant (condition B's population), of any operator."""
    return row.get("kind") == "mutant" and row.get("label") == VIOLATION


def meets_threshold(accepted: int, n: int) -> bool:
    return n > 0 and accepted * ACCEPT_DEN >= ACCEPT_NUM * n


def status_for(n: int, tasks: int) -> str:
    return "descriptive" if n < MIN_MUTANTS or tasks < MIN_TASKS else "registered_rule"


def validity_problems(row: Mapping[str, Any], *, require_file_check: bool = True) -> list[str]:
    """Why a row cannot be read: infrastructure, a raw rescoring that does not reproduce the
    registered verdict, or job files that changed or went missing during the rescoring."""
    problems = []
    if row.get("raw_infra") or row.get("zinv_infra"):
        problems.append("infrastructure")
    if verdict(row.get("raw")) != verdict(row.get("stored")):
        problems.append("raw_differs_from_stored")
    checked = row.get("files_unchanged")
    if checked is False or (require_file_check and checked is not True):
        problems.append("files_changed_or_missing")
    return problems


def _interval(interval: stats.Interval) -> dict[str, Any]:
    return {
        "estimate": interval.estimate,
        "low": interval.low,
        "high": interval.high,
        "n_clusters": interval.n_clusters,
        "n_units": interval.n_units,
        "method": interval.method,
    }


def _ids(rows: Iterable[Mapping[str, Any]]) -> list[str]:
    return sorted(str(r["id"]) for r in rows)


def judge(
    rows: Sequence[Mapping[str, Any]],
    *,
    require_file_check: bool = True,
    n_boot: int = N_BOOT,
    seed: int = SEED,
) -> dict[str, Any]:
    """The registered outcome, its status, intervals and the reported-only quantities."""
    ids = [str(r["id"]) for r in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate row ids")
    z = [r for r in rows if in_z(r)]
    v = [r for r in rows if in_v(r)]
    decision = {str(r["id"]) for r in z + v}
    invalid = {
        str(r["id"]): problems
        for r in rows
        if (problems := validity_problems(r, require_file_check=require_file_check))
    }
    invalid_decision = sorted(i for i in invalid if i in decision)

    z_tasks = sorted({str(r["task_id"]) for r in z})
    accepted = [r for r in z if is_pass(r.get("zinv"))]
    v_tasks = sorted({str(r["task_id"]) for r in v})
    new_accepts = [r for r in v if not is_pass(r.get("stored")) and is_pass(r.get("zinv"))]
    status = status_for(len(z), len(z_tasks))
    cond_a = meets_threshold(len(accepted), len(z))
    cond_b = not new_accepts
    if invalid_decision:
        outcome = "INCOMPLETE"
    elif not cond_b:
        outcome = "FAIL"  # a newly accepted violation is a counterexample at any size
    elif not z:
        outcome = "NOT_TESTABLE"
    elif cond_a:
        outcome = "PASS" if v else "PASS_A_ONLY"
    else:
        outcome = "FAIL"
    reasons = []
    if z and not cond_a:
        reasons.append("acceptance_below_95_percent")
    if not cond_b:
        reasons.append("violation_newly_accepted")

    out: dict[str, Any] = {
        "experiment_id": EXPERIMENT_ID,
        "outcome": outcome,
        "status": status,
        "license": LICENSES[outcome][status],
        "fail_reasons": reasons,
        "condition_a": {
            "rule": f"accepted * {ACCEPT_DEN} >= {ACCEPT_NUM} * n",
            "held": cond_a,
            "n": len(z),
            "tasks": len(z_tasks),
            "accepted": len(accepted),
            "not_accepted": _ids(r for r in z if not is_pass(r.get("zinv"))),
        },
        "condition_b": {
            "rule": "no violation mutant with an original fail and a zinv pass",
            "held": cond_b,
            "tested": bool(v),
            "n": len(v),
            "tasks": len(v_tasks),
            "new_accepts": _ids(new_accepts),
        },
        "descriptive_floor": {"min_mutants": MIN_MUTANTS, "min_tasks": MIN_TASKS},
        "validity": {
            "invalid_rows": {k: invalid[k] for k in sorted(invalid)},
            "invalid_decision_rows": invalid_decision,
            "require_file_check": require_file_check,
        },
    }
    if z:
        k, n = len(accepted), len(z)
        by_task: dict[str, list[bool]] = defaultdict(list)
        for r in z:
            by_task[str(r["task_id"])].append(is_pass(r.get("zinv")))
        whole = sum(all(events) for events in by_task.values())
        units = [stats.Unit(str(r["task_id"]), is_pass(r.get("zinv"))) for r in z]
        out["acceptance"] = {
            "share": k / n,
            "exact_95": list(stats.clopper_pearson(k, n, ALPHA)),
            "exact_one_sided_95_lower": 1.0 - stats.exact_upper_bound(n - k, n, ALPHA),
            "tasks_all_accepted": whole,
            "task_level_one_sided_95_lower": 1.0
            - stats.exact_upper_bound(len(by_task) - whole, len(by_task), ALPHA),
            "task_equal": _interval(stats.cluster_bootstrap_ci(units, n_boot=n_boot, seed=seed)),
        }
        out["original_on_z"] = {
            "fails": sum(not is_pass(r.get("stored")) for r in z),
            "n": n,
            "task_equal": _interval(
                stats.cluster_bootstrap_ci(
                    [stats.Unit(str(r["task_id"]), not is_pass(r.get("stored"))) for r in z],
                    n_boot=n_boot,
                    seed=seed,
                )
            ),
        }
        out["z_by_task"] = {
            task: {
                "n": len(events),
                "accepted": sum(events),
                "original_fails": sum(
                    not is_pass(r.get("stored")) for r in z if str(r["task_id"]) == task
                ),
            }
            for task, events in sorted(by_task.items())
        }
    if v:
        hit_tasks = {str(r["task_id"]) for r in new_accepts}
        out["violation_bounds"] = {
            "mutant_one_sided_95_upper": stats.exact_upper_bound(len(new_accepts), len(v), ALPHA),
            "task_one_sided_95_upper": stats.exact_upper_bound(len(hit_tasks), len(v_tasks), ALPHA),
            "original_passes": _ids(r for r in v if is_pass(r.get("stored"))),
        }

    def direction(r: Mapping[str, Any]) -> str:
        return f"{verdict(r.get('stored'))}->{verdict(r.get('zinv'))}"

    others = [r for r in rows if not in_z(r)]
    out["reported"] = {
        "rows": len(rows),
        "by_kind": dict(sorted(Counter(str(r.get("kind")) for r in rows).items())),
        "mutants_by_label": dict(
            sorted(Counter(str(r.get("label")) for r in rows if r.get("kind") == "mutant").items())
        ),
        "other_items_changed": [
            {
                "id": str(r["id"]),
                "kind": r.get("kind"),
                "operator": r.get("operator"),
                "label": r.get("label"),
                "change": direction(r),
            }
            for r in sorted(others, key=lambda x: str(x["id"]))
            if verdict(r.get("zinv")) != verdict(r.get("stored"))
        ],  # fmt: skip
        "other_items_equal": sum(
            verdict(r.get("zinv")) == verdict(r.get("stored")) for r in others
        ),
        "other_items": len(others),
        "extra_change_new_accepts": _ids(
            r
            for r in rows
            if r.get("kind") == "mutant"
            and r.get("label") == EXTRA
            and not is_pass(r.get("stored"))
            and is_pass(r.get("zinv"))
        ),  # fmt: skip
        "regressions_pass_to_not_pass": _ids(
            r for r in rows if is_pass(r.get("stored")) and not is_pass(r.get("zinv"))
        ),
        "zinv_errors": _ids(r for r in rows if r.get("zinv_error")),
        "zorder_other_labels": _ids(
            r
            for r in rows
            if r.get("kind") == "mutant" and r.get("operator") == ZORDER and r.get("label") != EQUIV
        ),  # fmt: skip
    }
    return out


# --------------------------------------------------------------------------- design (section 4)


def max_misses(n: int) -> int:
    """The most z-order mutants zinv may reject with condition A still holding."""
    return n - -(-ACCEPT_NUM * n // ACCEPT_DEN)


def p_fail_a(n: int, p: float, per_task: int = 1) -> float:
    """P(condition A fails) when each z-order mutant is accepted with probability ``p``:
    independently (``per_task`` 1), or all or none within tasks of ``per_task`` mutants."""
    if n <= 0 or per_task <= 0 or n % per_task:
        raise ValueError("n must be a positive multiple of per_task")
    tasks = n // per_task
    return 1.0 - stats.binomial_cdf(max_misses(n) // per_task, tasks, 1.0 - p)


def p80_acceptance(n: int, per_task: int = 1) -> float:
    """The true acceptance below which condition A fails with probability at least 0.8."""
    low, high = 0.0, 1.0
    for _ in range(200):
        mid = (low + high) / 2
        if p_fail_a(n, mid, per_task) > 0.8:
            low = mid
        else:
            high = mid
    return (low + high) / 2


def q80_new_accept(n_violation: int) -> float:
    """The true per-mutant new-accept rate that condition B detects with probability 0.8."""
    return 1.0 - 0.2 ** (1.0 / n_violation)


def floor_probability(
    yields: Sequence[int] = CONFIRM_ZORDER_YIELDS,
    targets: int = len(RESERVE_PPTX_TASKS),
    sims: int = 100_000,
    seed: int = SEED,
) -> dict[str, float]:
    """Resampling the confirm yields per target: P(at least 20 mutants), P(8 tasks with a
    z-order mutant), P(both, the registered-rule status) and the mean size."""
    rng = random.Random(f"{seed}:floor")
    both = mutants = tasks = 0
    total = 0
    for _ in range(sims):
        draw = [rng.choice(yields) for _ in range(targets)]
        n, t = sum(draw), sum(1 for x in draw if x > 0)
        total += n
        mutants += n >= MIN_MUTANTS
        tasks += t >= MIN_TASKS
        both += n >= MIN_MUTANTS and t >= MIN_TASKS
    return {
        "p_registered_rule": both / sims,
        "p_at_least_20_mutants": mutants / sims,
        "p_8_tasks": tasks / sims,
        "mean_mutants": total / sims,
    }


def design_table() -> dict[str, Any]:
    """The numbers section 4 quotes (rounded there to the digits shown)."""
    sizes = (12, 15, 18, 21, 24)
    rates = (0.80, 0.85, 0.90, 0.95)
    return {
        "max_misses": {n: max_misses(n) for n in (*sizes, 20)},
        "p_fail_independent": {n: {p: p_fail_a(n, p) for p in rates} for n in sizes},
        "p_fail_tasks_of_3": {n: {p: p_fail_a(n, p, 3) for p in rates} for n in sizes},
        "p80_independent": {n: p80_acceptance(n) for n in sizes},
        "p80_tasks_of_3": {n: p80_acceptance(n, 3) for n in sizes},
        "q80_violation": {n: q80_new_accept(n) for n in (15, 20, 25, 30)},
        "zero_miss_lower_bound": {n: 1.0 - stats.zero_event_upper_bound(n) for n in sizes},
        "floor": floor_probability(),
    }
