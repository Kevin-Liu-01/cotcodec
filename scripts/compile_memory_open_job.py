#!/usr/bin/env python3
"""Compile a bounded Slurm manifest for a pinned open-model memory screen."""

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
from scripts.submit_research_job import validate_manifest  # noqa: E402

RESOURCE_PROFILES: dict[str, dict[str, int]] = {
    "qwen3.5-4b": {"gpus": 1, "cpus": 16, "memory_gb": 64, "minutes": 240},
    "qwen3.5-9b": {"gpus": 1, "cpus": 16, "memory_gb": 96, "minutes": 240},
    "qwen3.6-35b-a3b": {"gpus": 2, "cpus": 32, "memory_gb": 192, "minutes": 240},
    "gpt-oss-120b": {"gpus": 2, "cpus": 32, "memory_gb": 192, "minutes": 240},
}


def compile_open_model_manifest(
    *,
    model_id: str,
    image: str,
    run_root: str,
    git_sha: str,
    source_sha256: str,
    memory_bundle_path: str,
    memory_bundle_sha256: str,
    seeds: tuple[int, ...] = (42, 43, 44),
    memory_budget_profile: str = "matched",
    predecessor_job_id: int | None = None,
    registry_path: Path = DEFAULT_REGISTRY,
) -> dict[str, Any]:
    if len(set(seeds)) < 3:
        raise ValueError("open-model confirmation requires three distinct seeds")
    if memory_budget_profile not in {"matched", "full-prefix-diagnostic"}:
        raise ValueError("unsupported memory budget profile")
    registry = load_registry(registry_path)
    entry = registry["models"].get(model_id)
    if not isinstance(entry, dict) or model_id not in RESOURCE_PROFILES:
        raise ValueError(f"{model_id}: no reviewed open-model Slurm profile")
    if entry["trust_remote_code"] or not entry["publication_eligible"]:
        raise ValueError(f"{model_id}: model is not eligible for the generic research image")
    profile = RESOURCE_PROFILES[model_id]
    command = [
        "uv",
        "run",
        "--frozen",
        "--extra",
        "architecture",
        "python",
        "scripts/run_memory_model_screen.py",
        "experiments/memory/stage1-model-transport.yaml",
        "--model-id",
        model_id,
        "--model-root",
        "/cache/huggingface/cotcodec-models",
        "--receipt-root",
        "/cache/huggingface/cotcodec-receipts",
        "--output-dir",
        "/outputs/screen",
        "--memory-bundle",
        "/inputs/memory-selection-bundle.json",
        "--memory-treatment-mode",
        "storage_and_service",
        "--memory-budget-profile",
        memory_budget_profile,
        "--evaluation-mode",
        (
            "diagnostic-ceiling"
            if memory_budget_profile == "full-prefix-diagnostic"
            else "matrix-cell"
        ),
        "--assignment-seeds",
        *(str(seed) for seed in seeds),
        "--require-gates",
    ]
    raw: dict[str, Any] = {
        "name": (
            f"memory-{model_id.replace('.', '-')}-fpdiag"
            if memory_budget_profile == "full-prefix-diagnostic"
            else f"memory-{model_id.replace('.', '-')}"
        ),
        "image": image,
        "command": command,
        "run_root": run_root,
        "git_sha": git_sha,
        "source_sha256": source_sha256,
        "seeds": list(seeds),
        "resources": {"gpu_type": "h100", **profile},
        "budget": {"max_gpu_hours": profile["gpus"] * profile["minutes"] / 60},
        "memory_bundle": {
            "host_path": memory_bundle_path,
            "sha256": memory_bundle_sha256,
            "container_path": "/inputs/memory-selection-bundle.json",
        },
        "memory_budget_profile": memory_budget_profile,
        "memory_source_admission": build_memory_job_admission(),
    }
    if predecessor_job_id is not None:
        raw["resume_from_job_id"] = predecessor_job_id
        raw["resume_subpath"] = "screen"
        command.append("--resume")
    validate_manifest(raw)
    return raw


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-id", choices=tuple(RESOURCE_PROFILES), required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--git-sha", required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--memory-bundle-path", required=True)
    parser.add_argument("--memory-bundle-sha256", required=True)
    parser.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44])
    parser.add_argument(
        "--memory-budget-profile",
        choices=("matched", "full-prefix-diagnostic"),
        default="matched",
    )
    parser.add_argument("--predecessor-job-id", type=int)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    manifest = compile_open_model_manifest(
        model_id=args.model_id,
        image=args.image,
        run_root=args.run_root,
        git_sha=args.git_sha,
        source_sha256=args.source_sha256,
        memory_bundle_path=args.memory_bundle_path,
        memory_bundle_sha256=args.memory_bundle_sha256,
        seeds=tuple(args.seeds),
        memory_budget_profile=args.memory_budget_profile,
        predecessor_job_id=args.predecessor_job_id,
        registry_path=args.registry,
    )
    rendered = yaml.safe_dump(manifest, sort_keys=False)
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.write_text(rendered, encoding="utf-8")
        print(json.dumps({"manifest": str(args.output), "model_id": args.model_id}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
