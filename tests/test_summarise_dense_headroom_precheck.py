"""The combined read of the dense headroom pre-check's lane receipts and its void rules."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from harness import dense_headroom_data as dhd
from scripts import preregister
from scripts import summarise_dense_headroom_precheck as summary

GIT, SOURCE = "b" * 40, "c" * 64
SMALL, LARGE = "qwen3-0.6b-base", "qwen3.5-4b-base"


def _decisions(lane_class: str) -> dict:
    return {"lane_class": lane_class, "lexical_confound": "PRESENT", "h2_status": "PASS",
            "entity_control": "SUFFICIENT",
            "null_calibration": {"hs": "CENTRED", "mp": "CENTRED"},
            "floor_candidate": "VIABLE"}


@pytest.fixture()
def frozen(tmp_path):
    prereg = tmp_path / "repo" / "program" / "preregistrations" / f"{dhd.EXPERIMENT_ID}.md"
    prereg.parent.mkdir(parents=True)
    prereg.write_text("# stand-in\n", encoding="utf-8")
    ledger = prereg.parent / "ledger.jsonl"
    row = preregister.freeze(prereg, dhd.EXPERIMENT_ID, ledger=ledger, root=tmp_path / "repo")
    return tmp_path / "repo", ledger, str(row["sha256"])


def _env(path: Path, fields: dict) -> None:
    path.write_text("".join(f"{k}={v}\n" for k, v in fields.items()), encoding="utf-8")


def _job(runs: Path, lane: str, job_id: int, *, seconds: int = 240, reason: str = "completed",
         exit_code: str = "0", predecessor: str = "none", checkpoint: bool = False,
         provenance: str = "PASS", git: str = GIT) -> Path:
    path = runs / lane / str(job_id)
    path.mkdir(parents=True)
    _env(path / "job.env", {"job_id": job_id, "predecessor_job_id": predecessor,
                            "git_sha": git, "source_sha256": SOURCE,
                            "started_at": "2026-10-08T10:00:00Z"})
    minutes, rest = divmod(seconds, 60)
    _env(path / "termination.env", {"job_id": job_id, "reason": reason, "exit_code": exit_code,
                                    "finished_at": f"2026-10-08T10:{minutes:02d}:{rest:02d}Z",
                                    "checkpoint_ready": "true" if checkpoint else "false"})
    (path / "provenance-verification.txt").write_text(json.dumps(
        {"status": provenance, "git_sha": git, "source_sha256": SOURCE}) + "\n")
    if checkpoint:
        (path / dhd.RESUME_SUBPATH).mkdir(parents=True)
        (path / dhd.RESUME_SUBPATH / "dev-artifact.sha256").write_text("e" * 64 + "\n")
    return path


def _receipt(job_dir: Path, lane: str, lane_class: str, prereg_sha: str, *,
             kind: str = "fresh", predecessor: str | None = None, **overrides) -> Path:
    payload = {"experiment_id": dhd.EXPERIMENT_ID, "status": "PRECHECK_COMPLETE",
               "profile": "registered", "lane": {"lane_id": lane},
               "decisions": _decisions(lane_class),
               "hashes": {"preregistration_sha256": prereg_sha,
                          "bundle_sha256": dhd.SOURCE_BUNDLE_SHA256, "git_sha": GIT,
                          "source_sha256": SOURCE, "dev_artifact_sha256": "e" * 64,
                          "job": {"kind": kind, "predecessor_job_id": predecessor,
                                  "minutes": 9}},
               "slurm_job_id": job_dir.name}
    payload.update(overrides)
    path = job_dir / dhd.OUTPUT_SUBDIR / "receipt.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _orx(tmp_path: Path, *jobs: int, exit_code: int = 0) -> Path:
    log = tmp_path / f"orx-{'-'.join(map(str, jobs))}-{exit_code}.log"
    log.write_text("".join(f"ORX_SLURM_JOB {j}\nORX_RESULT kind=slurm-manifest "
                           f"direction=q3-dense-headroom job={j} exit={exit_code}\n"
                           for j in jobs), encoding="utf-8")
    return log


def _main(paths, output, root, ledger, logs, *extra) -> int:
    argv = [*map(str, paths), "--output", str(output), "--ledger", str(ledger),
            "--root", str(root)]
    for log in logs:
        argv += ["--orx-log", str(log)]
    return summary.main([*argv, *extra])


def test_combined_read(frozen, tmp_path) -> None:
    root, ledger, sha = frozen
    runs = tmp_path / "runs"
    _job(runs, SMALL, 10, seconds=5, reason="foreign_gpu_process", exit_code="75")
    small = _receipt(_job(runs, SMALL, 11, seconds=250), SMALL, "GO_ONLY_CAPABLE", sha)
    large = _receipt(_job(runs, LARGE, 12, seconds=600), LARGE, "NEGATIVE_CAPABLE", sha)
    output = tmp_path / "combined.json"
    assert _main([small, large], output, root, ledger, [_orx(tmp_path, 11, 12)]) == 0
    read = json.loads(output.read_text())
    combined = read["combined"]
    assert (combined["design"], combined["base"]) == ("NEGATIVE_CAPABLE_V3", LARGE)
    assert read["lanes"][SMALL]["receipt_sha256"] == hashlib.sha256(small.read_bytes()
                                                                     ).hexdigest()
    usage = read["gpu_usage"][SMALL]
    assert [j["job_id"] for j in usage["jobs"]] == ["10", "11"]
    assert usage["gpu_hours_used"] == pytest.approx(255 / 3600)
    assert read["gpu_hours_used"] == pytest.approx(855 / 3600)
    assert _main([small, large], output, root, ledger, [_orx(tmp_path, 11, 12)]) == 2


@pytest.mark.parametrize("defect", ["failed", "no-orx", "orx-exit-5", "provenance", "source",
                                    "two-receipts", "over-cap", "unended"])
def test_void_jobs_are_refused(frozen, tmp_path, defect) -> None:
    root, ledger, sha = frozen
    runs = tmp_path / "runs"
    job = _job(runs, SMALL, 20,
               reason="workload_failed" if defect == "failed" else "completed",
               exit_code="3" if defect == "failed" else "0",
               provenance="FAIL" if defect == "provenance" else "PASS",
               seconds=9 * 60 + 30 if defect == "over-cap" else 240)
    receipt = _receipt(job, SMALL, "NOT_VIABLE", sha)
    if defect == "source":
        _env(job / "job.env", {"job_id": 20, "predecessor_job_id": "none", "git_sha": "f" * 40,
                               "source_sha256": SOURCE, "started_at": "2026-10-08T10:00:00Z"})
    if defect == "two-receipts":
        _receipt(_job(runs, SMALL, 21), SMALL, "NOT_VIABLE", sha)
    if defect == "unended":
        (_job(runs, SMALL, 22) / "termination.env").unlink()
    logs = {"no-orx": [], "orx-exit-5": [_orx(tmp_path, 20, exit_code=5)]}.get(
        defect, [_orx(tmp_path, 20)])
    with pytest.raises(summary.SummaryError):
        summary.load_receipts([receipt], logs)
    assert _main([receipt], tmp_path / "out.json", root, ledger, logs) == 2


def test_a_continuation_needs_its_checkpointed_predecessor(frozen, tmp_path) -> None:
    root, ledger, sha = frozen
    runs = tmp_path / "runs"
    _job(runs, LARGE, 30, seconds=300, reason="signal_TERM_checkpoint_confirmed",
         exit_code="75", checkpoint=True)
    good = _receipt(_job(runs, LARGE, 31, seconds=400, predecessor="30"), LARGE, "NOT_VIABLE",
                    sha, kind="continuation", predecessor="30")
    loaded = summary.load_receipts([good], [_orx(tmp_path, 31)])
    assert loaded[LARGE]["job"]["predecessor_job_id"] == "30"
    unrecorded = tmp_path / "unrecorded"
    _job(unrecorded, LARGE, 30, seconds=300, reason="signal_TERM_checkpoint_confirmed",
         exit_code="75", checkpoint=True)
    fresh = _receipt(_job(unrecorded, LARGE, 31, seconds=400, predecessor="30"), LARGE,
                     "NOT_VIABLE", sha)
    with pytest.raises(summary.SummaryError, match="predecessor"):
        summary.load_receipts([fresh], [_orx(tmp_path, 31)])
    failed = tmp_path / "failed"
    _job(failed, LARGE, 30, seconds=300, reason="workload_failed", exit_code="3")
    orphan = _receipt(_job(failed, LARGE, 31, seconds=400, predecessor="30"), LARGE,
                      "NOT_VIABLE", sha, kind="continuation", predecessor="30")
    with pytest.raises(summary.SummaryError, match="checkpoint"):
        summary.load_receipts([orphan], [_orx(tmp_path, 31)])


def test_inconsistent_receipts_are_refused(frozen, tmp_path) -> None:
    root, ledger, sha = frozen
    runs = tmp_path / "runs"
    small = _receipt(_job(runs, SMALL, 40), SMALL, "GO_ONLY_CAPABLE", sha)
    logs = [_orx(tmp_path, 40, 41, 42, 43)]
    with pytest.raises(summary.SummaryError):
        summary.load_receipts([small, small], logs)
    interrupted = _receipt(_job(runs, LARGE, 41), LARGE, "NOT_VIABLE", sha,
                           status="INTERRUPTED")
    with pytest.raises(summary.SummaryError):
        summary.load_receipts([small, interrupted], logs)
    other = _receipt(_job(tmp_path / "other", LARGE, 42), LARGE, "NOT_VIABLE", "f" * 64)
    with pytest.raises(summary.SummaryError):
        summary.summarise(summary.load_receipts([small, other], logs), ledger=ledger, root=root)
    tiny = _receipt(_job(tmp_path / "tiny", "tiny-hybrid", 43), "tiny-hybrid", "NOT_VIABLE", sha)
    with pytest.raises(summary.SummaryError):
        summary.load_receipts([tiny], logs)


def test_an_invalid_small_lane_ends_the_read(frozen, tmp_path) -> None:
    root, ledger, sha = frozen
    runs = tmp_path / "runs"
    small = _receipt(_job(runs, SMALL, 50), SMALL, "INVALID", sha)
    output = tmp_path / "combined.json"
    assert _main([small], output, root, ledger, [_orx(tmp_path, 50)]) == 0
    read = json.loads(output.read_text())
    assert (read["combined"]["design"], read["combined"]["base"]) == ("INVALID", None)
    assert read["gpu_usage"][LARGE] is None


def test_a_single_lane_is_incomplete(frozen, tmp_path) -> None:
    root, ledger, sha = frozen
    runs = tmp_path / "runs"
    small = _receipt(_job(runs, SMALL, 60), SMALL, "NOT_VIABLE", sha)
    _job(runs, LARGE, 61, seconds=120, reason="workload_failed", exit_code="3")
    output = tmp_path / "combined.json"
    assert _main([small], output, root, ledger, [_orx(tmp_path, 60)], "--run-root",
                 f"{LARGE}={runs / LARGE}") == 0
    read = json.loads(output.read_text())
    assert read["combined"]["design"] == "INCOMPLETE"
    assert read["gpu_usage"][LARGE]["gpu_hours_used"] == pytest.approx(120 / 3600)
