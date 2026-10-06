from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from harness.causal_memory_trials import (
    ArtifactIntegrityError,
    TrialContractError,
    TrialPlan,
    analyze_trials,
    run_trials,
)
from harness.memory_trials import (
    GeneratedMemoryTaskSource,
    GeneratedSafetyMemoryTaskSource,
    JsonCompletionMemoryActor,
    ReferenceMemorySystem,
    ReplayableMemoryWorld,
    collect_resumable,
)
from scripts.run_memory_trials import ALLOWED_FEATURES, run_study


def _audit_ids(ids: tuple[str, ...]) -> frozenset[str]:
    return frozenset(
        task_id
        for task_id in ids
        if int(hashlib.sha256(task_id.encode()).hexdigest()[:8], 16) % 4 == 0
    )


def _plan(source: GeneratedMemoryTaskSource) -> TrialPlan:
    ids = source.ids()
    return TrialPlan(
        study_id="memory-resume-test",
        trial_ids=ids,
        allowed_features=ALLOWED_FEATURES,
        paired_audit_ids=_audit_ids(ids),
        propensity=0.5,
        assignment_seed=42,
        folds=5,
        minimum_effective_sample_size=20,
        minimum_arm_effective_sample_size=10,
    )


def test_generated_source_covers_four_strata_and_is_deterministic() -> None:
    first = GeneratedMemoryTaskSource(seed=7, episode_count=8)
    second = GeneratedMemoryTaskSource(seed=7, episode_count=8)
    first_tasks = tuple(first.iter_tasks())
    second_tasks = tuple(second.iter_tasks())
    assert first_tasks == second_tasks
    assert {task.stratum.value for task in first_tasks} == {
        "active_core",
        "inactive_archive",
        "temporal_graph",
        "proactive_tool",
    }
    assert all(20 <= len(task.events) <= 40 for task in first_tasks)
    assert all(sum(event.candidate for event in task.events) == 1 for task in first_tasks)


def test_generated_safety_source_is_prefix_stable_and_executable() -> None:
    source = GeneratedSafetyMemoryTaskSource(seed=7, episode_count=8)
    assert set(source.provenance["implemented_safety_cases"]) == set(source.cases)
    primary = source.load("memory-000000")
    permuted = source.load("memory-000000", suffix_variant="permuted")
    candidate = next(event for event in primary.events if event.candidate)
    permuted_candidate = next(event for event in permuted.events if event.candidate)
    assert candidate == permuted_candidate
    assert primary.oracle.safety_case == "stored_prompt_injection"
    world = ReplayableMemoryWorld(source)
    prepared = world.prepare("memory-000000")
    served = world.continue_from(prepared, "serve", "a" * 64)
    held_out = world.continue_from(prepared, "holdout", "a" * 64)
    assert served.safety_failure is True
    assert held_out.safety_failure is False
    assert held_out.success is True


def test_suffix_permutation_regenerates_suffix_through_same_feature_extractor() -> None:
    world = ReplayableMemoryWorld(GeneratedMemoryTaskSource(seed=7, episode_count=1))
    primary = world.prepare("memory-000000")
    permuted = world.prepare_suffix_permutation("memory-000000")
    assert primary.snapshot_sha256 != permuted.snapshot_sha256
    assert primary.prefix_digest == permuted.prefix_digest
    assert primary.features == permuted.features
    primary_task = json.loads(primary.snapshot_json)["task"]
    permuted_task = json.loads(permuted.snapshot_json)["task"]
    assert (
        primary_task["events"][: primary.eligibility_step]
        == permuted_task["events"][: permuted.eligibility_step]
    )
    assert primary_task["events"][-1] != permuted_task["events"][-1]


