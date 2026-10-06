#!/usr/bin/env python3
"""Run and seal the contained ReasoningBank frozen-bank CPU doctor."""

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

from harness.memory_trials.procedural_bank import (  # noqa: E402
    FrozenProceduralBankArtifact,
    ProceduralQuery,
    ProceduralRetrieval,
)
from harness.memory_trials.schema import canonical_json, sha256_text  # noqa: E402
from scripts.run_reasoningbank_frozen_bank_doctor import (  # noqa: E402
    STATUS,
    _fixture_source_artifact_rows,
)
from scripts.run_reasoningbank_frozen_bank_doctor import (  # noqa: E402
    _fixture as _doctor_fixture,
)

EXPECTED_IMAGE_TITLE = "cotcodec-reasoningbank-frozen-bank-doctor"
EXPECTED_BASE_IMAGE = (
    "docker.io/library/python:3.12.11-slim-bookworm@sha256:"
    "519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7"
)
EXPECTED_TORCH_WHEEL_SHA256 = (
    "70ecb2659af6373b7c5336e692e665605b0201ea21ff51aaea47e1d75ea6b5aa"
)
EXPECTED_CODE_SHA256 = (
    "5bcc1cbc873c33fb49d1061daf7b829f872112b3bbb93d4ce9c9db092a920ce8"
)
EXPECTED_IMAGE_ID = (
    "sha256:d3f7858e55209cd3af46b97e21aafcb8e0675ee59a64a787589ee2679f283430"
)
CORE_FILES = (
    "bank.json",
    "fixture-source-artifacts.jsonl",
    "manifest.json",
    "report.json",
    "retrievals.jsonl",
)


class ContainerDoctorError(RuntimeError):
    """Raised when the live Docker or output contract fails closed."""


def _run(argv: list[str], *, timeout: int = 1200) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(argv, check=False, capture_output=True, timeout=timeout)
    if completed.returncode != 0:
        raise ContainerDoctorError(
            f"command failed ({completed.returncode}): {argv!r}\n"
            f"stdout={completed.stdout.decode(errors='replace')}\n"
            f"stderr={completed.stderr.decode(errors='replace')}"
        )
    return completed


