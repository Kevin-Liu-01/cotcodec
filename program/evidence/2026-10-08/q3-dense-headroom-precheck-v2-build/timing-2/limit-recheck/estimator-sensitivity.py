"""How the 4B limit depends on the estimator: the registered one against the first pass's line fit.

Standard library only; reads Slurm 810's committed receipt and analysis.json (the lane's mean
token length per stage comes from analysis.json, which the registered analysis computed from the
development artifact inside the image):

    python estimator-sensitivity.py [TIMING_810_DIR]   (default ../timing-810)

Prints a report and writes estimator-sensitivity.json next to this script. Rows:
- registered: per stage, the mean of the first evaluations without one-off compiles (a unit over
  five times its stage's median), times max(1, lane mean tokens / measured mean tokens), times the
  stage's units; plus the compile allowance (observed rate x all units x the larger compile's
  extra cost) and a 5 s statistics bound (analyse_timing2.py).
- line fit, compiles as registered: the first pass's per-stage least-squares line in tokens
  (slope clamped at 0, through the means) evaluated at the lane's mean length, the larger of that
  and the stage mean, but fitted on the units without compiles and with the same allowance.
- first pass as run: the line fitted on every first evaluation, compiles included, the larger of
  that and the stage's mean with compiles, no allowance (analyse_timing2-first-pass.py).
- larger of the first two in every stage: a bound on the choice between them, not an estimator
  either pass proposed; with the same allowance.
D36's rule: minutes = ceil((2 x (evaluation + statistics) + start-up) / 60) + 3.
"""
from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path

STAGES = ("A-main", "B-absent", "C-literal", "D-nohaystack")
OUTLIER_FACTOR = 5.0
STATS_BOUND_S = 5.0
LEAD_MIN = 3

here = Path(__file__).resolve().parent
timing = Path(sys.argv[1]) if len(sys.argv) > 1 else here.parent / "timing-810"
receipt = json.loads((timing / "dense-precheck_timing-receipt.json").read_text())
analysis = json.loads((timing / "analysis.json").read_text())
t = receipt["timing"]
check_unit = t["attention_backend_check"]["unit"]
cold = {s: [u for u in t["units"] if u["stage"] == s and u["unit"] != check_unit] for s in STAGES}
start_up = analysis["rule"]["start_up_s"]
allowance = analysis["compiles"]["allowance_s"]


def line(units: list[dict]) -> tuple[float, float]:
    """Least-squares slope (clamped at 0) and the intercept through the means, as the first pass."""

    x = [float(u["context_tokens"]) for u in units]
    y = [float(u["seconds"]) for u in units]
    mx, my = statistics.fmean(x), statistics.fmean(y)
    sxx = sum((xi - mx) ** 2 for xi in x)
    slope = max(0.0, sum((xi - mx) * (yi - my) for xi, yi in zip(x, y, strict=True)) / sxx) if sxx else 0.0
    return slope, my - slope * mx


def minutes(evaluation_s: float) -> tuple[float, int]:
    before_rounding = (2.0 * (evaluation_s + STATS_BOUND_S) + start_up) / 60.0
    return before_rounding, math.ceil(before_rounding) + LEAD_MIN


rows: dict[str, dict] = {}
estimates = {"registered": 0.0, "line_fit_compiles_as_registered": 0.0,
             "larger_of_the_two_per_stage": 0.0, "first_pass_as_run": 0.0}
