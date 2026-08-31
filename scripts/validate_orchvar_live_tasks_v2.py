#!/usr/bin/env python3
"""Audit prompt-to-oracle recoverability for OrchVar live tasks v2."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.agent_loop import TOOL_SCHEMAS  # noqa: E402
from harness.yaml_utils import load_yaml_file  # noqa: E402

DEFAULT_TASKS = (
    PROJECT_ROOT / "harness/benchmarks/specs/orchvar_canary_live_v2_tasks.yaml"
)
TASK_IDS = [
    "canary-reasoning-depth-01",
    "canary-context-recall-01",
    "canary-verbosity-sensitive-01",
    "canary-multi-turn-memory-01",
    "canary-tool-argument-precision-01",
    "canary-safety-01",
]
CATEGORIES = [
    "reasoning_depth",
    "context_recall",
    "verbosity_sensitive",
    "multi_turn_memory",
    "tool_argument_precision",
    "safety_canary",
]


class LiveTaskInterfaceError(ValueError):
    """Raised when a task requires information absent from the actor prompt."""


def _literal(value: Any) -> str:
    if isinstance(value, bool) or value is None or isinstance(value, (list, dict)):
        raise LiveTaskInterfaceError("tool arguments must use visible scalar leaves")
    return str(value).casefold()


def _scalar_leaves(value: Any) -> list[Any]:
    if isinstance(value, dict):
        return [leaf for item in value.values() for leaf in _scalar_leaves(item)]
    if isinstance(value, list):
        return [leaf for item in value for leaf in _scalar_leaves(item)]
    return [value]


def validate_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version",
        "interface_contract",
        "tasks",
    }:
        raise LiveTaskInterfaceError("live-v2 manifest fields drifted")
    if payload.get("schema_version") != 2 or payload.get("interface_contract") != {
        "self_contained": True,
        "tool_call_order": "exact",
        "response_oracle": "deterministic_phrase_groups",
        "claim_boundary": "one_plan_transport_smoke_not_multiturn_or_model_quality",
    }:
        raise LiveTaskInterfaceError("live-v2 interface contract drifted")
    tasks = payload.get("tasks")
    if not isinstance(tasks, list) or [task.get("task_id") for task in tasks] != TASK_IDS:
        raise LiveTaskInterfaceError("live-v2 task roster drifted")
    if [task.get("category") for task in tasks] != CATEGORIES:
        raise LiveTaskInterfaceError("live-v2 category roster drifted")

    projections: list[dict[str, Any]] = []
    task_fields = {
        "task_id",
        "category",
        "target_variable",
        "expected_failure_mode",
        "instruction",
        "tools",
        "expected_outcome",
        "metadata",
    }
    for task in tasks:
        task_id = task["task_id"]
        if set(task) != task_fields or not isinstance(task.get("instruction"), str):
            raise LiveTaskInterfaceError(f"{task_id}: task fields drifted")
        instruction = task["instruction"].casefold()
        tools = task.get("tools")
        if not isinstance(tools, list) or not tools:
            raise LiveTaskInterfaceError(f"{task_id}: tools are missing")
        exposed = [tool.get("name") for tool in tools if isinstance(tool, dict)]
        oracle = (task.get("expected_outcome") or {}).get("oracle")
        if not isinstance(oracle, dict) or set(oracle) not in (
            {"required_tool_calls", "response_contains_any", "response_not_contains"},
            {
                "required_tool_calls",
                "response_contains_any",
                "response_not_contains",
                "safety_refusal_required",
            },
        ):
            raise LiveTaskInterfaceError(f"{task_id}: oracle fields drifted")
        calls = oracle["required_tool_calls"]
        if not isinstance(calls, list) or not calls:
            raise LiveTaskInterfaceError(f"{task_id}: required calls are missing")
        visible_literals: list[str] = []
        for call in calls:
            if not isinstance(call, dict) or set(call) != {"name", "arguments"}:
                raise LiveTaskInterfaceError(f"{task_id}: call fields drifted")
            name = call["name"]
            arguments = call["arguments"]
            schema = TOOL_SCHEMAS.get(name)
            if name not in exposed or schema is None or set(arguments) != set(schema):
                raise LiveTaskInterfaceError(f"{task_id}: call schema is not exposed")
            for field, expected_type in schema.items():
                value = arguments[field]
                valid = (
                    isinstance(value, (int, float)) and not isinstance(value, bool)
                    if expected_type is float
                    else isinstance(value, expected_type)
                )
                if not valid:
                    raise LiveTaskInterfaceError(f"{task_id}: {name}.{field} type drifted")
            for leaf in _scalar_leaves(arguments):
                literal = _literal(leaf)
                visible_literals.append(literal)
                if literal not in instruction:
                    raise LiveTaskInterfaceError(
                        f"{task_id}: oracle literal is not visible: {literal}"
                    )
        groups = oracle["response_contains_any"]
        if not isinstance(groups, list) or not groups:
            raise LiveTaskInterfaceError(f"{task_id}: response groups are missing")
        for group in groups:
            if not isinstance(group, list) or not group or not all(
                isinstance(phrase, str) and phrase for phrase in group
            ):
                raise LiveTaskInterfaceError(f"{task_id}: response group drifted")
            if not any(phrase.casefold() in instruction for phrase in group):
                raise LiveTaskInterfaceError(
                    f"{task_id}: response criterion is not grounded in the prompt"
                )
        forbidden = oracle["response_not_contains"]
        if not isinstance(forbidden, list) or not all(
            isinstance(phrase, str) and phrase for phrase in forbidden
        ):
            raise LiveTaskInterfaceError(f"{task_id}: forbidden phrases drifted")
        if task.get("metadata") != {
            "category": task["category"],
            "target_variable": task["target_variable"],
            "expected_failure_mode": task["expected_failure_mode"],
        }:
            raise LiveTaskInterfaceError(f"{task_id}: metadata drifted")
        projections.append(
            {
                "task_id": task_id,
                "visible_oracle_literals": visible_literals,
                "required_tool_names": [call["name"] for call in calls],
                "response_group_count": len(groups),
            }
        )
    return {
        "schema_version": 1,
        "status": "ORCHVAR_LIVE_TASK_INTERFACE_V2_RECOVERABLE",
        "task_count": len(tasks),
        "tasks": projections,
    }


def validate_tasks(path: Path = DEFAULT_TASKS) -> dict[str, Any]:
    return validate_payload(load_yaml_file(path))


def main() -> int:
    projection = validate_tasks()
    print(
        json.dumps(
            {
                "status": projection["status"],
                "task_manifest_sha256": hashlib.sha256(DEFAULT_TASKS.read_bytes()).hexdigest(),
                "projection_sha256": hashlib.sha256(
                    json.dumps(projection, sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest(),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
