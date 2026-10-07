"""L0-fixed: the action-path suite's executor (runs inside the guest; python-xlib XTest).

One canonical IR action per process, sent as a base64-transported script through
OSWorld ``DesktopEnv.step`` (preregistration section 3). Every device event is
an XTest request on the guest's X server followed by a round trip, so the
server has processed it before the process exits.

* ``move``: one absolute motion.
* ``click``: motion to (x, y) if given; modifiers pressed in order; ``count``
  press/release pairs of the X button (1, 2, 3, 8 or 9), successive presses
  ``CLICK_GAP_S`` apart; modifiers released in reverse order.
* ``button_down`` / ``button_up``: motion if given, then one press or one
  release (the hold spans actions, so nothing releases it here).
* ``drag``: modifiers; motion to the first point (unless ``from_current``);
  press; motion along the path in ``DRAG_STEP_S`` steps over ``duration_ms``
  (consecutive identical integer points are skipped, since they move
  nothing); release at the last point; modifiers released.
* ``scroll``: motion if given; modifiers; one press/release of button 5 (down)
  or 4 (up) per ``wheel_y`` tick, then 7 (right) or 6 (left) per ``wheel_x``
  tick; modifiers released.
* ``key``: keys pressed in order, held ``KEY_HOLD_S`` (QEMU ``sendkey``'s
  hold in the R-dev reference capture), and released in reverse order.
  ``key_down`` / ``key_up`` press or release the listed keys and nothing else.
* ``type``: code points in order. ``\\n`` is Return and ``\\t`` is Tab. A code
  point whose keysym (Latin-1 value, else ``0x01000000 + cp``) is at index 0
  of a layout keycode is that key; at index 1, that key with Shift_L held.
  Any other code point goes through an executor-owned spare keycode remapped
  to ``[keysym, keysym]`` with a core ``ChangeKeyboardMapping`` before the
  press. Owned keycodes keep their mapping after the action (least recently
  used first when one must be reused; a keycode pressed less than
  ``REMAP_SETTLE_S`` ago is waited on before it is remapped), so no client
  can see a key event whose mapping has already been changed back.
* ``wait``: sleep. ``screenshot``: nothing. ``terminate`` never reaches the
  device.

A ``type`` action that changes the keymap first remaps every code point it
needs in one burst and waits for the desktop shell to answer on D-Bus before
typing (``shell_barrier``): the shell is the compositor, and it repaints
nothing while it rebuilds its keymap. Every action except ``wait`` ends with
the same barrier (the shell has processed the action's events; after a
keymap change, repeated until the shell answers promptly, ``shell_idle``),
re-damages every viewable top-level window so the compositor repaints each from
its current contents (``nudge_compositor``), then waits
until the screen has been unchanged for ``QUIET_S`` (0.25 s; the root window's
image read every 0.05 s, as ``/screenshot`` reads it), at least ``SETTLE_S``
(0.1 s, the default ``pyautogui.PAUSE``
that ends every upstream PyAutoGUI call) and at most ``QUIET_MAX_S`` (2 s)
after its device events (``screen_quiet``), so the screenshot
``DesktopEnv.step`` takes next shows the action's effect (development runs
486-499 showed screenshots one compositor frame behind without it).

Keysyms resolve to keycodes through the server's keyboard mapping read at the
start of each action, under the core protocol's keysym-list rules: a keysym at
index 0 of a keycode is that keycode; at index 1, that keycode with Shift_L;
otherwise an owned spare keycode. Unknown keysym names cannot reach here (the
IR rejects them), and zero spare keycodes raises when one is needed.
Modifiers this action pressed for a pointer action, and keys of a ``key``
chord, are released in ``finally`` if anything fails.

Owned spare keycodes are recorded in ``STATE_DIR/spares.json`` (keycode,
assigned keysym, last use); a keycode whose server row no longer matches its
record is treated as unassigned. The probe's reserved keycode is never empty
while it runs, so it is never owned.

Written for this repository; the spare-keycode technique follows gym-anything's
``_KEYBOARD_XLIB_PREAMBLE`` (MIT, Copyright (c) 2026 cmu-l3) in idea, not in
code. Everything above ``Executor`` is pure Python.
"""

