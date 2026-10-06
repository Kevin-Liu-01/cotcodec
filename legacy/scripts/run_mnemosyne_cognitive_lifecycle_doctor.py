#!/usr/bin/env python3
"""Seal two contained Mnemosyne Cognitive lifecycle falsifier repetitions."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validate_mnemosyne_cognitive_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    EXPECTED_STATUS,
    validate_experiment_contract,
)

DEFAULT_IMAGE = "cotcodec-mnemosyne-cognitive:5506aae-lifecycle-v2"
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data/results/mnemosyne-cognitive/2026-08-16-local-docker-v1"
)
DOCKERFILE = PROJECT_ROOT / "infra/memory-baselines/mnemosyne-cognitive/Dockerfile"
DOCTOR = PROJECT_ROOT / "infra/memory-baselines/mnemosyne-cognitive/doctor.mjs"


class MnemosyneCognitiveRunnerError(RuntimeError):
    """Raised when source, containment, or lifecycle evidence drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_path(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise MnemosyneCognitiveRunnerError(f"expected regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


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
                raise MnemosyneCognitiveRunnerError(f"short write: {path}")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _run(
    argv: list[str],
    *,
    timeout: int = 900,
    check: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        argv,
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    if check and completed.returncode != 0:
        raise MnemosyneCognitiveRunnerError(
            f"command failed ({completed.returncode}): {argv!r}\n"
            f"stdout={completed.stdout.decode(errors='replace')[-4000:]}\n"
            f"stderr={completed.stderr.decode(errors='replace')[-4000:]}"
        )
    return completed


def _strict_object(data: bytes, label: str) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise MnemosyneCognitiveRunnerError(
            f"{label} contains non-finite value: {value}"
        )

    try:
        payload = json.loads(data, parse_constant=reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MnemosyneCognitiveRunnerError(f"{label} is not strict JSON") from exc
    if not isinstance(payload, dict):
        raise MnemosyneCognitiveRunnerError(f"{label} must be a JSON object")
    return payload


def _source_contract(source_root: Path, experiment: dict[str, Any]) -> dict[str, Any]:
    source = experiment["source"]
    if source_root.is_symlink() or not source_root.is_dir():
        raise MnemosyneCognitiveRunnerError("source root is invalid")
    head = _run(["git", "-C", str(source_root), "rev-parse", "HEAD"]).stdout.decode().strip()
    tree = _run(
        ["git", "-C", str(source_root), "rev-parse", "HEAD^{tree}"]
    ).stdout.decode().strip()
    status = _run(
        [
            "git",
            "-C",
            str(source_root),
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ]
    ).stdout
    if head != source["revision"] or tree != source["tree"] or status:
        raise MnemosyneCognitiveRunnerError("source checkout drifted")
    archive = _run(
        ["git", "-C", str(source_root), "archive", "--format=tar", head]
    ).stdout
    if (
        _sha(archive) != source["git_archive_tar_sha256"]
        or _sha_path(source_root / "LICENSE") != source["license_sha256"]
        or _sha_path(source_root / "package-lock.json")
        != source["dependency_lock_sha256"]
    ):
        raise MnemosyneCognitiveRunnerError("source bytes drifted")
    return {
        "git_sha": head,
        "git_tree": tree,
        "archive": archive,
        "archive_sha256": _sha(archive),
        "archive_bytes": len(archive),
        "license_sha256": source["license_sha256"],
        "package_lock_sha256": source["dependency_lock_sha256"],
    }


def _inspect_image(image: str) -> tuple[dict[str, Any], bytes]:
    raw = _run(["docker", "image", "inspect", image]).stdout
    try:
        rows = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise MnemosyneCognitiveRunnerError("image inspect is not JSON") from exc
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise MnemosyneCognitiveRunnerError("image inspect roster drifted")
    return rows[0], raw


def _image_contract(
    image: str, qdrant_image: str, experiment: dict[str, Any]
) -> tuple[dict[str, Any], bytes, bytes]:
    inspect, raw = _inspect_image(image)
    config = inspect.get("Config") or {}
    labels = config.get("Labels") or {}
    source = experiment["source"]
    expected_labels = {
        "org.opencontainers.image.revision": source["revision"],
        "org.opencontainers.image.licenses": source["license"],
        "org.cotcodec.discovery-only": "true",
        "org.cotcodec.source-tree": source["tree"],
        "org.cotcodec.source-archive-sha256": source["git_archive_tar_sha256"],
        "org.cotcodec.doctor-sha256": _sha_path(DOCTOR),
    }
    if any(labels.get(key) != value for key, value in expected_labels.items()):
        raise MnemosyneCognitiveRunnerError("doctor image labels drifted")
    image_id = inspect.get("Id")
    if (
        not isinstance(image_id, str)
        or not image_id.startswith("sha256:")
        or inspect.get("Architecture") != "arm64"
        or inspect.get("Os") != "linux"
        or config.get("User") != "65534:65534"
    ):
        raise MnemosyneCognitiveRunnerError("doctor image runtime drifted")

    qdrant, qdrant_raw = _inspect_image(qdrant_image)
    if (
        qdrant.get("Id")
        != "sha256:affb67e1d6f2f93d7d20b90d238a7d4b974d36351c162e73bda794e4b2e03483"
        or qdrant.get("Architecture") != "arm64"
        or qdrant.get("Os") != "linux"
        or (qdrant.get("Config") or {}).get("User") != "1000:1000"
    ):
        raise MnemosyneCognitiveRunnerError("Qdrant image runtime drifted")
    return (
        {
            "image_id": image_id,
            "architecture": inspect["Architecture"],
            "os": inspect["Os"],
            "labels": expected_labels,
            "inspect_sha256": _sha(raw),
            "qdrant_image_id": qdrant["Id"],
            "qdrant_inspect_sha256": _sha(qdrant_raw),
        },
        raw,
        qdrant_raw,
    )


def _qdrant_argv(*, network: str, volume: str, name: str, image: str) -> list[str]:
    return [
        "docker",
        "run",
        "-d",
        "--name",
        name,
        "--pull=never",
        "--platform",
        "linux/arm64",
        "--network",
        network,
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        "256",
        "--memory",
        "1g",
        "--cpus",
        "1",
        "--env",
        "QDRANT__TELEMETRY_DISABLED=true",
        "--tmpfs",
        "/qdrant/snapshots:rw,noexec,nosuid,nodev,size=64m,uid=1000,gid=1000,mode=0700",
        "--mount",
        f"type=volume,source={volume},target=/qdrant/storage",
        image,
    ]


def _doctor_argv(
    *, image_id: str, network: str, qdrant_name: str, collection: str, phase: str
) -> list[str]:
    return [
        "docker",
        "run",
        "--rm",
        "--pull=never",
        "--platform",
        "linux/arm64",
        "--network",
        network,
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        "256",
        "--memory",
        "1g",
        "--cpus",
        "1",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=64m",
        "--env",
        f"COTCODEC_QDRANT_URL=http://{qdrant_name}:6333",
        "--env",
        f"COTCODEC_COLLECTION={collection}",
        image_id,
        "--phase",
        phase,
    ]


def _wait_qdrant(name: str) -> None:
    for _ in range(50):
        state = _run(
            ["docker", "inspect", name, "--format", "{{.State.Status}}"],
            timeout=10,
            check=False,
        ).stdout.strip()
        logs = _run(["docker", "logs", name], timeout=10, check=False)
        combined = logs.stdout + logs.stderr
        if state == b"running" and b"Qdrant HTTP listening on 6333" in combined:
            return
        if state == b"exited":
            break
        time.sleep(0.1)
    raise MnemosyneCognitiveRunnerError(f"Qdrant did not become ready: {name}")


def _strict_report(data: bytes, phase: str) -> dict[str, Any]:
    report = _strict_object(data, f"{phase} report")
    checks = report.get("projection", {}).get("checks", {})
    if (
        report.get("schema_version") != 1
        or report.get("source_revision")
        != "5506aae7cec9ada5523099fd5ab858a4eee593b6"
        or report.get("phase") != phase
        or report.get("status") != EXPECTED_STATUS
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("h100_actor_admission") is not False
        or report.get("provider_calls") != 0
        or report.get("model_backend_calls") != 0
        or not isinstance(checks, dict)
        or not checks
        or not all(value is True for value in checks.values())
    ):
        raise MnemosyneCognitiveRunnerError(f"{phase} report semantics drifted")
    projection = report["projection"]
    if report.get("projection_sha256") != _sha(
        json.dumps(projection, separators=(",", ":"), sort_keys=True).encode()
    ):
        raise MnemosyneCognitiveRunnerError(f"{phase} projection digest drifted")
    return report


def _upstream_test_argv(image_id: str) -> list[str]:
    return [
        "docker",
        "run",
        "--rm",
        "--pull=never",
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
        "256",
        "--memory",
        "1g",
        "--cpus",
        "1",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=64m",
        "--entrypoint",
        "/opt/mnemosyne/source/node_modules/.bin/vitest",
        image_id,
        "run",
        "--reporter=json",
    ]


def _cleanup(name: str, volume: str, network: str) -> None:
    _run(["docker", "rm", "-f", name], timeout=60, check=False)
    _run(["docker", "volume", "rm", volume], timeout=60, check=False)
    _run(["docker", "network", "rm", network], timeout=60, check=False)


def run(*, source_root: Path, image: str, output: Path) -> dict[str, Any]:
    experiment = validate_experiment_contract()
    output.mkdir(parents=True, exist_ok=False)
    source = _source_contract(source_root.resolve(), experiment)
    qdrant_image = experiment["runtime"]["qdrant_image"]
    image_contract, inspect_raw, qdrant_inspect_raw = _image_contract(
        image, qdrant_image, experiment
    )
    _write_once(output / "experiment.yaml", DEFAULT_EXPERIMENT.read_bytes())
    _write_once(output / "Dockerfile", DOCKERFILE.read_bytes())
    _write_once(output / "doctor.mjs", DOCTOR.read_bytes())
    _write_once(output / "source.tar", source.pop("archive"))
    _write_once(output / "source-receipt.json", _json_bytes(source))
    _write_once(output / "image-inspect.json", inspect_raw)
    _write_once(output / "qdrant-image-inspect.json", qdrant_inspect_raw)

    upstream = _run(_upstream_test_argv(image_contract["image_id"]), timeout=300)
    upstream_report = _strict_object(upstream.stdout, "upstream Vitest report")
    if (
        not isinstance(upstream_report.get("testResults"), list)
        or len(upstream_report["testResults"]) != 4
        or upstream_report.get("numTotalTests") != 62
        or upstream_report.get("numPassedTests") != 62
        or upstream_report.get("success") is not True
    ):
        raise MnemosyneCognitiveRunnerError("upstream test result drifted")
    _write_once(output / "upstream-tests.json", _json_bytes(upstream_report))

    reports: list[dict[str, dict[str, Any]]] = []
    phase_receipts: list[dict[str, Any]] = []
    for repeat in (1, 2):
        network = f"cotcodec-mnemosyne-cognitive-r{repeat}"
        volume = f"cotcodec-mnemosyne-cognitive-r{repeat}"
        qdrant_name = f"cotcodec-mnemosyne-cognitive-qdrant-r{repeat}"
        collection = f"cotcodec_mnemosyne_cognitive_r{repeat}"
        _cleanup(qdrant_name, volume, network)
        _run(["docker", "network", "create", "--internal", network])
        _run(["docker", "volume", "create", volume])
        repeat_reports: dict[str, dict[str, Any]] = {}
        try:
            first_qdrant = _qdrant_argv(
                network=network,
                volume=volume,
                name=qdrant_name,
                image=qdrant_image,
            )
            _run(first_qdrant)
            _wait_qdrant(qdrant_name)
            initial_argv = _doctor_argv(
                image_id=image_contract["image_id"],
                network=network,
                qdrant_name=qdrant_name,
                collection=collection,
                phase="initial",
            )
            initial = _run(initial_argv, timeout=300)
            initial_report = _strict_report(initial.stdout, "initial")
            _write_once(output / f"repeat-{repeat}-initial.json", _json_bytes(initial_report))
            _write_once(
                output / f"repeat-{repeat}-initial-qdrant.log",
                _run(["docker", "logs", qdrant_name]).stdout,
            )
            _run(["docker", "stop", qdrant_name], timeout=60)
            _run(["docker", "rm", qdrant_name], timeout=60)

            second_qdrant = _qdrant_argv(
                network=network,
                volume=volume,
                name=qdrant_name,
                image=qdrant_image,
            )
            _run(second_qdrant)
            _wait_qdrant(qdrant_name)
            restart_argv = _doctor_argv(
                image_id=image_contract["image_id"],
                network=network,
                qdrant_name=qdrant_name,
                collection=collection,
                phase="restart",
            )
            restart = _run(restart_argv, timeout=300)
            restart_report = _strict_report(restart.stdout, "restart")
            _write_once(output / f"repeat-{repeat}-restart.json", _json_bytes(restart_report))
            _write_once(
                output / f"repeat-{repeat}-restart-qdrant.log",
                _run(["docker", "logs", qdrant_name]).stdout,
            )
            repeat_reports = {"initial": initial_report, "restart": restart_report}
            phase_receipts.extend(
                [
                    {
                        "repeat": repeat,
                        "phase": "initial",
                        "doctor_argv": initial_argv,
                        "qdrant_argv": first_qdrant,
                        "report_sha256": _sha_path(output / f"repeat-{repeat}-initial.json"),
                    },
                    {
                        "repeat": repeat,
                        "phase": "restart",
                        "doctor_argv": restart_argv,
                        "qdrant_argv": second_qdrant,
                        "report_sha256": _sha_path(output / f"repeat-{repeat}-restart.json"),
                    },
                ]
            )
        finally:
            _cleanup(qdrant_name, volume, network)
        reports.append(repeat_reports)

    if reports[0] != reports[1]:
        raise MnemosyneCognitiveRunnerError("clean-state lifecycle repetitions diverged")
    initial_projection = reports[0]["initial"]["projection"]
    restart_projection = reports[0]["restart"]["projection"]
    summary = {
        "schema_version": 1,
        "status": EXPECTED_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "h100_actor_admission": "forbidden-for-this-revision",
        "source": source,
        "image": image_contract,
        "run_count": 2,
        "upstream_tests": {"suites": 4, "tests": 62, "passed": True},
        "phase_receipts": phase_receipts,
        "initial_projection_sha256": reports[0]["initial"]["projection_sha256"],
        "restart_projection_sha256": reports[0]["restart"]["projection_sha256"],
        "findings": {
            "dry_run_mutates_state": initial_projection["checks"][
                "dry_run_mutated_stale_priority"
            ],
            "repeated_consolidation_non_idempotent": initial_projection["checks"][
                "repeated_consolidation_non_idempotent"
            ],
            "demotion_remains_in_serving_search": initial_projection["checks"][
                "demoted_memory_remains_in_serving_search"
            ],
            "forget_retains_plaintext": initial_projection["checks"][
                "forgotten_point_physically_resident"
            ],
            "scoped_purge_absent": initial_projection["checks"]["no_native_scoped_purge"],
            "tombstones_and_plaintext_persist_after_restart": restart_projection[
                "checks"
            ]["forgotten_plaintext_persists"],
        },
        "claim_boundary": {
            "active_inactive_quality_evaluated": False,
            "graph_quality_evaluated": False,
            "h100_actor_admission": "forbidden-for-this-revision",
        },
    }
    _write_once(output / "report.json", _json_bytes(summary))
    files = {
        path.relative_to(output).as_posix(): _sha_path(path)
        for path in sorted(output.rglob("*"))
        if path.is_file() and path.name != "manifest.json"
    }
    _write_once(
        output / "manifest.json",
        _json_bytes(
            {
                "schema_version": 1,
                "status": EXPECTED_STATUS,
                "files": files,
                "file_count": len(files),
            }
        ),
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    summary = run(
        source_root=args.source_root,
        image=args.image,
        output=args.output,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
