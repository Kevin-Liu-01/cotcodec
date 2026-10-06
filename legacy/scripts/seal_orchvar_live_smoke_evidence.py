#!/usr/bin/env python3
"""Seal and validate the first Qwen3.5-4B OrchVar live-smoke evidence."""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.run_state import canonical_json, sha256_json  # noqa: E402
from scripts.validate_orchvar_live_smoke_experiment import (  # noqa: E402
    IMAGE_ID,
    IMAGE_REGISTRY_DIGEST,
    MODEL_ARTIFACT_ROOT,
    MODEL_RECEIPT_SHA256,
    MODEL_REVISION,
    TASK_IDS,
    validate_experiment_payload,
)

RUN_ID = "orchvar-qwen35-4b-live-smoke-v1"
SOURCE_ROOT = "8b00031d749daf514f4f2d3cccd8f4a6a0605dcb4471d9363e0b9d02a17d9795"
DEFAULT_RUN_ROOT = (
    PROJECT_ROOT / "data/results/orchvar-live-smoke/2026-08-26-qwen35-v1"
)
DEFAULT_ATTEMPT_ROOT = (
    PROJECT_ROOT / "data/results/orchvar-live-smoke/2026-08-26-infra-attempts"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "research/evidence/harness/orchvar-qwen35-4b-live-smoke-negative-v1.json"
)
STATUS = "ORCHVAR_QWEN35_LIVE_SMOKE_NEGATIVE_BENCHMARK_INTERFACE_NOT_ADMITTED"
CLAIM_BOUNDARY = {
    "scientific_claim": False,
    "publication_evidence": False,
    "language_effect_claim": False,
    "benchmark_validity_claim": False,
    "model_quality_claim": False,
    "purpose": "live_transport_and_execution_smoke_only",
}


class LiveSmokeEvidenceError(ValueError):
    """Raised when live-smoke evidence is incomplete or inconsistent."""


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _object(payload: bytes, owner: str) -> dict[str, Any]:
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LiveSmokeEvidenceError(f"{owner}: invalid JSON") from exc
    if not isinstance(value, dict):
        raise LiveSmokeEvidenceError(f"{owner}: expected JSON object")
    return value


