#!/usr/bin/env python3
"""Host load around the q2-action-path-v2 N = 1 acceptance campaigns (reported, not judged).

The driver takes a host snapshot before and after every session (``cycles/record-NN.json``:
``host_before`` and ``host_after``, each with the load average, the other Slurm jobs'
``squeue`` rows and the running container counts) and one at the start and end of the
campaign (``receipt.json``: ``host_start``, ``host_end``). The registrations judge them only
for a ladder rung (section 9); for an N = 1 campaign they are context. This script lists, per
job, the foreign Slurm jobs seen in any snapshot, the largest 1-minute load average and the
largest number of running containers.

    python3 -B host_snapshots.py RUNS JOB... > checks/host-snapshots-acceptance.json
"""

from __future__ import annotations

import glob
import json
import os
import sys
from typing import Any


def main() -> int:
    runs, *jobs = sys.argv[1:]
    out: dict[str, Any] = {}
    for job in jobs:
        run = os.path.join(runs, job)
        snapshots = []
        with open(os.path.join(run, "receipt.json"), encoding="utf-8") as handle:
            receipt = json.load(handle)
        snapshots += [receipt.get("host_start"), receipt.get("host_end")]
        for path in sorted(glob.glob(os.path.join(run, "cycles", "record-[0-9][0-9]*.json"))):
            with open(path, encoding="utf-8") as handle:
                record = json.load(handle)
            snapshots += [record.get("host_before"), record.get("host_after")]
        snapshots = [s for s in snapshots if s]
        foreign: dict[str, list[Any]] = {}
        for s in snapshots:
            for row in s.get("squeue_foreign") or []:
                foreign.setdefault(str(row[0]), row)
        out[job] = {
            "snapshots": len(snapshots),
            "foreign_jobs_seen": [foreign[k] for k in sorted(foreign)],
            "max_loadavg_1min": max(float((s.get("loadavg") or ["0"])[0]) for s in snapshots),
            "max_containers_running_total": max(
                s.get("containers_running_total") or 0 for s in snapshots
            ),
            "max_containers_ours": max(s.get("containers_ours") or 0 for s in snapshots),
        }
    json.dump(out, sys.stdout, indent=1, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
