#!/usr/bin/env python3
"""Section 12's report of key events read without their state, from the analysis itself.

Decision D45 (iii): ``acceptance.state_not_observed_report`` lists, over every trial of every
attempt, each key event the rule reads without its modifier state (recorded without Mod2
after a key press recorded with Mod2 in its window) with its offset from the preceding
processed press, and each trial with a key event without Mod2 that no processed press
preceded. This runs it on run directories loaded by ``acceptance.load``, one report per
job, from the repository at the commit given on the command line (run from that export, so
the report is the code's own). It judges nothing.

    python3 -B section12_report.py OUT.json RUN_DIR...

Python 3.10 with the repository on ``sys.path`` (run from the export's root).
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.getcwd())

from harness.q2.action_path import acceptance  # noqa: E402


def main(argv: list[str]) -> int:
    out_path, runs = argv[1], argv[2:]
    out = {"source": os.getcwd(), "jobs": {}}
    for run in runs:
        campaign = acceptance.load(run)
        report = acceptance.state_not_observed_report([campaign])
        out["jobs"][campaign["job"]] = {
            "run_dir": os.path.basename(run.rstrip("/")),
            "campaign_id": (campaign["manifest"] or {}).get("campaign_id"),
            "git_sha": (campaign["manifest"] or {}).get("git_sha"),
            **report,
        }
        events = sum(len(t["events"]) for t in report["read_without_state"])
        unpreceded = sum(len(t["events"]) for t in report["no_processed_press_before"])
        print(campaign["job"], report["trials"], "trials;", events, "events read without state;",
              unpreceded, "without Mod2 and no processed press before")  # fmt: skip
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(out, handle, indent=1, sort_keys=True)
        handle.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