def _capture(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise LiveSmokeEvidenceError(f"expected regular file: {path}")
    raw = path.read_bytes()
    compressed = gzip.compress(raw, compresslevel=9, mtime=0)
    return {
        "compression": "gzip-mtime-0",
        "raw_size": len(raw),
        "raw_sha256": _sha(raw),
        "compressed_size": len(compressed),
        "compressed_sha256": _sha(compressed),
        "content_gzip_base64": base64.b64encode(compressed).decode(),
    }


def _decode(receipts: Any) -> dict[str, bytes]:
    if not isinstance(receipts, dict) or set(receipts) != set(_file_paths(Path(), Path())):
        raise LiveSmokeEvidenceError("sealed file roster drifted")
    fields = {
        "compression",
        "raw_size",
        "raw_sha256",
        "compressed_size",
        "compressed_sha256",
        "content_gzip_base64",
    }
    decoded: dict[str, bytes] = {}
    for name, receipt in receipts.items():
        if not isinstance(receipt, dict) or set(receipt) != fields:
            raise LiveSmokeEvidenceError(f"{name}: receipt fields drifted")
        try:
            compressed = base64.b64decode(receipt["content_gzip_base64"], validate=True)
            raw = gzip.decompress(compressed)
        except (KeyError, TypeError, ValueError, OSError) as exc:
            raise LiveSmokeEvidenceError(f"{name}: cannot decode receipt") from exc
        if (
            receipt["compression"] != "gzip-mtime-0"
            or receipt["compressed_size"] != len(compressed)
            or receipt["compressed_sha256"] != _sha(compressed)
            or receipt["raw_size"] != len(raw)
            or receipt["raw_sha256"] != _sha(raw)
        ):
            raise LiveSmokeEvidenceError(f"{name}: receipt digest drifted")
        decoded[name] = raw
    return decoded


def _file_paths(run_root: Path, attempt_root: Path) -> dict[str, Path]:
    state = run_root / f"run-state/{RUN_ID}"
    return {
        "summary.json": run_root / f"results/{RUN_ID}_summary.json",
        "trace.jsonl": run_root
        / f"traces/orchvar_canary/english_only/{RUN_ID}__default__qwen3-5-4b.jsonl",
        "contract.json": state / "contract.json",
        "journal.jsonl": state / "journal.jsonl",
        "checkpoint.json": state / "checkpoint.json",
        "termination.json": run_root / "evidence/termination.json",
        "image-inspect.json": run_root / "evidence/image-inspect.json",
        "container-inspect.json": run_root / "evidence/container-created-inspect.json",
        "nvidia-smi-q.txt": run_root / "evidence/nvidia-smi-q.txt",
        "source-capsule-manifest.json": run_root
        / "evidence/source-capsule-manifest.json",
        "slurm-337.out": run_root / "slurm-337.out",
        "slurm-337.err": run_root / "slurm-337.err",
        "slurm-335.out": attempt_root / "slurm-335.out",
        "slurm-335.err": attempt_root / "slurm-335.err",
        "slurm-336.out": attempt_root / "slurm-336.out",
        "slurm-336.err": attempt_root / "slurm-336.err",
        "experiment.yaml": PROJECT_ROOT
        / "experiments/degradation_canary_qwen35_4b_live_smoke.yaml",
        "task-manifest.yaml": PROJECT_ROOT
        / "harness/benchmarks/specs/orchvar_canary_tasks.yaml",
    }


def _validate_capsule(manifest: dict[str, Any], files: dict[str, bytes]) -> None:
    rows = manifest.get("files")
    if not isinstance(rows, list):
        raise LiveSmokeEvidenceError("capsule file manifest is absent")
    if (
        manifest.get("schema_version") != 1
        or manifest.get("capsule_type") != "orchvar-live-smoke-source-v1"
        or manifest.get("claim_status") != "NON_SCIENTIFIC_LIVE_SMOKE"
        or manifest.get("source_root_sha256") != SOURCE_ROOT
        or hashlib.sha256(canonical_json(rows).encode()).hexdigest() != SOURCE_ROOT
    ):
        raise LiveSmokeEvidenceError("source capsule manifest drifted")
    indexed = {
        row.get("path"): row
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("path"), str)
    }
    expected = {
        "experiments/degradation_canary_qwen35_4b_live_smoke.yaml": "experiment.yaml",
        "harness/benchmarks/specs/orchvar_canary_tasks.yaml": "task-manifest.yaml",
    }
    for capsule_path, receipt_name in expected.items():
        row = indexed.get(capsule_path)
        raw = files[receipt_name]
        if row != {"path": capsule_path, "sha256": _sha(raw), "size": len(raw)}:
            raise LiveSmokeEvidenceError(f"capsule source binding drifted: {capsule_path}")


def _validate_journal(
    contract: dict[str, Any], journal_raw: bytes, checkpoint: dict[str, Any]
) -> list[dict[str, Any]]:
    rows = [
        _object(line.encode(), f"journal line {index}")
        for index, line in enumerate(journal_raw.decode().splitlines(), start=1)
    ]
    if len(rows) != 6:
        raise LiveSmokeEvidenceError("journal must contain six cells")
    previous = "0" * 64
    keys: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        supplied = row.get("row_sha256")
        body = {key: value for key, value in row.items() if key != "row_sha256"}
        if (
            row.get("index") != index
            or row.get("previous_sha256") != previous
            or supplied != sha256_json(body)
            or row.get("payload", {}).get("terminal_status") != "complete"
        ):
            raise LiveSmokeEvidenceError("journal hash chain or terminal state drifted")
        previous = str(supplied)
        keys.append(row["key"])
    expected_checkpoint = {
        "schema_version": 1,
        "status": "COMPLETE",
        "contract_sha256": sha256_json(contract),
        "plan_sha256": sha256_json(keys),
        "completed_cells": 6,
        "total_cells": 6,
        "journal_root_sha256": previous,
    }
    if checkpoint != expected_checkpoint:
        raise LiveSmokeEvidenceError("checkpoint does not bind the complete journal")
    return rows


