"""Author tool that writes ``catalog.yaml``; the YAML is the frozen artifact.

Run ``python -m harness.q2.action_path.build_catalog > harness/q2/action_path/catalog.yaml``.
A test checks that this module reproduces the committed YAML byte for byte, so
the two cannot drift. Key, chord and Caps Lock expectations are not written
here: they are copied verbatim from ``rdev_reference.json`` (the HMP reference
capture) when that file holds a stable stream for the entry, and stay
``events: null`` (pending) otherwise.
"""

import json
import sys
from pathlib import Path

import yaml

REFERENCE_PATH = Path(__file__).resolve().parent / "rdev_reference.json"


def _load_reference():
    if not REFERENCE_PATH.exists():
        return {}
    data = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    return {k: v for k, v in data["entries"].items() if v.get("stable")}


REFERENCE = _load_reference()

W, H = 1920, 1080


def bp(button, x, y):
    return [["ButtonPress", button, x, y], ["ButtonRelease", button, x, y]]


def kp(*keys):
    """Expected key events for a chord: press in order, release in reverse."""
    return [["KeyPress", k] for k in keys] + [["KeyRelease", k] for k in reversed(keys)]


entries = []


def add(eid, group, actions, expect, *, observable="app", side_effects=(), tags=(), note=None):
    entry = {
        "id": eid,
        "group": group,
        "observable": observable,
        "side_effects": list(side_effects),
        "tags": list(tags),
        "actions": actions,
        "expect": expect,
    }
    if note:
        entry["note"] = note
    entries.append(entry)


def ev(events, **extra):
    out = {"oracle": "catalog", "events": events, "tolerance_px": 2}
    out.update(extra)
    return out


def click(x, y, button=1, count=1, modifiers=()):
    a = {"op": "click", "x": x, "y": y}
    if button != 1:
        a["button"] = button
    if count != 1:
        a["count"] = count
    if modifiers:
        a["modifiers"] = list(modifiers)
    return a


def held(mods, inner):
    return [["KeyPress", m] for m in mods] + inner + [["KeyRelease", m] for m in reversed(mods)]


MASK = {"Control_L": "Control", "Shift_L": "Shift", "Alt_L": "Mod1", "Super_L": "Mod4"}

# ---------------- clicks, moves, holds (18) ----------------
add("click_left_center", "clicks", [click(960, 540)], ev(bp(1, 960, 540), final_pointer=[960, 540]))
add("click_right", "clicks", [click(700, 400, button=3)], ev(bp(3, 700, 400)))
add("click_middle", "clicks", [click(1200, 400, button=2)], ev(bp(2, 1200, 400)), tags=["table20"])
add(
    "click_double_left",
    "clicks",
    [click(960, 700, count=2)],
    ev(bp(1, 960, 700) * 2, max_gap_ms=[[0, 2, 300]]),
)
add(
    "click_triple_left",
    "clicks",
    [click(800, 700, count=3)],
    ev(bp(1, 800, 700) * 3, max_gap_ms=[[0, 2, 300], [2, 4, 300]]),
    tags=["regression"],
)
for eid, mods, xy, button in (
    ("click_ctrl_left", ["Control_L"], (500, 300), 1),
    ("click_shift_left", ["Shift_L"], (1100, 300), 1),
    ("click_alt_left", ["Alt_L"], (1300, 300), 1),
    ("click_ctrl_shift_right", ["Control_L", "Shift_L"], (900, 350), 3),
):
    add(
        eid,
        "clicks",
        [click(*xy, button=button, modifiers=mods)],
        ev(held(mods, bp(button, *xy)), button_state_includes=[MASK[m] for m in mods]),
        tags=["modifier_hold", "table20"],
    )
