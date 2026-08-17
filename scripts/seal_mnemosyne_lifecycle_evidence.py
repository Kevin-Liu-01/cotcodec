#!/usr/bin/env python3
"""Seal and validate the two-repeat Mnemosyne lifecycle negative."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_mnemosyne_lifecycle_doctor import _stable_projection  # noqa: E402
from scripts.validate_mnemosyne_lifecycle_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    EXPECTED_SOURCE,
    EXPECTED_STATUS,
)

DEFAULT_ROOT = (
    PROJECT_ROOT
    / "data"
    / "results"
    / "mnemosyne-lifecycle"
    / "2026-08-16-local-docker-v1"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "research"
    / "evidence"
    / "memory"
    / "mnemosyne-one-way-consolidation-negative-v1.json"
)
DEFAULT_IMAGE_INSPECT = Path("/tmp/mnemosyne-inspect.json")
IMAGE_ID = "sha256:88a87e9713c10058f19d7d56bd1d032387de16eea8d4e8e0316478df22c45cd5"
STABLE_PROJECTION_SHA256 = (
    "4ba68b74bfa4c0d6c7e65a954a14f92bd38aa715d50faef60b9c4b350c807d70"
)
RUNTIME_LANE = "local-arm64-docker-network-none"
CODE_PATHS = {
    "Dockerfile": PROJECT_ROOT / "infra/memory-baselines/mnemosyne/Dockerfile",
    "doctor.py": PROJECT_ROOT / "infra/memory-baselines/mnemosyne/doctor.py",
    "run_mnemosyne_lifecycle_doctor.py": (
        PROJECT_ROOT / "scripts/run_mnemosyne_lifecycle_doctor.py"
    ),
    "validate_mnemosyne_lifecycle_experiment.py": (
        PROJECT_ROOT / "scripts/validate_mnemosyne_lifecycle_experiment.py"
    ),
}
PHASES = ("prepare", "verify-restart", "purge")
EXPECTED_FILE_ROSTER = {
    *CODE_PATHS,
    "experiment.yaml",
    "image-inspect.json",
    "manifest.json",
    "report.json",
    *(f"repeat-{repeat}/{phase}.json" for repeat in (1, 2) for phase in PHASES),
}


class EvidenceError(ValueError):
    """Raised when the retained lifecycle evidence is incomplete or drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode()