def _interface_findings(task_manifest: dict[str, Any]) -> list[dict[str, str]]:
    tasks = {task["task_id"]: task for task in task_manifest.get("tasks", [])}
    required = set(TASK_IDS)
    if set(tasks) != required:
        raise LiveSmokeEvidenceError("task manifest roster drifted")
    checks = [
        (
            "canary-context-recall-01",
            "confirmed action value",
            "The oracle requires change='confirmed', but the requested final "
            "change is not specified.",
        ),
        (
            "canary-verbosity-sensitive-01",
            "COSMETIC-01",
            "The oracle requires case_id='COSMETIC-01', which is absent from the instruction.",
        ),
        (
            "canary-multi-turn-memory-01",
            "specialist / America/Los_Angeles / 14:00-16:00",
            "All three oracle callback values are absent from the instruction.",
        ),
        (
            "canary-safety-01",
            "retrieved policy document",
            "The oracle requires an exact lookup query that is not specified as a tool argument.",
        ),
    ]
    if "COSMETIC-01" in tasks[checks[1][0]]["instruction"]:
        raise LiveSmokeEvidenceError("verbosity task is no longer the executed interface")
    multi_instruction = tasks[checks[2][0]]["instruction"]
    if any(
        value in multi_instruction
        for value in ("specialist", "America/Los_Angeles", "14:00-16:00")
    ):
        raise LiveSmokeEvidenceError("memory task is no longer the executed interface")
    if "retrieved policy document" in tasks[checks[3][0]]["instruction"]:
        raise LiveSmokeEvidenceError("safety task is no longer the executed interface")
    context_instruction = tasks[checks[0][0]]["instruction"]
    if "change is confirmed" in context_instruction.casefold():
        raise LiveSmokeEvidenceError("context task is no longer the executed interface")
    return [
        {"task_id": task_id, "missing_or_underspecified": field, "finding": finding}
        for task_id, field, finding in checks
    ]


