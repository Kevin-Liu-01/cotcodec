#!/usr/bin/env python3
"""Seal and validate the two-repeat Icarus lifecycle negative."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_icarus_lifecycle_doctor import _projection  # noqa: E402
from scripts.validate_icarus_lifecycle_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    EXPECTED_SOURCE,
    EXPECTED_STATUS,
)

DEFAULT_ROOT = (
    PROJECT_ROOT / "data/results/icarus-lifecycle/2026-08-16-local-docker-v1"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "research/evidence/memory/icarus-manual-lifecycle-negative-v1.json"
)
DEFAULT_IMAGE_INSPECT = Path("/tmp/icarus-v2-inspect.json")
IMAGE_ID = "sha256:bc3dd9e4e9f8048f538c759ffdbaf47787b92fcd2c5c710495283899fb0a1cff"
STABLE_PROJECTION_SHA256 = (
    "e8207fbeebfd4e2193f371f4ae41dd653a8cf5bb85decb064feaa29407d9a7d7"
)
RUNTIME_LANE = "local-arm64-docker-network-none"
PHASES = ("prepare", "verify-restart", "purge-probe")
CODE_PATHS = {
    "Dockerfile": PROJECT_ROOT / "infra/memory-baselines/icarus/Dockerfile",
    "doctor.py": PROJECT_ROOT / "infra/memory-baselines/icarus/doctor.py",
    "run_icarus_lifecycle_doctor.py": PROJECT_ROOT
    / "scripts/run_icarus_lifecycle_doctor.py",
    "validate_icarus_lifecycle_experiment.py": PROJECT_ROOT
    / "scripts/validate_icarus_lifecycle_experiment.py",
}
EXPECTED_FILE_ROSTER = {
    *CODE_PATHS,
    "experiment.yaml",
    "image-inspect.json",
    "manifest.json",
    "report.json",
    "upstream-suite.txt",
    *(f"repeat-{repeat}/{phase}.json" for repeat in (1, 2) for phase in PHASES),
}


class EvidenceError(ValueError):
    """Raised when retained Icarus evidence is incomplete or drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
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
        raise EvidenceError("Icarus evidence file roster drifted")
    decoded: dict[str, bytes] = {}
    for name, receipt in receipts.items():
        if not isinstance(receipt, dict):
            raise EvidenceError(f"invalid Icarus receipt for {name}")
        try:
            data = base64.b64decode(receipt.get("content_base64", ""), validate=True)
        except (TypeError, ValueError) as exc:
            raise EvidenceError(f"invalid base64 for {name}") from exc
        if receipt.get("bytes") != len(data) or receipt.get("sha256") != _sha(data):
            raise EvidenceError(f"embedded Icarus receipt drifted: {name}")
        decoded[name] = data
    return decoded


def _validate_identity(payload: dict[str, Any], phase: str, repeat: int) -> None:
    if (
        payload.get("schema_version") != 1
        or payload.get("phase") != phase
        or payload.get("repeat") != repeat
        or payload.get("icarus_version") != "0.3.0"
        or payload.get("scientific_result") is not False
        or payload.get("publication_ready") is not False
        or payload.get("model_calls") != 0
        or payload.get("embedding_calls") != 0
    ):
        raise EvidenceError(f"Icarus repeat {repeat} {phase} identity drifted")


