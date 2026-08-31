"""Run the preregistered two-stage Qwen3.5-4B OrchVar smoke."""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import os
import re
import signal
import sys
from collections.abc import Callable
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

from harness.benchmarks.base import BenchmarkTask, TaskResult
from harness.benchmarks.orchvar_canary_live_v2 import OrchVarCanaryLiveV2Adapter
from harness.conditions import get_condition
from harness.config import ConditionID, ExperimentConfig
from harness.live_canary import SQLiteCanaryToolRuntime
from harness.live_runner import _mapping, _positive_int, _runtime_context, _select_tasks
from harness.receipted_tool_runtime import ReceiptedSQLiteCanaryToolRuntime
from harness.run_state import ExecutionJournal, canonical_json
from harness.two_stage_agent_loop import (
    ToolObservation,
    TwoStageExecutionError,
    execute_two_stage_agent_task,
)
from harness.two_stage_live_canary import load_transformers_two_stage_actor


def _message(message: Any) -> dict[str, Any]:
    return {
        "step": message.step,
        "role": message.role,
        "type": message.message_type.value,
        "language": message.language,
        "content": message.content,
        "metadata": message.metadata,
    }


def _observations(items: tuple[ToolObservation, ...]) -> list[dict[str, Any]]:
    return [
        {"call": asdict(observation.call), "result": observation.result}
        for observation in items
    ]


def _number(receipt: dict[str, Any], key: str) -> float:
    if key not in receipt:
        raise ValueError(f"two-stage backend receipt is missing {key}")
    value = receipt[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"two-stage backend receipt field {key} is not numeric")
    return float(value)


def _tool_counts(receipt: dict[str, Any]) -> tuple[int, int, int]:
    identity = receipt.get("identity")
    if identity == SQLiteCanaryToolRuntime.identity:
        attempts = receipt.get("operation_count")
        successes = attempts
        errors = 0
    elif identity == ReceiptedSQLiteCanaryToolRuntime.identity:
        attempts = receipt.get("attempt_count")
        successes = receipt.get("success_count")
        errors = receipt.get("error_count")
    else:
        raise ValueError("two-stage tool runtime receipt identity is unsupported")
    counts = (attempts, successes, errors)
    if any(isinstance(value, bool) or not isinstance(value, int) for value in counts):
        raise ValueError("two-stage tool runtime counts must be integers")
    if min(counts) < 0 or successes + errors != attempts:
        raise ValueError("two-stage tool runtime counts are inconsistent")
    return attempts, successes, errors


def _tool_runtime_factory(config: ExperimentConfig) -> Callable[[], Any]:
    tools = _mapping(config.extra.get("tools"), "tools")
    runtime_type = tools.get("type")
    if runtime_type == "sqlite_canary_v1":
        return SQLiteCanaryToolRuntime
    if runtime_type == "sqlite_canary_receipted_errors_v2":
        return ReceiptedSQLiteCanaryToolRuntime
    raise ValueError("two-stage tool runtime type is unsupported")


def _protocol_result(
    task: BenchmarkTask, error: TwoStageExecutionError
) -> TaskResult:
    tool_calls = [
        {"name": item.call.name, "arguments": item.call.arguments}
        for item in error.observations
    ]
    return TaskResult(
        task_id=task.task_id,
        success=False,
        tool_calls=tool_calls,
        tool_calls_correct=0,
        tool_calls_total=len(tool_calls),
        final_response="",
        metadata={
            "terminal_status": "protocol_failure",
            "protocol_failure_code": error.code,
            "protocol_failure_stage": error.stage,
            "protocol_failure_decision_index": error.decision_index,
        },
    )


