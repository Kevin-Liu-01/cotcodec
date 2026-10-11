"""Registered analysis of r04-checker-nuisance-invariance-v1 (standard library only).

Every comparison is paired with the control cell (``B0.ctrl_s.L0``, the checker-mutation
study's registered save): for an item valid in both cells (saved without failure, scored
deterministically, no infrastructure failure), the item is discordant when its verdict
(pass, fail or error) under the cell differs from its verdict under the control. A
discordance counts only when it is confirmed: both confirmation rounds re-save and re-score
the item under the control and under the cell and reproduce both verdicts. A discordance a
round does not reproduce, or for which a round's row is invalid, is unstable: harness
instability, counted and listed, never a finding. A discordance whose round rows are missing
stays pending, so its cell reads PENDING, never INVARIANT.

Per cell, on the primary populations (the gold items of the registered splits, and S1a's
pass states with the task as the unit):

* ``k_gold``: confirmed discordant golds; ``t_s1a``: S1a tasks with at least one confirmed
  discordant pass state;
* reading ``DRIFT`` if ``k_gold >= 3`` or ``t_s1a >= 3``; ``INVARIANT`` if both are 0;
  ``MINOR`` otherwise; ``NOT_EVALUABLE`` if the cell (or its build, or its locale) was not
  retained or not scored; ``PENDING`` if a discordance waits for its confirmation rounds.

A cell is retained when its save stage succeeded on at least 90% of its gold items and of
its S1a items (the save stage's outcome only: a scorer failure is not a save failure); a
build is retained when its ``ctrl_s`` cell is, and a locale when its data compiled and its
cell is retained. An arm (route, build, locale) reads ``DRIFT`` if any of its retained
primary cells does, ``INVARIANT`` if all do, ``NOT_EVALUABLE`` if none is retained (or, for
the build arm, fewer than two builds), and ``MINOR`` otherwise.

Validity, before any reading: the control cell is retained; V1, the control reproduces the
frozen control runs' saved gold verdicts (at most one difference, at least one gold
compared); V2, the replicate cell is scored, retained and has no confirmed discordance with
the control in any population. A failed gate makes every reading, per cell and per arm,
``INVALID``; a pending gate marks every reading pending.

Fail-closed inputs: every registered cell and the unsaved items are scored, or named with
the reason they were not (``cell_errors``, which may name only unscored cells); the rounds
are exactly two or none (none only before the rounds, when every discordance is pending);
the reference is the frozen control summaries of the analysed splits, checked by SHA-256;
the splits are dev alone or exactly confirm and reserve. ``--run`` reads all of these from a
run's own plan and directories, so the registered computation leaves no choice.

The pinned checker is primary; the corrected comparator (``zinv``) gets the same tables and
readings as a secondary checker. Every reading carries the parent registration's K2 label
("offline harness, VM fidelity unverified") until a K2 report is given; a K2 report that
drops a checker family takes that family's items out of the readings, which are then also
reported with them (``k2_exploratory``). Descriptive outputs: the P1 replication (control
against the unsaved gold), S1a's fixed point (control against the captured state), every
cell's flip set against the unsaved item and its overlap with the control's, discordances
by direction and checker family with the control's and the cell's office digests, save
failures and scoring failures per cell, intervals, save timing and dialogs, and a harness
noise flag per cell (changes no reading).
"""

from __future__ import annotations

import argparse
import functools
import hashlib
import json
import re
import statistics
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from harness.q2_mutation.analysis import K2_EXPLANATIONS, K2_UNVERIFIED
from harness.q2_mutation.stats import Unit, clopper_pearson, cluster_bootstrap_ci, exact_upper_bound
from harness.r04_nuisance import levels

SCHEMA = "r04-analysis-v2"
DRIFT_MIN = 3
RETENTION_MIN = 0.90
V1_MAX_DIFFERENCES = 1
CONFIRM_ROUNDS = 2
# A cell with at least this many unstable discordances among its golds and S1a pass states
# is flagged "harness_noise" (descriptive; it changes no reading), and so is a replicate
# with any unstable discordance.
NOISE_FLAG_MIN = 3
PRIMARY_S1A = "s1a_pass"
S1A_POPULATIONS = ("s1a_pass", "s1a_fail", "s1a_mixed")
SAVE_FAILED = frozenset({"save_failed", "infra_error", "no_lo_row"})
SCORING_FAILED = frozenset({"harness_error", "infra_failed", "nondeterministic"})
CHECKERS = ("pinned", "zinv")
K2_VERIFIED = "VM fidelity checked (K2)"
BLIND_WARNING = (
    "This output names checker verdicts per gold task and per S1a state, as the checker-"
    "mutation study's released analysis does. Kevin's adjudication of its pool and his human "
    "spot check are pending: to stay blind, answer them before reading this file "
    "(program/evidence/2026-10-08/q2-mutation-confirm/results/README.md, 'Pending for "
    "Kevin'). R04 reads no audit, decision, adjudication or rater file, and its reserve-split "
    "zinv verdicts are not used to change zinv before R03 (b)."
)
# R04 never reads an audit summary, a decision, the adjudication pool, an answer, a spot
# check or a rater file (registration section 2.1): every input path is checked.
FORBIDDEN_INPUT = re.compile(
    r"adjudicat|audit-summary|decisions|spot-check|pool|answers|rater|calls\.jsonl|sample\.jsonl$",
    re.IGNORECASE,
)


