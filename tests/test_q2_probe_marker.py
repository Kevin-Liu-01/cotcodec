"""Guest probe helpers, the marker block and its PNG decoder (inputs addendum components)."""

from __future__ import annotations

import pytest

from harness.q2.action_path import catalog as cat
from harness.q2.vm import marker
from harness.q2.vm.guest import probe
from harness.q2.vm.suite import tap_windows


def test_crc16_ccitt_false_check_value():
    assert probe.crc16(b"123456789") == 0x29B1
    assert probe.text_crc("") == 0xFFFF


@pytest.mark.parametrize("seq,crc", [(0, 0), (1, 0xFFFF), (59, 0x1234), (0xFFFFFF, 0xABCD)])
def test_marker_bits_round_trip(seq, crc):
    bits = probe.marker_bits(seq, crc)
    assert len(bits) == probe.MARKER_BITS
    assert probe.parse_marker_bits(bits) == (seq, crc)
    flipped = list(bits)
    flipped[20] ^= 1
    assert probe.parse_marker_bits(flipped) is None


@pytest.mark.parametrize("filt", [0, 1, 2, 3, 4])
def test_marker_decodes_from_png_with_every_filter(filt):
    cells = probe.marker_cells(37, probe.text_crc("probe ok"))
    width, height = 1600, probe.MARKER_ROWS + 6
    png = marker.encode_test_png(width, height, cells + [(0, 0, 40, 40)], filt)
    out = marker.read_marker(png)
    assert out["ok"] and out["seq"] == 37 and out["crc"] == probe.text_crc("probe ok")


def test_marker_under_a_cursor_is_unreadable_not_wrong():
    cells = probe.marker_cells(5, 0x1111)
    x0, y0 = probe.MARKER_ORIGIN
    half = (x0 + probe.CELL + 2, y0 + 2, 8, 12)  # half of white sync cell 1: samples disagree
    out = marker.read_marker(marker.encode_test_png(1500, probe.MARKER_ROWS + 2, cells + [half], 4))
    assert not out["ok"] and 1 in out["ambiguous_cells"]
    whole = (x0 + probe.CELL, y0, probe.CELL, probe.CELL)  # all of it: the sync check fails
    out = marker.read_marker(marker.encode_test_png(1500, probe.MARKER_ROWS + 2, cells + [whole], 4))
    assert not out["ok"] and out["seq"] is None


def test_marker_is_clear_of_every_catalog_point_and_the_park_point():
    data = cat.load()
    x0, y0 = probe.MARKER_ORIGIN
    x1, y1 = x0 + probe.MARKER_BITS * probe.CELL, y0 + probe.CELL
    points = {tuple(data["guard"]["park_pointer"])}
    for entry in data["entries"]:
        points |= cat.entry_points(entry)
    # The guest server pastes the cursor image (at most 64 px) at the pointer position.
    for x, y in points:
        assert not (x0 - 64 <= x < x1 and y0 - 64 <= y < y1), (x, y)


def test_select_keysym_follows_the_core_protocol_rules():
    row_a = [0x61, 0x41, 0x61, 0x41]
    assert probe.select_keysym(row_a, 0) == 0x61
    assert probe.select_keysym(row_a, probe.SHIFT) == 0x41
    assert probe.select_keysym(row_a, probe.LOCK) == 0x41
    assert probe.select_keysym([0x61], probe.SHIFT) == 0x41  # alphabetic case rule
    kp1 = [0xFF9C, 0xFFB1]  # KP_End, KP_1
    numlock = 16
    assert probe.select_keysym(kp1, numlock, numlock) == 0xFFB1
    assert probe.select_keysym(kp1, numlock | probe.SHIFT, numlock) == 0xFF9C
    assert probe.select_keysym([0x01000416, 0x01000416], probe.SHIFT) == 0x01000416


def test_apply_key_buffer_rules():
    buf: list[str] = []
    assert probe.apply_key(buf, 0x68, 0) == "h"
    assert probe.apply_key(buf, 0x0101F680, 0) == "\U0001f680"
    assert probe.apply_key(buf, 0xFF8D, 0) == "\n"  # KP_Enter
    assert probe.apply_key(buf, 0xFF09, 0) == "\t"
    assert probe.apply_key(buf, 0x61, probe.CONTROL) == ""  # a shortcut types nothing
    assert probe.apply_key(buf, 0xFE20, probe.SHIFT) == ""  # ISO_Left_Tab
    assert probe.apply_key(buf, 0xFF08, 0) == "\b"
    assert "".join(buf) == "h\U0001f680\n"
    assert probe.keysym_text(0x01000301) == "́"
    assert probe.keysym_text(0xFFAB) == "+"
    assert probe.keysym_text(0xFF1B) == ""


def test_delimiter_rows_and_tap_windows():
    assert probe.parse_delimiter(probe.delimiter_row("begin", 7)) == ("begin", 7)
    assert probe.parse_delimiter(probe.delimiter_row("end", 7)) == ("end", 7)
    assert probe.parse_delimiter([probe.RESERVE_MAGIC, probe.RESERVE_MAGIC]) == ("reserve", None)
    assert probe.parse_delimiter([0x61, 0x41]) is None
    reserved = 255

    def req(kind, seq):
        return {"kind": "mapping_request", "first_keycode": reserved,
                "rows": [probe.delimiter_row(kind, seq)]}  # fmt: skip

    motion = {"kind": "MotionNotify", "x": 1234, "y": 777}
    key = {"kind": "KeyPress", "detail": 36}
    other = {"kind": "mapping_request", "first_keycode": 200, "rows": [[0x41]]}
    records = [motion, req("begin", 0), key, other, req("end", 0), motion, req("begin", 1),
               req("end", 1)]  # fmt: skip
    windows = tap_windows(records, reserved)
    assert windows == {0: [key, other], 1: []}
