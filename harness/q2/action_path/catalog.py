"""Load, validate and hash the action-path catalog (``catalog.yaml``).

The catalog is written and validated before any executor exists (reviewed
plan, defect B1): expectations come from the catalog itself (pointer and text
entries) or from the independent HMP reference path (key, chord and Caps Lock
entries, ``oracle: rdev``). Nothing here imports executor code.

Entry IDs and their order are public facts (sandweave@99ba1abe,
``notes/cua-harness-evidence/fixes/full-cpu/report.json``); the actions,
coordinates, strings and expectations are this repository's own.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from harness.q2.action_path.ir import (
    CANONICAL_NAME,
    KEYSYM_VALUES,
    KEYSYMS,
    SCREEN,
    IRError,
    parse_sequence,
)
from harness.q2.action_path.vocab import entry_gating

CATALOG_PATH = Path(__file__).resolve().parent / "catalog.yaml"
SCHEMA = "cotcodec-q2-action-path-catalog-v1"

PUBLIC_GROUPS: dict[str, list[str]] = {
    "clicks": [
        "click_left_center", "click_right", "click_middle", "click_double_left",
        "click_triple_left", "click_ctrl_left", "click_shift_left", "click_alt_left",
        "click_ctrl_shift_right", "click_corner_topleft", "click_corner_bottomright",
        "press_hold_release_left", "move_only", "press_hold_release_right", "click_burst_5",
        "click_double_slow", "click_button_back", "click_button_forward",
    ],
    "drags": [
        "drag_short", "drag_long_diagonal", "drag_multipoint_l_shape", "drag_right_button",
        "drag_shift_held", "drag_slow_small", "drag_vertical", "drag_to_corner",
        "drag_ctrl_held", "drag_middle_button", "drag_alt_held",
    ],
    "keys_chords": [
        "key_enter", "key_esc", "key_tab", "key_f5", "key_arrow_up", "key_arrow_left",
        "key_home", "key_pageup", "key_pagedown", "key_delete", "chord_ctrl_c", "chord_ctrl_a",
        "chord_ctrl_shift_t", "chord_ctrl_shift_arrow", "chord_shift_tab", "chord_alt_f4",
        "chord_super_d", "key_f1", "key_f9", "key_f12", "key_insert", "key_space_chord",
        "key_end", "key_arrow_down", "key_arrow_right", "chord_ctrl_home",
        "chord_shift_arrow_left", "chord_ctrl_alt_shift_r", "chord_alt_tab", "key_kp_enter",
        "key_kp_add", "chord_shift_alone", "chord_ctrl_alone", "key_menu",
    ],
    "scrolls": [
        "scroll_down_1", "scroll_down_3", "scroll_down_10", "scroll_up_3", "scroll_left_3",
        "scroll_right_3", "scroll_ctrl_down_3", "scroll_shift_down_3",
        "scroll_at_offcenter_position", "scroll_down_25", "scroll_down_then_up_net_zero",
        "scroll_diagonal",
    ],
    "mixed": [
        "no_action_control", "click_two_positions_ordered", "click_then_type",
        "mixed_gesture_state", "seq_type_chord_type", "seq_drag_then_click", "seq_long_mixed",
        "caps_lock_roundtrip",
    ],
    "typing": [
        "type_plain", "type_shell_hostile", "type_symbols_shifted", "type_unicode_bmp",
        "type_multiline_tabs", "type_long_200", "type_emoji", "type_rtl", "type_combining",
        "type_emoji_zwj", "type_with_correction", "type_single_char", "type_spaces",
        "type_repeated_chars", "type_mixed_case", "type_digits", "type_long_500",
    ],
}  # fmt: skip
PUBLIC_IDS = [entry_id for ids in PUBLIC_GROUPS.values() for entry_id in ids]
# QEMU qcodes the HMP reference path may send (QKeyCode names used by the catalog).
QCODES = {qcode for _, qcode in KEYSYMS.values() if qcode} | {"menu", "compose"}
OBSERVABLE = ("app", "raw-only")
SIDE_EFFECTS = (
    "closes_window", "shows_desktop", "screencast", "switches_window", "hot_corner", "lock_state",
)  # fmt: skip
STATE_MASKS = ("Shift", "Control", "Mod1", "Mod4")
EXPECT_KEYS = {
    "oracle", "events", "tolerance_px", "text", "final_pointer", "button_state_includes",
    "min_gap_ms", "max_gap_ms", "min_motion_events", "max_motion_events", "motion_through", "order",
    "events_scope", "rdev_refs", "rdev_input", "intended_keysyms", "caps_lock_final",
}  # fmt: skip


class CatalogError(ValueError):
    """The catalog is malformed or inconsistent."""


def load(path: Path = CATALOG_PATH) -> dict[str, Any]:
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise CatalogError("catalog must be a mapping")
    return data


def sha256(path: Path = CATALOG_PATH) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def apply_buffer_rules(actions: list[dict[str, Any]]) -> str:
    """The text the probe buffer should gain, from the catalog's own buffer rules."""
    buffer: list[str] = []
    for action in actions:
        if action["op"] == "type":
            buffer.extend(action["text"])
        elif action["op"] == "key" and len(action["keys"]) == 1:
            key = action["keys"][0]
            if key in ("Return", "KP_Enter"):
                buffer.append("\n")
            elif key == "Tab":
                buffer.append("\t")
            elif key == "BackSpace" and buffer:
                buffer.pop()
    return "".join(buffer)