def validate_files(files: dict[str, bytes]) -> dict[str, Any]:
    if set(files) != EXPECTED_FILE_ROSTER:
        raise EvidenceError("Icarus evidence file roster drifted")
    experiment = yaml.safe_load(files["experiment.yaml"])
    if (
        not isinstance(experiment, dict)
        or experiment.get("name") != "stage3-icarus-lifecycle-doctor"
        or experiment.get("source") != EXPECTED_SOURCE
        or experiment.get("expected_falsification", {}).get("status") != EXPECTED_STATUS
        or experiment.get("admission", {}).get("h100_actor")
        != "forbidden-for-this-revision"
    ):
        raise EvidenceError("embedded Icarus experiment drifted")

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
        raise EvidenceError("Icarus report contract drifted")
    if manifest != {
        "artifact_count": 7,
        "image_id": IMAGE_ID,
        "report": "report.json",
        "report_sha256": _sha(files["report.json"]),
        "schema_version": 1,
        "stable_projection_sha256": STABLE_PROJECTION_SHA256,
        "status": "SEALED_DISCOVERY_NEGATIVE",
    }:
        raise EvidenceError("Icarus manifest contract drifted")

    suite = report.get("upstream_suite")
    if (
        not isinstance(suite, dict)
        or {key: suite.get(key) for key in ("failed", "passed", "skipped")}
        != {"failed": 6, "passed": 207, "skipped": 39}
        or suite.get("exit_code") != 1
        or suite.get("failure_class") != "mcp-major-version-path-incompatibility"
        or suite.get("output_sha256") != _sha(files["upstream-suite.txt"])
    ):
        raise EvidenceError("Icarus upstream-suite receipt drifted")
    suite_text = files["upstream-suite.txt"].decode("utf-8", errors="replace")
    if "6 failed, 207 passed, 39 skipped" not in suite_text:
        raise EvidenceError("Icarus upstream-suite output drifted")

    try:
        image_rows = json.loads(files["image-inspect.json"])
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceError("Icarus image inspection is invalid JSON") from exc
    if not isinstance(image_rows, list) or len(image_rows) != 1:
        raise EvidenceError("Icarus image inspection roster drifted")
    image = image_rows[0]
    labels = image.get("Config", {}).get("Labels", {})
    report_image = report.get("image", {})
    if (
        image.get("Id") != IMAGE_ID
        or image.get("Architecture") != "arm64"
        or image.get("Os") != "linux"
        or image.get("Config", {}).get("User") != "65532:65532"
        or image.get("Config", {}).get("Entrypoint") != ["python"]
        or labels.get("org.cotcodec.discovery-only") != "true"
        or labels.get("org.opencontainers.image.revision") != EXPECTED_SOURCE["revision"]
        or labels.get("org.cotcodec.source-tree") != EXPECTED_SOURCE["tree"]
        or labels.get("org.cotcodec.source-archive-sha256")
        != EXPECTED_SOURCE["git_archive_tar_sha256"]
        or labels.get("org.cotcodec.doctor-sha256") != _sha(files["doctor.py"])
        or report_image.get("image_id") != IMAGE_ID
        or report_image.get("inspect_sha256") != _sha(files["image-inspect.json"])
    ):
        raise EvidenceError("Icarus image provenance drifted")

    receipts = report.get("phase_receipts")
    if not isinstance(receipts, list) or len(receipts) != 6:
        raise EvidenceError("Icarus phase receipt roster drifted")
    receipt_map: dict[tuple[int, str], dict[str, Any]] = {}
    for receipt in receipts:
        if not isinstance(receipt, dict):
            raise EvidenceError("Icarus phase receipt is invalid")
        key = (receipt.get("repeat"), receipt.get("phase"))
        if key in receipt_map or key[0] not in (1, 2) or key[1] not in PHASES:
            raise EvidenceError("Icarus phase receipt identity drifted")
        argv = receipt.get("argv")
        if (
            not isinstance(argv, list)
            or argv[:4] != ["docker", "run", "--rm", "--pull"]
            or argv[4] != "never"
            or argv[argv.index("--network") + 1] != "none"
            or "--read-only" not in argv
            or argv[argv.index("--cap-drop") + 1] != "ALL"
            or argv[argv.index("--security-opt") + 1] != "no-new-privileges"
            or "--gpus" in argv
            or IMAGE_ID not in argv
            or any("KEY=" in value or "TOKEN=" in value for value in argv)
        ):
            raise EvidenceError("Icarus contained argv drifted")
        name = f"repeat-{key[0]}/{key[1]}.json"
        if receipt.get("artifact_sha256") != _sha(files[name]):
            raise EvidenceError(f"Icarus phase digest drifted: {name}")
        receipt_map[key] = receipt

    projections: list[dict[str, Any]] = []
    for repeat in (1, 2):
        run: dict[str, Any] = {}
        for phase in PHASES:
            payload = _strict_json(
                files[f"repeat-{repeat}/{phase}.json"],
                f"repeat-{repeat}/{phase}.json",
            )
            _validate_identity(payload, phase, repeat)
            run[phase] = payload
        projections.append(_projection(run))
    if projections[0] != projections[1] or projections[0] != report.get(
        "stable_projection"
    ):
        raise EvidenceError("Icarus clean-state semantic projections drifted")
    if _sha((json.dumps(projections[0], indent=2, sort_keys=True) + "\n").encode()) != (
        STABLE_PROJECTION_SHA256
    ):
        raise EvidenceError("Icarus stable projection digest drifted")
    return {
        "image_id": IMAGE_ID,
        "projection": projections[0],
        "report_sha256": _sha(files["report.json"]),
        "manifest_sha256": _sha(files["manifest.json"]),
    }


