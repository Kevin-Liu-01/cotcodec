from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

import pytest

from harness.causal_memory_trials import (
    ArtifactIntegrityError,
    FeatureLeakageError,
    FeatureValue,
    PreparedTrial,
    ReplayMismatchError,
    SymbolicTrialWorld,
    TrialBundle,
    TrialOutcome,
    TrialPlan,
    analyze_trials,
    make_symbolic_plan,
    run_trials,
    verify_analysis,
)


class JournalCheckingWorld:
    identity = "journal-checking-world-v1"

    def __init__(self, inner: SymbolicTrialWorld, journal: Path) -> None:
        self.inner = inner
        self.provenance = inner.provenance
        self.journal = journal
        self.checked: set[str] = set()

    def prepare(self, trial_id: str) -> PreparedTrial:
        return self.inner.prepare(trial_id)

    def prepare_suffix_permutation(self, trial_id: str) -> PreparedTrial:
        return self.inner.prepare_suffix_permutation(trial_id)

    def continue_from(
        self,
        prepared: PreparedTrial,
        visibility: Literal["serve", "holdout"],
        replay_key: str,
    ) -> TrialOutcome:
        committed_ids = {
            json.loads(line)["trial_id"]
            for line in self.journal.read_text().splitlines()
            if line.strip()
        }
        assert prepared.trial_id in committed_ids
        self.checked.add(prepared.trial_id)
        return self.inner.continue_from(prepared, visibility, replay_key)


class LeakyWorld:
    identity = "leaky-world-v1"

    def __init__(self, inner: SymbolicTrialWorld) -> None:
        self.inner = inner
        self.provenance = inner.provenance

    def prepare(self, trial_id: str) -> PreparedTrial:
        prepared = self.inner.prepare(trial_id)
        return prepared.model_copy(
            update={
                "features": {
                    **prepared.features,
                    "future_query": FeatureValue(
                        value=1.0,
                        source_event="future-query",
                        source_field="future_query",
                        observed_step=prepared.write_step,
                    ),
                }
            }
        )

    def prepare_suffix_permutation(self, trial_id: str) -> PreparedTrial:
        return self.inner.prepare_suffix_permutation(trial_id)

    def continue_from(
        self,
        prepared: PreparedTrial,
        visibility: Literal["serve", "holdout"],
        replay_key: str,
    ) -> TrialOutcome:
        return self.inner.continue_from(prepared, visibility, replay_key)


class MismatchedReplayWorld:
    identity = "mismatched-replay-world-v1"

    def __init__(self, inner: SymbolicTrialWorld) -> None:
        self.inner = inner
        self.provenance = inner.provenance

    def prepare(self, trial_id: str) -> PreparedTrial:
        return self.inner.prepare(trial_id)

    def prepare_suffix_permutation(self, trial_id: str) -> PreparedTrial:
        return self.inner.prepare_suffix_permutation(trial_id)

    def continue_from(
        self,
        prepared: PreparedTrial,
        visibility: Literal["serve", "holdout"],
        replay_key: str,
    ) -> TrialOutcome:
        outcome = self.inner.continue_from(prepared, visibility, replay_key)
        return outcome.model_copy(update={"restored_snapshot_sha256": "0" * 64})


class DriftedReplayWorld:
    identity = "drifted-replay-world-v1"

    def __init__(self, inner: SymbolicTrialWorld) -> None:
        self.inner = inner
        self.provenance = inner.provenance

    def prepare(self, trial_id: str) -> PreparedTrial:
        return self.inner.prepare(trial_id)

    def prepare_suffix_permutation(self, trial_id: str) -> PreparedTrial:
        return self.inner.prepare_suffix_permutation(trial_id)

    def continue_from(
        self,
        prepared: PreparedTrial,
        visibility: Literal["serve", "holdout"],
        replay_key: str,
    ) -> TrialOutcome:
        outcome = self.inner.continue_from(prepared, visibility, replay_key)
        if visibility == "holdout":
            return outcome.model_copy(update={"exogenous_trace_sha256": "f" * 64})
        return outcome


class PairedSafetyWorld:
    identity = "paired-safety-world-v1"

    def __init__(self, inner: SymbolicTrialWorld) -> None:
        self.inner = inner
        self.provenance = inner.provenance
        self.first_visibility: dict[str, str] = {}

    def prepare(self, trial_id: str) -> PreparedTrial:
        return self.inner.prepare(trial_id)

    def prepare_suffix_permutation(self, trial_id: str) -> PreparedTrial:
        return self.inner.prepare_suffix_permutation(trial_id)

    def continue_from(
        self,
        prepared: PreparedTrial,
        visibility: Literal["serve", "holdout"],
        replay_key: str,
    ) -> TrialOutcome:
        outcome = self.inner.continue_from(prepared, visibility, replay_key)
        first = self.first_visibility.setdefault(prepared.trial_id, visibility)
        if visibility != first:
            return outcome.model_copy(update={"safety_failure": True})
        return outcome


