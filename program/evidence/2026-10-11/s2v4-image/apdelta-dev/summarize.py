"""Summarize the S2 v4 ap_delta development jobs (dev only; decides nothing registered).

Reads each job directory (``<job>/NN-<campaign>/``, harness/q2's run layout) with harness/q2's
own ``acceptance.load``, ``counting_problems``, ``foreign_abort`` and ``snapshot_problems``, and
for the development rung ``acceptance.rung`` (at N = 2 on E and AR it cannot qualify: section 9
needs 20 boots; the point is that harness/q2's verdict code reads ``ap_delta``'s records).

    PYTHONPATH=. python program/evidence/2026-10-11/s2v4-image/apdelta-dev/summarize.py \
        <job dir> [<job dir> ...] > summary.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from harness.q2.action_path import acceptance as A


def campaign(sub: Path) -> dict:
    c = A.load(str(sub))
    trials = [t for s in c["sessions"] for t in s["trials"]]
    steps = [x for t in trials for x in t["steps_s"]]
    receipt = c["receipt"]
    out = {
        "campaign_id": c["manifest"]["campaign_id"],
        "cells": json.loads((sub / "apdelta.json").read_text())["cells"],
        "concurrency": c["manifest"]["vm"]["concurrency"],
        "sessions": len(c["sessions"]),
        "trials": len(trials),
        "trials_passed": sum(1 for t in trials if t["pass"]),
        "boot_s": [s["boot_s"] for s in c["sessions"]],
        "step_p95_s": A.quantile(steps, 0.95),
        "image_of_session": receipt.get("image_of_session"),
        "qcow2_unchanged": receipt.get("qcow2_unchanged"),
        "qcow2_sha256_before": receipt.get("qcow2_sha256_before"),
        "labelled_containers_left": receipt.get("labelled_containers_left"),
        "counting_problems": A.counting_problems(c),
        "foreign_abort": A.foreign_abort(c),
        "snapshot_problems": A.snapshot_problems(c),
        "batch_end": c["batch"],
    }
    if (sub / "apdelta.json").is_file() and len(out["cells"]) > 1:
        r = A.rung([c], float("inf"))
        out["acceptance_rung"] = {k: r[k] for k in ("n", "qualifies", "boots", "boot_p95_s",
                                                    "step_p95_s", "aborted")}
        # each problem's first 160 characters (the dev workload runs 3 of the 1,200 trials)
        out["acceptance_rung"]["problems"] = [p[:160] for p in r["problems"]]
    return out


def main(argv: list[str]) -> int:
    jobs = {}
    for job_dir in map(Path, argv):
        receipt = json.loads((job_dir / "apdelta-receipt.json").read_text())
        jobs[receipt["job_id"]] = {
            "purpose": receipt["purpose"],
            "executor_commit": receipt["executor_commit"],
            "preflight": (job_dir / "preflight.txt").read_text().splitlines(),
            "campaigns": [campaign(job_dir / c["dir"]) for c in receipt["campaigns"]],
        }
    print(json.dumps({"schema": "s2v4-apdelta-dev-summary-v1", "jobs": jobs}, indent=1,
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
