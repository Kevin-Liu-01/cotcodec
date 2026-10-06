#!/usr/bin/env python3
"""Seal and validate the two-repeat LightMem2 context-paging negative."""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_lightmem2_context_paging_doctor import _projection  # noqa: E402
from scripts.validate_lightmem2_context_paging_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    EXPECTED_SOURCE,
    EXPECTED_STATUS,
)

DEFAULT_ROOT = (
    PROJECT_ROOT
    / "data/results/lightmem2-context-paging/2026-08-16-local-docker-v1"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "research/evidence/memory/lightmem2-context-paging-negative-v1.json"
)
IMAGE_ID = "sha256:0ecd89daaab43e1e351de5a5c64a437f4b315e65109c45787bdd646dd5afce49"
STABLE_PROJECTION_SHA256 = (
    "bb2a508f6053a0ae0a17dc3e3120dc828724d3234dd4bdecb57f4af8d0d6ada1"
)
RUNTIME_LANE = "local-arm64-docker-network-none"
PHASES = ("prepare", "verify-restart", "purge-probe")
SOURCE_NAMES = (
    "archive-recovery-index.ts",
    "history-apply.ts",
    "mcp-index.ts",
    "package.json",
    "pnpm-lock.yaml",
)
CODE_PATHS = {
    "Dockerfile": PROJECT_ROOT / "infra/memory-baselines/lightmem2/Dockerfile",
    "doctor.ts": PROJECT_ROOT / "infra/memory-baselines/lightmem2/doctor.ts",
    "run_lightmem2_context_paging_doctor.py": PROJECT_ROOT
    / "scripts/run_lightmem2_context_paging_doctor.py",
    "validate_lightmem2_context_paging_experiment.py": PROJECT_ROOT
    / "scripts/validate_lightmem2_context_paging_experiment.py",
}
EXPECTED_FILE_ROSTER = {
    *CODE_PATHS,
    "experiment.yaml",
    "image-inspect.json",
    "manifest.json",
    "report.json",
    "upstream-relevant-suite.txt",
    *(f"source/{name}" for name in SOURCE_NAMES),
    *(f"repeat-{repeat}/{phase}.json" for repeat in (1, 2) for phase in PHASES),
    *(f"repeat-{repeat}/contract.json" for repeat in (1, 2)),
    *(f"repeat-{repeat}/state.tar" for repeat in (1, 2)),
}


class EvidenceError(ValueError):
    """Raised when retained LightMem2 evidence is incomplete or drifts."""


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
        raise EvidenceError("LightMem2 evidence file roster drifted")
    decoded: dict[str, bytes] = {}
    for name, receipt in receipts.items():
        if not isinstance(receipt, dict):
            raise EvidenceError(f"invalid LightMem2 receipt for {name}")
        try:
            data = base64.b64decode(receipt.get("content_base64", ""), validate=True)
        except (TypeError, ValueError) as exc:
            raise EvidenceError(f"invalid base64 for {name}") from exc
        if receipt.get("bytes") != len(data) or receipt.get("sha256") != _sha(data):
            raise EvidenceError(f"embedded LightMem2 receipt drifted: {name}")
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
        raise EvidenceError(f"LightMem2 repeat {repeat} {phase} identity drifted")


def _tar_regular_files(data: bytes, owner: str) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
            for member in archive.getmembers():
                path = PurePosixPath(member.name)
                parts = tuple(part for part in path.parts if part not in ("", "."))
                if path.is_absolute() or ".." in parts or not parts:
                    if member.isdir() and not parts:
                        continue
                    raise EvidenceError(f"unsafe {owner} member: {member.name}")
                normalized = "/".join(parts)
                if member.isdir():
                    continue
                if not member.isfile() or member.issym() or member.islnk():
                    raise EvidenceError(f"non-regular {owner} member: {member.name}")
                if normalized in files:
                    raise EvidenceError(f"duplicate {owner} member: {normalized}")
                source = archive.extractfile(member)
                if source is None:
                    raise EvidenceError(f"unreadable {owner} member: {normalized}")
                files[normalized] = source.read()
    except (tarfile.TarError, OSError) as exc:
        raise EvidenceError(f"cannot parse {owner}") from exc
    return files