class OppositeArmWorld:
    identity = "opposite-arm-world-v1"

    def __init__(self, inner: SymbolicTrialWorld) -> None:
        self.inner = inner
        self.provenance = inner.provenance

    def prepare(self, trial_id: str) -> PreparedTrial:
        return self.inner.prepare(trial_id)

    def prepare_suffix_permutation(self, trial_id: str) -> PreparedTrial:
        return self.inner.prepare_suffix_permutation(trial_id)

    def continue_from(
        self,
        prepared: PreparedTrial,
        visibility: Literal["serve", "holdout"],
        replay_key: str,
    ) -> TrialOutcome:
        opposite: Literal["serve", "holdout"] = (
            "holdout" if visibility == "serve" else "serve"
        )
        return self.inner.continue_from(prepared, opposite, replay_key)


def _small_world_plan(count: int = 180) -> tuple[SymbolicTrialWorld, TrialPlan]:
    world = SymbolicTrialWorld.generate(count, seed=7)
    plan = make_symbolic_plan(world, audit_fraction=0.25)
    plan = plan.model_copy(
        update={
            "minimum_effective_sample_size": min(
                400.0,
                0.8 * (len(plan.trial_ids) - len(plan.paired_audit_ids)),
            ),
            "minimum_arm_effective_sample_size": 5.0,
        }
    )
    return world, plan


def test_trial_pipeline_commits_assignment_before_world_execution(tmp_path: Path) -> None:
    world, plan = _small_world_plan(60)
    run_dir = tmp_path / "run"
    checking_world = JournalCheckingWorld(
        world,
        run_dir / "assignment_journal.jsonl",
    )
    bundle = run_trials(plan, checking_world, run_dir)
    assert checking_world.checked == set(plan.trial_ids)
    report = analyze_trials(bundle)
    assert report.observed_trials == 60
    assert report.paired_audits == len(plan.paired_audit_ids)
    assert report.policy_training_trials == 60 - report.paired_audits
    assert report.gates["effective_sample_size"]


def test_symbolic_aipw_and_sealed_oracle_are_executable(tmp_path: Path) -> None:
    world, plan = _small_world_plan()
    report = analyze_trials(run_trials(plan, world, tmp_path / "run"))
    assert report.effective_sample_size == pytest.approx(report.policy_training_trials)
    assert -1.0 <= report.aipw_oracle_correlation <= 1.0
    assert -1.0 <= report.policy_oracle_correlation <= 1.0
    assert report.learned_policy_success is not None
    assert (tmp_path / "run" / "analysis" / "pseudo_outcomes.jsonl").is_file()


def test_future_feature_name_and_lineage_fail_closed(tmp_path: Path) -> None:
    world, plan = _small_world_plan(40)
    payload = plan.model_dump(mode="python")
    payload["allowed_features"] = (*plan.allowed_features, "future_query")
    leaky_plan = TrialPlan.model_validate(payload)
    with pytest.raises(FeatureLeakageError, match="forbidden"):
        run_trials(leaky_plan, LeakyWorld(world), tmp_path / "leaky")
    failure = json.loads((tmp_path / "leaky" / "manifest.json").read_text())
    assert failure["status"] == "FAIL"


def test_snapshot_mismatch_fails_without_dropping_episode(tmp_path: Path) -> None:
    world, plan = _small_world_plan(40)
    with pytest.raises(ReplayMismatchError, match="different snapshot"):
        run_trials(plan, MismatchedReplayWorld(world), tmp_path / "mismatch")
    failure = json.loads((tmp_path / "mismatch" / "manifest.json").read_text())
    assert failure["error_type"] == "ReplayMismatchError"


def test_artifact_tampering_is_detected_before_analysis(tmp_path: Path) -> None:
    world, plan = _small_world_plan(40)
    bundle = run_trials(plan, world, tmp_path / "run")
    with (bundle.root / "observed_trials.jsonl").open("a", encoding="utf-8") as handle:
        handle.write("{}\n")
    with pytest.raises(ArtifactIntegrityError, match="hash mismatch"):
        analyze_trials(bundle)


def test_registered_symbolic_plan_never_weakens_ess_threshold() -> None:
    world = SymbolicTrialWorld.generate(500, seed=7)
    plan = make_symbolic_plan(world)
    assert plan.minimum_effective_sample_size == 400.0


def test_arm_specific_exogenous_drift_fails_paired_replay(tmp_path: Path) -> None:
    world, plan = _small_world_plan(40)
    with pytest.raises(ReplayMismatchError, match="exogenous_trace_sha256"):
        run_trials(plan, DriftedReplayWorld(world), tmp_path / "drift")


def test_paired_audit_safety_is_included_in_gate(tmp_path: Path) -> None:
    world, plan = _small_world_plan(80)
    report = analyze_trials(
        run_trials(plan, PairedSafetyWorld(world), tmp_path / "safety")
    )
    assert not report.gates["no_safety_failures"]


