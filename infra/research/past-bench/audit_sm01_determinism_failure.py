#!/usr/bin/env python3
"""Seal the preregistered SM01 restart-equivalence falsification."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

import sm01_job_doctor as doctor


class DeterminismAuditError(ValueError):
    """Raised when the two cells do not prove the registered falsifier."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def _root(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha256(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise DeterminismAuditError(f"unsafe audit artifact: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_object(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise DeterminismAuditError(f"{label} must be a regular file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise DeterminismAuditError(f"{label} is invalid JSON") from exc
    if not isinstance(value, dict):
        raise DeterminismAuditError(f"{label} must contain one object")
    return value


def _write_once(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _canonical(value) + b"\n"
    temporary = path.parent / f".{path.name}.{os.getpid()}.tmp"
    with temporary.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _primary_rows(episodes: Any, *, expected_count: int, label: str) -> list[dict[str, Any]]:
    if not isinstance(episodes, list):
        raise DeterminismAuditError(f"{label} episodes are invalid")
    primary = [
        episode
        for episode in episodes
        if isinstance(episode, dict) and episode.get("episode_kind") != "reflection"
    ]
    try:
        return doctor._validate_episode_results(
            primary,
            expected_task_ids=doctor.TASK_IDS[:expected_count],
            label=label,
        )
    except doctor.Sm01DoctorError as exc:
        raise DeterminismAuditError(str(exc)) from exc


def _compare_primary(
    continuous: list[dict[str, Any]], resumed: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for left, right in zip(continuous, resumed, strict=True):
        left_score = float(left["task_score"])
        right_score = float(right["task_score"])
        rows.append(
            {
                "task_id": left["task_id"],
                "continuous_score": left_score,
                "resumed_score": right_score,
                "score_equal": math.isclose(
                    left_score, right_score, rel_tol=0.0, abs_tol=0.0
                ),
                "continuous_passed": left["passed"],
                "resumed_passed": right["passed"],
                "passed_equal": left["passed"] == right["passed"],
                "normalized_episode_equal": doctor._normalize(left)
                == doctor._normalize(right),
            }
        )
    return rows


def audit(*, continuous_root: Path, resumed_root: Path, output: Path) -> dict[str, Any]:
    for root, label in (
        (continuous_root, "continuous"),
        (resumed_root, "resumed"),
    ):
        if not root.is_dir() or root.is_symlink():
            raise DeterminismAuditError(f"{label} root is missing or unsafe")
    continuous_evidence = continuous_root / "evidence"
    resumed_evidence = resumed_root / "evidence"
    continuous_run = continuous_root / "run"
    resumed_run = resumed_root / "run"
    continuous_identity = _read_object(
        continuous_evidence / "execution-identity.json", "continuous identity"
    )
    resumed_identity = _read_object(
        resumed_evidence / "execution-identity.json", "resumed identity"
    )
    if continuous_identity != resumed_identity:
        raise DeterminismAuditError("execution identities differ")

    continuous_preflight = _read_object(
        continuous_evidence / "preflight-uninterrupted.json", "continuous preflight"
    )
    continuous_termination = (
        continuous_evidence / "termination-uninterrupted.txt"
    )
    if (
        continuous_preflight.get("mode") != "uninterrupted"
        or continuous_preflight.get("slurm_job_id") != 254
        or continuous_termination.read_text(encoding="utf-8")
        != (
            "exit_code=1\ntermination_reason=artifact_finalization_failed\n"
            "signal_requested=true\n"
        )
    ):
        raise DeterminismAuditError("continuous kill evidence drifted")
    resumed_receipt = _read_object(
        resumed_evidence / "run-receipt-fresh-job-resume.json", "resumed receipt"
    )
    resumed_unsigned = {
        key: value for key, value in resumed_receipt.items() if key != "receipt_sha256"
    }
    if (
        resumed_receipt.get("receipt_sha256") != _root(resumed_unsigned)
        or resumed_receipt.get("status") != doctor.RECOVERED_RESUME_STATUS
        or resumed_receipt.get("slurm_job_id") != 250
        or resumed_receipt.get("validation_slurm_job_id") != 252
    ):
        raise DeterminismAuditError("resumed receipt drifted")
    try:
        continuous_state, continuous_pointer_sha256 = doctor._load_checkpoint_state(
            continuous_run, continuous_evidence
        )
        resumed_state, resumed_pointer_sha256 = doctor._load_checkpoint_state(
            resumed_run, resumed_evidence
        )
        resumed_result_roots = doctor._validate_complete_results(resumed_run)
    except doctor.Sm01DoctorError as exc:
        raise DeterminismAuditError(str(exc)) from exc
    if (
        continuous_state.get("stage") != "episode-complete"
        or continuous_state.get("variant") != "with_persistence"
        or continuous_state.get("completed_episode") != 4
        or resumed_state.get("stage") != "run-complete"
        or resumed_state.get("completed_episode") != 8
        or resumed_result_roots != resumed_receipt.get("sequence_result_sha256")
    ):
        raise DeterminismAuditError("checkpoint stages or result roots drifted")

    continuous_primary = _primary_rows(
        continuous_state.get("episode_results"), expected_count=4, label="continuous"
    )
    resumed_results = _read_object(
        resumed_run / "traces/with_persistence/sequence_results.json",
        "resumed persistence results",
    )
    resumed_primary = _primary_rows(
        resumed_results.get("episodes"), expected_count=8, label="resumed"
    )[:4]
    comparisons = _compare_primary(continuous_primary, resumed_primary)

    continuous_projection = doctor._trace_projection(continuous_run / "traces")
    resumed_projection = doctor._trace_projection(resumed_run / "traces")
    continuous_traces = {
        row["path"]: row for row in continuous_projection["traces"]
    }
    resumed_traces = {row["path"]: row for row in resumed_projection["traces"]}
    if not continuous_traces or not set(continuous_traces).issubset(resumed_traces):
        raise DeterminismAuditError("continuous trace paths are not a resumed subset")
    trace_comparisons = [
        {
            "path": path,
            "continuous_events_sha256": row["events_sha256"],
            "resumed_events_sha256": resumed_traces[path]["events_sha256"],
            "events_equal": row["events_sha256"]
            == resumed_traces[path]["events_sha256"],
        }
        for path, row in sorted(continuous_traces.items())
    ]
    score_mismatches = [row for row in comparisons if not row["score_equal"]]
    pass_mismatches = [row for row in comparisons if not row["passed_equal"]]
    trace_mismatches = [row for row in trace_comparisons if not row["events_equal"]]
    if not score_mismatches or not pass_mismatches or not trace_mismatches:
        raise DeterminismAuditError("registered determinism falsifier was not reproduced")

    report = {
        "schema_version": 1,
        "status": "PAST_SM01_RESTART_EQUIVALENCE_FALSIFIED",
        "scientific_result": False,
        "publication_ready": False,
        "registered_kill_triggered": True,
        "execution_identity_sha256": _root(continuous_identity),
        "continuous": {
            "slurm_job_id": 254,
            "checkpoint_pointer_sha256": continuous_pointer_sha256,
            "completed_episode": 4,
            "termination_sha256": _sha256(continuous_termination),
        },
        "resumed": {
            "workload_slurm_job_id": 250,
            "validation_slurm_job_id": 252,
            "checkpoint_pointer_sha256": resumed_pointer_sha256,
            "receipt_file_sha256": _sha256(
                resumed_evidence / "run-receipt-fresh-job-resume.json"
            ),
        },
        "primary_comparisons": comparisons,
        "score_mismatch_count": len(score_mismatches),
        "pass_mismatch_count": len(pass_mismatches),
        "common_trace_comparisons": trace_comparisons,
        "trace_mismatch_count": len(trace_mismatches),
        "conclusion": (
            "Greedy fixed-seed Qwen3.6-35B-A3B did not reproduce identical "
            "SM01 outcomes across a fresh continuous execution, so the strict "
            "restart-equivalence gate fails and the cell cannot be promoted."
        ),
        "external_attestation": False,
    }
    report["report_sha256"] = _root(report)
    _write_once(output, report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--continuous-root", type=Path, required=True)
    parser.add_argument("--resumed-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = audit(
            continuous_root=args.continuous_root,
            resumed_root=args.resumed_root,
            output=args.output,
        )
    except (DeterminismAuditError, OSError, UnicodeError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
