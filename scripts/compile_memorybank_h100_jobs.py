#!/usr/bin/env python3
"""Compile the three bounded Docker-under-Slurm MemoryBank H100 cells."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.fetch_open_model import DEFAULT_REGISTRY, load_registry  # noqa: E402
from scripts.memory_job_admission import build_memory_job_admission  # noqa: E402
from scripts.submit_docker_research_job import RUNTIME, validate_manifest  # noqa: E402
from scripts.validate_memorybank_h100_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    validate_experiment_contract,
)

SOURCE_ID = "memorybank-siliconfriend"


def compile_manifests(
    *,
    image_id: str,
    run_root: str,
    git_sha: str,
    source_sha256: str,
    model_cache_host: str,
    receipt_sha256: str,
    remote_bundle_root: str,
    resume_from_job_ids: Mapping[str, int] | None = None,
    experiment_path: Path = DEFAULT_EXPERIMENT,
    registry_path: Path = DEFAULT_REGISTRY,
) -> dict[str, dict[str, Any]]:
    config = validate_experiment_contract(experiment_path)
    model = config["model"]
    registry = load_registry(registry_path)
    entry = registry["models"].get(model["model_id"])
    if (
        not isinstance(entry, dict)
        or entry.get("revision") != model["revision"]
        or entry.get("trust_remote_code") is not False
        or entry.get("publication_eligible") is not True
    ):
        raise ValueError("MemoryBank H100 model registry identity drifted")
    execution = config["execution"]
    unknown_resume_arms = set(resume_from_job_ids or ()) - set(config["input"]["bundles"])
    if unknown_resume_arms:
        raise ValueError(f"unknown MemoryBank resume arms: {sorted(unknown_resume_arms)}")
    manifests: dict[str, dict[str, Any]] = {}
    for arm, bundle in config["input"]["bundles"].items():
        filename = Path(bundle["path"]).name
        output_slug = arm.replace("_", "-")
        command = [
            "python",
            "scripts/run_memory_model_screen.py",
            "experiments/memory/stage1-model-transport.yaml",
            "--model-id",
            model["model_id"],
            "--model-root",
            "/model-cache/cotcodec-models",
            "--receipt-root",
            "/model-cache/cotcodec-receipts",
            "--output-dir",
            f"/outputs/memorybank-{output_slug}",
            "--memory-bundle",
            "/inputs/memory-selection-bundle.json",
            "--memory-treatment-mode",
            config["input"]["treatment_mode"],
            "--evaluation-mode",
            "matrix-cell",
            "--assignment-seeds",
            *[str(seed) for seed in config["design"]["assignment_seeds"]],
            "--expected-memory-system-id",
            bundle["system_id"],
            "--require-gates",
        ]
        predecessor = (resume_from_job_ids or {}).get(arm)
        if predecessor is not None:
            if (
                not isinstance(predecessor, int)
                or isinstance(predecessor, bool)
                or predecessor <= 0
            ):
                raise ValueError(f"{arm}: predecessor job id must be a positive integer")
            command.append("--resume")
        raw = {
            "runtime": RUNTIME,
            "name": f"memorybank-qwen35-4b-{output_slug}",
            "image_id": image_id,
            "git_sha": git_sha,
            "source_sha256": source_sha256,
            "run_root": run_root,
            "command": command,
            "randomness_contract": "assignment-seed-matrix",
            "seeds": config["design"]["assignment_seeds"],
            "model": {
                "cache_host_path": model_cache_host,
                "model_id": model["model_id"],
                "revision": model["revision"],
                "receipt_sha256": receipt_sha256,
                "artifact_root_sha256": model["artifact_root_sha256"],
            },
            "memory_bundle": {
                "host_path": f"{remote_bundle_root.rstrip('/')}/{filename}",
                "sha256": bundle["file_sha256"],
            },
            "resources": {
                "gpu_type": execution["gpu_type"],
                "gpus": execution["gpus_per_arm"],
                "cpus": execution["cpus_per_arm"],
                "memory_gb": execution["memory_gb_per_arm"],
                "minutes": execution["minutes_per_arm"],
            },
            "budget": {"max_gpu_hours": execution["max_gpu_hours_per_arm"]},
            "memory_source_admission": build_memory_job_admission(
                [(SOURCE_ID, config["input"]["upstream_revision"])]
            ),
        }
        if predecessor is not None:
            raw["resume_from_job_id"] = predecessor
            raw["resume_subpath"] = f"memorybank-{output_slug}"
        # Validate the author-facing manifest, but preserve that schema on disk.
        # ``submit_docker_research_job.py`` validates the persisted YAML again;
        # serializing its normalized internal representation would drop the
        # nested resources/budget objects and make an otherwise valid job
        # impossible to submit.
        validate_manifest(raw)
        manifests[arm] = raw
    return manifests


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image-id", required=True)
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--git-sha", required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--model-cache-host", required=True)
    parser.add_argument("--receipt-sha256", required=True)
    parser.add_argument("--remote-bundle-root", required=True)
    parser.add_argument(
        "--resume-arm",
        action="append",
        default=[],
        metavar="ARM=JOB_ID",
        help="resume one registered arm from a predecessor Slurm job",
    )
    parser.add_argument("--experiment", type=Path, default=DEFAULT_EXPERIMENT)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    resume_from_job_ids: dict[str, int] = {}
    for item in args.resume_arm:
        arm, separator, job_id = item.partition("=")
        if not separator or not job_id.isdigit() or arm in resume_from_job_ids:
            raise ValueError("--resume-arm must be a unique ARM=JOB_ID pair")
        resume_from_job_ids[arm] = int(job_id)
    manifests = compile_manifests(
        image_id=args.image_id,
        run_root=args.run_root,
        git_sha=args.git_sha,
        source_sha256=args.source_sha256,
        model_cache_host=args.model_cache_host,
        receipt_sha256=args.receipt_sha256,
        remote_bundle_root=args.remote_bundle_root,
        resume_from_job_ids=resume_from_job_ids,
        experiment_path=args.experiment,
        registry_path=args.registry,
    )
    if args.output_dir is None:
        print(yaml.safe_dump(manifests, sort_keys=False), end="")
        return 0
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for arm, manifest in manifests.items():
        path = args.output_dir / f"memorybank-{arm.replace('_', '-')}.yaml"
        if path.exists():
            raise ValueError(f"refusing to overwrite manifest: {path}")
        path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    print(json.dumps({"arms": sorted(manifests), "count": len(manifests)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