def test_analysis_manifest_detects_post_analysis_tampering(tmp_path: Path) -> None:
    world, plan = _small_world_plan(80)
    bundle = run_trials(plan, world, tmp_path / "run")
    report = analyze_trials(bundle)
    verify_analysis(bundle, report.artifact_sha256)
    with (bundle.root / "analysis" / "folds.jsonl").open(
        "a", encoding="utf-8"
    ) as handle:
        handle.write("{}\n")
    with pytest.raises(ArtifactIntegrityError, match="analysis artifact hash mismatch"):
        verify_analysis(bundle, report.artifact_sha256)


def test_feature_name_cannot_remap_to_another_source_field(tmp_path: Path) -> None:
    world, plan = _small_world_plan(40)
    prepared = world.prepare(plan.trial_ids[0])
    source = prepared.features["source_quality"]

    class RemappedWorld:
        identity = "remapped-world-v1"
        provenance = world.provenance

        def prepare(self, trial_id: str) -> PreparedTrial:
            item = world.prepare(trial_id)
            if trial_id != prepared.trial_id:
                return item
            return item.model_copy(
                update={
                    "features": {
                        **item.features,
                        "age": source,
                    }
                }
            )

        def prepare_suffix_permutation(self, trial_id: str) -> PreparedTrial:
            return world.prepare_suffix_permutation(trial_id)

        def continue_from(
            self,
            item: PreparedTrial,
            visibility: Literal["serve", "holdout"],
            replay_key: str,
        ) -> TrialOutcome:
            return world.continue_from(item, visibility, replay_key)

    with pytest.raises(FeatureLeakageError, match="directly match"):
        run_trials(plan, RemappedWorld(), tmp_path / "remapped")


def test_world_cannot_return_the_opposite_requested_arm(tmp_path: Path) -> None:
    world, plan = _small_world_plan(40)
    with pytest.raises(ReplayMismatchError, match="opposite requested arm"):
        run_trials(plan, OppositeArmWorld(world), tmp_path / "opposite")


def test_safe_named_suffix_derived_feature_fails_permutation_check(
    tmp_path: Path,
) -> None:
    world, plan = _small_world_plan(40)
    payload = plan.model_dump(mode="python")
    payload["allowed_features"] = tuple(
        sorted((set(plan.allowed_features) - {"age"}) | {"latent"})
    )
    leaky_plan = TrialPlan.model_validate(payload)

    class SuffixSensitiveWorld:
        identity = "suffix-sensitive-world-v1"
        provenance = world.provenance

        @staticmethod
        def transform(item: PreparedTrial) -> PreparedTrial:
            latent = float(json.loads(item.snapshot_json)["future_use"])
            event = item.prefix_events[0].model_copy(
                update={"values": {**item.prefix_events[0].values, "latent": latent}}
            )
            prefix_json = json.dumps(
                [event.model_dump(mode="json")],
                sort_keys=True,
                separators=(",", ":"),
            )
            features = {
                name: value for name, value in item.features.items() if name != "age"
            }
            features["latent"] = FeatureValue(
                value=latent,
                source_event=event.event_id,
                source_field="latent",
                observed_step=event.step,
            )
            return item.model_copy(
                update={
                    "prefix_events": (event,),
                    "prefix_digest": hashlib.sha256(prefix_json.encode()).hexdigest(),
                    "features": features,
                }
            )

        def prepare(self, trial_id: str) -> PreparedTrial:
            return self.transform(world.prepare(trial_id))

        def prepare_suffix_permutation(self, trial_id: str) -> PreparedTrial:
            return self.transform(world.prepare_suffix_permutation(trial_id))

        def continue_from(
            self,
            item: PreparedTrial,
            visibility: Literal["serve", "holdout"],
            replay_key: str,
        ) -> TrialOutcome:
            return world.continue_from(item, visibility, replay_key)

    with pytest.raises(FeatureLeakageError, match="suffix permutation changed"):
        run_trials(leaky_plan, SuffixSensitiveWorld(), tmp_path / "suffix-leak")


def test_duplicate_audit_cannot_pass_after_local_hash_remint(tmp_path: Path) -> None:
    world, plan = _small_world_plan(40)
    bundle = run_trials(plan, world, tmp_path / "run")
    audit_path = bundle.root / "paired_audit.jsonl"
    first = audit_path.read_text().splitlines()[0]
    with audit_path.open("a", encoding="utf-8") as handle:
        handle.write(first + "\n")
    manifest_path = bundle.root / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"][audit_path.name] = hashlib.sha256(
        audit_path.read_bytes()
    ).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    reminted = TrialBundle(
        root=bundle.root,
        manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    )
    with pytest.raises(ArtifactIntegrityError, match="exactly once"):
        analyze_trials(reminted)
