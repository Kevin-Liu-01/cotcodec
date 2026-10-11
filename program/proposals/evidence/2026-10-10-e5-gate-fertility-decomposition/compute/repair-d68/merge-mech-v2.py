#!/usr/bin/env python3
"""Merge the S1v2 per-world outputs (mech-W1.json ... mech-W8.json, one process per world) into
mech-sim-v2.json with a summary table.

Usage: python3 merge-mech-v2.py <dir with mech-W*.json> <out mech-sim-v2.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    d = Path(sys.argv[1])
    merged = {"worlds": {}, "summary": []}
    for p in sorted(d.glob("mech-W*.json")):
        r = json.loads(p.read_text(encoding="utf-8"))
        merged.setdefault("params", r["params"])
        merged["worlds"].update(r["worlds"])
    for name, w in sorted(merged["worlds"].items()):
        row = {"world": name, "selected": w["heldout"]["selected"], "heldout_CAN": w["heldout"]["CAN"]}
        if "pool" in w:
            p = w["pool"]
            row.update({k: round(v, 2) for k, v in p.items() if k.startswith("b_")})
            row.update({"acc_CAN": p["acc_CAN"], "acc_NAT": p["acc_NAT"], "discordance_TNIE": round(p["discordance_TNIE"], 3),
                        "discordance_PNIE": round(p["discordance_PNIE"], 3), "identity_max_abs": p["identity_TE_eq_PNIE_PNDE_INT"],
                        "rf_median": round(w["ledger"]["rf_median_pooled"], 3),
                        "drift_k2_clamp_vs_nat": round(w["ledger"]["drift_k2_clamp_vs_nat"], 4),
                        "drift_k2_dec_vs_can": round(w["ledger"]["drift_k2_dec_vs_can"], 4),
                        "piece_sum_err": max(w["ledger"]["max_abs_piece_sum_error_clamp"], w["ledger"]["max_abs_piece_sum_error_dec"]),
                        "pool_reading": w["pool_reading"]["reading"],
                        "pool_TNIE_interval": [round(w["pool_reading"]["estimates"]["TNIE"][k], 2) for k in ("point", "lo", "hi")],
                        "pool_PNIE_interval": [round(w["pool_reading"]["estimates"]["PNIE"][k], 2) for k in ("point", "lo", "hi")],
                        "oc_registered_n": w["oc"]["P"], "oc_coverage": w["oc"]["coverage_90"]})
        if "v1_rule" in w:
            row["v1_rule"] = w["v1_rule"]
        if "line_scan" in w:
            row["line_scan"] = w["line_scan"]
            row["gscale"] = w["spec"]["gscale"]
        merged["summary"].append(row)
    Path(sys.argv[2]).write_text(json.dumps(merged, indent=1, default=float) + "\n", encoding="utf-8")
    for row in merged["summary"]:
        print(json.dumps({k: row.get(k) for k in ("world", "selected", "b_TE", "b_TNIE", "b_PNIE", "b_INT", "b_PNDE", "b_SIL_decay", "b_DOSE", "rf_median", "pool_reading", "oc_registered_n")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