add(
    "click_corner_topleft",
    "clicks",
    [click(0, 0)],
    ev(bp(1, 0, 0)),
    side_effects=["hot_corner"],
    tags=["edge"],
)
add(
    "click_corner_bottomright",
    "clicks",
    [click(W - 1, H - 1)],
    ev(bp(1, W - 1, H - 1)),
    tags=["edge", "regression"],
)
add(
    "press_hold_release_left",
    "clicks",
    [
        {"op": "button_down", "button": 1, "x": 600, "y": 800},
        {"op": "wait", "ms": 600},
        {"op": "button_up", "button": 1, "x": 600, "y": 800},
    ],
    ev(bp(1, 600, 800), min_gap_ms=[[0, 1, 500]]),
    tags=["hold"],
)
add(
    "move_only",
    "clicks",
    [{"op": "move", "x": 1500, "y": 900}],
    ev([], final_pointer=[1500, 900], min_motion_events=1),
)
add(
    "press_hold_release_right",
    "clicks",
    [
        {"op": "button_down", "button": 3, "x": 650, "y": 820},
        {"op": "wait", "ms": 600},
        {"op": "button_up", "button": 3, "x": 650, "y": 820},
    ],
    ev(bp(3, 650, 820), min_gap_ms=[[0, 1, 500]]),
    tags=["hold"],
)
add(
    "click_burst_5",
    "clicks",
    [click(1000, 600) for _ in range(5)],
    ev(bp(1, 1000, 600) * 5),
    tags=["timing"],
)
add(
    "click_double_slow",
    "clicks",
    [click(1000, 750), {"op": "wait", "ms": 700}, click(1000, 750)],
    ev(bp(1, 1000, 750) * 2, min_gap_ms=[[1, 2, 500]]),
    tags=["timing"],
)
add(
    "click_button_back",
    "clicks",
    [click(960, 540, button=8)],
    ev(bp(8, 960, 540)),
    tags=["extra_button"],
)
add(
    "click_button_forward",
    "clicks",
    [click(960, 540, button=9)],
    ev(bp(9, 960, 540)),
    tags=["extra_button"],
)


# ---------------- drags (11) ----------------
def drag(path, button=1, modifiers=(), duration_ms=500):
    a = {"op": "drag", "path": [list(p) for p in path], "duration_ms": duration_ms}
    if button != 1:
        a["button"] = button
    if modifiers:
        a["modifiers"] = list(modifiers)
    return a


def drag_ev(path, button=1, mods=(), **extra):
    (x0, y0), (x1, y1) = path[0], path[-1]
    inner = [["ButtonPress", button, x0, y0], ["ButtonRelease", button, x1, y1]]
    kw = {"min_motion_events": 3, "final_pointer": [x1, y1]}
    if len(path) > 2:
        kw["motion_through"] = [list(p) for p in path[1:-1]]
    if mods:
        kw["button_state_includes"] = [MASK[m] for m in mods]
    kw.update(extra)
    return ev(held(list(mods), inner), **kw)


for eid, path, button, mods, dur, tags in (
    ("drag_short", [(800, 500), (860, 540)], 1, (), 300, []),
    ("drag_long_diagonal", [(100, 100), (1800, 1000)], 1, (), 800, []),
    ("drag_multipoint_l_shape", [(400, 300), (400, 800), (1200, 800)], 1, (), 900, ["multipoint"]),
    ("drag_right_button", [(900, 300), (1100, 400)], 3, (), 500, ["extra_button"]),
    ("drag_shift_held", [(300, 600), (700, 650)], 1, ("Shift_L",), 500, ["modifier_hold"]),
    ("drag_slow_small", [(1000, 500), (1010, 505)], 1, (), 1500, ["timing"]),
    ("drag_vertical", [(1500, 200), (1500, 900)], 1, (), 600, []),
    ("drag_to_corner", [(960, 540), (W - 1, H - 1)], 1, (), 600, ["edge"]),
    ("drag_ctrl_held", [(500, 500), (800, 700)], 1, ("Control_L",), 500, ["modifier_hold"]),
    ("drag_middle_button", [(700, 700), (900, 750)], 2, (), 500, ["extra_button"]),
    ("drag_alt_held", [(1200, 600), (1400, 700)], 1, ("Alt_L",), 500, ["modifier_hold"]),
):
    add(eid, "drags", [drag(path, button, mods, dur)], drag_ev(path, button, mods), tags=tags)


# ---------------- keys and chords (34) ----------------
def rdev(keys_qcodes, keysyms, entry_id, **extra):
    ref = REFERENCE.get(entry_id)
    out = {
        "oracle": "rdev",
        "rdev_input": keys_qcodes,
        "intended_keysyms": keysyms,
        "events": ref["events"] if ref else None,
    }
    out.update(extra)
    return out


QC = {
    "Return": "ret",
    "Escape": "esc",
    "Tab": "tab",
    "Up": "up",
    "Left": "left",
    "Down": "down",
    "Right": "right",
    "Home": "home",
    "End": "end",
    "Prior": "pgup",
    "Next": "pgdn",
    "Delete": "delete",
    "Insert": "insert",
    "space": "spc",
    "Control_L": "ctrl",
    "Shift_L": "shift",
    "Alt_L": "alt",
    "Super_L": "meta_l",
    "KP_Enter": "kp_enter",
    "KP_Add": "kp_add",
    "Caps_Lock": "caps_lock",
    "Menu": "compose",
}


