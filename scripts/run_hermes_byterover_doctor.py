#!/usr/bin/env python3
"""Build and run the contained Hermes ByteRover offline falsifier."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validate_hermes_byterover_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    EXPECTED_STATUS,
    validate_experiment_contract,
)

DOCTOR_ROOT = PROJECT_ROOT / "infra/memory-baselines/hermes-byterover"
TARBALL = (
    PROJECT_ROOT / "raw/baselines/byterover-cli/byterover-cli-3.16.1.tgz"
)
HERMES_PROVIDER = (
    PROJECT_ROOT
    / "raw/baselines/hermes-agent/plugins/memory/byterover/__init__.py"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "data/results/hermes-byterover/2026-08-14-offline-doctor-v1"
)


class DoctorError(RuntimeError):
    """Raised when source, containment, or result identity drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_path(path: Path) -> str:
    return _sha(path.read_bytes())


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _run(
    argv: list[str], *, cwd: Path | None = None, timeout: int = 1200
) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        argv, cwd=cwd, capture_output=True, check=False, timeout=timeout
    )
    if result.returncode != 0:
        raise DoctorError(
            f"command failed ({result.returncode}): {argv!r}\n"
            f"stdout={result.stdout.decode(errors='replace')}\n"
            f"stderr={result.stderr.decode(errors='replace')}"
        )
    return result


