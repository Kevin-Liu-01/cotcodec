"""Q2 XRecord tap: keysyms follow keyboard-mapping changes in server order (review finding)."""

from __future__ import annotations

import json
import struct
from pathlib import Path

from harness.q2.vm import runner
from harness.q2.vm.guest import xrecord_tap as tap


def _core_event(code: int, detail: int, time: int, x: int, y: int, state: int) -> bytes:
    body = struct.pack("<BBHIIIIhhhhHBx", code, detail, 7, time, 1, 2, 0, x, y, x, y, state, 1)
    assert len(body) == 32
    return body


def _change_mapping(first: int, rows: list[list[int]], big: bool = False) -> bytes:
    per = len(rows[0])
    flat = [k for row in rows for k in row]
    if big:
        head = struct.pack("<BBHIBBH", 100, len(rows), 0, 3 + len(flat), first, per, 0)
    else:
        head = struct.pack("<BBHBBH", 100, len(rows), 2 + len(flat), first, per, 0)
    return head + struct.pack(f"<{len(flat)}I", *flat)


def test_module_imports_without_python_xlib():
    # The runner image has no python-xlib; only main() may import it.
    assert callable(tap.main)
    source = Path(tap.__file__).read_text(encoding="utf-8")
    head = source.split("def main(")[0]
    assert "from Xlib" not in head and "import Xlib" not in head


def test_decode_core_events():
    data = _core_event(2, 38, 1000, 960, 540, 4) + _core_event(5, 1, 1010, 3, 4, 0x100)
    events = tap.decode_core_events(data)
    assert events == [
        {"kind": "KeyPress", "detail": 38, "state": 4, "x": 960, "y": 540, "server_time": 1000},
        {"kind": "ButtonRelease", "detail": 1, "state": 0x100, "x": 3, "y": 4,
         "server_time": 1010},
    ]  # fmt: skip
    assert tap.decode_core_events(_core_event(12, 0, 0, 0, 0, 0)) == []  # Expose: ignored


def test_decode_change_keyboard_mapping_normal_and_big_requests():
    rows = [[0xE9, 0xC9], [0, 0]]
    assert tap.decode_change_keyboard_mapping(_change_mapping(253, rows)) == (253, rows)
    assert tap.decode_change_keyboard_mapping(_change_mapping(253, rows, big=True)) == (253, rows)
    assert tap.decode_change_keyboard_mapping(b"\x01" + bytes(11)) is None
    assert tap.decode_change_keyboard_mapping(_change_mapping(253, rows)[:12]) is None
    swapped = tap.byte_order(True)
    assert swapped != tap.byte_order(False)


def test_key_events_use_the_mapping_in_force_when_processed():
    """A spare keycode remapped after the tap started must not be read as 0x0."""
    keymap = tap.Keymap(8, [[0, 0] for _ in range(248)])
    press = tap.decode_core_events(_core_event(2, 255, 5, 0, 0, 0))[0]
    before = tap.key_record(press, keymap)
    assert before["keysym0"] == 0 and before["map_gen"] == 0
    start, rows = tap.decode_change_keyboard_mapping(_change_mapping(255, [[0xE9, 0xC9]]))
    keymap.apply(start, rows)
    after = tap.key_record(press, keymap)
    assert (after["keysym0"], after["keysym1"], after["map_gen"]) == (0xE9, 0xC9, 1)
    assert tap.key_record({"kind": "MotionNotify", "detail": 0}, keymap) == {
        "kind": "MotionNotify",
        "detail": 0,
    }


def test_mapping_check_flags_changes_without_a_recorded_request():
    ok = [
        {"kind": "mapping_request", "first_keycode": 255, "count": 1},
        {"kind": "mapping_notify", "request": 1, "first_keycode": 255, "count": 1},
        {"kind": "mapping_notify", "request": 0, "first_keycode": 0, "count": 0},
    ]
    assert tap.mapping_check(ok)["ok"] is True
    xkb = ok + [{"kind": "mapping_notify", "request": 1, "first_keycode": 8, "count": 248}]
    result = tap.mapping_check(xkb)
    assert result["ok"] is False and result["unmatched_ranges"] == [[8, 248]]


class _FakeGuest:
    """Just enough of GuestClient for runner.tap_selftest."""

    def __init__(self, records: list[dict], fixture: dict):
        self.records = records
        self.fixture = fixture

    def launch_script(self, source, args=None):
        return 200, ""

    def run_script(self, source, args=None):
        return dict(self.fixture)

    def execute(self, argv, timeout=30.0):
        if argv[0] == "cat":
            lines = "\n".join(json.dumps(r) for r in self.records)
            return {"returncode": 0, "output": lines}
        return {"returncode": 0, "output": ""}


def _selftest_records(keysyms: list[int]) -> tuple[list[dict], dict]:
    expected, records = [], [{"kind": "ready", "min_keycode": 8, "keymap": [[0] * 2] * 248}]
    for gen, keysym in enumerate([0xE9, 0x1000416, 0], start=1):
        records.append({"kind": "mapping_request", "first_keycode": 255, "count": 1})
        records.append({"kind": "mapping_notify", "request": 1, "first_keycode": 255, "count": 1})
        for kind in ("KeyPress", "KeyRelease"):
            records.append(
                {"kind": kind, "detail": 255, "keysym0": keysyms[gen - 1], "map_gen": gen}
            )
            expected.append([kind, 255, keysym])
    records.append({"kind": "stop", "map_gen": 3})
    return records, {"keycode": 255, "expected": expected}


def test_runner_selftest_passes_on_a_following_tap_and_fails_on_a_frozen_one(monkeypatch):
    monkeypatch.setattr(runner.time, "sleep", lambda _: None)
    records, fixture = _selftest_records([0xE9, 0x1000416, 0])
    result = runner.tap_selftest(_FakeGuest(records, fixture), "t")
    assert result["ok"] is True
    assert {k for _, _, k in result["frozen_keymap_would_give"]} == {0}
    stale, fixture = _selftest_records([0, 0, 0])
    assert runner.tap_selftest(_FakeGuest(stale, fixture), "t")["ok"] is False