def _cell_payload(
    *,
    key: dict[str, Any],
    task: BenchmarkTask,
    result: TaskResult,
    evaluation: dict[str, Any],
    messages: tuple[Any, ...],
    observations: tuple[ToolObservation, ...],
    stage_receipts: tuple[dict[str, Any], ...],
    backend_receipts: list[dict[str, Any]],
    tool_receipt: dict[str, Any],
    protocol_failure: dict[str, Any] | None,
    decision_count: int,
) -> dict[str, Any]:
    planner_receipts = [
        receipt for receipt in backend_receipts if receipt.get("stage") == "planner_message"
    ]
    memory_receipts = [
        receipt for receipt in backend_receipts if receipt.get("stage") == "memory_message"
    ]
    action_receipts = [
        receipt for receipt in backend_receipts if receipt.get("stage") == "action"
    ]
    message_receipts = planner_receipts + memory_receipts
    messages_compliant = bool(message_receipts) and all(
        receipt.get("compliance") == "valid" for receipt in message_receipts
    )
    actions_valid = bool(action_receipts) and all(
        receipt.get("compliance") == "valid" for receipt in action_receipts
    )
    prompt_tokens = sum(
        int(_number(receipt, "prompt_tokens")) for receipt in backend_receipts
    )
    completion_tokens = sum(
        int(_number(receipt, "completion_tokens")) for receipt in backend_receipts
    )
    latency_ms = sum(
        _number(receipt, "latency_ms") for receipt in backend_receipts
    )
    tool_attempts, tool_successes, tool_errors = _tool_counts(tool_receipt)
    success = bool(
        result.success
        and protocol_failure is None
        and messages_compliant
        and actions_valid
    )
    return {
        "terminal_status": "complete",
        "cell_status": "success" if success else (
            "protocol_failure" if protocol_failure is not None else "benchmark_failure"
        ),
        "trace": {
            "experiment_id": None,
            "benchmark": "orchvar_canary",
            "condition": key["condition"],
            "model": key["model"],
            "task_id": key["task_id"],
            "seed": key["seed"],
            "run_group": key["run_group"],
            "pair_key": key,
            "task": asdict(task),
            "messages": [_message(message) for message in messages],
            "observations": _observations(observations),
            "task_result": asdict(result),
            "benchmark_evaluation": evaluation,
            "stage_receipts": list(stage_receipts),
            "backend_stage_receipts": backend_receipts,
            "tool_runtime_receipt": tool_receipt,
            "protocol_failure": protocol_failure,
            "outcome": {
                "success": success,
                "message_compliance": messages_compliant,
                "all_actions_valid": actions_valid,
                "tool_calls_correct": result.tool_calls_correct,
                "tool_calls_total": result.tool_calls_total,
                "safety_failures": result.safety_failures,
                "decision_count": decision_count,
                "planner_stage_calls": len(planner_receipts),
                "memory_stage_calls": len(memory_receipts),
                "message_stage_calls": len(message_receipts),
                "action_stage_calls": len(action_receipts),
                "external_model_calls": len(backend_receipts),
                "local_tool_calls": tool_attempts,
                "local_tool_successes": tool_successes,
                "local_tool_errors": tool_errors,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "total_latency_ms": latency_ms,
                "cost_usd": 0.0,
            },
        },
    }


def _usage(payloads: list[dict[str, Any]]) -> dict[str, int]:
    outcomes = [payload["trace"]["outcome"] for payload in payloads]
    fields = (
        "planner_stage_calls",
        "memory_stage_calls",
        "message_stage_calls",
        "action_stage_calls",
        "external_model_calls",
        "local_tool_calls",
        "prompt_tokens",
        "completion_tokens",
    )
    return {
        field: sum(int(outcome[field]) for outcome in outcomes) for field in fields
    }


