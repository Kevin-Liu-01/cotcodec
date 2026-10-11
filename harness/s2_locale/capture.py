#!/usr/bin/env python3
"""S2 v3 Phase 0 repair pilot: every cell at every candidate task's post-setup state.

Runs inside the LO-VM container (the certified OSWorld VM's own LibreOffice 7.3.7.2 userland plus
Xvfb and openbox), CPU only, no network, through infra/slurm/host-single-node/s2v3-pilot-cpu.sbatch.
System Python 3.10, standard library plus the image's own PIL, python-xlib, pyatspi and PyAutoGUI
(the postconfig keys go through PyAutoGUI, as the VM's postconfig does).

Instrument (registration v3.1, P0.2-P0.3 as emulated here). Each worker owns a private copy of
/usr/lib/libreoffice whose fundamentalrc points both system layers (``xcsxcu:`` and ``res:``) at a
private copy of /etc/libreoffice/registry, so a cell's selector file sits in the system
configuration layer itself, next to main.xcd, exactly where the derived image puts it (only the
directory path differs). The "derived" registry adds what the Arabic language pack would add
(Langpack-ar.xcd and res/registry_ar.xcd, here generated) and the generated gettext catalogs
under program/resource/ar; it is the same in every derived cell. The cells differ only in one
file, ``zz-s2v3-cell.xcd`` (cell selector), byte-for-byte recorded:

  S    stock: the pristine registry, no selector, no catalogs (O6 reference)
  E    en-LTR:  ooLocale en-US, UIMirroring false
  E2   en-LTR again (A/A replicate)
  A    ar-LTR:  ooLocale ar,    UIMirroring false
  ER   en-RTL:  ooLocale en-US, UIMirroring true
  AR   ar-RTL:  ooLocale ar,    UIMirroring true
  AD   ar, no UIMirroring key (the layout follows the language; P7)
  Q    tagged:  ooLocale qtz (LibreOffice's KeyID UI language; registry tagged), UIMirroring false
  PL   placebo: the en-LTR selector, and every toolbar's items in a fixed seeded random order
       (the toolbar definitions under share/config/soffice.cfg/modules/*/toolbar, PCG64-free
       hash-seeded shuffle with seed 42): the most-clicked chrome targets relocate by a large,
       direction-free permutation; text, menus, sidebar and status bar stay as in en-LTR.
       (A window-state DockingArea pin in the system layer did not move the toolbars: debug
       job 1123, three forms.)
  dev tasks only:
  ER2  en-RTL again (A/A replicate of the mirrored cell)
  PCL  planted coupled string, left to right: E plus an en_US catalog that renders the status bar's
       language field as "English (USA):"
  PCR  the same plant mirrored (ER plus the catalog): bidi moves the colon in a mirrored VCL widget,
       so O2 on PCL-PCR must flag that field
  PD   planted document change: ER with one text run of the document changed before it opens
       (O5 must fail)

Every derived cell also pins, finalized: SheetPrefix "Sheet", CTLFont false,
EnglishFunctionName true; the interface language is set by both of its keys (Setup ooLocale and
Linguistic UILocale); ooSetupSystemLocale stays at its default (the system locale). A container-fidelity layer, identical in
every cell including S, pins the icon theme the VM's GNOME session uses (Yaru), because openbox
gives LibreOffice no desktop to infer it from. GTK caret blinking is off in every cell (a
deterministic screenshot), through the profile's GTK settings.

Per (task, cell): stage the task's setup from the pinned file cache (download, open; other steps
recorded as not emulated), start LibreOffice on the document, wait for its window title,
maximize, settle, screenshot until two consecutive frames agree, dump the accessibility tree,
(dev tasks) run the functional edit probe, replay the task's own postconfig (strict
activate_window, Ctrl+S, Enter, sleeps, convert) and keep every result file the checker reads.

Usage: python3 capture.py <pool-v3.json> <out_dir> [--workers 16] [--only-tasks a,b] [--cells E,ER]
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import zipfile
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalog as CAT  # noqa: E402
import reachability as RCH  # noqa: E402  (checker-mutation harness: postconfig planning)

LO_SRC = Path("/usr/lib/libreoffice")
REG_SRC = Path("/etc/libreoffice/registry")
PROFILE_TEMPLATE = Path("/home/user/.config/libreoffice/4/user")
CACHE = Path("/inputs/file_cache_1e112283/files")
OSW = Path("/inputs/OSWorld/evaluation_examples/examples")
URL_PREFIX = "https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/"
SCREEN = (1920, 1080)
SEED = 42
DOMAINS = sorted(set("acc accessibility avmedia basctl bib chart cnr cnt cui dba dbu dkt editeng flt for "
                     "frm fps fwk imp lng oox pcr rpt sb sc sca scc sd sfx sm svl svt svx sw uui vcl wiz "
                     "wpt xsc".split()))
APP_FLAG = {"libreoffice_calc": "--calc", "libreoffice_impress": "--impress", "libreoffice_writer": "--writer"}
T0 = time.monotonic()
LOCK = threading.Lock()

XCD_HEAD = ('<?xml version="1.0"?>\n<oor:data xmlns:xs="http://www.w3.org/2001/XMLSchema" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:oor="http://openoffice.org/2001/registry">\n')
XCD_TAIL = "</oor:data>\n"


def log(msg: str) -> None:
    with LOCK:
        print(f"[{time.monotonic() - T0:8.1f}s] {msg}", flush=True)


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha_file(p: Path) -> str | None:
    return sha(p.read_bytes()) if p.is_file() else None


def run(argv, env=None, timeout=60, **kw):
    try:
        r = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=timeout, **kw)
        return {"rc": r.returncode, "out": r.stdout[-4000:], "err": r.stderr[-1500:]}
    except Exception as exc:  # noqa: BLE001
        return {"rc": None, "error": repr(exc)}


# ------------------------------------------------------------------------------------------
# configuration files


def prop(name: str, value: str, typ: str | None = None) -> str:
    t = f' oor:type="{typ}"' if typ else ""
    return f'<prop oor:name="{name}" oor:finalized="true"{t}><value>{value}</value></prop>'


def comp(package: str, name: str, body: str) -> str:
    return f'<oor:component-data oor:package="{package}" oor:name="{name}">{body}</oor:component-data>\n'


def langpack(lang: str) -> str:
    return XCD_HEAD + comp("org.openoffice", "Setup",
                           '<node oor:name="Office"><node oor:name="InstalledLocales">'
                           f'<node oor:name="{lang}" oor:op="replace"><prop oor:name="Origin"><value>OpenOffice.org</value>'
                           '</prop></node></node></node>') + XCD_TAIL


def toolbar_states() -> dict[str, list[str]]:
    """Window-state components and the toolbar resource names defined in the system layer."""
    out: dict[str, set[str]] = {}
    pat = re.compile(r'<oor:component-data[^>]*oor:name="(\w+WindowState)"')
    for f in sorted(REG_SRC.glob("*.xcd")):
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in pat.finditer(text):
            name = m.group(1)
            end = text.find("</oor:component-data>", m.end())
            for tb in re.findall(r'oor:name="(private:resource/toolbar/[A-Za-z0-9_]+)"', text[m.end():end]):
                out.setdefault(name, set()).add(tb)
    return {k: sorted(v) for k, v in out.items()}


TOOLBAR_STATES: dict[str, list[str]] = {}
PLACEBO_APPS = ("CalcWindowState", "WriterWindowState", "ImpressWindowState")


def selector(cell: str) -> str | None:
    if cell == "S":
        return None
    locale = {"A": "ar", "AR": "ar", "AD": "ar", "Q": "qtz"}.get(cell, "en-US")
    mirror = {"ER": "true", "AR": "true", "ER2": "true", "PCR": "true", "PD": "true", "AD": None}.get(cell, "false")
    # ooSetupSystemLocale (number, date and paper defaults) is left at its default, the system
    # locale (en_US.UTF-8 in every cell), so it is held fixed without a pin: pinning it to en-US
    # changed the default paper from A4 to Letter in saved files (smoke 1124, S against E).
    setup = '<node oor:name="L10N">' + prop("ooLocale", locale) + "</node>"
    # The interface language has two keys: ooLocale (gettext catalogs) and Linguistic's UILocale,
    # which, when the profile sets it, decides the configuration locale of every registry label
    # (menus, commands, toolbars). Both carry the cell's language (smoke job 1116 and debug 1120:
    # with ooLocale alone the catalogs switched and the registry labels stayed English).
    ling = '<node oor:name="General">' + prop("UILocale", locale) + "</node>"
    ctl = '<node oor:name="I18N"><node oor:name="CTL">' + prop("CTLFont", "false")
    if mirror is not None:
        ctl += prop("UIMirroring", mirror)
    ctl += "</node></node>"
    calc = ('<node oor:name="Defaults"><node oor:name="Sheet">' + prop("SheetPrefix", "Sheet") + "</node></node>"
            '<node oor:name="Formula"><node oor:name="Syntax">' + prop("EnglishFunctionName", "true") + "</node></node>")
    body = (comp("org.openoffice", "Setup", setup) + comp("org.openoffice.Office", "Linguistic", ling)
            + comp("org.openoffice.Office", "Common", ctl) + comp("org.openoffice.Office", "Calc", calc))
    return XCD_HEAD + body + XCD_TAIL


TB_ITEM = re.compile(r"(<toolbar:toolbar(?:item|separator)\b[^>]*/>)")


def shuffled_toolbar(text: str, key: str) -> str:
    """The same toolbar definition with its items (and separators) in a seeded random order."""
    items = TB_ITEM.findall(text)
    if len(items) < 2:
        return text
    order = sorted(range(len(items)), key=lambda i: hashlib.sha256(f"{SEED}:{key}:{i}".encode()).hexdigest())
    it = iter([items[i] for i in order])
    return TB_ITEM.sub(lambda m: next(it), text)


def fidelity_xcd(symbol_style: str | None) -> str | None:
    if not symbol_style:
        return None
    return XCD_HEAD + comp("org.openoffice.Office", "Common",
                           '<node oor:name="Misc">' + prop("SymbolStyle", symbol_style) + "</node>") + XCD_TAIL


GTK_SETTINGS = "[Settings]\ngtk-cursor-blink=false\n"

# ------------------------------------------------------------------------------------------
# worker environment


class Worker:
    def __init__(self, idx: int, cat_dir: Path, symbol_style: str | None):
        self.idx = idx
        self.root = Path(f"/tmp/w{idx}")
        self.disp = 60 + idx
        self.lo = self.root / "lo"
        self.cat_dir = cat_dir
        self.symbol_style = symbol_style
        self.procs: list = []
        self.a11y_env: dict = {}

    def setup(self) -> dict:
        if self.root.exists():
            shutil.rmtree(self.root)
        self.root.mkdir(parents=True)
        shutil.copytree(LO_SRC, self.lo, symlinks=True)
        # relative symlinks (the icon-theme archives, among others) would dangle in the copy:
        # re-point them at their absolute targets (wave-1 pilot: no icons, text-only toolbars)
        self.relinked = 0
        for p in self.lo.rglob("*"):
            if p.is_symlink():
                tgt = os.readlink(p)
                if not tgt.startswith("/"):
                    orig = LO_SRC / p.relative_to(self.lo)
                    absolute = os.path.normpath(os.path.join(os.path.dirname(str(orig)), tgt))
                    p.unlink()
                    p.symlink_to(absolute)
                    self.relinked += 1
        res = self.lo / "program" / "resource"
        for lang_dir in ("ar", "qtz"):
            d = res / lang_dir / "LC_MESSAGES"
            d.mkdir(parents=True, exist_ok=True)
            if lang_dir == "ar":
                for dom in DOMAINS:
                    (d / f"{dom}.mo").symlink_to(self.cat_dir / "all.mo")
        # placebo toolbars: originals and seeded shuffles of every toolbar definition
        self.tb_files = sorted((self.lo / "share" / "config" / "soffice.cfg" / "modules").glob("*/toolbar/*.xml"))
        self.tb_orig = {p: p.read_bytes() for p in self.tb_files}
        self.tb_pl = {}
        for p in self.tb_files:
            if p.is_symlink():
                tgt = os.readlink(p)
                p.unlink()
                shutil.copyfile(tgt, p)
            text = self.tb_orig[p].decode("utf-8")
            self.tb_pl[p] = shuffled_toolbar(text, str(p.relative_to(self.lo))).encode("utf-8")
        self.tb_state = "orig"
        fid = fidelity_xcd(self.symbol_style)
        for base in ("stock", "derived", "qtz"):
            reg = self.root / f"reg-{base}"
            shutil.copytree(REG_SRC, reg, symlinks=False)
            if fid:
                (reg / "zz-s2v3-fidelity.xcd").write_text(fid)
            if base == "derived":
                (reg / "Langpack-ar.xcd").write_text(langpack("ar"))
                shutil.copyfile(self.cat_dir / "registry_ar.xcd", reg / "res" / "registry_ar.xcd")
            if base == "qtz":
                (reg / "Langpack-qtz.xcd").write_text(langpack("qtz"))
                shutil.copyfile(self.cat_dir / "registry_qtz.xcd", reg / "res" / "registry_qtz.xcd")
        self.rc_text = (LO_SRC / "program" / "fundamentalrc").read_text()
        self.start_display()
        info = self.start_a11y()
        kb = run(["setxkbmap", "-query"], env={"DISPLAY": f":{self.disp}", "PATH": "/usr/bin:/bin"})
        return {"a11y": info, "setxkbmap_query": kb, "relinked_symlinks": self.relinked,
                "toolbar_files": len(self.tb_files),
                "toolbar_files_shuffled": sum(1 for p in self.tb_files if self.tb_pl[p] != self.tb_orig[p])}

    def set_toolbars(self, state: str) -> None:
        if state == self.tb_state:
            return
        src = self.tb_pl if state == "pl" else self.tb_orig
        for p in self.tb_files:
            p.write_bytes(src[p])
        self.tb_state = state

    def point_registry(self, base: str) -> str:
        reg = self.root / f"reg-{base}"
        out = []
        for line in self.rc_text.splitlines():
            if line.startswith("BRAND_BASE_DIR="):
                line = f"BRAND_BASE_DIR=file://{self.lo}"
            if line.startswith("CONFIGURATION_LAYERS="):
                line = line.replace("file:///etc/libreoffice/registry", f"file://{reg}")
            out.append(line)
        text = "\n".join(out) + "\n"
        (self.lo / "program" / "fundamentalrc").write_text(text)
        return [ln for ln in out if ln.startswith("CONFIGURATION_LAYERS=")][0]

    def start_display(self):
        xlog = (self.root / "xvfb.log").open("wb")
        self.procs.append(subprocess.Popen(["Xvfb", f":{self.disp}", "-screen", "0", f"{SCREEN[0]}x{SCREEN[1]}x24",
                                            "-nolisten", "tcp"], stdout=xlog, stderr=subprocess.STDOUT,
                                           start_new_session=True))
        for _ in range(100):
            if subprocess.run(["xdpyinfo"], env={"DISPLAY": f":{self.disp}"}, capture_output=True).returncode == 0:
                break
            time.sleep(0.2)
        wm_home = self.root / "wm-home"
        wm_home.mkdir(parents=True, exist_ok=True)
        self.procs.append(subprocess.Popen(["openbox"], env={"DISPLAY": f":{self.disp}", "HOME": str(wm_home),
                                                             "PATH": "/usr/bin:/bin"},
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True))
        time.sleep(0.8)

    def start_a11y(self) -> dict:
        env = self.base_env(self.root / "a11y-home")
        info = {"ok": False}
        try:
            r = subprocess.run(["dbus-daemon", "--session", "--fork", "--print-address=1", "--print-pid=1", "--nopidfile"],
                               env=env, capture_output=True, text=True, timeout=20)
            lines = r.stdout.strip().splitlines()
            if r.returncode != 0 or len(lines) < 2:
                info["dbus_error"] = r.stderr[-300:]
                return info
            env["DBUS_SESSION_BUS_ADDRESS"] = lines[0]
            info["dbus_pid"] = int(lines[1])
            subprocess.Popen(["/usr/libexec/at-spi-bus-launcher", "--launch-immediately"], env=env,
                             stdout=(self.root / "atspi-launcher.log").open("wb"), stderr=subprocess.STDOUT,
                             start_new_session=True)
            time.sleep(2.0)
            subprocess.Popen(["/usr/libexec/at-spi2-registryd"], env=env,
                             stdout=(self.root / "atspi-registryd.log").open("wb"), stderr=subprocess.STDOUT,
                             start_new_session=True)
            time.sleep(1.0)
            self.a11y_env = {"DBUS_SESSION_BUS_ADDRESS": lines[0], "SAL_ACCESSIBILITY_ENABLED": "1",
                             "GTK_MODULES": "gail:atk-bridge", "NO_AT_BRIDGE": "0"}
            info["ok"] = True
        except Exception as exc:  # noqa: BLE001
            info["error"] = repr(exc)
        return info

    def base_env(self, home: Path) -> dict:
        return {"HOME": str(home), "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8", "DISPLAY": f":{self.disp}",
                "SAL_USE_VCLPLUGIN": "gtk3", "PYTHONUSERBASE": "/home/user/.local",
                "PYTHONPATH": "/usr/lib/python3/dist-packages:/usr/local/lib/python3.10/dist-packages"}

    def stop(self):
        for p in reversed(self.procs):
            with contextlib.suppress(Exception):
                os.killpg(p.pid, signal.SIGKILL)


# ------------------------------------------------------------------------------------------
# screen and accessibility capture

SHOT = (
    "import sys, hashlib\nfrom Xlib import display as xd, X\nfrom PIL import Image\n"
    "d = xd.Display(sys.argv[1]); r = d.screen().root; g = r.get_geometry()\n"
    "raw = r.get_image(0, 0, g.width, g.height, X.ZPixmap, 0xffffffff)\n"
    "img = Image.frombytes('RGB', (g.width, g.height), raw.data, 'raw', 'BGRX')\n"
    "b = img.tobytes(); print(hashlib.sha256(b).hexdigest())\n"
    "if len(sys.argv) > 2: img.save(sys.argv[2])\n"
)

A11Y_DUMP = r'''
import json, sys
import pyatspi
SKIP = {pyatspi.ROLE_TABLE, pyatspi.ROLE_TREE_TABLE, pyatspi.ROLE_DOCUMENT_TEXT, pyatspi.ROLE_DOCUMENT_SPREADSHEET,
        pyatspi.ROLE_DOCUMENT_PRESENTATION, pyatspi.ROLE_DOCUMENT_FRAME, pyatspi.ROLE_PARAGRAPH}
out = []
def walk(node, path, depth):
    if len(out) > 6000 or depth > 30:
        return
    try:
        role = node.getRoleName(); name = node.name or ""
    except Exception:
        return
    box, showing = None, False
    try:
        ext = node.queryComponent().getExtents(pyatspi.DESKTOP_COORDS)
        box = [ext.x, ext.y, ext.width, ext.height]
        showing = pyatspi.STATE_SHOWING in node.getState().getStates()
    except Exception:
        pass
    if box is not None:
        out.append({"path": path, "role": role, "name": name, "box": box, "showing": showing})
    try:
        if node.getRole() in SKIP:
            return
        n = node.childCount
    except Exception:
        return
    for i in range(min(n, 400)):
        try:
            c = node.getChildAtIndex(i)
        except Exception:
            continue
        if c is not None:
            walk(c, path + [i], depth + 1)
desk = pyatspi.Registry.getDesktop(0)
apps = []
for i in range(desk.childCount):
    a = desk.getChildAtIndex(i)
    if a is None: continue
    apps.append(a.name)
    if "soffice" in (a.name or "").lower() or "libreoffice" in (a.name or "").lower():
        walk(a, [i], 0)
open(sys.argv[1], "w").write(json.dumps({"apps": apps, "nodes": out}, ensure_ascii=False))
print(len(out))
'''


def windows(env: dict) -> list[dict]:
    r = subprocess.run(["wmctrl", "-lG"], env=env, capture_output=True, text=True)
    wins = []
    for line in r.stdout.splitlines():
        parts = line.split(None, 7)
        if len(parts) >= 7:
            wid, _desk, x, y, w, h = parts[:6]
            title = parts[7] if len(parts) == 8 else ""
            wins.append({"id": wid, "x": int(x), "y": int(y), "w": int(w), "h": int(h), "title": title,
                         "title_utf8_hex": title.encode().hex()})
    return wins


def frame_hash(env, png: Path | None = None) -> str | None:
    argv = ["python3", "-c", SHOT, env["DISPLAY"]] + ([str(png)] if png else [])
    r = run(argv, env=env, timeout=60)
    return r.get("out", "").strip().splitlines()[-1] if r.get("rc") == 0 and r.get("out") else None


# ------------------------------------------------------------------------------------------
# task staging and probes


def stage_task(task: dict, vmroot: Path) -> tuple[list[str], list[dict], dict]:
    cfg = json.loads((OSW / task["app"] / f"{task['task_id']}.json").read_text())
    to_open, steps = [], []
    for st in cfg.get("config", []):
        typ, par = st.get("type"), st.get("parameters", {})
        if typ == "download":
            for f in par.get("files", []):
                url, path = f["url"], f["path"]
                rel = unquote(url[len(URL_PREFIX):]) if url.startswith(URL_PREFIX) else None
                src = CACHE / rel if rel else None
                dst = vmroot / RCH.resolve_vm_path(path).lstrip("/")
                ok = bool(src and src.is_file())
                if ok:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(src, dst)
                steps.append({"type": "download", "path": path, "cached": ok})
        elif typ == "open":
            to_open.append(RCH.resolve_vm_path(par["path"]))
            steps.append({"type": "open", "path": par["path"]})
        elif typ in ("launch", "execute", "command"):
            cmd = par.get("command")
            argv = cmd if isinstance(cmd, list) else str(cmd).split()
            files = [a for a in argv if isinstance(a, str) and a.startswith("/home/user/")]
            if argv and any(x in str(argv[0]) for x in ("soffice", "libreoffice")) and files and "--convert-to" not in argv:
                to_open.extend(files)
                steps.append({"type": typ, "emulated_as": "open", "files": files})
            else:
                steps.append({"type": typ, "emulated": False, "argv_head": [str(a)[:60] for a in argv[:4]]})
        else:
            steps.append({"type": typ, "emulated": False})
    return to_open, steps, cfg


def plant_document(path: Path) -> dict:
    """Change the first text run of an OOXML or ODF document in place (PD cell)."""
    ext = path.suffix.lower()
    targets = {".xlsx": ("xl/sharedStrings.xml", r"(<t(?: [^>]*)?>)([^<]+)(</t>)"),
               ".docx": ("word/document.xml", r"(<w:t(?: [^>]*)?>)([^<]+)(</w:t>)"),
               ".pptx": (None, r"(<a:t>)([^<]+)(</a:t>)"),
               ".odt": ("content.xml", r"(<text:p[^>]*>)([^<]+)(</text:p>)"),
               ".ods": ("content.xml", r"(<text:p[^>]*>)([^<]+)(</text:p>)"),
               ".odp": ("content.xml", r"(<text:p[^>]*>)([^<]+)(</text:p>)")}
    if ext not in targets or not path.is_file():
        return {"planted": False, "reason": f"unsupported {ext}"}
    member, pat = targets[ext]
    zin = zipfile.ZipFile(path)
    names = zin.namelist()
    if member is None:
        slides = sorted((n for n in names if re.match(r"ppt/slides/slide\d+\.xml$", n)),
                        key=lambda n: int(re.findall(r"\d+", n)[-1]))
        member = slides[0] if slides else None
    if member not in names:
        return {"planted": False, "reason": f"no {member}"}
    data = {n: zin.read(n) for n in names}
    infos = {n: zin.getinfo(n) for n in names}
    zin.close()
    text = data[member].decode("utf-8")
    m = re.search(pat, text)
    if not m:
        return {"planted": False, "reason": "no text run"}
    old = m.group(2)
    new = "S2V3 PLANTED CHANGE"
    text = text[:m.start(2)] + new + text[m.end(2):]
    data[member] = text.encode("utf-8")
    tmp = path.with_suffix(path.suffix + ".tmp")
    with zipfile.ZipFile(tmp, "w") as zout:
        for n in names:
            zout.writestr(infos[n], data[n])
    tmp.replace(path)
    return {"planted": True, "member": member, "old_len": len(old)}


def plant_mo(lo: Path, pairs_file: Path) -> dict:
    """PC cell: an en_US svt catalog adding a trailing colon to the status bar language name."""
    entries = {}
    for line in pairs_file.read_text(encoding="utf-8").splitlines():
        ctx, msg = line.split("\t", 1)
        if msg == "English (USA)":
            entries[f"{ctx}\x04{msg}"] = "English (USA):"
    d = lo / "program" / "resource" / "en_US" / "LC_MESSAGES"
    for dom in ("svt", "svx", "vcl"):
        CAT.write_mo(d / f"{dom}.mo", entries)
    return {"entries": len(entries), "contexts": sorted({k.split(chr(4))[0] for k in entries})[:10]}


def key(env: dict, combo: str) -> dict:
    keys = [k for k in combo.split("+") if k]
    call = (f"pyautogui.hotkey({keys!r}[0], *{keys!r}[1:])" if len(keys) > 1 else f"pyautogui.press({keys[0]!r})")
    r = run(["python3", "-c", f"import pyautogui; pyautogui.PAUSE=0.05; {call}"], env=env, timeout=30)
    return {"combo": combo, "rc": r.get("rc")}


def typewrite(env: dict, text: str) -> dict:
    r = run(["python3", "-c", f"import pyautogui; pyautogui.write({text!r}, interval=0.02)"], env=env, timeout=60)
    return {"type": text, "rc": r.get("rc")}


EDIT_PROBE = {
    "libreoffice_calc": [("key", "ctrl+end"), ("key", "down"), ("key", "down"), ("type", "s2v3probe"),
                         ("key", "enter"), ("type", "=SUM(1;2)"), ("key", "enter")],
    "libreoffice_writer": [("key", "ctrl+end"), ("key", "enter"), ("type", "s2v3 probe 123 (x) ~!@#")],
    "libreoffice_impress": [],
}


def wait_written(path: Path, before, timeout: float) -> float | None:
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        if path.is_file():
            st = path.stat()
            if before is None or (st.st_mtime, st.st_size) != before:
                det = time.monotonic() - start
                time.sleep(0.3)
                st2 = path.stat()
                if (st2.st_mtime, st2.st_size) == (st.st_mtime, st.st_size):
                    return round(det, 3)
        time.sleep(0.1)
    return None


def replay_postconfig(env: dict, cfg: dict, vmroot: Path, opened: list[str], soffice: Path) -> dict:
    steps = RCH.plan_postconfig(cfg.get("evaluator", {}).get("postconfig", []))
    events = []
    last_activated = None
    for st in steps:
        if st.kind == "activate":
            r = run(["wmctrl", "-Fa" if st.strict else "-a", st.arg], env=env)
            events.append({"activate": st.arg, "strict": st.strict, "ok": r.get("rc") == 0})
            last_activated = st.arg
        elif st.kind == "sleep":
            time.sleep(min(st.seconds, 5.0))
            events.append({"sleep": st.seconds})
        elif st.kind == "key":
            target = None
            if st.arg == "ctrl+s":
                target = next((p for p in opened if last_activated and RCH.window_title_for(p) == last_activated), None)
                if target is None and opened:
                    target = opened[0]
            if target:
                hp = vmroot / target.lstrip("/")
                before = (hp.stat().st_mtime, hp.stat().st_size) if hp.is_file() else None
                wins_before = {w["title"] for w in windows(env)}
                k = key(env, st.arg)
                secs = wait_written(hp, before, 30.0)
                dialogs = sorted({w["title"] for w in windows(env)} - wins_before)
                events.append({"save": target, "key": k, "written": secs is not None, "seconds": secs,
                               "dialogs": dialogs, "sha256": sha_file(hp)})
            else:
                events.append({"key": key(env, st.arg)})
        elif st.kind == "convert":
            mapped = [str(soffice)] + [str(vmroot / a.lstrip("/")) if a.startswith("/") else a for a in st.argv[1:]]
            r = run(mapped, env=env, timeout=120)
            time.sleep(2.0)
            events.append({"convert": list(st.argv), "rc": r.get("rc")})
        else:
            events.append({"unemulated": st.kind, "arg": st.arg})
    return {"steps": [s.kind for s in steps], "events": events}


# ------------------------------------------------------------------------------------------


def render(w: Worker, task: dict, cell: str, out: Path, pairs_file: Path, dev: bool) -> dict:
    rec: dict = {"task_id": task["task_id"], "app": task["app"], "split": task["split"], "cell": cell}
    work = w.root / "run"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    base = "stock" if cell == "S" else ("qtz" if cell == "Q" else "derived")
    reg = w.root / f"reg-{base}"
    for b in ("stock", "derived", "qtz"):
        with contextlib.suppress(FileNotFoundError):
            (w.root / f"reg-{b}" / "zz-s2v3-cell.xcd").unlink()
    sel = selector(cell)
    if sel:
        (reg / "zz-s2v3-cell.xcd").write_text(sel)
        rec["selector_sha256"] = sha(sel.encode())
    rec["registry_base"] = base
    w.set_toolbars("pl" if cell == "PL" else "orig")
    rec["configuration_layers"] = w.point_registry(base)
    en_us = w.lo / "program" / "resource" / "en_US"
    if en_us.exists():
        shutil.rmtree(en_us)
    if cell in ("PCL", "PCR"):
        rec["plant_mo"] = plant_mo(w.lo, pairs_file)
    vmroot = work / "vm"
    to_open, steps, cfg = stage_task(task, vmroot)
    rec["setup_steps"] = steps
    if cell == "PD" and to_open:
        rec["plant_document"] = plant_document(vmroot / to_open[0].lstrip("/"))
    home = work / "home"
    prof = home / "user"
    shutil.copytree(PROFILE_TEMPLATE, prof)
    gtkd = home / ".config" / "gtk-3.0"
    gtkd.mkdir(parents=True)
    (gtkd / "settings.ini").write_text(GTK_SETTINGS)
    env = w.base_env(home)
    env.update(w.a11y_env)
    targets = [str(vmroot / p.lstrip("/")) for p in to_open[:1]]
    rec["opened"] = to_open[:1]
    soffice = w.lo / "program" / "soffice"
    argv = [str(soffice), "--norestore", "--nologo", f"-env:UserInstallation=file://{home}"] + (targets or [APP_FLAG[task["app"]]])
    expected = (task.get("activate_window_titles") or [None])[0]
    if not expected and to_open:
        expected = RCH.window_title_for(to_open[0])
    rec["expected_title"] = expected
    t = time.monotonic()
    proc = subprocess.Popen(argv, env=env, stdout=(work / "soffice.log").open("wb"), stderr=subprocess.STDOUT,
                            start_new_session=True)
    title = None
    for _ in range(360):
        ws = [x for x in windows(env) if "LibreOffice" in x["title"]]
        if expected:
            hit = [x for x in ws if x["title"] == expected]
            if hit:
                title = hit[0]["title"]
                break
            if ws and time.monotonic() - t > 45:
                title = ws[0]["title"]
                break
        elif ws:
            title = ws[0]["title"]
            break
        time.sleep(0.25)
    rec["window_seconds"] = round(time.monotonic() - t, 1)
    rec["title_found"] = title
    if title:
        subprocess.run(["wmctrl", "-r", title, "-b", "add,maximized_vert,maximized_horz"], env=env, capture_output=True)
    time.sleep(6.0)
    hashes = []
    for _ in range(10):
        h = frame_hash(env)
        hashes.append(h)
        if len(hashes) >= 2 and h is not None and hashes[-1] == hashes[-2]:
            break
        time.sleep(1.0)
    png = out / "shots" / task["task_id"] / f"{cell}.png"
    png.parent.mkdir(parents=True, exist_ok=True)
    final = frame_hash(env, png)
    rec["frames"] = len(hashes)
    rec["stable"] = len(hashes) >= 2 and hashes[-1] == hashes[-2] and final == hashes[-1]
    rec["screenshot_sha256"] = sha_file(png)
    rec["pixels_sha256"] = final
    rec["windows"] = windows(env)
    if w.a11y_env:
        a11y = out / "a11y" / task["task_id"] / f"{cell}.json"
        a11y.parent.mkdir(parents=True, exist_ok=True)
        dump = w.root / "a11y_dump.py"
        dump.write_text(A11Y_DUMP)
        r = run(["python3", str(dump), str(a11y)], env=env, timeout=120)
        rec["a11y_nodes"] = int(r["out"].strip().splitlines()[-1]) if r.get("rc") == 0 and r.get("out") else None
        rec["a11y_sha256"] = sha_file(a11y)
        if rec["a11y_nodes"] is None:
            rec["a11y_error"] = {k: r.get(k) for k in ("rc", "err", "error")}
    if dev and EDIT_PROBE.get(task["app"]) and cell not in ("PD",):
        if title:
            run(["wmctrl", "-Fa", title], env=env)
        probe = []
        for kind, arg in EDIT_PROBE[task["app"]]:
            probe.append(key(env, arg) if kind == "key" else typewrite(env, arg))
            time.sleep(0.2)
        rec["edit_probe"] = probe
        time.sleep(1.0)
    rec["postconfig"] = replay_postconfig(env, cfg, vmroot, to_open, soffice)
    saved_dir = out / "saved" / task["task_id"] / cell
    saved = {}
    result_paths = []
    for kind, path in task.get("result_inputs") or []:
        if kind == "vm_file":
            result_paths.extend(path if isinstance(path, list) else [path])
    for path in result_paths:
        hp = vmroot / RCH.resolve_vm_path(path).lstrip("/")
        if hp.is_file():
            dst = saved_dir / RCH.resolve_vm_path(path).lstrip("/")
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(hp, dst)
            saved[path] = sha_file(dst)
        else:
            saved[path] = None
    rec["saved"] = saved
    if any("save" in e and not e.get("written") for e in rec["postconfig"]["events"]):
        post = out / "shots" / task["task_id"] / f"{cell}.after-postconfig.png"
        rec["after_postconfig_pixels_sha256"] = frame_hash(env, post)
    rec["windows_after"] = [x["title"] for x in windows(env)]
    with contextlib.suppress(Exception):
        os.killpg(proc.pid, signal.SIGKILL)
    with contextlib.suppress(Exception):
        proc.wait(timeout=10)
    subprocess.run(["pkill", "-KILL", "-f", str(work)], capture_output=True)
    for _ in range(40):
        if not any("LibreOffice" in x["title"] for x in windows(env)):
            break
        time.sleep(0.25)
    return rec


def worker_main(w: Worker, items: list, out: Path, pairs_file: Path, results: list, infos: dict):
    try:
        infos[w.idx] = w.setup()
    except Exception as exc:  # noqa: BLE001
        infos[w.idx] = {"setup_error": repr(exc)}
        log(f"w{w.idx} setup failed {exc!r}")
        return
    log(f"w{w.idx} ready a11y={infos[w.idx]['a11y'].get('ok')}")
    for task, cell, dev in items:
        try:
            rec = render(w, task, cell, out, pairs_file, dev)
        except Exception as exc:  # noqa: BLE001
            rec = {"task_id": task["task_id"], "cell": cell, "error": repr(exc)}
        with LOCK:
            results.append(rec)
            with (out / "records.jsonl").open("a") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        log(f"w{w.idx} {task['task_id'][:8]} {cell:3s} {rec.get('window_seconds')}s stable={rec.get('stable')} "
            f"title={'ok' if rec.get('title_found') == rec.get('expected_title') else rec.get('title_found')}")
    w.stop()


def facts(cat_stats: dict) -> dict:
    zips = sorted(p.name for p in (LO_SRC / "share" / "config").glob("images*.zip"))
    prof = PROFILE_TEMPLATE / "registrymodifications.xcu"
    text = prof.read_text(errors="replace") if prof.is_file() else ""
    return {
        "soffice_version": run([str(LO_SRC / "program" / "soffice"), "--version"],
                               env={"HOME": "/tmp/fh", "PATH": "/usr/bin:/bin"}, timeout=90),
        "icon_theme_zips": zips,
        "profile_symbolstyle": re.findall(r'SymbolStyle"[^<]*<value>([^<]*)', text),
        "profile_oolocale": re.findall(r'ooLocale"[^<]*<value>([^<]*)', text),
        "registry_res_files": sorted(p.name for p in (REG_SRC / "res").iterdir()) if (REG_SRC / "res").is_dir() else [],
        "registry_files": sorted(p.name for p in REG_SRC.iterdir()),
        "toolbar_states": TOOLBAR_STATES,
        "catalog": cat_stats,
        "fundamentalrc_sha256": sha_file(LO_SRC / "program" / "fundamentalrc"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pool")
    ap.add_argument("out")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--only-tasks", default="")
    ap.add_argument("--cells", default="S,E,E2,A,ER,AR,AD,Q,PL")
    ap.add_argument("--dev-cells", default="ER2,PCL,PCR,PD")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pool = json.loads(Path(args.pool).read_text())
    tasks = [t for t in pool["tasks"] if t["class"] != "excluded"]
    if args.only_tasks:
        keep = set(args.only_tasks.split(","))
        tasks = [t for t in tasks if t["task_id"][:8] in keep or t["task_id"] in keep]
    log(f"{len(tasks)} tasks; building catalogs")
    cat_dir = Path("/tmp/cat")
    cat_stats = CAT.build(cat_dir)
    pairs_file = cat_dir / "code-pairs.tsv"  # the code pairs, for the planted catalog (PC)
    log(f"catalog: {json.dumps({k: v for k, v in cat_stats.items() if k not in ('examples', 'ui_domains')})}")
    global TOOLBAR_STATES
    TOOLBAR_STATES = toolbar_states()
    f = facts(cat_stats)
    symbol = "yaru" if "images_yaru.zip" in f["icon_theme_zips"] else None
    f["symbol_style_pinned"] = symbol
    shutil.copyfile(cat_dir / "catalog-stats.json", out / "catalog-stats.json")
    for name in ("registry_ar.xcd", "registry_qtz.xcd"):
        shutil.copyfile(cat_dir / name, out / name)
    for cell in ("S", "E", "A", "ER", "AR", "AD", "Q", "PL", "PCL", "PCR", "PD"):
        s = selector(cell)
        (out / "selectors").mkdir(exist_ok=True)
        (out / "selectors" / f"{cell}.xcd").write_text(s or "")
    cells = [c for c in args.cells.split(",") if c]
    dev_cells = [c for c in args.dev_cells.split(",") if c]
    items = []
    for t in tasks:
        dev = t["split"] == "dev"
        for c in cells + (dev_cells if dev else []):
            items.append((t, c, dev))
    workers = [Worker(i, cat_dir, symbol) for i in range(args.workers)]
    shards = [items[i::args.workers] for i in range(args.workers)]
    results: list = []
    infos: dict = {}
    (out / "records.jsonl").write_text("")
    threads = [threading.Thread(target=worker_main, args=(workers[i], shards[i], out, pairs_file, results, infos))
               for i in range(args.workers)]
    for th in threads:
        th.start()
        time.sleep(0.5)
    for th in threads:
        th.join()
    manifest = {}
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name not in ("manifest.json",):
            manifest[str(p.relative_to(out))] = sha_file(p)
    rec = {"schema": "s2v3-phase0-capture-v1", "seed": SEED, "pool_sha256": sha(Path(args.pool).read_bytes()),
           "cells": cells, "dev_cells": dev_cells, "tasks": len(tasks), "items": len(items), "workers": args.workers,
           "facts": f, "worker_info": infos, "wall_seconds": round(time.monotonic() - T0, 1),
           "job": os.environ.get("Q2M_SLURM_JOB_ID"),
           "code_sha256": {n: sha_file(Path(__file__).resolve().parent / n) for n in ("capture.py", "catalog.py", "reachability.py")}}
    (out / "capture-record.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1))
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    log(f"done: {len(results)} renders")
    return 0


if __name__ == "__main__":
    sys.exit(main())
