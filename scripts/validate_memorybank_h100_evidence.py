#!/usr/bin/env python3
"""Validate the sealed MemoryBank Qwen3.5-4B H100 control screen."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

EXPECTED_SOURCE_REVISION = "cf61c4196e4cfdb0f2b7a0316249fa40312dc3a9"
EXPECTED_SOURCE_SHA256 = "2d960d1a5cf6fd64cdd0baba0a2c752ad6216b8443d741cb7deef9e07d031322"
EXPECTED_GIT_SHA = "581ded8df71564b0212d8af5dcd401257aa6a28f"
EXPECTED_GIT_TREE = "5a83330044fda59e998e09c18266ad6f99a84bce"
EXPECTED_IMAGE_ID = (
    "sha256:ca32b5c26b92fbe2a7054ae96543cd62928b0493896ec355b869b612022aa9a2"
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
EXPECTED_EXPERIMENT_SHA256 = (
    "b3cc850ec1de79252052af8c0f63da9940f7d79b75a4a7455be3412c22746b15"
)
EXPECTED_ANALYSIS_SCRIPT_SHA256 = (
    "915e23a16ea5d5166119b2db8f75cfc50b9ebdca10acd7d4e6ab2ce3685248f6"
)
EXPECTED_ARTIFACT_ROSTER = {
    "aggregate-report.json",
    "analysis-plan.json",
    "execution-amendment-003.json",
    "remote-jobs/328/termination.env",
    "remote-jobs/329/manifest.json",
    "remote-jobs/329/memorybank-upstream-precedence/screen-matrix-report.json",
    "remote-jobs/329/termination.env",
    "remote-jobs/330/termination.env",
    "remote-jobs/333/image-inspect.json",
    "remote-jobs/333/manifest.json",
    "remote-jobs/333/memorybank-corrected/screen-matrix-report.json",
    "remote-jobs/333/model-receipt.json",
    "remote-jobs/333/resume-receipt.json",
    "remote-jobs/333/termination.env",
    "remote-jobs/334/manifest.json",
    "remote-jobs/334/memorybank-no-decay/screen-matrix-report.json",
    "remote-jobs/334/resume-receipt.json",
    "remote-jobs/334/termination.env",
    "remote-jobs/slurm-328.out",
    "remote-jobs/slurm-329.out",
    "remote-jobs/slurm-330.out",
    "remote-jobs/slurm-333.out",
    "remote-jobs/slurm-334.out",
}


class MemoryBankH100EvidenceError(ValueError):
    """Raised when the MemoryBank H100 evidence bundle drifts."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json(path: Path, *, owner: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise MemoryBankH100EvidenceError(f"{owner}: artifact is not a regular file")
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda item: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON constant {item}")
            ),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise MemoryBankH100EvidenceError(f"{owner}: artifact is not strict JSON") from exc
    if not isinstance(value, dict):
        raise MemoryBankH100EvidenceError(f"{owner}: artifact must be a JSON object")
    return value


