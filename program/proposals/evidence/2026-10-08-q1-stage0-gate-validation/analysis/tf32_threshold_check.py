"""Synthesis check (wave 1, 2026-10-08) of the kill-shot cell's finding that the
primary audit's TF32-admissible threshold T reaches 1 or more on level-2 matmul and
convolution problems.

Input: job 713's re-pilot scoring journal (run directory
~/cotcodec-runs/stage0/q1-engineering-d31/runs/713/q1/repilot/journal.jsonl on the
host; synthesis read a byte copy taken earlier in this session, SHA-256 recorded in
the output; the host was not touched by synthesis). Job 713 scored S1-cal
(calibration-half) kernels only, so nothing here exposes an evaluation unit (D28).

Rows used: gates A1, A2, A3; inline arm (kernel ids without '.store'); per-draw rows
(config ids without 'aggregate'); draws the audit validity gate admitted
(details.admissible is not False); every attempt. T and e are read from
details['tf32-admissible'] and details['strict-fp32'].

Why T >= 1 matters (registration 6.1): e(x) = max_i |x_i - r_i| / (|r_i| + 1e-3 ||r||_inf),
so e(0) < 1 for any finite reference and e(-r) < 2: with T >= 1 an all-zeros output
passes that draw's numerical check, and with T >= 2 a negated one does.
"""

import collections
import hashlib
import json
import re
import sys

HOST_PATH = "~/cotcodec-runs/stage0/q1-engineering-d31/runs/713/q1/repilot/journal.jsonl"
path = sys.argv[1]
with open(path, "rb") as handle:
    raw = handle.read()
rows = [json.loads(line) for line in raw.decode().splitlines() if line.strip()]


def prob(kid):
    return re.search(r"(L[12]-\d+)", kid).group(1)


per = collections.defaultdict(list)
for r in rows:
    if r.get("gate") not in ("A1", "A2", "A3"):
        continue
    kid = r["kernel_id"]
    if kid.endswith(".store") or "aggregate" in r.get("config_id", ""):
        continue
    d = r.get("details") or {}
    if d.get("admissible") is False:
        continue
    ta, ts = d.get("tf32-admissible") or {}, d.get("strict-fp32") or {}
    if ta.get("T") is None:
        continue
    per[prob(kid)].append((r["gate"], ta["T"], ts.get("T")))

table = {}
for p in sorted(per):
    xs = per[p]
    g = {}
    for gate in ("A1", "A2", "A3"):
        ts = [t for gg, t, _ in xs if gg == gate]
        if ts:
            g[gate] = {
                "draw_rows": len(ts),
                "T_min": round(min(ts), 4),
                "T_max": round(max(ts), 4),
                "rows_T_ge_1": sum(t >= 1 for t in ts),
                "rows_T_ge_2": sum(t >= 2 for t in ts),
            }
    table[p] = {
        "draw_rows": len(xs),
        "rows_T_ge_1": sum(t >= 1 for _, t, _ in xs),
        "rows_T_ge_2": sum(t >= 2 for _, t, _ in xs),
        "strict_fp32_T_max": round(max(s for _, _, s in xs if s is not None), 5),
        "by_channel": g,
    }

mut = []
for r in rows:
    kid = r["kernel_id"]
    if (
        "L2-95" in kid
        and "plus2minus" in kid
        and r["gate"] in ("a", "a_1e-3", "A1", "A2", "A3", "A4")
    ):
        d = r.get("details") or {}
        ta = d.get("tf32-admissible") or {}
        mut.append(
            {
                "arm": "store" if kid.endswith(".store") else "inline",
                "gate": r["gate"],
                "config_id": r.get("config_id"),
                "tf32_policy": r.get("tf32_policy"),
                "verdict": r["verdict"],
                "admissible": d.get("admissible"),
                "T_tf32_admissible": ta.get("T"),
                "e_tf32_admissible": ta.get("e"),
                "reason": (d.get("reason") or "")[:80],
            }
        )

ident = {}
for r in rows:
    kid = r["kernel_id"]
    if (
        kid.startswith("ctl-identity")
        and not kid.endswith(".store")
        and r["gate"] in ("A1", "A2", "A3")
        and "aggregate" in r.get("config_id", "")
    ):
        ident.setdefault(prob(kid), {})[f"{r['gate']}/{r.get('tf32_policy')}"] = r["verdict"]

print(
    json.dumps(
        {
            "input": {
                "path_on_host": HOST_PATH,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw),
                "rows": len(rows),
            },
            "tf32_admissible_threshold_by_problem": table,
            "l2_95_plus2minus_rows": mut,
            "identity_control_audit_aggregates": ident,
        },
        indent=1,
    )
)
