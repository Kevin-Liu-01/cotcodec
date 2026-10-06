from __future__ import annotations

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DOCTOR = _load(
    "past_sm01_job_doctor",
    ROOT / "infra/research/past-bench/sm01_job_doctor.py",
)
CHECKPOINT = _load(
    "past_sm01_checkpoint_runtime",
    ROOT / "infra/research/past-bench/checkpoint_runtime.py",
)
BATCH = ROOT / "infra/slurm/host-single-node/past-bench-sm01.sbatch"
RECOVERY_BATCH = (
    ROOT / "infra/slurm/host-single-node/past-sm01-recover-stop.sbatch"
)
COMPILER = _load(
    "compile_past_bench_sm01_for_job_tests",
    ROOT / "scripts/compile_past_bench_sm01.py",
)
EXPERIMENT = ROOT / "experiments/memory/stage-b-past-sm01-checkpoint.yaml"


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


def _trace_tree(run_root: Path, *, episode_count: int = 8) -> Path:
    traces = run_root / "traces"
    for variant in ("with_persistence", "without_persistence"):
        for index in range(1, episode_count + 1):
            episode = traces / variant / f"{index:02d}_episode"
            episode.mkdir(parents=True, exist_ok=True)
            event = {
                "type": "assistant_message",
                "task": index,
                "variant": variant,
                "content": f"answer-{index}",
                "wall_time_s": 0.25,
                "timestamp": "nondeterministic",
            }
            (episode / "trace.jsonl").write_text(
                json.dumps(event) + "\n", encoding="utf-8"
            )
        (traces / variant / "sequence_summary.json").write_text(
            json.dumps({"variant": variant}), encoding="utf-8"
        )
        (traces / variant / "sequence_results.json").write_text(
            json.dumps(
                {
                    "variant": variant,
                    "episodes": [
                        {
                            "task_id": task_id,
                            "task_score": 1.0,
                            "passed": True,
                            "infra_blocked": False,
                        }
                        for task_id in DOCTOR.TASK_IDS[:3]
                    ]
                    + [
                        {
                            "episode_kind": "reflection",
                            "task_id": f"{DOCTOR.TASK_IDS[2]}_REFLECT",
                            "index": "3r",
                            "bucket": "reflection",
                            "stage": "reflection",
                            "task_score": 0.0,
                            "passed": False,
                            "infra_blocked": False,
                        }
                    ]
                    + [
                        {
                            "task_id": task_id,
                            "task_score": 1.0,
                            "passed": True,
                            "infra_blocked": False,
                        }
                        for task_id in DOCTOR.TASK_IDS[3:]
                    ],
                }
            ),
            encoding="utf-8",
        )
    (traces / "sequence_comparison.json").write_text(
        json.dumps({"delta": 0.5}), encoding="utf-8"
    )
    return traces


def _commit(
    run_root: Path,
    stage: str,
    variant: str | None,
    completed: int,
    *,
    identity: dict[str, object] | None = None,
    episode_results: list[dict[str, object]] | None = None,
) -> None:
    store = CHECKPOINT.CheckpointStore(
        checkpoint_root=run_root / "checkpoints",
        trace_root=run_root / "traces",
        identity=identity or _identity(),
        marker=run_root / "checkpoint.ready",
    )
    store.commit(
        stage=stage,
        variant=variant,
        completed_episode=completed,
        episode_results=episode_results or [],
    )


def _compiled_manifest(
    tmp_path: Path,
    mode: str,
    *,
    predecessor_job_id: int = 321,
    predecessor_checkpoint_sha256: str = "9" * 64,
) -> tuple[Path, dict[str, object]]:
    batch = tmp_path / f"{mode}.sbatch"
    batch.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    args = Namespace(
        experiment=EXPERIMENT,
        mode=mode,
        batch_script=batch,
        predecessor_job_id=predecessor_job_id
        if mode == "fresh-job-resume"
        else None,
        predecessor_checkpoint_sha256=predecessor_checkpoint_sha256
        if mode == "fresh-job-resume"
        else None,
        output=tmp_path / f"{mode}.json",
    )
    manifest = COMPILER.compile_manifest(args)
    manifest["manifest_sha256"] = DOCTOR._root(manifest)
    path = args.output
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path, manifest


def _controlled_stop_results() -> list[dict[str, object]]:
    primary = [
        {
            "task_id": task_id,
            "task_score": 1.0,
            "passed": True,
            "infra_blocked": False,
        }
        for task_id in DOCTOR.TASK_IDS[:3]
    ]
    return [
        *primary,
        {
            "episode_kind": "reflection",
            "task_id": f"{DOCTOR.TASK_IDS[2]}_REFLECT",
            "index": "3r",
            "bucket": "reflection",
            "stage": "reflection",
            "task_score": 0.0,
            "passed": False,
            "infra_blocked": False,
        },
    ]


