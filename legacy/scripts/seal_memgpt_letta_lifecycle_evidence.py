#!/usr/bin/env python3
"""Seal and validate the exact-source legacy Letta V1 lifecycle negative."""

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

from scripts.validate_memgpt_letta_lifecycle_experiment import (  # noqa: E402
    EXPECTED_STATUS,
    validate_experiment_contract,
)

DEFAULT_ROOT = (
    PROJECT_ROOT
    / "data/results/memgpt-letta-lifecycle/2026-08-31-slurm-cpu-v4"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "research/evidence/memory/memgpt-letta-native-lifecycle-negative-v1.json"
)

LEGACY_REPOSITORY = "https://github.com/letta-ai/letta"
LEGACY_REVISION = "ff19ffeafeb54bd2a7dc5d4a552f10191732a235"
LEGACY_TREE = "675c06071568dd48ca9b16b755041937286b7d95"
LEGACY_ARCHIVE_SHA256 = (
    "68858b2315fd6a3f8f499fd5354307c22320d430a7a9b52e475523ec2d43f108"
)
LEGACY_ARCHIVE_BYTES = 24_176_640
CURRENT_REPOSITORY = "https://github.com/letta-ai/letta-code"
CURRENT_REVISION = "a575e11753943d9a4e18373a8817eb16a5b76b47"
CURRENT_TREE = "9bb2cadf097f522bdcbc09fe0268dd6dd82bb410"
CURRENT_ARCHIVE_SHA256 = (
    "d81b210456b049a09d1a98618846273c7f41aadd63e4873fa796ecab20db9bd9"
)
CURRENT_ARCHIVE_BYTES = 50_759_680
IMAGE_REFERENCE = (
    "docker.io/letta/letta@"
    "sha256:7bdff3a3f876b79db0b347900a392bd6f13eff5c294735eda98be1f8ecf7a7a2"
)
IMAGE_ID = "sha256:ddfc72e92d690aeea244fd55b617594e468290ee8ede21cbb5aca9876d40e356"
SLURM_JOB_ID = "351"
STABLE_PROJECTION_SHA256 = (
    "25b09cf3288e045afcb71908b03af97f898dab2ea8921e64506ba8d5234a8f3a"
)
REPORT_SHA256 = "78737148ddd6bb49cd23edee076414dcd5e02d18cf24f8114883a04f414d4c18"
MANIFEST_SHA256 = "525f19a1a6183ebedf78ceeeb4bd8a1e922fe44c86cd3e763894117fb9e4090d"
CLAIM_BOUNDARY = (
    "Exact pinned legacy Letta V1 public core-block and archival-memory "
    "lifecycle, official-image/source identity, organization isolation, "
    "fresh-process restart, injected message-update failure semantics, "
    "payload-equivalent write retry, agent/resource deletion, stopped "
    "PostgreSQL plaintext scan, and matched local operation diagnostics; not "
    "semantic memory quality, autonomous paging policy, live model behavior, "
    "concurrent serving, managed Letta Cloud, the separate Letta Code MemFS "
    "runtime, secure media erasure, H100 quality, or publication evidence."
)

