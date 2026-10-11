#!/usr/bin/env python3
"""Derive the band-path constants of registration v2 from S1v2's attenuation map.

Inputs: the merged attenuation map (consensus target; cells over aligner AER, error
correlation c and the spurious:missed split) and wave-1-of-this-run's per-aligner map
(single-aligner alpha; at c = 1 the consensus equals each aligner, so those cells give
the c = 1 end of the recall- and precision-heavy curves). Band: each aligner's link
AER at most 0.15, any c, any split.

Outputs (band.json):
* alpha_max: the largest consensus alpha in the band (the NO_HEADROOM correction
  divides by it, so it never overstates S inside the band);
* alpha_min_table: for each upper edge u of the measured pair agreement, the smallest
  consensus alpha among band conditions whose agreement is below u. Along each curve
  (fixed AER pair and split) alpha falls and agreement rises with c, so the worst case
  below u is the largest c whose agreement is below u, found by linear interpolation
  between simulated c values;
* agree_min: just below the smallest agreement seen in the band (lower values mean the
  aligners are worse than the band); agree_max: the top edge of the table (at or above
  it errors are presumed shared and only the gold path can decide).

Usage: band_envelope.py <atten-consensus.json> <atten-single.json> <band.json>
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

EDGES = (0.55, 0.65, 0.75, 0.85)
BAND_AER = 0.15


def main():
    cons = json.loads(Path(sys.argv[1]).read_text())["atten"]
    single = json.loads(Path(sys.argv[2]).read_text())["atten"]
    curves = defaultdict(dict)
    alpha_cells = []
    for block in cons:
        for r in block["rows"]:
            if r["profile"] != "zh":
                continue
            key = (r["split"], r["aer_target_A"], r["aer_target_B"])
            curves[key][r["c"]] = (r["pair_agreement_dice"], r["alpha_C"])
            if max(r["aer_target_A"], r["aer_target_B"]) <= BAND_AER + 1e-9:
                alpha_cells.append((r["alpha_C"], r["pair_agreement_dice"], key, r["c"]))
    for block in single:  # c = 1: consensus = single aligner (agreement 1.0)
        for r in block["rows"]:
            if r["profile"] != "zh" or r["c"] != 1.0:
                continue
            key = (r["split"], r["aer_target"], r["aer_target"])
            if 1.0 not in curves[key]:
                curves[key][1.0] = (1.0, r["alpha_A"])
    band_keys = [k for k in curves if max(k[1], k[2]) <= BAND_AER + 1e-9]
    table = []
    for u in EDGES:
        worst = (9.0, None)
        for key in band_keys:
            pts = sorted(curves[key].items())  # by c
            cand = []
            for (c0, (a0, al0)), (c1, (a1, al1)) in zip(pts, pts[1:]):
                if a0 < u:
                    cand.append((al0, c0))
                if a0 < u <= a1 and a1 > a0:          # interpolate to the c where agreement reaches u
                    t = (u - a0) / (a1 - a0)
                    cand.append((al0 + t * (al1 - al0), c0 + t * (c1 - c0)))
            if pts and pts[-1][1][0] < u:
                cand.append((pts[-1][1][1], pts[-1][0]))
            for al, c in cand:
                if al < worst[0]:
                    worst = (al, {"curve": list(key), "c": round(c, 3)})
        table.append({"agreement_below": u, "alpha_min": round(worst[0] - 0.005, 3), "worst_case": worst[1]})
    alpha_max = max(a for a, *_ in alpha_cells)
    agree_min = min(g for _, g, *_ in alpha_cells)
    out = {"alpha_max": round(alpha_max + 0.005, 3), "alpha_min_table": table,
           "agree_min": round(agree_min - 0.015, 3), "agree_max": EDGES[-1],
           "band": {"aer_max_each_aligner": BAND_AER, "c": "any", "splits": "balanced, precision-heavy, recall-heavy"},
           "rounding": "alpha_max rounded up by 0.005 and every alpha_min down by 0.005 (conservative)",
           "curves_used": {f"{k[0]}:{k[1]}:{k[2]}": {str(c): v for c, v in sorted(d.items())} for k, d in curves.items() if k in band_keys}}
    Path(sys.argv[3]).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("alpha_max", "alpha_min_table", "agree_min", "agree_max")}, indent=1))


if __name__ == "__main__":
    main()
