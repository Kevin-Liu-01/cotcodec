"""Run the preregistered iterative Qwen3.5-4B OrchVar smoke."""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import os
import re
import signal
import sys
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

from harness.benchmarks.orchvar_canary_live_v2 import OrchVarCanaryLiveV2Adapter
from harness.conditions import get_condition
from harness.config import ConditionID, ExperimentConfig
from harness.iterative_agent_loop import execute_iterative_agent_task
from harness.iterative_live_canary import (
    load_transformers_iterative_actor,
    load_transformers_structural_iterative_actor,
)
from harness.live_canary import SQLiteCanaryToolRuntime
from harness.live_runner import _mapping, _positive_int, _runtime_context, _select_tasks
from harness.run_state import ExecutionJournal, canonical_json


def _message(message) -> dict[str, Any]:
    return {
        "step": message.step,
        "role": message.role,
        "type": message.message_type.value,
        "language": message.language,
        "content": message.content,
        "metadata": message.metadata,
    }


def _number(receipt: dict[str, Any], key: str) -> float:
    value = receipt.get(key, 0)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"iterative receipt field {key} is not numeric")
    return float(value)


def _payload(
    key: dict[str, Any],
    task,
    execution,
    result,
    evaluation: dict[str, Any],
    decision_receipts: list[dict[str, Any]],
    tool_receipt: dict[str, Any],
) -> dict[str, Any]:
    all_valid = all(
        receipt.get("action_parse_status") == "valid" for receipt in decision_receipts
    )
    prompt_tokens = sum(int(_number(receipt, "prompt_tokens")) for receipt in decision_receipts)
    completion_tokens = sum(
        int(_number(receipt, "completion_tokens")) for receipt in decision_receipts
    )
    latency_ms = sum(_number(receipt, "latency_ms") for receipt in decision_receipts)
    return {
        "terminal_status": "complete",
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
            "messages": [_message(message) for message in execution.messages],
            "observations": [
                {"call": asdict(observation.call), "result": observation.result}
                for observation in execution.observations
            ],
            "task_result": asdict(result),
            "benchmark_evaluation": evaluation,
            "decision_receipts": decision_receipts,
            "tool_runtime_receipt": tool_receipt,
            "outcome": {
                "success": bool(result.success and all_valid),
                "all_actions_valid": all_valid,
                "tool_calls_correct": result.tool_calls_correct,
                "tool_calls_total": result.tool_calls_total,
                "safety_failures": result.safety_failures,
                "decision_count": execution.decision_count,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "total_latency_ms": latency_ms,
                "external_model_calls": len(decision_receipts),
                "local_tool_calls": tool_receipt["operation_count"],
                "cost_usd": 0.0,
            },
        },
    }