def _validate_source_semantics(files: dict[str, bytes]) -> None:
    archive = files["source/archive-recovery-index.ts"].decode("utf-8")
    mcp = files["source/mcp-index.ts"].decode("utf-8")
    eviction = files["source/history-apply.ts"].decode("utf-8")
    required_archive = (
        "export async function resolveArchivePathFromLookup",
        "export async function resolveArchivePathAcrossSessions",
        "resolveArchivePathFromLookup(dataKey, stateDir, entry.name)",
        "const timestamp = Date.now();",
        'await writeFile(archivePath, payload, "utf8")',
    )
    if any(marker not in archive for marker in required_archive):
        raise EvidenceError("LightMem2 archive source semantics drifted")
    if (
        "export async function resolveMemoryFaultRecover" not in mcp
        or "resolveArchivePathAcrossSessions(dataKey, stateDir)" not in mcp
    ):
        raise EvidenceError("LightMem2 MCP recovery semantics drifted")
    if (
        "await archiveContent" not in eviction
        or 'params.replacementMode === "pointer_stub"' not in eviction
        or eviction.index("await archiveContent")
        > eviction.index('params.replacementMode === "pointer_stub"')
    ):
        raise EvidenceError("LightMem2 archive-before-stub semantics drifted")


def _validate_state_tar(data: bytes, contract: dict[str, Any], repeat: int) -> None:
    members = _tar_regular_files(data, f"repeat-{repeat}/state.tar")
    required = {
        "contract.json",
        "tokenpilot/tool-result-archives/session-a/key-lookup.json",
        "tokenpilot/tool-result-archives/session-b/key-lookup.json",
    }
    if not required.issubset(members):
        raise EvidenceError(f"LightMem2 repeat {repeat} state roster drifted")
    joined = b"\n".join(
        value for name, value in members.items() if name.startswith("tokenpilot/")
    )
    for field in ("a_canary", "b_canary", "collision_second"):
        value = contract.get(field)
        if not isinstance(value, str) or value.encode() not in joined:
            raise EvidenceError(f"LightMem2 repeat {repeat} lost plaintext {field}")
    first = contract.get("collision_first")
    if not isinstance(first, str) or first.encode() in joined:
        raise EvidenceError(f"LightMem2 repeat {repeat} collision overwrite drifted")


