"""Crash-resumable episode transactions for executable memory studies."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from harness.causal_memory_trials import (
    ArtifactIntegrityError,
    TrialBundle,
    TrialContractError,
    TrialPlan,
    TrialWorld,
    make_assignment_receipt,
    validate_paired_trial,
    validate_prepared_for_plan,
    validate_trial_outcome,
)
from harness.memory_trials.schema import canonical_json, sha256_text


@dataclass(frozen=True)
class CollectionResult:
    status: Literal["CHECKPOINTED", "COMPLETE"]
    root: Path
    checkpoint_sha256: str
    completed_trials: int
    bundle: TrialBundle | None = None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_dir(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> str:
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("xb", buffering=0) as handle:
        handle.write(encoded)
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    _fsync_dir(path.parent)
    return hashlib.sha256(encoded).hexdigest()


def _atomic_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> str:
    encoded = "".join(canonical_json(row) + "\n" for row in rows).encode()
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("xb", buffering=0) as handle:
        handle.write(encoded)
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    _fsync_dir(path.parent)
    return hashlib.sha256(encoded).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactIntegrityError(f"invalid JSON artifact {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ArtifactIntegrityError(f"JSON artifact must contain a mapping: {path}")
    return payload


def _plan_payload(plan: TrialPlan) -> dict[str, Any]:
    payload = plan.model_dump(mode="json")
    payload["paired_audit_ids"] = sorted(plan.paired_audit_ids)
    return payload


def _contract(plan: TrialPlan, world: TrialWorld) -> dict[str, Any]:
    provenance = getattr(world, "provenance", None)
    if not isinstance(provenance, Mapping):
        raise TrialContractError("TrialWorld must expose a provenance mapping")
    return {
        "schema_version": "1.0",
        "plan": _plan_payload(plan),
        "plan_sha256": sha256_text(canonical_json(_plan_payload(plan))),
        "world_identity": world.identity,
        "world_provenance": dict(provenance),
        "collector": "memory-episode-transactions-v1",
    }


def _checkpoint_payload(
    contract_sha256: str,
    trial_ids: tuple[str, ...],
    episode_dir: Path,
) -> dict[str, Any]:
    completed: list[dict[str, Any]] = []
    for sequence, trial_id in enumerate(trial_ids, start=1):
        path = episode_dir / f"{sequence:08d}-{trial_id}.json"
        if not path.exists():
            break
        completed.append(
            {
                "sequence": sequence,
                "trial_id": trial_id,
                "sha256": _sha256_file(path),
            }
        )
    existing = sorted(path.name for path in episode_dir.glob("*.json"))
    expected_existing = [
        f"{item['sequence']:08d}-{item['trial_id']}.json" for item in completed
    ]
    if existing != expected_existing:
        raise ArtifactIntegrityError("episode directory is not a contiguous plan prefix")
    root = sha256_text(canonical_json(completed))
    return {
        "schema_version": "1.0",
        "contract_sha256": contract_sha256,
        "completed_trials": len(completed),
        "next_sequence": len(completed) + 1,
        "completed": completed,
        "completed_root_sha256": root,
    }


def _write_checkpoint(
    root: Path,
    contract_sha256: str,
    trial_ids: tuple[str, ...],
    episode_dir: Path,
) -> tuple[dict[str, Any], str]:
    checkpoint = _checkpoint_payload(contract_sha256, trial_ids, episode_dir)
    checkpoint_sha256 = _atomic_json(root / "checkpoint.json", checkpoint)
    marker = os.environ.get("COTCODEC_CHECKPOINT_MARKER")
    if marker:
        marker_path = Path(marker)
        marker_path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_json(
            marker_path,
            {
                "schema_version": "1.0",
                "checkpoint_sha256": checkpoint_sha256,
                "completed_trials": checkpoint["completed_trials"],
            },
        )
    return checkpoint, checkpoint_sha256


def _load_checkpoint(
    root: Path,
    contract_sha256: str,
    trial_ids: tuple[str, ...],
    episode_dir: Path,
) -> tuple[dict[str, Any], str]:
    path = root / "checkpoint.json"
    if not path.is_file():
        raise ArtifactIntegrityError("resume root has no checkpoint")
    actual = _read_json(path)
    expected = _checkpoint_payload(contract_sha256, trial_ids, episode_dir)
    if actual != expected:
        raise ArtifactIntegrityError("checkpoint does not match sealed episode files")
    return actual, _sha256_file(path)


def _validate_existing_assignment(path: Path, expected: Mapping[str, Any]) -> None:
    actual = _read_json(path)
    if actual != expected:
        raise ArtifactIntegrityError(f"committed assignment changed on resume: {path}")


def _episode_payload(
    plan: TrialPlan,
    world: TrialWorld,
    trial_id: str,
    sequence: int,
    assignment_path: Path,
    replay_failure_path: Path,
) -> dict[str, Any]:
    prepared = world.prepare(trial_id)
    permuted = world.prepare_suffix_permutation(trial_id)
    validate_prepared_for_plan(plan, prepared, permuted)
    if prepared.trial_id != trial_id:
        raise TrialContractError("world returned the wrong prepared trial")
    assignment, served, replay_key = make_assignment_receipt(
        plan,
        prepared,
        sequence=sequence,
    )
    if assignment_path.exists():
        _validate_existing_assignment(assignment_path, assignment)
    else:
        _atomic_json(assignment_path, assignment)
    visibility: Literal["serve", "holdout"] = "serve" if served else "holdout"
    observed = world.continue_from(prepared, visibility, replay_key)
    validate_trial_outcome(prepared, observed, replay_key, visibility)
    audit: dict[str, Any] | None = None
    if trial_id in plan.paired_audit_ids:
        repeated = world.continue_from(prepared, visibility, replay_key)
        validate_trial_outcome(prepared, repeated, replay_key, visibility)
        validate_paired_trial(observed, repeated)
        if repeated != observed:
            failure = {
                "schema_version": "1.0",
                "kind": "same-arm-aa-mismatch",
                "trial_id": trial_id,
                "sequence": sequence,
                "assignment": assignment,
                "prepared": prepared.model_dump(mode="json"),
                "first": observed.model_dump(mode="json"),
                "repeated": repeated.model_dump(mode="json"),
                "comparison": {
                    "utility_equal": observed.utility == repeated.utility,
                    "success_equal": observed.success == repeated.success,
                    "safety_equal": (
                        observed.safety_failure == repeated.safety_failure
                    ),
                    "prompt_equal": observed.prompt_sha256 == repeated.prompt_sha256,
                    "memory_frame_equal": (
                        observed.memory_frame_sha256
                        == repeated.memory_frame_sha256
                    ),
                    "model_output_equal": (
                        observed.model_output_sha256
                        == repeated.model_output_sha256
                    ),
                    "tool_trace_equal": (
                        observed.tool_trace_sha256 == repeated.tool_trace_sha256
                    ),
                    "model_receipt_equal": (
                        observed.model_receipt_sha256
                        == repeated.model_receipt_sha256
                    ),
                },
            }
            receipt = _atomic_json(replay_failure_path, failure)
            raise TrialContractError(
                "same-arm A/A replay changed the outcome; "
                f"diagnostic_sha256={receipt}"
            )
        opposite: Literal["serve", "holdout"] = (
            "holdout" if visibility == "serve" else "serve"
        )
        counterfactual = world.continue_from(prepared, opposite, replay_key)
        validate_trial_outcome(prepared, counterfactual, replay_key, opposite)
        validate_paired_trial(observed, counterfactual)
        served_outcome = observed if served else counterfactual
        held_out_outcome = counterfactual if served else observed
        audit = {
            "schema_version": "1.0",
            "trial_id": trial_id,
            "group_id": prepared.group_id,
            "snapshot_sha256": prepared.snapshot_sha256,
            "replay_key": replay_key,
            "same_arm_replay": repeated.model_dump(mode="json"),
            "served_outcome": served_outcome.model_dump(mode="json"),
            "held_out_outcome": held_out_outcome.model_dump(mode="json"),
            "first_use_serve_effect": served_outcome.utility - held_out_outcome.utility,
        }
    features = {
        name: feature.value for name, feature in sorted(prepared.features.items())
    }
    lineage = {
        name: {
            "source_event": feature.source_event,
            "source_field": feature.source_field,
            "observed_step": feature.observed_step,
        }
        for name, feature in sorted(prepared.features.items())
    }
    return {
        "schema_version": "1.0",
        "sequence": sequence,
        "trial_id": trial_id,
        "prepared": prepared.model_dump(mode="json"),
        "feature_audit": {
            "schema_version": "1.0",
            "trial_id": trial_id,
            "session_id": prepared.session_id,
            "candidate_id": prepared.candidate_id,
            "write_step": prepared.write_step,
            "eligibility_step": prepared.eligibility_step,
            "prefix_digest": prepared.prefix_digest,
            "features": features,
            "lineage": lineage,
            "snapshot_sha256": prepared.snapshot_sha256,
        },
        "assignment": assignment,
        "observed": {
            "schema_version": "1.0",
            "trial_id": trial_id,
            "group_id": prepared.group_id,
            "snapshot_sha256": prepared.snapshot_sha256,
            "features": features,
            "served": served,
            "propensity_serve": plan.propensity,
            "outcome": observed.model_dump(mode="json"),
        },
        "audit": audit,
    }


def _compile_bundle(
    root: Path,
    plan: TrialPlan,
    world: TrialWorld,
    contract: Mapping[str, Any],
    episode_dir: Path,
) -> TrialBundle:
    bundle_root = root / "bundle"
    if bundle_root.exists():
        manifest_path = bundle_root / "manifest.json"
        if not manifest_path.is_file():
            raise ArtifactIntegrityError("partial compiled bundle exists")
        return TrialBundle(root=bundle_root, manifest_sha256=_sha256_file(manifest_path))
    bundle_root.mkdir()
    _fsync_dir(root)
    episodes = [
        _read_json(episode_dir / f"{sequence:08d}-{trial_id}.json")
        for sequence, trial_id in enumerate(plan.trial_ids, start=1)
    ]
    assignments = [episode["assignment"] for episode in episodes]
    observed = [episode["observed"] for episode in episodes]
    audits = [episode["audit"] for episode in episodes if episode["audit"] is not None]
    prepared = [episode["prepared"] for episode in episodes]
    features = [episode["feature_audit"] for episode in episodes]
    rows_by_name = {
        "assignment_journal.jsonl": assignments,
        "observed_trials.jsonl": observed,
        "paired_audit.jsonl": audits,
        "prepared_trials.jsonl": prepared,
        "feature_audits.jsonl": features,
    }
    files = {
        name: _atomic_jsonl(bundle_root / name, rows)
        for name, rows in rows_by_name.items()
    }
    manifest = {
        "schema_version": "1.0",
        "study_id": plan.study_id,
        "status": "COMPLETE",
        "world_identity": world.identity,
        "world_provenance": dict(contract["world_provenance"]),
        "runtime": {
            "python": sys.version,
            "numpy": importlib.metadata.version("numpy"),
            "pydantic": importlib.metadata.version("pydantic"),
            "scipy": importlib.metadata.version("scipy"),
            "collector": "memory-episode-transactions-v1",
        },
        "plan": _plan_payload(plan),
        "plan_sha256": contract["plan_sha256"],
        "files": files,
        "observed_trials": len(plan.trial_ids),
        "paired_audits": len(plan.paired_audit_ids),
    }
    manifest_path = bundle_root / "manifest.json"
    manifest_sha256 = _atomic_json(manifest_path, manifest)
    return TrialBundle(root=bundle_root, manifest_sha256=manifest_sha256)


def collect_resumable(
    plan: TrialPlan,
    world: TrialWorld,
    root: Path,
    *,
    resume: bool = False,
    stop_after: int | None = None,
    stop_requested: Callable[[], bool] | None = None,
) -> CollectionResult:
    """Collect one atomic episode at a time and compile the legacy analysis bundle."""

    root = root.resolve()
    contract = _contract(plan, world)
    contract_sha256 = sha256_text(canonical_json(contract))
    contract_path = root / "contract.json"
    assignment_dir = root / "assignments"
    episode_dir = root / "episodes"
    failure_dir = root / "failures"
    if not root.exists():
        root.mkdir(parents=True)
        assignment_dir.mkdir()
        episode_dir.mkdir()
        failure_dir.mkdir()
        _fsync_dir(root.parent)
        _fsync_dir(root)
        _atomic_json(contract_path, contract)
    elif not resume:
        raise ArtifactIntegrityError(f"collection root already exists: {root}")
    if (
        not contract_path.is_file()
        or not assignment_dir.is_dir()
        or not episode_dir.is_dir()
        or not failure_dir.is_dir()
    ):
        raise ArtifactIntegrityError("resume root is missing collection structure")
    if _read_json(contract_path) != contract:
        raise ArtifactIntegrityError("resume contract does not match plan/world identity")

    if resume:
        checkpoint, checkpoint_sha256 = _load_checkpoint(
            root,
            contract_sha256,
            plan.trial_ids,
            episode_dir,
        )
    else:
        checkpoint, checkpoint_sha256 = _write_checkpoint(
            root,
            contract_sha256,
            plan.trial_ids,
            episode_dir,
        )
    completed = int(checkpoint["completed_trials"])
    processed_this_call = 0
    for sequence, trial_id in enumerate(plan.trial_ids, start=1):
        episode_path = episode_dir / f"{sequence:08d}-{trial_id}.json"
        assignment_path = assignment_dir / f"{sequence:08d}-{trial_id}.json"
        if sequence <= completed:
            episode = _read_json(episode_path)
            if episode.get("sequence") != sequence or episode.get("trial_id") != trial_id:
                raise ArtifactIntegrityError("checkpointed episode order changed")
            continue
        replay_failure_path = failure_dir / f"{sequence:08d}-{trial_id}.json"
        episode = _episode_payload(
            plan,
            world,
            trial_id,
            sequence,
            assignment_path,
            replay_failure_path,
        )
        _atomic_json(episode_path, episode)
        processed_this_call += 1
        checkpoint, checkpoint_sha256 = _write_checkpoint(
            root,
            contract_sha256,
            plan.trial_ids,
            episode_dir,
        )
        if (stop_after is not None and processed_this_call >= stop_after) or (
            stop_requested is not None and stop_requested()
        ):
            return CollectionResult(
                status="CHECKPOINTED",
                root=root,
                checkpoint_sha256=checkpoint_sha256,
                completed_trials=int(checkpoint["completed_trials"]),
            )
    bundle = _compile_bundle(root, plan, world, contract, episode_dir)
    return CollectionResult(
        status="COMPLETE",
        root=root,
        checkpoint_sha256=checkpoint_sha256,
        completed_trials=len(plan.trial_ids),
        bundle=bundle,
    )
