#!/usr/bin/env python3
"""Read-only scan of q2-action-path run directories for the lock bits (decision D43).

D43 has v2's judge treat the modifier state of a key event the XRecord tap recorded without
the lock bits the entry guard guarantees as unobservable. This scan establishes which bits
those are, from every session record the action-path lane wrote, and where key events lack
them:

* every session's baseline: the probe's ready record (LED mask, the modifier bit Num_Lock is
  mapped to, ``numlock_mask``, and its pointer mask), the baseline guard check and the tap's
  ready record;
* every guard check (each trial's pre and post check and any check after a restoration): the
  LED mask and the probe's pointer mask (the logical modifier state, with no key pressed);
* every key event in every trial's XRecord window (``tap_window``), in the probe's own event
  log, and in the R-dev captures' raw records (QEMU monitor input): whether its core state has
  Mod2 (0x10). An event without it is listed with its trial, cell, layer, mutant, position,
  the keys before it in the window, and whether a press of the key that activates the shell's
  grab for that cell came earlier in the window.

It judges nothing and writes one JSON file:

    python3 -B lock_bits_scan.py OUT.json RUN_DIR...

Standard library only (runs on the host with the system Python).
"""

from __future__ import annotations

import glob
import json
import os
import sys
from collections import Counter

MOD2 = 0x10
KEY_KINDS = ("KeyPress", "KeyRelease")
# The key whose press activates GNOME Shell's synchronous grab on each shell-grabbed cell
# (v2 section 26): the overlay key Super_L, and the keybindings Alt+F4, Alt+Tab and
# Ctrl+Alt+Shift+R. R13 presses Super_L alone.
GRAB_KEY = {
    "chord_super_d": 0xFFEB,
    "chord_alt_f4": 0xFFC1,
    "chord_alt_tab": 0xFF09,
    "chord_ctrl_alt_shift_r": 0x72,
    "R13": 0xFFEB,
}
NAMES = {0xFFEB: "Super_L", 0xFFC1: "F4", 0xFF09: "Tab", 0x72: "r"}


def _json(path: str):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def _mods(mask) -> int | None:
    return int(mask) & 0xFF if isinstance(mask, int) else None


def _check_row(check: dict | None) -> tuple | None:
    if not isinstance(check, dict):
        return None
    probe = check.get("probe") or {}
    return (
        check.get("led_mask"),
        _mods(probe.get("pointer_mask")),
        bool(check.get("keys")),
        bool(probe.get("absent")),
    )


def scan_suite_cycle(job: str, cycle_path: str, workload: dict, out: dict) -> None:
    data = _json(cycle_path)
    if not isinstance(data, dict):
        out["unreadable"].append(cycle_path)
        return
    start = data.get("start") or {}
    ready = start.get("probe_ready") or {}
    baseline_check = (start.get("baseline_check") or {}).get("check") or {}
    if ready:
        out["baseline"][
            json.dumps(
                {
                    "led_mask": ready.get("led_mask"),
                    "numlock_mask": ready.get("numlock_mask"),
                    "pointer_mods": _mods(ready.get("pointer_mask")),
                    "baseline_check_led": baseline_check.get("led_mask"),
                    "tap_ready_led": (start.get("tap_ready") or {}).get("led_mask"),
                },
                sort_keys=True,
            )
        ] += 1
        out["sessions"] += 1
    elif data.get("trials"):
        out["sessions_without_probe_ready"] += 1
    for trial in data.get("trials") or []:
        if not isinstance(trial, dict) or "cell" not in trial:
            continue
        out["trials"] += 1
        for side in ("pre", "post"):
            report = trial.get(side) or {}
            for name in ("check", "check_after_restore"):
                row = _check_row(report.get(name))
                if row is not None:
                    out["guard_checks"][json.dumps(list(row))] += 1
        cell = trial.get("cell")
        end = ((trial.get("post") or {}).get("end")) or {}
        for event in end.get("events") or []:
            if event and event[0] in KEY_KINDS:
                out["probe_key_events"] += 1
                if not int(event[2] or 0) & MOD2:
                    out["probe_without_mod2"].append(
                        {"job": job, "cycle": os.path.basename(cycle_path), "seq": trial.get("seq"),
                         "cell": cell, "kind": event[0], "keycode": event[1], "state": event[2]}
                    )  # fmt: skip
        window = trial.get("tap_window")
        if window is None:
            out["trials_without_tap_window"] += 1
            continue
        keys = [r for r in window if r and r[0] in KEY_KINDS]
        grab = GRAB_KEY.get(cell)
        grab_at = next((i for i, r in enumerate(keys) if r[0] == "KeyPress" and r[3] == grab), None)
        for index, record in enumerate(keys):
            out["tap_key_events"] += 1
            state = int(record[2] or 0)
            if state & MOD2:
                continue
            out["tap_without_mod2"].append(
                {
                    "job": job,
                    "cycle": os.path.basename(cycle_path)[6:8],
                    "setting": data.get("setting"),
                    "seq": trial.get("seq"),
                    "cell": cell,
                    "layer": trial.get("layer") or workload.get("layer"),
                    "mutant": workload.get("mutant"),
                    "index": index,
                    "kind": record[0],
                    "keycode": record[1],
                    "keysym0": record[3],
                    "state": state,
                    "keys_before": [[r[0], r[3]] for r in keys[:index]],
                    "after_grab_key_press": grab_at is not None and index > grab_at,
                    "pass": (trial.get("verdict") or {}).get("pass"),
                }
            )


