#!/usr/bin/env python3
"""Seal and validate MemForest's exact-source lifecycle negative."""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validate_memforest_lifecycle_experiment import (  # noqa: E402
    EXPECTED_STATUS,
    validate_experiment_contract,
)

DEFAULT_ROOT = PROJECT_ROOT / "data/results/memforest-lifecycle/2026-08-17-local-docker-v1"
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "research/evidence/memory/memforest-native-lifecycle-negative-v1.json"
)
REVISION = "fb4320a84d296bf7b0752d7ef1f2ad0726ae0b22"
TREE = "2e30793c77ef0b7fc8b36bd6d3648a1d9f2fecb2"
ARCHIVE_SHA256 = "3809857bcd1f2fb799038a604149a1354277f80dd87893c7f2e3949c743211e0"
ARCHIVE_BYTES = 183019520
IMAGE_ID = "sha256:33326b6049ab910889d472504d37f0f1b42ba481345f7b3af6e86b50f80a7ba6"
STABLE_PROJECTION_SHA256 = "ad833d7d60e6ff0e2590d2be2890a98f4fb656499314cc1a5e268965acc3d08b"
REPORT_SHA256 = "0c73e4e3c1da9e975f821c46411c90994397f76f84f19f49231960fdb1c6da45"
MANIFEST_SHA256 = "eb543945d9f476e4b76566cdae5e8400f45375d871244aad53a1c57ebf4da4cb"
CLAIM_BOUNDARY = (
    "Exact pinned public MemForest tenant registration, deterministic-fake ingest, "
    "save, restart, saved session deletion, tenant-path confinement, interrupted "
    "multi-file save recovery, native tenant-purge surface, bounded current-file "
    "plaintext scan, and synthetic incremental-versus-rebuild write diagnostics; "
    "not model extraction quality, semantic retrieval quality, secure filesystem "
    "erasure, sustained serving throughput, localized-maintenance causal effect, "
    "H100 actor quality, or publication evidence."
)
ARTIFACT_NAMES = {
    "Dockerfile",
    "docker-build.txt",
    "doctor-image-inspect.json",
    "doctor.py",
    "experiment.yaml",
    "manifest.json",
    "pip-freeze.txt",
    "repeat-1-phase-1.txt",
    "repeat-1-phase-2.txt",
    "repeat-1-phase-3.txt",
    "repeat-1-phase-4.txt",
    "repeat-1.json",
    "repeat-2-phase-1.txt",
    "repeat-2-phase-2.txt",
    "repeat-2-phase-3.txt",
    "repeat-2-phase-4.txt",
    "repeat-2.json",
    "report.json",
    "source-receipt.json",
}
MANIFEST_FILE_NAMES = (ARTIFACT_NAMES - {"manifest.json"}) | {"source.tar"}
CODE_PATHS = {
    "experiments/memory/stage3-memforest-native-lifecycle-doctor.yaml": (
        PROJECT_ROOT / "experiments/memory/stage3-memforest-native-lifecycle-doctor.yaml"
    ),
    "infra/memory-baselines/memforest/Dockerfile": (
        PROJECT_ROOT / "infra/memory-baselines/memforest/Dockerfile"
    ),
    "infra/memory-baselines/memforest/doctor.py": (
        PROJECT_ROOT / "infra/memory-baselines/memforest/doctor.py"
    ),
    "scripts/run_memforest_lifecycle_doctor.py": (
        PROJECT_ROOT / "scripts/run_memforest_lifecycle_doctor.py"
    ),
    "scripts/seal_memforest_lifecycle_evidence.py": Path(__file__).resolve(),
    "scripts/validate_memforest_lifecycle_experiment.py": (
        PROJECT_ROOT / "scripts/validate_memforest_lifecycle_experiment.py"
    ),
}
PHASE_CHECKS = [
    {
        "absolute_user_id_overrides_snapshot_root",
        "alias_equivalent_user_ids_share_storage",
        "native_tenant_purge_absent",
        "normal_user_initial_save_complete",
        "relative_user_id_escapes_snapshot_root",
    },
    {
        "interrupted_save_exception_observed",
        "interrupted_save_in_memory_contains_new_session",
        "normal_user_survives_first_restart",
        "saved_session_delete_completed_before_restart",
    },
    {
        "interrupted_save_exposes_mixed_component_generations",
        "post_delete_plaintext_scan_completed",
        "saved_session_delete_survives_restart",
        "write_path_diagnostic_completed",
    },
    {
        "absolute_escape_artifact_survives_restart",
        "alias_collision_artifact_survives_restart",
        "mixed_component_generations_survive_second_restart",
        "relative_escape_artifact_survives_restart",
    },
]
STATIC_FINDINGS = {
    "public_tenant_purge_method_absent",
    "register_user_joins_unvalidated_user_id",
    "save_writes_components_sequentially",
}
EXPECTED_FINDINGS = set().union(*PHASE_CHECKS, STATIC_FINDINGS)
DIRECT_REQUIREMENTS = {
    "aiosqlite==0.20.0",
    "faiss-cpu==1.9.0.post1",
    "fastapi==0.115.6",
    "httpx==0.28.1",
    "numpy==2.2.0",
    "openai==1.57.4",
    "pydantic==2.10.3",
    "pytest-asyncio==0.24.0",
    "pytest==8.3.4",
    "PyYAML==6.0.2",
    "tqdm==4.67.1",
    "uvicorn==0.32.1",
}
TOKEN_RE = re.compile(r"^[0-9A-F]{16}$")


