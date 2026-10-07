#!/usr/bin/env python3
"""Validate a bounded research manifest and submit it through Slurm."""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

# Same rule as scripts/submit_docker_research_job.py and the batch script;
# tests keep the three copies in parity.
ARCHIVED_MEMORY_MESSAGE = (
    "memory workloads were archived under legacy/ on 2026-10-06; "
    "restore them from tag legacy-2026-10-06 to submit memory jobs"
)
# The whole archive lives under legacy/, so any path or module component named
# legacy is refused, whatever the file it leads to.
ARCHIVE_ROOT = "legacy"
# Matched against every path and dotted-module component, not only after
# scripts/, so PYTHONPATH, chdir and python -m forms are covered.
ARCHIVED_MEMORY_NAME_PATTERNS = (
    "run_memory_*",
    "run_letta*",
    "*memory_model*",
    "memory_trials",
)
# Every memory-named entry point the restart archived: the files and packages
# directly under legacy/scripts, legacy/harness and legacy/infra whose names
# contain "mem" or "letta", by stem. Exact names, so a live file is refused only
# if it reuses an archived name; this also covers pre-restart images, where these
# files still sit at scripts/<name>.py. Tests regenerate the set from legacy/.
ARCHIVED_MEMORY_ENTRY_POINTS = frozenset(
    """
    aggregate_memory_control_matrix aggregate_memorybank_h100_screen
    analyze_causal_memory_bundle analyze_memory_system_semantic_smokes
    analyze_memorybank_frozen_controls audit_memforest_published_artifacts
    audit_mempalace_port_equivalence audit_mempalace_upstream_artifact
    audit_sodamem_published_artifacts build_mem0_overlay_on_h100 build_mempalace_container
    causal_memory_trials compare_memory_lifecycle_runs compare_mempalace_reproductions
    compile_memory_landscape compile_memory_open_job compile_memory_public_docker_job
    compile_memory_publication_wave compile_memory_replay_doctor_job
    compile_memorybank_h100_jobs freeze_memory_control_matrix freeze_memory_system_outputs
    memory-baselines memory_job_admission memory_trials mempalace_control_factory
    mempalace_upstream_adapter prepare_hermes_observational_memory_context
    prepare_longmemeval_judge_packet prepare_memory_baseline_context
    prepare_memory_benchmarks prepare_memory_publication_claim
    prepare_mempalace_source_context reanalyze_memory_frontier_screen
    run_allmem_topology_doctor run_causal_memory_holdout run_causal_memory_sensitivity
    run_hermes_observational_memory_doctor run_infini_memory_lifecycle_doctor
    run_jiuwen_memory_lifecycle_doctor run_langmem_lifecycle_doctor
    run_lightmem2_context_paging_doctor run_lightmem_offline_doctor
    run_longmemeval_official_judge run_mem0_lifecycle_doctor run_memforest_lifecycle_doctor
    run_memforge_fresh_install_doctor run_memgpt_letta_lifecycle_doctor
    run_memoria_lifecycle_doctor run_memory_doctors run_memory_frontier_screen
    run_memory_lifecycle_contract run_memory_model_replay_doctor run_memory_model_screen
    run_memory_system_smoke run_memory_trials run_memorybank_decay_container
    run_memorybank_decay_doctor run_mempalace_upstream_reproduction
    run_recmem_consolidation_doctor run_reference_memory_lifecycle_sidecar
    run_reference_memory_sidecar run_supermemory_local_doctor
    seal_infini_memory_lifecycle_evidence seal_jiuwen_memory_lifecycle_evidence
    seal_langmem_native_lifecycle_evidence seal_lightmem2_context_paging_evidence
    seal_memforest_artifact_evidence seal_memforest_lifecycle_evidence
    seal_memgpt_letta_lifecycle_evidence seal_memory_evidence seal_mempalace_runtime_receipt
    seal_mempalace_sbom_job_receipt seal_sodamem_artifact_evidence submit_mempalace_cpu_job
    validate_allmem_topology_experiment validate_hermes_observational_memory_experiment
    validate_infini_memory_lifecycle_experiment validate_jiuwen_memory_lifecycle_experiment
    validate_langmem_lifecycle_experiment validate_lightmem2_context_paging_experiment
    validate_lightmem_offline_evidence validate_lightmem_offline_experiment
    validate_mem0_lifecycle_experiment validate_mem0_persistence
    validate_memforest_artifact_experiment validate_memforest_lifecycle_experiment
    validate_memforge_fresh_install_evidence validate_memforge_fresh_install_experiment
    validate_memgpt_letta_lifecycle_experiment validate_memoria_lifecycle_evidence
    validate_memoria_lifecycle_experiment validate_memory_experiments
    validate_memory_lifecycle_experiment validate_memory_persistent_transport
    validate_memory_portfolio validate_memory_source_contract validate_memory_sources
    validate_memorybank_decay_evidence validate_memorybank_decay_experiment
    validate_memorybank_h100_evidence validate_memorybank_h100_experiment
    validate_recmem_consolidation_evidence validate_recmem_consolidation_experiment
    validate_sodamem_artifact_experiment validate_supermemory_local_experiment
    validate_timem_core_evidence validate_timem_core_experiment
    verify_memory_baseline_sources
    """.split()  # noqa: SIM905 - same compact block as the batch script
)
ARCHIVED_MEMORY_FLAGS = (
    "--memory-bundle",
    "--memory-treatment-mode",
    "--expected-memory-system-id",
)
_ARGV_TOKEN_SEPARATORS = re.compile(r"[\s=,;:'\"`()\[\]{}<>|&$]+")
_MODULE_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")
_SCRIPT_SUFFIXES = (".py", ".pyc", ".pyw", ".sh")


