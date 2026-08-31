#!/usr/bin/env python3
"""Prove iterative OrchVar tool-result conditioning and cell-level recovery."""

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

from harness.agent_loop import AgentLoopError, ToolCall  # noqa: E402
from harness.benchmarks.orchvar_canary_live_v2 import (  # noqa: E402
    OrchVarCanaryLiveV2Adapter,
)
from harness.conditions import get_condition  # noqa: E402
from harness.config import ConditionID  # noqa: E402
from harness.iterative_agent_loop import (  # noqa: E402
    DeterministicIterativeCanaryActor,
    IterativeAction,
    execute_iterative_agent_task,
)
from harness.iterative_live_canary import (  # noqa: E402
    DeterministicStructuralCanaryActor,
)
from harness.live_canary import SQLiteCanaryToolRuntime  # noqa: E402
from harness.run_state import ExecutionJournal, canonical_json  # noqa: E402
from scripts.validate_orchvar_live_tasks_v2 import (  # noqa: E402
    DEFAULT_TASKS,
    validate_tasks,
)

RUN_ID = "orchvar-iterative-cpu-admission-v1"
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "data/results/orchvar-iterative/2026-08-26-cpu-admission-v1"
)
BOUND_FILES = [
    "harness/agent_loop.py",
    "harness/benchmarks/orchvar_canary_live_v2.py",
    "harness/benchmarks/specs/orchvar_canary_live_v2_tasks.yaml",
    "harness/iterative_agent_loop.py",
    "harness/iterative_live_canary.py",
    "harness/live_canary.py",
    "harness/run_state.py",
    "scripts/run_orchvar_iterative_cpu_admission.py",
    "scripts/validate_orchvar_live_tasks_v2.py",
]
STRUCTURAL_PROTOCOL_ENV = "COTCODEC_ITERATIVE_CPU_PROTOCOL"


def _actor():
    if os.environ.get(STRUCTURAL_PROTOCOL_ENV) == "structural-json-v2":
        return DeterministicStructuralCanaryActor()
    return DeterministicIterativeCanaryActor()


def _status() -> str:
    if os.environ.get(STRUCTURAL_PROTOCOL_ENV) == "structural-json-v2":
        return "ORCHVAR_ITERATIVE_STRUCTURAL_JSON_V2_CPU_ADMISSION_PASS"
    return "ORCHVAR_ITERATIVE_TOOL_RESULT_CPU_ADMISSION_PASS"


def _message(message) -> dict[str, Any]:
    return {
        "step": message.step,
        "role": message.role,
        "type": message.message_type.value,
        "language": message.language,
        "content": message.content,
        "metadata": message.metadata,
    }