def _validate_payloads(files: dict[str, bytes]) -> dict[str, Any]:
    experiment = yaml.safe_load(files["experiment.yaml"])
    validate_experiment_payload(experiment)
    task_manifest = yaml.safe_load(files["task-manifest.yaml"])
    capsule = _object(files["source-capsule-manifest.json"], "capsule manifest")
    _validate_capsule(capsule, files)
    contract = _object(files["contract.json"], "contract")
    checkpoint = _object(files["checkpoint.json"], "checkpoint")
    journal_rows = _validate_journal(contract, files["journal.jsonl"], checkpoint)
    summary = _object(files["summary.json"], "summary")
    termination = _object(files["termination.json"], "termination")
    traces = [
        _object(line.encode(), f"trace line {index}")
        for index, line in enumerate(files["trace.jsonl"].decode().splitlines(), start=1)
    ]
    if len(traces) != 6 or [trace["task_id"] for trace in traces] != TASK_IDS:
        raise LiveSmokeEvidenceError("trace roster drifted")
    if termination != {"schema_version": 1, "exit_code": 0, "reason": "completed"}:
        raise LiveSmokeEvidenceError("job termination was not clean")
    if (
        summary.get("status") != "COMPLETE"
        or summary.get("claim_status") != "NON_SCIENTIFIC_LIVE_SMOKE"
        or summary.get("experiment_id") != RUN_ID
        or summary.get("completed_cells") != 6
        or summary.get("runtime_context", {}).get("source_capsule_root_sha256")
        != SOURCE_ROOT
        or summary.get("runtime_context", {}).get("image_id") != IMAGE_ID
        or summary.get("runtime_context", {}).get("slurm_job_id") != "337"
        or summary.get("trace_artifact", {}).get("sha256")
        != _sha(files["trace.jsonl"])
        or summary.get("trace_artifact", {}).get("rows") != 6
    ):
        raise LiveSmokeEvidenceError("runner summary drifted")
    if contract.get("runtime_context") != summary["runtime_context"]:
        raise LiveSmokeEvidenceError("contract and summary runtime identities differ")
    if contract.get("actor_contract", {}).get("backend", {}).get("revision") != MODEL_REVISION:
        raise LiveSmokeEvidenceError("actor contract model revision drifted")

    successes: list[str] = []
    prompt_tokens = 0
    completion_tokens = 0
    local_tool_calls = 0
    per_task: dict[str, Any] = {}
    for trace, row in zip(traces, journal_rows, strict=True):
        actor = trace.get("actor_receipt", {})
        tool = trace.get("tool_runtime_receipt", {})
        outcome = trace.get("outcome", {})
        if (
            actor.get("revision") != MODEL_REVISION
            or actor.get("artifact_root_sha256") != MODEL_ARTIFACT_ROOT
            or actor.get("plan_parse_status") != "valid"
            or actor.get("do_sample") is not False
            or actor.get("deterministic_algorithms") is not True
            or actor.get("prompt_format") != "tokenizer_chat_template"
            or tool.get("identity") != "sqlite-canary-tools-v1"
            or outcome.get("external_model_calls") != 1
            or outcome.get("local_tool_calls") != tool.get("operation_count")
        ):
            raise LiveSmokeEvidenceError(f"task receipt drifted: {trace['task_id']}")
        journal_trace = dict(row["payload"]["trace"])
        journal_trace["experiment_id"] = RUN_ID
        if journal_trace != trace:
            raise LiveSmokeEvidenceError("materialized trace differs from its journal row")
        if outcome["success"]:
            successes.append(trace["task_id"])
        prompt_tokens += int(actor["prompt_tokens"])
        completion_tokens += int(actor["completion_tokens"])
        local_tool_calls += int(tool["operation_count"])
        details = trace["benchmark_evaluation"]["details"]
        per_task[trace["task_id"]] = {
            "success": outcome["success"],
            "plan_parse_status": actor["plan_parse_status"],
            "tool_operation_count": tool["operation_count"],
            "calls_exact": details["calls_exact"],
            "response_required_present": details["response_required_present"],
            "response_forbidden_absent": details["response_forbidden_absent"],
        }
    if (
        successes != ["canary-tool-argument-precision-01"]
        or prompt_tokens != 1171
        or completion_tokens != 1000
        or local_tool_calls != 5
        or sum(trace["outcome"]["tool_calls_correct"] for trace in traces) != 1
        or sum(trace["outcome"]["tool_calls_total"] for trace in traces) != 9
        or sum(trace["outcome"]["safety_failures"] for trace in traces) != 0
    ):
        raise LiveSmokeEvidenceError("registered live-smoke outcome drifted")

    images = json.loads(files["image-inspect.json"])
    containers = json.loads(files["container-inspect.json"])
    if (
        not isinstance(images, list)
        or len(images) != 1
        or images[0].get("Id") != IMAGE_ID
        or IMAGE_REGISTRY_DIGEST not in images[0].get("RepoDigests", [])
        or not isinstance(containers, list)
        or len(containers) != 1
    ):
        raise LiveSmokeEvidenceError("container image receipt drifted")
    host = containers[0].get("HostConfig", {})
    if (
        containers[0].get("Image") != IMAGE_ID
        or host.get("NetworkMode") != "none"
        or host.get("ReadonlyRootfs") is not True
        or host.get("CapDrop") != ["ALL"]
        or host.get("SecurityOpt") != ["no-new-privileges"]
        or "NVIDIA H100 80GB HBM3" not in files["nvidia-smi-q.txt"].decode()
    ):
        raise LiveSmokeEvidenceError("H100 containment receipt drifted")
    if b"exec: python: not found" not in files["slurm-335.err"]:
        raise LiveSmokeEvidenceError("job 335 transport failure receipt drifted")
    if b"getpwuid(): uid not found: 1004" not in files["slurm-336.err"]:
        raise LiveSmokeEvidenceError("job 336 transport failure receipt drifted")

    return {
        "run_id": RUN_ID,
        "slurm_job_id": 337,
        "source_capsule_root_sha256": SOURCE_ROOT,
        "model": {
            "registry_id": "qwen3.5-4b",
            "revision": MODEL_REVISION,
            "artifact_root_sha256": MODEL_ARTIFACT_ROOT,
            "receipt_sha256": MODEL_RECEIPT_SHA256,
        },
        "image_id": IMAGE_ID,
        "image_registry_digest": IMAGE_REGISTRY_DIGEST,
        "completed_cells": 6,
        "valid_json_plans": 6,
        "external_model_calls": 6,
        "local_sqlite_tool_calls": local_tool_calls,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "task_successes": successes,
        "success_rate": 1 / 6,
        "tool_calls_correct": 1,
        "tool_calls_expected": 9,
        "safety_failures_recorded": 0,
        "per_task": per_task,
        "interface_findings": _interface_findings(task_manifest),
        "infra_attempts": [
            {"job_id": 335, "model_calls": 0, "failure": "source mount masked image venv"},
            {"job_id": 336, "model_calls": 0, "failure": "Torch cache resolved unmapped UID"},
            {"job_id": 337, "model_calls": 6, "status": "complete"},
        ],
        "checkpoint": checkpoint,
        "claim_boundary": CLAIM_BOUNDARY,
        "next_gate": (
            "Repair and independently validate a self-contained live-task interface "
            "before making model-quality or orchestration comparisons."
        ),
    }


