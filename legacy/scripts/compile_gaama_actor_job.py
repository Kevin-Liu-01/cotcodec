#!/usr/bin/env python3
"""Compile the bounded Docker-under-Slurm GAAMA H100 actor screen."""

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
from scripts.validate_gaama_actor_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    validate_experiment_contract,
)

GAAMA_REVISION = "2d992f7f7b97c802bfe4c799878a5477cac1b6ff"
EVIDENCE_SHA256 = "011a21918946e19255c1118de41ec99131e1cb64c32b50bc68af8da58d84dc79"
EVIDENCE_SIZE = 2_173_200


def compile_manifest(
    *,
    image_id: str,
    run_root: str,
    git_sha: str,
    source_sha256: str,
    model_cache_host: str,
    receipt_sha256: str,
    evidence_host_path: str,
    evidence_sha256: str = EVIDENCE_SHA256,
    evidence_size: int = EVIDENCE_SIZE,
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
        raise ValueError("GAAMA actor model registry identity drifted")
    if evidence_sha256 != config["input"]["evidence_sha256"]:
        raise ValueError("GAAMA actor evidence digest differs from the experiment")
    if evidence_size != EVIDENCE_SIZE:
        raise ValueError("GAAMA actor evidence size differs from the sealed bundle")
    if (resume_from_job_id is None) != (resume_subpath is None):
        raise ValueError("resume job id and subpath must be supplied together")
    if resume_subpath is not None and resume_subpath != "gaama-actor":
        raise ValueError("GAAMA actor resumes only the gaama-actor subtree")
    command = [
        "python",
        "scripts/run_gaama_actor_screen.py",
        "experiments/memory/stage3-gaama-h100-actor-screen.yaml",
        "--evidence",
        "/inputs/study-artifact.json",
        "--expected-evidence-sha256",
        evidence_sha256,
        "--output-dir",
        "/outputs/gaama-actor",
        "--model-root",
        "/model-cache/cotcodec-models",
        "--receipt-root",
        "/model-cache/cotcodec-receipts",
    ]
    execution = config["execution"]
    raw: dict[str, Any] = {
        "runtime": RUNTIME,
        "name": "gaama-qwen35-4b-actor",
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
            "source_id": "gaama-natural-v5",
            "revision": GAAMA_REVISION,
            "license": "CC-BY-NC-4.0",
            "host_path": evidence_host_path,
            "sha256": evidence_sha256,
            "size_bytes": evidence_size,
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
            [("gaama", GAAMA_REVISION)]
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
    parser.add_argument("--evidence-host-path", required=True)
    parser.add_argument("--evidence-sha256", default=EVIDENCE_SHA256)
    parser.add_argument("--evidence-size", type=int, default=EVIDENCE_SIZE)
    parser.add_argument("--resume-from-job-id")
    parser.add_argument("--resume-subpath", choices=("gaama-actor",))
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
        evidence_host_path=args.evidence_host_path,
        evidence_sha256=args.evidence_sha256,
        evidence_size=args.evidence_size,
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
        print(json.dumps({"manifest": str(args.output), "study": "gaama-actor"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
