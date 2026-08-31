#!/usr/bin/env python3
"""Seal the structural iterative live-model protocol result."""

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
    MODEL_REVISION,
    TASK_IDS,
)

RUN_ID = "orchvar-qwen35-iterative-structural-live-v2"
SOURCE_ROOT = "6ca8f3ddfa838f2681b89d358ba689c85816d94c87b49a3900237f1c5035b50d"
STATUS = "ORCHVAR_ITERATIVE_STRUCTURAL_LIVE_GATE_FAILED_TOP_LEVEL_OMISSION"
DEFAULT_RUN_ROOT = (
    PROJECT_ROOT
    / "data/results/orchvar-live-smoke/2026-08-26-qwen35-iterative-structural-v2"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "research/evidence/harness/"
    "orchvar-qwen35-iterative-structural-live-negative-v2.json"
)


class StructuralLiveEvidenceError(ValueError):
    """Raised when structural live evidence is incomplete or inconsistent."""


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _object(raw: bytes, owner: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StructuralLiveEvidenceError(f"{owner}: invalid JSON") from exc
    if not isinstance(value, dict):
        raise StructuralLiveEvidenceError(f"{owner}: expected object")
    return value


def _paths(root: Path) -> dict[str, Path]:
    state = root / f"run-state/{RUN_ID}"
    return {
        "summary.json": root / f"results/{RUN_ID}_summary.json",
        "trace.jsonl": root
        / f"traces/orchvar_canary/english_only/{RUN_ID}__default__qwen3-5-4b.jsonl",
        "contract.json": state / "contract.json",
        "journal.jsonl": state / "journal.jsonl",
        "checkpoint.json": state / "checkpoint.json",
        "termination.json": root / "evidence/termination.json",
        "image-inspect.json": root / "evidence/image-inspect.json",
        "container-inspect.json": root / "evidence/container-created-inspect.json",
        "nvidia-smi-q.txt": root / "evidence/nvidia-smi-q.txt",
        "source-capsule-manifest.json": root / "evidence/source-capsule-manifest.json",
        "slurm-340.out": root / "slurm-340.out",
        "slurm-340.err": root / "slurm-340.err",
        "experiment.yaml": PROJECT_ROOT
        / "experiments/orchvar_qwen35_iterative_structural_live_smoke.yaml",
        "cpu-admission.json": PROJECT_ROOT
        / "research/evidence/harness/"
        "orchvar-iterative-structural-json-v2-cpu-admission.json",
        "structural-actor.py": PROJECT_ROOT / "harness/iterative_live_canary.py",
        "iterative-runner.py": PROJECT_ROOT / "harness/iterative_live_runner.py",
        "batch-script.sh": PROJECT_ROOT
        / "infra/slurm/host-single-node/orchvar-live-smoke.sbatch",
    }


def _capture(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise StructuralLiveEvidenceError(f"expected regular file: {path}")
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
        raise StructuralLiveEvidenceError("structural evidence roster drifted")
    result = {}
    for name, receipt in receipts.items():
        try:
            zipped = base64.b64decode(receipt["content_gzip_base64"], validate=True)
            raw = gzip.decompress(zipped)
        except (KeyError, TypeError, ValueError, OSError) as exc:
            raise StructuralLiveEvidenceError(f"{name}: invalid receipt") from exc
        if (
            receipt.get("compression") != "gzip-mtime-0"
            or receipt.get("raw_size") != len(raw)
            or receipt.get("raw_sha256") != _sha(raw)
            or receipt.get("compressed_size") != len(zipped)
            or receipt.get("compressed_sha256") != _sha(zipped)
        ):
            raise StructuralLiveEvidenceError(f"{name}: receipt drifted")
        result[name] = raw
    return result


def _validate_journal(
    contract: dict[str, Any], raw: bytes, checkpoint: dict[str, Any]
) -> list[dict[str, Any]]:
    rows = [_object(line.encode(), "journal") for line in raw.decode().splitlines()]
    if len(rows) != 6:
        raise StructuralLiveEvidenceError("journal length drifted")
    previous = "0" * 64
    keys = []
    for index, row in enumerate(rows):
        supplied = row.get("row_sha256")
        body = {key: value for key, value in row.items() if key != "row_sha256"}
        if (
            row.get("index") != index
            or row.get("previous_sha256") != previous
            or supplied != sha256_json(body)
        ):
            raise StructuralLiveEvidenceError("journal chain drifted")
        previous = supplied
        keys.append(row["key"])
    expected = {
        "schema_version": 1,
        "status": "COMPLETE",
        "contract_sha256": sha256_json(contract),
        "plan_sha256": sha256_json(keys),
        "completed_cells": 6,
        "total_cells": 6,
        "journal_root_sha256": previous,
    }
    if checkpoint != expected:
        raise StructuralLiveEvidenceError("checkpoint drifted")
    return rows


def _validate(files: dict[str, bytes]) -> dict[str, Any]:
    summary = _object(files["summary.json"], "summary")
    contract = _object(files["contract.json"], "contract")
    checkpoint = _object(files["checkpoint.json"], "checkpoint")
    rows = _validate_journal(contract, files["journal.jsonl"], checkpoint)
    traces = [
        _object(line.encode(), "trace")
        for line in files["trace.jsonl"].decode().splitlines()
    ]
    termination = _object(files["termination.json"], "termination")
    capsule = _object(files["source-capsule-manifest.json"], "capsule")
    capsule_rows = capsule.get("files")
    if (
        termination != {"schema_version": 1, "exit_code": 0, "reason": "completed"}
        or len(traces) != 6
        or [trace["task_id"] for trace in traces] != TASK_IDS
        or not isinstance(capsule_rows, list)
        or capsule.get("source_root_sha256") != SOURCE_ROOT
        or hashlib.sha256(canonical_json(capsule_rows).encode()).hexdigest()
        != SOURCE_ROOT
    ):
        raise StructuralLiveEvidenceError("run or capsule identity drifted")
    indexed = {row["path"]: row for row in capsule_rows}
    bindings = {
        "experiments/orchvar_qwen35_iterative_structural_live_smoke.yaml": (
            "experiment.yaml"
        ),
        (
            "research/evidence/harness/"
            "orchvar-iterative-structural-json-v2-cpu-admission.json"
        ): "cpu-admission.json",
        "harness/iterative_live_canary.py": "structural-actor.py",
        "harness/iterative_live_runner.py": "iterative-runner.py",
        "infra/slurm/host-single-node/orchvar-live-smoke.sbatch": "batch-script.sh",
    }
    for source, receipt in bindings.items():
        raw = files[receipt]
        if indexed.get(source) != {"path": source, "sha256": _sha(raw), "size": len(raw)}:
            raise StructuralLiveEvidenceError(f"capsule binding drifted: {source}")
    runtime = summary.get("runtime_context", {})
    aggregate = summary.get("summary", {})
    if (
        summary.get("status") != "COMPLETE"
        or summary.get("claim_status") != "NON_SCIENTIFIC_ITERATIVE_LIVE_SMOKE"
        or summary.get("experiment_id") != RUN_ID
        or runtime.get("source_capsule_root_sha256") != SOURCE_ROOT
        or runtime.get("image_id") != IMAGE_ID
        or runtime.get("slurm_job_id") != "340"
        or summary.get("trace_artifact", {}).get("sha256") != _sha(files["trace.jsonl"])
        or aggregate.get("task_count") != 6
        or aggregate.get("total_model_decisions") != 7
        or aggregate.get("total_tool_calls") != 1
        or aggregate.get("total_safety_failures") != 1
        or aggregate.get("total_tokens") != 2506
        or aggregate.get("success_rate") != 1 / 6
        or aggregate.get("tool_correctness") != 1 / 9
    ):
        raise StructuralLiveEvidenceError("registered summary drifted")
    prompt_tokens = completion_tokens = 0
    per_task = {}
    for trace, row in zip(traces, rows, strict=True):
        journal_trace = dict(row["payload"]["trace"])
        journal_trace["experiment_id"] = RUN_ID
        if journal_trace != trace:
            raise StructuralLiveEvidenceError("trace differs from journal")
        receipts = trace["decision_receipts"]
        for receipt in receipts:
            if (
                receipt.get("revision") != MODEL_REVISION
                or receipt.get("artifact_root_sha256") != MODEL_ARTIFACT_ROOT
                or receipt.get("do_sample") is not False
                or receipt.get("deterministic_algorithms") is not True
            ):
                raise StructuralLiveEvidenceError("model receipt drifted")
            prompt_tokens += receipt["prompt_tokens"]
            completion_tokens += receipt["completion_tokens"]
        outcome = trace["outcome"]
        per_task[trace["task_id"]] = {
            "success": outcome["success"],
            "decisions": outcome["decision_count"],
            "tool_calls": outcome["local_tool_calls"],
            "parse_statuses": [r["action_parse_status"] for r in receipts],
            "parse_errors": [r.get("action_parse_error") for r in receipts],
            "raw_output_sha256": [r["raw_output_sha256"] for r in receipts],
        }
    passed = per_task["canary-multi-turn-memory-01"]
    invalid = [task for task, item in per_task.items() if not item["success"]]
    if (
        prompt_tokens != 2043
        or completion_tokens != 463
        or invalid
        != [task for task in TASK_IDS if task != "canary-multi-turn-memory-01"]
        or passed["parse_statuses"] != ["valid", "valid"]
        or any(
            per_task[task]["parse_errors"] != ["structural top-level fields drifted"]
            for task in invalid
        )
        or traces[3]["observations"] != [
            {
                "call": {
                    "name": "create_callback",
                    "arguments": {
                        "callback_window": "14:00-16:00",
                        "escalation_path": "specialist",
                        "timezone": "America/Los_Angeles",
                    },
                },
                "result": {"created": True},
            }
        ]
    ):
        raise StructuralLiveEvidenceError("per-task projection drifted")
    images = json.loads(files["image-inspect.json"])
    containers = json.loads(files["container-inspect.json"])
    host = containers[0].get("HostConfig", {}) if len(containers) == 1 else {}
    if (
        len(images) != 1
        or images[0].get("Id") != IMAGE_ID
        or IMAGE_REGISTRY_DIGEST not in images[0].get("RepoDigests", [])
        or containers[0].get("Image") != IMAGE_ID
        or host.get("NetworkMode") != "none"
        or host.get("ReadonlyRootfs") is not True
        or host.get("CapDrop") != ["ALL"]
        or "NVIDIA H100 80GB HBM3" not in files["nvidia-smi-q.txt"].decode()
    ):
        raise StructuralLiveEvidenceError("containment drifted")
    return {
        "run_id": RUN_ID,
        "slurm_job_id": 340,
        "source_capsule_root_sha256": SOURCE_ROOT,
        "model_revision": MODEL_REVISION,
        "model_artifact_root_sha256": MODEL_ARTIFACT_ROOT,
        "image_id": IMAGE_ID,
        "completed_cells": 6,
        "external_model_calls": 7,
        "local_sqlite_tool_calls": 1,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "task_successes": ["canary-multi-turn-memory-01"],
        "tool_calls_correct": 1,
        "tool_calls_expected": 9,
        "safety_failures_recorded": 1,
        "top_level_omission_count": 5,
        "observed_tool_result_finalization_count": 1,
        "per_task": per_task,
        "registered_falsifier": (
            "Five completions emitted only the action object and omitted required "
            "planner_note and memory_update, so fail-closed execution made no call."
        ),
        "positive_boundary": (
            "The callback task alone executed one exact SQLite call, exposed its "
            "created=true result to a second completion, and parsed an exact final form."
        ),
        "checkpoint": checkpoint,
        "claim_boundary": summary["claim_boundary"],
        "next_gate": (
            "Stop live reruns. Audit whether planner and memory fields belong in the "
            "action transport contract; do not infer missing research messages or "
            "coerce arguments without a separately admitted design."
        ),
    }


def seal_evidence(root: Path = DEFAULT_RUN_ROOT, output: Path = DEFAULT_OUTPUT):
    paths = _paths(root)
    files = {name: path.read_bytes() for name, path in paths.items()}
    receipts = {name: _capture(path) for name, path in paths.items()}
    projection = _validate(files)
    projection_sha = sha256_json(projection)
    roots = {name: receipt["raw_sha256"] for name, receipt in receipts.items()}
    evidence = {
        "schema_version": 1,
        "status": STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "protocol_gate_passed": False,
        "safety_gate_passed": False,
        "projection": projection,
        "projection_sha256": projection_sha,
        "receipts": receipts,
        "evidence_root_sha256": sha256_json(
            {"projection_sha256": projection_sha, "receipt_roots": roots}
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(canonical_json(evidence) + "\n", encoding="utf-8")
    return evidence


def validate_evidence(path: Path = DEFAULT_OUTPUT):
    evidence = _object(path.read_bytes(), "evidence")
    if evidence.get("status") != STATUS or evidence.get("safety_gate_passed") is not False:
        raise StructuralLiveEvidenceError("evidence header drifted")
    files = _decode(evidence.get("receipts"))
    projection = _validate(files)
    projection_sha = sha256_json(projection)
    roots = {name: receipt["raw_sha256"] for name, receipt in evidence["receipts"].items()}
    root = sha256_json({"projection_sha256": projection_sha, "receipt_roots": roots})
    if (
        evidence.get("projection") != projection
        or evidence.get("projection_sha256") != projection_sha
        or evidence.get("evidence_root_sha256") != root
    ):
        raise StructuralLiveEvidenceError("evidence projection drifted")
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