def scan_capture_cycle(job: str, cycle_path: str, out: dict) -> None:
    data = _json(cycle_path)
    capture = (data or {}).get("capture") or {}
    base = capture.get("baseline_guard") or {}
    if base:
        out["capture_baselines"][json.dumps(base.get("led_mask"))] += 1
    for trial in capture.get("trials") or []:
        for record in trial.get("raw") or []:
            out["capture_key_events"] += 1
            if not int(record[4] or 0) & MOD2:
                out["capture_without_mod2"].append(
                    {"job": job, "id": trial.get("id"), "rep": trial.get("rep"),
                     "kind": record[0], "keycode": record[1], "state": record[4]}
                )  # fmt: skip


def main(argv: list[str]) -> int:
    out_path, runs = argv[1], argv[2:]
    out: dict = {
        "runs": [],
        "sessions": 0,
        "sessions_without_probe_ready": 0,
        "trials": 0,
        "trials_without_tap_window": 0,
        "baseline": Counter(),
        "guard_checks": Counter(),
        "tap_key_events": 0,
        "tap_without_mod2": [],
        "probe_key_events": 0,
        "probe_without_mod2": [],
        "capture_baselines": Counter(),
        "capture_key_events": 0,
        "capture_without_mod2": [],
        "unreadable": [],
    }
    for run in runs:
        manifest = _json(os.path.join(run, "manifest.json")) or {}
        workload = manifest.get("workload") or {}
        job = os.path.basename(run.rstrip("/"))
        out["runs"].append(
            {"job": job, "kind": workload.get("kind"), "layer": workload.get("layer"),
             "mutant": workload.get("mutant"), "git_sha": manifest.get("git_sha")}
        )  # fmt: skip
        for cycle in sorted(glob.glob(os.path.join(run, "cycles", "cycle-[0-9][0-9].json"))):
            if workload.get("kind") == "rdev-capture":
                scan_capture_cycle(job, cycle, out)
            elif workload.get("kind") in ("suite-development", "suite-acceptance",
                                          "inputs-validation"):  # fmt: skip
                scan_suite_cycle(job, cycle, workload, out)
    without = out["tap_without_mod2"]
    out["summary"] = {
        "tap_without_mod2_by_cell_layer": dict(
            Counter(f"{r['cell']} {r['layer']} mutant={r['mutant']}" for r in without)
        ),
        "tap_without_mod2_not_after_grab_key": [
            r for r in without if not r["after_grab_key_press"]
        ],
        "tap_without_mod2_jobs": sorted({r["job"] for r in without}, key=int),
    }
    for key in ("baseline", "guard_checks", "capture_baselines"):
        out[key] = dict(out[key])
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(out, handle, indent=1, sort_keys=True)
        handle.write("\n")
    print(json.dumps({k: out[k] for k in ("sessions", "trials", "tap_key_events",
                                           "probe_key_events", "capture_key_events")}))  # fmt: skip
    print(json.dumps({"baseline": out["baseline"], "guard_checks": out["guard_checks"]}))
    print(json.dumps(out["summary"]["tap_without_mod2_by_cell_layer"], indent=0))
    print("not after grab key:", len(out["summary"]["tap_without_mod2_not_after_grab_key"]))
    print("probe without Mod2:", len(out["probe_without_mod2"]))
    print("capture without Mod2:", len(out["capture_without_mod2"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
