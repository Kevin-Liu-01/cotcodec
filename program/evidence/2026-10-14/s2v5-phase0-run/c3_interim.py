"""Interim C3 summary of one job (operator aid; decides nothing): per campaign, the cells its
mutant run failed (candidate kills, judged against the references in part 3)."""
import json, sys
from pathlib import Path
from harness.q2.action_path import acceptance as A
job = Path(sys.argv[1])
rec = json.loads((job / "apdelta-receipt.json").read_text())
rows = []
for c in rec["campaigns"]:
    sub = job / c["dir"]
    camp = A.load(str(sub))
    m = camp["manifest"]
    mut = m["workload"].get("mutant") or "none"
    failed = sorted({t["cell"] for s in camp["sessions"] for t in s["trials"] if not t["pass"]})
    infra = sorted({t["cell"] for s in camp["sessions"] for t in s["trials"] if t.get("infra")})
    n = sum(len(s["trials"]) for s in camp["sessions"])
    rows.append({"dir": c["dir"], "layer": m["workload"].get("layer"), "mutant": mut,
                 "trials": n, "failed_cells": failed, "infra_cells": infra,
                 "counting_problems": A.counting_problems(camp)})
print(json.dumps(rows, indent=1))
no_fail = [r["dir"] for r in rows if r["mutant"] != "none" and not r["failed_cells"]]
print("campaigns", len(rows), "counting problems", sum(bool(r["counting_problems"]) for r in rows),
      "mutants without a failed cell", no_fail, file=sys.stderr)
