import json, os, sys
from datetime import datetime
run = os.path.expanduser(sys.argv[1])
p = json.load(open(os.path.join(run, "plan.json")))
f = "%Y-%m-%dT%H:%M:%SZ"
tot = 0.0
for s in p["steps"]:
    r = None
    if s.get("job"):
        path = os.path.join(s["run_dir"], f"receipt-{s['job']}.json")
        if os.path.isfile(path):
            r = json.load(open(path))
    mins = None
    if r:
        mins = (datetime.strptime(r["finished_at"], f) - datetime.strptime(r["started_at"], f)).total_seconds() / 60
        tot += mins
    print("|", s["name"], "|", s.get("job"), "|", s["state"], "|", s.get("submitted_at"), "|", r and r["started_at"], "|", r and r["finished_at"], "|", None if mins is None else round(mins, 1), "|", s.get("projected_minutes"), "|", s.get("minutes"), "|", r and r["exit_status"], "|")
print("total lane minutes", round(tot, 1), "hours", round(tot / 60, 3))
