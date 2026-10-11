#!/usr/bin/env python3
"""Merge the S2v2 parts (misc, grid0, grid1, tau, prof0, prof1) into power-sim-v2.json and add
the decisiveness summary the proposal reports.

Usage: python3 merge-power-v2.py <dir with power-<part>.json> <out power-sim-v2.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PARTS = ("misc", "grid0", "grid1", "tau", "prof0", "prof1")


def main() -> int:
    d = Path(sys.argv[1])
    merged = {"parts": {}}
    for p in PARTS:
        r = json.loads((d / f"power-{p}.json").read_text(encoding="utf-8"))
        merged["parts"][p] = {"elapsed_s": r["elapsed_s"]}
        merged.setdefault("params", r["params"])
        for key in ("v1_dilution_reproduced", "selection", "coverage", "tau_sensitivity"):
            if key in r:
                merged[key] = r[key]
        merged.setdefault("grid_P1", []).extend(r.get("grid_P1", []))
        merged.setdefault("profiles", []).extend(r.get("profiles", []))
    reg = [r for r in merged["grid_P1"] if r["n_articles"] == "registered"]
    by_sigma = {}
    for r in reg:
        by_sigma.setdefault(r["sigma"], []).append(r)
    summary = {}
    for sg, rows in sorted(by_sigma.items()):
        summary[str(sg)] = {
            "discordance_TNIE": round(sum(r["discordance_TNIE_mean"] for r in rows) / len(rows), 3),
            "P_correct_by_scenario": {r["scenario"]: round(r["P_correct"], 3) for r in rows},
            "P_KILL_by_scenario": {r["scenario"]: round(r["P_KILL"], 3) for r in rows},
            "mean_P_correct": round(sum(r["P_correct"] for r in rows) / len(rows), 3),
            "min_P_correct": round(min(r["P_correct"] for r in rows), 3),
        }
    merged["decisiveness_summary_P1_registered_n"] = summary
    line_rows = [r for r in reg if r["scenario"].startswith("line_")]
    merged["false_kill_at_line_max"] = max(r["P_KILL"] for r in line_rows) if line_rows else None
    merged["loss_null_at_line_max"] = max(sum(r["P"].get(k, 0.0) for k in ("KILL", "MASKED", "SELF_NORMALIZED", "PARITY_NULL"))
                                          for r in line_rows if r["scenario"] in ("line_both", "line_tnie_only")) if line_rows else None
    Path(sys.argv[2]).write_text(json.dumps(merged, indent=1) + "\n", encoding="utf-8")
    for sg, s in summary.items():
        print(sg, s["discordance_TNIE"], s["mean_P_correct"], s["min_P_correct"])
    print("false KILL at the line, max:", merged["false_kill_at_line_max"], "; any loss-null reading when TNIE is at the line, max:", merged["loss_null_at_line_max"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
