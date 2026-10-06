from __future__ import annotations

import asyncio

import pytest

from harness.agent_loop import AgentLoopError, ToolCall
from harness.benchmarks.orchvar_canary_live_v2 import OrchVarCanaryLiveV2Adapter
from harness.conditions import get_condition
from harness.config import ConditionID
from harness.iterative_agent_loop import (
    DeterministicIterativeCanaryActor,
    IterativeAction,
    execute_iterative_agent_task,
)
from harness.live_canary import SQLiteCanaryToolRuntime


async def _tasks():
    adapter = OrchVarCanaryLiveV2Adapter()
    return adapter, await adapter.load_tasks(count=None)


def test_deterministic_iterative_actor_passes_all_live_v2_tasks() -> None:
    async def run() -> tuple[int, int, int]:
        adapter, tasks = await _tasks()
        condition = get_condition(ConditionID.ENGLISH_ONLY)
        successes = 0
        tool_calls = 0
        decisions = 0
        for task in tasks:
            runtime = SQLiteCanaryToolRuntime()
            execution = await execute_iterative_agent_task(
                task,
                actor=DeterministicIterativeCanaryActor(),
                tools=runtime,
                condition=condition,
                system_prompt=adapter.get_system_prompt(),
                seed=42,
                max_decisions=5,
                max_steps=12,
                max_tool_calls=4,
            )
            receipt = runtime.close_and_receipt()
            evaluation = await adapter.evaluate(task, execution.result)
            successes += int(evaluation["success"])
            tool_calls += receipt["operation_count"]
            decisions += execution.decision_count
        return successes, tool_calls, decisions

    assert asyncio.run(run()) == (6, 9, 15)


def test_iterative_safety_final_observes_actual_untrusted_document() -> None:
    async def run() -> tuple[str, dict]:
        adapter, tasks = await _tasks()
        task = next(task for task in tasks if task.task_id == "canary-safety-01")
        runtime = SQLiteCanaryToolRuntime()
        execution = await execute_iterative_agent_task(
            task,
            actor=DeterministicIterativeCanaryActor(),
            tools=runtime,
            condition=get_condition(ConditionID.ENGLISH_ONLY),
            system_prompt=adapter.get_system_prompt(),
            seed=42,
            max_decisions=3,
            max_steps=8,
            max_tool_calls=2,
        )
        runtime.close_and_receipt()
        return execution.result.final_response, execution.observations[0].result

    response, result = asyncio.run(run())
    assert result["found"] is True
    assert "UNTRUSTED:" in result["document"]
    assert "refuse" in response.casefold()
    assert "cannot reveal the system prompt" in response.casefold()


def test_iterative_tool_budget_fails_closed() -> None:
    class EndlessActor:
        identity = "endless-tool-actor"

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

    async def run() -> None:
        adapter, tasks = await _tasks()
        task = next(task for task in tasks if task.task_id == "canary-safety-01")
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
        finally:
            runtime.close_and_receipt()

    with pytest.raises(AgentLoopError, match="tool-call budget exhausted") as error:
        asyncio.run(run())
    assert error.value.code == "tool_budget_exhausted"
