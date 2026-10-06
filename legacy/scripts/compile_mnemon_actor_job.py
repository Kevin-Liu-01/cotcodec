#!/usr/bin/env python3
"""Compile the bounded Docker-under-Slurm Mnemon H100 actor screen."""

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
from scripts.submit_docker_research_job import RUNTIME, validate_manifest  # noqa: E402
from scripts.validate_mnemon_actor_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    validate_experiment_contract,
)

MNEMON_REVISION = "88d2981edeb18a5ebe048af472f6f96527615454"
PANEL_SHA256 = "43a416c62be619de641aa60ecefc83ad0efdd605f7f13fd8821936704acacee5"
PANEL_SIZE = 96_980


def compile_manifest(
    *,
    image_id: str,
    run_root: str,
    git_sha: str,
    source_sha256: str,
    model_cache_host: str,
    receipt_sha256: str,
    panel_host_path: str,
    panel_sha256: str = PANEL_SHA256,
    panel_size: int = PANEL_SIZE,
    resume_from_job_id: str | None = None,
    resume_subpath: str | None = None,
    experiment_path: Path = DEFAULT_EXPERIMENT,
    registry_path: Path = DEFAULT_REGISTRY,
) -> dict[str, Any]:
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
        raise ValueError("Mnemon actor model registry identity drifted")
    if panel_sha256 != config["input"]["panel_sha256"] or panel_size != PANEL_SIZE:
        raise ValueError("Mnemon actor panel identity differs from the sealed artifact")
    if (resume_from_job_id is None) != (resume_subpath is None):
        raise ValueError("resume job id and subpath must be supplied together")
    if resume_subpath is not None and resume_subpath != "mnemon-actor":
        raise ValueError("Mnemon actor resumes only the mnemon-actor subtree")
    command = [
        "python",
        "scripts/run_mnemon_actor_screen.py",
        "experiments/memory/stage3-mnemon-static-space-h100-actor.yaml",
        "--evidence",
        "/inputs/study-artifact.json",
        "--expected-evidence-sha256",
        panel_sha256,
        "--output-dir",
        "/outputs/mnemon-actor",
        "--model-root",
        "/model-cache/cotcodec-models",
        "--receipt-root",
        "/model-cache/cotcodec-receipts",
    ]
    execution = config["execution"]
    raw: dict[str, Any] = {
        "runtime": RUNTIME,
        "name": "mnemon-qwen35-4b-static-space",
        "image_id": image_id,
        "git_sha": git_sha,
        "source_sha256": source_sha256,
        "run_root": run_root,
        "command": command,
        "randomness_contract": "deterministic-all-serve",
        "seeds": [],
        "model": {
            "cache_host_path": model_cache_host,
            "model_id": model["model_id"],
            "revision": model["revision"],
            "receipt_sha256": receipt_sha256,
            "artifact_root_sha256": model["artifact_root_sha256"],
        },
        "study_artifact": {
            "source_id": "mnemon-static-space-panel-v1",
            "revision": MNEMON_REVISION,
            "license": "Apache-2.0",
            "host_path": panel_host_path,
            "sha256": panel_sha256,
            "size_bytes": panel_size,
        },
        "resources": {
            "gpu_type": execution["gpu_type"],
            "gpus": execution["gpus"],
            "cpus": execution["cpus"],
            "memory_gb": execution["memory_gb"],
            "minutes": execution["minutes"],
        },
        "budget": {"max_gpu_hours": execution["max_gpu_hours"]},
        "memory_source_admission": build_memory_job_admission(
            [("mnemon", MNEMON_REVISION)]
        ),
    }
    if resume_from_job_id is not None and resume_subpath is not None:
        raw["resume_from_job_id"] = resume_from_job_id
        raw["resume_subpath"] = resume_subpath
    validate_manifest(raw)
    return raw


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image-id", required=True)
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--git-sha", required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--model-cache-host", required=True)
    parser.add_argument("--receipt-sha256", required=True)
    parser.add_argument("--panel-host-path", required=True)
    parser.add_argument("--panel-sha256", default=PANEL_SHA256)
    parser.add_argument("--panel-size", type=int, default=PANEL_SIZE)
    parser.add_argument("--resume-from-job-id")
    parser.add_argument("--resume-subpath", choices=("mnemon-actor",))
    parser.add_argument("--experiment", type=Path, default=DEFAULT_EXPERIMENT)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    manifest = compile_manifest(
        image_id=args.image_id,
        run_root=args.run_root,
        git_sha=args.git_sha,
        source_sha256=args.source_sha256,
        model_cache_host=args.model_cache_host,
        receipt_sha256=args.receipt_sha256,
        panel_host_path=args.panel_host_path,
        panel_sha256=args.panel_sha256,
        panel_size=args.panel_size,
        resume_from_job_id=args.resume_from_job_id,
        resume_subpath=args.resume_subpath,
        experiment_path=args.experiment,
        registry_path=args.registry,
    )
    rendered = yaml.safe_dump(manifest, sort_keys=False)
    if args.output is None:
        print(rendered, end="")
    else:
        if args.output.exists():
            raise ValueError(f"refusing to overwrite manifest: {args.output}")
        args.output.write_text(rendered, encoding="utf-8")
        print(json.dumps({"manifest": str(args.output), "study": "mnemon-actor"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
