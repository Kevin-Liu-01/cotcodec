"""Operator check of one S2 v5 K1 (`ap_delta_v5`) job directory (interim; decides nothing).

The registered K1 verdict is `python -m harness.s2_locale.ap_delta_v5 verdict JOB...
--freeze-commit 7c963f51... --source-dir EXPORT` over every K1 job directory. This script reads one
job as it finishes, with harness/q2's own `acceptance` code (load, counting problems, foreign
abort, snapshot problems) and with `ap_delta_v5.verdict` on that one job, of which only the entry
for the job's own check and image (and, for A6, the cells-file check) is meaningful (the other
entries have no campaigns yet). It also states whether each campaign "counts" under
q2-action-path-v2 section 6.1 (driver exit 0, no labelled container left, the receipt's
`infra_gates_pass` true and the image unchanged; the Slurm state is read separately, from the
operator's last `scontrol show job` record). A copy of v4's operator check
(`program/evidence/2026-10-12/s2v4-phase0-run/check_job.py`) with v5's verdict and freeze commit.

    PYTHONPATH=<export of 7c963f51> python check_job.py <job dir> <export dir> > check-<job>.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from harness.q2.action_path import acceptance as A
from harness.s2_locale import ap_delta, ap_delta_v5

FREEZE = "7c963f51ad5a634c74c7ac2dff43f75a502656de"


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
        "cells_file": json.loads((sub / "apdelta.json").read_text()).get("cells_file"),
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
    job_dir, source_dir = Path(argv[0]), Path(argv[1])
    receipt = json.loads((job_dir / "apdelta-receipt.json").read_text())
    subs = [job_dir / c["dir"] for c in receipt["campaigns"] if c.get("dir")]
    camps = [campaign(s) for s in subs]
    v = ap_delta_v5.verdict([job_dir], FREEZE, source_dir)
    check, cells = receipt["check"], "+".join(camps[0]["cells"]) if camps else ""
    if check == "rung":
        own = {"rung": v["rung"]}
    else:
        own = {check: v["per_image"][cells].get(check)}
        if check == "A1":
            own["C4"] = v["per_image"][cells].get("C4")
        if check == "A6":
            own["a6_cells"] = v["a6_cells"]
    out = {
        "schema": "s2v5-k1-job-check-v1",
        "note": "interim, one job; the registered K1 verdict is ap_delta_v5.verdict over every "
                "K1 job",
        "job_id": receipt["job_id"],
        "check": check,
        "part": receipt.get("part"),
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
