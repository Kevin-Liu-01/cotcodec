from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/compile_past_bench_model_transport.py"
SPEC = importlib.util.spec_from_file_location("compile_past_transport", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path) -> tuple[Path, str, Path, Path, Path, Path, Path, Path]:
    acquisition = tmp_path / "vllm"
    acquisition.mkdir()
    doctor = acquisition / "contained-import-doctor.json"
    doctor.write_text(
        json.dumps(
            {
                "cuda": "NVIDIA H100 80GB HBM3",
                "gpu_uuid": "GPU-aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "torch": "2.x",
                "vllm": "0.25.1",
            }
        ),
        encoding="utf-8",
    )
    receipt = {
        "schema_version": 1,
        "status": "PAST_VLLM_DISCOVERY_IMAGE_ACQUIRED_NOT_SCIENTIFIC_RESULT",
        "scientific_result": False,
        "publication_ready": False,
        "image_id": "sha256:" + "a" * 64,
        "image_repo_digest": MODULE.VLLM_IMAGE_REPO_DIGEST,
        "platform": "linux/amd64",
        "artifacts": {
            "contained-import-doctor.json": {
                "sha256": _sha256(doctor),
                "size": doctor.stat().st_size,
            },
            "image.tar": {"sha256": "", "size": 0},
        },
    }
    image_archive = acquisition / "image.tar"
    image_archive.write_text("vllm image", encoding="utf-8")
    receipt["artifacts"]["image.tar"] = {
        "sha256": _sha256(image_archive),
        "size": image_archive.stat().st_size,
    }
    acquisition_receipt = acquisition / "acquisition-receipt.json"
    acquisition_receipt.write_text(json.dumps(receipt), encoding="utf-8")

    model_root = tmp_path / "model"
    model_root.mkdir()
    chat_template = model_root / "chat_template.jinja"
    chat_template.write_text("tool template", encoding="utf-8")
    model_receipt = tmp_path / "model-receipt.json"
    model_receipt.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "model_id": MODULE.MODEL_ID,
                "backend": "huggingface",
                "repo_id": MODULE.MODEL_REPO_ID,
                "revision": MODULE.MODEL_REVISION,
                "mode": "full",
                "publication_eligible": True,
                "trust_remote_code": False,
                "artifact_root_sha256": MODULE.MODEL_ARTIFACT_ROOT_SHA256,
                "total_bytes": chat_template.stat().st_size,
                "files": [
                    {
                        "path": "chat_template.jinja",
                        "bytes": chat_template.stat().st_size,
                        "sha256": _sha256(chat_template),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    sbom = tmp_path / "past.spdx.json"
    sbom.write_text("sbom", encoding="utf-8")
    doctor = tmp_path / "doctor.py"
    doctor.write_text("print('doctor')\n", encoding="utf-8")
    batch = tmp_path / "transport.sbatch"
    batch.write_text("#!/bin/bash\n", encoding="utf-8")
    past_archive = tmp_path / "past-image.tar"
    past_archive.write_text("past image", encoding="utf-8")
    return (
        acquisition_receipt,
        _sha256(acquisition_receipt),
        model_root,
        model_receipt,
        sbom,
        doctor,
        batch,
        past_archive,
    )


def test_transport_manifest_binds_internal_native_tool_transport(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (
        acquisition,
        acquisition_sha,
        model_root,
        model_receipt,
        sbom,
        doctor,
        batch,
        past_archive,
    ) = _fixture(tmp_path)
    monkeypatch.setattr(MODULE, "MODEL_RECEIPT_SHA256", _sha256(model_receipt))
    monkeypatch.setattr(MODULE, "PAST_SBOM_SHA256", _sha256(sbom))
    monkeypatch.setattr(MODULE, "PAST_IMAGE_ARCHIVE_SHA256", _sha256(past_archive))
    args = MODULE.argparse.Namespace(
        past_sbom=sbom,
        past_image_archive=past_archive,
        vllm_acquisition_receipt=acquisition,
        vllm_acquisition_sha256=acquisition_sha,
        model_root=model_root,
        model_receipt=model_receipt,
        transport_doctor=doctor,
        batch_script=batch,
    )
    manifest = MODULE.compile_manifest(args)
    assert manifest["vllm"]["image_repo_digest"] == MODULE.VLLM_IMAGE_REPO_DIGEST
    assert manifest["server"]["tool_call_parser"] == "qwen3_xml"
    assert "--enable-auto-tool-choice" in manifest["server"]["argv"]
    assert "--enforce-eager" in manifest["server"]["argv"]
    assert manifest["containment"]["external_egress"] is False
    assert manifest["containment"]["docker_network"] == "internal-only-no-host-port"
    assert manifest["model"]["trust_remote_code"] is False
    assert manifest["execution_tools"]["transport_doctor_sha256"] == _sha256(doctor)
    assert manifest["execution_tools"]["batch_script_sha256"] == _sha256(batch)
    assert manifest["past"]["image_archive_sha256"] == _sha256(past_archive)
    assert manifest["vllm"]["image_archive_path"].endswith("/image.tar")


def test_transport_manifest_rejects_forged_acquisition_doctor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (
        acquisition,
        acquisition_sha,
        model_root,
        model_receipt,
        sbom,
        doctor,
        batch,
        past_archive,
    ) = _fixture(tmp_path)
    monkeypatch.setattr(MODULE, "MODEL_RECEIPT_SHA256", _sha256(model_receipt))
    monkeypatch.setattr(MODULE, "PAST_SBOM_SHA256", _sha256(sbom))
    monkeypatch.setattr(MODULE, "PAST_IMAGE_ARCHIVE_SHA256", _sha256(past_archive))
    doctor = acquisition.parent / "contained-import-doctor.json"
    doctor.write_text(json.dumps({"cuda": "CPU", "vllm": "0.25.1"}), encoding="utf-8")
    args = MODULE.argparse.Namespace(
        past_sbom=sbom,
        past_image_archive=past_archive,
        vllm_acquisition_receipt=acquisition,
        vllm_acquisition_sha256=acquisition_sha,
        model_root=model_root,
        model_receipt=model_receipt,
        transport_doctor=doctor,
        batch_script=batch,
    )
    with pytest.raises(MODULE.TransportManifestError):
        MODULE.compile_manifest(args)
