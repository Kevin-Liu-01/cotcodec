#!/usr/bin/env python3
"""Registered Phase 1 caps of s2-arabic-cua-locale-v2 for every admissible task count K (26-43).

n = 16 if K <= 35, else 12 (power-osworld.N_MAX_BY_K); cap by the Q2 design study's slot rule at
the high slot price (the mean slot of S1a's 9B episodes that ran to the 15-step cap on the
candidate tasks, read from power-osworld.json), plus the 6-minute overlay reserve.

Usage: python registered-caps.py <power-osworld.json> <out.json>
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("po", HERE / "power-osworld.py")
po = importlib.util.module_from_spec(spec)
spec.loader.exec_module(po)


def main() -> int:
    d = json.loads(Path(sys.argv[1]).read_text())
    slot_high = next(iter(d["simulation"].values()))["cost"]["slot_high_s_cap_length_episodes"]
    by_k = {}
    for K in range(26, 44):
        n = next(nn for kmax, nn in po.N_MAX_BY_K if K <= kmax)
        by_k[str(K)] = {"n": n, **po.cost(K, n, slot_high)}
    worst = max(by_k.values(), key=lambda r: r["registered_caps_gpu_h_incl_overlay"])
    out = {
        "phase0": 0.0,
        "overlay_reserve_gpu_h": 0.1,
        "phase1_rule": "one job: ceil(3 + L/60 + (4 K n x s / V + drain) x 1.2 x 1.05 / 60) min, L = 113.2 s, drain = 104.6 s, V = 20, s = high slot price; n = 16 if K <= 35 else 12",
        "slot_high_s": slot_high,
        "phase1_plus_overlay_by_K": by_k,
        "maximum_over_K": worst["registered_caps_gpu_h_incl_overlay"],
        "d22_line": 8.0,
        "admission": "below D20's 8 GPU-h line for every admissible K; by D68's structural note the GPU stage still waits on Kevin's admission ruling or D24's trust store",
    }
    Path(sys.argv[2]).write_text(json.dumps(out, indent=1) + "\n")
    print(out["maximum_over_K"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
