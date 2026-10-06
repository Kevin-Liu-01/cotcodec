from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/compile_past_bench_sm01.py"
SPEC = importlib.util.spec_from_file_location("compile_past_bench_sm01", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
EXPERIMENT = ROOT / "experiments/memory/stage-b-past-sm01-checkpoint.yaml"


def _args(tmp_path: Path, mode: str) -> argparse.Namespace:
    batch = tmp_path / "past-sm01.sbatch"
    batch.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    return argparse.Namespace(
        experiment=EXPERIMENT,
        mode=mode,
        batch_script=batch,
        predecessor_job_id=321 if mode == "fresh-job-resume" else None,
        predecessor_checkpoint_sha256="9" * 64
        if mode == "fresh-job-resume"
        else None,
        output=tmp_path / "manifest.json",
    )


@pytest.mark.parametrize(
    ("mode", "suffix", "minutes", "gpu_hours"),
    [
        ("uninterrupted", [], 90, 3),
        ("stop-after-episode-three", ["--stop-after-episode", "3"], 30, 1),
        ("fresh-job-resume", ["--resume-checkpoint"], 90, 3),
    ],
)
def test_compiler_emits_registered_mode(
    tmp_path: Path,
    mode: str,
    suffix: list[str],
    minutes: int,
    gpu_hours: int,
) -> None:
    manifest = MODULE.compile_manifest(_args(tmp_path, mode))

    assert manifest["mode"] == mode
    assert manifest["actual_control_argv_suffix"] == suffix
    assert manifest["budget"] == {
        "minutes": minutes,
        "max_gpu_hours": gpu_hours,
    }
    assert manifest["sequence"]["task_ids"] == MODULE.EXPECTED_TASK_IDS
    assert "--resume-checkpoint" not in manifest["logical_workload_argv"]
    assert "--stop-after-episode" not in manifest["logical_workload_argv"]
    assert manifest["execution_identity"]["argv"] == manifest["logical_workload_argv"]
    assert manifest["runtime_config"] == {
        "path": MODULE.RUNTIME_CONFIG_PATH,
        "sha256": MODULE.RUNTIME_CONFIG_SHA256,
        "cache_dir": "/state/runtime_cache",
    }
    assert "--generation-config" in manifest["server_argv"]
    assert manifest["scientific_result"] is False


def test_resume_requires_predecessor_binding(tmp_path: Path) -> None:
    args = _args(tmp_path, "fresh-job-resume")
    args.predecessor_job_id = None
    with pytest.raises(ValueError, match="requires predecessor"):
        MODULE.compile_manifest(args)


def test_compiler_rejects_experiment_drift(tmp_path: Path) -> None:
    raw = yaml.safe_load(EXPERIMENT.read_text(encoding="utf-8"))
    raw["source"]["expected_task_ids"] = list(reversed(MODULE.EXPECTED_TASK_IDS))
    experiment = tmp_path / "experiment.yaml"
    experiment.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    args = _args(tmp_path, "uninterrupted")
    args.experiment = experiment

    with pytest.raises(ValueError, match="scientific contract"):
        MODULE.compile_manifest(args)


def test_runtime_config_is_exact_and_writable_outside_source_tree() -> None:
    path = ROOT / "infra/research/past-bench/sm01-runtime.yaml"
    assert MODULE._sha256(path) == MODULE.RUNTIME_CONFIG_SHA256
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert config == {
        "runtime": {
            "mode": "local",
            "temperature": 0.0,
            "cache_dir": "/state/runtime_cache",
            "registry_path": "configs/agents.yaml",
        }
    }
