from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

import pytest

from scripts.seal_memory_evidence import (
    EvidenceError,
    _decode_captured_files,
    validate_mem0_lifecycle_files,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = (
    PROJECT_ROOT / "research" / "evidence" / "memory" / "mem0-lifecycle-adapter-v6.json"
)


def _files() -> dict[str, bytes]:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    return _decode_captured_files(payload["files"])


def _canonical_sha(payload: object) -> str:
    data = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return hashlib.sha256(data).hexdigest()


def _rewrite_report(files: dict[str, bytes], run: int, report: dict) -> None:
    prefix = f"run-{run}"
    report_bytes = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode()
    files[f"{prefix}/report.json"] = report_bytes
    files[f"{prefix}/stdout.txt"] = report_bytes
    report_receipt = {
        "bytes": len(report_bytes),
        "sha256": hashlib.sha256(report_bytes).hexdigest(),
    }
    manifest = json.loads(files[f"{prefix}/manifest.json"])
    manifest["artifacts"] = {"report.json": report_receipt}
    manifest["artifact_root_sha256"] = _canonical_sha(manifest["artifacts"])
    files[f"{prefix}/manifest.json"] = (
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    ).encode()


def test_sealed_mem0_lifecycle_negative_recomputes() -> None:
    verified = validate_mem0_lifecycle_files(_files())
    assert verified["stable_projection"]["crash_recovery"] == {
        "continuation_recovered": False,
        "fail_closed": True,
        "plaintext_residue_cleared": False,
        "plaintext_residue_file_count": 2,
    }
    assert all(verified["stable_projection"]["gates"].values())
    assert len(set(verified["report_sha256s"])) == 2
    assert len(verified["crash_scope_plaintext_proof_roots"]) == 2


def test_mem0_lifecycle_gate_tamper_fails_closed() -> None:
    files = _files()
    report = json.loads(files["run-2/report.json"])
    report["stable_projection"]["gates"]["interrupted_operation_fail_closed"] = False
    files["run-2/report.json"] = (
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    ).encode()
    with pytest.raises(
        EvidenceError,
        match="output transport drifted|manifest drifted|result semantics drifted",
    ):
        validate_mem0_lifecycle_files(files)


def test_mem0_lifecycle_self_consistent_residue_drift_fails_closed() -> None:
    files = _files()
    report = json.loads(files["run-2/report.json"])
    report["crash_scope_plaintext_hits"] = []
    recovery = report["stable_projection"]["crash_recovery"]
    recovery["plaintext_residue_cleared"] = True
    recovery["plaintext_residue_file_count"] = 0
    report["stable_projection_sha256"] = _canonical_sha(report["stable_projection"])
    _rewrite_report(files, 2, report)
    with pytest.raises(EvidenceError, match="result semantics drifted"):
        validate_mem0_lifecycle_files(files)


def test_mem0_lifecycle_plaintext_proof_tamper_fails_closed() -> None:
    files = _files()
    report = json.loads(files["run-2/report.json"])
    path = report["crash_scope_plaintext_hits"][0]
    report["crash_scope_plaintext_proofs"][path][0]["window_base64"] = base64.b64encode(
        b"not-the-crash-canary"
    ).decode("ascii")
    _rewrite_report(files, 2, report)
    with pytest.raises(EvidenceError, match="crash plaintext proof drifted"):
        validate_mem0_lifecycle_files(files)


def test_mem0_lifecycle_copied_run_with_cost_noise_fails_closed() -> None:
    files = _files()
    for name in ("manifest.json", "report.json", "stderr.txt", "stdout.txt"):
        files[f"run-2/{name}"] = files[f"run-1/{name}"]
    report = json.loads(files["run-2/report.json"])
    report["costs"][0]["latency_ms"] += 1.0
    _rewrite_report(files, 2, report)
    with pytest.raises(EvidenceError, match="not distinct with equal projections"):
        validate_mem0_lifecycle_files(files)


def test_mem0_lifecycle_image_label_tamper_fails_closed() -> None:
    files = _files()
    inspect = json.loads(files["image-inspect.json"])
    inspect[0]["Config"]["Labels"]["org.cotcodec.scientific-result"] = "true"
    files["image-inspect.json"] = json.dumps(inspect).encode()
    with pytest.raises(EvidenceError, match="image receipt drifted"):
        validate_mem0_lifecycle_files(files)


def test_mem0_lifecycle_embedded_receipts_match_payload() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    for name, receipt in payload["files"].items():
        data = base64.b64decode(receipt["content_base64"], validate=True)
        assert len(data) == receipt["bytes"], name
