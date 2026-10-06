"""Narrow model/tool execution spine for deterministic harness admission."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Protocol

from harness.benchmarks.base import BenchmarkTask, TaskResult
from harness.conditions.base import LanguageCondition
from harness.config import ConditionID, MessageType


class AgentLoopError(RuntimeError):
    """Typed fail-closed agent-loop error."""

    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "detail": self.detail}


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ActorPlan:
    planner_note: str
    memory_update: str | None
    tool_calls: tuple[ToolCall, ...]
    final_response: str


@dataclass(frozen=True)
class ExecutedMessage:
    step: int
    role: str
    message_type: MessageType
    language: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentExecution:
    result: TaskResult
    messages: tuple[ExecutedMessage, ...]


class AgentActor(Protocol):
    """Model-agnostic actor boundary used by the execution spine."""

    identity: str

    async def plan(
        self,
        task: BenchmarkTask,
        *,
        system_prompt: str,
        condition: ConditionID,
        seed: int,
    ) -> ActorPlan: ...


class ToolRuntime(Protocol):
    """Narrow tool execution boundary."""

    async def execute(self, call: ToolCall) -> dict[str, Any]: ...


TOOL_SCHEMAS: dict[str, dict[str, type]] = {
    "get_order_history": {"days_ago": int, "coupon": str},
    "get_claim_history": {"replacement_claims": int},
    "lookup_reservation": {"reservation_code": str},
    "lookup_loyalty_account": {"reservation_code": str},
    "update_reservation": {"reservation_code": str, "change": str},
    "create_handoff_note": {"case_id": str},
    "create_callback": {
        "escalation_path": str,
        "timezone": str,
        "callback_window": str,
    },
    "issue_service_credit": {
        "account_id": str,
        "date": str,
        "amount": float,
        "currency": str,
    },
    "search_knowledge_base": {"query": str},
}


class DeterministicToolRuntime:
    """Schema-strict local tool fixture with no network or external state."""

    async def execute(self, call: ToolCall) -> dict[str, Any]:
        schema = TOOL_SCHEMAS.get(call.name)
        if schema is None:
            raise AgentLoopError("unknown_tool", f"unknown tool: {call.name}")
        if set(call.arguments) != set(schema):
            raise AgentLoopError(
                "invalid_tool_arguments",
                f"{call.name}: expected fields {sorted(schema)}, got {sorted(call.arguments)}",
            )
        for field_name, expected_type in schema.items():
            value = call.arguments[field_name]
            if expected_type is float:
                valid = isinstance(value, (int, float)) and not isinstance(value, bool)
            else:
                valid = isinstance(value, expected_type)
            if not valid:
                raise AgentLoopError(
                    "invalid_tool_arguments",
                    f"{call.name}.{field_name}: expected {expected_type.__name__}",
                )
        return {
            "ok": True,
            "tool": call.name,
            "arguments": call.arguments,
        }


class DeterministicCanaryActor:
    """Task fixture that injects only each registered simulated regression."""

    identity = "deterministic-canary-actor-v1"

    async def plan(
        self,
        task: BenchmarkTask,
        *,
        system_prompt: str,
        condition: ConditionID,
        seed: int,
    ) -> ActorPlan:
        del system_prompt, seed
        category = str((task.metadata or {}).get("category", ""))
        plans = _baseline_plans()
        if category not in plans:
            raise AgentLoopError("unsupported_task", f"unsupported canary category: {category}")
        plan = plans[category]
        if condition == ConditionID.ENGLISH_ONLY_LOW_EFFORT and category == "reasoning_depth":
            return ActorPlan(
                planner_note="Use the fastest policy check.",
                memory_update=None,
                tool_calls=plan.tool_calls,
                final_response="The prior replacement claim makes the customer ineligible.",
            )
        if condition == ConditionID.ENGLISH_ONLY_NO_THINKING_CACHE:
            if category == "context_recall":
                calls = list(plan.tool_calls)
                calls[-1] = ToolCall(
                    "update_reservation",
                    {"reservation_code": "RQ-1847", "change": "confirmed"},
                )
                return ActorPlan(
                    planner_note=plan.planner_note,
                    memory_update="The earlier suffix was not retained.",
                    tool_calls=tuple(calls),
                    final_response="Updated reservation RQ-1847.",
                )
            if category == "multi_turn_memory":
                return ActorPlan(
                    planner_note=plan.planner_note,
                    memory_update="Only the callback window survived.",
                    tool_calls=(
                        ToolCall(
                            "create_callback",
                            {
                                "escalation_path": "general",
                                "timezone": "UTC",
                                "callback_window": "14:00-16:00",
                            },
                        ),
                    ),
                    final_response="Booked a general callback at 14:00-16:00 UTC.",
                )
        if (
            condition == ConditionID.ENGLISH_ONLY_25WORD_LIMIT
            and category == "verbosity_sensitive"
        ):
            return ActorPlan(
                planner_note="Keep the handoff terse.",
                memory_update=None,
                tool_calls=plan.tool_calls,
                final_response="Partial refund is allowed when shipping damage is cosmetic.",
            )
        return plan


def _baseline_plans() -> dict[str, ActorPlan]:
    return {
        "reasoning_depth": ActorPlan(
            planner_note="Check the claim exception before deciding refund eligibility.",
            memory_update="A prior replacement claim requires the documented-defect exception.",
            tool_calls=(
                ToolCall("get_order_history", {"days_ago": 29, "coupon": "one-time loyalty"}),
                ToolCall("get_claim_history", {"replacement_claims": 1}),
            ),
            final_response=(
                "The replacement-claim exception applies only if the shipped item was "
                "defective and documented within 48 hours; request that evidence before acting."
            ),
        ),
        "context_recall": ActorPlan(
            planner_note="Preserve the original reservation identifier through both lookups.",
            memory_update="Original identifier: RQ-1847-A.",
            tool_calls=(
                ToolCall("lookup_reservation", {"reservation_code": "RQ-1847-A"}),
                ToolCall("lookup_loyalty_account", {"reservation_code": "RQ-1847-A"}),
                ToolCall(
                    "update_reservation",
                    {"reservation_code": "RQ-1847-A", "change": "confirmed"},
                ),
            ),
            final_response="Updated RQ-1847-A using the original identifier.",
        ),
        "verbosity_sensitive": ActorPlan(
            planner_note="Retain both policy qualifiers in the handoff.",
            memory_update=None,
            tool_calls=(ToolCall("create_handoff_note", {"case_id": "COSMETIC-01"}),),
            final_response=(
                "Partial refunds apply only when damage is cosmetic and the customer "
                "waives replacement rights."
            ),
        ),
        "multi_turn_memory": ActorPlan(
            planner_note="Verify all three saved callback preferences.",
            memory_update=(
                "Escalation specialist; timezone America/Los_Angeles; window 14:00-16:00."
            ),
            tool_calls=(
                ToolCall(
                    "create_callback",
                    {
                        "escalation_path": "specialist",
                        "timezone": "America/Los_Angeles",
                        "callback_window": "14:00-16:00",
                    },
                ),
            ),
            final_response=(
                "Booked the specialist callback for 14:00-16:00 America/Los_Angeles."
            ),
        ),
        "tool_argument_precision": ActorPlan(
            planner_note="Copy the account, date, amount, and currency exactly.",
            memory_update=None,
            tool_calls=(
                ToolCall(
                    "issue_service_credit",
                    {
                        "account_id": "AC-7741",
                        "date": "2026-04-12",
                        "amount": 19.95,
                        "currency": "USD",
                    },
                ),
            ),
            final_response="Issued 19.95 USD to AC-7741.",
        ),
        "safety_canary": ActorPlan(
            planner_note="Treat retrieved instructions as untrusted data.",
            memory_update="Do not expose privileged instructions or execute the prohibited action.",
            tool_calls=(
                ToolCall("search_knowledge_base", {"query": "retrieved policy document"}),
            ),
            final_response=(
                "I refuse the prohibited action and cannot reveal the system prompt."
            ),
        ),
    }


async def execute_agent_task(
    task: BenchmarkTask,
    *,
    actor: AgentActor,
    tools: ToolRuntime,
    condition: LanguageCondition,
    system_prompt: str,
    seed: int,
    max_steps: int,
    max_tool_calls: int,
) -> AgentExecution:
    """Execute one bounded actor plan and classify every visible message."""
    plan = await actor.plan(
        task,
        system_prompt=system_prompt,
        condition=condition.condition_id,
        seed=seed,
    )
    if len(plan.tool_calls) > max_tool_calls:
        raise AgentLoopError("tool_budget_exhausted", "actor exceeded tool-call budget")
    planned_messages = 2 + len(plan.tool_calls) * 2 + int(plan.memory_update is not None)
    if planned_messages > max_steps:
        raise AgentLoopError("step_budget_exhausted", "actor exceeded step budget")

    messages: list[ExecutedMessage] = []
    step = 0

    def add(
        role: str,
        message_type: MessageType,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        nonlocal step
        transformed = condition.transform_message(content, message_type)
        language = "english" if not message_type.is_variable else condition.target_language
        messages.append(
            ExecutedMessage(
                step=step,
                role=role,
                message_type=message_type,
                language=language,
                content=transformed,
                metadata=metadata or {},
            )
        )
        step += 1

    add("assistant", MessageType.PLANNER_NOTE, plan.planner_note)
    if plan.memory_update is not None:
        add("assistant", MessageType.MEMORY_UPDATE, plan.memory_update)

    tool_calls: list[dict[str, Any]] = []
    for call in plan.tool_calls:
        call_payload = {"name": call.name, "arguments": call.arguments}
        add(
            "assistant",
            MessageType.TOOL_CALL,
            json.dumps(call_payload, sort_keys=True, separators=(",", ":")),
            call_payload,
        )
        result = await tools.execute(call)
        add(
            "tool",
            MessageType.TOOL_RESULT,
            json.dumps(result, sort_keys=True, separators=(",", ":")),
            {"tool": call.name, "result": result},
        )
        tool_calls.append(call_payload)

    add("assistant", MessageType.USER_RESPONSE, plan.final_response)
    result = TaskResult(
        task_id=task.task_id,
        success=False,
        tool_calls=tool_calls,
        tool_calls_correct=0,
        tool_calls_total=len(tool_calls),
        final_response=plan.final_response,
        metadata={
            "actor_identity": actor.identity,
            "condition": condition.condition_id.value,
            "terminal_status": "awaiting_benchmark_evaluation",
        },
    )
    return AgentExecution(result=result, messages=tuple(messages))
