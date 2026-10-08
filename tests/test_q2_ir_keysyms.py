"""Q2 action-path IR: the full X keysym table and the IR-boundary coordinate clamp."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from harness.q2.action_path import ir
from harness.q2.action_path.build_keysyms import EXPECTED_SHA256, parse
from harness.q2.action_path.ir import IRError, clamp_point, parse_action

HERE = Path(ir.__file__).resolve().parent


def test_keysym_table_is_xorgproto_2024_1_and_ascii():
    raw = (HERE / "keysyms.json").read_bytes()
    assert all(byte < 0x80 for byte in raw)
    data = json.loads(raw)
    assert data["source"]["sha256"] == EXPECTED_SHA256
    assert data["source"]["version"] == "2024.1"
    assert "The Open Group" in data["notice"]
    assert len(data["keysyms"]) == 2109
    assert ["VoidSymbol", 0xFFFFFF] not in data["keysyms"]


def test_build_keysyms_parses_defines_in_file_order():
    header = (
        "#define XK_Prior 0xff55  /* Prior, previous */\n"
        "#define XK_Page_Up 0xff55  /* deprecated alias for Prior */\n"
        "#ifdef XK_LATIN1\n#define XK_plus 0x002b\n#endif\n"
        "#define XK_VoidSymbol 0xffffff\n"
    )
    assert parse(header) == [["Prior", 0xFF55], ["Page_Up", 0xFF55], ["plus", 0x2B]]
    assert hashlib.sha256(b"x").hexdigest() != EXPECTED_SHA256


def test_hmp_referenced_names_are_canonical_with_the_same_values():
    for name, (value, _) in ir.KEYSYMS.items():
        assert ir.KEYSYM_VALUES[name] == value, name
        assert ir.CANONICAL_NAME[value] == name, name


def test_ir_accepts_any_x_keysym_and_canonicalizes_aliases():
    """Review finding: a closed table of about 80 names made 'plus' or 'KP_0' fail at the IR."""
    action = parse_action({"op": "key", "keys": ["Control_L", "plus"]})
    assert action.keys == ("Control_L", "plus")
    names = ["semicolon", "apostrophe", "bracketleft", "backslash", "grave", "Print"]
    names += ["Pause", "Num_Lock", "KP_0", "KP_Subtract", "A", "F13", "ISO_Left_Tab"]
    for name in names:
        assert parse_action({"op": "key", "keys": [name]}).keys == (name,)
    assert parse_action({"op": "key", "keys": ["Page_Up"]}).keys == ("Prior",)
    assert parse_action({"op": "key_down", "keys": ["script_switch"]}).keys == ("Mode_switch",)
    with pytest.raises(IRError, match="repeats"):
        parse_action({"op": "key", "keys": ["Prior", "Page_Up"]})
    for bad in ("kp_enter", "ctrl", "VoidSymbol", "", 65293):
        with pytest.raises(IRError, match="unknown keysym"):
            parse_action({"op": "key", "keys": [bad]})


def test_rdev_projection_names_come_from_the_full_table():
    from harness.q2.action_path import rdev

    events = [
        {"kind": "KeyPress", "keysym0": 0xFF55, "state": 0},
        {"kind": "KeyPress", "keysym0": 0x2B, "state": 1},
        {"kind": "KeyPress", "keysym0": 0x1234567, "state": 0},
    ]
    assert [p[1] for p in rdev.project(events)] == ["Prior", "plus", "0x1234567"]


def test_clamp_point_maps_the_grid_corner_onto_the_last_pixel():
    """Review finding: R14 scales (999, 999) to (1920, 1080), which the IR rejects."""
    # Both Stage-1 harnesses: int(999 * 1920 / 999) == 1920 and int(999 * 1080 / 999) == 1080.
    scaled = (int(999 * (1920 / 999)), int(999 * 1080 / 999.0))
    assert scaled == (1920, 1080)
    with pytest.raises(IRError, match="x must be"):
        parse_action({"op": "click", "x": scaled[0], "y": scaled[1]})
    x, y = clamp_point(*scaled)
    assert (x, y) == (1919, 1079)
    assert parse_action({"op": "click", "x": x, "y": y}).x == 1919
    assert clamp_point(-4, 5000) == (0, 1079)
    assert clamp_point(959.9, 540.2) == (959, 540)
    # Scaling by width/1000 (mutation operator M24) lands one or two pixels short.
    assert clamp_point(int(999 * 1920 / 1000), int(999 * 1080 / 1000)) == (1918, 1078)
