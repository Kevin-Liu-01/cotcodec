#!/usr/bin/env python3
"""How the memory-aware policy's estimates compare with what job 713 survived (CPU).

For every interval of job 713 (the re-pilot at 12 per GPU), the sum of the
estimated peaks (``harness.q1.memory``) of the items running then, the units they
would hold under ``q1-stage0-exec/2``, and whether any of them met a resource
failure. Peaks of concurrent items do not coincide, so a sum of estimates above
the GPU's memory without a failure says the estimates are conservative; the
smallest sum at which a failure occurred bounds how far they could shrink.

    python program/evidence/2026-10-07/q1-engineering-d31/fixpass/memory_calibration.py \\
        --repilot-run RUN713/q1 --out memory-calibration.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from harness.q1 import faults, trim  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repilot-run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    base = args.repilot_run / "repilot"
    planned = {}
    for line in (base / "items.jsonl").read_text().splitlines():
        if line.strip():
            e = json.loads(line)
            planned[f"{e['kernel_id']}|{e['gate']}|seed-{e['seed']}"] = e
    rows = [
        json.loads(x)
        for name in ("journal.jsonl", "references.jsonl")
        for x in (base / name).read_text().splitlines()
        if x.strip()
    ]
    attempts: dict[tuple[str, int], dict] = {}
    for r in rows:
        d = r["details"]
        a = attempts.setdefault(
            (d["item_key"], r["attempt"]),
            {"key": d["item_key"], "start": d["item_started_at"], "end": d["item_ended_at"]},
        )
        a["failed"] = a.get("failed", False) or faults.is_resource_text(json.dumps(d))
    for a in attempts.values():
        e = planned[a["key"]]
        a["units"], peak = trim.item_units(e["problem_id"], e["gate"])
        a["estimate_gb"] = (peak or 0) / 1e9
    spans = list(attempts.values())
    events = sorted({t for a in spans for t in (a["start"], a["end"])})
    clean_max, failing = 0.0, []
    over_capacity_clean = 0.0
    for left, right in zip(events, events[1:], strict=False):
        active = [a for a in spans if a["start"] <= left and a["end"] >= right]
        if not active:
            continue
        total = sum(a["estimate_gb"] for a in active)
        units = sum(a["units"] for a in active)
        if any(a["failed"] for a in active):
            failing.append((total, units))
        else:
            clean_max = max(clean_max, total)
            if units > 12:
                over_capacity_clean += right - left
    out = {
        "attempts": len(spans),
        "largest_estimate_sum_gb_without_a_resource_failure": round(clean_max, 1),
        "smallest_estimate_sum_gb_with_a_resource_failure": round(min(t for t, _ in failing), 1),
        "median_estimate_sum_gb_with_a_resource_failure": round(
            statistics.median(t for t, _ in failing), 1
        ),
        "smallest_units_sum_with_a_resource_failure": min(u for _, u in failing),
        "seconds_over_12_units_without_a_resource_failure": round(over_capacity_clean, 1),
    }
    args.out.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