def test_engine_owns_detailed_replay_receipts_and_candidate_effect() -> None:
    source = GeneratedMemoryTaskSource(seed=7, episode_count=4)
    world = ReplayableMemoryWorld(source)
    prepared = world.prepare("memory-000000")
    replay_key = "1" * 64
    served = world.continue_from(prepared, "serve", replay_key)
    held_out = world.continue_from(prepared, "holdout", replay_key)
    repeated = world.continue_from(prepared, "serve", replay_key)
    assert served == repeated
    assert served.success is True
    assert held_out.success is False
    assert served.exogenous_trace_sha256 == held_out.exogenous_trace_sha256
    assert served.trace_sha256 != held_out.trace_sha256
    assert served.trace_json is not None
    assert served.prompt_json is not None
    assert served.memory_frame_json is not None
    assert served.model_output_json is not None
    assert served.tool_trace_json is not None
    assert served.prompt_sha256 is not None
    assert served.tool_trace_sha256 is not None


def test_json_completion_actor_receives_exact_prompt_and_preserves_raw_output() -> None:
    prompts: list[str] = []

    def complete(prompt: str) -> str:
        prompts.append(prompt)
        return 'prefix {"mode":"answer","answer":"UNKNOWN"} suffix'

    actor = JsonCompletionMemoryActor(
        identity="fake-json-model@immutable",
        complete=complete,
        contract={"identity": "fake-json-model@immutable", "fixture": "exact-prompt-v1"},
    )
    world = ReplayableMemoryWorld(
        GeneratedMemoryTaskSource(seed=7, episode_count=1),
        actor=actor,
    )
    outcome = world.continue_from(world.prepare("memory-000000"), "holdout", "6" * 64)
    assert prompts == [outcome.prompt_json]
    assert outcome.model_output_json == ('prefix {"mode":"answer","answer":"UNKNOWN"} suffix')
    assert outcome.success is False


def test_malformed_json_completion_is_recorded_as_failed_action() -> None:
    actor = JsonCompletionMemoryActor(
        identity="malformed-model@immutable",
        complete=lambda _prompt: "not valid action JSON",
        contract={
            "identity": "malformed-model@immutable",
            "fixture": "malformed-output-v1",
        },
    )
    world = ReplayableMemoryWorld(
        GeneratedMemoryTaskSource(seed=7, episode_count=1),
        actor=actor,
    )
    outcome = world.continue_from(world.prepare("memory-000000"), "serve", "7" * 64)
    assert outcome.model_output_json == "not valid action JSON"
    assert outcome.success is False
    assert outcome.metrics["tool_schema_correct"] == 0.0


def test_native_memory_system_feeds_task_blind_evidence_to_actor() -> None:
    prompts: list[str] = []

    def complete(prompt: str) -> str:
        prompts.append(prompt)
        payload = json.loads(prompt)
        evidence = payload["memory_frame"]["evidence"][0]
        value = json.loads(evidence["text"])["value"]
        return json.dumps(
            {
                "mode": "answer",
                "answer": value,
                "tool_name": None,
                "tool_arguments": {},
                "selected_record_id": evidence["id"],
            }
        )

    source = GeneratedMemoryTaskSource(seed=7, episode_count=2)
    world = ReplayableMemoryWorld(
        source,
        actor=JsonCompletionMemoryActor(
            identity="evidence-reader-v1",
            complete=complete,
            contract={"identity": "evidence-reader-v1", "fixture": "evidence-reader-v1"},
        ),
        memory_system=ReferenceMemorySystem(),
        memory_treatment_mode="storage_and_service",
    )
    prepared = world.prepare("memory-000001")
    served = world.continue_from(prepared, "serve", "8" * 64)
    held_out = world.continue_from(prepared, "holdout", "8" * 64)
    assert served.success is True
    assert held_out.success is False
    assert served.metrics["memory_candidate_served_to_actor"] == 1.0
    assert held_out.metrics["memory_candidate_served_to_actor"] == 0.0
    assert served.metrics["memory_writes"] > 2
    assert served.metrics["injected_memory_tokens"] <= 256
    assert "candidate" not in served.prompt_json
    assert "wrong-" not in served.prompt_json
    assert "distractor" not in served.prompt_json
    trace = json.loads(served.trace_json)
    assert trace["memory_system_run"]["receipt"]["system_id"] == ("reference-memory-system-v2")
    assert all(evidence["source_record_ids"] for evidence in trace["memory_system_run"]["evidence"])
    assert len(prompts) == 2