def validate_files(files: dict[str, bytes]) -> dict[str, Any]:
    if set(files) != EXPECTED_FILE_ROSTER:
        raise EvidenceError("LightMem2 evidence file roster drifted")
    experiment = yaml.safe_load(files["experiment.yaml"])
    if (
        not isinstance(experiment, dict)
        or experiment.get("name") != "stage3-lightmem2-context-paging-doctor"
        or experiment.get("source") != EXPECTED_SOURCE
        or experiment.get("expected_falsification", {}).get("status") != EXPECTED_STATUS
        or experiment.get("admission", {}).get("h100_actor")
        != "forbidden-for-this-revision"
    ):
        raise EvidenceError("embedded LightMem2 experiment drifted")
    _validate_source_semantics(files)

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
        or report.get("doctor_sha256") != _sha(files["doctor.ts"])
        or report.get("stable_projection_sha256") != STABLE_PROJECTION_SHA256
        or report.get("reproduced_in_two_clean_states") is not True
    ):
        raise EvidenceError("LightMem2 report contract drifted")
    if manifest != {
        "artifact_count": 10,
        "image_id": IMAGE_ID,
        "report": "report.json",
        "report_sha256": _sha(files["report.json"]),
        "schema_version": 1,
        "stable_projection_sha256": STABLE_PROJECTION_SHA256,
        "status": "SEALED_DISCOVERY_NEGATIVE",
    }:
        raise EvidenceError("LightMem2 manifest contract drifted")

    suite = report.get("upstream_relevant_suite")
    suite_text = files["upstream-relevant-suite.txt"].decode(
        "utf-8", errors="replace"
    )
    if (
        not isinstance(suite, dict)
        or {key: suite.get(key) for key in ("tests", "pass", "fail", "skipped")}
        != {"tests": 49, "pass": 47, "fail": 2, "skipped": 0}
        or suite.get("exit_code") != 1
        or suite.get("output_sha256") != _sha(files["upstream-relevant-suite.txt"])
        or suite_text.count("Cannot find module '@lightmem2/kernel'") < 2
    ):
        raise EvidenceError("LightMem2 relevant-suite receipt drifted")

    source_digests = {name: _sha(files[f"source/{name}"]) for name in SOURCE_NAMES}
    if source_digests != report.get("source_file_sha256"):
        raise EvidenceError("LightMem2 source file receipt drifted")

    image_rows = json.loads(files["image-inspect.json"])
    if not isinstance(image_rows, list) or len(image_rows) != 1:
        raise EvidenceError("LightMem2 image inspection roster drifted")
    image = image_rows[0]
    labels = image.get("Config", {}).get("Labels", {})
    if (
        image.get("Id") != IMAGE_ID
        or image.get("Architecture") != "arm64"
        or image.get("Os") != "linux"
        or image.get("Config", {}).get("User") != "65532:65532"
        or image.get("Config", {}).get("Entrypoint")
        != ["node", "--import", "tsx", "/opt/cotcodec/doctor.ts"]
        or labels.get("org.cotcodec.discovery-only") != "true"
        or labels.get("org.opencontainers.image.revision") != EXPECTED_SOURCE["revision"]
        or labels.get("org.cotcodec.source-tree") != EXPECTED_SOURCE["tree"]
        or labels.get("org.cotcodec.source-archive-sha256")
        != EXPECTED_SOURCE["git_archive_tar_sha256"]
        or labels.get("org.cotcodec.doctor-sha256") != _sha(files["doctor.ts"])
        or report.get("image", {}).get("image_id") != IMAGE_ID
        or report.get("image", {}).get("inspect_sha256")
        != _sha(files["image-inspect.json"])
    ):
        raise EvidenceError("LightMem2 image provenance drifted")

    receipts = report.get("artifact_receipts")
    if not isinstance(receipts, list) or len(receipts) != 10:
        raise EvidenceError("LightMem2 artifact receipt roster drifted")
    expected_digests = {
        f"repeat-{repeat}/{name}": _sha(files[f"repeat-{repeat}/{name}"])
        for repeat in (1, 2)
        for name in (
            "prepare.json",
            "verify-restart.json",
            "purge-probe.json",
            "contract.json",
            "state.tar",
        )
    }
    observed: dict[str, str] = {}
    marker = "data/results/lightmem2-context-paging/2026-08-16-local-docker-v1/"
    for receipt in receipts:
        if not isinstance(receipt, dict) or not isinstance(receipt.get("artifact"), str):
            raise EvidenceError("LightMem2 artifact receipt is invalid")
        artifact = receipt["artifact"]
        if not artifact.startswith(marker):
            raise EvidenceError("LightMem2 artifact path drifted")
        name = artifact.removeprefix(marker)
        if name in observed or name not in expected_digests:
            raise EvidenceError("LightMem2 artifact roster drifted")
        if receipt.get("artifact_sha256") != expected_digests[name]:
            raise EvidenceError(f"LightMem2 artifact digest drifted: {name}")
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
            raise EvidenceError("LightMem2 contained argv drifted")
        observed[name] = receipt["artifact_sha256"]
    if observed != expected_digests:
        raise EvidenceError("LightMem2 artifact coverage drifted")

    projections: list[dict[str, Any]] = []
    for repeat in (1, 2):
        run: dict[str, Any] = {}
        contract = _strict_json(
            files[f"repeat-{repeat}/contract.json"],
            f"repeat-{repeat}/contract.json",
        )
        if contract.get("repeat") != repeat:
            raise EvidenceError(f"LightMem2 repeat {repeat} contract drifted")
        _validate_state_tar(files[f"repeat-{repeat}/state.tar"], contract, repeat)
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
        raise EvidenceError("LightMem2 clean-state semantic projections drifted")
    projection_bytes = (
        json.dumps(projections[0], indent=2, sort_keys=True) + "\n"
    ).encode()
    if _sha(projection_bytes) != STABLE_PROJECTION_SHA256:
        raise EvidenceError("LightMem2 stable projection digest drifted")
    return {
        "image_id": IMAGE_ID,
        "projection": projections[0],
        "report_sha256": _sha(files["report.json"]),
        "manifest_sha256": _sha(files["manifest.json"]),
    }


