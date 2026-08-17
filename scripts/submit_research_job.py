#!/usr/bin/env python3
"""Validate a bounded research manifest and submit it through Slurm."""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
from pathlib import Path
from typing import Any

import yaml

if __package__:
    from scripts.memory_job_admission import validate_memory_job_admission
else:
    from memory_job_admission import validate_memory_job_admission

OCI_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[0-9a-f]{64}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_RE = re.compile(r"^[0-9a-f]{40}$")
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
RUN_ROOT_RE = re.compile(r"^/[A-Za-z0-9._/-]{1,255}$")
INPUT_PATH_RE = re.compile(r"^/[A-Za-z0-9._/-]{1,511}$")
JOB_ID_RE = re.compile(r"^[1-9][0-9]{0,19}$")
SUBPATH_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")
MAX_SINGLE_JOB_GPU_HOURS = 64.0


def _integer(mapping: dict[str, Any], key: str, minimum: int, maximum: int) -> int:
    value = mapping.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
        raise ValueError(f"{key} must be an integer in [{minimum}, {maximum}]")
    return value


def validate_manifest(raw: dict[str, Any]) -> dict[str, Any]:
    name = raw.get("name")
    image = raw.get("image")
    command = raw.get("command")
    run_root = raw.get("run_root")
    git_sha = raw.get("git_sha")
    source_sha = raw.get("source_sha256")
    resources = raw.get("resources")
    budget = raw.get("budget")
    seeds = raw.get("seeds")
    resume_from_job_id = raw.get("resume_from_job_id")
    resume_subpath = raw.get("resume_subpath")
    memory_bundle = raw.get("memory_bundle")

    if not isinstance(name, str) or not NAME_RE.fullmatch(name):
        raise ValueError("name must be a lowercase kebab-case Slurm-safe slug")
    if not isinstance(image, str) or not OCI_RE.fullmatch(image):
        raise ValueError("image must contain a full immutable OCI digest")
    if (
        not isinstance(command, list)
        or not command
        or len(command) > 64
        or not all(
            isinstance(argument, str)
            and argument
            and "\x00" not in argument
            and "\n" not in argument
            for argument in command
        )
    ):
        raise ValueError("command must be an argv list of 1-64 nonempty strings")
    if (
        not isinstance(run_root, str)
        or not RUN_ROOT_RE.fullmatch(run_root)
        or ".." in Path(run_root).parts
    ):
        raise ValueError("run_root must be a simple absolute path without traversal")
    if not isinstance(git_sha, str) or not GIT_RE.fullmatch(git_sha):
        raise ValueError("git_sha must be 40 lowercase hex characters")
    if not isinstance(source_sha, str) or not SHA_RE.fullmatch(source_sha):
        raise ValueError("source_sha256 must be 64 lowercase hex characters")
    if not isinstance(resources, dict) or not isinstance(budget, dict):
        raise ValueError("resources and budget objects are required")

    gpu_type = resources.get("gpu_type")
    if gpu_type != "h100":
        raise ValueError("the audited cluster contract currently permits only gpu_type=h100")
    gpus = _integer(resources, "gpus", 1, 8)
    cpus = _integer(resources, "cpus", 1, 208)
    memory_gb = _integer(resources, "memory_gb", 1, 1700)
    minutes = _integer(resources, "minutes", 1, 24 * 60)
    max_gpu_hours = budget.get("max_gpu_hours")
    if (
        not isinstance(max_gpu_hours, (int, float))
        or isinstance(max_gpu_hours, bool)
        or not math.isfinite(float(max_gpu_hours))
        or float(max_gpu_hours) <= 0
    ):
        raise ValueError("budget.max_gpu_hours must be a positive finite number")
    if float(max_gpu_hours) > MAX_SINGLE_JOB_GPU_HOURS:
        raise ValueError(
            f"budget.max_gpu_hours exceeds the {MAX_SINGLE_JOB_GPU_HOURS:g} GPU-hour "
            "single-job safety ceiling"
        )
    requested_gpu_hours = gpus * minutes / 60
    if requested_gpu_hours > float(max_gpu_hours):
        raise ValueError(
            f"allocation requests {requested_gpu_hours:.2f} GPU-hours, above budget {max_gpu_hours}"
        )
    if (
        not isinstance(seeds, list)
        or len(set(seeds)) < 3
        or not all(isinstance(seed, int) and not isinstance(seed, bool) for seed in seeds)
    ):
        raise ValueError("seeds must contain at least three distinct integers")
    if resume_from_job_id is None:
        if resume_subpath is not None:
            raise ValueError("resume_subpath requires resume_from_job_id")
        normalized_predecessor = None
        normalized_subpath = None
    else:
        normalized_predecessor = str(resume_from_job_id)
        if not JOB_ID_RE.fullmatch(normalized_predecessor):
            raise ValueError("resume_from_job_id must be a positive Slurm job id")
        if (
            not isinstance(resume_subpath, str)
            or not SUBPATH_RE.fullmatch(resume_subpath)
            or Path(resume_subpath).is_absolute()
            or ".." in Path(resume_subpath).parts
        ):
            raise ValueError("resume_subpath must be a safe relative artifact directory")
        normalized_subpath = resume_subpath

    manifest = {
        "name": name,
        "image": image,
        "command": command,
        "run_root": run_root,
        "git_sha": git_sha,
        "source_sha256": source_sha,
        "seeds": seeds,
        "gpu_type": gpu_type,
        "gpus": gpus,
        "cpus": cpus,
        "memory_gb": memory_gb,
        "minutes": minutes,
        "max_gpu_hours": float(max_gpu_hours),
    }
    if normalized_predecessor is not None:
        manifest["resume_from_job_id"] = normalized_predecessor
        manifest["resume_subpath"] = normalized_subpath
    if memory_bundle is not None:
        if not isinstance(memory_bundle, dict):
            raise ValueError("memory_bundle must be a mapping")
        host_path = memory_bundle.get("host_path")
        artifact_sha256 = memory_bundle.get("sha256")
        container_path = memory_bundle.get(
            "container_path", "/inputs/memory-selection-bundle.json"
        )
        if (
            not isinstance(host_path, str)
            or not INPUT_PATH_RE.fullmatch(host_path)
            or ".." in Path(host_path).parts
        ):
            raise ValueError("memory_bundle.host_path must be a simple absolute path")
        if not isinstance(artifact_sha256, str) or not SHA_RE.fullmatch(artifact_sha256):
            raise ValueError("memory_bundle.sha256 must be 64 lowercase hex characters")
        if container_path != "/inputs/memory-selection-bundle.json":
            raise ValueError("memory_bundle.container_path is fixed by the batch contract")
        manifest["memory_bundle"] = {
            "host_path": host_path,
            "sha256": artifact_sha256,
            "container_path": "/inputs/memory-selection-bundle.json",
        }
    admission = validate_memory_job_admission(
        raw.get("memory_source_admission"),
        command=command,
        has_memory_bundle=memory_bundle is not None,
    )
    if admission is not None:
        manifest["memory_source_admission"] = admission
    return manifest


