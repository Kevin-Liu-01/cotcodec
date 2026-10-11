#!/usr/bin/env python3
"""S2 v3 Phase 0 pilot, part B: layout cells at every candidate task's post-open state.

Runs inside the LO-VM container (LibreOffice 1:7.3.7-0ubuntu0.22.04.4, gtk3, Xvfb + openbox),
CPU only, no network, through infra/slurm/host-single-node/s2v3-pilot-cpu.sbatch. For each of
the 106 pool tasks (pool-v3.json) and each of three cells it emulates the task's setup steps
that create the initial state (download from the pinned OSWorld file cache, open), maximizes
the window, waits, and records a screenshot, the window list and the setup log:

  L1  English interface, left-to-right (Office.Common/I18N/CTL/UIMirroring = false, finalized,
      in an extra system-level configuration layer)
  L2  English interface, mirrored (UIMirroring = true, finalized, same layer)
  L4  pseudo-Arabic interface language (ooLocale = ar finalized, a minimal Langpack-ar.xcd; no
      catalogs, so strings fall back to English), no UIMirroring key: the layout follows the
      language

Setup steps other than download, open and an soffice launch with a file are recorded as not
emulated (the Phase 0 lane run replays them in the VM). Screenshots stay on the host; the record
holds their SHA-256 and the window titles. Analysis runs on the Mac (s2v3_pilot_b_analysis.py).

Usage: python3 s2v3_pilot_b.py <pool-v3.json> <out_dir> [workers] [cells, e.g. L1,L2]
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s2v3_pilot as A  # noqa: E402  (layer writers, profile copy, screenshot, windows)

CACHE = Path("/inputs/file_cache_1e112283/files")
OSW = Path("/inputs/OSWorld/evaluation_examples/examples")
URL_PREFIX = "https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/"
CELLS_B = {
    "L1": {"layer": {"s2v3-mirror.xcd": A.xcd_ui_mirroring(False)}},
    "L2": {"layer": {"s2v3-mirror.xcd": A.xcd_ui_mirroring(True)}},
    "L4": {"layer": {"Langpack-ar.xcd": A.xcd_langpack("ar"), "s2v3-uilocale.xcd": A.xcd_ui_locale("ar")}},
}
T0 = time.monotonic()
LOCK = threading.Lock()


def log(msg):
    with LOCK:
        print(f"[{time.monotonic() - T0:8.1f}s] {msg}", flush=True)


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def make_lo_copy(worker: int) -> Path:
    lo = Path(f"/tmp/lo{worker}")
    if lo.exists():
        shutil.rmtree(lo)
    shutil.copytree(A.LO_SRC, lo, symlinks=True)
    rc = lo / "program" / "fundamentalrc"
    out = []
    for line in rc.read_text().splitlines():
        if line.startswith("BRAND_BASE_DIR="):
            line = f"BRAND_BASE_DIR=file://{lo}"
        if line.startswith("CONFIGURATION_LAYERS="):
            line = line.replace("res:file:///etc/libreoffice/registry ",
                                f"res:file:///etc/libreoffice/registry xcsxcu:file:///tmp/w{worker}/layer ", 1)
        out.append(line)
    rc.write_text("\n".join(out) + "\n")
    return lo


def set_layer(worker: int, cell: str) -> dict:
    layer = Path(f"/tmp/w{worker}/layer")
    if layer.exists():
        shutil.rmtree(layer)
    layer.mkdir(parents=True)
    files = {}
    for fname, body in CELLS_B[cell]["layer"].items():
        (layer / fname).write_text(body)
        files[fname] = sha(body.encode())
    return files


def stage_task(task: dict, vmroot: Path) -> tuple[list[str], list[dict]]:
    cfg = json.loads((OSW / task["app"] / f"{task['task_id']}.json").read_text())
    to_open, steps = [], []
    for st in cfg.get("config", []):
        typ, par = st.get("type"), st.get("parameters", {})
        if typ == "download":
            for f in par.get("files", []):
                url, path = f["url"], f["path"]
                rel = unquote(url[len(URL_PREFIX):]) if url.startswith(URL_PREFIX) else None  # job 1099/1100 did not decode %23
                src = CACHE / rel if rel else None
                dst = vmroot / path.lstrip("/")
                ok = bool(src and src.is_file())
                if ok:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(src, dst)
                steps.append({"type": "download", "path": path, "cached": ok})
        elif typ == "open":
            to_open.append(par["path"])
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
    return to_open, steps


def run_one(worker: int, lo: Path, task: dict, cell: str, out: Path, disp: int, a11y_env: dict) -> dict:
    rec = {"task_id": task["task_id"], "app": task["app"], "cell": cell}
    work = Path(f"/tmp/w{worker}/run")
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    rec["layer"] = set_layer(worker, cell)
    vmroot = work / "vm"
    to_open, steps = stage_task(task, vmroot)
    rec["setup_steps"] = steps
    home = A.fresh_profile(work / "prof")
    env = A.base_env(f":{disp}", home)
    env.update(a11y_env)
    targets = [str(vmroot / p.lstrip("/")) for p in to_open[:1]]
    rec["opened"] = to_open[:1]
    argv = [str(lo / "program" / "soffice"), "--norestore", "--nologo", f"-env:UserInstallation=file://{home}"] + targets
    if not targets:
        argv.append({"libreoffice_calc": "--calc", "libreoffice_impress": "--impress", "libreoffice_writer": "--writer"}[task["app"]])
    t = time.monotonic()
    proc = subprocess.Popen(argv, env=env, stdout=(work / "soffice.log").open("wb"), stderr=subprocess.STDOUT,
                            start_new_session=True)
    title = None
    for _ in range(360):
        ws = [w for w in A.windows(env) if "LibreOffice" in w["title"]]
        if ws:
            title = ws[0]["title"]
            break
        time.sleep(0.25)
    rec["window_seconds"] = round(time.monotonic() - t, 1)
    if title:
        subprocess.run(["wmctrl", "-r", title, "-b", "add,maximized_vert,maximized_horz"], env=env, capture_output=True)
    time.sleep(8.0)
    rec["windows"] = A.windows(env)
    png = out / "shots" / f"{task['task_id']}-{cell}.png"
    png.parent.mkdir(parents=True, exist_ok=True)
    rec["screenshot"] = {k: v for k, v in A.screenshot(f":{disp}", png).items() if k in ("rc", "sha256", "err")}
    if a11y_env and cell in ("L1", "L2"):
        dump = Path(f"/tmp/w{worker}/a11y_dump.py")
        dump.write_text(A.A11Y_DUMP)
        p = out / "a11y" / f"{task['task_id']}-{cell}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        r = A.run(["python3", str(dump), "soffice", str(p)], env=env, timeout=90)
        try:
            data = json.loads(p.read_text())
            rec["a11y_nodes"] = len(data["nodes"])
            rec["a11y_sha256"] = sha(p.read_bytes())
        except Exception:  # noqa: BLE001
            rec["a11y_error"] = {k: r.get(k) for k in ("rc", "error", "err")}
    with contextlib.suppress(Exception):
        os.killpg(proc.pid, signal.SIGKILL)
    with contextlib.suppress(Exception):
        proc.wait(timeout=10)
    return rec


def worker_main(worker: int, items: list, out: Path, results: list):
    disp = 60 + worker
    wdir = Path(f"/tmp/w{worker}")
    wdir.mkdir(parents=True, exist_ok=True)
    xprocs = A.start_display(disp, wdir)
    lo = make_lo_copy(worker)
    benv = A.base_env(f":{disp}", wdir)
    info = A.start_a11y(benv, wdir)
    a11y_env = {k: benv[k] for k in ("DBUS_SESSION_BUS_ADDRESS", "SAL_ACCESSIBILITY_ENABLED", "GTK_MODULES", "NO_AT_BRIDGE")
                if k in benv} if info.get("ok") else {}
    log(f"w{worker} a11y {info}")
    for task, cell in items:
        try:
            rec = run_one(worker, lo, task, cell, out, disp, a11y_env)
        except Exception as exc:  # noqa: BLE001
            rec = {"task_id": task["task_id"], "cell": cell, "error": repr(exc)}
        with LOCK:
            results.append(rec)
        titles = [w["title"] for w in rec.get("windows", [])]
        log(f"w{worker} {task['task_id'][:8]} {cell} {rec.get('window_seconds')}s {titles}")
    for p in xprocs:
        A.killpg(p)


def main() -> int:
    pool = json.loads(Path(sys.argv[1]).read_text())
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    tasks = [t for t in pool["tasks"] if t["class"] != "excluded"]
    cells = sys.argv[4].split(",") if len(sys.argv) > 4 else list(CELLS_B)
    items = [(t, c) for t in tasks for c in cells]
    shards = [items[i::workers] for i in range(workers)]
    results: list = []
    threads = [threading.Thread(target=worker_main, args=(i, shards[i], out, results)) for i in range(workers)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    results.sort(key=lambda r: (r["task_id"], r["cell"]))
    rec = {"schema": "s2v3-pilot-b-v1", "pool_sha256": sha(Path(sys.argv[1]).read_bytes()), "cells": cells,
           "tasks": len(tasks), "workers": workers, "results": results, "wall_seconds": round(time.monotonic() - T0, 1),
           "job": os.environ.get("Q2M_SLURM_JOB_ID")}
    (out / "pilot-b-record.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1))
    log("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
