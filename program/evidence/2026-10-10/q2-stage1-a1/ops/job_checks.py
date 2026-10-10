"""Operator check of one finished S1a A1 pair: the lane's own checks, re-read from its records.

Run from the read-only export of the freeze commit (python3 -E -s -B job_checks.py NAME VM GPU).
Reads only infrastructure fields (no score, no outcome): the GPU job's provenance verification,
the bridge's engine argv against plan.engine_argv for the job's size, the Slurm limit the lane
read against the frozen T_A1, the receipt's error and stop, status counts, losses by type and
cell, base completion and the fill log, and the GPU job's physical run time from its final
scontrol record. Prints JSON.
"""

from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, ".")
from harness.q2_stage1 import plan as P  # noqa: E402
from harness.q2_stage1 import records as REC  # noqa: E402

R = Path("/home/kevin/cotcodec-runs/stage0/q2-stage1")
PLAN = "program/evidence/2026-10-09/q2-stage1-prefreeze/plan/plan-a0a.json"


def runtime_s(text: str) -> int | None:
    m = re.search(r"RunTime=(?:(\d+)-)?(\d+):(\d+):(\d+)", text)
    if not m:
        return None
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return ((d * 24 + h) * 60 + mi) * 60 + s


def field(text: str, name: str) -> str | None:
    m = re.search(rf"\b{name}=(\S+)", text)
    return m.group(1) if m else None


def main() -> None:
    name, vm, gpu = sys.argv[1:4]
    pair = R / "pairs" / name
    run = R / "runs" / vm
    gdir = R / "gpu" / gpu
    manifest = json.loads((run / "manifest.json").read_text())
    receipt = json.loads((run / "lane-receipt.json").read_text())
    rows = [json.loads(x) for x in (run / "episodes.jsonl").read_text().splitlines() if x.strip()]
    plan = json.loads(Path(PLAN).read_text())
    size, session = manifest["a1"]["size"], manifest["a1"]["session"]
    job = P.a1_job(size, session)
    cap = plan["constants"]["a1_cap_min"]
    ready = json.loads((gdir / "bridge" / "ready.json").read_text())
    stopped = json.loads((gdir / "bridge" / "stopped.json").read_text())
    prov = json.loads((gdir / "provenance-verification.txt").read_text())
    gpu_manifest = json.loads((gdir / "manifest.json").read_text())
    expected_argv = P.engine_argv(P.MODEL_DIRS[size], P.SERVED_NAME)
    out: dict = {"job": job, "vm_job": vm, "gpu_job": gpu}
    out["provenance"] = {
        "status": prov.get("status"),
        "git_sha": prov.get("git_sha"),
        "source_sha256": prov.get("source_sha256"),
        "equals_gpu_manifest": prov.get("git_sha") == gpu_manifest.get("git_sha")
        and prov.get("source_sha256") == gpu_manifest.get("source_sha256"),
    }
    out["engine_argv"] = {
        "equals_plan_engine_argv": ready.get("engine_argv") == expected_argv,
        "engine_argv_sha256": ready.get("engine_argv_sha256"),
        "model_dir": ready.get("engine_argv", [None, None, None])[2],
    }
    gj = receipt.get("gpu_job") or {}
    out["slurm_limit"] = {
        "time_limit_min_read_by_lane": gj.get("time_limit_min"),
        "frozen_T_A1": cap,
        "equal": gj.get("time_limit_min") == cap,
        "gpu_start": gj.get("start_time"),
        "usr1_epoch_equals_start_plus_cap_minus_180": receipt.get("usr1_epoch")
        == (gj.get("start_epoch") or 0) + cap * 60 - 180,
    }
    out["receipt"] = {
        "error": receipt.get("error"),
        "stopped": receipt.get("stopped"),
        "records": receipt.get("records"),
        "statuses": receipt.get("statuses"),
        "dispatched": len(receipt.get("dispatched") or []),
        "gpu_job_end": receipt.get("gpu_job_end"),
        "engine_stop_reason": stopped.get("stop_reason"),
        "engine_returncode": stopped.get("engine_returncode"),
        "first_dispatch_after_gpu_start_s": None
        if not gj.get("start_epoch") or not receipt.get("first_dispatch")
        else round(receipt["first_dispatch"] - gj["start_epoch"], 1),
    }
    fill = receipt.get("fill") or []
    finals = REC.final_records(r for r in rows if r.get("job") == job)
    out["fill"] = {
        "decisions": [
            {"block": f["block"], "allowed": f["allowed"],
             "minutes_to_usr1": round(f["minutes_to_usr1"], 2), "c_job_h": round(f["c_job_h"], 6)}
            for f in fill
        ],  # fmt: skip
        "blocks_started": sorted({r["extension_block"] for r in rows if r.get("extension_block")}),
        # records.completed_extension_blocks needs both sizes; this is its rule for one job.
        "blocks_completed_by_this_job": [
            int(b) for b, tasks in sorted(plan["extension_blocks"].items(), key=lambda x: int(x[0]))
            if all(REC._slot_final(finals.get((size, session, t, h, rr)))
                   for t in tasks for h in REC.HARNESSES for rr in REC.RERUNS)
        ],  # fmt: skip
    }
    status = collections.Counter(r["status"] for r in rows)
    by_type = collections.Counter(
        (r["harness"], r.get("infrastructure_type")) for r in rows if r["status"] == "infrastructure"
    )
    first = [r for r in rows if r.get("attempt") == 1 and r["status"] != "cap_truncated"]
    out["counts"] = {
        "records": len(rows),
        "status": dict(status),
        "attempt_2": sum(1 for r in rows if r.get("attempt") == 2),
        "infrastructure_by_harness_and_type": {f"{h}/{t}": n for (h, t), n in by_type.items()},
        "first_attempts_ran_to_an_end_by_harness": dict(
            collections.Counter(r["harness"] for r in first)
        ),
        "base_slots": sum(1 for r in rows if r["block"] in ("b1", "b2") and r.get("attempt") == 1),
        "cap_truncated_by_block": dict(
            collections.Counter(r["block"] for r in rows if r["status"] == "cap_truncated")
        ),
        "gpu_devices_seen": sum(1 for r in rows if r.get("gpu_devices")),
        "slot_occupancy_s_sum": round(
            sum((r.get("host") or {}).get("slot_occupancy_s") or 0 for r in rows
                if r["status"] in ("scored", "infrastructure")), 1),  # fmt: skip
    }
    end_txt = ""
    for p in (pair / "slurm-state" / f"{gpu}.txt", pair / f"scontrol-{gpu}.last.txt"):
        if p.is_file():
            end_txt = p.read_text()
            out["gpu_scontrol_source"] = p.name
            break
    rt = runtime_s(end_txt)
    out["gpu_physical"] = {
        "state": field(end_txt, "JobState"),
        "exit_code": field(end_txt, "ExitCode"),
        "start": field(end_txt, "StartTime"),
        "end": field(end_txt, "EndTime"),
        "run_time_s": rt,
        "gpu_hours": None if rt is None else round(rt / 3600, 4),
    }
    vm_txt = ""
    for p in (pair / "slurm-state" / f"{vm}.txt", pair / f"scontrol-{vm}.last.txt"):
        if p.is_file():
            vm_txt = p.read_text()
            break
    out["vm_physical"] = {
        "state": field(vm_txt, "JobState"),
        "exit_code": field(vm_txt, "ExitCode"),
        "start": field(vm_txt, "StartTime"),
        "end": field(vm_txt, "EndTime"),
        "run_time_s": runtime_s(vm_txt),
    }
    print(json.dumps(out, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
