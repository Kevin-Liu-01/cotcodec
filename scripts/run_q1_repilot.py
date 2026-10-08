#!/usr/bin/env python3
"""Q1 Stage 0 re-pilot (decision D31): one lane job, paired inline and store arms.

The corpus arrives as one hash-bound study artifact built by
``scripts/q1_prepare_repilot_corpus.py`` (S1-cal substrates, their
reference-identity controls and one mutant each; rule ``harness/q1/repilot.py``,
``q1-repilot/1``). Every kernel gets all 15 scoring items twice at replicate 42,
once inline and once through the reference store (kernel id plus ``.store``),
twins adjacent in the queue, reference items just before their group's first
consumer; 12 capacity units on the job's one GPU, one per item (every pick is
below 0.6 GB), size-scaled watchdog limits, and a time box that defers what
cannot finish. Replicates 43 and 44 are declared (lane seed binding) and not
scheduled: the paired cost measurement needs no replicate and no verdict here is
a Stage 0 result.

Output (``--output``): ``repilot/journal.jsonl`` (verdict rows of both arms),
``repilot/references.jsonl`` (reference items), ``repilot/items.jsonl``,
``phases.json`` and ``summary.json``; the store sits beside the output and its
tensors are deleted at the end (manifests and use records stay). The cost
analysis is ``scripts/q1_repilot_cost.py`` (CPU).

    python scripts/run_q1_repilot.py --evidence /inputs/study-artifact.json \\
        --expected-evidence-sha256 SHA --output /outputs/q1 --budget-minutes 26 \\
        --seeds 42 43 44
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

from harness.q1 import repilot, trim  # noqa: E402
from harness.q1.runner import (  # noqa: E402
    Runner,
    RunnerConfig,
    WorkItem,
    install_signal_handlers,
)

#: Seconds before the end of the budget that no item may still be running (the lane
#: sends SIGUSR1 180 s before its limit).
END_MARGIN_SECONDS = 240.0


def kernels_in_order(inputs: Path) -> list[dict[str, str]]:
    from harness.q1.schema import iter_kernel_dirs

    selection = json.loads((inputs / "selection" / "repilot_selection.json").read_text())
    paths = {
        k.kernel_id: (k.kernel_path, k.problem_id)
        for tree in ("substrates", "controls", "mutants")
        for k in iter_kernel_dirs(inputs / tree)
    }
    out = []
    for entry in selection["order"]:
        for kernel_id in entry["kernels"]:
            path, problem_id = paths[kernel_id]
            if problem_id != entry["problem_id"]:
                raise ValueError(f"{kernel_id} is not a kernel of {entry['problem_id']}")
            out.append(
                {"kernel_id": kernel_id, "kernel_path": str(path), "problem_id": problem_id}
            )
    return out


def drop_reference_tensors(store: Path) -> int:
    removed = 0
    for path in store.glob("*/*/draw-*.pt"):
        path.unlink(missing_ok=True)
        removed += 1
    return removed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--evidence", type=Path, required=True, help="study artifact")
    parser.add_argument("--expected-evidence-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--budget-minutes", type=float, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--gpu", default="cuda:0")
    parser.add_argument("--plan-only", action="store_true", help="write the items and stop")
    args = parser.parse_args(argv)
    if sorted(args.seeds) != [42, 43, 44]:
        parser.error("the re-pilot declares replicates 42, 43 and 44 (it schedules 42)")
    from harness.q1 import study_artifact

    started = time.monotonic()
    phases: list[dict[str, object]] = []
    args.output.mkdir(parents=True, exist_ok=True)
    inputs = args.output.parent / f"{args.output.name}-inputs"
    receipt = study_artifact.unpack(
        study_artifact.load(args.evidence, args.expected_evidence_sha256), inputs
    )
    job = os.environ.get("SLURM_JOB_ID", "local")
    (args.output / f"study-artifact-receipt-{job}.json").write_text(
        json.dumps(receipt, indent=1, sort_keys=True, default=str)
    )
    phases.append({"name": "unpack", "seconds": round(time.monotonic() - started, 3)})
    phase_dir = args.output / "repilot"
    phase_dir.mkdir(exist_ok=True)
    store = args.output.parent / f"{args.output.name}-refstore"
    store.mkdir(exist_ok=True)
    entries = repilot.items(
        kernels_in_order(inputs),
        store_root=str(store),
        journal=str(phase_dir / "references.jsonl"),
    )
    (phase_dir / "items.jsonl").write_text(
        "".join(json.dumps(e, sort_keys=True) + "\n" for e in entries)
    )
    print(json.dumps({"items": len(entries), "rule": repilot.RULE}), flush=True)
    if args.plan_only:
        return 0
    items = [WorkItem(**e) for e in entries]
    phase_start = time.monotonic()
    hard = started + args.budget_minutes * 60.0 - END_MARGIN_SECONDS
    marker = os.environ.get("COTCODEC_CHECKPOINT_MARKER")
    workdir = phase_dir / "items"
    workdir.mkdir(exist_ok=True)
    config = RunnerConfig(
        journal_path=phase_dir / "journal.jsonl",
        slots=[args.gpu] * int(trim.TRIM_RULE["slot_capacity"]),
        workdir=workdir,
        checkpoint_marker=Path(marker) if marker else None,
        progress_path=phase_dir / "progress.json",
        soft_deadline=hard,
        hard_deadline=hard,
        fit_deadline=True,
        extra_env={
            key: os.environ[key]
            for key in ("TRITON_CACHE_DIR", "TORCHINDUCTOR_CACHE_DIR")
            if key in os.environ
        },
    )
    runner = Runner(config)
    install_signal_handlers(runner)
    summary = runner.run(items)
    runner.write_checkpoint_marker()
    phases.append(
        {
            "name": "repilot",
            "seconds": round(time.monotonic() - phase_start, 3),
            "runs": [summary],
        }
    )
    summary.update(
        {
            "interrupted": runner.stopped.is_set() and not runner.expired,
            "rule": repilot.RULE,
            "items": len(items),
            "reference_tensors_deleted": drop_reference_tensors(store),
            "driver_seconds": round(time.monotonic() - started, 3),
        }
    )
    (args.output / "phases.json").write_text(json.dumps({"phases": phases}, indent=1))
    (args.output / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True))
    print(json.dumps(summary, sort_keys=True), flush=True)
    return 75 if summary["interrupted"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
