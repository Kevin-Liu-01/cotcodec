"""S2 v4 Phase 0 admission (K0): the rule of registration s2-arabic-cua-locale-v4, as code.

This module is the executable form of the registration's section "K0: Phase 0 admission rule",
committed with that section before any Phase 0 result on the derived images (the shipped Arabic
catalogs) existed. It reads per-task, per-cell observations (from the VM lane's probe records
and the oracle's per-task metrics) and returns each task's admission status, the instrument
checks and the K0 verdict. It contains no threshold that is not stated in the registration.

Admission (intention to treat: only failures no agent could get past exclude a task), read in
each admission cell (E, A, ER, AR, PL) against E:

  A1 setup: the cell was observed (a probed slot); a cell whose every attempt failed in the
     task's own setup fails A1; a cell lost to infrastructure on every attempt is unobserved;
  A2 window title: every strict ``activate_window`` target of the task's postconfig that E's
     post-setup window list contains is in the cell's list;
  A3 save: every file the checker reads that E's postconfig rewrote, the cell's rewrote;
  A4(i) do-nothing control: the checker's verdict on the post-setup state equals E's;
  A4(ii) passing-side control: the task's gold, saved through its own postconfig, passes in E
     and in every admission cell. A task whose gold does not exist or does not pass in E has
     no passing-side control: it is ``runnable`` (Phase 1 runs it; the secondary frame
     analyses it), not ``admitted``; a task whose gold passes in E and fails in a cell is
     excluded;
  C1: the three tasks whose checker reads ``registrymodifications.xcu`` enter only if P0.10
     passes for them.

Instrument checks (global): I1-doc (the synthetic document plant detected by O5 on every task
with an ER render, and the in-application document plant PD detected on each of the 15 dev tasks
where the S2 v3 pilot showed it on screen), I2 (E against S), I5 (AD against AR) and I6 (E
against E2) each within tol6 on at least 95% of tasks. K0 passes when at least 62 tasks are
admitted and these hold. Reported, not gating: I3 and I4 (structure and order under the text
switch, which a shipped translation can itself change) and the descriptors' validity (the O3
and O2 synthetic plants detected on at least 90% of tasks each).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

ADMISSION_CELLS = ("E", "A", "ER", "AR", "PL")
K_MIN = 62
SHARE = 0.95
DESCRIPTOR_SHARE = 0.90
TOL_FLOOR_PX = 50
SHELL_ROWS = 32  # the GNOME top bar: masked in every pixel comparison (held fixed, not LibreOffice)
C1_TASKS = ("0f84bef9", "2cd43775", "f178a4a9")
# Dev tasks whose planted document change was on screen in the S2 v3 pilot (oracle-1132: O5
# flagged PD on these 15; on 2b94c692 and bf4e9888 the changed run is off screen). The plant does
# not depend on the interface language, so the same 15 are the PD controls here.
PD_VISIBLE_DEV = (
    "01b269ae", "0e47de2a", "12382c62", "347ef137", "4172ea6e", "4ed5abd0", "5cfb9197",
    "6a33f9b9", "6e99a1ad", "936321ce", "ac9bb6cb", "af23762e", "d681960f", "e4ef0baf",
    "e528b65e",
)  # fmt: skip


def tolerance(aa_dev_diff_pixels: Iterable[int]) -> int:
    """tol5 = tol6 = max(50 px, 2 x the second-largest masked A/A count over the dev tasks)."""
    counts = sorted((int(x) for x in aa_dev_diff_pixels), reverse=True)
    second = counts[1] if len(counts) > 1 else (counts[0] if counts else 0)
    return max(TOL_FLOOR_PX, 2 * second)


def admit(task: Mapping[str, Any]) -> dict[str, Any]:
    """One task's admission status: ``admitted``, ``runnable`` or ``excluded``, with reasons.

    ``task``: ``task_id``; ``strict_titles`` (the postconfig's strict activate_window targets);
    ``p010_pass`` (C1 tasks only: True, False or None when not run); ``cells``: per admission
    cell ``observed`` (bool), ``setup_failed`` (bool), ``titles`` (list), ``rewritten``
    ({path: bool}), ``donothing`` ("pass", "fail", "error" or None) and ``gold`` ("pass",
    "fail", "error" or None when the task has no gold or it was not run)."""
    cells = task.get("cells") or {}
    reasons: list[str] = []
    for c in ADMISSION_CELLS:
        cell = cells.get(c) or {}
        if not cell.get("observed"):
            reasons.append(f"A1:{c}:setup_failed" if cell.get("setup_failed")
                           else f"unobserved:{c}")  # fmt: skip
    if reasons:
        return {"task_id": task["task_id"], "status": "excluded", "reasons": reasons}
    e = cells["E"]
    for title in task.get("strict_titles") or []:
        if title in (e.get("titles") or []):
            for c in ADMISSION_CELLS[1:]:
                if title not in (cells[c].get("titles") or []):
                    reasons.append(f"A2:{c}")
    for path, done in sorted((e.get("rewritten") or {}).items()):
        if done:
            for c in ADMISSION_CELLS[1:]:
                if not (cells[c].get("rewritten") or {}).get(path):
                    reasons.append(f"A3:{c}:{path}")
    for c in ADMISSION_CELLS[1:]:
        if cells[c].get("donothing") != e.get("donothing"):
            reasons.append(f"A4i:{c}")
    if e.get("donothing") is None:
        reasons.append("A4i:E:no_verdict")
    if any(task["task_id"].startswith(t) for t in C1_TASKS) and task.get("p010_pass") is not True:
        reasons.append("C1:held")
    passing = e.get("gold") == "pass"
    if passing:
        for c in ADMISSION_CELLS[1:]:
            gold = cells[c].get("gold")
            if gold is None:
                reasons.append(f"unobserved_gold:{c}")
            elif gold != "pass":
                reasons.append(f"A4ii:{c}")
    if reasons:
        return {"task_id": task["task_id"], "status": "excluded", "reasons": sorted(set(reasons))}
    if not passing:
        return {"task_id": task["task_id"], "status": "runnable",
                "reasons": ["no_passing_side_control"]}  # fmt: skip
    return {"task_id": task["task_id"], "status": "admitted", "reasons": []}


def share_check(passes: Sequence[bool], bar: float = SHARE) -> dict[str, Any]:
    n = len(passes)
    k = sum(1 for p in passes if p)
    return {"n": n, "k": k, "share": (k / n) if n else None, "pass": bool(n) and k / n >= bar}


def instrument_checks(metrics: Mapping[str, Any]) -> dict[str, Any]:
    """The global checks. ``metrics``: ``o5_block_detected`` (per task with an ER render),
    ``pd_detected`` ({dev task 8-prefix: bool}), ``e_vs_s``, ``e_vs_e2``, ``ad_vs_ar`` (masked
    differing-pixel counts per task), ``aa_dev`` (masked E-vs-E2 counts on the dev tasks, for
    the tolerance), ``o1_text_pairs`` (bool per task and pair), ``o4_parents`` (bool per compared
    parent), ``o3_shift_detected`` and ``o2_swap_detected`` (bool per task)."""
    tol = tolerance(metrics.get("aa_dev") or [])
    blocks = list(metrics.get("o5_block_detected") or [])
    pd = metrics.get("pd_detected") or {}
    i1 = {
        "o5_block": {"n": len(blocks), "k": sum(blocks),
                     "pass": bool(blocks) and all(blocks)},
        "pd": {t: pd.get(t) for t in PD_VISIBLE_DEV},
    }  # fmt: skip
    i1["pass"] = i1["o5_block"]["pass"] and all(pd.get(t) is True for t in PD_VISIBLE_DEV)
    out = {
        "tol6": tol,
        "I1_doc": i1,
        "I2_e_vs_s": share_check([d <= tol for d in metrics.get("e_vs_s") or []]),
        "I3_o1_text_pairs": share_check(list(metrics.get("o1_text_pairs") or [])),
        "I4_o4_order": share_check(list(metrics.get("o4_parents") or [])),
        "I5_ad_vs_ar": share_check([d <= tol for d in metrics.get("ad_vs_ar") or []]),
        "I6_e_vs_e2": share_check([d <= tol for d in metrics.get("e_vs_e2") or []]),
    }
    out["gating"] = ["I1_doc", "I2_e_vs_s", "I5_ad_vs_ar", "I6_e_vs_e2"]
    out["reported"] = ["I3_o1_text_pairs", "I4_o4_order"]
    out["pass"] = all(out[k]["pass"] for k in out["gating"])
    o3 = share_check(list(metrics.get("o3_shift_detected") or []), DESCRIPTOR_SHARE)
    o2 = share_check(list(metrics.get("o2_swap_detected") or []), DESCRIPTOR_SHARE)
    out["descriptors"] = {"o3_shift": o3, "o2_swap": o2, "valid": o3["pass"] and o2["pass"]}
    return out


def decide(tasks: Sequence[Mapping[str, Any]], metrics: Mapping[str, Any]) -> dict[str, Any]:
    """K0: at least ``K_MIN`` admitted tasks and every instrument check."""
    rows = [admit(t) for t in tasks]
    admitted = [r["task_id"] for r in rows if r["status"] == "admitted"]
    runnable = [r["task_id"] for r in rows if r["status"] in ("admitted", "runnable")]
    checks = instrument_checks(metrics)
    k0 = len(admitted) >= K_MIN and checks["pass"]
    return {
        "K0": "PASS" if k0 else "FAIL",
        "admitted": len(admitted),
        "runnable": len(runnable),
        "K_min": K_MIN,
        "admitted_task_ids": admitted,
        "runnable_task_ids": runnable,
        "tasks": rows,
        "instrument_checks": checks,
    }
