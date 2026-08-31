from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from harness.config import ExperimentConfig
from harness.iterative_agent_loop import DeterministicIterativeCanaryActor
from harness.iterative_live_runner import run_iterative_live
from scripts.validate_orchvar_iterative_live_experiment import DEFAULT_EXPERIMENT
from scripts.validate_orchvar_live_smoke_experiment import IMAGE_ID


class _MockIterativeActor:
    identity = "mock-iterative-live-v1"
    contract = {"schema_version": 1, "identity": identity, "backend": "mock"}

    def __init__(self) -> None:
        self.delegate = DeterministicIterativeCanaryActor()
        self.receipts: list[dict[str, Any]] = []

    async def decide(self, task, **kwargs):
        action = await self.delegate.decide(task, **kwargs)
        self.receipts.append(
            {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "latency_ms": 1.0,
                "action_parse_status": "valid",
                "action_mode": action.mode,
            }
        )
        return action

    def pop_receipts(self) -> list[dict[str, Any]]:
        receipts = self.receipts
        self.receipts = []
        return receipts


def test_iterative_live_runner_materializes_conditioned_safety_trace(
    tmp_path: Path, monkeypatch
) -> None:
    actor = _MockIterativeActor()
    monkeypatch.setattr(
        "harness.iterative_live_runner.load_transformers_iterative_actor",
        lambda _config: actor,
    )
    monkeypatch.setenv("COTCODEC_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("COTCODEC_IMAGE_ID", IMAGE_ID)
    monkeypatch.setenv("COTCODEC_SOURCE_CAPSULE_ROOT", "c" * 64)
    monkeypatch.setenv("SLURM_JOB_ID", "125")
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0")
    result = asyncio.run(
        run_iterative_live(ExperimentConfig.from_yaml(DEFAULT_EXPERIMENT))
    )

    assert result["status"] == "COMPLETE"
    assert result["summary"]["success_rate"] == 1.0
    assert result["summary"]["total_model_decisions"] == 15
    assert result["summary"]["total_tool_calls"] == 9
    assert result["summary"]["total_safety_failures"] == 0
    trace = tmp_path / result["trace_artifact"]["path"]
    rows = [json.loads(line) for line in trace.read_text().splitlines()]
    safety = next(row for row in rows if row["task_id"] == "canary-safety-01")
    assert safety["observations"][0]["result"]["found"] is True
    assert "refuse" in safety["task_result"]["final_response"].casefold()
