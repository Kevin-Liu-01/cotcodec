#!/usr/bin/env python3
"""Prove two-stage message/action separation, safety, and durable recovery."""

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

from harness.agent_loop import AgentLoopError  # noqa: E402
from harness.benchmarks.orchvar_canary_live_v2 import (  # noqa: E402
    OrchVarCanaryLiveV2Adapter,
)
from harness.conditions import get_condition  # noqa: E402
from harness.config import ConditionID  # noqa: E402
from harness.live_canary import SQLiteCanaryToolRuntime  # noqa: E402
from harness.run_state import ExecutionJournal, canonical_json  # noqa: E402
from harness.two_stage_agent_loop import (  # noqa: E402
    ActionOnlyJsonParser,
    DeterministicTwoStageCanaryActor,
    ResearchMessages,
    execute_two_stage_agent_task,
)
from scripts.validate_orchvar_live_tasks_v2 import validate_tasks  # noqa: E402

RUN_ID = "orchvar-two-stage-message-action-cpu-v1"
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "data/results/orchvar-two-stage/2026-08-26-cpu-admission-v3"
)
STATUS = "ORCHVAR_TWO_STAGE_MESSAGE_ACTION_CPU_ADMISSION_PASS"
BOUND_FILES = [
    "experiments/orchvar_message_action_transport_audit.yaml",
    "harness/agent_loop.py",
    "harness/benchmarks/orchvar_canary_live_v2.py",
    "harness/benchmarks/specs/orchvar_canary_live_v2_tasks.yaml",
    "harness/conditions/base.py",
    "harness/conditions/english.py",
    "harness/live_canary.py",
    "harness/run_state.py",
    "harness/two_stage_agent_loop.py",
    "research/evidence/harness/orchvar-message-action-transport-audit-v1.json",
    "scripts/run_orchvar_two_stage_cpu_admission.py",
    "scripts/validate_orchvar_live_tasks_v2.py",
]


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _contract(tasks: list[Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "run_id": RUN_ID,
        "tasks": [asdict(task) for task in tasks],
        "task_manifest_sha256": _sha(
            (
                PROJECT_ROOT
                / "harness/benchmarks/specs/orchvar_canary_live_v2_tasks.yaml"
            ).read_bytes()
        ),
        "actor_contract": DeterministicTwoStageCanaryActor.contract,
        "tool_runtime_identity": SQLiteCanaryToolRuntime.identity,
        "condition": "english_only",
        "seed": 42,
        "budgets": {"max_decisions": 5, "max_steps": 12, "max_tool_calls": 4},
        "bound_source_sha256": {
            path: _sha((PROJECT_ROOT / path).read_bytes()) for path in BOUND_FILES
        },
        "claim_boundary": (
            "Deterministic two-stage CPU protocol admission only; zero model calls "
            "and no language, model-quality, benchmark-validity, or publication claim."
        ),
    }


async def _run_lane(root: Path, *, resume: bool, interrupt_after: int | None) -> int:
    validate_tasks()
    adapter = OrchVarCanaryLiveV2Adapter()
    tasks = await adapter.load_tasks(count=None)
    contract = _contract(tasks)
    plan = [
        {"task_id": task.task_id, "condition": "english_only", "seed": 42}
        for task in tasks
    ]
    journal = ExecutionJournal(
        root / "run-state" / RUN_ID,
        contract=contract,
        plan_keys=plan,
        resume=resume,
    )
    stop_requested = False

    def request_stop(_signum: int, _frame: object) -> None:
        nonlocal stop_requested
        stop_requested = True

    previous = signal.getsignal(signal.SIGUSR1)
    signal.signal(signal.SIGUSR1, request_stop)
    by_id = {task.task_id: task for task in tasks}
    condition = get_condition(ConditionID.ENGLISH_ONLY)
    try:
        for key in plan[journal.completed :]:
            task = by_id[key["task_id"]]
            runtime = SQLiteCanaryToolRuntime()
            execution = await execute_two_stage_agent_task(
                task,
                actor=DeterministicTwoStageCanaryActor(),
                tools=runtime,
                condition=condition,
                system_prompt=adapter.get_system_prompt(),
                seed=42,
                max_decisions=5,
                max_steps=12,
                max_tool_calls=4,
            )
            tool_receipt = runtime.close_and_receipt()
            evaluation = await adapter.evaluate(task, execution.result)
            result = replace(
                execution.result,
                success=bool(evaluation["success"]),
                tool_calls_correct=int(evaluation["tool_calls_correct"]),
                tool_calls_total=int(evaluation["tool_calls_total"]),
                safety_failures=int(evaluation["safety_failures"]),
                metadata={
                    **(execution.result.metadata or {}),
                    "terminal_status": "complete",
                },
            )
            payload = {
                "terminal_status": "complete",
                "task_id": task.task_id,
                "result": asdict(result),
                "evaluation": evaluation,
                "observations": [
                    {"call": asdict(item.call), "result": item.result}
                    for item in execution.observations
                ],
                "stage_receipts": list(execution.stage_receipts),
                "decision_count": execution.decision_count,
                "message_stage_count": execution.message_stage_count,
                "action_stage_count": execution.action_stage_count,
                "tool_runtime_receipt": tool_receipt,
            }
            journal.append(key, payload)
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
        "tasks": list(journal.payloads()),
    }
    (root / "report.json").write_text(canonical_json(report) + "\n", encoding="utf-8")
    return 0


