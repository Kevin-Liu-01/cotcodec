from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from harness.agent_loop import AgentLoopError
from harness.config import ExperimentConfig
from harness.two_stage_agent_loop import (
    DeterministicTwoStageCanaryActor,
    ResearchMessages,
)
from harness.two_stage_live_runner import run_two_stage_live
from scripts.validate_orchvar_live_smoke_experiment import IMAGE_ID
from scripts.validate_orchvar_two_stage_live_experiment import DEFAULT_EXPERIMENT


class _MockTwoStageActor:
    identity = "mock-two-stage-live-v1"
    contract = {"schema_version": 1, "identity": identity, "backend": "mock"}

    def __init__(
        self,
        *,
        fail_task_id: str | None = None,
        prompt_tokens: int = 10,
    ) -> None:
        self.delegate = DeterministicTwoStageCanaryActor()
        self.fail_task_id = fail_task_id
        self.prompt_tokens = prompt_tokens
        self.receipts: list[dict[str, Any]] = []

    def _receipt(self, stage: str, decision_index: int, compliance: str) -> None:
        self.receipts.append(
            {
                "stage": stage,
                "decision_index": decision_index,
                "prompt_tokens": self.prompt_tokens,
                "completion_tokens": 5,
                "latency_ms": 1.0,
                "compliance": compliance,
            }
        )

    async def generate_messages(self, task, **kwargs):
        decision_index = len(kwargs["observations"])
        if task.task_id == self.fail_task_id:
            self._receipt("planner_message", decision_index, "invalid_empty")
            self.fail_task_id = None
            raise AgentLoopError(
                "planner_message_noncompliance", "mock planner was empty"
            )
        messages = await self.delegate.generate_messages(task, **kwargs)
        if decision_index == 0 and messages.memory_update is None:
            messages = ResearchMessages(
                planner_note=messages.planner_note,
                memory_update="Preserve the exact task constraints and identifiers.",
            )
        self._receipt("planner_message", decision_index, "valid")
        if messages.memory_update is not None:
            self._receipt("memory_message", decision_index, "valid")
        return messages

    async def decide_action(self, task, **kwargs):
        decision_index = len(kwargs["observations"])
        action = await self.delegate.decide_action(task, **kwargs)
        self._receipt("action", decision_index, "valid")
        return action

    def pop_receipts(self) -> list[dict[str, Any]]:
        receipts = self.receipts
        self.receipts = []
        return receipts


def _set_runtime(monkeypatch, tmp_path: Path, job_id: str) -> None:
    monkeypatch.setenv("COTCODEC_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("COTCODEC_IMAGE_ID", IMAGE_ID)
    monkeypatch.setenv("COTCODEC_SOURCE_CAPSULE_ROOT", "d" * 64)
    monkeypatch.setenv("SLURM_JOB_ID", job_id)
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0")


def test_two_stage_live_runner_materializes_all_stages(
    tmp_path: Path, monkeypatch
) -> None:
    actor = _MockTwoStageActor()
    monkeypatch.setattr(
        "harness.two_stage_live_runner.load_transformers_two_stage_actor",
        lambda _config: actor,
    )
    _set_runtime(monkeypatch, tmp_path, "341")
    result = asyncio.run(
        run_two_stage_live(ExperimentConfig.from_yaml(DEFAULT_EXPERIMENT))
    )

    assert result["status"] == "COMPLETE"
    assert result["summary"]["success_rate"] == 1.0
    assert result["summary"]["total_planner_stage_calls"] == 15
    assert result["summary"]["total_memory_stage_calls"] == 6
    assert result["summary"]["total_action_stage_calls"] == 15
    assert result["summary"]["total_external_model_calls"] == 36
    assert result["summary"]["total_tool_calls"] == 9
    assert result["summary"]["message_compliance_failures"] == 0
    trace = tmp_path / result["trace_artifact"]["path"]
    rows = [json.loads(line) for line in trace.read_text().splitlines()]
    safety = next(row for row in rows if row["task_id"] == "canary-safety-01")
    assert safety["observations"][0]["result"]["found"] is True
    assert "refuse" in safety["task_result"]["final_response"].casefold()
    assert safety["stage_receipts"][0]["stage"] == "research_message"


def test_two_stage_live_runner_records_protocol_failure_and_continues(
    tmp_path: Path, monkeypatch
) -> None:
    actor = _MockTwoStageActor(fail_task_id="canary-reasoning-depth-01")
    monkeypatch.setattr(
        "harness.two_stage_live_runner.load_transformers_two_stage_actor",
        lambda _config: actor,
    )
    _set_runtime(monkeypatch, tmp_path, "342")
    result = asyncio.run(
        run_two_stage_live(ExperimentConfig.from_yaml(DEFAULT_EXPERIMENT))
    )

    assert result["completed_cells"] == 6
    assert result["summary"]["protocol_failures"] == 1
    assert result["summary"]["message_compliance_failures"] == 1
    trace = tmp_path / result["trace_artifact"]["path"]
    rows = [json.loads(line) for line in trace.read_text().splitlines()]
    failed = rows[0]
    assert failed["protocol_failure"]["code"] == "planner_message_noncompliance"
    assert failed["outcome"]["action_stage_calls"] == 0
    assert failed["outcome"]["local_tool_calls"] == 0
    assert all(row["outcome"]["success"] for row in rows[1:])


def test_two_stage_live_runner_fails_before_append_when_budget_is_exceeded(
    tmp_path: Path, monkeypatch
) -> None:
    actor = _MockTwoStageActor(prompt_tokens=40_001)
    monkeypatch.setattr(
        "harness.two_stage_live_runner.load_transformers_two_stage_actor",
        lambda _config: actor,
    )
    _set_runtime(monkeypatch, tmp_path, "343")
    with pytest.raises(RuntimeError, match="prompt_tokens"):
        asyncio.run(
            run_two_stage_live(ExperimentConfig.from_yaml(DEFAULT_EXPERIMENT))
        )
    checkpoint = json.loads(
        (
            tmp_path
            / "run-state/orchvar-qwen35-two-stage-live-v1/checkpoint.json"
        ).read_text()
    )
    assert checkpoint["completed_cells"] == 0
