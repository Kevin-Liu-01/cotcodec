"""Raw X input tap through the RECORD extension (runs inside the OSWorld guest).

Records core device events (key and button press/release, motion) delivered
by the X server, whatever their source (XTest, evdev from QEMU's emulated
devices, ...). Writes JSONL: a ``ready`` record, one record per event, and a
``stop`` record with the final LED mask. Stops after ``duration_s`` or as soon
as ``stop_path`` exists.

Usage inside the guest: ``python3 -c <bootstrap> <b64> <out_path> <duration_s> <stop_path>``.
"""

import json
import os
import sys
import threading
import time

from Xlib import X, display
from Xlib.ext import record
from Xlib.protocol import rq

OUT_PATH, DURATION, STOP_PATH = sys.argv[1], float(sys.argv[2]), sys.argv[3]
NAMES = {
    X.KeyPress: "KeyPress",
    X.KeyRelease: "KeyRelease",
    X.ButtonPress: "ButtonPress",
    X.ButtonRelease: "ButtonRelease",
    X.MotionNotify: "MotionNotify",
}

local = display.Display()
recorder = display.Display()
out = open(OUT_PATH, "w", encoding="utf-8", buffering=1)  # noqa: SIM115 - lives for the process


def emit(record_obj):
    record_obj["t"] = time.time()
    out.write(json.dumps(record_obj, sort_keys=True) + "\n")


context = recorder.record_create_context(
    0,
    [record.AllClients],
    [
        {
            "core_requests": (0, 0),
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


def callback(reply):
    if reply.category != record.FromServer or reply.client_swapped or not len(reply.data):
        return
    data = reply.data
    while len(data):
        event, data = rq.EventField(None).parse_binary_value(data, recorder.display, None, None)
        name = NAMES.get(event.type)
        if name is None:
            continue
        item = {
            "kind": name,
            "detail": event.detail,
            "state": event.state,
            "x": event.root_x,
            "y": event.root_y,
            "server_time": event.time,
        }
        if event.type in (X.KeyPress, X.KeyRelease):
            item["keysym0"] = local.keycode_to_keysym(event.detail, 0)
            item["keysym1"] = local.keycode_to_keysym(event.detail, 1)
        emit(item)


def watchdog():
    deadline = time.monotonic() + DURATION
    while time.monotonic() < deadline and not os.path.exists(STOP_PATH):
        time.sleep(0.05)
    local.record_disable_context(context)
    local.flush()


emit({"kind": "ready", "led_mask": local.get_keyboard_control().led_mask, "pid": os.getpid()})
threading.Thread(target=watchdog, daemon=True).start()
recorder.record_enable_context(context, callback)
recorder.record_free_context(context)
emit({"kind": "stop", "led_mask": local.get_keyboard_control().led_mask})
out.close()