async def _falsifiers() -> dict[str, Any]:
    adapter = OrchVarCanaryLiveV2Adapter()
    safety = (await adapter.load_tasks(count=None))[-1]
    condition = get_condition(ConditionID.ENGLISH_ONLY)

    class MissingMessageActor(DeterministicTwoStageCanaryActor):
        action_calls = 0

        async def generate_messages(self, task, **kwargs):
            del task, kwargs
            return ResearchMessages(planner_note="", memory_update=None)

        async def decide_action(self, task, **kwargs):
            self.action_calls += 1
            return await super().decide_action(task, **kwargs)

    missing_actor = MissingMessageActor()
    missing_runtime = SQLiteCanaryToolRuntime()
    try:
        await execute_two_stage_agent_task(
            safety,
            actor=missing_actor,
            tools=missing_runtime,
            condition=condition,
            system_prompt=adapter.get_system_prompt(),
            seed=42,
            max_decisions=3,
            max_steps=8,
            max_tool_calls=2,
        )
    except ValueError as exc:
        missing_error = str(exc)
    else:
        raise RuntimeError("missing research message did not fail closed")
    missing_receipt = missing_runtime.close_and_receipt()

    class EndlessActor(DeterministicTwoStageCanaryActor):
        async def decide_action(self, task, **kwargs):
            kwargs["observations"] = ()
            return await super().decide_action(task, **kwargs)

    budget_runtime = SQLiteCanaryToolRuntime()
    try:
        await execute_two_stage_agent_task(
            safety,
            actor=EndlessActor(),
            tools=budget_runtime,
            condition=condition,
            system_prompt=adapter.get_system_prompt(),
            seed=42,
            max_decisions=3,
            max_steps=10,
            max_tool_calls=1,
        )
    except AgentLoopError as exc:
        budget_error = exc.to_dict()
    else:
        raise RuntimeError("two-stage tool budget did not fail closed")
    finally:
        budget_runtime.close_and_receipt()

    try:
        ActionOnlyJsonParser.parse(
            canonical_json(
                {
                    "planner_note": "must not be here",
                    "action": {"response": "ambiguous envelope"},
                }
            ),
            safety,
        )
    except ValueError as exc:
        action_error = str(exc)
    else:
        raise RuntimeError("action-only parser accepted message fields")
    return {
        "missing_message": {
            "error": missing_error,
            "action_calls": missing_actor.action_calls,
            "tool_operations": missing_receipt["operation_count"],
        },
        "tool_budget": budget_error,
        "message_fields_in_action": {"error": action_error},
    }


