"""Session engine of the action-path suite (runs in the GPU-less runner container).

A *session* is one cold-booted VM. The runner starts the XRecord tap and the
probe, records the session's guard baseline, then runs its trials in order:

    pre-guard + park + probe begin   (guest/guard.py pre: one /execute)
    the cell's actions               (one DesktopEnv.step each; see desktop.py)
    probe end + guard + restoration  (guest/guard.py post: one /execute)

and finally stops the tap and the probe. Every trial is judged with
``action_path.verdict.judge`` after the session, when the whole tap stream is
in hand (the stream is split at the probe's delimiter requests).

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
from harness.q2.vm.guest_http import GuestClient, GuestError
from harness.q2.vm.marker import MarkerError, read_marker

GUEST_DIR = Path(__file__).resolve().parent / "guest"


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
        self.tap_path = f"/tmp/q2ap_suite_tap_{token}.jsonl"
        self.tap_stop = f"/tmp/q2ap_suite_tap_{token}.stop"
        self.tap_offset = 0
        self.tap_records: list[dict[str, Any]] = []
        self.ready: dict[str, Any] = {}
        self.reserved: int | None = None
        self.baseline_led: int | None = None
        self.relaunches = 0
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

    def launch_probe(self) -> dict[str, Any]:
        self.client.execute(["rm", "-f", f"{self.probe_dir}/ready.json"], timeout=30.0)
        args = [self.probe_dir] + ([str(self.reserved)] if self.reserved else [])
        status, text = self.client.launch_script(guest_source("probe.py"), args)
        if status != 200:
            return {"error": f"probe launch failed: {status} {text}"}
        for _ in range(80):
            ready = self.cat_json(f"{self.probe_dir}/ready.json")
            if ready:
                return ready
            time.sleep(0.25)
        return {"error": "probe never became ready"}

    def start(self) -> dict[str, Any]:
        duration = int(self.config.get("tap_duration_s", 7200))
        status, text = self.client.launch_script(
            guest_source("xrecord_tap.py"), [self.tap_path, str(duration), self.tap_stop]
        )
        if status != 200:
            return {"error": f"tap launch failed: {status} {text}"}
        tap_ready = None
        for _ in range(40):
            self.read_tap()
            tap_ready = next((r for r in self.tap_records if r.get("kind") == "ready"), None)
            if tap_ready:
                break
            time.sleep(0.25)
        if not tap_ready:
            return {"error": "tap never became ready"}
        self.ready = self.launch_probe()
        if "error" in self.ready:
            return {"error": self.ready["error"]}
        self.reserved = int(self.ready["reserved_keycode"])
        check = self.run_guest(
            "guard.py",
            ["check", json.dumps({"sock": self.sock, "led_baseline": self.ready.get("led_mask")})],
            self.guard_src,
        )
        self.baseline_led = self.ready.get("led_mask")
        return {
            "tap_ready": {k: tap_ready.get(k) for k in ("pid", "min_keycode", "led_mask")},
            "probe_ready": self.ready,
            "baseline_check": check,
        }

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
        check = mapping_check(self.tap_records)
        return {
            "final_guard": quit_reply,
            "mapping_check": check,
            "tap_records": len(self.tap_records),
            "probe_relaunches": self.relaunches,
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
        trial["steps"] = steps
        trial["post"] = self.post(seq, cell.get("side_effects") or [])
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
        check = mapping_check(self.tap_records)
        windows = tap_windows(self.tap_records, self.reserved or -1)
        for trial in trials:
            cell = cells[trial["cell"]]
            obs = observation(trial, windows.get(trial["seq"]), check)
            trial["verdict"] = verdict.judge(cell, obs)
            trial["c4"] = verdict.rdev_agreement(cell["expect"], obs["tap_events"] or [])
            trial["tap_window"] = [_compact_tap(r) for r in windows.get(trial["seq"]) or []]
        return check


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
