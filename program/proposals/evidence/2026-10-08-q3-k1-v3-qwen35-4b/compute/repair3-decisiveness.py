"""K1 v3 repair under D52: the screen's chance of a verdict, from S3 (repair3-decision-sim.json).

P(GO or NEGATIVE) = P(pre-step passes) x P(H2 gate passes) x P(GO or NEGATIVE | both gates).
- P(H2): the second repair's predictive range at 2,000 cells, 0.42 (skeptical prior) to 0.57 (flat)
  (repair-h2-predictive.json); the H2 gate is unchanged by this repair.
- P(pre-step): synthesis judgement, 0.65 to 0.80 (the second repair's 0.6 to 0.8, with the mask
  coverage item and the LF and PRE coverage fallbacks now settled by the development facts, and
  the new item 9 adding a small risk).
- P(verdict | gates): S3 rows under the registered rules (variant `repair3`), averaged over a stated
  prior on the truth (no excess 0.5, a gray-zone input excess of 5 points 0.3, a GO-sized input
  excess of 12 or 15 points 0.2, split evenly), at masked headroom H 20, 30 or 40. Seeds: three when
  the seed SD of xi is 1; five (the seed top-up) at seed SD 2 or 3, where the sealed development
  seed read's 80 percent upper bound exceeds the top-up threshold with high probability.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
S3 = json.load(open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "repair3-decision-sim.json")))
RULE = os.environ.get("RULE", "repair3")


def row(table, H, s, g, n_seeds=3):
    for r in S3["rows"]:
        sc = r["scenario"]
        if (r["table"] == table and sc.get("H") == H and sc.get("seed_sd") == s and sc.get("gamma_u", 0.0) == g
                and r["n_seeds"] == n_seeds and "model" not in sc and "b_lit" not in sc):
            return r["result"][RULE]
    return None


PRIOR = [(0.0, 0.5), (5.0, 0.3), (12.0, 0.1), (15.0, 0.1)]
out = {"rule": RULE, "prior": PRIOR, "conditional": {}, "unconditional": {}}
for s in (1.0, 2.0, 3.0):
    for H in (20.0, 30.0, 40.0):
        for label, (table, n) in {"3 seeds": ("A", 3), "5 seeds (top-up)": ("D5", 5)}.items():
            vals = []
            for g, w in PRIOR:
                r = row(table, H, s, g, n)
                if r is None:
                    vals = None
                    break
                vals.append((w, r["P_GO"] + r["P_NEG"], r["P_GO"], r["P_NEG"]))
            if vals is None:
                continue
            out["conditional"][f"s{s}|H{H}|{label}"] = dict(
                P_verdict=round(sum(w * p for w, p, _, _ in vals), 3),
                P_GO=round(sum(w * p for w, _, p, _ in vals), 3), P_NEG=round(sum(w * p for w, _, _, p in vals), 3))
# registered policy: three seeds at seed SD 1, the top-up at seed SD 2 and 3 (POLICY=three: never)
cond = {}
POLICY = os.environ.get("POLICY", "topup")
out["policy"] = POLICY
for s, label in ((1.0, "3 seeds"), (2.0, "5 seeds (top-up)" if POLICY == "topup" else "3 seeds"),
                 (3.0, "5 seeds (top-up)" if POLICY == "topup" else "3 seeds")):
    xs = [out["conditional"][f"s{s}|H{H}|{label}"]["P_verdict"] for H in (20.0, 30.0, 40.0)
          if f"s{s}|H{H}|{label}" in out["conditional"]]
    cond[s] = (min(xs), max(xs)) if xs else None
for s, rng in cond.items():
    if rng is None:
        continue
    lo = 0.65 * 0.42 * rng[0]
    hi = 0.80 * 0.57 * rng[1]
    out["unconditional"][f"seed SD {s}"] = dict(given_gates=[round(x, 3) for x in rng], unconditional=[round(lo, 3), round(hi, 3)])
gates = (0.65 * 0.42, 0.80 * 0.57)
out["gates_pass"] = [round(g, 3) for g in gates]
print(json.dumps(out, indent=1))