def sbatch_argv(manifest: dict[str, Any], test_only: bool) -> list[str]:
    hours, minutes = divmod(manifest["minutes"], 60)
    command_json = json.dumps(manifest["command"], separators=(",", ":")).encode()
    command_hex = command_json.hex()
    manifest_hex = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode().hex()
    exported = {
        "COTCODEC_IMAGE": manifest["image"],
        "COTCODEC_COMMAND_JSON_HEX": command_hex,
        "COTCODEC_MANIFEST_JSON_HEX": manifest_hex,
        "COTCODEC_RUN_ROOT": manifest["run_root"],
        "COTCODEC_GIT_SHA": manifest["git_sha"],
        "COTCODEC_SOURCE_SHA256": manifest["source_sha256"],
        "COTCODEC_SEEDS": ":".join(str(seed) for seed in manifest["seeds"]),
        "COTCODEC_EXPECTED_GPUS": str(manifest["gpus"]),
    }
    if predecessor := manifest.get("resume_from_job_id"):
        exported["COTCODEC_PREDECESSOR_JOB_ID"] = predecessor
        exported["COTCODEC_RESUME_SUBPATH"] = manifest["resume_subpath"]
    if memory_bundle := manifest.get("memory_bundle"):
        exported["COTCODEC_MEMORY_BUNDLE_HOST_HEX"] = memory_bundle["host_path"].encode().hex()
        exported["COTCODEC_MEMORY_BUNDLE_SHA256"] = memory_bundle["sha256"]
    export_arg = ",".join(f"{key}={value}" for key, value in exported.items())
    argv = [
        "sbatch",
        "--parsable",
        f"--job-name={manifest['name']}",
        f"--gres=gpu:{manifest['gpu_type']}:{manifest['gpus']}",
        f"--cpus-per-task={manifest['cpus']}",
        f"--mem={manifest['memory_gb']}G",
        f"--time={hours:02d}:{minutes:02d}:00",
        f"--output={manifest['run_root']}/slurm-%j.out",
        f"--export={export_arg}",
    ]
    if test_only:
        argv.append("--test-only")
    argv.append("infra/slurm/research.sbatch")
    return argv


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="validate and print argv")
    parser.add_argument("--test-only", action="store_true", help="ask Slurm to validate only")
    args = parser.parse_args()
    raw = yaml.safe_load(args.manifest.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise SystemExit("manifest must contain a YAML object")
    try:
        manifest = validate_manifest(raw)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    argv = sbatch_argv(manifest, args.test_only)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "argv": argv,
                    "gpu_hours": math.prod([manifest["gpus"], manifest["minutes"]]) / 60,
                },
                indent=2,
            )
        )
        return
    completed = subprocess.run(argv, check=True, text=True, capture_output=True)
    print(completed.stdout.strip())


if __name__ == "__main__":
    main()