def validate_evidence(path: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise EvidenceError(f"expected regular LightMem2 evidence bundle: {path}")
    bundle = _strict_json(path.read_bytes(), "LightMem2 evidence bundle")
    if (
        bundle.get("schema_version") != 1
        or bundle.get("evidence_kind") != "native-negative-reproduction"
        or bundle.get("source_id") != "lightmem2"
        or bundle.get("evidence_grade") != "local-negative-reproduced"
        or bundle.get("status") != EXPECTED_STATUS
        or bundle.get("scientific_result") is not False
        or bundle.get("publication_ready") is not False
        or bundle.get("h100_admission") != "forbidden-for-this-revision"
        or bundle.get("runtime_lane") != RUNTIME_LANE
        or bundle.get("run_count") != 2
        or bundle.get("source_revisions")
        != {"https://github.com/zjunlp/LightMem2": EXPECTED_SOURCE["revision"]}
    ):
        raise EvidenceError("LightMem2 top-level evidence contract drifted")
    verified = validate_files(_decode_files(bundle.get("files")))
    expected_boundary = {
        "archive_before_pointer_stub": True,
        "strict_session_lookup_exists": True,
        "mcp_recovery_is_session_scoped": False,
        "collision_safe_archive_identity": False,
        "native_scoped_purge": False,
        "memory_quality_measured": False,
        "active_inactive_paging_demonstrated": False,
    }
    if (
        bundle.get("shared_image_id") != verified["image_id"]
        or bundle.get("stable_projection") != verified["projection"]
        or bundle.get("stable_projection_sha256") != STABLE_PROJECTION_SHA256
        or bundle.get("report_sha256") != verified["report_sha256"]
        or bundle.get("manifest_sha256") != verified["manifest_sha256"]
        or bundle.get("claim_boundary") != expected_boundary
    ):
        raise EvidenceError("LightMem2 evidence receipt drifted")
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
        "upstream-relevant-suite.txt": root / "upstream-relevant-suite.txt",
        **{f"source/{name}": root / "source" / name for name in SOURCE_NAMES},
        **{
            f"repeat-{repeat}/{name}": root / f"repeat-{repeat}/{name}"
            for repeat in (1, 2)
            for name in (
                "prepare.json",
                "verify-restart.json",
                "purge-probe.json",
                "contract.json",
                "state.tar",
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
        "source_id": "lightmem2",
        "source_revisions": {
            "https://github.com/zjunlp/LightMem2": EXPECTED_SOURCE["revision"]
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
            "archive_before_pointer_stub": True,
            "strict_session_lookup_exists": True,
            "mcp_recovery_is_session_scoped": False,
            "collision_safe_archive_identity": False,
            "native_scoped_purge": False,
            "memory_quality_measured": False,
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
    print(f"LightMem2 context-paging evidence PASS: {bundle['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