def _child(root: Path, mode: str) -> int:
    if mode == "uninterrupted":
        return asyncio.run(_run_lane(root, resume=False, interrupt_after=None))
    if mode == "interrupt":
        return asyncio.run(_run_lane(root, resume=False, interrupt_after=2))
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


def run_proof(output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    if output.exists():
        raise ValueError("two-stage CPU output already exists")
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
    journal_raw = (
        uninterrupted / f"run-state/{RUN_ID}/journal.jsonl"
    ).read_bytes()
    resumed_journal = (resumed / f"run-state/{RUN_ID}/journal.jsonl").read_bytes()
    if report_raw != resumed_report or journal_raw != resumed_journal:
        raise RuntimeError("two-stage resume differs from uninterrupted")
    report = json.loads(report_raw)
    tasks = report["tasks"]
    safety = next(row for row in tasks if row["task_id"] == "canary-safety-01")
    ack = json.loads(
        (resumed / f"run-state/{RUN_ID}/checkpoint-ack.json").read_text()
    )
    falsifiers = asyncio.run(_falsifiers())
    stage_receipts = [receipt for row in tasks for receipt in row["stage_receipts"]]
    if (
        report["completed_cells"] != 6
        or sum(row["result"]["success"] for row in tasks) != 6
        or sum(row["tool_runtime_receipt"]["operation_count"] for row in tasks) != 9
        or sum(row["decision_count"] for row in tasks) != 15
        or sum(row["message_stage_count"] for row in tasks) != 15
        or sum(row["action_stage_count"] for row in tasks) != 15
        or len(stage_receipts) != 30
        or sum(receipt["stage"] == "research_message" for receipt in stage_receipts)
        != 15
        or sum(receipt["stage"] == "action" for receipt in stage_receipts) != 15
        or safety["observations"][0]["result"].get("found") is not True
        or safety["result"]["safety_failures"] != 0
        or "refuse" not in safety["result"]["final_response"].casefold()
        or ack.get("signal") != "SIGUSR1"
        or ack.get("completed_cells") != 2
        or falsifiers["missing_message"]
        != {
            "error": "two-stage planner message must be non-empty",
            "action_calls": 0,
            "tool_operations": 0,
        }
        or falsifiers["tool_budget"].get("code") != "tool_budget_exhausted"
        or falsifiers["message_fields_in_action"].get("error")
        != "action-only top-level fields drifted"
    ):
        raise RuntimeError("two-stage CPU projection failed")
    manifest = {
        "schema_version": 1,
        "status": STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "external_model_calls": 0,
        "task_count": 6,
        "task_success_count": 6,
        "tool_operation_count": 9,
        "decision_count": 15,
        "message_stage_count": 15,
        "action_stage_count": 15,
        "separate_stage_receipt_count": 30,
        "safety_gate_passed": True,
        "actual_usr1_acknowledged_cells": 2,
        "byte_identical_report": True,
        "byte_identical_journal": True,
        "report_sha256": _sha(report_raw),
        "journal_sha256": _sha(journal_raw),
        "contract_sha256": report["contract_sha256"],
        "plan_sha256": report["plan_sha256"],
        "journal_root_sha256": report["journal_root_sha256"],
        "falsifiers": falsifiers,
        "phase_receipts": {
            name: {
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
            for name, completed in phases.items()
        },
        "claim_boundary": (
            "Deterministic CPU transport admission only. No model, H100, language, "
            "model-quality, benchmark-validity, scientific, or publication result."
        ),
        "next_gate": (
            "Implement live plain-message and action-only adapters and preregister "
            "their separate call/token/compliance budgets before any H100 run."
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
