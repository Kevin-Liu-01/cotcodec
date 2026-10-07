"""Infrastructure validation of the inputs-addendum components (no system under test).

Preregistration section 2.2: the probe, the marker, the guard and the canary
driver are validated before the inputs addendum is frozen by infrastructure
runs only: input sent through the QEMU human monitor into the probe, and the
canary's read-back with no input at all.

``probe_items`` builds the HMP trials from the R-dev plan and the L0 cells:

* every key, chord and Caps Lock entry of the R-dev plan (``rdev``), judged
  against its frozen R-dev reference on the probe's channel (``observable:
  app``) or the tap's (``raw-only``), and on the tap for agreement (C4's
  channel); side-effect entries exercise the guard's restorations;
* ``hmp_text``: letters, a Shift chord, the 102nd key, Return, Tab and a
  BackSpace into the probe's text buffer (expected ``hI <<\\n\\t``);
* ``hmp_buttons``: HMP buttons 1, 2 and 3 at the park point and one wheel
  notch each way (QEMU's absolute tablet is not moved, so the press lands on
  the park point);
* ``hmp_none``: nothing at all (zero events on both channels).

Each trial runs through the same ``Session`` pre/post guards, delimiters,
marker read and judge as an executor trial. Standard library only.
"""

from __future__ import annotations

import time
from typing import Any

from harness.q2.action_path import verdict
from harness.q2.vm import desktop
from harness.q2.vm.hmp import HmpClient, HmpError
from harness.q2.vm.marker import MarkerError, read_marker
from harness.q2.vm.suite import Session

PARK = (1234, 777)


def probe_items(plan: dict[str, Any], cells: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    items = []
    for entry in plan["entries"]:
        cell = cells[entry["id"]]
        items.append(
            {
                "id": entry["id"],
                "kind": "rdev",
                "chords": entry["chords"],
                "cell": {
                    "id": entry["id"],
                    "observable": cell["observable"],
                    "side_effects": cell["side_effects"],
                    "expect": cell["expect"],
                    "terminal": None,
                },
            }
        )
    text_chords = [
        ["h"],
        ["shift", "i"],
        ["spc"],
        ["shift", "comma"],
        ["less"],
        ["ret"],
        ["tab"],
        ["x"],
        ["backspace"],
    ]
    items.append(
        {
            "id": "hmp_text",
            "kind": "text",
            "chords": text_chords,
            "cell": {
                "id": "hmp_text",
                "observable": "app",
                "side_effects": [],
                "expect": {"oracle": "catalog", "text": "hI <<\n\t"},
                "terminal": None,
            },
        }
    )
    clicks = []
    for button in (1, 2, 3):
        clicks += [["ButtonPress", button, *PARK], ["ButtonRelease", button, *PARK]]
    clicks += [
        ["ButtonPress", 5, *PARK],
        ["ButtonRelease", 5, *PARK],
        ["ButtonPress", 4, *PARK],
        ["ButtonRelease", 4, *PARK],
    ]
    items.append(
        {
            "id": "hmp_buttons",
            "kind": "pointer",
            "calls": [
                ["mouse_button", 1],
                ["mouse_button", 0],
                ["mouse_button", 4],
                ["mouse_button", 0],
                ["mouse_button", 2],
                ["mouse_button", 0],
                ["mouse_move", 0, 0, -1],
                ["mouse_move", 0, 0, 1],
            ],
            "cell": {
                "id": "hmp_buttons",
                "observable": "app",
                "side_effects": [],
                "expect": {"oracle": "catalog", "events": clicks, "tolerance_px": 2},
                "terminal": None,
            },
        }
    )
    items.append(
        {
            "id": "hmp_none",
            "kind": "none",
            "cell": {
                "id": "hmp_none",
                "observable": "app",
                "side_effects": [],
                "control": "no_action",
                "expect": {"oracle": "catalog", "events": [], "text": "", "max_motion_events": 0},
                "terminal": None,
            },
        }
    )
    return items


def hmp_trial(session: Session, hmp: HmpClient, item: dict[str, Any], seq: int) -> dict[str, Any]:
    started = time.monotonic()
    trial: dict[str, Any] = {"seq": seq, "cell": item["id"], "layer": "HMP"}
    trial["pre"] = session.pre(seq)
    time.sleep(0.3)
    try:
        for chord in item.get("chords") or []:
            hmp.sendkey("-".join(chord), hold_ms=100)
            time.sleep(0.35)
        for call in item.get("calls") or []:
            getattr(hmp, call[0])(*call[1:])
            time.sleep(0.15)
    except (OSError, HmpError) as exc:
        trial["errors"] = [f"hmp: {exc}"]
    time.sleep(0.6)
    shot, attempts = desktop.get_screenshot(session.client)
    trial["observation_attempts"] = attempts
    trial["post"] = session.post(seq, item["cell"]["side_effects"])
    try:
        trial["marker"] = read_marker(shot) if shot else {"ok": False, "error": "no screenshot"}
    except MarkerError as exc:
        trial["marker"] = {"ok": False, "error": str(exc)}
    trial.setdefault("errors", [])
    trial["terminal"] = None
    trial["steps"] = []
    trial["timing_s"] = {"total": round(time.monotonic() - started, 4)}
    return trial


def summarize_validation(trials: list[dict[str, Any]]) -> dict[str, Any]:
    by_item: dict[str, list[dict[str, Any]]] = {}
    for trial in trials:
        by_item.setdefault(trial["cell"], []).append(trial)
    out = {}
    for item, rows in sorted(by_item.items()):
        out[item] = {
            "pass": sum(1 for r in rows if r["verdict"]["pass"]),
            "reps": len(rows),
            "c4": [r.get("c4") for r in rows],
            "marker_ok": sum(1 for r in rows if (r.get("marker") or {}).get("ok")),
            "reasons": sorted({reason for r in rows for reason in r["verdict"]["reasons"]})[:6],
        }
    passed = sum(1 for v in out.values() if v["pass"] == v["reps"])
    return {
        "items": out,
        "items_all_pass": passed,
        "items_total": len(out),
        "trials": len(trials),
        "trials_pass": sum(1 for t in trials if t["verdict"]["pass"]),
    }


def judge_probe_validation(
    session: Session, trials: list[dict[str, Any]], items: list[dict[str, Any]]
) -> dict[str, Any]:
    cells = {item["id"]: item["cell"] for item in items}
    check = session.judge_all(trials, cells)
    for trial in trials:
        trial["projection_probe"] = verdict.project(
            [
                verdict.from_probe(r)
                for r in ((trial.get("post") or {}).get("end") or {}).get("events") or []
            ]
        )
    return {"mapping_check": check, "summary": summarize_validation(trials)}
