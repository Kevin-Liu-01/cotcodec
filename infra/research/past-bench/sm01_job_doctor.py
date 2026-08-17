#!/usr/bin/env python3
"""Validate and seal one contained PAST-Bench SM01 checkpoint cell."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

STATUS = "COMPILED_PAST_SM01_CHECKPOINT_DISCOVERY_ONLY"
PAST_IMAGE_ID = "sha256:ebcf7eea7f1977f03e5e007edf265fcd120edadcd6d48e81f63df70715783150"
PAST_SBOM_SHA256 = "37f7eb4eab884c7d924e718f9ed8389102a61fe43b36d48e29249996bf857fff"
VLLM_IMAGE_ID = "sha256:f26809eb13339cbc59c3d0cc972f8c4997830dc8d2121cf18089cb122834e10d"
VLLM_SBOM_SHA256 = "3b87e628da75256fa7cfc0c33377af62707775a3606cf9be8c044e81952dcb48"
MODEL_ID = "qwen3.6-35b-a3b"
MODEL_REVISION = "995ad96eacd98c81ed38be0c5b274b04031597b0"
MODEL_RECEIPT_SHA256 = "18c2a12881bf613c7110439b8e765ff89a4c060a1fb60aee62bb7250890ce1f9"
MODEL_ARTIFACT_ROOT = "8ac6d764b84034f4ed0df3f2388c9180afceab806f7e75f5d1e43a73bdd2736b"
SEQUENCE_PATH = Path(
    "/opt/past-bench/source/configs/self_evolve_v2/"
    "hermes_self_evolve_v2_sm01_preference_adoption_only.yaml"
)
SEQUENCE_SHA256 = "6a311daff3ab1dc5f800ac0adb300f7b6ed5f6e37ba23d2f0b1e96516b719c60"
RUNTIME_CONFIG_PATH = "/tools/infra/research/past-bench/sm01-runtime.yaml"
RUNTIME_CONFIG_SHA256 = "0ddb0e8480b2f3005db4cf28b5b277736faafff8f0497b5658afe65a6fa2745a"
TASK_IDS = [
    "SM01_COLD_001",
    "SM01_LEARN_A_001",
    "SM01_LEARN_B_001",
    "SM01_EVAL_NEAR_001",
    "SM01_EVAL_FAR_001",
    "SM01_CONTROL_002",
    "SM01_CONTROL_001",
    "SM01_CONTROL_003",
]
MODES = {"uninterrupted", "stop-after-episode-three", "fresh-job-resume"}
CONTROLLED_STOP_STATUS = "PAST_SM01_CONTROLLED_STOP_CHECKPOINT_PASS"
RECOVERED_STOP_STATUS = (
    "PAST_SM01_CONTROLLED_STOP_CHECKPOINT_RECOVERED_AFTER_DOCTOR_FIX"
)
RECOVERED_RESUME_STATUS = "PAST_SM01_FRESH_RESUME_RECOVERED_AFTER_DOCTOR_FIX"
NONDETERMINISTIC_KEYS = {
    "created_at",
    "ended_at",
    "finished_at",
    "latency_ms",
    "request_id",
    "run_id",
    "session_id",
    "model_time_s",
    "other_time_s",
    "started_at",
    "timestamp",
    "tool_time_s",
    "trace_id",
    "wall_time_s",
}
SHA256_RE = re.compile(r"[0-9a-f]{64}")
LOGICAL_ARGV = [
    "/opt/past-bench-venv/bin/past-bench",
    "evolve",
    "--sequence",
    str(SEQUENCE_PATH),
    "--agent",
    "hermes-plus",
    "--model",
    MODEL_ID,
    "--api-key",
    "cotcodec-internal-transport",
    "--base-url",
    "http://past-qwen:8000/v1",
    "--runtime",
    "local",
    "--config",
    RUNTIME_CONFIG_PATH,
    "--temperature",
    "0",
    "--trace-dir",
    "/outputs/traces",
    "--no-judge",
    "--compare-no-persistence",
    "--background-review-wait-s",
    "5.0",
    "--checkpoint-dir",
    "/outputs/checkpoints",
    "--checkpoint-identity",
    "/inputs/execution-identity.json",
]
SERVER_ARGV = [
    "vllm",
    "serve",
    "/models/qwen3.6-35b-a3b",
    "--served-model-name",
    MODEL_ID,
    "--tensor-parallel-size",
    "2",
    "--dtype",
    "bfloat16",
    "--max-model-len",
    "32768",
    "--max-num-seqs",
    "1",
    "--seed",
    "42",
    "--enforce-eager",
    "--generation-config",
    "vllm",
    "--enable-auto-tool-choice",
    "--tool-call-parser",
    "qwen3_xml",
    "--chat-template",
    "/models/qwen3.6-35b-a3b/chat_template.jinja",
    "--default-chat-template-kwargs",
    '{"enable_thinking":false}',
    "--api-key",
    "cotcodec-internal-transport",
    "--host",
    "0.0.0.0",
    "--port",
    "8000",
]


class Sm01DoctorError(ValueError):
    """Raised when a PAST SM01 artifact violates its registered contract."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def _root(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fsync_dir(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_once(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _canonical(value) + b"\n"
    temporary = path.parent / f".{path.name}.{os.getpid()}.tmp"
    with temporary.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.link(temporary, path)
        _fsync_dir(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _read_object(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise Sm01DoctorError(f"{label} must be a regular non-symlink file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise Sm01DoctorError(f"{label} is invalid JSON") from exc
    if not isinstance(value, dict):
        raise Sm01DoctorError(f"{label} must contain one JSON object")
    return value


def _validate_manifest(path: Path, *, expected_sha256: str, mode: str) -> dict[str, Any]:
    manifest = _read_object(path, "SM01 manifest")
    stored = manifest.pop("manifest_sha256", None)
    actual = _root(manifest)
    if stored != expected_sha256 or actual != expected_sha256:
        raise Sm01DoctorError("SM01 manifest semantic digest drifted")
    if (
        manifest.get("schema_version") != 1
        or manifest.get("status") != STATUS
        or manifest.get("scientific_result") is not False
        or manifest.get("publication_ready") is not False
        or manifest.get("mode") != mode
    ):
        raise Sm01DoctorError("SM01 manifest header drifted")
    if mode not in MODES:
        raise Sm01DoctorError("SM01 run mode is invalid")
    past = manifest.get("past") or {}
    vllm = manifest.get("vllm") or {}
    model = manifest.get("model") or {}
    sequence = manifest.get("sequence") or {}
    containment = manifest.get("containment") or {}
    runtime_config = manifest.get("runtime_config") or {}
    if (
        past.get("image_id") != PAST_IMAGE_ID
        or past.get("sbom_sha256") != PAST_SBOM_SHA256
        or vllm.get("image_id") != VLLM_IMAGE_ID
        or vllm.get("sbom_sha256") != VLLM_SBOM_SHA256
        or model.get("id") != MODEL_ID
        or model.get("revision") != MODEL_REVISION
        or model.get("receipt_sha256") != MODEL_RECEIPT_SHA256
        or model.get("artifact_root_sha256") != MODEL_ARTIFACT_ROOT
        or model.get("trust_remote_code") is not False
        or sequence.get("path") != str(SEQUENCE_PATH)
        or sequence.get("sha256") != SEQUENCE_SHA256
        or sequence.get("task_ids") != TASK_IDS
        or containment
        != {
            "scheduler": "slurm",
            "gpu_type": "H100",
            "gpus": 2,
            "docker_network": "internal-no-external-egress",
            "pull_at_runtime": False,
            "sudo": False,
        }
        or runtime_config
        != {
            "path": RUNTIME_CONFIG_PATH,
            "sha256": RUNTIME_CONFIG_SHA256,
            "cache_dir": "/state/runtime_cache",
        }
    ):
        raise Sm01DoctorError("SM01 registered artifact or containment binding drifted")
    identity = manifest.get("execution_identity")
    if (
        not isinstance(identity, dict)
        or manifest.get("logical_workload_argv") != LOGICAL_ARGV
        or identity.get("argv") != LOGICAL_ARGV
        or manifest.get("server_argv") != SERVER_ARGV
    ):
        raise Sm01DoctorError("SM01 execution identity drifted")
    if identity.get("experiment_sha256") != manifest.get("experiment_file_sha256"):
        raise Sm01DoctorError("SM01 experiment identity drifted")
    suffix = manifest.get("actual_control_argv_suffix")
    expected_suffix = (
        ["--stop-after-episode", "3"]
        if mode == "stop-after-episode-three"
        else ["--resume-checkpoint"]
        if mode == "fresh-job-resume"
        else []
    )
    if suffix != expected_suffix:
        raise Sm01DoctorError("SM01 control argv drifted")
    expected_budget = (
        {"minutes": 30, "max_gpu_hours": 1}
        if mode == "stop-after-episode-three"
        else {"minutes": 90, "max_gpu_hours": 3}
    )
    if manifest.get("budget") != expected_budget:
        raise Sm01DoctorError("SM01 mode budget drifted")
    experiment = manifest.get("experiment_contract") or {}
    source = experiment.get("source") or {}
    agent = experiment.get("agent") or {}
    experiment_model = experiment.get("model") or {}
    recovery = experiment.get("recovery") or {}
    execution = experiment.get("execution") or {}
    if (
        experiment.get("name") != "stage-b-past-sm01-checkpoint"
        or experiment.get("scientific_result") is not False
        or source.get("expected_task_ids") != TASK_IDS
        or source.get("sequence_sha256") != SEQUENCE_SHA256
        or agent.get("runtime") != "local-inside-outer-container"
        or agent.get("runtime_config") != RUNTIME_CONFIG_PATH
        or agent.get("runtime_cache") != "/state/runtime_cache"
        or experiment_model.get("id") != MODEL_ID
        or experiment_model.get("revision") != MODEL_REVISION
        or experiment_model.get("temperature") != 0.0
        or experiment_model.get("generation_config") != "vllm-defaults"
        or experiment_model.get("judge") != "disabled"
        or recovery.get("controlled_stop_after_episode") != 3
        or recovery.get("resume_job_must_be_fresh") is not True
        or execution.get("prior_failed_contained_runtime_gpu_hours") != 0.451111
        or execution.get("total_max_gpu_hours") != 7.5
        or execution.get("sudo") != "forbidden"
    ):
        raise Sm01DoctorError("SM01 embedded experiment contract drifted")
    return {**manifest, "manifest_sha256": stored}


def _validate_sequence() -> dict[str, Any]:
    if not SEQUENCE_PATH.is_file() or SEQUENCE_PATH.is_symlink():
        raise Sm01DoctorError("registered SM01 sequence is missing")
    if _sha256(SEQUENCE_PATH) != SEQUENCE_SHA256:
        raise Sm01DoctorError("registered SM01 sequence bytes drifted")
    try:
        sequence = yaml.safe_load(SEQUENCE_PATH.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise Sm01DoctorError("registered SM01 sequence is invalid YAML") from exc
    episodes = sequence.get("episodes") if isinstance(sequence, dict) else None
    if not isinstance(episodes, list) or len(episodes) != 8:
        raise Sm01DoctorError("registered SM01 episode roster drifted")
    task_ids: list[str] = []
    rows: list[dict[str, Any]] = []
    for index, episode in enumerate(episodes, start=1):
        if not isinstance(episode, dict) or not isinstance(episode.get("task"), str):
            raise Sm01DoctorError("registered SM01 episode is malformed")
        task_dir = (SEQUENCE_PATH.parent / episode["task"]).resolve()
        task_yaml = task_dir / "task.yaml"
        try:
            task = yaml.safe_load(task_yaml.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise Sm01DoctorError("registered SM01 task is invalid") from exc
        task_id = task.get("task_id") if isinstance(task, dict) else None
        if not isinstance(task_id, str):
            raise Sm01DoctorError("registered SM01 task ID is invalid")
        task_ids.append(task_id)
        rows.append(
            {
                "index": index,
                "task_id": task_id,
                "task_yaml_sha256": _sha256(task_yaml),
                "label": episode.get("label"),
                "bucket": episode.get("bucket"),
                "stage": episode.get("stage"),
            }
        )
    if task_ids != TASK_IDS:
        raise Sm01DoctorError("registered SM01 ordered task IDs drifted")
    return {"sequence_sha256": SEQUENCE_SHA256, "episodes": rows, "episode_root": _root(rows)}


def _safe_relative(path: Path, root: Path) -> str:
    relative = path.relative_to(root)
    pure = PurePosixPath(relative.as_posix())
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise Sm01DoctorError("unsafe trace artifact path")
    return pure.as_posix()


def _prefix_manifest(trace_root: Path, completed_episode: int) -> list[dict[str, Any]]:
    prefixes = tuple(f"{index:02d}_" for index in range(1, completed_episode + 1))
    rows: list[dict[str, Any]] = []
    for path in sorted(trace_root.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise Sm01DoctorError("trace prefix contains a symlink")
        if not path.is_file():
            continue
        relative = _safe_relative(path, trace_root)
        if not any(part.startswith(prefixes) for part in PurePosixPath(relative).parts):
            continue
        rows.append({"path": relative, "size": path.stat().st_size, "sha256": _sha256(path)})
    if not rows:
        raise Sm01DoctorError("completed checkpoint has no episode-prefix artifacts")
    return rows


def _validate_preserved_prefix(
    before: Any, after: list[dict[str, Any]]
) -> None:
    """Require every predecessor prefix artifact to survive byte-for-byte.

    A resumed full run legitimately adds the no-persistence arm's episode-one to
    episode-three files, so equality of the entire later prefix roster would be
    too strict. Only predecessor paths are immutable.
    """
    if not isinstance(before, list) or not before:
        raise Sm01DoctorError("resume predecessor prefix is empty or invalid")
    after_by_path = {
        row.get("path"): row for row in after if isinstance(row, dict)
    }
    if len(after_by_path) != len(after):
        raise Sm01DoctorError("resume prefix contains duplicate paths")
    for row in before:
        if not isinstance(row, dict) or after_by_path.get(row.get("path")) != row:
            raise Sm01DoctorError("resume modified a completed episode-prefix artifact")


def _reject_future_episode_artifacts(trace_root: Path, completed_episode: int) -> None:
    future_prefixes = tuple(
        f"{index:02d}_" for index in range(completed_episode + 1, len(TASK_IDS) + 1)
    )
    for path in sorted(trace_root.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise Sm01DoctorError("controlled-stop trace tree contains a symlink")
        relative = _safe_relative(path, trace_root)
        if any(
            part.startswith(future_prefixes)
            for part in PurePosixPath(relative).parts
        ):
            raise Sm01DoctorError(
                "controlled stop contains a post-checkpoint episode artifact"
            )


def _tree_manifest(root: Path) -> list[dict[str, Any]]:
    if not root.is_dir() or root.is_symlink():
        raise Sm01DoctorError("checkpoint payload must be a regular directory")
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise Sm01DoctorError("checkpoint payload contains a symlink")
        relative = _safe_relative(path, root)
        mode = path.stat().st_mode & 0o7777
        if path.is_dir():
            rows.append({"path": relative, "kind": "directory", "mode": mode})
        elif path.is_file():
            rows.append(
                {
                    "path": relative,
                    "kind": "file",
                    "mode": mode,
                    "size": path.stat().st_size,
                    "sha256": _sha256(path),
                }
            )
        else:
            raise Sm01DoctorError("checkpoint payload contains a special file")
    return rows


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _normalize(item)
            for key, item in sorted(value.items())
            if key not in NONDETERMINISTIC_KEYS
            and not key.endswith("_time_s")
            and not key.endswith("_timestamp")
        }
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, str):
        return value.replace("/outputs/", "<OUTPUT>/").replace("/state/", "<STATE>/")
    return value


def _trace_projection(trace_root: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in sorted(trace_root.rglob("*.jsonl"), key=lambda item: item.as_posix()):
        if path.is_symlink() or not path.is_file():
            raise Sm01DoctorError("trace JSONL must be a regular non-symlink file")
        events: list[Any] = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise Sm01DoctorError(
                    f"trace JSONL is invalid at {path}:{line_number}"
                ) from exc
            events.append(_normalize(event))
        if not events:
            raise Sm01DoctorError(f"trace JSONL is empty: {path}")
        relative_parent = _safe_relative(path.parent, trace_root)
        rows.append(
            {
                "path": f"{relative_parent}/<trace>.jsonl",
                "event_count": len(events),
                "events_sha256": _root(events),
            }
        )
    if not rows:
        raise Sm01DoctorError("SM01 run produced no trace JSONL files")
    return {"trace_count": len(rows), "traces": rows, "projection_root_sha256": _root(rows)}


def _validate_episode_results(
    episodes: Any, *, expected_task_ids: list[str], label: str
) -> list[dict[str, Any]]:
    if not isinstance(episodes, list) or len(episodes) != len(expected_task_ids):
        raise Sm01DoctorError(f"{label} episode count drifted")
    normalized: list[dict[str, Any]] = []
    for expected_task_id, episode in zip(expected_task_ids, episodes, strict=True):
        if not isinstance(episode, dict) or episode.get("task_id") != expected_task_id:
            raise Sm01DoctorError(f"{label} ordered task IDs drifted")
        score = episode.get("task_score")
        if (
            episode.get("infra_blocked") is True
            or not isinstance(score, (int, float))
            or isinstance(score, bool)
            or not math.isfinite(float(score))
            or not isinstance(episode.get("passed"), bool)
        ):
            raise Sm01DoctorError(f"{label} contains an invalid or infra-blocked episode")
        normalized.append(episode)
    return normalized


def _validate_registered_reflection(reflection: Any, *, label: str) -> dict[str, Any]:
    score = reflection.get("task_score") if isinstance(reflection, dict) else None
    if (
        not isinstance(reflection, dict)
        or reflection.get("episode_kind") != "reflection"
        or reflection.get("task_id") != f"{TASK_IDS[2]}_REFLECT"
        or reflection.get("index") != "3r"
        or reflection.get("bucket") != "reflection"
        or reflection.get("stage") != "reflection"
        or reflection.get("infra_blocked") is True
        or not isinstance(score, (int, float))
        or isinstance(score, bool)
        or not math.isfinite(float(score))
        or not isinstance(reflection.get("passed"), bool)
    ):
        raise Sm01DoctorError(f"{label} reflection contract drifted")
    return reflection


def _validate_controlled_stop_results(episodes: Any) -> list[dict[str, Any]]:
    """Validate three primary episodes plus the registered episode-three reflection."""
    if not isinstance(episodes, list) or len(episodes) != 4:
        raise Sm01DoctorError("controlled stop episode count drifted")
    primary = _validate_episode_results(
        episodes[:3], expected_task_ids=TASK_IDS[:3], label="controlled stop"
    )
    _validate_registered_reflection(episodes[3], label="controlled stop")
    return primary


def _validate_complete_episode_results(
    episodes: Any, *, label: str
) -> list[dict[str, Any]]:
    """Validate eight primaries and the registered reflection after episode three."""
    if not isinstance(episodes, list) or len(episodes) != 9:
        raise Sm01DoctorError(f"{label} episode count drifted")
    primary = [*episodes[:3], *episodes[4:]]
    normalized = _validate_episode_results(
        primary, expected_task_ids=TASK_IDS, label=label
    )
    _validate_registered_reflection(episodes[3], label=label)
    return normalized


def _validate_complete_results(run_root: Path) -> dict[str, str]:
    roots: dict[str, str] = {}
    for variant in ("with_persistence", "without_persistence"):
        path = run_root / "traces" / variant / "sequence_results.json"
        payload = _read_object(path, f"{variant} sequence results")
        if payload.get("variant") != variant:
            raise Sm01DoctorError(f"{variant} sequence result label drifted")
        _validate_complete_episode_results(payload.get("episodes"), label=variant)
        roots[variant] = _sha256(path)
    return roots


def _load_checkpoint_state(
    run_root: Path, evidence_root: Path
) -> tuple[dict[str, Any], str]:
    checkpoint_root = run_root / "checkpoints"
    pointer_path = checkpoint_root / "LATEST"
    pointer = _read_object(pointer_path, "checkpoint pointer")
    if set(pointer) != {"generation", "receipt_sha256"}:
        raise Sm01DoctorError("checkpoint pointer schema drifted")
    name = pointer.get("generation")
    if not isinstance(name, str) or not name.startswith("generation-") or "/" in name:
        raise Sm01DoctorError("checkpoint generation pointer is invalid")
    generation = checkpoint_root / name
    receipt = _read_object(generation / "receipt.json", "checkpoint receipt")
    state = _read_object(generation / "state.json", "checkpoint state")
    manifest_path = generation / "payload-manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise Sm01DoctorError("checkpoint payload manifest is missing or unsafe")
    try:
        payload_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise Sm01DoctorError("checkpoint payload manifest is invalid") from exc
    if not isinstance(payload_manifest, list):
        raise Sm01DoctorError("checkpoint payload manifest must be a list")
    unsigned = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    if receipt.get("receipt_sha256") != _root(unsigned):
        raise Sm01DoctorError("checkpoint receipt self-digest is invalid")
    if pointer.get("receipt_sha256") != receipt.get("receipt_sha256"):
        raise Sm01DoctorError("checkpoint pointer and receipt differ")
    if receipt.get("state_sha256") != _root(state):
        raise Sm01DoctorError("checkpoint state digest is invalid")
    identity = _read_object(evidence_root / "execution-identity.json", "execution identity")
    if receipt.get("identity") != identity or receipt.get("identity_sha256") != _root(
        identity
    ):
        raise Sm01DoctorError("checkpoint execution identity drifted")
    if receipt.get("payload_manifest_sha256") != _root(payload_manifest):
        raise Sm01DoctorError("checkpoint payload manifest digest is invalid")
    if payload_manifest != _tree_manifest(generation / "payload"):
        raise Sm01DoctorError("checkpoint payload bytes differ from their manifest")
    if receipt.get("payload_file_count") != sum(
        row.get("kind") == "file" for row in payload_manifest
    ):
        raise Sm01DoctorError("checkpoint payload file count drifted")
    marker = _read_object(run_root / "checkpoint.ready", "checkpoint marker")
    if marker != {
        "generation": pointer["generation"],
        "receipt_sha256": pointer["receipt_sha256"],
    }:
        raise Sm01DoctorError("checkpoint marker and pointer differ")
    return state, _sha256(pointer_path)


def _snapshot_predecessor_checkpoint(
    run_root: Path, evidence_root: Path
) -> dict[str, Any]:
    pointer = _read_object(run_root / "checkpoints/LATEST", "checkpoint pointer")
    generation_name = pointer.get("generation")
    if (
        not isinstance(generation_name, str)
        or not generation_name.startswith("generation-")
        or "/" in generation_name
    ):
        raise Sm01DoctorError("predecessor checkpoint generation is invalid")
    source = run_root / "checkpoints" / generation_name
    source_manifest = _tree_manifest(source)
    destination = evidence_root / "predecessor-checkpoint"
    if destination.exists() or destination.is_symlink():
        raise Sm01DoctorError("predecessor checkpoint evidence already exists")
    shutil.copytree(source, destination, symlinks=False)
    for path in sorted(destination.rglob("*"), reverse=True):
        if path.is_file():
            descriptor = os.open(path, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        elif path.is_dir():
            _fsync_dir(path)
    _fsync_dir(destination)
    _fsync_dir(destination.parent)
    destination_manifest = _tree_manifest(destination)
    if destination_manifest != source_manifest:
        raise Sm01DoctorError("predecessor checkpoint evidence copy drifted")
    receipt = {
        "schema_version": 1,
        "status": "PAST_SM01_PREDECESSOR_CHECKPOINT_SNAPSHOTTED",
        "generation": generation_name,
        "checkpoint_receipt_sha256": pointer.get("receipt_sha256"),
        "manifest_sha256": _root(destination_manifest),
        "file_count": sum(row.get("kind") == "file" for row in destination_manifest),
    }
    _write_once(evidence_root / "predecessor-checkpoint-snapshot.json", receipt)
    return receipt


def preflight(
    *,
    manifest_path: Path,
    manifest_sha256: str,
    mode: str,
    run_root: Path,
    evidence_root: Path,
    slurm_job_id: int,
) -> dict[str, Any]:
    if SHA256_RE.fullmatch(manifest_sha256) is None or slurm_job_id <= 0:
        raise Sm01DoctorError("manifest digest is malformed")
    manifest = _validate_manifest(manifest_path, expected_sha256=manifest_sha256, mode=mode)
    sequence_receipt = _validate_sequence()
    identity = manifest["execution_identity"]
    identity_path = evidence_root / "execution-identity.json"
    if mode == "fresh-job-resume":
        existing_identity = _read_object(identity_path, "existing execution identity")
        if existing_identity != identity:
            raise Sm01DoctorError("resume execution identity drifted")
        state, pointer_sha256 = _load_checkpoint_state(run_root, evidence_root)
        predecessor = manifest.get("predecessor") or {}
        if predecessor.get("checkpoint_pointer_sha256") != pointer_sha256:
            raise Sm01DoctorError("resume predecessor checkpoint pointer drifted")
        predecessor_receipt = _read_object(
            evidence_root / "run-receipt-stop-after-episode-three.json",
            "controlled-stop receipt",
        )
        predecessor_unsigned = {
            key: value
            for key, value in predecessor_receipt.items()
            if key != "receipt_sha256"
        }
        status = predecessor_receipt.get("status")
        recovered_validation_job = predecessor_receipt.get("validation_slurm_job_id")
        if (
            predecessor_receipt.get("receipt_sha256") != _root(predecessor_unsigned)
            or status not in {CONTROLLED_STOP_STATUS, RECOVERED_STOP_STATUS}
            or predecessor_receipt.get("slurm_job_id")
            != predecessor.get("slurm_job_id")
            or predecessor_receipt.get("checkpoint_pointer_sha256") != pointer_sha256
            or predecessor_receipt.get("slurm_job_id") == slurm_job_id
        ):
            raise Sm01DoctorError("resume predecessor job receipt drifted")
        if status == RECOVERED_STOP_STATUS and (
            not isinstance(recovered_validation_job, int)
            or isinstance(recovered_validation_job, bool)
            or recovered_validation_job <= 0
            or recovered_validation_job
            in {predecessor_receipt.get("slurm_job_id"), slurm_job_id}
            or predecessor_receipt.get("recovery_reason")
            != "validator-counted-registered-reflection-as-primary-episode"
        ):
            raise Sm01DoctorError("recovered predecessor validation receipt drifted")
        completed = state.get("completed_episode")
        if state.get("stage") != "episode-complete" or completed != 3:
            raise Sm01DoctorError("resume checkpoint is not the registered episode-three stop")
        prefix = _prefix_manifest(run_root / "traces", completed)
        _write_once(evidence_root / "resume-prefix-before.json", prefix)
        predecessor_snapshot = _snapshot_predecessor_checkpoint(run_root, evidence_root)
    else:
        if identity_path.exists() or identity_path.is_symlink():
            raise Sm01DoctorError("new run execution identity already exists")
        _write_once(identity_path, identity)
        pointer_sha256 = ""
        predecessor_snapshot = None
    report = {
        "schema_version": 1,
        "status": "PAST_SM01_PREFLIGHT_PASS",
        "scientific_result": False,
        "mode": mode,
        "manifest_sha256": manifest_sha256,
        "execution_identity_sha256": _root(identity),
        "slurm_job_id": slurm_job_id,
        "sequence": sequence_receipt,
        "resume_checkpoint_pointer_sha256": pointer_sha256,
        "predecessor_checkpoint_snapshot": predecessor_snapshot,
    }
    _write_once(evidence_root / f"preflight-{mode}.json", report)
    return report


def finalize(
    *, mode: str, run_root: Path, evidence_root: Path, slurm_job_id: int
) -> dict[str, Any]:
    if mode not in MODES or slurm_job_id <= 0:
        raise Sm01DoctorError("finalization identity is invalid")
    state, pointer_sha256 = _load_checkpoint_state(run_root, evidence_root)
    if mode == "stop-after-episode-three":
        if (
            state.get("stage") != "episode-complete"
            or state.get("variant") != "with_persistence"
            or state.get("completed_episode") != 3
        ):
            raise Sm01DoctorError("controlled stop did not end at persistence episode three")
        _validate_controlled_stop_results(state.get("episode_results"))
        _reject_future_episode_artifacts(run_root / "traces", 3)
        result_roots: dict[str, str] = {}
        status = CONTROLLED_STOP_STATUS
    else:
        if state.get("stage") != "run-complete" or state.get("completed_episode") != 8:
            raise Sm01DoctorError("SM01 run did not seal a complete checkpoint")
        for relative in (
            "traces/with_persistence/sequence_summary.json",
            "traces/without_persistence/sequence_summary.json",
            "traces/sequence_comparison.json",
        ):
            path = run_root / relative
            if not path.is_file() or path.is_symlink():
                raise Sm01DoctorError(f"complete SM01 run is missing {relative}")
        result_roots = _validate_complete_results(run_root)
        status = (
            "PAST_SM01_FRESH_RESUME_PASS"
            if mode == "fresh-job-resume"
            else "PAST_SM01_UNINTERRUPTED_PASS"
        )
    projection = _trace_projection(run_root / "traces")
    _write_once(evidence_root / f"trace-projection-{mode}.json", projection)
    if mode == "fresh-job-resume":
        before = json.loads(
            (evidence_root / "resume-prefix-before.json").read_text(encoding="utf-8")
        )
        after = _prefix_manifest(run_root / "traces", 3)
        _validate_preserved_prefix(before, after)
    report = {
        "schema_version": 1,
        "status": status,
        "scientific_result": False,
        "publication_ready": False,
        "slurm_job_id": slurm_job_id,
        "mode": mode,
        "checkpoint_stage": state.get("stage"),
        "checkpoint_variant": state.get("variant"),
        "completed_episode": state.get("completed_episode"),
        "checkpoint_pointer_sha256": pointer_sha256,
        "trace_projection_root_sha256": projection["projection_root_sha256"],
        "trace_count": projection["trace_count"],
        "sequence_result_sha256": result_roots,
        "external_attestation": False,
    }
    unsigned = dict(report)
    report["receipt_sha256"] = _root(unsigned)
    _write_once(evidence_root / f"run-receipt-{mode}.json", report)
    return report


def recover_stop(
    *,
    run_root: Path,
    evidence_root: Path,
    workload_slurm_job_id: int,
    validation_slurm_job_id: int,
) -> dict[str, Any]:
    """Recover job 246's valid checkpoint after the original reflection-count bug."""
    if (
        workload_slurm_job_id <= 0
        or validation_slurm_job_id <= 0
        or workload_slurm_job_id == validation_slurm_job_id
    ):
        raise Sm01DoctorError("recovery Slurm identities are invalid")
    output_root = run_root.parent
    allocation = output_root / "allocation-stop-after-episode-three.txt"
    termination = evidence_root / "termination-stop-after-episode-three.txt"
    workload_stdout = evidence_root / "past-stop-after-episode-three.stdout"
    gpu_inventory = evidence_root / "gpu-inventory-stop-after-episode-three.txt"
    for path, label in (
        (allocation, "allocation"),
        (termination, "termination"),
        (workload_stdout, "workload stdout"),
        (gpu_inventory, "GPU inventory"),
    ):
        if not path.is_file() or path.is_symlink():
            raise Sm01DoctorError(f"recovery {label} evidence is missing or unsafe")
    allocation_text = allocation.read_text(encoding="utf-8")
    termination_text = termination.read_text(encoding="utf-8")
    stdout_text = workload_stdout.read_text(encoding="utf-8")
    gpu_lines = [
        line.strip()
        for line in gpu_inventory.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if (
        f"JobId={workload_slurm_job_id} " not in allocation_text
        or "TimeLimit=00:30:00" not in allocation_text
        or termination_text
        != "exit_code=1\ntermination_reason=running\nsignal_requested=false\n"
        or "CHECKPOINT_STOP variant=with_persistence completed_episode=3"
        not in stdout_text
        or len(gpu_lines) != 2
        or any("H100" not in line for line in gpu_lines)
    ):
        raise Sm01DoctorError("recovery evidence does not match the known validator failure")

    state, pointer_sha256 = _load_checkpoint_state(run_root, evidence_root)
    if (
        state.get("stage") != "episode-complete"
        or state.get("variant") != "with_persistence"
        or state.get("completed_episode") != 3
    ):
        raise Sm01DoctorError("recovered stop did not end at persistence episode three")
    _validate_controlled_stop_results(state.get("episode_results"))
    _reject_future_episode_artifacts(run_root / "traces", 3)
    projection = _trace_projection(run_root / "traces")
    _write_once(
        evidence_root / "trace-projection-stop-after-episode-three.json", projection
    )
    report = {
        "schema_version": 1,
        "status": RECOVERED_STOP_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "slurm_job_id": workload_slurm_job_id,
        "validation_slurm_job_id": validation_slurm_job_id,
        "mode": "stop-after-episode-three",
        "checkpoint_stage": state.get("stage"),
        "checkpoint_variant": state.get("variant"),
        "completed_episode": state.get("completed_episode"),
        "checkpoint_pointer_sha256": pointer_sha256,
        "trace_projection_root_sha256": projection["projection_root_sha256"],
        "trace_count": projection["trace_count"],
        "sequence_result_sha256": {},
        "recovery_reason": (
            "validator-counted-registered-reflection-as-primary-episode"
        ),
        "original_termination_sha256": _sha256(termination),
        "original_allocation_sha256": _sha256(allocation),
        "external_attestation": False,
    }
    unsigned = dict(report)
    report["receipt_sha256"] = _root(unsigned)
    _write_once(
        evidence_root / "run-receipt-stop-after-episode-three.json", report
    )
    return report


def recover_complete(
    *,
    run_root: Path,
    evidence_root: Path,
    workload_slurm_job_id: int,
    validation_slurm_job_id: int,
) -> dict[str, Any]:
    """Recover a valid fresh-resume run after the original reflection-count bug."""
    if (
        workload_slurm_job_id <= 0
        or validation_slurm_job_id <= 0
        or workload_slurm_job_id == validation_slurm_job_id
    ):
        raise Sm01DoctorError("recovery Slurm identities are invalid")
    output_root = run_root.parent
    allocation = output_root / "allocation-fresh-job-resume.txt"
    termination = evidence_root / "termination-fresh-job-resume.txt"
    workload_stdout = evidence_root / "past-fresh-job-resume.stdout"
    gpu_inventory = evidence_root / "gpu-inventory-fresh-job-resume.txt"
    for path, label in (
        (allocation, "allocation"),
        (termination, "termination"),
        (workload_stdout, "workload stdout"),
        (gpu_inventory, "GPU inventory"),
    ):
        if not path.is_file() or path.is_symlink():
            raise Sm01DoctorError(f"recovery {label} evidence is missing or unsafe")
    allocation_text = allocation.read_text(encoding="utf-8")
    termination_text = termination.read_text(encoding="utf-8")
    stdout_text = workload_stdout.read_text(encoding="utf-8")
    gpu_lines = [
        line.strip()
        for line in gpu_inventory.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if (
        f"JobId={workload_slurm_job_id} " not in allocation_text
        or "TimeLimit=01:30:00" not in allocation_text
        or termination_text
        != (
            "exit_code=1\ntermination_reason=artifact_finalization_failed\n"
            "signal_requested=false\n"
        )
        or "Summary [with_persistence]" not in stdout_text
        or "Summary [without_persistence]" not in stdout_text
        or "Comparison" not in stdout_text
        or len(gpu_lines) != 2
        or any("H100" not in line for line in gpu_lines)
    ):
        raise Sm01DoctorError("recovery evidence does not match the known validator failure")

    state, pointer_sha256 = _load_checkpoint_state(run_root, evidence_root)
    if state.get("stage") != "run-complete" or state.get("completed_episode") != 8:
        raise Sm01DoctorError("recovered SM01 run did not seal a complete checkpoint")
    for relative in (
        "traces/with_persistence/sequence_summary.json",
        "traces/without_persistence/sequence_summary.json",
        "traces/sequence_comparison.json",
    ):
        path = run_root / relative
        if not path.is_file() or path.is_symlink():
            raise Sm01DoctorError(f"recovered SM01 run is missing {relative}")
    result_roots = _validate_complete_results(run_root)
    before = json.loads(
        (evidence_root / "resume-prefix-before.json").read_text(encoding="utf-8")
    )
    after = _prefix_manifest(run_root / "traces", 3)
    _validate_preserved_prefix(before, after)
    projection = _trace_projection(run_root / "traces")
    _write_once(evidence_root / "trace-projection-fresh-job-resume.json", projection)
    report = {
        "schema_version": 1,
        "status": RECOVERED_RESUME_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "slurm_job_id": workload_slurm_job_id,
        "validation_slurm_job_id": validation_slurm_job_id,
        "mode": "fresh-job-resume",
        "checkpoint_stage": state.get("stage"),
        "checkpoint_variant": state.get("variant"),
        "completed_episode": state.get("completed_episode"),
        "checkpoint_pointer_sha256": pointer_sha256,
        "trace_projection_root_sha256": projection["projection_root_sha256"],
        "trace_count": projection["trace_count"],
        "sequence_result_sha256": result_roots,
        "recovery_reason": (
            "validator-counted-registered-reflection-as-primary-episode"
        ),
        "original_termination_sha256": _sha256(termination),
        "original_allocation_sha256": _sha256(allocation),
        "external_attestation": False,
    }
    unsigned = dict(report)
    report["receipt_sha256"] = _root(unsigned)
    _write_once(evidence_root / "run-receipt-fresh-job-resume.json", report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    pre = subparsers.add_parser("preflight")
    pre.add_argument("--manifest", type=Path, required=True)
    pre.add_argument("--manifest-sha256", required=True)
    pre.add_argument("--mode", choices=sorted(MODES), required=True)
    pre.add_argument("--run-root", type=Path, required=True)
    pre.add_argument("--evidence-root", type=Path, required=True)
    pre.add_argument("--slurm-job-id", type=int, required=True)
    final = subparsers.add_parser("finalize")
    final.add_argument("--mode", choices=sorted(MODES), required=True)
    final.add_argument("--run-root", type=Path, required=True)
    final.add_argument("--evidence-root", type=Path, required=True)
    final.add_argument("--slurm-job-id", type=int, required=True)
    recover = subparsers.add_parser("recover-stop")
    recover.add_argument("--run-root", type=Path, required=True)
    recover.add_argument("--evidence-root", type=Path, required=True)
    recover.add_argument("--workload-slurm-job-id", type=int, required=True)
    recover.add_argument("--validation-slurm-job-id", type=int, required=True)
    recover_complete_parser = subparsers.add_parser("recover-complete")
    recover_complete_parser.add_argument("--run-root", type=Path, required=True)
    recover_complete_parser.add_argument("--evidence-root", type=Path, required=True)
    recover_complete_parser.add_argument(
        "--workload-slurm-job-id", type=int, required=True
    )
    recover_complete_parser.add_argument(
        "--validation-slurm-job-id", type=int, required=True
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "preflight":
            result = preflight(
                manifest_path=args.manifest,
                manifest_sha256=args.manifest_sha256,
                mode=args.mode,
                run_root=args.run_root,
                evidence_root=args.evidence_root,
                slurm_job_id=args.slurm_job_id,
            )
        elif args.command == "finalize":
            result = finalize(
                mode=args.mode,
                run_root=args.run_root,
                evidence_root=args.evidence_root,
                slurm_job_id=args.slurm_job_id,
            )
        elif args.command == "recover-stop":
            result = recover_stop(
                run_root=args.run_root,
                evidence_root=args.evidence_root,
                workload_slurm_job_id=args.workload_slurm_job_id,
                validation_slurm_job_id=args.validation_slurm_job_id,
            )
        else:
            result = recover_complete(
                run_root=args.run_root,
                evidence_root=args.evidence_root,
                workload_slurm_job_id=args.workload_slurm_job_id,
                validation_slurm_job_id=args.validation_slurm_job_id,
            )
    except Sm01DoctorError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
