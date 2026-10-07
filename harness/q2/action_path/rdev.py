"""R-dev: the independent device-level reference for key, chord and Caps Lock entries.

The reference input path is QEMU's human monitor: ``sendkey`` drives the
emulated PS/2 keyboard, so events reach the guest through its kernel, evdev
and xkb like real hardware, with no project executor code involved. The
guest's XRecord stream is recorded; the reference for an entry is the
*projection* of its key events, identical across every repetition:

    (event kind, keysym name at index 0 of the keycode, modifier names)

where modifier names are the event state restricted to Shift, Control, Mod1
and Mod4 (NumLock and Caps Lock state bits are environment, not input).

Standard library only (the runner imports it inside the GPU-less container).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from harness.q2.action_path.ir import KEYSYMS

STATE_BITS = (("Shift", 1), ("Control", 4), ("Mod1", 8), ("Mod4", 64))
KEYSYM_NAMES = {value: name for name, (value, _) in KEYSYMS.items()}
# Recovery sent after an entry (recorded in its own window, never compared).
RECOVERY: dict[str, list[list[str]]] = {
    "key_menu": [["esc"]],
    "chord_super_d": [["meta_l", "d"]],
    "chord_ctrl_alt_shift_r": [["ctrl", "alt", "shift", "r"]],
    "key_f1": [["esc"]],
}
PLAN_SCHEMA = "cotcodec-q2-rdev-plan-v1"
REFERENCE_SCHEMA = "cotcodec-q2-rdev-reference-v1"


def state_names(state: int) -> list[str]:
    return [name for name, bit in STATE_BITS if state & bit]


def project(events: list[dict[str, Any]]) -> list[list[Any]]:
    """Project raw tap records onto the reference form; non-key events are dropped."""
    out: list[list[Any]] = []
    for event in events:
        if event.get("kind") not in ("KeyPress", "KeyRelease"):
            continue
        keysym = event.get("keysym0")
        name = KEYSYM_NAMES.get(keysym, f"0x{int(keysym or 0):x}")
        out.append([event["kind"], name, state_names(int(event.get("state", 0)))])
    return out


def build_plan(catalog: dict[str, Any]) -> dict[str, Any]:
    entries = []
    for entry in catalog["entries"]:
        expect = entry["expect"]
        if expect.get("oracle") != "rdev":
            continue
        entries.append(
            {
                "id": entry["id"],
                "chords": expect["rdev_input"],
                "recovery": RECOVERY.get(entry["id"], []),
                "caps_lock": "Caps_Lock" in (expect.get("intended_keysyms") or []),
            }
        )
    return {"schema": PLAN_SCHEMA, "entries": entries}


def plan_json(plan: dict[str, Any]) -> str:
    return json.dumps(plan, indent=2, sort_keys=True) + "\n"


def plan_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def summarize_capture(capture: dict[str, Any]) -> dict[str, Any]:
    """Turn a runner capture into the reference file (stable projections only)."""
    by_entry: dict[str, list[list[list[Any]]]] = {}
    caps: dict[str, list[bool]] = {}
    guards: dict[str, list[bool]] = {}
    for trial in capture["trials"]:
        by_entry.setdefault(trial["id"], []).append(trial["projection"])
        guards.setdefault(trial["id"], []).append(bool(trial.get("guard_clean")))
        if trial.get("caps_led_ok") is not None:
            caps.setdefault(trial["id"], []).append(bool(trial["caps_led_ok"]))
    entries = {}
    for entry_id, projections in by_entry.items():
        first = projections[0]
        stable = all(p == first for p in projections) and bool(first)
        stable = stable and all(guards[entry_id]) and all(caps.get(entry_id, [True]))
        entries[entry_id] = {
            "reps": len(projections),
            "stable": stable,
            "events": first if stable else None,
            "distinct_projections": len({json.dumps(p) for p in projections}),
            "guard_clean": sum(guards[entry_id]),
            "caps_led_ok": sum(caps[entry_id]) if entry_id in caps else None,
        }
    return {
        "schema": REFERENCE_SCHEMA,
        "source": {
            "job_id": capture.get("job_id"),
            "plan_sha256": capture.get("plan_sha256"),
            "qemu": capture.get("qemu_version"),
            "boot_id": capture.get("boot_id"),
        },
        "projection": "kind, keysym at index 0, state names restricted to Shift/Control/Mod1/Mod4",
        "entries": dict(sorted(entries.items())),
    }
