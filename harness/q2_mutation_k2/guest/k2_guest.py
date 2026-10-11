"""Guest-side helpers of the K2 injection executor (runs inside the OSWorld guest).

Registration ``q2-evaluator-mutation-v1-k2`` section 3. Shipped as base64 in an argv list
through the guest server's ``/execute`` (``GuestClient.run_script``), so nothing is shell-
parsed. Standard library only (the guest's Python 3.10). Every mode prints one JSON object on
its last stdout line.

Modes (``python3 -c <bootstrap> <b64> MODE <json>``):

* ``hash`` ``{"paths": [...]}``: per path, whether it exists, its SHA-256, size and
  ``st_mtime_ns``; plus the guest's ``time.time()`` (the clock-offset reading of section 8).
* ``close_app`` ``{"name": "soffice", "quit_wait_s": 15, "term_wait_s": 20, "kill_wait_s": 5}``:
  the ``kill_process`` op. For LibreOffice, its own Quit first (one of its windows activated
  with ``wmctrl -a``, then Ctrl+Q through pyautogui), awaited ``quit_wait_s``; then every
  process still alive whose ``comm`` or first argv element names ``name`` (``soffice``
  matches ``soffice.bin`` and ``oosplash``; never matched on the full command line, which
  would match this script) gets SIGTERM, and any alive after ``term_wait_s`` SIGKILL.
  Returns the processes found, the quit, the signals sent and the pids still alive at the
  end (the executor fails the run if any is).
* ``remove_locks`` ``{"paths": [...]}``: removes LibreOffice's ``.~lock.<name>#`` file next
  to each path, if one was left behind by the closed instance.
* ``windows`` ``{}``: the titles ``wmctrl -l`` lists.
* ``wait_written`` ``{"path", "mtime_ns", "size", "timeout_s"}``: seconds until the file's
  (mtime, size) differs from the given pair and then holds for 0.3 s (the offline save
  stage's ``LoSession.wait_written`` rule), or ``null`` after ``timeout_s``.
"""

import hashlib
import json
import os
import signal
import subprocess
import sys
import time

STABLE_S = 0.3
POLL_S = 0.1


def file_state(path):
    out = {"path": path, "exists": False, "sha256": None, "size": None, "mtime_ns": None}
    try:
        stat = os.stat(path)
    except OSError:
        return out
    if not os.path.isfile(path):
        out["exists"] = True
        out["not_a_file"] = True
        return out
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    out.update(exists=True, sha256=digest.hexdigest(), size=stat.st_size, mtime_ns=stat.st_mtime_ns)
    return out


def mode_hash(config):
    return {"files": [file_state(p) for p in config["paths"]], "guest_time": time.time()}


def processes(name):
    found = []
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
        if (
            name in comm
            or name in os.path.basename(argv0)
            or (name == "soffice" and comm == "oosplash")
        ):
            found.append({"pid": int(entry), "comm": comm})
    return found


def alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:
        with open(f"/proc/{pid}/stat", encoding="utf-8") as handle:
            return handle.read().split(") ", 1)[1].split()[0] != "Z"
    except OSError:
        return False


def wait_gone(pids, seconds):
    started = time.time()
    while time.time() - started < seconds:
        if not any(alive(pid) for pid in pids):
            return round(time.time() - started, 3)
        time.sleep(0.2)
    return None


def x_env():
    env = dict(os.environ)
    env.setdefault("DISPLAY", ":0")
    return env


