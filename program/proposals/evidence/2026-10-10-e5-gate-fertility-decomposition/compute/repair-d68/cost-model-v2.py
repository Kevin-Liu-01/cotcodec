#!/usr/bin/env python3
"""S3v2: token counts, GPU-hour estimate, registered caps and the degradation ladder for v2.

Same throughput assumptions as wave 1's S3 (`compute/cost-model.py`, kept unedited): no
inference throughput has been measured on this host. Central GDN 40,000 and RWKV-7 20,000
tok/s, hook overhead 1.2, resume 1.1, fixed 0.15 h per job; high (slow) GDN 20,000 and
RWKV-7 8,000 tok/s, hook overhead 1.5, fixed 0.25 h. The smoke measures both before the main
jobs.

v2 cells per subject (registration v2, "Cells"): the primary factorial CAN, DEC, CLAMP(f_p),
NAT(f_p) at the selected load K_p on 4 x N_ARTICLES_BY_F[f_p] episodes (8,000 at f_p = 2.7,
12,000 at f_p = 2.0), never cut; secondary cells at K_p on 1,000 episodes each, dropped in
the registered ladder order if the projection exceeds the cap. The smoke carries the
held-out operating-point cells (CAN at K in {4, 8, 16}, NAT at (K, f) for f in {2.7, 2.0},
200 episodes each) and the instrument gates. Every branch of (K_p, f_p) is costed; the caps
cover the worst branch's primary cells and gates at the high scenario.

Usage: python cost-model-v2.py <out.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

R = 512  # canonical passage tokens (subject G tokenizer; fewer on RWKV World)
LEAD, FACT, QUERY, CAND, DECODE = 24, 18, 12, 24, 6
CONTEXT_LIMIT = 1900
N_ART = {2.7: 2000, 2.0: 3000}
EPA = 4
N_SECONDARY = 1000
SCEN = {"central": dict(gdn=40000, rwkv=20000, hook=1.2, resume=1.1, fixed=0.15),
        "high": dict(gdn=20000, rwkv=8000, hook=1.5, resume=1.1, fixed=0.25)}
CAPS = {"smoke": 0.75, "gdn_main": 1.75, "rwkv_main": 3.75}


def base(k: int) -> int:
    return LEAD + k * FACT + QUERY + CAND + DECODE


def tok(k: int, r_units: float) -> float:
    return base(k) + r_units * R


def main_cells(k: int, f: float) -> list[dict]:
    n = N_ART[f] * EPA
    other = 2.0 if f == 2.7 else 2.7
    rows = [dict(cell="CAN", r=1.0, n=n, tier="primary"), dict(cell="DEC", r=1.0, n=n, tier="primary"),
            dict(cell=f"CLAMP({f})", r=f, n=n, tier="primary"), dict(cell=f"NAT({f})", r=f, n=n, tier="primary"),
            dict(cell="BPB subset (CAN, NAT(f_p), BND; full logits)", r=1.0 + f + 1.0, n=200, tier="L1"),
            dict(cell=f"NAT({other}) and CLAMP({other})", r=2 * other, n=N_SECONDARY, tier="L2"),
            dict(cell="BND and ZERO", r=1.0 + 0.0, n=N_SECONDARY, tier="L3", extra_base=1),
            dict(cell=f"R2(1) and R2({f})", r=1.0 + f, n=N_SECONDARY, tier="L4", extra_base=1),
            dict(cell=f"FILL({f})", r=f, n=N_SECONDARY, tier="L5"),
            dict(cell=f"CLAMP-LAST({f})", r=f, n=N_SECONDARY, tier="L6"),
            dict(cell=f"SIL-NAT({f}) and SIL-CLAMP({f})", r=2 * f, n=N_SECONDARY, tier="L7", extra_base=1),
            dict(cell=f"DOSE({f})", r=1.0, n=N_SECONDARY, tier="L8")]
    for row in rows:
        nb = 1 + row.get("extra_base", 0)
        if row["cell"].startswith("NAT(") and "and" in row["cell"]:
            nb = 2
        if row["cell"].startswith("BPB"):
            nb = 3
        row["tokens_per_episode"] = nb * base(k) + row["r"] * R
        row["tokens"] = row["n"] * row["tokens_per_episode"]
    return rows


def smoke_cells() -> list[dict]:
    rows = []
    for k in (4, 8, 16):
        rows.append(dict(cell=f"held-out CAN K{k}", n=200, tokens_per_episode=tok(k, 1.0)))
        for f in (2.7, 2.0):
            rows.append(dict(cell=f"held-out NAT({f}) K{k}", n=200, tokens_per_episode=tok(k, f)))
    rows += [dict(cell="I1 identity (hooks at c = 1 vs unhooked), K16 f=1 and f=2.7", n=200, tokens_per_episode=2 * tok(16, 1.0) + 2 * tok(16, 2.7)),
             dict(cell="I2 r = 2 two ways and c = 2 two ways (G) / I2b reference (R)", n=200, tokens_per_episode=4 * tok(16, 1.0)),
             dict(cell="I3 padding", n=200, tokens_per_episode=2 * tok(16, 2.7)),
             dict(cell="I7 loader perplexity", n=100, tokens_per_episode=1024),
             dict(cell="kill-and-resume test", n=40, tokens_per_episode=4 * tok(16, 2.7)),
             dict(cell="throughput (64 episodes x every cell type)", n=64, tokens_per_episode=12 * tok(16, 2.7))]
    for r in rows:
        r["tokens"] = r["n"] * r["tokens_per_episode"]
    return rows


def hours(tokens: float, tps: float, s: dict) -> float:
    return tokens / tps / 3600 * s["hook"] * s["resume"] + s["fixed"]


def main() -> int:
    out = {"assumptions": dict(R=R, LEAD=LEAD, FACT=FACT, QUERY=QUERY, CAND=CAND, DECODE=DECODE, N_ART=N_ART, EPA=EPA,
                               N_SECONDARY=N_SECONDARY, CONTEXT_LIMIT=CONTEXT_LIMIT, scenarios=SCEN,
                               anchor="73,045 tok/s/GPU training, 422M GDN hybrid, fla 0.5.2 (docs/h100-node.md); forward-only inference never measured on this host"),
           "branches": {}, "registered_caps_gpu_h": dict(CAPS, sum=round(sum(CAPS.values()), 2))}
    sm = smoke_cells()
    smoke_tokens = sum(r["tokens"] for r in sm)
    out["smoke"] = {"cells": sm, "tokens_per_subject": smoke_tokens,
                    "hours_both_subjects": {k: round(smoke_tokens / s["gdn"] / 3600 * s["hook"] + smoke_tokens / s["rwkv"] / 3600 * s["hook"] + s["fixed"], 3) for k, s in SCEN.items()}}
    worst = {"gdn": 0.0, "rwkv": 0.0}
    for k in (4, 8, 16):
        for f in (2.7, 2.0):
            rows = main_cells(k, f)
            prim = sum(r["tokens"] for r in rows if r["tier"] == "primary")
            total = sum(r["tokens"] for r in rows)
            ctx = max(base(k) - CAND - DECODE + 6 + f * R, base(k) - CAND - DECODE + 6 + f * R)
            br = {"cells": rows, "tokens_primary": prim, "tokens_total": total, "max_context_tokens": ctx,
                  "over_context_limit": ctx > CONTEXT_LIMIT, "estimate_h": {}}
            for name, s in SCEN.items():
                br["estimate_h"][name] = {"gdn_total": round(hours(total, s["gdn"], s), 3), "rwkv_total": round(hours(total, s["rwkv"], s), 3),
                                          "gdn_primary": round(hours(prim, s["gdn"], s), 3), "rwkv_primary": round(hours(prim, s["rwkv"], s), 3)}
            worst["gdn"] = max(worst["gdn"], br["estimate_h"]["high"]["gdn_primary"])
            worst["rwkv"] = max(worst["rwkv"], br["estimate_h"]["high"]["rwkv_primary"])
            # throughput below which the primary cells alone exceed each main cap (INFEASIBLE)
            hi = SCEN["high"]
            br["primary_only_throughput_floor_tok_s"] = {
                "gdn": round(prim * hi["hook"] * hi["resume"] / ((CAPS["gdn_main"] - hi["fixed"]) * 3600)),
                "rwkv": round(prim * hi["hook"] * hi["resume"] / ((CAPS["rwkv_main"] - hi["fixed"]) * 3600))}
            out["branches"][f"K{k}_f{f}"] = br
    out["worst_branch_primary_high_h"] = worst
    out["caps_cover_worst_primary_high"] = worst["gdn"] <= CAPS["gdn_main"] and worst["rwkv"] <= CAPS["rwkv_main"]
    out["d22_rule"] = "sum of registered caps of every job must be at most 8.0 GPU-h"
    out["ladder"] = ["L1 BPB subset", "L2 the other fertility (NAT and CLAMP)", "L3 BND and ZERO", "L4 R2 pair",
                     "L5 FILL(f_p)", "L6 CLAMP-LAST(f_p)", "L7 SIL-NAT and SIL-CLAMP", "L8 DOSE(f_p)",
                     "never cut: CAN, DEC, CLAMP(f_p), NAT(f_p) at K_p and the gates"]
    Path(sys.argv[1]).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    for key, br in out["branches"].items():
        print(key, f"primary {br['tokens_primary']:.3e} total {br['tokens_total']:.3e} ctx {br['max_context_tokens']:.0f}",
              br["estimate_h"]["central"], br["estimate_h"]["high"])
    print("smoke", out["smoke"]["hours_both_subjects"], "caps", out["registered_caps_gpu_h"], "worst primary high", worst,
          "covered", out["caps_cover_worst_primary_high"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