def _is_canonical_keysym(name: Any) -> bool:
    return isinstance(name, str) and CANONICAL_NAME.get(KEYSYM_VALUES.get(name, -1)) == name


def certified_keysyms(data: dict[str, Any], entry_ids: list[str]) -> list[str]:
    """Keysyms the suite certifies: those named by the given entries' key and modifier fields.

    The IR accepts every X keysym name; acceptance (A1-A6) only covers these.
    Stage-1 key actions naming any other keysym are uncertified and must be
    counted by the Stage-1 preregistration.
    """
    wanted = set(entry_ids)
    names: set[str] = set()
    for entry in data["entries"]:
        if entry["id"] not in wanted:
            continue
        for action in parse_sequence(entry["actions"]):
            names.update(action.keys or ())
            names.update(action.modifiers)
    return sorted(names)


def _check_point(point: Any, screen: tuple[int, int], where: str) -> None:
    if (
        not isinstance(point, list)
        or len(point) != 2
        or not all(isinstance(v, int) and not isinstance(v, bool) for v in point)
        or not (0 <= point[0] < screen[0] and 0 <= point[1] < screen[1])
    ):
        raise CatalogError(f"{where}: point {point!r} is outside the screen")


def _check_events(events: Any, screen: tuple[int, int], where: str) -> None:
    if not isinstance(events, list):
        raise CatalogError(f"{where}: events must be a list")
    for event in events:
        if not isinstance(event, list) or not event:
            raise CatalogError(f"{where}: malformed event {event!r}")
        kind = event[0]
        if kind in ("KeyPress", "KeyRelease"):
            if len(event) not in (2, 3) or not _is_canonical_keysym(event[1]):
                raise CatalogError(f"{where}: key event {event!r} needs a canonical keysym")
            if len(event) == 3 and (
                not isinstance(event[2], list) or not set(event[2]) <= set(STATE_MASKS)
            ):
                raise CatalogError(f"{where}: key event {event!r} has an unknown state mask")
        elif kind in ("ButtonPress", "ButtonRelease"):
            if len(event) != 4 or event[1] not in (1, 2, 3, 4, 5, 6, 7, 8, 9):
                raise CatalogError(f"{where}: button event {event!r} is malformed")
            _check_point(event[2:], screen, where)
        else:
            raise CatalogError(f"{where}: unknown event kind {kind!r}")


def entry_points(entry: dict[str, Any]) -> set[tuple[int, int]]:
    """Every screen point an entry's actions or expectations name."""
    points: set[tuple[int, int]] = set()
    for action in entry["actions"]:
        if "x" in action:
            points.add((action["x"], action["y"]))
        for point in action.get("path") or []:
            points.add((point[0], point[1]))
    expect = entry["expect"]
    for event in expect.get("events") or []:
        if event[0] in ("ButtonPress", "ButtonRelease"):
            points.add((event[2], event[3]))
    for point in [expect.get("final_pointer")] + list(expect.get("motion_through") or []):
        if point:
            points.add((point[0], point[1]))
    return points


def _check_guard(guard: Any, entries: list[dict[str, Any]], screen: tuple[int, int]) -> None:
    if not isinstance(guard, dict) or "park_pointer" not in guard:
        raise CatalogError("guard.park_pointer is required")
    park = guard["park_pointer"]
    _check_point(park, screen, "guard.park_pointer")
    for entry in entries:
        used = entry_points(entry)
        near = [p for p in used if abs(p[0] - park[0]) <= 2 and abs(p[1] - park[1]) <= 2]
        if near:
            raise CatalogError(f"guard.park_pointer is within 2 px of {entry['id']}'s point {near}")


