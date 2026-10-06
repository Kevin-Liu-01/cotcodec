from __future__ import annotations

import asyncio

import pytest

from harness.agent_loop import AgentLoopError
from harness.benchmarks.orchvar_canary_live_v2 import OrchVarCanaryLiveV2Adapter
from harness.conditions import get_condition
from harness.config import ConditionID
from harness.live_canary import SQLiteCanaryToolRuntime
from harness.two_stage_agent_loop import (
    ActionOnlyJsonParser,
    DeterministicTwoStageCanaryActor,
    ResearchMessages,
    execute_two_stage_agent_task,
)


def test_two_stage_deterministic_actor_passes_all_tasks_and_safety() -> None:
    async def run():
        adapter = OrchVarCanaryLiveV2Adapter()
        rows = []
        for task in await adapter.load_tasks(count=None):
            runtime = SQLiteCanaryToolRuntime()
            execution = await execute_two_stage_agent_task(
                task,
                actor=DeterministicTwoStageCanaryActor(),
                tools=runtime,
                condition=get_condition(ConditionID.ENGLISH_ONLY),
                system_prompt=adapter.get_system_prompt(),
                seed=42,
                max_decisions=5,
                max_steps=12,
                max_tool_calls=4,
            )
            receipt = runtime.close_and_receipt()
            rows.append((task, execution, await adapter.evaluate(task, execution.result), receipt))
        return rows

    rows = asyncio.run(run())
    assert sum(evaluation["success"] for _, _, evaluation, _ in rows) == 6
    assert sum(receipt["operation_count"] for *_, receipt in rows) == 9
    assert sum(execution.decision_count for _, execution, _, _ in rows) == 15
    assert all(
        execution.message_stage_count == execution.action_stage_count
        for _, execution, _, _ in rows
    )
    safety = rows[-1][1]
    assert safety.observations[0].result["found"] is True
    assert "refuse" in safety.result.final_response.casefold()


def test_action_only_parser_rejects_messages_ambiguity_and_bad_arguments() -> None:
    async def task():
        return (await OrchVarCanaryLiveV2Adapter().load_tasks(count=None))[-1]

    safety = asyncio.run(task())
    with pytest.raises(ValueError, match="top-level"):
        ActionOnlyJsonParser.parse(
            '{"planner_note":"x","action":{"response":"done"}}', safety
        )
    with pytest.raises(ValueError, match="ambiguous"):
        ActionOnlyJsonParser.parse(
            '{"action":{"response":"done","name":"search_knowledge_base",'
            '"arguments":{"query":"retrieved policy document"}}}',
            safety,
        )
    with pytest.raises(ValueError, match="arguments"):
        ActionOnlyJsonParser.parse(
            '{"action":{"name":"search_knowledge_base","arguments":{}}}', safety
        )


def test_missing_message_fails_before_action_or_tool_execution() -> None:
    class MissingMessageActor(DeterministicTwoStageCanaryActor):
        action_calls = 0

        async def generate_messages(self, task, **kwargs):
            del task, kwargs
            return ResearchMessages(planner_note="", memory_update=None)

        async def decide_action(self, task, **kwargs):
            self.action_calls += 1
            return await super().decide_action(task, **kwargs)

    async def run():
        adapter = OrchVarCanaryLiveV2Adapter()
        task = (await adapter.load_tasks(count=None))[-1]
        actor = MissingMessageActor()
        runtime = SQLiteCanaryToolRuntime()
        with pytest.raises(ValueError, match="planner message"):
            await execute_two_stage_agent_task(
                task,
                actor=actor,
                tools=runtime,
                condition=get_condition(ConditionID.ENGLISH_ONLY),
                system_prompt=adapter.get_system_prompt(),
                seed=42,
                max_decisions=3,
                max_steps=8,
                max_tool_calls=2,
            )
        receipt = runtime.close_and_receipt()
        return actor, receipt

    actor, receipt = asyncio.run(run())
    assert actor.action_calls == 0
    assert receipt["operation_count"] == 0


def test_two_stage_tool_budget_fails_closed() -> None:
    class EndlessActor(DeterministicTwoStageCanaryActor):
        async def decide_action(self, task, **kwargs):
            kwargs["observations"] = ()
            return await super().decide_action(task, **kwargs)

    async def run():
        adapter = OrchVarCanaryLiveV2Adapter()
        task = (await adapter.load_tasks(count=None))[-1]
        runtime = SQLiteCanaryToolRuntime()
        try:
            with pytest.raises(AgentLoopError, match="tool budget") as captured:
                await execute_two_stage_agent_task(
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
            return captured.value.code
        finally:
            runtime.close_and_receipt()

    assert asyncio.run(run()) == "tool_budget_exhausted"
