"""Registered analysis of r04-checker-nuisance-invariance-v1 (standard library only).

Every comparison is paired with the control cell (``B0.ctrl_s.L0``, the checker-mutation
study's registered save): for an item valid in both cells (saved without failure, scored
deterministically, no infrastructure failure), the item is discordant when its verdict
(pass, fail or error) under the cell differs from its verdict under the control. A
discordance counts only when it is confirmed: both confirmation rounds re-save and re-score
the item under the control and under the cell and reproduce both verdicts. Unconfirmed
discordances are harness instability, counted and listed, never a finding.

Per cell, on the primary populations (the gold items of the registered splits, and S1a's
pass states with the task as the unit):

* ``k_gold``: confirmed discordant golds; ``t_s1a``: S1a tasks with at least one confirmed
  discordant pass state;
* reading ``DRIFT`` if ``k_gold >= 3`` or ``t_s1a >= 3``; ``INVARIANT`` if both are 0;
  ``MINOR`` otherwise; ``NOT_EVALUABLE`` if the cell (or its build, or its locale) was not
  retained; ``PENDING`` if a discordance waits for its confirmation rounds.

A cell is retained when its save stage succeeded on at least 90% of its gold items and of
its S1a items; a build is retained when its ``ctrl_s`` cell is, and a locale when its
data compiled and its cell is retained. An arm (route, build, locale) reads ``DRIFT`` if
any of its retained primary cells does, ``INVARIANT`` if all do, ``NOT_EVALUABLE`` if none
is retained (or, for the build arm, fewer than two builds), and ``MINOR`` otherwise.

Validity, before any reading: V1, the control reproduces the frozen control runs' saved
gold verdicts (at most one difference); V2, the replicate cell has no confirmed discordance
with the control in any population. A failed or pending gate makes every reading
``INVALID`` or ``PENDING``.

The pinned checker is primary; the corrected comparator (``zinv``) gets the same tables and
readings as a secondary checker. Descriptive outputs: the P1 replication (control against
the unsaved gold), S1a's fixed point (control against the captured state), every cell's
flip set against the unsaved item and its overlap with the control's, discordances by
direction and checker family, intervals, save timing and dialogs.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from harness.q2_mutation.stats import Unit, clopper_pearson, cluster_bootstrap_ci, exact_upper_bound
from harness.r04_nuisance import levels

SCHEMA = "r04-analysis-v1"
DRIFT_MIN = 3
RETENTION_MIN = 0.90
V1_MAX_DIFFERENCES = 1
CONFIRM_ROUNDS = 2
PRIMARY_S1A = "s1a_pass"
SAVE_FAILED = frozenset({"save_failed", "infra_error", "no_lo_row"})
CHECKERS = ("pinned", "zinv")


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
            raise ValueError(f"item {row['item_id']} scored twice in cell {row.get('cell')}")
        out[row["item_id"]] = row
    return out


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
                }
            )
    return pairs, valid_ids, excluded


def confirm_status(
    pair: Mapping[str, Any],
    cell_id: str,
    rounds: Sequence[Mapping[str, Mapping[str, Mapping[str, Any]]]],
    checker: str,
) -> str:
    """confirmed, unstable (a round disagreed or was invalid), or pending (rounds missing)."""
    if len(rounds) < CONFIRM_ROUNDS:
        return "pending"
    iid = pair["item_id"]
    for rnd in rounds[:CONFIRM_ROUNDS]:
        if levels.CONTROL_CELL not in rnd or cell_id not in rnd:
            return "pending"
        a = rnd[levels.CONTROL_CELL].get(iid)
        b = rnd[cell_id].get(iid)
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
    for group, pops in (("gold", ("gold",)), ("s1a", ("s1a_pass", "s1a_fail", "s1a_mixed"))):
        ids = [i["item_id"] for i in items if i["population"] in pops]
        if not ids:
            out[group] = {"items": 0, "saved": 0, "share": None}
            continue
        saved = sum(
            1
            for iid in ids
            if rows.get(iid) is not None
            and rows[iid].get("status") not in SAVE_FAILED
            and rows[iid].get("status") != "harness_error"
        )
        out[group] = {"items": len(ids), "saved": saved, "share": saved / len(ids)}
    shares = [g["share"] for g in out.values() if g["share"] is not None]
    out["retained"] = bool(shares) and all(s >= RETENTION_MIN for s in shares)
    return out


def interval_block(k: int, n: int) -> dict[str, Any]:
    if n == 0:
        return {"k": k, "n": 0}
    low, high = clopper_pearson(k, n)
    return {
        "k": k,
        "n": n,
        "share": k / n,
        "cp95": [low, high],
        "upper95_one_sided": exact_upper_bound(k, n),
    }


def population_table(
    items: Sequence[Mapping[str, Any]],
    pairs: Sequence[Mapping[str, Any]],
    valid_ids: Sequence[str],
    status_of: Mapping[str, str],
    population: str,
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
        "by_family": dict(Counter("+".join(p.get("checker_funcs") or []) for p in confirmed)),
        "item_level": interval_block(len(confirmed), len(valid_pop)),
        "task_level": interval_block(len(tasks_conf), len(tasks_valid)),
        "discordances": [{**p, "status": status_of[p["item_id"]]} for p in disc],
    }
    if population != "gold" and valid_pop:
        conf_ids = {p["item_id"] for p in confirmed}
        units = [Unit(pop_items[iid]["task_id"], iid in conf_ids) for iid in valid_pop]
        ci = cluster_bootstrap_ci(units)
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
    for row in rows.values():
        for save in (row.get("save") or {}).get("saves") or []:
            saves += 1
            if save.get("seconds_to_write") is not None:
                seconds.append(float(save["seconds_to_write"]))
            dialogs += bool(save.get("dialogs"))
            changed += bool(save.get("changed"))
    if not seconds:
        return {"saves": saves}
    seconds.sort()
    return {
        "saves": saves,
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
    reference: Mapping[str, str] | None,
) -> dict[str, Any]:
    if reference is None:
        return {"status": "not_checked", "reason": "no frozen control verdicts given"}
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


def analyze(
    items: Sequence[Mapping[str, Any]],
    scores: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    rounds: Sequence[Mapping[str, Sequence[Mapping[str, Any]]]] = (),
    reference: Mapping[str, str] | None = None,
    cell_errors: Mapping[str, str] | None = None,
    splits: Sequence[str] = ("confirm", "reserve"),
) -> dict[str, Any]:
    """The registered analysis over one run's items, score rows and confirmation rounds."""
    scoped = [i for i in items if i["split"] in splits]
    by_cell = {cell: index_rows(rows) for cell, rows in scores.items()}
    round_idx = [{cell: index_rows(rows) for cell, rows in rnd.items()} for rnd in rounds]
    if levels.CONTROL_CELL not in by_cell:
        raise ValueError("the control cell was not scored")
    control = by_cell[levels.CONTROL_CELL]
    raw = by_cell.get("raw", {})
    cells = [c for c in levels.registered_cells() if c.id in by_cell and c.role != "control"]
    errors = dict(cell_errors or {})
    out: dict[str, Any] = {
        "schema": SCHEMA,
        "experiment_id": levels.EXPERIMENT_ID,
        "splits": list(splits),
        "items": len(scoped),
        "items_by_population": dict(Counter(i["population"] for i in scoped)),
        "cells_scored": sorted(by_cell),
    }
    out["retention"] = {c: retention(scoped, rows) for c, rows in by_cell.items() if c != "raw"}
    ret_ok = {c: r["retained"] and c not in errors for c, r in out["retention"].items()}
    build_ok = {
        b.id: ret_ok.get(levels.cell_id(b.id, "ctrl_s", "L0"), False) for b in levels.BUILDS
    }
    for checker in CHECKERS:
        tables: dict[str, Any] = {}
        for cell in cells:
            pairs, valid_ids, excluded = discordances(scoped, control, by_cell[cell.id], checker)
            status = {p["item_id"]: confirm_status(p, cell.id, round_idx, checker) for p in pairs}
            gold = population_table(scoped, pairs, valid_ids, status, "gold")
            s1a = {
                pop: population_table(scoped, pairs, valid_ids, status, pop)
                for pop in ("s1a_pass", "s1a_fail", "s1a_mixed")
            }
            retained = ret_ok.get(cell.id, False) and build_ok.get(cell.build, False)
            reading = cell_reading(gold, s1a[PRIMARY_S1A], retained)
            flips = flips_against_raw(scoped, raw, by_cell[cell.id], checker) if raw else []
            tables[cell.id] = {
                "cell": cell.as_dict(),
                "retained": retained,
                "reading": reading,
                "excluded_pairs": len(excluded),
                "gold": gold,
                "s1a": s1a,
                "flips_against_raw": flips,
                "cell_error": errors.get(cell.id),
            }
        control_flips = flips_against_raw(scoped, raw, control, checker) if raw else []
        for t in tables.values():
            t["jaccard_with_control_flips"] = jaccard(t["flips_against_raw"], control_flips)
        out[checker] = {"cells": tables, "control_flips_against_raw": control_flips}
    out["validity"] = {"V1": v1_check(scoped, control, reference)}
    rep = out["pinned"]["cells"].get(levels.REPLICATE_CELL)
    if rep is None:
        out["validity"]["V2"] = {"status": "not_run"}
    else:
        conf = rep["gold"]["confirmed"] + sum(p["confirmed"] for p in rep["s1a"].values())
        pend = rep["gold"]["pending"] + sum(p["pending"] for p in rep["s1a"].values())
        unstable = rep["gold"]["unstable"] + sum(p["unstable"] for p in rep["s1a"].values())
        out["validity"]["V2"] = {
            "status": "fail" if conf else ("pending" if pend else "pass"),
            "confirmed": conf,
            "pending": pend,
            "unstable": unstable,
        }
    gate = [out["validity"]["V1"]["status"], out["validity"]["V2"]["status"]]
    invalid = "fail" in gate
    pending = "pending" in gate or "not_run" in gate or "not_checked" in gate
    for checker in CHECKERS:
        arms: dict[str, Any] = {}
        cells_out = out[checker]["cells"]
        for arm in levels.PRIMARY_ARMS:
            members = [
                t
                for t in cells_out.values()
                if t["cell"]["arm"] == arm and t["cell"]["role"] == "primary"
            ]
            readings = [t["reading"] for t in members]
            if invalid:
                readings = ["INVALID"]
            retained_builds = sum(build_ok.get(b.id, False) for b in levels.BUILDS[1:])
            reading = arm_reading(readings, arm, retained_builds)
            if pending and reading not in ("INVALID",):
                reading = f"{reading} (validity gate pending)"
            arms[arm] = {
                "reading": reading,
                "cells": {t["cell"]["id"]: t["reading"] for t in members},
            }
        out[checker]["arms"] = arms
    out["builds_retained"] = build_ok
    out["descriptive"] = {
        "p1_replication_gold": _against_raw(scoped, raw, control, "gold"),
        "s1a_fixed_point": {
            pop: _against_raw(scoped, raw, control, pop)
            for pop in ("s1a_pass", "s1a_fail", "s1a_mixed")
        },
        "timing": {c: timing(rows) for c, rows in by_cell.items() if c != "raw"},
    }
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