def _write_once(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def _strict_json(data: bytes, owner: str) -> dict[str, Any]:
    try:
        value = json.loads(data)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise DoctorError(f"{owner} output is not JSON") from exc
    if not isinstance(value, dict):
        raise DoctorError(f"{owner} output is not a mapping")
    return value


def _verify_tarball(experiment: dict[str, Any]) -> dict[str, Any]:
    source = experiment["sources"]["byterover"]
    if TARBALL.is_symlink() or not TARBALL.is_file():
        raise DoctorError("ByteRover npm tarball is missing or unsafe")
    tarball = TARBALL.read_bytes()
    if _sha(tarball) != source["npm_tarball_sha256"]:
        raise DoctorError("ByteRover npm tarball SHA-256 drifted")
    actual_integrity = "sha512-" + base64.b64encode(
        hashlib.sha512(tarball).digest()
    ).decode("ascii")
    if actual_integrity != source["npm_integrity"]:
        raise DoctorError("ByteRover npm integrity drifted")
    with tarfile.open(TARBALL, mode="r:gz") as bundle:
        members = bundle.getmembers()
        if not members or len(members) > 40_000:
            raise DoctorError("ByteRover npm member count is invalid")
        if any(
            member.name.startswith("/")
            or ".." in Path(member.name).parts
            or not (member.isfile() or member.isdir() or member.issym())
            for member in members
        ):
            raise DoctorError("ByteRover npm tarball contains an unsafe member")
        package_member = bundle.getmember("package/package.json")
        package_file = bundle.extractfile(package_member)
        if package_file is None:
            raise DoctorError("ByteRover npm package.json is missing")
        package = json.load(package_file)
    if (
        not isinstance(package, dict)
        or package.get("name") != "byterover-cli"
        or package.get("version") != source["version"]
        or package.get("license") != source["license"]
        or package.get("repository") != "campfirein/byterover-cli"
    ):
        raise DoctorError("ByteRover npm metadata drifted")
    return {
        "path": TARBALL.relative_to(PROJECT_ROOT).as_posix(),
        "bytes": len(tarball),
        "sha256": _sha(tarball),
        "integrity": actual_integrity,
        "member_count": len(members),
        "package": {
            "name": package["name"],
            "version": package["version"],
            "license": package["license"],
            "repository": package["repository"],
        },
    }


def _verify_sources(experiment: dict[str, Any], checkout_root: Path) -> dict[str, Any]:
    byterover = experiment["sources"]["byterover"]
    checkout = checkout_root / "byterover-cli"
    _run(
        [
            "git",
            "clone",
            "--filter=blob:none",
            "--no-checkout",
            byterover["repository"],
            str(checkout),
        ]
    )
    _run(["git", "checkout", "--detach", byterover["revision"]], cwd=checkout)
    revision = _run(["git", "rev-parse", "HEAD"], cwd=checkout).stdout.decode().strip()
    tree = _run(["git", "rev-parse", "HEAD^{tree}"], cwd=checkout).stdout.decode().strip()
    tag_object = _run(
        ["git", "rev-parse", f"refs/tags/{byterover['tag']}"], cwd=checkout
    ).stdout.decode().strip()
    peeled_tag = _run(
        ["git", "rev-parse", f"refs/tags/{byterover['tag']}^{{}}"], cwd=checkout
    ).stdout.decode().strip()
    if (
        revision != byterover["revision"]
        or tree != byterover["tree"]
        or tag_object != byterover["tag_object"]
        or peeled_tag != revision
    ):
        raise DoctorError("ByteRover Git identity drifted")
    if _run(["git", "status", "--porcelain"], cwd=checkout).stdout.strip():
        raise DoctorError("ByteRover checkout is dirty")
    git_checks = {
        "license_sha256": _sha_path(checkout / "LICENSE"),
        "package_json_sha256": _sha_path(checkout / "package.json"),
        "package_lock_sha256": _sha_path(checkout / "package-lock.json"),
    }
    if any(git_checks[field] != byterover[field] for field in git_checks):
        raise DoctorError("ByteRover source receipt drifted")
    hermes = experiment["sources"]["hermes"]
    if HERMES_PROVIDER.is_symlink() or not HERMES_PROVIDER.is_file():
        raise DoctorError("Hermes ByteRover provider is missing or unsafe")
    if _sha_path(HERMES_PROVIDER) != hermes["provider_sha256"]:
        raise DoctorError("Hermes ByteRover provider SHA-256 drifted")
    return {
        "byterover": {
            "repository": byterover["repository"],
            "revision": revision,
            "tree": tree,
            "tag": byterover["tag"],
            "tag_object": tag_object,
            "worktree_clean": True,
            **git_checks,
            "npm": _verify_tarball(experiment),
        },
        "hermes": {
            "repository": hermes["repository"],
            "revision": hermes["revision"],
            "tree": hermes["tree"],
            "git_archive_tar_sha256": hermes["git_archive_tar_sha256"],
            "provider_path": HERMES_PROVIDER.relative_to(PROJECT_ROOT).as_posix(),
            "provider_sha256": _sha_path(HERMES_PROVIDER),
        },
        "dockerfile_sha256": _sha_path(DOCTOR_ROOT / "Dockerfile"),
        "doctor_sha256": _sha_path(DOCTOR_ROOT / "doctor.mjs"),
    }


def _build_image(experiment: dict[str, Any], image_tag: str) -> dict[str, Any]:
    runtime = experiment["runtime"]
    with tempfile.TemporaryDirectory(prefix="cotcodec-byterover-build-") as build_tmp:
        context = Path(build_tmp)
        shutil.copy2(DOCTOR_ROOT / "Dockerfile", context / "Dockerfile")
        target_tarball = (
            context / "raw/baselines/byterover-cli/byterover-cli-3.16.1.tgz"
        )
        target_provider = (
            context
            / "raw/baselines/hermes-agent/plugins/memory/byterover/__init__.py"
        )
        target_doctor = (
            context / "infra/memory-baselines/hermes-byterover/doctor.mjs"
        )
        for source_path, target_path in (
            (TARBALL, target_tarball),
            (HERMES_PROVIDER, target_provider),
            (DOCTOR_ROOT / "doctor.mjs", target_doctor),
        ):
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target_path)
        _run(
            [
                "docker",
                "build",
                "--platform",
                runtime["local_platform"],
                "--build-arg",
                f"BYTEROVER_REVISION={experiment['sources']['byterover']['revision']}",
                "--build-arg",
                "BYTEROVER_TARBALL_SHA256="
                f"{experiment['sources']['byterover']['npm_tarball_sha256']}",
                "--build-arg",
                f"HERMES_REVISION={experiment['sources']['hermes']['revision']}",
                "--tag",
                image_tag,
                str(context),
            ],
            timeout=1800,
        )
    raw = _run(["docker", "image", "inspect", image_tag]).stdout
    rows = json.loads(raw)
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise DoctorError("Docker inspect must return one image")
    inspect = rows[0]
    labels = inspect.get("Config", {}).get("Labels", {})
    if (
        inspect.get("Architecture") != "arm64"
        or inspect.get("Os") != "linux"
        or inspect.get("Config", {}).get("User")
        != runtime["user"].replace("1000:1000", "node:node")
        or labels.get("org.opencontainers.image.revision")
        != experiment["sources"]["byterover"]["revision"]
        or labels.get("org.cotcodec.byterover-tarball-sha256")
        != experiment["sources"]["byterover"]["npm_tarball_sha256"]
        or labels.get("org.cotcodec.hermes-revision")
        != experiment["sources"]["hermes"]["revision"]
    ):
        raise DoctorError("ByteRover image contract drifted")
    image_id = inspect.get("Id")
    if not isinstance(image_id, str) or not image_id.startswith("sha256:"):
        raise DoctorError("ByteRover image ID is invalid")
    return {"image_id": image_id, "inspect": inspect, "inspect_sha256": _sha(raw)}