def qc(k):
    if k in QC:
        return QC[k]
    if k.startswith("F") and k[1:].isdigit():
        return k.lower()
    return k  # letters


def key_entry(eid, keys, observable="app", side_effects=(), tags=(), note=None):
    add(
        eid,
        "keys_chords",
        [{"op": "key", "keys": list(keys)}],
        rdev([[qc(k) for k in keys]], list(keys), eid),
        observable=observable,
        side_effects=side_effects,
        tags=tags,
        note=note,
    )


key_entry("key_enter", ["Return"])
key_entry("key_esc", ["Escape"])
key_entry("key_tab", ["Tab"])
key_entry("key_f5", ["F5"])
key_entry("key_arrow_up", ["Up"])
key_entry("key_arrow_left", ["Left"])
key_entry("key_home", ["Home"])
key_entry("key_pageup", ["Prior"])
key_entry("key_pagedown", ["Next"])
key_entry("key_delete", ["Delete"])
key_entry("chord_ctrl_c", ["Control_L", "c"], tags=["chord"])
key_entry("chord_ctrl_a", ["Control_L", "a"], tags=["chord"])
key_entry("chord_ctrl_shift_t", ["Control_L", "Shift_L", "t"], tags=["chord"])
key_entry("chord_ctrl_shift_arrow", ["Control_L", "Shift_L", "Right"], tags=["chord"])
key_entry("chord_shift_tab", ["Shift_L", "Tab"], tags=["chord"])
key_entry(
    "chord_alt_f4",
    ["Alt_L", "F4"],
    observable="raw-only",
    side_effects=["closes_window"],
    tags=["chord", "desktop_shortcut"],
)
key_entry(
    "chord_super_d",
    ["Super_L", "d"],
    observable="raw-only",
    side_effects=["shows_desktop"],
    tags=["chord", "desktop_shortcut", "regression"],
)
key_entry("key_f1", ["F1"])
key_entry("key_f9", ["F9"])
key_entry("key_f12", ["F12"])
key_entry("key_insert", ["Insert"])
key_entry("key_space_chord", ["space"], note="space sent as a key action, not as typed text")
key_entry("key_end", ["End"])
key_entry("key_arrow_down", ["Down"])
key_entry("key_arrow_right", ["Right"])
key_entry("chord_ctrl_home", ["Control_L", "Home"], tags=["chord"])
key_entry("chord_shift_arrow_left", ["Shift_L", "Left"], tags=["chord"])
key_entry(
    "chord_ctrl_alt_shift_r",
    ["Control_L", "Alt_L", "Shift_L", "r"],
    observable="raw-only",
    side_effects=["screencast"],
    tags=["chord", "desktop_shortcut"],
    note="GNOME binds this chord to its screen recorder; the guard stops a recording",
)
key_entry(
    "chord_alt_tab",
    ["Alt_L", "Tab"],
    observable="raw-only",
    side_effects=["switches_window"],
    tags=["chord", "desktop_shortcut"],
)
key_entry("key_kp_enter", ["KP_Enter"], tags=["named_key", "regression"])
key_entry("key_kp_add", ["KP_Add"], tags=["named_key"])
key_entry("chord_shift_alone", ["Shift_L"], tags=["modifier_only"])
key_entry("chord_ctrl_alone", ["Control_L"], tags=["modifier_only"])
key_entry("key_menu", ["Menu"], tags=["named_key", "regression"])


# ---------------- scrolls (12) ----------------
def scroll(x, y, wy=0, wx=0, modifiers=()):
    a = {"op": "scroll", "x": x, "y": y}
    if wy:
        a["wheel_y"] = wy
    if wx:
        a["wheel_x"] = wx
    if modifiers:
        a["modifiers"] = list(modifiers)
    return a


def wheel(x, y, wy=0, wx=0):
    out = []
    if wy:
        out += bp(5 if wy > 0 else 4, x, y) * abs(wy)
    if wx:
        out += bp(7 if wx > 0 else 6, x, y) * abs(wx)
    return out


