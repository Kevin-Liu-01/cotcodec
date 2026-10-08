#!/usr/bin/env python3
"""Post hoc (written after job 752's data were seen): two regime-split views of the
``q1-stage0-exec/2`` projection, and the cost decomposition by phase.

Not pre-specified. ``analyze_exec2_validation.py`` scales the model by one ratio R
over every final re-pilot item. Job 752 showed two regimes with different errors:
the one-unit items (12 per GPU) of four light problems ran while the adversarial
controls compiled their CUDA extension (CPU contention), and the multi-unit items
of L2/59 ran after that phase, 2 per GPU, with no contention. This script

1. splits the measured/model ratio by phase (overlapping the adversarial controls
   or after them) and by regime (12 per GPU or fewer);
2. projects row B of the pre-specified analysis with the model's per-item cost
   scaled by the 12-per-GPU ratio for items the policy runs 12 per GPU and by the
   fewer-than-12 ratio (one problem, L2/59) for the others, references by their
   ratio (F); problems of 0.6 GB or more, which the size model does not scale by
   concurrency, keep the model (so F is low for them);
3. the same with the 12-per-GPU items at the model (ratio 1) and only the
   multi-unit items scaled (G: what the L2/59 ratio alone implies).

    python posthoc_regime_split.py --analysis exec2-validation.json --run RUN/q1 \\
        --counts stage0-counts-v2.json --repilot-run RUN713/q1 --out posthoc-regime-split.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import analyze_exec2_validation as pre  # noqa: E402

from harness.q1 import cost_card as cc  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--counts", type=Path, required=True)
    parser.add_argument("--repilot-run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    analysis = json.loads(args.analysis.read_text())
    rows = analysis["item_costs"]
    items = cc.load_job(args.run)["items"]
    start = {i["item_key"]: i["start"] for i in items}
    t0 = min(v for v in start.values() if v is not None)
    adversarial_end = max(
        i["end"] for i in items if i["problem_id"] == pre.rule.ADVERSARIAL_PROBLEM
    )
    repilot = [r for r in rows if not r["adversarial"] and r["arm"] == "store"]

    def block(selected: list[dict[str, Any]]) -> dict[str, Any]:
        m = sum(r["measured"] for r in selected)
        p = sum(r["model_exec2_store"] for r in selected)
        return {
            "items": len(selected),
            "measured_gpu_seconds": round(m, 2),
            "model_gpu_seconds": round(p, 2),
            "measured_over_model": round(m / p, 3) if p else None,
            "problems": sorted({r["problem_id"] for r in selected}),
        }

    overlapping = [r for r in repilot if start[r["item_key"]] < adversarial_end]
    after = [r for r in repilot if start[r["item_key"]] >= adversarial_end]
    scoring = [r for r in repilot if not r["reference"]]
    refs = [r for r in repilot if r["reference"]]
    r12 = block([r for r in scoring if r["per_gpu"] >= 12])["measured_over_model"]
    rlow = block([r for r in scoring if r["per_gpu"] < 12])["measured_over_model"]
    rref = block(refs)["measured_over_model"]
    adv = [r for r in rows if r["adversarial"]]
    out: dict[str, Any] = {
        "label": "post hoc (written after the data were seen)",
        "adversarial_phase_ends_seconds": round(adversarial_end - t0, 1),
        "gpu_seconds_by_group": {
            "adversarial_controls_and_their_references": round(sum(r["measured"] for r in adv), 1),
            "repilot_scoring": round(sum(r["measured"] for r in scoring), 1),
            "repilot_references": round(sum(r["measured"] for r in refs), 1),
        },
        "by_phase": {
            "overlapping_the_adversarial_controls": block(overlapping),
            "after_the_adversarial_controls": block(after),
        },
        "ratios": {"12_per_gpu": r12, "fewer_than_12_per_gpu": rlow, "references": rref},
    }
    card = json.loads(pre.CARD.read_text())
    counts = json.loads(args.counts.read_text())
    old = cc.load_job(args.repilot_run)["items"]
    store = cc.fit_store_model(
        cc.repilot_pairs(old), cc.reference_items(old), ratio_mode="linear", consumers=pre.CONSUMERS
    )
    job_gpu_hours = analysis["gpu"]["gpu_hours"]
    original = cc.concurrency_multiplier
    views = []
    for label, high_ratio, low_ratio in (
        (f"F: 12-per-GPU items x{r12}, fewer x{rlow}, references x{rref}", r12, rlow),
        (f"G: 12-per-GPU items at the model, fewer x{rlow}, references x{rref}", 1.0, rlow),
    ):

        def scaled(units: int, factor: float, capacity: int = 12, _h=high_ratio, _l=low_ratio):
            k = max(1, int(capacity) // max(1, int(units)))
            return original(units, factor, capacity) * (_h if k >= 12 else _l)

        ref_store = cc.StoreModel(
            ratio_fits=store.ratio_fits,
            reference_fits={
                g: {**f, "alpha": f["alpha"] * rref, "beta": f["beta"] * rref}
                for g, f in store.reference_fits.items()
            },
        )
        cc.concurrency_multiplier = scaled
        try:
            projection = pre.projection(counts, card, ref_store, [], job_gpu_hours)
        finally:
            cc.concurrency_multiplier = original
        row = next(r for r in projection["rows"] if r["scenario"].startswith("B:"))
        views.append({**row, "scenario": label, "note": "post hoc; L2/59 alone sets the low ratio"})
    out["projection_rows"] = views
    args.out.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
