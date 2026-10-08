"""Decision D31 evidence: execution incidents of re-pilot job 713 (both arms), from its
journals. Recorded analysis script (pure Python).

    python repilot_incidents.py RUN_DIR OUT.json

Counts items (not rows) whose shared attempt met a CUDA out-of-memory error and was
queued to run alone (``infra_failure-oom-shared``), items whose shared attempt timed
out, worker crashes, failed GPU health checks (each retires a slot), and items the
time box deferred, per problem and arm (inline, store, reference).
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path


def arm(kernel_id: str) -> str:
    if kernel_id.startswith("reference."):
        return "reference"
    return "store" if kernel_id.endswith(".store") else "inline"


def main() -> int:
    run, out = Path(sys.argv[1]), Path(sys.argv[2])
    phase = run / "q1" / "repilot"
    rows = [
        json.loads(line)
        for name in ("journal.jsonl", "references.jsonl")
        for line in (phase / name).open()
        if line.strip()
    ]
    items = [json.loads(line) for line in (phase / "items.jsonl").open() if line.strip()]
    problem = {f"{i['kernel_id']}|{i['gate']}|seed-{i['seed']}": i["problem_id"] for i in items}
    attempts: dict = collections.defaultdict(dict)
    for row in rows:
        key = row["details"]["item_key"]
        attempts[key].setdefault(int(row.get("attempt", 1)), []).append(row)
    counts: dict = collections.defaultdict(collections.Counter)
    for key, by_attempt in attempts.items():
        kernel_id = key.rsplit("|", 2)[0]
        where = (problem.get(key, "?"), arm(kernel_id))
        first = by_attempt[min(by_attempt)]
        kinds = {r["details"].get("infra_failure_kind") for r in first}
        if "infra_failure-oom-shared" in kinds:
            counts[where]["oom_shared_then_alone"] += 1
        if "infra_failure-timeout-shared" in kinds:
            counts[where]["timeout_shared_then_alone"] += 1
        for rs in by_attempt.values():
            reasons = {r["details"].get("reason") for r in rs}
            if "worker-crashed" in reasons:
                counts[where]["worker_crashed_attempts"] += 1
            if "infra_failure-gpu-health-check" in reasons:
                counts[where]["failed_health_checks"] += 1
        if not any(r["details"].get("item_final") for rs in by_attempt.values() for r in rs):
            counts[where]["never_final"] += 1
    ran = set(attempts)
    for key, problem_id in problem.items():
        if key not in ran:
            counts[(problem_id, arm(key.rsplit("|", 2)[0]))]["not_started_time_box"] += 1
    summary = json.loads((run / "q1" / "summary.json").read_text())
    report = {
        "runner_summary": {
            k: summary[k]
            for k in (
                "run",
                "items",
                "contention_oom_shared",
                "contention_timeout_shared",
                "crashes",
                "timeouts",
                "infra_failures",
                "retired_slots",
                "deferred_by_deadline",
                "left_in_queue",
            )
        },
        "per_problem_and_arm": {f"{p} [{a}]": dict(c) for (p, a), c in sorted(counts.items()) if c},
        "totals": dict(sum(counts.values(), collections.Counter())),
    }
    out.write_text(json.dumps(report, indent=1, sort_keys=True))
    print(json.dumps(report["totals"], indent=1))
    print(json.dumps(report["per_problem_and_arm"], indent=1)[:3000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