def _initialize_volume(*, image_id: str, volume: str) -> None:
    _run(
        [
            "docker",
            "run",
            "--rm",
            "--pull=never",
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--cap-add",
            "CHOWN",
            "--security-opt",
            "no-new-privileges",
            "--user",
            "0:0",
            "-v",
            f"{volume}:/state:rw",
            "--entrypoint",
            "/bin/chown",
            image_id,
            "1000:1000",
            "/state",
        ]
    )


def _run_phase(
    *, image_id: str, volume: str, phase: str, runtime: dict[str, Any]
) -> dict[str, Any]:
    argv = [
        "docker",
        "run",
        "--rm",
        "--pull=never",
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
        runtime["memory_limit"],
        "--cpus",
        str(runtime["cpu_limit"]),
        "--user",
        runtime["user"],
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=128m",
        "-e",
        "COTCODEC_STATE_ROOT=/state",
        "-v",
        f"{volume}:/state:rw",
        image_id,
        phase,
    ]
    result = _run(argv, timeout=runtime["phase_timeout_seconds"])
    return {
        "argv": argv,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "result": _strict_json(result.stdout, f"ByteRover {phase}"),
    }


def _validate_phase(result: dict[str, Any], phase: str) -> dict[str, Any]:
    if result.get("schema_version") != 1 or result.get("phase") != phase:
        raise DoctorError(f"ByteRover {phase} result identity drifted")
    version = result.get("version")
    if (
        not isinstance(version, dict)
        or version.get("exit_code") != 0
        or version.get("timed_out") is not False
        or version.get("stdout") != "byterover-cli/3.16.1 linux-arm64 node-v22.21.1"
    ):
        raise DoctorError(f"ByteRover {phase} version receipt drifted")
    availability: dict[str, bool] = {}
    for field in ("offline_search", "hermes_query", "hermes_curate"):
        command = result.get(field)
        if not isinstance(command, dict):
            raise DoctorError(f"ByteRover {phase} {field} receipt is missing")
        availability[field] = bool(
            command.get("exit_code") == 0 and command.get("timed_out") is False
        )
    daemon = result.get("daemon")
    source_checks = result.get("source_checks")
    if (
        not isinstance(daemon, dict)
        or daemon.get("fatal_network_count", 0) < 3
        or daemon.get("every_log_has_network_fatal") is not True
        or not isinstance(source_checks, dict)
        or not source_checks
        or not all(value is True for value in source_checks.values())
    ):
        raise DoctorError(f"ByteRover {phase} falsifier evidence drifted")
    canary_sha = result.get("canary_file_sha256")
    if not isinstance(canary_sha, str) or len(canary_sha) != 64:
        raise DoctorError(f"ByteRover {phase} canary receipt drifted")
    return {
        "canary_file_sha256": canary_sha,
        "version": version["stdout"],
        "offline_search_available_under_network_none": availability["offline_search"],
        "hermes_query_available_under_network_none": availability["hermes_query"],
        "hermes_curate_available_under_network_none": availability["hermes_curate"],
        "daemon_network_fatal_reproduced": True,
        "source_checks": source_checks,
    }


def _stable_projection(phases: dict[str, dict[str, Any]]) -> dict[str, Any]:
    prepare = _validate_phase(phases["prepare"]["result"], "prepare")
    restart = _validate_phase(phases["restart"]["result"], "restart")
    if prepare != restart:
        raise DoctorError("ByteRover result changed across fresh-process restart")
    return prepare


