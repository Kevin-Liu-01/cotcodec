#!/usr/bin/env python3
"""Render the simulation tables of the S2 v3 proposal and registration from power-v3.json.

Usage: python3 tables-v3.py <power-v3.json>   (prints Markdown: MAIN, then BYK)
"""
import json
import sys

d = json.load(open(sys.argv[1]))
R = d["results"]


def row(set_, n, struct, tgt=None, q=None):
    for r in R:
        if r["set"] == set_ and r["n"] == n and r["struct"] == struct and not r.get("unreachable"):
            if struct == "reshuffle" and r["reshuffle_q"] == q:
                return r
            if struct != "reshuffle" and r["target_RD"] == tgt:
                return r
    return None


def f(x, k=2):
    return "n/a" if x is None else f"{x:.{k}f}"


out = []
out.append("Census of all 106 pool tasks, n = 4 (cap 6.10 GPU-h). Nulls:\n")
out.append("| Null structure | census true D (pp) | PRESENT_HARM | PRESENT_BENEFIT | SMALL | INCONCLUSIVE | 95% coverage of the census D | SMALL_POP (population, with guard) | v2's rule: SMALL unqualified |")
out.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
for label, s, t, q in (("homogeneous (no effect)", "logit", 0.0, None), ("task-specific logit perturbation N(0, 1)", "perturb", 0.0, None),
                       ("reshuffle of 10% of tasks", "reshuffle", None, 0.1), ("reshuffle of 30% of tasks", "reshuffle", None, 0.3)):
    r = row("census_all_106", 4, s, t, q)
    out.append(f"| {label} | {f(r['mean_census_true_D_pp'])} | {f(r['present_harm'],3)} | {f(r['present_benefit'],3)} | {f(r['small'],3)} | "
               f"{f(r['inconclusive'],3)} | {f(r['cover95_census_D'],3)} | {f(r['pop_small_with_guard'],3)} | {f(r['v2_rule_small_unqualified'],3)} |")
out.append("\nAlternatives (relative layout effect RD on the census; the absolute census D is about 0.29 x RD):\n")
out.append("| Structure | RD | census true D (pp) | PRESENT_HARM | SMALL | SMALL when the census truth is beyond a margin | 95% coverage | SMALL_POP | v2's rule: SMALL unqualified |")
out.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
names = {"logit": "uniform logit shift", "prop": "proportional, every task", "conc25": "proportional, a quarter of tasks",
         "flip": "complete breaks", "perturb": "mixed-sign perturbation, mean shifted"}
for s in ("logit", "prop", "conc25", "flip", "perturb"):
    for t in (-0.10, -0.15, -0.20, -0.30):
        r = row("census_all_106", 4, s, t)
        if r is None:
            continue
        out.append(f"| {names[s]} | {t:+.2f} | {f(r['mean_census_true_D_pp'])} | {f(r['present_harm'],3)} | {f(r['small'],3)} | "
                   f"{f(r['false_small_given_census_beyond_margin'],3)} | {f(r['cover95_census_D'],3)} | {f(r['pop_small_with_guard'],3)} | "
                   f"{f(r['v2_rule_small_unqualified'],3)} |")
main = "\n".join(out)

out = ["By task count and episodes (census frame; 'at -15%' is the range over the five alternative structures):\n",
       "| Task set | K | n | cap GPU-h | census SE of D (pp, null) | SMALL, homogeneous null | SMALL, perturbation null | SMALL, 10% reshuffle | PRESENT_HARM at RD -15% | PRESENT_HARM at RD -20% | max SMALL when beyond a margin | SMALL_POP, homogeneous null |",
       "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
for set_, n in (("census_all_106", 4), ("census_all_106", 6), ("census_all_106", 8), ("without_dev_89", 4), ("confirm_only_62", 4),
                ("confirm_only_62", 8), ("v2_K26_like_confirm_informative", 16)):
    r0 = row(set_, n, "logit", 0.0)
    rp = row(set_, n, "perturb", 0.0)
    rr = row(set_, n, "reshuffle", None, 0.1)
    p15 = [row(set_, n, s, -0.15)["present_harm"] for s in ("logit", "prop", "conc25", "flip", "perturb")]
    p20 = [row(set_, n, s, -0.20)["present_harm"] for s in ("logit", "prop", "conc25", "flip")]
    fs = [r["false_small_given_census_beyond_margin"] for r in R if r["set"] == set_ and r["n"] == n
          and r.get("false_small_given_census_beyond_margin") is not None]
    out.append(f"| {set_} | {r0['K']} | {n} | {r0['cost']['cap_gpu_h_incl_overlay']:.2f} | {f(r0['mean_se_census_D_pp'])} | {f(r0['small'],3)} | "
               f"{f(rp['small'],3)} | {f(rr['small'],3)} | {min(p15):.3f}-{max(p15):.3f} | {min(p20):.3f}-{max(p20):.3f} | {max(fs):.3f} | "
               f"{f(r0['pop_small_with_guard'],3)} |")
out.append("\nThe K = 26 row is v2's kind of set (26 confirm tasks solved at least once in S1a), shown under v3's census rule for comparison: there the "
           "population-frame SMALL with the concentration guard is 0.001 and v2's own rule 0.002 at the null, and a direction-free 10% reshuffle "
           "gives PRESENT_HARM 0.46 because the selected tasks regress (census true D -2.9 pp): the selection effect the census avoids. Its RD targets "
           "are on a set with mean success near 0.6, so its absolute effects are about twice the census's. n = 6 and 8 at K = 106 cap above 8 GPU-h "
           "(9.03 and 11.97) and are shown only to size the value of reruns.")
byk = "\n".join(out)
print("MAIN\n" + main + "\nBYK\n" + byk)