def test_finalize_complete_sm01_run(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    _trace_tree(run_root)
    _commit(run_root, "run-complete", None, 8)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "execution-identity.json").write_text(
        json.dumps(_identity()), encoding="utf-8"
    )

    report = DOCTOR.finalize(
        mode="uninterrupted",
        run_root=run_root,
        evidence_root=evidence,
        slurm_job_id=237,
    )

    assert report["status"] == "PAST_SM01_UNINTERRUPTED_PASS"
    assert report["trace_count"] == 16
    assert len(report["trace_projection_root_sha256"]) == 64


def test_finalize_stop_requires_exact_episode_three(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    _trace_tree(run_root)
    _commit(run_root, "episode-complete", "with_persistence", 2)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "execution-identity.json").write_text(
        json.dumps(_identity()), encoding="utf-8"
    )

    with pytest.raises(DOCTOR.Sm01DoctorError, match="episode three"):
        DOCTOR.finalize(
            mode="stop-after-episode-three",
            run_root=run_root,
            evidence_root=evidence,
            slurm_job_id=238,
        )


def test_finalize_stop_rejects_future_episode_artifact(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    _trace_tree(run_root, episode_count=4)
    _commit(
        run_root,
        "episode-complete",
        "with_persistence",
        3,
        episode_results=_controlled_stop_results(),
    )
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "execution-identity.json").write_text(
        json.dumps(_identity()), encoding="utf-8"
    )

    with pytest.raises(DOCTOR.Sm01DoctorError, match="post-checkpoint"):
        DOCTOR.finalize(
            mode="stop-after-episode-three",
            run_root=run_root,
            evidence_root=evidence,
            slurm_job_id=238,
        )


def test_finalize_stop_accepts_registered_reflection(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    _trace_tree(run_root, episode_count=3)
    _commit(
        run_root,
        "episode-complete",
        "with_persistence",
        3,
        episode_results=_controlled_stop_results(),
    )
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "execution-identity.json").write_text(
        json.dumps(_identity()), encoding="utf-8"
    )

    report = DOCTOR.finalize(
        mode="stop-after-episode-three",
        run_root=run_root,
        evidence_root=evidence,
        slurm_job_id=246,
    )

    assert report["status"] == DOCTOR.CONTROLLED_STOP_STATUS
    assert report["completed_episode"] == 3


def test_recover_stop_records_both_slurm_jobs(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    _trace_tree(run_root, episode_count=3)
    _commit(
        run_root,
        "episode-complete",
        "with_persistence",
        3,
        episode_results=_controlled_stop_results(),
    )
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "execution-identity.json").write_text(
        json.dumps(_identity()), encoding="utf-8"
    )
    (tmp_path / "allocation-stop-after-episode-three.txt").write_text(
        "JobId=246 TimeLimit=00:30:00\n", encoding="utf-8"
    )
    (evidence / "termination-stop-after-episode-three.txt").write_text(
        "exit_code=1\ntermination_reason=running\nsignal_requested=false\n",
        encoding="utf-8",
    )
    (evidence / "past-stop-after-episode-three.stdout").write_text(
        "CHECKPOINT_STOP variant=with_persistence completed_episode=3\n",
        encoding="utf-8",
    )
    (evidence / "gpu-inventory-stop-after-episode-three.txt").write_text(
        "NVIDIA H100, GPU-one, driver\nNVIDIA H100, GPU-two, driver\n",
        encoding="utf-8",
    )

    report = DOCTOR.recover_stop(
        run_root=run_root,
        evidence_root=evidence,
        workload_slurm_job_id=246,
        validation_slurm_job_id=247,
    )

    assert report["status"] == DOCTOR.RECOVERED_STOP_STATUS
    assert report["slurm_job_id"] == 246
    assert report["validation_slurm_job_id"] == 247


def test_recover_complete_records_both_slurm_jobs(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    _trace_tree(run_root)
    _commit(run_root, "run-complete", None, 8)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "execution-identity.json").write_text(
        json.dumps(_identity()), encoding="utf-8"
    )
    (evidence / "resume-prefix-before.json").write_text(
        json.dumps(DOCTOR._prefix_manifest(run_root / "traces", 3)),
        encoding="utf-8",
    )
    (tmp_path / "allocation-fresh-job-resume.txt").write_text(
        "JobId=250 TimeLimit=01:30:00\n", encoding="utf-8"
    )
    (evidence / "termination-fresh-job-resume.txt").write_text(
        "exit_code=1\ntermination_reason=artifact_finalization_failed\n"
        "signal_requested=false\n",
        encoding="utf-8",
    )
    (evidence / "past-fresh-job-resume.stdout").write_text(
        "Summary [with_persistence]\nSummary [without_persistence]\nComparison\n",
        encoding="utf-8",
    )
    (evidence / "gpu-inventory-fresh-job-resume.txt").write_text(
        "NVIDIA H100, GPU-one, driver\nNVIDIA H100, GPU-two, driver\n",
        encoding="utf-8",
    )

    report = DOCTOR.recover_complete(
        run_root=run_root,
        evidence_root=evidence,
        workload_slurm_job_id=250,
        validation_slurm_job_id=252,
    )

    assert report["status"] == DOCTOR.RECOVERED_RESUME_STATUS
    assert report["slurm_job_id"] == 250
    assert report["validation_slurm_job_id"] == 252


