#!/usr/bin/env python3
"""Validate the sealed Mnemon static-space H100 negative and exact resume."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

EXPECTED_SOURCE_ID = "mnemon"
EXPECTED_STATUS = "MNEMON_STATIC_ROUTING_KILLED"
EXPECTED_SOURCE_SHA256 = "3b61ce38f314765850633a91c6f0900c9c229551f5866898af9309910a8c1cad"
EXPECTED_SOURCE_RECEIPT_SHA256 = "2e3aed5b02e146b1c3e21e6f5f3ca05ebe03089886609eefba4843b644efe390"
EXPECTED_IMAGE_ID = "sha256:d9ca96642e4c6621500d3c6f605ce3a613414bd5ae64b1907f0b2675cf8a51bb"
EXPECTED_GIT_SHA = "581ded8df71564b0212d8af5dcd401257aa6a28f"
EXPECTED_GIT_TREE = "5a83330044fda59e998e09c18266ad6f99a84bce"
EXPECTED_BATCH_SHA256 = "eee81e32e4b077ca056710cdbb1b7bc46401f566a3b46383dd7e06242248cda8"
EXPECTED_PANEL_SHA256 = "43a416c62be619de641aa60ecefc83ad0efdd605f7f13fd8821936704acacee5"
EXPECTED_EXPERIMENT_SHA256 = "70cde8cddc729f57063f45b77b254ba86f6cde0018062d4be75885d9e0039b04"
EXPECTED_MODEL = {
    "artifact_root_sha256": "3b8a075149bffe4dea784db5b4b37bc0896688cba0b3de7d8d0f6e8ae6157b9e",
    "model_id": "qwen3.5-4b",
    "receipt_sha256": "75ebfc531acdcbc0c39bbf83ee7bf5267a3ddf02c4fafdf6181624612a0d3082",
    "revision": "851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a",
}
EXPECTED_REVISIONS = {
    "https://github.com/mnemon-dev/mnemon": "88d2981edeb18a5ebe048af472f6f96527615454",
    "https://github.com/omdsh-dev/dsh-mnemon": "1889c68400e52a391ee9a6eedf15bf44bc39dd06",
}
EXPECTED_GATES = {
    "actor_aa_exact": True,
    "completion_nonempty": True,
    "lexical_beats_all_spaces": False,
    "lexical_beats_no_memory": True,
    "lexical_equals_oracle": True,
    "lexical_exact_minimum": True,
    "matched_nonempty_prompt_budget": False,
}
EXPECTED_CLAIM_BOUNDARY = {
    "h100_actor_admission": "forbidden-for-this-revision",
    "learned_paging_evaluated": False,
    "larger_model_admission": "forbidden-by-registered-kill-screen",
    "physical_erasure_evaluated": False,
    "static_space_answer_quality_lift": False,
}
ACTOR_FILES = {
    "checkpoint.json",
    "manifest.json",
    "panel.json",
    "predictions.jsonl",
    "report.json",
}
COMMON_JOB_FILES = {
    "command.json",
    "container-created-inspect.json",
    "container-doctor.txt",
    "container-final-inspect.json",
    "docker-research.sbatch",
    "image-inspect.json",
    "job.env",
    "manifest.json",
    "model-receipt.json",
    "model-verification.txt",
    "provenance-verification.txt",
    "study-artifact.json",
    "system.txt",
    "termination.env",
}
EXPECTED_ARTIFACT_ROSTER = {
    *(f"job-313/{name}" for name in COMMON_JOB_FILES),
    *(f"job-313/mnemon-actor/{name}" for name in ACTOR_FILES),
    "job-313/slurm-313.out",
    *(f"job-315/{name}" for name in COMMON_JOB_FILES),
    *(f"job-315/mnemon-actor/{name}" for name in ACTOR_FILES),
    "job-315/resume-receipt.json",
    "job-315/slurm-315.out",
}


class MnemonH100EvidenceError(ValueError):
    """Raised when the sealed Mnemon H100 evidence drifts."""


def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _object(value: bytes, *, owner: str) -> dict[str, Any]:
    def reject(constant: str) -> None:
        raise MnemonH100EvidenceError(f"{owner}: non-finite JSON {constant}")

    try:
        parsed = json.loads(value, parse_constant=reject)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise MnemonH100EvidenceError(f"{owner}: invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise MnemonH100EvidenceError(f"{owner}: expected one JSON object")
    return parsed


def _env(value: bytes, *, owner: str) -> dict[str, str]:
    try:
        lines = value.decode().splitlines()
    except UnicodeDecodeError as exc:
        raise MnemonH100EvidenceError(f"{owner}: invalid UTF-8") from exc
    result: dict[str, str] = {}
    for line in lines:
        key, separator, field = line.partition("=")
        if not separator or not key or key in result:
            raise MnemonH100EvidenceError(f"{owner}: malformed environment receipt")
        result[key] = field
    return result


def _safe_file(project_root: Path, value: Any, *, owner: str) -> Path:
    if (
        not isinstance(value, str)
        or not value
        or Path(value).is_absolute()
        or ".." in Path(value).parts
    ):
        raise MnemonH100EvidenceError(f"{owner}: unsafe path")
    path = project_root / value
    if path.is_symlink() or not path.is_file():
        raise MnemonH100EvidenceError(f"{owner}: missing or non-regular path")
    return path


def _artifacts(bundle: dict[str, Any], project_root: Path) -> dict[str, bytes]:
    root_value = bundle.get("artifact_root")
    if (
        not isinstance(root_value, str)
        or not root_value
        or Path(root_value).is_absolute()
        or ".." in Path(root_value).parts
    ):
        raise MnemonH100EvidenceError("artifact root is unsafe")
    root = project_root / root_value
    receipts = bundle.get("artifact_files")
    if not isinstance(receipts, dict) or set(receipts) != EXPECTED_ARTIFACT_ROSTER:
        raise MnemonH100EvidenceError("artifact roster drifted")
    result: dict[str, bytes] = {}
    for name, expected in receipts.items():
        path = root / name
        if (
            not isinstance(expected, str)
            or len(expected) != 64
            or path.is_symlink()
            or not path.is_file()
        ):
            raise MnemonH100EvidenceError(f"artifact {name} is invalid")
        value = path.read_bytes()
        if _sha256(value) != expected:
            raise MnemonH100EvidenceError(f"artifact {name} drifted")
        result[name] = value
    return result


def _validate_source(bundle: dict[str, Any], project_root: Path) -> None:
    archive = _safe_file(project_root, bundle.get("source_archive_path"), owner="source archive")
    receipt_path = _safe_file(
        project_root,
        bundle.get("source_receipt_path"),
        owner="source receipt",
    )
    if (
        _sha256(archive.read_bytes()) != EXPECTED_SOURCE_SHA256
        or bundle.get("source_archive_sha256") != EXPECTED_SOURCE_SHA256
        or _sha256(receipt_path.read_bytes()) != EXPECTED_SOURCE_RECEIPT_SHA256
        or bundle.get("source_receipt_sha256") != EXPECTED_SOURCE_RECEIPT_SHA256
    ):
        raise MnemonH100EvidenceError("source evidence digest drifted")
    receipt = _object(receipt_path.read_bytes(), owner="source receipt")
    if (
        receipt.get("schema_version") != 2
        or receipt.get("mode") != "discovery"
        or receipt.get("archive_sha256") != EXPECTED_SOURCE_SHA256
        or receipt.get("git_sha") != EXPECTED_GIT_SHA
        or receipt.get("git_tree") != EXPECTED_GIT_TREE
        or receipt.get("worktree_clean") is not False
        or receipt.get("data_excluded") is not True
    ):
        raise MnemonH100EvidenceError("source receipt semantics drifted")


def _validate_journal(panel: dict[str, Any], predictions: bytes) -> None:
    items = panel.get("items")
    arms = panel.get("arms")
    if not isinstance(items, list) or len(items) != 32 or not isinstance(arms, list):
        raise MnemonH100EvidenceError("panel roster drifted")
    expected = [
        (item.get("task_id"), arm)
        for item in items
        if isinstance(item, dict)
        for arm in arms
    ]
    actual: list[tuple[Any, Any]] = []
    previous = "0" * 64
    for line in predictions.splitlines():
        row = _object(line, owner="Mnemon prediction")
        record = row.pop("record_sha256", None)
        prior = row.pop("previous_sha256", None)
        if prior != previous or record != _sha256(_canonical_bytes(row)):
            raise MnemonH100EvidenceError("prediction journal chain drifted")
        previous = record
        actual.append((row.get("task_id"), row.get("arm")))
    if actual != expected or len(actual) != 128:
        raise MnemonH100EvidenceError("prediction roster drifted")


def _validate_actor_bundle(files: dict[str, bytes], *, job: str) -> dict[str, Any]:
    prefix = f"{job}/mnemon-actor/"
    report = _object(files[prefix + "report.json"], owner=f"{job} report")
    panel = _object(files[prefix + "panel.json"], owner=f"{job} panel")
    checkpoint = _object(files[prefix + "checkpoint.json"], owner=f"{job} checkpoint")
    manifest = _object(files[prefix + "manifest.json"], owner=f"{job} actor manifest")
    predictions = files[prefix + "predictions.jsonl"]
    unhashed = dict(manifest)
    root = unhashed.pop("root_sha256", None)
    receipts = manifest.get("files")
    if (
        manifest.get("status") != EXPECTED_STATUS
        or manifest.get("scientific_result") is not False
        or manifest.get("publication_ready") is not False
        or root != _sha256(_canonical_bytes(unhashed))
        or not isinstance(receipts, dict)
        or set(receipts) != ACTOR_FILES - {"manifest.json"}
    ):
        raise MnemonH100EvidenceError(f"{job} actor manifest drifted")
    for name, receipt in receipts.items():
        value = files[prefix + name]
        if receipt != {"bytes": len(value), "sha256": _sha256(value)}:
            raise MnemonH100EvidenceError(f"{job} actor manifest content drifted")
    if (
        _sha256(files[prefix + "panel.json"]) != EXPECTED_PANEL_SHA256
        or _sha256(predictions) != report.get("predictions_sha256")
        or checkpoint.get("status") != "COMPLETE"
        or checkpoint.get("completed_cases") != 128
        or checkpoint.get("contract", {}).get("experiment_sha256")
        != EXPECTED_EXPERIMENT_SHA256
        or checkpoint.get("contract", {}).get("panel_sha256") != EXPECTED_PANEL_SHA256
        or checkpoint.get("actor_contract") != report.get("actor_contract")
    ):
        raise MnemonH100EvidenceError(f"{job} actor completion drifted")
    _validate_journal(panel, predictions)
    return report


def _validate_runtime(files: dict[str, bytes]) -> None:
    shared = {
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "image_id": EXPECTED_IMAGE_ID,
        "model_receipt_sha256": EXPECTED_MODEL["receipt_sha256"],
        "model_artifact_root": EXPECTED_MODEL["artifact_root_sha256"],
        "study_artifact_sha256": EXPECTED_PANEL_SHA256,
    }
    for job_id in ("313", "315"):
        job = f"job-{job_id}"
        env = _env(files[f"{job}/job.env"], owner=f"{job} environment")
        termination = _env(files[f"{job}/termination.env"], owner=f"{job} termination")
        manifest = _object(files[f"{job}/manifest.json"], owner=f"{job} manifest")
        inspect = json.loads(files[f"{job}/image-inspect.json"])
        if (
            any(env.get(key) != value for key, value in shared.items())
            or env.get("job_id") != job_id
            or env.get("gpu_devices") != "0"
            or env.get("randomness_contract") != "deterministic-all-serve"
            or termination.get("job_id") != job_id
            or termination.get("reason") != "completed"
            or termination.get("exit_code") != "0"
            or manifest.get("image_id") != EXPECTED_IMAGE_ID
            or manifest.get("source_sha256") != EXPECTED_SOURCE_SHA256
            or manifest.get("batch_script_sha256") != EXPECTED_BATCH_SHA256
            or manifest.get("gpu_type") != "h100"
            or manifest.get("gpus") != 1
            or manifest.get("model", {}).get("receipt_sha256")
            != EXPECTED_MODEL["receipt_sha256"]
            or not isinstance(inspect, list)
            or len(inspect) != 1
            or inspect[0].get("Id") != EXPECTED_IMAGE_ID
            or "NVIDIA H100 80GB HBM3" not in files[f"{job}/system.txt"].decode()
            or files[f"{job}/docker-research.sbatch"]
            != files["job-313/docker-research.sbatch"]
        ):
            raise MnemonH100EvidenceError(f"{job} runtime provenance drifted")
    resume = _object(files["job-315/resume-receipt.json"], owner="resume receipt")
    manifest_315 = _object(files["job-315/manifest.json"], owner="job 315 manifest")
    if (
        resume.get("predecessor_job_id") != "313"
        or resume.get("resume_subpath") != "mnemon-actor"
        or any(resume.get(key) != value for key, value in shared.items())
        or manifest_315.get("resume_from_job_id") != "313"
        or manifest_315.get("resume_subpath") != "mnemon-actor"
    ):
        raise MnemonH100EvidenceError("resume provenance drifted")


def validate_mnemon_h100_evidence(
    bundle_or_path: dict[str, Any] | Path,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    if isinstance(bundle_or_path, Path):
        if bundle_or_path.is_symlink() or not bundle_or_path.is_file():
            raise MnemonH100EvidenceError("evidence path is not a regular file")
        bundle = _object(bundle_or_path.read_bytes(), owner="Mnemon evidence")
        root = project_root or bundle_or_path.resolve().parents[3]
    else:
        bundle = bundle_or_path
        if project_root is None:
            raise MnemonH100EvidenceError("project_root is required for in-memory evidence")
        root = project_root
    if (
        bundle.get("schema_version") != 1
        or bundle.get("source_id") != EXPECTED_SOURCE_ID
        or bundle.get("source_revisions") != EXPECTED_REVISIONS
        or bundle.get("evidence_kind") != "h100-static-space-routing-negative"
        or bundle.get("evidence_grade") != "local-negative-reproduced"
        or bundle.get("status") != EXPECTED_STATUS
        or bundle.get("scientific_result") is not False
        or bundle.get("publication_ready") is not False
        or bundle.get("runtime_lane") != "docker-under-slurm-h100-discovery"
        or bundle.get("primary_job_id") != 313
        or bundle.get("resume_job_id") != 315
        or bundle.get("model") != EXPECTED_MODEL
        or bundle.get("claim_boundary") != EXPECTED_CLAIM_BOUNDARY
    ):
        raise MnemonH100EvidenceError("Mnemon H100 evidence identity drifted")
    _validate_source(bundle, root)
    files = _artifacts(bundle, root)
    report_313 = _validate_actor_bundle(files, job="job-313")
    report_315 = _validate_actor_bundle(files, job="job-315")
    if any(
        files[f"job-313/mnemon-actor/{name}"]
        != files[f"job-315/mnemon-actor/{name}"]
        for name in ACTOR_FILES
    ):
        raise MnemonH100EvidenceError("fresh-allocation resume is not byte-exact")
    if report_313 != report_315:
        raise MnemonH100EvidenceError("fresh-allocation report drifted")
    metrics = report_313.get("arm_metrics", {})
    outcome = {
        "all_spaces_exact_match": metrics.get("all_spaces", {}).get("exact_match"),
        "lexical_exact_match": metrics.get("lexical_router", {}).get("exact_match"),
        "lexical_minus_all_token_f1": report_313.get("lexical_minus_all_token_f1"),
        "lexical_to_all_prompt_token_ratio": report_313.get("lexical_to_all_prompt_token_ratio"),
        "no_memory_exact_match": metrics.get("no_memory", {}).get("exact_match"),
        "oracle_exact_match": metrics.get("oracle_space", {}).get("exact_match"),
    }
    if (
        report_313.get("status") != EXPECTED_STATUS
        or report_313.get("scientific_result") is not False
        or report_313.get("publication_ready") is not False
        or report_313.get("completed_cases") != 128
        or report_313.get("total_cases") != 128
        or report_313.get("experiment_sha256") != EXPECTED_EXPERIMENT_SHA256
        or report_313.get("panel_sha256") != EXPECTED_PANEL_SHA256
        or report_313.get("gates") != EXPECTED_GATES
        or bundle.get("outcome") != outcome
    ):
        raise MnemonH100EvidenceError("Mnemon H100 report semantics drifted")
    _validate_runtime(files)
    return bundle


__all__ = [
    "MnemonH100EvidenceError",
    "validate_mnemon_h100_evidence",
]
