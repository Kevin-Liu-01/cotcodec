#!/usr/bin/env python3
"""Stage 0 report from a Q1 journal and the corpus (preregistration sections 6-10).

    python scripts/report_q1_stage0.py --journal RUN/journal.jsonl --corpus CORPUS \\
        --output RUN/stage0-report.json

Applies the preregistered splits (S1 calibration split and mutant dev/test,
seed 42), composes the gate ladder and audit tiers per replicate, and writes
MS/FAR/FRR/FA-share with Clopper-Pearson and problem-cluster bootstrap
intervals for every contract tier under both TF32 policies, plus cost.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.q1 import analysis  # noqa: E402
from harness.q1.journal import Journal  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44])
    parser.add_argument("--resamples", type=int, default=10_000)
    args = parser.parse_args(argv)
    journal = Journal(args.journal)
    rows = journal.final_rows()
    _, invalid = journal.read()
    table = analysis.kernel_table(args.corpus)
    s1_problems = [
        v["problem_id"]
        for v in table.values()
        if v["kind"] == "substrate" and v["source_kind"] == "inductor"
    ]
    calibration, evaluation = analysis.calibration_split(s1_problems)
    evaluation_substrates = {
        k
        for k, v in table.items()
        if v["kind"] == "substrate"
        and (v["source_kind"] != "inductor" or v["problem_id"] in set(evaluation))
    }
    dev, test = analysis.mutant_split(k for k, v in table.items() if v["kind"] == "mutant")
    report: dict = {
        "journal_rows": len(rows),
        "invalid_journal_lines": invalid,
        "splits": {
            "s1_calibration_problems": calibration,
            "s1_evaluation_problems": evaluation,
            "dev_mutants": len(dev),
            "test_mutants": len(test),
        },
        "replicates": {},
        "cost": analysis.cost(rows),
    }
    for seed in args.seeds:
        composed = analysis.compose(rows, seed=seed)
        per_split = {}
        for split_name, keep in (("test", set(test)), ("dev", set(dev))):
            subset_table = {k: v for k, v in table.items() if v["kind"] != "mutant" or k in keep}
            per_split[split_name] = {
                f"{policy}/{tier}": analysis.metrics(
                    composed,
                    subset_table,
                    policy=policy,
                    tier=tier,
                    evaluation_substrates=evaluation_substrates,
                    resamples=args.resamples,
                )
                for policy in analysis.POLICIES
                for tier in ("N", "G", "G-strict", "c-disjoint")
            }
        report["replicates"][str(seed)] = {
            "kernels": len(composed),
            "b_fail_open": sum(bool(v["b_fail_open"]) for v in composed.values()),
            "metrics": per_split,
        }
    args.output.write_text(json.dumps(report, indent=1, sort_keys=True, default=str))
    print(json.dumps({"rows": len(rows), "kernels": len(table)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
