from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts import submit_research_job
from scripts.submit_docker_research_job import (
    ARCHIVED_MEMORY_ENTRY_POINTS,
    BATCH_SCRIPT,
    RUNTIME,
    archived_memory_reference,
    prepare_run_root,
    sbatch_argv,
    seed_option_abbreviation,
    validate_manifest,
    validate_memory_job_admission,
)

ARCHIVED_PREFIX = "memory workloads were archived under legacy/"


def _manifest() -> dict:
    return {
        "runtime": RUNTIME,
        "name": "qwen-smoke",
        "image_id": "sha256:" + "a" * 64,
        "command": [
            "python",
            "scripts/run_translation_supervised_indexer_doctor.py",
            "--output",
            "/outputs/receipt.json",
            "--seeds",
            "42",
            "43",
            "44",
        ],
        "run_root": "/home/kevin/cotcodec-runs/research",
        "git_sha": "b" * 40,
        "source_sha256": "c" * 64,
        "model": {
            "cache_host_path": "/home/kevin/cotcodec-runs/hf-cache",
            "model_id": "qwen3.5-4b",
            "revision": "d" * 40,
            "receipt_sha256": "e" * 64,
            "artifact_root_sha256": "f" * 64,
        },
        "seeds": [42, 43, 44],
        "seed_binding": {"flag": "--seeds"},
        "resources": {
            "gpu_type": "h100",
            "gpus": 1,
            "cpus": 8,
            "memory_gb": 32,
            "minutes": 30,
        },
        "budget": {"max_gpu_hours": 0.5},
    }


def test_docker_manifest_builds_bounded_slurm_submission() -> None:
    manifest = validate_manifest(_manifest())
    argv = sbatch_argv(manifest, test_only=True)
    assert "--partition=research" in argv
    assert "--gres=gpu:h100:1" in argv
    assert "--time=00:30:00" in argv
    assert "--test-only" in argv
    export = next(argument for argument in argv if argument.startswith("--export="))
    assert "COTCODEC_IMAGE_ID=sha256:" + "a" * 64 in export
    assert "COTCODEC_RUN_ROOT_HEX=" in export
    assert "COTCODEC_MODEL_CACHE_HOST_HEX=" in export
    assert "/home/kevin" not in export
    assert "ALL" not in export


def test_submitter_direct_cli_resolves_project_imports() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/submit_docker_research_job.py", "--help"],
        cwd=BATCH_SCRIPT.parents[3],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert "manifest" in completed.stdout


