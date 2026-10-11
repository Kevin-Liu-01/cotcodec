#!/usr/bin/env python3
"""S2 v3 Phase 0, checker invariance (registration P0.8b and P0.9): does a cell change the
checker's verdict on a perfect answer?

For every candidate task whose checker compares result files with downloadable golds (the
checker-mutation study's gold controls, harness/q2_mutation/controls.py), the gold end state is
placed at the task's result paths, opened in LibreOffice and saved through the task's own
postconfig by the GUI-faithful save stage of the checker-mutation study
(harness/q2_mutation/reachability.py), once per cell (S, E, A, ER, AR, PL), in the cell's
configuration (capture.py's Worker: the cell selector in the system layer, the generated
catalogs, the placebo toolbars). The do-nothing end state (the initial files) is saved the same
way. A second job scores every saved candidate with the real OSWorld checker in the metric
container (harness/q2_mutation/offline_eval.py). A cell that changes the checker's verdict on
the gold, or on the do-nothing state, relative to en-LTR changes the outcome without any agent:
that is the agent-independent failure the admission rule excludes; a content leak the checker
does not read is a property of the treatment, reported.

Runs inside the LO-VM container (system Python 3.10, standard library), CPU only, no network.
Usage: python3 goldsave.py <pool-v3.json> <out_dir> [--workers 16] [--cells S,E,A,ER,AR,PL]
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))  # repository root inside /src

import capture as C  # noqa: E402
import catalog as CAT  # noqa: E402
from harness.q2_mutation import controls as CTL  # noqa: E402
from harness.q2_mutation import reachability as RCH  # noqa: E402

OSWORLD = Path("/inputs/OSWorld")
CACHE_ROOT = Path("/inputs/file_cache_1e112283/files")
LOCK = threading.Lock()
T0 = time.monotonic()


def log(msg):
    with LOCK:
        print(f"[{time.monotonic() - T0:8.1f}s] {msg}", flush=True)


class WDisplay:
    """The worker's Xvfb/openbox display, in the interface reachability.LoSession expects."""

    def __init__(self, w: C.Worker):
        self.w = w
        self.name = f":{w.disp}"

    def env(self, home: Path) -> dict:
        return self.w.base_env(home)


def set_cell(w: C.Worker, cell: str) -> dict:
    base = "stock" if cell == "S" else "derived"
    for b in ("stock", "derived", "qtz"):
        p = w.root / f"reg-{b}" / "zz-s2v3-cell.xcd"
        if p.exists():
            p.unlink()
    sel = C.selector(cell)
    if sel:
        (w.root / f"reg-{base}" / "zz-s2v3-cell.xcd").write_text(sel)
    w.point_registry(base)
    w.set_toolbars("pl" if cell == "PL" else "orig")
    en_us = w.lo / "program" / "resource" / "en_US"
    if en_us.exists():
        shutil.rmtree(en_us)
    return {"cell": cell, "registry_base": base, "selector_sha256": C.sha(sel.encode()) if sel else None}


def worker_main(w: C.Worker, items, out: Path, raws: dict, rows: list):
    w.setup()
    disp = WDisplay(w)
    soffice = str(w.lo / "program" / "soffice")
    for job, cell in items:
        meta = set_cell(w, cell)
        session = RCH.LoSession(disp, w.root / "sess", soffice, C.PROFILE_TEMPLATE)
        cell_out = out / "saved" / cell
        try:
            row = RCH.run_job(session, job, raws[job["task_id"]], cell_out)
        except Exception as exc:  # noqa: BLE001
            row = {"job_id": job["job_id"], "task_id": job["task_id"], "infra_error": repr(exc)[:300]}
        row["cell"] = cell
        row.update(meta)
        row["outputs_rel"] = {k: (str(Path(v).relative_to(out)) if v else None)
                              for k, v in (row.get("outputs") or {}).items()}
        with LOCK:
            rows.append(row)
            with (out / "lo-rows.jsonl").open("a") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        log(f"w{w.idx} {job['job_id'][:20]} {cell:2s} saves={[s.get('written') for s in row.get('saves', [])]} "
            f"fail={row.get('failures') or row.get('infra_error')}")
    w.stop()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pool")
    ap.add_argument("out")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--cells", default="S,E,A,ER,AR,PL")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pool = json.loads(Path(args.pool).read_text())
    task_ids = [t["task_id"] for t in pool["tasks"] if t["class"] != "excluded"]
    jobs, report = CTL.make_jobs(OSWORLD, CACHE_ROOT, task_ids, kinds=("gold", "initial"))
    jobs = [j for j in jobs if j["files"]]
    (out / "jobs.jsonl").write_text("".join(json.dumps(j) + "\n" for j in jobs))
    (out / "make-jobs-report.json").write_text(json.dumps(report, indent=1))
    raws = {t: CTL.load_task(OSWORLD, t) for t in task_ids}
    log(f"{len(jobs)} jobs ({sum(1 for j in jobs if j['kind'] == 'gold')} gold) from {len(task_ids)} tasks; "
        f"no_gold {len(report['no_gold'])}")
    cat_dir = Path("/tmp/cat")
    CAT.build(cat_dir)
    C.TOOLBAR_STATES = C.toolbar_states()
    zips = sorted(p.name for p in (C.LO_SRC / "share" / "config").glob("images*.zip"))
    symbol = "yaru" if "images_yaru.zip" in zips else None
    cells = args.cells.split(",")
    items = [(j, c) for j in jobs for c in cells]
    workers = [C.Worker(i, cat_dir, symbol) for i in range(args.workers)]
    shards = [items[i::args.workers] for i in range(args.workers)]
    rows: list = []
    (out / "lo-rows.jsonl").write_text("")
    threads = [threading.Thread(target=worker_main, args=(workers[i], shards[i], out, raws, rows))
               for i in range(args.workers)]
    for th in threads:
        th.start()
        time.sleep(0.5)
    for th in threads:
        th.join()
    # scoring jobs (paths relative to this output directory; the scorer maps them)
    score = []
    for cell in cells:
        cell_rows = [r for r in rows if r["cell"] == cell]
        for r in cell_rows:
            r["outputs"] = {k: (v if v is None else v) for k, v in (r.get("outputs_rel") or {}).items()}
        merged, excluded = CTL.merge_lo(jobs, cell_rows, suffix=cell)
        for m in merged:
            m["cell"] = cell
            score.append(m)
        (out / f"excluded-{cell}.json").write_text(json.dumps(excluded, indent=1))
    (out / "score-jobs.jsonl").write_text("".join(json.dumps(s) + "\n" for s in score))
    rec = {"schema": "s2v3-goldsave-v1", "jobs": len(jobs), "cells": cells, "renders": len(rows),
           "score_jobs": len(score), "wall_seconds": round(time.monotonic() - T0, 1),
           "job": os.environ.get("Q2M_SLURM_JOB_ID"),
           "code_sha256": {n: C.sha_file(HERE / n) for n in ("goldsave.py", "capture.py", "catalog.py")}}
    (out / "goldsave-record.json").write_text(json.dumps(rec, indent=1))
    log(f"done {json.dumps(rec)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
