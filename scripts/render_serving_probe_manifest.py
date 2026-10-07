#!/usr/bin/env python3
"""Render a serving-throughput-probe-v1 job manifest from measured receipts.

Inputs are artifacts, never copied hashes: the vLLM overlay build receipt (image ID,
git SHA, source-capsule SHA-256, image variant) and, for dummy-weight jobs, the
metadata receipts written by fetch-model-metadata-in-docker.sh. The renderer
replaces the template's FILL_* sentinels, cross-checks the result against the
probe contract and the current lane validator, and refuses to overwrite. Job C
renders only from job A's output directory, and only when job A is accepted and
its control X1 passed (preregistration design decisions 21 and 33).
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.serving_probe.config import ProbeConfigError, load_config  # noqa: E402
from scripts.submit_docker_research_job import validate_manifest  # noqa: E402

CONTAINER_PROFILES = {"default", "vllm", "large-cpu-mem"}
RUN_ROOT_PREFIX = "/home/kevin/cotcodec-runs/stage0/serving-throughput-probe/"
IMAGE_ID_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_RE = re.compile(r"^[0-9a-f]{40}$")


class RenderError(ValueError):
    """Raised when a manifest cannot be rendered from the given receipts."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_build_receipt(path: Path) -> dict[str, str]:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if receipt.get("kind") != "vllm-overlay-build":
        raise RenderError("build receipt is not a vLLM overlay build receipt")
    values = {
        "image_id": receipt.get("overlay_image_id"),
        "git_sha": receipt.get("git_sha"),
        "source_sha256": receipt.get("source_sha256"),
        "variant": receipt.get("variant"),
    }
    if not IMAGE_ID_RE.fullmatch(str(values["image_id"])):
        raise RenderError("build receipt overlay_image_id is malformed")
    if not GIT_RE.fullmatch(str(values["git_sha"])):
        raise RenderError("build receipt git_sha is malformed")
    if not SHA_RE.fullmatch(str(values["source_sha256"])):
        raise RenderError("build receipt source_sha256 is malformed")
    if values["variant"] not in {"cu129", "cu130"}:
        raise RenderError("build receipt variant must be cu129 or cu130")
    return {key: str(value) for key, value in values.items()}


def read_metadata_receipt(path: Path) -> tuple[str, str]:
    """Return ``(model_id, "RECEIPT_SHA256:ARTIFACT_ROOT")`` for a metadata-mode receipt."""
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if receipt.get("mode") != "metadata" or receipt.get("publication_eligible") is not False:
        raise RenderError(f"{path.name} is not a metadata-mode receipt")
    root = str(receipt.get("artifact_root_sha256", ""))
    if not SHA_RE.fullmatch(root):
        raise RenderError(f"{path.name} has a malformed artifact root")
    return str(receipt["model_id"]), f"{sha256_file(path)}:{root}"


def _option_values(command: Sequence[str], option: str) -> list[str]:
    return [command[i + 1] for i, part in enumerate(command[:-1]) if part == option]


def _seeds_after(command: Sequence[str], flag: str) -> list[int]:
    if command.count(flag) != 1:
        raise RenderError(f"command must contain exactly one {flag}")
    seeds = []
    for part in command[command.index(flag) + 1 :]:
        if part.startswith("--"):
            break
        seeds.append(int(part))
    return seeds


