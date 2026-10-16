#!/usr/bin/env python3
"""LM2: physical GPU-hours per Slurm job from the saved `scontrol show job` end records.

GPU-hours = GPUs in TresPerNode (gres:gpu:h100:N) x RunTime. CPU-only jobs (no GPU gres) count 0.
Usage: lm2-gpu-hours.py <dir with scontrol-<job>-end.txt> <out.json>
"""

import json
import re
import sys
from pathlib import Path


def seconds(runtime: str) -> int:
    days, _, hms = runtime.rpartition("-")
    h, m, s = (int(x) for x in hms.split(":"))
    return (int(days) if days else 0) * 86400 + h * 3600 + m * 60 + s


def main() -> int:
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    rows = []
    for path in sorted(src.glob("scontrol-*-end.txt")):
        fields = dict(
            item.split("=", 1) for item in path.read_text().split() if "=" in item
        )
        name = fields.get("JobName", "")
        gres = re.search(r"gpu:h100:(\d+)", fields.get("TresPerNode", ""))
        gpus = int(gres.group(1)) if gres else 0
        run_s = seconds(fields["RunTime"])
        rows.append(
            {
                "job": int(fields["JobId"]),
                "name": name,
                "state": fields.get("JobState"),
                "exit_code": fields.get("ExitCode"),
                "start": fields.get("StartTime"),
                "end": fields.get("EndTime"),
                "gpus": gpus,
                "run_s": run_s,
                "gpu_hours": round(gpus * run_s / 3600, 4),
            }
        )
    total = round(sum(r["gpu_hours"] for r in rows), 4)
    out.write_text(json.dumps({"jobs": rows, "total_gpu_hours": total}, indent=1) + "\n")
    for r in rows:
        print(r["job"], r["name"], r["state"], r["gpus"], r["run_s"], r["gpu_hours"])
    print("total", total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
