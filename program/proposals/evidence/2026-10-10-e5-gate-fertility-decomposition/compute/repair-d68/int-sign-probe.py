#!/usr/bin/env python3
"""S1v2 probe: where does the decay-by-write interaction change sign in the toy, and is that
region admissible under the registered floors?

Not the registered path: a small direct probe (75 articles x 4 episodes per cell, seed fixed)
of CAN, NAT, CLAMP and DEC at f = 2.0 in the erase-dominated family of mech-sim-v2.py
(lambda 0, rho 0, no write normalisation), over passage write strengths. It reports raw
accuracies and b_TNIE, b_PNIE, b_INT on the corrected scale, beside the native floor of 40.

Usage: python int-sign-probe.py <out.json>
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("ms", HERE / "mech-sim-v2.py")
ms = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ms)


def main() -> int:
    rows = []
    for tb in ((0.10, 0.25), (0.12, 0.30), (0.15, 0.30), (0.25, 0.45)):
        sp = dict(lam=0.0, rho=0.0, wnorm=False, gscale=1.0, tb=tb)
        w = ms.World("probe", sp, 42)
        w.gscale = 1.0
        for k in (4, 8, 16):
            bank = ms.make_bank(np.random.default_rng([1, k]), 75, k, 1.0, tb)
            can = ms.run_arm(bank, w, ms.canonical_passage(bank), "native")
            mc = ms.refine_counts(np.random.default_rng([2, k]), bank["n"], 2.0)
            psg = ms.passage(bank, w, mc, np.random.default_rng([3, k]))
            nat = ms.run_arm(bank, w, psg, "native")
            clamp = ms.run_arm(bank, w, psg, "clamp", can_targets={"g1": can["g1_tok"], "g2": can["g2_tok"]})
            dec = ms.run_arm(bank, w, ms.canonical_passage(bank), "transplant", dec_targets={"g1": nat["g1_tok"], "g2": nat["g2_tok"]})
            s = ms.ev2.secant_scale(2.0)
            tn = float((clamp["y"] - nat["y"]).mean() * s)
            pn = float((can["y"] - dec["y"]).mean() * s)
            rows.append({"tb": tb, "K": k, "f": 2.0, "episodes": int(bank["n"]), "acc_CAN": float(can["y"].mean()),
                         "acc_NAT": float(nat["y"].mean()), "b_TNIE": tn, "b_PNIE": pn, "b_INT": tn - pn,
                         "native_floor_passed": bool(nat["y"].mean() >= ms.ev2.FLOOR_NAT),
                         "canonical_under_ceiling": bool(can["y"].mean() <= ms.ev2.CEILING_CAN)})
            print(rows[-1], flush=True)
    Path(sys.argv[1]).write_text(json.dumps({"rows": rows}, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
