#!/usr/bin/env python3
"""Render the v3.1 simulation tables from power-v4.json (Markdown to stdout)."""
import json
import sys

d = json.load(open(sys.argv[1]))
R = d["results"]


def get(set_, npl, scen):
    for r in R:
        if r["set"] == set_ and r["n_pl"] == npl and r["scenario"] == scen and not r.get("unreachable"):
            return r
    return None


def f(x, k=3):
    return "n/a" if x is None else f"{x:.{k}f}"


NAMES = {
    "null": "null (no effect)", "perturb_null": "task-specific perturbation N(0, 1), both cells",
    "reshuffle_10": "reshuffle of 10% of tasks, both cells", "reshuffle_30": "reshuffle of 30% of tasks, both cells",
    "generic_uniform_15": "uniform -15%, mirror and placebo alike", "generic_breaks_15": "complete breaks -15%, both alike",
    "mirror_uniform_10": "mirror uniform -10%, placebo none", "mirror_uniform_15": "mirror uniform -15%, placebo none",
    "mirror_uniform_20": "mirror uniform -20%, placebo none", "mirror_prop_15": "mirror proportional -15%, placebo none",
    "mirror_quarter_15": "mirror on a quarter of tasks -15%, placebo none", "mirror_breaks_15": "mirror complete breaks -15%, placebo none",
    "mirror_perturb_15": "mirror mixed-sign -15%, placebo none",
    "mirror_uniform_15_placebo_reshuffle_10": "mirror uniform -15%, placebo reshuffle 10%",
    "mirror_uniform_30_placebo_uniform_15": "mirror uniform -30%, placebo uniform -15%",
}
for set_, npl, title in (("census_all_106", 2, "Census of all 106 candidates, n = 4 in the 2x2, n_pl = 2 (cap 6.83 GPU-h)"),
                         ("admitted_phase0", 2, "The 105 tasks admitted under checker invariance, n_pl = 2"),
                         ("census_all_106", 4, "Census of 106, n_pl = 4 (cap 7.57 GPU-h)"),
                         ("confirm_only_62", 2, "K_min = 62 (the confirm split), n_pl = 2")):
    print(f"\n{title}:\n")
    print("| Scenario | kind | census true D (pp) | PRESENT_HARM | SMALL | P3 CONFIRMED | P3 FALSIFIED | sharp-null reject | PRESENT_FRAGILE | MIRROR_SPECIFIC (population) | MIRROR_SPECIFIC (census, reported) | NO_EXCESS | 95% coverage of census D |")
    print("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for scen in NAMES:
        r = get(set_, npl, scen)
        if r is None:
            continue
        print(f"| {NAMES[scen]} | {r['kind']} | {r['mean_census_true_D_pp']:.2f} | {f(r['present_harm'])} | {f(r['small'])} | "
              f"{f(r['p3_confirmed'])} | {f(r['p3_falsified'])} | {f(r['sharp_null_reject'])} | {f(r['present_fragile'])} | "
              f"{f(r['mirror_specific_pop'])} | {f(r['mirror_specific_census'])} | {f(r['no_excess_pop'])} | {f(r['cover95_census_D'])} |")
