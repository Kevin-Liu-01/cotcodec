"""Session engine of the action-path suite (runs in the GPU-less runner container).

A *session* is one cold-booted VM. The runner starts the XRecord tap and the
probe, records the session's guard baseline, then runs its trials in order:

    pre-guard + park + probe begin   (guest/guard.py pre: one /execute)
    the cell's actions               (one DesktopEnv.step each; see desktop.py)
    probe end + guard + restoration  (guest/guard.py post: one /execute)

and finally stops the tap and the probe. Every trial is judged with
``action_path.verdict.judge`` after the session, when the whole tap stream is
in hand (the stream is split at the probe's delimiter requests).

The tap and the probe run in their own transient systemd scope (decision D30), not
in the guest server's unit: when the server crashes, systemd restarts the unit and
stops every process in its control group (development run 622), and a scope outside
that group keeps the oracle channels running, so a restart costs at most the entry
it hits. Every guard report names the server process that ran it, so the reports'
server ids (``server_pids``) say which entry a restart hit; ``session_restarts`` counts
a session's restarts (with the unit's own restart counter) and ``accessibility_calls``
the ``/accessibility`` calls ``DesktopEnv`` made (the observation-service bound of the
preregistration, criterion A7).

Layers: ``L0-fixed`` runs a catalog cell's IR actions directly; the harness
layers (``H-OSW-fixed``, ``H-GA`` and the detection controls ``H-OSW-up``,
``H-GA-buggy``) parse each model-response turn of the cell with
``action_path.adapters`` and run the IR it yields, stopping at ``terminate``.

``hmp_trial`` drives a trial through the QEMU monitor instead of an executor:
the inputs addendum's infrastructure validation of the probe, guard, marker
and delimiters (no system under test). ``canary_trial`` runs one A6 canary
cell (prepare, launch, wait, actions, finish keys, read-back, close).

Standard library only; Python 3.10 compatible.
"""

from __future__ import annotations

import base64
import contextlib
import json
import time
from pathlib import Path
from typing import Any

from harness.q2.action_path import verdict
from harness.q2.action_path.executor import step_command
from harness.q2.action_path.ir import IRError
from harness.q2.vm import desktop
from harness.q2.vm.guest import probe as probe_mod
from harness.q2.vm.guest.xrecord_tap import mapping_check
from harness.q2.vm.guest_http import GUEST_BOOTSTRAP, GuestClient, GuestError
from harness.q2.vm.marker import MarkerError, read_marker

GUEST_DIR = Path(__file__).resolve().parent / "guest"
# Decision D30: start a long-running guest script in its own transient systemd scope.
# ``systemd-run --scope`` registers the scope, moves itself into it and then execs the
# command, so the scope's one process is the script itself; the launcher returns once that
# process's control group is the scope's (or with systemd-run's output if it exits first).
# The guest server (osworld.service, a system unit) runs as the desktop user, so the scope
# belongs to that user's manager (development run 694: the probe and the tap in
# user@1000.service/app.slice/q2ap-*.scope, outside system.slice/osworld.service).
SCOPE_LAUNCHER = """\
import json, os, subprocess, sys, time
unit, log = sys.argv[1], sys.argv[2]
manager = ["--system"] if os.geteuid() == 0 else ["--user"]
argv = ["/usr/bin/systemd-run", *manager, "--scope", "--quiet", "--collect", "--unit=" + unit,
        "--", *sys.argv[3:]]
with open(log, "ab") as out:
    proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=out, stderr=out,
                            start_new_session=True)
target = "/" + unit + ".scope"
cgroup, deadline = "", time.monotonic() + 15.0
while time.monotonic() < deadline:
    try:
        with open("/proc/%d/cgroup" % proc.pid) as handle:
            cgroup = handle.read().strip()
    except OSError:
        cgroup = ""
    if cgroup.endswith(target) or proc.poll() is not None:
        break
    time.sleep(0.05)
result = {"pid": proc.pid, "unit": unit + ".scope", "manager": manager[0][2:], "cgroup": cgroup}
if not cgroup.endswith(target):
    with open(log, "rb") as handle:
        tail = handle.read()[-600:].decode("utf-8", "replace")
    result["error"] = "not in its scope (rc %s): %s" % (proc.poll(), tail)
print(json.dumps(result))
"""
SERVER_RESTART_WAIT_S = 60.0