ARTIFACT_NAMES = {
    "current-runtime-context-receipt.json",
    "doctor.py",
    "experiment.yaml",
    "image-receipt.json",
    "manifest.json",
    "repeat-1/initial.stderr",
    "repeat-1/initial.stdout",
    "repeat-1/phase-initial.json",
    "repeat-1/phase-restart-cleanup.json",
    "repeat-1/phase-scan.json",
    "repeat-1/postgres-stop-after-cleanup.json",
    "repeat-1/postgres-stop-after-initial.json",
    "repeat-1/restart-cleanup.stderr",
    "repeat-1/restart-cleanup.stdout",
    "repeat-1/scan.stderr",
    "repeat-1/scan.stdout",
    "repeat-1/server.log",
    "repeat-1/state.json",
    "repeat-2/initial.stderr",
    "repeat-2/initial.stdout",
    "repeat-2/phase-initial.json",
    "repeat-2/phase-restart-cleanup.json",
    "repeat-2/phase-scan.json",
    "repeat-2/postgres-stop-after-cleanup.json",
    "repeat-2/postgres-stop-after-initial.json",
    "repeat-2/restart-cleanup.stderr",
    "repeat-2/restart-cleanup.stdout",
    "repeat-2/scan.stderr",
    "repeat-2/scan.stdout",
    "repeat-2/server.log",
    "repeat-2/state.json",
    "report.json",
    "runner.py",
    "source-receipt.json",
    "validator.py",
}
MANIFEST_FILE_NAMES = (ARTIFACT_NAMES - {"manifest.json"}) | {
    "source.tar",
    "letta-code-source.tar",
}
CODE_PATHS = {
    "experiments/memory/stage3-memgpt-letta-native-lifecycle-doctor.yaml",
    "infra/memory-baselines/memgpt-letta/doctor.py",
    "infra/slurm/host-single-node/memgpt-letta-lifecycle.sbatch",
    "scripts/run_memgpt_letta_lifecycle_doctor.py",
    "scripts/seal_memgpt_letta_lifecycle_evidence.py",
    "scripts/validate_memgpt_letta_lifecycle_experiment.py",
}
REPORT_CHECKS = {
    "official_image_matches_exact_source",
    "provider_free_agent_creation_passes",
    "core_block_mutation_passes",
    "inactive_archive_write_and_read_passes",
    "cross_organization_isolation_passes",
    "normal_state_survives_fresh_process",
    "failed_core_update_returns_server_error_after_block_mutation",
    "failed_core_update_mutation_survives_fresh_process",
    "identical_archive_retry_creates_duplicate_rows",
    "duplicate_archive_rows_survive_fresh_process",
    "deleting_agent_retains_owner_archive_and_core_blocks",
    "explicit_archive_and_block_delete_is_logically_effective",
    "stopped_postgres_plaintext_residue_present",
    "reproduced_in_two_clean_states",
}
INITIAL_CHECKS = {
    "provider_free_agent_creation_passes",
    "core_block_mutation_passes",
    "inactive_archive_write_and_read_passes",
    "cross_organization_isolation_passes",
    "failed_core_update_returns_server_error_after_block_mutation",
    "identical_archive_retry_creates_duplicate_rows",
}
RESTART_CHECKS = {
    "normal_state_survives_fresh_process",
    "cross_organization_isolation_survives_fresh_process",
    "failed_core_update_mutation_survives_fresh_process",
    "failed_core_update_retry_repairs_compiled_prompt",
    "duplicate_archive_rows_survive_fresh_process",
    "deleting_agent_retains_owner_archive_and_core_blocks",
    "explicit_archive_and_block_delete_is_logically_effective",
}
SCAN_CHECKS = {"stopped_postgres_plaintext_residue_present"}
REPEAT_CHECKS = INITIAL_CHECKS | RESTART_CHECKS | SCAN_CHECKS
CANARY_KEYS = {"archive", "core_failed", "core_initial", "core_normal", "persona"}


