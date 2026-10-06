#!/usr/bin/env python3
"""Seal and validate ASTRA Slurm job 269's native-lifecycle negative."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = PROJECT_ROOT / "data/results/astra-native-lifecycle/2026-08-15-job269-v11"
DEFAULT_OUTPUT = PROJECT_ROOT / "research/evidence/memory/astra-native-lifecycle-negative-v1.json"
EXPECTED_STATUS = "BLOCKED_NONDETERMINISTIC_RECALL_ACCESS_ACCOUNTING"
EXPECTED_REVISION = "644f9d4e65f4e725996025834c91531592ab6166"
EXPECTED_SOURCE_ARCHIVE = "e8bc1a979c9b8f67df3efcbee28ed5694e5d6ff864a11d427e642ef106d187a4"
EXPECTED_IMAGE_ARCHIVE = "eac838215d1cdb61d1734e8bd4641863b9aeec2892cb3043824c8758951845da"
EXPECTED_CONTRACT = "074ad133451c61a077c03b84190a991676e4f8f7babb829152adb0330ae738ea"
EXPECTED_STRIPPED_PROJECTION = "5c947f1b251659dccbee26cab6e1f45b6911eb4d52149ed5a3ff0d8d6b1a31eb"
EXPECTED_FILES = {
    "analysis.json",
    "manifest.sha256",
    "repeat-0.json",
    "repeat-1.json",
    "slurm-269.out",
    "slurm-269.scontrol.txt",
}
CODE_PATHS = {
    "experiments/memory/stage3-astra-native-lifecycle-doctor.yaml",
    "infra/memory-baselines/astra/doctor.ts",
    "infra/slurm/host-single-node/astra-lifecycle.sbatch",
    "scripts/run_astra_lifecycle_doctor.py",
    "scripts/validate_astra_lifecycle_experiment.py",
}
CLAIM_BOUNDARY = {
    "native_restart_executed": True,
    "durable_readmission_executed": True,
    "user_isolation_executed": True,
    "physical_purge_available": False,
    "idempotency_key_available": False,
    "hard_pinned_capacity_enforced": False,
    "deterministic_recall_state": False,
    "h100_actor_admission": "forbidden-for-this-revision",
    "memory_quality_evaluated": False,
}


class AstraEvidenceError(ValueError):
    """Raised when retained ASTRA evidence is incomplete or drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json(data: bytes, owner: str) -> dict[str, Any]:
    def reject(value: str) -> None:
        raise AstraEvidenceError(f"{owner}: non-finite JSON value {value}")

    try:
        payload = json.loads(data, parse_constant=reject)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AstraEvidenceError(f"{owner}: invalid JSON") from exc
    if not isinstance(payload, dict):
        raise AstraEvidenceError(f"{owner}: expected JSON object")
    return payload


