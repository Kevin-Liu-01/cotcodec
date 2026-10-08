"""Synthesis estimate (wave 1, 2026-10-08): where the registered 8.0 GPU-h stop of
q1-stage0-trim/2 falls under the D37 validation job's projection rows.

Approximation, labelled as such in the proposal: the P1/P2/P3 split of scoring
GPU-hours is taken from the D31 cost card's exec/1 store-per-job scenario
(program/evidence/2026-10-07/q1-engineering-d31/cost-card-d31.json,
trimmed[name=trim2-store-per-job-paired-concurrency].gpu_hours_by_priority) and
applied to the exec/2 rows of the validation job
(branch stage0/q1-exec2-validation@13f3180,
program/evidence/2026-10-08/q1-exec2-validation/exec2-validation.json, projection.rows).
Under exec/2 the large FRR-core problems that close P1 get more units, so the
true P1 share is probably larger than this split; the estimate is optimistic.
"""

import json

SPLIT = {"P1": 1.961, "P2": 1.517, "P3": 0.522}  # exec/1 store per job, GPU-h
FIXED = 4.294  # validation job's fixed part, includes 1.338 spent and the 1.5 GPU-h reserve
CAP = 8.0
ROWS = {  # P3 scoring central, GPU-h (exec2-validation.json projection.rows)
    "A model, no store": 6.278,
    "B model, store": 6.472,
    "C primary (B x R=2.425)": 15.696,
    "C at R 2.5% (1.140)": 7.381,
    "C at R 97.5% (4.837)": 31.308,
    "D per-gate scales": 13.843,
    "E store-independent ratio": 21.817,
}
tot = sum(SPLIT.values())
room = CAP - FIXED
out = {
    "room_for_scoring_gpu_h": round(room, 3),
    "split_share": {k: round(v / tot, 3) for k, v in SPLIT.items()},
    "rows": {},
}
for name, p3 in ROWS.items():
    p = {k: p3 * v / tot for k, v in SPLIT.items()}
    if room < p["P1"]:
        where = f"P1, {100 * room / p['P1']:.0f}% through"
    elif room < p["P1"] + p["P2"]:
        where = f"P2, {100 * (room - p['P1']) / p['P2']:.0f}% through"
    elif room < p3:
        where = f"P3, {100 * (room - p['P1'] - p['P2']) / p['P3']:.0f}% through"
    else:
        where = "after P3"
    out["rows"][name] = {
        "P1": round(p["P1"], 2),
        "P2": round(p["P2"], 2),
        "P3": round(p["P3"], 2),
        "stop_falls_in": where,
    }
print(json.dumps(out, indent=1))
