#!/usr/bin/env python3
"""Validate the sealed GAAMA checkpoint/resume H100 negative."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SHA256_LENGTH = 64
EXPECTED_REPOSITORY = "https://github.com/swarna-kpaul/gaama"
EXPECTED_REVISION = "2d992f7f7b97c802bfe4c799878a5477cac1b6ff"
EXPECTED_SOURCE_SHA256 = "8bd7a65b78b049dedc6d1c5154d2c97834debd09255aedd9624516ba40c5c753"
EXPECTED_IMAGE_ID = (
    "sha256:791648995f657900f2c66da9f8e7dc357d56d41eab0ebb20bbe3c1a7937a0a4d"
)
EXPECTED_GIT_SHA = "581ded8df71564b0212d8af5dcd401257aa6a28f"
EXPECTED_GIT_TREE = "5a83330044fda59e998e09c18266ad6f99a84bce"
EXPECTED_EVIDENCE_SHA256 = (
    "011a21918946e19255c1118de41ec99131e1cb64c32b50bc68af8da58d84dc79"
)
EXPECTED_MODEL = {
    "artifact_root_sha256": (
        "3b8a075149bffe4dea784db5b4b37bc0896688cba0b3de7d8d0f6e8ae6157b9e"
    ),
    "model_id": "qwen3.5-4b",
    "receipt_sha256": (
        "75ebfc531acdcbc0c39bbf83ee7bf5267a3ddf02c4fafdf6181624612a0d3082"
    ),
    "revision": "851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a",
}
EXPECTED_CLAIM_BOUNDARY = {
    "gaama_larger_model_admission": "forbidden-by-registered-kill-screen",
    "general_graph_memory_claim": False,
    "official_locomo_evaluation": False,
    "retrieval_component_positive_retained": True,
}
EXPECTED_GATES = {
    "actor_a_a_exact": True,
    "completion_nonempty": True,
    "flat_actor_f1_at_least_0_20": True,
    "mean_prompt_token_ratio_within_1_10": True,
    "row_roster_exact": True,
    "true_f1_exceeds_at_least_two_shuffles": False,
    "true_f1_exceeds_flat": False,
    "true_f1_exceeds_mean_shuffled": False,
}
EXPECTED_ARTIFACT_ROSTER = {
    "build-job-292/final-image.txt",
    "build-job-292/image-inspect.json",
    "build-job-292/registry-inspect.json",
    "build-job-292/source-validation.json",
    "job-295/gaama-actor/checkpoint.json",
    "job-295/gaama-actor/panel.json",
    "job-295/gaama-actor/predictions.jsonl",
    "job-295/job.env",
    "job-295/termination.env",
    "job-297/docker-research.sbatch",
    "job-297/gaama-actor/checkpoint.json",
    "job-297/gaama-actor/manifest.json",
    "job-297/gaama-actor/panel.json",
    "job-297/gaama-actor/predictions.jsonl",
    "job-297/gaama-actor/report.json",
    "job-297/image-inspect.json",
    "job-297/job.env",
    "job-297/manifest.json",
    "job-297/model-receipt.json",
    "job-297/resume-receipt.json",
    "job-297/study-artifact.json",
    "job-297/termination.env",
}


class GaamaH100EvidenceError(ValueError):
    """Raised when the sealed GAAMA H100 evidence drifts."""


def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _parse_json(data: bytes, *, owner: str) -> Any:
    def reject_constant(value: str) -> None:
        raise GaamaH100EvidenceError(f"{owner}: non-finite JSON constant {value}")

    try:
        return json.loads(data, parse_constant=reject_constant)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise GaamaH100EvidenceError(f"{owner}: artifact is not strict JSON") from exc


def _require_object(data: bytes, *, owner: str) -> dict[str, Any]:
    value = _parse_json(data, owner=owner)
    if not isinstance(value, dict):
        raise GaamaH100EvidenceError(f"{owner}: artifact must be one JSON object")
    return value


def _parse_env(data: bytes, *, owner: str) -> dict[str, str]:
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise GaamaH100EvidenceError(f"{owner}: artifact is not UTF-8") from exc
    result: dict[str, str] = {}
    for line in lines:
        key, separator, value = line.partition("=")
        if not separator or not key or key in result:
            raise GaamaH100EvidenceError(f"{owner}: environment artifact is malformed")
        result[key] = value
    return result


def _safe_path(project_root: Path, value: Any, *, owner: str) -> Path:
    if (
        not isinstance(value, str)
        or not value
        or Path(value).is_absolute()
        or ".." in Path(value).parts
    ):
        raise GaamaH100EvidenceError(f"{owner}: path is unsafe")
    path = project_root / value
    if not path.is_file() or path.is_symlink():
        raise GaamaH100EvidenceError(f"{owner}: path is missing or not regular")
    return path


def _load_artifacts(bundle: dict[str, Any], project_root: Path) -> dict[str, bytes]:
    artifact_root_value = bundle.get("artifact_root")
    if (
        not isinstance(artifact_root_value, str)
        or not artifact_root_value
        or Path(artifact_root_value).is_absolute()
        or ".." in Path(artifact_root_value).parts
    ):
        raise GaamaH100EvidenceError("artifact root is unsafe")
    artifact_root = project_root / artifact_root_value
    receipts = bundle.get("artifact_files")
    if not isinstance(receipts, dict) or set(receipts) != EXPECTED_ARTIFACT_ROSTER:
        raise GaamaH100EvidenceError("artifact roster drifted")
    files: dict[str, bytes] = {}
    for name, expected_sha256 in receipts.items():
        path = artifact_root / name
        if (
            not isinstance(expected_sha256, str)
            or len(expected_sha256) != SHA256_LENGTH
            or not path.is_file()
            or path.is_symlink()
        ):
            raise GaamaH100EvidenceError(f"artifact {name} is invalid")
        data = path.read_bytes()
        if _sha256(data) != expected_sha256:
            raise GaamaH100EvidenceError(f"artifact {name} drifted")
        files[name] = data
    return files


def _validate_source(bundle: dict[str, Any], project_root: Path) -> None:
    archive = _safe_path(
        project_root, bundle.get("source_archive_path"), owner="source archive"
    )
    receipt_path = _safe_path(
        project_root, bundle.get("source_receipt_path"), owner="source receipt"
    )
    if (
        _sha256(archive.read_bytes()) != bundle.get("source_archive_sha256")
        or _sha256(receipt_path.read_bytes()) != bundle.get("source_receipt_sha256")
    ):
        raise GaamaH100EvidenceError("source evidence digest drifted")
    receipt = _require_object(receipt_path.read_bytes(), owner="source receipt")
    if (
        receipt.get("schema_version") != 2
        or receipt.get("mode") != "discovery"
        or receipt.get("archive_sha256") != EXPECTED_SOURCE_SHA256
        or receipt.get("git_sha") != EXPECTED_GIT_SHA
        or receipt.get("git_tree") != EXPECTED_GIT_TREE
        or receipt.get("worktree_clean") is not False
    ):
        raise GaamaH100EvidenceError("source receipt semantics drifted")


def _validate_report(bundle: dict[str, Any], files: dict[str, bytes]) -> dict[str, Any]:
    report = _require_object(
        files["job-297/gaama-actor/report.json"], owner="GAAMA report"
    )
    flat = report.get("arm_summaries", {}).get("flat", {})
    true_graph = report.get("arm_summaries", {}).get("true_graph", {})
    primary = report.get("primary_comparison", {})
    expected_outcome = {
        "flat_evidence_recall_all_at_10": flat.get("evidence_recall_all_at_10"),
        "flat_token_f1": flat.get("token_f1"),
        "true_evidence_recall_all_at_10": true_graph.get(
            "evidence_recall_all_at_10"
        ),
        "true_minus_flat_cluster_mean_f1": primary.get(
            "true_minus_flat_cluster_mean_f1"
        ),
        "true_minus_flat_clustered_bootstrap_95_ci": primary.get(
            "true_minus_flat_clustered_bootstrap_95_ci"
        ),
        "true_minus_mean_shuffled_cluster_mean_f1": primary.get(
            "true_minus_mean_shuffled_cluster_mean_f1"
        ),
        "true_minus_mean_shuffled_clustered_bootstrap_95_ci": primary.get(
            "true_minus_mean_shuffled_clustered_bootstrap_95_ci"
        ),
        "true_token_f1": true_graph.get("token_f1"),
    }
    if (
        report.get("status") != "GAAMA_H100_ACTOR_KILLED"
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("discovery_only") is not True
        or report.get("completed_cases") != 1000
        or report.get("total_cases") != 1000
        or report.get("gates") != EXPECTED_GATES
        or bundle.get("outcome") != expected_outcome
    ):
        raise GaamaH100EvidenceError("report semantics drifted")
    return report


def _validate_output_manifest(files: dict[str, bytes]) -> None:
    manifest = _require_object(
        files["job-297/gaama-actor/manifest.json"], owner="GAAMA output manifest"
    )
    root = manifest.get("root_sha256")
    unhashed = dict(manifest)
    unhashed.pop("root_sha256", None)
    receipts = manifest.get("files")
    if (
        manifest.get("status") != "GAAMA_H100_ACTOR_KILLED"
        or root != _sha256(_canonical_bytes(unhashed))
        or not isinstance(receipts, dict)
        or set(receipts)
        != {"checkpoint.json", "panel.json", "predictions.jsonl", "report.json"}
    ):
        raise GaamaH100EvidenceError("output manifest semantics drifted")
    for name, receipt in receipts.items():
        qualified = f"job-297/gaama-actor/{name}"
        if (
            not isinstance(receipt, dict)
            or receipt.get("bytes") != len(files[qualified])
            or receipt.get("sha256") != _sha256(files[qualified])
        ):
            raise GaamaH100EvidenceError("output manifest content drifted")


def _validate_journal_and_resume(
    bundle: dict[str, Any], files: dict[str, bytes], report: dict[str, Any]
) -> None:
    predecessor = files["job-295/gaama-actor/predictions.jsonl"]
    predictions = files["job-297/gaama-actor/predictions.jsonl"]
    if (
        predecessor.count(b"\n") != 656
        or predictions.count(b"\n") != 1000
        or not predictions.startswith(predecessor)
        or report.get("predictions_sha256") != _sha256(predictions)
    ):
        raise GaamaH100EvidenceError("resume prefix drifted")
    panel_295 = files["job-295/gaama-actor/panel.json"]
    panel_297 = files["job-297/gaama-actor/panel.json"]
    if panel_295 != panel_297:
        raise GaamaH100EvidenceError("panel changed across resume")
    panel = _require_object(panel_297, owner="GAAMA panel")
    items = panel.get("items")
    arms = panel.get("arms")
    if not isinstance(items, list) or not isinstance(arms, list):
        raise GaamaH100EvidenceError("panel roster is malformed")
    expected_keys = [
        (item.get("question_id"), arm)
        for item in items
        if isinstance(item, dict)
        for arm in arms
    ]
    actual_keys: list[tuple[Any, Any]] = []
    previous = "0" * SHA256_LENGTH
    for line in predictions.splitlines():
        row = _require_object(line, owner="GAAMA prediction")
        record_sha256 = row.pop("record_sha256", None)
        prior_sha256 = row.pop("previous_sha256", None)
        if prior_sha256 != previous or record_sha256 != _sha256(_canonical_bytes(row)):
            raise GaamaH100EvidenceError("journal hash chain drifted")
        previous = record_sha256
        actual_keys.append((row.get("question_id"), row.get("arm")))
    if actual_keys != expected_keys:
        raise GaamaH100EvidenceError("prediction roster drifted")

    checkpoint_295 = _require_object(
        files["job-295/gaama-actor/checkpoint.json"], owner="checkpoint 295"
    )
    checkpoint_297 = _require_object(
        files["job-297/gaama-actor/checkpoint.json"], owner="checkpoint 297"
    )
    if (
        checkpoint_295.get("status") != "IN_PROGRESS"
        or checkpoint_295.get("completed_cases") != 656
        or checkpoint_297.get("status") != "COMPLETE"
        or checkpoint_297.get("completed_cases") != 1000
        or checkpoint_297.get("journal_root_sha256") != previous
        or checkpoint_297.get("actor_contract") != report.get("actor_contract")
        or checkpoint_295.get("contract") != checkpoint_297.get("contract")
    ):
        raise GaamaH100EvidenceError("checkpoint semantics drifted")

    resume = _require_object(
        files["job-297/resume-receipt.json"], owner="resume receipt"
    )
    job_manifest = _require_object(files["job-297/manifest.json"], owner="job manifest")
    env_295 = _parse_env(files["job-295/job.env"], owner="job 295")
    env_297 = _parse_env(files["job-297/job.env"], owner="job 297")
    model = bundle["model"]
    shared = {
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "image_id": EXPECTED_IMAGE_ID,
        "model_receipt_sha256": model["receipt_sha256"],
        "model_artifact_root": model["artifact_root_sha256"],
        "study_artifact_sha256": EXPECTED_EVIDENCE_SHA256,
    }
    if (
        resume.get("predecessor_job_id") != "295"
        or resume.get("resume_subpath") != "gaama-actor"
        or any(env_295.get(key) != value for key, value in shared.items())
        or any(env_297.get(key) != value for key, value in shared.items())
        or any(resume.get(key) != value for key, value in shared.items())
        or job_manifest.get("resume_from_job_id") != "295"
        or job_manifest.get("resume_subpath") != "gaama-actor"
        or job_manifest.get("image_id") != EXPECTED_IMAGE_ID
        or job_manifest.get("source_sha256") != EXPECTED_SOURCE_SHA256
    ):
        raise GaamaH100EvidenceError("Slurm resume provenance drifted")


def _validate_runtime(bundle: dict[str, Any], files: dict[str, bytes]) -> None:
    termination_295 = _parse_env(files["job-295/termination.env"], owner="termination 295")
    termination_297 = _parse_env(files["job-297/termination.env"], owner="termination 297")
    if (
        termination_295.get("reason") != "signal_USR1_checkpoint_confirmed"
        or termination_295.get("exit_code") != "0"
        or termination_295.get("checkpoint_ready") != "true"
        or termination_297.get("reason") != "completed"
        or termination_297.get("exit_code") != "0"
    ):
        raise GaamaH100EvidenceError("termination evidence drifted")

    inspect = _parse_json(files["build-job-292/image-inspect.json"], owner="image inspect")
    if not isinstance(inspect, list) or len(inspect) != 1 or not isinstance(inspect[0], dict):
        raise GaamaH100EvidenceError("image inspect roster drifted")
    image = inspect[0]
    labels = image.get("Config", {}).get("Labels", {})
    if (
        image.get("Id") != EXPECTED_IMAGE_ID
        or labels.get("org.opencontainers.image.source-tree-sha256")
        != EXPECTED_SOURCE_SHA256
        or labels.get("org.opencontainers.image.revision") != EXPECTED_GIT_SHA
    ):
        raise GaamaH100EvidenceError("image provenance drifted")

    model_receipt = _require_object(
        files["job-297/model-receipt.json"], owner="model receipt"
    )
    if (
        bundle.get("model") != EXPECTED_MODEL
        or model_receipt.get("model_id") != EXPECTED_MODEL["model_id"]
        or model_receipt.get("revision") != EXPECTED_MODEL["revision"]
        or model_receipt.get("artifact_root_sha256")
        != EXPECTED_MODEL["artifact_root_sha256"]
        or model_receipt.get("mode") != "full"
    ):
        raise GaamaH100EvidenceError("model identity drifted")


def validate_gaama_h100_evidence(
    bundle: dict[str, Any], *, project_root: Path
) -> None:
    """Rehash and semantically validate the complete two-job negative."""

    if (
        bundle.get("schema_version") != 1
        or bundle.get("source_id") != "gaama"
        or bundle.get("source_revisions")
        != {EXPECTED_REPOSITORY: EXPECTED_REVISION}
        or bundle.get("evidence_grade") != "local-negative-reproduced"
        or bundle.get("evidence_kind") != "h100-actor-translation-negative"
        or bundle.get("status") != "GAAMA_H100_ACTOR_KILLED"
        or bundle.get("scientific_result") is not False
        or bundle.get("publication_ready") is not False
        or bundle.get("runtime_lane") != "docker-under-slurm-h100-discovery"
        or bundle.get("logical_run_count") != 1
        or bundle.get("predecessor_job_id") != 295
        or bundle.get("final_job_id") != 297
        or bundle.get("predecessor_completed_cases") != 656
        or bundle.get("total_cases") != 1000
        or bundle.get("claim_boundary") != EXPECTED_CLAIM_BOUNDARY
        or bundle.get("source_archive_sha256") != EXPECTED_SOURCE_SHA256
        or bundle.get("image_id") != EXPECTED_IMAGE_ID
    ):
        raise GaamaH100EvidenceError("top-level contract drifted")

    prior = bundle.get("prior_retrieval_receipt")
    prior_path = _safe_path(
        project_root,
        "research/evidence/memory/gaama-natural-graph-v5.json",
        owner="prior retrieval receipt",
    )
    if (
        prior
        != {
            "artifact_path": "research/evidence/memory/gaama-natural-graph-v5.json",
            "sha256": EXPECTED_EVIDENCE_SHA256,
        }
        or _sha256(prior_path.read_bytes()) != EXPECTED_EVIDENCE_SHA256
    ):
        raise GaamaH100EvidenceError("prior retrieval receipt drifted")

    files = _load_artifacts(bundle, project_root)
    _validate_source(bundle, project_root)
    report = _validate_report(bundle, files)
    _validate_output_manifest(files)
    _validate_journal_and_resume(bundle, files, report)
    _validate_runtime(bundle, files)


__all__ = [
    "GaamaH100EvidenceError",
    "validate_gaama_h100_evidence",
]
