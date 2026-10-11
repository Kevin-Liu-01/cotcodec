"""S2 v4: the VM lane's probe records as the inputs of ``k0_v4.admit`` (the admission half of K0).

Reads every attempt's record (``probes.jsonl`` of the registered ``phase0`` job, and of its one
resume if it was interrupted; capture slots from ``vm_probe.py``, gold slots from ``vm_gold.py``)
and the task pool (``pool-v3.json``: the 106 tasks and each task's strict ``activate_window``
targets), and builds, per pool task, what the registration's K0 section reads in each admission
cell:

* ``observed``: the cell's capture slot ended ``probed`` (its last attempt);
* ``setup_failed``: every attempt of the cell's capture slot failed in the task's own setup
  (``probe:reset_task``);
* ``titles``, ``rewritten``, ``donothing``: the post-setup window titles, whether the postconfig
  rewrote each file the checker reads, and the checker's verdict on the do-nothing state;
* ``gold``: the gold slot's verdict (``None`` when the task has no gold slot in that cell or it was
  never probed);
* ``p010_pass`` (the three C1 tasks): P0.10 from the capture slots' reader (``vm_probe``'s
  ``p010`` record): True when the values of every key the task's checker reads are the same in E
  and in every admission cell, False when one differs, None when a cell has no reading.

A pool task with no record at all is still listed (every cell unobserved, so excluded), so the
census report covers all 106. Which records count: a ``cap_truncated`` record is not a final
record; per slot, the attempts of the first job (in the order the record files are given) that
has a final record for it count, and of those the last attempt (the lane's re-queue).

The instrument checks need the oracle's per-task metrics (``oracle_vm.py``).
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from harness.s2_locale import k0_v4

SETUP_FAILURE = "probe:reset_task"
FINAL = ("probed", "infrastructure")


def load_records(paths: Iterable[Path]) -> list[dict[str, Any]]:
    """Every record of the given ``probes.jsonl`` files, each tagged with its file's position."""
    out = []
    for run, path in enumerate(paths):
        for line in Path(path).read_text().splitlines():
            if line.strip():
                out.append({**json.loads(line), "_run": run})
    return out


def strict_titles(pool: Mapping[str, Any]) -> dict[str, list[str]]:
    out = {}
    for t in pool.get("tasks", []):
        pairs = zip(t.get("activate_window_titles") or [], t.get("activate_window_strict") or [],
                    strict=False)  # fmt: skip
        out[t["task_id"]] = [title for title, strict in pairs if strict]
    return out


def counted(records: Iterable[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
    """Per slot id, the attempts that count (see the module docstring), oldest first."""
    by_slot: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for r in records:
        if r.get("status") in FINAL:
            by_slot[str(r["slot"])].append(r)
    out = {}
    for sid, rows in by_slot.items():
        first = min(int(r.get("_run", 0)) for r in rows)
        out[sid] = sorted((r for r in rows if int(r.get("_run", 0)) == first),
                          key=lambda r: int(r.get("attempt") or 1))
    return out


def p010_values(rec: Mapping[str, Any]) -> dict[str, list[Any]] | None:
    p010 = rec.get("p010") if rec.get("status") == "probed" else None
    return dict(p010.get("values") or {}) if isinstance(p010, Mapping) else None


def p010_pass(cells: Mapping[str, Mapping[str, Any]]) -> bool | None:
    """P0.10: every admission cell's reading equals E's (None when one is missing)."""
    readings = {c: (cells.get(c) or {}).get("p010") for c in k0_v4.ADMISSION_CELLS}
    if any(v is None for v in readings.values()):
        return None
    return all(v == readings["E"] for v in readings.values())


def tasks_from_records(records: Iterable[Mapping[str, Any]],
                       titles: Mapping[str, list[str]],
                       p010: Mapping[str, bool] | None = None,
                       pool_ids: Sequence[str] | None = None) -> list[dict[str, Any]]:  # fmt: skip
    tasks: dict[str, dict[str, Any]] = {}
    for task_id in pool_ids or ():
        tasks[task_id] = {"task_id": task_id, "strict_titles": titles.get(task_id, []),
                          "cells": {}}  # fmt: skip
    for _sid, rows in sorted(counted(records).items()):
        last = rows[-1]
        kind = last.get("kind", "capture")
        rep = str(last.get("slot", "")).rsplit(":", 1)[-1]
        if kind == "capture" and rep != "r1":
            continue  # replicate boots (E2, ER2) are A/A renders, not admission cells
        cell, task_id = last["cell"], last["task_id"]
        if cell not in k0_v4.ADMISSION_CELLS:
            continue  # S, AD and PD are instrument renders
        t = tasks.setdefault(task_id, {"task_id": task_id, "strict_titles": titles.get(task_id, []),
                                       "cells": {}})  # fmt: skip
        c = t["cells"].setdefault(cell, {"observed": False, "setup_failed": False, "gold": None})
        if kind == "gold":
            c["gold"] = last.get("verdict") if last.get("status") == "probed" else None
            continue
        probed = last.get("status") == "probed"
        post = last.get("post_setup") or {}
        c.update(
            observed=probed,
            setup_failed=all(r.get("infrastructure_type") == SETUP_FAILURE for r in rows),
            titles=list((post.get("facts") or {}).get("window_titles") or []),
            rewritten={p: bool(v.get("rewritten")) for p, v in
                       (last.get("result_files") or {}).items()},
            donothing=last.get("verdict") if probed else None,
            p010=p010_values(last),
        )  # fmt: skip
    for t in tasks.values():
        if any(t["task_id"].startswith(c1) for c1 in k0_v4.C1_TASKS):
            t["p010_pass"] = (p010 or {}).get(t["task_id"], p010_pass(t["cells"]))
        for cell in t["cells"].values():
            cell.pop("p010", None)
    return [tasks[k] for k in sorted(tasks)]


def admission(records: Iterable[Mapping[str, Any]], pool: Mapping[str, Any],
              p010: Mapping[str, bool] | None = None) -> list[dict[str, Any]]:  # fmt: skip
    """``k0_v4.admit`` for every pool task (no exclusion in pool-v3), records or not."""
    ids = [t["task_id"] for t in pool.get("tasks", []) if t.get("exclusion") is None]
    rows = tasks_from_records(records, strict_titles(pool), p010, ids)
    return [k0_v4.admit(t) for t in rows]