# --- CLI -----------------------------------------------------------------------------------


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def load_scores(directory: Path) -> dict[str, list[dict[str, Any]]]:
    return {
        p.name[len("scores-") : -len(".jsonl")]: read_jsonl(p)
        for p in sorted(directory.glob("scores-*.jsonl"))
    }


def reference_from_control_summaries(paths: Sequence[Path]) -> dict[str, str]:
    """Task -> saved gold verdict (lock venv) of the frozen control runs' summaries."""
    ref: dict[str, str] = {}
    for path in paths:
        tasks = json.loads(path.read_text(encoding="utf-8"))["tasks"]
        for task_id, entry in tasks.items():
            saved = entry.get("gold_saved_lock")
            if saved and saved.get("verdict"):
                ref[task_id] = str(saved["verdict"])
    return ref


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--items", type=Path, nargs="+", required=True)
    parser.add_argument("--scores", type=Path, required=True, help="dir of scores-<cell>.jsonl")
    parser.add_argument(
        "--round",
        type=Path,
        action="append",
        default=[],
        help="a confirmation round's scores dir (twice)",
    )
    parser.add_argument(
        "--reference", type=Path, nargs="*", default=[], help="frozen control-run summaries (V1)"
    )
    parser.add_argument("--splits", nargs="+", default=["confirm", "reserve"])
    parser.add_argument("--cell-errors", type=Path, default=None)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    items = [row for path in args.items for row in read_jsonl(path)]
    result = analyze(
        items,
        load_scores(args.scores),
        rounds=[load_scores(r) for r in args.round],
        reference=reference_from_control_summaries(args.reference) if args.reference else None,
        cell_errors=json.loads(args.cell_errors.read_text()) if args.cell_errors else None,
        splits=args.splits,
    )
    args.out.write_text(json.dumps(result, indent=1, sort_keys=True), encoding="utf-8")
    print(
        json.dumps(
            {"validity": result["validity"], "arms": {c: result[c]["arms"] for c in CHECKERS}},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