def test_submitter_can_seal_dry_run_without_shell_redirection(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.yaml"
    output_path = tmp_path / "dry-run.json"
    manifest_path.write_text(yaml.safe_dump(_manifest()), encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/submit_docker_research_job.py",
            str(manifest_path),
            "--dry-run",
            "--dry-run-output",
            str(output_path),
        ],
        cwd=BATCH_SCRIPT.parents[3],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["runtime"] == RUNTIME
    assert payload["gpu_hours"] == 0.5
    repeated = subprocess.run(
        [
            sys.executable,
            "scripts/submit_docker_research_job.py",
            str(manifest_path),
            "--dry-run",
            "--dry-run-output",
            str(output_path),
        ],
        cwd=BATCH_SCRIPT.parents[3],
        check=False,
        capture_output=True,
        text=True,
    )
    assert repeated.returncode != 0
    assert "already exists" in repeated.stderr


def test_submitter_precreates_only_a_nonsymlink_persistent_run_root(tmp_path: Path) -> None:
    base = tmp_path / "runs"
    base.mkdir()
    manifest = {"run_root": str(base / "nested" / "experiment")}
    created = prepare_run_root(manifest, allowed_roots=(base,))
    assert created.is_dir()
    assert not created.is_symlink()

    outside = tmp_path / "outside"
    outside.mkdir()
    with pytest.raises(ValueError, match="outside the dedicated"):
        prepare_run_root({"run_root": str(outside)}, allowed_roots=(base,))

    link = base / "link"
    link.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink component"):
        prepare_run_root({"run_root": str(link / "child")}, allowed_roots=(base,))


def test_docker_manifest_rejects_export_injection_and_paths() -> None:
    raw = _manifest()
    raw["image_id"] = "sha256:" + "a" * 63 + ","
    with pytest.raises(ValueError, match="exact local Docker"):
        validate_manifest(raw)
    raw = _manifest()
    raw["model"]["cache_host_path"] = "/home/kevin/cache,ALL"
    with pytest.raises(ValueError, match="simple absolute path"):
        validate_manifest(raw)


@pytest.mark.parametrize("ceiling", [float("nan"), float("inf"), 0, -1])
def test_docker_manifest_rejects_invalid_budget(ceiling: float) -> None:
    raw = _manifest()
    raw["budget"]["max_gpu_hours"] = ceiling
    with pytest.raises(ValueError, match="positive finite"):
        validate_manifest(raw)


def test_docker_manifest_rejects_allocation_above_budget() -> None:
    raw = _manifest()
    raw["resources"]["gpus"] = 8
    with pytest.raises(ValueError, match="above budget"):
        validate_manifest(raw)


def test_docker_manifest_binds_public_benchmark_provenance_and_mount() -> None:
    raw = _manifest()
    raw["command"][4:4] = [
        "--public-benchmark-path",
        "/inputs/longmemeval_s_cleaned.json",
    ]
    raw["public_benchmark"] = {
        "source_id": "longmemeval-s-cleaned",
        "revision": "2" * 40,
        "license": "MIT",
        "host_path": "/home/kevin/cotcodec-runs/inputs/longmemeval_s_cleaned.json",
        "sha256": "3" * 64,
        "size_bytes": 15_388_478,
    }
    manifest = validate_manifest(raw)
    assert manifest["public_benchmark"]["container_path"] == ("/inputs/longmemeval_s_cleaned.json")
    argv = sbatch_argv(manifest, test_only=False)
    export = next(argument for argument in argv if argument.startswith("--export="))
    assert "COTCODEC_PUBLIC_BENCHMARK_HOST_HEX=" in export
    assert "COTCODEC_PUBLIC_BENCHMARK_SHA256=" + "3" * 64 in export
    assert "COTCODEC_PUBLIC_BENCHMARK_SIZE=15388478" in export
    assert "/home/kevin" not in export


def test_docker_manifest_rejects_unmounted_or_drifting_public_benchmark() -> None:
    raw = _manifest()
    raw["command"][4:4] = [
        "--public-benchmark-path",
        "/inputs/longmemeval_s_cleaned.json",
    ]
    with pytest.raises(ValueError, match="without a hash-bound mount"):
        validate_manifest(raw)

    raw["public_benchmark"] = {
        "source_id": "longmemeval-s-cleaned",
        "revision": "2" * 40,
        "license": "MIT",
        "host_path": "/home/kevin/inputs/longmemeval.json",
        "sha256": "3" * 64,
        "size_bytes": 0,
    }
    with pytest.raises(ValueError, match="positive bounded integer"):
        validate_manifest(raw)

    raw["public_benchmark"]["size_bytes"] = 15_388_478
    raw["public_benchmark"]["container_path"] = "/inputs/other.json"
    with pytest.raises(ValueError, match="container_path is fixed"):
        validate_manifest(raw)


def test_docker_manifest_binds_generic_study_artifact_read_only() -> None:
    raw = _manifest()
    raw["command"][4:4] = [
        "--evidence",
        "/inputs/study-artifact.json",
        "--expected-evidence-sha256",
        "4" * 64,
    ]
    raw["study_artifact"] = {
        "source_id": "gaama-natural-v5",
        "revision": "2" * 40,
        "license": "CC-BY-NC-4.0",
        "host_path": "/shared/inputs/gaama-natural-v5.json",
        "sha256": "4" * 64,
        "size_bytes": 2_100_000,
    }
    manifest = validate_manifest(raw)
    assert manifest["study_artifact"]["container_path"] == "/inputs/study-artifact.json"
    export = next(
        value
        for value in sbatch_argv(manifest, test_only=True)
        if value.startswith("--export=")
    )
    assert "COTCODEC_STUDY_ARTIFACT_HOST_HEX=" in export
    assert "COTCODEC_STUDY_ARTIFACT_SHA256=" + "4" * 64 in export
    assert "/shared/inputs" not in export
    batch = BATCH_SCRIPT.read_text(encoding="utf-8")
    assert 'sha256sum "${study_artifact_host}"' in batch
    assert '"${study_artifact_host}:/inputs/study-artifact.json:ro"' in batch


def test_docker_manifest_rejects_unbound_or_mislabeled_study_artifact() -> None:
    raw = _manifest()
    raw["command"][4:4] = [
        "--evidence",
        "/inputs/study-artifact.json",
        "--expected-evidence-sha256",
        "4" * 64,
    ]
    with pytest.raises(ValueError, match="without a hash-bound mount"):
        validate_manifest(raw)

    raw["study_artifact"] = {
        "source_id": "gaama-natural-v5",
        "revision": "2" * 40,
        "license": "CC-BY-NC-4.0",
        "host_path": "/shared/inputs/gaama-natural-v5.json",
        "sha256": "5" * 64,
        "size_bytes": 2_100_000,
    }
    with pytest.raises(ValueError, match="differs from the claim admission contract"):
        validate_manifest(raw)


def test_docker_batch_reverifies_and_read_only_mounts_public_benchmark() -> None:
    content = BATCH_SCRIPT.read_text(encoding="utf-8")
    assert 'sha256sum "${public_benchmark_host}"' in content
    assert "stat -c '%s' \"${public_benchmark_host}\"" in content
    assert '"${public_benchmark_host}:/inputs/longmemeval_s_cleaned.json:ro"' in content
    assert "executed seeds do not exactly match declared seeds" in content
    assert 'echo "randomness_contract=${COTCODEC_RANDOMNESS_CONTRACT}"' in content


def test_archived_memory_workloads_fail_closed() -> None:
    raw = _manifest()
    raw["command"] = ["python", "scripts/run_memory_model_screen.py", "--output-dir", "/outputs"]
    with pytest.raises(ValueError, match="archived under legacy"):
        validate_manifest(raw)


def test_memory_admission_block_fails_closed_even_for_other_commands() -> None:
    raw = _manifest()
    raw["memory_source_admission"] = {"scope": "external-sources"}
    with pytest.raises(ValueError, match="archived under legacy"):
        validate_manifest(raw)


def _deterministic_manifest() -> dict:
    raw = _manifest()
    raw["randomness_contract"] = "deterministic"
    raw["seeds"] = []
    del raw["seed_binding"]
    raw["command"] = raw["command"][:4]
    return raw


def _export(manifest: dict) -> dict[str, str]:
    argument = next(
        value for value in sbatch_argv(manifest, test_only=True) if value.startswith("--export=")
    )
    return dict(item.split("=", 1) for item in argument.removeprefix("--export=").split(","))


def _decoded_manifest(export: dict[str, str]) -> dict:
    return json.loads(bytes.fromhex(export["COTCODEC_MANIFEST_JSON_HEX"]))


# Every variable the submitter exported before the opt-in fields existed, in order.
PREEXISTING_EXPORT_KEYS = [
    "COTCODEC_IMAGE_ID",
    "COTCODEC_COMMAND_JSON_HEX",
    "COTCODEC_MANIFEST_JSON_HEX",
    "COTCODEC_RUN_ROOT_HEX",
    "COTCODEC_GIT_SHA",
    "COTCODEC_SOURCE_SHA256",
    "COTCODEC_RANDOMNESS_CONTRACT",
    "COTCODEC_SEEDS",
    "COTCODEC_EXPECTED_GPUS",
    "COTCODEC_BATCH_SHA256",
    "COTCODEC_MODEL_CACHE_HOST_HEX",
    "COTCODEC_MODEL_ID",
    "COTCODEC_MODEL_REVISION",
    "COTCODEC_MODEL_RECEIPT_SHA256",
    "COTCODEC_MODEL_ARTIFACT_ROOT",
]
PREEXISTING_MANIFEST_KEYS = {
    "schema_version",
    "runtime",
    "name",
    "image_id",
    "command",
    "run_root",
    "git_sha",
    "source_sha256",
    "randomness_contract",
    "seeds",
    "model",
    "gpu_type",
    "gpus",
    "cpus",
    "memory_gb",
    "minutes",
    "max_gpu_hours",
    "batch_script_sha256",
}


@pytest.mark.parametrize("contract", ["deterministic", "deterministic-all-serve"])
def test_manifest_without_opt_in_fields_exports_exactly_the_preexisting_contract(
    contract: str,
) -> None:
    raw = _deterministic_manifest()
    raw["randomness_contract"] = contract
    export = _export(validate_manifest(raw))
    assert list(export) == PREEXISTING_EXPORT_KEYS
    assert export["COTCODEC_SEEDS"] == "none"
    assert export["COTCODEC_MODEL_ID"] == "qwen3.5-4b"
    decoded = _decoded_manifest(export)
    assert set(decoded) == PREEXISTING_MANIFEST_KEYS
    assert set(decoded["model"]) == {
        "cache_host_path",
        "model_id",
        "revision",
        "receipt_sha256",
        "artifact_root_sha256",
    }


# R1: precise archived-memory rule ------------------------------------------------

ARCHIVED_ARGV_ELEMENTS = [
    "scripts/run_memory_model_screen.py",
    "./scripts/run_memory_trials.py",
    "/workspace/cotcodec/scripts/run_memory_model_replay_doctor.py",
    "legacy/scripts/run_memory_frontier_screen.py",
    "scripts/run_letta_baseline.py",
    "scripts/run_letta",
    "scripts/compare_memory_model_outputs.py",
    "harness/memory_trials/runner.py",
    "harness/memory_trials",
    "scripts.run_memory_trials",
    "harness.memory_trials.runner",
    "--memory-bundle",
    "--memory-bundle=/inputs/memory-selection-bundle.json",
    "--memory-treatment-mode",
    "--expected-memory-system-id",
    "python scripts/run_memory_trials.py --seeds 1",
    # Review findings on 5ed577d: forms that reached archived code.
    "-mlegacy.scripts.run_memory_model_screen",
    "-mharness.memory_trials",
    "-Bmlegacy.harness.causal_memory_trials",
    "PYTHONPATH=legacy/scripts",
    "--chdir=legacy/scripts",
    "legacy/scripts",
    "legacy",
    "./legacy/",
    "run_memory_model_screen",
    "run_memory_trials.py",
    "from legacy.harness import memory_trials",
    "import runpy; runpy.run_path('legacy/scripts/run_mem0_lifecycle_doctor.py')",
    "cd legacy && python scripts/run_mem0_lifecycle_doctor.py",
    "legacy/scripts/run_memorybank_decay_container.py",
    "legacy.harness.causal_memory_trials",
    "legacy/scripts/run_memgpt_letta_lifecycle_doctor.py",
    "legacy/infra/memory-baselines/graphiti_sidecar.py",
    "legacy/experiments/memory/stage1-longmemeval-screen.yaml",
    "scripts/run_memorybank_decay_doctor.py",
    "harness/causal_memory_trials.py",
    "--memory-bund",
    "--memory-bund=/inputs/memory-selection-bundle.json",
    "--expected-memory-sys",
]
ADMITTED_ARGV_ELEMENTS = [
    "--gpu-memory-utilization",
    "0.9",
    "--gpu-memory-utilization=0.9",
    "--kv-cache-memory-bytes",
    "--enable-memory-profiling",
    "/outputs/memory.json",
    "scripts/memory_profile.py",
    "scripts/run_translation_supervised_indexer_doctor.py",
    "harness/memory_trials_v2/runner.py",
    "memory",
    "legacy-2026-10-06",
    "--legacy-format",
    "/outputs/legacy_scores.json",
    "-m",
    "-mvllm.entrypoints.openai.api_server",
    "--",
]


def _archived_memory_tree() -> set[str]:
    """Memory-named files and packages directly under the archived trees, by stem."""

    root = BATCH_SCRIPT.parents[3] / "legacy"
    names = set()
    for base in ("scripts", "harness", "infra"):
        for path in (root / base).iterdir():
            if path.name.startswith(".") or path.name == "__pycache__":
                continue
            lowered = path.name.lower()
            if "mem" in lowered or "letta" in lowered:
                names.add(path.name.removesuffix(".py").removesuffix(".sh"))
    return names


def _batch_archived_rule() -> dict:
    """Execute the batch script's archived-memory block exactly as written."""

    content = BATCH_SCRIPT.read_text(encoding="utf-8")
    block = (
        content.split("# BEGIN archived-memory-rule", 1)[1]
        .split("\n", 1)[1]
        .split("# END archived-memory-rule", 1)[0]
    )
    namespace: dict = {}
    exec(  # noqa: S102 - the batch script's own admission code, read from the repo
        "import re\nfrom fnmatch import fnmatchcase\nfrom pathlib import PurePosixPath\n"
        + block,
        namespace,
    )
    return namespace


@pytest.mark.parametrize("element", ARCHIVED_ARGV_ELEMENTS)
@pytest.mark.parametrize(
    "check",
    [
        validate_memory_job_admission,
        submit_research_job.validate_memory_job_admission,
    ],
    ids=["docker-submitter", "research-submitter"],
)
def test_archived_memory_interface_is_rejected_by_both_submitters(check, element: str) -> None:
    with pytest.raises(ValueError, match=f"^{ARCHIVED_PREFIX}"):
        check(None, command=["python", element], has_memory_bundle=False)


@pytest.mark.parametrize("element", ADMITTED_ARGV_ELEMENTS)
def test_memory_words_outside_the_archived_interface_are_admitted(element: str) -> None:
    assert archived_memory_reference(element) is None
    assert submit_research_job.archived_memory_reference(element) is None
    validate_memory_job_admission(None, command=["python", element], has_memory_bundle=False)


def test_both_submitters_and_the_batch_script_share_one_archived_memory_rule() -> None:
    batch = _batch_archived_rule()
    assert batch["archived_entry_points"] == ARCHIVED_MEMORY_ENTRY_POINTS
    assert submit_research_job.ARCHIVED_MEMORY_ENTRY_POINTS == ARCHIVED_MEMORY_ENTRY_POINTS
    forms = ARCHIVED_ARGV_ELEMENTS + ADMITTED_ARGV_ELEMENTS + [
        form for name in sorted(ARCHIVED_MEMORY_ENTRY_POINTS) for form in _entry_point_forms(name)
    ]
    for element in forms:
        expected = archived_memory_reference(element)
        assert submit_research_job.archived_memory_reference(element) == expected, element
        assert batch["archived_reference"](element) == expected, element


def _entry_point_forms(name: str) -> list[str]:
    forms = [
        f"legacy/scripts/{name}.py",
        f"scripts/{name}.py",
        f"/workspace/cotcodec/infra/{name}/doctor.py",
        f"{name}.py",
        name,
        f"-m{name}",
        f"PYTHONPATH=/workspace/cotcodec/scripts/{name}",
    ]
    if name.isidentifier():
        forms += [f"scripts.{name}", f"legacy.harness.{name}", f"import harness.{name} as h"]
    return forms


def test_archived_entry_points_are_every_memory_named_file_in_the_archive() -> None:
    assert _archived_memory_tree() == ARCHIVED_MEMORY_ENTRY_POINTS
    assert {"run_memorybank_decay_container", "causal_memory_trials", "memory_trials"} <= (
        ARCHIVED_MEMORY_ENTRY_POINTS
    )


@pytest.mark.parametrize("name", sorted(_archived_memory_tree()))
def test_every_archived_memory_entry_point_is_rejected_in_every_form(name: str) -> None:
    for form in _entry_point_forms(name):
        for check in (archived_memory_reference, submit_research_job.archived_memory_reference):
            assert check(form) is not None, (name, form)


@pytest.mark.parametrize(
    "command",
    [
        ["python", "-mlegacy.scripts.run_memory_model_screen", "--output-dir", "/outputs/x"],
        ["python", "-mharness.memory_trials"],
        ["env", "PYTHONPATH=legacy/scripts", "python", "-m", "run_memory_model_screen"],
        ["env", "--chdir=legacy/scripts", "python", "run_memory_trials.py"],
        ["env", "-C", "legacy", "python", "-m", "scripts.run_mem0_lifecycle_doctor"],
        ["python", "-c", "from legacy.harness import memory_trials"],
        ["python", "legacy/scripts/run_memorybank_decay_container.py", "--output", "/outputs/x"],
        ["python", "-m", "legacy.harness.causal_memory_trials"],
        ["python", "legacy/scripts/run_memgpt_letta_lifecycle_doctor.py"],
        ["python", "scripts/probe.py", "--memory-bund", "/inputs/bundle.json"],
    ],
)
def test_review_bypass_commands_are_rejected_by_both_submitters(command: list[str]) -> None:
    raw = _deterministic_manifest()
    raw["command"] = command
    with pytest.raises(ValueError, match=f"^{ARCHIVED_PREFIX}"):
        validate_manifest(raw)
    research = {
        "name": "bypass-check",
        "image": "registry.example/cotcodec@sha256:" + "a" * 64,
        "command": command,
        "run_root": "/shared/cotcodec/runs",
        "git_sha": "a" * 40,
        "source_sha256": "b" * 64,
        "seeds": [42, 43, 44],
        "resources": {"gpu_type": "h100", "gpus": 1, "cpus": 16, "memory_gb": 64, "minutes": 30},
        "budget": {"max_gpu_hours": 1},
    }
    with pytest.raises(ValueError, match=f"^{ARCHIVED_PREFIX}"):
        submit_research_job.validate_manifest(research)


def test_batch_masks_the_archive_inside_every_container() -> None:
    content = BATCH_SCRIPT.read_text(encoding="utf-8")
    assert "archive_mask=/workspace/cotcodec/legacy:ro,noexec,nosuid,nodev,size=64k" in content
    create = content.split("docker create \\\n", 1)[1].split("container-id.txt", 1)[0]
    assert '--tmpfs "${archive_mask}"' in create


def test_vllm_gpu_memory_utilization_flag_is_admitted_by_both_submitters() -> None:
    raw = _manifest()
    raw["command"] += ["--gpu-memory-utilization", "0.9"]
    manifest = validate_manifest(raw)
    assert manifest["command"][-2:] == ["--gpu-memory-utilization", "0.9"]

    research = {
        "name": "vllm-probe",
        "image": "registry.example/cotcodec@sha256:" + "a" * 64,
        "command": ["vllm", "serve", "/models/qwen", "--gpu-memory-utilization", "0.9"],
        "run_root": "/shared/cotcodec/runs",
        "git_sha": "a" * 40,
        "source_sha256": "b" * 64,
        "seeds": [42, 43, 44],
        "resources": {"gpu_type": "h100", "gpus": 1, "cpus": 16, "memory_gb": 64, "minutes": 30},
        "budget": {"max_gpu_hours": 1},
    }
    assert submit_research_job.validate_manifest(research)["command"][-1] == "0.9"


@pytest.mark.parametrize("field", ["memory_source_admission", "memory_bundle"])
def test_non_null_memory_blocks_are_rejected_and_null_is_admitted(field: str) -> None:
    raw = _manifest()
    raw[field] = None
    validate_manifest(raw)
    raw[field] = {"host_path": "/home/kevin/bundle.json", "sha256": "1" * 64}
    with pytest.raises(ValueError, match=f"^{ARCHIVED_PREFIX}.*{field}"):
        validate_manifest(raw)


def test_research_submitter_rejects_memory_bundle_before_shape_checks() -> None:
    research = {
        "name": "legacy-memory",
        "image": "registry.example/cotcodec@sha256:" + "a" * 64,
        "command": ["python", "scripts/train.py"],
        "run_root": "/shared/cotcodec/runs",
        "git_sha": "a" * 40,
        "source_sha256": "b" * 64,
        "seeds": [42, 43, 44],
        "resources": {"gpu_type": "h100", "gpus": 1, "cpus": 16, "memory_gb": 64, "minutes": 30},
        "budget": {"max_gpu_hours": 1},
        "memory_bundle": {"host_path": "relative/not-allowed"},
    }
    with pytest.raises(ValueError, match=f"^{ARCHIVED_PREFIX}"):
        submit_research_job.validate_manifest(research)


# R2: explicit seed binding ---------------------------------------------------------


@pytest.mark.parametrize("flag", ["--seeds", "--seed", "--assignment-seeds"])
def test_seed_binding_requires_the_declared_flag_and_exact_seeds(flag: str) -> None:
    raw = _manifest()
    raw["seed_binding"] = {"flag": flag}
    raw["command"][4] = flag
    manifest = validate_manifest(raw)
    assert manifest["seed_binding"] == {"flag": flag}
    export = _export(manifest)
    assert export["COTCODEC_SEED_BINDING_FLAG"] == flag
    assert export["COTCODEC_SEEDS"] == "42:43:44"
    assert _decoded_manifest(export)["seed_binding"] == {"flag": flag}


def test_declared_seeds_without_a_binding_are_rejected() -> None:
    raw = _manifest()
    del raw["seed_binding"]
    with pytest.raises(ValueError, match="without seed_binding"):
        validate_manifest(raw)
    raw["command"] = raw["command"][:4]
    with pytest.raises(ValueError, match="without seed_binding"):
        validate_manifest(raw)


@pytest.mark.parametrize(
    "binding",
    [
        {"flag": "--assignment-seed"},
        {"flag": "--rng"},
        {"flag": "--seeds", "extra": True},
        {},
        "--seeds",
    ],
)
def test_malformed_seed_binding_is_rejected(binding) -> None:
    raw = _manifest()
    raw["seed_binding"] = binding
    with pytest.raises(ValueError, match="seed_binding must be exactly"):
        validate_manifest(raw)


@pytest.mark.parametrize(
    ("tail", "message"),
    [
        (["--seeds", "43", "42", "44"], "do not match manifest seeds"),
        (["--seeds", "42", "43"], "do not match manifest seeds"),
        (["--seeds", "42", "43", "44", "45"], "do not match manifest seeds"),
        (["--seeds", "042", "43", "44"], "do not match manifest seeds"),
        (["--seeds", "42", "43", "44", "config.yaml"], "do not match manifest seeds"),
        (["--seeds", "42", "43", "44", "--seeds", "42", "43", "44"], "exactly one --seeds"),
        (["--seeds", "42", "43", "44", "--seed", "0"], "no other seed option"),
        (["--seeds=42,43,44"], "separate argv elements"),
        (["--output-dir", "/outputs"], "exactly one --seeds"),
        # argparse would expand these abbreviations to --seeds or --assignment-seeds.
        (["--seeds", "42", "43", "44", "--see", "7"], "spelled in full"),
        (["--seeds", "42", "43", "44", "--see=7"], "spelled in full"),
        (["--seeds", "42", "43", "44", "--s", "7"], "spelled in full"),
        (["--seeds", "42", "43", "44", "--assign", "7"], "spelled in full"),
        (["--se", "42", "43", "44"], "spelled in full"),
    ],
)
def test_seed_binding_rejects_drifting_or_extra_seed_arguments(
    tail: list[str], message: str
) -> None:
    raw = _manifest()
    raw["command"] = raw["command"][:4] + tail
    with pytest.raises(ValueError, match=message):
        validate_manifest(raw)


def test_seed_abbreviation_matches_what_argparse_would_expand() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    parser.add_argument("--seeds", type=int, nargs="+")
    parsed = parser.parse_args(["--output", "r.json", "--seeds", "42", "43", "44", "--see", "7"])
    assert parsed.seeds == [7]
    for argument in ("--see", "--see=7", "--s", "--assignment-se", "--assign"):
        assert seed_option_abbreviation(argument) is not None, argument
    for argument in ("--seeds", "--seed", "--seed-file", "--sequence-length", "--", "-s", "7"):
        assert seed_option_abbreviation(argument) is None, argument


def test_seed_abbreviation_after_valid_seeds_is_not_admitted_for_the_repo_workload() -> None:
    raw = _manifest()
    raw["command"] += ["--see", "7"]
    with pytest.raises(ValueError, match="argparse would expand --see"):
        validate_manifest(raw)
    raw = _manifest()
    raw["command"] += ["--sequence-length", "128"]
    assert validate_manifest(raw)["command"][-2:] == ["--sequence-length", "128"]


def test_seed_matrix_rejects_repeated_seeds() -> None:
    raw = _manifest()
    raw["seeds"] = [42, 43, 44, 44]
    raw["command"] += ["44"]
    with pytest.raises(ValueError, match="cannot repeat a seed"):
        validate_manifest(raw)


@pytest.mark.parametrize("contract", ["deterministic", "deterministic-all-serve"])
def test_deterministic_jobs_take_no_seeds_binding_or_seed_options(contract: str) -> None:
    raw = _deterministic_manifest()
    raw["randomness_contract"] = contract
    assert "seed_binding" not in validate_manifest(raw)

    seeded = _deterministic_manifest()
    seeded["randomness_contract"] = contract
    seeded["seeds"] = [42, 43, 44]
    with pytest.raises(ValueError, match="^deterministic jobs cannot declare seeds$"):
        validate_manifest(seeded)

    bound = _deterministic_manifest()
    bound["randomness_contract"] = contract
    bound["seed_binding"] = {"flag": "--seeds"}
    with pytest.raises(ValueError, match="cannot declare seed_binding"):
        validate_manifest(bound)

    for option in ("--seed", "--seeds", "--assignment-seeds", "--assignment-seed"):
        executing = _deterministic_manifest()
        executing["randomness_contract"] = contract
        executing["command"] += [option, "0"]
        with pytest.raises(ValueError, match="cannot execute seed options"):
            validate_manifest(executing)

    for abbreviation in ("--see", "--se=1", "--assignment-s"):
        abbreviated = _deterministic_manifest()
        abbreviated["randomness_contract"] = contract
        abbreviated["command"] += [abbreviation, "7"]
        with pytest.raises(ValueError, match="spelled in full"):
            validate_manifest(abbreviated)


def test_unknown_randomness_contract_is_rejected() -> None:
    raw = _manifest()
    raw["randomness_contract"] = "seeded"
    with pytest.raises(ValueError, match="randomness_contract is unsupported"):
        validate_manifest(raw)


# R3: container profiles -----------------------------------------------------------


@pytest.mark.parametrize("profile", ["default", "vllm", "large-cpu-mem"])
def test_container_profile_is_validated_and_exported(profile: str) -> None:
    raw = _manifest()
    raw["container_profile"] = profile
    export = _export(validate_manifest(raw))
    assert export["COTCODEC_CONTAINER_PROFILE"] == profile
    assert _decoded_manifest(export)["container_profile"] == profile


def test_absent_container_profile_exports_nothing() -> None:
    export = _export(validate_manifest(_manifest()))
    assert "COTCODEC_CONTAINER_PROFILE" not in export
    assert "container_profile" not in _decoded_manifest(export)


@pytest.mark.parametrize("profile", ["gpu-heavy", "", "VLLM", 1, True, ["vllm"]])
def test_unknown_container_profile_is_rejected(profile) -> None:
    raw = _manifest()
    raw["container_profile"] = profile
    with pytest.raises(ValueError, match="container_profile must be one of"):
        validate_manifest(raw)


def test_batch_maps_every_profile_with_a_failing_default_case() -> None:
    content = BATCH_SCRIPT.read_text(encoding="utf-8")
    assert 'container_profile="${COTCODEC_CONTAINER_PROFILE-default}"' in content
    assert 'case "${container_profile}" in' in content
    default = content.split("  default)\n", 1)[1].split(";;", 1)[0]
    assert "container_tmpfs=/tmp:rw,nosuid,nodev,size=8g" in default
    assert "container_pids_limit=4096" in default
    assert "container_shm_args=()" in default
    vllm = content.split("  vllm)\n", 1)[1].split(";;", 1)[0]
    assert "container_tmpfs=/tmp:rw,exec,nosuid,nodev,size=32g" in vllm
    assert "container_pids_limit=8192" in vllm
    assert "container_shm_args=(--shm-size 16g)" in vllm
    large = content.split("  large-cpu-mem)\n", 1)[1].split(";;", 1)[0]
    assert "container_tmpfs=/tmp:rw,exec,nosuid,nodev,size=8g" in large
    assert "container_pids_limit=4096" in large
    assert "container_shm_args=()" in large
    unknown = content.split("  *)\n    echo \"COTCODEC_CONTAINER_PROFILE", 1)[1].split(";;", 1)[0]
    assert "exit 2" in unknown


# R4: explicit memory ---------------------------------------------------------------


@pytest.mark.parametrize("memory_gb", [16, 32, 192])
def test_slurm_memory_request_matches_manifest_memory(memory_gb: int) -> None:
    raw = _manifest()
    raw["resources"]["memory_gb"] = memory_gb
    argv = sbatch_argv(validate_manifest(raw), test_only=True)
    assert f"--mem={memory_gb}G" in argv
    assert [value for value in argv if value.startswith("--mem")] == [f"--mem={memory_gb}G"]


def test_batch_has_no_silent_memory_fallback() -> None:
    content = BATCH_SCRIPT.read_text(encoding="utf-8")
    assert "65536" not in content
    assert 'memory_limit_mb="${SLURM_MEM_PER_NODE:?' in content
    assert "int(slurm_memory_mb) != memory_gb * 1024" in content
    assert '--memory "${memory_limit_mb}m"' in content
    assert '--memory-swap "${memory_limit_mb}m"' in content


@pytest.mark.parametrize("memory_gb", [0, 1701, "32", True])
def test_invalid_memory_is_rejected(memory_gb) -> None:
    raw = _manifest()
    raw["resources"]["memory_gb"] = memory_gb
    with pytest.raises(ValueError, match="memory_gb must be an integer"):
        validate_manifest(raw)


# R5: explicit no-model admission ---------------------------------------------------

NO_MODEL_REASON = "kernel-gate validation runs compiler-generated kernels only"


def test_no_model_job_exports_model_id_none_and_no_model_inputs() -> None:
    raw = _manifest()
    raw["model"] = {"kind": "none", "reason": NO_MODEL_REASON}
    manifest = validate_manifest(raw)
    assert manifest["model"] == {"kind": "none", "reason": NO_MODEL_REASON}
    export = _export(manifest)
    assert export["COTCODEC_MODEL_KIND"] == "none"
    assert export["COTCODEC_MODEL_ID"] == "none"
    for key in (
        "COTCODEC_MODEL_CACHE_HOST_HEX",
        "COTCODEC_MODEL_REVISION",
        "COTCODEC_MODEL_RECEIPT_SHA256",
        "COTCODEC_MODEL_ARTIFACT_ROOT",
    ):
        assert key not in export
    assert _decoded_manifest(export)["model"]["reason"] == NO_MODEL_REASON


@pytest.mark.parametrize(
    "model",
    [
        {"kind": "none", "reason": "x" * 19},
        {"kind": "none", "reason": " " + NO_MODEL_REASON},
        {"kind": "none", "reason": NO_MODEL_REASON + "\nsecond line"},
        {"kind": "none", "reason": "x" * 501},
        {"kind": "none", "reason": 42},
    ],
)
def test_no_model_job_requires_a_real_reason(model: dict) -> None:
    raw = _manifest()
    raw["model"] = model
    with pytest.raises(ValueError, match="model.reason must be"):
        validate_manifest(raw)


@pytest.mark.parametrize(
    "model",
    [
        {"kind": "none"},
        {"kind": "none", "reason": NO_MODEL_REASON, "model_id": "qwen3.5-4b"},
        {"kind": "none", "reason": NO_MODEL_REASON, "cache_host_path": "/home/kevin/hf"},
        {"kind": "checkpoint", "reason": NO_MODEL_REASON},
        {"kind": None, "reason": NO_MODEL_REASON},
    ],
)
def test_no_model_declaration_is_exact(model: dict) -> None:
    raw = _manifest()
    raw["model"] = model
    with pytest.raises(ValueError, match="model.kind may only be none"):
        validate_manifest(raw)


@pytest.mark.parametrize("model", [None, "none", []])
def test_no_model_job_is_never_inferred_from_a_missing_block(model) -> None:
    raw = _manifest()
    if model is None:
        del raw["model"]
    else:
        raw["model"] = model
    with pytest.raises(ValueError, match="model must be a mapping"):
        validate_manifest(raw)


def test_checkpoint_model_cannot_claim_the_reserved_none_id() -> None:
    raw = _manifest()
    raw["model"]["model_id"] = "none"
    with pytest.raises(ValueError, match="reserved"):
        validate_manifest(raw)


# R7: foreign-process prolog opt-out ------------------------------------------------

SHARED_GPU_REASON = "co-scheduled profiler measures contention on purpose"


def test_shared_gpu_opt_out_requires_true_and_a_reason() -> None:
    raw = _manifest()
    raw["allow_shared_gpu"] = True
    raw["shared_gpu_reason"] = SHARED_GPU_REASON
    manifest = validate_manifest(raw)
    assert manifest["allow_shared_gpu"] is True
    assert manifest["shared_gpu_reason"] == SHARED_GPU_REASON
    export = _export(manifest)
    assert export["COTCODEC_ALLOW_SHARED_GPU"] == "true"
    assert SHARED_GPU_REASON not in ",".join(export.values())


def test_shared_gpu_defaults_to_exclusive_and_exports_nothing() -> None:
    raw = _manifest()
    raw["allow_shared_gpu"] = False
    export = _export(validate_manifest(raw))
    assert "COTCODEC_ALLOW_SHARED_GPU" not in export
    assert "allow_shared_gpu" not in _decoded_manifest(export)


@pytest.mark.parametrize(
    ("flag", "reason", "message"),
    [
        (True, None, "shared_gpu_reason must be"),
        (True, "too short", "shared_gpu_reason must be"),
        ("true", SHARED_GPU_REASON, "allow_shared_gpu must be true or false"),
        (1, SHARED_GPU_REASON, "allow_shared_gpu must be true or false"),
        (None, SHARED_GPU_REASON, "allow_shared_gpu must be true or false"),
        (False, SHARED_GPU_REASON, "requires allow_shared_gpu: true"),
    ],
)
def test_shared_gpu_opt_out_is_fail_closed(flag, reason, message: str) -> None:
    raw = _manifest()
    raw["allow_shared_gpu"] = flag
    if reason is not None:
        raw["shared_gpu_reason"] = reason
    with pytest.raises(ValueError, match=message):
        validate_manifest(raw)
