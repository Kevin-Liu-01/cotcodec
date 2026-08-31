#!/usr/bin/env python3
"""Seal the exact-source two-stage runner integration CPU proof."""

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
from scripts import run_orchvar_two_stage_runner_integration_cpu as admission  # noqa: E402

RUN_ID = admission.RUN_ID
STATUS = admission.STATUS
BOUND_FILES = admission.BOUND_FILES
DEFAULT_RUN_ROOT = admission.DEFAULT_OUTPUT
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "research/evidence/harness/"
    "orchvar-two-stage-runner-tool-error-cpu-admission-v1.json"
)
TRACE_RELATIVE = (
    "traces/orchvar_canary/english_only/"
    f"{RUN_ID}__default__deterministic-two-stage-runner-fixture.jsonl"
)
SUMMARY_RELATIVE = f"results/{RUN_ID}_summary.json"


class RunnerIntegrationEvidenceError(ValueError):
    """Raised when runner integration evidence is incomplete or tampered."""


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _object(raw: bytes, owner: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RunnerIntegrationEvidenceError(f"{owner}: invalid JSON") from exc
    if not isinstance(value, dict):
        raise RunnerIntegrationEvidenceError(f"{owner}: expected object")
    return value


def _paths(root: Path) -> dict[str, Path]:
    uninterrupted = root / "uninterrupted"
    resumed = root / "interrupted-resumed"
    unexpected = root / "unexpected-exception"
    budget = root / "budget-exhaustion"
    paths = {
        "manifest.json": root / "manifest.json",
        "uninterrupted/summary.json": uninterrupted / SUMMARY_RELATIVE,
        "uninterrupted/trace.jsonl": uninterrupted / TRACE_RELATIVE,
        "uninterrupted/contract.json": uninterrupted
        / f"run-state/{RUN_ID}/contract.json",
        "uninterrupted/journal.jsonl": uninterrupted
        / f"run-state/{RUN_ID}/journal.jsonl",
        "uninterrupted/checkpoint.json": uninterrupted
        / f"run-state/{RUN_ID}/checkpoint.json",
        "resumed/summary.json": resumed / SUMMARY_RELATIVE,
        "resumed/trace.jsonl": resumed / TRACE_RELATIVE,
        "resumed/contract.json": resumed / f"run-state/{RUN_ID}/contract.json",
        "resumed/journal.jsonl": resumed / f"run-state/{RUN_ID}/journal.jsonl",
        "resumed/checkpoint.json": resumed / f"run-state/{RUN_ID}/checkpoint.json",
        "resumed/checkpoint-ack.json": resumed
        / f"run-state/{RUN_ID}/checkpoint-ack.json",
        "unexpected/falsifier.json": unexpected / "falsifier.json",
        "unexpected/contract.json": unexpected / f"run-state/{RUN_ID}/contract.json",
        "unexpected/checkpoint.json": unexpected
        / f"run-state/{RUN_ID}/checkpoint.json",
        "budget/falsifier.json": budget / "falsifier.json",
        "budget/contract.json": budget / f"run-state/{RUN_ID}/contract.json",
        "budget/checkpoint.json": budget / f"run-state/{RUN_ID}/checkpoint.json",
    }
    paths.update({f"source/{path}": PROJECT_ROOT / path for path in BOUND_FILES})
    return paths


def _capture(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise RunnerIntegrationEvidenceError(f"expected regular file: {path}")
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
        raise RunnerIntegrationEvidenceError("runner evidence roster drifted")
    result: dict[str, bytes] = {}
    for name, receipt in receipts.items():
        try:
            zipped = base64.b64decode(receipt["content_gzip_base64"], validate=True)
            raw = gzip.decompress(zipped)
        except (KeyError, TypeError, ValueError, OSError) as exc:
            raise RunnerIntegrationEvidenceError(f"{name}: invalid receipt") from exc
        if (
            receipt.get("compression") != "gzip-mtime-0"
            or receipt.get("raw_size") != len(raw)
            or receipt.get("raw_sha256") != _sha(raw)
            or receipt.get("compressed_size") != len(zipped)
            or receipt.get("compressed_sha256") != _sha(zipped)
        ):
            raise RunnerIntegrationEvidenceError(f"{name}: receipt drifted")
        result[name] = raw
    return result


def _journal(
    contract: dict[str, Any], raw: bytes, checkpoint: dict[str, Any]
) -> list[dict[str, Any]]:
    rows = [_object(line.encode(), "journal") for line in raw.decode().splitlines()]
    if len(rows) != 6:
        raise RunnerIntegrationEvidenceError("runner journal length drifted")
    previous = "0" * 64
    keys = []
    for index, row in enumerate(rows):
        supplied = row.get("row_sha256")
        body = {key: value for key, value in row.items() if key != "row_sha256"}
        if (
            row.get("index") != index
            or row.get("previous_sha256") != previous
            or supplied != sha256_json(body)
            or row.get("payload", {}).get("terminal_status") != "complete"
        ):
            raise RunnerIntegrationEvidenceError("runner journal chain drifted")
        previous = str(supplied)
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
        raise RunnerIntegrationEvidenceError("runner checkpoint drifted")
    return rows


def _validate(files: dict[str, bytes]) -> dict[str, Any]:
    manifest = _object(files["manifest.json"], "manifest")
    summary = _object(files["uninterrupted/summary.json"], "summary")
    resumed_summary = _object(files["resumed/summary.json"], "resumed summary")
    contract = _object(files["uninterrupted/contract.json"], "contract")
    resumed_contract = _object(files["resumed/contract.json"], "resumed contract")
    checkpoint = _object(files["uninterrupted/checkpoint.json"], "checkpoint")
    resumed_checkpoint = _object(files["resumed/checkpoint.json"], "resumed checkpoint")
    ack = _object(files["resumed/checkpoint-ack.json"], "checkpoint ack")
    rows = _journal(contract, files["uninterrupted/journal.jsonl"], checkpoint)
    resumed_rows = _journal(
        resumed_contract, files["resumed/journal.jsonl"], resumed_checkpoint
    )
    if (
        files["uninterrupted/summary.json"] != files["resumed/summary.json"]
        or files["uninterrupted/trace.jsonl"] != files["resumed/trace.jsonl"]
        or files["uninterrupted/journal.jsonl"] != files["resumed/journal.jsonl"]
        or contract != resumed_contract
        or rows != resumed_rows
        or summary != resumed_summary
    ):
        raise RunnerIntegrationEvidenceError("runner resume is not byte-identical")
    bound = manifest.get("bound_source_sha256")
    if not isinstance(bound, dict) or set(bound) != set(BOUND_FILES):
        raise RunnerIntegrationEvidenceError("runner bound source roster drifted")
    for path, expected in bound.items():
        if _sha(files[f"source/{path}"]) != expected:
            raise RunnerIntegrationEvidenceError(f"runner source drifted: {path}")
    traces = [
        _object(line.encode(), "trace")
        for line in files["uninterrupted/trace.jsonl"].decode().splitlines()
    ]
    if len(traces) != 6:
        raise RunnerIntegrationEvidenceError("runner trace length drifted")
    for trace, row in zip(traces, rows, strict=True):
        journal_trace = dict(row["payload"]["trace"])
        journal_trace["experiment_id"] = RUN_ID
        if trace != journal_trace:
            raise RunnerIntegrationEvidenceError("trace differs from journal")
    aggregate = summary.get("summary", {})
    verbosity = next(
        trace for trace in traces if trace["task_id"] == "canary-verbosity-sensitive-01"
    )
    safety = next(trace for trace in traces if trace["task_id"] == "canary-safety-01")
    verbosity_receipt = verbosity.get("tool_runtime_receipt", {})
    observed_error = any(
        receipt.get("observed_tool_error") is True
        for receipt in verbosity.get("backend_stage_receipts", [])
        if receipt.get("stage") == "action"
    )
    if (
        summary.get("status") != "COMPLETE"
        or summary.get("claim_status")
        != "NON_SCIENTIFIC_TWO_STAGE_RUNNER_CPU_DOCTOR"
        or summary.get("experiment_id") != RUN_ID
        or summary.get("completed_cells") != 6
        or summary.get("trace_artifact", {}).get("sha256")
        != _sha(files["uninterrupted/trace.jsonl"])
        or summary.get("runtime_context") != admission.RUNTIME_CONTEXT
        or aggregate.get("success_rate") != 5 / 6
        or aggregate.get("protocol_failures") != 0
        or aggregate.get("total_safety_failures") != 0
        or aggregate.get("total_external_model_calls") != 38
        or aggregate.get("total_tool_calls") != 10
        or aggregate.get("total_tool_successes") != 9
        or aggregate.get("total_tool_errors") != 1
        or verbosity.get("outcome", {}).get("success") is not False
        or verbosity_receipt.get("attempt_count") != 2
        or verbosity_receipt.get("success_count") != 1
        or verbosity_receipt.get("error_count") != 1
        or observed_error is not True
        or safety.get("outcome", {}).get("success") is not True
        or safety.get("outcome", {}).get("safety_failures") != 0
        or "refuse" not in safety.get("task_result", {}).get("final_response", "").casefold()
    ):
        raise RunnerIntegrationEvidenceError("runner trace projection drifted")
    unexpected = _object(files["unexpected/falsifier.json"], "unexpected falsifier")
    budget = _object(files["budget/falsifier.json"], "budget falsifier")
    unexpected_checkpoint = _object(
        files["unexpected/checkpoint.json"], "unexpected checkpoint"
    )
    budget_checkpoint = _object(files["budget/checkpoint.json"], "budget checkpoint")
    if (
        unexpected.get("checkpoint") != unexpected_checkpoint
        or budget.get("checkpoint") != budget_checkpoint
        or unexpected_checkpoint.get("status") != "IN_PROGRESS"
        or unexpected_checkpoint.get("completed_cells") != 0
        or budget_checkpoint.get("status") != "IN_PROGRESS"
        or budget_checkpoint.get("completed_cells") != 0
        or unexpected.get("error")
        != {"type": "RuntimeError", "detail": "unexpected runner tool failure"}
        or "prompt_tokens" not in budget.get("error", {}).get("detail", "")
        or ack.get("signal") != "SIGUSR1"
        or ack.get("completed_cells") != 2
    ):
        raise RunnerIntegrationEvidenceError("runner falsifier projection drifted")
    expected_manifest = {
        "completed_cells": 6,
        "benchmark_successes": 5,
        "benchmark_failures": 1,
        "protocol_failures": 0,
        "safety_failures": 0,
        "tool_attempts": 10,
        "tool_successes": 9,
        "tool_errors": 1,
        "simulated_backend_stage_receipts": 38,
        "actual_usr1_acknowledged_cells": 2,
    }
    if (
        manifest.get("status") != STATUS
        or manifest.get("scientific_result") is not False
        or manifest.get("publication_ready") is not False
        or manifest.get("live_model_result") is not False
        or manifest.get("h100_admission") is not False
        or manifest.get("external_model_calls") != 0
        or any(manifest.get(key) != value for key, value in expected_manifest.items())
        or manifest.get("duplicate_error_observed_before_final") is not True
        or manifest.get("unexpected_runtime_exception_aborts_before_append") is not True
        or manifest.get("budget_exhaustion_aborts_before_append") is not True
        or manifest.get("byte_identical_report") is not True
        or manifest.get("byte_identical_trace") is not True
        or manifest.get("byte_identical_journal") is not True
        or manifest.get("report_sha256") != _sha(files["uninterrupted/summary.json"])
        or manifest.get("trace_sha256") != _sha(files["uninterrupted/trace.jsonl"])
        or manifest.get("journal_sha256") != _sha(files["uninterrupted/journal.jsonl"])
    ):
        raise RunnerIntegrationEvidenceError("runner manifest drifted")
    return {
        "run_id": RUN_ID,
        **expected_manifest,
        "external_model_calls": 0,
        "live_model_result": False,
        "h100_admission": False,
        "duplicate_error_observed_before_final": True,
        "unexpected_runtime_exception_aborts_before_append": True,
        "budget_exhaustion_aborts_before_append": True,
        "safety_task_reached_and_passed": True,
        "byte_identical_report": True,
        "byte_identical_trace": True,
        "byte_identical_journal": True,
        "report_sha256": manifest["report_sha256"],
        "trace_sha256": manifest["trace_sha256"],
        "journal_sha256": manifest["journal_sha256"],
        "contract_sha256": manifest["contract_sha256"],
        "plan_sha256": manifest["plan_sha256"],
        "journal_root_sha256": manifest["journal_root_sha256"],
        "bound_source_sha256": bound,
        "claim_boundary": manifest["claim_boundary"],
        "next_gate": manifest["next_gate"],
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
        "live_model_result": False,
        "h100_admission": False,
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
        or evidence.get("live_model_result") is not False
        or evidence.get("h100_admission") is not False
    ):
        raise RunnerIntegrationEvidenceError("runner evidence header drifted")
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
        raise RunnerIntegrationEvidenceError("runner evidence projection drifted")
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
