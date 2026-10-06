#!/usr/bin/env python3
"""Compile one fail-closed PAST-Bench/Qwen internal model transport manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

PAST_IMAGE_ID = "sha256:ebcf7eea7f1977f03e5e007edf265fcd120edadcd6d48e81f63df70715783150"
PAST_IMAGE_REPO_DIGEST = (
    "127.0.0.1:5000/cotcodec-past@"
    "sha256:fd26757a9c5915a6059f8016235a7bdb587e67234e8c739b9a8fb310843b8bb4"
)
PAST_SOURCE_RECEIPT_SHA256 = (
    "5e686206db8d1447d1b18d27bfffdd792f45c9d3418aedc7c15a5d134d6a6a5c"
)
PAST_RUNTIME_RECEIPT_SHA256 = (
    "27fb11233ecb18bbdc60ca1c7c0100284b93c87b9fb5d07eb461d028bfd4a64d"
)
PAST_SBOM_SHA256 = "37f7eb4eab884c7d924e718f9ed8389102a61fe43b36d48e29249996bf857fff"
PAST_IMAGE_ARCHIVE_SHA256 = (
    "2f97fa8c18528eff8fd2e335e851255be280a20d2a3a81f74eab7485c0db285b"
)

VLLM_IMAGE_REPO_DIGEST = (
    "docker.io/vllm/vllm-openai@"
    "sha256:f0b9a0dc75a9fca3b6811e3279367b2d6a448055a000bfd13859587d74cef268"
)
VLLM_VERSION = "0.25.1"

MODEL_ID = "qwen3.6-35b-a3b"
MODEL_REPO_ID = "Qwen/Qwen3.6-35B-A3B"
MODEL_REVISION = "995ad96eacd98c81ed38be0c5b274b04031597b0"
MODEL_RECEIPT_SHA256 = (
    "18c2a12881bf613c7110439b8e765ff89a4c060a1fb60aee62bb7250890ce1f9"
)
MODEL_ARTIFACT_ROOT_SHA256 = (
    "8ac6d764b84034f4ed0df3f2388c9180afceab806f7e75f5d1e43a73bdd2736b"
)


class TransportManifestError(ValueError):
    """Raised when an input cannot support the registered transport doctor."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _regular_file(path: Path, *, expected_sha256: str | None = None) -> Path:
    resolved = path.resolve(strict=True)
    if path.is_symlink() or not resolved.is_file():
        raise TransportManifestError(f"input must be a regular non-symlink file: {path}")
    if expected_sha256 is not None and _sha256(resolved) != expected_sha256:
        raise TransportManifestError(f"input digest mismatch: {path}")
    return resolved


