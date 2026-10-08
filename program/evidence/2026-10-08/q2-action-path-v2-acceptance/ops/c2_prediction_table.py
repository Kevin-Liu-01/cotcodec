#!/usr/bin/env python3
"""Section 12's L0-raw prediction table: v2's C2 beside v1's a-priori result (job 768).

Reads v2's ``acceptance/c2-verdict.json`` and ``acceptance/c2-campaigns.json`` (written by
``analyze_controls.py`` with the frozen ``acceptance.c2``) and v1's
``../q2-action-path-acceptance/acceptance/c2-verdict.json``, and lists, for every entry
that was predicted to fail or was not PASS under either reading in either run: the v2
prediction, v2's status under C2's rule and under section 5 with its PASS count and
failure reasons, and v1's statuses. It judges nothing; the statuses are the frozen code's.

    python3 -B c2_prediction_table.py EVIDENCE_DIR > acceptance/c2-prediction-table.json
"""

from __future__ import annotations

import collections
import json
import os
import sys
from typing import Any


def read_json(path: str) -> Any:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    here = sys.argv[1]
    v2 = read_json(os.path.join(here, "acceptance", "c2-verdict.json"))
    campaigns = read_json(os.path.join(here, "acceptance", "c2-campaigns.json"))
    v1 = read_json(
        os.path.join(here, "..", "q2-action-path-acceptance", "acceptance", "c2-verdict.json")
    )
    failed: collections.Counter[str] = collections.Counter()
    reasons: dict[str, set[str]] = collections.defaultdict(set)
    for c in campaigns:
        for row in c["failed_trials"]:
            failed[row["cell"]] += 1
            for reason in row["reasons"] or []:
                reasons[row["cell"]].add(reason[:80])
    predicted = set(v2["predicted_fail"])
    cells = sorted(
        cell
        for cell in v2["entries"]
        if cell in predicted
        or any(
            status != "PASS"
            for status in (
                v2["entries"][cell],
                v2["strict_entries"][cell],
                v1["entries"].get(cell),
                v1["strict_entries"].get(cell),
            )
        )
    )
    reps = 5
    rows = [
        {
            "entry": cell,
            "predicted": "FAIL" if cell in predicted else "PASS",
            "v2_c2_rule": v2["entries"][cell],
            "v2_section5": v2["strict_entries"][cell],
            "v2_section5_pass": f"{reps - failed[cell]}/{reps}",
            "v2_failure_reasons": sorted(reasons[cell]),
            "v1_c2_rule": v1["entries"].get(cell),
            "v1_section5": v1["strict_entries"].get(cell),
        }
        for cell in cells
    ]
    others = sorted(set(v2["entries"]) - set(cells))
    json.dump(
        {
            "v2_pass": v2["pass"],
            "v2_problems": v2["problems"],
            "v1_pass": v1["pass"],
            "v1_problems": v1["problems"],
            "rows": rows,
            "other_entries_pass_under_both_readings_in_both_runs": len(others),
        },
        sys.stdout,
        indent=1,
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