def _strict_json(data: bytes, owner: str) -> Any:
    def reject(value: str) -> None:
        raise ContainerDoctorError(f"{owner} contains non-finite JSON: {value}")

    try:
        return json.loads(data, parse_constant=reject)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContainerDoctorError(f"{owner} is not strict JSON") from exc


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_path(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ContainerDoctorError(f"expected regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def _write_once(path: Path, data: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise ContainerDoctorError(f"short write: {path}")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _one_inspect(argv: list[str], owner: str) -> dict[str, Any]:
    payload = _strict_json(_run(argv).stdout, owner)
    if not isinstance(payload, list) or len(payload) != 1 or not isinstance(payload[0], dict):
        raise ContainerDoctorError(f"{owner} must contain exactly one object")
    return payload[0]


def _validate_image(image: str) -> dict[str, Any]:
    inspect = _one_inspect(["docker", "image", "inspect", image], "image inspect")
    labels = inspect.get("Config", {}).get("Labels", {})
    expected = {
        "org.opencontainers.image.title": EXPECTED_IMAGE_TITLE,
        "org.opencontainers.image.cotcodec-base-image": EXPECTED_BASE_IMAGE,
        "org.opencontainers.image.cotcodec-code-sha256": EXPECTED_CODE_SHA256,
        "org.opencontainers.image.cotcodec-torch-cpu-wheel-sha256": (
            EXPECTED_TORCH_WHEEL_SHA256
        ),
        "org.opencontainers.image.cotcodec-scientific-result": "false",
    }
    if not isinstance(labels, dict) or any(
        labels.get(key) != value for key, value in expected.items()
    ):
        raise ContainerDoctorError("image labels differ from the frozen doctor contract")
    image_id = inspect.get("Id")
    if (
        not isinstance(image_id, str)
        or not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id)
        or image_id != EXPECTED_IMAGE_ID
        or inspect.get("Architecture") != "arm64"
        or inspect.get("Os") != "linux"
    ):
        raise ContainerDoctorError("image identity or platform differs from the frozen contract")
    return inspect


def _mount_map(inspect: dict[str, Any]) -> dict[str, dict[str, Any]]:
    mounts = inspect.get("Mounts")
    if not isinstance(mounts, list):
        raise ContainerDoctorError("container mounts are absent")
    result: dict[str, dict[str, Any]] = {}
    for row in mounts:
        if not isinstance(row, dict) or not isinstance(row.get("Destination"), str):
            raise ContainerDoctorError("container mount row is invalid")
        result[row["Destination"]] = row
    return result


def _validate_container(
    inspect: dict[str, Any],
    *,
    image_id: str,
    model_root: Path,
    receipt_root: Path,
    output: Path,
    require_stopped: bool,
) -> dict[str, Any]:
    host = inspect.get("HostConfig")
    config = inspect.get("Config")
    state = inspect.get("State")
    if not isinstance(host, dict) or not isinstance(config, dict) or not isinstance(state, dict):
        raise ContainerDoctorError("container inspect is incomplete")
    if (
        inspect.get("Image") != image_id
        or host.get("NetworkMode") != "none"
        or host.get("ReadonlyRootfs") is not True
        or set(host.get("CapDrop") or []) != {"ALL"}
        or "no-new-privileges" not in set(host.get("SecurityOpt") or [])
        or host.get("PidsLimit") != 256
        or host.get("NanoCpus") != 4_000_000_000
        or host.get("Memory") != 4 * 1024**3
        or host.get("DeviceRequests") not in (None, [])
        or config.get("User") != f"{os.getuid()}:{os.getgid()}"
    ):
        raise ContainerDoctorError("container isolation or resource contract drifted")
    environment = config.get("Env")
    if not isinstance(environment, list) or any(
        value.startswith(("OPENAI_API_KEY=", "ANTHROPIC_API_KEY=", "HF_TOKEN="))
        for value in environment
    ):
        raise ContainerDoctorError("container environment contains a forbidden secret")
    mounts = _mount_map(inspect)
    expected_mounts = {
        "/models": (model_root, False),
        "/receipts": (receipt_root, False),
        "/outputs": (output, True),
    }
    for destination, (source, writable) in expected_mounts.items():
        row = mounts.get(destination)
        if (
            row is None
            or Path(str(row.get("Source"))).resolve() != source
            or bool(row.get("RW")) is not writable
        ):
            raise ContainerDoctorError(f"container mount drifted: {destination}")
    if require_stopped and (
        state.get("Running") is not False
        or state.get("ExitCode") != 0
        or state.get("OOMKilled") is not False
    ):
        raise ContainerDoctorError("container did not terminate cleanly")
    return {
        "image_id": image_id,
        "network_mode": host["NetworkMode"],
        "read_only_rootfs": host["ReadonlyRootfs"],
        "cap_drop": host["CapDrop"],
        "security_opt": host["SecurityOpt"],
        "pids_limit": host["PidsLimit"],
        "nano_cpus": host["NanoCpus"],
        "memory_bytes": host["Memory"],
        "device_requests": host.get("DeviceRequests"),
        "user": config["User"],
        "mounts": {
            destination: {
                "source": str(source),
                "writable": writable,
            }
            for destination, (source, writable) in expected_mounts.items()
        },
        "exit_code": state.get("ExitCode") if require_stopped else None,
        "oom_killed": state.get("OOMKilled") if require_stopped else None,
    }


def _load_jsonl_rows(path: Path, *, owner: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(path.read_bytes().splitlines(), start=1):
        if not raw_line:
            raise ContainerDoctorError(f"{owner} line {line_number} is empty")
        row = _strict_json(raw_line, f"{owner} line {line_number}")
        if not isinstance(row, dict):
            raise ContainerDoctorError(f"{owner} line {line_number} is not an object")
        rows.append(row)
    return rows


def _validate_fixture_source_rows(
    rows: list[dict[str, Any]],
    *,
    bank: FrozenProceduralBankArtifact,
) -> None:
    fixture_items, _, _ = _doctor_fixture()
    expected_rows = _fixture_source_artifact_rows(fixture_items)
    if rows != expected_rows:
        raise ContainerDoctorError("fixture source artifact roster or content drifted")
    items = {item.source_task_id: item for item in bank.items}
    for row in rows:
        task_id = row["source_task_id"]
        item = items.get(task_id)
        if item is None or (
            row["trajectory_sha256"]
            != sha256_text(canonical_json(row["trajectory"]))
            or row["correctness_receipt_sha256"]
            != sha256_text(canonical_json(row["correctness_receipt"]))
            or row["generator_receipt_sha256"]
            != sha256_text(canonical_json(row["generator_receipt"]))
            or row["trajectory_sha256"] != item.source_trajectory_sha256
            or row["correctness_receipt_sha256"]
            != item.correctness_receipt_sha256
            or row["generator_receipt_sha256"] != item.generator_receipt_sha256
        ):
            raise ContainerDoctorError("fixture source artifact does not bind bank lineage")


def _validate_retrieval_rows(
    rows: list[dict[str, Any]],
    *,
    bank: FrozenProceduralBankArtifact,
) -> None:
    fixture_items, fixture_split, fixture_queries = _doctor_fixture()
    if bank.split_manifest != fixture_split:
        raise ContainerDoctorError("bank split differs from the registered doctor fixture")
    actual_items = {
        item.source_task_id: item.model_dump(mode="json", exclude={"item_id"})
        for item in bank.items
    }
    expected_items = {
        item.source_task_id: item.model_dump(mode="json") for item in fixture_items
    }
    if actual_items != expected_items:
        raise ContainerDoctorError("bank items differ from the registered doctor fixture")
    if len(rows) != len(fixture_queries):
        raise ContainerDoctorError("retrieval row count differs from the registered fixture")
    bank_items = {item.source_task_id: item for item in bank.items}
    seen_requests: set[str] = set()
    for row, (expected_query, expected_source_task_id) in zip(
        rows, fixture_queries, strict=True
    ):
        if set(row) != {"query", "expected_source_task_id", "retrieval"}:
            raise ContainerDoctorError("retrieval row schema drifted")
        query = ProceduralQuery.model_validate(row["query"])
        retrieval = ProceduralRetrieval.model_validate(row["retrieval"])
        if (
            query != expected_query
            or row["expected_source_task_id"] != expected_source_task_id
            or query.request_id in seen_requests
        ):
            raise ContainerDoctorError("retrieval query roster or oracle drifted")
        seen_requests.add(query.request_id)
        if (
            retrieval.request_id != query.request_id
            or retrieval.query_sha256
            != sha256_text(canonical_json(query.model_dump(mode="json")))
            or retrieval.bank_artifact_sha256 != bank.artifact_sha256
            or retrieval.embedding_model_receipt_sha256
            != bank.embedding_identity.model_receipt_sha256
            or len(retrieval.hits) != 1
            or retrieval.hits[0].source_task_id != expected_source_task_id
        ):
            raise ContainerDoctorError("retrieval receipt or top-one gate drifted")
        source = bank_items.get(expected_source_task_id)
        hit = retrieval.hits[0]
        if source is None or (
            hit.item_id != source.item_id
            or hit.procedural_text != source.procedural_text
            or hit.outcome != source.outcome
            or hit.source_family_id != source.source_family_id
            or hit.source_trajectory_sha256 != source.source_trajectory_sha256
            or hit.correctness_receipt_sha256 != source.correctness_receipt_sha256
            or hit.generator_receipt_sha256 != source.generator_receipt_sha256
            or hit.truncated
            or retrieval.injected_tokens_estimate > query.max_injected_tokens
        ):
            raise ContainerDoctorError("retrieval hit does not bind the frozen bank item")


def _validate_outputs(output: Path, *, receipt_root: Path) -> dict[str, str]:
    names = {path.name for path in output.iterdir()}
    if names != set(CORE_FILES):
        raise ContainerDoctorError("doctor output roster differs before host sealing")
    manifest = _strict_json((output / "manifest.json").read_bytes(), "doctor manifest")
    report = _strict_json((output / "report.json").read_bytes(), "doctor report")
    bank_payload = _strict_json((output / "bank.json").read_bytes(), "bank artifact")
    if not isinstance(manifest, dict) or not isinstance(report, dict):
        raise ContainerDoctorError("doctor report or manifest is not an object")
    if (
        manifest.get("status") != STATUS
        or report.get("status") != STATUS
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
    ):
        raise ContainerDoctorError("doctor result status drifted")
    bank = FrozenProceduralBankArtifact.model_validate(bank_payload)
    fixture_source_rows = _load_jsonl_rows(
        output / "fixture-source-artifacts.jsonl",
        owner="fixture source JSONL",
    )
    _validate_fixture_source_rows(fixture_source_rows, bank=bank)
    retrieval_rows = _load_jsonl_rows(
        output / "retrievals.jsonl",
        owner="retrieval JSONL",
    )
    _validate_retrieval_rows(retrieval_rows, bank=bank)
    required_gates = {
        "bank_artifact_sha256": bank.artifact_sha256,
        "document_text_field": "procedural_text",
        "split_manifest_sha256": bank.split_manifest.manifest_sha256,
        "train_items": len(bank.items),
        "evaluation_queries": len(retrieval_rows),
        "top_one_correct": len(retrieval_rows),
        "repeated_bank_freeze_exact": True,
        "repeated_retrieval_exact": True,
        "retrieval_bank_immutable": True,
        "train_task_leakage_rejected": True,
        "task_family_mismatch_rejected": True,
        "fixture_source_artifacts": len(fixture_source_rows),
        "fixture_receipts_only": True,
        "real_reasoningbank_trajectories_present": False,
        "network_required": False,
        "api_calls": 0,
        "gpus": 0,
    }
    if any(report.get(key) != value for key, value in required_gates.items()):
        raise ContainerDoctorError("doctor report gates disagree with host recomputation")
    if report.get("model") != bank.embedding_identity.model_dump(mode="json"):
        raise ContainerDoctorError("doctor report model differs from the frozen bank")
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise ContainerDoctorError("doctor file manifest is absent")
    for name in (
        "bank.json",
        "fixture-source-artifacts.jsonl",
        "report.json",
        "retrievals.jsonl",
    ):
        if files.get(name) != _sha_path(output / name):
            raise ContainerDoctorError(f"doctor output hash drifted: {name}")
    expected_code = {
        relative: _sha_path(PROJECT_ROOT / relative)
        for relative in (
            "harness/memory_trials/procedural_bank.py",
            "harness/memory_trials/dense_control.py",
            "scripts/dense_bge_factory.py",
            "scripts/run_reasoningbank_frozen_bank_doctor.py",
        )
    }
    if manifest.get("code_sha256s") != expected_code:
        raise ContainerDoctorError("host and image code roster or digest differs")
    model_receipt = receipt_root / "bge-small-en-v1.5.json"
    if (
        manifest.get("model_receipt_file_sha256") != _sha_path(model_receipt)
        or manifest.get("model_receipt_file_sha256")
        != bank.embedding_identity.model_receipt_sha256
    ):
        raise ContainerDoctorError("model receipt file does not bind the bank")
    unsigned = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    if manifest.get("manifest_sha256") != sha256_text(canonical_json(unsigned)):
        raise ContainerDoctorError("doctor manifest digest drifted")
    return {name: _sha_path(output / name) for name in CORE_FILES}


def run_container(
    *,
    image: str,
    model_root: Path,
    receipt_root: Path,
    output: Path,
) -> dict[str, Any]:
    for path, owner in ((model_root, "model root"), (receipt_root, "receipt root")):
        if path.is_symlink() or not path.is_dir():
            raise ContainerDoctorError(f"{owner} must be a regular directory")
    if output.exists():
        raise ContainerDoctorError("output path already exists")
    output.mkdir(parents=True, mode=0o777)
    output.chmod(0o777)
    image_inspect = _validate_image(image)
    image_id = str(image_inspect["Id"])
    container_name = f"cotcodec-reasoningbank-{os.getpid()}"
    container_id: str | None = None
    stdout = b""
    stderr = b""
    try:
        created = _run(
            [
                "docker",
                "create",
                "--name",
                container_name,
                "--network",
                "none",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--pids-limit",
                "256",
                "--cpus",
                "4",
                "--memory",
                "4g",
                "--user",
                f"{os.getuid()}:{os.getgid()}",
                "--env",
                "USER=cotcodec-doctor",
                "--env",
                "LOGNAME=cotcodec-doctor",
                "--env",
                "TORCHINDUCTOR_CACHE_DIR=/tmp/torchinductor",
                "--tmpfs",
                "/tmp:rw,noexec,nosuid,nodev,size=536870912",
                "--volume",
                f"{model_root}:/models:ro",
                "--volume",
                f"{receipt_root}:/receipts:ro",
                "--volume",
                f"{output}:/outputs:rw",
                image_id,
            ]
        )
        container_id = created.stdout.decode().strip()
        if not re.fullmatch(r"[0-9a-f]{64}", container_id):
            raise ContainerDoctorError("docker create returned an invalid container ID")
        created_inspect = _one_inspect(
            ["docker", "container", "inspect", container_id], "created container inspect"
        )
        created_projection = _validate_container(
            created_inspect,
            image_id=image_id,
            model_root=model_root,
            receipt_root=receipt_root,
            output=output,
            require_stopped=False,
        )
        completed = subprocess.run(
            ["docker", "start", "--attach", container_id],
            check=False,
            capture_output=True,
            timeout=1200,
        )
        stdout = completed.stdout
        stderr = completed.stderr
        if completed.returncode != 0:
            raise ContainerDoctorError(
                f"doctor container exited {completed.returncode}: "
                f"{stderr.decode(errors='replace')}"
            )
        stopped_inspect = _one_inspect(
            ["docker", "container", "inspect", container_id], "stopped container inspect"
        )
        stopped_projection = _validate_container(
            stopped_inspect,
            image_id=image_id,
            model_root=model_root,
            receipt_root=receipt_root,
            output=output,
            require_stopped=True,
        )
        core_hashes = _validate_outputs(output, receipt_root=receipt_root)
        _write_once(output / "container-stdout.log", stdout)
        _write_once(output / "container-stderr.log", stderr)
        _write_once(output / "image-inspect.json", _json_bytes(image_inspect))
        _write_once(output / "container-inspect.json", _json_bytes(stopped_inspect))
        receipt_unsigned = {
            "schema_version": 1,
            "status": STATUS,
            "scientific_result": False,
            "publication_ready": False,
            "image_id": image_id,
            "image_labels": image_inspect["Config"]["Labels"],
            "host_code_sha256s": {
                "scripts/run_reasoningbank_frozen_bank_container.py": _sha_path(
                    Path(__file__).resolve()
                ),
                "infra/memory-baselines/reasoningbank-frozen/Dockerfile": _sha_path(
                    PROJECT_ROOT
                    / "infra/memory-baselines/reasoningbank-frozen/Dockerfile"
                ),
            },
            "created_contract": created_projection,
            "stopped_contract": stopped_projection,
            "core_files": core_hashes,
            "stdout_sha256": _sha_bytes(stdout),
            "stderr_sha256": _sha_bytes(stderr),
        }
        receipt = {
            **receipt_unsigned,
            "receipt_sha256": sha256_text(canonical_json(receipt_unsigned)),
        }
        _write_once(output / "execution-receipt.json", _json_bytes(receipt))
        output.chmod(0o755)
        return receipt
    finally:
        if container_id is not None:
            subprocess.run(
                ["docker", "container", "rm", "--force", container_id],
                check=False,
                capture_output=True,
                timeout=60,
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--image", default=EXPECTED_IMAGE_ID
    )
    parser.add_argument("--model-root", type=Path, default=PROJECT_ROOT / "data/models")
    parser.add_argument(
        "--receipt-root", type=Path, default=PROJECT_ROOT / "data/model-receipts"
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    receipt = run_container(
        image=args.image,
        model_root=args.model_root.resolve(),
        receipt_root=args.receipt_root.resolve(),
        output=args.output_dir.resolve(),
    )
    print(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
