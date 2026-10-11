"""The K2-C list: every checker candidate event of a mutation run (registration section 8).

A candidate event is what the parent's ``analysis.checker_candidates`` lists: an evaluable
mutant outside probe-touched cells that the checker fails although its label says it should
pass (``FN``), or passes although its label says it should fail (``FP_R``, ``FP_F``), under the
lock-exact venv. The list is fixed by the offline outcomes and verdicts alone: no audit
decision, adjudication answer or rater output is read, so it is the same before and after
Kevin's adjudication. It is selected on the checker's verdict, so it is a reproduction check
of the reported events, never a fidelity estimate (that is the frozen K2 sample's role).
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from harness.q2_mutation_k2.report import check_input, checker_family

EVENTS = ("FN", "FP_R", "FP_F")


def k2c_candidates(
    outcomes: Sequence[Mapping[str, Any]], verdicts: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    """The candidate events, sorted by mutant id, with the candidate digest each was scored on."""
    by_id = {str(v["mutant_id"]): v for v in verdicts}
    rows = []
    for row in outcomes:
        if row.get("lock_status") != "evaluable" or row.get("probe_touched"):
            continue
        if row.get("lock_event") not in EVENTS:
            continue
        verdict = by_id[str(row["mutant_id"])]
        rows.append(
            {
                "job_id": row["mutant_id"],
                "mutant_id": row["mutant_id"],
                "task_id": row["task_id"],
                "kind": "mutant",
                "candidate_sha256": verdict["candidate_sha256"],
                "checker_family": checker_family(verdict["checker_funcs"]),
                "event": row["lock_event"],
                "offline_verdict": verdict["verdict"],
            }
        )
    return sorted(rows, key=lambda r: r["mutant_id"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--outcomes", type=Path, required=True)
    parser.add_argument("--verdicts", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    outcomes = [json.loads(x) for x in check_input(args.outcomes).read_text().splitlines() if x]
    verdicts = [json.loads(x) for x in check_input(args.verdicts).read_text().splitlines() if x]
    rows = k2c_candidates(outcomes, verdicts)
    with args.out.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps({"candidates": len(rows), "out": str(args.out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
