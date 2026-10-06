#!/usr/bin/env python3
"""Seal and validate portable deterministic OrchVar-Canary admission evidence."""

from __future__ import annotations

import argparse
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

from harness.run_state import ExecutionJournal, canonical_json, sha256_json  # noqa: E402
from scripts.run_orchvar_canary_proof import (  # noqa: E402
    BOUND_FILES,
    RUN_ID,
)

DEFAULT_RUN_ROOT = (
    PROJECT_ROOT / "data/results/orchvar-canary/2026-08-26-local-admission-v1"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "research/evidence/harness/orchvar-canary-local-admission-v1.json"
)
STATUS = "ORCHVAR_CANARY_LOCAL_AGENT_LOOP_ADMISSION_PASS"
CLAIM_BOUNDARY = (
    "Deterministic local harness admission only. This evidence exercises the agent "
    "loop, independent task oracles, exact paired degradation analysis, append-only "
    "checkpoints, a real SIGUSR1 interruption, and exact resume. It is not a "
    "language-routing, model-quality, benchmark-validity, Paper 1, H100, or "
    "publication result."
)
EXPECTED_REGRESSIONS = {
    "english_only_25word_limit": ["verbosity_sensitive"],
    "english_only_low_effort": ["reasoning_depth"],
    "english_only_no_thinking_cache": ["context_recall", "multi_turn_memory"],
}
EXPECTED_OUTPUTS = {
    f"results/{RUN_ID}_degradation.json",
    f"results/{RUN_ID}_summary.json",
    f"traces/orchvar_canary/english_only/{RUN_ID}__default__deterministic-canary-v1.jsonl",
    f"traces/orchvar_canary/english_only_25word_limit/{RUN_ID}__default__deterministic-canary-v1.jsonl",
    f"traces/orchvar_canary/english_only_low_effort/{RUN_ID}__default__deterministic-canary-v1.jsonl",
    f"traces/orchvar_canary/english_only_no_thinking_cache/{RUN_ID}__default__deterministic-canary-v1.jsonl",
}
SUPPORT_FILES = {
    "proof-manifest.json": "manifest.json",
    "contract.json": f"usr1-resumed/run-state/{RUN_ID}/contract.json",
    "checkpoint.json": f"usr1-resumed/run-state/{RUN_ID}/checkpoint.json",
    "checkpoint-ack.json": f"usr1-resumed/run-state/{RUN_ID}/checkpoint-ack.json",
}


