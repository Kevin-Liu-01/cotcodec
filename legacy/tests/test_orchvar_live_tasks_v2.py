from __future__ import annotations

import asyncio
from copy import deepcopy

import pytest

from harness.yaml_utils import load_yaml_file
from scripts.run_orchvar_live_task_v2_admission import run_admission
from scripts.validate_orchvar_live_tasks_v2 import (
    DEFAULT_TASKS,
    LiveTaskInterfaceError,
    validate_payload,
    validate_tasks,
)


def test_live_v2_task_interface_is_recoverable() -> None:
    projection = validate_tasks()
    assert projection["task_count"] == 6
    assert all(task["visible_oracle_literals"] for task in projection["tasks"])


def test_live_v2_deterministic_sqlite_control_passes() -> None:
    report = asyncio.run(run_admission())
    assert report["external_model_calls"] == 0
    assert report["task_success_count"] == 6
    assert report["tool_operation_count"] == 9


@pytest.mark.parametrize(
    ("task_id", "literal"),
    [
        ("canary-context-recall-01", "confirmed"),
        ("canary-verbosity-sensitive-01", "COSMETIC-01"),
        ("canary-multi-turn-memory-01", "America/Los_Angeles"),
        ("canary-safety-01", "retrieved policy document"),
    ],
)
def test_live_v2_missing_oracle_literal_fails_closed(
    task_id: str, literal: str
) -> None:
    payload = deepcopy(load_yaml_file(DEFAULT_TASKS))
    task = next(task for task in payload["tasks"] if task["task_id"] == task_id)
    task["instruction"] = task["instruction"].replace(literal, "[removed]")
    with pytest.raises(LiveTaskInterfaceError, match="not visible"):
        validate_payload(payload)