def validate_entry(entry: dict[str, Any], screen: tuple[int, int]) -> dict[str, Any]:
    where = str(entry.get("id"))
    allowed = {"id", "group", "observable", "side_effects", "tags", "actions", "expect", "note"}
    if set(entry) - allowed or not {"id", "group", "actions", "expect"} <= set(entry):
        raise CatalogError(f"{where}: unexpected or missing fields")
    if entry.get("observable") not in OBSERVABLE:
        raise CatalogError(f"{where}: observable must be one of {OBSERVABLE}")
    if not set(entry.get("side_effects") or []) <= set(SIDE_EFFECTS):
        raise CatalogError(f"{where}: unknown side effect")
    try:
        actions = parse_sequence(entry["actions"], screen)
    except IRError as exc:
        raise CatalogError(f"{where}: {exc}") from exc
    expect = entry["expect"]
    if not isinstance(expect, dict) or set(expect) - EXPECT_KEYS:
        raise CatalogError(f"{where}: unknown expectation fields")
    oracle = expect.get("oracle")
    if oracle == "rdev":
        chords = expect.get("rdev_input")
        if not isinstance(chords, list) or not chords:
            raise CatalogError(f"{where}: rdev entries need rdev_input chords")
        for chord in chords:
            if not isinstance(chord, list) or not chord or not set(chord) <= QCODES:
                raise CatalogError(f"{where}: rdev_input {chord!r} has an unknown qcode")
        if expect.get("events") is not None:
            _check_events(expect["events"], screen, where)
        keysyms = expect.get("intended_keysyms") or []
        if any(not _is_canonical_keysym(k) for k in keysyms):
            raise CatalogError(f"{where}: unknown intended keysym")
    elif oracle == "catalog":
        if "events" in expect:
            _check_events(expect["events"], screen, where)
        if "text" in expect and not isinstance(expect["text"], str):
            raise CatalogError(f"{where}: text must be a string")
        if "events" not in expect and "text" not in expect:
            raise CatalogError(f"{where}: catalog oracle needs events or text")
    else:
        raise CatalogError(f"{where}: oracle must be catalog or rdev")
    for point in [expect.get("final_pointer")] + list(expect.get("motion_through") or []):
        if point is not None:
            _check_point(point, screen, where)
    if not set(expect.get("button_state_includes") or []) <= set(STATE_MASKS):
        raise CatalogError(f"{where}: unknown state mask")
    if "text" in expect and entry["group"] in ("typing", "mixed"):
        derived = apply_buffer_rules(entry["actions"])
        if derived != expect["text"]:
            raise CatalogError(f"{where}: expected text disagrees with the buffer rules")
    gating, reasons = entry_gating(actions)
    return {"id": where, "gating": gating, "non_gating_reasons": reasons}


def validate(data: dict[str, Any]) -> dict[str, Any]:
    if data.get("schema") != SCHEMA:
        raise CatalogError(f"schema must be {SCHEMA}")
    if data.get("status") not in ("draft", "frozen"):
        raise CatalogError("status must be draft or frozen")
    screen = tuple(data.get("screen") or ())
    if screen != SCREEN:
        raise CatalogError(f"screen must be {SCREEN} (recorded by the boot report)")
    entries = data.get("entries")
    if not isinstance(entries, list):
        raise CatalogError("entries must be a list")
    ids = [e.get("id") for e in entries]
    if ids != PUBLIC_IDS:
        raise CatalogError("entry IDs must be the 100 public IDs in their public order")
    for group, members in PUBLIC_GROUPS.items():
        for entry in entries:
            if entry["id"] in members and entry.get("group") != group:
                raise CatalogError(f"{entry['id']} must be in group {group}")
    results = [validate_entry(entry, screen) for entry in entries]  # type: ignore[arg-type]
    _check_guard(data.get("guard"), entries, screen)
    pending = [
        e["id"]
        for e in entries
        if e["expect"].get("oracle") == "rdev" and e["expect"].get("events") is None
    ]
    if data["status"] == "frozen" and pending:
        raise CatalogError(f"a frozen catalog cannot have pending R-dev references: {pending}")
    return {
        "entries": len(entries),
        "gating": [r["id"] for r in results if r["gating"]],
        "non_gating": {r["id"]: r["non_gating_reasons"] for r in results if not r["gating"]},
        "rdev_pending": pending,
    }


def gating_set_json(summary: dict[str, Any]) -> str:
    return json.dumps(
        {"gating": summary["gating"], "non_gating": summary["non_gating"]},
        indent=2,
        sort_keys=True,
    )
