from __future__ import annotations

import json
from pathlib import Path

from harness.memory_trials import (
    CompletionResult,
    GeneratedMemoryTaskSource,
    ReferenceMemorySystem,
)
from scripts.freeze_memory_system_outputs import compile_bundle, write_validated_bundle
from scripts.reanalyze_memory_frontier_screen import reanalyze_frontier_screen
from scripts.run_memory_frontier_screen import run_frontier_screen


class FakeFrontierBackend:
    identity = "openai:gpt-5.6-sol"

    def preflight(self):
        return {
            "provider": "openai",
            "endpoint": "/models",
            "requested_model": "gpt-5.6-sol",
            "available": True,
            "listed_model_count": 1,
            "model_ids_sha256": "1" * 64,
        }

    def complete(self, _prompt: str) -> CompletionResult:
        return CompletionResult(
            text='{"mode":"answer","answer":"UNKNOWN"}',
            receipt={
                "provider": "openai",
                "requested_model": "gpt-5.6-sol",
                "returned_model": "gpt-5.6-sol",
                "response_id": "fake-response",
            },
        )


def test_frontier_screen_is_single_arm_resumable_and_non_scientific(
    tmp_path: Path,
) -> None:
    config = Path("experiments/memory/stage1-model-transport.yaml")
    output = tmp_path / "frontier"
    backend = FakeFrontierBackend()
    checkpointed = run_frontier_screen(
        config,
        "gpt-5.6-sol",
        output,
        episodes_override=8,
        stop_after=3,
        backend=backend,
    )
    assert checkpointed["status"] == "CHECKPOINTED"
    assert checkpointed["completed_trials"] == 3
    report = run_frontier_screen(
        config,
        "gpt-5.6-sol",
        output,
        episodes_override=8,
        resume=True,
        backend=backend,
    )
    assert report["scientific_result"] is False
    assert report["replay_mode"] == "single_arm"
    manifest = json.loads(
        (output / "collection" / "bundle" / "manifest.json").read_text()
    )
    assert manifest["paired_audits"] == 0
    assert manifest["plan"]["replay_mode"] == "single_arm"
    assert (output / "provider-preflight.json").is_file()
    assert (output / "aa-drift.json").is_file()


def test_frontier_safety_screen_reports_matched_failure_increase(tmp_path: Path) -> None:
    report = run_frontier_screen(
        Path("experiments/memory/stage1-model-transport.yaml"),
        "gpt-5.6-sol",
        tmp_path / "safety",
        suite="safety",
        episodes_override=8,
        backend=FakeFrontierBackend(),
    )
    assert report["suite"] == "safety"
    assert set(report["metrics"]["safety_cases"]) == {
        "stored_prompt_injection",
        "pii_canary",
        "stale_permission",
        "delayed_activation",
    }
    assert isinstance(
        report["safety_evidence"]["aggregate"]["risk_difference_points"], float
    )
    assert len(report["safety_evidence"]["aggregate"]["newcombe_95_points"]) == 2
    expected_status = (
        "FRONTIER_SAFETY_SCREEN_PASS" if all(report["gates"].values()) else "FAIL"
    )
    assert report["status"] == expected_status


def test_frontier_reanalysis_is_immutable_and_binds_inputs(tmp_path: Path) -> None:
    config = Path("experiments/memory/stage1-model-transport.yaml")
    run_root = tmp_path / "frontier"
    original = run_frontier_screen(
        config,
        "gpt-5.6-sol",
        run_root,
        episodes_override=8,
        backend=FakeFrontierBackend(),
    )
    output_dir = tmp_path / "analysis"
    report = reanalyze_frontier_screen(
        run_root,
        output_dir,
        config_path=config,
    )
    assert report["inputs"]["bundle_manifest_sha256"] == original[
        "bundle_manifest_sha256"
    ]
    assert (output_dir / "manifest.json").is_file()
    try:
        reanalyze_frontier_screen(run_root, output_dir, config_path=config)
    except ValueError as exc:
        assert "refusing to overwrite" in str(exc)
    else:
        raise AssertionError("reanalyzer overwrote a sealed analysis")


def test_frontier_screen_consumes_one_frozen_memory_bundle(tmp_path: Path) -> None:
    source = GeneratedMemoryTaskSource(seed=7, episode_count=8)
    payload = compile_bundle(
        ReferenceMemorySystem(),
        source,
        treatment_modes=("storage_and_service",),
    )
    bundle_path = tmp_path / "frozen-memory.json"
    frozen = write_validated_bundle(
        bundle_path,
        payload,
        source=source,
        treatment_modes=("storage_and_service",),
    )
    report = run_frontier_screen(
        Path("experiments/memory/stage1-model-transport.yaml"),
        "gpt-5.6-sol",
        tmp_path / "frontier-frozen",
        episodes_override=8,
        backend=FakeFrontierBackend(),
        memory_bundle=bundle_path,
    )
    assert report["memory_bundle_sha256"] == frozen.bundle_sha256
    assert report["memory_treatment_mode"] == "storage_and_service"
