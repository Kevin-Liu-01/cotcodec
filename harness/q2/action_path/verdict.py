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

A key event's modifier state is compared only where the XRecord tap observed
it (decisions D43 and D45, ``modifier_state_observable``): on the tap's
channel, a key event recorded without the lock bit the entry guard guarantees
(Mod2), after a key press recorded with Mod2 in the same window, was recorded
while the X server held it queued under a synchronous grab, before it
computed the event's state, so that event is judged on its kind, keycode
(through the keysym the tap resolves from it) and order only. A key event
without Mod2 that no such press precedes in its window is judged on its state
as recorded, as is every other event and every event on the probe's channel.
Standard library only.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from harness.q2.action_path.ir import CANONICAL_NAME

STATE_BITS = (("Shift", 1), ("Control", 4), ("Mod1", 8), ("Mod4", 64))
KEY_KINDS = ("KeyPress", "KeyRelease")
BUTTON_KINDS = ("ButtonPress", "ButtonRelease")
# Decision D43. The lock bit the entry guard guarantees: Mod2, the modifier Num_Lock is mapped
# to. Before and after every entry the guard requires the Num Lock LED at the session baseline
# (condition b; the LED is on in every session) and Mod2 in the logical modifier state with no
# key pressed (conditions a and f; ``guest/guard.py``, ``NUMLOCK_MOD``), and no catalog entry
# presses Num_Lock. So every key event the X server has processed inside an entry carries
# Mod2 (development: 424 sessions, 519,344 tap and 517,032 probe key events; every tap key
# event without Mod2 had state 0 and came, in its own window, after the processed press, with
# Mod2, of the key that activates a GNOME Shell grab). Decision D45: an event is read without
# its state only after such a press in its window (``modifier_state_observable``).
GUARD_LOCKED_MODS = 0x10


def state_names(state: int) -> list[str]:
    return [name for name, bit in STATE_BITS if state & bit]


def carries_guard_lock_bit(event: dict[str, Any]) -> bool:
    """Whether a key event's recorded state has the bit the guard guarantees (Mod2)."""
    return int(event.get("state") or 0) & GUARD_LOCKED_MODS == GUARD_LOCKED_MODS


def modifier_state_observable(event: dict[str, Any], after_processed_press: bool) -> bool:
    """Whether the XRecord tap recorded this key event's modifier state (decisions D43, D45).

    ``after_processed_press``: a key press recorded with Mod2 comes before the event in the
    same window (the entry's XRecord stream between its delimiters).

    GNOME Shell grabs its overlay key and every keybinding with ``XIGrabModeSync``: once
    such a grab activates, the X server freezes the keyboard and queues later key events
    until the shell answers. RECORD reports a queued event when it is queued, before the
    server has computed its state, and not again when the queue is replayed, so the tap
    records it with core state 0, without the locked Mod2 that every processed event
    carries (``GUARD_LOCKED_MODS``). Its kind, keycode and position are recorded correctly;
    its modifier state is not observable on this channel.

    The rule (decision D45 narrows D43's): an event's state is read as not observed only
    when the event lacks Mod2 and a key press recorded with Mod2 comes before it in its
    window; every other event's state is judged as recorded. A press with Mod2 was
    processed by the server inside the entry, so the keyboard was not frozen when that
    press arrived; an event after it that lacks Mod2 was queued by a grab that activated
    after that press. In development every such grab was the shell's, activated
    by the entry's own press of its grab key (Super_L, or a keybinding's key with its
    modifiers held): each of the 280 key events the tap recorded without Mod2 followed that
    processed press in its own window.

    What this does and does not check. A synchronous grab already active before the
    entry's first key (any client's; an active grab needs no key press, and the guard
    cannot see one) queues every key event of the entry, the first included, so none
    follows a processed press and each is judged on its recorded state (0): it lacks the
    modifiers a chord's later events are expected to carry, so such a chord fails instead
    of passing unseen (an expectation that names no state, as R13's, is judged as it would
    be without the rule). The rule does not check that the grab which queued an event
    after a processed press was activated by the entry's own key: a synchronous grab
    another client activated between that press and the event would have the event read
    without its state too. Nor does it check why an event lacks Mod2: Num Lock unlocked
    inside the entry by a key event puts that Num_Lock event in the stream, which no
    catalog expectation contains, and a lasting change fails the post guard (b, f); by a
    client request with no key event, undone before the post guard, events processed
    after a processed press would lack Mod2 and be read without their state, and such a
    trial still passes only if every event's kind, keysym and order match. Development saw
    none of these.

    A chord whose grab key was never pressed, which includes every chord whose modifier was
    dropped before its key, is processed event by event and keeps its state. Applies to
    key events recorded by the tap; the probe receives events after the server has
    computed their state, so the judge never calls this for the probe's channel.
    """
    return carries_guard_lock_bit(event) or not after_processed_press


def _state_unread(events: list[dict[str, Any]]) -> list[bool]:
    """Per event of one tap window (any kind): whether its modifier state is not read."""
    out: list[bool] = []
    processed_press = False
    for event in events:
        key = event["kind"] in KEY_KINDS
        out.append(key and not modifier_state_observable(event, processed_press))
        if event["kind"] == "KeyPress" and carries_guard_lock_bit(event):
            processed_press = True
    return out