def _capture(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise AstraEvidenceError(f"expected regular evidence input: {path}")
    data = path.read_bytes()
    return {
        "bytes": len(data),
        "sha256": _sha(data),
        "content_base64": base64.b64encode(data).decode("ascii"),
    }


def _decode_files(receipts: Any) -> dict[str, bytes]:
    if not isinstance(receipts, dict) or set(receipts) != EXPECTED_FILES:
        raise AstraEvidenceError("ASTRA evidence file roster drifted")
    decoded: dict[str, bytes] = {}
    for name, receipt in receipts.items():
        if not isinstance(receipt, dict):
            raise AstraEvidenceError(f"invalid ASTRA receipt for {name}")
        try:
            data = base64.b64decode(receipt.get("content_base64", ""), validate=True)
        except (TypeError, ValueError) as exc:
            raise AstraEvidenceError(f"invalid base64 for {name}") from exc
        if receipt.get("bytes") != len(data) or receipt.get("sha256") != _sha(data):
            raise AstraEvidenceError(f"embedded ASTRA receipt drifted: {name}")
        decoded[name] = data
    return decoded


def _projection_sha(projection: Any) -> str:
    return _sha(json.dumps(projection, separators=(",", ":"), sort_keys=True).encode())


def _security_argv(argv: Any, *, network: str) -> None:
    if (
        not isinstance(argv, list)
        or argv[:2] != ["docker", "run"]
        or argv[argv.index("--network") + 1] != network
        or "--read-only" not in argv
        or argv[argv.index("--cap-drop") + 1] != "ALL"
        or argv[argv.index("--security-opt") + 1] != "no-new-privileges"
        or "--gpus" in argv
    ):
        raise AstraEvidenceError("ASTRA contained runtime argv drifted")


def _without_access_count(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _without_access_count(item) for key, item in value.items() if key != "access_count"
        }
    if isinstance(value, list):
        return [_without_access_count(item) for item in value]
    return value


def _validate_run(run: dict[str, Any], index: int) -> dict[str, Any]:
    if (
        run.get("repeat") != index
        or run.get("slurm_job_id") != 269
        or run.get("forced_database_sigkill") is not True
        or run.get("execution_contract_sha256") != EXPECTED_CONTRACT
    ):
        raise AstraEvidenceError(f"ASTRA repeat {index} identity drifted")
    _security_argv(run.get("database_first_start_argv"), network="none")
    _security_argv(run.get("database_second_start_argv"), network="none")
    for phase in ("prepare", "restart"):
        block = run.get(phase)
        if not isinstance(block, dict):
            raise AstraEvidenceError(f"ASTRA repeat {index} {phase} is missing")
        _security_argv(
            block.get("argv"), network=block["argv"][block["argv"].index("--network") + 1]
        )
        result = block.get("result")
        if not isinstance(result, dict) or result.get("phase") != phase:
            raise AstraEvidenceError(f"ASTRA repeat {index} {phase} result drifted")
        if result.get("projection_sha256") != _projection_sha(result.get("projection")):
            raise AstraEvidenceError(f"ASTRA repeat {index} {phase} projection drifted")
    prepare = run["prepare"]["result"]
    restart = run["restart"]["result"]
    if (
        prepare.get("all_pinned_window_exceeds_capacity") is not True
        or prepare.get("all_pinned_window_size") != 13
        or prepare.get("bounded_unpinned_window") is not True
        or prepare.get("duplicate_native_ids") != 2
        or prepare.get("duplicate_write_creates_distinct_rows") is not True
        or prepare.get("evicted_memory_remains_durable") is not True
        or prepare.get("retrieval_driven_readmission") is not True
        or prepare.get("user_isolation") is not True
        or restart.get("forced_restart_preserves_acknowledged_state") is not True
        or restart.get("native_idempotency_key_available") is not False
        or restart.get("native_physical_user_purge_available") is not False
        or restart.get("retrieval_driven_readmission") is not True
        or restart.get("session_state_retains_soft_deleted_reference") is not True
        or restart.get("soft_deleted_plaintext_row_remains") is not True
        or restart.get("user_isolation") is not True
    ):
        raise AstraEvidenceError(f"ASTRA repeat {index} lifecycle checks drifted")
    return {phase: run[phase]["result"]["projection"] for phase in ("prepare", "restart")}


def validate_astra_native_lifecycle_evidence(
    bundle_or_path: dict[str, Any] | Path,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    if isinstance(bundle_or_path, Path):
        bundle = _json(bundle_or_path.read_bytes(), "ASTRA evidence")
        root = project_root or bundle_or_path.resolve().parents[3]
    else:
        bundle = bundle_or_path
        if project_root is None:
            raise AstraEvidenceError("project_root is required")
        root = project_root
    if (
        bundle.get("schema_version") != 1
        or bundle.get("source_id") != "astra-working-set"
        or bundle.get("source_revisions") != {"https://github.com/cyh7789/astra": EXPECTED_REVISION}
        or bundle.get("evidence_grade") != "local-negative-reproduced"
        or bundle.get("evidence_kind") != "h100-native-lifecycle-admission-negative"
        or bundle.get("status") != EXPECTED_STATUS
        or bundle.get("runtime_lane") != "docker-under-slurm-h100-allocation-no-container-gpu"
        or bundle.get("scientific_result") is not False
        or bundle.get("publication_ready") is not False
        or bundle.get("run_count") != 2
        or bundle.get("slurm_job_id") != 269
        or bundle.get("gpu_sku") != "H100"
        or bundle.get("gpu_count") != 1
        or bundle.get("source_archive_sha256") != EXPECTED_SOURCE_ARCHIVE
        or bundle.get("image_archive_sha256") != EXPECTED_IMAGE_ARCHIVE
        or bundle.get("execution_contract_sha256") != EXPECTED_CONTRACT
        or bundle.get("claim_boundary") != CLAIM_BOUNDARY
        or bundle.get("projection_without_access_count_sha256") != EXPECTED_STRIPPED_PROJECTION
    ):
        raise AstraEvidenceError("ASTRA evidence identity drifted")
    code_files = bundle.get("code_files")
    if not isinstance(code_files, dict) or set(code_files) != CODE_PATHS:
        raise AstraEvidenceError("ASTRA code receipt roster drifted")
    for name, expected in code_files.items():
        path = root / name
        if (
            not isinstance(expected, str)
            or not re.fullmatch(r"[0-9a-f]{64}", expected)
            or path.is_symlink()
            or not path.is_file()
            or _sha(path.read_bytes()) != expected
        ):
            raise AstraEvidenceError(f"ASTRA code receipt drifted: {name}")
    prior = bundle.get("prior_component_receipt")
    prior_path = root / "research/evidence/memory/astra-working-set-core-v1.json"
    if (
        prior
        != {
            "artifact_path": "research/evidence/memory/astra-working-set-core-v1.json",
            "sha256": "3a310140916bd73dc525e5cd2a614978b40b106602411dc22eb7532f5e24258e",
        }
        or _sha(prior_path.read_bytes()) != prior["sha256"]
    ):
        raise AstraEvidenceError("ASTRA prior component receipt drifted")
    files = _decode_files(bundle.get("files"))
    manifest_rows = files["manifest.sha256"].decode().splitlines()
    expected_manifest = {
        name: _sha(files[name]) for name in EXPECTED_FILES if name != "manifest.sha256"
    }
    observed_manifest: dict[str, str] = {}
    for row in manifest_rows:
        digest, separator, name = row.partition("  ")
        if not separator or name in observed_manifest:
            raise AstraEvidenceError("ASTRA manifest row drifted")
        observed_manifest[name] = digest
    if observed_manifest != expected_manifest:
        raise AstraEvidenceError("ASTRA manifest content drifted")
    analysis = _json(files["analysis.json"], "analysis.json")
    if (
        analysis.get("schema_version") != 1
        or analysis.get("status") != EXPECTED_STATUS
        or analysis.get("scientific_result") is not False
        or analysis.get("publication_ready") is not False
        or analysis.get("evidence_role") != "native-lifecycle-admission-negative"
        or analysis.get("slurm_job_id") != 269
        or analysis.get("gpu_sku") != "H100"
        or analysis.get("gpu_count") != 1
        or analysis.get("source_archive_sha256") != EXPECTED_SOURCE_ARCHIVE
        or analysis.get("execution_contract_sha256") != EXPECTED_CONTRACT
        or analysis.get("projection_without_access_count_sha256") != EXPECTED_STRIPPED_PROJECTION
        or analysis.get("all_registered_boolean_lifecycle_checks_passed_in_each_repeat") is not True
        or analysis.get("cross_repeat_projection_gate_passed") is not False
        or analysis.get("claim_boundary") != CLAIM_BOUNDARY
    ):
        raise AstraEvidenceError("ASTRA analysis semantics drifted")
    runs = [_json(files[f"repeat-{index}.json"], f"repeat-{index}.json") for index in (0, 1)]
    projections = [_validate_run(run, index) for index, run in enumerate(runs)]
    for phase in ("prepare", "restart"):
        hashes = [_projection_sha(item[phase]) for item in projections]
        if hashes != analysis["repeat_projection_sha256"][phase] or len(set(hashes)) != 2:
            raise AstraEvidenceError(f"ASTRA {phase} nondeterminism receipt drifted")
        totals = [
            sum(row["access_count"] for row in item[phase]["memories"]) for item in projections
        ]
        if totals != analysis["access_count_totals"][phase] or len(set(totals)) != 1:
            raise AstraEvidenceError(f"ASTRA {phase} access totals drifted")
        first = {row["key"]: row["access_count"] for row in projections[0][phase]["memories"]}
        second = {row["key"]: row["access_count"] for row in projections[1][phase]["memories"]}
        differing = sum(first[key] != second[key] for key in first)
        if (
            set(first) != set(second)
            or differing != analysis["differing_access_count_records"][phase]
        ):
            raise AstraEvidenceError(f"ASTRA {phase} differing-record count drifted")
        if _without_access_count(projections[0][phase]) != _without_access_count(
            projections[1][phase]
        ):
            raise AstraEvidenceError(f"ASTRA {phase} non-access semantics drifted")
    cause = analysis.get("upstream_cause", {})
    if (
        cause.get("store_path") != "src/store.ts"
        or cause.get("store_sha256")
        != "61bda35f817de338943a41fb3f159a845afb45792b6305324191bb228817ebe9"
        or cause.get("embedder_path") != "src/embedder.ts"
        or cause.get("embedder_sha256")
        != "763bfe30ff23c33893aadeb40289532d0a4b81e9497a6dbd54db221ae6830ccc"
        or len(cause.get("missing_tie_breaks", [])) != 3
    ):
        raise AstraEvidenceError("ASTRA upstream-cause receipt drifted")
    if files["slurm-269.out"].decode() != (
        '{"status": "VALIDATED_DISCOVERY_SOURCE", "members": 594}\n'
        "ASTRA lifecycle doctor FAIL: ASTRA clean-state semantic projections differ\n"
    ):
        raise AstraEvidenceError("ASTRA Slurm output drifted")
    scontrol = files["slurm-269.scontrol.txt"].decode()
    for token in ("JobId=269", "JobState=FAILED", "ExitCode=1:0", "gres:gpu:h100:1"):
        if token not in scontrol:
            raise AstraEvidenceError(f"ASTRA Slurm allocation drifted: {token}")
    return bundle


def seal(root: Path, output: Path) -> dict[str, Any]:
    files = {name: _capture(root / name) for name in sorted(EXPECTED_FILES)}
    bundle = {
        "schema_version": 1,
        "source_id": "astra-working-set",
        "source_revisions": {"https://github.com/cyh7789/astra": EXPECTED_REVISION},
        "evidence_grade": "local-negative-reproduced",
        "evidence_kind": "h100-native-lifecycle-admission-negative",
        "status": EXPECTED_STATUS,
        "runtime_lane": "docker-under-slurm-h100-allocation-no-container-gpu",
        "scientific_result": False,
        "publication_ready": False,
        "run_count": 2,
        "slurm_job_id": 269,
        "gpu_sku": "H100",
        "gpu_count": 1,
        "source_archive_sha256": EXPECTED_SOURCE_ARCHIVE,
        "image_archive_sha256": EXPECTED_IMAGE_ARCHIVE,
        "execution_contract_sha256": EXPECTED_CONTRACT,
        "projection_without_access_count_sha256": EXPECTED_STRIPPED_PROJECTION,
        "claim_boundary": CLAIM_BOUNDARY,
        "prior_component_receipt": {
            "artifact_path": "research/evidence/memory/astra-working-set-core-v1.json",
            "sha256": "3a310140916bd73dc525e5cd2a614978b40b106602411dc22eb7532f5e24258e",
        },
        "code_files": {
            name: _sha((PROJECT_ROOT / name).read_bytes()) for name in sorted(CODE_PATHS)
        },
        "files": files,
    }
    validate_astra_native_lifecycle_evidence(bundle, project_root=PROJECT_ROOT)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return bundle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        validate_astra_native_lifecycle_evidence(args.output, project_root=PROJECT_ROOT)
        print(f"ASTRA native-lifecycle evidence valid: {args.output}")
    else:
        seal(args.root, args.output)
        print(f"sealed ASTRA native-lifecycle evidence: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
