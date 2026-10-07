"""Judge one trial of the action-path suite (preregistration sections 4.3, 5 and 6).

Pure functions over what a trial observed; no executor code is imported, and
the expectations come only from the cell (a catalog entry's ``expect`` or an R
case's frozen expectation). A trial is PASS only if every condition holds:

1. the entry guard is clean before and after it (no violation before
   restoration);
2. the event channel matches the oracle: the probe's own event log for
   ``observable: app`` cells, the XRecord stream between the entry's
   delimiters for ``raw-only`` cells;
3. for ``observable: app`` cells, the marker in the screenshot of the entry's
   last ``DesktopEnv.step`` decodes to the probe's final (sequence number,
   CRC-16 of the text buffer);
4. ``no_action_control`` records zero key, button and motion events on both
   channels;
5. for harness layers, the terminal action matches.

Infrastructure failures (an ``/execute`` or ``/screenshot`` failure, the probe
absent at a guard, a missing delimiter, a key event on a keycode range the
tap's mapping check marks unverified) fail the trial too and are reported by
type; they are never excluded (section 6.1).

Event forms: an observed event is a dict with ``kind``, ``detail`` (keycode or
button), ``state``, ``x``, ``y``, ``time`` (server ms) and, for key events,
``keysym0``. Expected key events are ``[kind, keysym name]`` or ``[kind,
keysym name, state names]``; button events ``[kind, button, x, y]``.
Standard library only.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from harness.q2.action_path.ir import CANONICAL_NAME

STATE_BITS = (("Shift", 1), ("Control", 4), ("Mod1", 8), ("Mod4", 64))
KEY_KINDS = ("KeyPress", "KeyRelease")
BUTTON_KINDS = ("ButtonPress", "ButtonRelease")


def state_names(state: int) -> list[str]:
    return [name for name, bit in STATE_BITS if state & bit]


def keysym_name(value: int | None) -> str:
    return CANONICAL_NAME.get(int(value or 0), f"0x{int(value or 0):x}")


def from_probe(record: list[Any]) -> dict[str, Any]:
    """A probe event-log record ([kind, detail, state, x, y, time, keysym0, ...]) as a dict."""
    event = {
        "kind": record[0],
        "detail": record[1],
        "state": record[2],
        "x": record[3],
        "y": record[4],
        "time": record[5],
    }
    if record[0] in KEY_KINDS:
        event["keysym0"] = record[6]
    return event


def from_tap(record: dict[str, Any]) -> dict[str, Any]:
    event = {key: record.get(key) for key in ("kind", "detail", "state", "x", "y")}
    event["time"] = record.get("server_time")
    if record.get("kind") in KEY_KINDS:
        event["keysym0"] = record.get("keysym0")
    return event


def project(events: list[dict[str, Any]]) -> list[list[Any]]:
    """The R-dev projection of key events: [kind, keysym at index 0, state names]."""
    return [
        [e["kind"], keysym_name(e.get("keysym0")), state_names(int(e.get("state") or 0))]
        for e in events
        if e["kind"] in KEY_KINDS
    ]


def _event_matches(expected: list[Any], observed: dict[str, Any], tolerance: int) -> bool:
    kind = expected[0]
    if observed["kind"] != kind:
        return False
    if kind in KEY_KINDS:
        if keysym_name(observed.get("keysym0")) != expected[1]:
            return False
        if len(expected) == 3:
            return state_names(int(observed.get("state") or 0)) == list(expected[2])
        return True
    return (
        observed["detail"] == expected[1]
        and abs(int(observed["x"]) - expected[2]) <= tolerance
        and abs(int(observed["y"]) - expected[3]) <= tolerance
    )


def match_events(
    expected: list[list[Any]],
    observed: list[dict[str, Any]],
    tolerance: int,
    multiset: bool = False,
) -> tuple[bool, list[int]]:
    """Exact ordered (or multiset) match; returns the observed index for each expected event."""
    if len(expected) != len(observed):
        return False, []
    if not multiset:
        ok = all(_event_matches(e, o, tolerance) for e, o in zip(expected, observed, strict=True))
        return ok, list(range(len(observed))) if ok else []
    free = list(range(len(observed)))
    mapping = []
    for event in expected:
        hit = next((i for i in free if _event_matches(event, observed[i], tolerance)), None)
        if hit is None:
            return False, []
        free.remove(hit)
        mapping.append(hit)
    return True, mapping


def judge_events(
    expect: dict[str, Any], events: list[dict[str, Any]], end_pointer: list[int] | None
) -> list[str]:
    """Reasons the channel's events miss a catalog-oracle or R-case expectation (empty = ok)."""
    reasons: list[str] = []
    tolerance = int(expect.get("tolerance_px", 2))
    scope = expect.get("events_scope")
    kinds = BUTTON_KINDS if scope == "pointer" else KEY_KINDS + BUTTON_KINDS
    relevant = [e for e in events if e["kind"] in kinds]
    motion = [i for i, e in enumerate(events) if e["kind"] == "MotionNotify"]
    if "events" in expect:
        wanted = [e for e in expect["events"] if e[0] in kinds]
        ok, mapping = match_events(wanted, relevant, tolerance, expect.get("order") == "multiset")
        if not ok:
            reasons.append(f"events differ: expected {wanted}, observed {_brief(relevant)}")
        else:
            for i, j, ms in expect.get("min_gap_ms") or []:
                gap = int(relevant[mapping[j]]["time"]) - int(relevant[mapping[i]]["time"])
                if gap < ms:
                    reasons.append(f"gap {i}->{j} is {gap} ms < {ms}")
            for i, j, ms in expect.get("max_gap_ms") or []:
                gap = int(relevant[mapping[j]]["time"]) - int(relevant[mapping[i]]["time"])
                if gap > ms:
                    reasons.append(f"gap {i}->{j} is {gap} ms > {ms}")
            masks = set(expect.get("button_state_includes") or [])
            for event in relevant:
                if event["kind"] in BUTTON_KINDS and not masks <= set(state_names(event["state"])):
                    reasons.append(
                        f"button event state {state_names(event['state'])} lacks {sorted(masks)}"
                    )
                    break
    if "min_motion_events" in expect:
        buttons = [i for i, e in enumerate(events) if e["kind"] in BUTTON_KINDS]
        inside = [i for i in motion if buttons[0] < i < buttons[-1]] if buttons else motion
        count = len(inside)
        if count < expect["min_motion_events"]:
            reasons.append(f"{count} motion events < {expect['min_motion_events']}")
    if "max_motion_events" in expect and len(motion) > expect["max_motion_events"]:
        reasons.append(f"{len(motion)} motion events > {expect['max_motion_events']}")
    for point in expect.get("motion_through") or []:
        if not any(
            abs(events[i]["x"] - point[0]) <= tolerance
            and abs(events[i]["y"] - point[1]) <= tolerance
            for i in motion
        ):
            reasons.append(f"no motion through {point}")
    final = expect.get("final_pointer")
    if final is not None:
        if end_pointer is None:
            reasons.append("final pointer not observed")
        elif (
            abs(end_pointer[0] - final[0]) > tolerance or abs(end_pointer[1] - final[1]) > tolerance
        ):
            reasons.append(f"final pointer {end_pointer} != {final}")
    return reasons


