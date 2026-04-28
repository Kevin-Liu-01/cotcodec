"""Experiment runner — executes experiment definitions against benchmarks.

Usage:
    python -m harness.runner experiments/pilot_01.yaml
"""

from __future__ import annotations

import asyncio
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

from harness.config import ConditionID, ExperimentConfig
from harness.conditions import get_condition
from harness.metrics.collector import MetricCollector

console = Console()

BENCHMARK_ADAPTERS = {
    "tau_bench": "harness.benchmarks.tau_bench.TauBenchAdapter",
    "api_bank": "harness.benchmarks.api_bank.APIBankAdapter",
}


def _load_benchmark(name: str):
    """Dynamically load a benchmark adapter."""
    module_path, class_name = BENCHMARK_ADAPTERS[name].rsplit(".", 1)
    import importlib
    module = importlib.import_module(module_path)
    return getattr(module, class_name)()


async def run_experiment(config: ExperimentConfig) -> dict:
    """Run a complete experiment across all conditions and tasks.

    For each (condition, task, seed) triple:
    1. Load the benchmark adapter
    2. Apply the language condition to the system prompt
    3. Execute the agent loop (TODO: integrate with model APIs)
    4. Collect traces and metrics
    5. Write results to disk
    """
    experiment_id = f"{config.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    output_dir = Path("data/traces")

    console.print(f"\n[bold]Experiment: {config.name}[/bold]")
    console.print(f"ID: {experiment_id}")
    console.print(f"Benchmark: {config.benchmark}")
    console.print(f"Model: {config.model}")
    console.print(f"Conditions: {[c.value for c in config.conditions]}")
    console.print(f"Seeds: {config.seeds}")
    console.print()

    benchmark = _load_benchmark(config.benchmark)
    base_prompt = benchmark.get_system_prompt()

    summaries = []

    for condition_id in config.conditions:
        condition = get_condition(condition_id)
        system_prompt = condition.transform_system_prompt(base_prompt)

        collector = MetricCollector(
            experiment_id=experiment_id,
            benchmark=config.benchmark,
            condition=condition_id,
            model=config.model,
        )

        console.print(f"[yellow]Condition: {condition_id.value}[/yellow]")
        console.print(f"  Target language: {condition.target_language}")
        console.print(f"  System prompt length: {len(system_prompt)} chars")

        tasks = await benchmark.load_tasks(
            count=config.tasks if isinstance(config.tasks, int) else None
        )

        for task in tasks:
            for seed in config.seeds:
                collector.start_task(task.task_id, seed)

                # TODO: Execute agent loop with model API
                # This is where the actual LLM calls happen.
                # For now, we just demonstrate the harness structure.
                console.print(
                    f"  Task {task.task_id} seed={seed} — "
                    f"[dim]agent loop not yet implemented[/dim]"
                )

                collector.end_task(success=False)

        trace_path = collector.flush(output_dir)
        summary = collector.summary()
        summaries.append(summary)

        console.print(f"  Traces written to: {trace_path}")
        console.print()

    result = {
        "experiment_id": experiment_id,
        "config": {
            "name": config.name,
            "benchmark": config.benchmark,
            "model": config.model,
            "conditions": [c.value for c in config.conditions],
            "tasks": config.tasks,
            "seeds": config.seeds,
        },
        "summaries": summaries,
        "timestamp": datetime.now().isoformat(),
    }

    result_path = Path(f"data/results/{experiment_id}_summary.json")
    result_path.parent.mkdir(parents=True, exist_ok=True)
    with open(result_path, "w") as f:
        json.dump(result, f, indent=2)

    _print_summary_table(summaries)

    return result


def _print_summary_table(summaries: list[dict]) -> None:
    """Print a comparison table of experiment results."""
    table = Table(title="Experiment Results")
    table.add_column("Condition", style="cyan")
    table.add_column("Success Rate", justify="right")
    table.add_column("Avg Tokens", justify="right")
    table.add_column("Avg Latency (ms)", justify="right")
    table.add_column("Tool Correctness", justify="right")
    table.add_column("Safety Failures", justify="right")

    for s in summaries:
        table.add_row(
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
