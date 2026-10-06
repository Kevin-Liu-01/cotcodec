#!/usr/bin/env python3
"""Construct the MemPalace control only from a completed equivalence bundle.

The ordinary memory freezer must not be able to instantiate the current-lock
port from a runtime receipt alone.  This module verifies the complete matched
port audit, binds both direct and port runtime receipts, and then exposes one
normal ``MemorySystem``-shaped object to the existing freezer.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from harness.memory_trials.mempalace_control import (
    MemPalaceEquivalenceEvidence,
    MemPalaceRawSessionMemorySystem,
)
from harness.memory_trials.schema import canonical_json, sha256_text
from harness.memory_trials.systems import (
    MemorySelection,
    MemorySystemReceipt,
    MemorySystemRequest,
)
from scripts.audit_mempalace_port_equivalence import (
    _summarize,
    _validate_completed,
)
from scripts.mempalace_upstream_adapter import PinnedUpstreamMemPalaceAdapter
from scripts.run_mempalace_upstream_reproduction import (
    ReproductionExpectations,
    _load_runtime_receipt,
)

EQUIVALENCE_FILES = (
    "contract.json",
    "journal.jsonl",
    "manifest.json",
    "progress.json",
    "report.json",
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _regular_file(path: Path, owner: str) -> Path:
    resolved = path.resolve(strict=True)
    if path.is_symlink() or not resolved.is_file():
        raise ValueError(f"{owner} must be a regular non-symlink file")
    return resolved


def _json_object(path: Path, owner: str) -> dict[str, Any]:
    path = _regular_file(path, owner)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{owner} is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{owner} must contain one JSON object")
    return payload


def _equivalence_journal(path: Path) -> tuple[list[dict[str, Any]], str]:
    path = _regular_file(path, "MemPalace equivalence journal")
    encoded = path.read_bytes()
    if not encoded or not encoded.endswith(b"\n"):
        raise ValueError("MemPalace equivalence journal is empty or incomplete")
    records: list[dict[str, Any]] = []
    previous = "0" * 64
    question_ids: set[str] = set()
    for index, line in enumerate(encoded.splitlines()):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError("MemPalace equivalence journal contains invalid JSON") from exc
        if not isinstance(record, dict):
            raise ValueError("MemPalace equivalence journal row must be an object")
        unsigned = {key: value for key, value in record.items() if key != "record_sha256"}
        question_id = record.get("question_id")
        result = record.get("result")
        if (
            record.get("schema_version") != 1
            or record.get("index") != index
            or not isinstance(question_id, str)
            or not question_id
            or question_id in question_ids
            or record.get("previous_record_sha256") != previous
            or not isinstance(result, dict)
            or result.get("question_id") != question_id
            or record.get("record_sha256") != sha256_text(canonical_json(unsigned))
        ):
            raise ValueError("MemPalace equivalence journal identity or hash chain drifted")
        question_ids.add(question_id)
        records.append(record)
        previous = record["record_sha256"]
    return records, previous


def _equivalence_bundle_root(root: Path) -> str:
    manifest = [
        {
            "path": name,
            "size": (root / name).stat().st_size,
            "sha256": _sha256_file(root / name),
        }
        for name in EQUIVALENCE_FILES
    ]
    return sha256_text(canonical_json(manifest))


@dataclass(frozen=True)
class VerifiedMemPalaceControl:
    """A normal memory system plus the evidence bundle that admitted it."""

    system: MemPalaceRawSessionMemorySystem
    evidence_root: Path
    admission_evidence: MemPalaceEquivalenceEvidence

    @property
    def identity(self) -> str:
        return self.system.identity

    @property
    def receipt(self) -> MemorySystemReceipt:
        return self.system.receipt

    def select(self, request: MemorySystemRequest) -> MemorySelection:
        return self.system.select(request)


def build_verified_mempalace_control(
    *,
    source_root: Path,
    equivalence_root: Path,
    expected_equivalence_contract_sha256: str,
    expected_equivalence_bundle_root_sha256: str,
    direct_runtime_receipt_path: Path,
    expected_direct_runtime_receipt_sha256: str,
    port_runtime_receipt_path: Path,
    expected_port_runtime_receipt_sha256: str,
    implementation_kind: Literal["in_process_reference", "oci_sidecar"] = (
        "in_process_reference"
    ),
) -> VerifiedMemPalaceControl:
    """Verify the exact port audit and construct the frozen-selection control."""

    root = equivalence_root.resolve(strict=True)
    if equivalence_root.is_symlink() or not root.is_dir():
        raise ValueError("MemPalace equivalence root must be a non-symlink directory")
    actual_names = {path.name for path in root.iterdir()}
    if actual_names != set(EQUIVALENCE_FILES):
        raise ValueError("MemPalace equivalence bundle file roster drifted")
    for name in EQUIVALENCE_FILES:
        _regular_file(root / name, f"MemPalace equivalence {name}")
    if re.fullmatch(r"[0-9a-f]{64}", expected_equivalence_bundle_root_sha256) is None:
        raise ValueError("expected MemPalace equivalence bundle root is malformed")
    equivalence_bundle_root_sha256 = _equivalence_bundle_root(root)
    if equivalence_bundle_root_sha256 != expected_equivalence_bundle_root_sha256:
        raise ValueError("MemPalace equivalence bundle root drifted")

    contract = _json_object(root / "contract.json", "MemPalace equivalence contract")
    unsigned_contract = {
        key: value for key, value in contract.items() if key != "contract_sha256"
    }
    contract_sha256 = sha256_text(canonical_json(unsigned_contract))
    if (
        contract.get("schema_version") != 2
        or contract.get("status") != "MEMPALACE_MATCHED_PORT_EQUIVALENCE_CONTRACT"
        or contract.get("scientific_result") is not False
        or contract.get("contract_sha256") != contract_sha256
        or contract_sha256 != expected_equivalence_contract_sha256
    ):
        raise ValueError("MemPalace equivalence contract identity drifted")

    expectations = ReproductionExpectations()
    direct_runtime, direct_runtime_sha256 = _load_runtime_receipt(
        _regular_file(direct_runtime_receipt_path, "direct runtime receipt"),
        expectations,
    )
    port_runtime, port_runtime_sha256 = _load_runtime_receipt(
        _regular_file(port_runtime_receipt_path, "port runtime receipt"),
        expectations,
    )
    if direct_runtime_sha256 != expected_direct_runtime_receipt_sha256:
        raise ValueError("direct runtime receipt differs from the registered control")
    if port_runtime_sha256 != expected_port_runtime_receipt_sha256:
        raise ValueError("port runtime receipt differs from the registered control")
    direct_contract = contract.get("direct_reproduction")
    if (
        not isinstance(direct_contract, dict)
        or direct_contract.get("runtime_receipt_sha256") != direct_runtime_sha256
        or direct_contract.get("runtime") != direct_runtime
    ):
        raise ValueError("direct runtime receipt is not bound by the equivalence contract")
    port_contract = contract.get("port")
    if (
        not isinstance(port_contract, dict)
        or port_contract.get("runtime_receipt_sha256") != port_runtime_sha256
        or port_contract.get("runtime") != port_runtime
    ):
        raise ValueError("port runtime receipt is not bound by the equivalence contract")

    records, previous = _equivalence_journal(root / "journal.jsonl")
    if len(records) != 500:
        raise ValueError("MemPalace control requires the complete 500-task audit")
    manifest = _validate_completed(
        output_dir=root,
        records=records,
        previous_sha256=previous,
        contract=contract,
    )
    report = _summarize(records)
    if (
        manifest.get("task_count") != 500
        or manifest.get("all_gates_pass") is not True
        or report.get("status") != "EXACT_MATCHED_PORT_EQUIVALENCE_PASS"
        or not all(report.get("gates", {}).values())
    ):
        raise ValueError("MemPalace matched-port equivalence did not pass every gate")

    evidence = MemPalaceEquivalenceEvidence(
        equivalence_contract_sha256=contract_sha256,
        equivalence_manifest_sha256=manifest["manifest_sha256"],
        equivalence_manifest_file_sha256=_sha256_file(root / "manifest.json"),
        equivalence_report_sha256=_sha256_file(root / "report.json"),
        equivalence_journal_sha256=_sha256_file(root / "journal.jsonl"),
        equivalence_bundle_root_sha256=equivalence_bundle_root_sha256,
        direct_runtime_receipt_sha256=direct_runtime_sha256,
        port_runtime_receipt_sha256=port_runtime_sha256,
    )
    adapter = PinnedUpstreamMemPalaceAdapter(
        source_root=source_root,
        runtime_receipt_path=port_runtime_receipt_path,
        expected_runtime_receipt_sha256=port_runtime_sha256,
        implementation_kind=implementation_kind,
    )
    system = MemPalaceRawSessionMemorySystem(
        adapter,
        equivalence_evidence=evidence,
    )
    return VerifiedMemPalaceControl(
        system=system,
        evidence_root=root,
        admission_evidence=evidence,
    )
