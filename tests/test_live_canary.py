from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import pytest

from harness.agent_loop import ToolCall
from harness.benchmarks.base import BenchmarkTask
from harness.config import ConditionID
from harness.live_canary import JsonPlanCanaryActor, SQLiteCanaryToolRuntime


@dataclass
class _Completion:
    text: str
    receipt: dict[str, Any]


class _Backend:
    identity = "mock-completion-v1"
    contract = {"identity": identity, "backend": "mock"}

    def __init__(self, text: str):
        self.text = text

    def complete_text(self, prompt: str) -> _Completion:
        assert "OUTPUT_CONTRACT=" in prompt
        return _Completion(
            text=self.text,
            receipt={"prompt_tokens": 10, "completion_tokens": 20},
        )


def _task() -> BenchmarkTask:
    return BenchmarkTask(
        task_id="task-1",
        instruction="Find the reservation.",
        tools=[{"name": "lookup_reservation", "type": "lookup"}],
    )


def test_json_plan_actor_accepts_exact_plan() -> None:
    actor = JsonPlanCanaryActor(
        _Backend(
            '{"planner_note":"Check it.","memory_update":null,'
            '"tool_calls":[{"name":"lookup_reservation","arguments":'
            '{"reservation_code":"RQ-1847-A"}}],'
            '"final_response":"Found RQ-1847-A."}'
        ),
        provenance={"receipt": "pinned"},
    )
    plan = asyncio.run(
        actor.plan(
            _task(),
            system_prompt="Be exact.",
            condition=ConditionID.ENGLISH_ONLY,
            seed=42,
        )
    )
    assert plan.tool_calls == (
        ToolCall("lookup_reservation", {"reservation_code": "RQ-1847-A"}),
    )
    receipt = actor.pop_receipt()
    assert receipt["plan_parse_status"] == "valid"
    assert receipt["prompt_tokens"] == 10
    assert len(receipt["prompt_sha256"]) == 64


def test_json_plan_actor_records_invalid_output_as_measured_failure() -> None:
    actor = JsonPlanCanaryActor(_Backend("not json"), provenance={})
    plan = asyncio.run(
        actor.plan(
            _task(),
            system_prompt="Be exact.",
            condition=ConditionID.ENGLISH_ONLY,
            seed=42,
        )
    )
    assert plan.tool_calls == ()
    assert plan.final_response == "not json"
    assert actor.pop_receipt()["plan_parse_status"] == "invalid"


def test_json_plan_actor_rejects_non_baseline_condition() -> None:
    actor = JsonPlanCanaryActor(_Backend("{}"), provenance={})
    with pytest.raises(Exception, match="English baseline"):
        asyncio.run(
            actor.plan(
                _task(),
                system_prompt="Be exact.",
                condition=ConditionID.INTERNAL_CHINESE,
                seed=42,
            )
        )


def test_sqlite_runtime_executes_lookup_and_mutation_with_stable_state() -> None:
    async def execute_once() -> dict[str, Any]:
        runtime = SQLiteCanaryToolRuntime()
        lookup = await runtime.execute(
            ToolCall("lookup_reservation", {"reservation_code": "RQ-1847-A"})
        )
        update = await runtime.execute(
            ToolCall(
                "update_reservation",
                {"reservation_code": "RQ-1847-A", "change": "confirmed"},
            )
        )
        receipt = runtime.close_and_receipt()
        assert lookup["found"] is True
        assert update["updated"] is True
        return receipt

    first = asyncio.run(execute_once())
    second = asyncio.run(execute_once())
    assert first["operation_count"] == 2
    assert first["operations"] == second["operations"]
    assert first["final_state_sha256"] == second["final_state_sha256"]
