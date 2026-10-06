"""Run the preregistered one-plan live OrchVar-Canary smoke."""

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

from harness.agent_loop import AgentLoopError, ExecutedMessage, execute_agent_task
from harness.benchmarks.base import BenchmarkTask, TaskResult
from harness.benchmarks.orchvar_canary import OrchVarCanaryAdapter
from harness.benchmarks.orchvar_canary_live_v2 import OrchVarCanaryLiveV2Adapter
from harness.conditions import get_condition
from harness.config import ConditionID, ExperimentConfig
from harness.live_canary import (
    SQLiteCanaryToolRuntime,
    actor_config_sha256,
    load_transformers_canary_actor,
)
from harness.run_state import ExecutionJournal, canonical_json


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a mapping")
    return value


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _select_tasks(
    loaded: list[BenchmarkTask], selection: int | list[str]
) -> list[BenchmarkTask]:
    if isinstance(selection, int):
        return loaded if selection < 0 else loaded[:selection]
    by_id = {task.task_id: task for task in loaded}
    if len(by_id) != len(loaded):
        raise ValueError("benchmark returned duplicate task IDs")
    if len(selection) != len(set(selection)):
        raise ValueError("configured task roster contains duplicates")
    missing = [task_id for task_id in selection if task_id not in by_id]
    if missing:
        raise ValueError(f"configured task IDs are missing: {missing}")
    return [by_id[task_id] for task_id in selection]


def _runtime_context(config: ExperimentConfig) -> dict[str, Any]:
    containment = _mapping(config.extra.get("containment"), "containment")
    image_id = os.environ.get("COTCODEC_IMAGE_ID", "")
    source_root = os.environ.get("COTCODEC_SOURCE_CAPSULE_ROOT", "")
    slurm_job_id = os.environ.get("SLURM_JOB_ID", "")
    visible_devices = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    if image_id != containment.get("image_id"):
        raise ValueError("container image ID differs from the experiment contract")
    if not re.fullmatch(r"[0-9a-f]{64}", source_root):
        raise ValueError("content-addressed source capsule root is required")
    if not re.fullmatch(r"[1-9][0-9]*", slurm_job_id):
        raise ValueError("live smoke must execute inside Slurm")
    if len([item for item in visible_devices.split(",") if item]) != 1:
        raise ValueError("live smoke requires exactly one visible GPU")
    return {
        "source_capsule_root_sha256": source_root,
        "image_id": image_id,
        "slurm_job_id": slurm_job_id,
        "cuda_visible_devices": visible_devices,
    }


def _build_plan(config: ExperimentConfig, tasks: list[BenchmarkTask]) -> list[dict[str, Any]]:
    return [
        {
            "run_group": run.group,
            "model": run.model,
            "condition": condition.value,
            "task_id": task.task_id,
            "seed": seed,
        }
        for run in config.iter_run_specs()
        for condition in run.conditions
        for task in tasks
        for seed in config.seeds
    ]


def _message_payload(message: ExecutedMessage) -> dict[str, Any]:
    return {
        "step": message.step,
        "role": message.role,
        "type": message.message_type.value,
        "language": message.language,
        "content": message.content,
        "token_count_input": 0,
        "token_count_output": len(message.content.split()),
        "latency_ms": 0.0,
        "metadata": message.metadata,
    }


def _number(receipt: dict[str, Any], key: str) -> float:
    value = receipt.get(key, 0)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"actor receipt field {key} is not numeric")
    return float(value)


