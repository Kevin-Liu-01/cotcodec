"""Guest-side facts for the S2 v4 VM probe (runs inside the OSWorld guest).

Shipped as base64 in an argv list through the guest server's ``/execute``
(``GuestClient.run_script``), so nothing is shell-parsed. Standard library only (the guest's
Python 3.10). Prints one JSON object on its last stdout line. It reads; it changes nothing.

Mode ``facts`` ``{"selector": PATH}``:

* the cell selector's SHA-256 (``null`` when absent: the stock image), the Arabic language
  pack's files that LibreOffice reads (the gettext catalog count and the four registry files'
  SHA-256), so every record names the image it ran on;
* ``setxkbmap -query`` and whether an input method runs (the keyboard check of P1's episode
  start);
* ``wmctrl -l`` window titles and the LibreOffice processes (pid, comm, first argv element);
* the guest server's ``LANG``/``LANGUAGE``/``LC_*`` environment (the system locale held fixed).

Mode ``hash`` ``{"paths": [...]}``: per path, whether it exists, its SHA-256, size and
``st_mtime_ns`` (the A3 save check reads these before and after the task's postconfig).
"""

import glob
import hashlib
import json
import os
import subprocess
import sys
import time

REGISTRY = "/etc/libreoffice/registry"
LANGPACK = {
    "Langpack-ar.xcd": REGISTRY + "/Langpack-ar.xcd",
    "ctl_ar.xcd": REGISTRY + "/ctl_ar.xcd",
    "res/registry_ar.xcd": REGISTRY + "/res/registry_ar.xcd",
    "res/fcfg_langpack_ar.xcd": REGISTRY + "/res/fcfg_langpack_ar.xcd",
}
CATALOGS = "/usr/lib/libreoffice/program/resource/ar/LC_MESSAGES/*.mo"
IM_NAMES = ("ibus-daemon", "fcitx", "fcitx5", "uim-xim", "scim")


def x_env():
    env = dict(os.environ)
    env.setdefault("DISPLAY", ":0")
    return env


def sha256_of(path):
    try:
        with open(path, "rb") as handle:
            return hashlib.sha256(handle.read()).hexdigest()
    except OSError:
        return None


def processes():
    out = []
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        try:
            with open(f"/proc/{entry}/comm", encoding="utf-8", errors="replace") as handle:
                comm = handle.read().strip()
            with open(f"/proc/{entry}/cmdline", "rb") as handle:
                argv0 = handle.read().split(b"\0")[0].decode("utf-8", errors="replace")
        except OSError:
            continue
        out.append({"pid": int(entry), "comm": comm, "argv0": os.path.basename(argv0)})
    return out


def run(argv):
    try:
        result = subprocess.run(argv, capture_output=True, text=True, env=x_env(), timeout=30)
        return {"returncode": result.returncode, "stdout": result.stdout[-2000:],
                "stderr": result.stderr[-300:]}
    except Exception as exc:  # noqa: BLE001 - recorded
        return {"error": repr(exc)[:300]}


def mode_facts(config):
    procs = processes()
    office = [p for p in procs if p["comm"] in ("soffice.bin", "oosplash")
              or p["argv0"] in ("soffice", "soffice.bin")]
    kb = run(["setxkbmap", "-query"])
    layout = None
    for line in kb.get("stdout", "").splitlines():
        if line.startswith("layout:"):
            layout = line.split(":", 1)[1].strip()
    windows = run(["wmctrl", "-l"])
    titles = []
    for line in windows.get("stdout", "").splitlines():
        parts = line.split(None, 3)
        titles.append(parts[3] if len(parts) == 4 else "")
    return {
        "selector_sha256": sha256_of(config["selector"]),
        "langpack": {k: sha256_of(v) for k, v in LANGPACK.items()},
        "ar_catalogs": len(glob.glob(CATALOGS)),
        "setxkbmap": kb,
        "keyboard_layout": layout,
        "input_methods": sorted({p["comm"] for p in procs if p["comm"] in IM_NAMES}),
        "window_titles": titles,
        "libreoffice_processes": office,
        "server_locale_env": {k: v for k, v in os.environ.items()
                              if k in ("LANG", "LANGUAGE") or k.startswith("LC_")},
    }


def file_state(path):
    out = {"path": path, "exists": False, "sha256": None, "size": None, "mtime_ns": None}
    try:
        stat = os.stat(path)
    except OSError:
        return out
    out.update(exists=True, size=stat.st_size, mtime_ns=stat.st_mtime_ns,
               sha256=sha256_of(path) if os.path.isfile(path) else None)
    return out


def mode_hash(config):
    return {"files": [file_state(p) for p in config["paths"]]}


MODES = {"facts": mode_facts, "hash": mode_hash}


def main(argv):
    mode, config = argv[0], json.loads(argv[1])
    if mode not in MODES:
        raise SystemExit(f"mode must be one of {sorted(MODES)}")
    started = time.time()
    result = MODES[mode](config)
    result["mode"] = mode
    result["guest_time"] = time.time()
    result["seconds_in_guest"] = round(time.time() - started, 3)
    print(json.dumps(result))


if __name__ == "__main__":
    main(sys.argv[1:])