def _enforce_global_budgets(
    payloads: list[dict[str, Any]], budgets: dict[str, Any]
) -> None:
    usage = _usage(payloads)
    limits = {
        "planner_stage_calls": _positive_int(
            budgets.get("max_planner_stage_calls"), "max_planner_stage_calls"
        ),
        "memory_stage_calls": _positive_int(
            budgets.get("max_memory_stage_calls"), "max_memory_stage_calls"
        ),
        "message_stage_calls": _positive_int(
            budgets.get("max_message_stage_calls"), "max_message_stage_calls"
        ),
        "action_stage_calls": _positive_int(
            budgets.get("max_action_stage_calls"), "max_action_stage_calls"
        ),
        "external_model_calls": _positive_int(
            budgets.get("max_external_model_calls"), "max_external_model_calls"
        ),
        "local_tool_calls": _positive_int(
            budgets.get("max_local_tool_calls"), "max_local_tool_calls"
        ),
        "prompt_tokens": _positive_int(
            budgets.get("max_prompt_tokens"), "max_prompt_tokens"
        ),
        "completion_tokens": _positive_int(
            budgets.get("max_completion_tokens"), "max_completion_tokens"
        ),
    }
    exceeded = [
        f"{field}={usage[field]}>{limit}"
        for field, limit in limits.items()
        if usage[field] > limit
    ]
    if exceeded:
        raise RuntimeError(
            "two-stage live global budget exhausted: " + ", ".join(exceeded)
        )


def _materialize(
    output_root: Path,
    run_id: str,
    config: ExperimentConfig,
    journal: ExecutionJournal,
    runtime_context: dict[str, Any],
) -> dict[str, Any]:
    traces: list[dict[str, Any]] = []
    for payload in journal.payloads():
        if payload.get("terminal_status") != "complete":
            raise RuntimeError("cannot materialize incomplete two-stage cells")
        trace = dict(payload["trace"])
        trace["experiment_id"] = run_id
        traces.append(trace)
    model_slug = re.sub(r"[^a-z0-9]+", "-", str(config.model).casefold()).strip("-")
    trace_path = (
        output_root
        / "traces/orchvar_canary/english_only"
        / f"{run_id}__default__{model_slug}.jsonl"
    )
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    encoded = "".join(canonical_json(trace) + "\n" for trace in traces)
    trace_path.write_text(encoded, encoding="utf-8")
    outcomes = [trace["outcome"] for trace in traces]
    total_expected = sum(int(item["tool_calls_total"]) for item in outcomes)
    message_calls = sum(int(item["message_stage_calls"]) for item in outcomes)
    valid_message_calls = sum(
        sum(
            receipt.get("compliance") == "valid"
            for receipt in trace["backend_stage_receipts"]
            if receipt.get("stage") in {"planner_message", "memory_message"}
        )
        for trace in traces
    )
    summary = {
        "experiment_id": run_id,
        "task_count": len(traces),
        "success_rate": sum(bool(item["success"]) for item in outcomes) / len(outcomes),
        "tool_correctness": sum(int(item["tool_calls_correct"]) for item in outcomes)
        / max(1, total_expected),
        "total_safety_failures": sum(int(item["safety_failures"]) for item in outcomes),
        "message_compliance_rate": valid_message_calls / max(1, message_calls),
        "message_compliance_failures": sum(
            not bool(item["message_compliance"]) for item in outcomes
        ),
        "action_compliance_failures": sum(
            not bool(item["all_actions_valid"]) for item in outcomes
        ),
        "protocol_failures": sum(
            trace["protocol_failure"] is not None for trace in traces
        ),
        "total_planner_stage_calls": sum(
            int(item["planner_stage_calls"]) for item in outcomes
        ),
        "total_memory_stage_calls": sum(
            int(item["memory_stage_calls"]) for item in outcomes
        ),
        "total_message_stage_calls": message_calls,
        "total_action_stage_calls": sum(
            int(item["action_stage_calls"]) for item in outcomes
        ),
        "total_external_model_calls": sum(
            int(item["external_model_calls"]) for item in outcomes
        ),
        "total_tool_calls": sum(int(item["local_tool_calls"]) for item in outcomes),
        "total_tool_successes": sum(
            int(item["local_tool_successes"]) for item in outcomes
        ),
        "total_tool_errors": sum(
            int(item["local_tool_errors"]) for item in outcomes
        ),
        "total_prompt_tokens": sum(int(item["prompt_tokens"]) for item in outcomes),
        "total_completion_tokens": sum(
            int(item["completion_tokens"]) for item in outcomes
        ),
        "avg_latency_ms": sum(float(item["total_latency_ms"]) for item in outcomes)
        / len(outcomes),
    }
    result = {
        "schema_version": 1,
        "status": "COMPLETE",
        "claim_status": str(
            _mapping(config.extra.get("execution"), "execution").get(
                "claim_status", "NON_SCIENTIFIC_TWO_STAGE_LIVE_SMOKE"
            )
        ),
        "experiment_id": run_id,
        "contract_sha256": journal.contract_sha256,
        "plan_sha256": journal.plan_sha256,
        "journal_root_sha256": journal.journal_root_sha256,
        "completed_cells": journal.completed,
        "runtime_context": runtime_context,
        "claim_boundary": config.extra["claim_boundary"],
        "trace_artifact": {
            "path": str(trace_path.relative_to(output_root)),
            "sha256": hashlib.sha256(encoded.encode()).hexdigest(),
            "rows": len(traces),
        },
        "summary": summary,
    }
    result_path = output_root / "results" / f"{run_id}_summary.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(canonical_json(result) + "\n", encoding="utf-8")
    return result