import json
import os
import subprocess
import sys
import time

STATE_DIR = "/tmp/q2ap_l0"
KEY_GAP_S = 0.01
TYPE_GAP_S = 0.004
CLICK_HOLD_S = 0.02
CLICK_GAP_S = 0.06
MOTION_SETTLE_S = 0.02
DRAG_STEP_S = 0.016
DRAG_PRESS_SETTLE_S = 0.05
SCROLL_GAP_S = 0.03
KEY_HOLD_S = 0.1  # a key or chord is held this long before release (QEMU sendkey's R-dev hold)
SETTLE_S = 0.1  # every action lasts at least this: PyAutoGUI 0.9.54's default PAUSE
QUIET_S = 0.25  # ...and ends only after the screen has been unchanged this long
QUIET_STEP_S = 0.05  # how often the screen is read while waiting
QUIET_MAX_S = 2.0  # ...or this long after its device events, whichever is first
IDLE_REPLY_S = 0.05  # a shell D-Bus reply within this means its main loop is idle
REMAP_SETTLE_S = 0.3
SHIFT_L = 0xFFE1
RETURN, TAB = 0xFF0D, 0xFF09


def char_keysym(ch):
    """The keysym for one code point: its Latin-1 value, else 0x01000000 + cp."""
    cp = ord(ch)
    if ch == "\n":
        return RETURN
    if ch == "\t":
        return TAB
    if cp < 0x20 or 0x7F <= cp < 0xA0:
        raise ValueError(f"control character U+{cp:04X} cannot be typed")
    return cp if cp <= 0xFF else cp | 0x01000000


def core_group(row):
    """Index 0 and index 1 keysyms of group 1 under the core protocol's list rules."""
    keys = list(row)
    while keys and not keys[-1]:
        keys.pop()
    if len(keys) == 1:
        keys = [keys[0], 0]
    keys = (keys + [0, 0])[:2]
    first, second = keys
    if not second:
        if 0x61 <= first <= 0x7A or 0xE0 <= first <= 0xFE and first != 0xF7:
            return first, first - 0x20
        if 0x41 <= first <= 0x5A or 0xC0 <= first <= 0xDE and first != 0xD7:
            return first + 0x20, first
        return first, first
    return first, second


def find_keycode(keymap, keysym, exclude=()):
    """(keycode, shift) with ``keysym`` at index 0 (preferred) or 1 of a keycode, else None."""
    shifted = None
    for keycode in sorted(keymap):
        if keycode in exclude:
            continue
        first, second = core_group(keymap[keycode])
        if first == keysym:
            return keycode, False
        if second == keysym and shifted is None:
            shifted = (keycode, True)
    return shifted


