"""Cross-app canary driver, guest side (acceptance criterion A6; runs inside the guest).

Fixes how each app in ``action_path/canary.yaml`` is prepared, launched,
waited for, read back and closed. The runner passes the app's frozen
configuration (from the derived ``suite_cells.json``) as JSON; nothing here
changes it.

Modes (``python3 -c <bootstrap> <b64> MODE <json>``; prints one JSON object):

* ``prepare``: write the fixture and a fresh per-trial profile with the app's
  settings, and return the launch argv and the window class to wait for.
  Writer gets a new LibreOffice user installation whose
  ``registrymodifications.xcu`` turns AutoCorrect while typing, word
  completion and automatic spell checking off; Chrome a new user-data
  directory and the textarea page with the fixture as a JSON string literal;
  VS Code a new user-data directory with the frozen ``settings.json``;
  GNOME Terminal a new window running ``cat > out.txt``.
* ``wait``: wait until the active window has the app's class and (for the
  accessibility read-backs) the app's text object is in the accessibility
  tree; returns the window id, its geometry and the elapsed time.
* ``readback``: Writer: the text of every paragraph of the document, in
  order, joined with ``\\n``, from the accessibility tree; Chrome: the
  textarea's text from the accessibility tree; VS Code: the saved fixture
  file's bytes as UTF-8; Terminal: ``out.txt`` as UTF-8 (after ``cat`` exits,
  or as it stands for the no-input validation).
* ``close``: terminate every process started for the trial (matched by the
  trial's profile path or window class) and wait until they are gone.

Written for this repository. Standard library plus the guest's python-xlib and
pyatspi.
"""

import contextlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.parse

CANARY_DIR = "/home/user/canary"
TRIAL_ROOT = "/tmp/q2ap_canary"
WINDOW_CLASSES = {
    "writer": ("libreoffice", "libreoffice-writer", "soffice"),
    "chrome": ("google-chrome",),
    "vscode": ("code",),
    "terminal": ("gnome-terminal-server", "gnome-terminal"),
}
# Seconds to wait after the app is ready (window active; Writer's document in the
# accessibility tree; Chrome's mirrored title set; VS Code's editor items in its status bar).
SETTLE_S = {"writer": 1.0, "chrome": 1.0, "vscode": 1.0, "terminal": 1.0}
READBACK_TIMEOUT_S = 5.0
PROCESS_PATTERNS = {
    "writer": ("soffice",),
    "chrome": ("chrome",),
    "vscode": ("code",),
    "terminal": ("cat",),
}
LO_PROPS = [
    # (node path, property, type, value): AutoCorrect while typing, word completion and
    # automatic spell checking off; no start-up dialogs.
    ("/org.openoffice.Office.Writer/AutoFunction/Format/ByInput", "Enable", "xs:boolean", "false"),
    ("/org.openoffice.Office.Writer/AutoFunction/Completion", "Enable", "xs:boolean", "false"),
    ("/org.openoffice.Office.Linguistic/SpellChecking", "IsSpellAuto", "xs:boolean", "false"),
    ("/org.openoffice.Office.Common/AutoCorrect", "UseReplacementTable", "xs:boolean", "false"),
    ("/org.openoffice.Office.Common/AutoCorrect", "TwoInitialCapitals", "xs:boolean", "false"),
    ("/org.openoffice.Office.Common/AutoCorrect", "CapitalAtStartSentence", "xs:boolean", "false"),
    ("/org.openoffice.Office.Common/AutoCorrect", "ChangeUnderlineWeight", "xs:boolean", "false"),
    ("/org.openoffice.Office.Common/AutoCorrect", "SetInetAttribute", "xs:boolean", "false"),
    ("/org.openoffice.Office.Common/AutoCorrect", "ChangeOrdinalNumber", "xs:boolean", "false"),
    ("/org.openoffice.Office.Common/AutoCorrect", "ChangeDash", "xs:boolean", "false"),
    ("/org.openoffice.Office.Common/AutoCorrect", "RemoveDoubleSpaces", "xs:boolean", "false"),
    (
        "/org.openoffice.Office.Common/AutoCorrect",
        "CorrectAccidentalCapsLock",
        "xs:boolean",
        "false",
    ),
    ("/org.openoffice.Office.Common/AutoCorrect", "ReplaceSingleQuote", "xs:boolean", "false"),
    ("/org.openoffice.Office.Common/AutoCorrect", "ReplaceDoubleQuote", "xs:boolean", "false"),
    ("/org.openoffice.Office.Common/Misc", "ShowTipOfTheDay", "xs:boolean", "false"),
    ("/org.openoffice.Office.Common/Misc", "FirstRun", "xs:boolean", "false"),
    ("/org.openoffice.Setup/Office", "ooSetupInstCompleted", "xs:boolean", "true"),
]


