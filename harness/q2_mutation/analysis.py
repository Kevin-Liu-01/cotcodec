"""Registered analysis of q2-evaluator-mutation-v1 (preregistration sections 4-10, 12).

Everything the registration computes after the runs, fixed in code before the
freeze so no analysis choice is made after a result is read. Decision D35:
D34's exit fired on the development audit (rater kappa below 0.6 after the one
permitted retry), so the study is a pre-specified descriptive protocol. The
confirmatory headline is empty: P1 was already replication only, and P2-P5
are always excluded from it (``D34_DEV_EXIT``), whatever the confirm audit
shows; they are still computed and reported as exploratory.

* P1 (replication only): saved-gold flips among golds exposed to the save
  stage (``report.p1_counted``), raw and audit-confirmed, with exact
  Clopper-Pearson intervals, over the confirm and the reserve control runs
  together (``p1_over_controls``: counts and flips are summed, the two runs'
  tasks must be disjoint and belong to their splits); K1 stays confirm-only;
* the checker candidates (``checker_candidates``, decision D35, descriptive):
  false-negative candidates are the evaluable ``should_pass_equiv`` and
  ``should_pass_alt_solution`` mutants outside probe-touched cells that the
  checker does not pass; false-positive candidates are the evaluable
  ``should_fail_violation`` and ``should_fail_extra_change`` mutants outside
  them that it passes. Each is listed with its audit decision and what that
  decision says (confirmed, label contradicted, unresolved, not audited);
  counts and task-equal candidate shares with the task-cluster percentile
  bootstrap are given pooled, per label, per checker family and per operator,
  and the audit-confirmed shares where the audit covered every candidate;
* P2 (exploratory): evaluable ``should_pass_equiv`` mutants plus the
  ``should_pass_alt_solution`` mutants the audit accepted; event: not pass;
* P3 (exploratory): evaluable ``should_fail_violation`` mutants; event: pass;
* P4 (exploratory): evaluable ``should_fail_extra_change`` mutants; event: the
  checker passes it and the audit rejects it. A passed extra-change mutant the
  audit does not reject (accepted, unresolved or not sampled) leaves P4's
  numerator and denominator; a failed one stays in the denominator. The count
  with unresolved items as events is a sensitivity estimate;
* P5 (exploratory): tasks with an evaluable equivalence or violation mutant,
  with at least one FN or FP_R event (exact interval);
* pooled rates and family rates are task-equal means with the task-cluster
  percentile bootstrap (10,000 resamples, seed 42); the family floor (8 tasks,
  20 mutants) is reported per family (``above_family_floor``) and decides
  where the descriptive K6b and K7 flags are computed;
* K2: a checker family with an unexplained in-VM/offline disagreement is
  dropped: P2-P5 and the candidates are recomputed without that family's
  mutants, and the dropped family's tables and the pooled rates including it
  are reported separately (``k2_exploratory``); without a K2 report the
  result is labelled ``offline harness, VM fidelity unverified``;
* K3 (reported): the K3 reasons are listed with the metrics they concern, next
  to the D34 exit; K4 is reported and is no longer a stop (D35);
* gold defects (decision D34): the tasks whose gold sham the audit decided
  reject (``raters.summarize``) are reported with P2 recomputed without those
  tasks' equivalence mutants, and each candidate carries its task's flag;
* K5, K9; K6's adequacy claim is retired (always blocked, with the reasons),
  and K6b and K7 are descriptive flags.

Every population is the one ``campaign.build_report`` marks: evaluable under
the primary venv and outside probe-touched cells (probe cells and the
probe-informed operators); candidate events inside probe-touched cells are
counted separately and are not audited.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from harness.q2_mutation.schema import SHOULD_FAIL_LABELS, SHOULD_PASS_LABELS
from harness.q2_mutation.stats import (
    Unit,
    clopper_pearson,
    cluster_bootstrap_ci,
    zero_event_upper_bound,
)

FAMILY_MIN_TASKS = 8
FAMILY_MIN_MUTANTS = 20
K6B_MIN_TASKS = 29
K7_NULL = 0.05
K9_MAX_NULL_NOT_PASS = 0.25
K5_MAX_NORMALIZED = 0.5
K2_EXPLANATIONS = (
    "save_slower_than_0_5s",
    "nondeterministic",
    "injection_hash_mismatch",
    "vm_infrastructure_failure",
)
K2_UNVERIFIED = "offline harness, VM fidelity unverified"
METRICS = ("P2", "P3", "P4", "P5")
# Decision D34 (i), applied by D35: after the one permitted rater retry the
# development audit (dev-audit-v4) gave rater kappa 0.066 under the registered
# ingest and 0.575 with the workflow harness's relay turn excepted (a
# sensitivity), both below 0.6. P2-P5 therefore leave the confirmatory
# headline before the confirm campaign runs, whatever the confirm audit shows.
D34_DEV_EXIT_REASON = "D34 (i): development kappa below 0.6"
D34_DEV_EXIT: Mapping[str, Any] = {
    "decision": "D34 (i), applied by D35",
    "fired": True,
    "reason": D34_DEV_EXIT_REASON,
    "metrics": METRICS,
    "audit": "dev-audit-v4",
    "kappa_min": 0.6,
    "kappa_registered": 0.0663,
    "kappa_relay_excepted_sensitivity": 0.5752,
    "evidence": "program/evidence/q2-mutation/integration/rater-isolated-dev-v4/summary.json",
}
K6_RETIRED = "D35: K6's adequacy claim is retired (P5 left the confirmatory headline under D34)"
K4_ROLE = "reported only; not a stop (D35)"
DESCRIPTIVE = "descriptive (D35): no confirmatory claim"
# Decision D35: the checker candidates the descriptive protocol reports.
CANDIDATE_KINDS: Mapping[str, tuple[str, ...]] = {
    "false_negative": ("should_pass_equiv", "should_pass_alt_solution"),
    "false_positive": ("should_fail_violation", "should_fail_extra_change"),
}
# The audit decision that confirms a candidate (the raters, or Kevin, read the
# end state as the label says while the checker disagrees).
CONFIRMING = {"false_negative": "accept", "false_positive": "reject"}


def _ci(units: Sequence[Unit], n_boot: int, seed: int) -> dict[str, Any] | None:
    if not units:
        return None
    ci = cluster_bootstrap_ci(units, n_boot=n_boot, seed=seed)
    return {
        "rate": ci.estimate,
        "low": ci.low,
        "high": ci.high,
        "tasks": ci.n_clusters,
        "mutants": ci.n_units,
    }


def _exact(k: int, n: int) -> dict[str, Any] | None:
    if n == 0:
        return None
    low, high = clopper_pearson(k, n)
    return {"events": k, "n": n, "share": k / n, "low": low, "high": high}


def population(rows: Sequence[Mapping[str, Any]], primary: str) -> list[Mapping[str, Any]]:
    return [
        r for r in rows if r.get(f"{primary}_status") == "evaluable" and not r.get("probe_touched")
    ]


def metric_units(
    rows: Sequence[Mapping[str, Any]],
    decisions: Mapping[str, str] | None,
    primary: str,
) -> tuple[dict[str, list[tuple[str, str, bool]]], dict[str, Any]]:
    """(task, family, event) per metric P2-P4, and what the audit gate removed."""
    units: dict[str, list[tuple[str, str, bool]]] = {"P2": [], "P3": [], "P4": []}
    gate: dict[str, Counter[str]] = {"P2_alt": Counter(), "P4_passed": Counter()}
    sensitivity_p4: list[tuple[str, str, bool]] = []
    for r in population(rows, primary):
        label = r["label"]
        passed = r[f"{primary}_verdict"] == "pass"
        key = (str(r["task_id"]), str(r.get("checker_family")))
        decision = (decisions or {}).get(str(r["mutant_id"]), "not_sampled")
        if label == "should_pass_equiv":
            units["P2"].append((*key, not passed))
        elif label == "should_pass_alt_solution":
            gate["P2_alt"][decision] += 1
            if decision == "accept":
                units["P2"].append((*key, not passed))
        elif label == "should_fail_violation":
            units["P3"].append((*key, passed))
        elif label == "should_fail_extra_change":
            if not passed:
                units["P4"].append((*key, False))
                sensitivity_p4.append((*key, False))
                continue
            gate["P4_passed"][decision] += 1
            if decision == "reject":
                units["P4"].append((*key, True))
            if decision in ("reject", "unresolved"):
                sensitivity_p4.append((*key, True))
    return units, {
        "P2_alt_decisions": dict(gate["P2_alt"]),
        "P4_passed_decisions": dict(gate["P4_passed"]),
        "P4_unresolved_as_events": sensitivity_p4,
    }


def rate_table(units: Sequence[tuple[str, str, bool]], n_boot: int, seed: int) -> dict[str, Any]:
    by_family: dict[str, list[Unit]] = defaultdict(list)
    for task, family, event in units:
        by_family[family].append(Unit(task, event))
    families = {}
    for family, fam_units in sorted(by_family.items()):
        ci = _ci(fam_units, n_boot, seed)
        tasks = len({u.task_id for u in fam_units})
        inferential = tasks >= FAMILY_MIN_TASKS and len(fam_units) >= FAMILY_MIN_MUTANTS
        events = sum(u.event for u in fam_units)
        # D35: nothing here is inferential; the family floor still decides where
        # the descriptive K7 and K6b flags are computed.
        families[family] = {
            **(ci or {}),
            "above_family_floor": inferential,
            "events": events,
            "k7_unreliable": bool(inferential and ci and ci["low"] > K7_NULL),
            "k6b_no_detected_error": bool(tasks >= K6B_MIN_TASKS and events == 0),
            "zero_event_upper_bound": zero_event_upper_bound(tasks) if events == 0 else None,
        }
    pooled = _ci([Unit(t, e) for t, _, e in units], n_boot, seed)
    return {"pooled": pooled, "by_family": families}


def p5_escapes(rows: Sequence[Mapping[str, Any]], primary: str) -> dict[str, Any]:
    escape: dict[str, bool] = defaultdict(bool)
    for r in population(rows, primary):
        if r["label"] in ("should_pass_equiv", "should_fail_violation"):
            escape[str(r["task_id"])] |= r[f"{primary}_event"] in ("FN", "FP_R")
    k = sum(escape.values())
    return {
        **(_exact(k, len(escape)) or {"events": 0, "n": 0}),
        "tasks_with_escape": sorted(t for t, v in escape.items() if v),
    }


def k9(rows: Sequence[Mapping[str, Any]], primary: str) -> dict[str, Any]:
    nulls: dict[str, tuple[str | None, str]] = {}
    for r in rows:
        nulls.setdefault(
            str(r["target_id"]), (r.get(f"{primary}_null_verdict"), str(r.get("checker_family")))
        )
    failing = {t: fam for t, (v, fam) in nulls.items() if v != "pass"}
    share = len(failing) / len(nulls) if nulls else 0.0
    return {
        "targets": len(nulls),
        "null_not_pass": len(failing),
        "share": share,
        "fires": share > K9_MAX_NULL_NOT_PASS,
        "families_excluded": sorted(set(failing.values())),
    }


def k5(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    checked: Counter[str] = Counter()
    erased: Counter[str] = Counter()
    for r in rows:
        if r.get("admitted") and r.get("post_save_admitted") is not None:
            checked[r["operator"]] += 1
            erased[r["operator"]] += int(not r["post_save_admitted"])
    return {
        op: {
            "checked": n,
            "normalized": erased[op],
            "normalization_finding_only": erased[op] / n > K5_MAX_NORMALIZED,
        }
        for op, n in sorted(checked.items())
    }


def headline_exclusions(
    audit: Mapping[str, Any] | None, k2: Mapping[str, Any] | None
) -> dict[str, Any]:
    """Why each metric is out of the confirmatory headline, and which families K2 drops.

    The D34 exit (``D34_DEV_EXIT``) always removes P2-P5 (decision D35); a
    pending audit and the K3 rules add their reasons, which are reported. K4
    is reported and stops nothing.
    """
    leave: dict[str, list[str]] = {m: [D34_DEV_EXIT_REASON] for m in METRICS}
    if audit is None:
        for metric in METRICS:
            leave[metric].append("audit pending")
        audit_state = "pending"
    else:
        audit_state = "done"
        fires = audit.get("k3_fires", {})
        if audit.get("kappa_fires"):
            for metric in METRICS:
                leave[metric].append("K3: rater kappa below 0.6")
        if fires.get("should_pass_equiv"):
            leave["P2"].append("K3: should_pass_equiv label error")
            leave["P5"].append("K3: should_pass_equiv label error")
        if fires.get("should_fail_violation"):
            leave["P3"].append("K3: should_fail_violation label error")
            leave["P5"].append("K3: should_fail_violation label error")
    if k2 is None:
        fidelity = {"label": K2_UNVERIFIED, "families_dropped": []}
    else:
        dropped = sorted(
            {
                str(row["checker_family"])
                for row in k2.get("disagreements", [])
                if row.get("explanation") not in K2_EXPLANATIONS
            }
        )
        fidelity = {
            "label": "VM fidelity checked (K2)",
            "executor_commit": k2.get("executor_commit"),
            "pairs": k2.get("pairs"),
            "families_dropped": dropped,
        }
    return {
        "audit": audit_state,
        "d34_dev_exit": dict(D34_DEV_EXIT, metrics=list(METRICS)),
        "confirmatory_metrics": [],
        "metrics_leaving_headline": {m: v for m, v in leave.items() if v},
        "K4": {"fires": bool(audit and audit.get("k4_fires")), "role": K4_ROLE},
        "k2": fidelity,
    }


def is_candidate(row: Mapping[str, Any], primary: str) -> bool:
    """A checker candidate event: a should-pass mutant failed or a should-fail one passed."""
    passed = row[f"{primary}_verdict"] == "pass"
    label = row["label"]
    return (label in SHOULD_PASS_LABELS and not passed) or (label in SHOULD_FAIL_LABELS and passed)


def audit_reading(kind: str, decision: str) -> str:
    """What a candidate's audit decision says (decision D35)."""
    if decision == "not_sampled":
        return "not_audited"
    if decision == "unresolved":
        return "unresolved"
    return "confirmed" if decision == CONFIRMING[kind] else "label_contradicted"


