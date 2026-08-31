"""Experiment runner — executes experiment definitions against benchmarks.

Usage:
    python -m harness.runner experiments/pilot_01.yaml
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import re
import signal
import sys
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

from harness.agent_loop import (
    AgentLoopError,
    DeterministicCanaryActor,
    DeterministicToolRuntime,
    ExecutedMessage,
    execute_agent_task,
)
from harness.benchmarks.base import BenchmarkTask, TaskResult
from harness.conditions import get_condition
from harness.config import ExperimentConfig, ExperimentRunSpec
from harness.run_state import ExecutionJournal, canonical_json

try:
    from rich.console import Console
    from rich.table import Table
except ModuleNotFoundError:

    class Console:  # type: ignore[no-redef]
        def print(self, *args, **kwargs) -> None:
            print(*args)

    class Table:  # type: ignore[no-redef]
        def __init__(self, title: str = ""):
            self.title = title
            self.columns: list[str] = []
            self.rows: list[list[str]] = []

        def add_column(self, name: str, **_: object) -> None:
            self.columns.append(name)

        def add_row(self, *values: str) -> None:
            self.rows.append(list(values))

        def __str__(self) -> str:
            lines = [self.title] if self.title else []
            if self.columns:
                lines.append(" | ".join(self.columns))
                lines.append("-" * max(3, len(lines[-1])))
            lines.extend(" | ".join(row) for row in self.rows)
            return "\n".join(lines)


console = Console()

BENCHMARK_ADAPTERS = {
    "tau_bench": "harness.benchmarks.tau_bench.TauBenchAdapter",
    "api_bank": "harness.benchmarks.api_bank.APIBankAdapter",
    "mcp_atlas": "harness.benchmarks.mcp_atlas.MCPAtlasAdapter",
    "toolathlon": "harness.benchmarks.toolathlon.ToolathlonAdapter",
    "swe_bench_verified": "harness.benchmarks.swe_bench_verified.SWEBenchVerifiedAdapter",
    "agent_race": "harness.benchmarks.agent_race.AgentRaceAdapter",
    "orchvar_canary": "harness.benchmarks.orchvar_canary.OrchVarCanaryAdapter",
    "multilingual_fidelity": "harness.benchmarks.multilingual_fidelity.MultilingualFidelityAdapter",
}


def _load_benchmark(name: str):
    """Dynamically load a benchmark adapter."""
    module_path, class_name = BENCHMARK_ADAPTERS[name].rsplit(".", 1)
    import importlib

    module = importlib.import_module(module_path)
    return getattr(module, class_name)()


async def run_experiment(config: ExperimentConfig) -> dict:
    """Run a complete experiment across all conditions and tasks.

    The first admitted execution backend is a deterministic local canary actor.
    Unknown or live-provider actor types fail closed until their adapters exist.
    Every cell is journaled before the next cell begins, and resume validates an
    exact contiguous plan prefix.
    """
    expected_seeds = os.environ.get("COTCODEC_SEEDS")
    if expected_seeds is not None:
        try:
            manifest_seeds = [int(seed) for seed in expected_seeds.split(":")]
        except ValueError as exc:
            raise ValueError("COTCODEC_SEEDS must be colon-separated integers") from exc
        if config.seeds != manifest_seeds:
            raise ValueError(
                f"experiment seeds {config.seeds} do not match manifest seeds {manifest_seeds}"
            )

    run_id = os.environ.get("COTCODEC_RUN_ID") or str(
        _mapping(config.extra.get("execution"), "execution").get("run_id", "")
    )
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", run_id):
        raise ValueError(
            "deterministic execution requires a kebab-case COTCODEC_RUN_ID "
            "or execution.run_id"
        )
    experiment_id = run_id
    output_root = Path(os.environ.get("COTCODEC_OUTPUT_DIR", "data"))
    resume = os.environ.get("COTCODEC_RESUME") == "1"

    console.print(f"\n[bold]Experiment: {config.name}[/bold]")
    console.print(f"ID: {experiment_id}")
    console.print(f"Benchmark: {config.benchmark}")
    console.print(f"Run specs: {len(config.iter_run_specs())}")
    console.print(f"Seeds: {config.seeds}")
    console.print()

    benchmark = _load_benchmark(config.benchmark)
    base_prompt = benchmark.get_system_prompt()
    loaded_tasks = await benchmark.load_tasks(count=None)
    tasks = _select_tasks(loaded_tasks, config.tasks)
    _validate_task_manifest(config)
    actor = _load_actor(config)
    budgets = _mapping(config.extra.get("budgets"), "budgets")
    max_steps = _positive_int(budgets.get("max_steps_per_task"), "max_steps_per_task")
    max_tool_calls = _positive_int(
        budgets.get("max_tool_calls_per_task"), "max_tool_calls_per_task"
    )
    plan = _build_plan(config.iter_run_specs(), tasks, config.seeds)
    contract = _execution_contract(config, tasks, base_prompt, actor.identity)
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

    previous_handler = None
    if hasattr(signal, "SIGUSR1"):
        previous_handler = signal.getsignal(signal.SIGUSR1)
        signal.signal(signal.SIGUSR1, request_stop)

    delay_ms = float(os.environ.get("COTCODEC_CELL_DELAY_MS", "0"))
    task_by_id = {task.task_id: task for task in tasks}
    run_spec_by_key = {
        (run.group, run.model): run for run in config.iter_run_specs()
    }
    try:
        for key in plan[journal.completed :]:
            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000)
            if stop_requested:
                journal.acknowledge_interrupt("SIGUSR1")
                return _interrupted_result(journal, run_id)
            task = task_by_id[str(key["task_id"])]
            run_spec = run_spec_by_key[(str(key["run_group"]), str(key["model"]))]
            condition_id = next(
                condition
                for condition in run_spec.conditions
                if condition.value == key["condition"]
            )
            condition = get_condition(condition_id)
            system_prompt = condition.transform_system_prompt(base_prompt)
            try:
                execution = await execute_agent_task(
                    task,
                    actor=actor,
                    tools=DeterministicToolRuntime(),
                    condition=condition,
                    system_prompt=system_prompt,
                    seed=int(key["seed"]),
                    max_steps=max_steps,
                    max_tool_calls=max_tool_calls,
                )
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
                    },
                )
                payload = _cell_payload(
                    key,
                    task,
                    result,
                    execution.messages,
                    evaluation,
                    system_prompt,
                )
            except AgentLoopError as exc:
                payload = _error_cell_payload(key, task, exc)
                journal.append(key, payload)
                raise RuntimeError(
                    f"{task.task_id}: agent loop failed closed: {exc.code}: {exc.detail}"
                ) from exc
            journal.append(key, payload)
            console.print(
                f"  {key['condition']} {task.task_id} seed={key['seed']} - "
                f"{'PASS' if payload['trace']['outcome']['success'] else 'FAIL'}"
            )
            if stop_requested:
                journal.acknowledge_interrupt("SIGUSR1")
                return _interrupted_result(journal, run_id)
    finally:
        if previous_handler is not None:
            signal.signal(signal.SIGUSR1, previous_handler)

    journal.complete()
    result = _materialize_outputs(
        output_root,
        run_id,
        config,
        journal,
    )
    _print_summary_table(result["summaries"])
    return result


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
    missing = [task_id for task_id in selection if task_id not in by_id]
    if missing:
        raise ValueError(f"configured task IDs are missing: {missing}")
    if len(set(selection)) != len(selection):
        raise ValueError("configured task roster contains duplicates")
    return [by_id[task_id] for task_id in selection]


def _load_actor(config: ExperimentConfig) -> DeterministicCanaryActor:
    actor = _mapping(config.extra.get("actor"), "actor")
    if actor != {"type": "deterministic_canary_v1"}:
        raise ValueError(
            "unsupported actor contract; only deterministic_canary_v1 is admitted"
        )
    return DeterministicCanaryActor()


def _validate_task_manifest(config: ExperimentConfig) -> None:
    expected = config.extra.get("task_manifest_sha256")
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError("task_manifest_sha256 is required")
    if config.benchmark != "orchvar_canary":
        raise ValueError("deterministic canary actor requires orchvar_canary")
    task_path = Path("harness/benchmarks/specs/orchvar_canary_tasks.yaml")
    actual = hashlib.sha256(task_path.read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError("OrchVar-Canary task manifest hash drifted")


def _build_plan(
    run_specs: list[ExperimentRunSpec],
    tasks: list[BenchmarkTask],
    seeds: list[int],
) -> list[dict[str, Any]]:
    return [
        {
            "run_group": run.group,
            "model": run.model,
            "condition": condition.value,
            "task_id": task.task_id,
            "seed": seed,
        }
        for run in run_specs
        for condition in run.conditions
        for task in tasks
        for seed in seeds
    ]


def _execution_contract(
    config: ExperimentConfig,
    tasks: list[BenchmarkTask],
    base_prompt: str,
    actor_identity: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "name": config.name,
        "benchmark": config.benchmark,
        "actor_identity": actor_identity,
        "run_specs": [
            {
                "group": run.group,
                "model": run.model,
                "conditions": [condition.value for condition in run.conditions],
            }
            for run in config.iter_run_specs()
        ],
        "tasks": [asdict(task) for task in tasks],
        "seeds": config.seeds,
        "metrics": config.metrics,
        "extra": config.extra,
        "base_prompt_sha256": hashlib.sha256(base_prompt.encode()).hexdigest(),
    }


def _message_payload(message: ExecutedMessage) -> dict[str, Any]:
    tokens = len(message.content.split())
    return {
        "step": message.step,
        "role": message.role,
        "type": message.message_type.value,
        "language": message.language,
        "content": message.content,
        "token_count_input": 0,
        "token_count_output": tokens,
        "latency_ms": 0.0,
        "metadata": message.metadata,
    }


def _cell_payload(
    key: dict[str, Any],
    task: BenchmarkTask,
    result: TaskResult,
    messages: tuple[ExecutedMessage, ...],
    evaluation: dict[str, Any],
    system_prompt: str,
) -> dict[str, Any]:
    message_payloads = [_message_payload(message) for message in messages]
    total_tokens = sum(message["token_count_output"] for message in message_payloads)
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
            "messages": message_payloads,
            "task_result": asdict(result),
            "benchmark_evaluation": evaluation,
            "task_metadata": task.metadata or {},
            "outcome": {
                "success": result.success,
                "tool_calls_correct": result.tool_calls_correct,
                "tool_calls_total": result.tool_calls_total,
                "retries": result.retries,
                "safety_failures": result.safety_failures,
                "total_tokens": total_tokens,
                "total_latency_ms": 0.0,
                "cost_usd": 0.0,
            },
        },
    }


def _error_cell_payload(
    key: dict[str, Any], task: BenchmarkTask, error: AgentLoopError
) -> dict[str, Any]:
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
            "error_receipt": error.to_dict(),
        },
    }


def _interrupted_result(journal: ExecutionJournal, run_id: str) -> dict[str, Any]:
    return {
        "status": "INTERRUPTED_CHECKPOINTED",
        "experiment_id": run_id,
        "completed_cells": journal.completed,
        "total_cells": len(journal.plan_keys),
        "contract_sha256": journal.contract_sha256,
        "journal_root_sha256": journal.journal_root_sha256,
    }


def _materialize_outputs(
    output_root: Path,
    run_id: str,
    config: ExperimentConfig,
    journal: ExecutionJournal,
) -> dict[str, Any]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for payload in journal.payloads():
        if payload.get("terminal_status") != "complete":
            raise RuntimeError("cannot materialize failed-closed experiment cells")
        trace = dict(payload["trace"])
        trace["experiment_id"] = run_id
        key = (trace["run_group"], trace["model"], trace["condition"])
        grouped.setdefault(key, []).append(trace)

    trace_artifacts: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    for (run_group, model, condition), traces in sorted(grouped.items()):
        safe_model = re.sub(r"[^a-z0-9]+", "-", model.casefold()).strip("-")
        path = (
            output_root
            / "traces"
            / config.benchmark
            / condition
            / f"{run_id}__{run_group}__{safe_model}.jsonl"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        encoded = "".join(canonical_json(trace) + "\n" for trace in traces)
        path.write_text(encoded, encoding="utf-8")
        trace_artifacts.append(
            {
                "path": str(path.relative_to(output_root)),
                "sha256": hashlib.sha256(encoded.encode()).hexdigest(),
                "rows": len(traces),
            }
        )
        outcomes = [trace["outcome"] for trace in traces]
        total_calls = sum(outcome["tool_calls_total"] for outcome in outcomes)
        summaries.append(
            {
                "experiment_id": run_id,
                "benchmark": config.benchmark,
                "condition": condition,
                "model": model,
                "run_group": run_group,
                "task_count": len(traces),
                "success_rate": sum(outcome["success"] for outcome in outcomes)
                / len(outcomes),
                "avg_tokens": sum(outcome["total_tokens"] for outcome in outcomes)
                / len(outcomes),
                "avg_latency_ms": 0.0,
                "total_retries": sum(outcome["retries"] for outcome in outcomes),
                "total_safety_failures": sum(
                    outcome["safety_failures"] for outcome in outcomes
                ),
                "tool_correctness": sum(
                    outcome["tool_calls_correct"] for outcome in outcomes
                )
                / max(1, total_calls),
            }
        )
    result = {
        "schema_version": 1,
        "status": "COMPLETE",
        "experiment_id": run_id,
        "contract_sha256": journal.contract_sha256,
        "plan_sha256": journal.plan_sha256,
        "journal_root_sha256": journal.journal_root_sha256,
        "completed_cells": journal.completed,
        "config": {
            "name": config.name,
            "benchmark": config.benchmark,
            "tasks": config.tasks,
            "seeds": config.seeds,
        },
        "trace_artifacts": trace_artifacts,
        "summaries": summaries,
    }
    result_path = output_root / "results" / f"{run_id}_summary.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(canonical_json(result) + "\n", encoding="utf-8")
    return result


def _print_summary_table(summaries: list[dict]) -> None:
    """Print a comparison table of experiment results."""
    table = Table(title="Experiment Results")
    table.add_column("Group", style="magenta")
    table.add_column("Model", style="green")
    table.add_column("Condition", style="cyan")
    table.add_column("Success Rate", justify="right")
    table.add_column("Avg Tokens", justify="right")
    table.add_column("Avg Latency (ms)", justify="right")
    table.add_column("Tool Correctness", justify="right")
    table.add_column("Safety Failures", justify="right")

    for s in summaries:
        table.add_row(
            s.get("run_group") or "-",
            s["model"],
            s["condition"],
            f"{s['success_rate']:.1%}",
            f"{s['avg_tokens']:.0f}",
            f"{s['avg_latency_ms']:.0f}",
            f"{s['tool_correctness']:.1%}",
            str(s["total_safety_failures"]),
        )

    console.print(table)


def main():
    if len(sys.argv) < 2:
        console.print("[red]Usage: python -m harness.runner <experiment.yaml>[/red]")
        sys.exit(1)

    config = ExperimentConfig.from_yaml(sys.argv[1])
    asyncio.run(run_experiment(config))


if __name__ == "__main__":
    main()