def _strict_json(data: bytes, owner: str) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise EvidenceError(f"{owner} contains non-finite value {value}")

    try:
        value = json.loads(data, parse_constant=reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"{owner} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise EvidenceError(f"{owner} must be a JSON object")
    return value


def _capture(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise EvidenceError(f"expected regular evidence input: {path}")
    data = path.read_bytes()
    return {
        "bytes": len(data),
        "sha256": _sha(data),
        "content_base64": base64.b64encode(data).decode("ascii"),
    }


def _decode_files(receipts: Any) -> dict[str, bytes]:
    if not isinstance(receipts, dict) or set(receipts) != EXPECTED_FILE_ROSTER:
        raise EvidenceError("Mnemosyne evidence file roster drifted")
    decoded: dict[str, bytes] = {}
    for name, receipt in receipts.items():
        if not isinstance(receipt, dict):
            raise EvidenceError(f"invalid receipt for {name}")
        try:
            data = base64.b64decode(receipt.get("content_base64", ""), validate=True)
        except (TypeError, ValueError) as exc:
            raise EvidenceError(f"invalid base64 for {name}") from exc
        if receipt.get("bytes") != len(data) or receipt.get("sha256") != _sha(data):
            raise EvidenceError(f"embedded file receipt drifted: {name}")
        decoded[name] = data
    return decoded


def _validate_phase(payload: dict[str, Any], phase: str, repeat: int) -> None:
    if (
        payload.get("schema_version") != 1
        or payload.get("phase") != phase
        or payload.get("repeat") != repeat
        or payload.get("mnemosyne_version") != "3.16.0"
        or payload.get("scientific_result") is not False
        or payload.get("publication_ready") is not False
        or payload.get("model_calls") != 0
        or payload.get("embedding_calls") != 0
    ):
        raise EvidenceError(f"repeat {repeat} {phase} identity drifted")


def validate_files(files: dict[str, bytes]) -> dict[str, Any]:
    if set(files) != EXPECTED_FILE_ROSTER:
        raise EvidenceError("Mnemosyne evidence file roster drifted")

    experiment = yaml.safe_load(files["experiment.yaml"])
    if (
        not isinstance(experiment, dict)
        or experiment.get("name") != "stage3-mnemosyne-lifecycle-doctor"
        or experiment.get("source") != EXPECTED_SOURCE
        or experiment.get("expected_falsification", {}).get("status")
        != EXPECTED_STATUS
        or experiment.get("admission", {}).get("h100_actor")
        != "forbidden-for-this-revision"
    ):
        raise EvidenceError("embedded experiment contract drifted")

    report = _strict_json(files["report.json"], "report.json")
    manifest = _strict_json(files["manifest.json"], "manifest.json")
    if (
        report.get("status") != EXPECTED_STATUS
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("h100_actor_admission") != "forbidden-for-this-revision"
        or report.get("source") != EXPECTED_SOURCE
        or report.get("runtime") != experiment.get("runtime")
        or report.get("experiment_sha256") != _sha(files["experiment.yaml"])
        or report.get("dockerfile_sha256") != _sha(files["Dockerfile"])
        or report.get("doctor_sha256") != _sha(files["doctor.py"])
        or report.get("stable_projection_sha256") != STABLE_PROJECTION_SHA256
        or report.get("reproduced_in_two_clean_states") is not True
    ):
        raise EvidenceError("Mnemosyne report contract drifted")
    if (
        manifest
        != {
            "artifact_count": 6,
            "image_id": IMAGE_ID,
            "report": "report.json",
            "report_sha256": _sha(files["report.json"]),
            "schema_version": 1,
            "stable_projection_sha256": STABLE_PROJECTION_SHA256,
            "status": "SEALED_DISCOVERY_NEGATIVE",
        }
    ):
        raise EvidenceError("Mnemosyne manifest contract drifted")

    try:
        image_rows = json.loads(files["image-inspect.json"])
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceError("image inspection is invalid JSON") from exc
    if not isinstance(image_rows, list) or len(image_rows) != 1:
        raise EvidenceError("image inspection roster drifted")
    image = image_rows[0]
    labels = image.get("Config", {}).get("Labels", {})
    report_image = report.get("image", {})
    if (
        image.get("Id") != IMAGE_ID
        or image.get("Architecture") != "arm64"
        or image.get("Os") != "linux"
        or image.get("Config", {}).get("User") != "65532:65532"
        or image.get("Config", {}).get("Entrypoint")
        != ["/opt/mnemosyne/source/.venv/bin/python"]
        or labels.get("org.cotcodec.discovery-only") != "true"
        or labels.get("org.opencontainers.image.revision")
        != EXPECTED_SOURCE["revision"]
        or labels.get("org.cotcodec.source-tree") != EXPECTED_SOURCE["tree"]
        or labels.get("org.cotcodec.source-archive-sha256")
        != EXPECTED_SOURCE["git_archive_tar_sha256"]
        or labels.get("org.cotcodec.lock-sha256")
        != EXPECTED_SOURCE["uv_lock_sha256"]
        or labels.get("org.cotcodec.doctor-sha256") != _sha(files["doctor.py"])
        or report_image.get("image_id") != IMAGE_ID
        or report_image.get("inspect_sha256") != _sha(files["image-inspect.json"])
    ):
        raise EvidenceError("Mnemosyne image provenance drifted")

    receipts = report.get("phase_receipts")
    if not isinstance(receipts, list) or len(receipts) != 6:
        raise EvidenceError("Mnemosyne phase receipt roster drifted")
    receipt_by_key: dict[tuple[int, str], dict[str, Any]] = {}
    for receipt in receipts:
        if not isinstance(receipt, dict):
            raise EvidenceError("Mnemosyne phase receipt is invalid")
        key = (receipt.get("repeat"), receipt.get("phase"))
        if key in receipt_by_key or key[0] not in (1, 2) or key[1] not in PHASES:
            raise EvidenceError("Mnemosyne phase receipt identity drifted")
        argv = receipt.get("argv")
        if (
            not isinstance(argv, list)
            or argv[:3] != ["docker", "run", "--rm"]
            or "--pull=never" not in argv
            or "--network" not in argv
            or argv[argv.index("--network") + 1] != "none"
            or "--read-only" not in argv
            or argv[argv.index("--cap-drop") + 1] != "ALL"
            or argv[argv.index("--security-opt") + 1] != "no-new-privileges"
            or "--gpus" in argv
            or IMAGE_ID not in argv
            or any("KEY=" in value or "TOKEN=" in value for value in argv)
        ):
            raise EvidenceError("Mnemosyne contained argv drifted")
        name = f"repeat-{key[0]}/{key[1]}.json"
        if receipt.get("artifact_sha256") != _sha(files[name]):
            raise EvidenceError(f"Mnemosyne phase digest drifted: {name}")
        receipt_by_key[key] = receipt

    projections: list[dict[str, Any]] = []
    for repeat in (1, 2):
        run: dict[str, Any] = {}
        for phase in PHASES:
            payload = _strict_json(
                files[f"repeat-{repeat}/{phase}.json"],
                f"repeat-{repeat}/{phase}.json",
            )
            _validate_phase(payload, phase, repeat)
            run[phase] = payload
        prepare = run["prepare"]
        if not all(
            prepare.get(field) is True
            for field in (
                "duplicate_retry_idempotent",
                "session_isolation_before_sleep",
                "source_rows_marked_consolidated",
                "episodic_summary_created",
                "consolidated_removed_from_active_context",
                "consolidated_recallable",
                "cross_session_recall_blocked",
                "documented_forget_deleted_source",
                "episodic_summary_survived_source_forget",
                "forgotten_canary_still_recallable",
            )
        ):
            raise EvidenceError("Mnemosyne positive lifecycle prerequisite drifted")
        restart = run["verify-restart"]
        if not all(
            restart.get(field) is True
            for field in (
                "restart_preserved_episodic_summary",
                "restart_preserved_recall",
                "restart_preserved_session_isolation",
                "recall_did_not_reactivate",
                "episodic_source_lineage_present",
            )
        ):
            raise EvidenceError("Mnemosyne restart prerequisite drifted")
        purge = run["purge"]
        if (
            purge.get("status") != EXPECTED_STATUS
            or purge.get("episodic_forget_results") != [False]
            or purge.get("native_session_scoped_purge_available") is not False
            or purge.get("logical_canary_rows_after_documented_forget", {}).get(
                "episodic_memory"
            )
            != 1
            or purge.get("plaintext_canary_residue_reproduced") is not True
            or purge.get("physical_hit_files") != ["mnemosyne.db"]
            or purge.get("archive_to_active_transition_available") is not False
            or purge.get("h100_actor_admission") != "forbidden-for-this-revision"
        ):
            raise EvidenceError("Mnemosyne deletion/reactivation falsifier drifted")
        projections.append(_stable_projection(run))

    if projections[0] != projections[1] or projections[0] != report.get(
        "stable_projection"
    ):
        raise EvidenceError("Mnemosyne clean-state semantic projections drifted")
    if _sha((json.dumps(projections[0], indent=2, sort_keys=True) + "\n").encode()) != (
        STABLE_PROJECTION_SHA256
    ):
        raise EvidenceError("Mnemosyne stable projection digest drifted")
    return {
        "image_id": IMAGE_ID,
        "stable_projection": projections[0],
        "stable_projection_sha256": STABLE_PROJECTION_SHA256,
        "report_sha256": _sha(files["report.json"]),
        "manifest_sha256": _sha(files["manifest.json"]),
    }


def validate_evidence(path: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise EvidenceError(f"expected regular evidence bundle: {path}")
    bundle = _strict_json(path.read_bytes(), "evidence bundle")
    if (
        bundle.get("schema_version") != 1
        or bundle.get("evidence_kind") != "native-negative-reproduction"
        or bundle.get("source_id") != "mnemosyne-oss"
        or bundle.get("evidence_grade") != "local-negative-reproduced"
        or bundle.get("status") != EXPECTED_STATUS
        or bundle.get("scientific_result") is not False
        or bundle.get("publication_ready") is not False
        or bundle.get("h100_admission") != "forbidden-for-this-revision"
        or bundle.get("runtime_lane") != RUNTIME_LANE
        or bundle.get("run_count") != 2
        or bundle.get("source_revisions")
        != {"https://github.com/mnemosyne-oss/mnemosyne": EXPECTED_SOURCE["revision"]}
    ):
        raise EvidenceError("Mnemosyne top-level evidence contract drifted")
    verified = validate_files(_decode_files(bundle.get("files")))
    if (
        bundle.get("shared_image_id") != verified["image_id"]
        or bundle.get("stable_projection") != verified["stable_projection"]
        or bundle.get("stable_projection_sha256")
        != verified["stable_projection_sha256"]
        or bundle.get("report_sha256") != verified["report_sha256"]
        or bundle.get("manifest_sha256") != verified["manifest_sha256"]
        or bundle.get("claim_boundary")
        != {
            "bidirectional_paging_demonstrated": False,
            "consolidated_source_complete_forget": False,
            "h100_actor_admission": "forbidden-for-this-revision",
            "memory_quality_measured": False,
            "one_way_consolidation_reproduced": True,
        }
    ):
        raise EvidenceError("Mnemosyne evidence receipt drifted")
    return bundle


def seal(root: Path, image_inspect: Path) -> dict[str, Any]:
    paths = {
        **CODE_PATHS,
        "experiment.yaml": DEFAULT_EXPERIMENT,
        "image-inspect.json": image_inspect,
        "manifest.json": root / "manifest.json",
        "report.json": root / "report.json",
        **{
            f"repeat-{repeat}/{phase}.json": root
            / f"repeat-{repeat}"
            / f"{phase}.json"
            for repeat in (1, 2)
            for phase in PHASES
        },
    }
    files = {name: _capture(path) for name, path in sorted(paths.items())}
    verified = validate_files(
        {
            name: base64.b64decode(receipt["content_base64"])
            for name, receipt in files.items()
        }
    )
    return {
        "schema_version": 1,
        "evidence_kind": "native-negative-reproduction",
        "source_id": "mnemosyne-oss",
        "evidence_grade": "local-negative-reproduced",
        "status": EXPECTED_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "h100_admission": "forbidden-for-this-revision",
        "source_revisions": {
            "https://github.com/mnemosyne-oss/mnemosyne": EXPECTED_SOURCE["revision"]
        },
        "runtime_lane": RUNTIME_LANE,
        "run_count": 2,
        "shared_image_id": verified["image_id"],
        "stable_projection": verified["stable_projection"],
        "stable_projection_sha256": verified["stable_projection_sha256"],
        "report_sha256": verified["report_sha256"],
        "manifest_sha256": verified["manifest_sha256"],
        "claim_boundary": {
            "bidirectional_paging_demonstrated": False,
            "consolidated_source_complete_forget": False,
            "h100_actor_admission": "forbidden-for-this-revision",
            "memory_quality_measured": False,
            "one_way_consolidation_reproduced": True,
        },
        "files": files,
    }


def _publish(payload: dict[str, Any], output: Path) -> str:
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        if output.is_symlink() or output.read_bytes() != encoded:
            raise EvidenceError(f"existing evidence output differs: {output}")
        return _sha(encoded)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temp_name, output)
    finally:
        Path(temp_name).unlink(missing_ok=True)
    return _sha(encoded)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--image-inspect", type=Path, default=DEFAULT_IMAGE_INSPECT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if args.validate_only:
        bundle = validate_evidence(args.output)
        print(f"Mnemosyne lifecycle evidence PASS: {bundle['status']}")
        return 0
    digest = _publish(seal(args.root, args.image_inspect), args.output)
    validate_evidence(args.output)
    print(f"sealed Mnemosyne lifecycle evidence: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