def _share(units: Sequence[tuple[str, bool]], n_boot: int, seed: int) -> dict[str, Any] | None:
    """Task-equal share with the registered task-cluster bootstrap, and its event count."""
    ci = _ci([Unit(task, event) for task, event in units], n_boot, seed)
    if ci is None:
        return None
    return {**ci, "events": sum(event for _, event in units)}


def _shares(
    rows: Sequence[Mapping[str, Any]],
    event: Any,
    n_boot: int,
    seed: int,
) -> dict[str, Any]:
    """Pooled, per-label, per-family and per-operator task-equal shares of ``event(row)``."""
    by: dict[str, dict[str, list[tuple[str, bool]]]] = {
        "by_label": defaultdict(list),
        "by_family": defaultdict(list),
        "by_operator": defaultdict(list),
    }
    pooled: list[tuple[str, bool]] = []
    for r in rows:
        unit = (str(r["task_id"]), bool(event(r)))
        pooled.append(unit)
        by["by_label"][str(r["label"])].append(unit)
        by["by_family"][str(r.get("checker_family"))].append(unit)
        by["by_operator"][str(r.get("operator"))].append(unit)
    return {
        "pooled": _share(pooled, n_boot, seed),
        **{
            name: {key: _share(units, n_boot, seed) for key, units in sorted(groups.items())}
            for name, groups in by.items()
        },
    }


