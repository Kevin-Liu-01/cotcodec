"""The suite session after a guest-server restart (development run 622, review of 2b492cd).

OSWorld's guest server runs under a systemd unit that, when the server dies, stops every
process it launched, the probe and the XRecord tap included, and restarts it. The session
relaunched only the probe, so every later trial of the session lost its tap window. These
tests drive ``suite.Session`` against a fake guest: after a restart the tap is relaunched
into a new file and each tap's records are checked against its own keymap.
"""

from __future__ import annotations

import json
from typing import Any

from harness.q2.vm import suite
from harness.q2.vm.guest import xrecord_tap as tap

KEYBOARD = tap.MAPPING_KEYBOARD


class FakeGuest:
    """Just enough of ``GuestClient`` for ``Session.start``, ``post`` and ``stop``."""

    def __init__(self) -> None:
        self.files: dict[str, list[str]] = {}
        self.alive: set[int] = set()
        self.next_pid = 1000
        self.tap_pids: dict[str, int] = {}
        self.probe_alive = False
        self.launches: list[str] = []

    # --- the server ------------------------------------------------------------------------
    def restart(self) -> None:
        """systemd: every process the server launched stops; the server comes back."""
        self.alive.clear()
        self.probe_alive = False

    def _spawn_tap(self, path: str) -> None:
        self.next_pid += 1
        pid = self.next_pid
        self.alive.add(pid)
        self.tap_pids[path] = pid
        ready = {"kind": "ready", "pid": pid, "min_keycode": 8, "led_mask": 0, "keymap": [[0]]}
        self.files[path] = [json.dumps(ready)]

    # --- GuestClient API -------------------------------------------------------------------
    def launch_script(self, source: str, args: list[str]) -> tuple[int, str]:
        if source == suite.guest_source("xrecord_tap.py"):
            self.launches.append(f"tap:{args[0]}")
            self._spawn_tap(args[0])
        elif source == suite.guest_source("probe.py"):
            self.launches.append("probe")
            self.probe_alive = True
        return 200, "launched"

    def execute(self, argv: list[str], timeout: float = 130.0) -> dict[str, Any]:
        if argv[:2] == ["test", "-d"]:
            pid = int(argv[2].rsplit("/", 1)[1])
            return {"returncode": 0 if pid in self.alive else 1}
        if argv[0] == "cat" and argv[1].endswith("ready.json"):
            ready = {"reserved_keycode": 250, "led_mask": 0}
            return {"returncode": 0 if self.probe_alive else 1, "output": json.dumps(ready)}
        return {"returncode": 0, "output": ""}

    def _tap_block(self, path: str, offset: int) -> dict[str, Any]:
        lines = self.files.get(path, [])
        return {"offset": len(lines), "text": "".join(line + "\n" for line in lines[offset:])}

    def run_script(self, source: str, args: list[str]) -> dict[str, Any]:
        if "f.seek(o)" in source:  # Session.read_tap's reader (offsets count lines here)
            return self._tap_block(args[0], int(args[1]))
        if source.startswith("import socket,sys"):  # Session.stop's quit message to the probe
            return {"ok": True}
        mode, config = args[0], json.loads(args[1])
        check = {"probe": {"absent": not self.probe_alive}}
        if mode == "warmup":
            return {"keycode": 255}
        if mode == "check":
            return {"check": check, "violations": []}
        if mode == "post":
            out = {"end": {"ok": self.probe_alive}, "check": check, "violations": []}
            out["tap"] = self._tap_block(config["tap_path"], int(config["tap_offset"]))
            return out
        raise AssertionError(mode)


def _session() -> tuple[suite.Session, FakeGuest]:
    guest = FakeGuest()
    session = suite.Session(guest, {"token": "t1", "park": [1234, 777], "tap_duration_s": 60})
    started = session.start()
    assert "error" not in started, started
    return session, guest


def test_a_guest_server_restart_relaunches_the_tap_and_the_probe():
    session, guest = _session()
    first_tap = session.tap_path
    guest.restart()
    out = session.post(3, [])
    assert out["probe_absent"] and "relaunch" in out
    assert out["tap_relaunch"]["pid"] == guest.tap_pids[session.tap_path]
    assert session.tap_path != first_tap and session.tap_path.endswith(".1.jsonl")
    assert session.tap_relaunches == 1 and session.relaunches == 1
    # The tap is relaunched before the probe, so it records the probe's delimiter keycode.
    assert guest.launches[-2:] == [f"tap:{session.tap_path}", "probe"]
    # Its ready record joins the session's stream; stop() reads the new file.
    assert sum(1 for r in session.tap_records if r.get("kind") == "ready") == 2
    guest.files[session.tap_path].append(json.dumps({"kind": "stop"}))
    stopped = session.stop()
    assert stopped["tap_relaunches"] == 1 and stopped["mapping_check"]["segments"] == 2


def test_a_closed_probe_window_alone_does_not_relaunch_the_tap():
    """chord_alt_f4 closes the probe on purpose; the tap still runs."""
    session, guest = _session()
    guest.probe_alive = False
    out = session.post(5, ["closes_window"])
    assert "relaunch" in out and "tap_relaunch" not in out
    assert session.tap_relaunches == 0 and session.tap_path.endswith("t1.jsonl")


def _ready(keycode_row: list[int]) -> dict[str, Any]:
    return {"kind": "ready", "pid": 1, "min_keycode": 250, "keymap": [keycode_row]}


def test_each_tap_segment_is_checked_against_its_own_keymap():
    """A keycode remapped while no tap ran is in the second tap's keymap, not the first's."""
    eacute = 0xE9
    notify = {
        "kind": "mapping_notify",
        "request": KEYBOARD,
        "first_keycode": 250,
        "count": 1,
        "rows": [[eacute, eacute]],
    }
    records = [_ready([0x61, 0x41]), _ready([eacute, eacute]), notify]
    whole = tap.mapping_check(records)
    assert not whole["ok"] and whole["unverified"]
    split = suite.segment_check(records)
    assert split["ok"] and split["segments"] == 2 and split["benign_unexplained"] == 1
    # One segment is exactly mapping_check.
    single = suite.segment_check(records[1:])
    assert single == dict(tap.mapping_check(records[1:]), segments=1)


def test_a_restart_between_entries_is_charged_to_the_next_entry():
    """The pre guard cannot run while the server restarts; the last pid seen stands in."""
    from harness.q2.vm.suite import observation

    end = {"ok": True, "events": [], "text": "", "seq": 4, "crc": 0}
    trial = {"pre": {"error": "refused"}, "server_before": 101, "post": {"server_pid": 202,
             "end": end}}  # fmt: skip
    infra = observation(trial, [], {"unverified": []})["infra"]
    assert "guest_server_restart" in infra and "guard_script" in infra
    same = dict(trial, post={"server_pid": 101, "end": end})
    assert "guest_server_restart" not in observation(same, [], {"unverified": []})["infra"]