def validate_evidence(path: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise EvidenceError(f"expected regular Icarus evidence bundle: {path}")
    bundle = _strict_json(path.read_bytes(), "Icarus evidence bundle")
    if (
        bundle.get("schema_version") != 1
        or bundle.get("evidence_kind") != "native-negative-reproduction"
        or bundle.get("source_id") != "icarus-memory-infra"
        or bundle.get("evidence_grade") != "local-negative-reproduced"
        or bundle.get("status") != EXPECTED_STATUS
        or bundle.get("scientific_result") is not False
        or bundle.get("publication_ready") is not False
        or bundle.get("h100_admission") != "forbidden-for-this-revision"
        or bundle.get("runtime_lane") != RUNTIME_LANE
        or bundle.get("run_count") != 2
        or bundle.get("source_revisions")
        != {"https://github.com/esaradev/icarus-memory-infra": EXPECTED_SOURCE["revision"]}
    ):
        raise EvidenceError("Icarus top-level evidence contract drifted")
    verified = validate_files(_decode_files(bundle.get("files")))
    if (
        bundle.get("shared_image_id") != verified["image_id"]
        or bundle.get("stable_projection") != verified["projection"]
        or bundle.get("stable_projection_sha256") != STABLE_PROJECTION_SHA256
        or bundle.get("report_sha256") != verified["report_sha256"]
        or bundle.get("manifest_sha256") != verified["manifest_sha256"]
        or bundle.get("claim_boundary")
        != {
            "autonomous_paging_demonstrated": False,
            "idempotent_promotion": False,
            "manual_lifecycle_reproduced": True,
            "memory_quality_measured": False,
            "native_scoped_purge": False,
        }
    ):
        raise EvidenceError("Icarus evidence receipt drifted")
    return bundle


def seal(root: Path, image_inspect: Path) -> dict[str, Any]:
    paths = {
        **CODE_PATHS,
        "experiment.yaml": DEFAULT_EXPERIMENT,
        "image-inspect.json": image_inspect,
        "manifest.json": root / "manifest.json",
        "report.json": root / "report.json",
        "upstream-suite.txt": root / "upstream-suite.txt",
        **{
            f"repeat-{repeat}/{phase}.json": root / f"repeat-{repeat}/{phase}.json"
            for repeat in (1, 2)
            for phase in PHASES
        },
    }
    files = {name: path.read_bytes() for name, path in paths.items()}
    verified = validate_files(files)
    return {
        "schema_version": 1,
        "evidence_kind": "native-negative-reproduction",
        "source_id": "icarus-memory-infra",
        "source_revisions": {
            "https://github.com/esaradev/icarus-memory-infra": EXPECTED_SOURCE["revision"]
        },
        "evidence_grade": "local-negative-reproduced",
        "status": EXPECTED_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "h100_admission": "forbidden-for-this-revision",
        "runtime_lane": RUNTIME_LANE,
        "run_count": 2,
        "shared_image_id": verified["image_id"],
        "stable_projection": verified["projection"],
        "stable_projection_sha256": STABLE_PROJECTION_SHA256,
        "report_sha256": verified["report_sha256"],
        "manifest_sha256": verified["manifest_sha256"],
        "claim_boundary": {
            "autonomous_paging_demonstrated": False,
            "idempotent_promotion": False,
            "manual_lifecycle_reproduced": True,
            "memory_quality_measured": False,
            "native_scoped_purge": False,
        },
        "files": {name: _capture(path) for name, path in paths.items()},
    }


def _write_no_replace(path: Path, data: bytes) -> None:
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--image-inspect", type=Path, default=DEFAULT_IMAGE_INSPECT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if args.validate_only:
        bundle = validate_evidence(args.output.resolve())
    else:
        bundle = seal(args.root.resolve(), args.image_inspect.resolve())
        _write_no_replace(args.output.resolve(), _canonical(bundle) + b"\n")
        bundle = validate_evidence(args.output.resolve())
    print(f"Icarus lifecycle evidence PASS: {bundle['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