def checker_candidates(
    rows: Sequence[Mapping[str, Any]],
    decisions: Mapping[str, str] | None,
    primary: str,
    n_boot: int,
    seed: int,
    *,
    gold_defect_tasks: Sequence[str] = (),
) -> dict[str, Any]:
    """The D35 descriptive output: the checker's false-negative and false-positive candidates.

    Population: ``population`` (evaluable under ``primary``, outside
    probe-touched cells). Each candidate is listed with its audit decision
    (``decisions``; ``not_sampled`` when the audit holds none) and its reading
    (``audit_reading``), and whether its task is a gold-defect task. Shares are
    task-equal with the task-cluster percentile bootstrap: the candidate share
    of the kind's mutants, and, when the audit decided every candidate of the
    kind (``audit_census``), the audit-confirmed share (unresolved candidates
    are not confirmed). Candidate events in probe-touched cells are counted
    per kind and family, unaudited.
    """
    pop = population(rows, primary)
    defects = set(gold_defect_tasks)
    out: dict[str, Any] = {
        "role": DESCRIPTIVE,
        "population": "evaluable, outside probe-touched cells (as P2-P5)",
        "definitions": {
            "false_negative": (
                "an evaluable should_pass_equiv or should_pass_alt_solution mutant outside "
                "probe-touched cells that the checker does not pass; confirmed when the audit "
                "decides accept"
            ),
            "false_positive": (
                "an evaluable should_fail_violation or should_fail_extra_change mutant outside "
                "probe-touched cells that the checker passes; confirmed when the audit decides "
                "reject"
            ),
        },
    }
    for kind, labels in CANDIDATE_KINDS.items():
        kind_rows = [r for r in pop if r["label"] in labels]
        events = []
        for r in sorted(kind_rows, key=lambda r: str(r["mutant_id"])):
            if not is_candidate(r, primary):
                continue
            decision = (decisions or {}).get(str(r["mutant_id"]), "not_sampled")
            events.append(
                {
                    "mutant_id": str(r["mutant_id"]),
                    "task_id": str(r["task_id"]),
                    "checker_family": str(r.get("checker_family")),
                    "operator": str(r.get("operator")),
                    "label": str(r["label"]),
                    "verdict": str(r[f"{primary}_verdict"]),
                    "audit_decision": decision,
                    "audit_reading": audit_reading(kind, decision),
                    "gold_defect_task": str(r["task_id"]) in defects,
                }
            )
        confirmed = frozenset(e["mutant_id"] for e in events if e["audit_reading"] == "confirmed")
        census = decisions is not None and all(e["audit_decision"] != "not_sampled" for e in events)
        audit_counts: dict[str, dict[str, dict[str, int]]] = {
            "by_family": {},
            "by_operator": {},
        }
        for e in events:
            for name, key in (("by_family", "checker_family"), ("by_operator", "operator")):
                cell = audit_counts[name].setdefault(e[key], {})
                cell[e["audit_reading"]] = cell.get(e["audit_reading"], 0) + 1
        out[kind] = {
            "labels": list(labels),
            "mutants": len(kind_rows),
            "tasks": len({str(r["task_id"]) for r in kind_rows}),
            "events": events,
            "counts": {
                "events": len(events),
                "by_label": dict(Counter(e["label"] for e in events)),
                "by_audit_reading": dict(Counter(e["audit_reading"] for e in events)),
                "gold_defect_tasks": sum(e["gold_defect_task"] for e in events),
                "audit": audit_counts,
            },
            "candidate_share": _shares(
                kind_rows, lambda r: is_candidate(r, primary), n_boot, seed
            ),
            "audit_census": census,
            "confirmed_share": (
                _shares(
                    kind_rows,
                    lambda r, ids=confirmed: str(r["mutant_id"]) in ids,
                    n_boot,
                    seed,
                )
                if census
                else None
            ),
        }
    touched: dict[str, Counter[str]] = {kind: Counter() for kind in CANDIDATE_KINDS}
    for r in rows:
        if r.get(f"{primary}_status") != "evaluable" or not r.get("probe_touched"):
            continue
        for kind, labels in CANDIDATE_KINDS.items():
            if r["label"] in labels and is_candidate(r, primary):
                touched[kind][str(r.get("checker_family"))] += 1
    out["probe_touched_events"] = {
        "role": "exploratory, not audited (probe-touched cells, section 12)",
        **{kind: dict(sorted(c.items())) for kind, c in touched.items()},
    }
    return out


