from __future__ import annotations

import asyncio
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from harness.config import ExperimentConfig
from harness.runner import run_experiment

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = PROJECT_ROOT / "experiments/degradation_canary_local_01.yaml"


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_deterministic_runner_executes_every_cell_and_emits_complete_traces(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("COTCODEC_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("COTCODEC_RUN_ID", "runner-admission")
    result = asyncio.run(run_experiment(ExperimentConfig.from_yaml(EXPERIMENT)))
    assert result["status"] == "COMPLETE"
    assert result["completed_cells"] == 120
    rates = {summary["condition"]: summary["success_rate"] for summary in result["summaries"]}
    assert rates == {
        "english_only": 1.0,
        "english_only_25word_limit": 25 / 30,
        "english_only_low_effort": 25 / 30,
        "english_only_no_thinking_cache": 20 / 30,
    }

    traces = [
        trace
        for path in sorted((tmp_path / "traces").rglob("*.jsonl"))
        for trace in _read_jsonl(path)
    ]
    assert len(traces) == 120
    assert len({json.dumps(trace["pair_key"], sort_keys=True) for trace in traces}) == 120
    assert all(
        trace["task_result"]["metadata"]["terminal_status"] == "complete"
        for trace in traces
    )
    assert all(trace["benchmark_evaluation"]["details"]["category"] for trace in traces)
    assert all(
        message["language"] == "english"
        for trace in traces
        for message in trace["messages"]
        if message["type"] in {"tool_call", "tool_result", "user_response"}
    )


def test_runner_refuses_unimplemented_live_actor(tmp_path: Path) -> None:
    config = ExperimentConfig.from_yaml(EXPERIMENT)
    config.extra["actor"] = {"type": "openai_live"}
    os.environ["COTCODEC_OUTPUT_DIR"] = str(tmp_path)
    os.environ["COTCODEC_RUN_ID"] = "unsupported-live-actor"
    try:
        with pytest.raises(ValueError, match="unsupported actor contract"):
            asyncio.run(run_experiment(config))
    finally:
        os.environ.pop("COTCODEC_OUTPUT_DIR", None)
        os.environ.pop("COTCODEC_RUN_ID", None)


@pytest.mark.skipif(not hasattr(signal, "SIGUSR1"), reason="USR1 is unavailable")
def test_usr1_resume_matches_uninterrupted_outputs_byte_for_byte(tmp_path: Path) -> None:
    uninterrupted = tmp_path / "uninterrupted"
    resumed = tmp_path / "resumed"
    base_env = {
        **os.environ,
        "COTCODEC_RUN_ID": "usr1-resume-proof",
    }
    subprocess.run(
        [sys.executable, "-m", "harness.runner", str(EXPERIMENT)],
        cwd=PROJECT_ROOT,
        env={**base_env, "COTCODEC_OUTPUT_DIR": str(uninterrupted)},
        check=True,
        capture_output=True,
        text=True,
    )

    interrupted = subprocess.Popen(
        [sys.executable, "-m", "harness.runner", str(EXPERIMENT)],
        cwd=PROJECT_ROOT,
        env={
            **base_env,
            "COTCODEC_OUTPUT_DIR": str(resumed),
            "COTCODEC_CELL_DELAY_MS": "20",
        },
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    checkpoint = resumed / "run-state/usr1-resume-proof/checkpoint.json"
    deadline = time.monotonic() + 10
    completed = 0
    while time.monotonic() < deadline:
        if checkpoint.exists():
            completed = json.loads(checkpoint.read_text(encoding="utf-8"))[
                "completed_cells"
            ]
            if completed >= 2:
                break
        time.sleep(0.01)
    assert completed >= 2
    os.kill(interrupted.pid, signal.SIGUSR1)
    stdout, stderr = interrupted.communicate(timeout=10)
    assert interrupted.returncode == 0, (stdout, stderr)
    assert (resumed / "run-state/usr1-resume-proof/checkpoint-ack.json").is_file()

    subprocess.run(
        [sys.executable, "-m", "harness.runner", str(EXPERIMENT)],
        cwd=PROJECT_ROOT,
        env={
            **base_env,
            "COTCODEC_OUTPUT_DIR": str(resumed),
            "COTCODEC_RESUME": "1",
        },
        check=True,
        capture_output=True,
        text=True,
    )
    left = {
        path.relative_to(uninterrupted): path.read_bytes()
        for path in uninterrupted.rglob("*")
        if path.is_file() and ("traces" in path.parts or "results" in path.parts)
    }
    right = {
        path.relative_to(resumed): path.read_bytes()
        for path in resumed.rglob("*")
        if path.is_file() and ("traces" in path.parts or "results" in path.parts)
    }
    assert right == left
