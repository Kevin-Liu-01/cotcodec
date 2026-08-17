from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "compare_past_bench_sm01_runs",
    ROOT / "scripts/compare_past_bench_sm01_runs.py",
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _identity() -> dict[str, object]:
    return {
        "source_revision": "f" * 40,
        "source_receipt_sha256": "1" * 64,
        "runtime_receipt_sha256": "2" * 64,
        "image_id": "sha256:" + "3" * 64,
        "sealed_sbom_sha256": "4" * 64,
        "model_receipt_sha256": "5" * 64,
        "experiment_sha256": "6" * 64,
        "argv": ["past-bench", "evolve"],
    }


def _write_cell(
    root: Path,
    *,
    mode: str,
    job_id: int,
    projection_root: str,
    raw_timestamp: str,
    recovered: bool = False,
) -> None:
    evidence = root / "evidence"
    traces = root / "run/traces"
    evidence.mkdir(parents=True)
    result_roots: dict[str, str] = {}
    for variant in ("with_persistence", "without_persistence"):
        variant_root = traces / variant
        variant_root.mkdir(parents=True)
        (variant_root / "trace.jsonl").write_text(
            json.dumps({"content": "same", "timestamp": raw_timestamp}) + "\n",
            encoding="utf-8",
        )
        result = variant_root / "sequence_results.json"
        result.write_text(
            json.dumps({"variant": variant, "episodes": ["same"]}),
            encoding="utf-8",
        )
        result_roots[variant] = MODULE._sha256(result)
    identity = _identity()
    (evidence / "execution-identity.json").write_text(
        json.dumps(identity), encoding="utf-8"
    )
    preflight = {
        "mode": mode,
        "slurm_job_id": job_id,
        "execution_identity_sha256": MODULE._root(identity),
    }
    (evidence / f"preflight-{mode}.json").write_text(
        json.dumps(preflight), encoding="utf-8"
    )
    projection = {"projection_root_sha256": projection_root, "trace_count": 2}
    (evidence / f"trace-projection-{mode}.json").write_text(
        json.dumps(projection), encoding="utf-8"
    )
    status = (
        "PAST_SM01_FRESH_RESUME_RECOVERED_AFTER_DOCTOR_FIX"
        if recovered
        else (
            "PAST_SM01_FRESH_RESUME_PASS"
            if mode == "fresh-job-resume"
            else "PAST_SM01_UNINTERRUPTED_PASS"
        )
    )
    receipt = {
        "schema_version": 1,
        "status": status,
        "scientific_result": False,
        "publication_ready": False,
        "external_attestation": False,
        "mode": mode,
        "slurm_job_id": job_id,
        "trace_count": 2,
        "trace_projection_root_sha256": projection_root,
        "sequence_result_sha256": result_roots,
    }
    if recovered:
        receipt.update(
            {
                "validation_slurm_job_id": job_id + 100,
                "recovery_reason": (
                    "validator-counted-registered-reflection-as-primary-episode"
                ),
            }
        )
    receipt["receipt_sha256"] = MODULE._root(receipt)
    (evidence / f"run-receipt-{mode}.json").write_text(
        json.dumps(receipt), encoding="utf-8"
    )


def test_comparison_accepts_projected_equivalence_and_reports_raw_drift(
    tmp_path: Path,
) -> None:
    uninterrupted = tmp_path / "uninterrupted"
    resumed = tmp_path / "resumed"
    _write_cell(
        uninterrupted,
        mode="uninterrupted",
        job_id=10,
        projection_root="a" * 64,
        raw_timestamp="one",
    )
    _write_cell(
        resumed,
        mode="fresh-job-resume",
        job_id=11,
        projection_root="a" * 64,
        raw_timestamp="two",
    )

    report = MODULE.compare_runs(uninterrupted=uninterrupted, resumed=resumed)

    assert report["status"] == "PAST_SM01_RECOVERY_EQUIVALENCE_PASS"
    assert all(report["gates"].values())
    assert report["raw_trace_byte_equality"] is False
    assert report["raw_trace_byte_equality_required"] is False


def test_comparison_rejects_projection_mismatch(tmp_path: Path) -> None:
    uninterrupted = tmp_path / "uninterrupted"
    resumed = tmp_path / "resumed"
    _write_cell(
        uninterrupted,
        mode="uninterrupted",
        job_id=10,
        projection_root="a" * 64,
        raw_timestamp="one",
    )
    _write_cell(
        resumed,
        mode="fresh-job-resume",
        job_id=11,
        projection_root="b" * 64,
        raw_timestamp="one",
    )

    with pytest.raises(MODULE.ComparisonError, match="equivalence failed"):
        MODULE.compare_runs(uninterrupted=uninterrupted, resumed=resumed)


def test_comparison_rehashes_sequence_results(tmp_path: Path) -> None:
    uninterrupted = tmp_path / "uninterrupted"
    resumed = tmp_path / "resumed"
    for root, mode, job in (
        (uninterrupted, "uninterrupted", 10),
        (resumed, "fresh-job-resume", 11),
    ):
        _write_cell(
            root,
            mode=mode,
            job_id=job,
            projection_root="a" * 64,
            raw_timestamp="one",
        )
    (resumed / "run/traces/with_persistence/sequence_results.json").write_text(
        "tampered", encoding="utf-8"
    )

    with pytest.raises(MODULE.ComparisonError, match="result bytes drifted"):
        MODULE.compare_runs(uninterrupted=uninterrupted, resumed=resumed)


def test_comparison_accepts_transparent_recovered_resume(tmp_path: Path) -> None:
    uninterrupted = tmp_path / "uninterrupted"
    resumed = tmp_path / "resumed"
    _write_cell(
        uninterrupted,
        mode="uninterrupted",
        job_id=10,
        projection_root="a" * 64,
        raw_timestamp="one",
    )
    _write_cell(
        resumed,
        mode="fresh-job-resume",
        job_id=11,
        projection_root="a" * 64,
        raw_timestamp="two",
        recovered=True,
    )

    report = MODULE.compare_runs(uninterrupted=uninterrupted, resumed=resumed)

    assert report["status"] == "PAST_SM01_RECOVERY_EQUIVALENCE_PASS"
