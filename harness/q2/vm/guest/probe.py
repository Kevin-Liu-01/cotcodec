"""Guest probe for the action-path suite (runs inside the OSWorld guest; python-xlib).

One fullscreen X window (1920x1080 at (0, 0)) that records every input event
it receives, keeps a text buffer under the catalog's buffer rules, and shows a
marker block that encodes the current entry's sequence number and the CRC-16
of the text buffer, so the runner can check that a screenshot shows the
probe's final state (preregistration section 5, condition 3).

Event log. Every KeyPress, KeyRelease, ButtonPress, ButtonRelease and
MotionNotify delivered to the window is logged with the keycode or button, the
state mask, the root position and the server time. Key events also carry the
keysym at index 0 of the keycode and the keysym selected for the event's
state, both resolved with the probe's own copy of the keyboard mapping, which
it re-reads on every MappingNotify (python-xlib clients see core
MappingNotify; ``refresh`` reads the notified range at once).

Text buffer (the catalog's ``probe_buffer_rules``). For a KeyPress whose state
has no Control, Mod1 or Mod4 bit: ``Return`` and ``KP_Enter`` append ``\\n``,
``Tab`` appends ``\\t``, ``BackSpace`` deletes the last code point, and a
keysym that encodes a printable code point appends it (``keysym_text``:
Latin-1 keysyms, Unicode keysyms ``0x01000000 + cp``, and the keypad keysyms
X's ``XLookupString`` maps to ASCII). Every other key leaves the buffer
unchanged. The keysym is selected from the keycode's row under the X11 core
protocol's rules (``select_keysym``): group from the state, Shift and Lock,
and Num_Lock for keypad keysyms.

Entry windows. The runner brackets each entry with ``begin`` and ``end``
commands. For each, the probe sends a core ``ChangeKeyboardMapping`` request
for one reserved spare keycode ``R`` (a *delimiter*: row
``[BEGIN_MAGIC or END_MAGIC, SEQ_BASE + seq]``), waits for the server's
round-trip reply and processes its own event queue up to the MappingNotify
that request caused. Because the X server processes requests and device
events in one order, and delivers events to each client in that order, every
event before the delimiter's MappingNotify happened before the request, and
every event after it happened after. The XRecord tap records the same request
in its stream (``mapping_request`` on keycode ``R``), so both channels split
entries at exactly the same point without timestamps. ``R`` is never pressed
and never empty while the probe runs (a reserve row is written at start), so
the executor's spare-keycode pool never contains it.

Marker block. ``MARKER_BITS`` cells of ``CELL`` x ``CELL`` pixels, left to
right from ``MARKER_ORIGIN``: 8 sync bits, 24 bits of sequence number, 16 bits
of CRC-16/CCITT-FALSE over the buffer's UTF-8 bytes, and an 8-bit check (the
CRC-8 of the 40 data bits). Black is 1, white 0. It sits in the top rows,
clear of every point the catalog uses (the runner pastes the cursor image at
the pointer position, so a cell under the cursor would be unreadable), and
the runner only decompresses the first rows of the PNG to read it.

Control. A UNIX socket in the state directory takes one JSON command per
connection and answers one JSON line: ``ping``, ``begin``, ``end``, ``state``,
``activate`` and ``quit``. ``ready.json`` is written once the window is
mapped.

Usage inside the guest: ``python3 -c <bootstrap> <b64> <state_dir>``.

Written for this repository from the X11 core protocol specification
(keyboard encoding, ChangeKeyboardMapping, MappingNotify) and python-xlib's
public API. Everything above ``main`` is pure Python, so the runner and the
tests import it without python-xlib.
"""

import contextlib
import json
import os
import select
import socket
import sys
import time

SCREEN = (1920, 1080)
CELL = 16
MARKER_ORIGIN = (512, 32)
SYNC_BITS = (1, 0, 1, 1, 0, 0, 1, 0)
MARKER_BITS = 8 + 24 + 16 + 8
MARKER_ROWS = MARKER_ORIGIN[1] + CELL  # PNG rows the decoder must reconstruct

