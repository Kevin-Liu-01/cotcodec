#!/usr/bin/env python3
"""Prove tool-error observation transport and durable CPU recovery."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import signal
import subprocess
import sys
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.agent_loop import ToolCall  # noqa: E402
from harness.benchmarks.orchvar_canary_live_v2 import (  # noqa: E402
    OrchVarCanaryLiveV2Adapter,
)
from harness.conditions import get_condition  # noqa: E402
from harness.config import ConditionID  # noqa: E402
from harness.receipted_tool_runtime import (  # noqa: E402
    ReceiptedSQLiteCanaryToolRuntime,
)
from harness.run_state import ExecutionJournal, canonical_json  # noqa: E402
from harness.two_stage_agent_loop import (  # noqa: E402
    DeterministicTwoStageCanaryActor,
    FixedAction,
    ResearchMessages,
    execute_two_stage_agent_task,
)
from scripts.validate_orchvar_tool_error_transport_experiment import (  # noqa: E402
    validate_experiment,
)

RUN_ID = "orchvar-tool-error-transport-cpu-v1"
STATUS = "ORCHVAR_TOOL_ERROR_TRANSPORT_CPU_ADMISSION_PASS"
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data/results/orchvar-tool-error-transport/2026-08-26-cpu-admission-v1"
)
BOUND_FILES = [
    "experiments/orchvar_tool_error_transport_cpu.yaml",
    "harness/agent_loop.py",
    "harness/benchmarks/orchvar_canary_live_v2.py",
    "harness/benchmarks/specs/orchvar_canary_live_v2_tasks.yaml",
    "harness/conditions/base.py",
    "harness/conditions/english.py",
    "harness/live_canary.py",
    "harness/receipted_tool_runtime.py",
    "harness/run_state.py",
    "harness/two_stage_agent_loop.py",
    "research/evidence/harness/"
    "orchvar-qwen35-two-stage-live-partial-negative-job341.json",
    "scripts/run_orchvar_tool_error_transport_cpu_admission.py",
    "scripts/validate_orchvar_tool_error_transport_experiment.py",
]


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class DuplicateRecoveryActor(DeterministicTwoStageCanaryActor):
    """Repeat one mutation, observe its stable error, then finalize."""

    identity = "deterministic-duplicate-recovery-v1"
    contract = {
        "schema_version": 1,
        "identity": identity,
        "protocol": "message-then-action-two-stage-v1",
        "tool_sequence": [
            "create_handoff_note",
            "create_handoff_note",
            "final",
        ],
        "requires_error_observation_before_final": True,
    }

    def __init__(self) -> None:
        self.error_observed_before_final = False

    async def generate_messages(self, task, **kwargs):
        observations = kwargs["observations"]
        if len(observations) == 0:
            return ResearchMessages(
                planner_note="Create the exact handoff note and preserve both qualifiers.",
                memory_update=(
                    "Case COSMETIC-01 requires cosmetic shipping damage and a waiver "
                    "of replacement rights."
                ),
            )
        if len(observations) == 1:
            return ResearchMessages(
                planner_note=(
                    "The first mutation succeeded; repeat it to exercise the admitted "
                    "constraint-error transport."
                ),
                memory_update=None,
            )
        return ResearchMessages(
            planner_note=(
                "The repeated mutation returned a non-retryable constraint error; "
                "finalize without another tool attempt."
            ),
            memory_update=None,
        )

    async def decide_action(self, task, **kwargs):
        observations = kwargs["observations"]
        if len(observations) < 2:
            return FixedAction(
                mode="tool",
                tool_call=ToolCall(
                    "create_handoff_note", {"case_id": "COSMETIC-01"}
                ),
            )
        expected = {
            "ok": False,
            "error": {
                "code": "sqlite_constraint_violation",
                "tool": "create_handoff_note",
                "message": "tool mutation violated a uniqueness constraint",
                "retryable": False,
            },
        }
        if observations[-1].result != expected:
            raise RuntimeError("duplicate actor did not observe the admitted error")
        self.error_observed_before_final = True
        return FixedAction(
            mode="final",
            final_response=(
                "The handoff note preserves that shipping damage is cosmetic and that "
                "the customer waives replacement rights."
            ),
        )


def _contract(tasks: list[Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "run_id": RUN_ID,
        "task_roster": [asdict(task) for task in tasks],
        "condition": "english_only",
        "seed": 42,
        "baseline_actor_contract": DeterministicTwoStageCanaryActor.contract,
        "duplicate_actor_contract": DuplicateRecoveryActor.contract,
        "runtime_contract": ReceiptedSQLiteCanaryToolRuntime.contract,
        "budgets": {
            "external_model_calls": 0,
            "max_cells": 7,
            "max_tool_attempts": 12,
            "max_decisions_per_cell": 5,
            "max_steps_per_cell": 12,
        },
        "bound_source_sha256": {
            path: _sha((PROJECT_ROOT / path).read_bytes()) for path in BOUND_FILES
        },
        "claim_boundary": (
            "Deterministic CPU tool-error transport and durability admission only; "
            "no live-model, benchmark-validity, scientific, or publication claim."
        ),
    }


def _plan(tasks: list[Any]) -> list[dict[str, Any]]:
    return [
        {"scenario": "baseline", "task_id": task.task_id, "seed": 42}
        for task in tasks
    ] + [
        {
            "scenario": "duplicate_mutation_recovery",
            "task_id": "canary-verbosity-sensitive-01",
            "seed": 42,
        }
    ]


async def _run_lane(root: Path, *, resume: bool, interrupt_after: int | None) -> int:
    validate_experiment()
    adapter = OrchVarCanaryLiveV2Adapter()
    tasks = await adapter.load_tasks(count=None)
    by_id = {task.task_id: task for task in tasks}
    plan = _plan(tasks)
    journal = ExecutionJournal(
        root / "run-state" / RUN_ID,
        contract=_contract(tasks),
        plan_keys=plan,
        resume=resume,
    )
    stop_requested = False

    def request_stop(_signum: int, _frame: object) -> None:
        nonlocal stop_requested
        stop_requested = True

    previous = signal.getsignal(signal.SIGUSR1)
    signal.signal(signal.SIGUSR1, request_stop)
    condition = get_condition(ConditionID.ENGLISH_ONLY)
    try:
        for key in plan[journal.completed :]:
            task = by_id[key["task_id"]]
            runtime = ReceiptedSQLiteCanaryToolRuntime()
            duplicate_actor: DuplicateRecoveryActor | None = None
            if key["scenario"] == "baseline":
                actor = DeterministicTwoStageCanaryActor()
            else:
                duplicate_actor = DuplicateRecoveryActor()
                actor = duplicate_actor
            execution = await execute_two_stage_agent_task(
                task,
                actor=actor,
                tools=runtime,
                condition=condition,
                system_prompt=adapter.get_system_prompt(),
                seed=42,
                max_decisions=5,
                max_steps=12,
                max_tool_calls=4,
            )
            tool_receipt = runtime.close_and_receipt()
            if key["scenario"] == "baseline":
                evaluation = await adapter.evaluate(task, execution.result)
                result = replace(
                    execution.result,
                    success=bool(evaluation["success"]),
                    tool_calls_correct=int(evaluation["tool_calls_correct"]),
                    tool_calls_total=int(evaluation["tool_calls_total"]),
                    safety_failures=int(evaluation["safety_failures"]),
                )
                protocol_passed = bool(result.success)
                error_observed = False
            else:
                evaluation = None
                result = execution.result
                protocol_passed = bool(
                    duplicate_actor is not None
                    and duplicate_actor.error_observed_before_final
                    and tool_receipt["attempt_count"] == 2
                    and tool_receipt["success_count"] == 1
                    and tool_receipt["error_count"] == 1
                )
                error_observed = bool(
                    duplicate_actor and duplicate_actor.error_observed_before_final
                )
            payload = {
                "terminal_status": "complete",
                "scenario": key["scenario"],
                "task_id": task.task_id,
                "protocol_passed": protocol_passed,
                "error_observed_before_final": error_observed,
                "result": asdict(result),
                "evaluation": evaluation,
                "observations": [
                    {"call": asdict(item.call), "result": item.result}
                    for item in execution.observations
                ],
                "stage_receipts": list(execution.stage_receipts),
                "decision_count": execution.decision_count,
                "tool_runtime_receipt": tool_receipt,
            }
            journal.append(key, payload)
            attempts = sum(
                row["tool_runtime_receipt"]["attempt_count"]
                for row in journal.payloads()
            )
            if attempts > 12:
                raise RuntimeError("tool-error CPU attempt budget exhausted")
            if interrupt_after is not None and journal.completed == interrupt_after:
                signal.raise_signal(signal.SIGUSR1)
            if stop_requested:
                journal.acknowledge_interrupt("SIGUSR1")
                return 75
    finally:
        signal.signal(signal.SIGUSR1, previous)
    journal.complete()
    report = {
        "schema_version": 1,
        "status": "COMPLETE",
        "run_id": RUN_ID,
        "contract_sha256": journal.contract_sha256,
        "plan_sha256": journal.plan_sha256,
        "journal_root_sha256": journal.journal_root_sha256,
        "completed_cells": journal.completed,
        "cells": list(journal.payloads()),
    }
    (root / "report.json").write_text(canonical_json(report) + "\n", encoding="utf-8")
    return 0


def _child(root: Path, mode: str) -> int:
    if mode == "uninterrupted":
        return asyncio.run(_run_lane(root, resume=False, interrupt_after=None))
    if mode == "interrupt":
        return asyncio.run(_run_lane(root, resume=False, interrupt_after=3))
    if mode == "resume":
        return asyncio.run(_run_lane(root, resume=True, interrupt_after=None))
    raise ValueError(f"unknown mode: {mode}")


def _invoke(root: Path, mode: str) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(PROJECT_ROOT)
    return subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "_child", str(root), mode],
        cwd=PROJECT_ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def _unexpected_exception_falsifier() -> dict[str, Any]:
    class BrokenDelegate:
        async def execute(self, call):
            del call
            raise RuntimeError("unexpected transport failure")

        def close_and_receipt(self):
            return {"identity": "broken"}

    async def run() -> dict[str, Any]:
        runtime = ReceiptedSQLiteCanaryToolRuntime(BrokenDelegate())
        try:
            await runtime.execute(
                ToolCall("create_handoff_note", {"case_id": "COSMETIC-01"})
            )
        except RuntimeError as exc:
            error = {"type": type(exc).__name__, "detail": str(exc)}
        else:
            raise RuntimeError("unexpected delegate exception was swallowed")
        receipt = runtime.close_and_receipt()
        return {"error": error, "attempt_count": receipt["attempt_count"]}

    return asyncio.run(run())


def run_proof(output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    if output.exists():
        raise ValueError("tool-error CPU output already exists")
    output.mkdir(parents=True)
    uninterrupted = output / "uninterrupted"
    resumed = output / "interrupted-resumed"
    phases = {
        "uninterrupted": _invoke(uninterrupted, "uninterrupted"),
        "interrupt": _invoke(resumed, "interrupt"),
        "resume": _invoke(resumed, "resume"),
    }
    for name, expected in {"uninterrupted": 0, "interrupt": 75, "resume": 0}.items():
        completed = phases[name]
        if completed.returncode != expected:
            raise RuntimeError(f"{name} failed: {completed.returncode}: {completed.stderr}")
    report_raw = (uninterrupted / "report.json").read_bytes()
    resumed_report = (resumed / "report.json").read_bytes()
    journal_raw = (uninterrupted / f"run-state/{RUN_ID}/journal.jsonl").read_bytes()
    resumed_journal = (resumed / f"run-state/{RUN_ID}/journal.jsonl").read_bytes()
    if report_raw != resumed_report or journal_raw != resumed_journal:
        raise RuntimeError("tool-error resume differs from uninterrupted")
    report = json.loads(report_raw)
    cells = report["cells"]
    baseline = [cell for cell in cells if cell["scenario"] == "baseline"]
    duplicate = cells[-1]
    ack = json.loads(
        (resumed / f"run-state/{RUN_ID}/checkpoint-ack.json").read_text()
    )
    falsifier = _unexpected_exception_falsifier()
    totals = {
        "attempts": sum(cell["tool_runtime_receipt"]["attempt_count"] for cell in cells),
        "successes": sum(cell["tool_runtime_receipt"]["success_count"] for cell in cells),
        "errors": sum(cell["tool_runtime_receipt"]["error_count"] for cell in cells),
        "decisions": sum(cell["decision_count"] for cell in cells),
    }
    if (
        report["completed_cells"] != 7
        or sum(cell["protocol_passed"] for cell in baseline) != 6
        or duplicate["protocol_passed"] is not True
        or duplicate["error_observed_before_final"] is not True
        or totals != {"attempts": 11, "successes": 10, "errors": 1, "decisions": 18}
        or duplicate["tool_runtime_receipt"]["delegate_receipt"]["operation_count"]
        != 1
        or ack.get("signal") != "SIGUSR1"
        or ack.get("completed_cells") != 3
        or falsifier
        != {
            "error": {
                "type": "RuntimeError",
                "detail": "unexpected transport failure",
            },
            "attempt_count": 0,
        }
    ):
        raise RuntimeError("tool-error CPU projection failed")
    manifest = {
        "schema_version": 1,
        "status": STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "external_model_calls": 0,
        "completed_cells": 7,
        "baseline_successes": 6,
        "tool_attempt_count": totals["attempts"],
        "tool_success_count": totals["successes"],
        "tool_error_count": totals["errors"],
        "decision_count": totals["decisions"],
        "duplicate_error_observed_before_final": True,
        "unexpected_exception_falsifier": falsifier,
        "actual_usr1_acknowledged_cells": 3,
        "byte_identical_report": True,
        "byte_identical_journal": True,
        "report_sha256": _sha(report_raw),
        "journal_sha256": _sha(journal_raw),
        "contract_sha256": report["contract_sha256"],
        "plan_sha256": report["plan_sha256"],
        "journal_root_sha256": report["journal_root_sha256"],
        "phase_receipts": {
            name: {
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
            for name, completed in phases.items()
        },
        "claim_boundary": (
            "Deterministic CPU tool-error transport admission only. No live-model, "
            "benchmark-validity, scientific, or publication result."
        ),
        "next_gate": (
            "Bind this exact-source runtime into a separately preregistered runner "
            "doctor; do not resume or rerun live job 341."
        ),
    }
    (output / "manifest.json").write_text(
        canonical_json(manifest) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    if len(sys.argv) >= 2 and sys.argv[1] == "_child":
        return _child(Path(sys.argv[2]).resolve(), sys.argv[3])
    output = Path(sys.argv[1]).resolve() if len(sys.argv) == 2 else DEFAULT_OUTPUT
    manifest = run_proof(output)
    print(
        canonical_json(
            {
                "status": manifest["status"],
                "report_sha256": manifest["report_sha256"],
                "journal_root_sha256": manifest["journal_root_sha256"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