def _load_json(path: Path, *, expected_sha256: str | None = None) -> tuple[Path, dict[str, Any]]:
    resolved = _regular_file(path, expected_sha256=expected_sha256)
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TransportManifestError(f"input is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise TransportManifestError(f"input JSON must be an object: {path}")
    return resolved, payload


def _validate_acquisition(receipt_path: Path, expected_sha256: str) -> dict[str, Any]:
    receipt_path, receipt = _load_json(receipt_path, expected_sha256=expected_sha256)
    expected = {
        "schema_version": 1,
        "status": "PAST_VLLM_DISCOVERY_IMAGE_ACQUIRED_NOT_SCIENTIFIC_RESULT",
        "scientific_result": False,
        "publication_ready": False,
        "image_repo_digest": VLLM_IMAGE_REPO_DIGEST,
        "platform": "linux/amd64",
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise TransportManifestError(f"vLLM acquisition field {key!r} is invalid")
    image_id = receipt.get("image_id")
    if not isinstance(image_id, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
        raise TransportManifestError("vLLM acquisition image ID is invalid")
    artifacts = receipt.get("artifacts")
    if not isinstance(artifacts, dict):
        raise TransportManifestError("vLLM acquisition artifact map is missing")
    doctor_entry = artifacts.get("contained-import-doctor.json")
    archive_entry = artifacts.get("image.tar")
    if not isinstance(doctor_entry, dict):
        raise TransportManifestError("vLLM import doctor receipt is missing")
    if not isinstance(archive_entry, dict):
        raise TransportManifestError("vLLM image archive receipt is missing")
    doctor_path = receipt_path.parent / "contained-import-doctor.json"
    doctor_path, doctor = _load_json(
        doctor_path,
        expected_sha256=str(doctor_entry.get("sha256") or ""),
    )
    if (
        doctor.get("vllm") != VLLM_VERSION
        or "H100" not in str(doctor.get("cuda") or "")
        or not re.fullmatch(r"GPU-[A-Fa-f0-9-]{16,80}", str(doctor.get("gpu_uuid") or ""))
    ):
        raise TransportManifestError("vLLM import doctor did not bind v0.25.1 on H100")
    archive_path = _regular_file(
        receipt_path.parent / "image.tar",
        expected_sha256=str(archive_entry.get("sha256") or ""),
    )
    return {
        "receipt_path": str(receipt_path),
        "receipt_sha256": expected_sha256,
        "image_id": image_id,
        "image_repo_digest": VLLM_IMAGE_REPO_DIGEST,
        "version": VLLM_VERSION,
        "import_doctor_path": str(doctor_path),
        "import_doctor_sha256": str(doctor_entry["sha256"]),
        "image_archive_path": str(archive_path),
        "image_archive_sha256": str(archive_entry["sha256"]),
    }


def _validate_model(receipt_path: Path, expected_sha256: str, model_root: Path) -> dict[str, Any]:
    receipt_path, receipt = _load_json(receipt_path, expected_sha256=expected_sha256)
    expected = {
        "schema_version": 1,
        "model_id": MODEL_ID,
        "backend": "huggingface",
        "repo_id": MODEL_REPO_ID,
        "revision": MODEL_REVISION,
        "mode": "full",
        "publication_eligible": True,
        "trust_remote_code": False,
        "artifact_root_sha256": MODEL_ARTIFACT_ROOT_SHA256,
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise TransportManifestError(f"model receipt field {key!r} is invalid")
    if model_root.is_symlink():
        raise TransportManifestError("model root must be a regular non-symlink directory")
    model_root = model_root.resolve(strict=True)
    if not model_root.is_dir():
        raise TransportManifestError("model root must be a directory")
    files = receipt.get("files")
    if not isinstance(files, list) or not files:
        raise TransportManifestError("model receipt file roster is missing")
    chat_template = next(
        (item for item in files if item.get("path") == "chat_template.jinja"),
        None,
    )
    if not isinstance(chat_template, dict) or not re.fullmatch(
        r"[0-9a-f]{64}", str(chat_template.get("sha256") or "")
    ):
        raise TransportManifestError("model receipt does not bind chat_template.jinja")
    return {
        "model_id": MODEL_ID,
        "repo_id": MODEL_REPO_ID,
        "revision": MODEL_REVISION,
        "root": str(model_root),
        "receipt_path": str(receipt_path),
        "receipt_sha256": expected_sha256,
        "artifact_root_sha256": MODEL_ARTIFACT_ROOT_SHA256,
        "total_bytes": receipt.get("total_bytes"),
        "file_count": len(files),
        "chat_template_sha256": str(chat_template["sha256"]),
        "trust_remote_code": False,
    }


def compile_manifest(args: argparse.Namespace) -> dict[str, Any]:
    sbom_path = _regular_file(args.past_sbom, expected_sha256=PAST_SBOM_SHA256)
    past_image_archive = _regular_file(
        args.past_image_archive,
        expected_sha256=PAST_IMAGE_ARCHIVE_SHA256,
    )
    doctor_path = _regular_file(args.transport_doctor)
    batch_path = _regular_file(args.batch_script)
    vllm = _validate_acquisition(args.vllm_acquisition_receipt, args.vllm_acquisition_sha256)
    model = _validate_model(args.model_receipt, MODEL_RECEIPT_SHA256, args.model_root)
    model_mount = f"/models/{MODEL_ID}"
    server_argv = [
        "vllm",
        "serve",
        model_mount,
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
        "--enable-auto-tool-choice",
        "--tool-call-parser",
        "qwen3_xml",
        "--chat-template",
        f"{model_mount}/chat_template.jinja",
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
        "status": "COMPILED_PAST_QWEN_INTERNAL_TRANSPORT_DISCOVERY_ONLY",
        "scientific_result": False,
        "publication_ready": False,
        "past": {
            "image_id": PAST_IMAGE_ID,
            "image_repo_digest": PAST_IMAGE_REPO_DIGEST,
            "source_receipt_sha256": PAST_SOURCE_RECEIPT_SHA256,
            "runtime_receipt_sha256": PAST_RUNTIME_RECEIPT_SHA256,
            "image_archive_path": str(past_image_archive),
            "image_archive_sha256": PAST_IMAGE_ARCHIVE_SHA256,
            "sbom_path": str(sbom_path),
            "sbom_sha256": PAST_SBOM_SHA256,
        },
        "vllm": vllm,
        "model": model,
        "server": {
            "argv": server_argv,
            "api_base": "http://past-qwen:8000/v1",
            "api_key_kind": "fixed-nonsecret-internal-token",
            "tool_call_parser": "qwen3_xml",
            "chat_template_sha256": model["chat_template_sha256"],
            "enable_thinking": False,
            "temperature": 0.0,
            "streaming_probe_required": True,
            "nonstreaming_probe_required": True,
        },
        "execution_tools": {
            "transport_doctor_path": str(doctor_path),
            "transport_doctor_sha256": _sha256(doctor_path),
            "batch_script_path": str(batch_path),
            "batch_script_sha256": _sha256(batch_path),
        },
        "containment": {
            "scheduler": "slurm",
            "gpu_type": "H100",
            "gpus": 2,
            "docker_network": "internal-only-no-host-port",
            "external_egress": False,
            "pull_at_runtime": False,
            "model_mount": "read-only",
            "past_rootfs": "read-only",
            "vllm_rootfs": "read-only",
        },
        "budget": {"minutes": 120, "max_gpu_hours": 4},
        "gates": [
            "full model receipt byte verification inside the vLLM image",
            "exact two-H100 visibility inside the model server",
            "internal-network health and model identity",
            "blocked external egress from both containers",
            "native OpenAI tool_calls for non-streaming and streaming forced-tool probes",
            "semantic A/A equality across two greedy requests",
        ],
        "compiler_sha256": _sha256(Path(__file__).resolve()),
    }


def _write_no_replace(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
    parser.add_argument("--past-sbom", type=Path, required=True)
    parser.add_argument("--past-image-archive", type=Path, required=True)
    parser.add_argument("--vllm-acquisition-receipt", type=Path, required=True)
    parser.add_argument("--vllm-acquisition-sha256", required=True)
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--model-receipt", type=Path, required=True)
    parser.add_argument("--transport-doctor", type=Path, required=True)
    parser.add_argument("--batch-script", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = compile_manifest(args)
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    manifest["manifest_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    _write_no_replace(
        args.output.resolve(),
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False).encode() + b"\n",
    )
    print(
        json.dumps(
            {
                "manifest_sha256": manifest["manifest_sha256"],
                "status": manifest["status"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