BEGIN_MAGIC = 0x0100F0B0
END_MAGIC = 0x0100F0E0
RESERVE_MAGIC = 0x0100F0A0
SEQ_BASE = 0x01100000
MAX_SEQ = 0xFFFF

SHIFT, LOCK, CONTROL, MOD1, MOD4 = 1, 2, 4, 8, 64
SHORTCUT_MASK = CONTROL | MOD1 | MOD4
KEYSYM_RETURN, KEYSYM_KP_ENTER, KEYSYM_TAB, KEYSYM_BACKSPACE = 0xFF0D, 0xFF8D, 0xFF09, 0xFF08
# Keypad keysyms XLookupString maps to ASCII (KP_Space, KP_Equal, KP_Multiply ... KP_9).
KEYPAD_TEXT = {
    0xFF80: " ",
    0xFFBD: "=",
    0xFFAA: "*",
    0xFFAB: "+",
    0xFFAC: ",",
    0xFFAD: "-",
    0xFFAE: ".",
    0xFFAF: "/",
}
KEYPAD_TEXT.update({0xFFB0 + d: str(d) for d in range(10)})


def crc16(data):
    """CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF, no reflection, no xor-out)."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def crc8(bits):
    """CRC-8 (poly 0x07, init 0) over a bit sequence, most significant bit first."""
    crc = 0
    for bit in bits:
        top = (crc >> 7) & 1
        crc = (crc << 1) & 0xFF
        if top ^ bit:
            crc ^= 0x07
    return crc


def _bits(value, width):
    return [(value >> (width - 1 - i)) & 1 for i in range(width)]


def marker_bits(seq, text_crc):
    """The marker's cells, left to right (1 = black)."""
    if not 0 <= seq <= 0xFFFFFF or not 0 <= text_crc <= 0xFFFF:
        raise ValueError("marker value out of range")
    data = _bits(seq, 24) + _bits(text_crc, 16)
    return list(SYNC_BITS) + data + _bits(crc8(data), 8)


def parse_marker_bits(bits):
    """(seq, crc) from decoded cells, or None when sync or check bits disagree."""
    if len(bits) != MARKER_BITS or tuple(bits[:8]) != SYNC_BITS:
        return None
    data = list(bits[8:48])
    check = 0
    for bit in bits[48:]:
        check = (check << 1) | bit
    if crc8(data) != check:
        return None
    seq = 0
    for bit in data[:24]:
        seq = (seq << 1) | bit
    crc = 0
    for bit in data[24:]:
        crc = (crc << 1) | bit
    return seq, crc


def marker_cells(seq, text_crc):
    """Rectangles (x, y, w, h) of the black cells."""
    x0, y0 = MARKER_ORIGIN
    return [
        (x0 + i * CELL, y0, CELL, CELL) for i, bit in enumerate(marker_bits(seq, text_crc)) if bit
    ]


def text_crc(text):
    return crc16(text.encode("utf-8", "surrogatepass"))


def _is_upper_lower(keysym):
    """(lower, upper) of an alphabetic Latin-1 or Unicode keysym, else None."""
    if 0x41 <= keysym <= 0x5A:
        return keysym + 0x20, keysym
    if 0x61 <= keysym <= 0x7A:
        return keysym, keysym - 0x20
    if 0xC0 <= keysym <= 0xDE and keysym != 0xD7:
        return keysym + 0x20, keysym
    if 0xE0 <= keysym <= 0xFE and keysym != 0xF7:
        return keysym, keysym - 0x20
    if keysym >= 0x01000100:
        ch = chr(keysym - 0x01000000)
        lower, upper = ch.lower(), ch.upper()
        if len(lower) == 1 and len(upper) == 1 and lower != upper:
            return 0x01000000 + ord(lower), 0x01000000 + ord(upper)
    return None


