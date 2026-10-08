#!/usr/bin/env python3
"""Validate and submit a contained Docker research job on the dedicated H100 host."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.publication_attestation import (  # noqa: E402
    verify_publication_claim_attestation,
)

# The archived memory interface. scripts/submit_research_job.py and the batch
# script carry the same rule; tests keep the three copies in parity.
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


BATCH_SCRIPT = PROJECT_ROOT / "infra/slurm/host-single-node/docker-research.sbatch"
RUNTIME = "docker-single-node-discovery-v1"
IMAGE_ID_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_RE = re.compile(r"^[0-9a-f]{40}$")
MODEL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9.-]{0,79}$")
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
PATH_RE = re.compile(r"^/[A-Za-z0-9._/-]{1,511}$")
JOB_ID_RE = re.compile(r"^[1-9][0-9]{0,19}$")
SUBPATH_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")
LICENSE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+-]{0,63}$")
MAX_SINGLE_JOB_GPU_HOURS = 64.0
PUBLIC_BENCHMARK_CONTAINER_PATH = "/inputs/longmemeval_s_cleaned.json"
PUBLICATION_CAPSULE_CONTAINER_PATH = "/inputs/publication-capsule.json"
PUBLICATION_ATTESTATION_CONTAINER_PATH = "/inputs/publication-capsule-attestation.json"
PUBLICATION_TRUST_STORE_CONTAINER_PATH = "/etc/cotcodec/trust/publication-attestors.json"
CONTROL_MATRIX_CONTAINER_PATH = "/inputs/control-matrix-manifest.json"
PUBLICATION_WAVE_CONTAINER_PATH = "/inputs/publication-wave-contract.json"
STUDY_ARTIFACT_CONTAINER_PATH = "/inputs/study-artifact.json"
PUBLIC_BENCHMARK_COMMAND_OPTIONS = (
    "--public-benchmark-path",
    "--longmemeval-path",
)
MAX_PUBLIC_BENCHMARK_BYTES = 100 * 1024**3
MAX_STUDY_ARTIFACT_BYTES = 512 * 1024**2
ALLOWED_RUN_ROOTS = (
    Path("/home/kevin/cotcodec-runs"),
    Path("/shared/cotcodec/runs"),
)
SEED_OPTIONS = ("--seeds", "--seed", "--assignment-seeds", "--assignment-seed")
SEED_BINDING_FLAGS = ("--seeds", "--seed", "--assignment-seeds")
DETERMINISTIC_RANDOMNESS_CONTRACTS = ("deterministic", "deterministic-all-serve")
RANDOMNESS_CONTRACTS = ("assignment-seed-matrix", *DETERMINISTIC_RANDOMNESS_CONTRACTS)
# default reproduces the original container flags exactly; see the batch script.
CONTAINER_PROFILES = ("default", "vllm", "large-cpu-mem")
REASON_MIN_CHARS = 20
REASON_MAX_CHARS = 500
# The batch script exits with this status (EX_TEMPFAIL) when a compute process
# already holds an allocated GPU and the manifest did not allow sharing.
FOREIGN_GPU_PROCESS_EXIT_CODE = 75


def _verify_claim_admission_files(
    claim: dict[str, Any], command: list[str]
) -> dict[str, Any]:
    """Cryptographically verify the exact host-side claim before sbatch admission."""

    capsule = claim["publication_capsule"]
    attestation = claim["publication_attestation"]
    matrix = claim["control_matrix"]
    wave_contract = claim["wave"]
    wave_path = Path(wave_contract["host_path"])
    try:
        wave = json.loads(wave_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("publication wave is unreadable during submission") from exc
    if not isinstance(wave, dict):
        raise ValueError("publication wave must contain one JSON object")
    experiment_path = (PROJECT_ROOT / command[2]).resolve(strict=True)
    receipt = verify_publication_claim_attestation(
        capsule_path=Path(capsule["host_path"]),
        matrix_path=Path(matrix["host_path"]),
        experiment_path=experiment_path,
        wave=wave,
        batch_script_path=BATCH_SCRIPT,
        attestation_path=Path(attestation["host_path"]),
        trust_store_path=Path(attestation["trust_store_host_path"]),
        expected_trust_store_sha256=attestation["trust_store_sha256"],
    )
    bindings = receipt["bindings"]
    expected = {
        "capsule_sha256": capsule["capsule_sha256"],
        "capsule_file_sha256": capsule["file_sha256"],
        "control_matrix_sha256": matrix["matrix_sha256"],
        "control_matrix_file_sha256": matrix["file_sha256"],
        "wave_sha256": wave_contract["wave_sha256"],
        "wave_file_sha256": wave_contract["file_sha256"],
        "batch_script_sha256": _sha256_file(BATCH_SCRIPT),
    }
    for field, value in expected.items():
        if bindings.get(field) != value:
            raise ValueError(f"signed publication claim field {field} drifted")
    if receipt["key_id"] != attestation["key_id"]:
        raise ValueError("signed publication claim attestor drifted")
    return receipt


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _integer(mapping: dict[str, Any], key: str, minimum: int, maximum: int) -> int:
    value = mapping.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
        raise ValueError(f"{key} must be an integer in [{minimum}, {maximum}]")
    return value


def _safe_absolute_path(value: Any, field: str) -> str:
    if not isinstance(value, str) or not PATH_RE.fullmatch(value) or ".." in Path(value).parts:
        raise ValueError(f"{field} must be a simple absolute path without traversal")
    return value


def prepare_run_root(
    manifest: dict[str, Any],
    *,
    allowed_roots: tuple[Path, ...] = ALLOWED_RUN_ROOTS,
) -> Path:
    """Create the validated persistent root before Slurm opens its output file."""

    requested = Path(manifest["run_root"])
    matches = [
        base
        for base in allowed_roots
        if requested == base or requested.is_relative_to(base)
    ]
    if len(matches) != 1:
        raise ValueError("run_root is outside the dedicated persistent run roots")
    base = matches[0]
    if not base.is_dir() or base.is_symlink():
        raise ValueError("persistent run-root base is missing, not a directory, or a symlink")
    current = base
    for part in requested.relative_to(base).parts:
        current = current / part
        if current.exists():
            if not current.is_dir() or current.is_symlink():
                raise ValueError("run_root contains a non-directory or symlink component")
        else:
            current.mkdir(mode=0o750)
    return requested


def _validate_command(value: Any) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or len(value) > 64
        or not all(
            isinstance(argument, str)
            and argument
            and "\x00" not in argument
            and "\n" not in argument
            for argument in value
        )
    ):
        raise ValueError("command must be an argv list of 1-64 nonempty strings")
    return value


def _reason(value: Any, field: str) -> str:
    if (
        not isinstance(value, str)
        or value != value.strip()
        or not REASON_MIN_CHARS <= len(value) <= REASON_MAX_CHARS
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise ValueError(
            f"{field} must be a single-line explanation of {REASON_MIN_CHARS}-"
            f"{REASON_MAX_CHARS} characters without surrounding whitespace"
        )
    return value


def _validate_seed_binding(value: Any) -> dict[str, str] | None:
    if value is None:
        return None
    if (
        not isinstance(value, dict)
        or set(value) != {"flag"}
        or value["flag"] not in SEED_BINDING_FLAGS
    ):
        raise ValueError(
            "seed_binding must be exactly {flag: " + " | ".join(SEED_BINDING_FLAGS) + "}"
        )
    return {"flag": value["flag"]}


def seed_option_abbreviation(argument: str) -> str | None:
    """Return a long option that argparse would expand to a seed option, or None.

    argparse accepts any unambiguous prefix of a long option by default
    (allow_abbrev=True), so ``--see 7`` after the bound seeds would replace them.
    """

    head = argument.split("=", 1)[0]
    if (
        head.startswith("--")
        and len(head) > 2
        and head not in SEED_OPTIONS
        and any(option.startswith(head) for option in SEED_OPTIONS)
    ):
        return head
    return None


def _validate_seed_execution(
    command: list[str],
    seeds: list[int],
    randomness_contract: str,
    seed_binding: dict[str, str] | None,
) -> None:
    """Require every declared seed to reach the workload through one declared flag."""

    abbreviated = [
        head for head in map(seed_option_abbreviation, command) if head is not None
    ]
    if abbreviated:
        raise ValueError(
            f"seed options must be spelled in full; argparse would expand {abbreviated[0]} "
            "to a seed option"
        )
    inline = [
        argument
        for argument in command
        if "=" in argument and argument.split("=", 1)[0] in SEED_OPTIONS
    ]
    if inline:
        raise ValueError("seed options must be separate argv elements, not --option=value")
    if randomness_contract in DETERMINISTIC_RANDOMNESS_CONTRACTS:
        if seeds:
            raise ValueError("deterministic jobs cannot declare seeds")
        if seed_binding is not None:
            raise ValueError("deterministic jobs cannot declare seed_binding")
        if any(option in command for option in SEED_OPTIONS):
            raise ValueError("deterministic jobs cannot execute seed options")
        return
    if seed_binding is None:
        raise ValueError(
            "manifest declares seeds without seed_binding; bind them with "
            "seed_binding.flag or use a deterministic randomness_contract with no seeds"
        )
    flag = seed_binding["flag"]
    if command.count(flag) != 1 or any(
        option in command for option in SEED_OPTIONS if option != flag
    ):
        raise ValueError(
            f"command must pass the manifest seeds through exactly one {flag} "
            "and no other seed option"
        )
    executed: list[str] = []
    for argument in command[command.index(flag) + 1 :]:
        if argument.startswith("--"):
            break
        executed.append(argument)
    if executed != [str(seed) for seed in seeds]:
        raise ValueError(
            f"command seeds {executed} after {flag} do not match manifest seeds {seeds}"
        )


def _validate_model(model: Any) -> dict[str, Any]:
    """Validate a pinned checkpoint or an explicit, justified no-model declaration."""

    if not isinstance(model, dict):
        raise ValueError(
            "model must be a mapping; a job without a checkpoint declares "
            "model: {kind: none, reason: ...}"
        )
    if "kind" in model:
        if model["kind"] != "none" or set(model) != {"kind", "reason"}:
            raise ValueError("model.kind may only be none, with exactly kind and reason fields")
        return {"kind": "none", "reason": _reason(model["reason"], "model.reason")}
    model_id = model.get("model_id")
    revision = model.get("revision")
    receipt_sha256 = model.get("receipt_sha256")
    artifact_root_sha256 = model.get("artifact_root_sha256")
    if not isinstance(model_id, str) or not MODEL_ID_RE.fullmatch(model_id):
        raise ValueError("model.model_id must be a safe registry model id")
    if model_id == "none":
        raise ValueError("model.model_id none is reserved for model: {kind: none, reason: ...}")
    if not isinstance(revision, str) or not GIT_RE.fullmatch(revision):
        raise ValueError("model.revision must be a pinned 40-hex commit")
    if not isinstance(receipt_sha256, str) or not SHA_RE.fullmatch(receipt_sha256):
        raise ValueError("model.receipt_sha256 must be a 64-hex digest")
    if not isinstance(artifact_root_sha256, str) or not SHA_RE.fullmatch(artifact_root_sha256):
        raise ValueError("model.artifact_root_sha256 must be a 64-hex digest")
    return {
        "cache_host_path": _safe_absolute_path(
            model.get("cache_host_path"), "model.cache_host_path"
        ),
        "model_id": model_id,
        "revision": revision,
        "receipt_sha256": receipt_sha256,
        "artifact_root_sha256": artifact_root_sha256,
    }


def _require_command_input(
    command: list[str],
    *,
    options: tuple[str, ...],
    container_path: str,
) -> None:
    present = [option for option in options if option in command]
    if len(present) != 1 or command.count(present[0]) != 1:
        rendered = " or ".join(options)
        raise ValueError(f"command must contain exactly one of {rendered}")
    option = present[0]
    index = command.index(option)
    if index + 1 >= len(command) or command[index + 1] != container_path:
        raise ValueError(f"{option} must consume the fixed read-only container path")


def _require_exact_option(command: list[str], option: str, value: str) -> None:
    if command.count(option) != 1:
        raise ValueError(f"command must contain exactly one {option}")
    index = command.index(option)
    if index + 1 >= len(command) or command[index + 1] != value:
        raise ValueError(f"{option} differs from the claim admission contract")


def _require_claim_command_schema(
    command: list[str],
    *,
    wave_sha256: str,
    control_id: str,
    system_id: str,
) -> None:
    expected = [
        "python",
        "scripts/run_memory_model_screen.py",
        "experiments/memory/stage1-longmemeval-screen.yaml",
        "--model-root",
        "/model-cache/cotcodec-models",
        "--receipt-root",
        "/model-cache/cotcodec-receipts",
        "--output-dir",
        "/outputs/screen",
        "--memory-bundle",
        "/inputs/memory-selection-bundle.json",
        "--memory-treatment-mode",
        "storage_and_service",
        "--expected-memory-system-id",
        system_id,
        "--evaluation-mode",
        "all-serve-benchmark",
        "--public-benchmark-path",
        PUBLIC_BENCHMARK_CONTAINER_PATH,
        "--require-gates",
        "--publication-capsule",
        PUBLICATION_CAPSULE_CONTAINER_PATH,
        "--publication-capsule-attestation",
        PUBLICATION_ATTESTATION_CONTAINER_PATH,
        "--publication-trust-store",
        PUBLICATION_TRUST_STORE_CONTAINER_PATH,
        "--expected-publication-trust-sha256",
        "__TRUST_STORE_SHA256__",
        "--control-matrix-manifest",
        CONTROL_MATRIX_CONTAINER_PATH,
        "--publication-wave-contract",
        PUBLICATION_WAVE_CONTAINER_PATH,
        "--expected-wave-sha256",
        wave_sha256,
        "--expected-control-id",
        control_id,
        "--expected-system-id",
        system_id,
    ]
    if len(command) != len(expected):
        raise ValueError("claim command differs from the exact registered argv schema")
    for actual, registered in zip(command, expected, strict=True):
        if registered != "__TRUST_STORE_SHA256__" and actual != registered:
            raise ValueError("claim command differs from the exact registered argv schema")
    trust_option = command.index("--expected-publication-trust-sha256")
    if not SHA_RE.fullmatch(command[trust_option + 1]):
        raise ValueError("claim command differs from the exact registered argv schema")


def validate_manifest(
    raw: dict[str, Any], *, verify_claim_files: bool = True
) -> dict[str, Any]:
    if raw.get("runtime") != RUNTIME:
        raise ValueError(f"runtime must be {RUNTIME}")
    name = raw.get("name")
    if not isinstance(name, str) or not NAME_RE.fullmatch(name):
        raise ValueError("name must be a lowercase kebab-case Slurm-safe slug")
    image_id = raw.get("image_id")
    if not isinstance(image_id, str) or not IMAGE_ID_RE.fullmatch(image_id):
        raise ValueError("image_id must be an exact local Docker sha256 image ID")
    git_sha = raw.get("git_sha")
    source_sha256 = raw.get("source_sha256")
    if not isinstance(git_sha, str) or not GIT_RE.fullmatch(git_sha):
        raise ValueError("git_sha must be 40 lowercase hex characters")
    if not isinstance(source_sha256, str) or not SHA_RE.fullmatch(source_sha256):
        raise ValueError("source_sha256 must be 64 lowercase hex characters")

    resources = raw.get("resources")
    budget = raw.get("budget")
    if not isinstance(resources, dict) or not isinstance(budget, dict):
        raise ValueError("resources and budget objects are required")
    if resources.get("gpu_type") != "h100":
        raise ValueError("the dedicated discovery runtime permits only gpu_type=h100")
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
        raise ValueError("budget.max_gpu_hours exceeds the 64 GPU-hour single-job ceiling")
    requested_gpu_hours = gpus * minutes / 60
    if requested_gpu_hours > float(max_gpu_hours):
        raise ValueError(
            f"allocation requests {requested_gpu_hours:.2f} GPU-hours, above budget {max_gpu_hours}"
        )

    randomness_contract = raw.get("randomness_contract", "assignment-seed-matrix")
    if randomness_contract not in RANDOMNESS_CONTRACTS:
        raise ValueError("randomness_contract is unsupported")
    seeds = raw.get("seeds")
    if not isinstance(seeds, list) or not all(
        isinstance(seed, int) and not isinstance(seed, bool) for seed in seeds
    ):
        raise ValueError("seeds must be an integer list")
    if randomness_contract == "assignment-seed-matrix":
        if len(set(seeds)) < 3:
            raise ValueError("seed matrices require at least three distinct integers")
        if len(set(seeds)) != len(seeds):
            raise ValueError("seed matrices cannot repeat a seed")
    seed_binding = _validate_seed_binding(raw.get("seed_binding"))

    model_manifest = _validate_model(raw.get("model"))

    container_profile = raw.get("container_profile")
    if container_profile is not None and container_profile not in CONTAINER_PROFILES:
        raise ValueError("container_profile must be one of " + ", ".join(CONTAINER_PROFILES))
    allow_shared_gpu = raw.get("allow_shared_gpu", False)
    if not isinstance(allow_shared_gpu, bool):
        raise ValueError("allow_shared_gpu must be true or false")
    if allow_shared_gpu:
        shared_gpu_reason = _reason(raw.get("shared_gpu_reason"), "shared_gpu_reason")
    elif raw.get("shared_gpu_reason") is not None:
        raise ValueError("shared_gpu_reason requires allow_shared_gpu: true")

    resume_job_id = raw.get("resume_from_job_id")
    resume_subpath = raw.get("resume_subpath")
    if resume_job_id is None:
        if resume_subpath is not None:
            raise ValueError("resume_subpath requires resume_from_job_id")
        normalized_job_id = None
        normalized_subpath = None
    else:
        normalized_job_id = str(resume_job_id)
        if not JOB_ID_RE.fullmatch(normalized_job_id):
            raise ValueError("resume_from_job_id must be a positive Slurm job id")
        if (
            not isinstance(resume_subpath, str)
            or not SUBPATH_RE.fullmatch(resume_subpath)
            or Path(resume_subpath).is_absolute()
            or ".." in Path(resume_subpath).parts
        ):
            raise ValueError("resume_subpath must be a safe relative artifact directory")
        normalized_subpath = resume_subpath

    command = _validate_command(raw.get("command"))
    # Memory workloads were archived on 2026-10-06; reject them before the
    # seed or bundle checks can produce a misleading error.
    validate_memory_job_admission(
        raw.get("memory_source_admission"),
        command=command,
        has_memory_bundle=raw.get("memory_bundle") is not None,
    )
    _validate_seed_execution(command, seeds, randomness_contract, seed_binding)
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "runtime": RUNTIME,
        "name": name,
        "image_id": image_id,
        "command": command,
        "run_root": _safe_absolute_path(raw.get("run_root"), "run_root"),
        "git_sha": git_sha,
        "source_sha256": source_sha256,
        "randomness_contract": randomness_contract,
        "seeds": seeds,
        "model": model_manifest,
        "gpu_type": "h100",
        "gpus": gpus,
        "cpus": cpus,
        "memory_gb": memory_gb,
        "minutes": minutes,
        "max_gpu_hours": float(max_gpu_hours),
        "batch_script_sha256": _sha256_file(BATCH_SCRIPT),
    }
    # Opt-in fields appear only when declared, so a manifest without them
    # serializes exactly as it did before they existed.
    if seed_binding is not None:
        manifest["seed_binding"] = seed_binding
    if container_profile is not None:
        manifest["container_profile"] = container_profile
    if allow_shared_gpu:
        manifest["allow_shared_gpu"] = True
        manifest["shared_gpu_reason"] = shared_gpu_reason
    if normalized_job_id is not None:
        manifest["resume_from_job_id"] = normalized_job_id
        manifest["resume_subpath"] = normalized_subpath

    memory_bundle = raw.get("memory_bundle")
    if memory_bundle is not None:
        if not isinstance(memory_bundle, dict):
            raise ValueError("memory_bundle must be a mapping")
        bundle_sha256 = memory_bundle.get("sha256")
        if not isinstance(bundle_sha256, str) or not SHA_RE.fullmatch(bundle_sha256):
            raise ValueError("memory_bundle.sha256 must be a 64-hex digest")
        manifest["memory_bundle"] = {
            "host_path": _safe_absolute_path(
                memory_bundle.get("host_path"), "memory_bundle.host_path"
            ),
            "sha256": bundle_sha256,
            "container_path": "/inputs/memory-selection-bundle.json",
        }

    public_benchmark = raw.get("public_benchmark")
    if public_benchmark is not None:
        if not isinstance(public_benchmark, dict):
            raise ValueError("public_benchmark must be a mapping")
        benchmark_sha256 = public_benchmark.get("sha256")
        source_id = public_benchmark.get("source_id")
        revision = public_benchmark.get("revision")
        license_id = public_benchmark.get("license")
        size_bytes = public_benchmark.get("size_bytes")
        if not isinstance(source_id, str) or not MODEL_ID_RE.fullmatch(source_id):
            raise ValueError("public_benchmark.source_id must be a safe artifact id")
        if not isinstance(revision, str) or not GIT_RE.fullmatch(revision):
            raise ValueError("public_benchmark.revision must be a pinned 40-hex commit")
        if not isinstance(license_id, str) or not LICENSE_RE.fullmatch(license_id):
            raise ValueError("public_benchmark.license must be a safe SPDX identifier")
        if not isinstance(benchmark_sha256, str) or not SHA_RE.fullmatch(benchmark_sha256):
            raise ValueError("public_benchmark.sha256 must be a 64-hex digest")
        if (
            not isinstance(size_bytes, int)
            or isinstance(size_bytes, bool)
            or not 1 <= size_bytes <= MAX_PUBLIC_BENCHMARK_BYTES
        ):
            raise ValueError("public_benchmark.size_bytes must be a positive bounded integer")
        container_path = public_benchmark.get("container_path", PUBLIC_BENCHMARK_CONTAINER_PATH)
        if container_path != PUBLIC_BENCHMARK_CONTAINER_PATH:
            raise ValueError("public_benchmark.container_path is fixed by the batch contract")
        _require_command_input(
            command,
            options=PUBLIC_BENCHMARK_COMMAND_OPTIONS,
            container_path=PUBLIC_BENCHMARK_CONTAINER_PATH,
        )
        manifest["public_benchmark"] = {
            "source_id": source_id,
            "revision": revision,
            "license": license_id,
            "host_path": _safe_absolute_path(
                public_benchmark.get("host_path"), "public_benchmark.host_path"
            ),
            "sha256": benchmark_sha256,
            "size_bytes": size_bytes,
            "container_path": PUBLIC_BENCHMARK_CONTAINER_PATH,
        }
    elif PUBLIC_BENCHMARK_CONTAINER_PATH in command:
        raise ValueError("command consumes the public benchmark path without a hash-bound mount")

    study_artifact = raw.get("study_artifact")
    if study_artifact is not None:
        if not isinstance(study_artifact, dict):
            raise ValueError("study_artifact must be a mapping")
        artifact_sha256 = study_artifact.get("sha256")
        source_id = study_artifact.get("source_id")
        source_revision = study_artifact.get("revision")
        license_id = study_artifact.get("license")
        size_bytes = study_artifact.get("size_bytes")
        if not isinstance(source_id, str) or not MODEL_ID_RE.fullmatch(source_id):
            raise ValueError("study_artifact.source_id must be a safe artifact id")
        if not isinstance(source_revision, str) or not GIT_RE.fullmatch(source_revision):
            raise ValueError("study_artifact.revision must be a pinned 40-hex commit")
        if not isinstance(license_id, str) or not LICENSE_RE.fullmatch(license_id):
            raise ValueError("study_artifact.license must be a safe SPDX identifier")
        if not isinstance(artifact_sha256, str) or not SHA_RE.fullmatch(artifact_sha256):
            raise ValueError("study_artifact.sha256 must be a 64-hex digest")
        if (
            not isinstance(size_bytes, int)
            or isinstance(size_bytes, bool)
            or not 1 <= size_bytes <= MAX_STUDY_ARTIFACT_BYTES
        ):
            raise ValueError("study_artifact.size_bytes must be a positive bounded integer")
        if study_artifact.get("container_path", STUDY_ARTIFACT_CONTAINER_PATH) != (
            STUDY_ARTIFACT_CONTAINER_PATH
        ):
            raise ValueError("study_artifact.container_path is fixed by the batch contract")
        _require_command_input(
            command,
            options=("--evidence",),
            container_path=STUDY_ARTIFACT_CONTAINER_PATH,
        )
        _require_exact_option(command, "--expected-evidence-sha256", artifact_sha256)
        manifest["study_artifact"] = {
            "source_id": source_id,
            "revision": source_revision,
            "license": license_id,
            "host_path": _safe_absolute_path(
                study_artifact.get("host_path"), "study_artifact.host_path"
            ),
            "sha256": artifact_sha256,
            "size_bytes": size_bytes,
            "container_path": STUDY_ARTIFACT_CONTAINER_PATH,
        }
    elif STUDY_ARTIFACT_CONTAINER_PATH in command:
        raise ValueError("command consumes the study artifact path without a hash-bound mount")

    claim_admission = raw.get("claim_admission")
    if claim_admission is not None:
        if not isinstance(claim_admission, dict):
            raise ValueError("claim_admission must be a mapping")
        capsule = claim_admission.get("publication_capsule")
        attestation = claim_admission.get("publication_attestation")
        matrix = claim_admission.get("control_matrix")
        wave = claim_admission.get("wave")
        if not all(isinstance(value, dict) for value in (capsule, attestation, matrix, wave)):
            raise ValueError(
                "claim admission requires capsule, attestation, matrix, and wave mappings"
            )
        if memory_bundle is None or public_benchmark is None:
            raise ValueError("claim admission requires hash-bound memory and benchmark inputs")
        if randomness_contract != "deterministic-all-serve":
            raise ValueError("claim admission is restricted to deterministic all-SERVE jobs")
        capsule_file_sha256 = capsule.get("file_sha256")
        capsule_sha256 = capsule.get("capsule_sha256")
        capsule_image_id = capsule.get("image_id")
        capsule_git_sha = capsule.get("git_sha")
        capsule_source_sha256 = capsule.get("source_sha256")
        for field, value in (
            ("publication_capsule.file_sha256", capsule_file_sha256),
            ("publication_capsule.capsule_sha256", capsule_sha256),
        ):
            if not isinstance(value, str) or not SHA_RE.fullmatch(value):
                raise ValueError(f"{field} must be a 64-hex digest")
        if (
            capsule_image_id != image_id
            or capsule_git_sha != git_sha
            or capsule_source_sha256 != source_sha256
        ):
            raise ValueError("publication capsule identity differs from the job manifest")
        attestation_file_sha256 = attestation.get("file_sha256")
        trust_store_sha256 = attestation.get("trust_store_sha256")
        key_id = attestation.get("key_id")
        for field, value in (
            ("publication_attestation.file_sha256", attestation_file_sha256),
            ("publication_attestation.trust_store_sha256", trust_store_sha256),
        ):
            if not isinstance(value, str) or not SHA_RE.fullmatch(value):
                raise ValueError(f"{field} must be a 64-hex digest")
        if not isinstance(key_id, str) or not MODEL_ID_RE.fullmatch(key_id):
            raise ValueError("publication attestation key_id must be a safe identifier")
        matrix_file_sha256 = matrix.get("file_sha256")
        matrix_sha256 = matrix.get("matrix_sha256")
        task_manifest_sha256 = matrix.get("task_manifest_sha256")
        for field, value in (
            ("control_matrix.file_sha256", matrix_file_sha256),
            ("control_matrix.matrix_sha256", matrix_sha256),
            ("control_matrix.task_manifest_sha256", task_manifest_sha256),
        ):
            if not isinstance(value, str) or not SHA_RE.fullmatch(value):
                raise ValueError(f"{field} must be a 64-hex digest")
        wave_sha256 = wave.get("wave_sha256")
        wave_file_sha256 = wave.get("file_sha256")
        wave_host_path = wave.get("host_path")
        control_id = wave.get("control_id")
        system_id = wave.get("system_id")
        if not isinstance(wave_sha256, str) or not SHA_RE.fullmatch(wave_sha256):
            raise ValueError("wave.wave_sha256 must be a 64-hex digest")
        if not isinstance(wave_file_sha256, str) or not SHA_RE.fullmatch(wave_file_sha256):
            raise ValueError("wave.file_sha256 must be a 64-hex digest")
        if not isinstance(control_id, str) or not MODEL_ID_RE.fullmatch(control_id):
            raise ValueError("wave.control_id must be a safe identifier")
        if not isinstance(system_id, str) or not MODEL_ID_RE.fullmatch(system_id):
            raise ValueError("wave.system_id must be a safe identifier")
        if wave.get("eligible_for_primary") is not True:
            raise ValueError("claim wave may include only primary-eligible controls")
        bundle_file_sha256 = wave.get("bundle_file_sha256")
        bundle_semantic_sha256 = wave.get("bundle_semantic_sha256")
        if bundle_file_sha256 != memory_bundle["sha256"]:
            raise ValueError("claim wave memory bundle file digest differs from the mount")
        if not isinstance(bundle_semantic_sha256, str) or not SHA_RE.fullmatch(
            bundle_semantic_sha256
        ):
            raise ValueError("claim wave memory bundle semantic digest is invalid")
        _require_exact_option(command, "--publication-capsule", PUBLICATION_CAPSULE_CONTAINER_PATH)
        _require_exact_option(
            command,
            "--publication-capsule-attestation",
            PUBLICATION_ATTESTATION_CONTAINER_PATH,
        )
        _require_exact_option(
            command, "--publication-trust-store", PUBLICATION_TRUST_STORE_CONTAINER_PATH
        )
        _require_exact_option(
            command,
            "--expected-publication-trust-sha256",
            trust_store_sha256,
        )
        _require_exact_option(command, "--control-matrix-manifest", CONTROL_MATRIX_CONTAINER_PATH)
        _require_exact_option(
            command, "--publication-wave-contract", PUBLICATION_WAVE_CONTAINER_PATH
        )
        _require_exact_option(command, "--expected-wave-sha256", wave_sha256)
        _require_exact_option(command, "--expected-control-id", control_id)
        _require_exact_option(command, "--expected-system-id", system_id)
        _require_claim_command_schema(
            command,
            wave_sha256=wave_sha256,
            control_id=control_id,
            system_id=system_id,
        )
        manifest["claim_admission"] = {
            "publication_capsule": {
                "host_path": _safe_absolute_path(
                    capsule.get("host_path"), "publication_capsule.host_path"
                ),
                "container_path": PUBLICATION_CAPSULE_CONTAINER_PATH,
                "file_sha256": capsule_file_sha256,
                "capsule_sha256": capsule_sha256,
                "image_id": capsule_image_id,
                "git_sha": capsule_git_sha,
                "source_sha256": capsule_source_sha256,
            },
            "publication_attestation": {
                "host_path": _safe_absolute_path(
                    attestation.get("host_path"), "publication_attestation.host_path"
                ),
                "container_path": PUBLICATION_ATTESTATION_CONTAINER_PATH,
                "file_sha256": attestation_file_sha256,
                "trust_store_host_path": _safe_absolute_path(
                    attestation.get("trust_store_host_path"),
                    "publication_attestation.trust_store_host_path",
                ),
                "trust_store_container_path": PUBLICATION_TRUST_STORE_CONTAINER_PATH,
                "trust_store_sha256": trust_store_sha256,
                "key_id": key_id,
            },
            "control_matrix": {
                "host_path": _safe_absolute_path(
                    matrix.get("host_path"), "control_matrix.host_path"
                ),
                "container_path": CONTROL_MATRIX_CONTAINER_PATH,
                "file_sha256": matrix_file_sha256,
                "matrix_sha256": matrix_sha256,
                "task_manifest_sha256": task_manifest_sha256,
            },
            "wave": {
                "host_path": _safe_absolute_path(wave_host_path, "wave.host_path"),
                "container_path": PUBLICATION_WAVE_CONTAINER_PATH,
                "file_sha256": wave_file_sha256,
                "wave_sha256": wave_sha256,
                "control_id": control_id,
                "system_id": system_id,
                "eligible_for_primary": True,
                "bundle_file_sha256": memory_bundle["sha256"],
                "bundle_semantic_sha256": bundle_semantic_sha256,
            },
        }
        if verify_claim_files:
            _verify_claim_admission_files(manifest["claim_admission"], command)
    return manifest


def sbatch_argv(manifest: dict[str, Any], test_only: bool) -> list[str]:
    hours, minutes = divmod(manifest["minutes"], 60)
    command_hex = json.dumps(manifest["command"], separators=(",", ":")).encode().hex()
    manifest_hex = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode().hex()
    model = manifest["model"]
    exported = {
        "COTCODEC_IMAGE_ID": manifest["image_id"],
        "COTCODEC_COMMAND_JSON_HEX": command_hex,
        "COTCODEC_MANIFEST_JSON_HEX": manifest_hex,
        "COTCODEC_RUN_ROOT_HEX": manifest["run_root"].encode().hex(),
        "COTCODEC_GIT_SHA": manifest["git_sha"],
        "COTCODEC_SOURCE_SHA256": manifest["source_sha256"],
        "COTCODEC_RANDOMNESS_CONTRACT": manifest["randomness_contract"],
        "COTCODEC_SEEDS": (
            ":".join(str(seed) for seed in manifest["seeds"]) if manifest["seeds"] else "none"
        ),
        "COTCODEC_EXPECTED_GPUS": str(manifest["gpus"]),
        "COTCODEC_BATCH_SHA256": manifest["batch_script_sha256"],
    }
    if model.get("kind") == "none":
        # The batch script admits a no-model job only through this explicit
        # pair; it never infers one from missing model variables.
        exported["COTCODEC_MODEL_KIND"] = "none"
        exported["COTCODEC_MODEL_ID"] = "none"
    else:
        exported.update(
            {
                "COTCODEC_MODEL_CACHE_HOST_HEX": model["cache_host_path"].encode().hex(),
                "COTCODEC_MODEL_ID": model["model_id"],
                "COTCODEC_MODEL_REVISION": model["revision"],
                "COTCODEC_MODEL_RECEIPT_SHA256": model["receipt_sha256"],
                "COTCODEC_MODEL_ARTIFACT_ROOT": model["artifact_root_sha256"],
            }
        )
    if seed_binding := manifest.get("seed_binding"):
        exported["COTCODEC_SEED_BINDING_FLAG"] = seed_binding["flag"]
    if container_profile := manifest.get("container_profile"):
        exported["COTCODEC_CONTAINER_PROFILE"] = container_profile
    if manifest.get("allow_shared_gpu") is True:
        exported["COTCODEC_ALLOW_SHARED_GPU"] = "true"
    if predecessor := manifest.get("resume_from_job_id"):
        exported["COTCODEC_PREDECESSOR_JOB_ID"] = predecessor
        exported["COTCODEC_RESUME_SUBPATH"] = manifest["resume_subpath"]
    if memory_bundle := manifest.get("memory_bundle"):
        exported["COTCODEC_MEMORY_BUNDLE_HOST_HEX"] = memory_bundle["host_path"].encode().hex()
        exported["COTCODEC_MEMORY_BUNDLE_SHA256"] = memory_bundle["sha256"]
    if public_benchmark := manifest.get("public_benchmark"):
        exported["COTCODEC_PUBLIC_BENCHMARK_HOST_HEX"] = (
            public_benchmark["host_path"].encode().hex()
        )
        exported["COTCODEC_PUBLIC_BENCHMARK_SHA256"] = public_benchmark["sha256"]
        exported["COTCODEC_PUBLIC_BENCHMARK_SIZE"] = str(public_benchmark["size_bytes"])
        exported["COTCODEC_PUBLIC_BENCHMARK_ID"] = public_benchmark["source_id"]
        exported["COTCODEC_PUBLIC_BENCHMARK_REVISION"] = public_benchmark["revision"]
        exported["COTCODEC_PUBLIC_BENCHMARK_LICENSE"] = public_benchmark["license"]
    if study_artifact := manifest.get("study_artifact"):
        exported["COTCODEC_STUDY_ARTIFACT_HOST_HEX"] = (
            study_artifact["host_path"].encode().hex()
        )
        exported["COTCODEC_STUDY_ARTIFACT_SHA256"] = study_artifact["sha256"]
        exported["COTCODEC_STUDY_ARTIFACT_SIZE"] = str(study_artifact["size_bytes"])
        exported["COTCODEC_STUDY_ARTIFACT_ID"] = study_artifact["source_id"]
        exported["COTCODEC_STUDY_ARTIFACT_REVISION"] = study_artifact["revision"]
        exported["COTCODEC_STUDY_ARTIFACT_LICENSE"] = study_artifact["license"]
    if claim_admission := manifest.get("claim_admission"):
        capsule = claim_admission["publication_capsule"]
        attestation = claim_admission["publication_attestation"]
        matrix = claim_admission["control_matrix"]
        wave = claim_admission["wave"]
        exported.update(
            {
                "COTCODEC_PUBLICATION_CAPSULE_HOST_HEX": capsule["host_path"].encode().hex(),
                "COTCODEC_PUBLICATION_CAPSULE_FILE_SHA256": capsule["file_sha256"],
                "COTCODEC_PUBLICATION_CAPSULE_SHA256": capsule["capsule_sha256"],
                "COTCODEC_PUBLICATION_ATTESTATION_HOST_HEX": attestation["host_path"]
                .encode()
                .hex(),
                "COTCODEC_PUBLICATION_ATTESTATION_FILE_SHA256": attestation["file_sha256"],
                "COTCODEC_PUBLICATION_TRUST_STORE_HOST_HEX": attestation["trust_store_host_path"]
                .encode()
                .hex(),
                "COTCODEC_PUBLICATION_TRUST_STORE_SHA256": attestation["trust_store_sha256"],
                "COTCODEC_PUBLICATION_ATTESTOR_KEY_ID": attestation["key_id"],
                "COTCODEC_CONTROL_MATRIX_HOST_HEX": matrix["host_path"].encode().hex(),
                "COTCODEC_CONTROL_MATRIX_FILE_SHA256": matrix["file_sha256"],
                "COTCODEC_CONTROL_MATRIX_SHA256": matrix["matrix_sha256"],
                "COTCODEC_TASK_MANIFEST_SHA256": matrix["task_manifest_sha256"],
                "COTCODEC_CLAIM_WAVE_SHA256": wave["wave_sha256"],
                "COTCODEC_CLAIM_WAVE_HOST_HEX": wave["host_path"].encode().hex(),
                "COTCODEC_CLAIM_WAVE_FILE_SHA256": wave["file_sha256"],
                "COTCODEC_MEMORY_CONTROL_ID": wave["control_id"],
                "COTCODEC_MEMORY_SYSTEM_ID": wave["system_id"],
                "COTCODEC_MEMORY_BUNDLE_SEMANTIC_SHA256": wave["bundle_semantic_sha256"],
            }
        )
    export_argument = ",".join(f"{key}={value}" for key, value in exported.items())
    argv = [
        "sbatch",
        "--parsable",
        "--partition=research",
        "--nodes=1",
        "--ntasks=1",
        f"--job-name={manifest['name']}",
        f"--gres=gpu:{manifest['gpu_type']}:{manifest['gpus']}",
        f"--cpus-per-task={manifest['cpus']}",
        f"--mem={manifest['memory_gb']}G",
        f"--time={hours:02d}:{minutes:02d}:00",
        "--signal=B:USR1@180",
        # One run directory per attempt: the batch script refuses a reused one.
        "--no-requeue",
        f"--output={manifest['run_root']}/slurm-%j.out",
        f"--export={export_argument}",
    ]
    if test_only:
        argv.append("--test-only")
    argv.append(str(BATCH_SCRIPT))
    return argv


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--dry-run-output",
        type=Path,
        help="write the dry-run JSON once to this existing directory",
    )
    parser.add_argument("--test-only", action="store_true")
    args = parser.parse_args()
    if args.dry_run_output is not None and not args.dry_run:
        raise SystemExit("--dry-run-output requires --dry-run")
    raw = yaml.safe_load(args.manifest.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise SystemExit("manifest must contain a YAML object")
    try:
        manifest = validate_manifest(raw)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    argv = sbatch_argv(manifest, args.test_only)
    if args.dry_run:
        rendered = json.dumps(
            {
                "argv": argv,
                "gpu_hours": manifest["gpus"] * manifest["minutes"] / 60,
                "runtime": RUNTIME,
            },
            indent=2,
        )
        if args.dry_run_output is None:
            print(rendered)
        else:
            if not args.dry_run_output.parent.is_dir():
                raise SystemExit("--dry-run-output parent must already exist")
            try:
                with args.dry_run_output.open("x", encoding="utf-8") as stream:
                    stream.write(rendered + "\n")
                    stream.flush()
                    os.fsync(stream.fileno())
            except FileExistsError as exc:
                raise SystemExit("--dry-run-output already exists") from exc
        return
    if not args.test_only:
        try:
            prepare_run_root(manifest)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
    completed = subprocess.run(argv, check=True, capture_output=True, text=True)
    print(completed.stdout.strip())


if __name__ == "__main__":
    main()