async def run_two_stage_live(
    config: ExperimentConfig,
    *,
    runtime_context_override: dict[str, Any] | None = None,
    actor_override: Any | None = None,
    tool_runtime_factory_override: Callable[[], Any] | None = None,
) -> dict[str, Any]:
    """Execute six cells while preserving measured protocol failures."""
    if config.benchmark != "orchvar_canary":
        raise ValueError("two-stage live runner admits only OrchVar-Canary")
    specs = config.iter_run_specs()
    if len(specs) != 1 or specs[0].conditions != [ConditionID.ENGLISH_ONLY]:
        raise ValueError("two-stage live runner admits one English-only run spec")
    run_id = str(_mapping(config.extra.get("execution"), "execution")["run_id"])
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", run_id):
        raise ValueError("two-stage live run ID must be kebab-case")
    runtime_context = (
        runtime_context_override
        if runtime_context_override is not None
        else _runtime_context(config)
    )
    output_root = Path(os.environ.get("COTCODEC_OUTPUT_DIR", "data"))
    resume = os.environ.get("COTCODEC_RESUME") == "1"
    adapter = OrchVarCanaryLiveV2Adapter()
    tasks = _select_tasks(await adapter.load_tasks(count=None), config.tasks)
    condition = get_condition(ConditionID.ENGLISH_ONLY)
    actor_config = _mapping(config.extra.get("actor"), "actor")
    if actor_override is None:
        if actor_config.get("type") != "transformers_two_stage_plain_action_json_v1":
            raise ValueError("two-stage live actor type is unsupported")
        actor = load_transformers_two_stage_actor(actor_config)
    else:
        actor = actor_override
    tool_runtime_factory = (
        tool_runtime_factory_override
        if tool_runtime_factory_override is not None
        else _tool_runtime_factory(config)
    )
    tool_runtime_identity = getattr(tool_runtime_factory, "identity", None)
    if not isinstance(tool_runtime_identity, str):
        raise ValueError("two-stage tool runtime factory lacks an identity")
    budgets = _mapping(config.extra.get("budgets"), "budgets")
    max_decisions = _positive_int(
        budgets.get("max_decisions_per_task"), "max_decisions_per_task"
    )
    max_steps = _positive_int(budgets.get("max_steps_per_task"), "max_steps_per_task")
    max_tools = _positive_int(
        budgets.get("max_tool_calls_per_task"), "max_tool_calls_per_task"
    )
    plan = [
        {
            "run_group": "default",
            "model": str(config.model),
            "condition": "english_only",
            "task_id": task.task_id,
            "seed": 42,
        }
        for task in tasks
    ]
    contract = {
        "schema_version": 1,
        "name": config.name,
        "tasks": [asdict(task) for task in tasks],
        "extra": config.extra,
        "actor_contract": actor.contract,
        "tool_runtime_identity": tool_runtime_identity,
        "runtime_context": runtime_context,
    }
    journal = ExecutionJournal(
        output_root / "run-state" / run_id,
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
    try:
        for key in plan[journal.completed :]:
            if stop_requested:
                journal.acknowledge_interrupt("SIGUSR1")
                return {"status": "INTERRUPTED_CHECKPOINTED"}
            task = task_by_id[key["task_id"]]
            runtime = tool_runtime_factory()
            protocol_failure: dict[str, Any] | None = None
            protocol_decision_index: int | None = None
            try:
                try:
                    execution = await execute_two_stage_agent_task(
                        task,
                        actor=actor,
                        tools=runtime,
                        condition=condition,
                        system_prompt=adapter.get_system_prompt(),
                        seed=42,
                        max_decisions=max_decisions,
                        max_steps=max_steps,
                        max_tool_calls=max_tools,
                    )
                    messages = execution.messages
                    observations = execution.observations
                    stage_receipts = execution.stage_receipts
                    raw_result = execution.result
                    decision_count = execution.decision_count
                except TwoStageExecutionError as error:
                    messages = error.messages
                    observations = error.observations
                    stage_receipts = error.stage_receipts
                    raw_result = _protocol_result(task, error)
                    protocol_decision_index = error.decision_index
                    protocol_failure = {
                        **error.to_dict(),
                        "stage": error.stage,
                        "decision_index": error.decision_index,
                    }
                backend_receipts = actor.pop_receipts()
                if protocol_failure is not None:
                    receipt_indices = [
                        int(receipt["decision_index"])
                        for receipt in backend_receipts
                        if isinstance(receipt.get("decision_index"), int)
                    ]
                    decision_count = (
                        max(receipt_indices) + 1
                        if receipt_indices
                        else int(protocol_decision_index) + 1
                    )
                tool_receipt = runtime.close_and_receipt()
                evaluation = await adapter.evaluate(task, raw_result)
                result = replace(
                    raw_result,
                    success=bool(evaluation["success"]),
                    tool_calls_correct=int(evaluation["tool_calls_correct"]),
                    tool_calls_total=int(evaluation["tool_calls_total"]),
                    safety_failures=int(evaluation["safety_failures"]),
                    metadata={
                        **(raw_result.metadata or {}),
                        "terminal_status": (
                            "protocol_failure"
                            if protocol_failure is not None
                            else "complete"
                        ),
                    },
                )
                payload = _cell_payload(
                    key=key,
                    task=task,
                    result=result,
                    evaluation=evaluation,
                    messages=messages,
                    observations=observations,
                    stage_receipts=stage_receipts,
                    backend_receipts=backend_receipts,
                    tool_receipt=tool_receipt,
                    protocol_failure=protocol_failure,
                    decision_count=decision_count,
                )
            except Exception:
                with contextlib.suppress(Exception):
                    actor.pop_receipts()
                with contextlib.suppress(Exception):
                    runtime.close_and_receipt()
                raise
            prior = list(journal.payloads()) + [payload]
            _enforce_global_budgets(prior, budgets)
            journal.append(key, payload)
            outcome = payload["trace"]["outcome"]
            print(
                f"{task.task_id}: {'PASS' if outcome['success'] else 'FAIL'} "
                f"messages={outcome['message_stage_calls']} "
                f"actions={outcome['action_stage_calls']} "
                f"tools={outcome['local_tool_calls']}",
                flush=True,
            )
    finally:
        signal.signal(signal.SIGUSR1, previous)
    journal.complete()
    result = _materialize(output_root, run_id, config, journal, runtime_context)
    print(canonical_json(result["summary"]), flush=True)
    return result


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python -m harness.two_stage_live_runner <experiment.yaml>")
        return 2
    path = Path(sys.argv[1]).resolve()
    from scripts.validate_orchvar_two_stage_live_experiment import validate_experiment

    validate_experiment(path)
    result = asyncio.run(run_two_stage_live(ExperimentConfig.from_yaml(path)))
    return 75 if result.get("status") == "INTERRUPTED_CHECKPOINTED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
