#!/usr/bin/env python3
"""GPU smoke for the Q1 gates and audit: the PyTorch reference as its own "kernel".

For a few KernelBench@423217d9 problems, the candidate is the problem's own
``Model`` re-exported as ``ModelNew`` (a reference-identity control: reviewed,
committed, benchmark code; no model-written kernel). Every gate and audit
channel runs through the runner on one GPU, and gate (a) is also run through
the verbatim vendored upstream ``eval_kernel_against_ref`` at both pinned
revisions for a fidelity check. Expected: gate (a) accepts (L1/95 is
unrefereeable at HEAD's fp32 cast), b1 and b2 reject (no Triton launch), gate
(c) and the audit accept.

Runs only as a Slurm job through the lane (one GPU, ``model: {kind: none}``,
``experiments/manifests/q1-core/q1-gate-gpu-smoke.yaml``) from a
source-overlay image of a revision that includes main's lane merge.

    python scripts/run_q1_gpu_smoke.py --output /outputs/q1-smoke --seeds 42 43 44
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

from harness.q1 import problems as problem_lib  # noqa: E402
from harness.q1.runner import (  # noqa: E402
    Runner,
    RunnerConfig,
    WorkItem,
    install_signal_handlers,
)
from harness.q1.schema import (  # noqa: E402
    KERNELBENCH_PROBLEMS_REVISION,
    canonical_json,
)

SMOKE_PROBLEMS = ("L1/19_ReLU", "L1/95_CrossEntropyLoss", "L2/12_Gemm_Multiply_LeakyReLU")
GATES = (
    "a",
    "a_head_1e-4",
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
EXPECT = {
    "a": "accept",
    "b1": "reject",
    "b2": "reject",
    "c1": "accept",
    "A1": "accept",
    "A2": "accept",
    "A4": "accept",
}


def write_controls(root: Path) -> dict[str, Path]:
    paths = {}
    for problem_id in SMOKE_PROBLEMS:
        level, number, name = problem_lib.parse_problem_id(problem_id)
        control_id = f"ctl-identity-L{level}-{number}_{name}"
        directory = root / control_id
        directory.mkdir(parents=True, exist_ok=True)
        source = problem_lib.load_problem_source(problem_id)
        (directory / "kernel.py").write_text(source + "\n\nModelNew = Model\n", encoding="utf-8")
        (directory / "control.json").write_text(
            canonical_json(
                {
                    "control_id": control_id,
                    "problem_id": problem_id,
                    "level": level,
                    "kernelbench_revision": KERNELBENCH_PROBLEMS_REVISION,
                    "control_kind": "reference-identity",
                    "expected": {"a": "accept", "b1": "reject"},
                    "source_repo": "https://github.com/ScalingIntelligence/KernelBench",
                    "source_revision": KERNELBENCH_PROBLEMS_REVISION,
                    "source_license": "MIT",
                    "origin_path": f"KernelBench/{problem_lib.problem_relpath(problem_id)}",
                }
            ),
            encoding="utf-8",
        )
        paths[problem_id] = directory
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    args = parser.parse_args(argv)
    import torch

    if not torch.cuda.is_available():
        print("FAIL: the GPU smoke needs one visible GPU", file=sys.stderr)
        return 2
    args.output.mkdir(parents=True, exist_ok=True)
    controls = write_controls(args.output / "controls")
    items = [
        WorkItem(
            kernel_id=path.name,
            kernel_path=str(path / "kernel.py"),
            problem_id=pid,
            gate=gate,
            seed=seed,
        )
        for seed in args.seeds
        for pid, path in controls.items()
        for gate in GATES
    ]
    (args.output / "items").mkdir(exist_ok=True)
    marker = os.environ.get("COTCODEC_CHECKPOINT_MARKER")
    runner = Runner(
        RunnerConfig(
            journal_path=args.output / "journal.jsonl",
            slots=["cuda:0"],
            workdir=args.output / "items",
            checkpoint_marker=Path(marker) if marker else None,
            progress_path=args.output / "progress.json",
        )
    )
    install_signal_handlers(runner)
    summary = runner.run(items)
    if runner.stopped.is_set():
        runner.write_checkpoint_marker()
        return 75
    timing = Runner(
        RunnerConfig(
            journal_path=args.output / "journal.jsonl",
            slots=[],
            timing_slots=["cuda:0"],
            workdir=args.output / "items",
        )
    )
    summary["timing"] = timing.run(
        [
            WorkItem(
                kernel_id=p.name,
                kernel_path=str(p / "kernel.py"),
                problem_id=pid,
                gate="timing",
                seed=args.seeds[0],
            )
            for pid, p in controls.items()
        ]
    )
    from harness.q1.gates.gate_a import upstream_gate_a

    fidelity = []
    for pid, path in controls.items():
        source = problem_lib.load_problem_source(pid)
        kernel = (path / "kernel.py").read_text(encoding="utf-8")
        for revision in ("44130946", "423217d9"):
            result = upstream_gate_a(source, kernel, revision=revision, device=0)
            fidelity.append(
                {"problem_id": pid, "revision": revision, "correctness": result["correctness"]}
            )
    from harness.q1.journal import Journal

    rows = Journal(args.output / "journal.jsonl").final_rows()
    checks = []
    for row in rows:
        gate = row["gate"]
        if gate in EXPECT and (
            row["config_id"] == "aggregate"
            or "/" not in row["config_id"]
            or row["config_id"].startswith("native")
        ):
            if gate in {"A1", "A2"} and row["tf32_policy"] != "tf32-admissible":
                continue
            checks.append(
                {
                    "kernel": row["kernel_id"],
                    "gate": gate,
                    "seed": row.get("seed"),
                    "expected": EXPECT[gate],
                    "got": row["verdict"],
                    "ok": row["verdict"] == EXPECT[gate],
                }
            )
    report = {
        "summary": summary,
        "upstream_gate_a": fidelity,
        "checks": checks,
        "status": "PASS" if all(c["ok"] for c in checks) else "FAIL",
    }
    (args.output / "smoke_report.json").write_text(json.dumps(report, indent=1, default=str))
    print(
        json.dumps(
            {"status": report["status"], "failed": [c for c in checks if not c["ok"]]}, default=str
        )
    )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
