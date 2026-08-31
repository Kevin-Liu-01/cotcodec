#!/usr/bin/env python3
"""Run the zero-model-call execution control for live task interface v2."""

from __future__ import annotations

import asyncio
import hashlib
import sys
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.agent_loop import DeterministicCanaryActor, execute_agent_task  # noqa: E402
from harness.benchmarks.orchvar_canary_live_v2 import (  # noqa: E402
    OrchVarCanaryLiveV2Adapter,
)
from harness.conditions import get_condition  # noqa: E402
from harness.config import ConditionID  # noqa: E402
from harness.live_canary import SQLiteCanaryToolRuntime  # noqa: E402
from harness.run_state import canonical_json, sha256_json  # noqa: E402
from scripts.validate_orchvar_live_tasks_v2 import (  # noqa: E402
    DEFAULT_TASKS,
    validate_tasks,
)

DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data/results/orchvar-live-task-interface-v2/2026-08-26-admission/report.json"
)
BOUND_FILES = [
    "harness/agent_loop.py",
    "harness/benchmarks/orchvar_canary_live_v2.py",
    "harness/benchmarks/specs/orchvar_canary_live_v2_tasks.yaml",
    "harness/live_canary.py",
    "scripts/run_orchvar_live_task_v2_admission.py",
    "scripts/validate_orchvar_live_tasks_v2.py",
]


async def run_admission() -> dict[str, Any]:
    interface_projection = validate_tasks()
    adapter = OrchVarCanaryLiveV2Adapter()
    tasks = await adapter.load_tasks(count=None)
    actor = DeterministicCanaryActor()
    condition = get_condition(ConditionID.ENGLISH_ONLY)
    system_prompt = condition.transform_system_prompt(adapter.get_system_prompt())
    task_receipts: list[dict[str, Any]] = []
    for task in tasks:
        tools = SQLiteCanaryToolRuntime()
        execution = await execute_agent_task(
            task,
            actor=actor,
            tools=tools,
            condition=condition,
            system_prompt=system_prompt,
            seed=42,
            max_steps=12,
            max_tool_calls=4,
        )
        tool_receipt = tools.close_and_receipt()
        evaluation = await adapter.evaluate(task, execution.result)
        result = replace(
            execution.result,
            success=bool(evaluation["success"]),
            tool_calls_correct=int(evaluation["tool_calls_correct"]),
            tool_calls_total=int(evaluation["tool_calls_total"]),
            safety_failures=int(evaluation["safety_failures"]),
        )
        task_receipts.append(
            {
                "task": asdict(task),
                "result": asdict(result),
                "evaluation": evaluation,
                "tool_runtime_receipt": tool_receipt,
            }
        )
    source_sha256 = {
        relative: hashlib.sha256((PROJECT_ROOT / relative).read_bytes()).hexdigest()
        for relative in BOUND_FILES
    }
    report = {
        "schema_version": 1,
        "status": "ORCHVAR_LIVE_TASK_INTERFACE_V2_CPU_ADMISSION_PASS",
        "scientific_result": False,
        "publication_ready": False,
        "task_manifest_sha256": hashlib.sha256(DEFAULT_TASKS.read_bytes()).hexdigest(),
        "interface_projection": interface_projection,
        "interface_projection_sha256": sha256_json(interface_projection),
        "actor_identity": actor.identity,
        "tool_runtime_identity": SQLiteCanaryToolRuntime.identity,
        "external_model_calls": 0,
        "task_count": len(task_receipts),
        "task_success_count": sum(receipt["result"]["success"] for receipt in task_receipts),
        "tool_operation_count": sum(
            receipt["tool_runtime_receipt"]["operation_count"]
            for receipt in task_receipts
        ),
        "tasks": task_receipts,
        "bound_source_sha256": source_sha256,
        "claim_boundary": (
            "CPU task-interface admission only. This proves visible prompt-to-oracle "
            "recoverability plus deterministic actor, evaluator, and SQLite execution "
            "compatibility. It is not a live-model, multiturn-memory, language-effect, "
            "benchmark-validity, model-quality, H100, or publication result."
        ),
    }
    if (
        report["task_count"] != 6
        or report["task_success_count"] != 6
        or report["tool_operation_count"] != 9
        or any(receipt["result"]["safety_failures"] for receipt in task_receipts)
    ):
        raise RuntimeError("live-v2 deterministic execution control failed")
    return report


def main() -> int:
    output = Path(sys.argv[1]).resolve() if len(sys.argv) == 2 else DEFAULT_OUTPUT
    report = asyncio.run(run_admission())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(canonical_json(report) + "\n", encoding="utf-8")
    print(
        canonical_json(
            {
                "status": report["status"],
                "task_manifest_sha256": report["task_manifest_sha256"],
                "report_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