@pytest.mark.parametrize("field", ["logical_workload_argv", "server_argv"])
def test_manifest_doctor_rejects_argv_injection(tmp_path: Path, field: str) -> None:
    path, manifest = _compiled_manifest(tmp_path, "uninterrupted")
    manifest[field] = [*manifest[field], "--malicious-option"]
    unsigned = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    manifest["manifest_sha256"] = DOCTOR._root(unsigned)
    path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(DOCTOR.Sm01DoctorError, match="execution identity"):
        DOCTOR._validate_manifest(
            path,
            expected_sha256=manifest["manifest_sha256"],
            mode="uninterrupted",
        )


def test_finalize_rejects_checkpoint_payload_tamper(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    _trace_tree(run_root)
    _commit(run_root, "run-complete", None, 8)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "execution-identity.json").write_text(
        json.dumps(_identity()), encoding="utf-8"
    )
    pointer = json.loads((run_root / "checkpoints/LATEST").read_text(encoding="utf-8"))
    payload_file = next(
        path
        for path in (run_root / "checkpoints" / pointer["generation"] / "payload").rglob("*")
        if path.is_file()
    )
    payload_file.write_text("tampered", encoding="utf-8")

    with pytest.raises(DOCTOR.Sm01DoctorError, match="payload bytes"):
        DOCTOR.finalize(
            mode="uninterrupted",
            run_root=run_root,
            evidence_root=evidence,
            slurm_job_id=237,
        )


def test_resume_preflight_binds_fresh_job_and_predecessor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_root = tmp_path / "run"
    _trace_tree(run_root, episode_count=3)
    stop_path, stop_manifest = _compiled_manifest(tmp_path, "stop-after-episode-three")
    del stop_path
    identity = stop_manifest["execution_identity"]
    assert isinstance(identity, dict)
    _commit(
        run_root,
        "episode-complete",
        "with_persistence",
        3,
        identity=identity,
        episode_results=_controlled_stop_results(),
    )
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "execution-identity.json").write_text(
        json.dumps(identity), encoding="utf-8"
    )
    DOCTOR.finalize(
        mode="stop-after-episode-three",
        run_root=run_root,
        evidence_root=evidence,
        slurm_job_id=321,
    )
    pointer_sha256 = DOCTOR._sha256(run_root / "checkpoints/LATEST")
    resume_path, resume_manifest = _compiled_manifest(
        tmp_path,
        "fresh-job-resume",
        predecessor_checkpoint_sha256=pointer_sha256,
    )
    monkeypatch.setattr(
        DOCTOR,
        "_validate_sequence",
        lambda: {
            "sequence_sha256": DOCTOR.SEQUENCE_SHA256,
            "episodes": [],
            "episode_root": "a" * 64,
        },
    )

    report = DOCTOR.preflight(
        manifest_path=resume_path,
        manifest_sha256=resume_manifest["manifest_sha256"],
        mode="fresh-job-resume",
        run_root=run_root,
        evidence_root=evidence,
        slurm_job_id=322,
    )

    assert report["slurm_job_id"] == 322
    assert report["resume_checkpoint_pointer_sha256"] == pointer_sha256
    assert report["predecessor_checkpoint_snapshot"]["status"] == (
        "PAST_SM01_PREDECESSOR_CHECKPOINT_SNAPSHOTTED"
    )
    assert (evidence / "predecessor-checkpoint/receipt.json").is_file()


