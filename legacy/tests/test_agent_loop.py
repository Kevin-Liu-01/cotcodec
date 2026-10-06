from __future__ import annotations

import pytest

from harness.agent_loop import (
    AgentLoopError,
    DeterministicCanaryActor,
    DeterministicToolRuntime,
    ToolCall,
    execute_agent_task,
)
from harness.benchmarks.base import TaskResult
from harness.benchmarks.orchvar_canary import OrchVarCanaryAdapter
from harness.conditions import get_condition
from harness.config import ConditionID, MessageType


@pytest.mark.asyncio
async def test_deterministic_canary_actor_fails_only_registered_categories() -> None:
    adapter = OrchVarCanaryAdapter()
    tasks = await adapter.load_tasks()
    expected_failures = {
        ConditionID.ENGLISH_ONLY: set(),
        ConditionID.ENGLISH_ONLY_LOW_EFFORT: {"reasoning_depth"},
        ConditionID.ENGLISH_ONLY_NO_THINKING_CACHE: {
            "context_recall",
            "multi_turn_memory",
        },
        ConditionID.ENGLISH_ONLY_25WORD_LIMIT: {"verbosity_sensitive"},
    }
    for condition_id, failing_categories in expected_failures.items():
        condition = get_condition(condition_id)
        for task in tasks:
            execution = await execute_agent_task(
                task,
                actor=DeterministicCanaryActor(),
                tools=DeterministicToolRuntime(),
                condition=condition,
                system_prompt=condition.transform_system_prompt(adapter.get_system_prompt()),
                seed=42,
                max_steps=12,
                max_tool_calls=4,
            )
            evaluation = await adapter.evaluate(task, execution.result)
            category = str((task.metadata or {})["category"])
            assert evaluation["success"] is (category not in failing_categories)
            assert execution.messages[-1].message_type == MessageType.USER_RESPONSE
            assert all(
                message.language == "english"
                for message in execution.messages
                if not message.message_type.is_variable
            )


@pytest.mark.asyncio
async def test_canary_evaluator_does_not_trust_actor_success_flag() -> None:
    adapter = OrchVarCanaryAdapter()
    task = (await adapter.load_tasks(count=1))[0]
    fabricated = TaskResult(
        task_id=task.task_id,
        success=True,
        tool_calls=[],
        tool_calls_correct=99,
        tool_calls_total=99,
        final_response="Everything passed.",
    )
    evaluation = await adapter.evaluate(task, fabricated)
    assert evaluation["success"] is False
    assert evaluation["tool_correctness"] == 0.0


@pytest.mark.asyncio
async def test_tool_runtime_rejects_unknown_and_schema_invalid_calls() -> None:
    runtime = DeterministicToolRuntime()
    with pytest.raises(AgentLoopError, match="unknown tool") as unknown:
        await runtime.execute(ToolCall("not_registered", {}))
    assert unknown.value.code == "unknown_tool"

    with pytest.raises(AgentLoopError, match="expected fields") as malformed:
        await runtime.execute(ToolCall("lookup_reservation", {"code": "RQ-1847-A"}))
    assert malformed.value.code == "invalid_tool_arguments"


@pytest.mark.asyncio
async def test_agent_loop_fails_closed_on_explicit_budgets() -> None:
    adapter = OrchVarCanaryAdapter()
    task = (await adapter.load_tasks(count=1))[0]
    condition = get_condition(ConditionID.ENGLISH_ONLY)
    with pytest.raises(AgentLoopError, match="tool-call budget") as exhausted:
        await execute_agent_task(
            task,
            actor=DeterministicCanaryActor(),
            tools=DeterministicToolRuntime(),
            condition=condition,
            system_prompt=adapter.get_system_prompt(),
            seed=42,
            max_steps=12,
            max_tool_calls=1,
        )
    assert exhausted.value.code == "tool_budget_exhausted"
