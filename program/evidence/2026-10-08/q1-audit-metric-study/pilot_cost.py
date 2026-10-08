"""Q1 audit-metric study: cost of the proposed S1-cal-only GPU validation pilot (revision 2).

Revision 2 fixes the first pass's cost model, which the replication found too low:

* every item is charged with the harness's own ``cost_card.charge`` (its share of the GPU
  while it ran, a sweep over concurrent items), not ``wall x units / 12``;
* every attempt counts. L2/59's A2/A3 items ran out of memory under exec/1 and were
  re-run alone (attempt 2, exclusive); the first pass priced the failed shared attempt;
* problems with only job 518's calibration A1 items (L1/15, L1/47, L2/52, L2/60) get their
  A2/A3 items as the A1 item times the largest A2-or-A3 over A1 ratio measured on the
  re-pilot problems whose items all ran in the same sharing regime (L2/59 is excluded:
  its A1 item ran shared, its A2/A3 items alone after running out of memory), and
  reference items as their consumer item times the largest reference over consumer
  ratio measured there (stated assumptions, no free choice);
* a problem never measured at all takes the measured costs of a problem of its size
  and op class (L2/56 and L2/18, linear layers with 0.017-0.034 GB inputs and a
  reduction epilogue: L2/95);
* the first pass's own stated fallback ("largest measured item of any problem") is
  reported as an upper bound.

Two plans are priced: the first pass's plan (to check the replication's figure) and the
revised plan of README section 6 (correct controls that differ from the yardstick, two
small reduction problems; and the same plus L1/47). Sources: job 713 (exec/1) and job 518's calibration phase, charged here from
the journals; job 752 (exec/2) from ``exec2-validation.json``, which charged it with the
same function. Job 752's rows on L1/1 (a problem hosting an S2 evaluation unit) are not
used, and no row of an evaluation unit is read: 518's calibration phase ran alone (phase
offsets 433.6-531.0 s of the job) and holds only S1-cal calibration substrates.

Usage: python pilot_cost.py --journals <dir with j518/ j713/>
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO))

from harness.q1 import cost_card as cc  # noqa: E402

CHANNELS = ("A1", "A2", "A3")
REFS = ("ref_A1", "ref_A2", "ref_A3")
REPILOT = ["L1/10", "L1/18", "L2/59", "L2/95", "L2/77", "L2/100", "L2/87", "L2/46"]
CALIBRATION_ONLY = ["L1/15", "L2/52", "L2/60", "L1/47"]
SIZE_CLASS_ANALOG = {"L2/56": "L2/95", "L2/18": "L2/95"}
MUTANT = {"L1/10", "L1/18", "L2/59", "L2/95", "L2/77", "L2/100", "L2/87", "L2/46"}
MATMUL = {"L1/10", "L1/18", "L1/15", "L2/59", "L2/95"}
CONV = {"L2/77", "L2/100", "L2/87", "L2/46", "L2/52", "L2/60"}
REDUCTION = {"L1/47", "L2/56", "L2/18"}

#: kernels per problem in each plan (consumer kernels; references are separate items)
PLANS: dict[str, dict[str, list[str]]] = {
    "first_pass": {
        p: ["substrate", "identity", "decoy-bundle"] + (["mutant"] if p in MUTANT else []) + (["tl.dot-control"] if p in MATMUL else [])
        for p in REPILOT + ["L1/15", "L2/52", "L2/60"]
    },
    "revised_plus_L1_47": {
        **{
            p: ["substrate", "identity", "decoy-bundle"]
            + (["inductor-triton-template"] if p in MATMUL else ["cudnn-benchmark"])
            + (["mutant"] if p in MUTANT else [])
            for p in REPILOT + ["L1/15", "L2/52", "L2/60"]
        },
        # reduction class: Inductor default and a reduction-order variant (compiler output,
        # D3), the identity control and the decoy bundle; L2/56 and L2/18 need their S1
        # substrates compiled
        **{p: ["substrate", "identity", "decoy-bundle", "inductor-reduction-variant"] for p in sorted(REDUCTION)},
    },
}
#: the recommended plan: L1/47 (8.6 GB inputs, items run alone) is covered on the CPU instead
PLANS["revised"] = {p: k for p, k in PLANS["revised_plus_L1_47"].items() if p != "L1/47"}


def prob(kid: str) -> str:
    m = re.search(r"(L[12])-(\d+)", kid)
    return f"{m.group(1)}/{m.group(2)}"


def charged(job_dir: Path, phase: str, files: list[str]) -> list[dict[str, Any]]:
    """Charge one job's items with ``cost_card.charge`` (via ``load_job``)."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / phase).mkdir()
        (root / "phases.json").write_text("{}")
        for f in files:
            src = job_dir / f
            if src.exists():
                dest = {"calibration-journal.jsonl": "journal.jsonl"}.get(f, f)
                shutil.copy(src, root / phase / dest)
        return cc.load_job(root)["items"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--journals", required=True)
    ap.add_argument("--out", default=str(HERE / "pilot-cost.json"))
    a = ap.parse_args()
    root = Path(a.journals)
    consumer: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    reference: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    # job 713 (exec/1): every attempt, both arms, charged
    for it in charged(root / "j713", "repilot", ["journal.jsonl", "references.jsonl", "items.jsonl"]):
        if it["gpu_seconds"] is None:
            continue
        p = prob(it["kernel_id"])
        rec = {"job": "713", "gate": it["gate"], "attempt": it["attempt"], "final": it["final"], "exclusive": it["exclusive"], "gpu_s": it["gpu_seconds"], "kernel": it["kernel_id"]}
        if it["gate"] in CHANNELS:
            consumer[p].append(rec)
        elif it["gate"] in REFS:
            reference[p].append(rec)
    # job 518 calibration phase (S1-cal calibration substrates only, A1 only)
    for it in charged(root / "j518", "calibration", ["calibration-journal.jsonl"]):
        if it["gpu_seconds"] is None or it["gate"] not in CHANNELS:
            continue
        consumer[prob(it["kernel_id"])].append({"job": "518", "gate": it["gate"], "attempt": it["attempt"], "final": it["final"], "exclusive": it["exclusive"], "gpu_s": it["gpu_seconds"], "kernel": it["kernel_id"]})
    # job 752 (exec/2), charged in exec2-validation.json
    ev = json.loads((REPO / "program/evidence/2026-10-08/q1-exec2-validation/exec2-validation.json").read_text())
    for it in ev["item_costs"]:
        p = prob(it["kernel_id"])
        if p == "L1/1":
            continue
        rec = {"job": "752", "gate": it["gate"], "attempt": it.get("attempt"), "final": True, "exclusive": it.get("exclusive"), "gpu_s": it["measured"], "kernel": it["kernel_id"]}
        if it["reference"] and it["gate"] in REFS:
            reference[p].append(rec)
        elif it["gate"] in CHANNELS:
            consumer[p].append(rec)

    def mx(xs: list[dict[str, Any]], gates: tuple[str, ...]) -> float | None:
        v = [x["gpu_s"] for x in xs if x["gate"] in gates]
        return max(v) if v else None

    # ratios measured on the re-pilot problems (used only for the calibration-only problems)
    same_regime = [p for p in REPILOT if len({x["exclusive"] for x in consumer[p] if x["gate"] in CHANNELS}) == 1]
    a23_over_a1 = max(mx(consumer[p], ("A2", "A3")) / mx(consumer[p], ("A1",)) for p in same_regime if mx(consumer[p], ("A1",)) and mx(consumer[p], ("A2", "A3")))
    ref_over_cons = max(mx(reference[p], REFS) / mx(consumer[p], CHANNELS) for p in REPILOT if mx(reference[p], REFS) and mx(consumer[p], CHANNELS))
    any_max = max(x["gpu_s"] for v in consumer.values() for x in v if x["gate"] in CHANNELS)

    per_item: dict[str, dict[str, Any]] = {}
    for p in REPILOT + CALIBRATION_ONLY + list(SIZE_CLASS_ANALOG):
        src = SIZE_CLASS_ANALOG.get(p, p)
        cons, refs = consumer.get(src, []), reference.get(src, [])
        a1 = mx(cons, ("A1",))
        a23 = mx(cons, ("A2", "A3"))
        basis = "measured (713, 752)"
        if a23 is None and a1 is not None:
            a23 = a1 * a23_over_a1
            basis = f"A1 measured (job 518 calibration); A2/A3 = A1 x {a23_over_a1:.2f}"
        r = mx(refs, REFS)
        if r is None:
            r = max(a1 or 0, a23 or 0) * ref_over_cons
            basis += f"; reference items = consumer x {ref_over_cons:.2f}"
        if p in SIZE_CLASS_ANALOG:
            basis = f"never measured: the costs of {src} (same size class), " + basis
        per_item[p] = {
            "A1_item_gpu_s": a1, "A2_A3_item_gpu_s": a23, "reference_item_gpu_s": r, "basis": basis,
            "measured_items": len(cons), "measured_reference_items": len(refs),
            "alone_run_items": sum(1 for x in cons if x["exclusive"]),
        }

    def price(plan: dict[str, list[str]], item: dict[str, dict[str, Any]], upper: bool = False) -> dict[str, Any]:
        per = {}
        for p, kernels in plan.items():
            c = item[p]
            a1, a23, r = c["A1_item_gpu_s"], c["A2_A3_item_gpu_s"], c["reference_item_gpu_s"]
            if upper:
                a1 = a23 = any_max
            # every consumer item at the problem's largest item (the first pass's stated rule;
            # under exec/2 a large problem's A1 item gets as many units as its A2/A3 items)
            gpu_s = len(kernels) * 3 * max(a1, a23) + 3 * r
            per[p] = {"kernels": kernels, "consumer_items": 3 * len(kernels), "reference_items": 3, "gpu_s": round(gpu_s, 1)}
        tot = sum(v["gpu_s"] for v in per.values())
        rep = sum(v["gpu_s"] for p, v in per.items() if p in REPILOT)
        return {"per_problem": per, "total_gpu_h": tot / 3600, "repilot_8_problems_gpu_h": rep / 3600, "total_with_2x_margin_gpu_h": 2 * tot / 3600,
                "kernels": sum(len(v["kernels"]) for v in per.values()), "consumer_items": sum(v["consumer_items"] for v in per.values()),
                "reference_items": sum(v["reference_items"] for v in per.values())}

    result = {
        "schema": "q1-audit-metric-study/pilot-cost/2",
        "method": "per problem: the largest charged A1 item and the largest charged A2/A3 item (any attempt, any arm, jobs 713 and 752), the largest charged ref_A1-A3 item; A2/A3 and reference items of calibration-only problems from the measured ratios; L1/94 from L1/47; GPU-s = kernels x 3 x max(A1 item, A2/A3 item) + 3 x reference item",
        "measured_ratios": {"A2_or_A3_over_A1_max_over_repilot_same_regime": a23_over_a1, "same_regime_problems": same_regime, "reference_over_consumer_max_over_repilot": ref_over_cons},
        "largest_measured_consumer_item_gpu_s": any_max,
        "per_problem_item_costs": per_item,
        "plans": {name: price(plan, per_item) for name, plan in PLANS.items()},
        "first_pass_stated_fallback_upper_bound": {
            "rule": "every consumer item of the calibration-only and unmeasured problems at the largest measured item of any problem",
            "first_pass_plan_gpu_h": None,
            "revised_plan_gpu_h": None,
        },
        "notes": [
            "first-pass figure: 0.28 GPU-h (0.20 for the 8 re-pilot problems), from wall x units / 12 on the failed shared attempt of L2/59's items",
            "job 752 measured 2.4x its exec/2 model; these per-item costs are measurements, so no model factor applies, but exec/2 runs large items with more units than 713's exec/1, so 713-measured items may be low",
            "the non-matmul problems have 4.3-8.6 GB native inputs and run alone; they dominate the revised plan",
        ],
    }
    for name, plan in PLANS.items():
        upper_items = {p: dict(v) for p, v in per_item.items()}
        for p in CALIBRATION_ONLY + list(SIZE_CLASS_ANALOG):
            upper_items[p]["A1_item_gpu_s"] = upper_items[p]["A2_A3_item_gpu_s"] = max(any_max, upper_items[p]["A2_A3_item_gpu_s"])
        result["first_pass_stated_fallback_upper_bound"][f"{name}_plan_gpu_h"] = price(plan, upper_items)["total_gpu_h"]
    Path(a.out).write_text(json.dumps(result, indent=1, sort_keys=True))
    for p, v in per_item.items():
        print(p, "A1 %.2f A2/A3 %.2f ref %.2f" % (v["A1_item_gpu_s"], v["A2_A3_item_gpu_s"], v["reference_item_gpu_s"]), "|", v["basis"])
    print("ratios", result["measured_ratios"], "largest item", round(any_max, 2))
    for name, pr in result["plans"].items():
        print(name, "kernels", pr["kernels"], "total %.3f GPU-h (8 re-pilot %.3f, 2x %.3f)" % (pr["total_gpu_h"], pr["repilot_8_problems_gpu_h"], pr["total_with_2x_margin_gpu_h"]))
    print("first-pass fallback upper bound", result["first_pass_stated_fallback_upper_bound"])


if __name__ == "__main__":
    main()
