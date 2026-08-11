from __future__ import annotations

import pytest

from scripts.submit_tinker_job import sbatch_argv, validate_manifest


def _manifest() -> dict:
    return {
        "backend": "tinker",
        "name": "capsule-kimi-contract",
        "image": "registry.example/cotcodec@sha256:" + "a" * 64,
        "command": [
            "uv",
            "run",
            "python",
            "scripts/run_tinker_training.py",
            "experiments/tinker/capsule-policy-kimi.yaml",
            "--seed",
            "42",
            "--train-jsonl",
            "/inputs/train.jsonl",
        ],
        "run_root": "/shared/cotcodec/tinker-runs",
        "git_sha": "a" * 40,
        "source_sha256": "b" * 64,
        "contract": "experiments/tinker/capsule-policy-kimi.yaml",
        "contract_sha256": "c" * 64,
        "train_jsonl": "/shared/cotcodec/datasets/train.jsonl",
        "train_sha256": "d" * 64,
        "seeds": [42, 43, 44],
        "run_seed": 42,
        "resources": {"cpus": 8, "memory_gb": 32, "minutes": 240},
        "budget": {"max_usd": 6},
    }


def test_tinker_manifest_builds_cpu_only_allowlisted_submission() -> None:
    manifest = validate_manifest(_manifest())
    argv = sbatch_argv(manifest, test_only=True)
    assert not any("--gres" in argument for argument in argv)
    assert argv[-1] == "infra/slurm/tinker.sbatch"
    export_arg = next(argument for argument in argv if argument.startswith("--export="))
    assert "TINKER_API_KEY" not in export_arg
    assert "ALL" not in export_arg
    assert "--test-only" in argv


def test_tinker_manifest_rejects_local_gpu_allocation() -> None:
    raw = _manifest()
    raw["resources"]["gpus"] = 1
    with pytest.raises(ValueError, match="CPU-only"):
        validate_manifest(raw)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), 0, -1, 51])
def test_tinker_manifest_rejects_invalid_cost_ceiling(value: float) -> None:
    raw = _manifest()
    raw["budget"]["max_usd"] = value
    with pytest.raises(ValueError, match="max_usd"):
        validate_manifest(raw)


def test_tinker_manifest_rejects_embedded_credentials() -> None:
    raw = _manifest()
    raw["tinker_api_key"] = "secret"
    with pytest.raises(ValueError, match="secret material"):
        validate_manifest(raw)


def test_tinker_manifest_rejects_contract_traversal() -> None:
    raw = _manifest()
    raw["contract"] = "experiments/tinker/../private.yaml"
    with pytest.raises(ValueError, match="repository-relative"):
        validate_manifest(raw)


def test_tinker_manifest_requires_a_registered_run_seed() -> None:
    raw = _manifest()
    raw["run_seed"] = 99
    with pytest.raises(ValueError, match="registered seeds"):
        validate_manifest(raw)


def test_tinker_manifest_binds_command_seed_and_dataset_mount() -> None:
    raw = _manifest()
    raw["command"][raw["command"].index("42")] = "43"
    with pytest.raises(ValueError, match="match run_seed"):
        validate_manifest(raw)