def drag_points(start, path, duration_ms, step_s=DRAG_STEP_S):
    """Integer motion points along ``path`` after ``start``, with their times (s).

    Each segment gets time in proportion to its length and steps of about
    ``step_s``; every path vertex is hit exactly; consecutive duplicates are
    dropped (they would move nothing).
    """
    points = [tuple(start)] + [tuple(p) for p in path]
    segments = list(zip(points, points[1:], strict=False))
    lengths = [((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5 for a, b in segments]
    total = sum(lengths)
    duration = max(duration_ms, 0) / 1000.0
    out = []
    last = tuple(start)
    elapsed = 0.0
    for (a, b), length in zip(segments, lengths, strict=False):
        seg_time = duration * length / total if total else duration / max(1, len(segments))
        steps = max(1, int(round(seg_time / step_s)))
        for i in range(1, steps + 1):
            f = i / steps
            point = (int(round(a[0] + (b[0] - a[0]) * f)), int(round(a[1] + (b[1] - a[1]) * f)))
            if point != last:
                out.append((point, elapsed + seg_time * f))
                last = point
        elapsed += seg_time
    return out


class SparePool:
    """Executor-owned spare keycodes, persisted between action processes."""

    def __init__(self, keymap, path):
        self.path = path
        self.state = {"keycodes": [], "assigned": {}, "last_used": {}, "counter": 0}
        if os.path.exists(path):
            with open(path, encoding="utf-8") as handle:
                self.state = json.load(handle)
        else:
            self.state["keycodes"] = [kc for kc in sorted(keymap) if not any(keymap[kc])]
        for kc in list(self.state["assigned"]):
            keysym = self.state["assigned"][kc]
            if core_group(keymap.get(int(kc)) or [])[0] != keysym:
                del self.state["assigned"][kc]
        self.state["keycodes"] = [
            kc
            for kc in self.state["keycodes"]
            if not any(keymap.get(kc) or []) or str(kc) in self.state["assigned"]
        ]

    def owned(self):
        return set(self.state["keycodes"])

    def lookup(self, keysym):
        for kc, assigned in self.state["assigned"].items():
            if assigned == keysym:
                return int(kc)
        return None

    def allocate(self, keysym, protected=()):
        """The least recently used owned keycode outside ``protected``, now assigned to keysym.

        It is marked used at once, so the next allocation of the same burst takes
        another keycode.
        """
        free = [kc for kc in self.state["keycodes"] if kc not in protected]
        if not free:
            raise RuntimeError("zero spare keycodes: cannot type this code point")
        last = self.state["last_used"]
        keycode = min(free, key=lambda kc: (last.get(str(kc), [-1, 0])[0], kc))
        used_at = last.get(str(keycode), [-1, 0])[1]
        wait = REMAP_SETTLE_S - (time.time() - used_at)
        self.state["assigned"][str(keycode)] = keysym
        self.touch(keycode)
        return keycode, max(0.0, wait)

    def touch(self, keycode):
        self.state["counter"] += 1
        self.state["last_used"][str(keycode)] = [self.state["counter"], time.time()]

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(self.state, handle)
        os.replace(tmp, self.path)


class Executor:
    def __init__(self):
        from Xlib import X, display
        from Xlib.ext import xtest

        self.X, self.xtest = X, xtest
        self.d = display.Display()
        info = self.d.display.info
        first, last = info.min_keycode, info.max_keycode
        rows = self.d.get_keyboard_mapping(first, last - first + 1)
        self.keymap = {first + i: list(row) for i, row in enumerate(rows)}
        self.pool = SparePool(self.keymap, os.path.join(STATE_DIR, "spares.json"))
        self.held_keys = []
        self.held_buttons = []
        self.log = {"events": 0, "remaps": []}

    # --- primitives --------------------------------------------------------------------
    def _fake(self, kind, detail=0, x=0, y=0):
        if kind == self.X.MotionNotify:
            self.xtest.fake_input(self.d, kind, x=x, y=y)
        else:
            self.xtest.fake_input(self.d, kind, detail)
        self.d.sync()
        self.log["events"] += 1

    def motion(self, x, y):
        self._fake(self.X.MotionNotify, x=x, y=y)

    def key_press(self, keycode):
        self._fake(self.X.KeyPress, keycode)
        self.held_keys.append(keycode)

    def key_release(self, keycode):
        self._fake(self.X.KeyRelease, keycode)
        if keycode in self.held_keys:
            self.held_keys.remove(keycode)

    def button_press(self, button):
        self._fake(self.X.ButtonPress, button)
        self.held_buttons.append(button)

    def button_release(self, button):
        self._fake(self.X.ButtonRelease, button)
        if button in self.held_buttons:
            self.held_buttons.remove(button)

    def remap(self, keycode, keysym):
        self.d.change_keyboard_mapping(keycode, [[keysym, keysym]])
        self.d.sync()
        self.keymap[keycode] = [keysym, keysym]
        self.log["remaps"].append([keycode, keysym])

    def resolve(self, keysym, protected=()):
        """(keycode, shift) for a keysym, remapping an owned spare keycode if needed."""
        found = find_keycode(self.keymap, keysym, exclude=self.pool.owned())
        if found is not None:
            return found
        keycode = self.pool.lookup(keysym)
        if keycode is None:
            keycode, wait = self.pool.allocate(keysym, protected)
            if wait:
                time.sleep(wait)
            self.remap(keycode, keysym)
        return keycode, False

    def shift_keycode(self):
        found = find_keycode(self.keymap, SHIFT_L)
        if found is None or found[1]:
            raise RuntimeError("no keycode carries Shift_L at index 0")
        return found[0]

    # --- IR ops ------------------------------------------------------------------------
    def press_keys(self, keysyms):
        """Press keysyms in order (Shift_L first for any shifted one); returns keycodes pressed."""
        pressed = []
        resolved = [self.resolve(k) for k in keysyms]
        if any(shift for _, shift in resolved) and SHIFT_L not in keysyms:
            shift = self.shift_keycode()
            self.key_press(shift)
            pressed.append(shift)
            time.sleep(KEY_GAP_S)
        for keycode, _ in resolved:
            self.key_press(keycode)
            pressed.append(keycode)
            if keycode in self.pool.owned():
                self.pool.touch(keycode)
            time.sleep(KEY_GAP_S)
        return pressed

    def release_keys(self, keycodes):
        for keycode in reversed(keycodes):
            self.key_release(keycode)
            time.sleep(KEY_GAP_S)

    def with_modifiers(self, modifiers, body):
        pressed = self.press_keys(modifiers) if modifiers else []
        try:
            body()
        finally:
            self.release_keys(pressed)

    def click(self, action):
        if action.get("x") is not None:
            self.motion(action["x"], action["y"])
            time.sleep(MOTION_SETTLE_S)
        button = action.get("button", 1)
        count = action.get("count", 1)

        def body():
            for index in range(count):
                self.button_press(button)
                time.sleep(CLICK_HOLD_S)
                self.button_release(button)
                if index < count - 1:
                    time.sleep(CLICK_GAP_S)

        self.with_modifiers(action.get("modifiers") or [], body)

    def drag(self, action):
        path = [tuple(p) for p in action["path"]]
        button = action.get("button", 1)

        def body():
            if action.get("from_current"):
                pointer = self.d.screen().root.query_pointer()
                start = (pointer.root_x, pointer.root_y)
                rest = path
            else:
                start, rest = path[0], path[1:]
                self.motion(start[0], start[1])
                time.sleep(MOTION_SETTLE_S)
            self.button_press(button)
            time.sleep(DRAG_PRESS_SETTLE_S)
            began = time.monotonic()
            for (x, y), at in drag_points(start, rest, action.get("duration_ms", 500)):
                delay = began + at - time.monotonic()
                if delay > 0:
                    time.sleep(delay)
                self.motion(x, y)
            time.sleep(DRAG_PRESS_SETTLE_S)
            self.button_release(button)

        self.with_modifiers(action.get("modifiers") or [], body)

    def scroll(self, action):
        if action.get("x") is not None:
            self.motion(action["x"], action["y"])
            time.sleep(MOTION_SETTLE_S)

        def body():
            wheel_y = action.get("wheel_y") or 0
            wheel_x = action.get("wheel_x") or 0
            for button, ticks in (
                (5 if wheel_y > 0 else 4, abs(wheel_y)),
                (7 if wheel_x > 0 else 6, abs(wheel_x)),
            ):
                for _ in range(ticks):
                    self.button_press(button)
                    self.button_release(button)
                    time.sleep(SCROLL_GAP_S)

        self.with_modifiers(action.get("modifiers") or [], body)

    def key(self, keysyms):
        pressed = []
        try:
            pressed = self.press_keys(keysyms)
            time.sleep(KEY_HOLD_S)
        finally:
            self.release_keys(pressed)

    def shell_barrier(self):
        """Wait until the desktop shell's main loop answers on D-Bus (after keymap changes).

        Every keymap change makes GNOME Shell, the compositor, rebuild its keymap;
        while it does, the screen is not repainted (development runs 486-493:
        screenshots after Unicode typing showed the first character only). A
        property read on org.gnome.Shell is answered from the shell's main loop,
        after the X events already queued there.
        """
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
        self.log.setdefault("barriers", []).append([elapsed, ok])
        return elapsed if ok else None

    def shell_idle(self):
        """Repeat the barrier until the shell answers within IDLE_REPLY_S (at most 5 s).

        A busy shell (rebuilding its keymap) answers late; two consecutive prompt
        answers mean it has drained the work queued before the first call.
        """
        deadline = time.monotonic() + 5.0
        prompt = 0
        while prompt < 2 and time.monotonic() < deadline:
            elapsed = self.shell_barrier()
            if elapsed is None:
                return
            prompt = prompt + 1 if elapsed < IDLE_REPLY_S else 0

    def nudge_compositor(self):
        """Re-damage every viewable top-level window (no pixel changes), so the compositor
        repaints from each window's current contents.

        Development runs 504-524: after typing, the probe's last drawing (made 4 ms
        before the executor's last event) stayed off the screen for good (still
        missing 1.9 s later, when the next entry's drawing finally showed it), in
        about 4% of typing trials, always exactly the last draw: the compositor
        consumed that damage without repainting it. A Stage-1 screenshot would be
        stale the same way. XDamage DamageAdd marks the windows damaged again;
        XFixes CreateRegion supplies the region (python-xlib has no binding, so
        the two requests are encoded here from the protocol).
        """
        from Xlib import X
        from Xlib.protocol import rq, structs

        class CreateRegion(rq.Request):
            _request = rq.Struct(
                rq.Card8("opcode"), rq.Opcode(5), rq.RequestLength(), rq.Card32("region"),
                rq.List("rectangles", structs.Rectangle),
            )  # fmt: skip

        class DestroyRegion(rq.Request):
            _request = rq.Struct(
                rq.Card8("opcode"), rq.Opcode(10), rq.RequestLength(), rq.Card32("region")
            )

        try:
            self.d.xfixes_query_version()
            self.d.damage_query_version()
            xfixes = self.d.get_extension_major("XFIXES")
            nudged = 0
            for window in self.d.screen().root.query_tree().children:
                try:
                    if window.get_attributes().map_state != X.IsViewable:
                        continue
                    geometry = window.get_geometry()
                except Exception:  # noqa: BLE001 - windows can vanish meanwhile
                    continue
                region = self.d.display.allocate_resource_id()
                CreateRegion(
                    display=self.d.display, opcode=xfixes, region=region,
                    rectangles=[{"x": 0, "y": 0, "width": geometry.width,
                                 "height": geometry.height}],
                )  # fmt: skip
                # python-xlib's DamageAdd fields are misnamed: the protocol's
                # (drawable, region) travel as (repair, parts).
                window.damage_add(window.id, region)
                DestroyRegion(display=self.d.display, opcode=xfixes, region=region)
                nudged += 1
            self.d.sync()
            self.log["nudged"] = nudged
        except Exception as exc:  # noqa: BLE001 - recorded; the quiet wait still runs
            self.log["nudged"] = repr(exc)[:200]

    def screen_quiet(self, started):
        """Return once the screen has been unchanged for QUIET_S, as a screenshot reads it.

        The compositor paints a client's drawing one or more frames later
        (development runs 489-499: the probe's marker reached the screen 72 ms
        after it was drawn at the median, 110 ms at the 99th percentile; run 520:
        after typing, a final draw made before the action's last event was still
        not on screen 0.26 s later). XDamage on the root window did not report the
        compositor's frames (one notify per action, runs 509-520), so the screen
        is read directly: the root window's image, as ``/screenshot`` reads it,
        every QUIET_STEP_S, until it has not changed for QUIET_S; at least
        SETTLE_S after ``started``, at most QUIET_MAX_S.
        """
        import hashlib

        from Xlib import X

        root = self.d.screen().root
        geometry = root.get_geometry()

        def grab():
            image = root.get_image(0, 0, geometry.width, geometry.height, X.ZPixmap, 0xFFFFFFFF)
            return hashlib.md5(image.data).digest()

        last_hash = grab()
        last_change = time.monotonic()
        grabs, changes = 1, 0
        while True:
            now = time.monotonic()
            if now - started >= QUIET_MAX_S:
                break
            if now - started >= SETTLE_S and now - last_change >= QUIET_S:
                break
            time.sleep(QUIET_STEP_S)
            current = grab()
            grabs += 1
            if current != last_hash:
                last_hash, last_change = current, time.monotonic()
                changes += 1
        self.log["quiet"] = {
            "grabs": grabs,
            "changes": changes,
            "waited_s": round(time.monotonic() - started, 4),
            "capped": time.monotonic() - started >= QUIET_MAX_S,
        }

    def needs_remap(self, ch):
        keysym = char_keysym(ch)
        owned = self.pool.owned()
        return find_keycode(self.keymap, keysym, exclude=owned) is None

    def segments(self, text):
        """Cut text so each piece needs at most one owned keycode per remapped code point."""
        limit = max(1, len(self.pool.owned()))
        pieces, current, distinct = [], [], set()
        for ch in text:
            if self.needs_remap(ch) and ch not in distinct and len(distinct) >= limit:
                pieces.append("".join(current))
                current, distinct = [], set()
            if self.needs_remap(ch):
                distinct.add(ch)
            current.append(ch)
        if current:
            pieces.append("".join(current))
        return pieces

    def type_text(self, text):
        for piece in self.segments(text):
            self.type_segment(piece)

    def type_segment(self, text):
        # Remap every code point this piece needs first, in one burst (no keycode the
        # piece uses is evicted), and let the shell absorb the keymap changes before
        # the first key event.
        before = len(self.log["remaps"])
        protected = set()
        for ch in dict.fromkeys(text):
            keycode, _ = self.resolve(char_keysym(ch), protected)
            protected.add(keycode)
        if len(self.log["remaps"]) > before:
            self.shell_idle()
        shift = None
        for ch in text:
            keycode, shifted = self.resolve(char_keysym(ch))
            if shifted:
                shift = shift or self.shift_keycode()
                self.key_press(shift)
            self.key_press(keycode)
            self.key_release(keycode)
            if shifted:
                self.key_release(shift)
            if keycode in self.pool.owned():
                self.pool.touch(keycode)
            time.sleep(TYPE_GAP_S)

    def run(self, action):
        op = action["op"]
        try:
            if op == "move":
                self.motion(action["x"], action["y"])
            elif op == "click":
                self.click(action)
            elif op == "button_down":
                if action.get("x") is not None:
                    self.motion(action["x"], action["y"])
                    time.sleep(MOTION_SETTLE_S)
                self.button_press(action["button"])
                self.held_buttons = []
            elif op == "button_up":
                if action.get("x") is not None:
                    self.motion(action["x"], action["y"])
                    time.sleep(MOTION_SETTLE_S)
                self.button_release(action["button"])
            elif op == "drag":
                self.drag(action)
            elif op == "scroll":
                self.scroll(action)
            elif op == "key":
                self.key([int(k) for k in action["keysyms"]])
            elif op == "key_down":
                self.press_keys([int(k) for k in action["keysyms"]])
                self.held_keys = []
            elif op == "key_up":
                for keysym in action["keysyms"]:
                    keycode, _ = self.resolve(int(keysym))
                    self.key_release(keycode)
                    time.sleep(KEY_GAP_S)
            elif op == "type":
                self.type_text(action["text"])
            elif op == "wait":
                time.sleep(action["ms"] / 1000.0)
            elif op == "screenshot":
                pass
            else:
                raise ValueError(f"L0-fixed has no device action for {op!r}")
            self.log["t_events_done"] = time.time()
            if op != "wait":
                ended = time.monotonic()
                if self.log["remaps"]:
                    self.shell_idle()
                else:
                    self.shell_barrier()
                self.nudge_compositor()
                self.screen_quiet(ended)
        finally:
            for keycode in list(reversed(self.held_keys)):
                self.key_release(keycode)
            for button in list(reversed(self.held_buttons)):
                self.button_release(button)
            self.pool.save()
        return self.log


def run_action(action):
    started = time.time()
    log = Executor().run(action)
    log["op"] = action["op"]
    log["elapsed_s"] = round(time.time() - started, 4)
    log["t_end"] = time.time()
    print(json.dumps(log, sort_keys=True))


if __name__ == "__main__":
    run_action(json.loads(sys.argv[1]))
