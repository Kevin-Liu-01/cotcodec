#!/usr/bin/env python3
"""Run Q1 Stage 0 scoring under the trimming rule ``q1-stage0-trim/2`` (one lane job).

The plan is a pure function of the corpus (``harness.q1.trim.plan``): which
substrates, mutants and controls are scored, at which replicates, in which
priority buckets (P1-P8), with which concurrency units and watchdog limits.
This driver runs exactly that plan, or the buckets a job is given, and nothing
else (preregistration section 18.7):

- **Plan.** ``--plan-only`` writes ``plan.json`` (the rule, seeds, FRR set,
  mutant frames and samples, control schedule, every item, ``plan_sha256``)
  and ``items.jsonl`` on the CPU. A job checks ``--expected-plan-sha256``
  against the plan it recomputes from its corpus before it scores anything.
- **Execution** (policy ``q1-stage0-exec/2``, ``harness.q1.memory``,
  preregistration section 18.9). One GPU per job and 32 CPUs (the conditions
  jobs 518 and 548 measured), one Stage 0 job at a time; ``slot_capacity`` (12)
  slots on the GPU; each item holds the capacity units its estimated peak GPU
  memory needs (``plan`` records them; never fewer than the native-input rule of
  ``q1-stage0-exec/1``: 1 unit below 0.6 GB, 3 from 0.6 to 1 GB, the whole GPU
  from 1 GB), so the items per GPU follow each problem's memory, not a fixed 12.
  ``--measured-memory`` replaces estimates by measured peaks (the runner's
  ``memory.jsonl`` of an earlier job, ``memory.measured_peaks``). Before an item
  starts the runner reads the GPU's used memory (``nvidia-smi``) and waits while
  it would not fit (``runner.MemoryGuard``; ``--memory-guard off`` disables it).
  Size-scaled watchdog limits on every item (``pilot.watchdog_limits``). A
  watchdog timeout or a GPU resource failure in a shared item is an
  infrastructure failure retried once alone (``runner``); alone, the outcome
  stands. A failed health check drains the GPU and is repeated alone before any
  slot stops (``runner``).
- **Reference store** (decision D31, ``harness/q1/refstore.py``). Unless
  ``--reference-store off``, every (problem, replicate, channel) that at least two
  of the job's pending kernels read gets one reference item, run just before its
  first consumer; consumers read the entry instead of recomputing the
  references (fp32 device, fp32 CPU, fp64 and TF32 references, validity) and
  compute inline whenever no usable entry exists. Verdict rows are the same
  either way for kernels with defined behaviour that leave process-global state
  alone (section 18.8). Gate (a) always computes inline. The store and its
  reference journal live beside the output (``OUTPUT-refstore``), so a resumed
  job recomputes what its pending items need. Disk: a group whose estimated
  entry exceeds ``refschedule.ENTRY_CAP_BYTES`` computes inline, an entry is
  written only while the store's tensors stay within ``refstore.STORE_CAP_BYTES``,
  an entry's tensors are deleted once its last consumer has left the queue, and
  every stored tensor when the job ends (entries' manifests, the reference
  journal and the consumers' use records stay).
- **Stop.** The job refuses to start unless the Stage 0 GPU-hours already
  spent (every finished Stage 0 job's Slurm allocation: the pilot's 0.899 and
  the D31 re-pilot's 0.330, 1.229 at this writing), this job's cap and the
  reserve (timing floor and audit-hole replay) fit in 8.0 GPU-h
  (``trim.budget_check``). The operator types the spent hours from the Slurm
  records; the job refuses a value below the Stage 0 entries of the repository's
  GPU ledger (``trim.stage0_spent_gpu_hours``, ``program/state.json``). The cap
  is the lane's time limit times its GPUs, so Slurm enforces it. Inside the job
  an item starts only if its watchdog limits end before the driver's hard
  deadline (``fit_deadline``), so a long item is deferred to the next job rather
  than started and killed; anything killed is recorded in ``cut.jsonl`` and
  reruns on resume.

    python scripts/run_q1_stage0.py --corpus CORPUS --output OUT --seeds 42 43 44 --plan-only
    python scripts/run_q1_stage0.py --evidence /inputs/study-artifact.json \\
        --expected-evidence-sha256 SHA --corpus corpus/substrates --corpus corpus/mutants \\
        --corpus corpus/controls --output /outputs/stage0 --seeds 42 43 44 --buckets P1 P2 \\
        --expected-plan-sha256 SHA --stage0-spent-gpu-hours 1.229 --job-cap-gpu-hours 3.0 \\
        --reserve-gpu-hours 1.5 --budget-minutes 180

With ``--evidence`` the corpus arrives as one hash-bound study artifact
(``harness/q1/study_artifact.py``), unpacked read-only beside the output
(``OUTPUT-inputs``); relative ``--corpus`` paths are resolved there. Every job
after the first resumes the previous job's journal: its manifest names the
previous job in ``resume_from_job_id`` with ``resume_subpath`` set to the
output directory, so the lane copies that directory in before the job starts.

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
            memory_bytes=item.get("memory_bytes"),
        )
        for item in record["items"]
        if item["bucket"] in buckets
    ]


def with_reference_store(
    items: list[WorkItem], *, store: Path, journal: Path, final: set[str]
) -> tuple[list[WorkItem], dict]:
    """The job's items with reference items for the groups its pending items share
    (``harness.q1.refschedule``); already-final items do not count toward a group.
    Also returns the schedule's disk facts (estimated footprint, groups over the
    per-entry cap)."""
    from dataclasses import asdict

    from harness.q1 import refschedule, refstore

    pending = [asdict(item) for item in items if item.key not in final]
    over_cap: list[dict] = []
    estimates: dict = {}
    scheduled = refschedule.with_references(
        pending,
        root=str(store),
        store_cap_bytes=refstore.STORE_CAP_BYTES,
        over_cap=over_cap,
        estimates=estimates,
    )
    facts = {
        **refschedule.footprint(scheduled, estimates),
        "entry_cap_bytes": refschedule.ENTRY_CAP_BYTES,
        "store_cap_bytes": refstore.STORE_CAP_BYTES,
        "groups_inline_over_entry_cap": over_cap,
    }
    out = [
        WorkItem(**({**entry, "journal": str(journal)} if entry.get("journal") else entry))
        for entry in scheduled
    ]
    return [item for item in items if item.key in final] + out, facts


class StoreJanitor:
    """``RunnerConfig.on_done`` hook: deletes a reference entry's tensors once every
    consumer that requires it has left the queue (D31 review, finding 5)."""

    def __init__(self, items: list[WorkItem]) -> None:
        import threading

        self._lock = threading.Lock()
        self.remaining: dict[str, set[str]] = {}
        for item in items:
            for ref in item.requires:
                self.remaining.setdefault(ref, set()).add(item.key)
        self.entries: dict[str, str | None] = {}
        self.deleted = 0
        self.freed_bytes = 0

    def __call__(self, item: WorkItem, rows: list[dict] | None) -> None:
        from harness.q1 import refstore

        ready: list[str] = []
        with self._lock:
            if refstore.is_reference_gate(item.gate):
                path = (rows or [{}])[-1].get("details", {}).get("entry_dir") if rows else None
                self.entries[item.key] = path
                if not self.remaining.get(item.key):
                    ready.append(item.key)
            for ref in item.requires:
                waiting = self.remaining.get(ref)
                if waiting is None:
                    continue
                waiting.discard(item.key)
                if not waiting and ref in self.entries:
                    ready.append(ref)
            paths = [self.entries.pop(ref, None) for ref in ready]
        for path in paths:
            if path:
                freed = refstore.delete_draws(Path(path))
                with self._lock:
                    self.deleted += 1
                    self.freed_bytes += freed


def drop_reference_tensors(store: Path) -> int:
    """Delete stored tensors (``draw-*.pt``) after the job; manifests stay."""
    removed = 0
    for path in store.glob("*/*/draw-*.pt"):
        path.unlink(missing_ok=True)
        removed += 1
    return removed


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
    parser.add_argument(
        "--reference-store",
        choices=("on", "off"),
        default="on",
        help="compute references once per problem, replicate and draw (decision D31)",
    )
    parser.add_argument("--keep-reference-tensors", action="store_true")
    parser.add_argument(
        "--measured-memory",
        type=Path,
        default=None,
        help="measured peak GPU bytes per problem|gate (memory.measured_peaks JSON)",
    )
    parser.add_argument("--memory-guard", choices=("on", "off"), default="on")
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
        # Beside the output, not in it: a later job resumes by copying the output
        # directory (the lane's resume_from_job_id / resume_subpath) and unpacks again.
        inputs = args.output.parent / f"{args.output.name}-inputs"
        receipt = study_artifact.unpack(
            study_artifact.load(args.evidence, args.expected_evidence_sha256), inputs
        )
        args.output.mkdir(parents=True, exist_ok=True)
        job = os.environ.get("SLURM_JOB_ID", "local")
        (args.output / f"study-artifact-receipt-{job}.json").write_text(
            json.dumps(receipt, indent=1, sort_keys=True, default=str)
        )
        corpus = [path if path.is_absolute() else inputs / path for path in corpus]
    from harness.q1 import memory

    records = trim.records_from_corpus(corpus)
    measured = memory.load_measured(args.measured_memory)
    record = trim.plan(records, rule=rule, exposed=exposed, measured=measured)
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
    ledger = PROJECT_ROOT / "program" / "state.json"
    if ledger.exists():
        recorded = trim.stage0_spent_gpu_hours(
            json.loads(ledger.read_text(encoding="utf-8")).get("gpu_hours_ledger", [])
        )
        if args.stage0_spent_gpu_hours + 1e-9 < recorded:
            print(
                f"FAIL: --stage0-spent-gpu-hours {args.stage0_spent_gpu_hours} is below the "
                f"{recorded} GPU-h of Stage 0 work in {ledger.relative_to(PROJECT_ROOT)}",
                file=sys.stderr,
            )
            return 2
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
    store = None
    if args.reference_store == "on":
        from harness.q1 import refschedule
        from harness.q1.journal import Journal

        # Beside the output, like the unpacked inputs: a resumed job copies the output
        # directory only, so it recomputes the references its pending items need.
        store = args.output.parent / f"{args.output.name}-refstore"
        store.mkdir(parents=True, exist_ok=True)
        status = Journal(args.output / "journal.jsonl").status()
        final = {key for key, entry in status.items() if entry["final"]}
        items, disk = with_reference_store(
            items, store=store, journal=store / "references.jsonl", final=final
        )
        (args.output / "items-run.jsonl").write_text(
            "".join(json.dumps(item.__dict__, sort_keys=True) + "\n" for item in items)
        )
        (args.output / "reference-schedule.json").write_text(
            json.dumps(
                {
                    "store": str(store),
                    **refschedule.summary([item.__dict__ for item in items]),
                    "disk": disk,
                },
                indent=1,
                sort_keys=True,
            )
        )
    from harness.q1.runner import MemoryGuard

    janitor = StoreJanitor(items) if store is not None and not args.keep_reference_tensors else None
    config = RunnerConfig(
        journal_path=args.output / "journal.jsonl",
        slots=[args.gpu] * int(rule["slot_capacity"]),
        workdir=workdir,
        checkpoint_marker=Path(marker) if marker else None,
        progress_path=args.output / "progress.json",
        soft_deadline=hard,
        hard_deadline=hard,
        fit_deadline=True,
        memory_guard=MemoryGuard(memory.budget_bytes()) if args.memory_guard == "on" else None,
        on_done=janitor,
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
            "reference_store": None if store is None else str(store),
            "driver_seconds": round(time.monotonic() - started, 3),
        }
    )
    if janitor is not None:
        summary["reference_entries_deleted_after_last_consumer"] = janitor.deleted
        summary["reference_bytes_freed_after_last_consumer"] = janitor.freed_bytes
    if store is not None and not args.keep_reference_tensors:
        summary["reference_tensors_deleted"] = drop_reference_tensors(store)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True))
    print(json.dumps(summary, sort_keys=True))
    return 75 if summary["interrupted"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
