"""Guest-side facts for the S2 v4 VM probe (runs inside the OSWorld guest).

Shipped as base64 in an argv list through the guest server's ``/execute``
(``GuestClient.run_script``), so nothing is shell-parsed. Standard library only (the guest's
Python 3.10). Prints one JSON object on its last stdout line. It reads; it changes nothing.

Mode ``facts`` ``{"selector": PATH}``:

* the cell selector's SHA-256 (``null`` when absent: the stock image), the Arabic language
  pack's files that LibreOffice reads (the gettext catalog count and the four registry files'
  SHA-256) and a digest over the toolbar definitions (PL's differ), so every record names the
  image it ran on;
* ``setxkbmap -query``, the input-method processes running (the stock image runs
  ``ibus-daemon``), GNOME's configured input sources and IBus's current engine (the keyboard
  check of Phase 1's episode start compares these with the stock cell S's record);
* ``wmctrl -l`` window titles and the LibreOffice processes (pid, comm, first argv element, and
  the locale variables of each process's initial environment, read from ``/proc/<pid>/environ``:
  whether the GTK catalogs of the GNOME language pack can be selected at all);
* the guest server's ``LANG``/``LANGUAGE``/``LC_*`` environment (the guest's stock locale,
  ``en_HK.UTF-8`` / ``en_HK:en``, held fixed in every cell).

Mode ``hash`` ``{"paths": [...]}``: per path, whether it exists, its SHA-256, size and
``st_mtime_ns`` (the A3 save check reads these before and after the task's postconfig).

Mode ``registry`` ``{"path": XCU, "keys": [[item path, prop name], ...]}``: P0.10's reader of the
user profile's ``registrymodifications.xcu``: the file's SHA-256, size and mtime, its item count,
and per key every ``value`` text of a ``prop`` with that name under an ``item`` with that
``oor:path`` (the way the three C1 checkers read it).

Mode ``end`` ``{}`` (run once, after the slot's last observation, so nothing it might touch can
change a measurement): ``fc-match :lang=ar`` and the number of Arabic-capable font families, and
``dpkg-query``'s status of the language packs' unmet dependencies and recommendations (the
registration discloses them).
"""

import glob
import hashlib
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

REGISTRY = "/etc/libreoffice/registry"
LANGPACK = {
    "Langpack-ar.xcd": REGISTRY + "/Langpack-ar.xcd",
    "ctl_ar.xcd": REGISTRY + "/ctl_ar.xcd",
    "res/registry_ar.xcd": REGISTRY + "/res/registry_ar.xcd",
    "res/fcfg_langpack_ar.xcd": REGISTRY + "/res/fcfg_langpack_ar.xcd",
}
CATALOGS = "/usr/lib/libreoffice/program/resource/ar/LC_MESSAGES/*.mo"
TOOLBARS = "/usr/lib/libreoffice/share/config/soffice.cfg/modules/*/toolbar/*.xml"
IM_NAMES = ("ibus-daemon", "fcitx", "fcitx5", "uim-xim", "scim")
LOCALE_VARS = ("LANG", "LANGUAGE", "LC_ALL", "LC_MESSAGES", "LC_CTYPE")
OOR = "{http://openoffice.org/2001/registry}"
# Packages the fetched archives name as Depends or Recommends that the image does not install
# (no maintainer script and no package database edit; registration P0.2).
UNMET = ("language-pack-ar", "language-pack-gnome-ar", "fonts-hosny-amiri", "fonts-kacst",
         "fonts-kacst-one", "fonts-sil-scheherazade", "locales", "ucf", "libreoffice-common")


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


def toolbar_digest():
    """SHA-256 over every toolbar definition (path and content): tells PL's image from E's."""
    digest = hashlib.sha256()
    paths = sorted(glob.glob(TOOLBARS))
    for path in paths:
        digest.update(path.encode() + b"\0" + (sha256_of(path) or "").encode() + b"\n")
    return {"files": len(paths), "sha256": digest.hexdigest()}


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


