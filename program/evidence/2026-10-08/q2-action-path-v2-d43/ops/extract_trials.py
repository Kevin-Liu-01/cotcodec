#!/usr/bin/env python3
"""Copy selected trial records out of q2-action-path run directories (decision D43).

Writes, for every trial of the named cells in each run directory, exactly what
``harness.q2.vm.suite.observation`` reads to build the judge's input (the guard reports'
violations, server ids and the probe's end record, the steps' infrastructure types and
retries, the marker, errors and terminal action), the trial's XRecord window in the tap's
own record form (rebuilt from the compact ``tap_window`` the runner stores: keys
``[kind, keycode, state, keysym0, time]``, pointer events ``[kind, detail, state, x, y,
time]``, mapping notifies ``[kind, request, first keycode, count]``), the session's mapping
check, and the verdict and C4 value the runner recorded. Nothing is judged here; the
records let the judge be re-run on real development trials (``tests/test_q2_d43_judge.py``).

    python3 -B extract_trials.py OUT.json CELLS RUN_DIR...

CELLS is a comma-separated list of cell ids, or ``chords`` for every ``chord_*`` cell.
Standard library only (runs on the host with the system Python).
"""

from __future__ import annotations

import glob
import json
import os
import sys

KEYS = ("KeyPress", "KeyRelease")
POINTER = ("ButtonPress", "ButtonRelease", "MotionNotify")


def _json(path: str):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def tap_record(compact: list) -> dict:
    kind = compact[0]
    if kind in KEYS:
        return {"kind": kind, "detail": compact[1], "state": compact[2], "keysym0": compact[3],
                "server_time": compact[4]}  # fmt: skip
    if kind in POINTER:
        return {"kind": kind, "detail": compact[1], "state": compact[2], "x": compact[3],
                "y": compact[4], "server_time": compact[5]}  # fmt: skip
    if kind == "mapping_notify":
        # Runs before dba0580 kept the kind only (v2 inputs addendum, section 5).
        rest = list(compact[1:4]) + [None] * (4 - len(compact))
        return {"kind": kind, "request": rest[0], "first_keycode": rest[1], "count": rest[2]}
    return {"kind": kind}


def guard_report(report: dict | None) -> dict:
    report = report or {}
    out = {k: report[k] for k in ("probe_absent", "error", "server_pid", "violations")
           if k in report}  # fmt: skip
    end = report.get("end")
    if isinstance(end, dict):
        out["end"] = {k: end.get(k) for k in ("ok", "events", "text", "seq", "crc")}
        out["end"]["state"] = {k: (end.get("state") or {}).get(k) for k in ("pointer", "focused")}
    check = report.get("check")
    if isinstance(check, dict):
        out["check"] = {k: check.get(k) for k in ("keys", "buttons", "led_mask", "mods")}
    return out


def trial_row(job: str, cycle: str, data: dict, trial: dict, workload: dict) -> dict:
    steps = [
        {"infra": s.get("infra") or [], "retried": s.get("retried") or []}
        for s in trial.get("steps") or []
    ]
    record = {
        "seq": trial.get("seq"),
        "cell": trial.get("cell"),
        "layer": trial.get("layer"),
        "pre": guard_report(trial.get("pre")),
        "post": guard_report(trial.get("post")),
        "server_before": trial.get("server_before"),
        "steps": steps,
        "errors": trial.get("errors") or [],
        "terminal": trial.get("terminal"),
        "marker": trial.get("marker"),
    }
    for key in ("observation_attempts", "observation_ok"):
        if key in trial:
            record[key] = trial[key]
    check = data.get("mapping_check") or (data.get("stop") or {}).get("mapping_check") or {}
    return {
        "job": job,
        "cycle": cycle,
        "setting": data.get("setting"),
        "layer": trial.get("layer") or workload.get("layer"),
        "mutant": workload.get("mutant"),
        "fault": (data.get("fault_injection") or {}).get("drop_modifier"),
        "trial": record,
        "window": [tap_record(r) for r in trial.get("tap_window") or []]
        if trial.get("tap_window") is not None
        else None,
        "check": {"unverified": check.get("unverified") or [], "ok": check.get("ok")},
        "runner_verdict": trial.get("verdict"),
        "runner_c4": trial.get("c4"),
    }


def main(argv: list[str]) -> int:
    out_path, cells, runs = argv[1], argv[2], argv[3:]
    wanted = None if cells == "chords" else set(cells.split(","))
    rows = []
    sources = []
    for run in runs:
        manifest = _json(os.path.join(run, "manifest.json")) or {}
        workload = manifest.get("workload") or {}
        job = os.path.basename(run.rstrip("/"))
        sources.append({"job": job, "git_sha": manifest.get("git_sha"),
                        "campaign_id": manifest.get("campaign_id")})  # fmt: skip
        for path in sorted(glob.glob(os.path.join(run, "cycles", "cycle-[0-9][0-9].json"))):
            data = _json(path)
            if not isinstance(data, dict):
                continue
            for trial in data.get("trials") or []:
                cell = str(trial.get("cell", ""))
                if (wanted is None and cell.startswith("chord_")) or (wanted and cell in wanted):
                    rows.append(trial_row(job, os.path.basename(path)[6:8], data, trial, workload))
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump({"schema": "q2ap-d43-trials-v1", "sources": sources, "trials": rows}, handle,
                  indent=None, sort_keys=True, separators=(",", ":"))  # fmt: skip
        handle.write("\n")
    print(json.dumps({"trials": len(rows), "runs": len(sources)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