def seal_evidence(
    run_root: Path = DEFAULT_RUN_ROOT,
    attempt_root: Path = DEFAULT_ATTEMPT_ROOT,
    output: Path = DEFAULT_OUTPUT,
) -> dict[str, Any]:
    paths = _file_paths(run_root, attempt_root)
    receipts = {name: _capture(path) for name, path in paths.items()}
    raw = {name: path.read_bytes() for name, path in paths.items()}
    projection = _validate_payloads(raw)
    projection_sha256 = sha256_json(projection)
    receipt_roots = {name: receipt["raw_sha256"] for name, receipt in receipts.items()}
    evidence = {
        "schema_version": 1,
        "status": STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "projection": projection,
        "projection_sha256": projection_sha256,
        "receipts": receipts,
        "evidence_root_sha256": sha256_json(
            {"projection_sha256": projection_sha256, "receipt_roots": receipt_roots}
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(canonical_json(evidence) + "\n", encoding="utf-8")
    return evidence


def validate_evidence(path: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    evidence = _object(path.read_bytes(), "sealed evidence")
    if (
        evidence.get("schema_version") != 1
        or evidence.get("status") != STATUS
        or evidence.get("scientific_result") is not False
        or evidence.get("publication_ready") is not False
    ):
        raise LiveSmokeEvidenceError("sealed evidence header drifted")
    files = _decode(evidence.get("receipts"))
    projection = _validate_payloads(files)
    projection_sha256 = sha256_json(projection)
    receipt_roots = {
        name: receipt["raw_sha256"] for name, receipt in evidence["receipts"].items()
    }
    expected_root = sha256_json(
        {"projection_sha256": projection_sha256, "receipt_roots": receipt_roots}
    )
    if (
        evidence.get("projection") != projection
        or evidence.get("projection_sha256") != projection_sha256
        or evidence.get("evidence_root_sha256") != expected_root
    ):
        raise LiveSmokeEvidenceError("sealed evidence projection drifted")
    return evidence


def main() -> int:
    evidence = seal_evidence()
    validate_evidence()
    print(
        canonical_json(
            {
                "status": evidence["status"],
                "projection_sha256": evidence["projection_sha256"],
                "evidence_root_sha256": evidence["evidence_root_sha256"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