def state_not_observed(events: list[dict[str, Any]], recorded_by_tap: bool) -> list[int]:
    """Indices (among the key events) of the events whose modifier state is not judged.

    ``events`` is one window of the channel, in recorded order (decisions D43 and D45,
    ``modifier_state_observable``); on the probe's channel the list is empty.
    """
    if not recorded_by_tap:
        return []
    unread = [u for e, u in zip(events, _state_unread(events), strict=True)
              if e["kind"] in KEY_KINDS]  # fmt: skip
    return [i for i, u in enumerate(unread) if u]


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


def _event_matches(
    expected: list[Any], observed: dict[str, Any], tolerance: int, state_read: bool = True
) -> bool:
    kind = expected[0]
    if observed["kind"] != kind:
        return False
    if kind in KEY_KINDS:
        if keysym_name(observed.get("keysym0")) != expected[1]:
            return False
        if len(expected) == 3 and state_read:
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
    recorded_by_tap: bool = False,
) -> tuple[bool, list[int]]:
    """Exact ordered (or multiset) match; returns the observed index for each expected event.

    ``recorded_by_tap``: the events are the XRecord tap's, so a key event's modifier state
    is compared only where it was observed (decisions D43 and D45,
    ``modifier_state_observable``). ``observed`` holds every key event of one window in
    recorded order (``judge_events`` passes them so), which is what the rule reads.
    """
    if len(expected) != len(observed):
        return False, []
    unread = _state_unread(observed) if recorded_by_tap else [False] * len(observed)

    def matches(e: list[Any], i: int) -> bool:
        return _event_matches(e, observed[i], tolerance, not unread[i])

    if not multiset:
        ok = all(matches(e, i) for i, e in enumerate(expected))
        return ok, list(range(len(observed))) if ok else []
    free = list(range(len(observed)))
    mapping = []
    for event in expected:
        hit = next((i for i in free if matches(event, i)), None)
        if hit is None:
            return False, []
        free.remove(hit)
        mapping.append(hit)
    return True, mapping


def rdev_matches(
    events: list[dict[str, Any]], reference: list[list[Any]], recorded_by_tap: bool
) -> bool:
    """The channel's key events equal an R-dev reference ([kind, keysym, state names] each).

    Kind, keysym at index 0 (resolved from the recorded keycode) and order always; the
    modifier state wherever it was observed (decisions D43 and D45: on the tap's channel,
    not for a key event recorded without ``GUARD_LOCKED_MODS`` after a key press recorded
    with it in the same window). ``events`` is one window in recorded order. Without the
    tap's exception this is ``project(events) == reference``.
    """
    unread = _state_unread(events) if recorded_by_tap else [False] * len(events)
    keys = [(e, u) for e, u in zip(events, unread, strict=True) if e["kind"] in KEY_KINDS]
    if len(keys) != len(reference):
        return False
    for (event, state_unread), expected in zip(keys, reference, strict=True):
        if event["kind"] != expected[0] or keysym_name(event.get("keysym0")) != expected[1]:
            return False
        if state_unread:
            continue
        if state_names(int(event.get("state") or 0)) != list(expected[2]):
            return False
    return True


def judge_events(
    expect: dict[str, Any],
    events: list[dict[str, Any]],
    end_pointer: list[int] | None,
    recorded_by_tap: bool = False,
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
        ok, mapping = match_events(
            wanted, relevant, tolerance, expect.get("order") == "multiset", recorded_by_tap
        )
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
    (list of infrastructure failure types), ``retried`` (observations a retry
    delivered; reported, never a failure), ``errors`` (executor or harness errors),
    ``terminal`` (None, "success" or "failure").
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
    # Decisions D43 and D45: on the tap's channel (raw-only cells) a key event recorded
    # without the guard's lock bit after a key press recorded with it in the same window is
    # judged without its modifier state; every other event, and the probe's channel, as before.
    unobserved = state_not_observed(channel, recorded_by_tap=not app)
    if expect.get("oracle") == "rdev":
        reference = expect.get("events")
        if reference is None:
            reasons.append("no R-dev reference (self-specified oracle)")
        elif not rdev_matches(channel, reference, recorded_by_tap=not app):
            note = f" (state not observed at key events {unobserved})" if unobserved else ""
            reasons.append(f"R-dev projection differs: {project(channel)} != {reference}{note}")
    elif "events" in expect or "min_motion_events" in expect or "final_pointer" in expect:
        reasons += judge_events(expect, channel, obs.get("end_pointer"), recorded_by_tap=not app)
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
    return {
        "pass": not reasons,
        "reasons": reasons,
        "infra": sorted(set(infra)),
        "retried": sorted(obs.get("retried") or []),
        # Reported, never a failure (decisions D43 and D45): the judged channel's key events
        # whose modifier state the tap did not observe, by index among its key events.
        "state_not_observed": unobserved,
    }


def rdev_agreement(expect: dict[str, Any], tap_events: list[dict[str, Any]]) -> bool | None:
    """Validity control C4 for one trial: the tap's key events equal the R-dev reference.

    As the judge reads the tap (decisions D43 and D45): kind, keysym and order always, the
    modifier state wherever the tap observed it (``rdev_matches``).
    """
    if expect.get("oracle") != "rdev" or expect.get("events") is None:
        return None
    return rdev_matches(tap_events, expect["events"], recorded_by_tap=True)


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