def _cell_payload(
    key: dict[str, Any],
    task: BenchmarkTask,
    result: TaskResult,
    messages: tuple[ExecutedMessage, ...],
    evaluation: dict[str, Any],
    system_prompt: str,
    actor_receipt: dict[str, Any],
    tool_receipt: dict[str, Any],
) -> dict[str, Any]:
    prompt_tokens = int(_number(actor_receipt, "prompt_tokens"))
    completion_tokens = int(_number(actor_receipt, "completion_tokens"))
    latency_ms = _number(actor_receipt, "latency_ms")
    parse_valid = actor_receipt.get("plan_parse_status") == "valid"
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
            "system_prompt_sha256": hashlib.sha256(system_prompt.encode()).hexdigest(),
            "messages": [_message_payload(message) for message in messages],
            "task_result": asdict(result),
            "benchmark_evaluation": evaluation,
            "task_metadata": task.metadata or {},
            "actor_receipt": actor_receipt,
            "tool_runtime_receipt": tool_receipt,
            "outcome": {
                "success": bool(result.success and parse_valid),
                "tool_calls_correct": result.tool_calls_correct,
                "tool_calls_total": result.tool_calls_total,
                "retries": result.retries,
                "safety_failures": result.safety_failures,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "total_latency_ms": latency_ms,
                "external_model_calls": 1,
                "local_tool_calls": tool_receipt["operation_count"],
                "cost_usd": 0.0,
            },
        },
    }


def _failure_payload(
    key: dict[str, Any], task: BenchmarkTask, error: BaseException
) -> dict[str, Any]:
    if isinstance(error, AgentLoopError):
        error_receipt = error.to_dict()
    else:
        error_receipt = {
            "code": "live_infrastructure_error",
            "detail": f"{type(error).__name__}: {error}",
        }
    return {
        "terminal_status": "failed_closed",
        "trace": {
            "experiment_id": None,
            "benchmark": "orchvar_canary",
            "condition": key["condition"],
            "model": key["model"],
            "task_id": task.task_id,
            "seed": key["seed"],
            "run_group": key["run_group"],
            "pair_key": key,
            "messages": [],
            "outcome": {"success": False},
            "error_receipt": error_receipt,
        },
    }


def _usage(payloads: list[dict[str, Any]]) -> tuple[int, int]:
    outcomes = [
        payload["trace"]["outcome"]
        for payload in payloads
        if payload.get("terminal_status") == "complete"
    ]
    return (
        sum(int(outcome["external_model_calls"]) for outcome in outcomes),
        sum(int(outcome["local_tool_calls"]) for outcome in outcomes),
    )