def run_doctor(output: Path, image_tag: str) -> dict[str, Any]:
    experiment = validate_experiment_contract(DEFAULT_EXPERIMENT)
    if output.exists():
        raise DoctorError(f"output path already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cotcodec-byterover-source-") as source_tmp:
        source = _verify_sources(experiment, Path(source_tmp))
        image = _build_image(experiment, image_tag)
        volumes = [f"cotcodec-byterover-{secrets.token_hex(8)}" for _ in range(2)]
        try:
            for volume in volumes:
                _run(
                    [
                        "docker",
                        "volume",
                        "create",
                        "--label",
                        "org.cotcodec.study=hermes-byterover-offline-v1",
                        volume,
                    ]
                )
                _initialize_volume(image_id=image["image_id"], volume=volume)
            runs = []
            for volume in volumes:
                phases = {
                    phase: _run_phase(
                        image_id=image["image_id"],
                        volume=volume,
                        phase=phase,
                        runtime=experiment["runtime"],
                    )
                    for phase in ("prepare", "restart")
                }
                runs.append(
                    {"phases": phases, "stable_projection": _stable_projection(phases)}
                )
        finally:
            for volume in volumes:
                subprocess.run(
                    ["docker", "volume", "rm", volume],
                    check=False,
                    capture_output=True,
                )
        if runs[0]["stable_projection"] != runs[1]["stable_projection"]:
            raise DoctorError("ByteRover result changed across clean state volumes")
        projection = runs[0]["stable_projection"]
        if any(
            projection[field]
            for field in (
                "offline_search_available_under_network_none",
                "hermes_query_available_under_network_none",
                "hermes_curate_available_under_network_none",
            )
        ):
            raise DoctorError("ByteRover unexpectedly passed an offline command")
        report = {
            "schema_version": 1,
            "study": "hermes-byterover-offline-falsification-v1",
            "status": EXPECTED_STATUS,
            "scientific_result": False,
            "publication_ready": False,
            "source": source,
            "image": {
                "image_id": image["image_id"],
                "inspect_sha256": image["inspect_sha256"],
            },
            "run_count": 2,
            "stable_projection_sha256": _sha(_json_bytes(projection)),
            "findings": {
                **{
                    field: projection[field]
                    for field in (
                        "offline_search_available_under_network_none",
                        "hermes_query_available_under_network_none",
                        "hermes_curate_available_under_network_none",
                        "daemon_network_fatal_reproduced",
                    )
                },
                "hermes_query_is_provider_dependent": True,
                "hermes_curate_is_provider_dependent": True,
                "session_scoped_directory": False,
                "native_session_purge_supported": False,
            },
            "admission": {
                "provider_contract": "native-negative-only",
                "memory_lifecycle_h100": "forbidden-for-this-revision",
                "cluster_confirmation": "not-run",
            },
        }
        staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
        try:
            _write_once(staging / "experiment.yaml", DEFAULT_EXPERIMENT.read_bytes())
            _write_once(staging / "source-receipt.json", _json_bytes(source))
            _write_once(staging / "image-inspect.json", _json_bytes(image["inspect"]))
            for index, run in enumerate(runs, start=1):
                root = staging / f"run-{index}"
                for phase in ("prepare", "restart"):
                    record = run["phases"][phase]
                    _write_once(root / f"{phase}.argv.json", _json_bytes(record["argv"]))
                    _write_once(root / f"{phase}.json", record["stdout"])
                    _write_once(root / f"{phase}.stderr", record["stderr"])
                _write_once(
                    root / "stable-projection.json",
                    _json_bytes(run["stable_projection"]),
                )
            _write_once(staging / "report.json", _json_bytes(report))
            artifacts: dict[str, dict[str, Any]] = {}
            for path in sorted(staging.rglob("*")):
                if path.is_file():
                    name = path.relative_to(staging).as_posix()
                    artifacts[name] = {
                        "bytes": path.stat().st_size,
                        "sha256": _sha_path(path),
                    }
            manifest = {
                "schema_version": 1,
                "status": EXPECTED_STATUS,
                "files": artifacts,
                "root_sha256": _sha(_json_bytes(artifacts)),
            }
            _write_once(staging / "manifest.json", _json_bytes(manifest))
            os.rename(staging, output)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--image-tag",
        default="cotcodec/hermes-byterover:doctor-v1",
    )
    args = parser.parse_args()
    report = run_doctor(args.output, args.image_tag)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
