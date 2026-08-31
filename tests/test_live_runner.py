from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from harness.agent_loop import ActorPlan, DeterministicCanaryActor
from harness.config import ConditionID, ExperimentConfig
from harness.live_runner import run_live_experiment
from scripts.validate_orchvar_live_smoke_experiment import (
    DEFAULT_EXPERIMENT,
    IMAGE_ID,
)
from scripts.validate_orchvar_live_v2_smoke_experiment import (
    DEFAULT_EXPERIMENT as V2_EXPERIMENT,
)


class _MockLiveActor:
    identity = "mock-live-actor-v1"
    contract = {"schema_version": 1, "identity": identity, "backend": "mock"}

    def __init__(self) -> None:
        self.delegate = DeterministicCanaryActor()
        self.receipt: dict[str, Any] | None = None

    async def plan(
        self,
        task,
        *,
        system_prompt: str,
        condition: ConditionID,
        seed: int,
    ) -> ActorPlan:
        plan = await self.delegate.plan(
            task,
            system_prompt=system_prompt,
            condition=condition,
            seed=seed,
        )
        self.receipt = {
            "prompt_tokens": 100,
            "completion_tokens": 40,
            "latency_ms": 1.5,
            "plan_parse_status": "valid",
            "raw_output": "mock",
        }
        return plan

    def pop_receipt(self) -> dict[str, Any]:
        assert self.receipt is not None
        receipt = self.receipt
        self.receipt = None
        return receipt


def test_live_runner_materializes_six_receipted_cells(
    tmp_path: Path, monkeypatch
) -> None:
    actor = _MockLiveActor()
    monkeypatch.setattr(
        "harness.live_runner.load_transformers_canary_actor", lambda _config: actor
    )
    monkeypatch.setenv("COTCODEC_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("COTCODEC_IMAGE_ID", IMAGE_ID)
    monkeypatch.setenv("COTCODEC_SOURCE_CAPSULE_ROOT", "a" * 64)
    monkeypatch.setenv("SLURM_JOB_ID", "123")
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0")
    config = ExperimentConfig.from_yaml(DEFAULT_EXPERIMENT)
    result = asyncio.run(run_live_experiment(config))

    assert result["status"] == "COMPLETE"
    assert result["claim_status"] == "NON_SCIENTIFIC_LIVE_SMOKE"
    assert result["completed_cells"] == 6
    assert result["summary"]["success_rate"] == 1.0
    trace_path = tmp_path / result["trace_artifact"]["path"]
    rows = [json.loads(line) for line in trace_path.read_text().splitlines()]
    assert len(rows) == 6
    assert sum(row["outcome"]["external_model_calls"] for row in rows) == 6
    assert sum(row["outcome"]["local_tool_calls"] for row in rows) == 9
    assert all(row["tool_runtime_receipt"]["identity"] for row in rows)


def test_live_runner_executes_self_contained_v2_tasks(
    tmp_path: Path, monkeypatch
) -> None:
    actor = _MockLiveActor()
    monkeypatch.setattr(
        "harness.live_runner.load_transformers_canary_actor", lambda _config: actor
    )
    monkeypatch.setenv("COTCODEC_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("COTCODEC_IMAGE_ID", IMAGE_ID)
    monkeypatch.setenv("COTCODEC_SOURCE_CAPSULE_ROOT", "b" * 64)
    monkeypatch.setenv("SLURM_JOB_ID", "124")
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0")
    result = asyncio.run(run_live_experiment(ExperimentConfig.from_yaml(V2_EXPERIMENT)))

    assert result["status"] == "COMPLETE"
    assert result["completed_cells"] == 6
    assert result["summary"]["success_rate"] == 1.0
    assert result["runtime_context"]["source_capsule_root_sha256"] == "b" * 64
