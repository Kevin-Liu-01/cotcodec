#!/usr/bin/env python3
"""Apply the registered v2 decision rule to S1v2's raw OC replicate statistics.

The OC runs store, per replicate, the consensus-target point estimate and 90%
interval of every system (band path: raw S_C; gold paths: S* = S_C / alpha_hat)
and the replicate's pair agreement. This script applies the registered constants
(band file) with the estimator's own decide functions, so verdict tables can be
recomputed without rerunning the simulation, and scores each verdict against the
truth: NO_HEADROOM is correct when S_true >= 0.90, HEADROOM when S_true < 0.85;
0.85 <= S_true < 0.90 is the tolerance zone, where any verdict is acceptable.

Usage: oc_decide.py <oc-merged.json> <band.json> <out.json>
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e3_estimator_v2 as est  # noqa: E402

NH_TRUE, H_TRUE = 0.90, 0.85


def truth(s):
    return "NH" if s >= NH_TRUE else ("H" if s < H_TRUE else "TOL")


def main():
    oc = json.loads(Path(sys.argv[1]).read_text())["oc"]
    band = json.loads(Path(sys.argv[2]).read_text())
    out = {"band_constants": band, "truth_lines": {"NO_HEADROOM_if_S_true_at_least": NH_TRUE, "HEADROOM_if_S_true_below": H_TRUE},
           "conditions": []}
    for cond in oc:
        raw = cond["raw_replicates"]
        ag = np.array(raw["agreement"])
        valid = np.array([est.band_valid(a, band["agree_min"], band["agree_max"]) for a in ag])
        paths = list(raw["systems"]["random_0.0"].keys())
        s_true = cond["S_true_all"]
        res = {"seed": cond["seed"], "aer_A_B": cond["aer_A_B"], "c": cond["c"], "split": cond["split"],
               "gold_alpha_hat_range": None,
               "alpha_pool": cond["alpha_pool"], "alpha_gold_pop_poststratified": cond.get("alpha_gold_pop_poststratified"),
               "pair_agreement_mean": cond["pair_agreement_mean"], "share_band_valid": round(float(valid.mean()), 4),
               "rows": []}
        per_rep = {}
        # alpha_hat of each replicate's gold draw, recovered from a well-conditioned system (S_C / S*)
        ref = raw["systems"]["random_0.0"]
        alpha_r = {path: [ref["C"][r][0] / reps[r][0] for r in range(len(reps))]
                   for path, reps in ref.items() if path != "C"}
        for name, d in raw["systems"].items():
            per_rep[name] = {}
            for path, reps in d.items():
                vs = []
                for r, (pt, lo, hi) in enumerate(reps):
                    if path == "C":
                        table = [(e["agreement_below"], e["alpha_min"]) for e in band["alpha_min_table"]]
                        vs.append(est.decide_band(pt, lo, hi, est.alpha_min_for(ag[r], table), band["alpha_max"]) if valid[r] else "INV")
                    else:
                        vs.append(est.decide_gold(pt, lo, hi, alpha_r[path][r]))
                per_rep[name]["band" if path == "C" else path] = vs
        res["gold_alpha_hat_range"] = {p: [round(min(v), 4), round(max(v), 4)] for p, v in alpha_r.items()}
        res["share_gold_valid"] = {p: round(float(np.mean([est.gold_valid(a) for a in v])), 4) for p, v in alpha_r.items()}
        for name in raw["systems"]:
            if name.startswith("M_"):
                continue
            row = {"system": name, "S_true": s_true[name], "truth": truth(s_true[name]), "paths": {}}
            for path, vs in per_rep[name].items():
                n = len(vs)
                cnt = defaultdict(int)
                for v in vs:
                    cnt[v] += 1
                fin = {}
                for q in ("M_low", "M_high"):
                    fc = defaultdict(int)
                    for v, vm in zip(vs, per_rep[q][path]):
                        fv = "INSTRUMENT_INVALID" if "INV" in (v, vm) else est.final_verdict(v, vm)
                        fc[fv] += 1
                    fin[q] = {k: round(c / n, 4) for k, c in fc.items()}
                t = truth(s_true[name])
                wrong = (cnt["H"] if t == "NH" else cnt["NH"] if t == "H" else 0) / n
                correct = (cnt[t] / n) if t in ("NH", "H") else None
                row["paths"][path] = {"primary": {k: round(c / n, 4) for k, c in cnt.items()},
                                      "decisive": round((cnt["NH"] + cnt["H"]) / n, 4),
                                      "correct": None if correct is None else round(correct, 4),
                                      "wrong_decisive": round(wrong, 4), "final": fin}
            res["rows"].append(row)
        res["mono"] = {q: {"S_true": s_true[q], **{p: {v: round(per_rep[q][p].count(v) / len(per_rep[q][p]), 4)
                                                      for v in set(per_rep[q][p])} for p in per_rep[q]}}
                       for q in ("M_low", "M_high")}
        out["conditions"].append(res)
    Path(sys.argv[3]).write_text(json.dumps(out, indent=1) + "\n")
    print(len(out["conditions"]), "conditions")


if __name__ == "__main__":
    main()
