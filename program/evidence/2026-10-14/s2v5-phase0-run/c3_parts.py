"""Operator aid (decides nothing): C3 on one image read over its three part jobs.

`ap_delta_v5.verdict` over the image's three C3 part job directories (parts 1 and 2 hold mutant
runs only; part 3 holds the remaining mutant runs and the three unmutated references, without
which no cell can kill). Only the C3 entry of that image is meaningful here; the registered K1
verdict is `ap_delta_v5.verdict` over every K1 job directory. Output as
`k1-jobs/c3-e-interim-1294-1296.json` (stint 1), plus per-outcome counts.

    PYTHONPATH=<export of 7c963f51> python c3_parts.py CELL <export dir> JOB_DIR JOB_DIR JOB_DIR
"""

import collections
import json
import sys
from pathlib import Path

from harness.s2_locale import ap_delta_v5

FREEZE = "7c963f51ad5a634c74c7ac2dff43f75a502656de"

cell, source, jobs = sys.argv[1], Path(sys.argv[2]), [Path(p) for p in sys.argv[3:]]
v = ap_delta_v5.verdict(jobs, FREEZE, source)
details = v["details"][cell]["C3"]
mutants = details.get("mutants", {})
out = {
    f"C3_{cell}": v["per_image"][cell]["C3"],
    "outcomes": dict(collections.Counter(m.get("outcome") for m in mutants.values())),
    "details": details,
    "jobs": [p.name for p in jobs],
    "note": f"interim: ap_delta_v5.verdict over jobs {', '.join(p.name for p in jobs)} (C3 on "
            f"{cell}, all three parts); only C3 on {cell} is meaningful here; the registered K1 "
            "verdict reads every K1 job",
}
print(json.dumps(out, indent=1, sort_keys=True, default=str))
