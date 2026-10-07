#!/usr/bin/env python3
"""Stage 0 report from a Q1 journal and the corpus (preregistration sections 6-11).

    python scripts/report_q1_stage0.py --journal RUN/journal.jsonl --corpus CORPUS \\
        --replay-journal RUN/audit-holes/journal.jsonl --calibration CAL/audit-v1.json \\
        --output RUN/stage0-report.json

Applies the preregistered splits (the substrate corpus's S1 calibration split
and the mutator's content-hash dev/test split, both seed 42), composes the
gate ladder and audit tiers per replicate (unrefereeable components vacuous
per problem), and writes, for every contract tier under both TF32 policies:

- primary mutant metrics on test mutants of evaluation-set parents (S1-eval
  and S2) that the same tier accepts; dev, and mutants of S1 calibration
  parents, as labelled secondaries;
- MS (unweighted and n/k-weighted), FAR, FRR, FRR over independent units
  (criterion 3), FA-share, paired gate differences, and breakdowns by
  family, operator origin and source tier, on the kernels a, b and c all
  referee, with Clopper-Pearson and family-linked cluster bootstrap intervals;
- the precision-only class, refereeability (vacuous components and
  disagreements), every control expectation (criterion 5), the causes of
  gate (c) rejections of correct substrates, audit-hole adjudications
  (criterion 4, from the replay journal), c-lite on dev mutants, the audit
  calibration record, and marginal and amortized cost.
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

SCOPES = ("evaluation_parents", "s1_calibration_parents")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--replay-journal", type=Path, default=None)
    parser.add_argument("--calibration", type=Path, default=None)
    parser.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44])
    parser.add_argument("--resamples", type=int, default=10_000)
    args = parser.parse_args(argv)
    journal = Journal(args.journal)
    rows = journal.final_rows()
    all_rows, invalid = journal.read()
    replay_rows = Journal(args.replay_journal).final_rows() if args.replay_journal else []
    table = analysis.kernel_table(args.corpus)
    problem_of = {k: v["problem_id"] for k, v in table.items()}
    clusters = analysis.cluster_map(table)
    split = analysis.s1_split()
    halves = analysis.substrate_halves(table, split)
    evaluation_substrates = halves["evaluation"]
    parents = {
        "evaluation_parents": halves["evaluation"],
        "s1_calibration_parents": halves["calibration"],
    }
    dev, test = analysis.mutant_split(table)
    report: dict = {
        "journal_rows": len(rows),
        "invalid_journal_lines": invalid,
        "infrastructure_failures": sorted(
            {
                row["details"].get("item_key", row["kernel_id"])
                for row in rows
                if row["verdict"] == "error"
                and str(row["details"].get("reason", "")).startswith("infra_failure")
            }
        ),
        "splits": {
            "s1_split_sha256": split["sha256"],
            "s1_calibration_problems": split["calibration"],
            "s1_evaluation_problems": split["evaluation"],
            "s1_calibration_substrates": sorted(halves["calibration"]),
            "evaluation_substrates": len(evaluation_substrates),
            "dev_mutants": len(dev),
            "test_mutants": len(test),
            "bootstrap_clusters": len(set(clusters.values())),
        },
        "calibration": json.loads(args.calibration.read_text()) if args.calibration else None,
        "replicates": {},
        "cost": analysis.cost(rows, all_rows),
    }
    for seed in args.seeds:
        composed = analysis.compose(rows, seed=seed, problem_of=problem_of)
        per_split = {}
        for split_name, keep in (("test", set(test)), ("dev", set(dev))):
            subset_table = {k: v for k, v in table.items() if v["kind"] != "mutant" or k in keep}
            per_split[split_name] = {
                scope: {
                    f"{policy}/{tier}": analysis.metrics(
                        composed,
                        subset_table,
                        policy=policy,
                        tier=tier,
                        evaluation_substrates=evaluation_substrates,
                        mutant_parents=parents[scope],
                        resamples=args.resamples,
                        clusters=clusters,
                    )
                    for policy in analysis.POLICIES
                    for tier in analysis.TIERS
                }
                for scope in SCOPES
            }
        causes = analysis.c_rejection_causes(rows, seed=seed)
        candidates = analysis.audit_hole_candidates(rows, composed, table, seed=seed)
        report["replicates"][str(seed)] = {
            "kernels": len(composed),
            "b_fail_open": sum(bool(v["b_fail_open"]) for v in composed.values()),
            "metrics": per_split,
            "criterion_3_FRR_c": per_split["test"]["evaluation_parents"][
                f"{analysis.PRIMARY_POLICY}/{analysis.PRIMARY_TIER}"
            ]["criterion_3_FRR_c"],
            "refereeability": analysis.refereeability_report(composed, table),
            "controls": {
                policy: analysis.control_checks(composed, table, policy=policy)
                for policy in analysis.POLICIES
            },
            "c_rejection_causes_evaluation_substrates": {
                k: v for k, v in causes.items() if k in evaluation_substrates
            },
            "audit_holes": {
                "candidates": candidates,
                "summary": analysis.audit_hole_summary(replay_rows, candidates, seed=seed),
            },
            "c_lite": analysis.c_lite_set_cover(
                rows, composed, table, dev, seed=seed, mutant_parents=parents["evaluation_parents"]
            ),
        }
    args.output.write_text(json.dumps(report, indent=1, sort_keys=True, default=str))
    print(json.dumps({"rows": len(rows), "kernels": len(table)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