def test_temporal_graph_requires_two_hop_traversal() -> None:
    source = GeneratedMemoryTaskSource(seed=7, episode_count=4)
    task = source.load("memory-000002")
    assert task.stratum.value == "temporal_graph"
    assert sum(event.key == "reports_to" for event in task.events) == 2
    assert sum(event.key == "located_in" for event in task.events) == 2
    assert all(
        event.value != task.oracle.expected_value
        for event in task.events
        if event.key == "reports_to"
    )
    world = ReplayableMemoryWorld(source)
    prepared = world.prepare(task.task_id)
    served = world.continue_from(prepared, "serve", "4" * 64)
    held_out = world.continue_from(prepared, "holdout", "4" * 64)
    assert served.success is True
    assert held_out.success is False
    assert json.loads(served.memory_frame_json)["residency"] == "graph"


@pytest.mark.parametrize(
    ("task_id", "expected_residency", "expected_reads"),
    [
        ("memory-000000", "active", 0.0),
        ("memory-000001", "archive", 1.0),
        ("memory-000002", "graph", 1.0),
        ("memory-000003", "archive", 1.0),
    ],
)
def test_residency_and_read_budget_are_explicit(
    task_id: str,
    expected_residency: str,
    expected_reads: float,
) -> None:
    world = ReplayableMemoryWorld(GeneratedMemoryTaskSource(seed=7, episode_count=4))
    prepared = world.prepare(task_id)
    outcome = world.continue_from(prepared, "serve", "5" * 64)
    assert json.loads(outcome.memory_frame_json)["residency"] == expected_residency
    assert outcome.metrics["memory_reads"] == expected_reads
    assert outcome.metrics["injected_memory_tokens"] <= 256


def test_world_has_no_cross_session_mutable_memory() -> None:
    source = GeneratedMemoryTaskSource(seed=7, episode_count=2)
    world = ReplayableMemoryWorld(source)
    first = world.prepare("memory-000000")
    second = world.prepare("memory-000001")
    first_before = world.continue_from(first, "serve", "2" * 64)
    world.continue_from(second, "holdout", "3" * 64)
    first_after = world.continue_from(first, "serve", "2" * 64)
    assert first_before == first_after


def test_public_trial_interface_recovers_known_executable_effect(tmp_path: Path) -> None:
    source = GeneratedMemoryTaskSource(seed=7, episode_count=320)
    ids = source.ids()
    plan = TrialPlan(
        study_id="memory-engine-test",
        trial_ids=ids,
        allowed_features=ALLOWED_FEATURES,
        paired_audit_ids=_audit_ids(ids),
        propensity=0.5,
        assignment_seed=42,
        folds=5,
        minimum_effective_sample_size=50,
        minimum_arm_effective_sample_size=20,
    )
    bundle = run_trials(plan, ReplayableMemoryWorld(source), tmp_path / "run")
    report = analyze_trials(bundle)
    assert all(report.gates.values())
    assert report.aipw_oracle_correlation >= 0.8
    assert report.policy_oracle_correlation >= 0.8
    assert report.learned_policy_success == pytest.approx(1.0)
    assert report.learned_policy_success > report.always_serve_success
    assert report.learned_policy_success > report.always_holdout_success


def test_stage0_script_labels_overridden_run_as_smoke(tmp_path: Path) -> None:
    config = Path("experiments/memory/stage0-oracle.yaml")
    manifest = run_study(
        config,
        tmp_path / "study",
        episodes_override=320,
        propensity_override=0.5,
    )
    assert manifest["status"] == "ORACLE_ENGINE_SMOKE"
    assert manifest["scientific_result"] is False
    assert (tmp_path / "study" / "manifest.json").is_file()


