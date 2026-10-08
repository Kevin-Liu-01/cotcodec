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
    "audit_hole",
    # fidelity only (preregistration section 8.2, criterion 1): unmodified
    # upstream code next to our implementation; never part of a ladder gate
    "a_upstream_44130946",
    "a_upstream_423217d9",
    "c1_kbv_compat",
    "c1_kbv_native",
    # reference items (decision D31, ``harness.q1.refstore``): no candidate, rows go
    # to the reference journal, never to a ladder gate or audit tier
    "ref_a",
    "ref_a_head",
    "ref_c",
    "ref_A1",
    "ref_A2",
    "ref_A3",
    "ref_A5",
)
#: Fidelity gates whose rows never enter a ladder gate or audit tier.
FIDELITY_GATES = (
    "b_native",
    "a_upstream_44130946",
    "a_upstream_423217d9",
    "c1_kbv_compat",
    "c1_kbv_native",
)
GATE_A_VARIANTS = ("a", "a_1e-3", "a_head_1e-4", "a_head_1e-2", "a_static")
#: ``details.reason`` of the row written when building or serialising rows fails.
HARNESS_ROW_FAILURE = "infra_failure-harness-row"


def _outcomes_for(item: Mapping[str, Any]) -> tuple[list[Any], dict[int, str], Any]:
    """Run the item's gate or channel. Candidate code runs only inside this function."""
    from harness.q1 import problems as problem_lib
    from harness.q1.gates.common import GateOutcome, report_phase, resolve_device

    report_phase("compile")
    gate = item["gate"]
    seed = int(item["seed"])
    options = dict(item.get("options", {}))
    device = resolve_device(item.get("device"))
    if gate.startswith("ref_"):
        from harness.q1 import refstore

        # A reference item loads no candidate (it stays in the compile phase).
        return refstore.reference_outcome(item), {0: "not-applicable"}, device
    # Consumer items read reference entries from here when given (decision D31).
    store = options.get("reference_store")
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
    if gate in GATE_A_VARIANTS:
        from harness.q1.gates.gate_a import run_gate_a

        outcomes = [
            run_gate_a(
                problem_source,
                kernel_source,
                variant=gate,
                seed=seed,
                num_trials=int(options.get("num_trials", 5)),
                device=device,
                problem_id=problem_id,
                reference_store=store,
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

        # Upstream loads the candidate itself; from here on candidate code runs.
        report_phase("correctness")
        outcomes = [
            run_b_native(
                problem_source,
                kernel_source,
                clone=options.get("kernelgym_src"),
                seed=seed,
                device=device.index or 0,
            )
        ]
    elif gate in {"a_upstream_44130946", "a_upstream_423217d9"}:
        import time

        from harness.q1.gates.gate_a import upstream_gate_a

        revision = gate.rsplit("_", 1)[1]
        start = time.perf_counter()
        report_phase("correctness")
        result = upstream_gate_a(
            problem_source,
            kernel_source,
            revision=revision,
            seed=seed,
            num_trials=int(options.get("num_trials", 5)),
            device=device.index or 0,
        )
        if result["correctness"] is None:
            verdict = "error"
        else:
            verdict = "accept" if result["correctness"] else "reject"
        outcomes = [
            GateOutcome(
                gate,
                f"native/seed-{seed}",
                verdict,
                tolerance=1e-2 if revision == "44130946" else 1e-4,
                details={"kernelbench_revision": revision, **result},
                wall_seconds=time.perf_counter() - start,
            )
        ]
    elif gate == "c1_kbv_compat":
        from harness.q1.gates.gate_c import run_gate_c

        # Gate (c1) in KBV-compatibility mode (inherited RNG, every tensor cast to
        # fp32, no validity filter), renamed so its rows never count as c1.
        renamed = {"c1": "c1_kbv_compat", "c_kbv_raw": "c1_kbv_compat_raw"}
        outcomes = []
        for outcome in run_gate_c(
            problem_id,
            kernel_source,
            problem_source=problem_source,
            families=("c1",),
            replicate_seed=seed,
            device=device,
            validity="off",
            kbv_compat=True,
        ):
            if outcome.gate in renamed:
                outcome.gate = renamed[outcome.gate]
                outcomes.append(outcome)
    elif gate == "c1_kbv_native":
        from harness.q1.gates.kbv_native import run_kbv_native

        outcomes = run_kbv_native(
            problem_id,
            kernel_source,
            clone=options.get("kbv_src"),
            seed=seed,
            device=device,
            ours_problem_source=problem_source,
        )
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
            reference_store=store,
        )
    elif gate in {"A1", "A2", "A3", "A4", "A5"}:
        from harness.q1.audit import run as audit

        subject = audit.prepare(
            problem_id, problem_source, kernel_source, replicate_seed=seed, device=device
        )
        multiplier = float(options.get("multiplier", 16))
        try:
            if gate == "A1":
                outcomes = audit.run_a1(subject, multiplier=multiplier, reference_store=store)
            elif gate == "A2":
                outcomes = audit.run_a2(subject, multiplier=multiplier, reference_store=store)
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
                    reference_store=store,
                )
            elif gate == "A4":
                outcomes = audit.run_a4(subject)
            else:
                outcomes = audit.run_a5(subject, reference_store=store)
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
    elif gate == "audit_hole":
        from harness.q1.audit import replay

        outcomes = replay.run_replays(
            problem_id,
            problem_source,
            kernel_source,
            replicate_seed=seed,
            device=device,
            rejections=list(options.get("rejections", [])),
            multiplier=float(options.get("multiplier", 16)),
            manifest_path=options.get("manifest_path"),
        )
        for index, outcome in enumerate(outcomes):
            policy_of[index] = outcome.details.get("policy", "tf32-admissible")
    else:
        raise SystemExit(f"unknown gate {gate}")
    return outcomes, policy_of, device