def core_group(row, group):
    """One group of a keycode row under the core protocol's list rules: (first, second)."""
    keys = list(row)
    while keys and not keys[-1]:
        keys.pop()
    if len(keys) == 1:
        keys = [keys[0], 0, keys[0], 0]
    elif len(keys) == 2:
        keys = keys + keys
    keys = (keys + [0, 0, 0, 0])[:4]
    first, second = (keys[2], keys[3]) if group else (keys[0], keys[1])
    if not second:
        pair = _is_upper_lower(first)
        if pair is not None:
            return pair
        return first, first
    return first, second


def is_keypad(keysym):
    return 0xFF80 <= keysym <= 0xFFBD or 0x11000000 <= keysym <= 0x1100FFFF


def select_keysym(row, state, numlock_mask=0):
    """The keysym a core client uses for this key event (X11 protocol, Keyboard Encoding)."""
    group = 1 if (state >> 13) & 3 else 0
    first, second = core_group(row, group)
    shift = bool(state & SHIFT)
    lock = bool(state & LOCK)
    if numlock_mask and state & numlock_mask and is_keypad(second):
        return first if shift else second
    if not shift and not lock:
        return first
    if not shift and lock:
        pair = _is_upper_lower(first)
        return pair[1] if pair else first
    if shift and lock:
        pair = _is_upper_lower(second)
        return pair[1] if pair else second
    return second


def keysym_text(keysym):
    """The printable text a keysym produces, or '' (no text)."""
    if 0x20 <= keysym <= 0x7E or 0xA0 <= keysym <= 0xFF:
        return chr(keysym)
    if 0x01000020 <= keysym <= 0x0110FFFF:
        cp = keysym - 0x01000000
        if cp < 0x20 or 0x7F <= cp < 0xA0 or 0xD800 <= cp <= 0xDFFF:
            return ""
        return chr(cp)
    return KEYPAD_TEXT.get(keysym, "")


def apply_key(buffer, keysym, state):
    """Apply one KeyPress to the text buffer (a list of code points); returns the change."""
    if state & SHORTCUT_MASK:
        return ""
    if keysym in (KEYSYM_RETURN, KEYSYM_KP_ENTER):
        buffer.append("\n")
        return "\n"
    if keysym == KEYSYM_TAB:
        buffer.append("\t")
        return "\t"
    if keysym == KEYSYM_BACKSPACE:
        if buffer:
            buffer.pop()
            return "\b"
        return ""
    text = keysym_text(keysym)
    buffer.extend(text)
    return text


def delimiter_row(kind, seq):
    if not 0 <= seq <= MAX_SEQ:
        raise ValueError("sequence number out of range")
    magic = {"begin": BEGIN_MAGIC, "end": END_MAGIC}[kind]
    return [magic, SEQ_BASE + seq]


def parse_delimiter(row):
    """('begin'|'end'|'reserve', seq) for a delimiter row, else None."""
    if not row:
        return None
    if row[0] == RESERVE_MAGIC:
        return "reserve", None
    if row[0] in (BEGIN_MAGIC, END_MAGIC) and len(row) >= 2 and row[1] >= SEQ_BASE:
        return ("begin" if row[0] == BEGIN_MAGIC else "end"), row[1] - SEQ_BASE
    return None