def trial_dir(config):
    return os.path.join(TRIAL_ROOT, str(config["trial"]))


def _write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(data)


def lo_registry():
    items = []
    for path, prop, _kind, value in LO_PROPS:
        items.append(
            f'<item oor:path="{path}"><prop oor:name="{prop}" oor:op="fuse">'
            f"<value>{value}</value></prop></item>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<oor:items xmlns:oor="http://openoffice.org/2001/registry" '
        'xmlns:xs="http://www.w3.org/2001/XMLSchema" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
        + "\n".join(items)
        + "\n</oor:items>\n"
    )


def chrome_page(template, fixture):
    return template.replace("FIXTURE", json.dumps(fixture, ensure_ascii=False))


def prepare(config):
    app = config["app"]
    base = trial_dir(config)
    shutil.rmtree(base, ignore_errors=True)
    os.makedirs(base)
    os.makedirs(CANARY_DIR, exist_ok=True)
    fixture = config["fixture_text"]
    out = {"app": app, "dir": base}
    if app == "writer":
        path = os.path.join(CANARY_DIR, f"fixture-{config['trial']}.txt")
        _write(path, fixture)
        _write(os.path.join(base, "user", "registrymodifications.xcu"), lo_registry())
        out["argv"] = [
            "soffice",
            f"-env:UserInstallation=file://{base}",
            "--norestore",
            "--nologo",
            "--writer",
            path,
        ]
        out["file"] = path
    elif app == "chrome":
        path = os.path.join(CANARY_DIR, "textarea.html")
        _write(path, chrome_page(config["page"], fixture))
        out["argv"] = [
            "google-chrome",
            *config["flags"],
            f"--user-data-dir={base}/profile",
            "file://" + path,
        ]
        out["file"] = path
    elif app == "vscode":
        path = os.path.join(CANARY_DIR, f"fixture-{config['trial']}.txt")
        _write(path, fixture)
        settings = os.path.join(base, "data", "User", "settings.json")
        _write(settings, json.dumps(config["settings"], indent=2, ensure_ascii=False))
        out["argv"] = [
            "code",
            "--user-data-dir",
            f"{base}/data",
            "--extensions-dir",
            f"{base}/ext",
            "--disable-extensions",
            "--password-store=basic",
            "--new-window",
            path,
        ]
        out["file"] = path
    elif app == "terminal":
        path = os.path.join(CANARY_DIR, "out.txt")
        if os.path.exists(path):
            os.unlink(path)
        out["argv"] = ["gnome-terminal", "--window", "--", "bash", "-c", f"cat > {path}"]
        out["file"] = path
    else:
        raise SystemExit(f"unknown app {app!r}")
    if os.path.exists(out["file"]):
        out["fixture_mtime_ns"] = os.stat(out["file"]).st_mtime_ns
    with open(os.path.join(base, "prepare.json"), "w", encoding="utf-8") as handle:
        json.dump(out, handle)
    return out


def _wm_class(d, window):
    try:
        value = window.get_wm_class()
    except Exception:  # noqa: BLE001 - windows can vanish while we look
        return ()
    return tuple(v.lower() for v in value or ())


def _active_window(d):
    root = d.screen().root
    atom = d.intern_atom("_NET_ACTIVE_WINDOW")
    prop = root.get_full_property(atom, 0)
    if not prop or not prop.value or not prop.value[0]:
        return None
    return d.create_resource_object("window", prop.value[0])


def _frame_geometry(d, window):
    root = d.screen().root
    origin = root.translate_coords(window, 0, 0)
    geometry = window.get_geometry()
    return [origin.x, origin.y, geometry.width, geometry.height]


