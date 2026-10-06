#!/usr/bin/env python3
"""Validate the contained ReasoningBank frozen-bank CPU doctor contract."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials.schema import canonical_json, sha256_text  # noqa: E402
from scripts.run_reasoningbank_frozen_bank_container import (  # noqa: E402
    ContainerDoctorError,
    _validate_outputs,
)

DEFAULT_EXPERIMENT = (
    PROJECT_ROOT
    / "experiments/memory/stage3-reasoningbank-frozen-bank-cpu-doctor.yaml"
)
EXPECTED_EVIDENCE_PATH = (
    PROJECT_ROOT / "research/evidence/memory/reasoningbank-frozen-bank-cpu-v1.json"
)
EXPECTED_EVIDENCE_SHA256 = (
    "c6f6d6284bcbd9afd8bb0d5e4658b2b892d9679a3614fa4a10169a878c98c994"
)
EXPECTED_STATUS = "FROZEN_PROCEDURAL_BANK_CPU_DOCTOR_PASS"
EXPECTED_IMAGE_ID = (
    "sha256:d3f7858e55209cd3af46b97e21aafcb8e0675ee59a64a787589ee2679f283430"
)
EXPECTED_CORE_FILES = {
    "bank.json": "99be19f00089e05463f4a025b57c48ced82e06b4805e1bbbfd11010c1d81f874",
    "fixture-source-artifacts.jsonl": (
        "2891c295e87564fdd967da30f875d47f9674724b281d1f938e3745ec85e4b12f"
    ),
    "manifest.json": "6270ee3c2687911d44a1cb6b4e76943325f632adeb1bc0b0a6908bd9c6a25c98",
    "report.json": "b6fcd4450bb62fa58902c3bce94016099ad42a33dfb30ca284078f0caec57c98",
    "retrievals.jsonl": (
        "3c88c94f65ef8a97ad9b47e7450f515023012b7b7a633a07e6c322e43cc6bbbe"
    ),
}
EXPECTED_RETAINED_ROOT = (
    PROJECT_ROOT
    / "research/evidence/memory/reasoningbank-frozen-bank-cpu-v1-artifacts"
)
EXPECTED_CODE_SHA256 = (
    "5bcc1cbc873c33fb49d1061daf7b829f872112b3bbb93d4ce9c9db092a920ce8"
)
EXPECTED_BANK_SHA256 = (
    "4d6c4456c2e4c1c95419c14c72bea60f7994fa460cdfa9b994e0e60b605d1f14"
)
EXPECTED_SPLIT_SHA256 = (
    "e24f57a0279441f26fa863ff854bbd872a6e9bbb1a8ad89d60d23dd7e4fb535c"
)


class ReasoningBankFrozenBankExperimentError(ValueError):
    """Raised when the frozen-bank CPU contract or evidence drifts."""


def _sha_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _mapping(payload: dict[str, Any], field: str) -> dict[str, Any]:
    value = payload.get(field)
    if not isinstance(value, dict):
        raise ReasoningBankFrozenBankExperimentError(f"{field} must be a mapping")
    return value


def _load_json_object(path: Path, owner: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ReasoningBankFrozenBankExperimentError(f"{owner} is not a regular file")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReasoningBankFrozenBankExperimentError(f"{owner} is invalid") from exc
    if not isinstance(payload, dict):
        raise ReasoningBankFrozenBankExperimentError(f"{owner} must be a mapping")
    return payload


def _verify_retained_artifacts(payload: dict[str, Any]) -> None:
    declared_root = payload.get("retained_artifact_root")
    if declared_root != str(EXPECTED_RETAINED_ROOT.relative_to(PROJECT_ROOT)):
        raise ReasoningBankFrozenBankExperimentError("retained artifact root drifted")
    if EXPECTED_RETAINED_ROOT.is_symlink() or not EXPECTED_RETAINED_ROOT.is_dir():
        raise ReasoningBankFrozenBankExperimentError("retained artifact root is absent")
    core_root = EXPECTED_RETAINED_ROOT / "core"
    receipt_root = EXPECTED_RETAINED_ROOT / "model-receipts"
    try:
        core_hashes = _validate_outputs(core_root, receipt_root=receipt_root)
    except (ContainerDoctorError, OSError, ValueError) as exc:
        raise ReasoningBankFrozenBankExperimentError(
            "retained core artifacts are invalid"
        ) from exc
    if core_hashes != EXPECTED_CORE_FILES:
        raise ReasoningBankFrozenBankExperimentError("retained core artifacts drifted")
    receipt_names = {path.name for path in receipt_root.iterdir()}
    if receipt_names != {"bge-small-en-v1.5.json"}:
        raise ReasoningBankFrozenBankExperimentError("retained model receipt roster drifted")
    runs = payload.get("runs")
    if not isinstance(runs, list) or len(runs) != 2:
        raise ReasoningBankFrozenBankExperimentError("evidence run roster drifted")
    expected_run_ids = {
        "2026-08-15-cpu-doctor-v9-sealed": "v9",
        "2026-08-15-cpu-doctor-v10-sealed": "v10",
    }
    if {row.get("run_id") for row in runs if isinstance(row, dict)} != set(
        expected_run_ids
    ):
        raise ReasoningBankFrozenBankExperimentError("evidence run IDs drifted")
    for row in runs:
        if not isinstance(row, dict):
            raise ReasoningBankFrozenBankExperimentError("evidence run row is invalid")
        run_id = row["run_id"]
        retained = EXPECTED_RETAINED_ROOT / expected_run_ids[run_id]
        if row.get("retained_artifact_root") != str(retained.relative_to(PROJECT_ROOT)):
            raise ReasoningBankFrozenBankExperimentError("retained run root drifted")
        if retained.is_symlink() or not retained.is_dir() or {
            path.name for path in retained.iterdir()
        } != {"execution-receipt.json", "container-inspect.json", "image-inspect.json"}:
            raise ReasoningBankFrozenBankExperimentError("retained run roster drifted")
        receipt_path = retained / "execution-receipt.json"
        container_path = retained / "container-inspect.json"
        image_path = retained / "image-inspect.json"
        if (
            _sha_path(receipt_path) != row.get("execution_receipt_file_sha256")
            or _sha_path(container_path) != row.get("container_inspect_sha256")
            or _sha_path(image_path)
            != payload.get("image", {}).get("image_inspect_sha256")
        ):
            raise ReasoningBankFrozenBankExperimentError("retained run file hash drifted")
        receipt = _load_json_object(receipt_path, "execution receipt")
        receipt_unsigned = {
            key: value for key, value in receipt.items() if key != "receipt_sha256"
        }
        if (
            receipt.get("receipt_sha256") != row.get("execution_receipt_sha256")
            or receipt.get("receipt_sha256")
            != sha256_text(canonical_json(receipt_unsigned))
            or receipt.get("status") != EXPECTED_STATUS
            or receipt.get("scientific_result") is not False
            or receipt.get("publication_ready") is not False
            or receipt.get("image_id") != EXPECTED_IMAGE_ID
            or receipt.get("core_files") != EXPECTED_CORE_FILES
            or receipt.get("stopped_contract", {}).get("exit_code") != 0
            or receipt.get("stopped_contract", {}).get("oom_killed") is not False
        ):
            raise ReasoningBankFrozenBankExperimentError("execution receipt drifted")
        container_inspect = json.loads(container_path.read_text(encoding="utf-8"))
        image_inspect = json.loads(image_path.read_text(encoding="utf-8"))
        if (
            not isinstance(container_inspect, dict)
            or container_inspect.get("Image") != EXPECTED_IMAGE_ID
            or container_inspect.get("State", {}).get("ExitCode") != 0
            or container_inspect.get("State", {}).get("OOMKilled") is not False
            or not isinstance(image_inspect, dict)
            or image_inspect.get("Id") != EXPECTED_IMAGE_ID
        ):
            raise ReasoningBankFrozenBankExperimentError("retained Docker inspect drifted")


def _load_evidence() -> dict[str, Any]:
    if (
        EXPECTED_EVIDENCE_PATH.is_symlink()
        or not EXPECTED_EVIDENCE_PATH.is_file()
        or _sha_path(EXPECTED_EVIDENCE_PATH) != EXPECTED_EVIDENCE_SHA256
    ):
        raise ReasoningBankFrozenBankExperimentError("evidence file drifted")
    try:
        payload = json.loads(EXPECTED_EVIDENCE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReasoningBankFrozenBankExperimentError("evidence file is invalid") from exc
    if not isinstance(payload, dict):
        raise ReasoningBankFrozenBankExperimentError("evidence must be a mapping")
    if (
        payload.get("status") != EXPECTED_STATUS
        or payload.get("scientific_result") is not False
        or payload.get("publication_ready") is not False
        or payload.get("two_fresh_runs_core_byte_identical") is not True
        or payload.get("exact_core_files") != EXPECTED_CORE_FILES
        or payload.get("image", {}).get("image_id") != EXPECTED_IMAGE_ID
    ):
        raise ReasoningBankFrozenBankExperimentError("evidence contract drifted")
    result = _mapping(payload, "contract_result")
    if (
        result.get("bank_artifact_sha256") != EXPECTED_BANK_SHA256
        or result.get("split_manifest_sha256") != EXPECTED_SPLIT_SHA256
        or result.get("fixture_source_artifacts") != 6
        or result.get("fixture_receipts_only") is not True
        or result.get("real_reasoningbank_trajectories_present") is not False
        or result.get("document_text_field") != "procedural_text"
    ):
        raise ReasoningBankFrozenBankExperimentError("evidence result scope drifted")
    _verify_retained_artifacts(payload)
    return payload


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ReasoningBankFrozenBankExperimentError(
            f"cannot load frozen-bank experiment: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise ReasoningBankFrozenBankExperimentError("experiment must be a mapping")
    if (
        payload.get("schema_version") != 1
        or payload.get("name") != "stage3-reasoningbank-frozen-bank-cpu-doctor"
        or payload.get("status") != "contained-cpu-contract-pass"
        or payload.get("scientific_result") is not False
        or payload.get("publication_ready") is not False
        or payload.get("protocol") != "frozen-procedural-bank-v1"
    ):
        raise ReasoningBankFrozenBankExperimentError("experiment identity drifted")
    source = _mapping(payload, "source")
    if source != {
        "source_id": "reasoningbank",
        "repository": "https://github.com/google-research/reasoning-bank",
        "revision": "ed80611788292ea739f1effd31f16c53823b8a0d",
        "tree": "7cc5e6e08ee8035cde81f1fb9fd871d32423a3e3",
        "git_archive_tar_sha256": (
            "d85d169c84f82782cefc50044adc192ab1d28956f36e177de0bf213d48298e09"
        ),
        "license": "Apache-2.0",
    }:
        raise ReasoningBankFrozenBankExperimentError("source contract drifted")
    model = _mapping(payload, "model")
    if (
        model.get("model_id") != "bge-small-en-v1.5"
        or model.get("revision") != "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"
        or model.get("artifact_root_sha256")
        != "85a178e1c7da2659a137728e9b6794f97a2607adfa315e3ee0eeb0f5cc497883"
        or model.get("model_receipt_sha256")
        != "9d30a2f1646e5e7b1d99db79232ca29ba727ae238736d02f95ea4270ca63926e"
        or model.get("trust_remote_code") is not False
    ):
        raise ReasoningBankFrozenBankExperimentError("model contract drifted")
    contract = _mapping(payload, "contract")
    if contract.get("document_embedding_field") != "procedural_text":
        raise ReasoningBankFrozenBankExperimentError(
            "document embedding field drifted"
        )
    runtime = _mapping(payload, "runtime")
    if (
        runtime.get("image_id") != EXPECTED_IMAGE_ID
        or runtime.get("image_code_sha256") != EXPECTED_CODE_SHA256
        or runtime.get("network") != "none"
        or runtime.get("read_only_rootfs") is not True
        or runtime.get("cap_drop") != ["ALL"]
        or runtime.get("security_opt") != ["no-new-privileges"]
        or runtime.get("model_mount") != "read-only"
        or runtime.get("receipt_mount") != "read-only"
        or runtime.get("gpus") != 0
        or runtime.get("api_calls") != 0
        or runtime.get("sudo") != "forbidden"
    ):
        raise ReasoningBankFrozenBankExperimentError("runtime contract drifted")
    gates = _mapping(payload, "gates")
    if gates != {
        "required_status": EXPECTED_STATUS,
        "train_items": 6,
        "evaluation_queries": 6,
        "top_one_correct": 6,
        "repeated_bank_freeze_exact": True,
        "repeated_retrieval_exact": True,
        "retrieval_bank_immutable": True,
        "train_task_leakage_rejected": True,
        "task_family_mismatch_rejected": True,
        "two_fresh_runs_core_byte_identical": True,
    }:
        raise ReasoningBankFrozenBankExperimentError("doctor gates drifted")
    evidence = _mapping(payload, "evidence")
    if (
        evidence.get("path")
        != "research/evidence/memory/reasoningbank-frozen-bank-cpu-v1.json"
        or evidence.get("sha256") != EXPECTED_EVIDENCE_SHA256
        or evidence.get("retained_artifact_root")
        != str(EXPECTED_RETAINED_ROOT.relative_to(PROJECT_ROOT))
        or evidence.get("bank_artifact_sha256") != EXPECTED_BANK_SHA256
        or evidence.get("split_manifest_sha256") != EXPECTED_SPLIT_SHA256
        or evidence.get("core_files") != EXPECTED_CORE_FILES
    ):
        raise ReasoningBankFrozenBankExperimentError("evidence binding drifted")
    admission = _mapping(payload, "admission")
    if (
        admission.get("patch_contract") != "pass"
        or admission.get("release_driver")
        != "BLOCKED_MUTABLE_EVALUATION_AND_UNPINNED_RETRIEVAL"
        or admission.get("h100_admission") != "blocked"
    ):
        raise ReasoningBankFrozenBankExperimentError("admission contract drifted")
    _load_evidence()
    return payload


def main() -> int:
    validate_experiment_contract()
    print("ReasoningBank frozen-bank CPU contract PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
