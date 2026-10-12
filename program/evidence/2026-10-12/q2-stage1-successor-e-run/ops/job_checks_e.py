"""Operator check of one finished E pair: the lane's own checks, re-read from its records.

S1a's ops/job_checks.py adapted to E (q2-stage1-successor-e-v1 sections 6.3, 13, 17): run from
the read-only export of E's freeze commit (python3 -E -s -B job_checks_e.py NAME VM GPU).
Reads only infrastructure fields (no score, no step count, no outcome): the GPU job's
provenance and model verification, the bridge's engine argv against S1a's plan.engine_argv for
the job's size, the Slurm limit the lane read against the job's cap in E's plan, the USR1
point, the receipt's error and stop, status counts, losses by type and cell, completeness of
the plan's slots, guest-server restarts and observation counts, GPU devices and teardown,
the session end (lane.job_end), and the GPU and VM jobs' physical run times from their final
scontrol records. Prints JSON.
"""

from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, ".")
from harness.q2_stage1 import plan as P1  # noqa: E402
from harness.q2_stage1e import lane as LE  # noqa: E402
from harness.q2_stage1e import plan as PE  # noqa: E402

R = Path("/home/kevin/cotcodec-runs/stage0/q2-stage1e")
G = Path("/home/kevin/cotcodec-runs/stage0/q2-stage1/gpu")
PLAN = "program/evidence/2026-10-11/q2-stage1-successor-e/plan/plan-e.json"


def runtime_s(text: str) -> int | None:
    m = re.search(r"RunTime=(?:(\d+)-)?(\d+):(\d+):(\d+)", text)
    if not m:
        return None
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return ((d * 24 + h) * 60 + mi) * 60 + s


def field(text: str, name: str) -> str | None:
    m = re.search(rf"\b{name}=(\S+)", text)
    return m.group(1) if m else None


def scontrol_text(pair: Path, job: str) -> tuple[str, str | None]:
    for p in (pair / "slurm-state" / f"{job}.txt", pair / f"scontrol-{job}.last.txt"):
        if p.is_file():
            return p.read_text(), p.name
    return "", None


