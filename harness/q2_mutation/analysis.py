"""Headline analysis of q2-evaluator-mutation-v1 (preregistration sections 4-10).

Everything the registration computes after the runs, fixed in code before the
freeze so no analysis choice is made after a confirmatory verdict is read:

* P1 (replication only): saved-gold flips among golds exposed to the save
  stage (``report.p1_counted``), raw and audit-confirmed, with exact
  Clopper-Pearson intervals;
* P2: evaluable ``should_pass_equiv`` mutants plus the
  ``should_pass_alt_solution`` mutants the audit accepted; event: not pass;
* P3: evaluable ``should_fail_violation`` mutants; event: pass;
* P4: evaluable ``should_fail_extra_change`` mutants; event: the checker passes
  it and the audit rejects it. A passed extra-change mutant the audit does not
  reject (accepted, unresolved or not sampled) leaves P4's numerator and
  denominator; a failed one stays in the denominator. The count with
  unresolved items as events is a sensitivity estimate;
* P5: tasks with an evaluable equivalence or violation mutant, with at least
  one FN or FP_R event (exact interval);
* pooled rates and family rates are task-equal means with the task-cluster
  percentile bootstrap (10,000 resamples, seed 42); a family rate is
  inferential only with at least 8 tasks and 20 mutants (the family floor);
* K2: a checker family with an unexplained in-VM/offline disagreement leaves
  the headline; without a K2 report the headline is labelled
  ``offline harness, VM fidelity unverified``;
* K3 (single rule): when K3 fires for ``should_pass_equiv``, P2 and P5 leave
  the headline and are reported as exploratory; for
  ``should_fail_violation``, P3 and P5; when kappa is below 0.6, P2-P5. K4
  stops the experiment;
* K5, K6, K6b, K7 (family floor decides whether K7 applies) and K9.

Every population is the one ``campaign.build_report`` marks: evaluable under
the primary venv and outside probe-touched cells (probe cells and the
probe-informed operators).
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from harness.q2_mutation.stats import (
    Unit,
    clopper_pearson,
    cluster_bootstrap_ci,
    zero_event_upper_bound,
)

FAMILY_MIN_TASKS = 8
FAMILY_MIN_MUTANTS = 20
K6_MIN_TASKS = 59
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
        families[family] = {
            **(ci or {}),
            "inferential": inferential,
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
    """Which metrics leave the headline (K3, K4) and which families (K2)."""
    leave: dict[str, list[str]] = {m: [] for m in METRICS}
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
        "k4_stop": bool(audit and audit.get("k4_fires")),
        "metrics_leaving_headline": {m: v for m, v in leave.items() if v},
        "k2": fidelity,
    }


def headline(
    outcomes: Sequence[Mapping[str, Any]],
    *,
    controls: Mapping[str, Any] | None = None,
    audit: Mapping[str, Any] | None = None,
    decisions: Mapping[str, str] | None = None,
    k2: Mapping[str, Any] | None = None,
    primary: str = "lock",
    n_boot: int = 10_000,
    seed: int = 42,
) -> dict[str, Any]:
    units, gate = metric_units(outcomes, decisions, primary)
    tables = {metric: rate_table(units[metric], n_boot, seed) for metric in ("P2", "P3", "P4")}
    tables["P4"]["unresolved_as_events"] = _ci(
        [Unit(t, e) for t, _, e in gate.pop("P4_unresolved_as_events")], n_boot, seed
    )
    p5 = p5_escapes(outcomes, primary)
    out: dict[str, Any] = {
        "primary_dep_set": primary,
        "population": (
            "evaluable, outside probe-touched cells (probe cells and probe-informed operators)"
        ),
        "audit_gate": gate,
        "P2": tables["P2"],
        "P3": tables["P3"],
        "P4": tables["P4"],
        "P5": p5,
        "K5": k5(outcomes),
        "K9": k9(outcomes, primary),
        "exclusions": headline_exclusions(audit, k2),
    }
    p1 = None
    if controls is not None:
        from harness.q2_mutation.report import p1_flip_tasks

        tasks = controls["tasks"]
        agg = controls["aggregate"][primary]
        flips = p1_flip_tasks(tasks, primary)
        confirmed = [t for t in flips if (decisions or {}).get(f"{t}__p1_flip") == "accept"]
        n = int(agg["gold_fixed_point_n"])
        p1 = {
            "role": "pre-specified replication of the scoping round trip (no confirmatory part)",
            "raw_flips": _exact(len(flips), n),
            "audit_confirmed_flips": _exact(len(confirmed), n),
            "flip_tasks": flips,
            "confirmed_tasks": confirmed,
            "not_exposed": agg.get("gold_fixed_point_not_exposed", []),
            "not_counted": agg.get("gold_fixed_point_not_counted", []),
        }
        out["K1"] = agg["k1_gold_pass_and_do_nothing_fail"]
    out["P1"] = p1
    confirmed_flips = len(p1["confirmed_tasks"]) if p1 else None
    out["K6"] = {
        "p5_tasks": p5["n"],
        "p5_escapes": p5["events"],
        "confirmed_p1_flips": confirmed_flips,
        "adequacy_claim": bool(
            p5["n"] >= K6_MIN_TASKS
            and p5["events"] == 0
            and confirmed_flips is not None
            and confirmed_flips <= 1
        ),
    }
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--outcomes", type=Path, required=True)
    parser.add_argument("--controls-summary", type=Path)
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