class MemForestLifecycleEvidenceError(ValueError):
    """Raised when retained MemForest lifecycle evidence is incomplete or drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _object(data: bytes, owner: str) -> dict[str, Any]:
    def reject(value: str) -> None:
        raise MemForestLifecycleEvidenceError(f"{owner} contains non-finite JSON {value}")

    try:
        payload = json.loads(data, parse_constant=reject)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MemForestLifecycleEvidenceError(f"{owner} is not strict JSON") from exc
    if not isinstance(payload, dict):
        raise MemForestLifecycleEvidenceError(f"{owner} must be an object")
    return payload


def _capture(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise MemForestLifecycleEvidenceError(f"expected regular evidence input: {path}")
    raw = path.read_bytes()
    compressed = gzip.compress(raw, mtime=0)
    return {
        "compression": "gzip-mtime-0",
        "raw_size": len(raw),
        "raw_sha256": _sha(raw),
        "compressed_size": len(compressed),
        "compressed_sha256": _sha(compressed),
        "content_gzip_base64": base64.b64encode(compressed).decode(),
    }


def _decode(receipts: Any) -> dict[str, bytes]:
    if not isinstance(receipts, dict) or set(receipts) != ARTIFACT_NAMES:
        raise MemForestLifecycleEvidenceError("MemForest lifecycle artifact roster drifted")
    files: dict[str, bytes] = {}
    expected_fields = {
        "compression",
        "raw_size",
        "raw_sha256",
        "compressed_size",
        "compressed_sha256",
        "content_gzip_base64",
    }
    for name, receipt in receipts.items():
        if not isinstance(receipt, dict) or set(receipt) != expected_fields:
            raise MemForestLifecycleEvidenceError(f"invalid artifact receipt: {name}")
        try:
            compressed = base64.b64decode(receipt["content_gzip_base64"], validate=True)
            raw = gzip.decompress(compressed)
        except (TypeError, ValueError, OSError) as exc:
            raise MemForestLifecycleEvidenceError(f"cannot decode artifact: {name}") from exc
        if (
            receipt["compression"] != "gzip-mtime-0"
            or receipt["compressed_size"] != len(compressed)
            or receipt["compressed_sha256"] != _sha(compressed)
            or receipt["raw_size"] != len(raw)
            or receipt["raw_sha256"] != _sha(raw)
        ):
            raise MemForestLifecycleEvidenceError(f"artifact receipt drifted: {name}")
        files[name] = raw
    return files


def _validate_code(bundle: dict[str, Any], root: Path) -> None:
    receipts = bundle.get("code_files")
    if not isinstance(receipts, dict) or set(receipts) != set(CODE_PATHS):
        raise MemForestLifecycleEvidenceError("MemForest lifecycle code roster drifted")
    for name, expected in receipts.items():
        path = root / name
        if (
            not isinstance(expected, str)
            or len(expected) != 64
            or path.is_symlink()
            or not path.is_file()
            or _sha(path.read_bytes()) != expected
        ):
            raise MemForestLifecycleEvidenceError(f"MemForest lifecycle code drifted: {name}")


def _validate_manifest(files: dict[str, bytes]) -> dict[str, Any]:
    manifest = _object(files["manifest.json"], "MemForest lifecycle manifest")
    declared = manifest.get("files")
    if (
        manifest.get("schema_version") != 1
        or manifest.get("status") != EXPECTED_STATUS
        or manifest.get("file_count") != len(MANIFEST_FILE_NAMES)
        or not isinstance(declared, dict)
        or set(declared) != MANIFEST_FILE_NAMES
        or declared.get("source.tar") != ARCHIVE_SHA256
        or _sha(files["manifest.json"]) != MANIFEST_SHA256
    ):
        raise MemForestLifecycleEvidenceError("MemForest lifecycle manifest drifted")
    for name in ARTIFACT_NAMES - {"manifest.json"}:
        if declared.get(name) != _sha(files[name]):
            raise MemForestLifecycleEvidenceError(f"manifest hash drifted: {name}")
    return manifest


def _validate_source(files: dict[str, bytes]) -> dict[str, Any]:
    receipt = _object(files["source-receipt.json"], "MemForest lifecycle source receipt")
    if (
        receipt.get("revision") != REVISION
        or receipt.get("tree") != TREE
        or receipt.get("archive_sha256") != ARCHIVE_SHA256
        or receipt.get("archive_bytes") != ARCHIVE_BYTES
        or receipt.get("static_source_checks")
        != {finding: True for finding in sorted(STATIC_FINDINGS)}
    ):
        raise MemForestLifecycleEvidenceError("MemForest lifecycle source receipt drifted")
    return receipt


def _validate_image(files: dict[str, bytes]) -> None:
    try:
        rows = json.loads(files["doctor-image-inspect.json"])
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MemForestLifecycleEvidenceError("MemForest image inspection is invalid") from exc
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise MemForestLifecycleEvidenceError("MemForest image inspection roster drifted")
    image = rows[0]
    config = image.get("Config") or {}
    labels = config.get("Labels") or {}
    if (
        image.get("Id") != IMAGE_ID
        or image.get("Architecture") != "arm64"
        or image.get("Os") != "linux"
        or config.get("User") != "65532:65532"
        or set(config.get("Volumes") or {}) != {"/state"}
        or labels.get("org.opencontainers.image.revision") != REVISION
        or labels.get("org.cotcodec.source-tree") != TREE
        or labels.get("org.cotcodec.source-archive-sha256") != ARCHIVE_SHA256
        or labels.get("org.cotcodec.doctor-sha256") != _sha(files["doctor.py"])
        or labels.get("org.cotcodec.discovery-only") != "true"
    ):
        raise MemForestLifecycleEvidenceError("MemForest doctor image provenance drifted")


def _phase_token(phase: dict[str, Any]) -> str:
    metrics = phase.get("metrics")
    if not isinstance(metrics, dict):
        raise MemForestLifecycleEvidenceError("MemForest phase metrics missing")
    projections = [value for value in metrics.values() if isinstance(value, dict)]
    encoded = json.dumps(projections, sort_keys=True)
    matches = re.findall(r"COTMF_[A-Z_]+_([0-9A-F]{16})", encoded)
    if not matches or len(set(matches)) != 1 or not TOKEN_RE.fullmatch(matches[0]):
        raise MemForestLifecycleEvidenceError("MemForest repeat token projection drifted")
    return matches[0]


def _validate_torn_projection(phase: dict[str, Any], token: str) -> None:
    metrics = phase["metrics"]
    torn = metrics.get("torn_after_restart")
    if not isinstance(torn, dict):
        raise MemForestLifecycleEvidenceError("MemForest torn projection missing")
    base_session = f"torn-base-{token}"
    new_session = f"torn-new-{token}"
    if (
        torn.get("active_sessions") != [base_session]
        or torn.get("facts") != [f"COTMF_TORN_BASE_{token}", f"COTMF_TORN_NEW_{token}"]
        or torn.get("session_alias_map") != {base_session: "sess_0001"}
        or not isinstance(torn.get("cell_ids"), list)
        or len(torn["cell_ids"]) != 1
        or not torn["cell_ids"][0].startswith(base_session + "#cell_")
        or new_session in torn.get("active_sessions", [])
        or "session:sess_0002" not in torn.get("tree_ids", [])
    ):
        raise MemForestLifecycleEvidenceError("MemForest torn generation semantics drifted")


def _validate_diagnostic(phase: dict[str, Any]) -> None:
    diagnostic = phase["metrics"].get("write_path_diagnostic")
    if not isinstance(diagnostic, dict):
        raise MemForestLifecycleEvidenceError("MemForest write diagnostic missing")
    exact = {
        "sessions": 5,
        "incremental_chat_calls": 8,
        "clean_rebuild_chat_calls": 21,
        "incremental_embedding_texts": 25,
        "clean_rebuild_embedding_texts": 76,
        "incremental_active_sessions": 5,
        "clean_rebuild_active_sessions": 5,
    }
    if any(diagnostic.get(key) != value for key, value in exact.items()):
        raise MemForestLifecycleEvidenceError("MemForest write diagnostic counts drifted")
    for key in (
        "incremental_elapsed_ns",
        "clean_rebuild_elapsed_ns",
        "incremental_current_bytes",
        "clean_rebuild_current_bytes",
    ):
        value = diagnostic.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise MemForestLifecycleEvidenceError("MemForest write diagnostic metric drifted")


def _validate_repeat(files: dict[str, bytes], repeat: int) -> dict[str, Any]:
    payload = _object(files[f"repeat-{repeat}.json"], f"MemForest repeat {repeat}")
    phases = payload.get("phases")
    if (
        payload.get("repeat") != repeat
        or payload.get("phase_count") != 4
        or payload.get("fresh_process_restart_count") != 3
        or payload.get("stable_projection_sha256") != STABLE_PROJECTION_SHA256
        or not isinstance(phases, list)
        or len(phases) != 4
    ):
        raise MemForestLifecycleEvidenceError(f"MemForest repeat {repeat} identity drifted")
    stable: list[dict[str, bool]] = []
    token: str | None = None
    for index, phase in enumerate(phases, start=1):
        checks = phase.get("checks") if isinstance(phase, dict) else None
        if (
            not isinstance(phase, dict)
            or phase.get("phase") != index
            or not isinstance(checks, dict)
            or set(checks) != PHASE_CHECKS[index - 1]
            or not all(value is True for value in checks.values())
        ):
            raise MemForestLifecycleEvidenceError(f"MemForest repeat {repeat} checks drifted")
        stable.append(checks)
        raw = files[f"repeat-{repeat}-phase-{index}.txt"]
        marker = b"COTCODEC_MEMFOREST_PHASE="
        rows = [line.split(marker, 1)[1] for line in raw.splitlines() if marker in line]
        if len(rows) != 1 or _object(rows[0], "MemForest phase marker") != phase:
            raise MemForestLifecycleEvidenceError(f"MemForest repeat {repeat} marker drifted")
        phase_token = _phase_token(phase)
        if token is None:
            token = phase_token
        elif phase_token != token:
            raise MemForestLifecycleEvidenceError(f"MemForest repeat {repeat} token drifted")
    if (
        payload.get("stable_projection") != stable
        or _sha(json.dumps(stable, separators=(",", ":"), sort_keys=True).encode())
        != STABLE_PROJECTION_SHA256
    ):
        raise MemForestLifecycleEvidenceError(f"MemForest repeat {repeat} projection drifted")
    assert token is not None
    _validate_torn_projection(phases[2], token)
    _validate_diagnostic(phases[2])
    if phases[2]["metrics"].get("post_delete_plaintext_residue_paths") != []:
        raise MemForestLifecycleEvidenceError("MemForest current-file deletion residue drifted")
    return payload


def _validate_report(files: dict[str, bytes], repeats: list[dict[str, Any]]) -> dict[str, Any]:
    report = _object(files["report.json"], "MemForest lifecycle report")
    findings = report.get("findings")
    diagnostics = report.get("write_path_diagnostics")
    if (
        _sha(files["report.json"]) != REPORT_SHA256
        or report.get("schema_version") != 1
        or report.get("status") != EXPECTED_STATUS
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("h100_actor_admission") != "forbidden-for-this-revision"
        or report.get("run_count") != 2
        or report.get("fresh_process_restart_count_per_run") != 3
        or report.get("stable_projection_sha256") != STABLE_PROJECTION_SHA256
        or report.get("claim_boundary") != CLAIM_BOUNDARY
        or not isinstance(findings, dict)
        or set(findings) != EXPECTED_FINDINGS
        or not all(value is True for value in findings.values())
        or report.get("post_delete_plaintext_residue_paths") != [[], []]
        or not isinstance(diagnostics, list)
        or len(diagnostics) != 2
    ):
        raise MemForestLifecycleEvidenceError("MemForest lifecycle report drifted")
    expected_diagnostics = [
        repeat["phases"][2]["metrics"]["write_path_diagnostic"] for repeat in repeats
    ]
    if diagnostics != expected_diagnostics:
        raise MemForestLifecycleEvidenceError("MemForest report diagnostics drifted")
    return report


def validate_evidence(
    source: Path | dict[str, Any] = DEFAULT_OUTPUT,
    *,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    if isinstance(source, Path):
        if source.is_symlink() or not source.is_file():
            raise MemForestLifecycleEvidenceError("MemForest lifecycle evidence is missing")
        bundle = _object(source.read_bytes(), "MemForest lifecycle evidence")
    else:
        bundle = source
    if (
        bundle.get("schema_version") != 1
        or bundle.get("source_id") != "memforest"
        or bundle.get("source_revision") != REVISION
        or bundle.get("source_revisions") != {"https://github.com/Concyclics/MemForest": REVISION}
        or bundle.get("source_tree") != TREE
        or bundle.get("evidence_kind") != "contained-native-lifecycle-negative"
        or bundle.get("evidence_grade") != "local-negative-reproduced"
        or bundle.get("status") != EXPECTED_STATUS
        or bundle.get("scientific_result") is not False
        or bundle.get("publication_ready") is not False
        or bundle.get("runtime_lane") != "local-arm64-docker-network-none"
        or bundle.get("run_count") != 2
        or bundle.get("fresh_process_restart_count_per_run") != 3
        or bundle.get("stable_projection_sha256") != STABLE_PROJECTION_SHA256
        or bundle.get("report_sha256") != REPORT_SHA256
        or bundle.get("manifest_sha256") != MANIFEST_SHA256
        or bundle.get("claim_boundary") != CLAIM_BOUNDARY
        or bundle.get("h100_actor_admission") != "forbidden-for-this-revision"
        or bundle.get("findings") != {finding: True for finding in sorted(EXPECTED_FINDINGS)}
        or bundle.get("source_archive")
        != {"bytes": ARCHIVE_BYTES, "sha256": ARCHIVE_SHA256, "embedded": False}
    ):
        raise MemForestLifecycleEvidenceError("MemForest lifecycle evidence identity drifted")
    _validate_code(bundle, project_root)
    files = _decode(bundle.get("artifact_files"))
    _validate_manifest(files)
    source_receipt = _validate_source(files)
    _validate_image(files)
    if (
        files["Dockerfile"]
        != (project_root / "infra/memory-baselines/memforest/Dockerfile").read_bytes()
    ):
        raise MemForestLifecycleEvidenceError("embedded MemForest Dockerfile drifted")
    if (
        files["doctor.py"]
        != (project_root / "infra/memory-baselines/memforest/doctor.py").read_bytes()
    ):
        raise MemForestLifecycleEvidenceError("embedded MemForest doctor drifted")
    freeze = set(files["pip-freeze.txt"].decode().splitlines())
    if not DIRECT_REQUIREMENTS.issubset(freeze):
        raise MemForestLifecycleEvidenceError("MemForest direct dependency receipt drifted")
    experiment = yaml.safe_load(files["experiment.yaml"])
    if not isinstance(experiment, dict) or experiment != validate_experiment_contract():
        raise MemForestLifecycleEvidenceError("embedded MemForest experiment drifted")
    repeats = [_validate_repeat(files, repeat) for repeat in (1, 2)]
    if repeats[0]["stable_projection"] != repeats[1]["stable_projection"]:
        raise MemForestLifecycleEvidenceError("MemForest clean-state projections diverged")
    report = _validate_report(files, repeats)
    if report.get("source") != source_receipt:
        raise MemForestLifecycleEvidenceError("MemForest report source receipt drifted")
    return bundle


def _write_once(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        os.write(descriptor, data)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def seal(root: Path = DEFAULT_ROOT, output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    if root.is_symlink() or not root.is_dir():
        raise MemForestLifecycleEvidenceError("MemForest lifecycle artifact root is missing")
    actual = {path.name for path in root.iterdir() if path.is_file()}
    if actual != ARTIFACT_NAMES | {"source.tar"}:
        raise MemForestLifecycleEvidenceError("MemForest lifecycle artifact directory drifted")
    artifact_files = {name: _capture(root / name) for name in sorted(ARTIFACT_NAMES)}
    report = _object((root / "report.json").read_bytes(), "MemForest lifecycle report")
    bundle = {
        "schema_version": 1,
        "source_id": "memforest",
        "source_revision": REVISION,
        "source_revisions": {"https://github.com/Concyclics/MemForest": REVISION},
        "source_tree": TREE,
        "evidence_kind": "contained-native-lifecycle-negative",
        "evidence_grade": "local-negative-reproduced",
        "status": EXPECTED_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "runtime_lane": "local-arm64-docker-network-none",
        "run_count": 2,
        "fresh_process_restart_count_per_run": 3,
        "stable_projection_sha256": STABLE_PROJECTION_SHA256,
        "report_sha256": REPORT_SHA256,
        "manifest_sha256": MANIFEST_SHA256,
        "claim_boundary": CLAIM_BOUNDARY,
        "h100_actor_admission": "forbidden-for-this-revision",
        "findings": {finding: True for finding in sorted(EXPECTED_FINDINGS)},
        "source_archive": {
            "bytes": ARCHIVE_BYTES,
            "sha256": ARCHIVE_SHA256,
            "embedded": False,
        },
        "code_files": {name: _sha(path.read_bytes()) for name, path in CODE_PATHS.items()},
        "artifact_files": artifact_files,
        "write_path_diagnostics": report["write_path_diagnostics"],
        "post_delete_plaintext_residue_paths": report["post_delete_plaintext_residue_paths"],
    }
    validate_evidence(bundle)
    _write_once(output, (json.dumps(bundle, indent=2, sort_keys=True) + "\n").encode())
    return bundle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        validate_evidence(args.output)
        print("MemForest native lifecycle evidence PASS")
    else:
        bundle = seal(args.root, args.output)
        print(json.dumps({"output": str(args.output), "status": bundle["status"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