def main() -> None:
    name, vm, gpu = sys.argv[1:4]
    pair = R / "pairs" / name
    run = R / "runs" / vm
    gdir = G / gpu
    manifest = json.loads((run / "manifest.json").read_text())
    receipt = json.loads((run / "lane-receipt.json").read_text())
    rows = [json.loads(x) for x in (run / "episodes.jsonl").read_text().splitlines() if x.strip()]
    plan = PE.load_plan(Path(PLAN))
    size, session = manifest["e"]["size"], manifest["e"]["session"]
    job = PE.job_name(size, session)
    cap = int(plan["caps_minutes"][f"E-{size}"])
    ready = json.loads((gdir / "bridge" / "ready.json").read_text())
    stopped = json.loads((gdir / "bridge" / "stopped.json").read_text())
    prov = json.loads((gdir / "provenance-verification.txt").read_text())
    gpu_manifest = json.loads((gdir / "manifest.json").read_text())
    expected_argv = P1.engine_argv(P1.MODEL_DIRS[size], P1.SERVED_NAME)
    out: dict = {"job": job, "vm_job": vm, "gpu_job": gpu}
    out["manifest"] = {
        "purpose": manifest.get("purpose"),
        "plan_sha256": (manifest.get("plan") or {}).get("sha256"),
        "prior_jobs": [
            {"job": p["job"], "records_sha256": p["records"]["sha256"],
             "receipt_sha256": p["receipt"]["sha256"]}
            for p in (manifest["e"].get("prior_jobs") or [])
        ],  # fmt: skip
        "slots": len(manifest["slots"]),
        "slots_equal_plan": manifest["slots"] == PE.slots(plan, size, session),
        "gpu_cap_min": manifest["engine"].get("gpu_cap_min"),
        "concurrency": manifest["vm"].get("concurrency"),
        "slurm": manifest.get("slurm"),
    }
    out["provenance"] = {
        "status": prov.get("status"),
        "git_sha": prov.get("git_sha"),
        "source_sha256": prov.get("source_sha256"),
        "equals_gpu_manifest": prov.get("git_sha") == gpu_manifest.get("git_sha")
        and prov.get("source_sha256") == gpu_manifest.get("source_sha256"),
        "gpu_manifest_image_id": gpu_manifest.get("image_id"),
    }
    mv = (gdir / "model-verification.txt").read_text() if (gdir / "model-verification.txt").is_file() else ""
    out["model_verification"] = mv.strip()[:400]
    out["engine_argv"] = {
        "equals_plan_engine_argv": ready.get("engine_argv") == expected_argv,
        "engine_argv_sha256": ready.get("engine_argv_sha256"),
        "model_dir": ready.get("engine_argv", [None, None, None])[2],
    }
    gj = receipt.get("gpu_job") or {}
    out["slurm_limit"] = {
        "time_limit_min_read_by_lane": gj.get("time_limit_min"),
        "registered_cap_min": cap,
        "equal": gj.get("time_limit_min") == cap,
        "gpu_start": gj.get("start_time"),
        "usr1_epoch": receipt.get("usr1_epoch"),
        "usr1_epoch_equals_start_plus_cap_minus_180": receipt.get("usr1_epoch")
        == (gj.get("start_epoch") or 0) + cap * 60 - 180,
    }
    t_end = receipt.get("t_end")
    out["receipt"] = {
        "error": receipt.get("error"),
        "stopped": receipt.get("stopped"),
        "records": receipt.get("records"),
        "statuses": receipt.get("statuses"),
        "dispatched": len(receipt.get("dispatched") or []),
        "gpu_job_end": receipt.get("gpu_job_end"),
        "t_end": t_end,
        "engine_stop_reason": stopped.get("stop_reason"),
        "engine_returncode": stopped.get("engine_returncode"),
        "first_dispatch_after_gpu_start_s": None
        if not gj.get("start_epoch") or not receipt.get("first_dispatch")
        else round(receipt["first_dispatch"] - gj["start_epoch"], 1),
        "lane_end_minutes_before_usr1": None
        if not isinstance(t_end, int | float) or not receipt.get("usr1_epoch")
        else round((receipt["usr1_epoch"] - t_end) / 60, 1),
        "snapshots": len(receipt.get("snapshots") or []),
        "snapshot_foreign_jobs": sorted({
            str(j[0]) for s in receipt.get("snapshots") or [] for j in s.get("squeue_foreign") or []
            if str(j[0]) not in (vm, gpu)
        }),  # fmt: skip
        "snapshot_max_loadavg_1m": max(
            (float((s.get("loadavg") or ["0"])[0]) for s in receipt.get("snapshots") or []),
            default=None,
        ),
    }
    try:
        out["session_end_epoch"] = LE.job_end(receipt)
    except Exception as exc:  # noqa: BLE001
        out["session_end_epoch"] = f"unknown: {exc}"
    status = collections.Counter(r["status"] for r in rows)
    by_type = collections.Counter(
        (r["harness"], r.get("infrastructure_type")) for r in rows if r["status"] == "infrastructure"
    )
    first = [r for r in rows if r.get("attempt") == 1 and r["status"] != "cap_truncated"]
    finals: dict = {}
    for r in rows:
        key = (r["task_id"], r["harness"])
        if key not in finals or r.get("attempt", 1) >= finals[key].get("attempt", 1):
            finals[key] = r
    expected_cells = {(s["task_id"], s["harness"]) for s in PE.slots(plan, size, session)}
    final_ok = sum(
        1 for c in expected_cells
        if c in finals and (finals[c]["status"] == "scored"
                            or (finals[c]["status"] == "infrastructure" and finals[c].get("attempt") == 2))
    )  # fmt: skip
    obs = collections.Counter()
    for r in rows:
        o = r.get("observations") or {}
        for k in ("agent", "checker"):
            for f in ("calls", "retried", "slow", "undelivered"):
                obs[f"{k}.{f}"] += int((o.get(k) or {}).get(f) or 0)
    out["counts"] = {
        "records": len(rows),
        "status": dict(status),
        "attempt_2": sum(1 for r in rows if r.get("attempt") == 2),
        "infrastructure_by_harness_and_type": {f"{h}/{t}": n for (h, t), n in by_type.items()},
        "first_attempts_ran_to_an_end_by_harness": dict(
            collections.Counter(r["harness"] for r in first)
        ),
        "plan_cells": len(expected_cells),
        "plan_cells_final": final_ok,
        "cap_truncated": status.get("cap_truncated", 0),
        "gpu_devices_seen": sum(1 for r in rows if r.get("gpu_devices")),
        "guest_server_restarts": sum(int(r.get("guest_server_restarts") or 0) for r in rows),
        "context_fallbacks": sum(int(r.get("context_fallbacks") or 0) for r in rows),
        "observations": dict(obs),
        "teardown_container_not_gone": sum(
            1 for r in rows if ((r.get("host") or {}).get("teardown") or {}).get("container_gone") is False
        ),
        "teardown_leaked_volumes": sum(
            len(((r.get("host") or {}).get("teardown") or {}).get("leaked_volumes") or []) for r in rows
        ),
        "setup_failures": sum(len((r.get("setup") or {}).get("failures") or []) for r in rows),
        "postconfig_failures": sum(int(r.get("postconfig_failures") or 0) for r in rows),
        "slot_occupancy_s_sum": round(
            sum((r.get("host") or {}).get("slot_occupancy_s") or 0 for r in rows
                if r["status"] in ("scored", "infrastructure")), 1),  # fmt: skip
    }
    end_txt, src = scontrol_text(pair, gpu)
    out["gpu_scontrol_source"] = src
    rt = runtime_s(end_txt)
    out["gpu_physical"] = {
        "state": field(end_txt, "JobState"),
        "exit_code": field(end_txt, "ExitCode"),
        "start": field(end_txt, "StartTime"),
        "end": field(end_txt, "EndTime"),
        "time_limit": field(end_txt, "TimeLimit"),
        "run_time_s": rt,
        "gpu_hours": None if rt is None else round(rt / 3600, 4),
        "gpu_h_per_episode": None
        if rt is None or not len(rows) else round(rt / 3600 / len(rows), 6),
    }
    vm_txt, _ = scontrol_text(pair, vm)
    out["vm_physical"] = {
        "state": field(vm_txt, "JobState"),
        "exit_code": field(vm_txt, "ExitCode"),
        "start": field(vm_txt, "StartTime"),
        "end": field(vm_txt, "EndTime"),
        "time_limit": field(vm_txt, "TimeLimit"),
        "run_time_s": runtime_s(vm_txt),
    }
    print(json.dumps(out, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
