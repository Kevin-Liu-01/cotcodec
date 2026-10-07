#!/usr/bin/env python3
"""Render the serving-throughput-probe-v2 job manifest from the overlay build receipt.

Inputs are artifacts, never copied hashes: the vLLM overlay build receipt (image
ID, git SHA, source-capsule SHA-256, image variant). The renderer replaces the
template's FILL_* sentinels, cross-checks the result against the v2 contract and
the current lane validator, and refuses to overwrite. v2 has one job (a), no
dummy-weight metadata pins and no conditional rung job. The receipt parsing is
v1's (``scripts/render_serving_probe_manifest.py``).
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.serving_probe.config import ProbeConfigError  # noqa: E402
from harness.serving_probe_v2.config import load_config  # noqa: E402
from scripts.render_serving_probe_manifest import (  # noqa: E402
    RenderError,
    _option_values,
    _seeds_after,
    read_build_receipt,
    sha256_file,
)
from scripts.submit_docker_research_job import validate_manifest  # noqa: E402

RUN_ROOT_PREFIX = "/home/kevin/cotcodec-runs/stage0/serving-throughput-probe-v2/"
DRIVER = "scripts/run_vllm_throughput_probe_v2.py"


def render(
    template: Mapping[str, Any],
    *,
    build: Mapping[str, str],
    config_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    manifest = copy.deepcopy(dict(template))
    manifest["image_id"] = build["image_id"]
    manifest["git_sha"] = build["git_sha"]
    manifest["source_sha256"] = build["source_sha256"]
    manifest["command"] = [
        build["variant"] if part == "FILL_IMAGE_VARIANT" else part for part in manifest["command"]
    ]
    leftover = [key for key, value in manifest.items() if "FILL_" in json.dumps(value)]
    if leftover:
        raise RenderError(f"unfilled sentinels remain in {leftover}")
    check_rendered(manifest, config_root=config_root)
    return manifest


def check_rendered(manifest: Mapping[str, Any], *, config_root: Path) -> None:
    """Cross-check a rendered manifest against the v2 contract and the lane."""
    if manifest.get("container_profile") != "vllm":
        raise RenderError("the probe runs only in the vllm container profile")
    binding = manifest.get("seed_binding")
    if not isinstance(binding, Mapping) or binding.get("flag") != "--seeds":
        raise RenderError("seed_binding.flag must be --seeds")
    if not str(manifest.get("run_root", "")).startswith(RUN_ROOT_PREFIX):
        raise RenderError(f"run_root must live under {RUN_ROOT_PREFIX}")
    command = list(manifest["command"])
    if command[:3] != ["python", DRIVER, "run"]:
        raise RenderError(f"the command must run {DRIVER}")
    if _seeds_after(command, "--seeds") != list(manifest["seeds"]):
        raise RenderError("command seeds differ from the manifest seeds")
    if _option_values(command, "--weights-pin"):
        raise RenderError("v2 pins no dummy-weight metadata")
    (config_path,) = _option_values(command, "--config")
    (job_id,) = _option_values(command, "--job")
    (minutes,) = _option_values(command, "--allocation-minutes")
    (variant,) = _option_values(command, "--image-variant")
    try:
        config = load_config(config_root / config_path)
        job = config.job(job_id)
    except ProbeConfigError as exc:
        raise RenderError(str(exc)) from exc
    if variant not in config.section("vllm")["image_variants"]:
        raise RenderError(f"image variant {variant} is not in the v2 contract")
    if list(config.primary_seeds) != list(manifest["seeds"]):
        raise RenderError("manifest seeds differ from the contract's primary seeds")
    resources = manifest["resources"]
    if int(resources["gpus"]) != 1:
        raise RenderError("the probe runs on exactly one GPU (TP=1, gate G0.2)")
    if int(minutes) != int(resources["minutes"]) or int(minutes) != job.allocation_minutes:
        raise RenderError("allocation minutes differ between command, resources and contract")
    if manifest["model"]["model_id"] != job.lane_model:
        raise RenderError("the bound model differs from the contract's lane model")
    lane = config.models[job.lane_model]
    for key in ("revision", "receipt_sha256", "artifact_root_sha256"):
        if manifest["model"][key] != lane[key]:
            raise RenderError(f"bound model {key} differs from the contract")
    validated = validate_manifest(dict(manifest), verify_claim_files=False)
    hours = validated["gpus"] * validated["minutes"] / 60
    if hours > validated["max_gpu_hours"] + 1e-9:
        raise RenderError("max_gpu_hours is below the allocation")
    if hours > 1.0 + 1e-9:
        raise RenderError("v2's probe cap is 1.0 GPU-h")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--build-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    template = yaml.safe_load(args.template.read_text(encoding="utf-8"))
    try:
        build = read_build_receipt(args.build_receipt)
        manifest = render(template, build=build)
    except (RenderError, ValueError, KeyError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    header = (
        f"# Rendered from {args.template.as_posix()} by "
        "scripts/render_serving_probe_v2_manifest.py\n"
        f"# build receipt sha256 {sha256_file(args.build_receipt)}\n"
    )
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        descriptor = os.open(args.output, flags, 0o644)
    except FileExistsError:
        print(f"FAIL: refusing to overwrite {args.output}", file=sys.stderr)
        return 2
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(header + yaml.safe_dump(manifest, sort_keys=False))
    print(json.dumps({"output": str(args.output), "name": manifest["name"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
