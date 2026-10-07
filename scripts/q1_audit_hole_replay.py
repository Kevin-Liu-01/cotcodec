#!/usr/bin/env python3
"""Replay every gate rejection of an audit-accepted kernel against the oracle (prereg 6.7).

    python scripts/q1_audit_hole_replay.py --journal RUN/journal.jsonl --corpus CORPUS \\
        --output RUN/audit-holes --multiplier 16 --seeds 42 43 44 --slots cuda:0

Reads the scoring journal's final rows, lists per replicate the gate (a) trials
and admissible gate (c) configurations that rejected a kernel the primary
audit tier accepts (``analysis.audit_hole_candidates``), and runs one
``audit_hole`` item per kernel and replicate through the Q1 runner into
``OUTPUT/journal.jsonl``. ``scripts/report_q1_stage0.py --replay-journal``
summarizes the adjudications. ``--plan-only`` writes the plan and runs nothing.
``--multiplier`` must be the frozen audit v1 multiplier.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.q1 import analysis  # noqa: E402
from harness.q1.journal import Journal  # noqa: E402
from harness.q1.runner import (  # noqa: E402
    DEFAULT_TIMEOUTS,
    Runner,
    RunnerConfig,
    WorkItem,
    install_signal_handlers,
)
from harness.q1.schema import iter_kernel_dirs  # noqa: E402


def plan(
    rows: list[dict], corpus_roots: list[Path], seeds: list[int], multiplier: float
) -> tuple[list[WorkItem], dict]:
    table = analysis.kernel_table(corpus_roots)
    paths = {
        k.kernel_id: str(k.kernel_path) for root in corpus_roots for k in iter_kernel_dirs(root)
    }
    problem_of = {k: v["problem_id"] for k, v in table.items()}
    items, candidates = [], {}
    for seed in seeds:
        composed = analysis.compose(rows, seed=seed, problem_of=problem_of)
        found = analysis.audit_hole_candidates(rows, composed, table, seed=seed)
        candidates[str(seed)] = found
        for kernel_id, entry in found.items():
            if not entry["replay"]:
                continue
            items.append(
                WorkItem(
                    kernel_id=kernel_id,
                    kernel_path=paths[kernel_id],
                    problem_id=table[kernel_id]["problem_id"],
                    gate="audit_hole",
                    seed=seed,
                    options={"rejections": entry["replay"], "multiplier": multiplier},
                )
            )
    return items, candidates


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--multiplier", type=float, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--slots", default="cuda:0")
    parser.add_argument("--timeouts", default=None, help="JSON overriding phase limits")
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args(argv)
    rows = Journal(args.journal).final_rows()
    items, candidates = plan(rows, args.corpus, args.seeds, args.multiplier)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "candidates.json").write_text(json.dumps(candidates, indent=1, sort_keys=True))
    (args.output / "items.jsonl").write_text(
        "".join(json.dumps(item.__dict__, sort_keys=True) + "\n" for item in items)
    )
    if args.plan_only:
        print(json.dumps({"items": len(items)}))
        return 0
    workdir = args.output / "items"
    workdir.mkdir(exist_ok=True)
    marker = os.environ.get("COTCODEC_CHECKPOINT_MARKER")
    config = RunnerConfig(
        journal_path=args.output / "journal.jsonl",
        slots=[s for s in args.slots.split(",") if s],
        timeouts={**DEFAULT_TIMEOUTS, **(json.loads(args.timeouts) if args.timeouts else {})},
        workdir=workdir,
        checkpoint_marker=Path(marker) if marker else None,
        progress_path=args.output / "progress.json",
    )
    runner = Runner(config)
    install_signal_handlers(runner)
    summary = runner.run(items)
    runner.write_checkpoint_marker()
    summary["interrupted"] = runner.stopped.is_set()
    (args.output / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True))
    print(json.dumps(summary, sort_keys=True))
    return 75 if summary["interrupted"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
