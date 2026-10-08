#!/usr/bin/env python3
"""Read-only summary of the D43 development runs (q2-action-path-v2 section 27).

For each run directory: the end state (batch record and the watcher's Slurm record), the
receipt's gates, digests and source tree, the workload (layer, fault or mutant, VMs), and per
cell the trials, the runner's PASS count, the trials whose verdict read a key event without
its state (``state_not_observed``) and every distinct failure reason. Across runs: every
guard report's violations and the modifier state it read (``mods``, condition f), the
sessions' restarts, and, for every key event a verdict read without its state, its offset
(server ms) from the press of the key that activates the shell's grab. It judges nothing;
the verdicts are the runner's (at the commit the runs name).

    python3 -B summarize.py OUT.json RUN_DIR...

Standard library only (runs on the host with the system Python).
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict

BATCH_END = re.compile(r"^driver_exit=(\d+) labelled_containers_left=(\d+)$", re.M)
KEYS = ("KeyPress", "KeyRelease")
GRAB_KEY = {"chord_super_d": 0xFFEB, "chord_alt_f4": 0xFFC1, "chord_alt_tab": 0xFF09,
            "chord_ctrl_alt_shift_r": 0x72}  # fmt: skip


def _json(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def _sha(path):
    try:
        with open(path, "rb") as handle:
            return hashlib.sha256(handle.read()).hexdigest()
    except OSError:
        return None


def _slurm(run):
    path = os.path.join(os.path.dirname(run.rstrip("/")), "slurm-state",
                        os.path.basename(run.rstrip("/")) + ".txt")  # fmt: skip
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return None
    out = {}
    for key in ("JobState", "ExitCode", "RunTime", "TRES"):
        match = re.search(key + r"=(\S+)", text)
        out[key] = match.group(1) if match else None
    return out


def _reports(data):
    """Every guard report of a session (each names the guest server that ran it)."""
    start = data.get("start") or {}
    reports = [start.get("baseline_check"), start.get("warmup")]
    for trial in data.get("trials") or []:
        reports += [trial.get("pre"), trial.get("post")]
    reports.append((data.get("stop") or {}).get("final_guard"))
    return [r for r in reports if isinstance(r, dict)]


def summarize(run, out):
    manifest = _json(os.path.join(run, "manifest.json")) or {}
    receipt = _json(os.path.join(run, "receipt.json")) or {}
    summary = receipt.get("summary") or {}
    workload = manifest.get("workload") or {}
    try:
        with open(os.path.join(run, "preflight.txt"), encoding="utf-8") as handle:
            end = BATCH_END.search(handle.read())
    except OSError:
        end = None
    cells = defaultdict(lambda: {"trials": 0, "pass": 0, "state_not_observed": 0,
                                 "reasons": Counter(), "infra": Counter()})  # fmt: skip
    c4 = Counter()
    restarts = 0
    sessions = 0
    for path in sorted(glob.glob(os.path.join(run, "cycles", "cycle-[0-9][0-9].json"))):
        data = _json(path) or {}
        sessions += 1
        ids = [r.get("server_pid") for r in _reports(data) if r.get("server_pid") is not None]
        restarts += sum(1 for a, b in zip(ids[:-1], ids[1:], strict=True) if a != b)
        start = data.get("start") or {}
        for report in (start.get("baseline_check"), start.get("warmup")):
            check = (report or {}).get("check") or {}
            if check:
                out["guard_mods"][str(check.get("mods"))] += 1
        for trial in data.get("trials") or []:
            cell = trial.get("cell")
            verdict = trial.get("verdict") or {}
            row = cells[cell]
            row["trials"] += 1
            row["pass"] += bool(verdict.get("pass") if "verdict" in trial else trial.get("pass"))
            row["state_not_observed"] += bool(verdict.get("state_not_observed"))
            if "c4" in trial and trial["c4"] is not None:
                c4[str(trial["c4"])] += 1
            for reason in verdict.get("reasons") or []:
                row["reasons"][re.sub(r"\[.*", "[...]", reason)[:120]] += 1
            for kind in verdict.get("infra") or trial.get("infra") or []:
                row["infra"][kind] += 1
            for side in ("pre", "post"):
                report = trial.get(side) or {}
                for name in ("violations", "violations_after_restore"):
                    for letter in report.get(name) or []:
                        out["guard_violations"][f"{side} {name} {letter}"] += 1
                check = report.get("check") or {}
                if check:
                    out["guard_mods"][str(check.get("mods"))] += 1
            unobserved = verdict.get("state_not_observed") or []
            if unobserved:
                keys = [r for r in trial.get("tap_window") or [] if r and r[0] in KEYS]
                grab = next((r for r in keys if r[0] == "KeyPress"
                             and r[3] == GRAB_KEY.get(cell)), None)  # fmt: skip
                for index in unobserved:
                    record = keys[index]
                    out["unobserved_events"].append({
                        "job": os.path.basename(run.rstrip("/")), "cell": cell,
                        "layer": trial.get("layer"), "kind": record[0], "keysym0": record[3],
                        "state": record[2],
                        "after_grab_ms": record[4] - grab[4] if grab else None,
                    })  # fmt: skip
    job = os.path.basename(run.rstrip("/"))
    out["runs"].append({
        "job": job,
        "campaign_id": manifest.get("campaign_id"),
        "git_sha": manifest.get("git_sha"),
        "kind": workload.get("kind"),
        "layer": workload.get("layer"),
        "fault_drop_modifier": workload.get("fault_drop_modifier"),
        "concurrency": (manifest.get("vm") or {}).get("concurrency"),
        "batch_end": {"driver_exit": int(end.group(1)), "labelled_left": int(end.group(2))}
        if end else None,
        "slurm": _slurm(run),
        "receipt_sha256": _sha(os.path.join(run, "receipt.json")),
        "manifest_sha256": _sha(os.path.join(run, "manifest.json")),
        "source_tree_sha256": receipt.get("source_tree_sha256"),
        "infra_gates_pass": summary.get("infra_gates_pass"),
        "no_gpu_all": summary.get("no_gpu_all"),
        "qcow2_unchanged": receipt.get("qcow2_unchanged"),
        "labelled_containers_left": receipt.get("labelled_containers_left"),
        "sessions": sessions,
        "server_id_changes": restarts,
        "c4": dict(c4),
        "trials": sum(c["trials"] for c in cells.values()),
        "passed": sum(c["pass"] for c in cells.values()),
        "cells": {k: {"trials": v["trials"], "pass": v["pass"],
                      "state_not_observed": v["state_not_observed"],
                      "reasons": dict(v["reasons"]), "infra": dict(v["infra"])}
                  for k, v in sorted(cells.items())},
    })  # fmt: skip


def main(argv):
    out_path, runs = argv[1], argv[2:]
    out = {"runs": [], "guard_violations": Counter(), "guard_mods": Counter(),
           "unobserved_events": []}  # fmt: skip
    for run in runs:
        summarize(run, out)
    out["guard_violations"] = dict(out["guard_violations"])
    out["guard_mods"] = dict(out["guard_mods"])
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(out, handle, indent=1, sort_keys=True)
        handle.write("\n")
    for row in out["runs"]:
        print(row["job"], row["campaign_id"], row["slurm"], row["batch_end"],
              row["infra_gates_pass"], row["qcow2_unchanged"], row["sessions"],
              f"{row['passed']}/{row['trials']}", "c4", row["c4"],
              "server id changes", row["server_id_changes"])  # fmt: skip
    print("guard mods:", out["guard_mods"], "violations:", out["guard_violations"])
    print("unobserved events:", len(out["unobserved_events"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