for eid, x, y, wy, wx, mods, tags in (
    ("scroll_down_1", 960, 540, 1, 0, (), []),
    ("scroll_down_3", 960, 540, 3, 0, (), []),
    ("scroll_down_10", 960, 540, 10, 0, (), []),
    ("scroll_up_3", 960, 540, -3, 0, (), []),
    ("scroll_left_3", 960, 540, 0, -3, (), ["horizontal"]),
    ("scroll_right_3", 960, 540, 0, 3, (), ["horizontal"]),
    ("scroll_ctrl_down_3", 960, 540, 3, 0, ("Control_L",), ["modifier_hold"]),
    ("scroll_shift_down_3", 960, 540, 3, 0, ("Shift_L",), ["modifier_hold"]),
    ("scroll_at_offcenter_position", 300, 900, 2, 0, (), ["regression"]),
    ("scroll_down_25", 960, 540, 25, 0, (), ["magnitude"]),
):
    extra = {"final_pointer": [x, y]}
    if mods:
        extra["button_state_includes"] = [MASK[m] for m in mods]
    add(
        eid,
        "scrolls",
        [scroll(x, y, wy, wx, mods)],
        ev(held(list(mods), wheel(x, y, wy, wx)), **extra),
        tags=tags,
    )
add(
    "scroll_down_then_up_net_zero",
    "scrolls",
    [scroll(960, 540, 3), scroll(960, 540, -3)],
    ev(wheel(960, 540, 3) + wheel(960, 540, -3)),
)
add(
    "scroll_diagonal",
    "scrolls",
    [scroll(960, 540, 2, 2)],
    ev(wheel(960, 540, 2, 2), order="multiset"),
    tags=["horizontal"],
    note="one action on two axes; the event order across axes is not specified",
)

# ---------------- mixed sequences (8) ----------------
add("no_action_control", "mixed", [], ev([], text="", max_motion_events=0), tags=["control"])
add(
    "click_two_positions_ordered",
    "mixed",
    [click(400, 400), click(1500, 700)],
    ev(bp(1, 400, 400) + bp(1, 1500, 700)),
    tags=["regression"],
)
add(
    "click_then_type",
    "mixed",
    [click(960, 540), {"op": "type", "text": "probe ok"}],
    ev(bp(1, 960, 540), text="probe ok", events_scope="pointer"),
)
add(
    "mixed_gesture_state",
    "mixed",
    [
        {"op": "key_down", "keys": ["Shift_L"]},
        click(700, 500),
        drag([(700, 500), (900, 600)]),
        {"op": "key_up", "keys": ["Shift_L"]},
    ],
    ev(
        held(
            ["Shift_L"],
            bp(1, 700, 500) + [["ButtonPress", 1, 700, 500], ["ButtonRelease", 1, 900, 600]],
        ),
        button_state_includes=["Shift"],
    ),
    tags=["hold", "modifier_hold"],
    note="a modifier held across two pointer actions",
)
add(
    "seq_type_chord_type",
    "mixed",
    [{"op": "type", "text": "one"}, {"op": "key", "keys": ["Tab"]}, {"op": "type", "text": "two"}],
    {"oracle": "catalog", "text": "one\ttwo", "rdev_refs": ["key_tab"]},
)
add(
    "seq_drag_then_click",
    "mixed",
    [drag([(300, 300), (600, 450)]), click(1200, 500)],
    ev(
        [["ButtonPress", 1, 300, 300], ["ButtonRelease", 1, 600, 450]] + bp(1, 1200, 500),
        min_motion_events=3,
    ),
)
add(
    "seq_long_mixed",
    "mixed",
    [
        {"op": "move", "x": 200, "y": 200},
        click(200, 200),
        {"op": "type", "text": "seq 9"},
        {"op": "key", "keys": ["Return"]},
        scroll(960, 540, 2),
        drag([(1000, 300), (1100, 350)]),
        click(1300, 600, button=3),
        {"op": "key", "keys": ["Escape"]},
    ],
    ev(
        bp(1, 200, 200)
        + wheel(960, 540, 2)
        + [["ButtonPress", 1, 1000, 300], ["ButtonRelease", 1, 1100, 350]]
        + bp(3, 1300, 600),
        text="seq 9\n",
        events_scope="pointer",
        rdev_refs=["key_enter", "key_esc"],
    ),
    tags=["sequence"],
)
add(
    "caps_lock_roundtrip",
    "mixed",
    [{"op": "key", "keys": ["Caps_Lock"]}, {"op": "key", "keys": ["Caps_Lock"]}],
    rdev(
        [["caps_lock"], ["caps_lock"]],
        ["Caps_Lock", "Caps_Lock"],
        "caps_lock_roundtrip",
        caps_lock_final="off",
    ),
    side_effects=["lock_state"],
    tags=["named_key", "lock"],
)

