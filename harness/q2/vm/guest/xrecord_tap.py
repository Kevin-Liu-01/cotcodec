"""Raw X input tap through the RECORD extension (runs inside the OSWorld guest).

What it records, in the X server's own processing order (one RECORD context):

* core device events (key and button press and release, motion) as the
  server processes them, whatever their source (XTest, or evdev from QEMU's
  emulated devices);
* every core ``ChangeKeyboardMapping`` request (opcode 100) from any client.

Keysyms are resolved by the tap itself. It snapshots the full keyboard mapping
when it starts (in the ``ready`` record) and applies each recorded
``ChangeKeyboardMapping`` in stream order, so a key event's ``keysym0`` and
``keysym1`` come from the mapping in force when the server processed that
event. The previous tap read keysyms through python-xlib's per-connection
keymap cache, which is filled when the connection opens and refreshed only
when the client handles MappingNotify; it never did, so a spare keycode
remapped after the tap started was projected with its old keysym (0x0). The
raw keycode is always recorded too (``detail``), so any projection can be
recomputed offline from the ``ready`` snapshot and the ``mapping_request``
records.

A second connection watches MappingNotify, which the server sends to every
non-XKB client on any keyboard-mapping change, core or XKB. Each one becomes a
``mapping_notify`` record. ``mapping_check`` pairs them with the recorded
requests: a keyboard MappingNotify without a recorded core request means the
mapping changed through XKB requests, which the tap does not decode, and every
later key event on that keycode range is unverified. The suite treats an
unverified key event inside an entry's window as an infrastructure failure of
the oracle (preregistration section 6.1).

Output is JSONL. Every record has ``kind`` and ``t`` (guest wall time):

* ``ready``: led_mask, pid, min_keycode, keymap (rows from min_keycode, every
  keysym column), map_gen 0
* ``KeyPress``/``KeyRelease``: detail (the keycode), state, x, y, server_time,
  keysym0, keysym1, map_gen
* ``ButtonPress``/``ButtonRelease``/``MotionNotify``: detail, state, x, y,
  server_time
* ``mapping_request``: first_keycode, count, keysyms_per_keycode, rows, map_gen
* ``mapping_notify``: request (0 modifier, 1 keyboard, 2 pointer),
  first_keycode, count, rows (as queried when the notify was read)
* ``stop``: led_mask, map_gen, keyboard_notifies

Usage inside the guest: ``python3 -c <bootstrap> <b64> <out_path> <duration_s> <stop_path>``.

Written for this repository from the X11 core protocol encoding (event and
ChangeKeyboardMapping layouts), the RECORD extension protocol specification
and python-xlib's ``Xlib.ext.record`` API. An earlier version followed the
structure of python-xlib's example ``examples/record_demo.py`` (LGPL-2.1+,
Copyright 2006 Alex Badea); see the NOTICE in ``harness/q2/README.md``.
Everything above ``main`` is pure Python so the runner and the tests can
import it without python-xlib.
"""

import json
import os
import struct
import sys
import threading
import time

CHANGE_KEYBOARD_MAPPING = 100  # X11 core request opcode
EVENT_NAMES = {
    2: "KeyPress",
    3: "KeyRelease",
    4: "ButtonPress",
    5: "ButtonRelease",
    6: "MotionNotify",
}
MAPPING_KEYBOARD = 1
EVENT_SIZE = 32


def byte_order(swapped):
    """struct prefix for intercepted data: native order unless RECORD says swapped."""
    native = "<" if sys.byteorder == "little" else ">"
    if not swapped:
        return native
    return ">" if native == "<" else "<"


def decode_core_events(data, order="<"):
    """Split RECORD device-event data into core events (32 bytes each)."""
    events = []
    for offset in range(0, len(data) - EVENT_SIZE + 1, EVENT_SIZE):
        chunk = data[offset : offset + EVENT_SIZE]
        kind = EVENT_NAMES.get(chunk[0] & 0x7F)
        if kind is None:
            continue
        (server_time,) = struct.unpack_from(order + "I", chunk, 4)
        root_x, root_y = struct.unpack_from(order + "hh", chunk, 20)
        (state,) = struct.unpack_from(order + "H", chunk, 28)
        events.append(
            {
                "kind": kind,
                "detail": chunk[1],
                "state": state,
                "x": root_x,
                "y": root_y,
                "server_time": server_time,
            }
        )
    return events


def decode_change_keyboard_mapping(data, order="<"):
    """(first_keycode, rows) from a recorded ChangeKeyboardMapping request, else None."""
    if len(data) < 8 or data[0] != CHANGE_KEYBOARD_MAPPING:
        return None
    count = data[1]
    (length,) = struct.unpack_from(order + "H", data, 2)
    header = 8 if length else 12  # a BIG-REQUESTS request carries a 4-byte length after it
    if len(data) < header:
        return None
    first = data[header - 4]
    per = data[header - 3]
    needed = header + 4 * count * per
    if per == 0 or len(data) < needed:
        return None
    flat = struct.unpack_from(f"{order}{count * per}I", data, header)
    rows = [list(flat[i * per : (i + 1) * per]) for i in range(count)]
    return first, rows


