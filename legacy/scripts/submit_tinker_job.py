#!/usr/bin/env python3
"""Validate and submit a CPU-only Slurm client for managed Tinker training."""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
from pathlib import Path
from typing import Any

import yaml

OCI_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[0-9a-f]{64}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_RE = re.compile(r"^[0-9a-f]{40}$")
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
RUN_ROOT_RE = re.compile(r"^/[A-Za-z0-9._/-]{1,255}$")
CONTRACT_RE = re.compile(r"^experiments/tinker/[a-z0-9][a-z0-9-]{0,63}\.yaml$")
SECRET_KEY_RE = re.compile(r"(?:api.?key|password|secret|access.?token)", re.IGNORECASE)
MAX_SINGLE_JOB_USD = 50.0


def _integer(mapping: dict[str, Any], key: str, minimum: int, maximum: int) -> int:
    value = mapping.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
        raise ValueError(f"{key} must be an integer in [{minimum}, {maximum}]")
    return value


def _reject_secret_material(value: Any, path: str = "manifest") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(key, str) and SECRET_KEY_RE.search(key):
                raise ValueError(f"secret material is forbidden in manifests: {path}.{key}")
            _reject_secret_material(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_secret_material(child, f"{path}[{index}]")


def validate_manifest(raw: dict[str, Any]) -> dict[str, Any]:
    _reject_secret_material(raw)
    name = raw.get("name")
    image = raw.get("image")
    command = raw.get("command")
    run_root = raw.get("run_root")
    git_sha = raw.get("git_sha")
    source_sha = raw.get("source_sha256")
    contract = raw.get("contract")
    contract_sha = raw.get("contract_sha256")
    train_jsonl = raw.get("train_jsonl")
    train_sha = raw.get("train_sha256")
    resources = raw.get("resources")
    budget = raw.get("budget")
    seeds = raw.get("seeds")
    run_seed = raw.get("run_seed")

    if raw.get("backend") != "tinker":
        raise ValueError("backend must equal tinker")
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
    if not isinstance(contract, str) or not CONTRACT_RE.fullmatch(contract):
        raise ValueError("contract must be a repository-relative experiments/tinker YAML path")
    if not isinstance(contract_sha, str) or not SHA_RE.fullmatch(contract_sha):
        raise ValueError("contract_sha256 must be 64 lowercase hex characters")
    if (
        not isinstance(train_jsonl, str)
        or not RUN_ROOT_RE.fullmatch(train_jsonl)
        or ".." in Path(train_jsonl).parts
    ):
        raise ValueError("train_jsonl must be a simple absolute path without traversal")
    if not isinstance(train_sha, str) or not SHA_RE.fullmatch(train_sha):
        raise ValueError("train_sha256 must be 64 lowercase hex characters")
    if not isinstance(resources, dict) or not isinstance(budget, dict):
        raise ValueError("resources and budget objects are required")
    if "gpus" in resources or "gpu_type" in resources:
        raise ValueError("Tinker clients are CPU-only; GPU requests are forbidden")

    cpus = _integer(resources, "cpus", 1, 64)
    memory_gb = _integer(resources, "memory_gb", 1, 256)
    minutes = _integer(resources, "minutes", 1, 24 * 60)
    max_usd = budget.get("max_usd")
    if (
        not isinstance(max_usd, (int, float))
        or isinstance(max_usd, bool)
        or not math.isfinite(float(max_usd))
        or float(max_usd) <= 0
    ):
        raise ValueError("budget.max_usd must be a positive finite number")
    if float(max_usd) > MAX_SINGLE_JOB_USD:
        raise ValueError(
            f"budget.max_usd exceeds the ${MAX_SINGLE_JOB_USD:g} single-job safety ceiling"
        )
    if (
        not isinstance(seeds, list)
        or len(set(seeds)) < 3
        or not all(isinstance(seed, int) and not isinstance(seed, bool) for seed in seeds)
    ):
        raise ValueError("seeds must contain at least three distinct integers")
    if not isinstance(run_seed, int) or isinstance(run_seed, bool) or run_seed not in seeds:
        raise ValueError("run_seed must be one of the registered seeds")
    if contract not in command:
        raise ValueError("command must reference the validated Tinker contract")
    if "--seed" not in command:
        raise ValueError("command must declare --seed")
    seed_index = command.index("--seed") + 1
    if seed_index >= len(command) or command[seed_index] != str(run_seed):
        raise ValueError("command --seed must match run_seed")
    if "/inputs/train.jsonl" not in command:
        raise ValueError("command must consume the read-only /inputs/train.jsonl mount")

    return {
        "backend": "tinker",
        "name": name,
        "image": image,
        "command": command,
        "run_root": run_root,
        "git_sha": git_sha,
        "source_sha256": source_sha,
        "contract": contract,
        "contract_sha256": contract_sha,
        "train_jsonl": train_jsonl,
        "train_sha256": train_sha,
        "seeds": seeds,
        "run_seed": run_seed,
        "cpus": cpus,
        "memory_gb": memory_gb,
        "minutes": minutes,
        "max_usd": float(max_usd),
    }


def sbatch_argv(manifest: dict[str, Any], test_only: bool) -> list[str]:
    hours, minutes = divmod(manifest["minutes"], 60)
    command_hex = json.dumps(manifest["command"], separators=(",", ":")).encode().hex()
    manifest_hex = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode().hex()
    exported = {
        "COTCODEC_IMAGE": manifest["image"],
        "COTCODEC_COMMAND_JSON_HEX": command_hex,
        "COTCODEC_MANIFEST_JSON_HEX": manifest_hex,
        "COTCODEC_RUN_ROOT": manifest["run_root"],
        "COTCODEC_GIT_SHA": manifest["git_sha"],
        "COTCODEC_SOURCE_SHA256": manifest["source_sha256"],
        "COTCODEC_TINKER_CONTRACT": manifest["contract"],
        "COTCODEC_TINKER_CONTRACT_SHA256": manifest["contract_sha256"],
        "COTCODEC_TRAIN_JSONL": manifest["train_jsonl"],
        "COTCODEC_TRAIN_SHA256": manifest["train_sha256"],
        "COTCODEC_SEEDS": ":".join(str(seed) for seed in manifest["seeds"]),
        "COTCODEC_RUN_SEED": str(manifest["run_seed"]),
    }
    export_arg = ",".join(f"{key}={value}" for key, value in exported.items())
    argv = [
        "sbatch",
        "--parsable",
        f"--job-name={manifest['name']}",
        f"--cpus-per-task={manifest['cpus']}",
        f"--mem={manifest['memory_gb']}G",
        f"--time={hours:02d}:{minutes:02d}:00",
        f"--output={manifest['run_root']}/slurm-%j.out",
        f"--export={export_arg}",
    ]
    if test_only:
        argv.append("--test-only")
    argv.append("infra/slurm/tinker.sbatch")
    return argv


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--test-only", action="store_true")
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
        print(json.dumps({"argv": argv, "max_usd": manifest["max_usd"]}, indent=2))
        return
    completed = subprocess.run(argv, check=True, text=True, capture_output=True)
    print(completed.stdout.strip())


if __name__ == "__main__":
    main()
