from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from harness.memory_trials.gaama_actor import (
    ARM_IDS,
    PANEL_SIZE,
    answer_scores,
    canonical_bytes,
    compile_panel,
    load_frozen_input,
    sha256_bytes,
)
from harness.memory_trials.models import CompletionResult, JsonCompletionMemoryActor
from scripts.run_gaama_actor_screen import run_screen
from scripts.validate_gaama_actor_experiment import DEFAULT_EXPERIMENT

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = PROJECT_ROOT / "research/evidence/memory/gaama-natural-graph-v5.json"
EVIDENCE_SHA256 = "011a21918946e19255c1118de41ec99131e1cb64c32b50bc68af8da58d84dc79"
MODEL_REVISION = "851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a"
MODEL_ROOT = "3b8a075149bffe4dea784db5b4b37bc0896688cba0b3de7d8d0f6e8ae6157b9e"


def _fake_actor(answers: dict[str, str], calls: list[str]) -> JsonCompletionMemoryActor:
    identity = f"hf:qwen3.5-4b@{MODEL_REVISION}#{MODEL_ROOT}"

    def complete(prompt: str) -> CompletionResult:
        calls.append(prompt)
        matches = [
            answer
            for question, answer in answers.items()
            if f"Question: {question}\nAnswer:" in prompt
        ]
        if len(matches) != 1:
            raise AssertionError("fake actor could not identify one frozen question")
        text = matches[0]
        return CompletionResult(
            text=text,
            receipt={
                "backend": "fake-transformers",
                "model_id": "qwen3.5-4b",
                "revision": MODEL_REVISION,
                "artifact_root_sha256": MODEL_ROOT,
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(text.split()),
                "do_sample": False,
                "deterministic_algorithms": True,
                "attention_implementation": "eager",
                "prompt_token_ids_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                "completion_token_ids_sha256": hashlib.sha256(text.encode()).hexdigest(),
            },
        )

    return JsonCompletionMemoryActor(
        identity=identity,
        complete=complete,
        contract={
            "schema_version": 1,
            "identity": identity,
            "backend": "fake-transformers",
            "model_id": "qwen3.5-4b",
            "revision": MODEL_REVISION,
            "artifact_root_sha256": MODEL_ROOT,
            "max_new_tokens": 64,
            "dtype": "bfloat16",
            "use_chat_template": True,
            "do_sample": False,
            "deterministic_algorithms": True,
            "attention_implementation": "eager",
        },
    )


def test_frozen_gaama_panel_is_balanced_and_deterministic() -> None:
    frozen = load_frozen_input(EVIDENCE, expected_sha256=EVIDENCE_SHA256)
    first = compile_panel(frozen)
    second = compile_panel(frozen)
    assert first == second
    assert first["panel_size"] == PANEL_SIZE
    assert first["category_counts"] == {"1": 50, "2": 50, "3": 50, "4": 50}
    assert first["arms"] == list(ARM_IDS)
    assert len(first["items"]) == 200
    assert all(len(item["rankings"][arm]) == 10 for item in first["items"] for arm in ARM_IDS)


def test_answer_scores_use_normalized_exact_and_token_f1() -> None:
    assert answer_scores("The 7th of May!", "7th of May") == (1.0, 1.0)
    exact, token_f1 = answer_scores("May 7", "May 7 2023")
    assert exact == 0.0
    assert token_f1 == pytest.approx(0.8)


def test_completion_actor_exposes_same_registered_raw_transport() -> None:
    actor = JsonCompletionMemoryActor(
        identity="test-actor",
        complete=lambda prompt: CompletionResult(text=prompt, receipt={"calls": 1}),
        contract={"identity": "test-actor"},
    )
    result = actor.complete_text("hello")
    assert result.text == "hello"
    assert result.receipt == {"calls": 1}


def test_gaama_actor_screen_checkpoints_resumes_and_seals(tmp_path: Path) -> None:
    frozen = load_frozen_input(EVIDENCE, expected_sha256=EVIDENCE_SHA256)
    panel = compile_panel(frozen)
    answers = {item["question"]: item["answer"] for item in panel["items"]}
    calls: list[str] = []
    actor = _fake_actor(answers, calls)
    output = tmp_path / "run"

    partial = run_screen(
        config_path=DEFAULT_EXPERIMENT,
        evidence_path=EVIDENCE,
        expected_evidence_sha256=EVIDENCE_SHA256,
        output_dir=output,
        actor=actor,
        stop_requested=lambda: len(calls) >= 2,
    )
    assert partial["status"] == "CHECKPOINTED"
    checkpoint = json.loads((output / "checkpoint.json").read_text())
    assert checkpoint["completed_cases"] == 1
    assert (output / "predictions.jsonl").read_text().count("\n") == 1

    report = run_screen(
        config_path=DEFAULT_EXPERIMENT,
        evidence_path=EVIDENCE,
        expected_evidence_sha256=EVIDENCE_SHA256,
        output_dir=output,
        actor=actor,
    )
    assert report["status"] == "GAAMA_H100_ACTOR_KILLED"
    assert report["gates"]["actor_a_a_exact"] is True
    assert report["gates"]["row_roster_exact"] is True
    assert report["completed_cases"] == PANEL_SIZE * len(ARM_IDS)
    assert (output / "predictions.jsonl").read_text().count("\n") == 1000

    resumed = run_screen(
        config_path=DEFAULT_EXPERIMENT,
        evidence_path=EVIDENCE,
        expected_evidence_sha256=EVIDENCE_SHA256,
        output_dir=output,
        actor=actor,
    )
    assert resumed == report

    forged_report = dict(report)
    forged_report["primary_comparison"] = {
        **forged_report["primary_comparison"],
        "true_minus_flat_cluster_mean_f1": 1.0,
    }
    (output / "report.json").write_bytes(canonical_bytes(forged_report))
    manifest = json.loads((output / "manifest.json").read_text())
    report_bytes = (output / "report.json").read_bytes()
    manifest["files"]["report.json"] = {
        "bytes": len(report_bytes),
        "sha256": sha256_bytes(report_bytes),
    }
    manifest.pop("root_sha256")
    manifest["root_sha256"] = sha256_bytes(canonical_bytes(manifest))
    (output / "manifest.json").write_bytes(canonical_bytes(manifest))
    with pytest.raises(ValueError, match="analysis does not reproduce"):
        run_screen(
            config_path=DEFAULT_EXPERIMENT,
            evidence_path=EVIDENCE,
            expected_evidence_sha256=EVIDENCE_SHA256,
            output_dir=output,
            actor=actor,
        )


def test_gaama_evidence_digest_tamper_fails_before_parsing(tmp_path: Path) -> None:
    copied = tmp_path / "evidence.json"
    copied.write_bytes(EVIDENCE.read_bytes() + b" ")
    with pytest.raises(ValueError, match="SHA-256 drifted"):
        load_frozen_input(copied, expected_sha256=EVIDENCE_SHA256)
