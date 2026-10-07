"""Guest facts for the boot report (runs inside the OSWorld guest, stdlib + guest packages).

Shipped by the runner through ``/execute`` as base64; prints one JSON object.
Read-only: it inspects the session and installed software and changes nothing.
Usage inside the guest: ``python3 -c <bootstrap> <b64> [full|brief]``.
"""

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys

MODE = sys.argv[1] if len(sys.argv) > 1 else "full"


def run(argv, timeout=15):
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return {"rc": done.returncode, "out": done.stdout[-3000:], "err": done.stderr[-600:]}
    except Exception as exc:  # noqa: BLE001 - facts are best effort and recorded
        return {"rc": None, "error": repr(exc)[:300]}


def read(path, limit=4000):
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read(limit)
    except OSError as exc:
        return "ERR " + repr(exc)[:200]


def sha256_path(path):
    try:
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError as exc:
        return "ERR " + repr(exc)[:200]


facts = {
    "boot_id": read("/proc/sys/kernel/random/boot_id").strip(),
    "uptime_s": float(read("/proc/uptime").split()[0] or 0),
    "env": {
        key: os.environ.get(key)
        for key in ("DISPLAY", "XAUTHORITY", "XDG_SESSION_TYPE", "WAYLAND_DISPLAY", "USER", "LANG")
    },
    "dbus_session_present": bool(os.environ.get("DBUS_SESSION_BUS_ADDRESS")),
}

# The server is this script's parent's parent: server -> python3 -c (us).
server_pid = os.getppid()
server_cmdline = read(f"/proc/{server_pid}/cmdline").replace("\0", " ").strip()
try:
    server_cwd = os.readlink(f"/proc/{server_pid}/cwd")
except OSError:
    server_cwd = None
facts["server"] = {"pid": server_pid, "cmdline": server_cmdline[:300], "cwd": server_cwd}
for token in server_cmdline.split():
    if token.endswith(".py"):
        main_path = token if os.path.isabs(token) else os.path.join(server_cwd or "/", token)
        facts["server"]["main_py"] = main_path
        facts["server"]["main_py_sha256"] = sha256_path(main_path)
        break

if MODE == "full":
    facts["python"] = sys.version
    facts["executable"] = sys.executable
    facts["uname"] = list(platform.uname())
    facts["os_release"] = read("/etc/os-release", 1200)
    comms = []
    for pid in os.listdir("/proc"):
        if pid.isdigit():
            comm = read(f"/proc/{pid}/comm", 64).strip()
            if comm and not comm.startswith("ERR"):
                comms.append(comm)
    wanted = ("Xorg", "Xwayland", "gnome-shell", "gdm", "Xvfb", "mutter", "ibus-daemon")
    facts["display_processes"] = sorted({c for c in comms if c in wanted})
    facts["setxkbmap"] = run(["setxkbmap", "-query"])
    facts["xrandr"] = run(["xrandr", "--current"])
    facts["gnome_shell_version"] = run(["gnome-shell", "--version"])
    facts["xset_q"] = run(["xset", "q"])
    facts["loginctl"] = run(["loginctl", "list-sessions", "--no-legend"])
    modules = {}
    for name in ("pyautogui", "Xlib", "pynput", "tkinter", "PIL", "pyatspi", "requests", "flask"):
        try:
            module = __import__(name)
            modules[name] = str(
                getattr(module, "__version__", getattr(module, "VERSION", "present"))
            )
        except Exception as exc:  # noqa: BLE001
            modules[name] = "ERR " + type(exc).__name__
    facts["python_modules"] = modules
    apps = {}
    for app in (
        "libreoffice",
        "soffice",
        "google-chrome",
        "chromium",
        "chromium-browser",
        "code",
        "gnome-terminal",
        "thunderbird",
        "vlc",
        "gimp",
        "nautilus",
        "gedit",
        "xdotool",
        "xev",
        "xinput",
        "dconf",
        "gsettings",
        "wmctrl",
        "xclip",
    ):
        apps[app] = shutil.which(app)
    facts["apps"] = apps
    try:
        from Xlib import display as xdisplay

        dpy = xdisplay.Display()
        screen = dpy.screen()
        extensions = dpy.list_extensions()
        keymap_min = dpy.display.info.min_keycode
        keymap_max = dpy.display.info.max_keycode
        mapping = dpy.get_keyboard_mapping(keymap_min, keymap_max - keymap_min + 1)
        spare = [
            keymap_min + index for index, syms in enumerate(mapping) if not any(sym for sym in syms)
        ]
        facts["x11"] = {
            "screen": [screen.width_in_pixels, screen.height_in_pixels],
            "extensions": sorted(extensions),
            "record": "RECORD" in extensions,
            "xtest": "XTEST" in extensions,
            "keycode_range": [keymap_min, keymap_max],
            "spare_keycodes": len(spare),
            "led_mask": dpy.get_keyboard_control().led_mask,
        }
        dpy.close()
    except Exception as exc:  # noqa: BLE001
        facts["x11"] = {"error": repr(exc)[:300]}

print(json.dumps(facts, sort_keys=True))
