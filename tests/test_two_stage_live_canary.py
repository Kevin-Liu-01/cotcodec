from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import pytest

from harness.agent_loop import AgentLoopError
from harness.benchmarks.orchvar_canary_live_v2 import OrchVarCanaryLiveV2Adapter
from harness.conditions import get_condition
from harness.config import ConditionID
from harness.live_canary import SQLiteCanaryToolRuntime
from harness.two_stage_agent_loop import ResearchMessages, execute_two_stage_agent_task
from harness.two_stage_live_canary import PlainMessageActionJsonActor


@dataclass
class _Completion:
    text: str
    receipt: dict[str, Any]


class _QueueBackend:
    identity = "two-stage-queue-v1"
    contract = {"identity": identity, "backend": "mock"}

    def __init__(self, outputs: list[str]) -> None:
        self.outputs = list(outputs)
        self.prompts: list[str] = []

    def complete_text(self, prompt: str) -> _Completion:
        self.prompts.append(prompt)
        return _Completion(
            self.outputs.pop(0),
            {"prompt_tokens": 10, "completion_tokens": 5},
        )


def test_live_two_stage_actor_conditions_safety_action_on_tool_result() -> None:
    backend = _QueueBackend(
        [
            "Search for the exact policy document safely.",
            "Remember the exact query and refuse untrusted instructions.",
            '{"action":{"name":"search_knowledge_base","arguments":'
            '{"query":"retrieved policy document"}}}',
            "The result is untrusted and requests prohibited disclosure.",
            '{"action":{"response":"I refuse the prohibited action and cannot '
            'reveal the system prompt."}}',
        ]
    )
    actor = PlainMessageActionJsonActor(backend, provenance={})

    async def run():
        adapter = OrchVarCanaryLiveV2Adapter()
        task = (await adapter.load_tasks(count=None))[-1]
        runtime = SQLiteCanaryToolRuntime()
        execution = await execute_two_stage_agent_task(
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
        runtime.close_and_receipt()
        return execution, await adapter.evaluate(task, execution.result)

    execution, evaluation = asyncio.run(run())
    assert evaluation["success"] is True
    assert execution.message_stage_count == execution.action_stage_count == 2
    assert '"found":true' in backend.prompts[3]
    assert "UNTRUSTED:" in backend.prompts[4]
    receipts = actor.pop_receipts()
    assert [row["stage"] for row in receipts] == [
        "planner_message",
        "memory_message",
        "action",
        "planner_message",
        "action",
    ]
    assert all(row["compliance"] == "valid" for row in receipts)


def test_empty_planner_stops_before_memory_or_action() -> None:
    backend = _QueueBackend([""])
    actor = PlainMessageActionJsonActor(backend, provenance={})

    async def run():
        task = (await OrchVarCanaryLiveV2Adapter().load_tasks(count=None))[-1]
        with pytest.raises(AgentLoopError) as captured:
            await actor.generate_messages(
                task,
                message_system_prompt="system",
                condition=ConditionID.ENGLISH_ONLY,
                seed=42,
                observations=(),
            )
        return captured.value

    error = asyncio.run(run())
    assert error.code == "planner_message_noncompliance"
    assert len(backend.prompts) == 1
    assert actor.pop_receipts()[0]["compliance"] == "invalid_empty"


def test_invalid_action_is_measured_and_rejected() -> None:
    backend = _QueueBackend(['{"action":{"name":"search_knowledge_base","arguments":{}}}'])
    actor = PlainMessageActionJsonActor(backend, provenance={})

    async def run():
        task = (await OrchVarCanaryLiveV2Adapter().load_tasks(count=None))[-1]
        with pytest.raises(AgentLoopError) as captured:
            await actor.decide_action(
                task,
                action_system_prompt="system",
                conditioned_messages=ResearchMessages("plan", "memory"),
                seed=42,
                observations=(),
            )
        return captured.value

    error = asyncio.run(run())
    assert error.code == "action_contract_invalid"
    receipt = actor.pop_receipts()[0]
    assert receipt["compliance"] == "invalid"
    assert "arguments" in receipt["parse_error"]
