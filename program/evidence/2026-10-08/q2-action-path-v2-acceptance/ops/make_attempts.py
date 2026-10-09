#!/usr/bin/env python3
"""Attempt map of one validity control from the submission log.

Reads ``ops/submissions.log`` (one line per submission: time, label, ``job=``,
``manifest=``), keeps the lines whose label starts with the control's name, reads each
manifest's ``campaign_id`` and writes ``{campaign_id: [job, ...]}`` with the jobs in
submission order (the first attempt, then a rerun under section 6.1).

    python3 -B make_attempts.py ROOT {C1,C2,C3} OUT.json
"""

from __future__ import annotations

import json
import os
import re
import sys

import yaml


def main() -> int:
    root, control, out = sys.argv[1:4]
    attempts: dict[str, list[str]] = {}
    line_re = re.compile(r"^\S+ (\S+) job=(\d+) manifest=(\S+)$")
    with open(os.path.join(root, "ops", "submissions.log"), encoding="utf-8") as handle:
        for line in handle:
            match = line_re.match(line.strip())
            if not match or not match.group(1).startswith(control + "-"):
                continue
            path = os.path.join(root, "manifests", "rendered", match.group(3))
            with open(path, encoding="utf-8") as manifest:
                campaign = yaml.safe_load(manifest)["campaign_id"]
            attempts.setdefault(campaign, []).append(match.group(2))
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(attempts, handle, indent=1, sort_keys=True)
        handle.write("\n")
    print(json.dumps({"control": control, "campaigns": len(attempts),
                      "jobs": sum(len(v) for v in attempts.values())}))  # fmt: skip
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
