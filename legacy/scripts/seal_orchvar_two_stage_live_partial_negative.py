#!/usr/bin/env python3
"""Seal job 341's partial two-stage live negative without completing its claims."""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

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
)

RUN_ID = "orchvar-qwen35-two-stage-live-v1"
SOURCE_ROOT = "32d7622f1b9815952a41c83c655d419ec22bae0935798e915cb5e217cca59818"
STATUS = "ORCHVAR_QWEN35_TWO_STAGE_LIVE_PARTIAL_NEGATIVE_TOOL_ERROR_UNRECEIPTED"
DEFAULT_RUN_ROOT = (
    PROJECT_ROOT
    / "data/results/orchvar-two-stage/2026-08-26-live-job-341-negative"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "research/evidence/harness/"
    "orchvar-qwen35-two-stage-live-partial-negative-job341.json"
)


class TwoStagePartialEvidenceError(ValueError):
    """Raised when the partial live evidence is incomplete or inconsistent."""


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _object(raw: bytes, owner: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TwoStagePartialEvidenceError(f"{owner}: invalid JSON") from exc
    if not isinstance(value, dict):
        raise TwoStagePartialEvidenceError(f"{owner}: expected object")
    return value


def _paths(root: Path) -> dict[str, Path]:
    state = root / f"run-state/{RUN_ID}"
    evidence = root / "evidence"
    return {
        "contract.json": state / "contract.json",
        "journal.jsonl": state / "journal.jsonl",
        "checkpoint.json": state / "checkpoint.json",
        "termination.json": evidence / "termination.json",
        "container.log": evidence / "container.log",
        "container-created-inspect.json": evidence / "container-created-inspect.json",
        "container-final-inspect.json": evidence / "container-final-inspect.json",
        "image-inspect.json": evidence / "image-inspect.json",
        "nvidia-smi-q.txt": evidence / "nvidia-smi-q.txt",
        "slurm-341.out": evidence / "slurm-341.out",
        "slurm-341.err": evidence / "slurm-341.err",
        "source-capsule-manifest.json": evidence / "source-capsule-manifest.json",
        "experiment.yaml": evidence / "experiment.yaml",
        "experiment-validator.py": evidence / "experiment-validator.py",
        "task-manifest.yaml": evidence / "task-manifest.yaml",
        "two-stage-agent-loop.py": evidence / "two-stage-agent-loop.py",
        "two-stage-live-canary.py": evidence / "two-stage-live-canary.py",
        "two-stage-live-runner.py": evidence / "two-stage-live-runner.py",
        "live-canary.py": evidence / "live-canary.py",
        "batch-script.sh": evidence / "batch-script.sh",
        "transport-audit.json": evidence / "transport-audit.json",
        "cpu-admission.json": evidence / "cpu-admission.json",
        "model-receipt.json": evidence / "model-receipt.json",
    }


def _capture(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise TwoStagePartialEvidenceError(f"expected regular file: {path}")
    raw = path.read_bytes()
    zipped = gzip.compress(raw, compresslevel=9, mtime=0)
    return {
        "compression": "gzip-mtime-0",
        "raw_size": len(raw),
        "raw_sha256": _sha(raw),
        "compressed_size": len(zipped),
        "compressed_sha256": _sha(zipped),
        "content_gzip_base64": base64.b64encode(zipped).decode(),
    }


def _decode(receipts: Any) -> dict[str, bytes]:
    if not isinstance(receipts, dict) or set(receipts) != set(_paths(Path())):
        raise TwoStagePartialEvidenceError("partial evidence roster drifted")
    result: dict[str, bytes] = {}
    for name, receipt in receipts.items():
        try:
            zipped = base64.b64decode(receipt["content_gzip_base64"], validate=True)
            raw = gzip.decompress(zipped)
        except (KeyError, TypeError, ValueError, OSError) as exc:
            raise TwoStagePartialEvidenceError(f"{name}: invalid receipt") from exc
        if (
            receipt.get("compression") != "gzip-mtime-0"
            or receipt.get("raw_size") != len(raw)
            or receipt.get("raw_sha256") != _sha(raw)
            or receipt.get("compressed_size") != len(zipped)
            or receipt.get("compressed_sha256") != _sha(zipped)
        ):
            raise TwoStagePartialEvidenceError(f"{name}: receipt drifted")
        result[name] = raw
    return result


def _plan(contract: dict[str, Any]) -> list[dict[str, Any]]:
    tasks = contract.get("tasks")
    if not isinstance(tasks, list) or [task.get("task_id") for task in tasks] != TASK_IDS:
        raise TwoStagePartialEvidenceError("contract task roster drifted")
    return [
        {
            "run_group": "default",
            "model": "qwen3.5-4b",
            "condition": "english_only",
            "task_id": task_id,
            "seed": 42,
        }
        for task_id in TASK_IDS
    ]


def _journal(
    contract: dict[str, Any], raw: bytes, checkpoint: dict[str, Any]
) -> list[dict[str, Any]]:
    rows = [_object(line.encode(), "journal") for line in raw.decode().splitlines()]
    plan = _plan(contract)
    if len(rows) != 2:
        raise TwoStagePartialEvidenceError("partial journal length drifted")
    previous = "0" * 64
    for index, row in enumerate(rows):
        supplied = row.get("row_sha256")
        body = {key: value for key, value in row.items() if key != "row_sha256"}
        if (
            row.get("index") != index
            or row.get("key") != plan[index]
            or row.get("previous_sha256") != previous
            or supplied != sha256_json(body)
            or row.get("payload", {}).get("terminal_status") != "complete"
        ):
            raise TwoStagePartialEvidenceError("partial journal chain drifted")
        previous = str(supplied)
    expected = {
        "schema_version": 1,
        "status": "IN_PROGRESS",
        "contract_sha256": sha256_json(contract),
        "plan_sha256": sha256_json(plan),
        "completed_cells": 2,
        "total_cells": 6,
        "journal_root_sha256": previous,
    }
    if checkpoint != expected:
        raise TwoStagePartialEvidenceError("partial checkpoint drifted")
    return rows


def _validate_capsule(files: dict[str, bytes]) -> None:
    capsule = _object(files["source-capsule-manifest.json"], "source capsule")
    rows = capsule.get("files")
    if (
        not isinstance(rows, list)
        or capsule.get("source_root_sha256") != SOURCE_ROOT
        or _sha(canonical_json(rows).encode()) != SOURCE_ROOT
    ):
        raise TwoStagePartialEvidenceError("source capsule root drifted")
    indexed = {row["path"]: row for row in rows}
    bindings = {
        "experiments/orchvar_qwen35_two_stage_live_smoke.yaml": "experiment.yaml",
        "scripts/validate_orchvar_two_stage_live_experiment.py": (
            "experiment-validator.py"
        ),
        "harness/benchmarks/specs/orchvar_canary_live_v2_tasks.yaml": (
            "task-manifest.yaml"
        ),
        "harness/two_stage_agent_loop.py": "two-stage-agent-loop.py",
        "harness/two_stage_live_canary.py": "two-stage-live-canary.py",
        "harness/two_stage_live_runner.py": "two-stage-live-runner.py",
        "harness/live_canary.py": "live-canary.py",
        "infra/slurm/host-single-node/orchvar-live-smoke.sbatch": "batch-script.sh",
        "research/evidence/harness/orchvar-message-action-transport-audit-v1.json": (
            "transport-audit.json"
        ),
        (
            "research/evidence/harness/"
            "orchvar-two-stage-message-action-cpu-admission-v3.json"
        ): "cpu-admission.json",
    }
    for source, receipt in bindings.items():
        raw = files[receipt]
        expected = {"path": source, "sha256": _sha(raw), "size": len(raw)}
        if indexed.get(source) != expected:
            raise TwoStagePartialEvidenceError(f"capsule binding drifted: {source}")


def _validate_containment(files: dict[str, bytes]) -> None:
    images = json.loads(files["image-inspect.json"])
    created = json.loads(files["container-created-inspect.json"])
    final = json.loads(files["container-final-inspect.json"])
    if not (
        isinstance(images, list)
        and len(images) == 1
        and images[0].get("Id") == IMAGE_ID
        and IMAGE_REGISTRY_DIGEST in images[0].get("RepoDigests", [])
        and isinstance(created, list)
        and len(created) == 1
        and isinstance(final, list)
        and len(final) == 1
    ):
        raise TwoStagePartialEvidenceError("container image identity drifted")
    host = created[0].get("HostConfig", {})
    state = final[0].get("State", {})
    command = created[0].get("Config", {}).get("Cmd", [])
    if (
        created[0].get("Image") != IMAGE_ID
        or host.get("NetworkMode") != "none"
        or host.get("ReadonlyRootfs") is not True
        or host.get("CapDrop") != ["ALL"]
        or "no-new-privileges" not in host.get("SecurityOpt", [])
        or state.get("ExitCode") != 1
        or state.get("OOMKilled") is not False
        or not any("harness.two_stage_live_runner" in str(item) for item in command)
        or "NVIDIA H100 80GB HBM3" not in files["nvidia-smi-q.txt"].decode()
    ):
        raise TwoStagePartialEvidenceError("live containment drifted")


def _validate(files: dict[str, bytes]) -> dict[str, Any]:
    contract = _object(files["contract.json"], "contract")
    checkpoint = _object(files["checkpoint.json"], "checkpoint")
    rows = _journal(contract, files["journal.jsonl"], checkpoint)
    _validate_capsule(files)
    _validate_containment(files)
    termination = _object(files["termination.json"], "termination")
    runtime = contract.get("runtime_context", {})
    actor = contract.get("actor_contract", {})
    extra = contract.get("extra", {})
    model_receipt = _object(files["model-receipt.json"], "model receipt")
    if (
        termination != {"schema_version": 1, "exit_code": 1, "reason": "workload_failed"}
        or contract.get("name") != "orchvar_qwen35_two_stage_live_smoke"
        or runtime.get("source_capsule_root_sha256") != SOURCE_ROOT
        or runtime.get("image_id") != IMAGE_ID
        or runtime.get("slurm_job_id") != "341"
        or actor.get("protocol") != "message-then-action-two-stage-v1"
        or actor.get("backend", {}).get("revision") != MODEL_REVISION
        or actor.get("backend", {}).get("artifact_root_sha256")
        != MODEL_ARTIFACT_ROOT
        or _sha(files["model-receipt.json"]) != MODEL_RECEIPT_SHA256
        or model_receipt.get("revision") != MODEL_REVISION
        or model_receipt.get("artifact_root_sha256") != MODEL_ARTIFACT_ROOT
        or _sha(files["transport-audit.json"])
        != extra.get("transport_audit", {}).get("evidence_sha256")
        or _sha(files["cpu-admission.json"])
        != extra.get("two_stage_cpu_admission", {}).get("evidence_sha256")
    ):
        raise TwoStagePartialEvidenceError("run or model identity drifted")
    first = rows[0]["payload"]["trace"]
    second = rows[1]["payload"]["trace"]
    first_receipts = first.get("backend_stage_receipts", [])
    second_receipts = second.get("backend_stage_receipts", [])
    if (
        rows[0]["payload"].get("cell_status") != "protocol_failure"
        or first.get("protocol_failure", {}).get("code") != "action_contract_invalid"
        or first.get("protocol_failure", {}).get("detail")
        != "action-only tool is unavailable"
        or [receipt.get("compliance") for receipt in first_receipts]
        != ["valid", "valid", "invalid"]
        or first.get("outcome", {}).get("external_model_calls") != 3
        or first.get("outcome", {}).get("local_tool_calls") != 0
        or rows[1]["payload"].get("cell_status") != "benchmark_failure"
        or second.get("protocol_failure") is not None
        or [receipt.get("compliance") for receipt in second_receipts]
        != ["valid", "valid", "valid", "valid", "valid"]
        or second.get("outcome", {}).get("external_model_calls") != 5
        or second.get("outcome", {}).get("local_tool_calls") != 1
        or second.get("outcome", {}).get("tool_calls_correct") != 1
        or second.get("outcome", {}).get("tool_calls_total") != 3
        or second.get("outcome", {}).get("success") is not False
    ):
        raise TwoStagePartialEvidenceError("partial cell projection drifted")
    log = files["container.log"].decode()
    stderr = files["slurm-341.err"].decode()
    unique_error = "sqlite3.IntegrityError: UNIQUE constraint failed: handoffs.case_id"
    if (
        unique_error not in log
        or unique_error not in stderr
        or "INSERT INTO handoffs VALUES (?)" not in log
        or "canary-reasoning-depth-01: FAIL" not in log
        or "canary-context-recall-01: FAIL" not in log
        or "canary-verbosity-sensitive-01" not in TASK_IDS
        or b"CREATE TABLE handoffs(case_id TEXT PRIMARY KEY)" not in files["live-canary.py"]
    ):
        raise TwoStagePartialEvidenceError("unreceipted tool failure drifted")
    prompt_tokens = sum(
        int(receipt["prompt_tokens"])
        for trace in (first, second)
        for receipt in trace["backend_stage_receipts"]
    )
    completion_tokens = sum(
        int(receipt["completion_tokens"])
        for trace in (first, second)
        for receipt in trace["backend_stage_receipts"]
    )
    if prompt_tokens != 2240 or completion_tokens != 520:
        raise TwoStagePartialEvidenceError("partial token projection drifted")
    return {
        "run_id": RUN_ID,
        "slurm_job_id": 341,
        "source_capsule_root_sha256": SOURCE_ROOT,
        "image_id": IMAGE_ID,
        "model_revision": MODEL_REVISION,
        "model_artifact_root_sha256": MODEL_ARTIFACT_ROOT,
        "live_run_complete": False,
        "completed_cells": 2,
        "planned_cells": 6,
        "completed_task_ids": TASK_IDS[:2],
        "next_unjournaled_task_id": TASK_IDS[2],
        "task_success_count": 0,
        "external_model_calls_receipted": 8,
        "local_tool_calls_receipted": 1,
        "prompt_tokens_receipted": prompt_tokens,
        "completion_tokens_receipted": completion_tokens,
        "reasoning_cell": {
            "status": "protocol_failure",
            "failure_code": "action_contract_invalid",
            "failure_detail": "action-only tool is unavailable",
            "message_calls": 2,
            "action_calls": 1,
            "tool_calls": 0,
        },
        "context_cell": {
            "status": "benchmark_failure",
            "message_calls": 3,
            "action_calls": 2,
            "tool_calls_correct": 1,
            "tool_calls_expected": 3,
        },
        "unreceipted_failure": {
            "exception": unique_error,
            "classification": "harness_tool_error_transport_gap",
            "direct_observation": (
                "The fresh per-task SQLite runtime raised a primary-key uniqueness "
                "error during the third planned cell before that cell was journaled."
            ),
            "inference": (
                "Because the handoffs table starts empty and the third task exposes "
                "only create_handoff_note, at least two same-key insert attempts are "
                "required to explain the observed uniqueness error. The raw third-cell "
                "model outputs and receipts were lost and are not claimed."
            ),
        },
        "safety_gate_evaluated": False,
        "safety_reason": "the safety task was not reached",
        "checkpoint": checkpoint,
        "claim_boundary": extra["claim_boundary"],
        "next_gate": (
            "Do not resume or rerun job 341. Preregister and CPU-prove a deterministic "
            "tool-error envelope that preserves failed attempts and partial state, then "
            "reassess whether another live run is warranted."
        ),
    }


def seal_evidence(
    root: Path = DEFAULT_RUN_ROOT, output: Path = DEFAULT_OUTPUT
) -> dict[str, Any]:
    paths = _paths(root)
    files = {name: path.read_bytes() for name, path in paths.items()}
    receipts = {name: _capture(path) for name, path in paths.items()}
    projection = _validate(files)
    projection_sha = sha256_json(projection)
    receipt_roots = {
        name: receipt["raw_sha256"] for name, receipt in receipts.items()
    }
    evidence = {
        "schema_version": 1,
        "status": STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "protocol_gate_passed": False,
        "live_run_complete": False,
        "safety_gate_evaluated": False,
        "projection": projection,
        "projection_sha256": projection_sha,
        "receipts": receipts,
        "evidence_root_sha256": sha256_json(
            {"projection_sha256": projection_sha, "receipt_roots": receipt_roots}
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(canonical_json(evidence) + "\n", encoding="utf-8")
    return evidence


def validate_evidence(path: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    evidence = _object(path.read_bytes(), "evidence")
    if (
        evidence.get("status") != STATUS
        or evidence.get("live_run_complete") is not False
        or evidence.get("safety_gate_evaluated") is not False
    ):
        raise TwoStagePartialEvidenceError("evidence header drifted")
    files = _decode(evidence.get("receipts"))
    projection = _validate(files)
    projection_sha = sha256_json(projection)
    receipt_roots = {
        name: receipt["raw_sha256"] for name, receipt in evidence["receipts"].items()
    }
    root = sha256_json(
        {"projection_sha256": projection_sha, "receipt_roots": receipt_roots}
    )
    if (
        evidence.get("projection") != projection
        or evidence.get("projection_sha256") != projection_sha
        or evidence.get("evidence_root_sha256") != root
    ):
        raise TwoStagePartialEvidenceError("evidence projection drifted")
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
