#!/usr/bin/env python3
"""Debug step for the S2 v3 pilot (job 1096 could not connect to a headless soffice).

Checks, with stderr captured: the private copy of LibreOffice, a headless conversion with the
system and the private build, and a UNO pipe connection with each. CPU only, no network.
Usage: python3 s2v3_debug.py <out_dir>
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
rec = {}


def run(argv, env=None, timeout=90):
    t = time.monotonic()
    try:
        r = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=timeout)
        return {"argv": argv, "rc": r.returncode, "out": r.stdout[-3000:], "err": r.stderr[-3000:], "s": round(time.monotonic() - t, 1)}
    except Exception as e:  # noqa: BLE001
        return {"argv": argv, "error": repr(e), "s": round(time.monotonic() - t, 1)}


def env_for(home):
    Path(home).mkdir(parents=True, exist_ok=True)
    return {"HOME": home, "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "en_US.UTF-8",
            "LC_ALL": "en_US.UTF-8", "PYTHONPATH": "/usr/lib/python3/dist-packages", "SAL_USE_VCLPLUGIN": "gtk3"}


rec["du_src"] = run(["du", "-s", "--apparent-size", "/usr/lib/libreoffice"])
rec["count_src"] = run(["sh", "-c", "find /usr/lib/libreoffice | wc -l; find /usr/lib/libreoffice -type l | wc -l"])
rec["soffice_script_head"] = run(["head", "-60", "/usr/lib/libreoffice/program/soffice"])
if Path("/tmp/lo").exists():
    shutil.rmtree("/tmp/lo")
t = time.monotonic()
shutil.copytree("/usr/lib/libreoffice", "/tmp/lo", symlinks=True)
rec["copy_s"] = round(time.monotonic() - t, 1)
rec["du_copy"] = run(["du", "-s", "--apparent-size", "/tmp/lo"])
csv = Path("/tmp/t.csv"); csv.write_text("a,b\n1,2\n")
rec["sys_convert"] = run(["/usr/lib/libreoffice/program/soffice", "--headless", "--norestore", "-env:UserInstallation=file:///tmp/p_sys",
                          "--convert-to", "xlsx", "--outdir", "/tmp/o_sys", str(csv)], env=env_for("/tmp/h_sys"), timeout=120)
rec["copy_convert_unmodified"] = run(["/tmp/lo/program/soffice", "--headless", "--norestore", "-env:UserInstallation=file:///tmp/p_cp",
                                      "--convert-to", "xlsx", "--outdir", "/tmp/o_cp", str(csv)], env=env_for("/tmp/h_cp"), timeout=120)
rc = Path("/tmp/lo/program/fundamentalrc")
txt = rc.read_text()
rc.write_text(txt.replace("BRAND_BASE_DIR=file:///usr/lib/libreoffice", "BRAND_BASE_DIR=file:///tmp/lo"))
rec["copy_convert_brand"] = run(["/tmp/lo/program/soffice", "--headless", "--norestore", "-env:UserInstallation=file:///tmp/p_cp2",
                                 "--convert-to", "xlsx", "--outdir", "/tmp/o_cp2", str(csv)], env=env_for("/tmp/h_cp2"), timeout=120)
Path("/tmp/layer").mkdir(exist_ok=True)
rc.write_text(rc.read_text().replace("res:file:///etc/libreoffice/registry ", "res:file:///etc/libreoffice/registry xcsxcu:file:///tmp/layer ", 1))
rec["copy_convert_brand_layer"] = run(["/tmp/lo/program/soffice", "--headless", "--norestore", "-env:UserInstallation=file:///tmp/p_cp3",
                                       "--convert-to", "xlsx", "--outdir", "/tmp/o_cp3", str(csv)], env=env_for("/tmp/h_cp3"), timeout=120)
rec["outputs"] = {d: sorted(os.listdir(d)) if os.path.isdir(d) else None for d in ("/tmp/o_sys", "/tmp/o_cp", "/tmp/o_cp2", "/tmp/o_cp3")}

CLIENT = r'''
import json, sys, time, uno
pipe = sys.argv[1]
local = uno.getComponentContext()
resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
last = None
for _ in range(60):
    try:
        ctx = resolver.resolve(f"uno:pipe,name={pipe};urp;StarOffice.ComponentContext")
        print(json.dumps({"ok": True})); sys.exit(0)
    except Exception as e:
        last = repr(e); time.sleep(0.5)
print(json.dumps({"ok": False, "last": last[:500]}))
'''
Path("/tmp/c.py").write_text(CLIENT)
for label, exe, extra in (("sys", "/usr/lib/libreoffice/program/soffice", []),
                          ("copy", "/tmp/lo/program/soffice", [])):
    home = f"/tmp/h_uno_{label}"
    env = env_for(home)
    log = open(out / f"uno-{label}.log", "wb")
    p = subprocess.Popen([exe, "--headless", "--invisible", "--norestore", "--nologo", "--nodefault",
                          f"--accept=pipe,name=dbg_{label};urp;", f"-env:UserInstallation=file:///tmp/p_uno_{label}"] + extra,
                         env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    time.sleep(2)
    rec[f"uno_{label}"] = run(["python3", "/tmp/c.py", f"dbg_{label}"], env=env, timeout=60)
    rec[f"uno_{label}_alive"] = p.poll() is None
    rec[f"uno_{label}_ps"] = run(["sh", "-c", "ps -eo pid,args | grep -i soffice | grep -v grep | head"])
    rec[f"uno_{label}_pipes"] = run(["sh", "-c", "ls -la /tmp | grep -i osl || true"])
    try:
        os.killpg(p.pid, 9)
    except Exception:  # noqa: BLE001
        pass
    log.close()
    rec[f"uno_{label}_log"] = (out / f"uno-{label}.log").read_text(errors="replace")[-2000:]
(out / "debug-record.json").write_text(json.dumps(rec, indent=1))
print(json.dumps({k: (v if not isinstance(v, dict) else {kk: v.get(kk) for kk in ("rc", "s", "err", "out", "error")}) for k, v in rec.items()}, indent=1)[:12000])
