#!/usr/bin/env python3
"""Run the registered Icarus lifecycle falsifier in contained clean states."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validate_icarus_lifecycle_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    EXPECTED_STATUS,
    validate_experiment_contract,
)

DEFAULT_OUTPUT = (
    PROJECT_ROOT / "data" / "results" / "icarus-lifecycle" / "2026-08-16-local-docker-v1"
)
DEFAULT_IMAGE = "cotcodec-icarus-lifecycle:6e34870-arm64-v2"
DOCTOR = PROJECT_ROOT / "infra" / "memory-baselines" / "icarus" / "doctor.py"
DOCKERFILE = PROJECT_ROOT / "infra" / "memory-baselines" / "icarus" / "Dockerfile"
SUMMARY_RE = re.compile(r"(?P<failed>\d+) failed, (?P<passed>\d+) passed, (?P<skipped>\d+) skipped")


class RunnerError(RuntimeError):
    """Raised when contained Icarus evidence drifts or cannot be executed."""


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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
                raise RunnerError(f"short write: {path}")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _strict_json(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RunnerError(f"{label} did not emit strict JSON") from exc
    if not isinstance(value, dict):
        raise RunnerError(f"{label} did not emit a JSON object")
    return value


def _run(argv: list[str], *, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(argv, capture_output=True, check=False)
    if check and completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace")[-4000:]
        raise RunnerError(f"command failed ({completed.returncode}): {argv!r}\n{stderr}")
    return completed


def _image_contract(image: str, experiment: dict[str, Any]) -> dict[str, Any]:
    completed = _run(["docker", "image", "inspect", image])
    try:
        values = json.loads(completed.stdout)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RunnerError("docker image inspect was not JSON") from exc
    if not isinstance(values, list) or len(values) != 1 or not isinstance(values[0], dict):
        raise RunnerError("docker image inspect returned an unexpected roster")
    inspect = values[0]
    labels = (inspect.get("Config") or {}).get("Labels") or {}
    source = experiment["source"]
    expected = {
        "org.opencontainers.image.revision": source["revision"],
        "org.opencontainers.image.licenses": source["license"],
        "org.cotcodec.discovery-only": "true",
        "org.cotcodec.source-tree": source["tree"],
        "org.cotcodec.source-archive-sha256": source["git_archive_tar_sha256"],
        "org.cotcodec.doctor-sha256": _sha_path(DOCTOR),
    }
    for key, expected_value in expected.items():
        if labels.get(key) != expected_value:
            raise RunnerError(f"Icarus image label {key} drifted")
    if inspect.get("Architecture") != "arm64" or inspect.get("Os") != "linux":
        raise RunnerError("Icarus image platform drifted")
    return {
        "image_id": inspect.get("Id"),
        "architecture": inspect.get("Architecture"),
        "os": inspect.get("Os"),
        "inspect_sha256": _sha_bytes(completed.stdout),
        "labels": expected,
    }


def _docker_prefix(*, image_id: str, state_root: Path | None = None) -> list[str]:
    argv = [
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
        "256",
        "--memory",
        "1g",
        "--cpus",
        "1",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=256m",
        "--user",
        "65532:65532",
        "-e",
        "HOME=/tmp/icarus-home",
    ]
    if state_root is not None:
        argv.extend(["-v", f"{state_root.resolve()}:/state:rw"])
    argv.append(image_id)
    return argv


def _upstream_suite(image_id: str, output: Path) -> dict[str, Any]:
    argv = [*_docker_prefix(image_id=image_id), "-m", "pytest", "-q"]
    completed = _run(argv, check=False)
    raw = completed.stdout + completed.stderr
    _write_once(output / "upstream-suite.txt", raw)
    match = SUMMARY_RE.search(raw.decode("utf-8", errors="replace"))
    if match is None:
        raise RunnerError("cannot parse Icarus upstream-suite summary")
    counts = {key: int(value) for key, value in match.groupdict().items()}
    if completed.returncode != 1 or counts != {"failed": 6, "passed": 207, "skipped": 39}:
        raise RunnerError(f"Icarus upstream-suite outcome drifted: {counts}")
    return {
        "argv": argv,
        "exit_code": completed.returncode,
        **counts,
        "output": "upstream-suite.txt",
        "output_sha256": _sha_path(output / "upstream-suite.txt"),
        "failure_class": "mcp-major-version-path-incompatibility",
    }


def _phase(
    image_id: str, state_root: Path, phase: str, repeat: int
) -> tuple[dict[str, Any], list[str]]:
    argv = [
        *_docker_prefix(image_id=image_id, state_root=state_root),
        "/opt/cotcodec/doctor.py",
        phase,
        "--state-root",
        "/state",
        "--repeat",
        str(repeat),
    ]
    completed = _run(argv)
    return _strict_json(completed.stdout, f"Icarus repeat {repeat} {phase}"), argv


def _projection(run: dict[str, dict[str, Any]]) -> dict[str, Any]:
    prepare = run["prepare"]
    restart = run["verify-restart"]
    purge = run["purge-probe"]
    return {
        "prepare": {
            field: prepare[field]
            for field in (
                "manual_promotion_created_shared_page",
                "working_state_removed_after_archive",
                "private_archive_created",
                "same_agent_briefing_contains_private_attempt",
                "other_agent_briefing_excludes_private_attempt",
                "supersession_marks_old_entry",
                "rollback_is_non_destructive_and_persisted",
                "duplicate_end_session_created_extra_summary",
                "duplicate_end_session_created_extra_wiki_link",
                "first_briefing_was_empty_floor",
            )
        },
        "restart": {
            field: restart[field]
            for field in (
                "restart_preserved_private_archive",
                "restart_preserved_shared_wiki",
                "restart_preserved_agent_isolation",
                "restart_preserved_supersession",
                "restart_preserved_rollback",
                "restart_preserved_duplicate_promotions",
            )
        },
        "purge": {
            "status": purge["status"],
            "native_delete_or_purge_api_available": purge[
                "native_delete_or_purge_api_available"
            ],
            "plaintext_residue": purge["plaintext_residue"],
            "all_canaries_remain_physically_present": purge[
                "all_canaries_remain_physically_present"
            ],
            "manual_promotion_only": purge["manual_promotion_only"],
            "h100_actor_admission": purge["h100_actor_admission"],
        },
    }


def run_doctor(*, experiment_path: Path, output: Path, image: str) -> dict[str, Any]:
    experiment = validate_experiment_contract(experiment_path)
    if output.exists():
        raise RunnerError(f"output already exists: {output}")
    output.mkdir(parents=True, mode=0o700)
    image_contract = _image_contract(image, experiment)
    suite = _upstream_suite(image_contract["image_id"], output)

    runs: list[dict[str, dict[str, Any]]] = []
    phase_receipts: list[dict[str, Any]] = []
    for repeat in (1, 2):
        repeat_root = output / f"repeat-{repeat}"
        state_root = repeat_root / "state"
        state_root.mkdir(parents=True, mode=0o777)
        os.chmod(state_root, 0o777)
        run: dict[str, dict[str, Any]] = {}
        for phase in ("prepare", "verify-restart", "purge-probe"):
            result, argv = _phase(image_contract["image_id"], state_root, phase, repeat)
            artifact = repeat_root / f"{phase}.json"
            _write_once(artifact, _json_bytes(result))
            run[phase] = result
            phase_receipts.append(
                {
                    "repeat": repeat,
                    "phase": phase,
                    "argv": argv,
                    "artifact": str(artifact.relative_to(PROJECT_ROOT)),
                    "artifact_sha256": _sha_path(artifact),
                }
            )
        os.chmod(state_root, 0o700)
        runs.append(run)

    projections = [_projection(run) for run in runs]
    if projections[0] != projections[1]:
        raise RunnerError("Icarus clean-state semantic projections differ")
    projection = projections[0]
    positive_values = [
        *projection["prepare"].values(),
        *projection["restart"].values(),
    ]
    if not all(value is True for value in positive_values):
        raise RunnerError("Icarus positive lifecycle prerequisites did not all pass")
    purge = projection["purge"]
    if (
        purge["status"] != EXPECTED_STATUS
        or purge["native_delete_or_purge_api_available"] is not False
        or purge["all_canaries_remain_physically_present"] is not True
        or not all(purge["plaintext_residue"].values())
        or purge["manual_promotion_only"] is not True
        or purge["h100_actor_admission"] != "forbidden-for-this-revision"
    ):
        raise RunnerError("Icarus preregistered falsification was not reproduced")

    report = {
        "schema_version": 1,
        "status": EXPECTED_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "h100_actor_admission": "forbidden-for-this-revision",
        "experiment": str(experiment_path.relative_to(PROJECT_ROOT)),
        "experiment_sha256": _sha_path(experiment_path),
        "source": experiment["source"],
        "runtime": experiment["runtime"],
        "image": image_contract,
        "dockerfile_sha256": _sha_path(DOCKERFILE),
        "doctor_sha256": _sha_path(DOCTOR),
        "upstream_suite": suite,
        "phase_receipts": phase_receipts,
        "stable_projection": projection,
        "stable_projection_sha256": _sha_bytes(_json_bytes(projection)),
        "reproduced_in_two_clean_states": True,
        "conclusion": (
            "Pinned Icarus reproduces manual promotion, private archives, shared wiki state, "
            "supersession, non-destructive rollback, and fresh-process persistence. Replaying "
            "end_session duplicates promoted summaries and wiki links; no native scoped delete "
            "or purge API exists, and all synthetic canaries remain physically resident. The "
            "unlocked MCP dependency also resolves to an incompatible major version."
        ),
    }
    report_path = output / "report.json"
    _write_once(report_path, _json_bytes(report))
    manifest = {
        "schema_version": 1,
        "status": "SEALED_DISCOVERY_NEGATIVE",
        "report": "report.json",
        "report_sha256": _sha_path(report_path),
        "image_id": image_contract["image_id"],
        "stable_projection_sha256": report["stable_projection_sha256"],
        "artifact_count": len(phase_receipts) + 1,
    }
    _write_once(output / "manifest.json", _json_bytes(manifest))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", type=Path, default=DEFAULT_EXPERIMENT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    args = parser.parse_args()
    report = run_doctor(
        experiment_path=args.experiment.resolve(),
        output=args.output.resolve(),
        image=args.image,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