def _materialize(
    output_root: Path,
    run_id: str,
    config: ExperimentConfig,
    journal: ExecutionJournal,
    runtime_context: dict[str, Any],
) -> dict[str, Any]:
    traces = []
    for payload in journal.payloads():
        if payload.get("terminal_status") != "complete":
            raise RuntimeError("cannot materialize failed iterative cells")
        trace = dict(payload["trace"])
        trace["experiment_id"] = run_id
        traces.append(trace)
    path = (
        output_root
        / "traces/orchvar_canary/english_only"
        / f"{run_id}__default__qwen3-5-4b.jsonl"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = "".join(canonical_json(trace) + "\n" for trace in traces)
    path.write_text(encoded, encoding="utf-8")
    outcomes = [trace["outcome"] for trace in traces]
    total_expected = sum(outcome["tool_calls_total"] for outcome in outcomes)
    summary = {
        "experiment_id": run_id,
        "task_count": len(traces),
        "success_rate": sum(outcome["success"] for outcome in outcomes) / len(outcomes),
        "tool_correctness": sum(outcome["tool_calls_correct"] for outcome in outcomes)
        / max(1, total_expected),
        "total_safety_failures": sum(outcome["safety_failures"] for outcome in outcomes),
        "total_model_decisions": sum(outcome["external_model_calls"] for outcome in outcomes),
        "total_tool_calls": sum(outcome["local_tool_calls"] for outcome in outcomes),
        "total_tokens": sum(outcome["total_tokens"] for outcome in outcomes),
        "avg_latency_ms": sum(outcome["total_latency_ms"] for outcome in outcomes)
        / len(outcomes),
    }
    result = {
        "schema_version": 1,
        "status": "COMPLETE",
        "claim_status": "NON_SCIENTIFIC_ITERATIVE_LIVE_SMOKE",
        "experiment_id": run_id,
        "contract_sha256": journal.contract_sha256,
        "plan_sha256": journal.plan_sha256,
        "journal_root_sha256": journal.journal_root_sha256,
        "completed_cells": journal.completed,
        "runtime_context": runtime_context,
        "claim_boundary": config.extra["claim_boundary"],
        "trace_artifact": {
            "path": str(path.relative_to(output_root)),
            "sha256": hashlib.sha256(encoded.encode()).hexdigest(),
            "rows": len(traces),
        },
        "summary": summary,
    }
    result_path = output_root / "results" / f"{run_id}_summary.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(canonical_json(result) + "\n", encoding="utf-8")
    return result


async def run_iterative_live(config: ExperimentConfig) -> dict[str, Any]:
    run_id = str(_mapping(config.extra.get("execution"), "execution")["run_id"])
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", run_id):
        raise ValueError("iterative live run ID must be kebab-case")
    runtime_context = _runtime_context(config)
    output_root = Path(os.environ.get("COTCODEC_OUTPUT_DIR", "data"))
    resume = os.environ.get("COTCODEC_RESUME") == "1"
    adapter = OrchVarCanaryLiveV2Adapter()
    tasks = _select_tasks(await adapter.load_tasks(count=None), config.tasks)
    condition = get_condition(ConditionID.ENGLISH_ONLY)
    actor_config = _mapping(config.extra.get("actor"), "actor")
    actor_type = actor_config.get("type")
    if actor_type == "transformers_iterative_structural_json_v2":
        actor = load_transformers_structural_iterative_actor(actor_config)
    elif actor_type == "transformers_iterative_json_v1":
        actor = load_transformers_iterative_actor(actor_config)
    else:
        raise ValueError("iterative live actor type is unsupported")
    budgets = _mapping(config.extra.get("budgets"), "budgets")
    max_decisions = _positive_int(
        budgets.get("max_decisions_per_task"), "max_decisions_per_task"
    )
    max_steps = _positive_int(budgets.get("max_steps_per_task"), "max_steps_per_task")
    max_tools = _positive_int(
        budgets.get("max_tool_calls_per_task"), "max_tool_calls_per_task"
    )
    max_model_calls = _positive_int(
        budgets.get("max_external_model_calls"), "max_external_model_calls"
    )
    max_local_tools = _positive_int(
        budgets.get("max_local_tool_calls"), "max_local_tool_calls"
    )
    plan = [
        {
            "run_group": "default",
            "model": "qwen3.5-4b",
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
        "tool_runtime_identity": SQLiteCanaryToolRuntime.identity,
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
            runtime = SQLiteCanaryToolRuntime()
            try:
                execution = await execute_iterative_agent_task(
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
                decision_receipts = actor.pop_receipts()
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
                payload = _payload(
                    key,
                    task,
                    execution,
                    result,
                    evaluation,
                    decision_receipts,
                    tool_receipt,
                )
            except Exception:
                with contextlib.suppress(Exception):
                    runtime.close_and_receipt()
                raise
            prior = list(journal.payloads()) + [payload]
            model_calls = sum(
                row["trace"]["outcome"]["external_model_calls"] for row in prior
            )
            tool_calls = sum(row["trace"]["outcome"]["local_tool_calls"] for row in prior)
            if model_calls > max_model_calls or tool_calls > max_local_tools:
                raise RuntimeError("iterative live global budget exhausted")
            journal.append(key, payload)
            outcome = payload["trace"]["outcome"]
            print(
                f"{task.task_id}: {'PASS' if outcome['success'] else 'FAIL'} "
                f"decisions={outcome['decision_count']} tools={outcome['local_tool_calls']}",
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
        print("Usage: python -m harness.iterative_live_runner <experiment.yaml>")
        return 2
    path = Path(sys.argv[1]).resolve()
    config = ExperimentConfig.from_yaml(path)
    if config.name == "orchvar_qwen35_iterative_structural_live_smoke":
        from scripts.validate_orchvar_iterative_structural_live_experiment import (
            validate_experiment,
        )
    else:
        from scripts.validate_orchvar_iterative_live_experiment import (
            validate_experiment,
        )

    validate_experiment(path)
    result = asyncio.run(run_iterative_live(config))
    return 75 if result.get("status") == "INTERRUPTED_CHECKPOINTED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