def test_resume_preflight_accepts_transparent_recovered_stop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_root = tmp_path / "run"
    _trace_tree(run_root, episode_count=3)
    _, stop_manifest = _compiled_manifest(tmp_path, "stop-after-episode-three")
    identity = stop_manifest["execution_identity"]
    assert isinstance(identity, dict)
    _commit(
        run_root,
        "episode-complete",
        "with_persistence",
        3,
        identity=identity,
        episode_results=_controlled_stop_results(),
    )
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "execution-identity.json").write_text(
        json.dumps(identity), encoding="utf-8"
    )
    (tmp_path / "allocation-stop-after-episode-three.txt").write_text(
        "JobId=321 TimeLimit=00:30:00\n", encoding="utf-8"
    )
    (evidence / "termination-stop-after-episode-three.txt").write_text(
        "exit_code=1\ntermination_reason=running\nsignal_requested=false\n",
        encoding="utf-8",
    )
    (evidence / "past-stop-after-episode-three.stdout").write_text(
        "CHECKPOINT_STOP variant=with_persistence completed_episode=3\n",
        encoding="utf-8",
    )
    (evidence / "gpu-inventory-stop-after-episode-three.txt").write_text(
        "NVIDIA H100, GPU-one, driver\nNVIDIA H100, GPU-two, driver\n",
        encoding="utf-8",
    )
    DOCTOR.recover_stop(
        run_root=run_root,
        evidence_root=evidence,
        workload_slurm_job_id=321,
        validation_slurm_job_id=323,
    )
    pointer_sha256 = DOCTOR._sha256(run_root / "checkpoints/LATEST")
    resume_path, resume_manifest = _compiled_manifest(
        tmp_path,
        "fresh-job-resume",
        predecessor_checkpoint_sha256=pointer_sha256,
    )
    monkeypatch.setattr(
        DOCTOR,
        "_validate_sequence",
        lambda: {
            "sequence_sha256": DOCTOR.SEQUENCE_SHA256,
            "episodes": [],
            "episode_root": "a" * 64,
        },
    )

    report = DOCTOR.preflight(
        manifest_path=resume_path,
        manifest_sha256=resume_manifest["manifest_sha256"],
        mode="fresh-job-resume",
        run_root=run_root,
        evidence_root=evidence,
        slurm_job_id=322,
    )

    assert report["slurm_job_id"] == 322
    assert report["resume_checkpoint_pointer_sha256"] == pointer_sha256


def test_projection_ignores_only_registered_timing_fields(tmp_path: Path) -> None:
    left = tmp_path / "left"
    right = tmp_path / "right"
    for root, timestamp, content in (
        (left, "one", "same"),
        (right, "two", "same"),
    ):
        root.mkdir()
        (root / "trace.jsonl").write_text(
            json.dumps({"timestamp": timestamp, "content": content}) + "\n",
            encoding="utf-8",
        )
    assert (
        DOCTOR._trace_projection(left)["projection_root_sha256"]
        == DOCTOR._trace_projection(right)["projection_root_sha256"]
    )
    (right / "trace.jsonl").write_text(
        json.dumps({"timestamp": "three", "content": "changed"}) + "\n",
        encoding="utf-8",
    )
    assert (
        DOCTOR._trace_projection(left)["projection_root_sha256"]
        != DOCTOR._trace_projection(right)["projection_root_sha256"]
    )


def test_resume_prefix_allows_new_control_arm_but_rejects_mutation() -> None:
    before = [{"path": "with_persistence/01_episode/trace.jsonl", "sha256": "a"}]
    after = [
        *before,
        {"path": "without_persistence/01_episode/trace.jsonl", "sha256": "b"},
    ]
    DOCTOR._validate_preserved_prefix(before, after)
    with pytest.raises(DOCTOR.Sm01DoctorError, match="modified"):
        DOCTOR._validate_preserved_prefix(
            before,
            [
                {
                    "path": "with_persistence/01_episode/trace.jsonl",
                    "sha256": "changed",
                }
            ],
        )


def test_sm01_batch_is_contained_checkpointed_and_h100_only() -> None:
    content = BATCH.read_text(encoding="utf-8")
    assert "#SBATCH --gres=gpu:h100:2" in content
    assert "docker network create --internal" in content
    assert "--pull=never" in content
    assert "--resume-checkpoint" not in content
    assert "actual_control_argv_suffix" in content
    assert "COTCODEC_CHECKPOINT_MARKER=/outputs/checkpoint.ready" in content
    assert "sm01-runtime.yaml" in content
    assert "PAST_SM01_RUNTIME_CONFIG_PASS" in content
    assert "prepare_hermes_offline_bootstrap.py" in content
    assert "termination_reason=artifact_finalization_failed" in content
    assert content.count('--volume "${tools_root}:/tools:ro"') >= 2
    assert "docker kill --signal=USR1" in content
    assert "--cap-drop ALL" in content
    assert 'TimeLimit=${expected_time_limit}' in content
    assert content.count("--root /model --receipt /input/model-receipt.json") == 1
    assert "sudo" not in content
    assert "/var/run/docker.sock" not in content


def test_sm01_recovery_batch_is_cpu_only_contained_and_explicit() -> None:
    content = RECOVERY_BATCH.read_text(encoding="utf-8")
    assert "#SBATCH --gres" not in content
    assert "--network none" in content
    assert "--pull=never" in content
    assert "recover-stop" in content
    assert "--workload-slurm-job-id" in content
    assert "--validation-slurm-job-id" in content
    assert "sudo" not in content
    assert "/var/run/docker.sock" not in content
