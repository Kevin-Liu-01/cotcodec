"""Entry guard for the action-path suite (runs inside the OSWorld guest; python-xlib).

Preregistration section 6.2. Before and after every entry the guard checks:

(a) no key is pressed (``QueryKeymap``) and no pointer button is pressed;
(b) the keyboard LED mask equals the session baseline;
(c) the probe window is mapped, focused and covers 1920x1080 at (0, 0);
(d) no GNOME screen recording is running (no file under the screencast
    directory grows over ``GROWTH_WINDOW_S``);
(f) Num Lock's modifier, Mod2 (``NUMLOCK_MOD``), is in the logical modifier
    state (``QueryPointer``'s mask; with no key pressed, (a), a lock or latch);
    with (b), whose baseline has the Num Lock LED on in every session, Mod2 is
    locked (decision D43: the judge reads a key event the XRecord tap recorded
    without Mod2 as recorded while queued under a grab, so the guard must
    guarantee that every processed key event inside an entry carries it);

and before the entry, outside its window, it moves the pointer to the
catalog's ``guard.park_pointer`` (e), so an entry that moves the pointer always
produces motion.

One guest process per side of an entry, so an entry costs two extra
``/execute`` calls:

* ``pre``: check, park, then the probe's ``begin`` (which opens the entry
  window with a delimiter request; see ``probe.py``).
* ``post``: the probe's ``end`` (closes the window and returns the probe's
  event log, text and marker), then the declared side effect's restoration,
  then the check; on a violation it restores state (releases every pressed
  key and button through XTest, puts the LED mask back, re-activates the
  probe, Escape for a shell overlay) and checks again. It also returns the
  XRecord tap's new records from a byte offset.

Session warm-up (``warmup``, once per session before its first trial, outside
every entry window; preregistration design decision 31): one XTest press and
release of a keycode with no keysym, then a wait until the desktop shell
answers a D-Bus property read twice within ``IDLE_REPLY_S``. The X server's
master keyboard follows the last slave device that sent a key; the boot leaves
it on another device, and its switch to the XTest keyboard, at the session's
first XTest key event, re-sends the keymap and recomputes the modifier state.
Development run 549 showed a chord whose modifier was that first key lose it
(``chord_super_d``: the ``d`` press arrived with state 0). The warm-up makes
that switch happen before any entry; Stage 1 runs it once per boot.

Restoration per declared side effect (preregistration 6.2): ``screencast``:
the chord again while a screencast file grows (at most three times), then
Escape; ``closes_window``: the runner relaunches the probe if it is gone;
``shows_desktop`` and ``switches_window``: re-activate the probe;
``hot_corner``: Escape; ``lock_state``: none (the entry must leave the LED
at baseline).

Usage inside the guest: ``python3 -c <bootstrap> <b64> pre|post|check|warmup <json>``.
Prints one JSON object. Everything above ``main`` is pure Python.
"""

import contextlib
import json
import os
import socket
import sys
import time

GROWTH_WINDOW_S = 0.4
IDLE_REPLY_S = 0.05  # a shell D-Bus reply within this means its main loop is idle
IDLE_MAX_S = 5.0
SCREENCAST_DIRS = ("~/Videos/Screencasts", "~/Videos")
SCREENCAST_SUFFIXES = (".webm", ".mp4", ".mkv")
PARK_SETTLE_S = 0.03
CAPS_LED_BIT, NUM_LED_BIT = 1, 2
NUMLOCK_MOD = 0x10  # Mod2, the modifier Num_Lock is mapped to (the probe's numlock_mask)
CAPS_LOCK, NUM_LOCK, ESCAPE = 0xFFE5, 0xFF7F, 0xFF1B
SCREENCAST_CHORD = (0xFFE3, 0xFFE9, 0xFFE1, 0x72)  # Control_L, Alt_L, Shift_L, r


def pressed_keycodes(keymap_bytes):
    """Keycodes whose bit is set in a 32-byte QueryKeymap reply."""
    return [i * 8 + b for i, byte in enumerate(keymap_bytes) for b in range(8) if byte >> b & 1]


def pressed_buttons(mask):
    """Pointer buttons 1-5 pressed according to a state mask (Button1Mask = 1 << 8)."""
    return [n for n in range(1, 6) if mask & (1 << (7 + n))]


def violations(check, baseline_led):
    """The guard conditions a check fails, by letter."""
    out = []
    if check.get("keys") or check.get("buttons"):
        out.append("a")
    if check.get("led_mask") != baseline_led:
        out.append("b")
    probe = check.get("probe") or {}
    if not (probe.get("mapped") and probe.get("focused") and probe.get("covers_screen")):
        out.append("c")
    if (check.get("screencast") or {}).get("growing"):
        out.append("d")
    if not int(check.get("mods") or 0) & NUMLOCK_MOD:
        out.append("f")
    return out