def _argv_name_variants(token: str) -> list[str]:
    """The token, plus any value glued to a short option (python -mpkg.mod)."""

    variants = [token]
    if token.startswith("-") and not token.startswith("--"):
        # Up to three option letters may precede the value, as in -Bmpkg.mod.
        variants += [token[1 + cut :] for cut in range(4) if token[1 + cut :]]
    return variants


def _name_components(variant: str) -> list[str]:
    """Path components (with and without a script suffix) and module components."""

    components: list[str] = []
    for part in PurePosixPath(variant).parts:
        if part == "/":
            continue
        components.append(part)
        components += [part[: -len(suffix)] for suffix in _SCRIPT_SUFFIXES if part.endswith(suffix)]
    module = variant[:-3] if variant.endswith(".py") else variant
    if _MODULE_RE.fullmatch(module):
        components += module.split(".")
    return components


def archived_memory_reference(argument: str) -> str | None:
    """Return what an argv element names from the archive, or None.

    The element is split on shell and Python punctuation, a value glued to a
    short option is tried on its own, and every path or module component is
    compared with the archive root, the archived memory entry points and the
    archived name patterns. A long option that is an archived memory flag, or
    an argparse abbreviation of one, is refused too.
    """

    for token in _ARGV_TOKEN_SEPARATORS.split(argument):
        for variant in _argv_name_variants(token):
            if (
                variant.startswith("--")
                and len(variant) > 2
                and any(flag.startswith(variant) for flag in ARCHIVED_MEMORY_FLAGS)
            ):
                return f"the archived memory flag {variant}"
            for component in _name_components(variant):
                if component == ARCHIVE_ROOT:
                    return "the legacy/ archive"
                if component in ARCHIVED_MEMORY_ENTRY_POINTS or any(
                    fnmatchcase(component, pattern) for pattern in ARCHIVED_MEMORY_NAME_PATTERNS
                ):
                    return f"the archived memory entry point {component}"
    return None


def validate_memory_job_admission(
    admission: Any, *, command: list[str], has_memory_bundle: bool
) -> None:
    """Reject the archived memory interface, not every argv that mentions memory.

    Flags such as vLLM's ``--gpu-memory-utilization`` are admitted; anything
    under legacy/, the archived memory entry points and name patterns, the
    archived memory flags, and any memory admission or bundle block are not.
    """

    if admission is not None:
        raise ValueError(f"{ARCHIVED_MEMORY_MESSAGE}: memory_source_admission must be absent")
    if has_memory_bundle:
        raise ValueError(f"{ARCHIVED_MEMORY_MESSAGE}: memory_bundle must be absent")
    for index, argument in enumerate(command):
        reference = archived_memory_reference(str(argument))
        if reference is not None:
            raise ValueError(f"{ARCHIVED_MEMORY_MESSAGE}: argv[{index}] names {reference}")


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
    # Reject the archived memory interface before the bundle checks below can
    # produce a misleading error.
    validate_memory_job_admission(
        raw.get("memory_source_admission"),
        command=command,
        has_memory_bundle=memory_bundle is not None,
    )
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
