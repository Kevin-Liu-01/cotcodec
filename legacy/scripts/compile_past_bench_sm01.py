#!/usr/bin/env python3
"""Compile one fail-closed PAST-Bench SM01 discovery workload."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

import yaml

PAST_IMAGE_ID = "sha256:ebcf7eea7f1977f03e5e007edf265fcd120edadcd6d48e81f63df70715783150"
PAST_REPO_DIGEST = (
    "127.0.0.1:5000/cotcodec-past@"
    "sha256:fd26757a9c5915a6059f8016235a7bdb587e67234e8c739b9a8fb310843b8bb4"
)
PAST_ARCHIVE = Path(
    "/home/kevin/cotcodec-runs/past-bench/"
    "build-20260814-checkpoint-d4945b33-v1/image.tar"
)
PAST_ARCHIVE_SHA256 = "2f97fa8c18528eff8fd2e335e851255be280a20d2a3a81f74eab7485c0db285b"
PAST_SBOM = Path(
    "/home/kevin/cotcodec-runs/past-bench/"
    "sbom-20260814-checkpoint-ebcf7eea-v2/sbom.spdx.json"
)
PAST_SBOM_SHA256 = "37f7eb4eab884c7d924e718f9ed8389102a61fe43b36d48e29249996bf857fff"
PAST_SOURCE_REVISION = "f8223517ae7491e776b69793d9f11e9d074ab42e"
PAST_SOURCE_RECEIPT = "5e686206db8d1447d1b18d27bfffdd792f45c9d3418aedc7c15a5d134d6a6a5c"
PAST_RUNTIME_RECEIPT = "27fb11233ecb18bbdc60ca1c7c0100284b93c87b9fb5d07eb461d028bfd4a64d"

VLLM_IMAGE_ID = "sha256:f26809eb13339cbc59c3d0cc972f8c4997830dc8d2121cf18089cb122834e10d"
VLLM_REPO_DIGEST = (
    "docker.io/vllm/vllm-openai@"
    "sha256:f0b9a0dc75a9fca3b6811e3279367b2d6a448055a000bfd13859587d74cef268"
)
VLLM_ARCHIVE = Path(
    "/home/kevin/cotcodec-runs/past-bench/vllm-acquire-v0251-f0b9-v5/image.tar"
)
VLLM_ARCHIVE_SHA256 = "aecb8b90cd6378c1440c60efd3eef1d98d189e47110539350858dfde2ec9d0f4"
VLLM_ACQUISITION_RECEIPT = Path(
    "/home/kevin/cotcodec-runs/past-bench/"
    "vllm-acquire-v0251-f0b9-v5/acquisition-receipt.json"
)
VLLM_ACQUISITION_SHA256 = "ae800444ba8a1912cbe8932d2e6d54d68266a0dc6c6166739eae58b0db7c485b"
VLLM_SBOM = Path(
    "/home/kevin/cotcodec-runs/past-bench/vllm-sbom-v0251-f0b9-v3/sbom.spdx.json"
)
VLLM_SBOM_SHA256 = "3b87e628da75256fa7cfc0c33377af62707775a3606cf9be8c044e81952dcb48"
VLLM_SBOM_JOB_RECEIPT = Path(
    "/home/kevin/cotcodec-runs/past-bench/"
    "vllm-sbom-v0251-f0b9-v3/sbom-job-receipt.json"
)
VLLM_SBOM_JOB_RECEIPT_SHA256 = (
    "49ec867957af7c538eab7174e9e18698ff872adaf00936d5461f986ed6ab35ef"
)

MODEL_ROOT = Path(
    "/home/kevin/cotcodec-runs/past-bench/"
    "model-transport-qwen36-35b-c46153-v4/model-snapshot"
)
MODEL_RECEIPT = Path(
    "/home/kevin/cotcodec-runs/hf-cache/cotcodec-receipts/qwen3.6-35b-a3b.json"
)
MODEL_RECEIPT_SHA256 = "18c2a12881bf613c7110439b8e765ff89a4c060a1fb60aee62bb7250890ce1f9"
MODEL_ARTIFACT_ROOT = "8ac6d764b84034f4ed0df3f2388c9180afceab806f7e75f5d1e43a73bdd2736b"
MODEL_REVISION = "995ad96eacd98c81ed38be0c5b274b04031597b0"
MODEL_ID = "qwen3.6-35b-a3b"
MODEL_SNAPSHOT_RECEIPT = Path(
    "/home/kevin/cotcodec-runs/past-bench/model-transport-qwen36-35b-c46153-v4/"
    "private-model-snapshot-receipt.json"
)
MODEL_SNAPSHOT_RECEIPT_SHA256 = (
    "cf207899913f7efe2250599a9672fa6e9b8cec1e574c90d61372583cb2679910"
)

SEQUENCE_PATH = (
    "/opt/past-bench/source/configs/self_evolve_v2/"
    "hermes_self_evolve_v2_sm01_preference_adoption_only.yaml"
)
SEQUENCE_SHA256 = "6a311daff3ab1dc5f800ac0adb300f7b6ed5f6e37ba23d2f0b1e96516b719c60"
RUNTIME_CONFIG_PATH = "/tools/infra/research/past-bench/sm01-runtime.yaml"
RUNTIME_CONFIG_SHA256 = "0ddb0e8480b2f3005db4cf28b5b277736faafff8f0497b5658afe65a6fa2745a"
EXPECTED_TASK_IDS = [
    "SM01_COLD_001",
    "SM01_LEARN_A_001",
    "SM01_LEARN_B_001",
    "SM01_EVAL_NEAR_001",
    "SM01_EVAL_FAR_001",
    "SM01_CONTROL_002",
    "SM01_CONTROL_001",
    "SM01_CONTROL_003",
]
MODES = {"uninterrupted", "stop-after-episode-three", "fresh-job-resume"}
SHA256_RE = re.compile(r"[0-9a-f]{64}")


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_experiment(path: Path) -> tuple[dict[str, Any], str]:
    if not path.is_file() or path.is_symlink():
        raise ValueError("experiment must be a regular non-symlink YAML file")
    encoded = path.read_bytes()
    try:
        payload = yaml.safe_load(encoded)
    except yaml.YAMLError as exc:
        raise ValueError("experiment YAML is invalid") from exc
    if not isinstance(payload, dict):
        raise ValueError("experiment must contain one YAML object")
    expected = {
        "schema_version": 1,
        "name": "stage-b-past-sm01-checkpoint",
        "status": "registered-discovery-pilot-not-scientific-result",
        "scientific_result": False,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise ValueError(f"experiment field {key!r} drifted")
    source = payload.get("source") or {}
    agent = payload.get("agent") or {}
    model = payload.get("model") or {}
    recovery = payload.get("recovery") or {}
    execution = payload.get("execution") or {}
    if (
        source.get("revision") != PAST_SOURCE_REVISION
        or source.get("source_receipt_sha256") != PAST_SOURCE_RECEIPT
        or source.get("runtime_receipt_sha256") != PAST_RUNTIME_RECEIPT
        or source.get("sequence_sha256") != SEQUENCE_SHA256
        or source.get("expected_task_ids") != EXPECTED_TASK_IDS
        or source.get("episode_count") != 8
        or agent.get("runtime") != "local-inside-outer-container"
        or agent.get("runtime_config") != RUNTIME_CONFIG_PATH
        or agent.get("runtime_cache") != "/state/runtime_cache"
        or model.get("id") != MODEL_ID
        or model.get("revision") != MODEL_REVISION
        or model.get("receipt_sha256") != MODEL_RECEIPT_SHA256
        or model.get("artifact_root_sha256") != MODEL_ARTIFACT_ROOT
        or model.get("trust_remote_code") is not False
        or model.get("temperature") != 0.0
        or model.get("generation_config") != "vllm-defaults"
        or model.get("judge") != "disabled"
        or recovery.get("controlled_stop_after_episode") != 3
        or recovery.get("resume_job_must_be_fresh") is not True
        or execution.get("prior_failed_contained_runtime_gpu_hours") != 0.451111
        or execution.get("total_max_gpu_hours") != 7.5
        or execution.get("sudo") != "forbidden"
    ):
        raise ValueError("experiment scientific contract drifted")
    return payload, hashlib.sha256(encoded).hexdigest()


def validate_experiment_contract(path: Path) -> str:
    """Validate the exact registered PAST SM01 contract and return its file digest."""

    _, experiment_file_sha256 = _load_experiment(path)
    return experiment_file_sha256


def _logical_workload_argv() -> list[str]:
    return [
        "/opt/past-bench-venv/bin/past-bench",
        "evolve",
        "--sequence",
        SEQUENCE_PATH,
        "--agent",
        "hermes-plus",
        "--model",
        MODEL_ID,
        "--api-key",
        "cotcodec-internal-transport",
        "--base-url",
        "http://past-qwen:8000/v1",
        "--runtime",
        "local",
        "--config",
        RUNTIME_CONFIG_PATH,
        "--temperature",
        "0",
        "--trace-dir",
        "/outputs/traces",
        "--no-judge",
        "--compare-no-persistence",
        "--background-review-wait-s",
        "5.0",
        "--checkpoint-dir",
        "/outputs/checkpoints",
        "--checkpoint-identity",
        "/inputs/execution-identity.json",
    ]


def compile_manifest(args: argparse.Namespace) -> dict[str, Any]:
    experiment, experiment_file_sha256 = _load_experiment(args.experiment.resolve())
    mode = args.mode
    if mode not in MODES:
        raise ValueError("unsupported run mode")
    if not args.batch_script.is_file() or args.batch_script.is_symlink():
        raise ValueError("batch script must be a regular non-symlink file")
    predecessor: dict[str, Any] | None = None
    if mode == "fresh-job-resume":
        if (
            args.predecessor_job_id is None
            or args.predecessor_job_id <= 0
            or args.predecessor_checkpoint_sha256 is None
            or SHA256_RE.fullmatch(args.predecessor_checkpoint_sha256) is None
        ):
            raise ValueError("resume mode requires predecessor job and checkpoint digest")
        predecessor = {
            "slurm_job_id": args.predecessor_job_id,
            "checkpoint_pointer_sha256": args.predecessor_checkpoint_sha256,
        }
    elif args.predecessor_job_id is not None or args.predecessor_checkpoint_sha256 is not None:
        raise ValueError("predecessor fields are valid only for resume mode")

    budget_minutes = 30 if mode == "stop-after-episode-three" else 90
    max_gpu_hours = 1 if mode == "stop-after-episode-three" else 3
    logical_argv = _logical_workload_argv()
    execution_identity = {
        "source_revision": PAST_SOURCE_REVISION,
        "source_receipt_sha256": PAST_SOURCE_RECEIPT,
        "runtime_receipt_sha256": PAST_RUNTIME_RECEIPT,
        "image_id": PAST_IMAGE_ID,
        "sealed_sbom_sha256": PAST_SBOM_SHA256,
        "model_receipt_sha256": MODEL_RECEIPT_SHA256,
        "experiment_sha256": experiment_file_sha256,
        "argv": logical_argv,
    }
    server_argv = [
        "vllm",
        "serve",
        "/models/qwen3.6-35b-a3b",
        "--served-model-name",
        MODEL_ID,
        "--tensor-parallel-size",
        "2",
        "--dtype",
        "bfloat16",
        "--max-model-len",
        "32768",
        "--max-num-seqs",
        "1",
        "--seed",
        "42",
        "--enforce-eager",
        "--generation-config",
        "vllm",
        "--enable-auto-tool-choice",
        "--tool-call-parser",
        "qwen3_xml",
        "--chat-template",
        "/models/qwen3.6-35b-a3b/chat_template.jinja",
        "--default-chat-template-kwargs",
        '{"enable_thinking":false}',
        "--api-key",
        "cotcodec-internal-transport",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
    ]
    return {
        "schema_version": 1,
        "status": "COMPILED_PAST_SM01_CHECKPOINT_DISCOVERY_ONLY",
        "scientific_result": False,
        "publication_ready": False,
        "mode": mode,
        "experiment_file_sha256": experiment_file_sha256,
        "experiment_contract": experiment,
        "execution_identity": execution_identity,
        "logical_workload_argv": logical_argv,
        "actual_control_argv_suffix": (
            ["--stop-after-episode", "3"]
            if mode == "stop-after-episode-three"
            else ["--resume-checkpoint"]
            if mode == "fresh-job-resume"
            else []
        ),
        "predecessor": predecessor,
        "past": {
            "image_id": PAST_IMAGE_ID,
            "image_repo_digest": PAST_REPO_DIGEST,
            "image_archive_path": str(PAST_ARCHIVE),
            "image_archive_sha256": PAST_ARCHIVE_SHA256,
            "sbom_path": str(PAST_SBOM),
            "sbom_sha256": PAST_SBOM_SHA256,
        },
        "vllm": {
            "image_id": VLLM_IMAGE_ID,
            "image_repo_digest": VLLM_REPO_DIGEST,
            "image_archive_path": str(VLLM_ARCHIVE),
            "image_archive_sha256": VLLM_ARCHIVE_SHA256,
            "acquisition_receipt_path": str(VLLM_ACQUISITION_RECEIPT),
            "acquisition_receipt_sha256": VLLM_ACQUISITION_SHA256,
            "sbom_path": str(VLLM_SBOM),
            "sbom_sha256": VLLM_SBOM_SHA256,
            "sbom_job_receipt_path": str(VLLM_SBOM_JOB_RECEIPT),
            "sbom_job_receipt_sha256": VLLM_SBOM_JOB_RECEIPT_SHA256,
        },
        "model": {
            "id": MODEL_ID,
            "revision": MODEL_REVISION,
            "root": str(MODEL_ROOT),
            "receipt_path": str(MODEL_RECEIPT),
            "receipt_sha256": MODEL_RECEIPT_SHA256,
            "artifact_root_sha256": MODEL_ARTIFACT_ROOT,
            "trust_remote_code": False,
            "snapshot_receipt_path": str(MODEL_SNAPSHOT_RECEIPT),
            "snapshot_receipt_sha256": MODEL_SNAPSHOT_RECEIPT_SHA256,
        },
        "server_argv": server_argv,
        "runtime_config": {
            "path": RUNTIME_CONFIG_PATH,
            "sha256": RUNTIME_CONFIG_SHA256,
            "cache_dir": "/state/runtime_cache",
        },
        "sequence": {
            "path": SEQUENCE_PATH,
            "sha256": SEQUENCE_SHA256,
            "task_ids": EXPECTED_TASK_IDS,
        },
        "containment": {
            "scheduler": "slurm",
            "gpu_type": "H100",
            "gpus": 2,
            "docker_network": "internal-no-external-egress",
            "pull_at_runtime": False,
            "sudo": False,
        },
        "budget": {"minutes": budget_minutes, "max_gpu_hours": max_gpu_hours},
        "batch_script_sha256": _sha256(args.batch_script.resolve()),
        "compiler_sha256": _sha256(Path(__file__).resolve()),
    }


def _write_no_replace(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode() + b"\n"
    temporary = path.parent / f".{path.name}.{os.getpid()}.tmp"
    with temporary.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--mode", choices=sorted(MODES), required=True)
    parser.add_argument("--batch-script", type=Path, required=True)
    parser.add_argument("--predecessor-job-id", type=int)
    parser.add_argument("--predecessor-checkpoint-sha256")
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest = compile_manifest(args)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    unsigned = dict(manifest)
    manifest["manifest_sha256"] = hashlib.sha256(_canonical(unsigned)).hexdigest()
    _write_no_replace(args.output.resolve(), manifest)
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "mode": manifest["mode"],
                "manifest_sha256": manifest["manifest_sha256"],
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