def test_single_arm_plan_for_hosted_models_forbids_fake_paired_replay() -> None:
    source = GeneratedMemoryTaskSource(seed=7, episode_count=80)
    plan = _plan(source).model_copy(
        update={"replay_mode": "single_arm", "paired_audit_ids": frozenset()}
    )
    validated = TrialPlan.model_validate(plan.model_dump())
    assert validated.replay_mode == "single_arm"
    with pytest.raises(ValueError, match="cannot execute counterfactual"):
        TrialPlan.model_validate(
            plan.model_copy(update={"paired_audit_ids": frozenset({source.ids()[0]})})
        )


def test_stage0_script_resumes_from_episode_checkpoint(tmp_path: Path) -> None:
    config = Path("experiments/memory/stage0-oracle.yaml")
    output = tmp_path / "study"
    checkpointed = run_study(
        config,
        output,
        episodes_override=120,
        propensity_override=0.5,
        stop_after=11,
    )
    assert checkpointed["status"] == "CHECKPOINTED"
    assert checkpointed["cells"][0]["completed_trials"] == 11
    resumed = run_study(
        config,
        output,
        episodes_override=120,
        propensity_override=0.5,
        resume=True,
    )
    assert resumed["status"] == "ORACLE_ENGINE_SMOKE"


def test_stage0_script_refuses_to_overwrite_artifacts(tmp_path: Path) -> None:
    output = tmp_path / "study"
    output.mkdir()
    (output / "existing.txt").write_text("keep\n")
    with pytest.raises(ValueError, match="refusing to overwrite"):
        run_study(
            Path("experiments/memory/stage0-oracle.yaml"),
            output,
            episodes_override=80,
            propensity_override=0.5,
        )


def test_resumable_collection_matches_uninterrupted_bundle(tmp_path: Path) -> None:
    source = GeneratedMemoryTaskSource(seed=7, episode_count=120)
    plan = _plan(source)
    world = ReplayableMemoryWorld(source)
    interrupted = collect_resumable(
        plan,
        world,
        tmp_path / "interrupted",
        stop_after=37,
    )
    assert interrupted.status == "CHECKPOINTED"
    assert interrupted.completed_trials == 37
    resumed = collect_resumable(
        plan,
        world,
        tmp_path / "interrupted",
        resume=True,
    )
    uninterrupted = collect_resumable(plan, world, tmp_path / "uninterrupted")
    assert resumed.status == "COMPLETE"
    assert uninterrupted.status == "COMPLETE"
    assert resumed.bundle is not None
    assert uninterrupted.bundle is not None
    assert resumed.bundle.manifest_sha256 == uninterrupted.bundle.manifest_sha256
    resumed_report = analyze_trials(resumed.bundle)
    uninterrupted_report = analyze_trials(uninterrupted.bundle)
    assert resumed_report.model_dump() == uninterrupted_report.model_dump()


def test_assignment_is_committed_before_inference_and_reused_after_crash(
    tmp_path: Path,
) -> None:
    source = GeneratedMemoryTaskSource(seed=7, episode_count=80)
    plan = _plan(source)
    root = tmp_path / "crash"
    inner = ReplayableMemoryWorld(source)

    class FailOnceWorld:
        identity = inner.identity
        provenance = inner.provenance

        def __init__(self) -> None:
            self.failed = False

        def prepare(self, trial_id: str):
            return inner.prepare(trial_id)

        def prepare_suffix_permutation(self, trial_id: str):
            return inner.prepare_suffix_permutation(trial_id)

        def continue_from(self, prepared, visibility, replay_key):
            if not self.failed:
                self.failed = True
                assignment = root / "assignments" / "00000001-memory-000000.json"
                assert assignment.is_file()
                raise RuntimeError("injected crash after durable assignment")
            return inner.continue_from(prepared, visibility, replay_key)

    world = FailOnceWorld()
    with pytest.raises(RuntimeError, match="injected crash"):
        collect_resumable(plan, world, root)
    assignment = root / "assignments" / "00000001-memory-000000.json"
    assignment_hash = hashlib.sha256(assignment.read_bytes()).hexdigest()
    resumed = collect_resumable(plan, world, root, resume=True)
    assert resumed.status == "COMPLETE"
    assert hashlib.sha256(assignment.read_bytes()).hexdigest() == assignment_hash


