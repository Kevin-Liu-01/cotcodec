#!/usr/bin/env python3
"""Validate the retained Neo4j identical-tuple H100 parity evidence."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = (
    PROJECT_ROOT
    / "research/evidence/memory/neo4j-identical-tuple-flat-parity-h100-v1.json"
)
STATUS = "NEO4J_IDENTICAL_TUPLE_TRAVERSAL_COMPONENT_PASS"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class EvidenceError(ValueError):
    """Raised when retained parity evidence is incomplete or inconsistent."""


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise EvidenceError(f"expected regular file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise EvidenceError(f"expected JSON object: {path}")
    return value


def validate_evidence(path: Path = DEFAULT_EVIDENCE) -> dict[str, Any]:
    evidence = _load(path)
    if (
        evidence.get("schema_version") != 1
        or evidence.get("source_id") != "neo4j-agent-memory"
        or evidence.get("study") != "neo4j-identical-tuple-flat-parity-v1"
        or evidence.get("status") != STATUS
        or evidence.get("evidence_role")
        != "cluster-amd64-designed-traversal-component"
        or evidence.get("scientific_result") is not False
        or evidence.get("publication_ready") is not False
        or evidence.get("slurm_job_id") != 304
        or evidence.get("slurm_h100_count") != 1
        or evidence.get("container_gpu_count") != 0
        or evidence.get("model_calls") != 0
    ):
        raise EvidenceError("top-level evidence contract drifted")
    root = PROJECT_ROOT / evidence["artifact_root"]
    if root.is_symlink() or not root.is_dir():
        raise EvidenceError("artifact root is missing or unsafe")
    artifacts = evidence.get("artifact_sha256")
    if not isinstance(artifacts, dict) or not artifacts:
        raise EvidenceError("artifact hash roster is missing")
    for relative, expected in artifacts.items():
        if not isinstance(expected, str) or not SHA256_RE.fullmatch(expected):
            raise EvidenceError(f"invalid artifact digest: {relative}")
        target = root / relative
        if _sha(target) != expected:
            raise EvidenceError(f"artifact digest drifted: {relative}")
    for section, path_key, hash_key in (
        (evidence["source_archive"], "path", "sha256"),
        (evidence["source_archive"], "receipt_path", "receipt_sha256"),
        (evidence["runtime_inputs"], "client_image_archive_path", "client_image_archive_sha256"),
        (evidence["runtime_inputs"], "client_sbom_path", "client_sbom_sha256"),
    ):
        if _sha(PROJECT_ROOT / section[path_key]) != section[hash_key]:
            raise EvidenceError(f"external input drifted: {path_key}")
    report = _load(root / "parity-304/report.json")
    component = evidence["component"]
    projection = report.get("semantic_projection")
    if (
        report.get("status") != STATUS
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("slurm_h100_count") != 1
        or report.get("container_gpu_count") != 0
        or report.get("model_calls") != 0
        or not isinstance(projection, dict)
        or projection.get("case_count") != component["case_count"]
        or projection.get("tuple_count") != component["tuple_count"]
        or projection.get("top_k") != component["top_k"]
        or projection.get("max_injected_bytes") != component["max_injected_bytes"]
        or projection.get("tuple_payload_sha256") != component["tuple_payload_sha256"]
        or projection.get("hit_counts") != component["hit_counts"]
        or not all(projection.get("gates", {}).values())
        or len(report.get("repeats", [])) != component["clean_repetitions"]
    ):
        raise EvidenceError("report semantic projection drifted")
    projections = []
    for repeat in report["repeats"]:
        component_report = repeat.get("component_report")
        if not isinstance(component_report, dict):
            raise EvidenceError("repeat component report is missing")
        supplied = component_report.get("report_sha256")
        body = {
            key: value
            for key, value in component_report.items()
            if key != "report_sha256"
        }
        canonical = (
            json.dumps(body, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode()
        if supplied != hashlib.sha256(canonical).hexdigest():
            raise EvidenceError("repeat component self-hash drifted")
        projections.append(
            {
                key: value
                for key, value in component_report.items()
                if key not in {"elapsed_seconds", "report_sha256"}
            }
        )
    if projections[0] != projections[1] or projections[0] != projection:
        raise EvidenceError("clean repetition projection drifted")
    manifest = _load(root / "parity-304/manifest.json")
    expected_manifest_files = {
        "experiment.yaml": {
            "bytes": (root / "parity-304/experiment.yaml").stat().st_size,
            "sha256": artifacts["parity-304/experiment.yaml"],
        },
        "report.json": {
            "bytes": (root / "parity-304/report.json").stat().st_size,
            "sha256": artifacts["parity-304/report.json"],
        },
    }
    if (
        manifest.get("status") != STATUS
        or manifest.get("files") != expected_manifest_files
        or manifest.get("root_sha256")
        != hashlib.sha256(
            (json.dumps(expected_manifest_files, indent=2, sort_keys=True) + "\n").encode()
        ).hexdigest()
    ):
        raise EvidenceError("parity manifest drifted")
    receipt = _load(root / "job-304.receipt.json")
    runtime = evidence["runtime_inputs"]
    if (
        receipt.get("slurm_job_id") != 304
        or receipt.get("slurm_job_name") != "cotcodec-neo4j-flat-parity"
        or receipt.get("client_image_id") != runtime["client_image_id"]
        or receipt.get("client_image_archive_sha256")
        != runtime["client_image_archive_sha256"]
        or receipt.get("client_sbom_sha256") != runtime["client_sbom_sha256"]
        or receipt.get("batch_sha256") != runtime["batch_sha256"]
        or receipt.get("report_sha256") != artifacts["parity-304/report.json"]
        or receipt.get("manifest_sha256") != artifacts["parity-304/manifest.json"]
        or receipt.get("container_gpu_count") != 0
        or receipt.get("model_calls") != 0
    ):
        raise EvidenceError("job receipt binding drifted")
    scontrol = (root / "scontrol-304.txt").read_text(encoding="utf-8")
    if not all(
        token in scontrol
        for token in (
            "JobId=304",
            "JobState=COMPLETED",
            "ExitCode=0:0",
            "NodeList=fal-h100-01",
            "TresPerNode=gres:gpu:h100:1",
        )
    ):
        raise EvidenceError("Slurm completion evidence drifted")
    if (root / "sacct-304.txt").read_text(encoding="utf-8").strip() != (
        "Slurm accounting storage is disabled"
    ):
        raise EvidenceError("sacct limitation drifted")
    return evidence


def main() -> int:
    evidence = validate_evidence()
    print(
        "Neo4j flat-parity H100 evidence PASS: "
        f"job {evidence['slurm_job_id']}, status {evidence['status']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
