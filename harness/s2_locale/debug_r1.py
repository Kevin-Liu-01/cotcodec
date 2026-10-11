#!/usr/bin/env python3
"""S2 v3 Phase 0 repair pilot, debug job: why the generated registry labels and icons did not apply,
and what dialog the Ctrl+S postconfig meets under a non-English interface. CPU only, container only."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import capture as C  # noqa: E402
import catalog as CAT  # noqa: E402

UNO = r'''
import json, sys, time, uno
from com.sun.star.beans import PropertyValue
pipe = sys.argv[1]
local = uno.getComponentContext()
resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
ctx = None
for _ in range(120):
    try:
        ctx = resolver.resolve(f"uno:pipe,name={pipe};urp;StarOffice.ComponentContext"); break
    except Exception:
        time.sleep(0.5)
smgr = ctx.ServiceManager
def pv(n, v):
    p = PropertyValue(); p.Name = n; p.Value = v; return p
cp = smgr.createInstanceWithContext("com.sun.star.configuration.ConfigurationProvider", ctx)
def cfg(path, key):
    try:
        acc = cp.createInstanceWithArguments("com.sun.star.configuration.ConfigurationAccess", (pv("nodepath", path),))
        return acc.getByName(key)
    except Exception as exc:
        return "ERR:" + repr(exc)[:160]
res = {"ooLocale": cfg("/org.openoffice.Setup/L10N", "ooLocale"),
       "SymbolStyle": cfg("/org.openoffice.Office.Common/Misc", "SymbolStyle"),
       "PickList_label_cfg": cfg("/org.openoffice.Office.UI.GenericCommands/UserInterface/Commands/.uno:PickList", "Label"),
       "Save_label_cfg": cfg("/org.openoffice.Office.UI.GenericCommands/UserInterface/Commands/.uno:Save", "Label")}
try:
    ucd = ctx.getValueByName("/singletons/com.sun.star.frame.theUICommandDescription")
    mod = ucd.getByName("com.sun.star.sheet.SpreadsheetDocument")
    props = {p.Name: p.Value for p in mod.getByName(".uno:PickList")}
    res["PickList_label_ucd"] = props.get("Label")
    props = {p.Name: p.Value for p in mod.getByName(".uno:Save")}
    res["Save_label_ucd"] = props.get("Label")
except Exception as exc:
    res["ucd_error"] = repr(exc)[:200]
print(json.dumps(res, ensure_ascii=False))
'''


def headless_probe(w: C.Worker, base: str, extra: dict[str, str], tag: str) -> dict:
    reg = w.root / f"reg-{base}"
    added = []
    for name, body in extra.items():
        p = reg / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
        added.append(p)
    w.point_registry(base)
    home = w.root / f"home-{tag}"
    if home.exists():
        shutil.rmtree(home)
    shutil.copytree(C.PROFILE_TEMPLATE, home / "user")
    env = {"HOME": str(home), "PATH": "/usr/bin:/bin", "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8",
           "PYTHONPATH": "/usr/lib/python3/dist-packages:/usr/local/lib/python3.10/dist-packages"}
    pipe = f"dbg_{tag}"
    p = subprocess.Popen([str(w.lo / "program" / "soffice"), "--headless", "--invisible", "--norestore", "--nologo",
                          "--nodefault", f"--accept=pipe,name={pipe};urp;", f"-env:UserInstallation=file://{home}"],
                         env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    client = w.root / "uno_dbg.py"
    client.write_text(UNO)
    r = C.run(["python3", str(client), pipe], env=env, timeout=150)
    with __import__("contextlib").suppress(Exception):
        os.killpg(p.pid, 9)
    for f in added:
        f.unlink()
    try:
        return json.loads(r["out"].strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        return {"raw": r}


def main() -> int:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    rec: dict = {}
    lo = Path("/usr/lib/libreoffice")
    links = {}
    for p in [lo / "share", lo / "share" / "config", lo / "share" / "config" / "images_yaru.zip", lo / "program" / "resource",
              lo / "share" / "registry", lo / "share" / "config" / "soffice.cfg"]:
        links[str(p)] = {"is_symlink": p.is_symlink(), "target": os.readlink(p) if p.is_symlink() else None, "exists": p.exists()}
    rec["links"] = links
    cat_dir = Path("/tmp/cat")
    rec["catalog"] = {k: v for k, v in CAT.build(cat_dir).items() if k != "ui_domains"}
    pairs = (cat_dir / "code-pairs.tsv").read_text().splitlines()
    rec["english_usa_pairs"] = [l for l in pairs if "English (USA)" in l][:20]
    rec["lang_table_ctx"] = sorted({l.split("\t")[0] for l in pairs if "LANGUAGE" in l.split("\t")[0]})[:40]
    rec["n_pairs"] = len(pairs)
    shutil.copyfile(cat_dir / "code-pairs.tsv", out / "code-pairs.tsv")
    C.TOOLBAR_STATES = C.toolbar_states()
    w = C.Worker(0, cat_dir, "yaru")
    rec["worker"] = w.setup()
    copied = w.lo / "share" / "config" / "images_yaru.zip"
    rec["copied_yaru"] = {"is_symlink": copied.is_symlink(), "target": os.readlink(copied) if copied.is_symlink() else None,
                          "exists": copied.exists()}
    sel_ar = C.selector("A")
    sel_en = C.selector("E")
    reg_ar = (cat_dir / "registry_ar.xcd").read_text()
    variants = {
        "en_derived": ("derived", {"zz-s2v3-cell.xcd": sel_en}),
        "ar_derived_res_fuse": ("derived", {"zz-s2v3-cell.xcd": sel_ar}),
        "ar_xcsxcu_labels": ("derived", {"zz-s2v3-cell.xcd": sel_ar, "zz-ar-labels.xcd": reg_ar}),
        "ar_res_replace": ("derived", {"zz-s2v3-cell.xcd": sel_ar,
                                       "res/registry_ar.xcd": reg_ar.replace('oor:op="fuse"', 'oor:op="replace"')}),
    }
    rec["variants"] = {}
    for tag, (base, extra) in variants.items():
        rec["variants"][tag] = headless_probe(w, base, extra, tag)
        print(tag, json.dumps(rec["variants"][tag], ensure_ascii=False), flush=True)
    (out / "debug-record.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1))
    # GUI: Calc task in the A cell; screenshot after Ctrl+S
    pool = json.loads(Path("/src/pool-v3.json").read_text())
    task = next(t for t in pool["tasks"] if t["task_id"].startswith("12382c62"))
    for cell in ("A", "E"):
        r = C.render(w, task, cell, out, cat_dir / "code-pairs.tsv", False)
        rec[f"render_{cell}"] = r
    # a direct look at the dialog: reopen in A, press ctrl+s, screenshot and a11y
    reg = w.root / "reg-derived"
    (reg / "zz-s2v3-cell.xcd").write_text(sel_ar)
    w.point_registry("derived")
    work = w.root / "run2"
    if work.exists():
        shutil.rmtree(work)
    vm = work / "vm"
    to_open, _, _ = C.stage_task(task, vm)
    home = work / "home"
    shutil.copytree(C.PROFILE_TEMPLATE, home / "user")
    env = w.base_env(home)
    env.update(w.a11y_env)
    p = subprocess.Popen([str(w.lo / "program" / "soffice"), "--norestore", "--nologo", f"-env:UserInstallation=file://{home}",
                          str(vm / to_open[0].lstrip("/"))], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    time.sleep(14)
    C.run(["wmctrl", "-Fa", task["activate_window_titles"][0]], env=env)
    C.key(env, "ctrl+s")
    time.sleep(4)
    C.frame_hash(env, out / "after-ctrl-s-A.png")
    rec["after_windows"] = C.windows(env)
    dump = w.root / "a11y_dump.py"
    dump.write_text(C.A11Y_DUMP)
    C.run(["python3", str(dump), str(out / "after-ctrl-s-A.a11y.json")], env=env, timeout=120)
    with __import__("contextlib").suppress(Exception):
        os.killpg(p.pid, 9)
    (out / "debug-record.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1))
    w.stop()
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
