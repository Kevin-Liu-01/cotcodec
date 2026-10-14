"""Per-job and per-campaign facts of the confirmation's records (descriptive; decides nothing).

    python3 -I facts.py JOB_DIR [JOB_DIR ...]
"""
import datetime as dt
import json
import re
import sys
from pathlib import Path


def iso(t):
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if isinstance(t, (int, float)) else t


out = []
for job in map(Path, sys.argv[1:]):
    r = json.loads((job / "apdelta-receipt.json").read_text())
    pre = (job / "preflight.txt").read_text()
    st = (job / "slurm-state" / f"{job.name}.txt")
    slurm = {}
    if st.is_file():
        txt = st.read_text()
        for k in ("JobState", "ExitCode", "SubmitTime", "StartTime", "EndTime", "RunTime", "TRES"):
            m = re.search(rf"\b{k}=(\S+)", txt)
            slurm[k] = m.group(1) if m else None
    j = {"job": job.name, "t_start": iso(r.get("t_start")), "t_end": iso(r.get("t_end")),
         "executor_commit": r.get("executor_commit"), "batch_end": re.findall(r"^lane_exit=.*$", pre, re.M),
         "slurm": slurm, "campaigns": []}
    for c in r["campaigns"]:
        sub = job / c["dir"]
        rc = json.loads((sub / "receipt.json").read_text())
        s = rc["summary"]
        sess = s["sessions"]
        j["campaigns"].append({
            "dir": c["dir"], "cells": c["cells"], "cells_file": c.get("cells_file"),
            "driver_exit": c.get("driver_exit"),
            "batch_end": re.findall(r"^driver_exit=.*$", (sub / "preflight.txt").read_text(), re.M),
            "started_at": iso(rc.get("started_at")), "finished_at": iso(rc.get("finished_at")),
            "infra_gates_pass": s.get("infra_gates_pass"), "qcow2_unchanged": rc.get("qcow2_unchanged"),
            "qcow2_sha256": [rc.get("qcow2_sha256_before"), rc.get("qcow2_sha256_after")],
            "labelled_containers_left": rc.get("labelled_containers_left"),
            "leaked_volumes": s.get("leaked_volumes"), "no_gpu_all": s.get("no_gpu_all"),
            "no_published_ports_all": s.get("no_published_ports_all"),
            "containers_removed_all": s.get("containers_removed_all"),
            "boots_ok": s.get("boots_ok"), "cycles": s.get("cycles"), "boot_s": s.get("boot_s"),
            "cell_counts": sess.get("cell_counts"), "guest_server_restarts": sess.get("guest_server_restarts"),
            "infra_failures": sess.get("infra_failures"), "runner_errors": sess.get("runner_errors"),
            "session_wall_s": [x.get("wall_s") for x in sess.get("sessions") or []],
            "trial_s": sess.get("trial_s"), "errors": s.get("errors"),
            "dangling_volumes": [rc.get("dangling_volumes_before"), rc.get("dangling_volumes_after")],
            "git_sha": rc.get("git_sha"), "source_tree_sha256": rc.get("source_tree_sha256"),
            "manifest_sha256": rc.get("manifest_sha256"), "session_plan_sha256": rc.get("session_plan_sha256"),
        })
    out.append(j)
print(json.dumps(out, indent=1, sort_keys=True))
