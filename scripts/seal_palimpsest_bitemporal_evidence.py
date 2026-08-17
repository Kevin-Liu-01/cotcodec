#!/usr/bin/env python3
"""Seal and validate the two-repeat Palimpsest bitemporal negative."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_palimpsest_bitemporal_doctor import _projection  # noqa: E402
from scripts.validate_palimpsest_bitemporal_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    EXPECTED_SOURCE,
    EXPECTED_STATUS,
)

DEFAULT_ROOT = (
    PROJECT_ROOT / "data/results/palimpsest-bitemporal/2026-08-16-local-docker-v1"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "research/evidence/memory/palimpsest-bitemporal-negative-v1.json"
)
IMAGE_ID = "sha256:afb752691fad10b3048b46772f56a92c54c467e3982e6bfed5f6295d45ff8781"
STABLE_PROJECTION_SHA256 = (
    "f490afe9402622abe1ce3ffe2d738df55e979758381dde4faed777b830d76047"
)
RUNTIME_LANE = "local-arm64-docker-network-none"
PHASES = ("prepare", "verify-restart", "purge-probe")
CODE_PATHS = {
    "Dockerfile": PROJECT_ROOT / "infra/memory-baselines/palimpsest/Dockerfile",
    "doctor.py": PROJECT_ROOT / "infra/memory-baselines/palimpsest/doctor.py",
    "run_palimpsest_bitemporal_doctor.py": PROJECT_ROOT
    / "scripts/run_palimpsest_bitemporal_doctor.py",
    "validate_palimpsest_bitemporal_experiment.py": PROJECT_ROOT
    / "scripts/validate_palimpsest_bitemporal_experiment.py",
}
EXPECTED_FILE_ROSTER = {
    *CODE_PATHS,
    "experiment.yaml",
    "image-inspect.json",
    "manifest.json",
    "report.json",
    "upstream-suite.txt",
    *(f"repeat-{repeat}/{phase}.json" for repeat in (1, 2) for phase in PHASES),
    *(f"repeat-{repeat}/contract.json" for repeat in (1, 2)),
    *(f"repeat-{repeat}/palimpsest.db" for repeat in (1, 2)),
}


class EvidenceError(ValueError):
    """Raised when retained Palimpsest evidence is incomplete or drifts."""


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


def _capture_bytes(data: bytes) -> dict[str, Any]:
    return {
        "bytes": len(data),
        "sha256": _sha(data),
        "content_base64": base64.b64encode(data).decode("ascii"),
    }


def _capture(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise EvidenceError(f"expected regular evidence input: {path}")
    return _capture_bytes(path.read_bytes())


def _decode_files(receipts: Any) -> dict[str, bytes]:
    if not isinstance(receipts, dict) or set(receipts) != EXPECTED_FILE_ROSTER:
        raise EvidenceError("Palimpsest evidence file roster drifted")
    decoded: dict[str, bytes] = {}
    for name, receipt in receipts.items():
        if not isinstance(receipt, dict):
            raise EvidenceError(f"invalid Palimpsest receipt for {name}")
        try:
            data = base64.b64decode(receipt.get("content_base64", ""), validate=True)
        except (TypeError, ValueError) as exc:
            raise EvidenceError(f"invalid base64 for {name}") from exc
        if receipt.get("bytes") != len(data) or receipt.get("sha256") != _sha(data):
            raise EvidenceError(f"embedded Palimpsest receipt drifted: {name}")
        decoded[name] = data
    return decoded


def _validate_phase_identity(payload: dict[str, Any], phase: str, repeat: int) -> None:
    if (
        payload.get("schema_version") != 1
        or payload.get("phase") != phase
        or payload.get("repeat") != repeat
        or payload.get("scientific_result") is not False
        or payload.get("publication_ready") is not False
        or payload.get("model_calls") != 0
        or payload.get("embedding_model_calls") != 0
        or payload.get("external_api_calls") != 0
    ):
        raise EvidenceError(f"Palimpsest repeat {repeat} {phase} identity drifted")


def validate_files(files: dict[str, bytes]) -> dict[str, Any]:
    if set(files) != EXPECTED_FILE_ROSTER:
        raise EvidenceError("Palimpsest evidence file roster drifted")
    experiment = yaml.safe_load(files["experiment.yaml"])
    if (
        not isinstance(experiment, dict)
        or experiment.get("name") != "stage3-palimpsest-bitemporal-doctor"
        or experiment.get("source") != EXPECTED_SOURCE
        or experiment.get("expected_falsification", {}).get("status") != EXPECTED_STATUS
        or experiment.get("admission", {}).get("h100_actor")
        != "forbidden-for-this-revision"
    ):
        raise EvidenceError("embedded Palimpsest experiment drifted")

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
        raise EvidenceError("Palimpsest report contract drifted")
    if manifest != {
        "artifact_count": 12,
        "image_id": IMAGE_ID,
        "report": "report.json",
        "report_sha256": _sha(files["report.json"]),
        "schema_version": 1,
        "stable_projection_sha256": STABLE_PROJECTION_SHA256,
        "status": "SEALED_DISCOVERY_NEGATIVE",
    }:
        raise EvidenceError("Palimpsest manifest contract drifted")

    suite = report.get("upstream_suite")
    if (
        not isinstance(suite, dict)
        or {key: suite.get(key) for key in ("failed", "passed", "skipped")}
        != {"failed": 11, "passed": 274, "skipped": 35}
        or suite.get("exit_code") != 1
        or suite.get("output_sha256") != _sha(files["upstream-suite.txt"])
        or "11 failed, 274 passed, 35 skipped"
        not in files["upstream-suite.txt"].decode("utf-8", errors="replace")
    ):
        raise EvidenceError("Palimpsest upstream-suite receipt drifted")

    image_rows = json.loads(files["image-inspect.json"])
    if not isinstance(image_rows, list) or len(image_rows) != 1:
        raise EvidenceError("Palimpsest image inspection roster drifted")
    image = image_rows[0]
    labels = image.get("Config", {}).get("Labels", {})
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
        or report.get("image", {}).get("image_id") != IMAGE_ID
        or report.get("image", {}).get("inspect_sha256")
        != _sha(files["image-inspect.json"])
    ):
        raise EvidenceError("Palimpsest image provenance drifted")

    receipts = report.get("artifact_receipts")
    if not isinstance(receipts, list) or len(receipts) != 10:
        raise EvidenceError("Palimpsest artifact receipt roster drifted")
    expected_digests = {
        f"repeat-{repeat}/{name}": _sha(files[f"repeat-{repeat}/{name}"])
        for repeat in (1, 2)
        for name in (
            "prepare.json",
            "verify-restart.json",
            "purge-probe.json",
            "contract.json",
            "palimpsest.db",
        )
    }
    observed: dict[str, str] = {}
    for receipt in receipts:
        if not isinstance(receipt, dict) or not isinstance(receipt.get("artifact"), str):
            raise EvidenceError("Palimpsest artifact receipt is invalid")
        marker = "data/results/palimpsest-bitemporal/2026-08-16-local-docker-v1/"
        artifact = receipt["artifact"]
        if not artifact.startswith(marker):
            raise EvidenceError("Palimpsest artifact path drifted")
        name = artifact.removeprefix(marker)
        if name in observed or name not in expected_digests:
            raise EvidenceError("Palimpsest artifact roster drifted")
        if receipt.get("artifact_sha256") != expected_digests[name]:
            raise EvidenceError(f"Palimpsest artifact digest drifted: {name}")
        argv = receipt.get("argv")
        if argv is not None and (
            not isinstance(argv, list)
            or argv[:5] != ["docker", "run", "--rm", "--pull", "never"]
            or argv[argv.index("--network") + 1] != "none"
            or "--read-only" not in argv
            or argv[argv.index("--cap-drop") + 1] != "ALL"
            or argv[argv.index("--security-opt") + 1] != "no-new-privileges"
            or argv[argv.index("--user") + 1] != "65532:65532"
            or "--gpus" in argv
            or IMAGE_ID not in argv
        ):
            raise EvidenceError("Palimpsest contained argv drifted")
        observed[name] = receipt["artifact_sha256"]
    if observed != expected_digests:
        raise EvidenceError("Palimpsest artifact coverage drifted")

    projections: list[dict[str, Any]] = []
    for repeat in (1, 2):
        run: dict[str, Any] = {}
        contract = _strict_json(
            files[f"repeat-{repeat}/contract.json"],
            f"repeat-{repeat}/contract.json",
        )
        canary = contract.get("canary")
        if not isinstance(canary, str) or canary.encode() not in files[
            f"repeat-{repeat}/palimpsest.db"
        ]:
            raise EvidenceError("Palimpsest physical residue proof drifted")
        for phase in PHASES:
            payload = _strict_json(
                files[f"repeat-{repeat}/{phase}.json"],
                f"repeat-{repeat}/{phase}.json",
            )
            _validate_phase_identity(payload, phase, repeat)
            run[phase] = payload
        projections.append(_projection(run))
    if projections[0] != projections[1] or projections[0] != report.get(
        "stable_projection"
    ):
        raise EvidenceError("Palimpsest clean-state semantic projections drifted")
    if _sha((json.dumps(projections[0], indent=2, sort_keys=True) + "\n").encode()) != (
        STABLE_PROJECTION_SHA256
    ):
        raise EvidenceError("Palimpsest stable projection digest drifted")
    return {
        "image_id": IMAGE_ID,
        "projection": projections[0],
        "report_sha256": _sha(files["report.json"]),
        "manifest_sha256": _sha(files["manifest.json"]),
    }


def validate_evidence(path: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise EvidenceError(f"expected regular Palimpsest evidence bundle: {path}")
    bundle = _strict_json(path.read_bytes(), "Palimpsest evidence bundle")
    if (
        bundle.get("schema_version") != 1
        or bundle.get("evidence_kind") != "native-negative-reproduction"
        or bundle.get("source_id") != "palimpsest-bitemporal-memory"
        or bundle.get("evidence_grade") != "local-negative-reproduced"
        or bundle.get("status") != EXPECTED_STATUS
        or bundle.get("scientific_result") is not False
        or bundle.get("publication_ready") is not False
        or bundle.get("h100_admission") != "forbidden-for-this-revision"
        or bundle.get("runtime_lane") != RUNTIME_LANE
        or bundle.get("run_count") != 2
        or bundle.get("source_revisions")
        != {"https://github.com/joe51111jwd/palimpsest": EXPECTED_SOURCE["revision"]}
    ):
        raise EvidenceError("Palimpsest top-level evidence contract drifted")
    verified = validate_files(_decode_files(bundle.get("files")))
    if (
        bundle.get("shared_image_id") != verified["image_id"]
        or bundle.get("stable_projection") != verified["projection"]
        or bundle.get("stable_projection_sha256") != STABLE_PROJECTION_SHA256
        or bundle.get("report_sha256") != verified["report_sha256"]
        or bundle.get("manifest_sha256") != verified["manifest_sha256"]
        or bundle.get("claim_boundary")
        != {
            "bitemporal_structure_before_restart": True,
            "bitemporal_durability": False,
            "memory_quality_measured": False,
            "native_scoped_purge": False,
            "active_inactive_paging_demonstrated": False,
        }
    ):
        raise EvidenceError("Palimpsest evidence receipt drifted")
    return bundle


def seal(root: Path) -> dict[str, Any]:
    image_inspect = subprocess.run(
        ["docker", "image", "inspect", IMAGE_ID], capture_output=True, check=True
    ).stdout
    paths = {
        **CODE_PATHS,
        "experiment.yaml": DEFAULT_EXPERIMENT,
        "manifest.json": root / "manifest.json",
        "report.json": root / "report.json",
        "upstream-suite.txt": root / "upstream-suite.txt",
        **{
            f"repeat-{repeat}/{name}": root / f"repeat-{repeat}/{name}"
            for repeat in (1, 2)
            for name in (
                "prepare.json",
                "verify-restart.json",
                "purge-probe.json",
                "contract.json",
                "palimpsest.db",
            )
        },
    }
    files = {name: path.read_bytes() for name, path in paths.items()}
    files["image-inspect.json"] = image_inspect
    verified = validate_files(files)
    captures = {name: _capture(path) for name, path in paths.items()}
    captures["image-inspect.json"] = _capture_bytes(image_inspect)
    return {
        "schema_version": 1,
        "evidence_kind": "native-negative-reproduction",
        "source_id": "palimpsest-bitemporal-memory",
        "source_revisions": {
            "https://github.com/joe51111jwd/palimpsest": EXPECTED_SOURCE["revision"]
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
            "bitemporal_structure_before_restart": True,
            "bitemporal_durability": False,
            "memory_quality_measured": False,
            "native_scoped_purge": False,
            "active_inactive_paging_demonstrated": False,
        },
        "files": captures,
    }


def _write_no_replace(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise EvidenceError(f"short write: {path}")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if args.validate_only:
        bundle = validate_evidence(args.output.resolve())
    else:
        bundle = seal(args.root.resolve())
        _write_no_replace(args.output.resolve(), _canonical(bundle) + b"\n")
        bundle = validate_evidence(args.output.resolve())
    print(f"Palimpsest bitemporal evidence PASS: {bundle['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