def probe_call(sock_path, request, timeout=15.0):
    """One JSON request to the probe's control socket; None when the probe is absent."""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
            conn.settimeout(timeout)
            conn.connect(sock_path)
            conn.sendall((json.dumps(request) + "\n").encode("utf-8"))
            data = b""
            while not data.endswith(b"\n"):
                chunk = conn.recv(1 << 20)
                if not chunk:
                    break
                data += chunk
        return json.loads(data.decode("utf-8"))
    except (OSError, ValueError):
        return None


def screencast_sizes():
    sizes = {}
    for folder in SCREENCAST_DIRS:
        path = os.path.expanduser(folder)
        if not os.path.isdir(path):
            continue
        for name in os.listdir(path):
            if name.endswith(SCREENCAST_SUFFIXES):
                with contextlib.suppress(OSError):
                    sizes[os.path.join(folder, name)] = os.path.getsize(os.path.join(path, name))
    return sizes


def screencast_state():
    first = screencast_sizes()
    if not first:
        return {"files": {}, "growing": False}
    time.sleep(GROWTH_WINDOW_S)
    second = screencast_sizes()
    growing = [name for name, size in second.items() if size != first.get(name)]
    return {"files": second, "growing": bool(growing), "grown": growing}


def read_tap(path, offset):
    """New JSONL records of the XRecord tap from a byte offset (whole lines only)."""
    try:
        with open(path, "rb") as handle:
            handle.seek(offset)
            data = handle.read()
    except OSError as exc:
        return {"error": repr(exc)[:200], "offset": offset, "records": []}
    end = data.rfind(b"\n") + 1
    records = []
    for line in data[:end].splitlines():
        if line.strip():
            try:
                records.append(json.loads(line))
            except ValueError:
                records.append({"kind": "unparsed", "bytes": len(line)})
    return {"offset": offset + end, "records": records}


class Guard:
    def __init__(self):
        from Xlib import X, display
        from Xlib.ext import xtest

        self.X, self.xtest = X, xtest
        self.d = display.Display()
        self.root = self.d.screen().root

    def keycode(self, keysym):
        return self.d.keysym_to_keycode(keysym)

    def check(self, sock_path):
        keys = pressed_keycodes(self.d.query_keymap())
        pointer = self.root.query_pointer()
        probe = probe_call(sock_path, {"op": "state"})
        return {
            "keys": keys,
            "buttons": pressed_buttons(pointer.mask),
            "mods": pointer.mask & 0xFF,  # the logical modifier state (condition f)
            "led_mask": self.d.get_keyboard_control().led_mask,
            "pointer": [pointer.root_x, pointer.root_y],
            "probe": probe if probe and probe.get("ok") else {"absent": True},
            "screencast": screencast_state(),
        }

    def tap_keys(self, keysyms):
        X = self.X
        codes = [self.keycode(k) for k in keysyms]
        codes = [c for c in codes if c]
        for code in codes:
            self.xtest.fake_input(self.d, X.KeyPress, code)
            self.d.sync()
            time.sleep(0.02)
        for code in reversed(codes):
            self.xtest.fake_input(self.d, X.KeyRelease, code)
            self.d.sync()
            time.sleep(0.02)
        return len(codes)

    def warm_up(self, reserved):
        """Press and release one keycode that has no keysym (never the probe's reserved one)."""
        X = self.X
        info = self.d.display.info
        first = info.min_keycode
        rows = self.d.get_keyboard_mapping(first, info.max_keycode - first + 1)
        empty = [first + i for i, row in enumerate(rows) if not any(row) and first + i != reserved]
        if not empty:
            raise RuntimeError("no keycode without a keysym for the warm-up")
        code = empty[-1]
        self.xtest.fake_input(self.d, X.KeyPress, code)
        self.d.sync()
        time.sleep(0.02)
        self.xtest.fake_input(self.d, X.KeyRelease, code)
        self.d.sync()
        return code

    def park(self, x, y):
        self.xtest.fake_input(self.d, self.X.MotionNotify, x=x, y=y)
        self.d.sync()
        time.sleep(PARK_SETTLE_S)

    def release_all(self, check):
        X = self.X
        released = {"keys": [], "buttons": []}
        for code in check.get("keys") or []:
            self.xtest.fake_input(self.d, X.KeyRelease, code)
            released["keys"].append(code)
        for button in check.get("buttons") or []:
            self.xtest.fake_input(self.d, X.ButtonRelease, button)
            released["buttons"].append(button)
        self.d.sync()
        return released

    def fix_leds(self, led_mask, baseline):
        toggled = []
        for bit, keysym in ((CAPS_LED_BIT, CAPS_LOCK), (NUM_LED_BIT, NUM_LOCK)):
            if (led_mask ^ baseline) & bit:
                self.tap_keys([keysym])
                toggled.append(keysym)
        return toggled

    def restore_side_effects(self, effects, sock_path):
        done = []
        if "screencast" in effects:
            for _ in range(3):
                if not screencast_state()["growing"]:
                    break
                self.tap_keys(SCREENCAST_CHORD)
                done.append("screencast_chord")
                time.sleep(1.0)
            self.tap_keys([ESCAPE])
            done.append("escape")
        if "hot_corner" in effects:
            self.tap_keys([ESCAPE])
            done.append("escape")
        if effects & {"shows_desktop", "switches_window", "closes_window", "screencast"}:
            time.sleep(0.3)
            probe_call(sock_path, {"op": "activate"})
            done.append("activate")
        if effects:
            time.sleep(0.3)
        return done

    def restore(self, check, baseline_led, sock_path):
        actions = {"released": self.release_all(check)}
        actions["leds_toggled"] = self.fix_leds(check.get("led_mask", baseline_led), baseline_led)
        probe = check.get("probe") or {}
        if not probe.get("absent") and not (probe.get("focused") and probe.get("mapped")):
            self.tap_keys([ESCAPE])
            time.sleep(0.3)
            probe_call(sock_path, {"op": "activate"})
            actions["activated"] = True
            time.sleep(0.2)
        return actions


