"""Operator aid (decides nothing): per-entry pass counts of K1 campaign directories.

Reads each campaign with harness/q2's own `acceptance.load` and prints, per campaign, the number of
catalog entries, the entries per application, every entry that did not pass in all its trials (with
passed/run), guest-server restarts, accessibility calls, and the trials with a state-not-observed,
infrastructure or retried mark. The registered reading is `ap_delta_v5.verdict`; this only
describes a campaign for the README.

    PYTHONPATH=<export of 7c963f51> python campaign_summary.py <campaign dir>...
"""

import collections
import json
import sys

from harness.q2.action_path import acceptance as A


def count(x) -> int:
    return len(x) if isinstance(x, list) else int(x or 0)


for d in sys.argv[1:]:
    c = A.load(d)
    per: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0])
    tally = collections.Counter()
    for s in c["sessions"]:
        tally["restarts"] += count(s.get("restarts"))
        tally["accessibility_calls"] += count(s.get("accessibility_calls"))
        for t in s["trials"]:
            per[t["cell"]][1] += 1
            per[t["cell"]][0] += bool(t["pass"])
            tally["state_not_observed_trials"] += bool(t["state_not_observed"])
            tally["infra_trials"] += bool(t["infra"])
            tally["retried_trials"] += bool(t["retried"])
    print(json.dumps({
        "dir": d.rstrip("/").split("/")[-1],
        "sessions": len(c["sessions"]),
        "trials": sum(v[1] for v in per.values()),
        "trials_passed": sum(v[0] for v in per.values()),
        "entries": len(per),
        "entries_per_app": collections.Counter(k.split(":")[0] for k in per),
        "entries_not_all_pass": {k: v for k, v in sorted(per.items()) if v[0] != v[1]},
        **tally,
    }, sort_keys=True))
