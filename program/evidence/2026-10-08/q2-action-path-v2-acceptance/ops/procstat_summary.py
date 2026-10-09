#!/usr/bin/env python3
"""Host CPU utilization and steal while each ladder rung ran (section 12; reported only).

The frozen lane records neither CPU steal nor utilization, which section 12's concurrency
table lists. During each rung the operator sampled the host's aggregate ``/proc/stat`` cpu
line every 30 s over ssh, read-only (``checks/procstat/procstat-<job>.log``: epoch, the
``cpu`` line, the job's ``squeue`` state). This reads, over the samples taken while the job
was RUNNING, the host-wide busy fraction (everything but idle and iowait) and the steal
fraction of all CPU time, and the same as CPU equivalents of the host's CPUs. It covers the
whole host (every process, not only the rung's VMs), so it is context, never a criterion.

    python3 procstat_summary.py HOST_CPUS LOG... > checks/procstat-summary.json
"""

from __future__ import annotations

import json
import os
import sys


def main() -> int:
    host_cpus = int(sys.argv[1])
    out = {}
    for path in sys.argv[2:]:
        rows = []
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                parts = line.split()
                if len(parts) < 12 or parts[1] != "cpu":
                    continue
                rows.append((int(parts[0]), [int(x) for x in parts[2:12]], parts[12:]))
        running = [r for r in rows if r[2] == ["RUNNING"]]
        job = os.path.basename(path).removeprefix("procstat-").removesuffix(".log")
        if len(running) < 2:
            out[job] = {"samples_running": len(running)}
            continue
        first, last = running[0][1], running[-1][1]
        delta = [b - a for a, b in zip(first, last, strict=True)]
        total = sum(delta[:8])  # user nice system idle iowait irq softirq steal
        idle = delta[3] + delta[4]
        out[job] = {
            "samples_running": len(running),
            "window_s": running[-1][0] - running[0][0],
            "busy_fraction": round((total - idle) / total, 4),
            "busy_cpu_equivalents": round((total - idle) / total * host_cpus, 1),
            "steal_fraction": round(delta[7] / total, 6),
            "steal_cpu_equivalents": round(delta[7] / total * host_cpus, 3),
            "iowait_fraction": round(delta[4] / total, 6),
        }
    json.dump(out, sys.stdout, indent=1, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