def environ_of(pid):
    """The initial environment of a process (``/proc/<pid>/environ``), or None if unreadable."""
    try:
        with open(f"/proc/{pid}/environ", "rb") as handle:
            raw = handle.read()
    except OSError:
        return None
    out = {}
    for item in raw.split(b"\0"):
        key, sep, value = item.partition(b"=")
        if sep:
            out[key.decode("utf-8", errors="replace")] = value.decode("utf-8", errors="replace")
    return out


def session_env(procs):
    """X and D-Bus session variables taken from the IBus daemon's own environment, so the
    read-only ``gsettings``/``ibus`` queries reach the session without starting a bus (None
    when no session bus address is found: then neither query runs, so nothing can autolaunch
    a bus)."""
    env = x_env()
    env.pop("DBUS_SESSION_BUS_ADDRESS", None)
    for p in procs:
        if p["comm"] == "ibus-daemon":
            found = environ_of(p["pid"]) or {}
            for key in ("DBUS_SESSION_BUS_ADDRESS", "XDG_RUNTIME_DIR", "HOME", "USER"):
                if found.get(key):
                    env[key] = found[key]
            break
    return env if env.get("DBUS_SESSION_BUS_ADDRESS") else None


def run(argv, env=None, timeout=30):
    try:
        result = subprocess.run(argv, capture_output=True, text=True, env=env or x_env(),
                                timeout=timeout)
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
    for p in office:
        env = environ_of(p["pid"])
        p["locale_env"] = None if env is None else {k: env[k] for k in LOCALE_VARS if k in env}
    senv = session_env(procs)
    nobus = {"error": "no session bus address in ibus-daemon's environment"}
    sources = (run(["gsettings", "get", "org.gnome.desktop.input-sources", "sources"], senv, 10)
               if senv else nobus)
    engine = run(["ibus", "engine"], senv, 10) if senv else nobus
    return {
        "selector_sha256": sha256_of(config["selector"]),
        "langpack": {k: sha256_of(v) for k, v in LANGPACK.items()},
        "ar_catalogs": len(glob.glob(CATALOGS)),
        "toolbars": toolbar_digest(),
        "setxkbmap": kb,
        "keyboard_layout": layout,
        "input_methods": sorted({p["comm"] for p in procs if p["comm"] in IM_NAMES}),
        "input_sources": (sources.get("stdout") or "").strip() or None,
        "input_sources_rc": sources.get("returncode", sources.get("error")),
        "ibus_engine": (engine.get("stdout") or "").strip() or None,
        "ibus_engine_rc": engine.get("returncode", engine.get("error")),
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


def mode_registry(config):
    """P0.10: the values the C1 checkers read from ``registrymodifications.xcu``."""
    out = file_state(config["path"])
    out["values"] = {}
    if not out["exists"]:
        return out
    try:
        root = ET.parse(config["path"]).getroot()
    except Exception as exc:  # noqa: BLE001 - recorded: a file the checker cannot parse either
        out["parse_error"] = repr(exc)[:300]
        return out
    items = root.findall(".//item")
    out["items"] = len(items)
    for item_path, prop_name in config["keys"]:
        values = []
        for item in items:
            if item.get(OOR + "path") != item_path:
                continue
            for prop in item.findall(".//prop"):
                if prop.get(OOR + "name") == prop_name:
                    values += [v.text for v in prop.findall(".//value")]
        out["values"][f"{item_path}|{prop_name}"] = values
    return out


def mode_end(config):
    match = run(["fc-match", ":lang=ar", "family"])
    families = run(["fc-list", ":lang=ar", "family"])
    names = {line.split(",")[0].strip() for line in (families.get("stdout") or "").splitlines()
             if line.strip()}
    status = run(["dpkg-query", "-W", "-f=${Package}\t${Status}\t${Version}\n", *UNMET])
    packages = {}
    for line in (status.get("stdout") or "").splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            packages[parts[0]] = {"status": parts[1], "version": parts[2]}
    for name in UNMET:
        packages.setdefault(name, {"status": "not known to dpkg", "version": None})
    return {"fc_match_ar": (match.get("stdout") or "").strip() or None,
            "arabic_font_families": len(names), "arabic_font_family_names": sorted(names)[:40],
            "packages": packages}


MODES = {"facts": mode_facts, "hash": mode_hash, "registry": mode_registry, "end": mode_end}


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
