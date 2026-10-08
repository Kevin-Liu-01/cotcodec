"""The suite session and guest-server restarts (run 622, the review of 2b492cd, decision D30).

OSWorld's guest server runs under a systemd unit that, when the server dies, stops every
process left in its control group and restarts it. Since decision D30 the probe and the
XRecord tap run in their own transient systemd scopes, so a restart leaves them running and
costs at most the entry it hits. These tests drive ``suite.Session`` against a fake guest:
scoped processes survive a restart, a tap or probe that stops for another reason is
relaunched (in a new scope, the tap into a new file), and the session's restarts and
accessibility calls are counted for criterion A7.
"""

from __future__ import annotations

import base64
import json
from typing import Any

import pytest

from harness.q2.vm import suite
from harness.q2.vm.guest import xrecord_tap as tap

KEYBOARD = tap.MAPPING_KEYBOARD


class FakeGuest:
    """Just enough of ``GuestClient`` for ``Session.start``, ``post`` and ``stop``."""

    def __init__(self, scope_error: str | None = None) -> None:
        self.files: dict[str, list[str]] = {}
        self.alive: set[int] = set()
        self.next_pid = 1000
        self.tap_pids: dict[str, int] = {}
        self.probe_alive = False
        self.launches: list[str] = []
        self.units: list[str] = []
        self.server_pid = 500
        self.n_restarts = 0
        self.scope_error = scope_error

    # --- the server ------------------------------------------------------------------------
    def restart(self) -> None:
        """systemd restarts the unit; processes in their own scopes keep running."""
        self.server_pid += 1
        self.n_restarts += 1

    def stop_everything(self) -> None:
        """The tap and the probe stop (as every launched process did before the scopes)."""
        self.alive.clear()
        self.probe_alive = False

    def _spawn_tap(self, path: str) -> int:
        self.next_pid += 1
        pid = self.next_pid
        self.alive.add(pid)
        self.tap_pids[path] = pid
        ready = {"kind": "ready", "pid": pid, "min_keycode": 8, "led_mask": 0, "keymap": [[0]]}
        self.files[path] = [json.dumps(ready)]
        return pid

    def _scope(self, argv: list[str]) -> dict[str, Any]:
        unit, _log, python, flag, _bootstrap, encoded, *args = argv
        assert (python, flag) == ("python3", "-c")
        source = base64.b64decode(encoded).decode("utf-8")
        self.units.append(unit)
        if self.scope_error:
            return {"pid": 1, "unit": f"{unit}.scope", "error": self.scope_error}
        if source == suite.guest_source("xrecord_tap.py"):
            self.launches.append(f"tap:{args[0]}")
            pid = self._spawn_tap(args[0])
        else:
            assert source == suite.guest_source("probe.py")
            self.launches.append("probe")
            self.probe_alive = True
            pid = 2000 + len(self.launches)
        cgroup = f"0::/user.slice/user-1000.slice/user@1000.service/app.slice/{unit}.scope"
        return {"pid": pid, "unit": f"{unit}.scope", "manager": "user", "cgroup": cgroup}

    # --- GuestClient API -------------------------------------------------------------------
    def execute(self, argv: list[str], timeout: float = 130.0) -> dict[str, Any]:
        if argv[:2] == ["test", "-d"]:
            pid = int(argv[2].rsplit("/", 1)[1])
            return {"returncode": 0 if pid in self.alive else 1}
        if argv[0] == "cat" and argv[1].endswith("ready.json"):
            ready = {"pid": 2000, "reserved_keycode": 250, "led_mask": 0}
            return {"returncode": 0 if self.probe_alive else 1, "output": json.dumps(ready)}
        if argv[0] == "cat" and argv[1].endswith("/cgroup"):
            return {"returncode": 0, "output": "0::/system.slice/osworld_server.service\n"}
        if argv[:2] == ["systemctl", "show"]:
            assert argv[-1] == "osworld_server.service"
            return {"returncode": 0, "output": f"{self.n_restarts}\n"}
        return {"returncode": 0, "output": ""}

    def _tap_block(self, path: str, offset: int) -> dict[str, Any]:
        lines = self.files.get(path, [])
        return {"offset": len(lines), "text": "".join(line + "\n" for line in lines[offset:])}

    def run_script(self, source: str, args: list[str]) -> dict[str, Any]:
        if source == suite.SCOPE_LAUNCHER:
            return self._scope(args)
        if "f.seek(o)" in source:  # Session.read_tap's reader (offsets count lines here)
            return self._tap_block(args[0], int(args[1]))
        if source.startswith("import socket,sys"):  # Session.stop's quit message to the probe
            return {"ok": True}
        mode, config = args[0], json.loads(args[1])
        check = {"probe": {"absent": not self.probe_alive}}
        if mode == "warmup":
            return {"keycode": 255, "server_pid": self.server_pid}
        if mode == "check":
            return {"check": check, "violations": [], "server_pid": self.server_pid}
        if mode == "post":
            out = {"end": {"ok": self.probe_alive}, "check": check, "violations": []}
            out["tap"] = self._tap_block(config["tap_path"], int(config["tap_offset"]))
            out["server_pid"] = self.server_pid
            return out
        raise AssertionError(mode)