class MemgptLettaLifecycleEvidenceError(ValueError):
    """Raised when retained Letta lifecycle evidence drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _strict_object(data: bytes, owner: str) -> dict[str, Any]:
    def reject(value: str) -> None:
        raise MemgptLettaLifecycleEvidenceError(
            f"{owner} contains non-finite JSON {value}"
        )

    try:
        payload = json.loads(data, parse_constant=reject)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise MemgptLettaLifecycleEvidenceError(f"{owner} is not strict JSON") from error
    if not isinstance(payload, dict):
        raise MemgptLettaLifecycleEvidenceError(f"{owner} must be an object")
    return payload


def _capture(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise MemgptLettaLifecycleEvidenceError(
            f"expected regular evidence input: {path}"
        )
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
    if not isinstance(receipts, dict) or set(receipts) != ARTIFACT_NAMES:
        raise MemgptLettaLifecycleEvidenceError("Letta artifact roster drifted")
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
            raise MemgptLettaLifecycleEvidenceError(f"invalid artifact receipt: {name}")
        try:
            compressed = base64.b64decode(
                receipt["content_gzip_base64"], validate=True
            )
            raw = gzip.decompress(compressed)
        except (TypeError, ValueError, OSError) as error:
            raise MemgptLettaLifecycleEvidenceError(
                f"cannot decode artifact: {name}"
            ) from error
        if (
            receipt["compression"] != "gzip-mtime-0"
            or receipt["compressed_size"] != len(compressed)
            or receipt["compressed_sha256"] != _sha(compressed)
            or receipt["raw_size"] != len(raw)
            or receipt["raw_sha256"] != _sha(raw)
        ):
            raise MemgptLettaLifecycleEvidenceError(f"artifact receipt drifted: {name}")
        decoded[name] = raw
    return decoded


def _validate_code(bundle: dict[str, Any], project_root: Path) -> None:
    receipts = bundle.get("code_files")
    if not isinstance(receipts, dict) or set(receipts) != CODE_PATHS:
        raise MemgptLettaLifecycleEvidenceError("Letta code roster drifted")
    for name, expected in receipts.items():
        path = project_root / name
        if (
            not isinstance(expected, str)
            or len(expected) != 64
            or path.is_symlink()
            or not path.is_file()
            or _sha(path.read_bytes()) != expected
        ):
            raise MemgptLettaLifecycleEvidenceError(f"Letta code drifted: {name}")


def _validate_manifest(files: dict[str, bytes]) -> None:
    if _sha(files["manifest.json"]) != MANIFEST_SHA256:
        raise MemgptLettaLifecycleEvidenceError("Letta manifest identity drifted")
    manifest = _strict_object(files["manifest.json"], "Letta manifest")
    declared = manifest.get("files")
    if not isinstance(declared, dict) or set(declared) != MANIFEST_FILE_NAMES:
        raise MemgptLettaLifecycleEvidenceError("Letta manifest roster drifted")
    for name, receipt in declared.items():
        if not isinstance(receipt, dict) or set(receipt) != {"bytes", "sha256"}:
            raise MemgptLettaLifecycleEvidenceError(
                f"invalid Letta manifest member: {name}"
            )
        if name == "source.tar":
            raw_size, raw_sha = LEGACY_ARCHIVE_BYTES, LEGACY_ARCHIVE_SHA256
        elif name == "letta-code-source.tar":
            raw_size, raw_sha = CURRENT_ARCHIVE_BYTES, CURRENT_ARCHIVE_SHA256
        else:
            raw = files[name]
            raw_size, raw_sha = len(raw), _sha(raw)
        if receipt != {"bytes": raw_size, "sha256": raw_sha}:
            raise MemgptLettaLifecycleEvidenceError(
                f"Letta manifest member drifted: {name}"
            )


def _validate_source_and_image(files: dict[str, bytes]) -> None:
    source = _strict_object(files["source-receipt.json"], "Letta source receipt")
    context = _strict_object(
        files["current-runtime-context-receipt.json"], "Letta Code receipt"
    )
    image = _strict_object(files["image-receipt.json"], "Letta image receipt")
    if (
        source.get("repository") != LEGACY_REPOSITORY
        or source.get("revision") != LEGACY_REVISION
        or source.get("tree") != LEGACY_TREE
        or source.get("archive_sha256") != LEGACY_ARCHIVE_SHA256
        or source.get("archive_bytes") != LEGACY_ARCHIVE_BYTES
    ):
        raise MemgptLettaLifecycleEvidenceError("legacy Letta source identity drifted")
    if (
        context.get("repository") != CURRENT_REPOSITORY
        or context.get("revision") != CURRENT_REVISION
        or context.get("tree") != CURRENT_TREE
        or context.get("archive_sha256") != CURRENT_ARCHIVE_SHA256
        or context.get("archive_bytes") != CURRENT_ARCHIVE_BYTES
        or context.get("role")
        != "provenance-context-only-different-local-memfs-mechanism"
    ):
        raise MemgptLettaLifecycleEvidenceError("Letta Code context identity drifted")
    source_files = source.get("file_sha256")
    image_files = image.get("source_file_sha256")
    if (
        image.get("reference") != IMAGE_REFERENCE
        or image.get("image_id") != IMAGE_ID
        or image.get("letta_version") != "0.16.8"
        or image.get("python_version") != "3.11.2"
        or not isinstance(source_files, dict)
        or not isinstance(image_files, dict)
        or {f"/app/{name}": digest for name, digest in source_files.items()}
        != image_files
    ):
        raise MemgptLettaLifecycleEvidenceError("official Letta image identity drifted")


def _all_true(payload: Any, names: set[str], owner: str) -> None:
    if (
        not isinstance(payload, dict)
        or set(payload) != names
        or any(payload[name] is not True for name in names)
    ):
        raise MemgptLettaLifecycleEvidenceError(f"{owner} checks drifted")


def _validate_phases(files: dict[str, bytes]) -> list[dict[str, Any]]:
    repeats: list[dict[str, Any]] = []
    for repeat in (1, 2):
        prefix = f"repeat-{repeat}"
        initial = _strict_object(
            files[f"{prefix}/phase-initial.json"], f"{prefix} initial phase"
        )
        restart = _strict_object(
            files[f"{prefix}/phase-restart-cleanup.json"],
            f"{prefix} restart phase",
        )
        scan = _strict_object(
            files[f"{prefix}/phase-scan.json"], f"{prefix} scan phase"
        )
        state = _strict_object(files[f"{prefix}/state.json"], f"{prefix} state")
        _all_true(initial.get("checks"), INITIAL_CHECKS, f"{prefix} initial")
        _all_true(restart.get("checks"), RESTART_CHECKS, f"{prefix} restart")
        _all_true(scan.get("checks"), SCAN_CHECKS, f"{prefix} scan")
        if (
            initial.get("repeat") != repeat
            or initial.get("phase") != "initial"
            or initial.get("external_model_calls") != 0
            or initial.get("provider_calls") != 0
            or initial.get("http_call_count") != 14
            or len(initial.get("http_calls", [])) != 14
            or initial.get("failed_update_status") != 500
            or initial.get("system_message_contains_failed_canary") is not False
            or initial.get("isolation_statuses") != [404, 404, 404]
        ):
            raise MemgptLettaLifecycleEvidenceError(
                f"{prefix} initial diagnostics drifted"
            )
        if (
            restart.get("repeat") != repeat
            or restart.get("phase") != "restart-cleanup"
            or restart.get("external_model_calls") != 0
            or restart.get("provider_calls") != 0
            or restart.get("http_call_count") != 18
            or len(restart.get("http_calls", [])) != 18
            or restart.get("passage_count_after_agent_delete") != 2
            or restart.get("current_passage_count") != 0
            or restart.get("current_block_count") != 0
        ):
            raise MemgptLettaLifecycleEvidenceError(
                f"{prefix} restart diagnostics drifted"
            )
        hits = scan.get("plaintext_hits")
        if (
            scan.get("repeat") != repeat
            or scan.get("phase") != "scan"
            or scan.get("stopped_state_bytes") != 68_272_020
            or not isinstance(scan.get("scanned_file_count"), int)
            or scan["scanned_file_count"] <= 0
            or not isinstance(hits, dict)
            or set(hits) != CANARY_KEYS
            or any(not isinstance(paths, list) or not paths for paths in hits.values())
        ):
            raise MemgptLettaLifecycleEvidenceError(
                f"{prefix} stopped-state diagnostics drifted"
            )
        canaries = state.get("canaries")
        if (
            state.get("repeat") != repeat
            or not isinstance(canaries, dict)
            or set(canaries) != CANARY_KEYS
            or any(
                not isinstance(value, str) or not value.startswith("COTCODEC_LETTA_R")
                for value in canaries.values()
            )
        ):
            raise MemgptLettaLifecycleEvidenceError(f"{prefix} state drifted")
        for suffix in ("after-initial", "after-cleanup"):
            stopped = _strict_object(
                files[f"{prefix}/postgres-stop-{suffix}.json"],
                f"{prefix} PostgreSQL stop {suffix}",
            )
            if stopped.get("returncode") != 0 or stopped.get("stderr") != "":
                raise MemgptLettaLifecycleEvidenceError(
                    f"{prefix} PostgreSQL stop receipt drifted"
                )
        for phase in ("initial", "restart-cleanup", "scan"):
            for stream in ("stdout", "stderr"):
                if files[f"{prefix}/{phase}.{stream}"] != b"":
                    raise MemgptLettaLifecycleEvidenceError(
                        f"{prefix} phase stream is not empty: {phase}.{stream}"
                    )
        projection = {**initial["checks"], **restart["checks"], **scan["checks"]}
        _all_true(projection, REPEAT_CHECKS, f"{prefix} projection")
        repeats.append(
            {
                "repeat": repeat,
                "phase_returncodes": {
                    "initial": 0,
                    "restart_cleanup": 0,
                    "scan": 0,
                },
                "projection": projection,
                "http_call_count": 32,
                "stopped_state_bytes": scan["stopped_state_bytes"],
                "plaintext_hits": hits,
            }
        )
    projection_bytes = json.dumps(
        [row["projection"] for row in repeats], sort_keys=True, separators=(",", ":")
    ).encode()
    if _sha(projection_bytes) != STABLE_PROJECTION_SHA256:
        raise MemgptLettaLifecycleEvidenceError("Letta stable projection drifted")
    return repeats


def _validate_report(files: dict[str, bytes], repeats: list[dict[str, Any]]) -> None:
    if _sha(files["report.json"]) != REPORT_SHA256:
        raise MemgptLettaLifecycleEvidenceError("Letta report identity drifted")
    report = _strict_object(files["report.json"], "Letta report")
    checks = report.get("checks")
    _all_true(checks, REPORT_CHECKS, "Letta report")
    if (
        report.get("schema_version") != 1
        or report.get("status") != EXPECTED_STATUS
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("h100_admission") is not False
        or report.get("expected_checks") != checks
        or report.get("unexpected_checks") != []
        or report.get("stable_projection_sha256") != STABLE_PROJECTION_SHA256
        or report.get("claim_boundary") != CLAIM_BOUNDARY
        or report.get("repeats") != repeats
    ):
        raise MemgptLettaLifecycleEvidenceError("Letta report semantics drifted")
    runtime = report.get("runtime")
    if runtime != {
        "slurm_job_id": SLURM_JOB_ID,
        "slurm_cpus_per_task": "4",
        "slurm_mem_per_node": "16384",
        "gpu_count": 0,
        "container_network": "none",
        "external_model_calls": 0,
        "provider_calls": 0,
    }:
        raise MemgptLettaLifecycleEvidenceError("Letta runtime receipt drifted")
    if (
        report.get("source")
        != _strict_object(files["source-receipt.json"], "Letta source receipt")
        or report.get("current_runtime_context")
        != _strict_object(
            files["current-runtime-context-receipt.json"], "Letta Code receipt"
        )
        or report.get("image")
        != _strict_object(files["image-receipt.json"], "Letta image receipt")
        or report.get("code_sha256")
        != {
            "doctor": _sha(files["doctor.py"]),
            "experiment": _sha(files["experiment.yaml"]),
            "runner": _sha(files["runner.py"]),
            "validator": _sha(files["validator.py"]),
        }
    ):
        raise MemgptLettaLifecycleEvidenceError("Letta report provenance drifted")


def _identity(bundle: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": bundle.get("schema_version"),
        "source_id": bundle.get("source_id"),
        "evidence_grade": bundle.get("evidence_grade"),
        "evidence_kind": bundle.get("evidence_kind"),
        "status": bundle.get("status"),
        "source_revisions": bundle.get("source_revisions"),
        "source_trees": bundle.get("source_trees"),
        "source_archives": bundle.get("source_archives"),
        "runtime_lane": bundle.get("runtime_lane"),
        "slurm_job_id": bundle.get("slurm_job_id"),
        "run_count": bundle.get("run_count"),
        "fresh_process_restart_count_per_run": bundle.get(
            "fresh_process_restart_count_per_run"
        ),
        "official_image": bundle.get("official_image"),
        "stable_projection_sha256": bundle.get("stable_projection_sha256"),
        "report_sha256": bundle.get("report_sha256"),
        "manifest_sha256": bundle.get("manifest_sha256"),
        "findings": bundle.get("findings"),
        "h100_actor_admission": bundle.get("h100_actor_admission"),
        "scientific_result": bundle.get("scientific_result"),
        "publication_ready": bundle.get("publication_ready"),
        "claim_boundary": bundle.get("claim_boundary"),
    }


def _expected_identity() -> dict[str, Any]:
    findings = {name: True for name in REPORT_CHECKS | REPEAT_CHECKS}
    return {
        "schema_version": 1,
        "source_id": "memgpt-letta",
        "evidence_grade": "local-negative-reproduced",
        "evidence_kind": "contained-native-lifecycle-negative",
        "status": EXPECTED_STATUS,
        "source_revisions": {
            LEGACY_REPOSITORY: LEGACY_REVISION,
            CURRENT_REPOSITORY: CURRENT_REVISION,
        },
        "source_trees": {
            LEGACY_REPOSITORY: LEGACY_TREE,
            CURRENT_REPOSITORY: CURRENT_TREE,
        },
        "source_archives": {
            LEGACY_REPOSITORY: {
                "bytes": LEGACY_ARCHIVE_BYTES,
                "sha256": LEGACY_ARCHIVE_SHA256,
            },
            CURRENT_REPOSITORY: {
                "bytes": CURRENT_ARCHIVE_BYTES,
                "sha256": CURRENT_ARCHIVE_SHA256,
            },
        },
        "runtime_lane": "slurm-cpu-amd64-official-image-network-none",
        "slurm_job_id": SLURM_JOB_ID,
        "run_count": 2,
        "fresh_process_restart_count_per_run": 1,
        "official_image": {"reference": IMAGE_REFERENCE, "image_id": IMAGE_ID},
        "stable_projection_sha256": STABLE_PROJECTION_SHA256,
        "report_sha256": REPORT_SHA256,
        "manifest_sha256": MANIFEST_SHA256,
        "findings": findings,
        "h100_actor_admission": "forbidden-for-this-revision",
        "scientific_result": False,
        "publication_ready": False,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def validate_evidence(
    evidence: Path | dict[str, Any], *, project_root: Path = PROJECT_ROOT
) -> dict[str, Any]:
    if isinstance(evidence, Path):
        bundle = _strict_object(evidence.read_bytes(), "Letta evidence bundle")
    elif isinstance(evidence, dict):
        bundle = evidence
    else:
        raise MemgptLettaLifecycleEvidenceError("Letta evidence must be a path or object")
    if _identity(bundle) != _expected_identity():
        raise MemgptLettaLifecycleEvidenceError("Letta evidence identity drifted")
    files = _decode(bundle.get("artifact_files"))
    _validate_manifest(files)
    _validate_source_and_image(files)
    repeats = _validate_phases(files)
    _validate_report(files, repeats)
    _validate_code(bundle, project_root)
    return bundle


def build_evidence(root: Path, *, project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    validate_experiment_contract(
        project_root
        / "experiments/memory/stage3-memgpt-letta-native-lifecycle-doctor.yaml"
    )
    artifacts = {name: _capture(root / name) for name in sorted(ARTIFACT_NAMES)}
    code_files = {
        name: _sha((project_root / name).read_bytes()) for name in sorted(CODE_PATHS)
    }
    bundle = {
        **_expected_identity(),
        "artifact_files": artifacts,
        "code_files": code_files,
    }
    validate_evidence(bundle, project_root=project_root)
    return bundle


def _encoded(bundle: dict[str, Any]) -> bytes:
    return (json.dumps(bundle, indent=2, sort_keys=True) + "\n").encode()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if args.validate_only:
        validate_evidence(args.output)
        print(f"MemGPT/Letta lifecycle evidence PASS: {args.output}")
        return 0
    bundle = build_evidence(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(_encoded(bundle))
    validate_evidence(args.output)
    print(f"MemGPT/Letta lifecycle evidence sealed: {args.output}")
    print(f"sha256={_sha(args.output.read_bytes())}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (MemgptLettaLifecycleEvidenceError, OSError, ValueError) as error:
        print(f"MemGPT/Letta lifecycle evidence failed: {error}", file=sys.stderr)
        raise SystemExit(2) from error
