"""Q1 audit-metric study: cost of the proposed S1-cal-only GPU validation pilot.

Per-item GPU-seconds of the audit channels A1-A3 and of their reference items, from
the stored journals of job 713 (exec/1, 12 one-unit items per GPU: GPU-s =
item wall seconds x units / 12) and the measured item costs of job 752 (exec/2,
``exec2-validation.json``). The pilot plan is the one the report proposes:
per problem one reference item per channel (A1, A2, A3) that also writes the
new yardstick (device TF32, emulated RNE and RZ TF32) and per-block error
statistics, and one consumer item per kernel and channel. Problems whose items
were never measured get the largest measured per-item cost of their size class
(a stated assumption). Output: ``pilot-cost.json``.

Usage: python pilot_cost.py --journals <dir with j713/ j752/>
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]

#: the pilot's problems (S1-cal, no S2 substrate) and kernels per problem
PROBLEMS = ["L1/10", "L1/18", "L1/15", "L2/59", "L2/95", "L2/77", "L2/100", "L2/87", "L2/46", "L2/52", "L2/60"]
MUTANT = {"L1/10", "L1/18", "L2/59", "L2/95", "L2/77", "L2/100", "L2/87", "L2/46"}
TL_DOT_CONTROL = {"L1/10", "L1/18", "L1/15", "L2/59", "L2/95"}
CHANNELS = ("A1", "A2", "A3")
#: L2/59's A1-A3 items were measured only under exec/1 (12 per GPU, where they ran out of
#: memory). Under exec/2 they take 7-11 of 12 units; job 752 measured its other gates at
#: 6 units, 5.3-16.0 GPU-s. Assumed: the largest of those scaled by 8/6 units.
OVERRIDE_CONSUMER = {"L2/59": 16.0 * 8 / 6}


def prob(kid: str) -> str:
    m = re.search(r"(L[12])-(\d+)", kid)
    return f"{m.group(1)}/{m.group(2)}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--journals", required=True)
    ap.add_argument("--out", default=str(HERE / "pilot-cost.json"))
    a = ap.parse_args()
    root = Path(a.journals)
    consumer = collections.defaultdict(list)
    reference = collections.defaultdict(list)
    seen = set()
    for line in (root / "j713/journal.jsonl").read_text().splitlines():
        r = json.loads(line)
        if r["gate"] not in CHANNELS or r["kernel_id"].endswith(".store"):
            continue
        d = r.get("details") or {}
        key = d.get("item_key")
        if key in seen or d.get("item_wall_seconds") is None:
            continue
        seen.add(key)
        consumer[(prob(r["kernel_id"]), "713-inline")].append(d["item_wall_seconds"] * d.get("item_units", 1) / 12)
    for line in (root / "j713/references.jsonl").read_text().splitlines():
        r = json.loads(line)
        d = r.get("details") or {}
        if r["gate"] in ("ref_A1", "ref_A2", "ref_A3") and d.get("item_wall_seconds") is not None:
            reference[(prob(r["kernel_id"]), "713")].append(d["item_wall_seconds"] * d.get("item_units", 1) / 12)
    ev = json.loads((REPO / "program/evidence/2026-10-08/q1-exec2-validation/exec2-validation.json").read_text())
    for it in ev["item_costs"]:
        p = prob(it["kernel_id"])
        if p == "L1/1":
            continue  # adversarial controls on a problem hosting an S2 evaluation unit: not used
        if it["reference"] and it["gate"] in ("ref_A1", "ref_A2", "ref_A3"):
            reference[(p, "752")].append(it["measured"])
        elif it["gate"] in CHANNELS:
            consumer[(p, "752-store")].append(it["measured"])
    per_problem = {}
    measured_max = max(max(v) for v in consumer.values())
    for p in PROBLEMS:
        cons = consumer.get((p, "713-inline"), []) + consumer.get((p, "752-store"), [])
        refs = reference.get((p, "713"), []) + reference.get((p, "752"), [])
        kernels = 3 + (p in MUTANT) + (p in TL_DOT_CONTROL)  # substrate, identity, decoy bundle
        c_item = OVERRIDE_CONSUMER.get(p, max(cons) if cons else measured_max)
        r_item = max(refs) if refs else 3 * c_item
        per_problem[p] = {
            "kernels": kernels,
            "consumer_items": kernels * len(CHANNELS),
            "consumer_item_gpu_s_measured": {"n": len(cons), "median": statistics.median(cons) if cons else None, "max": max(cons) if cons else None},
            "reference_item_gpu_s_measured": {"n": len(refs), "max": max(refs) if refs else None},
            "assumed_consumer_item_gpu_s": c_item,
            "assumed_reference_item_gpu_s": r_item,
            "unmeasured": not cons,
            "gpu_s": kernels * len(CHANNELS) * c_item + len(CHANNELS) * r_item,
        }
    total = sum(v["gpu_s"] for v in per_problem.values())
    result = {
        "schema": "q1-audit-metric-study/pilot-cost/1",
        "method": "per item: the largest measured A1-A3 item of the problem (713 inline, 752 store); reference items: the largest measured ref_A1-A3 item, else 3x the consumer item; unmeasured problems take the largest measured item of any problem",
        "per_problem": per_problem,
        "total_gpu_seconds": total,
        "total_gpu_hours": total / 3600,
        "with_2x_safety_gpu_hours": 2 * total / 3600,
        "minimal_variant": {
            "problems": [p for p in PROBLEMS if p not in ("L1/15", "L2/52", "L2/60")],
            "gpu_hours": sum(v["gpu_s"] for p, v in per_problem.items() if p not in ("L1/15", "L2/52", "L2/60")) / 3600,
            "what_it_drops": "the three 518-calibration problems (no measured A2/A3 items; L2/52 and L2/60 are the batch- and group-norm cases)",
        },
        "notes": [
            "job 752 measured 2.4x its exec/2 model; the per-item costs here are measured values, so no model factor is applied",
            "L2/59 (4.3 GB of parameters) dominates; L2/87, L2/100 and L2/46 consumer items under exec/2 were never measured (job 752 did not reach them)",
        ],
    }
    Path(a.out).write_text(json.dumps(result, indent=1, sort_keys=True))
    for p, v in per_problem.items():
        print(p, v["kernels"], "kernels", "item %.2f ref %.2f" % (v["assumed_consumer_item_gpu_s"], v["assumed_reference_item_gpu_s"]), "unmeasured" if v["unmeasured"] else "", "-> %.0f GPU-s" % v["gpu_s"])
    print("total %.0f GPU-s = %.3f GPU-h (x2 safety %.3f)" % (total, total / 3600, 2 * total / 3600))


if __name__ == "__main__":
    main()
