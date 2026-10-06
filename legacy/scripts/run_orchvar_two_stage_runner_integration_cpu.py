#!/usr/bin/env python3
"""Exercise the complete two-stage runner with receipted tool errors on CPU."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.agent_loop import ToolCall  # noqa: E402
from harness.config import ExperimentConfig  # noqa: E402
from harness.run_state import canonical_json  # noqa: E402
from harness.two_stage_agent_loop import (  # noqa: E402
    DeterministicTwoStageCanaryActor,
    ResearchMessages,
)
from harness.two_stage_live_runner import run_two_stage_live  # noqa: E402
from scripts.validate_orchvar_two_stage_runner_integration_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    validate_experiment,
)

RUN_ID = "orchvar-two-stage-runner-tool-errors-cpu-v1"
STATUS = "ORCHVAR_TWO_STAGE_RUNNER_TOOL_ERROR_CPU_ADMISSION_PASS"
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data/results/orchvar-two-stage-runner/2026-08-26-cpu-admission-v1"
)
BOUND_FILES = [
    "experiments/orchvar_two_stage_runner_integration_cpu.yaml",
    "harness/agent_loop.py",
    "harness/benchmarks/orchvar_canary_live_v2.py",
    "harness/benchmarks/specs/orchvar_canary_live_v2_tasks.yaml",
    "harness/conditions/base.py",
    "harness/conditions/english.py",
    "harness/live_canary.py",
    "harness/receipted_tool_runtime.py",
    "harness/run_state.py",
    "harness/two_stage_agent_loop.py",
    "harness/two_stage_live_runner.py",
    "research/evidence/harness/"
    "orchvar-qwen35-two-stage-live-partial-negative-job341.json",
    "research/evidence/harness/orchvar-tool-error-transport-cpu-admission-v1.json",
    "scripts/run_orchvar_two_stage_runner_integration_cpu.py",
    "scripts/validate_orchvar_two_stage_runner_integration_experiment.py",
]
RUNTIME_CONTEXT = {
    "execution_environment": "cpu",
    "runner_doctor": True,
    "external_model_calls": 0,
    "source_binding": "exact-source-evidence-seal",
}


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class RunnerDoctorActor:
    """Deterministic stage fixture with one injected repeated mutation."""

    identity = "deterministic-two-stage-duplicate-injection-fixture-v1"
    contract = {
        "schema_version": 1,
        "identity": identity,
        "backend": "deterministic-cpu-fixture",
        "external_model_calls": 0,
        "duplicate_task_id": "canary-verbosity-sensitive-01",
        "duplicate_tool": "create_handoff_note",
        "error_observation_required_before_final": True,
    }

    def __init__(
        self,
        *,
        prompt_tokens: int = 10,
        signal_after_context_final: bool = False,
    ) -> None:
        self.delegate = DeterministicTwoStageCanaryActor()
        self.prompt_tokens = prompt_tokens
        self.signal_after_context_final = signal_after_context_final
        self.receipts: list[dict[str, Any]] = []

    def _receipt(
        self,
        *,
        stage: str,
        task_id: str,
        decision_index: int,
        observed_tool_error: bool = False,
    ) -> None:
        self.receipts.append(
            {
                "backend": "deterministic-cpu-fixture",
                "stage": stage,
                "task_id": task_id,
                "decision_index": decision_index,
                "prompt_tokens": self.prompt_tokens,
                "completion_tokens": 5,
                "latency_ms": 1.0,
                "compliance": "valid",
                "observed_tool_error": observed_tool_error,
            }
        )

    async def generate_messages(self, task, **kwargs):
        decision_index = len(kwargs["observations"])
        messages = await self.delegate.generate_messages(task, **kwargs)
        if decision_index == 0 and messages.memory_update is None:
            messages = ResearchMessages(
                planner_note=messages.planner_note,
                memory_update="Preserve every exact task constraint and identifier.",
            )
        self._receipt(
            stage="planner_message",
            task_id=task.task_id,
            decision_index=decision_index,
        )
        if messages.memory_update is not None:
            self._receipt(
                stage="memory_message",
                task_id=task.task_id,
                decision_index=decision_index,
            )
        return messages

    async def decide_action(self, task, **kwargs):
        observations = kwargs["observations"]
        decision_index = len(observations)
        observed_error = False
        if task.task_id == "canary-verbosity-sensitive-01" and decision_index == 1:
            action = await self.delegate.decide_action(
                task, **{**kwargs, "observations": ()}
            )
        else:
            if task.task_id == "canary-verbosity-sensitive-01" and decision_index == 2:
                error = observations[-1].result.get("error", {})
                if (
                    observations[-1].result.get("ok") is not False
                    or error.get("code") != "sqlite_constraint_violation"
                    or error.get("retryable") is not False
                ):
                    raise RuntimeError("runner doctor did not receive the tool error")
                observed_error = True
            action = await self.delegate.decide_action(task, **kwargs)
        self._receipt(
            stage="action",
            task_id=task.task_id,
            decision_index=decision_index,
            observed_tool_error=observed_error,
        )
        if (
            self.signal_after_context_final
            and task.task_id == "canary-context-recall-01"
            and action.mode == "final"
        ):
            self.signal_after_context_final = False
            signal.raise_signal(signal.SIGUSR1)
        return action

    def pop_receipts(self) -> list[dict[str, Any]]:
        receipts = self.receipts
        self.receipts = []
        return receipts


class UnexpectedToolRuntime:
    """Falsifier runtime whose non-admitted exception must abort the cell."""

    identity = "unexpected-tool-runtime-fixture-v1"

    async def execute(self, call: ToolCall) -> dict[str, Any]:
        del call
        raise RuntimeError("unexpected runner tool failure")

    def close_and_receipt(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "identity": self.identity,
            "attempt_count": 0,
        }


def _config() -> ExperimentConfig:
    validate_experiment()
    return ExperimentConfig.from_yaml(DEFAULT_EXPERIMENT)


async def _run_lane(
    root: Path, *, resume: bool, signal_after_context_final: bool
) -> dict[str, Any]:
    os.environ["COTCODEC_OUTPUT_DIR"] = str(root)
    if resume:
        os.environ["COTCODEC_RESUME"] = "1"
    else:
        os.environ.pop("COTCODEC_RESUME", None)
    return await run_two_stage_live(
        _config(),
        runtime_context_override=RUNTIME_CONTEXT,
        actor_override=RunnerDoctorActor(
            signal_after_context_final=signal_after_context_final
        ),
    )


async def _run_unexpected(root: Path) -> dict[str, Any]:
    os.environ["COTCODEC_OUTPUT_DIR"] = str(root)
    os.environ.pop("COTCODEC_RESUME", None)
    try:
        await run_two_stage_live(
            _config(),
            runtime_context_override=RUNTIME_CONTEXT,
            actor_override=RunnerDoctorActor(),
            tool_runtime_factory_override=UnexpectedToolRuntime,
        )
    except RuntimeError as exc:
        if str(exc) != "unexpected runner tool failure":
            raise
        error = {"type": type(exc).__name__, "detail": str(exc)}
    else:
        raise RuntimeError("unexpected runner exception was swallowed")
    checkpoint = json.loads(
        (root / f"run-state/{RUN_ID}/checkpoint.json").read_text()
    )
    result = {"error": error, "checkpoint": checkpoint}
    (root / "falsifier.json").write_text(canonical_json(result) + "\n")
    return result


async def _run_budget(root: Path) -> dict[str, Any]:
    os.environ["COTCODEC_OUTPUT_DIR"] = str(root)
    os.environ.pop("COTCODEC_RESUME", None)
    try:
        await run_two_stage_live(
            _config(),
            runtime_context_override=RUNTIME_CONTEXT,
            actor_override=RunnerDoctorActor(prompt_tokens=40_001),
        )
    except RuntimeError as exc:
        if "prompt_tokens" not in str(exc):
            raise
        error = {"type": type(exc).__name__, "detail": str(exc)}
    else:
        raise RuntimeError("runner budget exhaustion was swallowed")
    checkpoint = json.loads(
        (root / f"run-state/{RUN_ID}/checkpoint.json").read_text()
    )
    result = {"error": error, "checkpoint": checkpoint}
    (root / "falsifier.json").write_text(canonical_json(result) + "\n")
    return result


def _child(root: Path, mode: str) -> int:
    if mode == "uninterrupted":
        result = asyncio.run(
            _run_lane(root, resume=False, signal_after_context_final=False)
        )
        return 0 if result.get("status") == "COMPLETE" else 1
    if mode == "interrupt":
        result = asyncio.run(
            _run_lane(root, resume=False, signal_after_context_final=True)
        )
        return 75 if result.get("status") == "INTERRUPTED_CHECKPOINTED" else 1
    if mode == "resume":
        result = asyncio.run(
            _run_lane(root, resume=True, signal_after_context_final=False)
        )
        return 0 if result.get("status") == "COMPLETE" else 1
    if mode == "unexpected":
        asyncio.run(_run_unexpected(root))
        return 0
    if mode == "budget":
        asyncio.run(_run_budget(root))
        return 0
    raise ValueError(f"unknown mode: {mode}")


def _invoke(root: Path, mode: str) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(PROJECT_ROOT)
    return subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "_child", str(root), mode],
        cwd=PROJECT_ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def run_proof(output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    if output.exists():
        raise ValueError("runner integration output already exists")
    output.mkdir(parents=True)
    uninterrupted = output / "uninterrupted"
    resumed = output / "interrupted-resumed"
    unexpected = output / "unexpected-exception"
    budget = output / "budget-exhaustion"
    phases = {
        "uninterrupted": _invoke(uninterrupted, "uninterrupted"),
        "interrupt": _invoke(resumed, "interrupt"),
        "resume": _invoke(resumed, "resume"),
        "unexpected": _invoke(unexpected, "unexpected"),
        "budget": _invoke(budget, "budget"),
    }
    expected_codes = {
        "uninterrupted": 0,
        "interrupt": 75,
        "resume": 0,
        "unexpected": 0,
        "budget": 0,
    }
    for name, expected in expected_codes.items():
        completed = phases[name]
        if completed.returncode != expected:
            raise RuntimeError(f"{name} failed: {completed.returncode}: {completed.stderr}")
    summary_path = f"results/{RUN_ID}_summary.json"
    trace_path = (
        "traces/orchvar_canary/english_only/"
        f"{RUN_ID}__default__deterministic-two-stage-runner-fixture.jsonl"
    )
    report_raw = (uninterrupted / summary_path).read_bytes()
    resumed_report = (resumed / summary_path).read_bytes()
    trace_raw = (uninterrupted / trace_path).read_bytes()
    resumed_trace = (resumed / trace_path).read_bytes()
    journal_raw = (uninterrupted / f"run-state/{RUN_ID}/journal.jsonl").read_bytes()
    resumed_journal = (resumed / f"run-state/{RUN_ID}/journal.jsonl").read_bytes()
    if (
        report_raw != resumed_report
        or trace_raw != resumed_trace
        or journal_raw != resumed_journal
    ):
        raise RuntimeError("runner integration resume differs from uninterrupted")
    report = json.loads(report_raw)
    traces = [json.loads(line) for line in trace_raw.decode().splitlines()]
    verbosity = next(
        trace for trace in traces if trace["task_id"] == "canary-verbosity-sensitive-01"
    )
    safety = next(trace for trace in traces if trace["task_id"] == "canary-safety-01")
    ack = json.loads(
        (resumed / f"run-state/{RUN_ID}/checkpoint-ack.json").read_text()
    )
    unexpected_result = json.loads((unexpected / "falsifier.json").read_text())
    budget_result = json.loads((budget / "falsifier.json").read_text())
    aggregate = report["summary"]
    observed_error = any(
        receipt.get("observed_tool_error") is True
        for receipt in verbosity["backend_stage_receipts"]
        if receipt.get("stage") == "action"
    )
    if (
        report.get("claim_status")
        != "NON_SCIENTIFIC_TWO_STAGE_RUNNER_CPU_DOCTOR"
        or report.get("completed_cells") != 6
        or aggregate.get("success_rate") != 5 / 6
        or aggregate.get("protocol_failures") != 0
        or aggregate.get("total_safety_failures") != 0
        or aggregate.get("total_external_model_calls") != 38
        or aggregate.get("total_tool_calls") != 10
        or aggregate.get("total_tool_successes") != 9
        or aggregate.get("total_tool_errors") != 1
        or verbosity.get("outcome", {}).get("success") is not False
        or verbosity.get("outcome", {}).get("local_tool_errors") != 1
        or observed_error is not True
        or safety.get("outcome", {}).get("success") is not True
        or safety.get("observations", [])[0].get("result", {}).get("found") is not True
        or "refuse" not in safety.get("task_result", {}).get("final_response", "").casefold()
        or ack.get("signal") != "SIGUSR1"
        or ack.get("completed_cells") != 2
        or unexpected_result.get("checkpoint", {}).get("completed_cells") != 0
        or unexpected_result.get("error", {}).get("detail")
        != "unexpected runner tool failure"
        or budget_result.get("checkpoint", {}).get("completed_cells") != 0
        or "prompt_tokens" not in budget_result.get("error", {}).get("detail", "")
    ):
        raise RuntimeError("runner integration projection failed")
    manifest = {
        "schema_version": 1,
        "status": STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "live_model_result": False,
        "h100_admission": False,
        "external_model_calls": 0,
        "simulated_backend_stage_receipts": 38,
        "completed_cells": 6,
        "benchmark_successes": 5,
        "benchmark_failures": 1,
        "protocol_failures": 0,
        "safety_failures": 0,
        "tool_attempts": 10,
        "tool_successes": 9,
        "tool_errors": 1,
        "duplicate_error_observed_before_final": True,
        "unexpected_runtime_exception_aborts_before_append": True,
        "budget_exhaustion_aborts_before_append": True,
        "actual_usr1_acknowledged_cells": 2,
        "byte_identical_report": True,
        "byte_identical_trace": True,
        "byte_identical_journal": True,
        "report_sha256": _sha(report_raw),
        "trace_sha256": _sha(trace_raw),
        "journal_sha256": _sha(journal_raw),
        "contract_sha256": report["contract_sha256"],
        "plan_sha256": report["plan_sha256"],
        "journal_root_sha256": report["journal_root_sha256"],
        "phase_receipts": {
            name: {
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
            for name, completed in phases.items()
        },
        "bound_source_sha256": {
            path: _sha((PROJECT_ROOT / path).read_bytes()) for path in BOUND_FILES
        },
        "claim_boundary": _config().extra["claim_boundary"],
        "next_gate": (
            "Keep OrchVar H100 closed. Return to the first untouched queue item or "
            "preregister a genuinely new model/benchmark gate; never resume job 341."
        ),
    }
    (output / "manifest.json").write_text(
        canonical_json(manifest) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    if len(sys.argv) >= 2 and sys.argv[1] == "_child":
        return _child(Path(sys.argv[2]).resolve(), sys.argv[3])
    output = Path(sys.argv[1]).resolve() if len(sys.argv) == 2 else DEFAULT_OUTPUT
    manifest = run_proof(output)
    print(
        canonical_json(
            {
                "status": manifest["status"],
                "report_sha256": manifest["report_sha256"],
                "journal_root_sha256": manifest["journal_root_sha256"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
