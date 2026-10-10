#!/usr/bin/env python3
"""S3: token counts, GPU-hour estimate, registered caps and the degradation ladder.

No inference throughput has been measured on this host (docs/h100-node.md). The only
measured anchor is training throughput in an fla 0.5.2 image: 73,045 tok/s/GPU for a
422M GDN hybrid (6 x 4.22e8 x 73,045 = 1.85e14 FLOP/s, about 18.7% of 989 TFLOP/s
dense bf16). A forward pass of a 1.466B model is about 2 x 1.466e9 FLOP/token, so the
same achieved rate would give about 63,000 tok/s. The scenarios below derate that:
central GDN 40,000 and RWKV-7 20,000 tok/s; high (slow) GDN 20,000 and RWKV-7 8,000.
These are assumptions, not measurements; the smoke job measures both before the main
jobs and the ladder below applies.

Usage: python cost-model.py <out.json>
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

R = 512  # canonical retention-span tokens on the m-a-p tokenizer (fewer on RWKV World)
LEAD = 24  # lead-in passage tokens
FACT = 18  # tokens per fact sentence (upper estimate on the m-a-p tokenizer)
QUERY = 12
CAND = 24  # four candidate codes of up to 6 tokens, scored from the cached state
DECODE = 6  # greedy decode steps for the secondary exact-match readout
N_PRIMARY = 1500  # episodes per primary load (3 seeds x 500)
N_SECONDARY = 500
FS = (1.5, 2.0, 2.7)
CONTEXT_LIMIT = 1900  # leaves margin under the m-a-p config's 2,048


def base(k: int) -> int:
    return LEAD + k * FACT + QUERY + CAND + DECODE


def cell_tokens(k: int, r_units: float, extra_fact: int = 0) -> float:
    return base(k) + extra_fact + r_units * R


def cells() -> list[dict]:
    rows = []
    for k in (1, 4):  # primary loads
        rows.append(dict(cell=f"CAN K{k}", k=k, f=1.0, n=N_PRIMARY, tier="primary"))
        for f in FS:
            rows.append(dict(cell=f"NAT({f}) K{k}", k=k, f=f, n=N_PRIMARY, tier="primary"))
            rows.append(dict(cell=f"CLAMP({f}) K{k}", k=k, f=f, n=N_PRIMARY, tier="primary"))
        rows.append(dict(cell=f"BND K{k}", k=k, f=1.0, n=N_PRIMARY, tier="primary"))
        rows.append(dict(cell=f"ZERO K{k}", k=k, f=0.0, n=N_PRIMARY, tier="primary"))
    for c, f in (("CAN K16", 1.0), ("NAT(2.7) K16", 2.7), ("CLAMP(2.7) K16", 2.7), ("ZERO K16", 0.0)):
        rows.append(dict(cell=c, k=16, f=f, n=N_SECONDARY, tier="ladder-3 K16"))
    for f in FS:
        rows.append(dict(cell=f"FILL({f}) K4", k=4, f=f, n=N_SECONDARY, tier="ladder-2 FILL"))
    rows += [dict(cell="SIL(1) K4", k=4, f=1.0, n=N_SECONDARY, tier="ladder-5 SIL"),
             dict(cell="SIL(2.7) K4", k=4, f=2.7, n=N_SECONDARY, tier="ladder-5 SIL"),
             dict(cell="SIL-CLAMP(2.7) K4", k=4, f=2.7, n=N_SECONDARY, tier="ladder-5 SIL"),
             dict(cell="R2(1) K4", k=4, f=1.0, n=N_SECONDARY, tier="ladder-6 R2"),
             dict(cell="R2(2.7) K4", k=4, f=2.7, n=N_SECONDARY, tier="ladder-6 R2"),
             dict(cell="FACT(2.0) K4", k=4, f=1.0, n=N_SECONDARY, tier="ladder-4 FACT", extra_fact=4 * FACT),
             dict(cell="BOTH(2.0) K4", k=4, f=2.0, n=N_SECONDARY, tier="ladder-4 FACT", extra_fact=4 * FACT)]
    rows.append(dict(cell="identity and r=2 cross-check (5 passes x 200 episodes, K4, f=1)", k=4, f=5.0,
                     n=200, tier="gate", extra_fact=4 * base(4)))
    rows.append(dict(cell="BPB full-logit subset (CAN, NAT x3, BND; 200 episodes)", k=4, f=1 + sum(FS) + 1,
                     n=200, tier="ladder-1 BPB", extra_fact=4 * base(4)))
    for r in rows:
        r["tokens_per_episode"] = cell_tokens(r["k"], r["f"], r.get("extra_fact", 0))
        r["tokens"] = r["n"] * r["tokens_per_episode"]
        if "x3" not in r["cell"] and "5 passes" not in r["cell"]:
            r["max_context"] = r["tokens_per_episode"] - CAND - DECODE + 6
    return rows


def hours(tokens: float, tps: float, hook: float, resume: float, fixed: float) -> float:
    return tokens / tps / 3600 * hook * resume + fixed


def main() -> int:
    rows = cells()
    total = sum(r["tokens"] for r in rows)
    primary = sum(r["tokens"] for r in rows if r["tier"] in ("primary", "gate"))
    over = [r["cell"] for r in rows if r.get("max_context", 0) > CONTEXT_LIMIT]
    scen = {"central": dict(gdn=40000, rwkv=20000, hook=1.2, resume=1.1, fixed=0.15),
            "high": dict(gdn=20000, rwkv=8000, hook=1.5, resume=1.1, fixed=0.25)}
    est = {}
    for name, s in scen.items():
        g = hours(total, s["gdn"], s["hook"], s["resume"], s["fixed"])
        w = hours(total, s["rwkv"], s["hook"], s["resume"], s["fixed"])
        gp = hours(primary, s["gdn"], s["hook"], s["resume"], s["fixed"])
        wp = hours(primary, s["rwkv"], s["hook"], s["resume"], s["fixed"])
        est[name] = {"gdn_job_h": round(g, 3), "rwkv_job_h": round(w, 3), "sum_h": round(g + w, 3),
                     "gdn_primary_only_h": round(gp, 3), "rwkv_primary_only_h": round(wp, 3)}
    caps = {"smoke": 0.25, "gdn_main": 1.25, "rwkv_main": 2.5}
    caps["sum"] = sum(caps.values())
    # throughput at which the primary cells alone reach each main cap (INFEASIBLE below it)
    def tps_floor(cap: float, hook: float = 1.5, resume: float = 1.1, fixed: float = 0.25) -> float:
        return primary * hook * resume / ((cap - fixed) * 3600)
    out = {
        "assumptions": {"R": R, "LEAD": LEAD, "FACT": FACT, "QUERY": QUERY, "CAND": CAND, "DECODE": DECODE,
                        "N_PRIMARY": N_PRIMARY, "N_SECONDARY": N_SECONDARY, "FS": FS, "CONTEXT_LIMIT": CONTEXT_LIMIT,
                        "anchor": "73,045 tok/s/GPU training, 422M GDN hybrid, fla 0.5.2 image 0b3ecef0-architecture (docs/h100-node.md); forward-only inference never measured on this host",
                        "scenarios": scen},
        "cells": rows,
        "tokens_per_subject": total, "tokens_primary_and_gates": primary,
        "cells_over_context_limit": over,
        "estimate": est,
        "registered_caps_gpu_h": caps,
        "d22_rule": "sum of registered caps of every job (smoke 0.25 + GDN 1.25 + RWKV 2.5 = 4.0) must be at most 8.0 GPU-h",
        "primary_only_throughput_floor_tok_s": {"gdn": round(tps_floor(caps["gdn_main"])),
                                                 "rwkv": round(tps_floor(caps["rwkv_main"]))},
        "ladder": ["ladder-1 BPB subset", "ladder-2 FILL (keep FILL(2.7))", "ladder-3 K16",
                   "ladder-4 FACT and BOTH", "ladder-5 SIL arms", "ladder-6 R2 arms",
                   "never cut: primary cells (CAN, NAT and CLAMP at f in {1.5, 2.0, 2.7}, BND, ZERO at K in {1, 4}) and the gates"],
    }
    Path(sys.argv[1]).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(f"tokens/subject {total:.3e}; primary+gates {primary:.3e}; over-limit {over}")
    print(json.dumps(est, indent=1), json.dumps(caps), out["primary_only_throughput_floor_tok_s"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