def _rows_from(
    item: Mapping[str, Any], outcomes: list[Any], policy_of: Mapping[int, str], device: Any
) -> list[dict[str, Any]]:
    """Verdict rows from finished outcomes. Pure harness code: no candidate code runs here."""
    import torch

    from harness.q1.versions import row_code_sha256

    seed = int(item["seed"])
    gate = item["gate"]
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

    # Candidate code runs only in _outcomes_for. An exception there propagates
    # and the runner attributes the dead worker by phase (preregistration
    # section 10). Building, validating and serialising rows afterwards is
    # harness code: a failure there is an infrastructure failure, never a
    # candidate rejection, so it becomes one ``error`` row.
    outcomes, policy_of, device = _outcomes_for(item)
    store = dict(item.get("options", {})).get("reference_store")
    if store and not str(item.get("gate", "")).startswith("ref_"):
        from harness.q1 import refstore

        refstore.write_uses(store, item)  # best effort; never part of a row
    try:
        text = "".join(
            dump_verdict_row(row) for row in _rows_from(item, outcomes, policy_of, device)
        )
    except Exception as exc:  # harness fault after every candidate call returned
        text = dump_verdict_row(harness_failure_row(item, exc, outcomes=len(outcomes)))
    Path(args[1]).write_text(text, encoding="utf-8")
    return 0


def harness_failure_row(item: Mapping[str, Any], exc: BaseException, **facts: Any) -> dict:
    """The single ``error`` row written when row construction or serialisation fails."""
    from harness.q1.gates.outcome import exception_details
    from harness.q1.schema import make_verdict_row
    from harness.q1.versions import row_code_sha256

    seed = int(item["seed"])
    return make_verdict_row(
        kernel_id=item["kernel_id"],
        gate=item["gate"],
        config_id=f"item/seed-{seed}",
        verdict="error",
        tf32_policy="not-applicable",
        gpu_seconds=0.0,
        wall_seconds=0.0,
        details={
            "reason": HARNESS_ROW_FAILURE,
            "item_key": item.get("item_key"),
            **facts,
            **exception_details(exc),
        },
        seed=seed,
        run_id=item["run_id"],
        attempt=int(item["attempt"]),
        code_sha256=row_code_sha256(item["gate"]),
    )


if __name__ == "__main__":
    raise SystemExit(main())