class Probe:
    """The window, its event log and its buffer (X calls only in methods that need them)."""

    EVENT_KINDS = {
        2: "KeyPress",
        3: "KeyRelease",
        4: "ButtonPress",
        5: "ButtonRelease",
        6: "MotionNotify",
    }

    def __init__(self, state_dir, reserved=None):
        from Xlib import X, Xatom, Xutil, display

        self.X, self.Xatom = X, Xatom
        self.state_dir = state_dir
        self.d = display.Display()
        self.screen = self.d.screen()
        self.root = self.screen.root
        info = self.d.display.info
        self.min_kc, self.max_kc = info.min_keycode, info.max_keycode
        self.keymap = {}
        self.refresh(self.min_kc, self.max_kc - self.min_kc + 1)
        spares = [kc for kc, row in sorted(self.keymap.items()) if not any(row)]
        if reserved is not None:
            # A relaunch keeps the session's reserved keycode (empty or holding a delimiter).
            row = self.keymap.get(reserved) or []
            if any(row) and parse_delimiter(row) is None:
                raise SystemExit(f"keycode {reserved} is in use; it cannot be the delimiter key")
            self.reserved = reserved
        elif len(spares) < 2:
            raise SystemExit("the probe needs two spare keycodes (one is reserved)")
        else:
            self.reserved = spares[-1]
        self.spares_at_start = len(spares)
        self.numlock_mask = self._numlock_mask()
        self.seq = 0
        self.buffer = []
        self.window_events = None  # list while an entry is open
        self.counters = {
            "mapping_notify": 0,
            "delimiters": 0,
            "delete_requests": 0,
            "focus_in": 0,
            "focus_out": 0,
            "redraws": 0,
            "outside_events": 0,
        }
        self.drawn = None
        self.atoms = {
            name: self.d.intern_atom(name)
            for name in (
                "WM_PROTOCOLS",
                "WM_DELETE_WINDOW",
                "_NET_WM_STATE",
                "_NET_WM_STATE_FULLSCREEN",
                "_NET_ACTIVE_WINDOW",
                "_NET_WM_BYPASS_COMPOSITOR",
                "_NET_WM_NAME",
                "UTF8_STRING",
            )
        }
        mask = (
            X.KeyPressMask
            | X.KeyReleaseMask
            | X.ButtonPressMask
            | X.ButtonReleaseMask
            | X.PointerMotionMask
            | X.ExposureMask
            | X.StructureNotifyMask
            | X.FocusChangeMask
        )
        self.win = self.root.create_window(
            0,
            0,
            SCREEN[0],
            SCREEN[1],
            0,
            self.screen.root_depth,
            X.InputOutput,
            X.CopyFromParent,
            background_pixel=self.screen.white_pixel,
            event_mask=mask,
        )
        self.win.set_wm_name("cotcodec-q2ap-probe")
        self.win.change_property(
            self.atoms["_NET_WM_NAME"], self.atoms["UTF8_STRING"], 8, b"cotcodec-q2ap-probe"
        )
        self.win.set_wm_class("q2ap-probe", "Q2apProbe")
        self.win.set_wm_hints(flags=Xutil.InputHint, input=1)
        self.win.set_wm_protocols([self.atoms["WM_DELETE_WINDOW"]])
        self.win.change_property(
            self.atoms["_NET_WM_STATE"], Xatom.ATOM, 32, [self.atoms["_NET_WM_STATE_FULLSCREEN"]]
        )
        self.win.change_property(self.atoms["_NET_WM_BYPASS_COMPOSITOR"], Xatom.CARDINAL, 32, [1])
        self.black = self.win.create_gc(foreground=self.screen.black_pixel)
        self.white = self.win.create_gc(foreground=self.screen.white_pixel)
        # Keep the reserved keycode non-empty for the whole session.
        self.d.change_keyboard_mapping(self.reserved, [[RESERVE_MAGIC, RESERVE_MAGIC]])
        self.win.map()
        self.d.sync()

    # --- X helpers -------------------------------------------------------------------
    def _numlock_mask(self):
        mapping = self.d.get_modifier_mapping()
        for index, keycodes in enumerate(mapping):
            for keycode in keycodes:
                if keycode and 0xFF7F in (self.keymap.get(keycode) or []):
                    return 1 << index
        return 0

    def refresh(self, first, count):
        last = min(first + count - 1, self.max_kc)
        first = max(first, self.min_kc)
        if last < first:
            return
        rows = self.d.get_keyboard_mapping(first, last - first + 1)
        for i, row in enumerate(rows):
            self.keymap[first + i] = list(row)

    def activate(self):
        from Xlib.protocol import event

        X = self.X
        self.win.map()
        self.win.configure(stack_mode=X.Above)
        message = event.ClientMessage(
            window=self.win,
            client_type=self.atoms["_NET_ACTIVE_WINDOW"],
            data=(32, [2, X.CurrentTime, 0, 0, 0]),
        )
        self.root.send_event(
            message, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask
        )
        self.d.sync()
        time.sleep(0.05)
        # Not viewable yet is possible here; the guard reports focus either way.
        with contextlib.suppress(Exception):
            self.win.set_input_focus(X.RevertToParent, X.CurrentTime)
        self.d.sync()

    def draw_marker(self):
        crc = text_crc("".join(self.buffer))
        x0, y0 = MARKER_ORIGIN
        self.win.fill_rectangle(
            self.white, x0 - CELL, y0 - CELL // 2, (MARKER_BITS + 2) * CELL, 2 * CELL
        )
        cells = marker_cells(self.seq, crc)
        if cells:
            self.win.poly_fill_rectangle(self.black, cells)
        self.d.flush()
        self.drawn = (self.seq, crc)
        self.counters["redraws"] += 1

    def state(self):
        X = self.X
        focus = self.d.get_input_focus().focus
        focus_id = focus if isinstance(focus, int) else focus.id
        attributes = self.win.get_attributes()
        geometry = self.win.get_geometry()
        origin = self.root.translate_coords(self.win, 0, 0)
        pointer = self.root.query_pointer()
        return {
            "window": self.win.id,
            "mapped": attributes.map_state == X.IsViewable,
            "focused": focus_id == self.win.id,
            "focus": focus_id,
            "geometry": [origin.x, origin.y, geometry.width, geometry.height],
            "covers_screen": [origin.x, origin.y, geometry.width, geometry.height]
            == [0, 0, SCREEN[0], SCREEN[1]],
            "pointer": [pointer.root_x, pointer.root_y],
            "pointer_mask": pointer.mask,
        }

    # --- events ----------------------------------------------------------------------
    def handle(self, ev):
        X = self.X
        kind = self.EVENT_KINDS.get(ev.type)
        if kind is not None:
            record = [kind, ev.detail, ev.state, ev.root_x, ev.root_y, ev.time]
            if kind in ("KeyPress", "KeyRelease"):
                row = self.keymap.get(ev.detail) or []
                keysym = select_keysym(row, ev.state, self.numlock_mask)
                record += [row[0] if row else 0, keysym]
                if kind == "KeyPress":
                    change = apply_key(self.buffer, keysym, ev.state)
                    record.append(change)
                    if change:
                        self.draw_marker()
            if self.window_events is not None:
                self.window_events.append(record)
            else:
                self.counters["outside_events"] += 1
            return None
        if ev.type == X.MappingNotify:
            self.counters["mapping_notify"] += 1
            if ev.request == 1:  # MappingKeyboard
                self.refresh(ev.first_keycode, ev.count)
                if ev.first_keycode == self.reserved and ev.count == 1:
                    return parse_delimiter(self.keymap.get(self.reserved))
            elif ev.request == 0:  # MappingModifier
                self.numlock_mask = self._numlock_mask()
            return None
        if ev.type == X.Expose and ev.count == 0:
            self.draw_marker()
        elif ev.type == X.ClientMessage:
            if ev.client_type == self.atoms["WM_PROTOCOLS"]:
                self.counters["delete_requests"] += 1  # the probe stays open
        elif ev.type == X.FocusIn:
            self.counters["focus_in"] += 1
        elif ev.type == X.FocusOut:
            self.counters["focus_out"] += 1
        return None

    def drain(self):
        while self.d.pending_events():
            self.handle(self.d.next_event())

    def delimit(self, kind, seq):
        """Send a delimiter request and process events up to its MappingNotify."""
        self.drain()
        self.d.change_keyboard_mapping(self.reserved, [delimiter_row(kind, seq)])
        self.d.sync()
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            if not self.d.pending_events():
                self.d.sync()
                if not self.d.pending_events():
                    time.sleep(0.005)
                    continue
            found = self.handle(self.d.next_event())
            if found == (kind, seq):
                self.counters["delimiters"] += 1
                return True
        return False

    # --- commands --------------------------------------------------------------------
    def command(self, request):
        op = request.get("op")
        if op == "ping":
            return {"ok": True, "seq": self.seq}
        if op == "state":
            self.drain()
            return {"ok": True, **self.state()}
        if op == "activate":
            self.activate()
            self.drain()
            return {"ok": True, **self.state()}
        if op == "begin":
            seq = int(request["seq"])
            self.window_events = None
            if not self.delimit("begin", seq):
                return {"ok": False, "error": "begin delimiter never arrived"}
            self.seq = seq
            self.buffer = []
            self.window_events = []
            self.draw_marker()
            return {"ok": True, "seq": seq, "drawn": list(self.drawn), "state": self.state()}
        if op == "end":
            seq = int(request["seq"])
            if seq != self.seq or self.window_events is None:
                return {"ok": False, "error": f"end {seq} without begin"}
            ok = self.delimit("end", seq)
            events, self.window_events = self.window_events, None
            text = "".join(self.buffer)
            return {
                "ok": ok,
                "seq": seq,
                "events": events,
                "text": text,
                "crc": text_crc(text),
                "drawn": list(self.drawn) if self.drawn else None,
                "state": self.state(),
                "counters": dict(self.counters),
            }
        if op == "quit":
            return {"ok": True, "quit": True}
        return {"ok": False, "error": f"unknown op {op!r}"}


