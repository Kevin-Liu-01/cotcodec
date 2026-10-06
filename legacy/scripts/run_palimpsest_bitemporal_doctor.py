#!/usr/bin/env python3
"""Run and seal the registered Palimpsest bitemporal falsifier."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validate_palimpsest_bitemporal_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    EXPECTED_STATUS,
    validate_experiment_contract,
)

DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data"
    / "results"
    / "palimpsest-bitemporal"
    / "2026-08-16-local-docker-v1"
)
DEFAULT_IMAGE = "cotcodec-palimpsest-bitemporal:0f83e16-arm64-v1"
DOCTOR = PROJECT_ROOT / "infra" / "memory-baselines" / "palimpsest" / "doctor.py"
DOCKERFILE = PROJECT_ROOT / "infra" / "memory-baselines" / "palimpsest" / "Dockerfile"
SUMMARY_RE = re.compile(
    r"(?P<failed>\d+) failed, (?P<passed>\d+) passed, (?P<skipped>\d+) skipped"
)


class RunnerError(RuntimeError):
    """Raised when contained Palimpsest evidence drifts."""


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


def _run(argv: list[str], *, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(argv, capture_output=True, check=False)
    if check and completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace")[-4000:]
        raise RunnerError(f"command failed ({completed.returncode}): {argv!r}\n{stderr}")
    return completed


def _strict_json(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RunnerError(f"{label} did not emit strict JSON") from exc
    if not isinstance(value, dict):
        raise RunnerError(f"{label} did not emit a JSON object")
    return value


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
            raise RunnerError(f"Palimpsest image label {key} drifted")
    if inspect.get("Architecture") != "arm64" or inspect.get("Os") != "linux":
        raise RunnerError("Palimpsest image platform drifted")
    return {
        "image_id": inspect.get("Id"),
        "architecture": inspect.get("Architecture"),
        "os": inspect.get("Os"),
        "inspect_sha256": _sha_bytes(completed.stdout),
        "labels": expected,
    }


def _docker_prefix(image_id: str) -> list[str]:
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
        "256",
        "--memory",
        "2g",
        "--cpus",
        "2",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=512m",
        "--user",
        "65532:65532",
        "-e",
        "HOME=/tmp/palimpsest-home",
        image_id,
    ]


def _upstream_suite(image_id: str, output: Path) -> dict[str, Any]:
    argv = [*_docker_prefix(image_id), "-m", "pytest", "-rA"]
    completed = _run(argv, check=False)
    raw = completed.stdout + completed.stderr
    _write_once(output / "upstream-suite.txt", raw)
    match = SUMMARY_RE.search(raw.decode("utf-8", errors="replace"))
    if match is None:
        raise RunnerError("cannot parse Palimpsest upstream-suite summary")
    counts = {key: int(value) for key, value in match.groupdict().items()}
    expected = {"failed": 11, "passed": 274, "skipped": 35}
    if completed.returncode != 1 or counts != expected:
        raise RunnerError(f"Palimpsest upstream-suite outcome drifted: {counts}")
    return {
        "argv": argv,
        "exit_code": completed.returncode,
        **counts,
        "output": "upstream-suite.txt",
        "output_sha256": _sha_path(output / "upstream-suite.txt"),
    }


def _initialize_volume(image_id: str, volume: str) -> None:
    # Root is used only to make a new Docker-managed volume writable. The
    # third-party doctor itself always runs unprivileged with all caps dropped.
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
        "--user",
        "0:0",
        "-v",
        f"{volume}:/state:rw",
        image_id,
        "-c",
        'import os; os.chmod("/state", 0o777)',
    ]
    _run(argv)


def _phase(image_id: str, volume: str, phase: str, repeat: int) -> tuple[dict[str, Any], list[str]]:
    argv = [
        *_docker_prefix(image_id)[:-1],
        "-v",
        f"{volume}:/state:rw",
        image_id,
        "/opt/cotcodec/doctor.py",
        phase,
        "--state-root",
        "/state",
        "--repeat",
        str(repeat),
    ]
    completed = _run(argv)
    return _strict_json(completed.stdout, f"Palimpsest repeat {repeat} {phase}"), argv


def _export_volume_file(image_id: str, volume: str, path: str) -> bytes:
    argv = [
        *_docker_prefix(image_id)[:-1],
        "-v",
        f"{volume}:/state:ro",
        image_id,
        "-c",
        f'import sys; sys.stdout.buffer.write(open("/state/{path}", "rb").read())',
    ]
    return _run(argv).stdout


def _projection(run: dict[str, dict[str, Any]]) -> dict[str, Any]:
    prepare = run["prepare"]
    restart = run["verify-restart"]
    purge = run["purge-probe"]
    return {
        "prepare": {
            field: prepare[field]
            for field in (
                "ordinary_valid_time_correct",
                "pre_restart_knowledge_cutoff_correct",
                "pre_restart_cardinality_vote_correct",
                "native_save_is_row_count_idempotent",
            )
        },
        "restart": {
            field: restart[field]
            for field in (
                "restart_preserved_ordinary_valid_time",
                "restart_preserved_current_value",
                "restart_preserved_knowledge_cutoff",
                "restart_preserved_closed_tx",
                "restart_preserved_cardinality_continuation",
                "uninterrupted_goal_after_continuation",
                "restored_goal_after_continuation",
            )
        },
        "purge": {
            field: purge[field]
            for field in (
                "status",
                "correction_hides_canary_from_current_facts",
                "native_delete_or_purge_api_available",
                "plaintext_canary_remains_in_sqlite",
                "h100_actor_admission",
            )
        },
    }


def run_doctor(*, experiment_path: Path, output: Path, image: str) -> dict[str, Any]:
    experiment = validate_experiment_contract(experiment_path)
    if output.exists():
        raise RunnerError(f"output already exists: {output}")
    output.mkdir(parents=True, mode=0o700)
    image_contract = _image_contract(image, experiment)
    image_id = image_contract["image_id"]
    suite = _upstream_suite(image_id, output)

    runs: list[dict[str, dict[str, Any]]] = []
    receipts: list[dict[str, Any]] = []
    for repeat in (1, 2):
        volume = f"cotcodec-palimpsest-{uuid.uuid4().hex}"
        _run(["docker", "volume", "create", volume])
        try:
            _initialize_volume(image_id, volume)
            run: dict[str, dict[str, Any]] = {}
            repeat_root = output / f"repeat-{repeat}"
            for phase in ("prepare", "verify-restart", "purge-probe"):
                result, argv = _phase(image_id, volume, phase, repeat)
                artifact = repeat_root / f"{phase}.json"
                _write_once(artifact, _json_bytes(result))
                run[phase] = result
                receipts.append(
                    {
                        "repeat": repeat,
                        "phase": phase,
                        "argv": argv,
                        "artifact": str(artifact.relative_to(PROJECT_ROOT)),
                        "artifact_sha256": _sha_path(artifact),
                    }
                )
            database = repeat_root / "palimpsest.db"
            contract = repeat_root / "contract.json"
            _write_once(database, _export_volume_file(image_id, volume, "palimpsest.db"))
            _write_once(contract, _export_volume_file(image_id, volume, "contract.json"))
            receipts.extend(
                [
                    {
                        "repeat": repeat,
                        "artifact": str(path.relative_to(PROJECT_ROOT)),
                        "artifact_sha256": _sha_path(path),
                    }
                    for path in (database, contract)
                ]
            )
            runs.append(run)
        finally:
            _run(["docker", "volume", "rm", volume], check=False)

    projections = [_projection(run) for run in runs]
    if projections[0] != projections[1]:
        raise RunnerError("Palimpsest clean-state semantic projections differ")
    projection = projections[0]
    prepare = projection["prepare"]
    restart = projection["restart"]
    purge = projection["purge"]
    if not all(prepare.values()):
        raise RunnerError("Palimpsest pre-restart prerequisites did not pass")
    if not (
        restart["restart_preserved_ordinary_valid_time"] is True
        and restart["restart_preserved_current_value"] is True
        and restart["restart_preserved_knowledge_cutoff"] is False
        and restart["restart_preserved_closed_tx"] is False
        and restart["restart_preserved_cardinality_continuation"] is False
        and restart["uninterrupted_goal_after_continuation"] == ["delta"]
        and restart["restored_goal_after_continuation"] == ["gamma", "delta"]
    ):
        raise RunnerError("Palimpsest restart falsification drifted")
    if not (
        purge["status"] == EXPECTED_STATUS
        and purge["correction_hides_canary_from_current_facts"] is True
        and purge["native_delete_or_purge_api_available"] is False
        and purge["plaintext_canary_remains_in_sqlite"] is True
        and purge["h100_actor_admission"] == "forbidden-for-this-revision"
    ):
        raise RunnerError("Palimpsest erasure falsification drifted")

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
        "artifact_receipts": receipts,
        "stable_projection": projection,
        "stable_projection_sha256": _sha_bytes(_json_bytes(projection)),
        "reproduced_in_two_clean_states": True,
        "conclusion": (
            "Pinned Palimpsest preserves ordinary valid-time/current values across SQLite "
            "restart, but drops transaction-time closure metadata and per-key cardinality "
            "votes. Knowledge-cutoff answers and subsequent writes therefore diverge after "
            "restart. Native correction only hides a value logically; plaintext remains in "
            "the append-only SQLite store, and there is no scoped delete/purge API."
        ),
    }
    report_path = output / "report.json"
    _write_once(report_path, _json_bytes(report))
    manifest = {
        "schema_version": 1,
        "status": "SEALED_DISCOVERY_NEGATIVE",
        "report": "report.json",
        "report_sha256": _sha_path(report_path),
        "image_id": image_id,
        "stable_projection_sha256": report["stable_projection_sha256"],
        "artifact_count": len(receipts) + 2,
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
