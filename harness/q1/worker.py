"""One work item (one kernel x one gate or audit channel x one seed) in a fresh process.

    python -m harness.q1.worker ITEM.json OUT.jsonl

The runner spawns this module once per item, so compiled kernels, caches,
allocator state and any state a candidate keeps between calls never leak
between gates. The worker reports phases to the runner's watchdog through
``Q1_PHASE_FD`` and writes schema verdict rows to ``OUT.jsonl``. It never
appends to the journal itself.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

WORK_GATES = (
    "a",
    "a_1e-3",
    "a_head_1e-4",
    "a_head_1e-2",
    "a_static",
    "b1",
    "b2",
    "b_native",
    "c",
    "A1",
    "A2",
    "A3",
    "A4",
    "A5",
    "A4_poison",
    "A4_sanitizer",
    "timing",
)


def _rows_for(item: Mapping[str, Any]) -> list[dict[str, Any]]:
    import torch

    from harness.q1 import problems as problem_lib
    from harness.q1.gates.common import GateOutcome, report_phase, resolve_device

    report_phase("compile")
    gate = item["gate"]
    seed = int(item["seed"])
    options = dict(item.get("options", {}))
    device = resolve_device(item.get("device"))
    kernel_source = Path(item["kernel_path"]).read_text(encoding="utf-8")
    problem_id = item["problem_id"]
    if item.get("problem_source_path"):
        problem_source = Path(item["problem_source_path"]).read_text(encoding="utf-8")
    else:
        problem_source = problem_lib.load_problem_source(problem_id)
    if device.type == "cuda":
        from harness.q1.audit.contracts import install_poison_allocator_from_env

        install_poison_allocator_from_env()

    outcomes: list[GateOutcome]
    policy_of: dict[int, str] = {}
    if gate.startswith("a"):
        from harness.q1.gates.gate_a import run_gate_a

        outcomes = [
            run_gate_a(
                problem_source,
                kernel_source,
                variant=gate,
                seed=seed,
                num_trials=int(options.get("num_trials", 5)),
                device=device,
            )
        ]
    elif gate in {"b1", "b2"}:
        from harness.q1.gates import gate_b

        if gate == "b1":
            outcomes = [gate_b.run_gate_b1(problem_source, kernel_source, seed=seed, device=device)]
        else:
            outcomes = [
                gate_b.run_gate_b2(
                    problem_source,
                    kernel_source,
                    seed=seed,
                    device=device,
                    num_perf_trials=int(options.get("num_perf_trials", 10)),
                    cpu_rows_as_kernels=bool(options.get("cpu_rows_as_kernels", False)),
                )
            ]
    elif gate == "b_native":
        from harness.q1.gates.b_native import run_b_native

        outcomes = [
            run_b_native(
                problem_source,
                kernel_source,
                clone=options.get("kernelgym_src"),
                seed=seed,
                device=device.index or 0,
            )
        ]
    elif gate == "c":
        from harness.q1.gates.gate_c import run_gate_c

        manifest = None
        if options.get("manifest_path"):
            manifest = json.loads(Path(options["manifest_path"]).read_text(encoding="utf-8"))
        outcomes = run_gate_c(
            problem_id,
            kernel_source,
            problem_source=problem_source,
            replicate_seed=seed,
            device=device,
            validity=options.get("validity", "inline"),
            manifest=manifest,
        )
    elif gate in {"A1", "A2", "A3", "A4", "A5"}:
        from harness.q1.audit import run as audit

        subject = audit.prepare(
            problem_id, problem_source, kernel_source, replicate_seed=seed, device=device
        )
        multiplier = float(options.get("multiplier", 16))
        try:
            if gate == "A1":
                outcomes = audit.run_a1(subject, multiplier=multiplier)
            elif gate == "A2":
                outcomes = audit.run_a2(subject, multiplier=multiplier)
            elif gate == "A3":
                from harness.q1.gates.gate_c import shape_manifest

                manifest = (
                    json.loads(Path(options["manifest_path"]).read_text(encoding="utf-8"))
                    if options.get("manifest_path")
                    else shape_manifest()
                )
                outcomes = audit.run_a3(
                    subject,
                    manifest_entry=manifest["problems"].get(problem_id, {}),
                    multiplier=multiplier,
                )
            elif gate == "A4":
                outcomes = audit.run_a4(subject)
            else:
                outcomes = audit.run_a5(subject)
        finally:
            subject.cleanup()
        for index, outcome in enumerate(outcomes):
            if gate in {"A4", "A5"}:
                policy_of[index] = "not-applicable"
            else:
                policy_of[index] = outcome.details.get("policy", "tf32-admissible")
    elif gate in {"A4_poison", "A4_sanitizer"}:
        from harness.q1.audit import gpu_probes

        if device.type != "cuda":
            raise SystemExit(f"{gate} needs a CUDA device")
        workdir = Path(item.get("workdir") or Path(item["kernel_path"]).parent)
        probe_item = {key: item[key] for key in ("problem_id", "kernel_path", "seed")}
        probe_item["problem_source_path"] = item.get("problem_source_path")
        if gate == "A4_poison":
            outcomes = [gpu_probes.run_poison(probe_item, workdir, options.get("so_path"))]
        else:
            from harness.q1.gates.gate_c import shape_manifest

            manifest = (
                json.loads(Path(options["manifest_path"]).read_text(encoding="utf-8"))
                if options.get("manifest_path")
                else shape_manifest()
            )
            probe_item["a3_entry"] = manifest["problems"].get(problem_id, {})
            outcomes = [gpu_probes.run_sanitizer(probe_item, workdir)]
        policy_of[0] = "not-applicable"
    elif gate == "timing":
        from harness.q1.audit import run as audit
        from harness.q1.timing import time_against_baselines

        subject = audit.prepare(
            problem_id, problem_source, kernel_source, replicate_seed=seed, device=device
        )
        try:
            inputs = audit.draw_inputs(subject.get_inputs, seed, device)
            result = time_against_baselines(
                subject.reference,
                subject.candidate,
                inputs,
                device=device,
                rounds=int(options.get("rounds", 30)),
                warmup=int(options.get("warmup", 10)),
                seed=seed,
                gpu_index=options.get("gpu_index"),
                resamples=int(options.get("resamples", 10_000)),
            )
        finally:
            subject.cleanup()
        outcomes = [GateOutcome("timing", f"native/seed-{seed}", "accept", details=result)]
        policy_of[0] = "not-applicable"
    else:
        raise SystemExit(f"unknown gate {gate}")

    from harness.q1.versions import row_code_sha256

    rows = []
    for index, outcome in enumerate(outcomes):
        gpu_seconds = outcome.wall_seconds if device.type == "cuda" else 0.0
        details = dict(outcome.details)
        details["item_key"] = item["item_key"]
        details["device"] = str(device)
        details["torch"] = torch.__version__
        outcome.details = details
        rows.append(
            outcome.to_row(
                item["kernel_id"],
                tf32_policy=policy_of.get(index, "torch-default"),
                gpu_seconds=gpu_seconds,
                seed=seed,
                run_id=item["run_id"],
                attempt=int(item["attempt"]),
                code_sha256=row_code_sha256(gate),
            )
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print("usage: python -m harness.q1.worker ITEM.json OUT.jsonl", file=sys.stderr)
        return 2
    item = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    if item.get("gate") not in WORK_GATES:
        print(f"unknown gate {item.get('gate')}", file=sys.stderr)
        return 2
    from harness.q1.schema import dump_verdict_row

    rows = _rows_for(item)
    with Path(args[1]).open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(dump_verdict_row(row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
