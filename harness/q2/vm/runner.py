"""In-namespace runner for VM campaigns (runs inside a GPU-less runner container).

The host driver starts one runner container per VM cycle with
``--network container:<vm>``, so this process shares the VM container's
network namespace: it reaches the guest server at the image's NAT address and
the QEMU monitor on loopback, while nothing is published to the host or to
Docker's bridge.

Subcommands:

* ``boot-cycle --config FILE``: measure one cold boot (container start to the
  first valid ``/screenshot``), record guest facts, run the reset sentinel,
  time the observation endpoints, check that HMP input reaches X and,
  optionally, run the XRecord tap's oracle self-test (keyboard remaps).
* ``tcp-probe``: from a separate container, test whether a VM's guest server
  is reachable over Docker's bridge (documents the exposure of the
  bridge-unpublished fallback; decision D13).

Standard library only; Python 3.10 compatible.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any

from harness.q2.vm.guest_http import GuestClient, GuestError, is_png, png_size
from harness.q2.vm.hmp import HmpClient, HmpError

GUEST_DIR = Path(__file__).resolve().parent / "guest"

# HMP reachability sequence. Each step is a list of monitor calls plus the X
# events it should produce. Keysyms are X11 values; buttons are X core numbers.
HMP_STEPS: list[dict[str, Any]] = [
    {"id": "key_a", "calls": [["sendkey", "a"]], "expect_keys": [0x61]},
    {
        "id": "chord_shift_comma",
        "calls": [["sendkey", "shift-comma"]],
        "expect_keys": [0xFFE1, 0x2C],
    },
    {"id": "key_kp_enter", "calls": [["sendkey", "kp_enter"]], "expect_keys": [0xFF8D]},
    {"id": "key_kp_add", "calls": [["sendkey", "kp_add"]], "expect_keys": [0xFFAB]},
    # QEMU has two candidate qcodes for the PC application key; record both.
    {"id": "key_menu", "calls": [["sendkey", "menu"]], "expect_keys": [0xFF67]},
    {"id": "key_esc_after_menu", "calls": [["sendkey", "esc"]], "expect_keys": [0xFF1B]},
    {"id": "key_compose", "calls": [["sendkey", "compose"]], "expect_keys": [0xFF67]},
    {"id": "key_esc_after_compose", "calls": [["sendkey", "esc"]], "expect_keys": [0xFF1B]},
    # The 102nd key (keycode 94 on pc105): the `<` path that pyautogui prefers.
    {"id": "key_less_102nd", "calls": [["sendkey", "less"]], "expect_keys": [0x3C]},
    {"id": "caps_lock_on", "calls": [["sendkey", "caps_lock"]], "expect_keys": [0xFFE5], "led": 1},
    {"id": "caps_lock_off", "calls": [["sendkey", "caps_lock"]], "expect_keys": [0xFFE5], "led": 0},
    {
        "id": "button_left",
        "calls": [["mouse_button", 1], ["mouse_button", 0]],
        "expect_buttons": [1],
    },
    {
        "id": "button_middle",
        "calls": [["mouse_button", 4], ["mouse_button", 0]],
        "expect_buttons": [2],
    },
    {
        "id": "button_right",
        "calls": [["mouse_button", 2], ["mouse_button", 0]],
        "expect_buttons": [3],
    },
    {"id": "key_esc_after_right", "calls": [["sendkey", "esc"]], "expect_keys": [0xFF1B]},
    {"id": "wheel_dz_neg", "calls": [["mouse_move", 0, 0, -1]], "expect_buttons_any": [4, 5]},
    {"id": "wheel_dz_pos", "calls": [["mouse_move", 0, 0, 1]], "expect_buttons_any": [4, 5]},
    {"id": "rel_motion", "calls": [["mouse_move", 40, 30]], "expect_motion": True},
]
LED_SNIPPET = (
    "from Xlib import display;import json;"
    "print(json.dumps({'led_mask':display.Display().get_keyboard_control().led_mask}))"
)
CLOCK_SNIPPET = "import time,json;print(json.dumps({'t':time.time()}))"
# Guard probe: pressed keycodes, pressed pointer buttons and LED mask.
GUARD_SNIPPET = (
    "from Xlib import display;import json;d=display.Display();"
    "km=d.query_keymap();p=d.screen().root.query_pointer();"
    "keys=[i*8+b for i,v in enumerate(km) for b in range(8) if v>>b&1];"
    "print(json.dumps({'keys':keys,'buttons':p.mask&0x1f00,"
    "'led_mask':d.get_keyboard_control().led_mask}))"
)


def gpu_free_assertion() -> dict[str, Any]:
    """Decision D12: the runner must see no NVIDIA device and no CUDA selection."""
    devices = sorted(glob.glob("/dev/nvidia*")) + sorted(glob.glob("/dev/dri/*"))
    status = {}
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith(("CapEff", "CapBnd", "NoNewPrivs", "Seccomp")):
                key, value = line.split(":", 1)
                status[key] = value.strip()
    except OSError:
        pass
    result = {
        "nvidia_devices": devices,
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "uid": os.getuid(),
        "proc_status": status,
        "net_interfaces": sorted(os.listdir("/sys/class/net"))
        if os.path.isdir("/sys/class/net")
        else [],
    }
    result["ok"] = not devices
    return result


def _now() -> float:
    return time.time()


def _guest_script(name: str) -> str:
    return (GUEST_DIR / name).read_text(encoding="utf-8")


def wait_for_boot(client: GuestClient, t0: float, timeout: float) -> dict[str, Any]:
    """Poll until the guest serves a valid PNG screenshot; times are seconds after t0."""
    record: dict[str, Any] = {"t_tcp_open": None, "t_screenshot_200": None, "polls": 0}
    deadline = t0 + timeout
    last_error = None
    while _now() < deadline:
        record["polls"] += 1
        if record["t_tcp_open"] is None and client.tcp_open(timeout=1.0):
            record["t_tcp_open"] = round(_now() - t0, 3)
        if record["t_tcp_open"] is not None:
            try:
                status, payload, _ = client.screenshot(timeout=10.0)
                if status == 200 and is_png(payload):
                    record["t_screenshot_200"] = round(_now() - t0, 3)
                    record["screenshot_size"] = png_size(payload)
                    return record
                last_error = f"status {status}"
            except GuestError as exc:
                last_error = str(exc)[:200]
        time.sleep(1.0)
    record["error"] = f"no valid screenshot within {timeout}s ({last_error})"
    return record


def wait_for_settle(client: GuestClient, t0: float, timeout: float) -> dict[str, Any]:
    """Screenshots 2 s apart until two consecutive ones are byte-identical."""
    started = _now()
    previous = None
    shots = 0
    while _now() - started < timeout:
        try:
            status, payload, _ = client.screenshot(timeout=10.0)
        except GuestError:
            status, payload = 0, b""
        shots += 1
        digest = hashlib.sha256(payload).hexdigest() if status == 200 else None
        if digest is not None and digest == previous:
            return {"t_settled": round(_now() - t0, 3), "shots": shots}
        previous = digest
        time.sleep(2.0)
    return {"t_settled": None, "shots": shots}


def latency_block(client: GuestClient, reps: int) -> dict[str, Any]:
    out: dict[str, Any] = {
        "screenshot_s": [],
        "accessibility_s": [],
        "accessibility_bytes": [],
        "execute_noop_s": [],
        "errors": [],
    }
    for _ in range(reps):
        try:
            status, _, elapsed = client.screenshot(timeout=30.0)
            if status == 200:
                out["screenshot_s"].append(round(elapsed, 4))
            status, size, elapsed = client.accessibility()
            if status == 200:
                out["accessibility_s"].append(round(elapsed, 4))
                out["accessibility_bytes"].append(size)
            else:
                out["errors"].append(f"accessibility {status}")
            result = client.execute(["python3", "-c", "pass"], timeout=60.0)
            if result.get("http_status") == 200 and result.get("returncode") == 0:
                out["execute_noop_s"].append(round(result["elapsed_s"], 4))
        except GuestError as exc:
            out["errors"].append(str(exc)[:200])
    return out


def guest_clock_offset(client: GuestClient) -> float:
    """Guest time minus runner time, from the lowest-latency of three round trips."""
    samples = []
    for _ in range(3):
        sent = _now()
        result = client.execute(["python3", "-c", CLOCK_SNIPPET], timeout=30.0)
        received = _now()
        guest_t = json.loads(str(result.get("output", "")).strip().splitlines()[-1])["t"]
        samples.append((received - sent, guest_t - (sent + received) / 2))
    samples.sort()
    return samples[0][1]


def read_tap(client: GuestClient, path: str) -> list[dict[str, Any]]:
    result = client.execute(["cat", path], timeout=30.0)
    if result.get("returncode") != 0:
        return []
    records = []
    for line in str(result.get("output", "")).splitlines():
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def read_led(client: GuestClient) -> int | None:
    result = client.execute(["python3", "-c", LED_SNIPPET], timeout=30.0)
    try:
        return int(json.loads(str(result.get("output", "")).strip().splitlines()[-1])["led_mask"])
    except (ValueError, KeyError, IndexError, json.JSONDecodeError):
        return None


def evaluate_step(step: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    keys = [e for e in events if e["kind"] in ("KeyPress", "KeyRelease")]
    buttons = [e for e in events if e["kind"] in ("ButtonPress", "ButtonRelease")]
    motion = [e for e in events if e["kind"] == "MotionNotify"]
    observed_presses = [e["keysym0"] for e in keys if e["kind"] == "KeyPress"]
    observed_releases = [e["keysym0"] for e in keys if e["kind"] == "KeyRelease"]
    observed_buttons = [(e["kind"], e["detail"]) for e in buttons]
    keycodes = [(e["kind"], e["detail"]) for e in keys]
    ok = True
    if "expect_keys" in step:
        ok = observed_presses == step["expect_keys"] and sorted(observed_releases) == sorted(
            step["expect_keys"]
        )
    if "expect_buttons" in step:
        expected = []
        for number in step["expect_buttons"]:
            expected += [("ButtonPress", number), ("ButtonRelease", number)]
        ok = ok and observed_buttons == expected
    if "expect_buttons_any" in step:
        details = {detail for _, detail in observed_buttons}
        ok = (
            ok
            and len(observed_buttons) == 2
            and len(details) == 1
            and details <= set(step["expect_buttons_any"])
        )
    if step.get("expect_motion"):
        ok = ok and bool(motion)
    return {
        "id": step["id"],
        "ok": bool(ok),
        "key_presses": observed_presses,
        "key_releases": observed_releases,
        "key_states": [e["state"] for e in keys],
        "keycodes": keycodes,
        "shifted_keysyms": [e.get("keysym1") for e in keys if e["kind"] == "KeyPress"],
        "buttons": observed_buttons,
        "motion_events": len(motion),
        "motion_last": [motion[-1]["x"], motion[-1]["y"]] if motion else None,
    }


def hmp_input_check(client: GuestClient, hmp_port: int, token: str) -> dict[str, Any]:
    tap_path = f"/tmp/q2ap_tap_{token}.jsonl"
    stop_path = f"/tmp/q2ap_tap_{token}.stop"
    offset = guest_clock_offset(client)
    status, text = client.launch_script(
        _guest_script("xrecord_tap.py"), [tap_path, "60", stop_path]
    )
    if status != 200:
        return {"ok": False, "error": f"tap launch failed: {status} {text}"}
    ready = None
    for _ in range(40):
        records = read_tap(client, tap_path)
        ready = next((r for r in records if r.get("kind") == "ready"), None)
        if ready:
            break
        time.sleep(0.25)
    if not ready:
        return {"ok": False, "error": "tap never became ready"}
    starts: list[float] = []
    led_after: dict[str, int | None] = {}
    with HmpClient(port=hmp_port) as hmp:
        banner = hmp.banner
        for step in HMP_STEPS:
            # Window i is [start_i, start_i+1) in guest time. A quiet lead of
            # 0.3 s before the first call absorbs clock-offset error.
            starts.append(_now())
            time.sleep(0.3)
            for call in step["calls"]:
                method = getattr(hmp, call[0])
                method(*call[1:])
                time.sleep(0.15)
            time.sleep(0.6)
            if "led" in step:
                led_after[step["id"]] = read_led(client)
    starts.append(_now())
    time.sleep(0.5)
    client.execute(["touch", stop_path], timeout=30.0)
    records: list[dict[str, Any]] = []
    for _ in range(40):
        records = read_tap(client, tap_path)
        if any(r.get("kind") == "stop" for r in records):
            break
        time.sleep(0.25)
    events = [r for r in records if r.get("kind") not in ("ready", "stop")]
    steps = []
    assigned = 0
    for index, step in enumerate(HMP_STEPS):
        low, high = starts[index] + offset, starts[index + 1] + offset
        in_window = [e for e in events if low <= e["t"] < high]
        assigned += len(in_window)
        result = evaluate_step(step, in_window)
        if "led" in step:
            measured = led_after.get(step["id"])
            result["led_mask_after"] = measured
            result["ok"] = result["ok"] and measured is not None and (measured & 1) == step["led"]
        steps.append(result)
    stop = next((r for r in records if r.get("kind") == "stop"), None)
    client.execute(["rm", "-f", tap_path, stop_path], timeout=30.0)
    return {
        "ok": all(s["ok"] for s in steps),
        "hmp_banner": banner[:200],
        "clock_offset_s": round(offset, 4),
        "led_ready": ready.get("led_mask"),
        "led_stop": stop.get("led_mask") if stop else None,
        "events_total": len(events),
        "events_unassigned": len(events) - assigned,
        "steps": steps,
    }


def tap_selftest(client: GuestClient, token: str) -> dict[str, Any]:
    """Oracle validation: the tap must follow keyboard-mapping changes in stream order.

    Runs ``guest/tap_selftest.py`` (remap one spare keycode three times, press
    it after each change) under the tap and compares the tap's key events on
    that keycode with the expected keysyms. Also reports what a keymap frozen
    at tap start would have given, which is what the previous tap did.
    """
    from harness.q2.vm.guest.xrecord_tap import mapping_check

    tap_path = f"/tmp/q2ap_tapself_{token}.jsonl"
    stop_path = f"/tmp/q2ap_tapself_{token}.stop"
    status, text = client.launch_script(
        _guest_script("xrecord_tap.py"), [tap_path, "60", stop_path]
    )
    if status != 200:
        return {"ok": False, "error": f"tap launch failed: {status} {text}"}
    ready = None
    for _ in range(40):
        ready = next((r for r in read_tap(client, tap_path) if r.get("kind") == "ready"), None)
        if ready:
            break
        time.sleep(0.25)
    if not ready:
        return {"ok": False, "error": "tap never became ready"}
    fixture = client.run_script(_guest_script("tap_selftest.py"))
    time.sleep(0.8)
    client.execute(["touch", stop_path], timeout=30.0)
    records: list[dict[str, Any]] = []
    for _ in range(40):
        records = read_tap(client, tap_path)
        if any(r.get("kind") == "stop" for r in records):
            break
        time.sleep(0.25)
    client.execute(["rm", "-f", tap_path, stop_path], timeout=30.0)
    if "error" in fixture:
        return {"ok": False, "error": fixture["error"]}
    keycode = int(fixture["keycode"])
    observed = [
        [r["kind"], r["detail"], r.get("keysym0")]
        for r in records
        if r.get("kind") in ("KeyPress", "KeyRelease") and r.get("detail") == keycode
    ]
    snapshot_row = (ready.get("keymap") or [])[keycode - int(ready.get("min_keycode", 0))]
    frozen = [[kind, code, snapshot_row[0] if snapshot_row else 0] for kind, code, _ in observed]
    check = mapping_check(records)
    stop = next((r for r in records if r.get("kind") == "stop"), {})
    return {
        "ok": observed == fixture["expected"] and check["ok"] and check["requests"] >= 3,
        "keycode": keycode,
        "expected": fixture["expected"],
        "observed": observed,
        "frozen_keymap_would_give": frozen,
        "mapping_check": check,
        "map_gen_at_stop": stop.get("map_gen"),
    }


def read_guard(client: GuestClient) -> dict[str, Any]:
    result = client.execute(["python3", "-c", GUARD_SNIPPET], timeout=30.0)
    try:
        return json.loads(str(result.get("output", "")).strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return {"error": str(result.get("error", ""))[-300:]}


def rdev_capture(client: GuestClient, config: dict[str, Any]) -> dict[str, Any]:
    """Send every plan entry's chords through HMP, rep times, and record XRecord.

    Each (repetition, entry) gets the window [start, next start) in guest time,
    with a 0.3 s quiet lead before its first chord. Recovery chords run in a
    window of their own and are never compared. A guard read after each entry
    records pressed keys and buttons (they must be empty) and the LED mask.
    """
    from harness.q2.action_path.rdev import project

    plan = json.loads(Path(config["plan_path"]).read_text(encoding="utf-8"))
    reps = int(config["reps"])
    token = config["token"]
    tap_path = f"/tmp/q2ap_rdev_{token}.jsonl"
    stop_path = f"/tmp/q2ap_rdev_{token}.stop"
    offset_start = guest_clock_offset(client)
    duration = 120 + reps * len(plan["entries"]) * 6
    status, text = client.launch_script(
        _guest_script("xrecord_tap.py"), [tap_path, str(duration), stop_path]
    )
    if status != 200:
        return {"error": f"tap launch failed: {status} {text}"}
    ready = None
    for _ in range(40):
        ready = next((r for r in read_tap(client, tap_path) if r.get("kind") == "ready"), None)
        if ready:
            break
        time.sleep(0.25)
    if not ready:
        return {"error": "tap never became ready"}
    baseline = read_guard(client)
    marks: list[dict[str, Any]] = []
    with HmpClient(port=config["hmp_port"]) as hmp:
        banner = hmp.banner
        qemu_version = hmp.command("info version")
        for rep in range(reps):
            for entry in plan["entries"]:
                mark: dict[str, Any] = {"rep": rep, "id": entry["id"], "start": _now()}
                time.sleep(0.3)
                leds = []
                for chord in entry["chords"]:
                    hmp.sendkey("-".join(chord), hold_ms=100)
                    time.sleep(0.35)
                    if entry.get("caps_lock"):
                        leds.append(read_led(client))
                time.sleep(0.5)
                mark["end"] = _now()
                # Quiet gap so recovery input cannot fall inside the entry's window
                # (job 387 showed recovery presses leaking across the boundary).
                time.sleep(0.6)
                if entry["recovery"]:
                    for chord in entry["recovery"]:
                        hmp.sendkey("-".join(chord), hold_ms=100)
                        time.sleep(1.0)
                    time.sleep(1.5)
                mark["guard"] = read_guard(client)
                if entry.get("caps_lock"):
                    base_bit = int(baseline.get("led_mask", 0)) & 1
                    expected = [base_bit ^ ((i + 1) % 2) for i in range(len(leds))]
                    observed = [None if v is None else v & 1 for v in leds]
                    mark["caps_leds"] = observed
                    mark["caps_led_ok"] = observed == expected and observed[-1] == base_bit
                marks.append(mark)
    offset_end = guest_clock_offset(client)
    offset = (offset_start + offset_end) / 2
    time.sleep(0.5)
    client.execute(["touch", stop_path], timeout=30.0)
    records: list[dict[str, Any]] = []
    for _ in range(60):
        records = read_tap(client, tap_path)
        if any(r.get("kind") == "stop" for r in records):
            break
        time.sleep(0.5)
    events = [r for r in records if r.get("kind") not in ("ready", "stop")]
    trials = []
    for mark in marks:
        low, high = mark["start"] + offset, mark["end"] + offset
        window = [e for e in events if low <= e["t"] < high]
        guard = mark["guard"]
        trials.append(
            {
                "rep": mark["rep"],
                "id": mark["id"],
                "projection": project(window),
                "raw": [
                    [e["kind"], e["detail"], e.get("keysym0"), e.get("keysym1"), e["state"]]
                    for e in window
                    if e["kind"] in ("KeyPress", "KeyRelease")
                ],
                "guard": guard,
                "guard_clean": not guard.get("keys") and not guard.get("buttons"),
                "caps_leds": mark.get("caps_leds"),
                "caps_led_ok": mark.get("caps_led_ok"),
            }
        )
    client.execute(["rm", "-f", tap_path, stop_path], timeout=30.0)
    return {
        "hmp_banner": banner[:200],
        "qemu_version": qemu_version[:200],
        "clock_offset_s": [round(offset_start, 4), round(offset_end, 4)],
        "baseline_guard": baseline,
        "events_total": len(events),
        "trials": trials,
    }


def capture_cycle(config: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {"cycle": config["cycle"], "token": config["token"]}
    result["runner"] = gpu_free_assertion()
    if not result["runner"]["ok"]:
        result["error"] = "runner sees an NVIDIA device; refusing to continue"
        return result
    client = GuestClient(config["guest_ip"], config["server_port"])
    boot = wait_for_boot(client, config["t0"], config["boot_timeout_s"])
    result["boot"] = boot
    if boot.get("t_screenshot_200") is None:
        result["error"] = boot.get("error", "boot failed")
        return result
    if config["settle_timeout_s"]:
        result["settle"] = wait_for_settle(client, config["t0"], config["settle_timeout_s"])
    result["facts"] = client.run_script(_guest_script("facts.py"), ["brief"])
    capture = rdev_capture(client, config)
    capture["boot_id"] = result["facts"].get("boot_id")
    capture["plan_sha256"] = config["plan_sha256"]
    result["capture"] = capture
    if "error" in capture:
        result["error"] = capture["error"]
    return result


def boot_cycle(config: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {"cycle": config["cycle"], "token": config["token"]}
    result["runner"] = gpu_free_assertion()
    if not result["runner"]["ok"]:
        result["error"] = "runner sees an NVIDIA device; refusing to continue"
        return result
    client = GuestClient(config["guest_ip"], config["server_port"])
    boot = wait_for_boot(client, config["t0"], config["boot_timeout_s"])
    result["boot"] = boot
    if boot.get("t_screenshot_200") is None:
        result["error"] = boot.get("error", "boot failed")
        return result
    if config["settle_timeout_s"]:
        result["settle"] = wait_for_settle(client, config["t0"], config["settle_timeout_s"])
    try:
        result["platform"] = client.platform()
    except GuestError as exc:
        result["platform_error"] = str(exc)[:200]
    try:
        with HmpClient(port=config["hmp_port"]) as hmp:
            result["hmp_info"] = {
                "banner": hmp.banner[:200],
                "version": hmp.command("info version")[:200],
                "kvm": hmp.command("info kvm")[:200],
                "status": hmp.command("info status")[:200],
            }
    except (OSError, HmpError) as exc:
        result["hmp_info"] = {"error": str(exc)[:200]}
    mode = "full" if config["full_facts"] else "brief"
    try:
        result["facts"] = client.run_script(_guest_script("facts.py"), [mode])
    except GuestError as exc:
        result["facts"] = {"error": str(exc)[:500]}
    sentinel_src = _guest_script("sentinel.py")
    try:
        result["sentinel_before"] = client.run_script(sentinel_src, ["check"])
        result["sentinel_write"] = client.run_script(sentinel_src, ["write", config["token"]])
        result["sentinel_after"] = client.run_script(sentinel_src, ["check"])
    except GuestError as exc:
        result["sentinel_error"] = str(exc)[:500]
    if config["latency_reps"]:
        result["latency"] = latency_block(client, config["latency_reps"])
    if config["hmp_input_check"]:
        try:
            result["hmp_input"] = hmp_input_check(client, config["hmp_port"], config["token"])
        except (OSError, HmpError, GuestError, KeyError, ValueError) as exc:
            result["hmp_input"] = {"ok": False, "error": repr(exc)[:500]}
    if config.get("tap_selftest"):
        try:
            result["tap_selftest"] = tap_selftest(client, config["token"])
        except (OSError, GuestError, KeyError, ValueError, IndexError) as exc:
            result["tap_selftest"] = {"ok": False, "error": repr(exc)[:500]}
    return result


def _progress(config: dict[str, Any], trial: dict[str, Any]) -> dict[str, Any]:
    """Append one trial to ``cycle-NN.trials.jsonl`` so a killed session keeps its trials."""
    path = Path(config["out"]).with_suffix(".trials.jsonl")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(trial, sort_keys=True) + "\n")
    return trial


def session_cycle(config: dict[str, Any]) -> dict[str, Any]:
    """One cold-booted session of the suite: inputs validation, development or canary."""
    from harness.q2.vm.suite import Session

    started = time.monotonic()
    result: dict[str, Any] = {"cycle": config["cycle"], "token": config["token"],
                              "kind": config["kind"], "setting": config["setting"],
                              "layer": config.get("layer")}  # fmt: skip
    result["runner"] = gpu_free_assertion()
    if not result["runner"]["ok"]:
        result["error"] = "runner sees an NVIDIA device; refusing to continue"
        return result
    client = GuestClient(config["guest_ip"], config["server_port"])
    boot = wait_for_boot(client, config["t0"], config["boot_timeout_s"])
    result["boot"] = boot
    if boot.get("t_screenshot_200") is None:
        result["error"] = boot.get("error", "boot failed")
        return result
    if config["settle_timeout_s"]:
        result["settle"] = wait_for_settle(client, config["t0"], config["settle_timeout_s"])
    try:
        result["facts"] = client.run_script(_guest_script("facts.py"), ["brief"])
    except GuestError as exc:
        result["facts"] = {"error": str(exc)[:500]}
    cells = json.loads(Path(config["cells_path"]).read_text(encoding="utf-8"))
    config["park"] = cells["guard"]["park_pointer"]
    a11y = config["setting"] == "screenshot+a11y"
    kind = config["kind"]
    if kind in ("canary-development", "canary-acceptance"):
        from harness.q2.vm.canary_run import canary_trial

        # Decision 31: the session's first XTest key event happens before any trial.
        from harness.q2.vm.suite import guest_source

        try:
            result["warmup"] = client.run_script(guest_source("guard.py"), ["warmup", "{}"])
        except GuestError as exc:
            result["error"] = f"session warm-up failed: {str(exc)[:300]}"
            return result
        trials = []
        measure = bool(config.get("measure_targets"))
        if measure:
            from harness.q2.vm.canary_run import install_canary_module

            result["canary_module"] = install_canary_module(client)
        shot_dir = str(Path(config["out"]).parent) if measure else None
        for seq, pair in config["trials"]:
            app, entry = pair.split(":", 1)
            trial = canary_trial(
                client, cells["canary"], app, entry, seq, measure=measure, shot_dir=shot_dir
            )
            trial["seq"], trial["cell"] = seq, pair
            trials.append(_progress(config, trial))
        result["trials"] = trials
        result["session_wall_s"] = round(time.monotonic() - started, 2)
        return result
    session = Session(client, config)
    result["start"] = session.start()
    if "error" in result["start"]:
        result["error"] = result["start"]["error"]
        return result
    if kind != "inputs-validation":
        # OSWorld's DesktopEnv.reset ends with an observation (_get_obs), so a Stage-1
        # episode's first step never makes the boot's first /screenshot or /accessibility
        # call. The same observation is taken here, recorded and not judged (development
        # run 537: the boot's first /accessibility call answered HTTP 500, its retry 200).
        from harness.q2.vm import desktop

        shot, shot_attempts = desktop.get_screenshot(client)
        result["reset_observation"] = {
            "screenshot_attempts": shot_attempts,
            "screenshot_ok": shot is not None,
        }
        if a11y:
            tree, tree_attempts = desktop.get_accessibility_tree(client)
            result["reset_observation"]["accessibility_attempts"] = tree_attempts
            result["reset_observation"]["accessibility_ok"] = tree is not None
    trials: list[dict[str, Any]] = []
    if kind == "inputs-validation":
        from harness.q2.vm.validation import hmp_trial, judge_probe_validation, probe_items

        plan = json.loads(Path(config["plan_path"]).read_text(encoding="utf-8"))
        l0 = {c["id"]: c for c in cells["layers"]["L0-fixed"]}
        items = probe_items(plan, l0)
        seq = 0
        with HmpClient(port=config["hmp_port"]) as hmp:
            for _ in range(int(config["reps"])):
                for item in items:
                    trials.append(_progress(config, hmp_trial(session, hmp, item, seq)))
                    seq += 1
        result["stop"] = session.stop()
        result["judged"] = judge_probe_validation(session, trials, items)
        result["trials"] = trials
        if config.get("canary_readback"):
            from harness.q2.vm.canary_run import canary_trial

            readback = []
            fixtures_seen = set()
            for app, spec in cells["canary"]["apps"].items():
                for entry_id in spec["entries"]:
                    fixture = cells["canary"]["entries"][entry_id]["fixture"]
                    if (app, fixture) in fixtures_seen:
                        continue
                    fixtures_seen.add((app, fixture))
                    trial = canary_trial(client, cells["canary"], app, entry_id, seq, no_input=True)
                    seq += 1
                    readback.append(trial)
            result["canary_readback"] = readback
        result["session_wall_s"] = round(time.monotonic() - started, 2)
        return result
    layer = config["layer"]
    by_id = {c["id"]: c for c in cells["layers"]["L0-fixed" if layer == "L0-raw" else layer]}
    source = None
    mutant = config.get("mutant")
    if mutant not in (None, "none"):
        # C3: one mutant per session (patched modules stay loaded in this process).
        from harness.q2.action_path import mutants

        loaded = mutants.load_layer(layer, mutants.build(mutant, layer))
        source = loaded if isinstance(loaded, str) else None
        result["mutant"] = mutant
    kill_after = config.get("kill_guest_server_after_seq")
    for seq, cell_id in config["trials"]:
        trial = session.run_cell(by_id[cell_id], layer, seq, a11y, source)
        trials.append(_progress(config, trial))
        if kill_after is not None and seq == kill_after:
            result["fault_injection"] = kill_guest_server(client, seq)
    result["stop"] = session.stop()
    result["mapping_check"] = session.judge_all(trials, by_id)
    result["trials"] = trials
    result["session_wall_s"] = round(time.monotonic() - started, 2)
    return result


def kill_guest_server(client: GuestClient, after_seq: int) -> dict[str, Any]:
    """Development only: SIGKILL the guest server, as the crash of run 622 ended it.

    Its systemd unit restarts it a few seconds later and, on the way, stops every process
    it launched, the probe and the tap included; the next trials then exercise the
    suite's restart handling (``guest_server_restart``, probe and tap relaunch). The
    request that kills the server never answers, so its error is the expected outcome.
    """
    out: dict[str, Any] = {"after_seq": after_seq, "t": time.time()}
    try:
        reply = client.execute(["bash", "-c", "kill -KILL $PPID"], timeout=30.0)
        out["reply"] = {k: reply.get(k) for k in ("returncode", "error")}
    except GuestError as exc:
        out["error"] = str(exc)[:200]
    return out


def tcp_probe(host: str, port: int, path: str) -> dict[str, Any]:
    client = GuestClient(host, port, timeout=5.0)
    out: dict[str, Any] = {"host": host, "port": port, "runner": gpu_free_assertion()}
    out["tcp_open"] = client.tcp_open(timeout=3.0)
    if out["tcp_open"]:
        try:
            status, payload, elapsed = client._request("GET", path, timeout=5.0)
            out["http_status"] = status
            out["bytes"] = len(payload)
            out["elapsed_s"] = round(elapsed, 4)
        except GuestError as exc:
            out["http_error"] = str(exc)[:200]
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    boot = commands.add_parser("boot-cycle")
    boot.add_argument("--config", type=Path, required=True)
    capture = commands.add_parser("rdev-capture")
    capture.add_argument("--config", type=Path, required=True)
    session = commands.add_parser("session")
    session.add_argument("--config", type=Path, required=True)
    probe = commands.add_parser("tcp-probe")
    probe.add_argument("--host", required=True)
    probe.add_argument("--port", type=int, default=5000)
    probe.add_argument("--path", default="/platform")
    probe.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command in ("boot-cycle", "rdev-capture", "session"):
        config = json.loads(args.config.read_text(encoding="utf-8"))
        out_path = Path(config["out"])
        handler = {"boot-cycle": boot_cycle, "rdev-capture": capture_cycle,
                   "session": session_cycle}[args.command]  # fmt: skip
        try:
            result = handler(config)
        except Exception:  # noqa: BLE001 - every failure is recorded, never swallowed
            result = {"cycle": config.get("cycle"), "error": traceback.format_exc()[-2000:]}
        result["runner_finished_at"] = _now()
        out_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
        return 0 if "error" not in result else 1
    result = tcp_probe(args.host, args.port, args.path)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