def render(
    template: Mapping[str, Any],
    *,
    build: Mapping[str, str],
    pins: Mapping[str, str],
    job_a_output: Path | None = None,
    config_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    manifest = copy.deepcopy(dict(template))
    manifest["image_id"] = build["image_id"]
    manifest["git_sha"] = build["git_sha"]
    manifest["source_sha256"] = build["source_sha256"]
    command = []
    for part in manifest["command"]:
        if part == "FILL_IMAGE_VARIANT":
            command.append(build["variant"])
        elif isinstance(part, str) and part.startswith("FILL_PIN_"):
            model_id = part.removeprefix("FILL_PIN_")
            if model_id not in pins:
                raise RenderError(f"no metadata receipt given for {model_id}")
            command.append(f"{model_id}={pins[model_id]}")
        else:
            command.append(part)
    manifest["command"] = command
    leftover = [key for key, value in manifest.items() if "FILL_" in json.dumps(value)]
    if leftover:
        raise RenderError(f"unfilled sentinels remain in {leftover}")
    check_rendered(manifest, config_root=config_root, pins=pins, job_a_output=job_a_output)
    return manifest


def check_job_c_gate(config: Any, job_a_output: Path | None) -> None:
    """Refuse job C unless job A is accepted and its control X1 passed."""
    from scripts.run_vllm_throughput_probe import ProjectionError, job_c_gate

    if job_a_output is None:
        raise RenderError(
            "job C renders only from job A's output directory (--job-a-output), after "
            "control X1 passed"
        )
    try:
        verdict = job_c_gate(config, job_a_output)
    except (ProjectionError, OSError, ValueError) as exc:
        raise RenderError(f"job A output {job_a_output} cannot be read: {exc}") from exc
    if not verdict["job_a"]["accepted"]:
        reasons = "; ".join(verdict["job_a"]["reasons"])
        raise RenderError(f"job C needs an accepted job A; job A is not accepted: {reasons}")
    if not verdict["submit"]:
        raise RenderError(
            f"job C needs control X1 to pass; job A has X1 {verdict['x1']['outcome']}"
        )


def check_rendered(
    manifest: Mapping[str, Any],
    *,
    config_root: Path,
    pins: Mapping[str, str],
    job_a_output: Path | None = None,
) -> None:
    """Cross-check a rendered manifest against the probe contract and the lane."""
    if manifest.get("container_profile") not in CONTAINER_PROFILES:
        raise RenderError("container_profile must be one of the lane profiles")
    if manifest.get("container_profile") != "vllm":
        raise RenderError("the probe runs only in the vllm container profile")
    binding = manifest.get("seed_binding")
    if not isinstance(binding, Mapping) or binding.get("flag") != "--seeds":
        raise RenderError("seed_binding.flag must be --seeds")
    if not str(manifest.get("run_root", "")).startswith(RUN_ROOT_PREFIX):
        raise RenderError(f"run_root must live under {RUN_ROOT_PREFIX}")
    command = list(manifest["command"])
    if _seeds_after(command, "--seeds") != list(manifest["seeds"]):
        raise RenderError("command seeds differ from the manifest seeds")
    (config_path,) = _option_values(command, "--config")
    (job_id,) = _option_values(command, "--job")
    (minutes,) = _option_values(command, "--allocation-minutes")
    try:
        config = load_config(config_root / config_path)
        job = config.job(job_id)
    except ProbeConfigError as exc:
        raise RenderError(str(exc)) from exc
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
    pinned = {value.split("=", 1)[0] for value in _option_values(command, "--weights-pin")}
    if pinned != set(job.pinned_models()):
        raise RenderError(f"weight pins {sorted(pinned)} differ from {job.pinned_models()}")
    validated = validate_manifest(dict(manifest), verify_claim_files=False)
    if validated["gpus"] * validated["minutes"] / 60 > validated["max_gpu_hours"] + 1e-9:
        raise RenderError("max_gpu_hours is below the allocation")
    if job_id == "c":
        check_job_c_gate(config, job_a_output)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--build-receipt", type=Path, required=True)
    parser.add_argument("--metadata-receipt", type=Path, action="append", default=[])
    parser.add_argument(
        "--job-a-output",
        type=Path,
        help=(
            "job A's probe output directory, inside the lane run directory that holds its "
            "termination.env (required for job C: accepted, X1 passed)"
        ),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    template = yaml.safe_load(args.template.read_text(encoding="utf-8"))
    try:
        build = read_build_receipt(args.build_receipt)
        pins = dict(read_metadata_receipt(path) for path in args.metadata_receipt)
        manifest = render(template, build=build, pins=pins, job_a_output=args.job_a_output)
    except (RenderError, ValueError, KeyError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    header = (
        f"# Rendered from {args.template.as_posix()} by scripts/render_serving_probe_manifest.py\n"
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
