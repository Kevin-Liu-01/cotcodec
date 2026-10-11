#!/usr/bin/env python3
"""Design exploration (recorded, not decision-bearing): attenuation of alternative targets.

For one condition (profile, AER of A and B, error correlation c) and seed, builds a small pool
and reports, for several ways of turning two aligners' links into a target, the attenuation
alpha (S of the truth oracle under the target), the floor share, and S of the truth oracle
under the truth. Targets: A alone (registered per-aligner target), consensus links A&B,
union of allowed pairs, and the consensus target with each aligner's links pruned to those
the other aligner supports within one word on the other side.

Usage: explore_targets.py <out.json> <seed> <aerA> <aerB> <c> <n>
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e3_estimator_v2 as est  # noqa: E402
import instrument_sim_v2 as sim  # noqa: E402


def soft_support(la, lb):
    keep = set()
    lbs = set(lb)
    for i, j in la:
        if any((i, j + d) in lbs for d in (-1, 0, 1)):
            keep.add((i, j))
    return keep


def main():
    out, seed, aa, ab, c, n = sys.argv[1], int(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]), int(sys.argv[6])
    calib = json.loads((HERE / "calib.json").read_text())["calib"]
    da, sa = sim.calib_lookup(calib, "zh", aa)
    db, sb = sim.calib_lookup(calib, "zh", ab)
    rng = np.random.default_rng(seed)
    acc = {}
    for _ in range(n):
        pair = sim.gen_pair(rng, sim.PROFILES["zh"])
        n_ev = len(pair["links_T"]) + pair["n_a"] + pair["n_b"]
        shared = rng.random((n_ev, 2))
        la = sim.noisy_links(pair, da, sa, c, shared, rng)
        lb = sim.noisy_links(pair, db, sb, c, shared, rng)
        na, nb = pair["n_a"], pair["n_b"]
        MT = est.allowed_pairs(na, nb, pair["links_T"])
        MA = est.allowed_pairs(na, nb, la)
        MB = est.allowed_pairs(na, nb, lb)
        targets = {
            "A": MA,
            "consensus_links": est.allowed_pairs(na, nb, la & lb),
            "union_pairs": MA | MB,
            "soft_consensus_links": est.allowed_pairs(na, nb, soft_support(la, lb) | soft_support(lb, la)),
        }
        adjT = est.row_masks(MT)
        for name, M in targets.items():
            adj = est.row_masks(M)
            nuX = est.nu(M, adj=adj)
            k = est.budget(na - 1, nb - 1, nuX, nuX)
            if k <= 0:
                continue
            mm = est.max_matching_pairs(MT, rng, adj=adjT)
            sel = [mm[i] for i in rng.permutation(len(mm))[: min(k, len(mm))]]
            ra = sorted({a for a, _ in sel}); cb = sorted({b for _, b in sel})
            h = est.matching_size_masks(adj, ra, cb)
            f = est.floor_hits(M, k, rng, 32, adj=adj)
            fT = est.floor_hits(MT, k, rng, 32, adj=adjT)
            hT = est.matching_size_masks(adjT, ra, cb)
            a = acc.setdefault(name, {"h": 0.0, "f": 0.0, "k": 0.0, "hT": 0.0, "fT": 0.0, "cT": 0.0, "pairs": 0.0, "truepairs": 0.0})
            a["h"] += h; a["f"] += f; a["k"] += k; a["hT"] += hT; a["fT"] += fT; a["cT"] += min(k, len(mm))
            a["pairs"] += M.sum(); a["truepairs"] += (M & MT).sum()
    res = {"seed": seed, "aer_A_B": [aa, ab], "c": c, "pairs": n, "targets": {}}
    for name, a in acc.items():
        res["targets"][name] = {"alpha": round((a["h"] - a["f"]) / (a["k"] - a["f"]), 4),
                                "floor_share": round(a["f"] / a["k"], 4),
                                "S_truth_oracle_under_truth": round((a["hT"] - a["fT"]) / (a["cT"] - a["fT"]), 4),
                                "precision_of_allowed_pairs": round(a["truepairs"] / max(a["pairs"], 1), 4),
                                "mean_k": round(a["k"] / n, 3)}
    Path(out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res["targets"]))


if __name__ == "__main__":
    main()