# ---------------- typing (17) ----------------
LONG_200 = (
    "Action path check 01: the quick probe records every key; "
    "commas, periods; numbers 0123456789 and CAPS stay exact. "
)
LONG_200 = (LONG_200 * 3)[:200]
LONG_500 = (
    "Line A: verify typed text arrives in order (no drops, no doubles) "
    "-- symbols: [] {} () <> ; : ' \" / \\ | ` ~ ! @ # $ % ^ & * _ + = ? 42. "
)
LONG_500 = (LONG_500 * 5)[:500]
assert len(LONG_200) == 200 and len(LONG_500) == 500
TEXTS = [
    ("type_plain", "plain text check", []),
    (
        "type_shell_hostile",
        "$PATH `uname` $(true) 'a' \"b\" \\n; x && y || z > /dev/null < in * ? ~ #!",
        ["shell"],
    ),
    ("type_symbols_shifted", '<>?:"{}|~!@#$%^&*()_+', ["shifted"]),
    ("type_unicode_bmp", "crème brûlée, Ærø, Ωμέγα, Жук, 日本語", ["unicode"]),
    ("type_multiline_tabs", "line one\n\tindented\nline three", []),
    ("type_long_200", LONG_200, ["length"]),
    ("type_emoji", "ok \U0001f680 done \U0001f389", ["unicode", "astral"]),
    ("type_rtl", "שלום עולם مرحبا", ["unicode", "rtl"]),
    ("type_combining", "é ä ñ", ["unicode", "combining"]),
    (
        "type_emoji_zwj",
        "\U0001f469‍\U0001f4bb \U0001f468‍\U0001f469‍\U0001f467",
        ["unicode", "astral", "zwj"],
    ),
]
for eid, text, tags in TEXTS:
    add(
        eid,
        "typing",
        [{"op": "type", "text": text}],
        {"oracle": "catalog", "text": text},
        tags=tags,
    )
add(
    "type_with_correction",
    "typing",
    [
        {"op": "type", "text": "helo"},
        {"op": "key", "keys": ["BackSpace"]},
        {"op": "type", "text": "lo world"},
    ],
    {"oracle": "catalog", "text": "hello world", "rdev_refs": []},
    tags=["correction"],
    note="the probe buffer applies BackSpace as delete-last-code-point",
)
for eid, text, tags in (
    ("type_single_char", "x", []),
    ("type_spaces", "  two  spaces   three   ", ["whitespace"]),
    ("type_repeated_chars", "zzzzzzzzzz 0000000000 ..........", ["repeat"]),
    ("type_mixed_case", "MiXeD CaSe TeXt QwErTy", ["shifted"]),
    ("type_digits", "0123456789 9876543210", []),
    ("type_long_500", LONG_500, ["length"]),
):
    add(
        eid,
        "typing",
        [{"op": "type", "text": text}],
        {"oracle": "catalog", "text": text},
        tags=tags,
    )

catalog = {
    "schema": "cotcodec-q2-action-path-catalog-v1",
    "status": "draft",
    "screen": [W, H],
    "description": (
        "Independent reimplementation of a 100-entry action-path catalog. Entry IDs and "
        "group sizes are public facts from sandweave@99ba1abe report.json; every action, "
        "coordinate, string and expectation here was written for this repository."
    ),
    "probe_buffer_rules": {
        "printable": "the code points produced for a KeyPress are appended",
        "Return": "\\n",
        "KP_Enter": "\\n",
        "Tab": "\\t",
        "BackSpace": "deletes the last code point",
        "other": "keys that produce no text leave the buffer unchanged",
    },
    "event_rules": {
        "events": "ordered key and button events; motion is ignored unless a field asks for it",
        "key_event": "[KeyPress|KeyRelease, keysym name]",
        "button_event": "[ButtonPress|ButtonRelease, X button, x, y] with tolerance_px",
        "events_scope_pointer": "only button events are compared; text is compared separately",
        "button_state_includes": "every button event's state mask must include these modifiers",
        "min_gap_ms": "[i, j, ms]: server time of event j minus event i is at least ms",
        "max_gap_ms": "[i, j, ms]: server time of event j minus event i is at most ms",
        "min_motion_events": (
            "at least this many MotionNotify events in the entry; "
            "with button events, between the first and the last of them"
        ),
        "order_multiset": "events compared as a multiset",
        "rdev": "key events must equal the frozen R-dev reference stream for rdev_input",
    },
    "entries": entries,
}
assert len(entries) == 100, len(entries)


def render():
    return yaml.safe_dump(
        catalog, sort_keys=False, allow_unicode=False, width=100, default_flow_style=None
    )


if __name__ == "__main__":
    sys.stdout.write(render())
