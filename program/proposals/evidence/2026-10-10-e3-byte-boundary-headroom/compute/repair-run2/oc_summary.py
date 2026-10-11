#!/usr/bin/env python3
"""Summarise oc_decide.py's verdict tables into the proposal's operating-characteristics tables.

Groups of conditions (aligner link AER of A and B, error correlation c):
  G1 published rates, c 0 and 0.5 (AER 0.085 / 0.05)
  G2 published rates, identical errors (c 1)
  G3 band, c 0 to 0.5 (AER 0.085 / 0.085 at c 0.25; 0.12 at c 0 and 0.5; 0.15 at c 0 and 0.5, balanced
     and recall-heavy)
  G4 band edge, identical errors (AER 0.15, c 1)
  G5 beyond the band (AER 0.20 at c 0.5; 0.25 at c 1)
Scenario systems: a selection on true allowed pairs with a fraction f of each side's gaps displaced
to random word gaps (random_f) or to adjacent word gaps (near_f). A verdict is decisive if it is
NO_HEADROOM or HEADROOM; correct if NO_HEADROOM with S_true >= 0.90 or HEADROOM with S_true < 0.85;
systems in the tolerance zone (0.85 <= S_true < 0.90) count toward decisiveness only.

Usage: oc_summary.py <decisions.json> <out.json> <out.md>
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np


def group(c):
    a, b = c["aer_A_B"]
    if (a, b) == (0.085, 0.05):
        return "G2" if c["c"] == 1.0 else "G1"
    if max(a, b) <= 0.15 + 1e-9:
        return "G4" if c["c"] == 1.0 else "G3"
    return "G5"


NAMES = {"G1": "published rates (AER 0.085 and 0.05), c 0-0.5", "G2": "published rates, identical errors (c 1)",
         "G3": "band (AER 0.085-0.15), c 0-0.5", "G4": "band edge (AER 0.15), identical errors (c 1)",
         "G5": "beyond the band (AER 0.20 at c 0.5; 0.25 at c 1)"}


def main():
    dec = json.loads(Path(sys.argv[1]).read_text())
    acc = defaultdict(lambda: defaultdict(list))   # (group, path) -> system -> list of row dicts
    conds = defaultdict(list)
    for c in dec["conditions"]:
        g = group(c)
        conds[g].append(f"seed {c['seed']} AER {c['aer_A_B'][0]}/{c['aer_A_B'][1]} c {c['c']} {c['split']}")
        for r in c["rows"]:
            for path, v in r["paths"].items():
                pk = "band" if path == "band" else ("gold" if path == "gold+0.00" else path)
                acc[(g, pk)][r["system"]].append((r["S_true"], v))
    out = {"groups": {}, "conditions": {g: v for g, v in conds.items()}}
    md = []
    for g in ("G1", "G2", "G3", "G4", "G5"):
        if not conds[g]:
            continue
        md.append(f"**{g}: {NAMES[g]}** ({len(conds[g])} condition-seed runs)")
        md.append("")
        md.append("| scenario system | mean S_true | band: P(NH) / P(H) / P(no verdict) | gold: P(NH) / P(H) / P(no verdict) |")
        md.append("|---|---:|---|---|")
        gsum = {}
        extra_paths = sorted({pk for (gg, pk) in acc if gg == g and pk not in ("band", "gold")})
        for path in ("band", "gold") + tuple(extra_paths):
            sysd = acc[(g, path)]
            if not sysd:
                continue
            dec_p, cor_p, wrong = [], [], []
            for name, items in sysd.items():
                st = np.mean([x[0] for x in items])
                nh = np.mean([x[1]["primary"].get("NH", 0) for x in items])
                hh = np.mean([x[1]["primary"].get("H", 0) for x in items])
                dec_p.append(nh + hh)
                if st >= 0.90:
                    cor_p.append(nh)
                    wrong.append(hh)
                elif st < 0.85:
                    cor_p.append(hh)
                    wrong.append(nh)
            gsum[path] = {"mean_decisive": round(float(np.mean(dec_p)), 3), "mean_correct_outside_tolerance": round(float(np.mean(cor_p)), 3),
                          "max_wrong_decisive": round(float(np.max(wrong)), 3)}
        out["groups"][g] = {"name": NAMES[g], "summary": gsum, "runs": conds[g]}
        names = sorted(acc[(g, "band")], key=lambda n: (n.split("_")[0], float(n.split("_")[1])))
        for name in names:
            row = [name.replace("_", " f = ")]
            st = np.mean([x[0] for x in acc[(g, "band")][name]])
            row.append(f"{st:.2f}")
            for path in ("band", "gold"):
                items = acc[(g, path)].get(name, [])
                if not items:
                    row.append("")
                    continue
                nh = np.mean([x[1]["primary"].get("NH", 0) for x in items])
                hh = np.mean([x[1]["primary"].get("H", 0) for x in items])
                row.append(f"{nh:.2f} / {hh:.2f} / {1 - nh - hh:.2f}")
            md.append("| " + " | ".join(row) + " |")
        md.append("")
        md.append(f"Summary: band path mean P(decisive) {gsum['band']['mean_decisive']}, mean P(correct) outside the tolerance zone "
                  f"{gsum['band']['mean_correct_outside_tolerance']}, largest P(wrong decisive) {gsum['band']['max_wrong_decisive']}; "
                  f"gold path {gsum['gold']['mean_decisive']}, {gsum['gold']['mean_correct_outside_tolerance']}, {gsum['gold']['max_wrong_decisive']}."
                  + "".join(f" Gold sample with aligner AER shifted by {p[4:]} (seed 42 only): {gsum[p]['mean_decisive']}, "
                            f"{gsum[p]['mean_correct_outside_tolerance']}, {gsum[p]['max_wrong_decisive']}." for p in extra_paths))
        md.append("")
    Path(sys.argv[2]).write_text(json.dumps(out, indent=1) + "\n")
    Path(sys.argv[3]).write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
