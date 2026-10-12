"""Operator check of one S2 v4 K1 (`ap_delta`) job directory (interim; decides nothing).

The registered K1 verdict is `python -m harness.s2_locale.ap_delta verdict JOB... --freeze-commit
cf174050...` over every K1 job. This script reads one job as it finishes, with harness/q2's own
`acceptance` code (load, counting problems, foreign abort, snapshot problems) and with
`ap_delta.verdict` on that one job, of which only the entry for the job's own check and image is
meaningful (the other entries have no campaigns yet). It also states whether each campaign
"counts" under q2-action-path-v2 section 6.1 (driver exit 0, no labelled container left, the
receipt's `infra_gates_pass` true and the image unchanged; the Slurm state is read separately).

    PYTHONPATH=<export of cf174050> python check_job.py <job dir> > check-<job>.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from harness.q2.action_path import acceptance as A
from harness.s2_locale import ap_delta

FREEZE = "cf17405026ca2aa20f528b39bdaaff3b257a6610"


def campaign(sub: Path) -> dict:
    c = A.load(str(sub))
    trials = [t for s in c["sessions"] for t in s["trials"]]
    steps = [x for t in trials for x in t["steps_s"]]
    receipt = c["receipt"] or {}
    batch = c.get("batch") or {}
    return {
        "dir": sub.name,
        "campaign_id": c["manifest"]["campaign_id"],
        "key": ap_delta.campaign_key(c["manifest"]),
        "cells": json.loads((sub / "apdelta.json").read_text())["cells"],
        "sessions": len(c["sessions"]),
        "trials": len(trials),
        "trials_passed": sum(1 for t in trials if t["pass"]),
        "boot_s_max": max((s["boot_s"] for s in c["sessions"] if s.get("boot_s") is not None),
                          default=None),
        "step_p95_s": A.quantile(steps, 0.95),
        "infra_gates_pass": receipt.get("infra_gates_pass",
                                        (receipt.get("summary") or {}).get("infra_gates_pass")),
        "qcow2_unchanged": receipt.get("qcow2_unchanged"),
        "labelled_containers_left": receipt.get("labelled_containers_left"),
        "batch_end": batch,
        "counting_problems": A.counting_problems(c),
        "foreign_abort": A.foreign_abort(c),
        "snapshot_problems": A.snapshot_problems(c),
    }


def main(argv: list[str]) -> int:
    job_dir = Path(argv[0])
    receipt = json.loads((job_dir / "apdelta-receipt.json").read_text())
    subs = [job_dir / c["dir"] for c in receipt["campaigns"] if c.get("dir")]
    camps = [campaign(s) for s in subs]
    v = ap_delta.verdict([job_dir], FREEZE)
    check, cells = receipt["check"], "+".join(camps[0]["cells"]) if camps else ""
    if check == "rung":
        own = {"rung": v["rung"]}
    else:
        own = {check: v["per_image"][cells].get(check)}
        if check == "A1":
            own["C4"] = v["per_image"][cells].get("C4")
    out = {
        "schema": "s2v4-k1-job-check-v1",
        "note": "interim, one job; the registered K1 verdict is ap_delta.verdict over every K1 job",
        "job_id": receipt["job_id"],
        "check": check,
        "cells": cells,
        "executor_commit": receipt.get("executor_commit"),
        "job_preflight": (job_dir / "preflight.txt").read_text().splitlines(),
        "receipt_campaigns": receipt["campaigns"],
        "t_start": receipt.get("t_start"),
        "t_end": receipt.get("t_end"),
        "campaigns": camps,
        "own_check_on_this_job": own,
    }
    print(json.dumps(out, indent=1, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
