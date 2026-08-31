#!/usr/bin/env python3
"""Seal the receipted tool-error CPU admission proof."""

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
from scripts import run_orchvar_tool_error_transport_cpu_admission as admission  # noqa: E402

RUN_ID = admission.RUN_ID
STATUS = admission.STATUS
BOUND_FILES = admission.BOUND_FILES
DEFAULT_RUN_ROOT = admission.DEFAULT_OUTPUT
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "research/evidence/harness/"
    "orchvar-tool-error-transport-cpu-admission-v1.json"
)


class ToolErrorTransportEvidenceError(ValueError):
    """Raised when tool-error transport evidence is incomplete or tampered."""


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _object(raw: bytes, owner: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ToolErrorTransportEvidenceError(f"{owner}: invalid JSON") from exc
    if not isinstance(value, dict):
        raise ToolErrorTransportEvidenceError(f"{owner}: expected object")
    return value


def _paths(root: Path) -> dict[str, Path]:
    uninterrupted = root / "uninterrupted"
    resumed = root / "interrupted-resumed"
    paths = {
        "manifest.json": root / "manifest.json",
        "uninterrupted/report.json": uninterrupted / "report.json",
        "uninterrupted/contract.json": uninterrupted
        / f"run-state/{RUN_ID}/contract.json",
        "uninterrupted/journal.jsonl": uninterrupted
        / f"run-state/{RUN_ID}/journal.jsonl",
        "uninterrupted/checkpoint.json": uninterrupted
        / f"run-state/{RUN_ID}/checkpoint.json",
        "resumed/report.json": resumed / "report.json",
        "resumed/contract.json": resumed / f"run-state/{RUN_ID}/contract.json",
        "resumed/journal.jsonl": resumed / f"run-state/{RUN_ID}/journal.jsonl",
        "resumed/checkpoint.json": resumed / f"run-state/{RUN_ID}/checkpoint.json",
        "resumed/checkpoint-ack.json": resumed
        / f"run-state/{RUN_ID}/checkpoint-ack.json",
    }
    paths.update({f"source/{path}": PROJECT_ROOT / path for path in BOUND_FILES})
    return paths


def _capture(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise ToolErrorTransportEvidenceError(f"expected regular file: {path}")
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
        raise ToolErrorTransportEvidenceError("tool-error evidence roster drifted")
    result: dict[str, bytes] = {}
    for name, receipt in receipts.items():
        try:
            zipped = base64.b64decode(receipt["content_gzip_base64"], validate=True)
            raw = gzip.decompress(zipped)
        except (KeyError, TypeError, ValueError, OSError) as exc:
            raise ToolErrorTransportEvidenceError(f"{name}: invalid receipt") from exc
        if (
            receipt.get("compression") != "gzip-mtime-0"
            or receipt.get("raw_size") != len(raw)
            or receipt.get("raw_sha256") != _sha(raw)
            or receipt.get("compressed_size") != len(zipped)
            or receipt.get("compressed_sha256") != _sha(zipped)
        ):
            raise ToolErrorTransportEvidenceError(f"{name}: receipt drifted")
        result[name] = raw
    return result


def _journal(
    contract: dict[str, Any], raw: bytes, checkpoint: dict[str, Any]
) -> list[dict[str, Any]]:
    rows = [_object(line.encode(), "journal") for line in raw.decode().splitlines()]
    if len(rows) != 7:
        raise ToolErrorTransportEvidenceError("tool-error journal length drifted")
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
            raise ToolErrorTransportEvidenceError("tool-error journal chain drifted")
        previous = str(supplied)
        keys.append(row["key"])
    expected = {
        "schema_version": 1,
        "status": "COMPLETE",
        "contract_sha256": sha256_json(contract),
        "plan_sha256": sha256_json(keys),
        "completed_cells": 7,
        "total_cells": 7,
        "journal_root_sha256": previous,
    }
    if checkpoint != expected:
        raise ToolErrorTransportEvidenceError("tool-error checkpoint drifted")
    return rows


def _validate(files: dict[str, bytes]) -> dict[str, Any]:
    manifest = _object(files["manifest.json"], "manifest")
    report = _object(files["uninterrupted/report.json"], "report")
    resumed_report = _object(files["resumed/report.json"], "resumed report")
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
        files["uninterrupted/report.json"] != files["resumed/report.json"]
        or files["uninterrupted/journal.jsonl"] != files["resumed/journal.jsonl"]
        or contract != resumed_contract
        or rows != resumed_rows
        or report != resumed_report
    ):
        raise ToolErrorTransportEvidenceError("tool-error resume is not byte-identical")
    bound = contract.get("bound_source_sha256")
    if not isinstance(bound, dict) or set(bound) != set(BOUND_FILES):
        raise ToolErrorTransportEvidenceError("tool-error bound source roster drifted")
    for path, expected in bound.items():
        if _sha(files[f"source/{path}"]) != expected:
            raise ToolErrorTransportEvidenceError(f"tool-error source drifted: {path}")
    cells = report.get("cells")
    if (
        report.get("status") != "COMPLETE"
        or report.get("run_id") != RUN_ID
        or report.get("completed_cells") != 7
        or not isinstance(cells, list)
        or len(cells) != 7
    ):
        raise ToolErrorTransportEvidenceError("tool-error report drifted")
    baseline = cells[:6]
    duplicate = cells[6]
    receipt = duplicate.get("tool_runtime_receipt", {})
    attempts = receipt.get("attempts", [])
    expected_error = {
        "ok": False,
        "error": {
            "code": "sqlite_constraint_violation",
            "tool": "create_handoff_note",
            "message": "tool mutation violated a uniqueness constraint",
            "retryable": False,
        },
    }
    totals = {
        "attempts": sum(cell["tool_runtime_receipt"]["attempt_count"] for cell in cells),
        "successes": sum(cell["tool_runtime_receipt"]["success_count"] for cell in cells),
        "errors": sum(cell["tool_runtime_receipt"]["error_count"] for cell in cells),
        "decisions": sum(cell["decision_count"] for cell in cells),
    }
    if (
        any(cell.get("scenario") != "baseline" for cell in baseline)
        or sum(cell.get("protocol_passed") is True for cell in baseline) != 6
        or duplicate.get("scenario") != "duplicate_mutation_recovery"
        or duplicate.get("protocol_passed") is not True
        or duplicate.get("error_observed_before_final") is not True
        or totals != {"attempts": 11, "successes": 10, "errors": 1, "decisions": 18}
        or [attempt.get("status") for attempt in attempts] != ["success", "error"]
        or attempts[1].get("result") != expected_error
        or duplicate.get("observations", [])[-1].get("result") != expected_error
        or receipt.get("delegate_receipt", {}).get("operation_count") != 1
    ):
        raise ToolErrorTransportEvidenceError("tool-error cell projection drifted")
    falsifier = manifest.get("unexpected_exception_falsifier")
    if (
        manifest.get("status") != STATUS
        or manifest.get("scientific_result") is not False
        or manifest.get("publication_ready") is not False
        or manifest.get("external_model_calls") != 0
        or manifest.get("completed_cells") != 7
        or manifest.get("baseline_successes") != 6
        or manifest.get("tool_attempt_count") != 11
        or manifest.get("tool_success_count") != 10
        or manifest.get("tool_error_count") != 1
        or manifest.get("decision_count") != 18
        or manifest.get("duplicate_error_observed_before_final") is not True
        or falsifier
        != {
            "error": {
                "type": "RuntimeError",
                "detail": "unexpected transport failure",
            },
            "attempt_count": 0,
        }
        or ack.get("signal") != "SIGUSR1"
        or ack.get("completed_cells") != 3
        or manifest.get("report_sha256") != _sha(files["uninterrupted/report.json"])
        or manifest.get("journal_sha256")
        != _sha(files["uninterrupted/journal.jsonl"])
    ):
        raise ToolErrorTransportEvidenceError("tool-error manifest drifted")
    return {
        "run_id": RUN_ID,
        "completed_cells": 7,
        "baseline_successes": 6,
        "external_model_calls": 0,
        "tool_attempt_count": totals["attempts"],
        "tool_success_count": totals["successes"],
        "tool_error_count": totals["errors"],
        "decision_count": totals["decisions"],
        "duplicate_error_observed_before_final": True,
        "unexpected_exception_propagated": True,
        "actual_usr1_acknowledged_cells": 3,
        "byte_identical_report": True,
        "byte_identical_journal": True,
        "report_sha256": manifest["report_sha256"],
        "journal_sha256": manifest["journal_sha256"],
        "contract_sha256": manifest["contract_sha256"],
        "plan_sha256": manifest["plan_sha256"],
        "journal_root_sha256": manifest["journal_root_sha256"],
        "error_result": expected_error,
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
    if evidence.get("status") != STATUS:
        raise ToolErrorTransportEvidenceError("tool-error evidence header drifted")
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
        raise ToolErrorTransportEvidenceError("tool-error evidence projection drifted")
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