def guest_source(name: str) -> str:
    return (GUEST_DIR / name).read_text(encoding="utf-8")


def _last_json(result: dict[str, Any]) -> dict[str, Any] | None:
    lines = [line for line in str(result.get("output", "")).splitlines() if line.strip()]
    if not lines:
        return None
    try:
        parsed = json.loads(lines[-1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def tap_windows(records: list[dict[str, Any]], reserved: int) -> dict[int, list[dict[str, Any]]]:
    """Tap records strictly between each entry's begin and end delimiter requests."""
    out: dict[int, list[dict[str, Any]]] = {}
    open_seq: int | None = None
    current: list[dict[str, Any]] = []
    for record in records:
        if record.get("kind") == "mapping_request" and record.get("first_keycode") == reserved:
            parsed = probe_mod.parse_delimiter((record.get("rows") or [[]])[0])
            if parsed is None:
                continue
            kind, seq = parsed
            if kind == "begin":
                open_seq, current = seq, []
            elif kind == "end" and seq == open_seq:
                out[seq] = current
                open_seq = None
            continue
        if open_seq is not None:
            current.append(record)
    return out


def segment_check(records: list[dict[str, Any]]) -> dict[str, Any]:
    """``mapping_check`` per tap process, merged.

    A relaunched tap (after a guest-server restart) starts its own stream with a ready
    record and a fresh keymap; each segment is checked against its own keymap, and a
    keycode unverified in any segment is unverified for the session.
    """
    starts = [i for i, r in enumerate(records) if r.get("kind") == "ready"] or [0]
    starts[0] = 0
    bounds = list(zip(starts, starts[1:] + [len(records)], strict=True))
    checks = [mapping_check(records[a:b]) for a, b in bounds]
    if len(checks) == 1:
        return dict(checks[0], segments=1)
    merged: dict[str, Any] = {"ok": all(c["ok"] for c in checks), "segments": len(checks)}
    for key in ("requests", "keyboard_notifies", "explained", "benign_unexplained"):
        merged[key] = sum(c[key] for c in checks)
    for key in ("unverified", "requests_without_notify"):
        merged[key] = [item for c in checks for item in c[key]]
    return merged


def unverified_in_window(check: dict[str, Any], window: list[dict[str, Any]]) -> bool:
    """A key event in the window on a keycode the tap's mapping check marks unverified."""
    bad = {
        kc
        for item in check.get("unverified") or []
        for kc in item.get("keycodes") or []
        if isinstance(kc, int)
    }
    return any(r.get("kind") in verdict.KEY_KINDS and r.get("detail") in bad for r in window)


class Session:
    def __init__(self, client: GuestClient, config: dict[str, Any]):
        self.client = client
        self.config = config
        token = config["token"]
        self.probe_dir = f"/tmp/q2ap_probe_{token}"
        self.sock = f"{self.probe_dir}/sock"
        self.token = token
        self.tap_path = f"/tmp/q2ap_suite_tap_{token}.jsonl"
        self.tap_stop = f"/tmp/q2ap_suite_tap_{token}.stop"
        self.tap_offset = 0
        self.tap_records: list[dict[str, Any]] = []
        self.tap_ready: dict[str, Any] | None = None
        self.ready: dict[str, Any] = {}
        self.reserved: int | None = None
        self.baseline_led: int | None = None
        self.relaunches = 0
        self.tap_relaunches = 0
        self.scopes = 0
        self.server_pid: int | None = None  # the guest server last seen by a guard report
        self.server_unit_name: str | None = None
        self.guard_src = guest_source("guard.py")

    # --- guest helpers -------------------------------------------------------------------
    def run_guest(self, name: str, args: list[str], source: str | None = None) -> dict[str, Any]:
        started = time.monotonic()
        try:
            out = self.client.run_script(source or guest_source(name), args)
        except GuestError as exc:
            out = {"error": str(exc)[-800:]}
        out["_wall_s"] = round(time.monotonic() - started, 4)
        return out

    def cat_json(self, path: str) -> dict[str, Any] | None:
        result = self.client.execute(["cat", path], timeout=30.0)
        if result.get("returncode") != 0:
            return None
        return _last_json(result)

    def launch_scoped(self, role: str, source: str, args: list[str]) -> dict[str, Any]:
        """Start a guest script in a new transient systemd scope (``SCOPE_LAUNCHER``)."""
        self.scopes += 1
        unit = f"q2ap-{role}-{self.token}-{self.scopes}"
        encoded = base64.b64encode(source.encode("utf-8")).decode("ascii")
        argv = [unit, f"/tmp/{unit}.log", "python3", "-c", GUEST_BOOTSTRAP, encoded, *args]
        try:
            scope = self.client.run_script(SCOPE_LAUNCHER, argv)
        except GuestError as exc:
            return {"error": f"{role} launch failed: {str(exc)[-400:]}"}
        if "error" in scope:
            scope["error"] = f"{role} launch failed: {scope['error']}"
        return scope

    def launch_probe(self) -> dict[str, Any]:
        self.client.execute(["rm", "-f", f"{self.probe_dir}/ready.json"], timeout=30.0)
        args = [self.probe_dir] + ([str(self.reserved)] if self.reserved else [])
        scope = self.launch_scoped("probe", guest_source("probe.py"), args)
        if "error" in scope:
            return {"error": scope["error"], "scope": scope}
        for _ in range(80):
            ready = self.cat_json(f"{self.probe_dir}/ready.json")
            if ready:
                return dict(ready, scope=scope)
            time.sleep(0.25)
        return {"error": "probe never became ready", "scope": scope}

    def launch_tap(self) -> dict[str, Any]:
        """Start the XRecord tap writing to ``self.tap_path`` and wait for its ready record."""
        duration = int(self.config.get("tap_duration_s", 7200))
        scope = self.launch_scoped(
            "tap", guest_source("xrecord_tap.py"), [self.tap_path, str(duration), self.tap_stop]
        )
        if "error" in scope:
            return {"error": scope["error"], "scope": scope}
        known = len(self.tap_records)
        for _ in range(40):
            self.read_tap()
            ready = next((r for r in self.tap_records[known:] if r.get("kind") == "ready"), None)
            if ready:
                self.tap_ready = ready
                return dict(ready, scope=scope)
            time.sleep(0.25)
        return {"error": "tap never became ready", "scope": scope}

    def server_unit(self) -> dict[str, Any]:
        """The guest server's control group, its systemd unit and the unit's restart count.

        Read at the session's start and end: ``NRestarts`` counts every automatic restart
        of the unit, so its difference is the session's restart count however the restarts
        fell between guard reports (``session_restarts``).
        """
        out: dict[str, Any] = {"server_pid": self.server_pid}
        try:
            if self.server_unit_name is None and isinstance(self.server_pid, int):
                result = self.client.execute(["cat", f"/proc/{self.server_pid}/cgroup"], 30.0)
                out["cgroup"] = str(result.get("output", "")).strip()
                self.server_unit_name = unit_of_cgroup(out["cgroup"])
            out["unit"] = self.server_unit_name
            if self.server_unit_name:
                argv = ["systemctl", "show", "--property=NRestarts", "--value"]
                result = self.client.execute([*argv, self.server_unit_name], timeout=30.0)
                value = str(result.get("output", "")).strip()
                out["n_restarts"] = int(value) if value.isdigit() else None
        except GuestError as exc:
            out["error"] = str(exc)[-300:]
        return out

    def tap_alive(self) -> bool | None:
        """Whether the tap process still runs (None when that cannot be read)."""
        pid = (self.tap_ready or {}).get("pid")
        if not isinstance(pid, int):
            return None
        try:
            result = self.client.execute(["test", "-d", f"/proc/{pid}"], timeout=30.0)
        except GuestError:
            return None
        return result.get("returncode") == 0

    def relaunch_tap(self) -> dict[str, Any]:
        """A new tap in a new file when the old one is gone.

        Since decision D30 the tap runs in its own scope and survives a guest-server
        restart; this path remains for a tap that stopped for any other reason. The old
        file keeps what the old tap recorded; the session's stream continues in the new
        file from its own ready record (a fresh keymap), and ``segment_check`` judges each
        tap's records against its own keymap.
        """
        self.tap_relaunches += 1
        self.tap_path = f"/tmp/q2ap_suite_tap_{self.token}.{self.tap_relaunches}.jsonl"
        self.tap_offset = 0
        ready = self.launch_tap()
        keys = ("error", "pid", "min_keycode", "led_mask", "scope")
        return {k: ready.get(k) for k in keys if k in ready}

    def start(self) -> dict[str, Any]:
        tap_ready = self.launch_tap()
        if "error" in tap_ready:
            return {"error": tap_ready["error"], "tap_ready": tap_ready}
        self.ready = self.launch_probe()
        if "error" in self.ready:
            return {"error": self.ready["error"], "probe_ready": self.ready}
        self.reserved = int(self.ready["reserved_keycode"])
        check = self.run_guest(
            "guard.py",
            ["check", json.dumps({"sock": self.sock, "led_baseline": self.ready.get("led_mask")})],
            self.guard_src,
        )
        self.baseline_led = self.ready.get("led_mask")
        self.server_pid = check.get("server_pid")
        # Decision 31: the master keyboard's switch to the XTest device happens here,
        # outside every entry window (guest/guard.py, warmup).
        warmup = self.run_guest(
            "guard.py", ["warmup", json.dumps({"sock": self.sock, "reserved": self.reserved})],
            self.guard_src,
        )  # fmt: skip
        out = {
            "tap_ready": {k: tap_ready.get(k) for k in ("pid", "min_keycode", "led_mask", "scope")},
            "probe_ready": self.ready,
            "baseline_check": check,
            "warmup": warmup,
            "server_unit": self.server_unit(),
        }
        if not isinstance(warmup.get("keycode"), int):
            out["error"] = f"session warm-up failed: {str(warmup)[:300]}"
        return out

    def read_tap(self) -> None:
        script = (
            "import sys,json\n"
            "p,o=sys.argv[1],int(sys.argv[2])\n"
            "try:\n f=open(p,'rb');f.seek(o);d=f.read();f.close()\n"
            "except OSError:\n d=b''\n"
            "e=d.rfind(b'\\n')+1\n"
            "sys.stdout.write(json.dumps({'offset':o+e,'text':d[:e].decode('utf-8','replace')}))\n"
        )
        try:
            out = self.client.run_script(script, [self.tap_path, str(self.tap_offset)])
        except GuestError:
            return
        self.ingest_tap({"offset": out.get("offset", self.tap_offset), "text": out.get("text", "")})

    def ingest_tap(self, block: dict[str, Any]) -> None:
        if "records" in block:
            records = block["records"]
        else:
            records = []
            for line in str(block.get("text", "")).splitlines():
                if line.strip():
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        records.append({"kind": "unparsed"})
        self.tap_records.extend(records)
        self.tap_offset = int(block.get("offset", self.tap_offset))

    def pre(self, seq: int) -> dict[str, Any]:
        config = {
            "sock": self.sock,
            "seq": seq,
            "park": self.config["park"],
            "led_baseline": self.baseline_led,
        }
        out = self.run_guest("guard.py", ["pre", json.dumps(config)], self.guard_src)
        begin = out.get("begin") or {}
        if not begin.get("ok"):
            out["probe_absent"] = True
        return out

    def post(self, seq: int, side_effects: list[str]) -> dict[str, Any]:
        config = {
            "sock": self.sock,
            "seq": seq,
            "led_baseline": self.baseline_led,
            "side_effects": side_effects,
            "tap_path": self.tap_path,
            "tap_offset": self.tap_offset,
        }
        out = self.run_guest("guard.py", ["post", json.dumps(config)], self.guard_src)
        if out.get("tap"):
            self.ingest_tap(out.pop("tap"))
        end = out.get("end") or {}
        probe_gone = not end.get("ok") or ((out.get("check") or {}).get("probe") or {}).get(
            "absent"
        )
        if probe_gone:
            out["probe_absent"] = True
            ping = self.run_guest(
                "guard.py",
                ["check", json.dumps({"sock": self.sock, "led_baseline": self.baseline_led})],
                self.guard_src,
            )
            if ((ping.get("check") or {}).get("probe") or {}).get("absent"):
                self.relaunches += 1
                if self.tap_alive() is False:
                    # A tap that stopped with the probe is relaunched first, so it records
                    # the relaunched probe's delimiter keycode (run 622, before the scopes).
                    out["tap_relaunch"] = self.relaunch_tap()
                out["relaunch"] = self.launch_probe()
        return out

    def stop(self) -> dict[str, Any]:
        self.client.execute(["touch", self.tap_stop], timeout=30.0)
        for _ in range(60):
            self.read_tap()
            if any(r.get("kind") == "stop" for r in self.tap_records):
                break
            time.sleep(0.5)
        quit_reply = self.run_guest(
            "guard.py",
            ["check", json.dumps({"sock": self.sock, "led_baseline": self.baseline_led})],
            self.guard_src,
        )
        with contextlib.suppress(GuestError):
            self.client.run_script(
                "import socket,sys\ns=socket.socket(socket.AF_UNIX);s.connect(sys.argv[1])\n"
                's.sendall(b\'{"op": "quit"}\\n\');print(s.recv(4096).decode())',
                [self.sock],
            )
        check = segment_check(self.tap_records)
        return {
            "final_guard": quit_reply,
            "mapping_check": check,
            "tap_records": len(self.tap_records),
            "probe_relaunches": self.relaunches,
            "tap_relaunches": self.tap_relaunches,
            "server_unit": self.server_unit(),
        }

    # --- trials ------------------------------------------------------------------------
    def run_actions(
        self,
        actions: list[dict[str, Any]],
        a11y: bool,
        source: str | None,
        steps: list[dict[str, Any]],
        transport: str = "L0-fixed",
    ) -> tuple[bytes | None, str | None, list[str]]:
        """Run IR dicts through L0-fixed (or the L0-raw control); returns (shot, terminal, errors).

        L0-raw (validity control C2) sends ``l0_raw.translate``'s PyAutoGUI command for
        each action through the same ``DesktopEnv.step``; it is only ever scored, never
        developed (manifest.py admits no L0-raw development run).
        """
        shot = None
        errors: list[str] = []
        for action in actions:
            if action["op"] == "terminate":
                return shot, action["status"], errors
            try:
                if transport == "L0-raw":
                    from harness.q2.action_path.ir import parse_action
                    from harness.q2.action_path.l0_raw import translate

                    command = translate(parse_action(action))
                else:
                    command = step_command(action, source)
            except (IRError, ValueError, KeyError) as exc:
                errors.append(f"IR: {exc}")
                return shot, None, errors
            record, shot = desktop.step(self.client, command, pause=0.0, a11y=a11y)
            result = ((record.get("execute") or {}).get("result")) or {}
            record["returncode"] = result.get("returncode")
            if result.get("returncode") not in (0, None):
                errors.append(
                    f"executor rc={result.get('returncode')}: {str(result.get('error'))[-300:]}"
                )
            record["executor"] = _last_json(result) if result else None
            record["op"] = action["op"]
            steps.append(record)
            if errors:
                return shot, None, errors
        return shot, None, errors

    def run_cell(
        self, cell: dict[str, Any], layer: str, seq: int, a11y: bool, source: str | None = None
    ) -> dict[str, Any]:
        started = time.monotonic()
        trial: dict[str, Any] = {"seq": seq, "cell": cell["id"], "layer": layer}
        trial["pre"] = self.pre(seq)
        # The server that served the guard before this entry: the pre report's, or, when the
        # pre guard could not run (the server was restarting), the last one seen.
        trial["server_before"] = trial["pre"].get("server_pid") or self.server_pid
        t_pre = time.monotonic()
        steps: list[dict[str, Any]] = []
        errors: list[str] = []
        terminal = None
        shot = None
        if layer in ("L0-fixed", "L0-raw"):
            shot, terminal, errors = self.run_actions(cell["actions"], a11y, source, steps, layer)
            trial["ir"] = cell["actions"]
        else:
            from harness.q2.action_path.adapters import turn_ir

            trial["ir"] = []
            for turn in cell["turns"]:
                try:
                    actions = turn_ir(layer, turn)
                except Exception as exc:  # noqa: BLE001 - a harness failing a turn is recorded
                    errors.append(f"harness: {type(exc).__name__}: {exc}")
                    break
                trial["ir"].append(actions)
                shot, terminal, errs = self.run_actions(actions, a11y, source, steps)
                errors += errs
                if terminal or errs:
                    break
        t_act = time.monotonic()
        if shot is None:
            shot, attempts = desktop.get_screenshot(self.client)
            trial["observation_attempts"] = attempts
            trial["observation_ok"] = shot is not None
        if seq == self.config.get("kill_guest_server_during_seq"):
            # Development only: the guest server dies inside the entry, after its last
            # observation, as run 622's crash inside /accessibility did; the post guard runs
            # once the restarted server answers.
            trial["fault_injection"] = kill_guest_server(self.client, seq, "during")
            trial["fault_injection"]["restart_s"] = wait_for_server(self.client)
        trial["steps"] = steps
        trial["post"] = self.post(seq, cell.get("side_effects") or [])
        self.server_pid = trial["post"].get("server_pid") or trial["server_before"]
        t_post = time.monotonic()
        try:
            trial["marker"] = read_marker(shot) if shot else {"ok": False, "error": "no screenshot"}
        except MarkerError as exc:
            trial["marker"] = {"ok": False, "error": str(exc)}
        trial["errors"] = errors
        trial["terminal"] = terminal
        trial["timing_s"] = {
            "pre": round(t_pre - started, 4),
            "actions": round(t_act - t_pre, 4),
            "post": round(t_post - t_act, 4),
            "total": round(time.monotonic() - started, 4),
            "steps": [s["timing_s"]["total"] for s in steps],
        }
        return trial

    def judge_all(
        self, trials: list[dict[str, Any]], cells: dict[str, dict[str, Any]]
    ) -> dict[str, Any]:
        check = segment_check(self.tap_records)
        windows = tap_windows(self.tap_records, self.reserved or -1)
        for trial in trials:
            cell = cells[trial["cell"]]
            obs = observation(trial, windows.get(trial["seq"]), check)
            trial["verdict"] = verdict.judge(cell, obs)
            trial["c4"] = verdict.rdev_agreement(cell["expect"], obs["tap_events"] or [])
            trial["tap_window"] = [_compact_tap(r) for r in windows.get(trial["seq"]) or []]
        return check


def kill_guest_server(client: GuestClient, seq: int, when: str) -> dict[str, Any]:
    """Development only: SIGKILL the guest server, as the crash of run 622 ended it.

    Its systemd unit restarts it about 5 s later and, on the way, stops every process left
    in its control group; the probe and the tap run in their own scopes and are not among
    them (decision D30). ``when`` is ``during`` (inside an entry, before its post guard) or
    ``after`` (between two entries). The request that kills the server never answers, so its
    error is the expected outcome.
    """
    out: dict[str, Any] = {"seq": seq, "when": when, "t": time.time()}
    try:
        reply = client.execute(["bash", "-c", "kill -KILL $PPID"], timeout=30.0)
        out["reply"] = {k: reply.get(k) for k in ("returncode", "error")}
    except GuestError as exc:
        out["error"] = str(exc)[:200]
    return out


def wait_for_server(client: GuestClient, timeout: float = SERVER_RESTART_WAIT_S) -> float | None:
    """Seconds until the guest server answers ``/platform`` again (None after ``timeout``)."""
    started = time.monotonic()
    while time.monotonic() - started < timeout:
        try:
            client.platform()
            return round(time.monotonic() - started, 3)
        except GuestError:
            time.sleep(0.5)
    return None


def unit_of_cgroup(text: str) -> str | None:
    """The systemd service a ``/proc/PID/cgroup`` text places the process in, if any."""
    for line in text.splitlines():
        parts = line.split(":", 2)
        if len(parts) == 3 and (parts[0] == "0" or parts[1] == "name=systemd"):
            name = parts[2].rstrip("/").rsplit("/", 1)[-1]
            if name.endswith(".service"):
                return name
    return None


def server_pids(result: dict[str, Any]) -> list[int]:
    """The guest-server process ids a session's guard reports name, in the order they ran.

    The baseline check and the warm-up, each trial's pre and post guard, and the final
    guard. Every ``/accessibility`` call of a session (the reset observation's and each
    step's) is followed by at least one of them, so a restart shows as a change of id; the
    changes say which entry a restart hit, and ``session_restarts`` counts them.
    """
    start = result.get("start") or {}
    reports = [start.get("baseline_check"), start.get("warmup")]
    for trial in result.get("trials") or []:
        reports += [trial.get("pre"), trial.get("post")]
    reports.append((result.get("stop") or {}).get("final_guard"))
    return [r["server_pid"] for r in reports if isinstance((r or {}).get("server_pid"), int)]


def restarts(pids: list[int]) -> int:
    """Guest-server restarts in a sequence of reported server ids (changes of id)."""
    return sum(1 for before, after in zip(pids[:-1], pids[1:], strict=True) if before != after)


def session_restarts(result: dict[str, Any]) -> int:
    """Guest-server restarts during a session: the larger of two counts.

    The unit's ``NRestarts`` at the session's end minus at its start (every automatic
    restart, even two between the same pair of guard reports), and the changes of server
    id in the guard reports (which also see a restart systemd did not count, should one
    ever happen). Either count alone is used when the other could not be read.
    """
    by_ids = restarts(server_pids(result))
    first = ((result.get("start") or {}).get("server_unit") or {}).get("n_restarts")
    last = ((result.get("stop") or {}).get("server_unit") or {}).get("n_restarts")
    if isinstance(first, int) and isinstance(last, int):
        return max(by_ids, last - first)
    return by_ids


def accessibility_calls(result: dict[str, Any]) -> int:
    """``/accessibility`` calls ``DesktopEnv`` made in a session (retries are attempts).

    The reset observation's (screenshot-plus-accessibility setting) and every step's.
    """
    reset = result.get("reset_observation") or {}
    calls = 1 if reset.get("accessibility_attempts") else 0
    for trial in result.get("trials") or []:
        calls += sum(1 for step in trial.get("steps") or [] if step.get("accessibility_attempts"))
    return calls


def _compact_tap(record: dict[str, Any]) -> list[Any]:
    kind = record.get("kind")
    if kind in verdict.KEY_KINDS:
        return [
            kind,
            record.get("detail"),
            record.get("state"),
            record.get("keysym0"),
            record.get("server_time"),
        ]
    if kind in verdict.BUTTON_KINDS or kind == "MotionNotify":
        return [
            kind,
            record.get("detail"),
            record.get("state"),
            record.get("x"),
            record.get("y"),
            record.get("server_time"),
        ]
    if kind == "mapping_notify":
        # request: 0 modifier, 1 keyboard, 2 pointer (diagnostic; never judged).
        return [kind, record.get("request"), record.get("first_keycode"), record.get("count")]
    if kind == "mapping_request":
        return [kind, record.get("first_keycode"), record.get("count")]
    return [kind]


def observation(
    trial: dict[str, Any], window: list[dict[str, Any]] | None, check: dict[str, Any]
) -> dict[str, Any]:
    """What verdict.judge needs, from one trial record and its tap window."""
    infra: list[str] = []
    pre, post = trial.get("pre") or {}, trial.get("post") or {}
    if pre.get("probe_absent") or post.get("probe_absent"):
        infra.append("probe_absent")
    if "error" in pre or "error" in post:
        infra.append("guard_script")
    before = pre.get("server_pid") or trial.get("server_before")
    servers = {before, post.get("server_pid")} - {None}
    if len(servers) > 1:
        # The guest server crashed and systemd restarted it during the entry, or between
        # the last guard report and this entry's post guard (section 6.1).
        infra.append("guest_server_restart")
    retried: list[str] = []
    for step in trial.get("steps") or []:
        infra += step.get("infra") or []
        retried += step.get("retried") or []
    attempts = trial.get("observation_attempts")
    if attempts is not None:
        # The no-action entry's screenshot (section 5, condition 3): a failure only when no
        # attempt delivers an image (section 6.1); a retry that does is reported.
        if not trial.get("observation_ok", attempts[-1].get("status") == 200):
            infra.append("screenshot")
        elif len(attempts) > 1:
            retried.append("screenshot")
    end = post.get("end") or {}
    tap_events = None
    if window is None:
        infra.append("tap_window_missing")
    else:
        tap_events = [
            verdict.from_tap(r)
            for r in window
            if r.get("kind") in verdict.KEY_KINDS + verdict.BUTTON_KINDS + ("MotionNotify",)
        ]
        if unverified_in_window(check, window):
            infra.append("tap_unverified")
    probe_events = (
        [verdict.from_probe(r) for r in end.get("events") or []] if end.get("ok") else None
    )
    return {
        "probe_events": probe_events,
        "tap_events": tap_events,
        "text": end.get("text"),
        "end_pointer": ((end.get("state") or {}).get("pointer")),
        "marker": trial.get("marker"),
        "probe_final": [end.get("seq"), end.get("crc")] if end.get("ok") else None,
        "guard_violations": {"pre": pre.get("violations"), "post": post.get("violations")},
        "infra": sorted(set(infra)),
        "retried": sorted(retried),
        "errors": trial.get("errors") or [],
        "terminal": trial.get("terminal"),
    }