def _env(path: Path, *, owner: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if not separator or not key or key in result:
            raise MemoryBankH100EvidenceError(f"{owner}: malformed environment receipt")
        result[key] = value
    return result


def _safe_file(project_root: Path, value: Any, *, owner: str) -> Path:
    if (
        not isinstance(value, str)
        or not value
        or Path(value).is_absolute()
        or ".." in Path(value).parts
    ):
        raise MemoryBankH100EvidenceError(f"{owner}: unsafe path")
    path = project_root / value
    if not path.is_file() or path.is_symlink():
        raise MemoryBankH100EvidenceError(f"{owner}: missing or non-regular file")
    return path


def _artifact_files(
    bundle: dict[str, Any], project_root: Path
) -> tuple[Path, dict[str, Path]]:
    root_value = bundle.get("artifact_root")
    if (
        not isinstance(root_value, str)
        or not root_value
        or Path(root_value).is_absolute()
        or ".." in Path(root_value).parts
    ):
        raise MemoryBankH100EvidenceError("artifact root is unsafe")
    root = project_root / root_value
    receipts = bundle.get("artifact_files")
    if not isinstance(receipts, dict) or set(receipts) != EXPECTED_ARTIFACT_ROSTER:
        raise MemoryBankH100EvidenceError("artifact roster drifted")
    result: dict[str, Path] = {}
    for name, expected in receipts.items():
        path = root / name
        if (
            not isinstance(expected, str)
            or len(expected) != 64
            or not path.is_file()
            or path.is_symlink()
            or _sha256(path) != expected
        ):
            raise MemoryBankH100EvidenceError(f"artifact {name} drifted")
        result[name] = path
    return root, result


def _validate_runtime(
    bundle: dict[str, Any], files: dict[str, Path]
) -> None:
    expected_terminations = {
        "328": ("signal_USR1_checkpoint_confirmed", "true"),
        "329": ("completed", "true"),
        "330": ("signal_TERM_checkpoint_confirmed", "true"),
        "333": ("completed", "false"),
        "334": ("completed", "true"),
    }
    for job_id, (reason, checkpoint_ready) in expected_terminations.items():
        values = _env(
            files[f"remote-jobs/{job_id}/termination.env"],
            owner=f"job {job_id} termination",
        )
        if (
            values.get("job_id") != job_id
            or values.get("reason") != reason
            or values.get("exit_code") != "0"
            or values.get("checkpoint_ready") != checkpoint_ready
        ):
            raise MemoryBankH100EvidenceError(f"job {job_id} termination drifted")

    for job_id, arm, predecessor in (
        ("333", "memorybank-corrected", "328"),
        ("334", "memorybank-no-decay", "330"),
    ):
        manifest = _json(files[f"remote-jobs/{job_id}/manifest.json"], owner="manifest")
        resume = _json(
            files[f"remote-jobs/{job_id}/resume-receipt.json"], owner="resume receipt"
        )
        if (
            manifest.get("resume_from_job_id") != predecessor
            or manifest.get("resume_subpath") != arm
            or manifest.get("source_sha256") != EXPECTED_SOURCE_SHA256
            or manifest.get("image_id") != EXPECTED_IMAGE_ID
            or manifest.get("model") != {
                **EXPECTED_MODEL,
                "cache_host_path": "/home/kevin/cotcodec-runs/hf-cache",
            }
            or manifest.get("command", []).count("--resume") != 1
            or resume.get("predecessor_job_id") != predecessor
            or resume.get("resume_subpath") != arm
            or resume.get("source_sha256") != EXPECTED_SOURCE_SHA256
            or resume.get("image_id") != EXPECTED_IMAGE_ID
        ):
            raise MemoryBankH100EvidenceError(f"job {job_id} resume lineage drifted")

    upstream = _json(files["remote-jobs/329/manifest.json"], owner="upstream manifest")
    if (
        "resume_from_job_id" in upstream
        or "--resume" in upstream.get("command", [])
        or upstream.get("source_sha256") != EXPECTED_SOURCE_SHA256
        or upstream.get("image_id") != EXPECTED_IMAGE_ID
        or upstream.get("model")
        != {**EXPECTED_MODEL, "cache_host_path": "/home/kevin/cotcodec-runs/hf-cache"}
    ):
        raise MemoryBankH100EvidenceError("upstream arm provenance drifted")

    inspect = json.loads(files["remote-jobs/333/image-inspect.json"].read_text())
    if not isinstance(inspect, list) or len(inspect) != 1:
        raise MemoryBankH100EvidenceError("image inspection roster drifted")
    labels = inspect[0].get("Config", {}).get("Labels", {})
    if (
        inspect[0].get("Id") != EXPECTED_IMAGE_ID
        or labels.get("org.opencontainers.image.cotcodec-git-sha") != EXPECTED_GIT_SHA
        or labels.get("org.opencontainers.image.cotcodec-git-tree") != EXPECTED_GIT_TREE
        or labels.get("org.opencontainers.image.source-tree-sha256")
        != EXPECTED_SOURCE_SHA256
    ):
        raise MemoryBankH100EvidenceError("image provenance drifted")
    model = _json(files["remote-jobs/333/model-receipt.json"], owner="model receipt")
    if (
        any(
            model.get(key) != value
            for key, value in EXPECTED_MODEL.items()
            if key != "receipt_sha256"
        )
        or _sha256(files["remote-jobs/333/model-receipt.json"])
        != EXPECTED_MODEL["receipt_sha256"]
    ):
        raise MemoryBankH100EvidenceError("model receipt drifted")
    if bundle.get("image_id") != EXPECTED_IMAGE_ID or bundle.get("model") != EXPECTED_MODEL:
        raise MemoryBankH100EvidenceError("top-level runtime identity drifted")


def validate_memorybank_h100_evidence(
    bundle: dict[str, Any], *, project_root: Path
) -> None:
    """Rehash and semantically validate the full five-job control screen."""

    # Keep this import lazy: the actor summarizer reaches the landscape validators,
    # which themselves import this receipt validator.
    from scripts.aggregate_memorybank_h100_screen import (
        aggregate_memorybank_h100_screen,
    )

    if (
        bundle.get("schema_version") != 1
        or bundle.get("source_id") != "memorybank-siliconfriend"
        or bundle.get("source_revisions")
        != {
            "https://github.com/zhongwanjun/MemoryBank-SiliconFriend": (
                EXPECTED_SOURCE_REVISION
            )
        }
        or bundle.get("evidence_grade") != "local-negative-reproduced"
        or bundle.get("evidence_kind") != "clean-room-h100-control-screen"
        or bundle.get("status")
        != "MEMORYBANK_CORRECTED_DECAY_PASS_NO_DECAY_KILLS_SCALING"
        or bundle.get("scientific_result") is not False
        or bundle.get("publication_ready") is not False
        or bundle.get("runtime_lane") != "docker-under-slurm-h100-discovery"
        or bundle.get("experiment_sha256") != EXPECTED_EXPERIMENT_SHA256
        or bundle.get("git_sha") != EXPECTED_GIT_SHA
        or bundle.get("git_tree") != EXPECTED_GIT_TREE
        or bundle.get("initial_jobs")
        != {"corrected": 328, "no_decay": 330, "upstream_precedence": 329}
        or bundle.get("resume_jobs") != {"corrected": 333, "no_decay": 334}
        or bundle.get("claim_boundary")
        != {
            "larger_model_admission": "forbidden-because-no-decay-dominates",
            "memorybank_paper_reproduced": False,
            "no_decay_control_dominates_corrected": True,
            "upstream_precedence_bug_repaired": True,
        }
    ):
        raise MemoryBankH100EvidenceError("top-level evidence contract drifted")

    source = _safe_file(project_root, bundle.get("source_archive_path"), owner="source")
    receipt = _safe_file(
        project_root, bundle.get("source_receipt_path"), owner="source receipt"
    )
    if (
        _sha256(source) != EXPECTED_SOURCE_SHA256
        or bundle.get("source_archive_sha256") != EXPECTED_SOURCE_SHA256
        or _sha256(receipt) != bundle.get("source_receipt_sha256")
    ):
        raise MemoryBankH100EvidenceError("source archive evidence drifted")
    source_receipt = _json(receipt, owner="source receipt")
    if (
        source_receipt.get("archive_sha256") != EXPECTED_SOURCE_SHA256
        or source_receipt.get("git_sha") != EXPECTED_GIT_SHA
        or source_receipt.get("git_tree") != EXPECTED_GIT_TREE
        or source_receipt.get("worktree_clean") is not False
    ):
        raise MemoryBankH100EvidenceError("source receipt semantics drifted")

    artifact_root, files = _artifact_files(bundle, project_root)
    plan = _json(files["analysis-plan.json"], owner="analysis plan")
    analysis_script = project_root / str(plan.get("analysis_script"))
    experiment = _safe_file(
        project_root, bundle.get("experiment_path"), owner="experiment"
    )
    if (
        plan.get("status") != "MEMORYBANK_H100_ANALYSIS_PLAN_SEALED"
        or plan.get("analysis_script_sha256") != EXPECTED_ANALYSIS_SCRIPT_SHA256
        or _sha256(analysis_script) != EXPECTED_ANALYSIS_SCRIPT_SHA256
        or plan.get("experiment_sha256") != EXPECTED_EXPERIMENT_SHA256
        or _sha256(experiment) != EXPECTED_EXPERIMENT_SHA256
    ):
        raise MemoryBankH100EvidenceError("analysis plan drifted")
    amendment = _json(files["execution-amendment-003.json"], owner="amendment")
    if (
        amendment.get("status") != "MEMORYBANK_H100_LOGISTICS_AMENDMENT_SEALED"
        or amendment.get("amended_cumulative_budget")
        != {"max_gpu_hours_per_arm": 1.0, "max_total_gpu_hours": 3.0}
        or amendment.get("initial_jobs") != bundle.get("initial_jobs")
    ):
        raise MemoryBankH100EvidenceError("execution amendment drifted")

    _validate_runtime(bundle, files)
    report = _json(files["aggregate-report.json"], owner="aggregate report")
    recomputed = aggregate_memorybank_h100_screen(
        experiment_path=experiment,
        arm_roots={
            "corrected": artifact_root / "remote-jobs/333/memorybank-corrected",
            "upstream_precedence": (
                artifact_root / "remote-jobs/329/memorybank-upstream-precedence"
            ),
            "no_decay": artifact_root / "remote-jobs/334/memorybank-no-decay",
        },
    )
    if report != recomputed:
        raise MemoryBankH100EvidenceError("aggregate report does not recompute")
    corrected_upstream = report["contrasts"]["corrected_minus_upstream_precedence"][
        "primary_served_oracle_success"
    ]
    corrected_no_decay = report["contrasts"]["corrected_minus_no_decay"][
        "primary_served_oracle_success"
    ]
    expected_outcome = {
        "corrected_minus_no_decay_ci95_points": [
            corrected_no_decay["ci95_low_points"],
            corrected_no_decay["ci95_high_points"],
        ],
        "corrected_minus_no_decay_points": corrected_no_decay["point_delta_points"],
        "corrected_minus_upstream_ci95_points": [
            corrected_upstream["ci95_low_points"],
            corrected_upstream["ci95_high_points"],
        ],
        "corrected_minus_upstream_points": corrected_upstream["point_delta_points"],
        "safety_failures": sum(
            seed["safety_failures"] for arm in report["arms"] for seed in arm["seeds"]
        ),
        "valid_action_rate": min(
            seed["valid_action_rate"] for arm in report["arms"] for seed in arm["seeds"]
        ),
    }
    if (
        report.get("status") != "MEMORYBANK_CORRECTED_DECAY_ACTOR_PASS"
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or not all(report.get("gates", {}).values())
        or bundle.get("outcome") != expected_outcome
    ):
        raise MemoryBankH100EvidenceError("registered outcome drifted")


__all__ = [
    "MemoryBankH100EvidenceError",
    "validate_memorybank_h100_evidence",
]