def shell_idle():
    """D-Bus round trips to GNOME Shell until two in a row answer within IDLE_REPLY_S."""
    import subprocess

    replies = []
    prompt = 0
    deadline = time.monotonic() + IDLE_MAX_S
    while prompt < 2 and time.monotonic() < deadline:
        started = time.monotonic()
        try:
            done = subprocess.run(
                ["gdbus", "call", "--session", "--dest", "org.gnome.Shell", "--object-path",
                 "/org/gnome/Shell", "--method", "org.freedesktop.DBus.Properties.Get",
                 "org.gnome.Shell", "ShellVersion"],
                capture_output=True, timeout=10,
            )  # fmt: skip
            ok = done.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            ok = False
        elapsed = round(time.monotonic() - started, 4)
        replies.append([elapsed, ok])
        if not ok:
            break
        prompt = prompt + 1 if elapsed < IDLE_REPLY_S else 0
    return {"replies": replies, "idle": prompt >= 2}


def run_warmup(config):
    guard = Guard()
    result = {"keycode": guard.warm_up(config.get("reserved"))}
    result["shell"] = shell_idle()
    result["check"] = guard.check(config["sock"]) if config.get("sock") else None
    return result


def run_pre(config):
    guard = Guard()
    sock = config["sock"]
    baseline = config["led_baseline"]
    result = {"check": guard.check(sock)}
    result["violations"] = violations(result["check"], baseline)
    if result["violations"]:
        result["restore"] = guard.restore(result["check"], baseline, sock)
        result["check_after_restore"] = guard.check(sock)
        result["violations_after_restore"] = violations(result["check_after_restore"], baseline)
    park = config["park"]
    guard.park(park[0], park[1])
    result["begin"] = probe_call(sock, {"op": "begin", "seq": config["seq"]})
    return result


def run_post(config):
    guard = Guard()
    sock = config["sock"]
    baseline = config["led_baseline"]
    result = {"end": probe_call(sock, {"op": "end", "seq": config["seq"]}, timeout=30.0)}
    effects = set(config.get("side_effects") or [])
    if effects:
        result["side_effect_restoration"] = guard.restore_side_effects(effects, sock)
    result["check"] = guard.check(sock)
    result["violations"] = violations(result["check"], baseline)
    if result["violations"]:
        result["restore"] = guard.restore(result["check"], baseline, sock)
        result["check_after_restore"] = guard.check(sock)
        result["violations_after_restore"] = violations(result["check_after_restore"], baseline)
    if config.get("tap_path"):
        result["tap"] = read_tap(config["tap_path"], int(config.get("tap_offset", 0)))
    return result


def main(argv):
    mode, config = argv[0], json.loads(argv[1])
    started = time.time()
    if mode == "pre":
        result = run_pre(config)
    elif mode == "post":
        result = run_post(config)
    elif mode == "check":
        guard = Guard()
        result = {"check": guard.check(config["sock"])}
        result["violations"] = violations(result["check"], config["led_baseline"])
    elif mode == "warmup":
        result = run_warmup(config)
    else:
        raise SystemExit("mode must be pre, post, check or warmup")
    result["mode"] = mode
    result["elapsed_s"] = round(time.time() - started, 4)
    # The guest server that ran this script (/execute): a different id after the entry than
    # before it means the server restarted during the entry (its systemd unit restarts it on
    # failure and stops every process it launched; development run 622).
    result["server_pid"] = os.getppid()
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main(sys.argv[1:])