def _brief(events: list[dict[str, Any]]) -> list[list[Any]]:
    out = []
    for e in events[:24]:
        if e["kind"] in KEY_KINDS:
            out.append(
                [e["kind"], keysym_name(e.get("keysym0")), state_names(int(e.get("state") or 0))]
            )
        else:
            out.append([e["kind"], e["detail"], e["x"], e["y"]])
    return out


def judge(cell: dict[str, Any], obs: dict[str, Any]) -> dict[str, Any]:
    """PASS/FAIL for one trial with every reason and every infrastructure failure.

    ``obs`` keys: ``probe_events`` (dicts), ``tap_events`` (dicts), ``text``,
    ``end_pointer``, ``marker`` ({"ok", "seq", "crc"}), ``probe_final`` ([seq,
    crc]), ``guard_violations`` ({"pre": [...], "post": [...]}), ``infra``
    (list of infrastructure failure types), ``errors`` (executor or harness
    errors), ``terminal`` (None, "success" or "failure").
    """
    expect = cell["expect"]
    reasons: list[str] = []
    infra = list(obs.get("infra") or [])
    reasons += [f"error: {e}" for e in obs.get("errors") or []]
    guard = obs.get("guard_violations") or {}
    for side in ("pre", "post"):
        if guard.get(side):
            reasons.append(f"guard {side}: {''.join(guard[side])}")
    app = cell.get("observable", "app") == "app"
    channel = obs.get("probe_events") if app else obs.get("tap_events")
    if channel is None:
        infra.append("channel_missing")
        channel = []
    if expect.get("oracle") == "rdev":
        reference = expect.get("events")
        if reference is None:
            reasons.append("no R-dev reference (self-specified oracle)")
        elif project(channel) != [list(e[:2]) + [list(e[2])] for e in reference]:
            reasons.append(f"R-dev projection differs: {project(channel)} != {reference}")
    elif "events" in expect or "min_motion_events" in expect or "final_pointer" in expect:
        reasons += judge_events(expect, channel, obs.get("end_pointer"))
    if "text" in expect and app and obs.get("text") != expect["text"]:
        reasons.append(f"text {obs.get('text')!r} != {expect['text']!r}")
    if cell.get("control") == "no_action":
        for name in ("probe_events", "tap_events"):
            if obs.get(name):
                reasons.append(f"{name}: {len(obs[name])} events, expected none")
    if app:
        marker = obs.get("marker") or {}
        final = obs.get("probe_final")
        if not marker.get("ok"):
            reasons.append(
                f"marker unreadable: {marker.get('error') or marker.get('ambiguous_cells')}"
            )
        elif final is None or [marker["seq"], marker["crc"]] != list(final):
            reasons.append(f"marker {[marker['seq'], marker['crc']]} != probe final {final}")
    if cell.get("terminal") != obs.get("terminal"):
        reasons.append(f"terminal {obs.get('terminal')} != {cell.get('terminal')}")
    reasons += [f"infra: {kind}" for kind in infra]
    return {"pass": not reasons, "reasons": reasons, "infra": sorted(set(infra))}


def rdev_agreement(expect: dict[str, Any], tap_events: list[dict[str, Any]]) -> bool | None:
    """Validity control C4 for one trial: the tap projection equals the R-dev reference."""
    if expect.get("oracle") != "rdev" or expect.get("events") is None:
        return None
    return project(tap_events) == [list(e[:2]) + [list(e[2])] for e in expect["events"]]


def summarize(trials: list[dict[str, Any]]) -> dict[str, Any]:
    """Per cell: k of k PASS (PASS), mixed (FLAKY) or none (FAIL)."""
    by_cell: dict[str, list[bool]] = {}
    for trial in trials:
        by_cell.setdefault(trial["cell"], []).append(bool(trial["verdict"]["pass"]))
    out = {}
    for cell, results in sorted(by_cell.items()):
        passed = sum(results)
        status = "PASS" if passed == len(results) else "FAIL" if passed == 0 else "FLAKY"
        out[cell] = {"status": status, "passed": passed, "reps": len(results)}
    counts = Counter(v["status"] for v in out.values())
    return {"cells": out, "counts": dict(counts)}
