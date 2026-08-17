#!/usr/bin/env python3
"""Compile a bounded contained H100 job for strict open-model replay diagnosis."""

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
from scripts.memory_job_admission import build_memory_job_admission  # noqa: E402
from scripts.submit_docker_research_job import (  # noqa: E402
    RUNTIME,
    validate_manifest,
)

RESOURCE_PROFILES: dict[str, dict[str, int]] = {
    "qwen3.5-4b": {"gpus": 1, "cpus": 16, "memory_gb": 64, "minutes": 90},
    "qwen3.5-9b": {"gpus": 1, "cpus": 16, "memory_gb": 96, "minutes": 90},
    "qwen3.6-35b-a3b": {
        "gpus": 2,
        "cpus": 32,
        "memory_gb": 192,
        "minutes": 120,
    },
}
DEFAULT_TASK_IDS = ("0", "4", "106", "180")


def compile_replay_doctor_manifest(
    *,
    model_id: str,
    image_id: str,
    run_root: str,
    git_sha: str,
    source_sha256: str,
    model_cache_host: str,
    receipt_sha256: str,
    artifact_root_sha256: str,
    seeds: tuple[int, ...] = (42, 43, 44),
    task_ids: tuple[str, ...] = DEFAULT_TASK_IDS,
    repetitions: int = 3,
    cold_reloads: int = 2,
    memory_bundle_path: str | None = None,
    memory_bundle_sha256: str | None = None,
    resume_from_job_id: str | None = None,
    resume_subpath: str | None = None,
    registry_path: Path = DEFAULT_REGISTRY,
) -> dict[str, Any]:
    if len(seeds) < 3 or len(set(seeds)) != len(seeds):
        raise ValueError("replay doctor requires at least three distinct seeds")
    if repetitions < 2 or cold_reloads < 2:
        raise ValueError("replay doctor requires two repeats and two cold reloads")
    if not task_ids or len(set(task_ids)) != len(task_ids):
        raise ValueError("replay doctor task ids must be nonempty and distinct")
    if (memory_bundle_path is None) != (memory_bundle_sha256 is None):
        raise ValueError("memory bundle path and digest must be supplied together")
    if (resume_from_job_id is None) != (resume_subpath is None):
        raise ValueError("resume job id and subpath must be supplied together")
    if resume_subpath is not None and resume_subpath != "replay-doctor":
        raise ValueError("replay doctor resumes only the replay-doctor artifact subtree")
    registry = load_registry(registry_path)
    entry = registry["models"].get(model_id)
    if not isinstance(entry, dict) or model_id not in RESOURCE_PROFILES:
        raise ValueError(f"{model_id}: no reviewed replay-doctor resource profile")
    if entry["trust_remote_code"] or not entry["publication_eligible"]:
        raise ValueError(f"{model_id}: checkpoint is not eligible for strict replay")

    command = [
        "python",
        "scripts/run_memory_model_replay_doctor.py",
        "experiments/memory/stage1-model-transport.yaml",
        "--output-dir",
        "/outputs/replay-doctor",
        "--model-id",
        model_id,
        "--model-root",
        "/model-cache/cotcodec-models",
        "--receipt-root",
        "/model-cache/cotcodec-receipts",
        "--repetitions",
        str(repetitions),
        "--cold-reloads",
        str(cold_reloads),
    ]
    for task_id in task_ids:
        command.extend(("--task-id", task_id))
    command.extend(("--seeds", *(str(seed) for seed in seeds)))
    if memory_bundle_path is not None:
        command.extend(("--memory-bundle", "/inputs/memory-selection-bundle.json"))

    profile = RESOURCE_PROFILES[model_id]
    raw: dict[str, Any] = {
        "runtime": RUNTIME,
        "name": f"replay-{model_id.replace('.', '-')}",
        "image_id": image_id,
        "git_sha": git_sha,
        "source_sha256": source_sha256,
        "run_root": run_root,
        "command": command,
        "model": {
            "cache_host_path": model_cache_host,
            "model_id": model_id,
            "revision": entry["revision"],
            "receipt_sha256": receipt_sha256,
            "artifact_root_sha256": artifact_root_sha256,
        },
        "seeds": list(seeds),
        "resources": {"gpu_type": "h100", **profile},
        "budget": {
            "max_gpu_hours": profile["gpus"] * profile["minutes"] / 60
        },
        "memory_source_admission": build_memory_job_admission(),
    }
    if memory_bundle_path is not None and memory_bundle_sha256 is not None:
        raw["memory_bundle"] = {
            "host_path": memory_bundle_path,
            "sha256": memory_bundle_sha256,
        }
    if resume_from_job_id is not None and resume_subpath is not None:
        raw["resume_from_job_id"] = resume_from_job_id
        raw["resume_subpath"] = resume_subpath
    validate_manifest(raw)
    return raw


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-id", choices=tuple(RESOURCE_PROFILES), required=True)
    parser.add_argument("--image-id", required=True)
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--git-sha", required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--model-cache-host", required=True)
    parser.add_argument("--receipt-sha256", required=True)
    parser.add_argument("--artifact-root-sha256", required=True)
    parser.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44])
    parser.add_argument("--task-id", action="append")
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--cold-reloads", type=int, default=2)
    parser.add_argument("--memory-bundle-path")
    parser.add_argument("--memory-bundle-sha256")
    parser.add_argument("--resume-from-job-id")
    parser.add_argument("--resume-subpath", choices=("replay-doctor",))
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    manifest = compile_replay_doctor_manifest(
        model_id=args.model_id,
        image_id=args.image_id,
        run_root=args.run_root,
        git_sha=args.git_sha,
        source_sha256=args.source_sha256,
        model_cache_host=args.model_cache_host,
        receipt_sha256=args.receipt_sha256,
        artifact_root_sha256=args.artifact_root_sha256,
        seeds=tuple(args.seeds),
        task_ids=tuple(args.task_id or DEFAULT_TASK_IDS),
        repetitions=args.repetitions,
        cold_reloads=args.cold_reloads,
        memory_bundle_path=args.memory_bundle_path,
        memory_bundle_sha256=args.memory_bundle_sha256,
        resume_from_job_id=args.resume_from_job_id,
        resume_subpath=args.resume_subpath,
        registry_path=args.registry,
    )
    rendered = yaml.safe_dump(manifest, sort_keys=False)
    if args.output is None:
        print(rendered, end="")
    else:
        if args.output.exists():
            raise ValueError(f"refusing to overwrite manifest: {args.output}")
        args.output.write_text(rendered, encoding="utf-8")
        print(json.dumps({"manifest": str(args.output), "model_id": args.model_id}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