class Keymap:
    """The tap's own keycode -> keysym table, updated in server order."""

    def __init__(self, min_keycode, rows):
        self.min_keycode = min_keycode
        self.rows = {min_keycode + i: list(row) for i, row in enumerate(rows)}
        self.generation = 0

    def apply(self, first, rows):
        for i, row in enumerate(rows):
            self.rows[first + i] = list(row)
        self.generation += 1

    def lookup(self, keycode, index):
        row = self.rows.get(keycode) or []
        return row[index] if index < len(row) else 0


def key_record(event, keymap):
    record = dict(event)
    if event["kind"] in ("KeyPress", "KeyRelease"):
        record["keysym0"] = keymap.lookup(event["detail"], 0)
        record["keysym1"] = keymap.lookup(event["detail"], 1)
        record["map_gen"] = keymap.generation
    return record


def mapping_check(records):
    """Pair keyboard MappingNotify records with recorded core requests, in order.

    Returns ok, the counts, and the keycode ranges changed by something other
    than a recorded core request (key events on them after that point are
    unverified).
    """
    requests = [r for r in records if r.get("kind") == "mapping_request"]
    notifies = [
        r
        for r in records
        if r.get("kind") == "mapping_notify" and r.get("request") == MAPPING_KEYBOARD
    ]
    pending = [(r["first_keycode"], r["count"]) for r in requests]
    unmatched = []
    for notify in notifies:
        key = (notify["first_keycode"], notify["count"])
        if key in pending:
            pending.remove(key)
        else:
            unmatched.append(list(key))
    return {
        "ok": not unmatched,
        "requests": len(requests),
        "keyboard_notifies": len(notifies),
        "unmatched_ranges": unmatched,
        "requests_without_notify": [list(k) for k in pending],
    }


def main(argv):
    from Xlib import X, display
    from Xlib.ext import record

    out_path, duration, stop_path = argv[0], float(argv[1]), argv[2]
    control = display.Display()
    data_conn = display.Display()
    watcher = display.Display()
    lock = threading.Lock()
    out = open(out_path, "w", encoding="utf-8", buffering=1)  # noqa: SIM115 - process lifetime
    state = {"notifies": 0}

    def emit(obj):
        obj["t"] = time.time()
        line = json.dumps(obj, sort_keys=True) + "\n"
        with lock:
            out.write(line)

    info = control.display.info
    first, last = info.min_keycode, info.max_keycode
    initial = [list(row) for row in control.get_keyboard_mapping(first, last - first + 1)]
    keymap = Keymap(first, initial)
    context = control.record_create_context(
        0,
        [record.AllClients],
        [
            {
                "core_requests": (CHANGE_KEYBOARD_MAPPING, CHANGE_KEYBOARD_MAPPING),
                "core_replies": (0, 0),
                "ext_requests": (0, 0, 0, 0),
                "ext_replies": (0, 0, 0, 0),
                "delivered_events": (0, 0),
                "device_events": (X.KeyPress, X.MotionNotify),
                "errors": (0, 0),
                "client_started": False,
                "client_died": False,
            }
        ],
    )

    def on_data(reply):
        payload = bytes(reply.data)
        if not payload:
            return
        if reply.category == record.FromClient:
            decoded = decode_change_keyboard_mapping(payload, byte_order(reply.client_swapped))
            if decoded is not None:
                start, rows = decoded
                keymap.apply(start, rows)
                emit(
                    {
                        "kind": "mapping_request",
                        "first_keycode": start,
                        "count": len(rows),
                        "keysyms_per_keycode": len(rows[0]) if rows else 0,
                        "rows": rows,
                        "map_gen": keymap.generation,
                    }
                )
        elif reply.category == record.FromServer:
            for event in decode_core_events(payload, byte_order(False)):
                emit(key_record(event, keymap))

    def watch_mapping():
        while True:
            event = watcher.next_event()
            if event.type != X.MappingNotify:
                continue
            rows = []
            if event.request == MAPPING_KEYBOARD and event.count:
                rows = [
                    list(r) for r in watcher.get_keyboard_mapping(event.first_keycode, event.count)
                ]
                state["notifies"] += 1
            emit(
                {
                    "kind": "mapping_notify",
                    "request": event.request,
                    "first_keycode": event.first_keycode,
                    "count": event.count,
                    "rows": rows,
                }
            )

    def stop_when_done():
        deadline = time.monotonic() + duration
        while time.monotonic() < deadline and not os.path.exists(stop_path):
            time.sleep(0.05)
        control.record_disable_context(context)
        control.flush()

    emit(
        {
            "kind": "ready",
            "led_mask": control.get_keyboard_control().led_mask,
            "pid": os.getpid(),
            "min_keycode": first,
            "keymap": initial,
            "map_gen": 0,
        }
    )
    threading.Thread(target=watch_mapping, daemon=True).start()
    threading.Thread(target=stop_when_done, daemon=True).start()
    data_conn.record_enable_context(context, on_data)
    control.record_free_context(context)
    # Let the watcher drain MappingNotify events raised just before the stop.
    time.sleep(0.3)
    emit(
        {
            "kind": "stop",
            "led_mask": control.get_keyboard_control().led_mask,
            "map_gen": keymap.generation,
            "keyboard_notifies": state["notifies"],
        }
    )
    with lock:
        out.close()


if __name__ == "__main__":
    main(sys.argv[1:])
