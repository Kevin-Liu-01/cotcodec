#!/usr/bin/env python3
"""Run a bounded self-hosted frozen-model screen through the memory runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import signal
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.causal_memory_trials import TrialBundle, TrialPlan  # noqa: E402
from harness.memory_trials import (  # noqa: E402
    FrozenMemorySystem,
    GeneratedMemoryTaskSource,
    LongMemEvalTaskSource,
    MemoryBudget,
    MemoryTaskSource,
    ReplayableMemoryWorld,
    TransformersMemoryActor,
    collect_all_serve,
    collect_resumable,
    load_quality_outcomes,
    task_manifest_sha256,
)
from harness.memory_trials.schema import canonical_json, sha256_text  # noqa: E402
from harness.publication_attestation import (  # noqa: E402
    verify_publication_claim_attestation,
)
from scripts.compile_memory_public_docker_job import CONTROL_SYSTEMS  # noqa: E402
from scripts.fetch_open_model import (  # noqa: E402
    DEFAULT_MODEL_ROOT,
    DEFAULT_RECEIPT_ROOT,
    DEFAULT_REGISTRY,
    load_registry,
    receipt_path,
    verify_receipt,
)
from scripts.freeze_memory_system_outputs import (  # noqa: E402
    DEFAULT_LONGMEMEVAL_PATH,
    SYSTEM_IDENTITIES,
)
from scripts.run_memory_trials import ALLOWED_FEATURES, atomic_json, audit_ids  # noqa: E402
from scripts.validate_memory_experiments import validate_experiment_path  # noqa: E402

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PUBLICATION_BATCH_SCRIPT = PROJECT_ROOT / "infra/slurm/host-single-node/docker-research.sbatch"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _semantic_root(payload: dict[str, Any], field: str, owner: str) -> str:
    unsigned = dict(payload)
    expected = unsigned.pop(field, None)
    actual = sha256_text(canonical_json(unsigned))
    if not isinstance(expected, str) or expected != actual:
        raise ValueError(f"{owner} semantic root is invalid")
    return expected


def _load_publication_admission(
    *,
    capsule_path: Path,
    attestation_path: Path,
    trust_store_path: Path,
    expected_trust_store_sha256: str,
    matrix_path: Path,
    experiment_path: Path,
    wave_path: Path,
    expected_wave_sha256: str,
    expected_control_id: str,
    expected_system_id: str,
    frozen_memory: FrozenMemorySystem,
    exact_task_manifest_sha256: str,
    model_id: str,
    model_revision: str,
    model_receipt_sha256: str,
    model_artifact_root_sha256: str,
    registered_actor_contract: dict[str, Any],
) -> dict[str, Any]:
    if not SHA256_RE.fullmatch(expected_wave_sha256):
        raise ValueError("expected publication wave digest is invalid")
    try:
        capsule = json.loads(capsule_path.read_text(encoding="utf-8"))
        matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
        wave = json.loads(wave_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("publication admission inputs are unreadable") from exc
    if not all(isinstance(value, dict) for value in (capsule, matrix, wave)):
        raise ValueError("publication admission inputs must be JSON objects")
    capsule_sha256 = _semantic_root(capsule, "capsule_sha256", "publication capsule")
    attestation_receipt = verify_publication_claim_attestation(
        capsule_path=capsule_path,
        matrix_path=matrix_path,
        experiment_path=experiment_path,
        wave=wave,
        batch_script_path=PUBLICATION_BATCH_SCRIPT,
        attestation_path=attestation_path,
        trust_store_path=trust_store_path,
        expected_trust_store_sha256=expected_trust_store_sha256,
    )
    matrix_sha256 = _semantic_root(matrix, "matrix_sha256", "control matrix")
    wave_sha256 = _semantic_root(wave, "wave_sha256", "publication wave")
    if wave_sha256 != expected_wave_sha256:
        raise ValueError("publication wave semantic root differs from the command")
    if (
        capsule.get("schema_version") != 2
        or capsule.get("status") != "SEALED_PUBLICATION_CAPSULE_CANDIDATE"
        or capsule.get("publication_ready") is not False
    ):
        raise ValueError("publication capsule is not claim-ready")
    if matrix.get("status") != "FROZEN_CONTROL_MATRIX":
        raise ValueError("control matrix is not frozen")
    if (
        wave.get("publication_capsule_sha256") != capsule_sha256
        or wave.get("publication_capsule_file_sha256") != _sha256_file(capsule_path)
        or wave.get("control_matrix_sha256") != matrix_sha256
        or wave.get("control_matrix_file_sha256") != _sha256_file(matrix_path)
        or wave.get("model_id") != model_id
        or wave.get("model_revision") != model_revision
        or wave.get("model_receipt_sha256") != model_receipt_sha256
        or wave.get("model_artifact_root_sha256") != model_artifact_root_sha256
        or wave.get("registered_actor_contract") != registered_actor_contract
        or wave.get("command_schema") != "longmemeval-publication-actor-all-serve-v2"
        or wave.get("experiment_sha256") != _sha256_file(experiment_path)
        or wave.get("batch_script_sha256") != _sha256_file(PUBLICATION_BATCH_SCRIPT)
    ):
        raise ValueError("publication wave provenance differs from the actor runtime")
    task_source = matrix.get("task_source")
    if (
        not isinstance(task_source, dict)
        or task_source.get("task_manifest_sha256") != exact_task_manifest_sha256
    ):
        raise ValueError("control matrix task manifest differs from the actor source")
    matrix_controls = matrix.get("controls")
    if not isinstance(matrix_controls, list) or not all(
        isinstance(row, dict) for row in matrix_controls
    ):
        raise ValueError("control matrix roster is invalid")
    matrix_control_ids = [str(row.get("control_id")) for row in matrix_controls]
    if (
        len(matrix_control_ids) != len(set(matrix_control_ids))
        or set(matrix_control_ids) != set(CONTROL_SYSTEMS)
    ):
        raise ValueError("control matrix roster is incomplete or unregistered")
    access_identified = int(matrix.get("event_kind_counts", {}).get("access", 0)) > 0
    expected_eligible_ids = sorted(
        control_id
        for control_id in CONTROL_SYSTEMS
        if control_id != "reference" and (control_id != "lru" or access_identified)
    )
    expected_eligible_rows = []
    by_id = {str(row["control_id"]): row for row in matrix_controls}
    for control_id in expected_eligible_ids:
        row = by_id[control_id]
        registered_system_id = SYSTEM_IDENTITIES[control_id]
        expected_row = {
            "control_id": control_id,
            "system_id": registered_system_id,
            "bundle_semantic_sha256": row.get("bundle_semantic_sha256"),
            "bundle_file_sha256": row.get("bundle_file_sha256"),
        }
        if (
            row.get("eligible_for_primary") is not True
            or row.get("system_id") != registered_system_id
        ):
            raise ValueError(
                f"control matrix eligibility or system mapping drifted: {control_id}"
            )
        expected_eligible_rows.append(expected_row)
    if wave.get("eligible_controls") != expected_eligible_rows:
        raise ValueError("publication wave is not the complete registered eligible roster")
    matches = [
        row
        for row in matrix.get("controls", [])
        if isinstance(row, dict) and row.get("control_id") == expected_control_id
    ]
    if len(matches) != 1:
        raise ValueError("expected control is absent or duplicated in the matrix")
    control = matches[0]
    if (
        control.get("system_id") != expected_system_id
        or control.get("system_id") != frozen_memory.receipt.system_id
        or control.get("bundle_semantic_sha256") != frozen_memory.bundle_sha256
        or control.get("bundle_sha256") != frozen_memory.bundle_sha256
        or control.get("eligible_for_primary") is not True
    ):
        raise ValueError("actor memory bundle differs from its primary matrix cell")
    eligible_matches = [
        row
        for row in wave.get("eligible_controls", [])
        if isinstance(row, dict) and row.get("control_id") == expected_control_id
    ]
    if len(eligible_matches) != 1 or eligible_matches[0] != {
        "control_id": expected_control_id,
        "system_id": expected_system_id,
        "bundle_semantic_sha256": frozen_memory.bundle_sha256,
        "bundle_file_sha256": _sha256_file(frozen_memory.path),
    }:
        raise ValueError("publication wave does not bind the selected frozen control")
    source = capsule.get("source")
    image = capsule.get("image")
    if not isinstance(source, dict) or not isinstance(image, dict):
        raise ValueError("publication capsule lacks source or image identity")
    environment_checks = {
        "COTCODEC_GIT_SHA": source.get("git_sha"),
        "COTCODEC_SOURCE_SHA256": source.get("archive_sha256"),
    }
    for variable, expected in environment_checks.items():
        observed = os.environ.get(variable)
        if observed is not None and observed != expected:
            raise ValueError(f"{variable} differs from publication admission")
    return {
        "schema_version": 1,
        "capsule_sha256": capsule_sha256,
        "publication_attestation": attestation_receipt,
        "matrix_sha256": matrix_sha256,
        "wave_sha256": wave_sha256,
        "wave_file_sha256": _sha256_file(wave_path),
        "control_id": expected_control_id,
        "system_id": expected_system_id,
        "memory_bundle_semantic_sha256": frozen_memory.bundle_sha256,
        "task_manifest_sha256": exact_task_manifest_sha256,
        "image_id": image.get("image_id"),
        "git_sha": source.get("git_sha"),
        "source_sha256": source.get("archive_sha256"),
    }


def summarize_screen(bundle: TrialBundle) -> dict[str, Any]:
    assignments = _read_jsonl(bundle.root / "assignment_journal.jsonl")
    rows = _read_jsonl(bundle.root / "observed_trials.jsonl")
    if len(assignments) != len(rows):
        raise ValueError("assignment and outcome counts differ in the sealed bundle")
    schedule: list[dict[str, Any]] = []
    task_results: list[dict[str, Any]] = []
    for assignment, row in zip(assignments, rows, strict=True):
        if assignment["trial_id"] != row["trial_id"]:
            raise ValueError("assignment and outcome task order differs")
        outcome = row["outcome"]
        if assignment["visibility"] != outcome["visibility"]:
            raise ValueError("assignment and outcome visibility differs")
        schedule.append(
            {
                "sequence": assignment["sequence"],
                "trial_id": assignment["trial_id"],
                "candidate_id": assignment["candidate_id"],
                "prefix_digest": assignment["prefix_digest"],
                "snapshot_sha256": assignment["snapshot_sha256"],
                "visibility": assignment["visibility"],
                "propensity_serve": assignment["propensity_serve"],
                "draw_digest": assignment["draw_digest"],
            }
        )
        task_results.append(
            {
                "trial_id": row["trial_id"],
                "group_id": row["group_id"],
                "visibility": outcome["visibility"],
                "utility": outcome["utility"],
                "success": outcome["success"],
                "safety_failure": outcome["safety_failure"],
                "prompt_sha256": outcome["prompt_sha256"],
                "memory_frame_sha256": outcome["memory_frame_sha256"],
                "model_output_sha256": outcome["model_output_sha256"],
                "model_receipt_sha256": outcome["model_receipt_sha256"],
                "tool_trace_sha256": outcome["tool_trace_sha256"],
                "metrics": outcome["metrics"],
            }
        )
    outcomes = [row["outcome"] for row in rows]
    served = [outcome for outcome in outcomes if outcome["visibility"] == "serve"]
    valid_actions = 0
    bound_receipts = 0
    by_stratum: dict[str, dict[str, int]] = {}
    safety_cases: dict[str, dict[str, int]] = {}
    served_safety_failures = 0
    holdout_safety_failures = 0
    for outcome in outcomes:
        tool_trace = json.loads(outcome["tool_trace_json"])
        valid = tool_trace["actual"].get("mode") in {"answer", "tool"}
        if valid:
            valid_actions += 1
        receipt = json.loads(outcome["model_receipt_json"])
        if receipt:
            bound_receipts += 1
        memory_frame = json.loads(outcome["memory_frame_json"])
        stratum = str(memory_frame["stratum"])
        cell = by_stratum.setdefault(
            stratum,
            {"episodes": 0, "served_episodes": 0, "served_successes": 0, "valid_actions": 0},
        )
        cell["episodes"] += 1
        cell["valid_actions"] += int(valid)
        if outcome["visibility"] == "serve":
            cell["served_episodes"] += 1
            cell["served_successes"] += int(bool(outcome["success"]))
            served_safety_failures += int(bool(outcome["safety_failure"]))
        else:
            holdout_safety_failures += int(bool(outcome["safety_failure"]))
        safety_case = tool_trace.get("safety_case")
        if isinstance(safety_case, str):
            safety_cell = safety_cases.setdefault(
                safety_case,
                {
                    "episodes": 0,
                    "failures": 0,
                    "served_episodes": 0,
                    "served_failures": 0,
                    "holdout_episodes": 0,
                    "holdout_failures": 0,
                },
            )
            safety_cell["episodes"] += 1
            safety_cell["failures"] += int(bool(outcome["safety_failure"]))
            arm = "served" if outcome["visibility"] == "serve" else "holdout"
            safety_cell[f"{arm}_episodes"] += 1
            safety_cell[f"{arm}_failures"] += int(bool(outcome["safety_failure"]))
    count = len(outcomes)
    manifest = json.loads((bundle.root / "manifest.json").read_text(encoding="utf-8"))
    return {
        "episodes": count,
        "assignment_seed": int(manifest["plan"]["assignment_seed"]),
        "trial_plan_sha256": manifest["plan_sha256"],
        "assignment_journal_sha256": _sha256_file(bundle.root / "assignment_journal.jsonl"),
        "assignment_schedule": schedule,
        "assignment_schedule_sha256": sha256_text(canonical_json(schedule)),
        "task_results": task_results,
        "task_results_sha256": sha256_text(canonical_json(task_results)),
        "served_episodes": len(served),
        "valid_action_rate": valid_actions / count,
        "model_receipt_rate": bound_receipts / count,
        "served_oracle_success": (
            sum(bool(outcome["success"]) for outcome in served) / len(served) if served else 0.0
        ),
        "safety_failures": sum(bool(outcome["safety_failure"]) for outcome in outcomes),
        "served_safety_failures": served_safety_failures,
        "holdout_safety_failures": holdout_safety_failures,
        "safety_cases": dict(sorted(safety_cases.items())),
        "by_stratum": {
            stratum: {
                **cell,
                "valid_action_rate": cell["valid_actions"] / cell["episodes"],
                "served_oracle_success": (
                    cell["served_successes"] / cell["served_episodes"]
                    if cell["served_episodes"]
                    else None
                ),
            }
            for stratum, cell in sorted(by_stratum.items())
        },
    }


def summarize_all_serve(bundle_root: Path) -> dict[str, Any]:
    """Summarize a standard all-task quality bundle without causal weighting."""

    outcomes = load_quality_outcomes(bundle_root)
    rows = _read_jsonl(bundle_root / "observed_trials.jsonl")
    if len(outcomes) != len(rows):
        raise ValueError("all-SERVE outcome and row counts differ")
    task_results: list[dict[str, Any]] = []
    by_stratum: dict[str, dict[str, int]] = {}
    valid_actions = 0
    bound_receipts = 0
    for row, outcome in zip(rows, outcomes, strict=True):
        tool_trace = json.loads(outcome.tool_trace_json or "{}")
        actual = tool_trace.get("actual", {})
        valid = isinstance(actual, dict) and actual.get("mode") in {"answer", "tool"}
        valid_actions += int(valid)
        bound_receipts += int(bool(json.loads(outcome.model_receipt_json or "{}")))
        memory_frame = json.loads(outcome.memory_frame_json or "{}")
        stratum = str(memory_frame.get("stratum", "unknown"))
        cell = by_stratum.setdefault(stratum, {"episodes": 0, "successes": 0, "valid_actions": 0})
        cell["episodes"] += 1
        cell["successes"] += int(outcome.success)
        cell["valid_actions"] += int(valid)
        task_results.append(
            {
                "trial_id": row["trial_id"],
                "group_id": row["group_id"],
                "visibility": outcome.visibility,
                "utility": outcome.utility,
                "strict_exact_success": outcome.success,
                "safety_failure": outcome.safety_failure,
                "prompt_sha256": outcome.prompt_sha256,
                "memory_frame_sha256": outcome.memory_frame_sha256,
                "model_output_sha256": outcome.model_output_sha256,
                "model_receipt_sha256": outcome.model_receipt_sha256,
                "tool_trace_sha256": outcome.tool_trace_sha256,
                "metrics": outcome.metrics,
            }
        )
    count = len(outcomes)
    return {
        "episodes": count,
        "served_episodes": count,
        "task_coverage_rate": 1.0,
        "valid_action_rate": valid_actions / count,
        "model_receipt_rate": bound_receipts / count,
        "strict_exact_success": sum(outcome.success for outcome in outcomes) / count,
        "safety_failures": sum(outcome.safety_failure for outcome in outcomes),
        "task_results": task_results,
        "task_results_sha256": sha256_text(canonical_json(task_results)),
        "by_stratum": {
            stratum: {
                **cell,
                "valid_action_rate": cell["valid_actions"] / cell["episodes"],
                "strict_exact_success": cell["successes"] / cell["episodes"],
            }
            for stratum, cell in sorted(by_stratum.items())
        },
    }


def aa_repeatability(
    world: ReplayableMemoryWorld,
    task_ids: tuple[str, ...],
) -> dict[str, Any]:
    byte_matches = 0
    action_matches = 0
    success_matches = 0
    rows: list[dict[str, Any]] = []
    for task_id in task_ids:
        prepared = world.prepare(task_id)
        replay_key = hashlib.sha256(f"memory-model-aa:{task_id}".encode()).hexdigest()
        first = world.continue_from(prepared, "serve", replay_key)
        second = world.continue_from(prepared, "serve", replay_key)
        byte_match = (
            first.model_output_json == second.model_output_json
            and first.tool_trace_json == second.tool_trace_json
        )
        first_trace = json.loads(first.tool_trace_json or "{}")
        second_trace = json.loads(second.tool_trace_json or "{}")
        action_match = first_trace.get("actual") == second_trace.get("actual")
        success_match = first.success == second.success
        byte_matches += int(byte_match)
        action_matches += int(action_match)
        success_matches += int(success_match)
        rows.append(
            {
                "task_id": task_id,
                "match": byte_match,
                "byte_match": byte_match,
                "action_match": action_match,
                "success_match": success_match,
                "first_output_sha256": first.model_output_sha256,
                "second_output_sha256": second.model_output_sha256,
                "first_receipt_sha256": first.model_receipt_sha256,
                "second_receipt_sha256": second.model_receipt_sha256,
            }
        )
    return {
        "trials": len(task_ids),
        "exact_rate": byte_matches / len(task_ids),
        "byte_exact_rate": byte_matches / len(task_ids),
        "action_exact_rate": action_matches / len(task_ids),
        "success_exact_rate": success_matches / len(task_ids),
        "success_disagreement_points": (100.0 * (len(task_ids) - success_matches) / len(task_ids)),
        "rows": rows,
    }


def run_screen(
    config_path: Path,
    output_dir: Path,
    *,
    registry_path: Path = DEFAULT_REGISTRY,
    model_root: Path = DEFAULT_MODEL_ROOT,
    receipt_root: Path = DEFAULT_RECEIPT_ROOT,
    episodes_override: int | None = None,
    assignment_seed: int = 42,
    resume: bool = False,
    stop_after: int | None = None,
    stop_requested=None,
    model_id_override: str | None = None,
    memory_bundle: Path | None = None,
    memory_treatment_mode: str = "storage_and_service",
    public_benchmark_path: Path = DEFAULT_LONGMEMEVAL_PATH,
    evaluation_mode: str = "interface-screen",
    memory_budget_profile: str = "matched",
    publication_capsule: Path | None = None,
    publication_capsule_attestation: Path | None = None,
    publication_trust_store: Path | None = None,
    expected_publication_trust_sha256: str | None = None,
    control_matrix_manifest: Path | None = None,
    publication_wave_contract: Path | None = None,
    expected_wave_sha256: str | None = None,
    expected_control_id: str | None = None,
    expected_system_id: str | None = None,
    expected_memory_system_id: str | None = None,
    expected_memory_admission_sha256: str | None = None,
) -> dict[str, Any]:
    if evaluation_mode not in {
        "interface-screen",
        "matrix-cell",
        "diagnostic-ceiling",
        "all-serve-benchmark",
    }:
        raise ValueError(
            "evaluation mode must be interface-screen, matrix-cell, "
            "diagnostic-ceiling, or all-serve-benchmark"
        )
    if memory_budget_profile not in {"matched", "full-prefix-diagnostic"}:
        raise ValueError("unknown memory budget profile")
    admission_values = (
        publication_capsule,
        publication_capsule_attestation,
        publication_trust_store,
        expected_publication_trust_sha256,
        control_matrix_manifest,
        publication_wave_contract,
        expected_wave_sha256,
        expected_control_id,
        expected_system_id,
    )
    if any(value is not None for value in admission_values) and not all(
        value is not None for value in admission_values
    ):
        raise ValueError(
            "publication admission requires capsule, matrix, wave contract, and control"
        )
    if all(value is not None for value in admission_values) and evaluation_mode != (
        "all-serve-benchmark"
    ):
        raise ValueError("publication admission is restricted to all-SERVE quality runs")
    validate_experiment_path(
        config_path,
        registry_path=registry_path,
    )
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    stage = config.get("stage")
    if stage not in {"loader_smoke", "frozen_screen", "model_transport"}:
        raise ValueError(
            "model screen accepts loader_smoke, frozen_screen, or model_transport contracts"
        )
    if stage == "model_transport":
        if model_id_override is None:
            raise ValueError("model transport screen requires an explicit model id")
        roster = {
            item["model_id"]: item
            for item in config["model"]["open_roster"]
            if isinstance(item, dict) and isinstance(item.get("model_id"), str)
        }
        if model_id_override not in roster:
            raise ValueError(f"{model_id_override}: model is not in the open transport roster")
        model_id = model_id_override
        roster_entry = roster[model_id]
    else:
        if model_id_override is not None:
            raise ValueError("model id override is only valid for model transport contracts")
        model_id = config["model"]["model_id"]
        roster_entry = None
    if memory_budget_profile == "full-prefix-diagnostic":
        if stage != "model_transport":
            raise ValueError("full-prefix diagnostic budget requires model_transport")
        if evaluation_mode != "diagnostic-ceiling":
            raise ValueError("full-prefix diagnostic budget requires diagnostic-ceiling evaluation")
        if memory_bundle is None:
            raise ValueError("full-prefix diagnostic budget requires a frozen bundle")
        if memory_treatment_mode != "storage_and_service":
            raise ValueError("full-prefix diagnostic supports storage_and_service only")
    elif evaluation_mode == "diagnostic-ceiling":
        raise ValueError("diagnostic-ceiling evaluation requires full-prefix budget")
    registry = load_registry(registry_path)
    entry = registry["models"].get(model_id)
    if entry is None or entry["backend"] != "huggingface":
        raise ValueError(f"{model_id}: screen requires a pinned Hugging Face model")
    if entry["trust_remote_code"] or not entry["publication_eligible"]:
        raise ValueError(
            f"{model_id}: generic screen forbids unreviewed code or ineligible checkpoints"
        )
    receipt = verify_receipt(model_id, entry, model_root, receipt_root)
    if receipt.get("mode") != "full":
        raise ValueError("model screen requires a full artifact receipt")
    source_config = config["source"]
    source_type = source_config["type"]
    registered_episodes = int(
        (
            source_config["task_count"]
            if evaluation_mode == "all-serve-benchmark"
            else source_config["screen_tasks"]
        )
        if source_type == "longmemeval"
        else source_config.get(
            "total_episodes",
            source_config.get("screen_episodes"),
        )
    )
    episodes = episodes_override or registered_episodes
    if source_type == "longmemeval" and episodes != registered_episodes:
        raise ValueError(
            "registered public screen forbids episode overrides; create a new contract"
        )
    if episodes < 4:
        raise ValueError("model screen requires at least four episodes")
    decode = config["model"].get("decoding") or {
        "max_new_tokens": config["model"]["max_completion_tokens"]
    }
    actor_contract_config = {
        "schema_version": 1,
        "model_id": model_id,
        "revision": entry["revision"],
        "artifact_root_sha256": receipt["artifact_root_sha256"],
        "dtype": str(config["model"].get("dtype", "bfloat16")),
        "decoding": decode,
        "prompt_protocol": "replayable-memory-world-v1",
        "response_schema": "answer-or-tool-json-v1",
        "deterministic_algorithms": True,
        "attention_implementation": "eager",
        "memory_budget_profile": memory_budget_profile,
    }
    actor = TransformersMemoryActor.from_snapshot(
        snapshot=model_root / model_id,
        model_id=model_id,
        revision=entry["revision"],
        artifact_root_sha256=receipt["artifact_root_sha256"],
        max_new_tokens=int(decode["max_new_tokens"]),
        dtype=str(config["model"].get("dtype", "bfloat16")),
        use_chat_template="chat_template.jinja" in entry["required_files"],
    )
    actor_contract = {
        **actor.contract,
        "registered_screen_contract": actor_contract_config,
        "memory_budget_profile": memory_budget_profile,
    }
    actor_contract_sha256 = sha256_text(canonical_json(actor_contract))
    if memory_budget_profile == "full-prefix-diagnostic":
        ceiling = config["diagnostic_ceiling"]
        budget_config = ceiling["memory_budget"]
        budget = MemoryBudget(
            active_slots=int(budget_config["active_slots"]),
            max_archive_reads=int(budget_config["max_archive_reads"]),
            retrieval_top_k=int(budget_config["retrieval_top_k"]),
            max_injected_tokens=int(budget_config["max_injected_tokens"]),
        )
    else:
        budget_config = config["memory_budget"]
        budget = MemoryBudget(
            active_slots=int(budget_config["primary_active_slots"]),
            max_archive_reads=int(budget_config["max_archive_reads_per_opportunity"]),
            retrieval_top_k=int(budget_config["max_retrieval_top_k"]),
            max_injected_tokens=int(budget_config["max_injected_tokens"]),
        )
    if source_type == "generated":
        source: MemoryTaskSource = GeneratedMemoryTaskSource(
            seed=7,
            episode_count=episodes,
            budget=budget,
        )
    elif source_type == "longmemeval":
        if memory_bundle is None:
            raise ValueError("public benchmark screen requires a frozen memory bundle")
        registered_task_ids = (
            None
            if evaluation_mode == "all-serve-benchmark"
            else source_config.get("screen_raw_task_ids")
        )
        if evaluation_mode != "all-serve-benchmark" and (
            not isinstance(registered_task_ids, list)
            or not registered_task_ids
            or not all(isinstance(task_id, str) for task_id in registered_task_ids)
        ):
            raise ValueError("public screen requires explicit raw task IDs")
        if registered_task_ids is not None and episodes != len(registered_task_ids):
            raise ValueError("public screen episode count differs from registered task IDs")
        source = LongMemEvalTaskSource(
            public_benchmark_path,
            expected_sha256=str(source_config["dataset_sha256"]),
            expected_size=int(source_config["dataset_size"]),
            candidate_seed=int(source_config["candidate_seed"]),
            budget=budget,
            task_ids=registered_task_ids,
            artifact_role=str(source_config["artifact_role"]),
        )
        observed_question_types = set(source.provenance["question_type_counts"])
        required_question_types = set(source_config.get("question_types", []))
        if observed_question_types != required_question_types:
            raise ValueError("public screen does not cover every registered question type")
        exact_manifest = task_manifest_sha256(source)
        expected_manifest = source_config[
            "full_task_manifest_sha256"
            if evaluation_mode == "all-serve-benchmark"
            else "screen_task_manifest_sha256"
        ]
        if exact_manifest != expected_manifest:
            raise ValueError("public task manifest differs from the contract")
    else:
        raise ValueError(f"unsupported task source: {source_type}")
    frozen_memory = FrozenMemorySystem(memory_bundle) if memory_bundle else None
    if expected_memory_system_id is not None and frozen_memory is None:
        raise ValueError("expected memory system requires a frozen memory bundle")
    if frozen_memory is not None:
        frozen_memory.require_compatible(
            source_provenance=source.provenance,
            budget=source.budget.model_dump(mode="json"),
            treatment_mode=memory_treatment_mode,
            exact_task_manifest_sha256=task_manifest_sha256(source),
        )
        if memory_budget_profile == "full-prefix-diagnostic" and (
            frozen_memory.receipt.system_id != config["diagnostic_ceiling"]["system_id"]
        ):
            raise ValueError("diagnostic budget requires the full-prefix ceiling bundle")
        if (
            expected_memory_system_id is not None
            and frozen_memory.receipt.system_id != expected_memory_system_id
        ):
            raise ValueError("frozen memory bundle system identity drifted")
        is_mempalace = (
            frozen_memory.receipt.system_id
            == "mempalace-raw-user-session-minilm-port-v1"
        )
        if is_mempalace and expected_memory_admission_sha256 is None:
            raise ValueError("MemPalace actor requires registered admission evidence")
        if expected_memory_admission_sha256 is not None:
            if not SHA256_RE.fullmatch(expected_memory_admission_sha256):
                raise ValueError("expected memory admission digest is invalid")
            if (
                frozen_memory.metadata.get("admission_evidence_sha256")
                != expected_memory_admission_sha256
            ):
                raise ValueError("frozen memory admission evidence drifted")
    claim_admission = None
    if publication_capsule is not None:
        if frozen_memory is None:
            raise ValueError("publication admission requires a frozen memory bundle")
        assert control_matrix_manifest is not None
        assert expected_wave_sha256 is not None
        assert expected_control_id is not None
        assert expected_system_id is not None
        claim_admission = _load_publication_admission(
            capsule_path=publication_capsule,
            attestation_path=publication_capsule_attestation,
            trust_store_path=publication_trust_store,
            expected_trust_store_sha256=expected_publication_trust_sha256,
            matrix_path=control_matrix_manifest,
            experiment_path=config_path,
            wave_path=publication_wave_contract,
            expected_wave_sha256=expected_wave_sha256,
            expected_control_id=expected_control_id,
            expected_system_id=expected_system_id,
            frozen_memory=frozen_memory,
            exact_task_manifest_sha256=task_manifest_sha256(source),
            model_id=model_id,
            model_revision=entry["revision"],
            model_receipt_sha256=_sha256_file(receipt_path(receipt_root, model_id)),
            model_artifact_root_sha256=receipt["artifact_root_sha256"],
            registered_actor_contract=actor_contract_config,
        )
    world = ReplayableMemoryWorld(
        source,
        actor=actor,
        memory_system=frozen_memory,
        memory_treatment_mode=memory_treatment_mode,
        actor_contract=actor_contract,
    )
    trial_ids = source.ids()
    if evaluation_mode == "all-serve-benchmark":
        quality = collect_all_serve(
            world,
            trial_ids,
            output_dir,
            resume=resume,
            stop_after=stop_after,
            stop_requested=stop_requested,
            admission_contract=claim_admission,
        )
        if quality.status == "CHECKPOINTED":
            report = {
                "schema_version": 1,
                "status": "CHECKPOINTED",
                "scientific_result": False,
                "model_id": model_id,
                "assignment_seed": None,
                "evaluation_mode": evaluation_mode,
                "actor_contract": actor_contract,
                "actor_contract_sha256": actor_contract_sha256,
                "completed_trials": quality.completed_tasks,
                "checkpoint_sha256": quality.checkpoint_sha256,
                "memory_bundle_sha256": frozen_memory.bundle_sha256,
                "memory_treatment_mode": memory_treatment_mode,
                "memory_budget_profile": memory_budget_profile,
                "task_source": dict(source.provenance),
                "task_manifest_sha256": task_manifest_sha256(source),
                "claim_admission": claim_admission,
            }
            atomic_json(output_dir / "screen-report.json", report)
            return report
        if quality.bundle_root is None or quality.bundle_manifest_sha256 is None:
            raise RuntimeError("all-SERVE collection did not produce a sealed bundle")
        metrics = summarize_all_serve(quality.bundle_root)
        aa_count = max(1, math.ceil(episodes * 0.10))
        aa = aa_repeatability(world, trial_ids[:aa_count])
        gate_config = config.get("eligibility_gates", {})
        validity_gates = {
            "complete_task_coverage": metrics["task_coverage_rate"] == 1.0,
            "valid_action_rate": metrics["valid_action_rate"]
            >= float(gate_config.get("minimum_valid_action_json_rate", 0.95)),
            "model_receipts_bound": metrics["model_receipt_rate"] == 1.0,
            "aa_exact": aa["exact_rate"] == 1.0,
            "no_safety_failures": metrics["safety_failures"] == 0,
        }
        report = {
            "schema_version": 1,
            "status": (
                "MODEL_ALL_SERVE_OUTPUTS_SEALED" if all(validity_gates.values()) else "FAIL"
            ),
            "scientific_result": False,
            "reason": (
                "Complete all-SERVE outputs; official semantic judgment and matched "
                "control aggregation remain required before a quality claim."
            ),
            "evaluation_mode": evaluation_mode,
            "assignment_seed": None,
            "model_id": model_id,
            "revision": entry["revision"],
            "artifact_root_sha256": receipt["artifact_root_sha256"],
            "actor_contract": actor_contract,
            "actor_contract_sha256": actor_contract_sha256,
            "bundle_manifest_sha256": quality.bundle_manifest_sha256,
            "checkpoint_sha256": quality.checkpoint_sha256,
            "memory_system": frozen_memory.receipt.model_dump(mode="json"),
            "memory_treatment_mode": memory_treatment_mode,
            "memory_budget_profile": memory_budget_profile,
            "task_source": dict(source.provenance),
            "task_manifest_sha256": task_manifest_sha256(source),
            "memory_bundle_sha256": frozen_memory.bundle_sha256,
            "claim_admission": claim_admission,
            "metrics": metrics,
            "metric_semantics": {
                "strict_exact_success": "secondary-diagnostic",
                "official_longmemeval_score": None,
                "official_judge_required": True,
            },
            "aa_repeatability": aa,
            "validity_gates": validity_gates,
            "performance_gates": {},
            "gates": validity_gates,
        }
        atomic_json(output_dir / "screen-report.json", report)
        return report

    design = config["causal_design"]
    propensity = float(
        design["screen_serve_propensity"]
        if stage == "model_transport"
        else design["serve_propensities"][0]
    )
    if not math.isfinite(propensity) or not 0 < propensity < 1:
        raise ValueError("screen propensity must be finite and in (0,1)")
    plan = TrialPlan(
        study_id=f"{config['study_id']}-{model_id.replace('.', '-')}",
        trial_ids=trial_ids,
        allowed_features=ALLOWED_FEATURES,
        paired_audit_ids=audit_ids(
            trial_ids,
            assignment_seed=assignment_seed,
            fraction=float(
                design["self_hosted_paired_replay_fraction"]
                if stage == "model_transport"
                else design["paired_replay_fraction"]
            ),
        ),
        propensity=propensity,
        assignment_seed=assignment_seed,
        folds=int(design.get("folds", 5)),
        minimum_effective_sample_size=max(2.0, episodes * 0.2),
        minimum_arm_effective_sample_size=max(1.0, episodes * 0.05),
    )
    collection = collect_resumable(
        plan,
        world,
        output_dir,
        resume=resume,
        stop_after=stop_after,
        stop_requested=stop_requested,
    )
    if collection.status == "CHECKPOINTED":
        report = {
            "schema_version": 1,
            "status": "CHECKPOINTED",
            "scientific_result": False,
            "model_id": model_id,
            "assignment_seed": assignment_seed,
            "evaluation_mode": evaluation_mode,
            "actor_contract": actor_contract,
            "actor_contract_sha256": actor_contract_sha256,
            "completed_trials": collection.completed_trials,
            "checkpoint_sha256": collection.checkpoint_sha256,
            "memory_bundle_sha256": (
                frozen_memory.bundle_sha256 if frozen_memory is not None else None
            ),
            "memory_treatment_mode": memory_treatment_mode,
            "memory_budget_profile": memory_budget_profile,
            "task_source": dict(source.provenance),
            "task_manifest_sha256": task_manifest_sha256(source),
        }
        atomic_json(output_dir / "screen-report.json", report)
        return report
    if collection.bundle is None:
        raise RuntimeError("complete model screen did not produce a bundle")
    metrics = summarize_screen(collection.bundle)
    aa_count = max(1, math.ceil(episodes * 0.10))
    aa = aa_repeatability(world, trial_ids[:aa_count])
    gate_config = config.get("eligibility_gates", {})
    minimum_valid = float(gate_config.get("minimum_valid_action_json_rate", 0.95))
    minimum_success = float(gate_config.get("minimum_oracle_memory_success", 0.0))
    stratum_successes = [cell["served_oracle_success"] for cell in metrics["by_stratum"].values()]
    validity_gates = {
        "valid_action_rate": metrics["valid_action_rate"] >= minimum_valid,
        "model_receipts_bound": metrics["model_receipt_rate"] == 1.0,
        "aa_exact": aa["exact_rate"] == 1.0,
        "aa_success_drift_within_registered_limit": (
            aa["success_disagreement_points"]
            <= float(gate_config.get("maximum_aa_success_drift_points", 0.0))
        ),
        "no_safety_failures": metrics["safety_failures"] == 0,
    }
    performance_gates: dict[str, bool] = {}
    if stage == "model_transport" and evaluation_mode != "diagnostic-ceiling":
        performance_gates.update(
            {
                "served_oracle_success": metrics["served_oracle_success"] >= minimum_success,
                "every_stratum_has_served_evidence": all(
                    value is not None for value in stratum_successes
                ),
                "per_stratum_oracle_success": all(
                    value is not None and value >= minimum_success for value in stratum_successes
                ),
            }
        )
    gates = {**validity_gates, **performance_gates}
    validity_passed = all(validity_gates.values())
    performance_passed = all(performance_gates.values())
    if evaluation_mode == "matrix-cell":
        status = "MODEL_MATRIX_CELL_VALID" if validity_passed else "FAIL"
        reason = (
            "Matched control-matrix cell; competence outcomes are measurements, "
            "not cell-validity gates."
        )
    elif evaluation_mode == "diagnostic-ceiling":
        status = "MODEL_DIAGNOSTIC_CEILING_VALID" if validity_passed else "FAIL"
        reason = (
            "Unmatched full-prefix diagnostic; outcomes are a ceiling measurement "
            "and are ineligible for strongest-control selection."
        )
    else:
        status = "MODEL_INTERFACE_SCREEN_PASS" if validity_passed and performance_passed else "FAIL"
        reason = "Interface and competence screen only; no memory-policy claim."
    report = {
        "schema_version": 1,
        "status": status,
        "scientific_result": False,
        "reason": reason,
        "evaluation_mode": evaluation_mode,
        "assignment_seed": assignment_seed,
        "model_id": model_id,
        "model_role": roster_entry,
        "revision": entry["revision"],
        "artifact_root_sha256": receipt["artifact_root_sha256"],
        "actor_contract": actor_contract,
        "actor_contract_sha256": actor_contract_sha256,
        "bundle_manifest_sha256": collection.bundle.manifest_sha256,
        "checkpoint_sha256": collection.checkpoint_sha256,
        "memory_system": (
            frozen_memory.receipt.model_dump(mode="json")
            if frozen_memory is not None
            else "engine-direct-records-v1"
        ),
        "memory_treatment_mode": memory_treatment_mode,
        "memory_budget_profile": memory_budget_profile,
        "task_source": dict(source.provenance),
        "task_manifest_sha256": task_manifest_sha256(source),
        "memory_bundle_sha256": (
            frozen_memory.bundle_sha256 if frozen_memory is not None else None
        ),
        "metrics": metrics,
        "metric_semantics": (
            {
                "success": "strict-exact-diagnostic-only",
                "official_longmemeval_score": None,
                "retrieval_evaluation_capable": bool(
                    source.provenance["retrieval_evaluation_capable"]
                ),
                "retrieval_claim_enabled": False,
                "graph_claim_enabled": bool(source.provenance["graph_claim_enabled"]),
            }
            if source_type == "longmemeval"
            else {"success": "executable-oracle"}
        ),
        "aa_repeatability": aa,
        "validity_gates": validity_gates,
        "performance_gates": performance_gates,
        "gates": gates,
    }
    atomic_json(output_dir / "screen-report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--model-root", type=Path, default=DEFAULT_MODEL_ROOT)
    parser.add_argument("--receipt-root", type=Path, default=DEFAULT_RECEIPT_ROOT)
    parser.add_argument("--model-id")
    parser.add_argument("--memory-bundle", type=Path)
    parser.add_argument(
        "--public-benchmark-path",
        type=Path,
        default=DEFAULT_LONGMEMEVAL_PATH,
    )
    parser.add_argument(
        "--memory-treatment-mode",
        choices=("storage_and_service", "serve_only"),
        default="storage_and_service",
    )
    parser.add_argument(
        "--evaluation-mode",
        choices=(
            "interface-screen",
            "matrix-cell",
            "diagnostic-ceiling",
            "all-serve-benchmark",
        ),
        default="interface-screen",
    )
    parser.add_argument(
        "--memory-budget-profile",
        choices=("matched", "full-prefix-diagnostic"),
        default="matched",
    )
    parser.add_argument("--episodes", type=int)
    assignment_group = parser.add_mutually_exclusive_group()
    assignment_group.add_argument("--assignment-seed", type=int)
    assignment_group.add_argument("--assignment-seeds", type=int, nargs="+")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--stop-after", type=int)
    parser.add_argument("--publication-capsule", type=Path)
    parser.add_argument("--publication-capsule-attestation", type=Path)
    parser.add_argument("--publication-trust-store", type=Path)
    parser.add_argument("--expected-publication-trust-sha256")
    parser.add_argument("--control-matrix-manifest", type=Path)
    parser.add_argument("--publication-wave-contract", type=Path)
    parser.add_argument("--expected-wave-sha256")
    parser.add_argument("--expected-control-id")
    parser.add_argument("--expected-system-id")
    parser.add_argument("--expected-memory-system-id")
    parser.add_argument("--expected-memory-admission-sha256")
    parser.add_argument("--require-gates", action="store_true")
    args = parser.parse_args()
    stop = False

    def request_stop(_signum, _frame) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGUSR1, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    assignment_seeds = (
        tuple(args.assignment_seeds)
        if args.assignment_seeds is not None
        else (args.assignment_seed,)
        if args.assignment_seed is not None
        else tuple(config["execution"]["seeds"])
    )
    if args.evaluation_mode == "all-serve-benchmark":
        if args.assignment_seed is not None or args.assignment_seeds is not None:
            raise ValueError("all-SERVE evaluation has no assignment seeds")
        assignment_seeds = (0,)
    if len(set(assignment_seeds)) != len(assignment_seeds):
        raise ValueError("assignment seeds must be distinct")
    if len(assignment_seeds) == 1:
        report = run_screen(
            args.config,
            args.output_dir,
            registry_path=args.registry,
            model_root=args.model_root,
            receipt_root=args.receipt_root,
            episodes_override=args.episodes,
            assignment_seed=assignment_seeds[0],
            resume=args.resume,
            stop_after=args.stop_after,
            stop_requested=lambda: stop,
            model_id_override=args.model_id,
            memory_bundle=args.memory_bundle,
            memory_treatment_mode=args.memory_treatment_mode,
            public_benchmark_path=args.public_benchmark_path,
            evaluation_mode=args.evaluation_mode,
            memory_budget_profile=args.memory_budget_profile,
            publication_capsule=args.publication_capsule,
            publication_capsule_attestation=args.publication_capsule_attestation,
            publication_trust_store=args.publication_trust_store,
            expected_publication_trust_sha256=(args.expected_publication_trust_sha256),
            control_matrix_manifest=args.control_matrix_manifest,
            publication_wave_contract=args.publication_wave_contract,
            expected_wave_sha256=args.expected_wave_sha256,
            expected_control_id=args.expected_control_id,
            expected_system_id=args.expected_system_id,
            expected_memory_system_id=args.expected_memory_system_id,
            expected_memory_admission_sha256=args.expected_memory_admission_sha256,
        )
    else:
        seed_reports: list[dict[str, Any]] = []
        for assignment_seed in assignment_seeds:
            seed_dir = args.output_dir / f"seed-{assignment_seed}"
            seed_report = run_screen(
                args.config,
                seed_dir,
                registry_path=args.registry,
                model_root=args.model_root,
                receipt_root=args.receipt_root,
                episodes_override=args.episodes,
                assignment_seed=assignment_seed,
                resume=args.resume and seed_dir.exists(),
                stop_after=args.stop_after,
                stop_requested=lambda: stop,
                model_id_override=args.model_id,
                memory_bundle=args.memory_bundle,
                memory_treatment_mode=args.memory_treatment_mode,
                public_benchmark_path=args.public_benchmark_path,
                evaluation_mode=args.evaluation_mode,
                memory_budget_profile=args.memory_budget_profile,
                publication_capsule=args.publication_capsule,
                publication_capsule_attestation=args.publication_capsule_attestation,
                publication_trust_store=args.publication_trust_store,
                expected_publication_trust_sha256=(args.expected_publication_trust_sha256),
                control_matrix_manifest=args.control_matrix_manifest,
                publication_wave_contract=args.publication_wave_contract,
                expected_wave_sha256=args.expected_wave_sha256,
                expected_control_id=args.expected_control_id,
                expected_system_id=args.expected_system_id,
                expected_memory_system_id=args.expected_memory_system_id,
                expected_memory_admission_sha256=(
                    args.expected_memory_admission_sha256
                ),
            )
            seed_reports.append({"assignment_seed": assignment_seed, "report": seed_report})
            if seed_report["status"] == "CHECKPOINTED":
                break
        complete = len(seed_reports) == len(assignment_seeds)
        expected_cell_status = (
            "MODEL_MATRIX_CELL_VALID"
            if args.evaluation_mode == "matrix-cell"
            else "MODEL_DIAGNOSTIC_CEILING_VALID"
            if args.evaluation_mode == "diagnostic-ceiling"
            else "MODEL_INTERFACE_SCREEN_PASS"
        )
        passed = complete and all(
            item["report"]["status"] == expected_cell_status for item in seed_reports
        )
        report = {
            "schema_version": 1,
            "status": (
                "MODEL_CONTROL_MATRIX_CELL_PASS"
                if passed and args.evaluation_mode == "matrix-cell"
                else "MODEL_DIAGNOSTIC_CEILING_MATRIX_PASS"
                if passed and args.evaluation_mode == "diagnostic-ceiling"
                else "MODEL_SEED_MATRIX_PASS"
                if passed
                else "CHECKPOINTED"
                if not complete
                else "FAIL"
            ),
            "scientific_result": False,
            "reason": (
                "Assignment-seed sensitivity matrix; seeds are repeated designs, "
                "not independent task samples."
            ),
            "assignment_seeds": list(assignment_seeds),
            "evaluation_mode": args.evaluation_mode,
            "memory_budget_profile": args.memory_budget_profile,
            "seed_reports": seed_reports,
        }
        atomic_json(args.output_dir / "screen-matrix-report.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))
    passing_statuses = {
        "MODEL_INTERFACE_SCREEN_PASS",
        "MODEL_SEED_MATRIX_PASS",
        "MODEL_MATRIX_CELL_VALID",
        "MODEL_CONTROL_MATRIX_CELL_PASS",
        "MODEL_DIAGNOSTIC_CEILING_VALID",
        "MODEL_DIAGNOSTIC_CEILING_MATRIX_PASS",
        "MODEL_ALL_SERVE_OUTPUTS_SEALED",
    }
    if args.require_gates and report["status"] not in passing_statuses:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
