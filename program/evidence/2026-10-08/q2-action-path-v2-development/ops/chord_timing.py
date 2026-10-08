#!/usr/bin/env python3
"""Read-only summary of chord trials in q2-action-path run directories (decision D40).

For every run directory given, writes one row per run (end state, receipt gates, sessions,
trials, per-cell PASS counts) and one row per trial of a ``chord_*`` entry (any layer): the
key events of the trial's XRecord window with their offset from the first key event (server
ms) and core state, the section-5 verdict and its reasons, whether the session ran the
keyboard warm-up and how many key events the tap recorded earlier in the session, and what
the shell did: the probe's own events, whether the probe had the focus after the entry, and
whether the step's screenshot showed the probe's marker. It judges nothing; the verdicts are
the runner's.

    python3 -B chord_timing.py OUT.json RUN_DIR...

Standard library only (runs on the host with the system Python).
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys

STATE_BITS = (("Shift", 1), ("Lock", 2), ("Control", 4), ("Mod1", 8), ("Mod2", 16), ("Mod4", 64))
BATCH_END = re.compile(r"^driver_exit=(\d+) labelled_containers_left=(\d+)$", re.M)


def _json(path: str):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def _sha256(path: str) -> str | None:
    import hashlib

    try:
        with open(path, "rb") as handle:
            return hashlib.sha256(handle.read()).hexdigest()
    except OSError:
        return None


def states(value: int) -> list[str]:
    return [name for name, bit in STATE_BITS if int(value or 0) & bit]


def run_row(run: str) -> dict:
    manifest = _json(os.path.join(run, "manifest.json")) or {}
    receipt = _json(os.path.join(run, "receipt.json")) or {}
    summary = receipt.get("summary") or {}
    preflight = ""
    try:
        with open(os.path.join(run, "preflight.txt"), encoding="utf-8") as handle:
            preflight = handle.read()
    except OSError:
        pass
    end = BATCH_END.search(preflight)
    slurm = None
    state_file = os.path.join(os.path.dirname(run), "slurm-state", f"{os.path.basename(run)}.txt")
    try:
        with open(state_file, encoding="utf-8") as handle:
            text = handle.read()
        js = re.search(r"JobState=(\S+)", text)
        ec = re.search(r"ExitCode=(\S+)", text)
        rt = re.search(r"RunTime=(\S+)", text)
        slurm = {
            "state": js.group(1) if js else None,
            "exit_code": ec.group(1) if ec else None,
            "run_time": rt.group(1) if rt else None,
        }
    except OSError:
        pass
    workload = manifest.get("workload") or {}
    cells: dict[str, list[bool]] = {}
    for cycle in sorted(glob.glob(os.path.join(run, "cycles", "cycle-[0-9][0-9].json"))):
        data = _json(cycle) or {}
        for trial in data.get("trials") or []:
            cells.setdefault(trial["cell"], []).append(
                bool((trial.get("verdict") or {}).get("pass"))
            )
    return {
        "job": os.path.basename(run),
        "campaign_id": manifest.get("campaign_id"),
        "git_sha": manifest.get("git_sha"),
        "layer": workload.get("layer"),
        "seed": (manifest.get("randomness") or {}).get("seeds"),
        "concurrency": (manifest.get("vm") or {}).get("concurrency"),
        "session_trials": workload.get("session_trials"),
        "batch_end": {"driver_exit": int(end.group(1)), "labelled_left": int(end.group(2))}
        if end
        else None,
        "slurm": slurm,
        "receipt_sha256": _sha256(os.path.join(run, "receipt.json")),
        "infra_gates_pass": summary.get("infra_gates_pass"),
        "no_gpu_all": summary.get("no_gpu_all"),
        "qcow2_unchanged": receipt.get("qcow2_unchanged"),
        "labelled_containers_left": receipt.get("labelled_containers_left"),
        "leaked_volumes": summary.get("leaked_volumes"),
        "source_tree_sha256": receipt.get("source_tree_sha256"),
        "sessions_planned": workload.get("sessions"),
        "trials_planned": workload.get("trials"),
        "trials_run": sum(len(v) for v in cells.values()),
        "cells": {cell: f"{sum(v)}/{len(v)}" for cell, v in sorted(cells.items())},
    }


def chord_rows(run: str) -> list[dict]:
    out = []
    manifest = _json(os.path.join(run, "manifest.json")) or {}
    mutant = (manifest.get("workload") or {}).get("mutant")
    for cycle in sorted(glob.glob(os.path.join(run, "cycles", "cycle-[0-9][0-9].json"))):
        data = _json(cycle) or {}
        setting = data.get("setting") or (data.get("session") or {}).get("setting")
        warmup = bool((data.get("start") or {}).get("warmup"))
        keys_before = 0  # key events the tap recorded in this session's earlier trials
        for position, trial in enumerate(data.get("trials") or []):
            keys = [
                e
                for e in (trial.get("tap_window") or [])
                if e and e[0] in ("KeyPress", "KeyRelease")
            ]
            earlier, keys_before = keys_before, keys_before + len(keys)
            if not str(trial.get("cell", "")).startswith("chord_"):
                continue
            first = keys[0][-1] if keys else None
            end = (trial.get("post") or {}).get("end") or {}
            verdict = trial.get("verdict") or {}
            out.append(
                {
                    "job": os.path.basename(run),
                    "cycle": os.path.basename(cycle)[6:8],
                    "setting": setting,
                    "position": position,
                    "session_warmup": warmup,
                    "key_events_earlier_in_session": earlier,
                    "mutant": mutant,
                    "seq": trial.get("seq"),
                    "cell": trial.get("cell"),
                    "layer": trial.get("layer"),
                    "pass": verdict.get("pass"),
                    "infra": verdict.get("infra"),
                    "reasons": [r[:160] for r in verdict.get("reasons") or []],
                    "keys": [
                        [
                            e[0],
                            e[1],
                            e[2],
                            states(e[2]),
                            (e[-1] - first) if first is not None else None,
                        ]
                        for e in keys
                    ],
                    "probe_events": len(end.get("events") or []),
                    "probe_focused_after": (end.get("state") or {}).get("focused"),
                    "marker_on_screen": (trial.get("marker") or {}).get("ok"),
                    "side_effect_restoration": (trial.get("post") or {}).get(
                        "side_effect_restoration"
                    ),
                }
            )
    return out


def main(argv: list[str]) -> int:
    out_path, runs = argv[1], argv[2:]
    result = {"runs": [run_row(r) for r in runs], "chord_trials": []}
    for run in runs:
        result["chord_trials"] += chord_rows(run)
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=1, sort_keys=True)
        handle.write("\n")
    print(
        json.dumps(
            [{k: r[k] for k in ("job", "campaign_id", "trials_run")} for r in result["runs"]]
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