def mutation_metrics(
    rows: Sequence[Mapping[str, Any]],
    decisions: Mapping[str, str] | None,
    primary: str,
    n_boot: int,
    seed: int,
) -> dict[str, Any]:
    """P2-P5 and the audit gate counts on one set of outcome rows."""
    units, gate = metric_units(rows, decisions, primary)
    tables = {metric: rate_table(units[metric], n_boot, seed) for metric in ("P2", "P3", "P4")}
    tables["P4"]["unresolved_as_events"] = _ci(
        [Unit(t, e) for t, _, e in gate.pop("P4_unresolved_as_events")], n_boot, seed
    )
    return {
        "audit_gate": gate,
        "P2": tables["P2"],
        "P3": tables["P3"],
        "P4": tables["P4"],
        "P5": p5_escapes(rows, primary),
    }


def p1_over_controls(
    runs: Sequence[tuple[str, Mapping[str, Any]]],
    decisions: Mapping[str, str] | None,
    primary: str,
    splits: Mapping[str, Sequence[str]] | None = None,
) -> dict[str, Any]:
    """P1 over the control runs ``(split, summary)``: the confirm and the reserve run.

    Counted golds and flips are summed over the runs (each run counts only its
    own golds, ``report.aggregate``); a task in two runs, or in a run of another
    split than ``splits`` gives it, is refused. A flip is audit-confirmed when
    its ``<task>__p1_flip`` decision is accept.
    """
    from harness.q2_mutation.report import p1_flip_tasks

    seen: dict[str, str] = {}
    n = 0
    flips: list[str] = []
    per_run: dict[str, Any] = {}
    not_exposed: list[str] = []
    not_counted: list[str] = []
    for split, summary in runs:
        tasks = summary["tasks"]
        for task in tasks:
            if task in seen:
                raise ValueError(f"task {task} is in the {seen[task]} and the {split} control run")
            if splits is not None and task not in set(splits.get(split, ())):
                raise ValueError(f"task {task} of the {split} control run is not a {split} task")
            seen[task] = split
        agg = summary["aggregate"][primary]
        run_flips = p1_flip_tasks(tasks, primary)
        n += int(agg["gold_fixed_point_n"])
        flips += run_flips
        not_exposed += list(agg.get("gold_fixed_point_not_exposed", []))
        not_counted += list(agg.get("gold_fixed_point_not_counted", []))
        per_run[split] = {"n": int(agg["gold_fixed_point_n"]), "flips": run_flips}
    flips = sorted(flips)
    confirmed = [t for t in flips if (decisions or {}).get(f"{t}__p1_flip") == "accept"]
    return {
        "role": "pre-specified replication of the scoping round trip (no confirmatory part)",
        "runs": per_run,
        "raw_flips": _exact(len(flips), n),
        "audit_confirmed_flips": _exact(len(confirmed), n),
        "flip_tasks": flips,
        "confirmed_tasks": confirmed,
        "not_exposed": sorted(not_exposed),
        "not_counted": sorted(not_counted),
    }