class OrchVarCanaryEvidenceError(ValueError):
    """Raised when admission evidence is incomplete, inconsistent, or tampered."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _object(data: bytes, owner: str) -> dict[str, Any]:
    try:
        value = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OrchVarCanaryEvidenceError(f"{owner}: invalid JSON") from exc
    if not isinstance(value, dict):
        raise OrchVarCanaryEvidenceError(f"{owner}: expected JSON object")
    return value


def _capture(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise OrchVarCanaryEvidenceError(f"expected regular file: {path}")
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


def _decode_receipts(
    receipts: Any, expected_names: set[str], owner: str
) -> dict[str, bytes]:
    if not isinstance(receipts, dict) or set(receipts) != expected_names:
        raise OrchVarCanaryEvidenceError(f"{owner}: file roster drifted")
    expected_fields = {
        "compression",
        "raw_size",
        "raw_sha256",
        "compressed_size",
        "compressed_sha256",
        "content_gzip_base64",
    }
    decoded: dict[str, bytes] = {}
    for name, receipt in receipts.items():
        if not isinstance(receipt, dict) or set(receipt) != expected_fields:
            raise OrchVarCanaryEvidenceError(f"{owner}/{name}: receipt drifted")
        try:
            compressed = base64.b64decode(
                receipt["content_gzip_base64"], validate=True
            )
            raw = gzip.decompress(compressed)
        except (KeyError, TypeError, ValueError, OSError) as exc:
            raise OrchVarCanaryEvidenceError(
                f"{owner}/{name}: receipt cannot be decoded"
            ) from exc
        if (
            receipt["compression"] != "gzip-mtime-0"
            or receipt["compressed_size"] != len(compressed)
            or receipt["compressed_sha256"] != _sha(compressed)
            or receipt["raw_size"] != len(raw)
            or receipt["raw_sha256"] != _sha(raw)
        ):
            raise OrchVarCanaryEvidenceError(f"{owner}/{name}: receipt hash drifted")
        decoded[name] = raw
    return decoded


def _validate_manifest(manifest: dict[str, Any]) -> None:
    if (
        manifest.get("status") != "PASS"
        or manifest.get("scientific_result") is not False
        or manifest.get("publication_ready") is not False
        or manifest.get("external_model_calls") != 0
        or manifest.get("external_tool_calls") != 0
        or manifest.get("planned_cells") != 120
        or manifest.get("byte_identical_scientific_outputs") is not True
        or not isinstance(manifest.get("usr1_acknowledged_cells"), int)
        or isinstance(manifest.get("usr1_acknowledged_cells"), bool)
        or not 0 < manifest["usr1_acknowledged_cells"] < 120
        or set(manifest.get("output_sha256", {})) != EXPECTED_OUTPUTS
        or set(manifest.get("bound_source_sha256", {})) != set(BOUND_FILES)
    ):
        raise OrchVarCanaryEvidenceError("proof manifest contract drifted")


def _validate_summary(summary: dict[str, Any], manifest: dict[str, Any]) -> None:
    trace_hashes = {
        item.get("path"): item.get("sha256")
        for item in summary.get("trace_artifacts", [])
        if isinstance(item, dict)
    }
    expected_trace_hashes = {
        path: digest
        for path, digest in manifest["output_sha256"].items()
        if path.startswith("traces/")
    }
    if (
        summary.get("status") != "COMPLETE"
        or summary.get("experiment_id") != RUN_ID
        or summary.get("completed_cells") != 120
        or len(summary.get("summaries", [])) != 4
        or trace_hashes != expected_trace_hashes
        or any(item.get("rows") != 30 for item in summary["trace_artifacts"])
    ):
        raise OrchVarCanaryEvidenceError("runner summary contract drifted")


def _validate_degradation(report: dict[str, Any]) -> None:
    treatments = report.get("treatments")
    if (
        report.get("status") != "PASS"
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("run_id") != RUN_ID
        or not isinstance(treatments, dict)
        or set(treatments) != set(EXPECTED_REGRESSIONS)
    ):
        raise OrchVarCanaryEvidenceError("degradation report contract drifted")
    for treatment, expected in EXPECTED_REGRESSIONS.items():
        result = treatments[treatment]
        if (
            result.get("expected_regressions") != expected
            or result.get("observed_regressions") != expected
            or result.get("matched_pairs") != 30
            or result.get("fisher_expected_categories", {}).get("is_degradation")
            is not True
            or result.get("categories", {}).get("safety_canary", {}).get(
                "is_degradation"
            )
            is not False
        ):
            raise OrchVarCanaryEvidenceError(
                f"degradation treatment drifted: {treatment}"
            )


def _projection(
    manifest: dict[str, Any],
    summary: dict[str, Any],
    degradation: dict[str, Any],
    checkpoint: dict[str, Any],
    ack: dict[str, Any],
) -> dict[str, Any]:
    return {
        "run_id": RUN_ID,
        "planned_cells": manifest["planned_cells"],
        "completed_cells": summary["completed_cells"],
        "usr1_acknowledged_cells": ack["completed_cells"],
        "byte_identical_scientific_outputs": manifest[
            "byte_identical_scientific_outputs"
        ],
        "contract_sha256": checkpoint["contract_sha256"],
        "plan_sha256": checkpoint["plan_sha256"],
        "journal_root_sha256": checkpoint["journal_root_sha256"],
        "output_sha256": manifest["output_sha256"],
        "observed_regressions": {
            treatment: degradation["treatments"][treatment][
                "observed_regressions"
            ]
            for treatment in sorted(EXPECTED_REGRESSIONS)
        },
        "safety_canary_stable": all(
            not degradation["treatments"][treatment]["categories"][
                "safety_canary"
            ]["is_degradation"]
            for treatment in EXPECTED_REGRESSIONS
        ),
        "external_model_calls": manifest["external_model_calls"],
        "external_tool_calls": manifest["external_tool_calls"],
    }


def _validate_live_run(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = _object((root / "manifest.json").read_bytes(), "manifest")
    _validate_manifest(manifest)
    for source, expected in manifest["bound_source_sha256"].items():
        path = PROJECT_ROOT / source
        if not path.is_file() or _sha(path.read_bytes()) != expected:
            raise OrchVarCanaryEvidenceError(f"bound source drifted: {source}")

    lane_bytes: dict[str, dict[str, bytes]] = {}
    journals: dict[str, ExecutionJournal] = {}
    for lane in ("uninterrupted", "usr1-resumed"):
        lane_root = root / lane
        lane_bytes[lane] = {}
        for relative, expected in manifest["output_sha256"].items():
            raw = (lane_root / relative).read_bytes()
            if _sha(raw) != expected:
                raise OrchVarCanaryEvidenceError(
                    f"{lane}/{relative}: scientific output drifted"
                )
            lane_bytes[lane][relative] = raw
        state = lane_root / f"run-state/{RUN_ID}"
        contract = _object((state / "contract.json").read_bytes(), f"{lane}/contract")
        rows = [
            _object(line.encode(), f"{lane}/journal line {index}")
            for index, line in enumerate(
                (state / "journal.jsonl").read_text(encoding="utf-8").splitlines(),
                start=1,
            )
        ]
        journals[lane] = ExecutionJournal(
            state,
            contract=contract,
            plan_keys=[row.get("key") for row in rows],
            resume=True,
        )
        if journals[lane].completed != 120:
            raise OrchVarCanaryEvidenceError(f"{lane}: journal is incomplete")

    if lane_bytes["uninterrupted"] != lane_bytes["usr1-resumed"]:
        raise OrchVarCanaryEvidenceError("scientific outputs are not byte-identical")
    if (
        journals["uninterrupted"].contract != journals["usr1-resumed"].contract
        or journals["uninterrupted"].rows != journals["usr1-resumed"].rows
        or journals["uninterrupted"].journal_root_sha256
        != journals["usr1-resumed"].journal_root_sha256
    ):
        raise OrchVarCanaryEvidenceError("resumed journal differs from uninterrupted")

    summary_name = f"results/{RUN_ID}_summary.json"
    degradation_name = f"results/{RUN_ID}_degradation.json"
    summary = _object(lane_bytes["uninterrupted"][summary_name], "summary")
    degradation = _object(
        lane_bytes["uninterrupted"][degradation_name], "degradation"
    )
    _validate_summary(summary, manifest)
    _validate_degradation(degradation)
    checkpoint = _object(
        (root / f"usr1-resumed/run-state/{RUN_ID}/checkpoint.json").read_bytes(),
        "checkpoint",
    )
    ack = _object(
        (root / f"usr1-resumed/run-state/{RUN_ID}/checkpoint-ack.json").read_bytes(),
        "checkpoint acknowledgement",
    )
    if (
        checkpoint.get("status") != "COMPLETE"
        or checkpoint.get("completed_cells") != 120
        or checkpoint.get("total_cells") != 120
        or checkpoint.get("contract_sha256") != summary.get("contract_sha256")
        or checkpoint.get("plan_sha256") != summary.get("plan_sha256")
        or checkpoint.get("journal_root_sha256")
        != summary.get("journal_root_sha256")
        or ack.get("signal") != "SIGUSR1"
        or ack.get("completed_cells") != manifest["usr1_acknowledged_cells"]
        or ack.get("journal_root_sha256")
        != journals["usr1-resumed"].rows[ack["completed_cells"] - 1]["row_sha256"]
    ):
        raise OrchVarCanaryEvidenceError("checkpoint or SIGUSR1 receipt drifted")
    return manifest, _projection(manifest, summary, degradation, checkpoint, ack)


def _evidence_root(bundle: dict[str, Any]) -> str:
    body = {key: value for key, value in bundle.items() if key != "evidence_root_sha256"}
    return sha256_json(body)


def validate_evidence(bundle_or_path: dict[str, Any] | Path) -> dict[str, Any]:
    """Validate a self-contained evidence bundle and return its stable projection."""
    if isinstance(bundle_or_path, Path):
        bundle = _object(bundle_or_path.read_bytes(), "evidence bundle")
    else:
        bundle = bundle_or_path
    if (
        bundle.get("schema_version") != 1
        or bundle.get("status") != STATUS
        or bundle.get("evidence_kind") != "deterministic-agent-loop-admission-proof"
        or bundle.get("evidence_grade") != "local-admission-reproduced"
        or bundle.get("scientific_result") is not False
        or bundle.get("publication_ready") is not False
        or bundle.get("claim_boundary") != CLAIM_BOUNDARY
        or bundle.get("evidence_root_sha256") != _evidence_root(bundle)
    ):
        raise OrchVarCanaryEvidenceError("evidence envelope drifted")

    scientific = _decode_receipts(
        bundle.get("scientific_outputs"), EXPECTED_OUTPUTS, "scientific outputs"
    )
    support = _decode_receipts(
        bundle.get("supporting_receipts"), set(SUPPORT_FILES), "supporting receipts"
    )
    manifest = _object(support["proof-manifest.json"], "proof manifest")
    _validate_manifest(manifest)
    for name, raw in scientific.items():
        if _sha(raw) != manifest["output_sha256"][name]:
            raise OrchVarCanaryEvidenceError(f"manifest output hash drifted: {name}")

    summary = _object(scientific[f"results/{RUN_ID}_summary.json"], "summary")
    degradation = _object(
        scientific[f"results/{RUN_ID}_degradation.json"], "degradation"
    )
    contract = _object(support["contract.json"], "contract")
    checkpoint = _object(support["checkpoint.json"], "checkpoint")
    ack = _object(support["checkpoint-ack.json"], "checkpoint acknowledgement")
    _validate_summary(summary, manifest)
    _validate_degradation(degradation)
    if (
        sha256_json(contract) != checkpoint.get("contract_sha256")
        or checkpoint.get("status") != "COMPLETE"
        or checkpoint.get("completed_cells") != 120
        or checkpoint.get("total_cells") != 120
        or checkpoint.get("contract_sha256") != summary.get("contract_sha256")
        or checkpoint.get("plan_sha256") != summary.get("plan_sha256")
        or checkpoint.get("journal_root_sha256")
        != summary.get("journal_root_sha256")
        or ack.get("signal") != "SIGUSR1"
        or ack.get("completed_cells") != manifest["usr1_acknowledged_cells"]
        or not 0 < ack["completed_cells"] < checkpoint["completed_cells"]
    ):
        raise OrchVarCanaryEvidenceError("portable checkpoint receipt drifted")
    projection = _projection(manifest, summary, degradation, checkpoint, ack)
    if (
        bundle.get("stable_projection") != projection
        or bundle.get("stable_projection_sha256") != sha256_json(projection)
    ):
        raise OrchVarCanaryEvidenceError("stable projection drifted")
    return projection


def seal(root: Path = DEFAULT_RUN_ROOT, output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    """Validate the live proof and write one self-contained evidence artifact."""
    manifest, projection = _validate_live_run(root)
    scientific = {
        name: _capture(root / "uninterrupted" / name)
        for name in sorted(EXPECTED_OUTPUTS)
    }
    support = {
        name: _capture(root / relative)
        for name, relative in sorted(SUPPORT_FILES.items())
    }
    bundle: dict[str, Any] = {
        "schema_version": 1,
        "status": STATUS,
        "evidence_kind": "deterministic-agent-loop-admission-proof",
        "evidence_grade": "local-admission-reproduced",
        "scientific_result": False,
        "publication_ready": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_state": manifest["source_state"],
        "bound_source_sha256": manifest["bound_source_sha256"],
        "stable_projection": projection,
        "stable_projection_sha256": sha256_json(projection),
        "scientific_outputs": scientific,
        "supporting_receipts": support,
    }
    bundle["evidence_root_sha256"] = _evidence_root(bundle)
    validate_evidence(bundle)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(canonical_json(bundle) + "\n", encoding="utf-8")
    return bundle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--validate", type=Path)
    args = parser.parse_args()
    if args.validate:
        projection = validate_evidence(args.validate)
        print(f"OrchVar-Canary evidence valid: {sha256_json(projection)}")
        return 0
    bundle = seal(args.run_root, args.output)
    print(f"OrchVar-Canary evidence sealed: {bundle['evidence_root_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