class AnalysisError(ValueError):
    """The inputs are not the registered computation's (missing, extra or inconsistent)."""


def checker_family(funcs: Iterable[str]) -> str:
    """``harness.q2_mutation.campaign.checker_family`` (a test keeps the two equal)."""
    return "+".join(sorted(set(funcs)))


def valid(row: Mapping[str, Any] | None, checker: str = "pinned") -> bool:
    if row is None or row.get("status") != "scored":
        return False
    result = row.get(checker) or {}
    return not result.get("nondeterministic") and not result.get("infra_failed")


def verdict(row: Mapping[str, Any], checker: str = "pinned") -> str:
    return str((row.get(checker) or {}).get("verdict"))


def index_rows(rows: Iterable[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    out: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if row["item_id"] in out:
            raise AnalysisError(f"item {row['item_id']} scored twice in cell {row.get('cell')}")
        out[row["item_id"]] = row
    return out


def saved(row: Mapping[str, Any] | None) -> bool:
    """The save stage's outcome for an (item, cell); a scorer failure is not a save failure."""
    if row is None or row.get("status") in SAVE_FAILED:
        return False
    if "save_status" in row:
        return row["save_status"] == "saved"
    return row.get("status") != "harness_error"  # rows written before save_status existed


def discordances(
    items: Sequence[Mapping[str, Any]],
    control: Mapping[str, Mapping[str, Any]],
    cell: Mapping[str, Mapping[str, Any]],
    checker: str,
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """(discordant pairs, valid pair ids, excluded ids) for one cell against the control."""
    pairs: list[dict[str, Any]] = []
    valid_ids: list[str] = []
    excluded: list[str] = []
    for item in items:
        iid = item["item_id"]
        a, b = control.get(iid), cell.get(iid)
        if not (valid(a, checker) and valid(b, checker)):
            excluded.append(iid)
            continue
        valid_ids.append(iid)
        va, vb = verdict(a, checker), verdict(b, checker)  # type: ignore[arg-type]
        if va != vb:
            pairs.append(
                {
                    "item_id": iid,
                    "task_id": item["task_id"],
                    "population": item["population"],
                    "control": va,
                    "cell": vb,
                    "direction": f"{va}->{vb}",
                    "checker_funcs": (b or {}).get("checker_funcs"),
                    # Session-specific: LibreOffice saves are not byte-deterministic.
                    "control_office_sha256": (a or {}).get("office_sha256"),
                    "cell_office_sha256": (b or {}).get("office_sha256"),
                }
            )
    return pairs, valid_ids, excluded


def confirm_status(
    pair: Mapping[str, Any],
    cell_id: str,
    rounds: Sequence[Mapping[str, Mapping[str, Mapping[str, Any]]]],
    checker: str,
) -> str:
    """confirmed; unstable (a round disagreed, or its row is invalid); pending (no rounds yet,
    or a round has no row for the item under the control or the cell)."""
    if not rounds:
        return "pending"
    iid = pair["item_id"]
    for rnd in rounds:
        a = (rnd.get(levels.CONTROL_CELL) or {}).get(iid)
        b = (rnd.get(cell_id) or {}).get(iid)
        if a is None or b is None:
            return "pending"
        if not (valid(a, checker) and valid(b, checker)):
            return "unstable"
        if verdict(a, checker) != pair["control"] or verdict(b, checker) != pair["cell"]:
            return "unstable"
    return "confirmed"


def retention(
    items: Sequence[Mapping[str, Any]], rows: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for group, pops in (("gold", ("gold",)), ("s1a", S1A_POPULATIONS)):
        ids = [i["item_id"] for i in items if i["population"] in pops]
        if not ids:
            out[group] = {"items": 0, "saved": 0, "share": None}
            continue
        n_saved = sum(saved(rows.get(iid)) for iid in ids)
        out[group] = {"items": len(ids), "saved": n_saved, "share": n_saved / len(ids)}
    shares = [g["share"] for g in out.values() if g["share"] is not None]
    out["retained"] = bool(shares) and all(s >= RETENTION_MIN for s in shares)
    return out


def failures(
    items: Sequence[Mapping[str, Any]], rows: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    """Every save failure with its reason, and every scoring failure, in one cell."""
    save_failures, scoring = [], []
    for item in items:
        row = rows.get(item["item_id"])
        if row is None:
            save_failures.append({"item_id": item["item_id"], "status": "no_score_row"})
            continue
        if not saved(row):
            save_failures.append(
                {
                    "item_id": item["item_id"],
                    "status": row.get("save_status") or row.get("status"),
                    "reason": row.get("reason")
                    or ((row.get("save") or {}).get("infra_error"))
                    or "; ".join((row.get("save") or {}).get("failures") or []),
                }
            )
        elif row.get("status") in SCORING_FAILED:
            scoring.append({"item_id": item["item_id"], "status": row.get("status")})
    return {
        "save_failures": save_failures,
        "scoring_failures": scoring,
        "scoring_failures_by_status": dict(Counter(f["status"] for f in scoring)),
    }


@functools.lru_cache(maxsize=4096)
def _exact_bounds(k: int, n: int) -> tuple[float, float, float]:
    low, high = clopper_pearson(k, n)
    return low, high, exact_upper_bound(k, n)


def interval_block(k: int, n: int) -> dict[str, Any]:
    if n == 0:
        return {"k": k, "n": 0}
    low, high, upper = _exact_bounds(k, n)
    return {
        "k": k,
        "n": n,
        "share": k / n,
        "cp95": [low, high],
        "upper95_one_sided": upper,
    }


def population_table(
    items: Sequence[Mapping[str, Any]],
    pairs: Sequence[Mapping[str, Any]],
    valid_ids: Sequence[str],
    status_of: Mapping[str, str],
    population: str,
    n_boot: int = 10_000,
) -> dict[str, Any]:
    pop_items = {i["item_id"]: i for i in items if i["population"] == population}
    valid_pop = [iid for iid in valid_ids if iid in pop_items]
    disc = [p for p in pairs if p["population"] == population]
    confirmed = [p for p in disc if status_of[p["item_id"]] == "confirmed"]
    tasks_valid = sorted({pop_items[iid]["task_id"] for iid in valid_pop})
    tasks_conf = sorted({p["task_id"] for p in confirmed})
    table: dict[str, Any] = {
        "items": len(pop_items),
        "valid_pairs": len(valid_pop),
        "tasks_valid": len(tasks_valid),
        "discordant": len(disc),
        "confirmed": len(confirmed),
        "unstable": sum(status_of[p["item_id"]] == "unstable" for p in disc),
        "pending": sum(status_of[p["item_id"]] == "pending" for p in disc),
        "confirmed_tasks": tasks_conf,
        "by_direction": dict(Counter(p["direction"] for p in confirmed)),
        "by_family": dict(Counter(checker_family(p.get("checker_funcs") or []) for p in confirmed)),
        "item_level": interval_block(len(confirmed), len(valid_pop)),
        "task_level": interval_block(len(tasks_conf), len(tasks_valid)),
        "discordances": [{**p, "status": status_of[p["item_id"]]} for p in disc],
    }
    if population != "gold" and valid_pop:
        conf_ids = {p["item_id"] for p in confirmed}
        units = [Unit(pop_items[iid]["task_id"], iid in conf_ids) for iid in valid_pop]
        ci = cluster_bootstrap_ci(units, n_boot=n_boot)
        table["state_level_task_equal"] = {
            "estimate": ci.estimate,
            "low": ci.low,
            "high": ci.high,
            "method": ci.method,
        }
    return table


def cell_reading(gold: Mapping[str, Any], s1a: Mapping[str, Any], retained: bool) -> str:
    if not retained:
        return "NOT_EVALUABLE"
    if gold["pending"] or s1a["pending"]:
        return "PENDING"
    k, t = gold["confirmed"], len(s1a["confirmed_tasks"])
    if k >= DRIFT_MIN or t >= DRIFT_MIN:
        return "DRIFT"
    if k == 0 and t == 0:
        return "INVARIANT"
    return "MINOR"


def arm_reading(readings: Sequence[str], arm: str, retained_builds: int) -> str:
    if "INVALID" in readings:
        return "INVALID"
    evaluable = [r for r in readings if r != "NOT_EVALUABLE"]
    if arm == "build" and retained_builds < 2:
        return "NOT_EVALUABLE"
    if not evaluable:
        return "NOT_EVALUABLE"
    if "DRIFT" in evaluable:
        return "DRIFT"
    if "PENDING" in evaluable:
        return "PENDING"
    if all(r == "INVARIANT" for r in evaluable):
        return "INVARIANT"
    return "MINOR"


def gated(reading: str, gate: str) -> str:
    """A reading after the validity gates: INVALID if a gate failed, marked if one is pending."""
    if gate == "invalid":
        return "INVALID"
    if gate == "pending":
        return f"{reading} (validity gate pending)"
    return reading


def flips_against_raw(
    items: Sequence[Mapping[str, Any]],
    raw: Mapping[str, Mapping[str, Any]],
    cell: Mapping[str, Mapping[str, Any]],
    checker: str,
) -> list[str]:
    out = []
    for item in items:
        a, b = raw.get(item["item_id"]), cell.get(item["item_id"])
        if valid(a, checker) and valid(b, checker) and verdict(a, checker) != verdict(b, checker):
            out.append(item["item_id"])  # type: ignore[arg-type]
    return sorted(out)


def jaccard(a: Iterable[str], b: Iterable[str]) -> float | None:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return None
    return len(sa & sb) / len(sa | sb)


def timing(rows: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    seconds = []
    dialogs = 0
    changed = 0
    saves = 0
    adapted = 0
    for row in rows.values():
        adapted += bool((row.get("save") or {}).get("activations_adapted"))
        for save in (row.get("save") or {}).get("saves") or []:
            saves += 1
            if save.get("seconds_to_write") is not None:
                seconds.append(float(save["seconds_to_write"]))
            dialogs += bool(save.get("dialogs"))
            changed += bool(save.get("changed"))
    if not seconds:
        return {"saves": saves, "items_with_adapted_activation": adapted}
    seconds.sort()
    return {
        "saves": saves,
        "items_with_adapted_activation": adapted,
        "written": len(seconds),
        "median_s": statistics.median(seconds),
        "p90_s": seconds[min(len(seconds) - 1, int(0.9 * len(seconds)))],
        "max_s": seconds[-1],
        "slower_than_0_5_s": sum(s > 0.5 for s in seconds),
        "with_dialog": dialogs,
        "bytes_changed": changed,
    }


def v1_check(
    items: Sequence[Mapping[str, Any]],
    control: Mapping[str, Mapping[str, Any]],
    reference: Mapping[str, str],
) -> dict[str, Any]:
    """The control's gold verdicts against the frozen control runs' saved-gold verdicts. A
    gold not valid in the control (or absent from the reference) is not compared and is
    listed; retention bounds how many there can be."""
    diffs, compared, missing = [], 0, []
    for item in items:
        if item["population"] != "gold":
            continue
        ref = reference.get(item["task_id"])
        row = control.get(item["item_id"])
        if ref is None or not valid(row):
            missing.append(item["task_id"])
            continue
        compared += 1
        if verdict(row) != ref:  # type: ignore[arg-type]
            diffs.append({"task_id": item["task_id"], "frozen": ref, "control": verdict(row)})  # type: ignore[arg-type]
    ok = len(diffs) <= V1_MAX_DIFFERENCES and compared > 0
    return {
        "status": "pass" if ok else "fail",
        "compared": compared,
        "differences": diffs,
        "not_compared": sorted(missing),
    }


def k2_fidelity(k2: Mapping[str, Any] | None) -> dict[str, Any]:
    """The parent's K2 label and the checker families a K2 report drops (an unexplained
    in-VM difference), as ``harness.q2_mutation.analysis.headline_exclusions`` reads it."""
    if k2 is None:
        return {"label": K2_UNVERIFIED, "families_dropped": []}
    dropped = sorted(
        {
            str(row["checker_family"])
            for row in k2.get("disagreements", [])
            if row.get("explanation") not in K2_EXPLANATIONS
        }
    )
    return {
        "label": K2_VERIFIED,
        "executor_commit": k2.get("executor_commit"),
        "pairs": k2.get("pairs"),
        "outcome": k2.get("outcome"),
        "families_dropped": dropped,
    }


def item_families(
    items: Sequence[Mapping[str, Any]], by_cell: Mapping[str, Mapping[str, Mapping[str, Any]]]
) -> dict[str, str | None]:
    """Each item's checker family (its task's set of metric functions), from its score rows."""
    out: dict[str, str | None] = {}
    order = [levels.RAW, levels.CONTROL_CELL, *sorted(by_cell)]
    for item in items:
        out[item["item_id"]] = None
        for cell in order:
            row = (by_cell.get(cell) or {}).get(item["item_id"])
            if row is not None and row.get("checker_funcs") is not None:
                out[item["item_id"]] = checker_family(row["checker_funcs"])
                break
    return out


def _cell_tables(
    items: Sequence[Mapping[str, Any]],
    by_cell: Mapping[str, Mapping[str, Mapping[str, Any]]],
    round_idx: Sequence[Mapping[str, Mapping[str, Mapping[str, Any]]]],
    errors: Mapping[str, str],
    n_boot: int,
) -> dict[str, Any]:
    """Per checker, every registered cell's tables and its reading before the gates."""
    control = by_cell[levels.CONTROL_CELL]
    raw = by_cell.get(levels.RAW, {})
    ret = {c: retention(items, rows) for c, rows in by_cell.items() if c != levels.RAW}
    ret_ok = {c: r["retained"] for c, r in ret.items()}
    build_ok = {
        b.id: ret_ok.get(levels.cell_id(b.id, "ctrl_s", "L0"), False) for b in levels.BUILDS
    }
    out: dict[str, Any] = {"retention": ret, "builds_retained": build_ok}
    for checker in CHECKERS:
        tables: dict[str, Any] = {}
        control_flips = flips_against_raw(items, raw, control, checker) if raw else []
        for cell in levels.registered_cells():
            if cell.role == "control":
                continue
            if cell.id not in by_cell:
                tables[cell.id] = {
                    "cell": cell.as_dict(),
                    "scored": False,
                    "not_scored_reason": errors[cell.id],
                    "retained": False,
                    "reading_before_gates": "NOT_EVALUABLE",
                }
                continue
            rows = by_cell[cell.id]
            pairs, valid_ids, excluded = discordances(items, control, rows, checker)
            status = {p["item_id"]: confirm_status(p, cell.id, round_idx, checker) for p in pairs}
            gold = population_table(items, pairs, valid_ids, status, "gold", n_boot)
            s1a = {
                pop: population_table(items, pairs, valid_ids, status, pop, n_boot)
                for pop in S1A_POPULATIONS
            }
            retained = ret_ok.get(cell.id, False) and build_ok.get(cell.build, False)
            flips = flips_against_raw(items, raw, rows, checker) if raw else []
            unstable_primary = gold["unstable"] + s1a[PRIMARY_S1A]["unstable"]
            tables[cell.id] = {
                "cell": cell.as_dict(),
                "scored": True,
                "retained": retained,
                "reading_before_gates": cell_reading(gold, s1a[PRIMARY_S1A], retained),
                "excluded_pairs": len(excluded),
                "gold": gold,
                "s1a": s1a,
                "harness_noise": unstable_primary >= NOISE_FLAG_MIN,
                "flips_against_raw": flips,
                "jaccard_with_control_flips": jaccard(flips, control_flips),
                **failures(items, rows),
            }
        out[checker] = {"cells": tables, "control_flips_against_raw": control_flips}
    return out


def _gates(
    items: Sequence[Mapping[str, Any]],
    by_cell: Mapping[str, Mapping[str, Mapping[str, Any]]],
    tables: Mapping[str, Any],
    reference: Mapping[str, str],
    errors: Mapping[str, str],
) -> dict[str, Any]:
    control_ret = tables["retention"][levels.CONTROL_CELL]
    gates: dict[str, Any] = {
        "control_retained": {
            "status": "pass" if control_ret["retained"] else "fail",
            "retention": control_ret,
        },
        "V1": v1_check(items, by_cell[levels.CONTROL_CELL], reference),
    }
    rep = tables["pinned"]["cells"][levels.REPLICATE_CELL]
    if not rep["scored"]:
        gates["V2"] = {"status": "not_evaluable", "reason": errors[levels.REPLICATE_CELL]}
    elif not rep["retained"]:
        gates["V2"] = {"status": "not_evaluable", "reason": "the replicate cell was not retained"}
    else:
        pops = [rep["gold"], *rep["s1a"].values()]
        conf = sum(p["confirmed"] for p in pops)
        pend = sum(p["pending"] for p in pops)
        unstable = sum(p["unstable"] for p in pops)
        gates["V2"] = {
            "status": "fail" if conf else ("pending" if pend else "pass"),
            "confirmed": conf,
            "pending": pend,
            "unstable": unstable,
            "harness_noise": unstable > 0,
        }
    statuses = [g["status"] for g in gates.values()]
    if "fail" in statuses or "not_evaluable" in statuses:
        gates["gate"] = "invalid"
    elif "pending" in statuses:
        gates["gate"] = "pending"
    else:
        gates["gate"] = "pass"
    return gates


def _readings(tables: dict[str, Any], gate: str) -> None:
    """Fill every cell's and arm's reading after the gates (in place)."""
    build_ok = tables["builds_retained"]
    retained_builds = sum(build_ok.get(b.id, False) for b in levels.BUILDS[1:])
    for checker in CHECKERS:
        cells = tables[checker]["cells"]
        for table in cells.values():
            table["reading"] = gated(table["reading_before_gates"], gate)
        arms: dict[str, Any] = {}
        for arm in levels.PRIMARY_ARMS:
            members = [
                t
                for t in cells.values()
                if t["cell"]["arm"] == arm and t["cell"]["role"] == "primary"
            ]
            before = arm_reading([t["reading_before_gates"] for t in members], arm, retained_builds)
            arms[arm] = {
                "reading": gated(before, gate),
                "reading_before_gates": before,
                "cells": {t["cell"]["id"]: t["reading"] for t in members},
            }
        tables[checker]["arms"] = arms


def _computation(
    items: Sequence[Mapping[str, Any]],
    by_cell: Mapping[str, Mapping[str, Mapping[str, Any]]],
    round_idx: Sequence[Mapping[str, Mapping[str, Mapping[str, Any]]]],
    errors: Mapping[str, str],
    gate: str | None,
    reference: Mapping[str, str],
    n_boot: int,
) -> dict[str, Any]:
    tables = _cell_tables(items, by_cell, round_idx, errors, n_boot)
    validity = _gates(items, by_cell, tables, reference, errors)
    _readings(tables, gate or validity["gate"])
    raw = by_cell.get(levels.RAW, {})
    control = by_cell[levels.CONTROL_CELL]
    return {
        "items": len(items),
        "items_by_population": dict(Counter(i["population"] for i in items)),
        "validity": validity,
        "retention": tables["retention"],
        "builds_retained": tables["builds_retained"],
        "pinned": tables["pinned"],
        "zinv": tables["zinv"],
        "descriptive": {
            "p1_replication_gold": _against_raw(items, raw, control, "gold"),
            "s1a_fixed_point": {
                pop: _against_raw(items, raw, control, pop) for pop in S1A_POPULATIONS
            },
            "timing": {c: timing(rows) for c, rows in by_cell.items() if c != levels.RAW},
        },
    }


def analyze(
    items: Sequence[Mapping[str, Any]],
    scores: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    reference: Mapping[str, str],
    splits: Sequence[str],
    rounds: Sequence[Mapping[str, Sequence[Mapping[str, Any]]]] = (),
    cell_errors: Mapping[str, str] | None = None,
    k2: Mapping[str, Any] | None = None,
    inputs: Mapping[str, Any] | None = None,
    n_boot: int = 10_000,
) -> dict[str, Any]:
    """The registered analysis over one run's items, score rows and confirmation rounds."""
    chosen = levels.check_split_set(splits)
    if len(rounds) not in (0, CONFIRM_ROUNDS):
        raise AnalysisError(f"{len(rounds)} confirmation rounds given; exactly 0 or 2")
    scoped = [i for i in items if i["split"] in chosen]
    if not scoped:
        raise AnalysisError(f"no item of splits {list(chosen)}")
    by_cell = {cell: index_rows(rows) for cell, rows in scores.items()}
    known = set(levels.CELL_BY_ID) | {levels.RAW}
    if set(by_cell) - known:
        raise AnalysisError(f"unregistered cells scored: {sorted(set(by_cell) - known)}")
    errors = dict(cell_errors or {})
    if set(errors) - known:
        raise AnalysisError(f"cell errors name unregistered cells: {sorted(set(errors) - known)}")
    if set(errors) & set(by_cell):
        raise AnalysisError(
            f"cell errors may name only cells without scores: {sorted(set(errors) & set(by_cell))}"
        )
    missing = sorted(c for c in known if c not in by_cell and c not in errors)
    if missing:
        raise AnalysisError(f"cells neither scored nor named with a reason: {missing}")
    round_idx = [{cell: index_rows(rows) for cell, rows in rnd.items()} for rnd in rounds]
    for rnd in round_idx:
        if set(rnd) - set(levels.CELL_BY_ID):
            raise AnalysisError(f"a round scored unregistered cells: {sorted(set(rnd))}")
    fidelity = k2_fidelity(k2)
    out: dict[str, Any] = {
        "schema": SCHEMA,
        "experiment_id": levels.EXPERIMENT_ID,
        "warning": BLIND_WARNING,
        "vm_fidelity": fidelity,
        "splits": list(chosen),
        "confirmation_rounds": len(rounds),
        "cells_scored": sorted(by_cell),
        "cells_not_scored": dict(sorted(errors.items())),
        "inputs": dict(inputs or {}),
    }
    if levels.CONTROL_CELL not in by_cell:
        out["validity"] = {
            "control_scored": {"status": "fail", "reason": errors[levels.CONTROL_CELL]},
            "gate": "invalid",
        }
        for checker in CHECKERS:
            out[checker] = {
                "cells": {
                    c.id: {"cell": c.as_dict(), "reading": "INVALID"}
                    for c in levels.registered_cells()
                    if c.role != "control"
                },
                "arms": {arm: {"reading": "INVALID"} for arm in levels.PRIMARY_ARMS},
            }
        out["complete"] = True
        return out
    dropped = set(fidelity["families_dropped"])
    if dropped:
        full = _computation(scoped, by_cell, round_idx, errors, None, reference, n_boot)
        family = item_families(scoped, by_cell)
        kept = [i for i in scoped if family[i["item_id"]] not in dropped]
        main = _computation(
            kept, by_cell, round_idx, errors, full["validity"]["gate"], reference, n_boot
        )
        main["validity"] = full["validity"]
        out.update(main)
        out["k2_exploratory"] = {
            "families": sorted(dropped),
            "items_left_out": len(scoped) - len(kept),
            "including_dropped_families": full,
        }
    else:
        out.update(_computation(scoped, by_cell, round_idx, errors, None, reference, n_boot))
    pending = pending_confirmations(out)
    out["complete"] = out["validity"]["gate"] != "pending" and not pending["items"]
    return out


def _against_raw(
    items: Sequence[Mapping[str, Any]],
    raw: Mapping[str, Mapping[str, Any]],
    control: Mapping[str, Mapping[str, Any]],
    population: str,
) -> dict[str, Any]:
    pop = [i for i in items if i["population"] == population]
    n, changes = 0, defaultdict(list)
    for item in pop:
        a, b = raw.get(item["item_id"]), control.get(item["item_id"])
        if valid(a) and valid(b):
            n += 1
            if verdict(a) != verdict(b):  # type: ignore[arg-type]
                changes[f"{verdict(a)}->{verdict(b)}"].append(item["item_id"])  # type: ignore[arg-type]
    total = sum(len(v) for v in changes.values())
    return {
        "items": len(pop),
        "valid": n,
        "changed": total,
        "by_direction": {k: sorted(v) for k, v in sorted(changes.items())},
        **({"interval": interval_block(total, n)} if n else {}),
    }


def pending_confirmations(result: Mapping[str, Any]) -> dict[str, list[str]]:
    """The items and cells the confirmation rounds must re-run: every discordance of either
    checker whose status is pending, K2-dropped families included (the control is always
    re-run with them)."""
    source = (result.get("k2_exploratory") or {}).get("including_dropped_families") or result
    item_ids: set[str] = set()
    cells: set[str] = set()
    for checker in CHECKERS:
        for cid, table in ((source.get(checker) or {}).get("cells") or {}).items():
            if not table.get("scored"):
                continue
            for pop in [table["gold"], *table["s1a"].values()]:
                for disc in pop["discordances"]:
                    if disc["status"] == "pending":
                        item_ids.add(disc["item_id"])
                        cells.add(cid)
    return {"items": sorted(item_ids), "cells": sorted(cells)}


# --- inputs --------------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_input(path: Path) -> Path:
    """Refuse an input that names an audit, decision, adjudication or rater file."""
    tail = "/".join(path.parts[-2:])
    if FORBIDDEN_INPUT.search(tail):
        raise AnalysisError(f"{path}: R04 never reads audit, decision or adjudication files")
    if not path.exists():
        raise AnalysisError(f"{path}: missing")
    return path


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    check_input(path)
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def receipts(directory: Path) -> list[dict[str, Any]]:
    """The lane receipts of a score directory (job id and exit status of each)."""
    out = []
    for path in sorted(directory.glob("receipt-*.json")):
        receipt = json.loads(path.read_text(encoding="utf-8"))
        out.append({"job": str(receipt.get("job_id")), "exit_status": receipt.get("exit_status")})
    return out


def load_scores(
    directories: Sequence[Path],
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    """Score rows by cell from one or more score directories, each holding the receipt of a
    lane job that finished with exit status 0; a cell scored in two directories is refused."""
    scores: dict[str, list[dict[str, Any]]] = {}
    record = []
    for directory in directories:
        check_input(directory)
        jobs = receipts(directory)
        if not jobs:
            raise AnalysisError(f"{directory}: no lane receipt")
        if any(j["exit_status"] != 0 for j in jobs):
            raise AnalysisError(f"{directory}: a lane job did not finish with exit status 0")
        cells = []
        for path in sorted(directory.glob("scores-*.jsonl")):
            cell = path.name[len("scores-") : -len(".jsonl")]
            if cell in scores:
                raise AnalysisError(f"cell {cell} scored in two directories")
            scores[cell] = read_jsonl(path)
            cells.append(cell)
        record.append({"dir": str(directory), "jobs": [j["job"] for j in jobs], "cells": cells})
    return scores, record


def reference_from_control_summaries(
    paths: Sequence[Path], splits: Sequence[str]
) -> tuple[dict[str, str], list[dict[str, str]]]:
    """Task -> saved gold verdict (lock venv) of the frozen control runs' summaries, which
    must be exactly the pinned summaries of the analysed splits."""
    want = {levels.CONTROL_SUMMARIES[s][1]: s for s in levels.check_split_set(splits)}
    got: dict[str, Path] = {}
    for path in paths:
        digest = sha256_file(check_input(path))
        if digest not in want or digest in got:
            raise AnalysisError(f"{path} is not one of the pinned control summaries of {splits}")
        got[digest] = path
    if set(got) != set(want):
        missing = sorted(want[d] for d in set(want) - set(got))
        raise AnalysisError(f"the pinned control summaries of splits {missing} were not given")
    ref: dict[str, str] = {}
    for path in got.values():
        tasks = json.loads(path.read_text(encoding="utf-8"))["tasks"]
        for task_id, entry in tasks.items():
            saved_gold = entry.get("gold_saved_lock")
            if saved_gold and saved_gold.get("verdict"):
                ref[task_id] = str(saved_gold["verdict"])
    record = [{"path": str(p), "sha256": d, "split": want[d]} for d, p in sorted(got.items())]
    return ref, record


# Step states of a finished plan (``r04_host.py``): done, or ended without output.
STEP_DONE = "done"
STEP_ENDED = ("superseded", "failed_final", "not_run", "dropped")


def load_run(run_dir: Path, src: Path) -> dict[str, Any]:
    """Every input of the registered analysis from a run's plan and directories.

    The plan names each step's state and directory (host paths under the plan's
    ``run_root``, read here under ``run_dir``). Refused while a step is pending or
    submitted. The analysis reads the items, the score directory of every main score step
    that finished, and, once the confirmation rounds exist, those of both rounds; a cell
    whose score step or save step ended without scoring it is named with the plan's reason;
    the reference is the pinned control summaries of the plan's splits (from ``src``)."""
    plan = json.loads(check_input(run_dir / "plan.json").read_text(encoding="utf-8"))
    root = Path(plan["run_root"])

    def local(path: str) -> Path:
        return run_dir / Path(path).relative_to(root)

    unfinished = [s["name"] for s in plan["steps"] if s["state"] not in (STEP_DONE, *STEP_ENDED)]
    if unfinished:
        raise AnalysisError(f"the run has unfinished steps: {unfinished}")
    steps = [s for s in plan["steps"] if s["state"] != "superseded"]
    items_step = next(s for s in steps if s["kind"] == "items")
    if items_step["state"] != "done":
        raise AnalysisError("the item step did not finish")
    main_dirs: list[Path] = []
    errors: dict[str, str] = {}
    for step in steps:
        if step["kind"] != "score" or step["out"] != "main":
            continue
        for cell, reason in (step.get("not_scored") or {}).items():
            errors[cell] = reason
        if step["state"] == "done":
            main_dirs.append(local(step["run_dir"]))
        else:
            for cell in step["cells"]:
                errors.setdefault(
                    cell,
                    f"score job {step['name']} {step['state']}: {step.get('reason') or ''}".strip(),
                )
    rounds: list[list[Path]] = []
    if plan.get("rounds"):
        for out in ("round-1", "round-2"):
            rounds.append(
                [
                    local(s["run_dir"])
                    for s in steps
                    if s["kind"] == "score" and s["out"] == out and s["state"] == "done"
                ]
            )
    reference = [src / levels.CONTROL_SUMMARIES[s][0] for s in plan["splits"]]
    return {
        "plan": plan,
        "items": [local(items_step["run_dir"]) / "items.jsonl"],
        "scores": main_dirs,
        "rounds": rounds,
        "splits": plan["splits"],
        "reference": reference,
        "cell_errors": errors,
        "jobs": [
            {"name": s["name"], "job": s.get("job"), "state": s["state"]} for s in plan["steps"]
        ],
    }


def _round_scores(dirs: Sequence[Path]) -> tuple[dict[str, list[dict[str, Any]]], list[Any]]:
    if not dirs:
        return {}, []
    return load_scores(dirs)


def run_analysis(args: argparse.Namespace) -> dict[str, Any]:
    k2 = None
    inputs: dict[str, Any] = {}
    if args.k2_report:
        k2 = json.loads(check_input(args.k2_report).read_text(encoding="utf-8"))
        inputs["k2_report"] = {"path": str(args.k2_report), "sha256": sha256_file(args.k2_report)}
    if args.run:
        spec = load_run(args.run, args.src)
        inputs["mode"] = "run"
        inputs["run"] = {"name": spec["plan"]["name"], "src_sha": spec["plan"].get("src_sha")}
        inputs["jobs"] = spec["jobs"]
        item_paths, score_dirs, round_dirs = spec["items"], spec["scores"], spec["rounds"]
        splits, ref_paths, errors = spec["splits"], spec["reference"], spec["cell_errors"]
    else:
        if not (args.items and args.scores and args.splits and args.reference):
            raise AnalysisError("--items, --scores, --splits and --reference are required")
        inputs["mode"] = "explicit"
        item_paths, score_dirs = args.items, args.scores
        round_dirs = args.round
        splits, ref_paths = args.splits, args.reference
        errors = (
            json.loads(check_input(args.cell_errors).read_text(encoding="utf-8"))
            if args.cell_errors
            else {}
        )
    items = [row for path in item_paths for row in read_jsonl(path)]
    inputs["items"] = [{"path": str(p), "sha256": sha256_file(p)} for p in item_paths]
    scores, inputs["scores"] = load_scores(score_dirs)
    rounds = []
    inputs["rounds"] = []
    for dirs in round_dirs:
        rnd, record = _round_scores(dirs)
        rounds.append(rnd)
        inputs["rounds"].append(record)
    reference, inputs["reference"] = reference_from_control_summaries(ref_paths, splits)
    if args.run and rounds:
        # The rounds re-ran exactly what the main run left pending.
        main_only = analyze(
            items, scores, reference=reference, splits=splits, cell_errors=errors, k2=k2, n_boot=10
        )
        if pending_confirmations(main_only) != spec["plan"]["rounds"]["pending"]:
            raise AnalysisError("the rounds did not re-run the main run's pending discordances")
    return analyze(
        items,
        scores,
        reference=reference,
        splits=splits,
        rounds=rounds,
        cell_errors=errors,
        k2=k2,
        inputs=inputs,
        n_boot=args.n_boot,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--run",
        type=Path,
        default=None,
        help="a run directory with plan.json (the registered computation)",
    )
    parser.add_argument("--src", type=Path, default=Path("."), help="repository root")
    parser.add_argument("--items", type=Path, nargs="+", default=None)
    parser.add_argument("--scores", type=Path, nargs="+", default=None, help="score directories")
    parser.add_argument(
        "--round",
        type=Path,
        nargs="+",
        action="append",
        default=[],
        help="one confirmation round's score directories (given twice, or not at all)",
    )
    parser.add_argument("--reference", type=Path, nargs="+", default=None)
    parser.add_argument("--splits", nargs="+", default=None)
    parser.add_argument("--cell-errors", type=Path, default=None, help="unscored cells' reasons")
    parser.add_argument("--k2-report", type=Path, default=None)
    parser.add_argument("--n-boot", type=int, default=10_000)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--pending-out",
        type=Path,
        default=None,
        help="write the items and cells the confirmation rounds re-run",
    )
    args = parser.parse_args(argv)
    if args.run and (
        args.items or args.scores or args.round or args.reference or args.splits or args.cell_errors
    ):
        parser.error("--run reads every input from the run; give no other input")
    try:
        result = run_analysis(args)
    except AnalysisError as exc:
        raise SystemExit(f"refused: {exc}") from exc
    args.out.write_text(json.dumps(result, indent=1, sort_keys=True), encoding="utf-8")
    if args.pending_out:
        args.pending_out.write_text(
            json.dumps(pending_confirmations(result), indent=1, sort_keys=True), encoding="utf-8"
        )
    print(
        json.dumps(
            {
                "validity": {
                    k: v.get("status", v) if isinstance(v, dict) else v
                    for k, v in result["validity"].items()
                },
                "arms": {
                    c: {a: v["reading"] for a, v in result[c]["arms"].items()} for c in CHECKERS
                },
                "complete": result["complete"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
