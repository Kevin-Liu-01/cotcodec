"""Descriptions added to the S1a results after their review (2026-10-10). Not code of record.

Reads only committed files: `../a1.jsonl` (the registered merge's record file), the four A1
GPU jobs' bridge samples (`../../q2-stage1-a1/<job>/gpu-<id>/bridge/gpu.jsonl`) and
`../report/guard.json` (for the labels). Standard library only, deterministic, and it
changes no estimand, rule or decision. It writes `post-review.json` beside itself, once.

1. Section 2 item 5's setup, evaluation and queue times, which the registered report and the
   section 15 assembler do not summarise: per size, over every final record (each one
   scored), the median and the nearest-rank 90th percentile (the ceil(0.9 n)-th smallest) of
   the episode record's `timings` fields and of the slot occupancy; per A1 job, the engine's
   request queue-time histogram (sum and count; section 7.3, `bridge.ENGINE_METRICS`) at its
   last sample, the largest number of waiting requests in any sample and the prefix-cache hit
   share.
2. The exact randomization p-values of the registered sign-flip tests on the primary set
   (base, raw verdicts). The registered tests are Monte Carlo (10,000 flips, PCG64 seed 42;
   `estimators.signflip_p`, p = (1 + #{T* >= T}) / (1 + nflip)); a task whose statistic is
   0 cannot change the sum when flipped, so the 2^n sign patterns of the n non-zero tasks
   give the exact p = #{T* >= T} / 2^n (on |T| for the two-sided session test).
3. DR3's common session share inputs: C_z, V_z = (D_b,z - D_w,z) / 2, the frozen code's
   rho_z (NaN when V_z <= 0) and the section 9 item 8 formula read literally (C_z / V_z
   truncated to [0, 1], undefined when V_z = 0).
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ANALYSIS = HERE.parent
A1 = ANALYSIS.parent / "q2-stage1-a1"
RECORDS = ANALYSIS / "a1.jsonl"
GUARD = ANALYSIS / "report" / "guard.json"
BRIDGES = {
    "A1-9B-S1": A1 / "a1-9b-s1" / "gpu-1047" / "bridge" / "gpu.jsonl",
    "A1-4B-S1": A1 / "a1-4b-s1" / "gpu-1050" / "bridge" / "gpu.jsonl",
    "A1-9B-S2": A1 / "a1-9b-s2" / "gpu-1053" / "bridge" / "gpu.jsonl",
    "A1-4B-S2": A1 / "a1-4b-s2" / "gpu-1064" / "bridge" / "gpu.jsonl",
}
OUT = HERE / "post-review.json"

SIZES = ("4B", "9B")
HARNESSES = ("H-OSW-fixed", "H-GA")
SESSIONS = ("S1", "S2")
BLOCKS = ("b1", "b2")
TIMING_FIELDS = ("boot_s", "setup_s", "warmup_s", "evaluate_s", "capture_s", "runner_s")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def nearest_rank(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[max(1, math.ceil(q * len(ordered))) - 1]


def summary(values: list[float]) -> dict[str, float | int]:
    return {
        "n": len(values),
        "median": round(statistics.median(values), 3),
        "p90": round(nearest_rank(values, 0.90), 3),
        "max": round(max(values), 3),
    }


def timings(records: list[dict]) -> dict:
    out: dict = {}
    for size in SIZES:
        rows = [r for r in records if r["size"] == size]
        cell = {f: summary([float(r["timings"][f]) for r in rows]) for f in TIMING_FIELDS}
        cell["slot_occupancy_s"] = summary([float(r["host"]["slot_occupancy_s"]) for r in rows])
        out[size] = cell
    return out


def engine_queue(records: list[dict]) -> dict:
    steps: dict[str, int] = {}
    for r in records:
        steps[r["job"]] = steps.get(r["job"], 0) + int(r["steps"])
    out = {}
    for job, path in BRIDGES.items():
        samples = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        engine = [s.get("engine") or {} for s in samples]
        count = max(float(e.get("vllm:request_queue_time_seconds_count") or 0.0) for e in engine)
        total = max(float(e.get("vllm:request_queue_time_seconds_sum") or 0.0) for e in engine)
        queries = max(float(e.get("vllm:prefix_cache_queries") or 0.0) for e in engine)
        hits = max(float(e.get("vllm:prefix_cache_hits") or 0.0) for e in engine)
        waiting = max(float(e.get("vllm:num_requests_waiting") or 0.0) for e in engine)
        out[job] = {
            "samples": len(samples),
            "requests": int(count),
            "episode_steps": steps[job],
            "queue_time_sum_s": round(total, 6),
            "queue_time_mean_ms": round(1000.0 * total / count, 4) if count else None,
            "max_requests_waiting_in_a_sample": int(waiting),
            "prefix_cache_hit_share": round(hits / queries, 4) if queries else None,
        }
    return out


def outcome_array(records: list[dict]) -> tuple[list[str], dict]:
    base = [r for r in records if r["extension_block"] is None]
    tasks = sorted({r["task_id"] for r in base})
    y: dict = {}
    for r in base:
        key = (r["size"], r["task_id"], r["harness"], r["session"], r["block"])
        if key in y:
            raise SystemExit(f"duplicate base slot {key}")
        y[key] = 1.0 if r["score"] == 1.0 else 0.0
    want = len(SIZES) * len(tasks) * len(HARNESSES) * len(SESSIONS) * len(BLOCKS)
    if len(y) != want:
        raise SystemExit(f"base slots {len(y)} != {want}")
    return tasks, y


def cell_mean(y: dict, z: str, t: str, h: str, s: str) -> float:
    return sum(y[(z, t, h, s, b)] for b in BLOCKS) / len(BLOCKS)


def exact_signflip(values: list[float], two_sided: bool) -> dict:
    nonzero = [v for v in values if abs(v) > 1e-12]
    obs = sum(values) / len(values)
    hits = 0
    for signs in itertools.product((-1.0, 1.0), repeat=len(nonzero)):
        t = sum(sg * v for sg, v in zip(signs, nonzero)) / len(values)
        if two_sided:
            hits += abs(t) >= abs(obs) - 1e-12
        else:
            hits += t >= obs - 1e-12
    n = 2 ** len(nonzero)
    return {
        "statistic": round(obs, 6),
        "tasks": len(values),
        "nonzero_tasks": len(nonzero),
        "signs_of_nonzero": sorted({1 if v > 0 else -1 for v in nonzero}),
        "patterns_at_least_as_extreme": hits,
        "patterns": n,
        "exact_p": round(hits / n, 6),
    }


def discordance(y: dict, tasks: list[str], z: str, kind: str) -> float:
    fractions = []
    for t in tasks:
        for h in HARNESSES:
            v = {(s, b): y[(z, t, h, s, b)] for s in SESSIONS for b in BLOCKS}
            if kind == "between":
                pairs = [(v[("S1", a)], v[("S2", b)]) for a in BLOCKS for b in BLOCKS]
            else:
                pairs = [(v[(s, "b1")], v[(s, "b2")]) for s in SESSIONS]
            fractions.append(sum(p != q for p, q in pairs) / len(pairs))
    return sum(fractions) / len(fractions)


def primary_checks(records: list[dict]) -> tuple[dict, dict]:
    tasks, y = outcome_array(records)
    d = {
        (z, t, s): cell_mean(y, z, t, "H-GA", s) - cell_mean(y, z, t, "H-OSW-fixed", s)
        for z in SIZES
        for t in tasks
        for s in SESSIONS
    }
    q = [sum(d[(z, t, "S1")] * d[(z, t, "S2")] for z in SIZES) / len(SIZES) for t in tasks]
    w = {
        (z, t, h): cell_mean(y, z, t, h, "S2") - cell_mean(y, z, t, h, "S1")
        for z in SIZES
        for t in tasks
        for h in HARNESSES
    }
    tests = {
        "registered_monte_carlo": "estimators.signflip_p: 10,000 flips, PCG64 seed 42 "
        "(report-guarded.json primary.tests)",
        "x_signflip_one_sided": exact_signflip(q, two_sided=False),
        "session_signflip_two_sided": {
            z: exact_signflip(
                [sum(w[(z, t, h)] for h in HARNESSES) / len(HARNESSES) for t in tasks],
                two_sided=True,
            )
            for z in SIZES
        },
    }
    dr3 = {}
    for z in SIZES:
        c = sum(w[(z, t, "H-GA")] * w[(z, t, "H-OSW-fixed")] for t in tasks) / len(tasks) / 2
        db = discordance(y, tasks, z, "between")
        dw = discordance(y, tasks, z, "within")
        v = (db - dw) / 2
        dr3[z] = {
            "C_z": round(c, 6),
            "D_b": round(db, 6),
            "D_w": round(dw, 6),
            "V_z": round(v, 6),
            "rho_frozen_code": round(min(max(c / v, 0.0), 1.0), 6) if v > 0 else None,
            "rho_formula_literal": round(min(max(c / v, 0.0), 1.0), 6) if v != 0 else None,
        }
    return tests, dr3


def main() -> int:
    if OUT.exists():
        print(f"refusing: {OUT} exists", file=sys.stderr)
        return 2
    records = [json.loads(line) for line in RECORDS.read_text().splitlines() if line.strip()]
    guard = json.loads(GUARD.read_text())
    labels = dict(guard["labels"])
    labels["source"] = f"guard.json (sha256 {sha256(GUARD)})"
    tests, dr3 = primary_checks(records)
    out = {
        "schema": "q2-stage1a-post-review-v1",
        "labels": labels,
        "inputs": {
            str(p.relative_to(ANALYSIS.parent)): sha256(p)
            for p in (RECORDS, GUARD, *BRIDGES.values())
        },
        "records": len(records),
        "timings_per_size": timings(records),
        "engine_queue_per_job": engine_queue(records),
        "exact_signflip_primary": tests,
        "dr3_common_session_share": dr3,
    }
    OUT.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"written": OUT.name, "sha256": sha256(OUT)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