def find_text_node(app):
    """The accessibility node holding the app's text, or None."""
    import pyatspi

    desktop = pyatspi.Registry.getDesktop(0)
    wanted = {"writer": ("soffice",), "chrome": ("google chrome", "google-chrome", "chrome")}[app]
    for index in range(desktop.childCount):
        application = desktop.getChildAtIndex(index)
        if application is None or (application.name or "").lower() not in wanted:
            continue
        if app == "writer":
            found = pyatspi.findDescendant(
                application, lambda n: n.getRoleName() == "document text", True
            )
        else:
            found = pyatspi.findDescendant(
                application,
                lambda n: (
                    n.getRoleName() in ("entry", "text")
                    and "multi line" in [pyatspi.stateToString(s) for s in n.getState().getStates()]
                ),
                True,
            )
        if found is not None:
            return found
    return None


def _vscode_ready(geometry):
    """VS Code's status bar shows the text editor's items (Ln, Col, encoding, mode).

    With a file in the active editor the right half of the status bar holds text;
    while the workbench loads, or with no text editor active, only the bell is there.
    """
    from PIL import ImageGrab

    x, y, w, h = geometry
    box = (x + w // 2, y + h - 20, x + w - 60, y + h - 2)
    image = ImageGrab.grab(bbox=box).convert("L")
    bright = sum(1 for v in image.getdata() if v > 170)
    return bright > 40, bright


def _chrome_title(d):
    """The Chrome window's mirrored textarea value (None if no such window)."""
    from Xlib import X

    name = d.intern_atom("_NET_WM_NAME")
    utf8 = d.intern_atom("UTF8_STRING")
    clients = d.screen().root.get_full_property(
        d.intern_atom("_NET_CLIENT_LIST"), X.AnyPropertyType
    )
    for wid in clients.value if clients else []:
        window = d.create_resource_object("window", wid)
        try:
            prop = window.get_full_property(name, utf8)
        except Exception:  # noqa: BLE001 - windows can vanish while we look
            continue
        title = prop.value.decode("utf-8", "replace") if prop and prop.value else ""
        if title.startswith("Q2AP:") and title.endswith(" - Google Chrome"):
            encoded = title[len("Q2AP:") : -len(" - Google Chrome")]
            try:
                return urllib.parse.unquote(encoded, encoding="utf-8", errors="strict")
            except UnicodeDecodeError:
                return None
    return None


def _titles(d):
    """Every client window's title (diagnostics when the mirror is missing)."""
    from Xlib import X

    name = d.intern_atom("_NET_WM_NAME")
    utf8 = d.intern_atom("UTF8_STRING")
    root = d.screen().root
    clients = root.get_full_property(d.intern_atom("_NET_CLIENT_LIST"), X.AnyPropertyType)
    out = []
    for wid in clients.value if clients else []:
        try:
            prop = d.create_resource_object("window", wid).get_full_property(name, utf8)
        except Exception:  # noqa: BLE001
            continue
        out.append(prop.value.decode("utf-8", "replace")[:300] if prop and prop.value else "")
    return out


def chrome_readback():
    from Xlib import display

    d = display.Display()
    deadline = time.monotonic() + READBACK_TIMEOUT_S
    last, since = object(), time.monotonic()
    while time.monotonic() < deadline:
        value = _chrome_title(d)
        if value != last:
            last, since = value, time.monotonic()
        elif value is not None and time.monotonic() - since >= 0.5:
            return {"ok": True, "text": value}
        time.sleep(0.1)
    if isinstance(last, str):
        return {"ok": True, "text": last, "unstable": True}
    return {"ok": False, "error": "no mirrored title", "titles": _titles(d)}


def wait_window(config):
    from Xlib import display

    app = config["app"]
    classes = WINDOW_CLASSES[app]
    deadline = time.monotonic() + float(config.get("timeout_s", 60))
    started = time.monotonic()
    d = display.Display()
    window = None
    while time.monotonic() < deadline:
        active = _active_window(d)
        if active is not None and set(_wm_class(d, active)) & set(classes):
            window = active
            break
        time.sleep(0.25)
    out = {"ok": window is not None, "elapsed_s": round(time.monotonic() - started, 3)}
    if window is None:
        return out
    out["window"] = window.id
    out["wm_class"] = list(_wm_class(d, window))
    if app == "writer":
        node = None
        while time.monotonic() < deadline and node is None:
            node = find_text_node(app)
            if node is None:
                time.sleep(0.5)
        out["a11y_ready"] = node is not None
        out["ok"] = node is not None
    if app == "chrome":
        title = None
        while time.monotonic() < deadline and title is None:
            title = _chrome_title(d)
            if title is None:
                time.sleep(0.25)
        out["title_ready"] = title is not None
        out["ok"] = title is not None
    if app == "vscode":
        ready, bright = False, 0
        while time.monotonic() < deadline and not ready:
            ready, bright = _vscode_ready(_frame_geometry(d, window))
            if not ready:
                time.sleep(0.5)
        out["editor_ready"] = ready
        out["status_bar_bright"] = bright
        out["ok"] = ready
    time.sleep(float(config.get("settle_s", SETTLE_S[app])))
    out["geometry"] = _frame_geometry(d, window)
    out["elapsed_s"] = round(time.monotonic() - started, 3)
    return out


def _node_text(node):
    text = node.queryText()
    return text.getText(0, text.characterCount)


def _find_text_node_retry(app):
    """The text node, retried for READBACK_TIMEOUT_S (the tree can be rebuilding after input)."""
    deadline = time.monotonic() + READBACK_TIMEOUT_S
    while True:
        node = find_text_node(app)
        if node is not None or time.monotonic() >= deadline:
            return node
        time.sleep(0.25)


def _wait_saved(path, before_ns):
    """VS Code writes the file after Ctrl+S returns: wait until it changed and is stable."""
    deadline = time.monotonic() + READBACK_TIMEOUT_S
    last = None
    while time.monotonic() < deadline:
        try:
            stat = os.stat(path)
        except OSError:
            stat = None
        current = (stat.st_mtime_ns, stat.st_size) if stat else None
        if current and current[0] != before_ns and current == last:
            return True
        last = current
        time.sleep(0.2)
    return False


def readback(config):
    app = config["app"]
    if app == "writer":
        node = _find_text_node_retry(app)
        if node is None:
            return {"ok": False, "error": "no document text node"}
        paragraphs = []
        for index in range(node.childCount):
            child = node.getChildAtIndex(index)
            if child is not None and child.getRoleName() == "paragraph":
                paragraphs.append(_node_text(child))
        return {"ok": True, "text": "\n".join(paragraphs), "paragraphs": len(paragraphs)}
    if app == "chrome":
        return chrome_readback()
    path = config["file"]
    saved = None
    if app == "vscode" and config.get("wait_cat_exit", True):
        with open(os.path.join(trial_dir(config), "prepare.json"), encoding="utf-8") as handle:
            saved = _wait_saved(path, json.load(handle).get("fixture_mtime_ns"))
    if app == "terminal" and config.get("wait_cat_exit", True):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and _pids(["cat"], path):
            time.sleep(0.2)
    try:
        with open(path, "rb") as handle:
            data = handle.read()
    except OSError as exc:
        return {"ok": False, "error": repr(exc)[:200]}
    try:
        return {"ok": True, "text": data.decode("utf-8"), "bytes": len(data), "saved": saved}
    except UnicodeDecodeError:
        return {"ok": False, "error": "not UTF-8", "bytes": len(data)}


def _pids(names, needle):
    pids = []
    for pid in os.listdir("/proc"):
        if not pid.isdigit() or int(pid) == os.getpid():
            continue
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as handle:
                cmdline = handle.read().replace(b"\0", b" ").decode("utf-8", "replace")
            with open(f"/proc/{pid}/comm", encoding="utf-8") as handle:
                comm = handle.read().strip()
        except OSError:
            continue
        if needle in cmdline and any(name in comm or name in cmdline for name in names):
            pids.append(int(pid))
    return pids


def close(config):
    app = config["app"]
    needle = trial_dir(config) if app in ("writer", "chrome", "vscode") else config["file"]
    pids = _pids(PROCESS_PATTERNS[app], needle)
    for pid in pids:
        with contextlib.suppress(OSError):
            os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and _pids(PROCESS_PATTERNS[app], needle):
        time.sleep(0.2)
    left = _pids(PROCESS_PATTERNS[app], needle)
    for pid in left:
        with contextlib.suppress(OSError):
            os.kill(pid, signal.SIGKILL)
    if app == "terminal":
        # The terminal window closes when its shell exits; close stray windows of the class.
        subprocess.run(["wmctrl", "-c", "Terminal"], capture_output=True, timeout=10)
    time.sleep(0.5)
    return {"ok": True, "terminated": pids, "killed": left}


def main(argv):
    mode, config = argv[0], json.loads(argv[1])
    handlers = {"prepare": prepare, "wait": wait_window, "readback": readback, "close": close}
    if mode not in handlers:
        raise SystemExit("mode must be prepare, wait, readback or close")
    result = handlers[mode](config)
    result["mode"] = mode
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:])
