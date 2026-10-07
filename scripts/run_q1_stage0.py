#!/usr/bin/env python3
"""Plan and run Q1 Stage 0 work items over a corpus of kernel directories.

A corpus root holds substrate, mutant and control directories in the shared
layout (``harness/q1/schema.py``). This script expands every kernel into one
work item per gate or audit channel per seed, then runs them with the Q1
runner (one subprocess per item, watchdog, append-only journal, resume).

    python scripts/run_q1_stage0.py --corpus /inputs/corpus --output /outputs/stage0 \\
        --gates a,a_1e-3,a_head_1e-4,a_head_1e-2,a_static,b1,b2,c,A1,A2,A3,A4,A5 \\
        --slots cuda:0 --seeds 42 43 44

Seeds 42, 43 and 44 are robustness replicates of the whole stack (gate (a)'s
``seed_num``, gate (c)'s and the audit's draw seeds shift with the replicate).
Re-running with the same ``--output`` resumes from the journal.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.q1.runner import DEFAULT_TIMEOUTS, Runner, RunnerConfig, WorkItem  # noqa: E402
from harness.q1.schema import iter_kernel_dirs  # noqa: E402
from harness.q1.worker import WORK_GATES  # noqa: E402

DEFAULT_GATES = (
    "a",
    "a_1e-3",
    "a_head_1e-4",
    "a_head_1e-2",
    "a_static",
    "b1",
    "b2",
    "c",
    "A1",
    "A2",
    "A3",
    "A4",
    "A4_poison",
    "A4_sanitizer",
    "A5",
)


def plan(
    corpus_roots: list[Path], gates: list[str], seeds: list[int], options: dict
) -> list[WorkItem]:
    unknown = sorted(set(gates) - set(WORK_GATES))
    if unknown:
        raise SystemExit(f"unknown gates: {unknown}")
    items: list[WorkItem] = []
    for root in corpus_roots:
        for kernel in iter_kernel_dirs(root):
            for seed in seeds:
                for gate in gates:
                    items.append(
                        WorkItem(
                            kernel_id=kernel.kernel_id,
                            kernel_path=str(kernel.kernel_path),
                            problem_id=kernel.problem_id,
                            gate=gate,
                            seed=seed,
                            options=dict(options.get(gate, {})),
                        )
                    )
    return items


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--corpus", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--gates", default=",".join(DEFAULT_GATES))
    parser.add_argument("--slots", default="cuda:0")
    parser.add_argument("--timing-slots", default="")
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--options", type=Path, default=None, help="JSON {gate: {option: value}}")
    parser.add_argument("--timeouts", default=None, help="JSON overriding phase limits")
    args = parser.parse_args(argv)
    options = json.loads(args.options.read_text()) if args.options else {}
    items = plan(args.corpus, [g for g in args.gates.split(",") if g], args.seeds, options)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "items.jsonl").write_text(
        "".join(json.dumps(item.__dict__, sort_keys=True) + "\n" for item in items)
    )
    workdir = args.output / "items"
    workdir.mkdir(exist_ok=True)
    marker = os.environ.get("COTCODEC_CHECKPOINT_MARKER")
    config = RunnerConfig(
        journal_path=args.output / "journal.jsonl",
        slots=[s for s in args.slots.split(",") if s],
        timing_slots=[s for s in args.timing_slots.split(",") if s],
        timeouts={**DEFAULT_TIMEOUTS, **(json.loads(args.timeouts) if args.timeouts else {})},
        workdir=workdir,
        checkpoint_marker=Path(marker) if marker else None,
    )
    runner = Runner(config)
    for signum in (signal.SIGUSR1, signal.SIGTERM):
        signal.signal(signum, lambda *_: runner.stop())
    summary = runner.run(items)
    runner.write_checkpoint_marker()
    summary["interrupted"] = runner.stopped.is_set()
    (args.output / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True))
    print(json.dumps(summary, sort_keys=True))
    return 75 if summary["interrupted"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
