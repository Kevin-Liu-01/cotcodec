#!/usr/bin/env python3
"""Run Q1 Stage 0 scoring under the trimming rule ``q1-stage0-trim/2`` (one lane job).

The plan is a pure function of the corpus (``harness.q1.trim.plan``): which
substrates, mutants and controls are scored, at which replicates, in which
priority buckets (P1-P8), with which concurrency units and watchdog limits.
This driver runs exactly that plan, or the buckets a job is given, and nothing
else (preregistration section 18.6):

- **Plan.** ``--plan-only`` writes ``plan.json`` (the rule, seeds, FRR set,
  mutant frames and samples, control schedule, every item, ``plan_sha256``)
  and ``items.jsonl`` on the CPU. A job checks ``--expected-plan-sha256``
  against the plan it recomputes from its corpus before it scores anything.
- **Execution.** One GPU per job and 32 CPUs (the conditions jobs 518 and 548
  measured), one Stage 0 job at a time; ``slot_capacity`` (12) slots on the
  GPU; an item holds 1 unit below 0.6 GB of native inputs, 3 from 0.6 to 1 GB
  (4 at a time, as in job 518), and the whole GPU from 1 GB; size-scaled
  watchdog limits on every item (``pilot.watchdog_limits``). A watchdog timeout
  or a CUDA out-of-memory error in a shared item is an infrastructure failure
  retried once alone (``runner``); alone, the outcome stands.
- **Stop.** The job refuses to start unless the Stage 0 GPU-hours already
  spent (every finished Stage 0 job's Slurm allocation, the pilot's 0.899
  included), this job's cap and the reserve (timing floor and audit-hole replay)
  fit in 8.0 GPU-h (``trim.budget_check``). The cap is the lane's time limit
  times its GPUs, so Slurm enforces it. Inside the job an item starts only if
  its watchdog limits end before the driver's hard deadline (``fit_deadline``),
  so a long item is deferred to the next job rather than started and killed;
  anything killed is recorded in ``cut.jsonl`` and reruns on resume.

    python scripts/run_q1_stage0.py --corpus CORPUS --output OUT --seeds 42 43 44 --plan-only
    python scripts/run_q1_stage0.py --evidence /inputs/study-artifact.json \\
        --expected-evidence-sha256 SHA --corpus corpus/substrates --corpus corpus/mutants \\
        --corpus corpus/controls --output /outputs/stage0 --seeds 42 43 44 --buckets P1 P2 \\
        --expected-plan-sha256 SHA --stage0-spent-gpu-hours 0.899 --job-cap-gpu-hours 3.0 \\
        --reserve-gpu-hours 1.5 --budget-minutes 180

With ``--evidence`` the corpus arrives as one hash-bound study artifact
(``harness/q1/study_artifact.py``), unpacked read-only under ``OUTPUT/inputs``;
relative ``--corpus`` paths are resolved there.

Re-running with the same ``--output`` resumes from the journal.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.q1 import trim  # noqa: E402
from harness.q1.runner import (  # noqa: E402
    Runner,
    RunnerConfig,
    WorkItem,
    install_signal_handlers,
)

#: Seconds before the lane's time limit that no item may still be running: the lane
#: sends SIGUSR1 180 s before the limit (docs/operations.md).
END_MARGIN_SECONDS = 240.0


def work_items(record: dict, buckets: list[str]) -> list[WorkItem]:
    capacity = int(record["rule"]["slot_capacity"])
    return [
        WorkItem(
            kernel_id=item["kernel_id"],
            kernel_path=item["kernel_path"],
            problem_id=item["problem_id"],
            gate=item["gate"],
            seed=int(item["seed"]),
            exclusive=int(item["units"]) >= capacity,
            units=int(item["units"]),
            timeouts=dict(item["timeouts"]),
        )
        for item in record["items"]
        if item["bucket"] in buckets
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--corpus", type=Path, action="append", required=True)
    parser.add_argument("--evidence", type=Path, default=None, help="study artifact")
    parser.add_argument("--expected-evidence-sha256", default=None)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--buckets", nargs="+", choices=list(trim.BUCKETS), default=None)
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--expected-plan-sha256", default=None)
    parser.add_argument("--exposed", type=Path, default=trim.PILOT_EXPOSED_PATH)
    parser.add_argument("--stage0-spent-gpu-hours", type=float, default=None)
    parser.add_argument("--job-cap-gpu-hours", type=float, default=None)
    parser.add_argument("--reserve-gpu-hours", type=float, default=None)
    parser.add_argument("--budget-minutes", type=float, default=None)
    parser.add_argument("--gpu", default="cuda:0", help="the job's one GPU slot device")
    args = parser.parse_args(argv)
    if sorted(args.seeds) != [42, 43, 44]:
        parser.error("Stage 0 declares replicates 42, 43 and 44")
    rule = trim.TRIM_RULE
    exposed = trim.load_exposed(args.exposed)
    corpus = list(args.corpus)
    if args.evidence is not None:
        from harness.q1 import study_artifact

        if not args.expected_evidence_sha256:
            parser.error("--evidence needs --expected-evidence-sha256")
        inputs = args.output / "inputs"
        receipt = study_artifact.unpack(
            study_artifact.load(args.evidence, args.expected_evidence_sha256), inputs
        )
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "study-artifact-receipt.json").write_text(
            json.dumps(receipt, indent=1, sort_keys=True, default=str)
        )
        corpus = [path if path.is_absolute() else inputs / path for path in corpus]
    records = trim.records_from_corpus(corpus)
    record = trim.plan(records, rule=rule, exposed=exposed)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "plan.json").write_text(json.dumps(record, indent=1, sort_keys=True))
    buckets = args.buckets or list(trim.BUCKETS)
    items = work_items(record, buckets)
    (args.output / "items.jsonl").write_text(
        "".join(json.dumps(item.__dict__, sort_keys=True) + "\n" for item in items)
    )
    print(
        json.dumps(
            {
                "plan_sha256": record["plan_sha256"],
                "buckets": buckets,
                "items": len(items),
                "bucket_counts": record["bucket_counts"],
            },
            sort_keys=True,
        ),
        flush=True,
    )
    if args.plan_only:
        return 0
    if args.expected_plan_sha256 != record["plan_sha256"]:
        print(
            f"FAIL: plan {record['plan_sha256']} differs from --expected-plan-sha256",
            file=sys.stderr,
        )
        return 2
    needed = (
        args.stage0_spent_gpu_hours,
        args.job_cap_gpu_hours,
        args.reserve_gpu_hours,
        args.budget_minutes,
    )
    if any(value is None for value in needed):
        parser.error(
            "a scoring job needs --stage0-spent-gpu-hours, --job-cap-gpu-hours, "
            "--reserve-gpu-hours and --budget-minutes"
        )
    gpus = int(rule["gpus_per_job"])
    if abs(args.job_cap_gpu_hours - gpus * args.budget_minutes / 60.0) > 1e-6:
        print("FAIL: --job-cap-gpu-hours must equal GPUs x --budget-minutes / 60", file=sys.stderr)
        return 2
    budget = trim.budget_check(
        spent_gpu_hours=args.stage0_spent_gpu_hours,
        job_cap_gpu_hours=args.job_cap_gpu_hours,
        reserve_gpu_hours=args.reserve_gpu_hours,
        rule=rule,
    )
    (args.output / "budget.json").write_text(json.dumps(budget, indent=1, sort_keys=True))
    if not budget["ok"]:
        print(f"FAIL: Stage 0 budget exceeded: {json.dumps(budget)}", file=sys.stderr)
        return 2
    started = time.monotonic()
    hard = started + args.budget_minutes * 60.0 - END_MARGIN_SECONDS
    marker = os.environ.get("COTCODEC_CHECKPOINT_MARKER")
    workdir = args.output / "items"
    workdir.mkdir(exist_ok=True)
    config = RunnerConfig(
        journal_path=args.output / "journal.jsonl",
        slots=[args.gpu] * int(rule["slot_capacity"]),
        workdir=workdir,
        checkpoint_marker=Path(marker) if marker else None,
        progress_path=args.output / "progress.json",
        soft_deadline=hard,
        hard_deadline=hard,
        fit_deadline=True,
    )
    runner = Runner(config)
    install_signal_handlers(runner)
    summary = runner.run(items)
    runner.write_checkpoint_marker()
    summary.update(
        {
            "interrupted": runner.stopped.is_set() and not runner.expired,
            "plan_sha256": record["plan_sha256"],
            "buckets": buckets,
            "budget": budget,
            "driver_seconds": round(time.monotonic() - started, 3),
        }
    )
    (args.output / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True))
    print(json.dumps(summary, sort_keys=True))
    return 75 if summary["interrupted"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
