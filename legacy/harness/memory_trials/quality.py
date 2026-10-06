"""Crash-resumable all-SERVE collection for standard memory-system quality."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from harness.causal_memory_trials import (
    TrialContractError,
    TrialOutcome,
    TrialWorld,
    validate_trial_outcome,
)
from harness.memory_trials.schema import canonical_json, sha256_text


class QualityCollectionError(ValueError):
    """Raised when an all-SERVE benchmark artifact violates its contract."""


@dataclass(frozen=True)
class QualityCollectionResult:
    status: Literal["CHECKPOINTED", "COMPLETE"]
    root: Path
    completed_tasks: int
    checkpoint_sha256: str
    bundle_root: Path | None = None
    bundle_manifest_sha256: str | None = None


def _fsync_dir(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
        raise QualityCollectionError(f"invalid quality artifact: {path}") from exc
    if not isinstance(payload, dict):
        raise QualityCollectionError(f"quality artifact must be an object: {path}")
    return payload


def _contract(
    world: TrialWorld,
    task_ids: tuple[str, ...],
    admission_contract: Mapping[str, Any] | None,
) -> dict[str, Any]:
    provenance = getattr(world, "provenance", None)
    if not isinstance(provenance, Mapping):
        raise TrialContractError("TrialWorld must expose a provenance mapping")
    payload = {
        "schema_version": "1.0",
        "mode": "all-serve-system-quality",
        "task_ids": list(task_ids),
        "world_identity": world.identity,
        "world_provenance": dict(provenance),
        "collector": "memory-all-serve-quality-v1",
        "admission_contract": (
            dict(admission_contract) if admission_contract is not None else None
        ),
    }
    return {**payload, "contract_sha256": sha256_text(canonical_json(payload))}


def _checkpoint(
    root: Path,
    episode_dir: Path,
    contract_sha256: str,
    task_ids: tuple[str, ...],
) -> tuple[dict[str, Any], str]:
    completed: list[dict[str, Any]] = []
    for sequence, task_id in enumerate(task_ids, start=1):
        path = episode_dir / f"{sequence:08d}-{task_id}.json"
        if not path.is_file():
            break
        completed.append(
            {"sequence": sequence, "task_id": task_id, "sha256": _sha256_file(path)}
        )
    expected = [
        f"{item['sequence']:08d}-{item['task_id']}.json" for item in completed
    ]
    if sorted(path.name for path in episode_dir.glob("*.json")) != expected:
        raise QualityCollectionError("quality episodes are not a contiguous task prefix")
    payload = {
        "schema_version": "1.0",
        "contract_sha256": contract_sha256,
        "completed_tasks": len(completed),
        "completed": completed,
        "completed_root_sha256": sha256_text(canonical_json(completed)),
    }
    return payload, _atomic_json(root / "checkpoint.json", payload)


def _episode(world: TrialWorld, task_id: str, sequence: int) -> dict[str, Any]:
    prepared = world.prepare(task_id)
    if prepared.trial_id != task_id:
        raise QualityCollectionError("world prepared a different task")
    replay_key = sha256_text(
        f"memory-all-serve-quality-v1:{sequence}:{task_id}:{prepared.snapshot_sha256}"
    )
    outcome = world.continue_from(prepared, "serve", replay_key)
    validate_trial_outcome(prepared, outcome, replay_key, "serve")
    return {
        "schema_version": "1.0",
        "sequence": sequence,
        "trial_id": task_id,
        "group_id": prepared.group_id,
        "prepared_sha256": sha256_text(
            canonical_json(prepared.model_dump(mode="json"))
        ),
        "outcome": outcome.model_dump(mode="json"),
    }


def _compile_bundle(
    root: Path,
    episode_dir: Path,
    contract: Mapping[str, Any],
    task_ids: tuple[str, ...],
) -> tuple[Path, str]:
    bundle_root = root / "bundle"
    if bundle_root.exists():
        manifest = bundle_root / "manifest.json"
        if not manifest.is_file():
            raise QualityCollectionError("partial quality bundle exists")
        return bundle_root, _sha256_file(manifest)
    bundle_root.mkdir()
    _fsync_dir(root)
    rows = [
        _read_json(episode_dir / f"{sequence:08d}-{task_id}.json")
        for sequence, task_id in enumerate(task_ids, start=1)
    ]
    observed_sha256 = _atomic_jsonl(bundle_root / "observed_trials.jsonl", rows)
    manifest = {
        "schema_version": "1.0",
        "status": "COMPLETE",
        "mode": "all-serve-system-quality",
        "scientific_result": False,
        "reason": "Sealed model outputs; semantic evaluation is a separate required stage.",
        "world_identity": contract["world_identity"],
        "world_provenance": contract["world_provenance"],
        "admission_contract": contract["admission_contract"],
        "plan": {
            "mode": "all-serve",
            "trial_ids": list(task_ids),
            "assignment_seed": None,
        },
        "contract_sha256": contract["contract_sha256"],
        "task_count": len(task_ids),
        "served_task_count": len(task_ids),
        "files": {"observed_trials.jsonl": observed_sha256},
    }
    manifest_sha256 = _atomic_json(bundle_root / "manifest.json", manifest)
    return bundle_root, manifest_sha256


def collect_all_serve(
    world: TrialWorld,
    task_ids: Sequence[str],
    root: Path,
    *,
    resume: bool = False,
    stop_after: int | None = None,
    stop_requested: Callable[[], bool] | None = None,
    admission_contract: Mapping[str, Any] | None = None,
) -> QualityCollectionResult:
    """Execute every registered task with memory served exactly once."""

    ordered_ids = tuple(task_ids)
    if not ordered_ids or len(set(ordered_ids)) != len(ordered_ids):
        raise QualityCollectionError("task_ids must be non-empty and unique")
    if stop_after is not None and stop_after < 1:
        raise QualityCollectionError("stop_after must be positive")
    root = root.resolve()
    contract = _contract(world, ordered_ids, admission_contract)
    contract_path = root / "contract.json"
    episode_dir = root / "episodes"
    if root.exists():
        if not resume:
            raise QualityCollectionError(f"quality output already exists: {root}")
        if _read_json(contract_path) != contract:
            raise QualityCollectionError("quality resume contract changed")
    else:
        root.mkdir(parents=True)
        episode_dir.mkdir()
        _fsync_dir(root.parent)
        _atomic_json(contract_path, contract)
    episode_dir.mkdir(exist_ok=True)
    checkpoint_path = root / "checkpoint.json"
    completed = 0
    if checkpoint_path.is_file():
        checkpoint = _read_json(checkpoint_path)
        expected, checkpoint_sha256 = _checkpoint(
            root, episode_dir, contract["contract_sha256"], ordered_ids
        )
        if checkpoint != expected:
            raise QualityCollectionError("quality checkpoint does not bind episodes")
        completed = int(checkpoint["completed_tasks"])
    else:
        _checkpoint(root, episode_dir, contract["contract_sha256"], ordered_ids)

    for sequence, task_id in enumerate(ordered_ids, start=1):
        path = episode_dir / f"{sequence:08d}-{task_id}.json"
        if sequence <= completed:
            continue
        _atomic_json(path, _episode(world, task_id, sequence))
        checkpoint, checkpoint_sha256 = _checkpoint(
            root, episode_dir, contract["contract_sha256"], ordered_ids
        )
        completed = int(checkpoint["completed_tasks"])
        if (stop_after is not None and completed >= stop_after) or (
            stop_requested is not None and stop_requested()
        ):
            return QualityCollectionResult(
                status="CHECKPOINTED",
                root=root,
                completed_tasks=completed,
                checkpoint_sha256=checkpoint_sha256,
            )

    bundle_root, manifest_sha256 = _compile_bundle(
        root, episode_dir, contract, ordered_ids
    )
    checkpoint_sha256 = _sha256_file(root / "checkpoint.json")
    return QualityCollectionResult(
        status="COMPLETE",
        root=root,
        completed_tasks=len(ordered_ids),
        checkpoint_sha256=checkpoint_sha256,
        bundle_root=bundle_root,
        bundle_manifest_sha256=manifest_sha256,
    )


def load_quality_outcomes(bundle_root: Path) -> tuple[TrialOutcome, ...]:
    """Verify and load a complete all-SERVE output bundle."""

    manifest = _read_json(bundle_root / "manifest.json")
    if manifest.get("status") != "COMPLETE" or manifest.get("mode") != (
        "all-serve-system-quality"
    ):
        raise QualityCollectionError("not a complete all-SERVE quality bundle")
    expected = manifest.get("files", {}).get("observed_trials.jsonl")
    observed_path = bundle_root / "observed_trials.jsonl"
    if not isinstance(expected, str) or _sha256_file(observed_path) != expected:
        raise QualityCollectionError("all-SERVE outcomes failed hash verification")
    rows = [
        json.loads(line)
        for line in observed_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != manifest.get("task_count"):
        raise QualityCollectionError("all-SERVE outcome count differs from manifest")
    outcomes = tuple(TrialOutcome.model_validate(row["outcome"]) for row in rows)
    if any(outcome.visibility != "serve" for outcome in outcomes):
        raise QualityCollectionError("all-SERVE bundle contains a holdout outcome")
    return outcomes