def test_same_arm_mismatch_is_durable_before_collection_aborts(tmp_path: Path) -> None:
    source = GeneratedMemoryTaskSource(seed=7, episode_count=80)
    calls = 0

    def drifting_complete(_prompt: str) -> str:
        nonlocal calls
        calls += 1
        answer = "value-000" if calls == 1 else "UNKNOWN"
        return json.dumps({"mode": "answer", "answer": answer})

    actor = JsonCompletionMemoryActor(
        identity="drifting-fixture-v1",
        complete=drifting_complete,
        contract={"identity": "drifting-fixture-v1", "fixture": "aa-drift-v1"},
    )
    plan = _plan(source).model_copy(update={"paired_audit_ids": frozenset({"memory-000000"})})
    root = tmp_path / "aa-mismatch"
    with pytest.raises(TrialContractError, match="diagnostic_sha256"):
        collect_resumable(plan, ReplayableMemoryWorld(source, actor=actor), root)
    failure_path = root / "failures" / "00000001-memory-000000.json"
    failure = json.loads(failure_path.read_text())
    assert failure["kind"] == "same-arm-aa-mismatch"
    assert failure["comparison"]["prompt_equal"] is True
    assert failure["comparison"]["memory_frame_equal"] is True
    assert failure["comparison"]["model_output_equal"] is False
    assert failure["comparison"]["tool_trace_equal"] is False
    assert not (root / "episodes" / "00000001-memory-000000.json").exists()


def test_checkpoint_tampering_blocks_resume(tmp_path: Path) -> None:
    source = GeneratedMemoryTaskSource(seed=7, episode_count=80)
    plan = _plan(source)
    world = ReplayableMemoryWorld(source)
    root = tmp_path / "tampered"
    result = collect_resumable(plan, world, root, stop_after=5)
    assert result.status == "CHECKPOINTED"
    episode = root / "episodes" / "00000003-memory-000002.json"
    episode.write_text(episode.read_text() + "\n")
    with pytest.raises(ArtifactIntegrityError, match="checkpoint does not match"):
        collect_resumable(plan, world, root, resume=True)


def test_checkpoint_marker_is_written_after_episode_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = GeneratedMemoryTaskSource(seed=7, episode_count=80)
    plan = _plan(source)
    marker = tmp_path / "checkpoint.ready"
    monkeypatch.setenv("COTCODEC_CHECKPOINT_MARKER", str(marker))
    result = collect_resumable(
        plan,
        ReplayableMemoryWorld(source),
        tmp_path / "marker-run",
        stop_after=1,
    )
    receipt = json.loads(marker.read_text())
    assert result.completed_trials == 1
    assert receipt["completed_trials"] == 1
    assert receipt["checkpoint_sha256"] == result.checkpoint_sha256


@pytest.mark.parametrize("task_id", ["memory-000004", "memory-000008"])
def test_direct_memory_frame_never_serves_superseded_or_deleted_records(
    task_id: str,
) -> None:
    source = GeneratedMemoryTaskSource(seed=7, episode_count=9)
    world = ReplayableMemoryWorld(source)
    prepared = world.prepare(task_id)
    outcome = world.continue_from(prepared, "holdout", "a" * 64)
    frame = json.loads(outcome.memory_frame_json)
    record_ids = {record["id"] for record in frame["records"]}
    assert not any(record_id.endswith("history-stale") for record_id in record_ids)
    assert any(record_id.endswith("baseline") for record_id in record_ids)