def quit_libreoffice(wait_s):
    """LibreOffice's own Quit (Ctrl+Q in one of its windows): a clean exit that leaves no
    document-recovery state, so the reopened document shows no recovery dialog. A SIGTERM
    leaves the open documents in the recovery list (development job 1113)."""
    titles = mode_windows({}).get("titles") or []
    window = next((t for t in titles if "LibreOffice" in t), None)
    out = {"window": window, "sent": False}
    if window is None:
        return out
    env = x_env()
    activate = subprocess.run(
        ["wmctrl", "-a", window], capture_output=True, text=True, env=env, timeout=30
    )
    time.sleep(0.5)
    key = subprocess.run(
        ["python3", "-c", "import pyautogui; pyautogui.hotkey('ctrl', 'q')"],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    out.update(
        sent=key.returncode == 0,
        activate_rc=activate.returncode,
        key_rc=key.returncode,
        key_stderr=key.stderr[-200:],
    )
    return out


def mode_close_app(config):
    """The plan's ``kill_process``: LibreOffice's own Quit first, then SIGTERM, then SIGKILL."""
    name = config["name"]
    found = processes(name)
    pids = [p["pid"] for p in found]
    out = {"name": name, "found": found, "quit": None, "term": [], "kill": [], "remaining": []}
    if name == "soffice" and pids:
        out["quit"] = quit_libreoffice(float(config.get("quit_wait_s", 15.0)))
        if out["quit"]["sent"]:
            out["quit"]["exited_s"] = wait_gone(pids, float(config.get("quit_wait_s", 15.0)))
    for pid in pids:
        if alive(pid):
            try:
                os.kill(pid, signal.SIGTERM)
                out["term"].append(pid)
            except (ProcessLookupError, PermissionError) as exc:
                out.setdefault("errors", []).append(f"TERM {pid}: {exc}")
    if out["term"]:
        out["term_wait_s"] = wait_gone(pids, float(config.get("term_wait_s", 20.0)))
    for pid in pids:
        if alive(pid):
            try:
                os.kill(pid, signal.SIGKILL)
                out["kill"].append(pid)
            except (ProcessLookupError, PermissionError) as exc:
                out.setdefault("errors", []).append(f"KILL {pid}: {exc}")
    if out["kill"]:
        wait_gone(pids, float(config.get("kill_wait_s", 5.0)))
    # A new instance may have started meanwhile (it would hold the file again).
    out["remaining"] = [p for p in processes(name) if alive(p["pid"])]
    return out


def mode_remove_locks(config):
    removed = []
    for path in config["paths"]:
        lock = os.path.join(os.path.dirname(path), ".~lock." + os.path.basename(path) + "#")
        if os.path.lexists(lock):
            try:
                os.remove(lock)
                removed.append(lock)
            except OSError as exc:
                return {"removed": removed, "error": f"{lock}: {exc}"}
    return {"removed": removed}


def mode_windows(config):
    env = x_env()
    result = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True, env=env, timeout=30)
    titles = []
    for line in result.stdout.splitlines():
        parts = line.split(None, 3)
        titles.append(parts[3] if len(parts) == 4 else "")
    return {"returncode": result.returncode, "titles": titles, "stderr": result.stderr[-200:]}


def mode_wait_written(config):
    path = config["path"]
    before = (config.get("mtime_ns"), config.get("size"))
    timeout = float(config.get("timeout_s", 30.0))
    started = time.time()
    while time.time() - started < timeout:
        try:
            stat = os.stat(path)
        except OSError:
            time.sleep(POLL_S)
            continue
        now = (stat.st_mtime_ns, stat.st_size)
        if now != before:
            detected = time.time() - started
            time.sleep(STABLE_S)
            try:
                again = os.stat(path)
            except OSError:
                continue
            if (again.st_mtime_ns, again.st_size) == now:
                return {"seconds": round(detected, 3), "state": file_state(path)}
        time.sleep(POLL_S)
    return {"seconds": None, "state": file_state(path)}


MODES = {
    "hash": mode_hash,
    "close_app": mode_close_app,
    "remove_locks": mode_remove_locks,
    "windows": mode_windows,
    "wait_written": mode_wait_written,
}


def main(argv):
    mode, config = argv[0], json.loads(argv[1])
    if mode not in MODES:
        raise SystemExit(f"mode must be one of {sorted(MODES)}")
    started = time.time()
    result = MODES[mode](config)
    result["mode"] = mode
    result["seconds_in_guest"] = round(time.time() - started, 3)
    print(json.dumps(result))


if __name__ == "__main__":
    main(sys.argv[1:])
