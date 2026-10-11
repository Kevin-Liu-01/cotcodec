#!/usr/bin/env python3
"""S2 v3 Phase 0 pilot, part A: switch mechanics and content leaks on the real LibreOffice 7.3.7.2.

Runs inside the LO-VM container (the OSWorld VM's own userland: Ubuntu LibreOffice
1:7.3.7-0ubuntu0.22.04.4, gtk3 VCL plugin, Xvfb + openbox), CPU only, no network, through
infra/slurm/host-single-node/q2-mutation-cpu.sbatch in run mode. Standard library plus the
image's own PIL, python-xlib, pyatspi and pyuno. Nothing here downloads anything.

What it does not have: the shipped Arabic catalogs (libreoffice-l10n-ar is not in the image,
and fetching it needs the program owner's permission). "Pseudo-ar" cells below install a
minimal Langpack-ar.xcd and an Arabic sc.mo with one string, so they test the mechanics of
an Arabic interface language (layout default, UIMirroring override, content strings), not the
real catalogs.

Layers: a private copy of /usr/lib/libreoffice in /tmp/lo with fundamentalrc edited so that a
per-cell directory /tmp/cells/<cell>/layer is an extra xcsxcu configuration layer after the
system layer /etc/libreoffice/registry (the derived image would put the same .xcd files in
/etc/libreoffice/registry), and per-cell .mo files under /tmp/lo/program/resource.

Parts:
  A1 facts: version, VCL plugins, fonts for Arabic, layers, resources.
  A2 content probes (headless, UNO): the first sheet name of a new Calc document, the
     effective UI locale, and the sheet names inside a saved .xlsx, per cell K0-K6.
  A3 layout probes (GUI, gtk3): blank Calc, Impress and Writer per cell L0-L5; a screenshot,
     the window list and geometry, and an AT-SPI dump of the frame when the a11y bus starts.
  A4 analysis: reflection check of matched AT-SPI boxes between LTR and RTL cells, a coarse
     column-ink check on the screenshots, and window-title identity across cells.

Usage (inside the container): python3 s2v3_pilot.py <out_dir>
Seed: 42 (no randomness is used; the seed is recorded for the record).
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
import signal
import struct
import subprocess
import sys
import time
import zipfile
from pathlib import Path

SEED = 42
LO_SRC = Path("/usr/lib/libreoffice")
LO = Path("/tmp/lo")
CELLS_ROOT = Path("/tmp/cells")
PROFILE_TEMPLATE = Path("/home/user/.config/libreoffice/4/user")
FSI, PDI = "⁨", "⁩"
AR_SHEET = "ورقة"  # Arabic "sheet" (pseudo catalog, one string)
TAG_SHEET = "⟦Sheet⟧"  # visibly tagged English
SCREEN = (1920, 1080)

T0 = time.monotonic()


def log(msg: str) -> None:
    print(f"[{time.monotonic() - T0:8.1f}s] {msg}", flush=True)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def run(argv, env=None, timeout=60, **kw):
    try:
        r = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=timeout, **kw)
        return {"argv": argv, "rc": r.returncode, "out": r.stdout[-4000:], "err": r.stderr[-2000:]}
    except Exception as exc:  # noqa: BLE001 - record and continue
        return {"argv": argv, "rc": None, "error": repr(exc)}


# --------------------------------------------------------------------------------------
# gettext .mo writer (GNU format, little endian); context keys are "ctxt\x04msgid"


def write_mo(path: Path, entries: dict[str, str]) -> None:
    header = "Content-Type: text/plain; charset=UTF-8\nPlural-Forms: nplurals=1; plural=0;\n"
    items = sorted({"": header, **entries}.items(), key=lambda kv: kv[0].encode())
    n = len(items)
    o_off, t_off = 28, 28 + 8 * n
    data_off = 28 + 16 * n
    ids, strs, otab, ttab = b"", b"", [], []
    for k, _ in items:
        kb = k.encode()
        otab.append((len(kb), data_off + len(ids)))
        ids += kb + b"\0"
    base = data_off + len(ids)
    for _, v in items:
        vb = v.encode()
        ttab.append((len(vb), base + len(strs)))
        strs += vb + b"\0"
    out = struct.pack("<7I", 0x950412DE, 0, n, o_off, t_off, 0, data_off)
    out += b"".join(struct.pack("<2I", *x) for x in otab)
    out += b"".join(struct.pack("<2I", *x) for x in ttab)
    out += ids + strs
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(out)


# --------------------------------------------------------------------------------------
# configuration layer files


XCD_HEAD = ('<?xml version="1.0"?>\n<oor:data xmlns:xs="http://www.w3.org/2001/XMLSchema" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:oor="http://openoffice.org/2001/registry">\n')


def xcd_ui_mirroring(value: bool) -> str:
    v = "true" if value else "false"
    return (XCD_HEAD + '<oor:component-data oor:name="Common" oor:package="org.openoffice.Office">'
            '<node oor:name="I18N"><node oor:name="CTL">'
            f'<prop oor:name="UIMirroring" oor:finalized="true"><value>{v}</value></prop>'
            '</node></node></oor:component-data>\n</oor:data>\n')


def xcd_sheet_prefix(prefix: str) -> str:
    return (XCD_HEAD + '<oor:component-data oor:name="Calc" oor:package="org.openoffice.Office">'
            '<node oor:name="Defaults"><node oor:name="Sheet">'
            f'<prop oor:name="SheetPrefix" oor:finalized="true"><value>{prefix}</value></prop>'
            '</node></node></oor:component-data>\n</oor:data>\n')


def xcd_ui_locale(lang: str) -> str:
    return (XCD_HEAD + '<oor:component-data oor:name="Setup" oor:package="org.openoffice">'
            '<node oor:name="L10N">'
            f'<prop oor:name="ooLocale" oor:finalized="true"><value>{lang}</value></prop>'
            '</node></oor:component-data>\n</oor:data>\n')


def xcd_langpack(lang: str) -> str:
    return (XCD_HEAD + '<oor:component-data oor:name="Setup" oor:package="org.openoffice">'
            '<node oor:name="Office"><node oor:name="InstalledLocales">'
            f'<node oor:name="{lang}" oor:op="replace"><prop oor:name="Origin"><value>OpenOffice.org</value></prop></node>'
            '</node></node></oor:component-data>\n</oor:data>\n')


# Cell definitions: layer files, resource files, extra environment.
CELLS = {
    # content probes
    "K0_stock": {},
    "K1_en_US_mo_tagged": {"mo": {"en_US": {"STR_TABLE_DEF\x04Sheet": TAG_SHEET}}},
    "K1b_en_mo_tagged": {"mo": {"en": {"STR_TABLE_DEF\x04Sheet": TAG_SHEET}}},
    "K2_en_US_mo_fsi": {"mo": {"en_US": {"STR_TABLE_DEF\x04Sheet": FSI + "Sheet" + PDI}}},
    "K3_en_US_mo_fsi_prefix_pin": {"mo": {"en_US": {"STR_TABLE_DEF\x04Sheet": FSI + "Sheet" + PDI}},
                                   "layer": {"s2v3-sheetprefix.xcd": xcd_sheet_prefix("Sheet")}},
    "K4_pseudo_ar": {"mo": {"ar": {"STR_TABLE_DEF\x04Sheet": AR_SHEET}},
                     "layer": {"Langpack-ar.xcd": xcd_langpack("ar"), "s2v3-uilocale.xcd": xcd_ui_locale("ar")}},
    "K5_pseudo_ar_prefix_pin": {"mo": {"ar": {"STR_TABLE_DEF\x04Sheet": AR_SHEET}},
                                "layer": {"Langpack-ar.xcd": xcd_langpack("ar"), "s2v3-uilocale.xcd": xcd_ui_locale("ar"),
                                          "s2v3-sheetprefix.xcd": xcd_sheet_prefix("Sheet")}},
    "K6_stock_prefix_pin": {"layer": {"s2v3-sheetprefix.xcd": xcd_sheet_prefix("Sheet")}},
    # layout probes
    "L0_stock": {},
    "L1_en_ltr_uimirroring_false": {"layer": {"s2v3-mirror.xcd": xcd_ui_mirroring(False)}},
    "L2_en_rtl_uimirroring_true": {"layer": {"s2v3-mirror.xcd": xcd_ui_mirroring(True)}},
    "L3_en_rtl_sal_env": {"env": {"SAL_RTL_ENABLED": "1"}},
    "L4_pseudo_ar_default": {"mo": {"ar": {"STR_TABLE_DEF\x04Sheet": AR_SHEET}},
                             "layer": {"Langpack-ar.xcd": xcd_langpack("ar"), "s2v3-uilocale.xcd": xcd_ui_locale("ar")}},
    "L5_pseudo_ar_uimirroring_false": {"mo": {"ar": {"STR_TABLE_DEF\x04Sheet": AR_SHEET}},
                                       "layer": {"Langpack-ar.xcd": xcd_langpack("ar"), "s2v3-uilocale.xcd": xcd_ui_locale("ar"),
                                                 "s2v3-mirror.xcd": xcd_ui_mirroring(False)}},
    "L6_pseudo_ar_sal_env_plus_false": {"mo": {"ar": {"STR_TABLE_DEF\x04Sheet": AR_SHEET}},
                                        "layer": {"Langpack-ar.xcd": xcd_langpack("ar"), "s2v3-uilocale.xcd": xcd_ui_locale("ar"),
                                                  "s2v3-mirror.xcd": xcd_ui_mirroring(False)},
                                        "env": {"SAL_RTL_ENABLED": "1"}},
}
CONTENT_CELLS = [c for c in CELLS if c.startswith("K")]
LAYOUT_CELLS = [c for c in CELLS if c.startswith("L")]
APPS = {"calc": "--calc", "impress": "--impress", "writer": "--writer"}


def prepare_lo() -> dict:
    t = time.monotonic()
    if LO.exists():
        shutil.rmtree(LO)
    shutil.copytree(LO_SRC, LO, symlinks=True)
    rc = LO / "program" / "fundamentalrc"
    text = rc.read_text()
    orig_sha = sha256_bytes(text.encode())
    lines = []
    for line in text.splitlines():
        if line.startswith("BRAND_BASE_DIR="):
            line = "BRAND_BASE_DIR=file:///tmp/lo"
        if line.startswith("CONFIGURATION_LAYERS="):
            line = line.replace("res:file:///etc/libreoffice/registry ",
                                "res:file:///etc/libreoffice/registry xcsxcu:file:///tmp/cells/current/layer ", 1)
        lines.append(line)
    rc.write_text("\n".join(lines) + "\n")
    return {"copied_seconds": round(time.monotonic() - t, 1), "fundamentalrc_sha256_before": orig_sha,
            "fundamentalrc_after": rc.read_text()}


def activate_cell(name: str) -> dict:
    spec = CELLS[name]
    res = LO / "program" / "resource"
    for d in list(res.iterdir()):
        if d.name != "common":
            shutil.rmtree(d)
    cur = CELLS_ROOT / "current"
    if cur.exists() or cur.is_symlink():
        if cur.is_symlink():
            cur.unlink()
        else:
            shutil.rmtree(cur)
    layer = cur / "layer"
    layer.mkdir(parents=True)
    files = {}
    for fname, body in spec.get("layer", {}).items():
        (layer / fname).write_text(body)
        files[f"layer/{fname}"] = sha256_bytes(body.encode())
    for lang, entries in spec.get("mo", {}).items():
        p = res / lang / "LC_MESSAGES" / "sc.mo"
        write_mo(p, entries)
        files[f"resource/{lang}/LC_MESSAGES/sc.mo"] = sha256_bytes(p.read_bytes())
    return {"cell": name, "files": files, "env": spec.get("env", {})}


def fresh_profile(root: Path) -> Path:
    if root.exists():
        shutil.rmtree(root)
    prof = root / "user"
    shutil.copytree(PROFILE_TEMPLATE, prof)
    return root


def base_env(display: str | None, home: Path) -> dict:
    env = {"HOME": str(home), "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
           "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8",
           "PYTHONPATH": "/usr/lib/python3/dist-packages:/usr/local/lib/python3.10/dist-packages"}
    if display:
        # the VM runs LibreOffice under GNOME with the gtk3 VCL plugin; headless runs must not
        # force it (debug job 1097: SAL_USE_VCLPLUGIN=gtk3 makes --headless open a display)
        env["DISPLAY"] = display
        env["SAL_USE_VCLPLUGIN"] = "gtk3"
    return env


def killpg(proc):
    with contextlib.suppress(Exception):
        os.killpg(proc.pid, signal.SIGKILL)
    with contextlib.suppress(Exception):
        proc.wait(timeout=10)


# --------------------------------------------------------------------------------------
# A2 content probes (headless UNO)

UNO_CLIENT = r'''
import json, sys, time, zipfile, uno
from com.sun.star.beans import PropertyValue
pipe, out_xlsx = sys.argv[1], sys.argv[2]
local = uno.getComponentContext()
resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
ctx = None
for _ in range(120):
    try:
        ctx = resolver.resolve(f"uno:pipe,name={pipe};urp;StarOffice.ComponentContext"); break
    except Exception:
        time.sleep(0.5)
if ctx is None:
    print(json.dumps({"error": "no connection"})); sys.exit(3)
smgr = ctx.ServiceManager
def pv(n, v):
    p = PropertyValue(); p.Name = n; p.Value = v; return p
cp = smgr.createInstanceWithContext("com.sun.star.configuration.ConfigurationProvider", ctx)
def cfg(path, key):
    try:
        acc = cp.createInstanceWithArguments("com.sun.star.configuration.ConfigurationAccess", (pv("nodepath", path),))
        return acc.getByName(key)
    except Exception as exc:
        return "ERR:" + repr(exc)[:120]
res = {"ooLocale": cfg("/org.openoffice.Setup/L10N", "ooLocale"),
       "SheetPrefix": cfg("/org.openoffice.Office.Calc/Defaults/Sheet", "SheetPrefix"),
       "UIMirroring": cfg("/org.openoffice.Office.Common/I18N/CTL", "UIMirroring")}
desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
doc = desktop.loadComponentFromURL("private:factory/scalc", "_blank", 0, (pv("Hidden", True),))
names = list(doc.Sheets.ElementNames)
res["new_doc_sheet_names"] = names
res["new_doc_sheet_names_codepoints"] = [[hex(ord(c)) for c in n] for n in names]
doc.storeToURL(uno.systemPathToFileUrl(out_xlsx), (pv("FilterName", "Calc MS Excel 2007 XML"),))
doc.close(True)
z = zipfile.ZipFile(out_xlsx)
wb = z.read("xl/workbook.xml").decode("utf-8")
import re
res["xlsx_sheet_names"] = re.findall(r'<sheet name="([^"]*)"', wb)
res["xlsx_contains_isolates"] = any(ch in wb for ch in ("⁦", "⁧", "⁨", "⁩"))
print(json.dumps(res, ensure_ascii=False))
'''


def content_probe(cell: str, out: Path) -> dict:
    rec = activate_cell(cell)
    home = fresh_profile(Path("/tmp/prof") / cell)
    env = base_env(None, home)
    env.update(rec["env"])
    pipe = f"s2v3_{CONTENT_CELLS.index(cell)}"
    soffice = subprocess.Popen(
        [str(LO / "program" / "soffice"), "--headless", "--invisible", "--norestore", "--nologo", "--nodefault",
         f"--accept=pipe,name={pipe};urp;", f"-env:UserInstallation=file://{home}"],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    client = Path("/tmp/uno_client.py")
    client.write_text(UNO_CLIENT)
    xlsx = out / f"content-{cell}.xlsx"
    r = run(["python3", str(client), pipe, str(xlsx)], env=env, timeout=150)
    killpg(soffice)
    try:
        rec["result"] = json.loads(r.get("out", "").strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        rec["result"] = None
        rec["client"] = r
    if xlsx.exists():
        rec["xlsx_sha256"] = sha256_bytes(xlsx.read_bytes())
    return rec


# --------------------------------------------------------------------------------------
# A3 layout probes (GUI)


def start_display(num: int, work: Path):
    procs = []
    xlog = (work / f"xvfb-{num}.log").open("wb")
    procs.append(subprocess.Popen(["Xvfb", f":{num}", "-screen", "0", f"{SCREEN[0]}x{SCREEN[1]}x24", "-nolisten", "tcp"],
                                  stdout=xlog, stderr=subprocess.STDOUT, start_new_session=True))
    for _ in range(100):
        if subprocess.run(["xdpyinfo"], env={"DISPLAY": f":{num}"}, capture_output=True).returncode == 0:
            break
        time.sleep(0.2)
    wm_home = work / "wm-home"
    wm_home.mkdir(parents=True, exist_ok=True)
    procs.append(subprocess.Popen(["openbox"], env={"DISPLAY": f":{num}", "HOME": str(wm_home), "PATH": "/usr/bin:/bin"},
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True))
    time.sleep(0.8)
    return procs


def start_a11y(env: dict, work: Path) -> dict:
    info = {"ok": False}
    try:
        r = subprocess.run(["dbus-daemon", "--session", "--fork", "--print-address=1", "--print-pid=1",
                            "--nopidfile"], env=env, capture_output=True, text=True, timeout=20)
        lines = r.stdout.strip().splitlines()
        if r.returncode != 0 or len(lines) < 2:
            info["dbus_error"] = r.stderr[-500:]
            return info
        env["DBUS_SESSION_BUS_ADDRESS"] = lines[0]
        info["dbus_pid"] = int(lines[1])
        subprocess.Popen(["/usr/libexec/at-spi-bus-launcher", "--launch-immediately"], env=env,
                         stdout=(work / "atspi-launcher.log").open("wb"), stderr=subprocess.STDOUT, start_new_session=True)
        time.sleep(2.0)
        subprocess.Popen(["/usr/libexec/at-spi2-registryd"], env=env,
                         stdout=(work / "atspi-registryd.log").open("wb"), stderr=subprocess.STDOUT, start_new_session=True)
        time.sleep(1.0)
        env["SAL_ACCESSIBILITY_ENABLED"] = "1"
        env["GTK_MODULES"] = "gail:atk-bridge"
        env["NO_AT_BRIDGE"] = "0"
        info["ok"] = True
    except Exception as exc:  # noqa: BLE001
        info["error"] = repr(exc)
    return info


A11Y_DUMP = r'''
import json, sys, time
import pyatspi
want = sys.argv[1]
SKIP = {pyatspi.ROLE_TABLE, pyatspi.ROLE_TREE_TABLE, pyatspi.ROLE_DOCUMENT_TEXT, pyatspi.ROLE_DOCUMENT_SPREADSHEET,
        pyatspi.ROLE_DOCUMENT_PRESENTATION, pyatspi.ROLE_DOCUMENT_FRAME, pyatspi.ROLE_PARAGRAPH}
out = []
def walk(node, path, depth):
    if len(out) > 4000 or depth > 30:
        return
    try:
        role = node.getRoleName(); name = node.name or ""
        ext = node.queryComponent().getExtents(pyatspi.DESKTOP_COORDS)
        box = [ext.x, ext.y, ext.width, ext.height]
        states = node.getState().getStates()
        showing = pyatspi.STATE_SHOWING in states
    except Exception:
        return
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
print(json.dumps({"apps": apps, "nodes": out}, ensure_ascii=False))
'''


def screenshot(display: str, path: Path) -> dict:
    code = (
        "import sys\nfrom Xlib import display as xd, X\nfrom PIL import Image\n"
        f"d = xd.Display('{display}'); r = d.screen().root; g = r.get_geometry()\n"
        "raw = r.get_image(0, 0, g.width, g.height, X.ZPixmap, 0xffffffff)\n"
        "img = Image.frombytes('RGB', (g.width, g.height), raw.data, 'raw', 'BGRX')\n"
        f"img.save('{path}')\nprint(g.width, g.height)\n"
    )
    r = run(["python3", "-c", code], env={"PATH": "/usr/bin:/bin",
                                           "PYTHONPATH": "/usr/lib/python3/dist-packages:/usr/local/lib/python3.10/dist-packages"},
            timeout=60)
    if path.exists():
        r["sha256"] = sha256_bytes(path.read_bytes())
    return r


def windows(env: dict) -> list[dict]:
    r = subprocess.run(["wmctrl", "-lG"], env=env, capture_output=True, text=True)
    wins = []
    for line in r.stdout.splitlines():
        parts = line.split(None, 7)
        if len(parts) >= 7:
            wid, desk, x, y, w, h = parts[:6]
            title = parts[7] if len(parts) == 8 else ""
            wins.append({"id": wid, "x": int(x), "y": int(y), "w": int(w), "h": int(h), "title": title,
                         "title_utf8_hex": title.encode().hex()})
    return wins


def layout_probe(cell: str, app: str, out: Path, disp_num: int) -> dict:
    rec = activate_cell(cell)
    rec["app"] = app
    work = Path("/tmp/work") / f"{cell}-{app}"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    xprocs = start_display(disp_num, work)
    display = f":{disp_num}"
    home = fresh_profile(Path("/tmp/prof") / f"{cell}-{app}")
    env = base_env(display, home)
    env.update(rec["env"])
    rec["a11y_setup"] = start_a11y(env, work)
    t = time.monotonic()
    proc = subprocess.Popen([str(LO / "program" / "soffice"), APPS[app], "--norestore", "--nologo",
                             f"-env:UserInstallation=file://{home}"],
                            env=env, stdout=(work / "soffice.log").open("wb"), stderr=subprocess.STDOUT,
                            start_new_session=True)
    title = None
    for _ in range(240):
        ws = [w for w in windows(env) if "LibreOffice" in w["title"]]
        if ws:
            title = ws[0]["title"]
            break
        time.sleep(0.25)
    rec["window_seconds"] = round(time.monotonic() - t, 1)
    if title:
        # maximize like the VM session's windows (the OSWorld image maximizes LibreOffice)
        subprocess.run(["wmctrl", "-r", title, "-b", "add,maximized_vert,maximized_horz"], env=env, capture_output=True)
    time.sleep(8.0)
    rec["windows"] = windows(env)
    png = out / f"layout-{cell}-{app}.png"
    rec["screenshot"] = screenshot(display, png)
    if rec["a11y_setup"].get("ok"):
        dump = Path("/tmp/a11y_dump.py")
        dump.write_text(A11Y_DUMP)
        r = run(["python3", str(dump), "soffice"], env=env, timeout=90)
        try:
            data = json.loads(r["out"].strip().splitlines()[-1])
            (out / f"a11y-{cell}-{app}.json").write_text(json.dumps(data, ensure_ascii=False))
            rec["a11y_nodes"] = len(data["nodes"])
            rec["a11y_apps"] = data["apps"]
        except Exception:  # noqa: BLE001
            rec["a11y_error"] = {k: r.get(k) for k in ("rc", "err", "error")}
    killpg(proc)
    for p in xprocs:
        killpg(p)
    if "dbus_pid" in rec["a11y_setup"]:
        with contextlib.suppress(Exception):
            os.kill(rec["a11y_setup"]["dbus_pid"], signal.SIGKILL)
    subprocess.run(["pkill", "-9", "-f", "at-spi"], capture_output=True)
    return rec


# --------------------------------------------------------------------------------------
# A4 analysis


def ink_profile(png: Path, y0: int, y1: int, bins: int = 120):
    from PIL import Image
    img = Image.open(png).convert("L")
    w, h = img.size
    px = img.load()
    bg = 255
    prof = [0] * bins
    step = w / bins
    for y in range(y0, min(y1, h)):
        for x in range(0, w, 2):
            if px[x, y] < 200:
                prof[min(int(x / step), bins - 1)] += 1
    return prof


def corr(a, b):
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((x - mb) ** 2 for x in b)
    if va == 0 or vb == 0:
        return None
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (va * vb) ** 0.5


def reflection_check(ltr: list[dict], rtl: list[dict], win_x: int, win_w: int, tol: int = 2) -> dict:
    def key(n):
        return (tuple(n["path"]), n["role"], n["name"].replace(FSI, "").replace(PDI, ""))
    L = {key(n): n for n in ltr if n["showing"] and n["box"][2] > 0}
    R = {key(n): n for n in rtl if n["showing"] and n["box"][2] > 0}
    common = sorted(set(L) & set(R))
    errs = []
    by_role = {}
    for k in common:
        lx, ly, lw, lh = L[k]["box"]
        rx, ry, rw, rh = R[k]["box"]
        expect = win_x + win_w - (lx - win_x) - lw
        e = rx - expect
        errs.append(abs(e))
        ok = abs(e) <= tol
        d = by_role.setdefault(k[1], [0, 0])
        d[0] += 1
        d[1] += int(ok)
    n = len(errs)
    return {"matched": n, "ltr_only": len(set(L) - set(R)), "rtl_only": len(set(R) - set(L)),
            "within_tol": sum(1 for e in errs if e <= tol), "share_within_tol": (sum(1 for e in errs if e <= tol) / n) if n else None,
            "median_abs_err_px": sorted(errs)[n // 2] if n else None, "by_role_matched_ok": by_role}


def unmoved_check(ltr: list[dict], rtl: list[dict], tol: int = 2) -> dict:
    def key(n):
        return (tuple(n["path"]), n["role"], n["name"].replace(FSI, "").replace(PDI, ""))
    L = {key(n): n for n in ltr if n["showing"] and n["box"][2] > 0}
    R = {key(n): n for n in rtl if n["showing"] and n["box"][2] > 0}
    common = sorted(set(L) & set(R))
    same = sum(1 for k in common if abs(L[k]["box"][0] - R[k]["box"][0]) <= tol and abs(L[k]["box"][1] - R[k]["box"][1]) <= tol)
    return {"matched": len(common), "same_x_within_tol": same, "share_same": (same / len(common)) if common else None}


def analyse(layout_recs: list[dict], out: Path) -> dict:
    res = {"pairs": []}
    pairs = [("L1_en_ltr_uimirroring_false", "L2_en_rtl_uimirroring_true"),
             ("L1_en_ltr_uimirroring_false", "L3_en_rtl_sal_env"),
             ("L5_pseudo_ar_uimirroring_false", "L4_pseudo_ar_default"),
             ("L5_pseudo_ar_uimirroring_false", "L6_pseudo_ar_sal_env_plus_false"),
             ("L0_stock", "L1_en_ltr_uimirroring_false")]
    by = {(r["cell"], r["app"]): r for r in layout_recs}
    for app in APPS:
        for a, b in pairs:
            ra, rb = by.get((a, app)), by.get((b, app))
            if not ra or not rb:
                continue
            item = {"app": app, "ltr_cell": a, "other_cell": b}
            pa, pb = out / f"layout-{a}-{app}.png", out / f"layout-{b}-{app}.png"
            if pa.exists() and pb.exists():
                # chrome band: below the title bar, above the document (top 180 px of a maximized window)
                la = ink_profile(pa, 30, 180)
                lb = ink_profile(pb, 30, 180)
                item["chrome_ink_corr_same"] = corr(la, lb)
                item["chrome_ink_corr_mirrored"] = corr(la, list(reversed(lb)))
                item["screens_identical"] = ra["screenshot"].get("sha256") == rb["screenshot"].get("sha256")
            ta = [w["title"] for w in ra.get("windows", []) if "LibreOffice" in w["title"]]
            tb = [w["title"] for w in rb.get("windows", []) if "LibreOffice" in w["title"]]
            item["titles"] = [ta, tb]
            item["titles_identical"] = ta == tb
            fa, fb = out / f"a11y-{a}-{app}.json", out / f"a11y-{b}-{app}.json"
            if fa.exists() and fb.exists():
                win = next((w for w in ra.get("windows", []) if "LibreOffice" in w["title"]), None)
                if win:
                    na = json.loads(fa.read_text())["nodes"]
                    nb = json.loads(fb.read_text())["nodes"]
                    item["reflection"] = reflection_check(na, nb, win["x"], win["w"])
                    item["unmoved"] = unmoved_check(na, nb)
            res["pairs"].append(item)
    return res


def main() -> int:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    record = {"seed": SEED, "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "job": os.environ.get("Q2M_SLURM_JOB_ID")}
    log("A1 facts")
    facts = {
        "soffice_version": run([str(LO_SRC / "program" / "soffice"), "--version"], env=base_env(None, Path("/tmp/home")), timeout=60),
        "vcl_plugins": sorted(p.name for p in (LO_SRC / "program").glob("libvclplug_*")),
        "resource_dirs": sorted(p.name for p in (LO_SRC / "program" / "resource").iterdir()),
        "system_layer_files": sorted(p.name for p in Path("/etc/libreoffice/registry").iterdir()),
        "fc_match_ar": run(["fc-match", "-f", "%{family}|%{file}\\n", ":lang=ar"]),
        "fc_list_ar_count": run(["sh", "-c", "fc-list :lang=ar family | sort -u | wc -l"]),
        "fc_list_ar": run(["sh", "-c", "fc-list :lang=ar family | sort -u"]),
        "locale_a": run(["locale", "-a"]),
        "gtk3_ar_catalog": Path("/usr/share/locale/ar/LC_MESSAGES/gtk30.mo").exists(),
        "lo_l10n_ar_installed": (LO_SRC / "program" / "resource" / "ar").exists(),
        "dpkg_l10n": run(["sh", "-c", "dpkg-query -W -f='${Package} ${Version}\\n' 'libreoffice-l10n-*' 'language-pack-*ar*' 2>/dev/null || true"]),
    }
    record["facts"] = facts
    record["prepare"] = prepare_lo()
    log(f"prepared private LibreOffice copy in {record['prepare']['copied_seconds']} s")
    record["content"] = []
    for cell in CONTENT_CELLS:
        log(f"A2 content {cell}")
        rec = content_probe(cell, out)
        log(f"   -> {json.dumps(rec.get('result'), ensure_ascii=False)[:300]}")
        record["content"].append(rec)
    record["layout"] = []
    num = 40
    for cell in LAYOUT_CELLS:
        for app in APPS:
            log(f"A3 layout {cell} {app}")
            try:
                rec = layout_probe(cell, app, out, num)
            except Exception as exc:  # noqa: BLE001
                rec = {"cell": cell, "app": app, "error": repr(exc)}
            num += 1
            log(f"   -> windows {[w['title'] for w in rec.get('windows', [])]} a11y_nodes {rec.get('a11y_nodes')}")
            record["layout"].append(rec)
            (out / "pilot-record.partial.json").write_text(json.dumps(record, ensure_ascii=False, indent=1))
    log("A4 analysis")
    try:
        record["analysis"] = analyse(record["layout"], out)
    except Exception as exc:  # noqa: BLE001
        record["analysis"] = {"error": repr(exc)}
    record["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    record["wall_seconds"] = round(time.monotonic() - T0, 1)
    (out / "pilot-record.json").write_text(json.dumps(record, ensure_ascii=False, indent=1))
    log("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