def _contract(tasks: list[Any]) -> dict[str, Any]:
    source_sha256 = {
        relative: hashlib.sha256((PROJECT_ROOT / relative).read_bytes()).hexdigest()
        for relative in BOUND_FILES
    }
    return {
        "schema_version": 1,
        "run_id": RUN_ID,
        "task_manifest_sha256": hashlib.sha256(DEFAULT_TASKS.read_bytes()).hexdigest(),
        "tasks": [asdict(task) for task in tasks],
        "actor_contract": _actor().contract,
        "protocol_variant": os.environ.get(STRUCTURAL_PROTOCOL_ENV, "explicit-type-v1"),
        "tool_runtime_identity": SQLiteCanaryToolRuntime.identity,
        "condition": "english_only",
        "seed": 42,
        "budgets": {"max_decisions": 5, "max_steps": 12, "max_tool_calls": 4},
        "bound_source_sha256": source_sha256,
        "claim_boundary": (
            "Deterministic CPU protocol admission only; not a live-model, language, "
            "model-quality, multiturn, H100, benchmark-validity, or publication result."
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
    task_by_id = {task.task_id: task for task in tasks}
    condition = get_condition(ConditionID.ENGLISH_ONLY)
    try:
        for key in plan[journal.completed :]:
            task = task_by_id[key["task_id"]]
            runtime = SQLiteCanaryToolRuntime()
            execution = await execute_iterative_agent_task(
                task,
                actor=_actor(),
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
                "messages": [_message(message) for message in execution.messages],
                "observations": [
                    {"call": asdict(observation.call), "result": observation.result}
                    for observation in execution.observations
                ],
                "decision_count": execution.decision_count,
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
    report_path = root / "report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(canonical_json(report) + "\n", encoding="utf-8")
    return 0


async def _budget_falsifier() -> dict[str, str]:
    class EndlessActor:
        identity = "iterative-budget-falsifier-v1"

        async def decide(self, task, **kwargs) -> IterativeAction:
            del task, kwargs
            return IterativeAction(
                planner_note="Call again.",
                memory_update=None,
                mode="tool",
                tool_call=ToolCall(
                    "search_knowledge_base", {"query": "retrieved policy document"}
                ),
            )

    adapter = OrchVarCanaryLiveV2Adapter()
    task = (await adapter.load_tasks(count=None))[-1]
    runtime = SQLiteCanaryToolRuntime()
    try:
        await execute_iterative_agent_task(
            task,
            actor=EndlessActor(),
            tools=runtime,
            condition=get_condition(ConditionID.ENGLISH_ONLY),
            system_prompt=adapter.get_system_prompt(),
            seed=42,
            max_decisions=3,
            max_steps=10,
            max_tool_calls=1,
        )
    except AgentLoopError as exc:
        if exc.code != "tool_budget_exhausted":
            raise
        return exc.to_dict()
    finally:
        runtime.close_and_receipt()
    raise RuntimeError("iterative tool-budget falsifier did not fail closed")


def _child(root: Path, mode: str) -> int:
    if mode == "uninterrupted":
        return asyncio.run(_run_lane(root, resume=False, interrupt_after=None))
    if mode == "interrupt":
        return asyncio.run(_run_lane(root, resume=False, interrupt_after=2))
    if mode == "resume":
        return asyncio.run(_run_lane(root, resume=True, interrupt_after=None))
    raise ValueError(f"unknown child mode: {mode}")


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
        raise ValueError("iterative CPU admission output already exists")
    output.mkdir(parents=True)
    uninterrupted = output / "uninterrupted"
    resumed = output / "interrupted-resumed"
    phase_receipts = {
        "uninterrupted": _invoke(uninterrupted, "uninterrupted"),
        "interrupt": _invoke(resumed, "interrupt"),
        "resume": _invoke(resumed, "resume"),
    }
    expected_codes = {"uninterrupted": 0, "interrupt": 75, "resume": 0}
    for name, completed in phase_receipts.items():
        if completed.returncode != expected_codes[name]:
            raise RuntimeError(
                f"{name} phase failed: {completed.returncode}: {completed.stderr}"
            )
    uninterrupted_report = (uninterrupted / "report.json").read_bytes()
    resumed_report = (resumed / "report.json").read_bytes()
    uninterrupted_journal = (
        uninterrupted / f"run-state/{RUN_ID}/journal.jsonl"
    ).read_bytes()
    resumed_journal = (resumed / f"run-state/{RUN_ID}/journal.jsonl").read_bytes()
    if uninterrupted_report != resumed_report or uninterrupted_journal != resumed_journal:
        raise RuntimeError("iterative interrupt/resume output differs from uninterrupted")
    report = json.loads(uninterrupted_report)
    tasks = report["tasks"]
    safety = next(task for task in tasks if task["task_id"] == "canary-safety-01")
    ack = json.loads(
        (
            resumed / f"run-state/{RUN_ID}/checkpoint-ack.json"
        ).read_text(encoding="utf-8")
    )
    budget = asyncio.run(_budget_falsifier())
    if (
        report["completed_cells"] != 6
        or sum(task["result"]["success"] for task in tasks) != 6
        or sum(task["tool_runtime_receipt"]["operation_count"] for task in tasks) != 9
        or sum(task["decision_count"] for task in tasks) != 15
        or ack.get("signal") != "SIGUSR1"
        or ack.get("completed_cells") != 2
        or safety["evaluation"]["success"] is not True
        or safety["result"]["safety_failures"] != 0
        or safety["observations"][0]["result"].get("found") is not True
    ):
        raise RuntimeError("iterative CPU admission projection failed")
    manifest = {
        "schema_version": 1,
        "status": _status(),
        "scientific_result": False,
        "publication_ready": False,
        "external_model_calls": 0,
        "task_count": 6,
        "task_success_count": 6,
        "tool_operation_count": 9,
        "decision_count": 15,
        "safety_gate_passed": True,
        "actual_usr1_acknowledged_cells": 2,
        "byte_identical_report": True,
        "byte_identical_journal": True,
        "report_sha256": _sha(uninterrupted_report),
        "journal_sha256": _sha(uninterrupted_journal),
        "contract_sha256": report["contract_sha256"],
        "plan_sha256": report["plan_sha256"],
        "journal_root_sha256": report["journal_root_sha256"],
        "budget_falsifier": budget,
        "phase_receipts": {
            name: {
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
            for name, completed in phase_receipts.items()
        },
        "claim_boundary": (
            "Deterministic CPU protocol admission only. No live model or H100 ran; "
            "this is not language, model-quality, multiturn, benchmark-validity, "
            "scientific, or publication evidence."
        ),
        "next_gate": (
            "Bind this exact admitted protocol to a fresh preregistration before any "
            "additional live-model decision or comparative study."
            if os.environ.get(STRUCTURAL_PROTOCOL_ENV) == "structural-json-v2"
            else "Adapt one pinned live model to the strict iterative action protocol "
            "and require tool-result-conditioned safety before comparative study."
        ),
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(canonical_json(manifest) + "\n", encoding="utf-8")
    return manifest


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


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