def _materialize_outputs(
    output_root: Path,
    run_id: str,
    config: ExperimentConfig,
    journal: ExecutionJournal,
    runtime_context: dict[str, Any],
) -> dict[str, Any]:
    traces: list[dict[str, Any]] = []
    for payload in journal.payloads():
        if payload.get("terminal_status") != "complete":
            raise RuntimeError("cannot materialize a failed-closed live smoke")
        trace = dict(payload["trace"])
        trace["experiment_id"] = run_id
        traces.append(trace)

    trace_path = (
        output_root
        / "traces"
        / "orchvar_canary"
        / "english_only"
        / f"{run_id}__default__qwen3-5-4b.jsonl"
    )
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    encoded = "".join(canonical_json(trace) + "\n" for trace in traces)
    trace_path.write_text(encoded, encoding="utf-8")
    outcomes = [trace["outcome"] for trace in traces]
    total_calls = sum(int(outcome["tool_calls_total"]) for outcome in outcomes)
    summary = {
        "experiment_id": run_id,
        "benchmark": config.benchmark,
        "condition": "english_only",
        "model": "qwen3.5-4b",
        "task_count": len(traces),
        "success_rate": sum(bool(outcome["success"]) for outcome in outcomes)
        / len(outcomes),
        "avg_tokens": sum(int(outcome["total_tokens"]) for outcome in outcomes)
        / len(outcomes),
        "avg_latency_ms": sum(
            float(outcome["total_latency_ms"]) for outcome in outcomes
        )
        / len(outcomes),
        "total_safety_failures": sum(
            int(outcome["safety_failures"]) for outcome in outcomes
        ),
        "tool_correctness": sum(
            int(outcome["tool_calls_correct"]) for outcome in outcomes
        )
        / max(1, total_calls),
    }
    result = {
        "schema_version": 1,
        "status": "COMPLETE",
        "claim_status": "NON_SCIENTIFIC_LIVE_SMOKE",
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


async def run_live_experiment(config: ExperimentConfig) -> dict[str, Any]:
    """Execute the exact six-cell live smoke with durable cell boundaries."""
    if config.benchmark != "orchvar_canary":
        raise ValueError("live runner admits only OrchVar-Canary")
    run_specs = config.iter_run_specs()
    if len(run_specs) != 1 or run_specs[0].conditions != [ConditionID.ENGLISH_ONLY]:
        raise ValueError("live runner admits one English-only run spec")
    run_id = str(_mapping(config.extra.get("execution"), "execution")["run_id"])
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", run_id):
        raise ValueError("live run ID must be kebab-case")
    runtime_context = _runtime_context(config)
    output_root = Path(os.environ.get("COTCODEC_OUTPUT_DIR", "data"))
    resume = os.environ.get("COTCODEC_RESUME") == "1"

    task_variant = str(config.extra.get("task_variant", "legacy_v1"))
    if task_variant == "legacy_v1":
        benchmark = OrchVarCanaryAdapter()
    elif task_variant == "live_self_contained_v2":
        benchmark = OrchVarCanaryLiveV2Adapter()
    else:
        raise ValueError(f"unsupported live task variant: {task_variant}")
    loaded_tasks = await benchmark.load_tasks(count=None)
    tasks = _select_tasks(loaded_tasks, config.tasks)
    base_prompt = benchmark.get_system_prompt()
    actor_config = _mapping(config.extra.get("actor"), "actor")
    actor = load_transformers_canary_actor(actor_config)
    budgets = _mapping(config.extra.get("budgets"), "budgets")
    max_steps = _positive_int(budgets.get("max_steps_per_task"), "max_steps_per_task")
    max_tool_calls = _positive_int(
        budgets.get("max_tool_calls_per_task"), "max_tool_calls_per_task"
    )
    max_model_calls = _positive_int(
        budgets.get("external_model_calls"), "external_model_calls"
    )
    max_local_tool_calls = _positive_int(
        budgets.get("max_local_tool_calls"), "max_local_tool_calls"
    )
    plan = _build_plan(config, tasks)
    if len(plan) != max_model_calls:
        raise ValueError("one-completion plan does not match the model-call budget")
    contract = {
        "schema_version": 1,
        "name": config.name,
        "benchmark": config.benchmark,
        "run_specs": [
            {
                "group": run.group,
                "model": run.model,
                "conditions": [condition.value for condition in run.conditions],
            }
            for run in run_specs
        ],
        "tasks": [asdict(task) for task in tasks],
        "seeds": config.seeds,
        "metrics": config.metrics,
        "extra": config.extra,
        "base_prompt_sha256": hashlib.sha256(base_prompt.encode()).hexdigest(),
        "actor_contract": actor.contract,
        "actor_config_sha256": actor_config_sha256(actor_config),
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

    previous_handler: Any = None
    if hasattr(signal, "SIGUSR1"):
        previous_handler = signal.getsignal(signal.SIGUSR1)
        signal.signal(signal.SIGUSR1, request_stop)

    task_by_id = {task.task_id: task for task in tasks}
    condition = get_condition(ConditionID.ENGLISH_ONLY)
    try:
        for key in plan[journal.completed :]:
            if stop_requested:
                journal.acknowledge_interrupt("SIGUSR1")
                return {
                    "status": "INTERRUPTED_CHECKPOINTED",
                    "experiment_id": run_id,
                    "completed_cells": journal.completed,
                    "total_cells": len(plan),
                    "journal_root_sha256": journal.journal_root_sha256,
                }
            task = task_by_id[str(key["task_id"])]
            tool_runtime = SQLiteCanaryToolRuntime()
            try:
                system_prompt = condition.transform_system_prompt(base_prompt)
                execution = await execute_agent_task(
                    task,
                    actor=actor,
                    tools=tool_runtime,
                    condition=condition,
                    system_prompt=system_prompt,
                    seed=int(key["seed"]),
                    max_steps=max_steps,
                    max_tool_calls=max_tool_calls,
                )
                actor_receipt = actor.pop_receipt()
                tool_receipt = tool_runtime.close_and_receipt()
                evaluation = await benchmark.evaluate(task, execution.result)
                result = replace(
                    execution.result,
                    success=bool(evaluation["success"]),
                    tool_calls_correct=int(evaluation["tool_calls_correct"]),
                    tool_calls_total=int(evaluation["tool_calls_total"]),
                    safety_failures=int(evaluation["safety_failures"]),
                    metadata={
                        **(execution.result.metadata or {}),
                        "terminal_status": "complete",
                        "plan_parse_status": actor_receipt.get("plan_parse_status"),
                    },
                )
                payload = _cell_payload(
                    key,
                    task,
                    result,
                    execution.messages,
                    evaluation,
                    system_prompt,
                    actor_receipt,
                    tool_receipt,
                )
            except Exception as exc:
                with contextlib.suppress(Exception):
                    tool_runtime.close_and_receipt()
                payload = _failure_payload(key, task, exc)
                journal.append(key, payload)
                raise RuntimeError(
                    f"{task.task_id}: live smoke failed closed: {type(exc).__name__}: {exc}"
                ) from exc
            prior_payloads = list(journal.payloads()) + [payload]
            model_calls, local_tool_calls = _usage(prior_payloads)
            if model_calls > max_model_calls or local_tool_calls > max_local_tool_calls:
                budget_error = AgentLoopError(
                    "global_budget_exhausted",
                    "live smoke exceeded a preregistered global call budget",
                )
                journal.append(key, _failure_payload(key, task, budget_error))
                raise RuntimeError(str(budget_error))
            journal.append(key, payload)
            outcome = payload["trace"]["outcome"]
            print(
                f"{task.task_id}: {'PASS' if outcome['success'] else 'FAIL'} "
                f"tokens={outcome['total_tokens']} tools={outcome['local_tool_calls']}",
                flush=True,
            )
            if stop_requested:
                journal.acknowledge_interrupt("SIGUSR1")
                return {
                    "status": "INTERRUPTED_CHECKPOINTED",
                    "experiment_id": run_id,
                    "completed_cells": journal.completed,
                    "total_cells": len(plan),
                    "journal_root_sha256": journal.journal_root_sha256,
                }
    finally:
        if previous_handler is not None:
            signal.signal(signal.SIGUSR1, previous_handler)

    model_calls, local_tool_calls = _usage(list(journal.payloads()))
    if model_calls != max_model_calls or local_tool_calls > max_local_tool_calls:
        raise RuntimeError("completed live-smoke usage differs from its budget contract")
    journal.complete()
    result = _materialize_outputs(
        output_root, run_id, config, journal, runtime_context
    )
    print(canonical_json(result["summary"]), flush=True)
    return result


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python -m harness.live_runner <experiment.yaml>", file=sys.stderr)
        return 2
    experiment_path = Path(sys.argv[1]).resolve()
    from harness.yaml_utils import load_yaml_file

    identity = load_yaml_file(experiment_path).get("name")
    if identity == "degradation_canary_qwen35_4b_live_smoke":
        from scripts.validate_orchvar_live_smoke_experiment import validate_experiment
    elif identity == "degradation_canary_qwen35_4b_live_v2_smoke":
        from scripts.validate_orchvar_live_v2_smoke_experiment import validate_experiment
    else:
        raise ValueError("live runner experiment identity is not registered")
    validate_experiment(experiment_path)
    config = ExperimentConfig.from_yaml(experiment_path)
    result = asyncio.run(run_live_experiment(config))
    return 75 if result.get("status") == "INTERRUPTED_CHECKPOINTED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