def _session(guest: FakeGuest | None = None) -> tuple[suite.Session, FakeGuest]:
    guest = guest or FakeGuest()
    session = suite.Session(guest, {"token": "t1", "park": [1234, 777], "tap_duration_s": 60})
    started = session.start()
    assert "error" not in started, started
    return session, guest


def test_the_tap_and_the_probe_start_in_their_own_scopes():
    session, guest = _session()
    assert guest.units == ["q2ap-tap-t1-1", "q2ap-probe-t1-2"]
    assert session.ready["scope"]["cgroup"].endswith("/q2ap-probe-t1-2.scope")
    assert session.tap_ready["pid"] == guest.tap_pids[session.tap_path]
    # The launcher runs systemd-run --scope and waits until the process is in the scope.
    assert "--scope" in suite.SCOPE_LAUNCHER and '"--collect"' in suite.SCOPE_LAUNCHER
    assert "cgroup.endswith(target)" in suite.SCOPE_LAUNCHER


def test_the_session_records_the_servers_unit_and_restart_count():
    guest = FakeGuest()
    session = suite.Session(guest, {"token": "t1", "park": [1234, 777], "tap_duration_s": 60})
    started = session.start()
    assert started["server_unit"]["unit"] == "osworld_server.service"
    assert started["server_unit"]["n_restarts"] == 0


def test_a_scope_that_cannot_start_fails_the_session_start():
    guest = FakeGuest(scope_error="not in its scope (rc 1): Failed to start transient scope")
    session = suite.Session(guest, {"token": "t1", "park": [1234, 777], "tap_duration_s": 60})
    started = session.start()
    assert started["error"].startswith("tap launch failed: not in its scope")


def test_scoped_processes_survive_a_guest_server_restart():
    """Decision D30: a restart neither stops the probe nor the tap; nothing is relaunched."""
    session, guest = _session()
    first_tap = session.tap_path
    guest.restart()
    out = session.post(3, [])
    assert not out.get("probe_absent") and "relaunch" not in out and "tap_relaunch" not in out
    assert session.tap_path == first_tap and session.relaunches == session.tap_relaunches == 0
    assert out["server_pid"] == 501
    guest.files[session.tap_path].append(json.dumps({"kind": "stop"}))
    stopped = session.stop()
    assert stopped["mapping_check"]["segments"] == 1
    assert stopped["server_unit"]["n_restarts"] == 1