def main(argv):
    state_dir = argv[0]
    os.makedirs(state_dir, exist_ok=True)
    sock_path = os.path.join(state_dir, "sock")
    if os.path.exists(sock_path):
        os.unlink(sock_path)
    probe = Probe(state_dir, int(argv[1]) if len(argv) > 1 else None)
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(sock_path)
    server.listen(8)
    deadline = time.monotonic() + 10.0
    mapped = False
    while time.monotonic() < deadline and not mapped:
        ev = probe.d.next_event()
        probe.handle(ev)
        mapped = ev.type == probe.X.MapNotify
    probe.activate()
    probe.drain()
    probe.draw_marker()
    ready = {
        "pid": os.getpid(),
        "reserved_keycode": probe.reserved,
        "spare_keycodes": probe.spares_at_start,
        "numlock_mask": probe.numlock_mask,
        "led_mask": probe.d.get_keyboard_control().led_mask,
        "t": time.time(),
        **probe.state(),
    }
    tmp = os.path.join(state_dir, "ready.json.tmp")
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(ready, handle, sort_keys=True)
    os.replace(tmp, os.path.join(state_dir, "ready.json"))
    xfd = probe.d.fileno()
    running = True
    while running:
        readable, _, _ = select.select([xfd, server], [], [], 0.05)
        probe.drain()
        if server in readable:
            conn, _ = server.accept()
            with conn:
                conn.settimeout(10.0)
                data = b""
                while not data.endswith(b"\n"):
                    chunk = conn.recv(65536)
                    if not chunk:
                        break
                    data += chunk
                try:
                    reply = probe.command(json.loads(data.decode("utf-8")))
                except Exception as exc:  # noqa: BLE001 - every failure is answered
                    reply = {"ok": False, "error": repr(exc)[:500]}
                conn.sendall((json.dumps(reply, sort_keys=True) + "\n").encode("utf-8"))
                running = not reply.get("quit")
    server.close()
    os.unlink(sock_path)


if __name__ == "__main__":
    main(sys.argv[1:])