for stage in STAGES:
    units = cold[stage]
    median = statistics.median(u["seconds"] for u in units)
    regular = [u for u in units if u["seconds"] <= OUTLIER_FACTOR * median]
    lane_tokens = analysis["per_stage"][stage]["lane_tokens_mean"]
    n = analysis["per_stage"][stage]["lane_units"]
    mean_regular = statistics.fmean(u["seconds"] for u in regular)
    tokens_regular = statistics.fmean(u["context_tokens"] for u in regular)
    proportional = mean_regular * max(1.0, lane_tokens / tokens_regular)
    slope, intercept = line(regular)
    fit = max(mean_regular, intercept + slope * lane_tokens)
    slope_all, intercept_all = line(units)
    first = max(statistics.fmean(u["seconds"] for u in units), intercept_all + slope_all * lane_tokens)
    estimates["registered"] += proportional * n
    estimates["line_fit_compiles_as_registered"] += fit * n
    estimates["larger_of_the_two_per_stage"] += max(proportional, fit) * n
    estimates["first_pass_as_run"] += first * n
    rows[stage] = {
        "lane_units": n, "lane_tokens_mean": lane_tokens, "regular_n": len(regular),
        "regular_tokens_min": min(u["context_tokens"] for u in regular),
        "regular_tokens_max": max(u["context_tokens"] for u in regular),
        "regular_mean_s": mean_regular, "regular_tokens_mean": tokens_regular,
        "registered_unit_s": proportional,
        "line_slope_ms_per_token": slope * 1e3, "line_unit_s": fit,
        "line_minus_registered_stage_s": (fit - proportional) * n,
        "first_pass_slope_ms_per_token": slope_all * 1e3, "first_pass_unit_s": first,
    }
    print(f"{stage:13s} lane {n:3d} units at {lane_tokens:7.1f} tokens; measured {len(regular):2d} "
          f"units {rows[stage]['regular_tokens_min']:,}-{rows[stage]['regular_tokens_max']:,} tokens, "
          f"mean {mean_regular:.4f} s at {tokens_regular:7.1f}")
    print(f"{'':13s} registered {proportional:.4f} s/unit; line fit {slope * 1e3:.4f} ms/token "
          f"-> {fit:.4f} s/unit ({(fit - proportional) * n:+.1f} s for the stage); "
          f"first pass {slope_all * 1e3:.4f} ms/token -> {first:.4f} s/unit")

# B-absent, the only stage with measured units at the lane's long contexts: where proportional scaling
# lands against the longest measured units, and how the unit's parts grow with length.
b_regular = [u for u in cold["B-absent"]
             if u["seconds"] <= OUTLIER_FACTOR * statistics.median(v["seconds"] for v in cold["B-absent"])]
groups = {"short (< 5,000 tokens)": [u for u in b_regular if u["context_tokens"] < 5000],
          "long (> 8,000 tokens)": [u for u in b_regular if u["context_tokens"] > 8000]}
b_absent = {}
for name, group in groups.items():
    b_absent[name] = {
        "n": len(group), "tokens_mean": statistics.fmean(u["context_tokens"] for u in group),
        "unit_s": statistics.fmean(u["seconds"] for u in group),
        "parts_s": {k: statistics.fmean(u["parts"][k]["wall_s"] for u in group)
                    for k in group[0]["parts"]},
        "chunks": sorted({f"{u['phase']}:{u['chunk']}" for u in group})}
    g = b_absent[name]
    print(f"B-absent {name}: {g['n']} units, {g['tokens_mean']:.0f} tokens, unit {g['unit_s']:.3f} s, "
          f"prefill {g['parts_s']['prefill_forward']:.3f} s, option forwards "
          f"{g['parts_s']['mc_option_forward']:.3f} s, chunks {g['chunks']}")
row = rows["B-absent"]
b_absent["proportional_at_long_mean_s"] = row["regular_mean_s"] * (
    b_absent["long (> 8,000 tokens)"]["tokens_mean"] / row["regular_tokens_mean"])
print(f"B-absent proportional scaling at the long units' length: "
      f"{b_absent['proportional_at_long_mean_s']:.3f} s against "
      f"{b_absent['long (> 8,000 tokens)']['unit_s']:.3f} s measured")

out = {"rows": rows, "b_absent_length": b_absent, "start_up_s": start_up,
       "compile_allowance_s": allowance, "statistics_bound_s": STATS_BOUND_S, "estimators": {}}
for name, stages_s in estimates.items():
    evaluation = stages_s + (0.0 if name == "first_pass_as_run" else allowance)
    raw, mins = minutes(evaluation)
    out["estimators"][name] = {"stages_s": stages_s, "evaluation_s": evaluation,
                               "evaluation_and_statistics_s": evaluation + STATS_BOUND_S,
                               "minutes_before_rounding_and_lead": raw, "minutes": mins,
                               "one_pass_with_start_up_min": (evaluation + STATS_BOUND_S + start_up) / 60}
    print(f"{name:34s} stages {stages_s:7.1f} s, evaluation and statistics "
          f"{evaluation + STATS_BOUND_S:7.1f} s, (2 x that + {start_up:.1f}) / 60 = {raw:6.2f} "
          f"-> {mins} minutes; one pass with start-up {(evaluation + STATS_BOUND_S + start_up) / 60:.1f} min")
assert out["estimators"]["registered"]["minutes"] == analysis["rule"]["minutes"]
(here / "estimator-sensitivity.json").write_text(json.dumps(out, indent=1) + "\n")
