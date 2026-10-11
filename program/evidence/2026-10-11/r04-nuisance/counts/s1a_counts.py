"""Pre-freeze count of R04's S1a items from S1a's committed records (no capture is read).

Run from the repository root: python3 program/evidence/2026-10-11/r04-nuisance/counts/s1a_counts.py
It applies the registered rules of harness/r04_nuisance/items.py (office-exposed scored
episodes, one item per state digest, populations, the seeded fail sample) to a1.jsonl, whose
``state_sha256`` and ``checker_input_sha256`` are the capture manifests' digests and paths,
and writes s1a-counts.json beside itself. The item builder recomputes all of this from the
captures on the host after the freeze.
"""

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, ".")
from harness.r04_nuisance import items as I  # noqa: E402

RECORDS = Path("program/evidence/2026-10-10/q2-stage1-analysis/a1.jsonl")
rows = [json.loads(x) for x in RECORDS.read_text().splitlines() if x.strip()]
states = {}
for r in sorted(rows, key=lambda r: (r["job"], str(r["slot"]), r["attempt"])):
    if r["status"] != "scored" or not any(I.is_office(p) for p in r["checker_input_sha256"]):
        continue
    s = states.setdefault(r["state_sha256"], {"task_id": r["task_id"], "scores": [], "n": 0})
    s["scores"].append(r["score"])
    s["n"] += 1
table = [
    {"task_id": v["task_id"], "state_sha256": k, "population": I.population_of(v["scores"])}
    for k, v in sorted(states.items())
]
fails = [t for t in table if t["population"] == "s1a_fail"]
sample = I.sample_fail_states(fails)
out = {
    "records": str(RECORDS),
    "office_exposed_episodes": sum(v["n"] for v in states.values()),
    "office_exposed_tasks": len({t["task_id"] for t in table}),
    "states": len(table),
    "states_by_population": dict(Counter(t["population"] for t in table)),
    "tasks_by_population": {
        p: len({t["task_id"] for t in table if t["population"] == p})
        for p in ("s1a_pass", "s1a_fail", "s1a_mixed")
    },
    "fail_sample": len(sample),
    "items": sum(t["population"] != "s1a_fail" for t in table) + len(sample),
    "fail_sample_state_sha256": sample,
}
Path(__file__).with_name("s1a-counts.json").write_text(json.dumps(out, indent=1) + "\n")
print(json.dumps({k: v for k, v in out.items() if k != "fail_sample_state_sha256"}))
