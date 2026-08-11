"""Causal memory holdout trials with durable assignment and paired replay audits.

This module deliberately exposes only collection and analysis. Model/tool details
remain behind ``TrialWorld`` so the causal ordering cannot drift across callers.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Literal, Protocol

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator
from scipy.stats import spearmanr


class TrialContractError(ValueError):
    """Raised when a plan or prepared trial violates the causal contract."""


class FeatureLeakageError(TrialContractError):
    """Raised when a policy feature is unavailable at memory-write time."""


class ReplayMismatchError(TrialContractError):
    """Raised when paired continuations do not restore the same state/randomness."""


class ArtifactIntegrityError(TrialContractError):
    """Raised when an artifact bundle is missing, changed, or would be overwritten."""


class EstimationError(TrialContractError):
    """Raised when overlap or cross-fitting cannot support the registered estimator."""


class PrefixEvent(BaseModel):
    """One content-addressed framework event available before memory use."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
    entity_id: str = Field(min_length=1)
    step: int = Field(ge=0)
    kind: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    values: dict[str, float]

    @model_validator(mode="after")
    def finite_values(self) -> PrefixEvent:
        if any(not math.isfinite(value) for value in self.values.values()):
            raise ValueError("prefix event values must be finite")
        return self


class FeatureValue(BaseModel):
    """One scalar feature and evidence that it existed at write time."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    value: float
    source_event: str = Field(min_length=1)
    source_field: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    observed_step: int = Field(ge=0)

    @model_validator(mode="after")
    def finite_value(self) -> FeatureValue:
        if not math.isfinite(self.value):
            raise ValueError("feature value must be finite")
        return self


class PreparedTrial(BaseModel):
    """A world snapshot stopped immediately before first retrieval eligibility."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    trial_id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
    group_id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
    session_id: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1)
    write_step: int = Field(ge=0)
    eligibility_step: int = Field(ge=1)
    prefix_events: tuple[PrefixEvent, ...]
    prefix_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    snapshot_json: str = Field(min_length=2)
    snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    rng_state_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    tool_tape_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    features: dict[str, FeatureValue]

    @model_validator(mode="after")
    def validate_causal_order(self) -> PreparedTrial:
        if self.write_step >= self.eligibility_step:
            raise ValueError("write_step must precede eligibility_step")
        computed = hashlib.sha256(self.snapshot_json.encode()).hexdigest()
        if computed != self.snapshot_sha256:
            raise ValueError("snapshot_sha256 does not bind snapshot_json")
        if not self.prefix_events:
            raise ValueError("prefix_events must be non-empty")
        event_ids = [event.event_id for event in self.prefix_events]
        if len(set(event_ids)) != len(event_ids):
            raise ValueError("prefix event ids must be unique")
        if any(event.step > self.write_step for event in self.prefix_events):
            raise ValueError("prefix event occurs after write_step")
        prefix_payload = [
            event.model_dump(mode="json")
            for event in sorted(self.prefix_events, key=lambda item: (item.step, item.event_id))
        ]
        prefix_json = json.dumps(
            prefix_payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        if hashlib.sha256(prefix_json.encode()).hexdigest() != self.prefix_digest:
            raise ValueError("prefix_digest does not bind prefix_events")
        events = {event.event_id: event for event in self.prefix_events}
        late = [
            name
            for name, feature in self.features.items()
            if feature.observed_step > self.write_step
        ]
        if late:
            raise ValueError(f"features observed after write_step: {sorted(late)}")
        for name, feature in self.features.items():
            event = events.get(feature.source_event)
            if event is None:
                raise ValueError(f"feature {name} references an unknown prefix event")
            if event.step != feature.observed_step:
                raise ValueError(f"feature {name} observed_step contradicts its event")
            if event.values.get(feature.source_field) != feature.value:
                raise ValueError(f"feature {name} does not match its source event field")
        return self


class TrialOutcome(BaseModel):
    """Executable continuation outcome for exactly one memory-visibility arm."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    visibility: Literal["serve", "holdout"]
    utility: float = Field(ge=0.0, le=1.0)
    success: bool
    safety_failure: bool = False
    restored_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    replay_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    rng_state_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    tool_tape_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    exogenous_trace_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_visible: bool
    metrics: dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_visibility(self) -> TrialOutcome:
        expected = self.visibility == "serve"
        if self.candidate_visible is not expected:
            raise ValueError("candidate visibility receipt contradicts the assigned arm")
        if any(not math.isfinite(value) for value in self.metrics.values()):
            raise ValueError("outcome metrics must be finite")
        return self


class TrialPlan(BaseModel):
    """Frozen collection and estimator choices for one CPU study."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    study_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    trial_ids: tuple[str, ...]
    allowed_features: tuple[str, ...]
    paired_audit_ids: frozenset[str]
    propensity: float = Field(gt=0.0, lt=1.0)
    assignment_seed: int
    folds: int = Field(default=5, ge=2, le=20)
    ridge: float = Field(default=1e-3, ge=0.0, le=100.0)
    minimum_effective_sample_size: float = Field(default=400.0, gt=0.0)
    minimum_arm_effective_sample_size: float = Field(default=100.0, gt=0.0)
    maximum_aipw_oracle_ate_gap: float = Field(default=0.05, ge=0.0, le=1.0)
    minimum_aipw_oracle_correlation: float = Field(default=0.2, ge=-1.0, le=1.0)
    minimum_audit_correlation: float = Field(default=0.2, ge=-1.0, le=1.0)

    @model_validator(mode="after")
    def validate_plan(self) -> TrialPlan:
        if not self.trial_ids or len(set(self.trial_ids)) != len(self.trial_ids):
            raise ValueError("trial_ids must be non-empty and unique")
        if not self.allowed_features or len(set(self.allowed_features)) != len(
            self.allowed_features
        ):
            raise ValueError("allowed_features must be non-empty and unique")
        unknown_audits = set(self.paired_audit_ids) - set(self.trial_ids)
        if unknown_audits:
            raise ValueError(f"unknown paired audit ids: {sorted(unknown_audits)}")
        if not self.paired_audit_ids:
            raise ValueError("paired_audit_ids must include a sealed replay audit set")
        return self


class TrialBundle(BaseModel):
    """Content-addressed directory emitted by ``run_trials``."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    root: Path
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class EffectPolicy(BaseModel):
    """Small deterministic ridge policy trained on AIPW pseudo-outcomes."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    feature_names: tuple[str, ...]
    intercept: float
    coefficients: tuple[float, ...]

    def predict(self, features: Mapping[str, float]) -> float:
        try:
            values = np.asarray([features[name] for name in self.feature_names], dtype=float)
        except KeyError as exc:
            raise TrialContractError(f"missing policy feature: {exc.args[0]}") from exc
        if not np.isfinite(values).all():
            raise TrialContractError("policy features must be finite")
        return float(self.intercept + values @ np.asarray(self.coefficients))


class AnalysisReport(BaseModel):
    """Registered diagnostics and learned policy for one sealed bundle."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    study_id: str
    observed_trials: int
    paired_audits: int
    policy_training_trials: int
    aipw_average_effect: float
    aipw_standard_error: float
    effective_sample_size: float
    treated_effective_sample_size: float
    control_effective_sample_size: float
    paired_oracle_average_effect: float
    aipw_audit_average_effect: float
    aipw_oracle_absolute_gap: float
    aipw_oracle_correlation: float
    aipw_oracle_rmse: float
    policy_oracle_correlation: float
    learned_policy_success: float | None
    always_serve_success: float | None
    always_holdout_success: float | None
    gates: dict[str, bool]
    policy: EffectPolicy
    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class TrialWorld(Protocol):
    """The only adapter seam: prepare and continue a replayable environment."""

    identity: str
    provenance: Mapping[str, Any]

    def prepare(self, trial_id: str) -> PreparedTrial: ...

    def prepare_suffix_permutation(self, trial_id: str) -> PreparedTrial: ...

    def continue_from(
        self,
        prepared: PreparedTrial,
        visibility: Literal["serve", "holdout"],
        replay_key: str,
    ) -> TrialOutcome: ...


_FORBIDDEN_FEATURE_PARTS = {
    "assignment",
    "branch",
    "future",
    "oracle",
    "outcome",
    "query",
    "suffix",
    "treatment",
    "use-time",
    "use_time",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _keyed_hex(*parts: str | int) -> str:
    payload = "\x1f".join(str(part) for part in parts).encode()
    return _sha256_bytes(payload)


def _assignment(plan: TrialPlan, prepared: PreparedTrial) -> tuple[bool, str]:
    draw_digest = _keyed_hex(
        "cmht-assignment-v1",
        plan.assignment_seed,
        prepared.trial_id,
        prepared.snapshot_sha256,
    )
    draw = int(draw_digest[:16], 16) / float(1 << 64)
    return draw < plan.propensity, draw_digest


def _validate_features(plan: TrialPlan, prepared: PreparedTrial) -> None:
    names = set(prepared.features)
    unknown = names - set(plan.allowed_features)
    missing = set(plan.allowed_features) - names
    if unknown or missing:
        raise FeatureLeakageError(
            f"feature schema mismatch; unknown={sorted(unknown)}, missing={sorted(missing)}"
        )
    forbidden = sorted(
        name
        for name in names
        if any(part in name.casefold() for part in _FORBIDDEN_FEATURE_PARTS)
    )
    if forbidden:
        raise FeatureLeakageError(f"forbidden future/branch features: {forbidden}")
    remapped = sorted(
        name
        for name, feature in prepared.features.items()
        if name != feature.source_field
    )
    if remapped:
        raise FeatureLeakageError(
            f"feature names must directly match source fields: {remapped}"
        )
    forbidden_lineage = sorted(
        name
        for name, feature in prepared.features.items()
        if any(
            part in feature.source_event.casefold()
            for part in _FORBIDDEN_FEATURE_PARTS
        )
        or any(
            part in feature.source_field.casefold()
            for part in _FORBIDDEN_FEATURE_PARTS
        )
    )
    if forbidden_lineage:
        raise FeatureLeakageError(
            f"feature lineage references future/branch events: {forbidden_lineage}"
        )


def _append_durable(path: Path, row: Mapping[str, Any]) -> None:
    encoded = (_canonical_json(row) + "\n").encode()
    with path.open("ab", buffering=0) as handle:
        handle.write(encoded)
        os.fsync(handle.fileno())


def _write_durable_json(path: Path, row: Mapping[str, Any]) -> None:
    encoded = (json.dumps(row, indent=2, sort_keys=True) + "\n").encode()
    with path.open("wb", buffering=0) as handle:
        handle.write(encoded)
        os.fsync(handle.fileno())


def _write_durable_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    encoded = "".join(_canonical_json(row) + "\n" for row in rows).encode()
    with path.open("xb", buffering=0) as handle:
        handle.write(encoded)
        os.fsync(handle.fileno())


def _validate_outcome(
    prepared: PreparedTrial,
    outcome: TrialOutcome,
    replay_key: str,
    expected_visibility: Literal["serve", "holdout"],
) -> None:
    if outcome.visibility != expected_visibility:
        raise ReplayMismatchError("continuation returned the opposite requested arm")
    if outcome.restored_snapshot_sha256 != prepared.snapshot_sha256:
        raise ReplayMismatchError("continuation restored a different snapshot")
    if outcome.replay_key != replay_key:
        raise ReplayMismatchError("continuation changed the common replay key")
    if outcome.rng_state_sha256 != prepared.rng_state_sha256:
        raise ReplayMismatchError("continuation used a different RNG state")
    if outcome.tool_tape_sha256 != prepared.tool_tape_sha256:
        raise ReplayMismatchError("continuation used a different tool-response tape")


def _validate_paired_replay(first: TrialOutcome, second: TrialOutcome) -> None:
    for field in (
        "rng_state_sha256",
        "tool_tape_sha256",
        "exogenous_trace_sha256",
    ):
        if getattr(first, field) != getattr(second, field):
            raise ReplayMismatchError(f"paired branches differ in {field}")


def run_trials(
    plan: TrialPlan,
    world: TrialWorld,
    output_dir: Path,
) -> TrialBundle:
    """Collect randomized observed arms and sealed paired replay audits."""

    output_dir = output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ArtifactIntegrityError(f"refusing to overwrite non-empty run directory: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    assignment_path = output_dir / "assignment_journal.jsonl"
    observed_path = output_dir / "observed_trials.jsonl"
    audit_path = output_dir / "paired_audit.jsonl"
    feature_path = output_dir / "feature_audits.jsonl"
    prepared_path = output_dir / "prepared_trials.jsonl"
    artifact_paths = (
        assignment_path,
        observed_path,
        audit_path,
        feature_path,
        prepared_path,
    )
    for path in artifact_paths:
        path.touch(exist_ok=False)
    plan_payload = plan.model_dump(mode="json")
    plan_payload["paired_audit_ids"] = sorted(plan.paired_audit_ids)
    plan_sha256 = _sha256_bytes(_canonical_json(plan_payload).encode())
    prefix_frames: dict[str, str] = {}
    world_provenance = getattr(world, "provenance", None)
    if not isinstance(world_provenance, Mapping):
        raise TrialContractError("TrialWorld must expose a provenance mapping")
    world_provenance = dict(world_provenance)

    try:
        for sequence, trial_id in enumerate(plan.trial_ids, start=1):
            prepared = world.prepare(trial_id)
            _validate_features(plan, prepared)
            prepared = PreparedTrial.model_validate(prepared.model_dump(mode="python"))
            permuted = world.prepare_suffix_permutation(trial_id)
            _validate_features(plan, permuted)
            permuted = PreparedTrial.model_validate(permuted.model_dump(mode="python"))
            if permuted.snapshot_sha256 == prepared.snapshot_sha256:
                raise FeatureLeakageError("suffix permutation did not change the suffix snapshot")
            if (
                permuted.prefix_digest != prepared.prefix_digest
                or permuted.features != prepared.features
            ):
                raise FeatureLeakageError(
                    "suffix permutation changed write-time features or prefix digest"
                )
            if prepared.trial_id != trial_id:
                raise TrialContractError(
                    f"world prepared {prepared.trial_id!r} for requested {trial_id!r}"
                )
            feature_values = {
                name: feature.value for name, feature in sorted(prepared.features.items())
            }
            frame_json = _canonical_json(feature_values)
            prior_frame = prefix_frames.setdefault(prepared.prefix_digest, frame_json)
            if prior_frame != frame_json:
                raise FeatureLeakageError(
                    "identical prefix digests produced different feature frames"
                )
            feature_lineage = {
                name: {
                    "source_event": feature.source_event,
                    "source_field": feature.source_field,
                    "observed_step": feature.observed_step,
                }
                for name, feature in sorted(prepared.features.items())
            }
            _append_durable(
                prepared_path,
                {
                    "schema_version": "1.0",
                    "trial_id": trial_id,
                    "session_id": prepared.session_id,
                    "candidate_id": prepared.candidate_id,
                    "write_step": prepared.write_step,
                    "eligibility_step": prepared.eligibility_step,
                    "prefix_events": [
                        event.model_dump(mode="json") for event in prepared.prefix_events
                    ],
                    "prefix_digest": prepared.prefix_digest,
                    "snapshot_json": prepared.snapshot_json,
                    "snapshot_sha256": prepared.snapshot_sha256,
                    "rng_state_sha256": prepared.rng_state_sha256,
                    "tool_tape_sha256": prepared.tool_tape_sha256,
                },
            )
            _append_durable(
                feature_path,
                {
                    "schema_version": "1.0",
                    "trial_id": trial_id,
                    "session_id": prepared.session_id,
                    "candidate_id": prepared.candidate_id,
                    "write_step": prepared.write_step,
                    "eligibility_step": prepared.eligibility_step,
                    "prefix_digest": prepared.prefix_digest,
                    "features": feature_values,
                    "lineage": feature_lineage,
                    "status": "past-only-pass",
                    "suffix_permutation_snapshot_sha256": permuted.snapshot_sha256,
                },
            )

            serve, draw_digest = _assignment(plan, prepared)
            visibility: Literal["serve", "holdout"] = "serve" if serve else "holdout"
            replay_key = _keyed_hex(
                "cmht-replay-v1",
                plan.assignment_seed,
                prepared.trial_id,
                prepared.snapshot_sha256,
            )
            assignment = {
                "schema_version": "1.0",
                "sequence": sequence,
                "trial_id": trial_id,
                "candidate_id": prepared.candidate_id,
                "prefix_digest": prepared.prefix_digest,
                "snapshot_sha256": prepared.snapshot_sha256,
                "visibility": visibility,
                "propensity_serve": plan.propensity,
                "draw_digest": draw_digest,
                "replay_key": replay_key,
            }
            # Scientific validity depends on this durable write occurring before execution.
            _append_durable(assignment_path, assignment)

            observed = world.continue_from(prepared, visibility, replay_key)
            _validate_outcome(prepared, observed, replay_key, visibility)
            observed_row = {
                "schema_version": "1.0",
                "trial_id": trial_id,
                "group_id": prepared.group_id,
                "snapshot_sha256": prepared.snapshot_sha256,
                "features": feature_values,
                "served": serve,
                "propensity_serve": plan.propensity,
                "outcome": observed.model_dump(mode="json"),
            }
            _append_durable(observed_path, observed_row)

            if trial_id in plan.paired_audit_ids:
                repeated = world.continue_from(prepared, visibility, replay_key)
                _validate_outcome(prepared, repeated, replay_key, visibility)
                _validate_paired_replay(observed, repeated)
                if repeated != observed:
                    raise ReplayMismatchError(
                        "same-arm A/A replay did not reproduce the observed outcome"
                    )
                opposite: Literal["serve", "holdout"] = (
                    "holdout" if visibility == "serve" else "serve"
                )
                counterfactual = world.continue_from(prepared, opposite, replay_key)
                _validate_outcome(prepared, counterfactual, replay_key, opposite)
                _validate_paired_replay(observed, counterfactual)
                served_outcome = observed if serve else counterfactual
                held_out_outcome = counterfactual if serve else observed
                _append_durable(
                    audit_path,
                    {
                        "schema_version": "1.0",
                        "trial_id": trial_id,
                        "group_id": prepared.group_id,
                        "snapshot_sha256": prepared.snapshot_sha256,
                        "replay_key": replay_key,
                        "same_arm_replay": repeated.model_dump(mode="json"),
                        "served_outcome": served_outcome.model_dump(mode="json"),
                        "held_out_outcome": held_out_outcome.model_dump(mode="json"),
                        "first_use_serve_effect": (
                            served_outcome.utility - held_out_outcome.utility
                        ),
                    },
                )

        files = {
            path.name: _sha256_file(path) if path.exists() else _sha256_bytes(b"")
            for path in artifact_paths
        }
        manifest = {
            "schema_version": "1.0",
            "study_id": plan.study_id,
            "status": "COMPLETE",
            "world_identity": world.identity,
            "world_provenance": world_provenance,
            "runtime": {
                "python": sys.version,
                "numpy": importlib.metadata.version("numpy"),
                "pydantic": importlib.metadata.version("pydantic"),
                "scipy": importlib.metadata.version("scipy"),
                "implementation_sha256": _sha256_file(Path(__file__)),
            },
            "plan": plan_payload,
            "plan_sha256": plan_sha256,
            "files": files,
            "observed_trials": len(plan.trial_ids),
            "paired_audits": len(plan.paired_audit_ids),
        }
    except Exception as exc:
        failure = {
            "schema_version": "1.0",
            "study_id": plan.study_id,
            "status": "FAIL",
            "world_identity": world.identity,
            "world_provenance": world_provenance,
            "plan": plan_payload,
            "plan_sha256": plan_sha256,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        _write_durable_json(output_dir / "manifest.json", failure)
        raise

    manifest_path = output_dir / "manifest.json"
    _write_durable_json(manifest_path, manifest)
    return TrialBundle(root=output_dir, manifest_sha256=_sha256_file(manifest_path))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactIntegrityError(f"invalid JSONL artifact {path}: {exc}") from exc


def _load_bundle(bundle: TrialBundle) -> tuple[dict[str, Any], list[dict], list[dict]]:
    manifest_path = bundle.root / "manifest.json"
    if _sha256_file(manifest_path) != bundle.manifest_sha256:
        raise ArtifactIntegrityError("manifest hash mismatch")
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("status") != "COMPLETE":
        raise ArtifactIntegrityError("cannot analyze an incomplete trial bundle")
    for name, expected in manifest.get("files", {}).items():
        path = bundle.root / name
        actual = _sha256_file(path) if path.exists() else _sha256_bytes(b"")
        if actual != expected:
            raise ArtifactIntegrityError(f"artifact hash mismatch: {name}")
    assignments = _read_jsonl(bundle.root / "assignment_journal.jsonl")
    observed = _read_jsonl(bundle.root / "observed_trials.jsonl")
    audits = _read_jsonl(bundle.root / "paired_audit.jsonl")
    expected_ids = tuple(manifest["plan"]["trial_ids"])
    assignment_ids = tuple(str(row["trial_id"]) for row in assignments)
    observed_ids = tuple(str(row["trial_id"]) for row in observed)
    if assignment_ids != expected_ids or observed_ids != expected_ids:
        raise ArtifactIntegrityError(
            "assignment and observed trial order must match the frozen plan exactly"
        )
    if len(set(assignment_ids)) != len(assignment_ids):
        raise ArtifactIntegrityError("assignment journal contains duplicate trials")
    registered_propensity = float(manifest["plan"]["propensity"])
    assignment_seed = int(manifest["plan"]["assignment_seed"])
    for assignment, outcome in zip(assignments, observed, strict=True):
        assignment_served = assignment.get("visibility") == "serve"
        if assignment.get("visibility") not in {"serve", "holdout"}:
            raise ArtifactIntegrityError("assignment journal contains an invalid arm")
        if bool(outcome.get("served")) is not assignment_served:
            raise ArtifactIntegrityError("observed arm contradicts its assignment")
        if outcome.get("outcome", {}).get("visibility") != assignment.get("visibility"):
            raise ArtifactIntegrityError("outcome visibility contradicts its assignment")
        if assignment.get("snapshot_sha256") != outcome.get("snapshot_sha256"):
            raise ArtifactIntegrityError("assignment and outcome snapshots differ")
        logged_propensities = (
            float(assignment.get("propensity_serve")),
            float(outcome.get("propensity_serve")),
        )
        if any(value != registered_propensity for value in logged_propensities):
            raise ArtifactIntegrityError("logged propensity contradicts the frozen plan")
        expected_draw = _keyed_hex(
            "cmht-assignment-v1",
            assignment_seed,
            assignment["trial_id"],
            assignment["snapshot_sha256"],
        )
        if assignment.get("draw_digest") != expected_draw:
            raise ArtifactIntegrityError("assignment draw digest is not reproducible")
        draw = int(expected_draw[:16], 16) / float(1 << 64)
        if assignment_served != (draw < registered_propensity):
            raise ArtifactIntegrityError("assignment arm contradicts its committed draw")
        expected_replay = _keyed_hex(
            "cmht-replay-v1",
            assignment_seed,
            assignment["trial_id"],
            assignment["snapshot_sha256"],
        )
        if assignment.get("replay_key") != expected_replay:
            raise ArtifactIntegrityError("assignment replay key is not reproducible")

    expected_audits = set(manifest["plan"]["paired_audit_ids"])
    audit_ids = [str(row.get("trial_id")) for row in audits]
    if len(audit_ids) != len(expected_audits) or set(audit_ids) != expected_audits:
        raise ArtifactIntegrityError("paired audits must match the plan exactly once")
    observed_by_id = {str(row["trial_id"]): row for row in observed}
    assignments_by_id = {str(row["trial_id"]): row for row in assignments}
    for audit in audits:
        trial_id = str(audit["trial_id"])
        observed_row = observed_by_id[trial_id]
        assignment = assignments_by_id[trial_id]
        served_outcome = TrialOutcome.model_validate(audit["served_outcome"])
        held_out_outcome = TrialOutcome.model_validate(audit["held_out_outcome"])
        repeated_outcome = TrialOutcome.model_validate(audit["same_arm_replay"])
        if served_outcome.visibility != "serve" or held_out_outcome.visibility != "holdout":
            raise ArtifactIntegrityError("paired audit arms are mislabeled")
        expected_effect = served_outcome.utility - held_out_outcome.utility
        if float(audit.get("first_use_serve_effect")) != expected_effect:
            raise ArtifactIntegrityError("paired audit effect is not reproducible")
        if (
            audit.get("snapshot_sha256") != observed_row.get("snapshot_sha256")
            or audit.get("group_id") != observed_row.get("group_id")
            or audit.get("replay_key") != assignment.get("replay_key")
        ):
            raise ArtifactIntegrityError("paired audit does not join its observed trial")
        if repeated_outcome.model_dump(mode="json") != observed_row.get("outcome"):
            raise ArtifactIntegrityError("same-arm replay does not match observed outcome")
    return (
        manifest,
        observed,
        audits,
    )


def _ridge_fit(x: np.ndarray, y: np.ndarray, ridge: float) -> np.ndarray:
    design = np.column_stack([np.ones(len(x)), x])
    penalty = np.eye(design.shape[1]) * ridge
    penalty[0, 0] = 0.0
    return np.linalg.pinv(design.T @ design + penalty) @ design.T @ y


def _ridge_predict(beta: np.ndarray, x: np.ndarray) -> np.ndarray:
    return np.column_stack([np.ones(len(x)), x]) @ beta


def _fold_ids(groups: Sequence[str], folds: int) -> np.ndarray:
    unique_groups = sorted(set(groups))
    if len(unique_groups) < folds:
        raise EstimationError(
            f"need at least {folds} groups for group cross-fitting; got {len(unique_groups)}"
        )
    group_to_fold = {
        group: int(_keyed_hex("cmht-fold-v1", group)[:16], 16) % folds
        for group in unique_groups
    }
    occupied = set(group_to_fold.values())
    if len(occupied) < folds:
        # Deterministically fill every fold without using row order or outcomes.
        group_to_fold = {
            group: index % folds for index, group in enumerate(unique_groups)
        }
    return np.asarray([group_to_fold[group] for group in groups], dtype=int)


def _feature_matrix(
    rows: Sequence[Mapping[str, Any]],
    feature_names: Sequence[str],
) -> np.ndarray:
    matrix = np.asarray(
        [[row["features"][name] for name in feature_names] for row in rows],
        dtype=float,
    )
    if matrix.ndim != 2 or not np.isfinite(matrix).all():
        raise EstimationError("feature matrix must be finite and two-dimensional")
    return matrix


def _effective_sample_size(z: np.ndarray, p: np.ndarray) -> float:
    weights = z / p + (1.0 - z) / (1.0 - p)
    return float(weights.sum() ** 2 / np.square(weights).sum())


def _arm_effective_sample_size(weights: np.ndarray) -> float:
    positive = weights[weights > 0.0]
    if not len(positive):
        return 0.0
    return float(np.square(positive.sum()) / np.square(positive).sum())


def _clustered_standard_error(values: np.ndarray, groups: Sequence[str]) -> float:
    if len(values) != len(groups):
        raise EstimationError("cluster labels do not align with estimator values")
    unique = sorted(set(groups))
    if len(unique) < 2:
        raise EstimationError("clustered standard error requires at least two groups")
    centered = values - values.mean()
    cluster_sums = np.asarray(
        [centered[np.asarray(groups) == group].sum() for group in unique],
        dtype=float,
    )
    variance = len(unique) / (len(unique) - 1) * float(
        np.square(cluster_sums).sum() / np.square(len(values))
    )
    return math.sqrt(max(variance, 0.0))


def _safe_spearman(first: np.ndarray, second: np.ndarray) -> float:
    if len(np.unique(first)) < 2 or len(np.unique(second)) < 2:
        return 0.0
    correlation = spearmanr(first, second).statistic
    return float(correlation) if math.isfinite(correlation) else 0.0


def analyze_trials(bundle: TrialBundle) -> AnalysisReport:
    """Verify a sealed bundle, cross-fit AIPW targets, and fit a past-only policy."""

    manifest, rows, audits = _load_bundle(bundle)
    plan = TrialPlan.model_validate(manifest["plan"])
    if len(rows) != len(plan.trial_ids):
        raise ArtifactIntegrityError("observed row count does not match the frozen plan")
    feature_names = plan.allowed_features
    x = _feature_matrix(rows, feature_names)
    z = np.asarray([float(row["served"]) for row in rows])
    p = np.asarray([float(row["propensity_serve"]) for row in rows])
    y = np.asarray([float(row["outcome"]["utility"]) for row in rows])
    groups = [str(row["group_id"]) for row in rows]
    audit_ids = {str(row["trial_id"]) for row in audits}
    if audit_ids != set(plan.paired_audit_ids):
        raise ArtifactIntegrityError("paired audit rows do not match the sealed audit plan")
    policy_train = np.asarray(
        [str(row["trial_id"]) not in audit_ids for row in rows],
        dtype=bool,
    )
    if policy_train.sum() < x.shape[1] + 2:
        raise EstimationError("too few non-audit trials to fit the retention policy")
    if not np.all((p > 0.0) & (p < 1.0)):
        raise EstimationError("logged propensities violate positivity")
    folds = _fold_ids(groups, plan.folds)
    m0 = np.empty(len(rows), dtype=float)
    m1 = np.empty(len(rows), dtype=float)
    fold_rows: list[dict[str, Any]] = []
    nuisance_rows: list[dict[str, Any]] = []

    for fold in range(plan.folds):
        test = folds == fold
        train = ~test
        if not test.any():
            raise EstimationError(f"cross-fit fold {fold} is empty")
        for arm, target in ((0.0, m0), (1.0, m1)):
            arm_train = train & policy_train & (z == arm)
            if arm_train.sum() < x.shape[1] + 2:
                raise EstimationError(
                    f"fold {fold} arm {int(arm)} has too few nuisance rows: {arm_train.sum()}"
                )
            beta = _ridge_fit(x[arm_train], y[arm_train], plan.ridge)
            target[test] = np.clip(_ridge_predict(beta, x[test]), 0.0, 1.0)
            nuisance_rows.append(
                {
                    "fold": fold,
                    "arm": int(arm),
                    "train_rows": int(arm_train.sum()),
                    "coefficients": beta.tolist(),
                }
            )
        fold_rows.extend(
            {"trial_id": rows[index]["trial_id"], "fold": fold}
            for index in np.flatnonzero(test)
        )

    pseudo = m1 - m0 + z / p * (y - m1) - (1.0 - z) / (1.0 - p) * (y - m0)
    if not np.isfinite(pseudo).all():
        raise EstimationError("AIPW pseudo-outcomes are non-finite")
    # Both arms of audit episodes remain sealed from nuisance and policy fitting.
    # This makes the reported policy-to-oracle correlation genuinely held out.
    policy_beta = _ridge_fit(x[policy_train], pseudo[policy_train], plan.ridge)
    policy_prediction = _ridge_predict(policy_beta, x)
    policy = EffectPolicy(
        feature_names=tuple(feature_names),
        intercept=float(policy_beta[0]),
        coefficients=tuple(float(value) for value in policy_beta[1:]),
    )
    effective_n = _effective_sample_size(z[policy_train], p[policy_train])
    treated_effective_n = _arm_effective_sample_size(
        z[policy_train] / p[policy_train]
    )
    control_effective_n = _arm_effective_sample_size(
        (1.0 - z[policy_train]) / (1.0 - p[policy_train])
    )
    training_groups = [
        group for group, included in zip(groups, policy_train, strict=True) if included
    ]
    standard_error = _clustered_standard_error(
        pseudo[policy_train],
        training_groups,
    )

    row_by_id = {str(row["trial_id"]): row for row in rows}
    prediction_by_id = {
        str(row["trial_id"]): float(prediction)
        for row, prediction in zip(rows, policy_prediction, strict=True)
    }
    paired_oracle_average = 0.0
    aipw_audit_average = 0.0
    aipw_oracle_gap = 0.0
    aipw_oracle_correlation = 0.0
    aipw_oracle_rmse = 0.0
    policy_oracle_correlation = 0.0
    learned_success: float | None = None
    serve_success: float | None = None
    holdout_success: float | None = None
    if audits:
        if any(str(row["trial_id"]) not in row_by_id for row in audits):
            raise ArtifactIntegrityError("paired audit references an unknown observed trial")
        effects = np.asarray([float(row["first_use_serve_effect"]) for row in audits])
        row_index = {
            str(row["trial_id"]): index for index, row in enumerate(rows)
        }
        audit_pseudo = np.asarray(
            [pseudo[row_index[str(row["trial_id"])]] for row in audits]
        )
        audit_predictions = np.asarray(
            [prediction_by_id[str(row["trial_id"])] for row in audits]
        )
        paired_oracle_average = float(effects.mean())
        aipw_audit_average = float(audit_pseudo.mean())
        aipw_oracle_gap = abs(aipw_audit_average - paired_oracle_average)
        aipw_oracle_correlation = _safe_spearman(audit_pseudo, effects)
        aipw_oracle_rmse = float(np.sqrt(np.mean(np.square(audit_pseudo - effects))))
        policy_oracle_correlation = _safe_spearman(audit_predictions, effects)
        served = np.asarray(
            [float(row["served_outcome"]["utility"]) for row in audits]
        )
        held_out = np.asarray(
            [float(row["held_out_outcome"]["utility"]) for row in audits]
        )
        learned = np.where(audit_predictions > 0.0, served, held_out)
        learned_success = float(learned.mean())
        serve_success = float(served.mean())
        holdout_success = float(held_out.mean())

    audit_safety_failures = any(
        bool(audit[key].get("safety_failure"))
        for audit in audits
        for key in ("served_outcome", "held_out_outcome", "same_arm_replay")
    )
    gates = {
        "effective_sample_size": effective_n >= plan.minimum_effective_sample_size,
        "minimum_arm_effective_sample_size": min(
            treated_effective_n,
            control_effective_n,
        )
        >= plan.minimum_arm_effective_sample_size,
        "aipw_oracle_ate_gap": (
            aipw_oracle_gap <= plan.maximum_aipw_oracle_ate_gap
        ),
        "aipw_oracle_correlation": (
            aipw_oracle_correlation >= plan.minimum_aipw_oracle_correlation
        ),
        "policy_oracle_correlation": (
            policy_oracle_correlation >= plan.minimum_audit_correlation
        ),
        "no_safety_failures": not any(
            bool(row["outcome"].get("safety_failure")) for row in rows
        )
        and not audit_safety_failures,
    }
    analysis_dir = bundle.root / "analysis"
    if analysis_dir.exists():
        raise ArtifactIntegrityError("refusing to overwrite an existing analysis")
    analysis_dir.mkdir()
    folds_path = analysis_dir / "folds.jsonl"
    nuisance_path = analysis_dir / "nuisance.jsonl"
    pseudo_path = analysis_dir / "pseudo_outcomes.jsonl"
    _write_durable_jsonl(folds_path, fold_rows)
    _write_durable_jsonl(nuisance_path, nuisance_rows)
    pseudo_rows = [
        {
            "trial_id": row["trial_id"],
            "fold": int(fold),
            "m0": float(control),
            "m1": float(treated),
            "pseudo_outcome": float(effect),
            "policy_prediction": float(prediction),
        }
        for row, fold, control, treated, effect, prediction in zip(
            rows,
            folds,
            m0,
            m1,
            pseudo,
            policy_prediction,
            strict=True,
        )
    ]
    _write_durable_jsonl(pseudo_path, pseudo_rows)
    report_payload = {
        "study_id": plan.study_id,
        "observed_trials": len(rows),
        "paired_audits": len(audits),
        "policy_training_trials": int(policy_train.sum()),
        "aipw_average_effect": float(pseudo[policy_train].mean()),
        "aipw_standard_error": standard_error,
        "effective_sample_size": effective_n,
        "treated_effective_sample_size": treated_effective_n,
        "control_effective_sample_size": control_effective_n,
        "paired_oracle_average_effect": paired_oracle_average,
        "aipw_audit_average_effect": aipw_audit_average,
        "aipw_oracle_absolute_gap": aipw_oracle_gap,
        "aipw_oracle_correlation": aipw_oracle_correlation,
        "aipw_oracle_rmse": aipw_oracle_rmse,
        "policy_oracle_correlation": policy_oracle_correlation,
        "learned_policy_success": learned_success,
        "always_serve_success": serve_success,
        "always_holdout_success": holdout_success,
        "gates": gates,
        "policy": policy.model_dump(mode="json"),
    }
    report_path = analysis_dir / "report.json"
    _write_durable_json(report_path, report_payload)
    analysis_manifest_path = analysis_dir / "manifest.json"
    analysis_manifest = {
        "schema_version": "1.0",
        "study_id": plan.study_id,
        "raw_manifest_sha256": bundle.manifest_sha256,
        "analyzer_sha256": _sha256_file(Path(__file__)),
        "runtime": {
            "python": sys.version,
            "numpy": importlib.metadata.version("numpy"),
            "scipy": importlib.metadata.version("scipy"),
        },
        "files": {
            path.name: _sha256_file(path)
            for path in (folds_path, nuisance_path, pseudo_path, report_path)
        },
    }
    _write_durable_json(analysis_manifest_path, analysis_manifest)
    report = AnalysisReport(
        **report_payload,
        artifact_sha256=_sha256_file(analysis_manifest_path),
    )
    verify_analysis(bundle, report.artifact_sha256)
    return report


def verify_analysis(bundle: TrialBundle, manifest_sha256: str) -> None:
    """Verify that a sealed analysis still binds every file and its raw bundle."""

    manifest_path = bundle.root / "analysis" / "manifest.json"
    if _sha256_file(manifest_path) != manifest_sha256:
        raise ArtifactIntegrityError("analysis manifest hash mismatch")
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("raw_manifest_sha256") != bundle.manifest_sha256:
        raise ArtifactIntegrityError("analysis does not bind the supplied raw bundle")
    for name, expected in manifest.get("files", {}).items():
        path = manifest_path.parent / name
        if not path.is_file() or _sha256_file(path) != expected:
            raise ArtifactIntegrityError(f"analysis artifact hash mismatch: {name}")


class SymbolicTrialWorld:
    """Deterministic first adapter with a known but hidden memory treatment effect."""

    def __init__(
        self,
        trials: Mapping[str, PreparedTrial],
        *,
        seed: int,
        groups: int,
    ) -> None:
        self._trials = dict(trials)
        self.identity = f"symbolic-memory-world-v2-seed{seed}-n{len(trials)}"
        self.provenance = {
            "generator": "symbolic-memory-world-v2",
            "seed": seed,
            "groups": groups,
            "trials": len(trials),
        }

    @classmethod
    def generate(cls, count: int, seed: int, *, groups: int = 20) -> SymbolicTrialWorld:
        if count < 20:
            raise TrialContractError("symbolic world requires at least 20 trials")
        if groups < 5 or groups > count:
            raise TrialContractError("groups must be between 5 and count")
        rng = np.random.default_rng(seed)
        trials: dict[str, PreparedTrial] = {}
        for index in range(count):
            trial_id = f"episode-{index:05d}"
            source_quality = float(rng.uniform())
            provenance_strength = float(rng.uniform())
            contradiction = float(rng.random() < 0.3)
            novelty = float(rng.uniform())
            budget_pressure = float(rng.uniform())
            age = float(rng.uniform())
            future_use_probability = float(
                np.clip(
                    0.10
                    + 0.45 * source_quality
                    + 0.20 * contradiction
                    + 0.10 * provenance_strength,
                    0.05,
                    0.90,
                )
            )
            future_use = float(rng.random() < future_use_probability)
            poisoned = float(
                rng.random() < np.clip(0.35 - 0.30 * provenance_strength, 0.02, 0.35)
            )
            stale = float(rng.random() < (0.10 + 0.35 * age))
            hidden_noise = float(rng.normal(0.0, 0.05))
            treatment_effect = float(
                np.clip(
                    future_use
                    * (0.15 + 0.35 * source_quality + 0.20 * contradiction)
                    - poisoned * (0.30 + 0.20 * novelty)
                    - stale * 0.15
                    + hidden_noise,
                    -0.75,
                    0.75,
                )
            )
            base_probability = float(
                np.clip(0.35 + 0.25 * rng.uniform() - 0.10 * budget_pressure, 0.10, 0.85)
            )
            snapshot = {
                "trial_id": trial_id,
                "base_probability": base_probability,
                "first_use_serve_effect": treatment_effect,
                "future_use": future_use,
                "poisoned": poisoned,
                "stale": stale,
            }
            snapshot_json = _canonical_json(snapshot)
            candidate_id = f"memory-{index:05d}"
            prefix_values = {
                "source_quality": source_quality,
                "provenance_strength": provenance_strength,
                "contradiction": contradiction,
                "novelty": novelty,
                "budget_pressure": budget_pressure,
                "age": age,
            }
            prefix_event = PrefixEvent(
                event_id=f"write-{index:05d}",
                entity_id=candidate_id,
                step=4,
                kind="memory_write",
                values=prefix_values,
            )
            prefix_json = _canonical_json([prefix_event.model_dump(mode="json")])
            features = {
                name: FeatureValue(
                    value=value,
                    source_event=prefix_event.event_id,
                    source_field=name,
                    observed_step=4,
                )
                for name, value in prefix_values.items()
            }
            trials[trial_id] = PreparedTrial(
                trial_id=trial_id,
                group_id=f"family-{index % groups:02d}",
                session_id=f"session-{index:05d}",
                candidate_id=candidate_id,
                write_step=4,
                eligibility_step=8,
                prefix_events=(prefix_event,),
                prefix_digest=_sha256_bytes(prefix_json.encode()),
                snapshot_json=snapshot_json,
                snapshot_sha256=_sha256_bytes(snapshot_json.encode()),
                rng_state_sha256=_keyed_hex("cmht-rng-state-v1", seed, trial_id),
                tool_tape_sha256=_keyed_hex("cmht-tool-tape-v1", seed, trial_id),
                features=features,
            )
        return cls(trials, seed=seed, groups=groups)

    @property
    def trial_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._trials))

    def prepare(self, trial_id: str) -> PreparedTrial:
        try:
            return self._trials[trial_id]
        except KeyError as exc:
            raise TrialContractError(f"unknown symbolic trial: {trial_id}") from exc

    def prepare_suffix_permutation(self, trial_id: str) -> PreparedTrial:
        prepared = self.prepare(trial_id)
        hidden = json.loads(prepared.snapshot_json)
        hidden["future_use"] = 1.0 - float(hidden["future_use"])
        hidden["suffix_permutation"] = _keyed_hex(
            "cmht-suffix-permutation-v1",
            trial_id,
        )
        snapshot_json = _canonical_json(hidden)
        return prepared.model_copy(
            update={
                "snapshot_json": snapshot_json,
                "snapshot_sha256": _sha256_bytes(snapshot_json.encode()),
            }
        )

    def continue_from(
        self,
        prepared: PreparedTrial,
        visibility: Literal["serve", "holdout"],
        replay_key: str,
    ) -> TrialOutcome:
        hidden = json.loads(prepared.snapshot_json)
        probability = float(hidden["base_probability"])
        if visibility == "serve":
            probability += float(hidden["first_use_serve_effect"])
        probability = float(np.clip(probability, 0.01, 0.99))
        common_draw = int(_keyed_hex("cmht-outcome-v1", replay_key)[:16], 16) / float(
            1 << 64
        )
        success = common_draw < probability
        return TrialOutcome(
            visibility=visibility,
            utility=float(success),
            success=success,
            safety_failure=False,
            restored_snapshot_sha256=prepared.snapshot_sha256,
            replay_key=replay_key,
            rng_state_sha256=prepared.rng_state_sha256,
            tool_tape_sha256=prepared.tool_tape_sha256,
            exogenous_trace_sha256=_keyed_hex("cmht-exogenous-v1", replay_key),
            candidate_visible=visibility == "serve",
            metrics={"success_probability": probability},
        )


def make_symbolic_plan(
    world: SymbolicTrialWorld,
    *,
    assignment_seed: int = 42,
    audit_fraction: float = 0.25,
    propensity: float = 0.5,
    folds: int = 5,
) -> TrialPlan:
    """Create the registered Stage-0 plan without exposing hidden symbolic fields."""

    if not 0.0 < audit_fraction <= 1.0:
        raise TrialContractError("audit_fraction must be in (0, 1]")
    audit_ids = frozenset(
        trial_id
        for trial_id in world.trial_ids
        if int(_keyed_hex("cmht-audit-v1", assignment_seed, trial_id)[:16], 16)
        / float(1 << 64)
        < audit_fraction
    )
    if not audit_ids:
        raise TrialContractError("audit schedule selected no trials")
    first = world.prepare(world.trial_ids[0])
    return TrialPlan(
        study_id="causal-memory-holdout-symbolic",
        trial_ids=world.trial_ids,
        allowed_features=tuple(sorted(first.features)),
        paired_audit_ids=audit_ids,
        propensity=propensity,
        assignment_seed=assignment_seed,
        folds=folds,
        minimum_effective_sample_size=400.0,
        minimum_arm_effective_sample_size=100.0,
    )


__all__ = [
    "AnalysisReport",
    "ArtifactIntegrityError",
    "EffectPolicy",
    "EstimationError",
    "FeatureLeakageError",
    "FeatureValue",
    "PrefixEvent",
    "PreparedTrial",
    "ReplayMismatchError",
    "SymbolicTrialWorld",
    "TrialBundle",
    "TrialContractError",
    "TrialOutcome",
    "TrialPlan",
    "TrialWorld",
    "analyze_trials",
    "make_symbolic_plan",
    "run_trials",
    "verify_analysis",
]