def test_a_stopped_tap_and_probe_are_relaunched_in_new_scopes():
    session, guest = _session()
    first_tap = session.tap_path
    guest.stop_everything()
    out = session.post(3, [])
    assert out["probe_absent"] and "relaunch" in out
    assert out["tap_relaunch"]["pid"] == guest.tap_pids[session.tap_path]
    assert session.tap_path != first_tap and session.tap_path.endswith(".1.jsonl")
    assert session.tap_relaunches == 1 and session.relaunches == 1
    # The tap is relaunched before the probe, so it records the probe's delimiter keycode,
    # and every launch gets a scope of its own.
    assert guest.launches[-2:] == [f"tap:{session.tap_path}", "probe"]
    assert guest.units[-2:] == ["q2ap-tap-t1-3", "q2ap-probe-t1-4"]
    assert out["tap_relaunch"]["scope"]["unit"] == "q2ap-tap-t1-3.scope"
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


def test_a_restart_inside_an_entry_is_that_entrys_only_infrastructure_failure():
    """With the probe and the tap alive, the entry a restart hits shows the restart alone."""
    from harness.q2.vm.suite import observation

    end = {"ok": True, "events": [], "text": "", "seq": 4, "crc": 0}
    trial = {"pre": {"server_pid": 101}, "server_before": 101,
             "post": {"server_pid": 202, "end": end}}  # fmt: skip
    assert observation(trial, [], {"unverified": []})["infra"] == ["guest_server_restart"]


@pytest.mark.parametrize(
    "text, unit",
    [
        ("0::/system.slice/osworld_server.service\n", "osworld_server.service"),
        ("12:pids:/system.slice/x.service\n1:name=systemd:/system.slice/x.service\n0::/\n",
         "x.service"),
        ("0::/user.slice/user-1000.slice/session-2.scope\n", None),
        ("", None),
    ],
)  # fmt: skip
def test_unit_of_cgroup(text, unit):
    assert suite.unit_of_cgroup(text) == unit


def _result(pids: list[int], n_restarts: tuple[int | None, int | None]) -> dict[str, Any]:
    """A session result whose guard reports name ``pids`` in order (2 + 2 per trial + 1)."""
    trials = []
    inner = pids[2:-1]
    for i in range(0, len(inner), 2):
        steps = [{"accessibility_attempts": [{"status": 200}]}, {"screenshot_attempts": []}]
        trials.append({"pre": {"server_pid": inner[i]}, "post": {"server_pid": inner[i + 1]},
                       "steps": steps})  # fmt: skip
    return {
        "start": {
            "baseline_check": {"server_pid": pids[0]},
            "warmup": {"server_pid": pids[1]},
            "server_unit": {"n_restarts": n_restarts[0]},
        },
        "reset_observation": {"accessibility_attempts": [{"error": "x"}, {"status": 200}]},
        "trials": trials,
        "stop": {
            "final_guard": {"server_pid": pids[-1]},
            "server_unit": {"n_restarts": n_restarts[1]},
        },  # fmt: skip
    }


def test_restarts_and_accessibility_calls_are_counted_per_session():
    quiet = _result([7, 7, 7, 7, 7, 7, 7], (0, 0))
    assert suite.server_pids(quiet) == [7] * 7 and suite.session_restarts(quiet) == 0
    # One reset observation (retried once: one call) and one step call per trial.
    assert suite.accessibility_calls(quiet) == 3
    hit = _result([7, 7, 7, 8, 8, 8, 8], (0, 1))
    assert suite.restarts(suite.server_pids(hit)) == 1 and suite.session_restarts(hit) == 1
    # Two restarts between the same two guard reports: systemd's counter sees both.
    hidden = _result([7, 7, 7, 9, 9, 9, 9], (3, 5))
    assert suite.session_restarts(hidden) == 2
    # Without the counter, the changes of id are the count.
    unread = _result([7, 7, 7, 8, 8, 9, 9], (None, 2))
    assert suite.session_restarts(unread) == 2
    screenshot_only = dict(quiet, reset_observation={"screenshot_attempts": [{}]})
    for trial in screenshot_only["trials"]:
        trial["steps"] = [{"screenshot_attempts": [{"status": 200}]}]
    assert suite.accessibility_calls(screenshot_only) == 0
