"""S2 v4: the VM lane's probe records as the inputs of ``k0_v4.admit`` (the admission half of K0).

Reads every attempt's record (``probes.jsonl`` of one or more lane runs: capture slots from
``vm_probe.py``, gold slots from ``vm_gold.py``) and the task pool (``pool-v3.json``: each task's
strict ``activate_window`` targets), and builds, per task, what the registration's K0 section reads
in each admission cell:

* ``observed``: the cell's capture slot ended ``probed`` (its last attempt);
* ``setup_failed``: every attempt of the cell's capture slot failed in the task's own setup
  (``probe:reset_task``);
* ``titles``, ``rewritten``, ``donothing``: the post-setup window titles, whether the postconfig
  rewrote each file the checker reads, and the checker's verdict on the do-nothing state;
* ``gold``: the gold slot's verdict (``None`` when the task has no gold slot in that cell or it was
  never probed).

The instrument checks need the oracle's per-task metrics, which this module does not compute.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from harness.s2_locale import k0_v4

SETUP_FAILURE = "probe:reset_task"


def load_records(paths: Iterable[Path]) -> list[dict[str, Any]]:
    out = []
    for path in paths:
        out += [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]
    return out


def strict_titles(pool: Mapping[str, Any]) -> dict[str, list[str]]:
    out = {}
    for t in pool.get("tasks", []):
        pairs = zip(t.get("activate_window_titles") or [], t.get("activate_window_strict") or [],
                    strict=False)  # fmt: skip
        out[t["task_id"]] = [title for title, strict in pairs if strict]
    return out


def tasks_from_records(records: Iterable[Mapping[str, Any]],
                       titles: Mapping[str, list[str]],
                       p010: Mapping[str, bool] | None = None) -> list[dict[str, Any]]:  # fmt: skip
    attempts: dict[tuple[str, str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for r in records:
        kind = r.get("kind", "capture")
        rep = str(r.get("slot", "")).rsplit(":", 1)[-1]
        if kind == "capture" and rep != "r1":
            continue  # replicate boots (E2, ER2) are A/A renders, not admission cells
        attempts[(r["task_id"], r["cell"], kind)].append(r)
    tasks: dict[str, dict[str, Any]] = {}
    for (task_id, cell, kind), rows in sorted(attempts.items()):
        if cell not in k0_v4.ADMISSION_CELLS:
            continue
        rows = sorted(rows, key=lambda r: int(r.get("attempt") or 1))
        last = rows[-1]
        t = tasks.setdefault(task_id, {"task_id": task_id, "strict_titles": titles.get(task_id, []),
                                       "cells": {}})  # fmt: skip
        if p010 is not None and task_id in p010:
            t["p010_pass"] = p010[task_id]
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
        )  # fmt: skip
    return [tasks[k] for k in sorted(tasks)]


def admission(records: Iterable[Mapping[str, Any]], pool: Mapping[str, Any],
              p010: Mapping[str, bool] | None = None) -> list[dict[str, Any]]:  # fmt: skip
    return [k0_v4.admit(t) for t in tasks_from_records(records, strict_titles(pool), p010)]
