#!/usr/bin/env python3
"""Build and run the pinned Mnemon + dsh-mnemon admission cell twice."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validate_mnemon_active_space_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    EXPECTED_SOURCES,
    EXPECTED_STATUS,
    validate_experiment_contract,
)

DEFAULT_IMAGE = "cotcodec-mnemon-active-space:88d2981-1889c68-arm64-v1"
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "data/results/mnemon-active-space/2026-08-16-local-docker-v1"
)
DOCKERFILE = PROJECT_ROOT / "infra/memory-baselines/mnemon/Dockerfile"
DOCTOR = PROJECT_ROOT / "infra/memory-baselines/mnemon/doctor.mjs"
SOURCE_PATHS = {
    "mnemon/LICENSE": "/opt/sources/mnemon/LICENSE",
    "mnemon/go.mod": "/opt/sources/mnemon/go.mod",
    "mnemon/go.sum": "/opt/sources/mnemon/go.sum",
    "mnemon/store.go": "/opt/sources/mnemon/store.go",
    "mnemon/forget.go": "/opt/sources/mnemon/forget.go",
    "mnemon/node.go": "/opt/sources/mnemon/node.go",
    "dsh-mnemon/LICENSE": "/opt/sources/dsh-mnemon/LICENSE",
    "dsh-mnemon/package.json": "/opt/sources/dsh-mnemon/package.json",
    "dsh-mnemon/pnpm-lock.yaml": "/opt/sources/dsh-mnemon/pnpm-lock.yaml",
    "dsh-mnemon/memory-bodies.ts": "/opt/sources/dsh-mnemon/memory-bodies.ts",
    "dsh-mnemon/service.ts": "/opt/sources/dsh-mnemon/service.ts",
    "dsh-mnemon/runner.ts": "/opt/sources/dsh-mnemon/runner.ts",
}


class MnemonRunnerError(RuntimeError):
    """Raised when Mnemon admission evidence violates its contract."""


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode()


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _write_once(path: Path, data: bytes) -> None:
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
                raise MnemonRunnerError(f"short write: {path}")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _run(argv: list[str], *, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(argv, capture_output=True, check=False)
    if check and completed.returncode != 0:
        stdout = completed.stdout.decode("utf-8", errors="replace")[-10000:]
        stderr = completed.stderr.decode("utf-8", errors="replace")[-5000:]
        raise MnemonRunnerError(
            f"command failed ({completed.returncode}): {argv!r}\n{stdout}\n{stderr}"
        )
    return completed


def _git_identity(path: Path, expected: dict[str, str]) -> None:
    if not path.is_dir():
        raise MnemonRunnerError(f"source checkout missing: {path}")
    status = _run(["git", "-C", str(path), "status", "--porcelain"]).stdout
    revision = _run(["git", "-C", str(path), "rev-parse", "HEAD"]).stdout.strip()
    tree = _run(["git", "-C", str(path), "rev-parse", "HEAD^{tree}"]).stdout.strip()
    archive = _run(["git", "-C", str(path), "archive", "--format=tar", "HEAD"]).stdout
    if status or revision.decode() != expected["revision"] or tree.decode() != expected["tree"]:
        raise MnemonRunnerError(f"source checkout identity drifted: {path}")
    if _sha_bytes(archive) != expected["git_archive_tar_sha256"]:
        raise MnemonRunnerError(f"source archive drifted: {path}")


def build_image(image: str, mnemon_source: Path, plugin_source: Path) -> None:
    _git_identity(mnemon_source, EXPECTED_SOURCES["mnemon"])
    _git_identity(plugin_source, EXPECTED_SOURCES["dsh_mnemon"])
    source = EXPECTED_SOURCES
    argv = [
        "docker",
        "build",
        "--platform",
        "linux/arm64",
        "--build-arg",
        f"MNEMON_REVISION={source['mnemon']['revision']}",
        "--build-arg",
        f"MNEMON_TREE={source['mnemon']['tree']}",
        "--build-arg",
        f"MNEMON_ARCHIVE_SHA256={source['mnemon']['git_archive_tar_sha256']}",
        "--build-arg",
        f"DSH_MNEMON_REVISION={source['dsh_mnemon']['revision']}",
        "--build-arg",
        f"DSH_MNEMON_TREE={source['dsh_mnemon']['tree']}",
        "--build-arg",
        f"DSH_MNEMON_ARCHIVE_SHA256={source['dsh_mnemon']['git_archive_tar_sha256']}",
        "--build-arg",
        f"DOCTOR_SHA256={_sha_path(DOCTOR)}",
        "-f",
        str(DOCKERFILE),
        "-t",
        image,
        str(PROJECT_ROOT),
    ]
    _run(argv)


def _docker_options() -> list[str]:
    return [
        "docker",
        "run",
        "--rm",
        "--pull",
        "never",
        "--platform",
        "linux/arm64",
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        "1024",
        "--memory",
        "4g",
        "--cpus",
        "4",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=2g,uid=65532,gid=65532,mode=0700",
        "--user",
        "65532:65532",
        "-e",
        "HOME=/tmp/mnemon-home",
    ]


def _image_contract(image: str, output: Path) -> dict[str, Any]:
    completed = _run(["docker", "image", "inspect", image])
    _write_once(output / "image-inspect.json", completed.stdout)
    values = json.loads(completed.stdout)
    if not isinstance(values, list) or len(values) != 1 or not isinstance(values[0], dict):
        raise MnemonRunnerError("docker inspect returned an unexpected roster")
    inspect = values[0]
    labels = (inspect.get("Config") or {}).get("Labels") or {}
    source = EXPECTED_SOURCES
    expected_labels = {
        "org.opencontainers.image.revision": source["mnemon"]["revision"],
        "org.opencontainers.image.licenses": "Apache-2.0 AND MIT",
        "org.cotcodec.mnemon-tree": source["mnemon"]["tree"],
        "org.cotcodec.mnemon-archive-sha256": source["mnemon"]["git_archive_tar_sha256"],
        "org.cotcodec.dsh-mnemon-revision": source["dsh_mnemon"]["revision"],
        "org.cotcodec.dsh-mnemon-tree": source["dsh_mnemon"]["tree"],
        "org.cotcodec.dsh-mnemon-archive-sha256": source["dsh_mnemon"]["git_archive_tar_sha256"],
        "org.cotcodec.doctor-sha256": _sha_path(DOCTOR),
        "org.cotcodec.discovery-only": "true",
    }
    if any(labels.get(key) != value for key, value in expected_labels.items()):
        raise MnemonRunnerError("Mnemon image labels drifted")
    config = inspect.get("Config") or {}
    if (
        inspect.get("Architecture") != "arm64"
        or inspect.get("Os") != "linux"
        or config.get("User") != "65532:65532"
        or config.get("Entrypoint") != ["node", "/opt/cotcodec/doctor.mjs"]
    ):
        raise MnemonRunnerError("Mnemon image runtime contract drifted")
    return {
        "image_id": inspect.get("Id"),
        "architecture": inspect.get("Architecture"),
        "os": inspect.get("Os"),
        "inspect_sha256": _sha_bytes(completed.stdout),
        "labels": expected_labels,
    }


def _export_sources(image_id: str, output: Path) -> dict[str, str]:
    digests: dict[str, str] = {}
    for name, source_path in SOURCE_PATHS.items():
        completed = _run(
            [*_docker_options(), "--entrypoint", "/bin/cat", image_id, source_path]
        )
        path = output / "source" / name
        _write_once(path, completed.stdout)
        digests[name] = _sha_path(path)
    return digests


def _strict_report(raw: bytes, repeat: int) -> dict[str, Any]:
    marker = b"COTCODEC_MNEMON_REPORT="
    rows = [line[len(marker) :] for line in raw.splitlines() if line.startswith(marker)]
    if len(rows) != 1:
        raise MnemonRunnerError(f"repeat {repeat} emitted {len(rows)} report markers")
    report = json.loads(rows[0])
    expected_checks = {
        "core_named_stores_use_distinct_databases",
        "plugin_active_set_limits_default_recall",
        "explicit_inactive_read_is_rejected",
        "targeted_write_autoactivates_space",
        "activation_registry_survives_restart",
        "core_soft_forget_hides_but_preserves_row",
        "plugin_space_delete_removes_store_directory",
        "last_native_store_delete_is_rejected",
    }
    if (
        not isinstance(report, dict)
        or report.get("schema_version") != 1
        or report.get("system_id") != "mnemon-dsh-static-active-space-admission-v1"
        or report.get("status") != EXPECTED_STATUS
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("h100_actor_admission") is not True
        or set(report.get("checks", {})) != expected_checks
        or any(report["checks"].get(field) is not True for field in expected_checks)
    ):
        raise MnemonRunnerError(f"repeat {repeat} admission contract drifted")
    observations = report.get("observations")
    if (
        not isinstance(observations, dict)
        or observations.get("soft_delete_preserved_plaintext") is not True
        or observations.get("learned_promotion_or_demotion") is not False
        or observations.get("access_control") is not False
        or observations.get("physical_item_erasure_proven") is not False
    ):
        raise MnemonRunnerError(f"repeat {repeat} claim boundary drifted")
    return report


def _doctor_repeat(image_id: str, repeat: int, output: Path) -> dict[str, Any]:
    completed = _run([*_docker_options(), image_id], check=False)
    raw = completed.stdout + completed.stderr
    _write_once(output / f"repeat-{repeat}.txt", raw)
    if completed.returncode != 0:
        raise MnemonRunnerError(
            f"repeat {repeat} failed ({completed.returncode}): "
            + raw.decode("utf-8", errors="replace")[-5000:]
        )
    report = _strict_report(raw, repeat)
    _write_once(output / f"repeat-{repeat}.json", _json_bytes(report))
    return report


def run(image: str, output: Path) -> dict[str, Any]:
    validate_experiment_contract()
    output.mkdir(parents=True, exist_ok=False)
    _write_once(output / "experiment.yaml", DEFAULT_EXPERIMENT.read_bytes())
    _write_once(output / "Dockerfile", DOCKERFILE.read_bytes())
    _write_once(output / "doctor.mjs", DOCTOR.read_bytes())
    image_contract = _image_contract(image, output)
    image_id = image_contract["image_id"]
    if not isinstance(image_id, str) or not image_id.startswith("sha256:"):
        raise MnemonRunnerError("Mnemon image lacks an immutable local ID")
    source_digests = _export_sources(image_id, output)
    repeats = [_doctor_repeat(image_id, repeat, output) for repeat in (1, 2)]
    if repeats[0] != repeats[1]:
        raise MnemonRunnerError("Mnemon clean-state repeats diverged")
    report = {
        "schema_version": 1,
        "status": EXPECTED_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "h100_actor_admission": True,
        "experiment_sha256": _sha_path(DEFAULT_EXPERIMENT),
        "dockerfile_sha256": _sha_path(DOCKERFILE),
        "doctor_sha256": _sha_path(DOCTOR),
        "image": image_contract,
        "source_file_sha256": source_digests,
        "run_count": 2,
        "stable_projection_sha256": _sha_bytes(_canonical(repeats[0])),
        "stable_projection": repeats[0],
    }
    _write_once(output / "report.json", _json_bytes(report))
    files = {
        str(path.relative_to(output)): {
            "sha256": _sha_path(path),
            "bytes": path.stat().st_size,
        }
        for path in sorted(output.rglob("*"))
        if path.is_file()
    }
    manifest = {
        "schema_version": 1,
        "status": EXPECTED_STATUS,
        "files": files,
    }
    _write_once(output / "manifest.json", _json_bytes(manifest))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--mnemon-source", type=Path)
    parser.add_argument("--dsh-mnemon-source", type=Path)
    args = parser.parse_args()
    if args.build:
        if args.mnemon_source is None or args.dsh_mnemon_source is None:
            parser.error("--build requires --mnemon-source and --dsh-mnemon-source")
        build_image(args.image, args.mnemon_source, args.dsh_mnemon_source)
    report = run(args.image, args.output)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
