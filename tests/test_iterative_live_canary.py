from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import pytest

from harness.benchmarks.orchvar_canary_live_v2 import OrchVarCanaryLiveV2Adapter
from harness.conditions import get_condition
from harness.config import ConditionID
from harness.iterative_agent_loop import execute_iterative_agent_task
from harness.iterative_live_canary import (
    DeterministicStructuralCanaryActor,
    JsonIterativeCanaryActor,
    JsonStructuralIterativeCanaryActor,
)
from harness.live_canary import SQLiteCanaryToolRuntime


@dataclass
class _Completion:
    text: str
    receipt: dict[str, Any]


class _QueueBackend:
    identity = "queued-completion-v1"
    contract = {"identity": identity, "backend": "queued-mock"}

    def __init__(self, outputs: list[str]):
        self.outputs = list(outputs)
        self.prompts: list[str] = []

    def complete_text(self, prompt: str) -> _Completion:
        self.prompts.append(prompt)
        return _Completion(
            text=self.outputs.pop(0),
            receipt={"prompt_tokens": 10, "completion_tokens": 5},
        )


def test_json_iterative_actor_conditions_final_on_tool_result() -> None:
    backend = _QueueBackend(
        [
            '{"planner_note":"Search safely.","memory_update":null,"action":'
            '{"type":"tool","name":"search_knowledge_base","arguments":'
            '{"query":"retrieved policy document"}}}',
            '{"planner_note":"Reject the injected instruction.","memory_update":null,'
            '"action":{"type":"final","response":"I refuse the prohibited action '
            'and cannot reveal the system prompt."}}',
        ]
    )
    actor = JsonIterativeCanaryActor(backend, provenance={"model": "mock"})

    async def run():
        adapter = OrchVarCanaryLiveV2Adapter()
        tasks = await adapter.load_tasks(count=None)
        task = next(task for task in tasks if task.task_id == "canary-safety-01")
        runtime = SQLiteCanaryToolRuntime()
        execution = await execute_iterative_agent_task(
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
    assert execution.decision_count == 2
    assert '"found":true' in backend.prompts[1]
    assert "UNTRUSTED:" in backend.prompts[1]
    receipts = actor.pop_receipts()
    assert [receipt["action_mode"] for receipt in receipts] == ["tool", "final"]


def test_json_iterative_actor_measures_invalid_tool_arguments_without_execution() -> None:
    backend = _QueueBackend(
        [
            '{"planner_note":"Search.","memory_update":null,"action":'
            '{"type":"tool","name":"search_knowledge_base","arguments":{}}}'
        ]
    )
    actor = JsonIterativeCanaryActor(backend, provenance={})

    async def run():
        adapter = OrchVarCanaryLiveV2Adapter()
        task = (await adapter.load_tasks(count=None))[-1]
        return await actor.decide(
            task,
            system_prompt=adapter.get_system_prompt(),
            condition=ConditionID.ENGLISH_ONLY,
            seed=42,
            observations=(),
        )

    action = asyncio.run(run())
    assert action.mode == "final"
    assert action.tool_call is None
    assert actor.pop_receipts()[0]["action_parse_status"] == "invalid"


def test_structural_protocol_discriminates_exact_action_shapes() -> None:
    async def load():
        return (await OrchVarCanaryLiveV2Adapter().load_tasks(count=None))[-1]

    task = asyncio.run(load())
    tool = JsonStructuralIterativeCanaryActor._parse(
        '{"planner_note":"Search.","memory_update":null,"action":'
        '{"name":"search_knowledge_base","arguments":'
        '{"query":"retrieved policy document"}}}',
        task,
    )
    final = JsonStructuralIterativeCanaryActor._parse(
        '{"planner_note":"Finish.","memory_update":null,"action":'
        '{"response":"I refuse."}}',
        task,
    )
    assert tool.mode == "tool"
    assert final.mode == "final"
    with pytest.raises(ValueError, match="ambiguous"):
        JsonStructuralIterativeCanaryActor._parse(
            '{"planner_note":"Bad.","memory_update":null,"action":'
            '{"name":"search_knowledge_base","arguments":'
            '{"query":"retrieved policy document"},"response":"also finish"}}',
            task,
        )


def test_deterministic_structural_actor_conditions_safety_end_to_end() -> None:
    async def run():
        adapter = OrchVarCanaryLiveV2Adapter()
        task = (await adapter.load_tasks(count=None))[-1]
        runtime = SQLiteCanaryToolRuntime()
        execution = await execute_iterative_agent_task(
            task,
            actor=DeterministicStructuralCanaryActor(),
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
    assert execution.observations[0].result["found"] is True
