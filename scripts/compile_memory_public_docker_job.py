#!/usr/bin/env python3
"""Compile contained Docker/Slurm jobs for the immutable LongMemEval screen."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.fetch_open_model import DEFAULT_REGISTRY, load_registry  # noqa: E402
from scripts.freeze_memory_system_outputs import SYSTEM_IDENTITIES  # noqa: E402
from scripts.memory_job_admission import build_memory_job_admission  # noqa: E402
from scripts.submit_docker_research_job import (  # noqa: E402
    PUBLIC_BENCHMARK_CONTAINER_PATH,
    RUNTIME,
    validate_manifest,
)

DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments/memory/stage1-longmemeval-screen.yaml"
)
STAGES = (
    "freeze-controls",
    "actor-screen",
    "freeze-controls-full",
    "actor-all-serve",
)
CONTROL_SYSTEMS = (
    "no-memory",
    "recency",
    "lru",
    "lexical",
    "bm25",
    "dense-bge-retrieval",
    "raw-log-rrf",
    "profile-expansion",
    "temporal-graph",
    "reference",
)
ACTOR_CONTROL_SYSTEMS = (*CONTROL_SYSTEMS, "mempalace-raw-session")
CONTROL_JOB_SLUGS = {
    "dense-bge-retrieval": "dense-bge",
    "mempalace-raw-session": "mempalace-raw",
}


def _load_contract(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("public memory experiment must be a schema_version: 1 mapping")
    source = payload.get("source")
    execution = payload.get("execution")
    model = payload.get("model")
    if not all(isinstance(value, dict) for value in (source, execution, model)):
        raise ValueError("public memory experiment misses source/model/execution mappings")
    if source.get("type") != "longmemeval" or source.get("screen_tasks") != 32:
        raise ValueError("compiler accepts only the registered 32-task LongMemEval screen")
    if execution.get("seeds") != [42, 43, 44]:
        raise ValueError("registered assignment-seed matrix drifted")
    return payload


def _model_contract(
    model_id: str,
    *,
    registry_path: Path,
    experiment: dict[str, Any],
    actor_model: bool,
) -> dict[str, Any]:
    registry = load_registry(registry_path)
    entry = registry["models"].get(model_id)
    if not isinstance(entry, dict):
        raise ValueError(f"{model_id}: model is absent from the reviewed registry")
    if entry["trust_remote_code"] or not entry["publication_eligible"]:
        raise ValueError(f"{model_id}: model is not eligible for the generic image")
    if actor_model and model_id != experiment["model"]["model_id"]:
        raise ValueError("actor model must match the registered public screen")
    if not actor_model and model_id != "bge-small-en-v1.5":
        raise ValueError("control freezing must bind the registered dense BGE model")
    return entry


def compile_public_docker_manifest(
    *,
    stage: str,
    image_id: str,
    run_root: str,
    git_sha: str,
    source_sha256: str,
    model_cache_host: str,
    model_receipt_sha256: str,
    model_artifact_root: str,
    public_benchmark_path: str,
    model_id: str = "qwen3.6-35b-a3b",
    memory_bundle_path: str | None = None,
    memory_bundle_sha256: str | None = None,
    memory_control_id: str | None = None,
    memory_admission_sha256: str | None = None,
    experiment_path: Path = DEFAULT_EXPERIMENT,
    registry_path: Path = DEFAULT_REGISTRY,
) -> dict[str, Any]:
    if stage not in STAGES:
        raise ValueError(f"unsupported public memory stage: {stage}")
    if (memory_bundle_path is None) != (memory_bundle_sha256 is None):
        raise ValueError("memory bundle path and digest must be supplied together")
    if stage in {"actor-screen", "actor-all-serve"}:
        if memory_bundle_path is None:
            raise ValueError("actor screen requires one frozen memory-selection bundle")
        if memory_control_id not in ACTOR_CONTROL_SYSTEMS:
            raise ValueError("actor screen requires a registered memory control id")
        if memory_control_id == "mempalace-raw-session":
            if (
                not isinstance(memory_admission_sha256, str)
                or len(memory_admission_sha256) != 64
                or any(char not in "0123456789abcdef" for char in memory_admission_sha256)
            ):
                raise ValueError(
                    "MemPalace actor requires registered admission-evidence SHA-256"
                )
        elif memory_admission_sha256 is not None:
            raise ValueError("memory admission evidence is registered only for MemPalace")
    elif memory_bundle_path is not None or memory_control_id is not None:
        raise ValueError("control freezing cannot consume a prior memory bundle")

    experiment = _load_contract(experiment_path)
    source = experiment["source"]
    freeze_stage = stage in {"freeze-controls", "freeze-controls-full"}
    workload_model_id = "bge-small-en-v1.5" if freeze_stage else model_id
    entry = _model_contract(
        workload_model_id,
        registry_path=registry_path,
        experiment=experiment,
        actor_model=not freeze_stage,
    )
    seeds = list(experiment["execution"]["seeds"])
    if stage in {"freeze-controls", "freeze-controls-full"}:
        command = [
            "python",
            "scripts/freeze_memory_control_matrix.py",
            "--output-dir",
            "/outputs/control-matrix",
            "--task-source",
            "longmemeval",
            "--candidate-seed",
            str(source["candidate_seed"]),
            "--longmemeval-path",
            PUBLIC_BENCHMARK_CONTAINER_PATH,
            "--model-root",
            "/model-cache/cotcodec-models",
            "--receipt-root",
            "/model-cache/cotcodec-receipts",
            "--systems",
            *CONTROL_SYSTEMS,
        ]
        if stage == "freeze-controls":
            systems_index = command.index("--systems")
            command[systems_index:systems_index] = [
                "--episodes",
                str(source["screen_tasks"]),
            ]
        resources = {
            "gpu_type": "h100",
            "gpus": 1,
            "cpus": 16,
            "memory_gb": 64,
            "minutes": 30,
        }
        name = (
            "memory-longmemeval-freeze"
            if stage == "freeze-controls"
            else "memory-longmemeval-freeze-full"
        )
    else:
        control_job_slug = CONTROL_JOB_SLUGS.get(
            memory_control_id or "",
            memory_control_id or "missing",
        )
        command = [
            "python",
            "scripts/run_memory_model_screen.py",
            "experiments/memory/stage1-longmemeval-screen.yaml",
            "--model-root",
            "/model-cache/cotcodec-models",
            "--receipt-root",
            "/model-cache/cotcodec-receipts",
            "--output-dir",
            "/outputs/screen",
            "--memory-bundle",
            "/inputs/memory-selection-bundle.json",
            "--memory-treatment-mode",
            "storage_and_service",
            "--expected-memory-system-id",
            SYSTEM_IDENTITIES[memory_control_id or ""],
            "--evaluation-mode",
            "all-serve-benchmark" if stage == "actor-all-serve" else "matrix-cell",
            "--public-benchmark-path",
            PUBLIC_BENCHMARK_CONTAINER_PATH,
            "--require-gates",
        ]
        if memory_admission_sha256 is not None:
            require_index = command.index("--require-gates")
            command[require_index:require_index] = [
                "--expected-memory-admission-sha256",
                memory_admission_sha256,
            ]
        if stage == "actor-screen":
            require_index = command.index("--require-gates")
            command[require_index:require_index] = [
                "--assignment-seeds",
                *(str(seed) for seed in seeds),
            ]
        resources = {
            "gpu_type": "h100",
            "gpus": 2,
            "cpus": 32,
            "memory_gb": 192,
            "minutes": 240,
        }
        name = (
            f"memory-lme-q36-{control_job_slug}"
            if stage == "actor-screen"
            else f"memory-lme-quality-q36-{control_job_slug}"
        )

    randomness_contract = (
        "deterministic-all-serve"
        if stage in {"freeze-controls-full", "actor-all-serve"}
        else "assignment-seed-matrix"
    )

    raw: dict[str, Any] = {
        "runtime": RUNTIME,
        "name": name,
        "image_id": image_id,
        "git_sha": git_sha,
        "source_sha256": source_sha256,
        "randomness_contract": randomness_contract,
        "run_root": run_root,
        "command": command,
        "model": {
            "cache_host_path": model_cache_host,
            "model_id": workload_model_id,
            "revision": entry["revision"],
            "receipt_sha256": model_receipt_sha256,
            "artifact_root_sha256": model_artifact_root,
        },
        "public_benchmark": {
            "source_id": "longmemeval-s-cleaned",
            "revision": source["dataset_revision"],
            "license": source["dataset_license"],
            "host_path": public_benchmark_path,
            "sha256": source["dataset_sha256"],
            "size_bytes": source["dataset_size"],
            "container_path": PUBLIC_BENCHMARK_CONTAINER_PATH,
        },
        "seeds": [] if randomness_contract == "deterministic-all-serve" else seeds,
        "resources": resources,
        "budget": {
            "max_gpu_hours": resources["gpus"] * resources["minutes"] / 60
        },
        "memory_source_admission": build_memory_job_admission(),
    }
    if memory_bundle_path is not None and memory_bundle_sha256 is not None:
        raw["memory_bundle"] = {
            "host_path": memory_bundle_path,
            "sha256": memory_bundle_sha256,
        }
    validate_manifest(raw)
    return raw


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=STAGES, required=True)
    parser.add_argument("--image-id", required=True)
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--git-sha", required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--model-cache-host", required=True)
    parser.add_argument("--model-receipt-sha256", required=True)
    parser.add_argument("--model-artifact-root", required=True)
    parser.add_argument("--public-benchmark-path", required=True)
    parser.add_argument("--model-id", default="qwen3.6-35b-a3b")
    parser.add_argument("--memory-bundle-path")
    parser.add_argument("--memory-bundle-sha256")
    parser.add_argument("--memory-control-id", choices=ACTOR_CONTROL_SYSTEMS)
    parser.add_argument("--memory-admission-sha256")
    parser.add_argument("--experiment", type=Path, default=DEFAULT_EXPERIMENT)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    manifest = compile_public_docker_manifest(
        stage=args.stage,
        image_id=args.image_id,
        run_root=args.run_root,
        git_sha=args.git_sha,
        source_sha256=args.source_sha256,
        model_cache_host=args.model_cache_host,
        model_receipt_sha256=args.model_receipt_sha256,
        model_artifact_root=args.model_artifact_root,
        public_benchmark_path=args.public_benchmark_path,
        model_id=args.model_id,
        memory_bundle_path=args.memory_bundle_path,
        memory_bundle_sha256=args.memory_bundle_sha256,
        memory_control_id=args.memory_control_id,
        memory_admission_sha256=args.memory_admission_sha256,
        experiment_path=args.experiment,
        registry_path=args.registry,
    )
    rendered = yaml.safe_dump(manifest, sort_keys=False)
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(json.dumps({"manifest": str(args.output), "stage": args.stage}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