def headline(
    outcomes: Sequence[Mapping[str, Any]],
    *,
    controls: Mapping[str, Any] | None = None,
    reserve_controls: Mapping[str, Any] | None = None,
    audit: Mapping[str, Any] | None = None,
    decisions: Mapping[str, str] | None = None,
    k2: Mapping[str, Any] | None = None,
    splits: Mapping[str, Sequence[str]] | None = None,
    primary: str = "lock",
    n_boot: int = 10_000,
    seed: int = 42,
) -> dict[str, Any]:
    exclusions = headline_exclusions(audit, k2)
    dropped = set(exclusions["k2"]["families_dropped"])
    kept = [r for r in outcomes if str(r.get("checker_family")) not in dropped]
    metrics = mutation_metrics(kept, decisions, primary, n_boot, seed)
    p5 = metrics["P5"]
    gold_defects = (audit or {}).get("gold_defects") or {}
    defect_tasks = sorted(str(t) for t in gold_defects.get("tasks", []))
    out: dict[str, Any] = {
        "primary_dep_set": primary,
        "protocol": (
            "descriptive (decision D35): P1 is a replication only and P2-P5 are out of the "
            "confirmatory headline under D34 (i); no confirmatory claim is made"
        ),
        "population": (
            "evaluable, outside probe-touched cells (probe cells and probe-informed operators)"
            + (f"; K2-dropped families left out: {sorted(dropped)}" if dropped else "")
        ),
        "checker_candidates": checker_candidates(
            kept, decisions, primary, n_boot, seed, gold_defect_tasks=defect_tasks
        ),
        "metrics_role": "exploratory (D34 (i), D35): reported with the same tables",
        **metrics,
        "K5": k5(outcomes),
        "K9": k9(outcomes, primary),
        "exclusions": exclusions,
        "K4": exclusions["K4"],
        "descriptive_outputs": {
            "P1": "pre-specified replication of the scoping round trip (section 4)",
            "checker_candidates": "this result's checker_candidates (sections 4 and 12)",
            "S1-S7": "report.json of the runs and audit-summary.json, as registered (section 5)",
        },
    }
    if dropped:
        out["k2_exploratory"] = {
            "families": sorted(dropped),
            "including_dropped_families": mutation_metrics(
                outcomes, decisions, primary, n_boot, seed
            ),
            "dropped_families_only": mutation_metrics(
                [r for r in outcomes if str(r.get("checker_family")) in dropped],
                decisions,
                primary,
                n_boot,
                seed,
            ),
            "dropped_families_candidates": checker_candidates(
                [r for r in outcomes if str(r.get("checker_family")) in dropped],
                decisions,
                primary,
                n_boot,
                seed,
                gold_defect_tasks=defect_tasks,
            ),
        }
    without = [
        r
        for r in kept
        if not (r.get("label") == "should_pass_equiv" and str(r["task_id"]) in set(defect_tasks))
    ]
    out["gold_defects"] = {
        "rule": (
            "tasks whose gold sham the audit decided reject; their equivalence items left the "
            "equivalence K3 group (decision D34); P2 stays defined relative to the gold"
        ),
        "tasks": defect_tasks,
        "P2_without_their_equivalence_mutants": (
            rate_table(metric_units(without, decisions, primary)[0]["P2"], n_boot, seed)
            if defect_tasks
            else None
        ),
    }
    p1 = None
    if controls is not None:
        runs = [("confirm", controls)]
        if reserve_controls is not None:
            runs.append(("reserve", reserve_controls))
        p1 = p1_over_controls(runs, decisions, primary, splits)
        # K1 is a harness check of the confirm control run only.
        out["K1"] = controls["aggregate"][primary]["k1_gold_pass_and_do_nothing_fail"]
    out["P1"] = p1
    confirmed_flips = len(p1["confirmed_tasks"]) if p1 else None
    # K6 was a claim about P5. P5 left the confirmatory headline under D34 (i),
    # so D35 retires the claim: it is reported as blocked, with every reason.
    blocked = [K6_RETIRED, *exclusions["metrics_leaving_headline"].get("P5", [])]
    out["K6"] = {
        "role": "retired (D35); reported as blocked",
        "p5_tasks": p5["n"],
        "p5_escapes": p5["events"],
        "confirmed_p1_flips": confirmed_flips,
        "p1_runs": sorted(p1["runs"]) if p1 else [],
        "blocked_by": blocked,
        "adequacy_claim": False,
    }
    for name, flag in (("K6b", "k6b_no_detected_error"), ("K7", "k7_unreliable")):
        out[name] = {
            "role": DESCRIPTIVE,
            "families": {
                metric: sorted(
                    family
                    for family, row in out[metric]["by_family"].items()
                    if row.get(flag)
                )
                for metric in ("P2", "P3", "P4")
            },
        }
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--outcomes", type=Path, required=True)
    parser.add_argument("--controls-summary", type=Path, help="confirm control run summary")
    parser.add_argument(
        "--reserve-controls-summary",
        type=Path,
        help="reserve control run summary (P1 and K6 count its golds; K1 does not)",
    )
    parser.add_argument(
        "--splits",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "program/evidence/q2-mutation/splits.json",
    )
    parser.add_argument("--audit-summary", type=Path)
    parser.add_argument("--decisions", type=Path)
    parser.add_argument("--k2-report", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--n-boot", type=int, default=10_000)
    args = parser.parse_args(argv)

    def load(path: Path | None) -> Any:
        return json.loads(path.read_text(encoding="utf-8")) if path else None

    outcomes = [
        json.loads(line)
        for line in args.outcomes.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    decisions = None
    if args.decisions:
        decisions = {
            row["key"]: row["decision"]
            for row in (
                json.loads(line)
                for line in args.decisions.read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
        }
    result = headline(
        outcomes,
        controls=load(args.controls_summary),
        reserve_controls=load(args.reserve_controls_summary),
        splits=load(args.splits) if args.splits and args.splits.is_file() else None,
        audit=load(args.audit_summary),
        decisions=decisions,
        k2=load(args.k2_report),
        n_boot=args.n_boot,
    )
    args.out.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result["exclusions"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
