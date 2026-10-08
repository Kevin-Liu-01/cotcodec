#!/usr/bin/env python3
"""Q1 Stage 0 validation job under ``q1-stage0-exec/2`` (decision D37 iii): one lane job.

Rule ``q1-exec2-validation/1`` (``harness/q1/exec2_validation.py``). The corpus is
the D31 re-pilot's hash-bound study artifact (``scripts/q1_prepare_repilot_corpus.py``,
the 24 kernels job 713 scored); the three KernelBench adversarial controls are
written in the job from the image's vendored files, each checked against
``third_party/kernelbench/SOURCES.json``. Execution is a Stage 0 job's under
``q1-stage0-exec/2``: 12 capacity units on the job's one GPU, units and peak
estimates from ``trim.item_units``, the free-memory guard
(``runner.MemoryGuard``, ``memory.budget_bytes``), the contention-safe health
check, the reference store with its janitor and disk caps, size-scaled watchdog
limits. The time box differs from ``run_q1_stage0.py``: the job is 10 minutes, so
items are not fitted to their watchdog limits (every limit exceeds the box);
slots stop taking items ``--drain-seconds`` before the hard deadline, and an item
still running at the hard deadline is killed and recorded in ``cut.jsonl``
(censored cost), never journaled.

Output (``--output``): ``validation/journal.jsonl`` (verdict rows),
``validation/references.jsonl`` (reference items), ``validation/memory.jsonl``
(each worker's peak CUDA memory), ``validation/items.jsonl``,
``validation/cut.jsonl``, ``plan.json``, ``exposure.json``,
``adversarial-controls.json``, ``reference-schedule.json``, ``nvidia-smi-*.txt``,
``phases.json`` and ``summary.json``. The store sits beside the output and its
tensors are deleted after their last consumer and at the end.

    python scripts/run_q1_exec2_validation.py --evidence /inputs/study-artifact.json \\
        --expected-evidence-sha256 SHA --output /outputs/q1 --budget-minutes 10 \\
        --seeds 42 43 44
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.q1 import exec2_validation as rule  # noqa: E402
from harness.q1 import memory, refschedule, trim  # noqa: E402
from harness.q1.runner import (  # noqa: E402
    MemoryGuard,
    Runner,
    RunnerConfig,
    WorkItem,
    install_signal_handlers,
)

#: No item may still run this many seconds before the end of ``--budget-minutes``
#: (the lane sends SIGUSR1 180 s before its limit; this leaves 30 s for the store's
#: cleanup and the summary before it).
END_MARGIN_SECONDS = 210.0
#: Slots stop taking items this long before the hard deadline.
DEFAULT_DRAIN_SECONDS = 60.0


def nvidia_smi(path: Path) -> None:
    """Best-effort snapshot of the job's GPU (``nvidia-smi``), never fatal."""
    try:
        out = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,name,memory.used,memory.total,utilization.gpu",
                "--format=csv",
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        apps = subprocess.run(
            [
                "nvidia-smi",
                "--query-compute-apps=pid,used_memory",
                "--format=csv",
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        path.write_text(out.stdout + out.stderr + "\n" + apps.stdout + apps.stderr)
    except (OSError, subprocess.SubprocessError) as exc:
        path.write_text(f"unavailable: {type(exc).__name__}: {exc}\n")


def write_adversarial(root: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Write the three adversarial controls and check each kernel against
    ``SOURCES.json``; returns (kernels in rule order, provenance rows)."""
    from harness.q1 import controls
    from harness.q1.schema import iter_kernel_dirs

    sources = json.loads(
        (PROJECT_ROOT / "harness/q1/third_party/kernelbench/SOURCES.json").read_text()
    )
    pinned = {Path(f["local"]).name: f["sha256"] for f in sources["files"]}
    controls.write_controls(root, identity=[], adversarial=rule.ADVERSARIAL)
    found = {k.kernel_id: k for k in iter_kernel_dirs(root)}
    kernels, provenance = [], []
    for name in rule.ADVERSARIAL:
        kernel_id = f"ctl-kernelbench-{name.replace('_', '-')}-L1-1"
        record = found[kernel_id]
        digest = hashlib.sha256(Path(record.kernel_path).read_bytes()).hexdigest()
        expected = pinned[f"{name}_kernel.py"]
        if digest != expected:
            raise SystemExit(f"FAIL: {kernel_id} kernel.py {digest} differs from SOURCES.json")
        kernels.append(
            {
                "kernel_id": kernel_id,
                "kernel_path": str(record.kernel_path),
                "problem_id": record.problem_id,
            }
        )
        provenance.append({"kernel_id": kernel_id, "kernel_sha256": digest, "pinned": expected})
    return kernels, provenance


def check_exposure(
    repilot: list[dict[str, str]], adversarial: list[dict[str, str]]
) -> dict[str, object]:
    from harness.q1 import problems
    from harness.q1.substrates import s2_catalog
    from harness.q1.substrates import split as s1_split

    split = s1_split.calibration_split(problems.list_problem_ids(include_excluded=True), seed=42)
    record = rule.exposure(
        repilot,
        adversarial,
        calibration=split["calibration"],
        evaluation=split["evaluation"],
        s2_problems={e.problem_id for e in s2_catalog.CATALOG},
        exposed=trim.load_exposed(),
    )
    record["s1_split_sha256"] = split["sha256"]
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--evidence", type=Path, required=True, help="re-pilot study artifact")
    parser.add_argument("--expected-evidence-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--budget-minutes", type=float, required=True)
    parser.add_argument("--drain-seconds", type=float, default=DEFAULT_DRAIN_SECONDS)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--gpu", default="cuda:0")
    parser.add_argument("--plan-only", action="store_true", help="write the plan and stop")
    args = parser.parse_args(argv)
    if sorted(args.seeds) != [42, 43, 44]:
        parser.error("the job declares replicates 42, 43 and 44 (it schedules 42)")
    from harness.q1 import study_artifact
    from harness.q1.versions import version_card
    from scripts.run_q1_repilot import kernels_in_order
    from scripts.run_q1_stage0 import StoreJanitor, drop_reference_tensors

    started = time.monotonic()
    hard = started + args.budget_minutes * 60.0 - END_MARGIN_SECONDS
    soft = hard - args.drain_seconds
    args.output.mkdir(parents=True, exist_ok=True)
    phase_dir = args.output / "validation"
    phase_dir.mkdir(exist_ok=True)
    if not args.plan_only:
        nvidia_smi(args.output / "nvidia-smi-start.txt")
    phases: list[dict[str, object]] = []
    inputs = args.output.parent / f"{args.output.name}-inputs"
    receipt = study_artifact.unpack(
        study_artifact.load(args.evidence, args.expected_evidence_sha256), inputs
    )
    (args.output / "study-artifact-receipt.json").write_text(
        json.dumps(receipt, indent=1, sort_keys=True, default=str)
    )
    repilot = kernels_in_order(inputs)
    adversarial, provenance = write_adversarial(args.output.parent / f"{args.output.name}-controls")
    (args.output / "adversarial-controls.json").write_text(json.dumps(provenance, indent=1))
    exposure = check_exposure(repilot, adversarial)
    (args.output / "exposure.json").write_text(json.dumps(exposure, indent=1, sort_keys=True))
    if not exposure["ok"]:
        print(f"FAIL: exposure check: {json.dumps(exposure['violations'])}", file=sys.stderr)
        return 2
    phases.append({"name": "prepare", "seconds": round(time.monotonic() - started, 3)})
    store = args.output.parent / f"{args.output.name}-refstore"
    store.mkdir(exist_ok=True)
    over_cap: list[dict] = []
    estimates: dict = {}
    entries = rule.items(
        repilot,
        adversarial,
        store_root=str(store),
        journal=str(phase_dir / "references.jsonl"),
        over_cap=over_cap,
        estimates=estimates,
    )
    (phase_dir / "items.jsonl").write_text(
        "".join(json.dumps(e, sort_keys=True) + "\n" for e in entries)
    )
    version = version_card()
    plan = {
        "rule": rule.RULE,
        "execution_policy": memory.POLICY_VERSION,
        "policy": memory.POLICY,
        "memory_table_sha256": hashlib.sha256(memory.TABLE_PATH.read_bytes()).hexdigest(),
        "guard_budget_bytes": memory.budget_bytes(),
        "items": len(entries),
        "items_sha256": rule.items_sha256(entries),
        "problem_order": list(rule.PROBLEM_ORDER),
        "adversarial": list(rule.ADVERSARIAL),
        "adversarial_gates": list(rule.ADVERSARIAL_GATES),
        "budget_minutes": args.budget_minutes,
        "end_margin_seconds": END_MARGIN_SECONDS,
        "drain_seconds": args.drain_seconds,
        "driver_sha256": version["driver_sha256"],
        "gate_code_sha256": version["gate_code_sha256"],
        "audit_code_sha256": version["audit_code_sha256"],
        # The validation rule and this driver are outside the registered card on
        # purpose: the job runs the card's gate, audit and driver code unchanged.
        "validation_files_sha256": {
            rel: hashlib.sha256((PROJECT_ROOT / rel).read_bytes()).hexdigest()
            for rel in ("harness/q1/exec2_validation.py", "scripts/run_q1_exec2_validation.py")
        },
    }
    (args.output / "plan.json").write_text(json.dumps(plan, indent=1, sort_keys=True))
    (args.output / "reference-schedule.json").write_text(
        json.dumps(
            {
                "store": str(store),
                "reference_items": dict(
                    sorted(
                        Counter(e["gate"] for e in entries if e["gate"].startswith("ref_")).items()
                    )
                ),
                "consumers_with_store": sum(
                    1
                    for e in entries
                    if not e["gate"].startswith("ref_") and "reference_store" in e["options"]
                ),
                "disk": {
                    **refschedule.footprint(entries, estimates),
                    "entry_cap_bytes": refschedule.ENTRY_CAP_BYTES,
                    "groups_inline_over_entry_cap": over_cap,
                },
            },
            indent=1,
            sort_keys=True,
        )
    )
    print(
        json.dumps({k: plan[k] for k in ("rule", "items", "items_sha256", "driver_sha256")}),
        flush=True,
    )
    if args.plan_only:
        return 0
    items = [WorkItem(**e) for e in entries]
    marker = os.environ.get("COTCODEC_CHECKPOINT_MARKER")
    workdir = phase_dir / "items"
    workdir.mkdir(exist_ok=True)
    janitor = StoreJanitor(items)
    config = RunnerConfig(
        journal_path=phase_dir / "journal.jsonl",
        slots=[args.gpu] * int(trim.TRIM_RULE["slot_capacity"]),
        workdir=workdir,
        checkpoint_marker=Path(marker) if marker else None,
        progress_path=phase_dir / "progress.json",
        soft_deadline=soft,
        hard_deadline=hard,
        fit_deadline=False,
        memory_guard=MemoryGuard(memory.budget_bytes()),
        on_done=janitor,
        extra_env={
            key: os.environ[key]
            for key in ("TRITON_CACHE_DIR", "TORCHINDUCTOR_CACHE_DIR")
            if key in os.environ
        },
    )
    runner = Runner(config)
    install_signal_handlers(runner)
    phase_start = time.monotonic()
    summary = runner.run(items)
    runner.write_checkpoint_marker()
    phases.append(
        {
            "name": "validation",
            "seconds": round(time.monotonic() - phase_start, 3),
            "runs": [summary],
        }
    )
    nvidia_smi(args.output / "nvidia-smi-end.txt")
    summary.update(
        {
            "interrupted": runner.stopped.is_set() and not runner.expired,
            "expired_at_hard_deadline": runner.expired,
            "rule": rule.RULE,
            "items": len(items),
            "items_sha256": plan["items_sha256"],
            "reference_entries_deleted_after_last_consumer": janitor.deleted,
            "reference_bytes_freed_after_last_consumer": janitor.freed_bytes,
            "reference_tensors_deleted": drop_reference_tensors(store),
            "soft_deadline_seconds": round(soft - started, 3),
            "hard_deadline_seconds": round(hard - started, 3),
            "driver_seconds": round(time.monotonic() - started, 3),
        }
    )
    (args.output / "phases.json").write_text(json.dumps({"phases": phases}, indent=1))
    (args.output / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True))
    print(json.dumps(summary, sort_keys=True), flush=True)
    return 75 if summary["interrupted"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
