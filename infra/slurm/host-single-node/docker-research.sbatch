#!/usr/bin/env bash
#SBATCH --job-name=cotcodec-docker
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:h100:1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --signal=B:USR1@180
#SBATCH --no-requeue
#SBATCH --output=slurm-%x-%j.out

set -Eeuo pipefail
umask 077

# Exit status 2 is an admission or configuration failure found by this script.
# Exit status 75 (EX_TEMPFAIL) means a compute process already held an allocated
# GPU before the container started; resubmit once the GPU is idle.
foreign_gpu_process_exit_code=75

: "${COTCODEC_IMAGE_ID:?Set an exact local Docker sha256 image ID}"
: "${COTCODEC_COMMAND_JSON_HEX:?Set the hex-encoded JSON argv}"
: "${COTCODEC_MANIFEST_JSON_HEX:?Set the hex-encoded validated manifest}"
: "${COTCODEC_RUN_ROOT_HEX:?Set the hex-encoded persistent job storage path}"
: "${COTCODEC_GIT_SHA:?Set the embedded 40-hex source revision}"
: "${COTCODEC_SOURCE_SHA256:?Set the embedded source archive digest}"
: "${COTCODEC_BATCH_SHA256:?Set the audited batch script digest}"
: "${COTCODEC_MODEL_ID:?Set the reviewed model registry id, or none for a no-model job}"
: "${COTCODEC_EXPECTED_GPUS:?Set the requested H100 count}"
: "${COTCODEC_RANDOMNESS_CONTRACT:?Set the validated randomness contract}"
: "${COTCODEC_SEEDS:?Set the colon-delimited assignment seeds}"

# A job runs without a model checkpoint only when the submitter exported the
# explicit COTCODEC_MODEL_KIND=none for model: {kind: none, reason: ...}.
# Missing model variables never imply it.
model_kind=checkpoint
if [[ "${COTCODEC_MODEL_KIND+set}" == set ]]; then
  if [[ "${COTCODEC_MODEL_KIND}" != none ]]; then
    echo "COTCODEC_MODEL_KIND may only be none" >&2
    exit 2
  fi
  model_kind=none
fi
case "${model_kind}" in
  checkpoint)
    : "${COTCODEC_MODEL_CACHE_HOST_HEX:?Set the hex-encoded model cache path}"
    : "${COTCODEC_MODEL_REVISION:?Set the pinned model revision}"
    : "${COTCODEC_MODEL_RECEIPT_SHA256:?Set the model receipt digest}"
    : "${COTCODEC_MODEL_ARTIFACT_ROOT:?Set the model artifact root}"
    if [[ "${COTCODEC_MODEL_ID}" == none ]]; then
      echo "COTCODEC_MODEL_ID=none requires COTCODEC_MODEL_KIND=none" >&2
      exit 2
    fi
    ;;
  none)
    if [[ "${COTCODEC_MODEL_ID}" != none \
      || "${COTCODEC_MODEL_CACHE_HOST_HEX+set}" == set \
      || "${COTCODEC_MODEL_REVISION+set}" == set \
      || "${COTCODEC_MODEL_RECEIPT_SHA256+set}" == set \
      || "${COTCODEC_MODEL_ARTIFACT_ROOT+set}" == set ]]; then
      echo "a no-model job sets COTCODEC_MODEL_ID=none and no model cache, revision or receipt" >&2
      exit 2
    fi
    ;;
esac

if [[ ! "${COTCODEC_IMAGE_ID}" =~ ^sha256:[0-9a-f]{64}$ ]]; then
  echo "COTCODEC_IMAGE_ID must be an exact local Docker image ID" >&2
  exit 2
fi
sha256_values=("${COTCODEC_SOURCE_SHA256}" "${COTCODEC_BATCH_SHA256}")
revision_values=("${COTCODEC_GIT_SHA}")
if [[ "${model_kind}" == checkpoint ]]; then
  sha256_values+=("${COTCODEC_MODEL_RECEIPT_SHA256}" "${COTCODEC_MODEL_ARTIFACT_ROOT}")
  revision_values+=("${COTCODEC_MODEL_REVISION}")
fi
for value in "${sha256_values[@]}"; do
  if [[ ! "${value}" =~ ^[0-9a-f]{64}$ ]]; then
    echo "all SHA-256 values must be lowercase 64-hex digests" >&2
    exit 2
  fi
done
for value in "${revision_values[@]}"; do
  if [[ ! "${value}" =~ ^[0-9a-f]{40}$ ]]; then
    echo "git and model revisions must be lowercase 40-hex commits" >&2
    exit 2
  fi
done
if [[ ! "${COTCODEC_MODEL_ID}" =~ ^[a-z0-9][a-z0-9.-]{0,79}$ ]]; then
  echo "COTCODEC_MODEL_ID is unsafe" >&2
  exit 2
fi
if [[ ! "${COTCODEC_EXPECTED_GPUS}" =~ ^[1-8]$ ]]; then
  echo "COTCODEC_EXPECTED_GPUS must be in [1,8]" >&2
  exit 2
fi

# Container profiles. default keeps the original flags exactly; its /tmp is a
# noexec tmpfs (Docker's default for --tmpfs), so JIT caches that dlopen
# compiled objects (Triton, TorchInductor) must live under /outputs.
container_profile="${COTCODEC_CONTAINER_PROFILE-default}"
case "${container_profile}" in
  default)
    container_tmpfs=/tmp:rw,nosuid,nodev,size=8g
    container_pids_limit=4096
    container_shm_args=()
    ;;
  vllm)
    container_tmpfs=/tmp:rw,exec,nosuid,nodev,size=32g
    container_pids_limit=8192
    container_shm_args=(--shm-size 16g)
    ;;
  large-cpu-mem)
    container_tmpfs=/tmp:rw,exec,nosuid,nodev,size=8g
    container_pids_limit=4096
    container_shm_args=()
    ;;
  *)
    echo "COTCODEC_CONTAINER_PROFILE is not a registered container profile" >&2
    exit 2
    ;;
esac

# The archive (legacy/) is part of the image's source tree but of no live
# workload. Every container gets an empty read-only tmpfs over it, so archived
# code cannot run even when an argv hides its path from the admission rule below
# (for example inside python -c). Docker creates the mount point if an image has
# no legacy/ directory.
archive_mask=/workspace/cotcodec/legacy:ro,noexec,nosuid,nodev,size=64k

allow_shared_gpu=false
if [[ "${COTCODEC_ALLOW_SHARED_GPU+set}" == set ]]; then
  if [[ "${COTCODEC_ALLOW_SHARED_GPU}" != true ]]; then
    echo "COTCODEC_ALLOW_SHARED_GPU may only be true" >&2
    exit 2
  fi
  allow_shared_gpu=true
fi

# Re-check the submitter's admission decisions against the hex-encoded
# manifest: archived memory interface, seed binding, opt-in fields, model kind,
# GPU count, and the Slurm memory limit (no fallback when it is missing).
python - <<'PY'
import json
import os
import re
import sys
from fnmatch import fnmatchcase
from pathlib import PurePosixPath

env = os.environ


def fail(message):
    print(message, file=sys.stderr)
    raise SystemExit(2)


def valid_reason(value):
    return (
        isinstance(value, str)
        and value == value.strip()
        and 20 <= len(value) <= 500
        and not any(ord(character) < 32 or ord(character) == 127 for character in value)
    )


try:
    command = json.loads(bytes.fromhex(env["COTCODEC_COMMAND_JSON_HEX"]))
    manifest = json.loads(bytes.fromhex(env["COTCODEC_MANIFEST_JSON_HEX"]))
except (ValueError, UnicodeDecodeError):
    fail("command or manifest is not valid hex-encoded JSON")
if not isinstance(command, list) or not command or not all(isinstance(arg, str) for arg in command):
    fail("command must be a JSON argv list")
if not isinstance(manifest, dict) or manifest.get("command") != command:
    fail("the manifest does not bind the exported command")

# BEGIN archived-memory-rule: mirrors validate_memory_job_admission in both
# submitters; tests execute this block and keep the three copies in parity.
archived = (
    "memory workloads were archived under legacy/ on 2026-10-06; "
    "restore them from tag legacy-2026-10-06 to submit memory jobs"
)
archive_root = "legacy"
name_patterns = ("run_memory_*", "run_letta*", "*memory_model*", "memory_trials")
archived_entry_points = frozenset(
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
    """.split()
)
memory_flags = ("--memory-bundle", "--memory-treatment-mode", "--expected-memory-system-id")
token_separators = re.compile(r"[\s=,;:'\"`()\[\]{}<>|&$]+")
module_re = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")
script_suffixes = (".py", ".pyc", ".pyw", ".sh")


def name_variants(token):
    variants = [token]
    if token.startswith("-") and not token.startswith("--"):
        variants += [token[1 + cut :] for cut in range(4) if token[1 + cut :]]
    return variants


def name_components(variant):
    components = []
    for part in PurePosixPath(variant).parts:
        if part == "/":
            continue
        components.append(part)
        components += [part[: -len(suffix)] for suffix in script_suffixes if part.endswith(suffix)]
    module = variant[:-3] if variant.endswith(".py") else variant
    if module_re.fullmatch(module):
        components += module.split(".")
    return components


def archived_reference(argument):
    for token in token_separators.split(argument):
        for variant in name_variants(token):
            if (
                variant.startswith("--")
                and len(variant) > 2
                and any(flag.startswith(variant) for flag in memory_flags)
            ):
                return "the archived memory flag " + variant
            for component in name_components(variant):
                if component == archive_root:
                    return "the legacy/ archive"
                if component in archived_entry_points or any(
                    fnmatchcase(component, pattern) for pattern in name_patterns
                ):
                    return "the archived memory entry point " + component
    return None
# END archived-memory-rule

if (
    manifest.get("memory_source_admission") is not None
    or manifest.get("memory_bundle") is not None
    or "COTCODEC_MEMORY_BUNDLE_HOST_HEX" in env
    or "COTCODEC_MEMORY_BUNDLE_SHA256" in env
):
    fail(archived + ": memory inputs are not admitted")
for index, argument in enumerate(command):
    reference = archived_reference(argument)
    if reference is not None:
        fail(f"{archived}: argv[{index}] names {reference}")

# Seed binding.
seed_options = ("--seeds", "--seed", "--assignment-seeds", "--assignment-seed")
binding_flags = ("--seeds", "--seed", "--assignment-seeds")
contract = env["COTCODEC_RANDOMNESS_CONTRACT"]
if manifest.get("randomness_contract") != contract:
    fail("randomness contract differs from the manifest")
binding_flag = env.get("COTCODEC_SEED_BINDING_FLAG")
expected_binding = None if binding_flag is None else {"flag": binding_flag}
if manifest.get("seed_binding") != expected_binding:
    fail("seed binding differs from the manifest")


def seed_abbreviation(argument):
    # argparse expands any unambiguous prefix of a long option (allow_abbrev).
    head = argument.split("=", 1)[0]
    return (
        head.startswith("--")
        and len(head) > 2
        and head not in seed_options
        and any(option.startswith(head) for option in seed_options)
    )


if any(seed_abbreviation(argument) for argument in command):
    fail("seed options must be spelled in full, not as an argparse abbreviation")
if any("=" in argument and argument.split("=", 1)[0] in seed_options for argument in command):
    fail("seed options must be separate argv elements")
if contract in ("deterministic", "deterministic-all-serve"):
    if env["COTCODEC_SEEDS"] != "none" or manifest.get("seeds") != []:
        fail("deterministic jobs cannot declare seeds")
    if binding_flag is not None:
        fail("deterministic jobs cannot declare a seed binding")
    if any(option in command for option in seed_options):
        fail("deterministic jobs cannot execute seed options")
elif contract == "assignment-seed-matrix":
    if not re.fullmatch(r"-?[0-9]+(?::-?[0-9]+)*", env["COTCODEC_SEEDS"]):
        fail("declared seeds must be colon-delimited integers")
    declared = env["COTCODEC_SEEDS"].split(":")
    if declared != [str(seed) for seed in manifest.get("seeds", [])]:
        fail("declared seeds differ from the manifest")
    if len(declared) < 3 or len(declared) != len(set(declared)):
        fail("at least three distinct declared seeds are required")
    if binding_flag not in binding_flags:
        fail("declared seeds require a registered seed binding flag")
    if command.count(binding_flag) != 1 or any(
        option in command for option in seed_options if option != binding_flag
    ):
        fail(f"command does not execute declared seeds via exactly one {binding_flag}")
    executed = []
    for argument in command[command.index(binding_flag) + 1 :]:
        if argument.startswith("--"):
            break
        executed.append(argument)
    if executed != declared:
        fail("executed seeds do not exactly match declared seeds")
else:
    fail("unsupported randomness contract")

# Opt-in container profile and shared-GPU admission.
if manifest.get("container_profile") != env.get("COTCODEC_CONTAINER_PROFILE"):
    fail("container profile differs from the manifest")
if env.get("COTCODEC_ALLOW_SHARED_GPU") == "true":
    if manifest.get("allow_shared_gpu") is not True or not valid_reason(
        manifest.get("shared_gpu_reason")
    ):
        fail("shared-GPU admission differs from the manifest or lacks a reason")
elif "allow_shared_gpu" in manifest or "shared_gpu_reason" in manifest:
    fail("shared-GPU admission differs from the manifest")

# Model kind.
model = manifest.get("model")
if not isinstance(model, dict):
    fail("the manifest has no model block")
if env.get("COTCODEC_MODEL_KIND") == "none":
    if (
        model.get("kind") != "none"
        or set(model) != {"kind", "reason"}
        or not valid_reason(model.get("reason"))
        or env["COTCODEC_MODEL_ID"] != "none"
    ):
        fail("no-model admission differs from the manifest")
elif (
    "kind" in model
    or model.get("model_id") != env["COTCODEC_MODEL_ID"]
    or model.get("revision") != env.get("COTCODEC_MODEL_REVISION")
    or model.get("receipt_sha256") != env.get("COTCODEC_MODEL_RECEIPT_SHA256")
    or model.get("artifact_root_sha256") != env.get("COTCODEC_MODEL_ARTIFACT_ROOT")
    or str(model.get("cache_host_path", "")).encode().hex()
    != env.get("COTCODEC_MODEL_CACHE_HOST_HEX")
):
    fail("model checkpoint differs from the manifest")

# Resources: GPU count and the explicit memory limit.
if manifest.get("gpus") != int(env["COTCODEC_EXPECTED_GPUS"]):
    fail("GPU count differs from the manifest")
memory_gb = manifest.get("memory_gb")
if not isinstance(memory_gb, int) or isinstance(memory_gb, bool) or not 1 <= memory_gb <= 1700:
    fail("manifest memory_gb is invalid")
slurm_memory_mb = env.get("SLURM_MEM_PER_NODE", "")
if not re.fullmatch(r"[1-9][0-9]*", slurm_memory_mb):
    fail("Slurm did not export SLURM_MEM_PER_NODE; refusing to guess the memory limit")
if int(slurm_memory_mb) != memory_gb * 1024:
    fail("SLURM_MEM_PER_NODE differs from the manifest memory_gb")
PY
actual_batch_sha256="$(sha256sum "$0" | cut -d' ' -f1)"
if [[ "${actual_batch_sha256}" != "${COTCODEC_BATCH_SHA256}" ]]; then
  echo "batch script digest does not match the submitted manifest" >&2
  exit 2
fi

decode_host_path() {
  local encoded="$1"
  python - "${encoded}" <<'PY'
import pathlib
import re
import sys

try:
    value = bytes.fromhex(sys.argv[1]).decode("utf-8")
except (ValueError, UnicodeDecodeError) as exc:
    raise SystemExit("host path is not valid UTF-8 hex") from exc
if not re.fullmatch(r"/[A-Za-z0-9._/-]{1,511}", value):
    raise SystemExit("decoded host path is outside the allowlist")
if ".." in pathlib.Path(value).parts:
    raise SystemExit("decoded host path contains traversal")
print(value, end="")
PY
}

run_root_host="$(decode_host_path "${COTCODEC_RUN_ROOT_HEX}")"
run_dir="${run_root_host}/${SLURM_JOB_ID}"
# One run directory per job attempt. A requeued job (the submitter passes
# --no-requeue, but the host default is JobRequeue=1) or a job id reused after a
# Slurm state reset would find an earlier attempt's records here. Writing over
# them would erase that attempt's evidence and let its hard-stop.env or
# container-id.txt mislabel this one, so refuse.
if [[ -e "${run_dir}" || -L "${run_dir}" ]]; then
  echo "run directory ${run_dir} already exists (a requeued or reused job id); refusing to overwrite an earlier attempt's records" >&2
  exit 2
fi
mkdir -p "${run_root_host}"
mkdir "${run_dir}"
chmod 700 "${run_dir}"

# A no-model job mounts no model cache and verifies no receipt.
model_cache_host=""
model_receipt=""
model_cache_mount=()
if [[ "${model_kind}" == checkpoint ]]; then
  model_cache_host="$(decode_host_path "${COTCODEC_MODEL_CACHE_HOST_HEX}")"
  if [[ ! -d "${model_cache_host}" || -L "${model_cache_host}" ]]; then
    echo "model cache must be a regular non-symlink directory" >&2
    exit 2
  fi
  model_snapshot="${model_cache_host}/cotcodec-models/${COTCODEC_MODEL_ID}"
  model_receipt="${model_cache_host}/cotcodec-receipts/${COTCODEC_MODEL_ID}.json"
  if [[ ! -d "${model_snapshot}" || -L "${model_snapshot}" ]]; then
    echo "pinned model snapshot is missing or is a symlink" >&2
    exit 2
  fi
  if [[ ! -f "${model_receipt}" || -L "${model_receipt}" ]]; then
    echo "pinned model receipt is missing or is a symlink" >&2
    exit 2
  fi
  actual_receipt_sha256="$(sha256sum "${model_receipt}" | cut -d' ' -f1)"
  if [[ "${actual_receipt_sha256}" != "${COTCODEC_MODEL_RECEIPT_SHA256}" ]]; then
    echo "model receipt digest mismatch" >&2
    exit 2
  fi
  python - "${model_receipt}" \
    "${COTCODEC_MODEL_ID}" \
    "${COTCODEC_MODEL_REVISION}" \
    "${COTCODEC_MODEL_ARTIFACT_ROOT}" <<'PY'
import json
import pathlib
import sys

receipt = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
expected = {
    "model_id": sys.argv[2],
    "revision": sys.argv[3],
    "artifact_root_sha256": sys.argv[4],
    "mode": "full",
    "publication_eligible": True,
    "trust_remote_code": False,
}
for key, value in expected.items():
    if receipt.get(key) != value:
        raise SystemExit(f"model receipt field {key!r} does not match the manifest")
PY
  model_cache_mount=(--volume "${model_cache_host}:/model-cache:ro")
fi

memory_bundle_host=""
memory_bundle_mount=()
if [[ -n "${COTCODEC_MEMORY_BUNDLE_HOST_HEX:-}" \
  || -n "${COTCODEC_MEMORY_BUNDLE_SHA256:-}" ]]; then
  if [[ -z "${COTCODEC_MEMORY_BUNDLE_HOST_HEX:-}" \
    || ! "${COTCODEC_MEMORY_BUNDLE_SHA256:-}" =~ ^[0-9a-f]{64}$ ]]; then
    echo "both memory bundle path and digest are required" >&2
    exit 2
  fi
  memory_bundle_host="$(decode_host_path "${COTCODEC_MEMORY_BUNDLE_HOST_HEX}")"
  if [[ ! -f "${memory_bundle_host}" || -L "${memory_bundle_host}" ]]; then
    echo "memory bundle must be a regular non-symlink file" >&2
    exit 2
  fi
  actual_bundle_sha256="$(sha256sum "${memory_bundle_host}" | cut -d' ' -f1)"
  if [[ "${actual_bundle_sha256}" != "${COTCODEC_MEMORY_BUNDLE_SHA256}" ]]; then
    echo "memory bundle digest mismatch" >&2
    exit 2
  fi
  memory_bundle_mount=(
    --volume "${memory_bundle_host}:/inputs/memory-selection-bundle.json:ro"
  )
fi

public_benchmark_host=""
public_benchmark_mount=()
if [[ -n "${COTCODEC_PUBLIC_BENCHMARK_HOST_HEX:-}" \
  || -n "${COTCODEC_PUBLIC_BENCHMARK_SHA256:-}" \
  || -n "${COTCODEC_PUBLIC_BENCHMARK_SIZE:-}" \
  || -n "${COTCODEC_PUBLIC_BENCHMARK_ID:-}" \
  || -n "${COTCODEC_PUBLIC_BENCHMARK_REVISION:-}" \
  || -n "${COTCODEC_PUBLIC_BENCHMARK_LICENSE:-}" ]]; then
  if [[ -z "${COTCODEC_PUBLIC_BENCHMARK_HOST_HEX:-}" \
    || ! "${COTCODEC_PUBLIC_BENCHMARK_SHA256:-}" =~ ^[0-9a-f]{64}$ \
    || ! "${COTCODEC_PUBLIC_BENCHMARK_SIZE:-}" =~ ^[1-9][0-9]*$ \
    || ! "${COTCODEC_PUBLIC_BENCHMARK_ID:-}" =~ ^[a-z0-9][a-z0-9.-]{0,79}$ \
    || ! "${COTCODEC_PUBLIC_BENCHMARK_REVISION:-}" =~ ^[0-9a-f]{40}$ \
    || ! "${COTCODEC_PUBLIC_BENCHMARK_LICENSE:-}" =~ ^[A-Za-z0-9][A-Za-z0-9.+-]{0,63}$ ]]; then
    echo "all public benchmark provenance fields are required" >&2
    exit 2
  fi
  public_benchmark_host="$(decode_host_path \
    "${COTCODEC_PUBLIC_BENCHMARK_HOST_HEX}")"
  if [[ ! -f "${public_benchmark_host}" || -L "${public_benchmark_host}" ]]; then
    echo "public benchmark must be a regular non-symlink file" >&2
    exit 2
  fi
  actual_benchmark_sha256="$(sha256sum "${public_benchmark_host}" | cut -d' ' -f1)"
  if [[ "${actual_benchmark_sha256}" != "${COTCODEC_PUBLIC_BENCHMARK_SHA256}" ]]; then
    echo "public benchmark digest mismatch" >&2
    exit 2
  fi
  actual_benchmark_size="$(stat -c '%s' "${public_benchmark_host}")"
  if [[ "${actual_benchmark_size}" != "${COTCODEC_PUBLIC_BENCHMARK_SIZE}" ]]; then
    echo "public benchmark size mismatch" >&2
    exit 2
  fi
  public_benchmark_mount=(
    --volume "${public_benchmark_host}:/inputs/longmemeval_s_cleaned.json:ro"
  )
fi

study_artifact_host=""
study_artifact_mount=()
if [[ -n "${COTCODEC_STUDY_ARTIFACT_HOST_HEX:-}" \
  || -n "${COTCODEC_STUDY_ARTIFACT_SHA256:-}" \
  || -n "${COTCODEC_STUDY_ARTIFACT_SIZE:-}" \
  || -n "${COTCODEC_STUDY_ARTIFACT_ID:-}" \
  || -n "${COTCODEC_STUDY_ARTIFACT_REVISION:-}" \
  || -n "${COTCODEC_STUDY_ARTIFACT_LICENSE:-}" ]]; then
  if [[ -z "${COTCODEC_STUDY_ARTIFACT_HOST_HEX:-}" \
    || ! "${COTCODEC_STUDY_ARTIFACT_SHA256:-}" =~ ^[0-9a-f]{64}$ \
    || ! "${COTCODEC_STUDY_ARTIFACT_SIZE:-}" =~ ^[1-9][0-9]*$ \
    || ! "${COTCODEC_STUDY_ARTIFACT_ID:-}" =~ ^[a-z0-9][a-z0-9.-]{0,79}$ \
    || ! "${COTCODEC_STUDY_ARTIFACT_REVISION:-}" =~ ^[0-9a-f]{40}$ \
    || ! "${COTCODEC_STUDY_ARTIFACT_LICENSE:-}" =~ ^[A-Za-z0-9][A-Za-z0-9.+-]{0,63}$ ]]; then
    echo "all study artifact provenance fields are required" >&2
    exit 2
  fi
  study_artifact_host="$(decode_host_path \
    "${COTCODEC_STUDY_ARTIFACT_HOST_HEX}")"
  if [[ ! -f "${study_artifact_host}" || -L "${study_artifact_host}" ]]; then
    echo "study artifact must be a regular non-symlink file" >&2
    exit 2
  fi
  if [[ "$(sha256sum "${study_artifact_host}" | cut -d' ' -f1)" \
      != "${COTCODEC_STUDY_ARTIFACT_SHA256}" ]]; then
    echo "study artifact digest mismatch" >&2
    exit 2
  fi
  if [[ "$(stat -c '%s' "${study_artifact_host}")" \
      != "${COTCODEC_STUDY_ARTIFACT_SIZE}" ]]; then
    echo "study artifact size mismatch" >&2
    exit 2
  fi
  study_artifact_mount=(
    --volume "${study_artifact_host}:/inputs/study-artifact.json:ro"
  )
fi

publication_capsule_host=""
publication_attestation_host=""
publication_trust_store_host=""
control_matrix_host=""
publication_wave_host=""
claim_admission_mounts=()
if [[ -n "${COTCODEC_PUBLICATION_CAPSULE_HOST_HEX:-}" \
  || -n "${COTCODEC_PUBLICATION_CAPSULE_FILE_SHA256:-}" \
  || -n "${COTCODEC_PUBLICATION_CAPSULE_SHA256:-}" \
  || -n "${COTCODEC_PUBLICATION_ATTESTATION_HOST_HEX:-}" \
  || -n "${COTCODEC_PUBLICATION_ATTESTATION_FILE_SHA256:-}" \
  || -n "${COTCODEC_PUBLICATION_TRUST_STORE_HOST_HEX:-}" \
  || -n "${COTCODEC_PUBLICATION_TRUST_STORE_SHA256:-}" \
  || -n "${COTCODEC_CONTROL_MATRIX_HOST_HEX:-}" \
  || -n "${COTCODEC_CONTROL_MATRIX_FILE_SHA256:-}" \
  || -n "${COTCODEC_CONTROL_MATRIX_SHA256:-}" \
  || -n "${COTCODEC_TASK_MANIFEST_SHA256:-}" \
  || -n "${COTCODEC_CLAIM_WAVE_SHA256:-}" \
  || -n "${COTCODEC_CLAIM_WAVE_HOST_HEX:-}" \
  || -n "${COTCODEC_CLAIM_WAVE_FILE_SHA256:-}" \
  || -n "${COTCODEC_MEMORY_CONTROL_ID:-}" \
  || -n "${COTCODEC_MEMORY_SYSTEM_ID:-}" ]]; then
  for value in \
    "${COTCODEC_PUBLICATION_CAPSULE_FILE_SHA256:-}" \
    "${COTCODEC_PUBLICATION_CAPSULE_SHA256:-}" \
    "${COTCODEC_PUBLICATION_ATTESTATION_FILE_SHA256:-}" \
    "${COTCODEC_PUBLICATION_TRUST_STORE_SHA256:-}" \
    "${COTCODEC_CONTROL_MATRIX_FILE_SHA256:-}" \
    "${COTCODEC_CONTROL_MATRIX_SHA256:-}" \
    "${COTCODEC_TASK_MANIFEST_SHA256:-}" \
    "${COTCODEC_CLAIM_WAVE_SHA256:-}" \
    "${COTCODEC_CLAIM_WAVE_FILE_SHA256:-}"; do
    if [[ ! "${value}" =~ ^[0-9a-f]{64}$ ]]; then
      echo "claim admission digests must be lowercase 64-hex values" >&2
      exit 2
    fi
  done
  if [[ -z "${COTCODEC_PUBLICATION_CAPSULE_HOST_HEX:-}" \
    || -z "${COTCODEC_PUBLICATION_ATTESTATION_HOST_HEX:-}" \
    || -z "${COTCODEC_PUBLICATION_TRUST_STORE_HOST_HEX:-}" \
    || -z "${COTCODEC_CONTROL_MATRIX_HOST_HEX:-}" \
    || -z "${COTCODEC_CLAIM_WAVE_HOST_HEX:-}" \
    || ! "${COTCODEC_MEMORY_CONTROL_ID:-}" =~ ^[a-z0-9][a-z0-9.-]{0,79}$ \
    || ! "${COTCODEC_MEMORY_SYSTEM_ID:-}" =~ ^[a-z0-9][a-z0-9.-]{0,79}$ \
    || -z "${memory_bundle_host}" \
    || "${model_kind}" != checkpoint ]]; then
    echo "claim admission requires every capsule, matrix, control, bundle and model field" >&2
    exit 2
  fi
  publication_capsule_host="$(decode_host_path \
    "${COTCODEC_PUBLICATION_CAPSULE_HOST_HEX}")"
  publication_attestation_host="$(decode_host_path \
    "${COTCODEC_PUBLICATION_ATTESTATION_HOST_HEX}")"
  publication_trust_store_host="$(decode_host_path \
    "${COTCODEC_PUBLICATION_TRUST_STORE_HOST_HEX}")"
  if [[ "${publication_trust_store_host}" \
      != "/etc/cotcodec/trust/publication-attestors.json" ]]; then
    echo "publication trust store must use the administrator-owned fixed path" >&2
    exit 2
  fi
  control_matrix_host="$(decode_host_path "${COTCODEC_CONTROL_MATRIX_HOST_HEX}")"
  publication_wave_host="$(decode_host_path "${COTCODEC_CLAIM_WAVE_HOST_HEX}")"
  for path in \
    "${publication_capsule_host}" \
    "${publication_attestation_host}" \
    "${publication_trust_store_host}" \
    "${control_matrix_host}" \
    "${publication_wave_host}"; do
    if [[ ! -f "${path}" || -L "${path}" ]]; then
      echo "claim admission inputs must be regular non-symlink files" >&2
      exit 2
    fi
  done
  if [[ "$(sha256sum "${publication_capsule_host}" | cut -d' ' -f1)" \
      != "${COTCODEC_PUBLICATION_CAPSULE_FILE_SHA256}" \
    || "$(sha256sum "${publication_attestation_host}" | cut -d' ' -f1)" \
      != "${COTCODEC_PUBLICATION_ATTESTATION_FILE_SHA256}" \
    || "$(sha256sum "${publication_trust_store_host}" | cut -d' ' -f1)" \
      != "${COTCODEC_PUBLICATION_TRUST_STORE_SHA256}" \
    || "$(sha256sum "${control_matrix_host}" | cut -d' ' -f1)" \
      != "${COTCODEC_CONTROL_MATRIX_FILE_SHA256}" \
    || "$(sha256sum "${publication_wave_host}" | cut -d' ' -f1)" \
      != "${COTCODEC_CLAIM_WAVE_FILE_SHA256}" ]]; then
    echo "claim admission file digest mismatch" >&2
    exit 2
  fi
  python - \
    "${publication_capsule_host}" \
    "${control_matrix_host}" \
    "${publication_wave_host}" \
    "${COTCODEC_PUBLICATION_CAPSULE_SHA256}" \
    "${COTCODEC_CONTROL_MATRIX_SHA256}" \
    "${COTCODEC_TASK_MANIFEST_SHA256}" \
    "${COTCODEC_MEMORY_CONTROL_ID}" \
    "${COTCODEC_MEMORY_SYSTEM_ID}" \
    "${COTCODEC_MEMORY_BUNDLE_SEMANTIC_SHA256}" \
    "${COTCODEC_IMAGE_ID}" \
    "${COTCODEC_GIT_SHA}" \
    "${COTCODEC_SOURCE_SHA256}" <<'PY'
import hashlib
import json
import pathlib
import sys


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


capsule = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
matrix = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8"))
wave = json.loads(pathlib.Path(sys.argv[3]).read_text(encoding="utf-8"))
capsule_root = capsule.pop("capsule_sha256", None)
if capsule_root != sys.argv[4] or hashlib.sha256(canonical(capsule).encode()).hexdigest() != capsule_root:
    raise SystemExit("publication capsule semantic root is invalid")
matrix_root = matrix.pop("matrix_sha256", None)
if matrix_root != sys.argv[5] or hashlib.sha256(canonical(matrix).encode()).hexdigest() != matrix_root:
    raise SystemExit("control matrix semantic root is invalid")
wave_root = wave.pop("wave_sha256", None)
if wave_root != __import__("os").environ["COTCODEC_CLAIM_WAVE_SHA256"] or hashlib.sha256(canonical(wave).encode()).hexdigest() != wave_root:
    raise SystemExit("publication wave semantic root is invalid")
if (
    wave.get("publication_capsule_sha256") != capsule_root
    or wave.get("control_matrix_sha256") != matrix_root
    or wave.get("batch_script_sha256") != __import__("os").environ["COTCODEC_BATCH_SHA256"]
    or wave.get("model_id") != __import__("os").environ["COTCODEC_MODEL_ID"]
    or wave.get("model_revision") != __import__("os").environ["COTCODEC_MODEL_REVISION"]
    or wave.get("model_receipt_sha256") != __import__("os").environ["COTCODEC_MODEL_RECEIPT_SHA256"]
    or wave.get("model_artifact_root_sha256") != __import__("os").environ["COTCODEC_MODEL_ARTIFACT_ROOT"]
):
    raise SystemExit("publication wave differs from the submitted runtime")
if (
    capsule.get("status") != "SEALED_PUBLICATION_CAPSULE_CANDIDATE"
    or capsule.get("publication_ready") is not False
    or capsule.get("runtime", {}).get("batch_script_sha256")
    != __import__("os").environ["COTCODEC_BATCH_SHA256"]
):
    raise SystemExit("publication capsule does not bind the active batch script")
source = capsule.get("source", {})
image = capsule.get("image", {})
if (
    image.get("image_id") != sys.argv[10]
    or source.get("git_sha") != sys.argv[11]
    or source.get("archive_sha256") != sys.argv[12]
):
    raise SystemExit("publication capsule differs from the submitted job")
task_source = matrix.get("task_source", {})
if task_source.get("task_manifest_sha256") != sys.argv[6]:
    raise SystemExit("control matrix task manifest differs from the submitted job")
matches = [
    row
    for row in matrix.get("controls", [])
    if isinstance(row, dict) and row.get("control_id") == sys.argv[7]
]
if len(matches) != 1:
    raise SystemExit("claim control is absent or duplicated in the matrix")
control = matches[0]
if (
    control.get("system_id") != sys.argv[8]
    or control.get("bundle_semantic_sha256") != sys.argv[9]
    or control.get("bundle_sha256") != sys.argv[9]
    or control.get("bundle_file_sha256") != __import__("os").environ[
        "COTCODEC_MEMORY_BUNDLE_SHA256"
    ]
    or control.get("eligible_for_primary") is not True
):
    raise SystemExit("claim control identity or eligibility differs from the matrix")
PY
  claim_admission_mounts=(
    --volume "${publication_capsule_host}:/inputs/publication-capsule.json:ro"
    --volume "${publication_attestation_host}:/inputs/publication-capsule-attestation.json:ro"
    --volume "${publication_trust_store_host}:/etc/cotcodec/trust/publication-attestors.json:ro"
    --volume "${control_matrix_host}:/inputs/control-matrix-manifest.json:ro"
    --volume "${publication_wave_host}:/inputs/publication-wave-contract.json:ro"
  )
fi

if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
  echo "Docker is unavailable to the Slurm job user" >&2
  exit 2
fi
if [[ -n "${publication_capsule_host}" ]]; then
  docker run --rm --network none --read-only --cap-drop ALL \
    --security-opt no-new-privileges --user 65534:65534 \
    --volume "${publication_capsule_host}:/inputs/publication-capsule.json:ro" \
    --volume "${publication_attestation_host}:/inputs/publication-capsule-attestation.json:ro" \
    --volume "${publication_trust_store_host}:/etc/cotcodec/trust/publication-attestors.json:ro" \
    --volume "${control_matrix_host}:/inputs/control-matrix-manifest.json:ro" \
    --volume "${publication_wave_host}:/inputs/publication-wave-contract.json:ro" \
    "${COTCODEC_IMAGE_ID}" \
    python scripts/verify_publication_attestation.py \
      --capsule /inputs/publication-capsule.json \
      --matrix /inputs/control-matrix-manifest.json \
      --experiment experiments/memory/stage1-longmemeval-screen.yaml \
      --wave /inputs/publication-wave-contract.json \
      --batch-script infra/slurm/host-single-node/docker-research.sbatch \
      --attestation /inputs/publication-capsule-attestation.json \
      --trust-store /etc/cotcodec/trust/publication-attestors.json \
      --expected-trust-store-sha256 "${COTCODEC_PUBLICATION_TRUST_STORE_SHA256}" \
    > "${run_dir}/publication-attestation-verification.json"
fi
actual_image_id="$(docker image inspect --format '{{.Id}}' "${COTCODEC_IMAGE_ID}")"
if [[ "${actual_image_id}" != "${COTCODEC_IMAGE_ID}" ]]; then
  echo "Docker resolved a different image ID" >&2
  exit 2
fi
image_git="$(docker image inspect --format \
  '{{index .Config.Labels "org.opencontainers.image.revision"}}' "${COTCODEC_IMAGE_ID}")"
image_source="$(docker image inspect --format \
  '{{index .Config.Labels "org.opencontainers.image.source-tree-sha256"}}' \
  "${COTCODEC_IMAGE_ID}")"
if [[ "${image_git}" != "${COTCODEC_GIT_SHA}" \
  || "${image_source}" != "${COTCODEC_SOURCE_SHA256}" ]]; then
  echo "Docker image labels do not match the submitted source provenance" >&2
  exit 2
fi

gpu_devices="${CUDA_VISIBLE_DEVICES:-${SLURM_JOB_GPUS:-}}"
if [[ ! "${gpu_devices}" =~ ^[0-7](,[0-7])*$ ]]; then
  echo "Slurm did not expose a simple physical GPU device list" >&2
  exit 2
fi
gpu_count="$(awk -F, '{print NF}' <<< "${gpu_devices}")"
if [[ "${gpu_count}" -ne "${COTCODEC_EXPECTED_GPUS}" ]]; then
  echo "Slurm GPU allocation does not match the manifest" >&2
  exit 2
fi
if [[ "$(tr ',' '\n' <<< "${gpu_devices}" | sort -u | wc -l | tr -d ' ')" \
  -ne "${gpu_count}" ]]; then
  echo "Slurm GPU device list contains duplicates" >&2
  exit 2
fi
if nvidia-smi -i "${gpu_devices}" --query-gpu=name --format=csv,noheader \
  | grep -qv 'H100'; then
  echo "the Slurm allocation contains a non-H100 GPU" >&2
  exit 2
fi

# Container lifetime. The container is a child of the Docker daemon, not of this
# job, so Slurm cannot end it. When Slurm ends a job (time limit, scancel,
# preemption) it sends TERM to the job's processes and KILL KillWait seconds
# later; a container still running when this script is killed outlives the job
# and keeps its GPU (Slurm 617: 74 GB of GPU 0 for 88 s after the time limit).
# So this script bounds the container's life itself:
#   * a hard-stop timer SIGKILLs the container hard_stop_margin_seconds before
#     the time limit. USR1 comes 180 s before the limit and its checkpoint wait
#     is checkpoint_wait_seconds, so the hard stop falls after that window. The
#     time is fixed here, at start: a later TimeLimit change or a suspension
#     does not move it. The timer also kills the container as soon as this
#     shell is gone, killed alone so that no trap ran;
#   * on TERM it forwards TERM and gives the container at most
#     term_grace_seconds (KillWait minus term_kill_reserve_seconds) to save a
#     signal-triggered checkpoint and exit, then SIGKILLs and removes it before
#     Slurm's KILL. It uses `docker kill`, never `docker stop`, which would wait;
#   * no container is created past the hard stop or after a TERM.
checkpoint_wait_seconds=120
hard_stop_margin_seconds=30
term_kill_reserve_seconds=20
time_left_queried_at="$(date +%s)"
slurm_time_left="$(squeue -h -j "${SLURM_JOB_ID}" -o %L 2>/dev/null || true)"
if ! time_left_seconds="$(python - "${slurm_time_left}" "${hard_stop_margin_seconds}" <<'PY'
import json
import os
import re
import sys

# squeue %L is [days-][hours:]minutes:seconds, or UNLIMITED, NOT_SET or INVALID.
match = re.fullmatch(r"(?:([0-9]+)-)?(?:([0-9]+):)?([0-9]+):([0-9]{2})", sys.argv[1].strip())
if match is None:
    raise SystemExit("Slurm did not report a finite time left for this job; refusing to guess")
days, hours, minutes, seconds = (int(value or 0) for value in match.groups())
left = ((days * 24 + hours) * 60 + minutes) * 60 + seconds
manifest = json.loads(bytes.fromhex(os.environ["COTCODEC_MANIFEST_JSON_HEX"]))
if left > manifest["minutes"] * 60:
    raise SystemExit("Slurm's time left exceeds the manifest minutes")
if left <= int(sys.argv[2]):
    raise SystemExit("the time left does not reach past the container hard stop")
print(left)
PY
)"; then
  exit 2
fi
hard_stop_epoch=$((time_left_queried_at + time_left_seconds - hard_stop_margin_seconds))
hard_stop_at="$(date -u -d "@${hard_stop_epoch}" +%Y-%m-%dT%H:%M:%SZ)"
slurm_kill_wait="$(scontrol show config 2>/dev/null \
  | awk '$1 == "KillWait" {print $3; exit}' || true)"
if [[ "${slurm_kill_wait}" =~ ^[0-9]{1,5}$ ]]; then
  term_grace_seconds=$((10#${slurm_kill_wait} - term_kill_reserve_seconds))
  if [[ "${term_grace_seconds}" -lt 0 ]]; then
    term_grace_seconds=0
  elif [[ "${term_grace_seconds}" -gt "${checkpoint_wait_seconds}" ]]; then
    term_grace_seconds="${checkpoint_wait_seconds}"
  fi
else
  echo "could not read Slurm's KillWait; a TERM will kill the container at once" >&2
  slurm_kill_wait=unknown
  term_grace_seconds=0
fi

if [[ -n "${COTCODEC_PREDECESSOR_JOB_ID:-}" ]]; then
  if [[ ! "${COTCODEC_PREDECESSOR_JOB_ID}" =~ ^[1-9][0-9]{0,19}$ \
    || ! "${COTCODEC_RESUME_SUBPATH:-}" =~ ^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$ \
    || "/${COTCODEC_RESUME_SUBPATH}/" == *"/../"* ]]; then
    echo "resume job or subpath is unsafe" >&2
    exit 2
  fi
  python - "${run_root_host}" "${run_dir}" \
    "${COTCODEC_PREDECESSOR_JOB_ID}" "${COTCODEC_RESUME_SUBPATH}" <<'PY'
import json
import os
import pathlib
import shutil
import sys

run_root = pathlib.Path(sys.argv[1]).resolve()
run_dir = pathlib.Path(sys.argv[2]).resolve()
predecessor_id = sys.argv[3]
subpath = pathlib.Path(sys.argv[4])
predecessor = (run_root / predecessor_id).resolve()
if predecessor.parent != run_root or run_dir.parent != run_root:
    raise SystemExit("resume directory escaped the registered run root")
job_env_path = predecessor / "job.env"
if not job_env_path.is_file():
    raise SystemExit("predecessor job.env is missing")
actual = {}
for line in job_env_path.read_text(encoding="utf-8").splitlines():
    key, separator, value = line.partition("=")
    if separator and key in {
        "git_sha",
        "source_sha256",
        "image_id",
        "batch_script_sha256",
        "model_kind",
        "model_receipt_sha256",
        "model_artifact_root",
        "container_profile",
        "memory_bundle_sha256",
        "memory_bundle_semantic_sha256",
        "public_benchmark_sha256",
        "public_benchmark_size",
        "public_benchmark_revision",
        "study_artifact_sha256",
        "study_artifact_size",
        "study_artifact_id",
        "study_artifact_revision",
        "study_artifact_license",
        "publication_capsule_sha256",
        "publication_attestation_file_sha256",
        "publication_trust_store_sha256",
        "control_matrix_sha256",
        "task_manifest_sha256",
        "claim_wave_sha256",
        "claim_wave_file_sha256",
        "memory_control_id",
        "memory_system_id",
    }:
        actual[key] = value
expected = {
    "git_sha": os.environ["COTCODEC_GIT_SHA"],
    "source_sha256": os.environ["COTCODEC_SOURCE_SHA256"],
    "image_id": os.environ["COTCODEC_IMAGE_ID"],
    "batch_script_sha256": os.environ["COTCODEC_BATCH_SHA256"],
    "model_kind": os.environ.get("COTCODEC_MODEL_KIND", "checkpoint"),
    "model_receipt_sha256": os.environ.get("COTCODEC_MODEL_RECEIPT_SHA256", "none"),
    "model_artifact_root": os.environ.get("COTCODEC_MODEL_ARTIFACT_ROOT", "none"),
    "container_profile": os.environ.get("COTCODEC_CONTAINER_PROFILE", "default"),
    "memory_bundle_sha256": os.environ.get("COTCODEC_MEMORY_BUNDLE_SHA256", "none"),
    "memory_bundle_semantic_sha256": os.environ.get(
        "COTCODEC_MEMORY_BUNDLE_SEMANTIC_SHA256", "none"
    ),
    "public_benchmark_sha256": os.environ.get(
        "COTCODEC_PUBLIC_BENCHMARK_SHA256", "none"
    ),
    "public_benchmark_size": os.environ.get("COTCODEC_PUBLIC_BENCHMARK_SIZE", "none"),
    "public_benchmark_revision": os.environ.get(
        "COTCODEC_PUBLIC_BENCHMARK_REVISION", "none"
    ),
    "study_artifact_sha256": os.environ.get(
        "COTCODEC_STUDY_ARTIFACT_SHA256", "none"
    ),
    "study_artifact_size": os.environ.get("COTCODEC_STUDY_ARTIFACT_SIZE", "none"),
    "study_artifact_id": os.environ.get("COTCODEC_STUDY_ARTIFACT_ID", "none"),
    "study_artifact_revision": os.environ.get(
        "COTCODEC_STUDY_ARTIFACT_REVISION", "none"
    ),
    "study_artifact_license": os.environ.get(
        "COTCODEC_STUDY_ARTIFACT_LICENSE", "none"
    ),
    "publication_capsule_sha256": os.environ.get(
        "COTCODEC_PUBLICATION_CAPSULE_SHA256", "none"
    ),
    "publication_attestation_file_sha256": os.environ.get(
        "COTCODEC_PUBLICATION_ATTESTATION_FILE_SHA256", "none"
    ),
    "publication_trust_store_sha256": os.environ.get(
        "COTCODEC_PUBLICATION_TRUST_STORE_SHA256", "none"
    ),
    "control_matrix_sha256": os.environ.get("COTCODEC_CONTROL_MATRIX_SHA256", "none"),
    "task_manifest_sha256": os.environ.get("COTCODEC_TASK_MANIFEST_SHA256", "none"),
    "claim_wave_sha256": os.environ.get("COTCODEC_CLAIM_WAVE_SHA256", "none"),
    "claim_wave_file_sha256": os.environ.get(
        "COTCODEC_CLAIM_WAVE_FILE_SHA256", "none"
    ),
    "memory_control_id": os.environ.get("COTCODEC_MEMORY_CONTROL_ID", "none"),
    "memory_system_id": os.environ.get("COTCODEC_MEMORY_SYSTEM_ID", "none"),
}
if actual != expected:
    raise SystemExit("predecessor provenance does not match this job")
source = (predecessor / subpath).resolve()
destination = (run_dir / subpath).resolve()
if predecessor not in source.parents or run_dir not in destination.parents:
    raise SystemExit("resume subpath escaped its job directory")
if not source.is_dir() or destination.exists():
    raise SystemExit("resume source is missing or destination already exists")
if any(path.is_symlink() for path in source.rglob("*")):
    raise SystemExit("resume source must not contain symbolic links")
destination.parent.mkdir(parents=True, exist_ok=True)
shutil.copytree(source, destination)
receipt = {
    "schema_version": 1,
    "predecessor_job_id": predecessor_id,
    "resume_subpath": subpath.as_posix(),
    **expected,
}
(run_dir / "resume-receipt.json").write_text(
    json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
PY
fi

python - "${run_dir}" <<'PY'
import json
import os
import pathlib
import sys

run_dir = pathlib.Path(sys.argv[1])
for filename, variable in (
    ("command.json", "COTCODEC_COMMAND_JSON_HEX"),
    ("manifest.json", "COTCODEC_MANIFEST_JSON_HEX"),
):
    payload = json.loads(bytes.fromhex(os.environ[variable]))
    (run_dir / filename).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
PY
if [[ "${model_kind}" == checkpoint ]]; then
  cp "${model_receipt}" "${run_dir}/model-receipt.json"
fi
cp "$0" "${run_dir}/docker-research.sbatch"
if [[ -n "${publication_capsule_host}" ]]; then
  cp "${publication_capsule_host}" "${run_dir}/publication-capsule.json"
  cp "${publication_attestation_host}" "${run_dir}/publication-capsule-attestation.json"
  cp "${publication_trust_store_host}" "${run_dir}/publication-trust-store.json"
  cp "${control_matrix_host}" "${run_dir}/control-matrix-manifest.json"
  cp "${publication_wave_host}" "${run_dir}/publication-wave-contract.json"
fi
if [[ -n "${study_artifact_host}" ]]; then
  cp "${study_artifact_host}" "${run_dir}/study-artifact.json"
fi
docker image inspect "${COTCODEC_IMAGE_ID}" > "${run_dir}/image-inspect.json"
{
  uname -a
  docker version
  docker info
  nvidia-smi -i "${gpu_devices}" \
    --query-gpu=index,name,uuid,memory.total,driver_version --format=csv,noheader
  scontrol show job "${SLURM_JOB_ID}"
} > "${run_dir}/system.txt" 2>&1
{
  echo "job_id=${SLURM_JOB_ID}"
  echo "predecessor_job_id=${COTCODEC_PREDECESSOR_JOB_ID:-none}"
  echo "git_sha=${COTCODEC_GIT_SHA}"
  echo "source_sha256=${COTCODEC_SOURCE_SHA256}"
  echo "image_id=${COTCODEC_IMAGE_ID}"
  echo "batch_script_sha256=${COTCODEC_BATCH_SHA256}"
  echo "model_kind=${model_kind}"
  echo "model_id=${COTCODEC_MODEL_ID}"
  echo "model_revision=${COTCODEC_MODEL_REVISION:-none}"
  echo "model_receipt_sha256=${COTCODEC_MODEL_RECEIPT_SHA256:-none}"
  echo "model_artifact_root=${COTCODEC_MODEL_ARTIFACT_ROOT:-none}"
  echo "memory_bundle_sha256=${COTCODEC_MEMORY_BUNDLE_SHA256:-none}"
  echo "memory_bundle_semantic_sha256=${COTCODEC_MEMORY_BUNDLE_SEMANTIC_SHA256:-none}"
  echo "public_benchmark_id=${COTCODEC_PUBLIC_BENCHMARK_ID:-none}"
  echo "public_benchmark_revision=${COTCODEC_PUBLIC_BENCHMARK_REVISION:-none}"
  echo "public_benchmark_license=${COTCODEC_PUBLIC_BENCHMARK_LICENSE:-none}"
  echo "public_benchmark_sha256=${COTCODEC_PUBLIC_BENCHMARK_SHA256:-none}"
  echo "public_benchmark_size=${COTCODEC_PUBLIC_BENCHMARK_SIZE:-none}"
  echo "study_artifact_id=${COTCODEC_STUDY_ARTIFACT_ID:-none}"
  echo "study_artifact_revision=${COTCODEC_STUDY_ARTIFACT_REVISION:-none}"
  echo "study_artifact_license=${COTCODEC_STUDY_ARTIFACT_LICENSE:-none}"
  echo "study_artifact_sha256=${COTCODEC_STUDY_ARTIFACT_SHA256:-none}"
  echo "study_artifact_size=${COTCODEC_STUDY_ARTIFACT_SIZE:-none}"
  echo "publication_capsule_sha256=${COTCODEC_PUBLICATION_CAPSULE_SHA256:-none}"
  echo "publication_attestation_file_sha256=${COTCODEC_PUBLICATION_ATTESTATION_FILE_SHA256:-none}"
  echo "publication_trust_store_sha256=${COTCODEC_PUBLICATION_TRUST_STORE_SHA256:-none}"
  echo "control_matrix_sha256=${COTCODEC_CONTROL_MATRIX_SHA256:-none}"
  echo "task_manifest_sha256=${COTCODEC_TASK_MANIFEST_SHA256:-none}"
  echo "claim_wave_sha256=${COTCODEC_CLAIM_WAVE_SHA256:-none}"
  echo "claim_wave_file_sha256=${COTCODEC_CLAIM_WAVE_FILE_SHA256:-none}"
  echo "memory_control_id=${COTCODEC_MEMORY_CONTROL_ID:-none}"
  echo "memory_system_id=${COTCODEC_MEMORY_SYSTEM_ID:-none}"
  echo "randomness_contract=${COTCODEC_RANDOMNESS_CONTRACT}"
  echo "seeds=${COTCODEC_SEEDS:-unknown}"
  echo "seed_binding_flag=${COTCODEC_SEED_BINDING_FLAG:-none}"
  echo "container_profile=${container_profile}"
  echo "allow_shared_gpu=${allow_shared_gpu}"
  echo "memory_limit_mb=${SLURM_MEM_PER_NODE}"
  echo "started_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "nodelist=${SLURM_JOB_NODELIST}"
  echo "gpu_devices=${gpu_devices}"
  echo "slurm_time_left_seconds=${time_left_seconds}"
  echo "hard_stop_at=${hard_stop_at}"
  echo "slurm_kill_wait_seconds=${slurm_kill_wait}"
  echo "term_grace_seconds=${term_grace_seconds}"
} > "${run_dir}/job.env"

checkpoint_marker="${run_dir}/checkpoint.ready"
termination_file="${run_dir}/termination.env"
hard_stop_file="${run_dir}/hard-stop.env"
container_name="cotcodec-${SLURM_JOB_ID}"
# create_attempted is true while docker create runs; container_created once it
# has succeeded. Slurm's TERM can kill the CLI mid-create while dockerd still
# finishes the create.
create_attempted=false
container_created=false
docker_client_pid=""
hard_stop_timer_pid=""
termination_reason="starting"
# Who sent the container SIGKILL: none, hard_stop, signal_TERM or exit (the
# exit trap found it still running). The first killer is recorded.
container_killed_by=none
container_killed_at=none
exited_state_re='^exited ([0-9]+)$'
# true only after forward_signal confirmed a fresh, signal-triggered marker in
# this job. A marker that merely exists (stale, periodic or copied) never sets it.
signal_checkpoint_confirmed=false
# The marker record a TERM-triggered checkpoint is checked against. Slurm sends
# TERM to every process of the job, and the attached `docker start` client
# proxies it to the container before this script's trap can run, so the record
# is taken before any TERM can reach the container: just before the container
# starts, and again before each TERM this script sends itself. Empty until then.
term_marker_before=""
term_requested_ns=""

# shellcheck disable=SC2329  # reached through the signal and EXIT traps
write_termination() {
  local exit_code="$1"
  {
    echo "job_id=${SLURM_JOB_ID}"
    echo "reason=${termination_reason}"
    echo "exit_code=${exit_code}"
    echo "finished_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "checkpoint_ready=${signal_checkpoint_confirmed}"
    echo "checkpoint_marker_present=$([[ -f "${checkpoint_marker}" ]] && echo true || echo false)"
    echo "hard_stop_at=${hard_stop_at}"
    echo "container_killed_by=${container_killed_by}"
    echo "container_killed_at=${container_killed_at}"
  } > "${termination_file}"
}

# shellcheck disable=SC2329  # reached through the signal and EXIT traps
container_running() {
  [[ "${container_created}" == true ]] \
    && [[ "$(docker inspect --format '{{.State.Running}}' "${container_name}" 2>/dev/null \
      || echo false)" == true ]]
}

# Identity of the checkpoint marker as device:inode:size:mtime (nanoseconds),
# or "absent". An atomic write (temporary file plus rename) always changes it.
# shellcheck disable=SC2329  # reached through the signal and EXIT traps
checkpoint_marker_identity() {
  if [[ -f "${checkpoint_marker}" && ! -L "${checkpoint_marker}" ]]; then
    stat -c '%d:%i:%s:%.9Y' "${checkpoint_marker}" 2>/dev/null || echo absent
  else
    echo absent
  fi
}

# A marker confirms the checkpoint requested by signal SIG<name> only when all
# of these hold:
#   1. it is a different file version from the one recorded just before the
#      signal was sent (so a stale marker never confirms);
#   2. its mtime is not earlier than that moment;
#   3. its content has the line trigger=SIG<name>, which only the workload's
#      handler for this signal writes (so a periodic save that lands in the same
#      window, or a marker without a trigger, never confirms);
#   4. it did not change while its content was read.
# shellcheck disable=SC2329  # reached through the signal and EXIT traps
checkpoint_marker_is_fresh() {
  local before="$1" requested_ns="$2" signal_name="$3" current mtime_ns content
  current="$(checkpoint_marker_identity)"
  if [[ "${current}" == absent || "${current}" == "${before}" ]]; then
    return 1
  fi
  mtime_ns="${current##*:}"
  mtime_ns="${mtime_ns/./}"
  if [[ ! "${mtime_ns}" =~ ^[0-9]+$ ]] || (( 10#${mtime_ns} < requested_ns )); then
    return 1
  fi
  content="$(timeout 5 head -c 4096 -- "${checkpoint_marker}" 2>/dev/null)" || return 1
  [[ "$(checkpoint_marker_identity)" == "${current}" ]] || return 1
  [[ $'\n'"${content}"$'\n' == *$'\n'"trigger=SIG${signal_name}"$'\n'* ]]
}

# SIG<name> could not be sent: the container is not running (any more). Keep an
# earlier confirmation, since the container is gone because of it. Slurm's TERM
# may still have reached the container through the attached client, and the
# workload may have saved and exited before this trap ran.
# shellcheck disable=SC2329  # reached through the signal and EXIT traps
signal_not_delivered() {
  local signal_name="$1" marker_before="$2" requested_ns="$3"
  if [[ "${signal_checkpoint_confirmed}" == true ]]; then
    return 0
  fi
  if [[ "${signal_name}" == TERM && -n "${requested_ns}" ]] \
    && checkpoint_marker_is_fresh "${marker_before}" "${requested_ns}" TERM; then
    signal_checkpoint_confirmed=true
    termination_reason="signal_TERM_checkpoint_confirmed"
  else
    termination_reason="signal_${signal_name}_not_forwarded"
  fi
}

# Forward SIG<name> to the container and wait up to wait_seconds for a
# confirming marker or the container's exit. After USR1, send TERM if the
# container still runs; after TERM, on_term decides what follows.
# shellcheck disable=SC2329  # reached through the signal and EXIT traps
forward_signal() {
  local signal_name="$1" wait_seconds="$2" marker_before="" requested_ns="" deadline_ns
  if [[ "${signal_name}" == TERM ]]; then
    marker_before="${term_marker_before}"
    requested_ns="${term_requested_ns}"
  fi
  if ! container_running; then
    signal_not_delivered "${signal_name}" "${marker_before}" "${requested_ns}"
    return 0
  fi
  termination_reason="signal_${signal_name}_checkpoint_requested"
  if [[ "${signal_name}" != TERM ]]; then
    # Record the marker and the clock as late as possible but still before the
    # signal: the workload's handler may finish before `docker kill` returns,
    # so a snapshot taken after it could hide the real checkpoint. USR1 comes
    # to this script alone (B:USR1), so nothing reaches the container earlier.
    marker_before="$(checkpoint_marker_identity)"
    requested_ns="$(date +%s%N)"
  fi
  if ! docker kill --signal "${signal_name}" "${container_name}" >/dev/null 2>&1; then
    # Most often the container exited between the check above and this kill.
    signal_not_delivered "${signal_name}" "${marker_before}" "${requested_ns}"
    return 0
  fi
  # Nanoseconds, so the wait is never cut short by a whole-second clock.
  deadline_ns=$(($(date +%s%N) + wait_seconds * 1000000000))
  while true; do
    if checkpoint_marker_is_fresh "${marker_before}" "${requested_ns}" "${signal_name}"; then
      signal_checkpoint_confirmed=true
      termination_reason="signal_${signal_name}_checkpoint_confirmed"
      break
    fi
    if ! container_running; then
      if checkpoint_marker_is_fresh "${marker_before}" "${requested_ns}" "${signal_name}"; then
        signal_checkpoint_confirmed=true
        termination_reason="signal_${signal_name}_checkpoint_confirmed"
      else
        termination_reason="signal_${signal_name}_checkpoint_missing"
      fi
      break
    fi
    if [[ "$(date +%s%N)" -ge "${deadline_ns}" ]]; then
      termination_reason="signal_${signal_name}_checkpoint_timeout"
      break
    fi
    sleep 1
  done
  if [[ "${signal_name}" != TERM ]] && container_running; then
    term_marker_before="$(checkpoint_marker_identity)"
    term_requested_ns="$(date +%s%N)"
    docker kill --signal TERM "${container_name}" >/dev/null 2>&1 || true
  fi
}

# SIGKILL the container if it runs. `docker kill`, not `docker stop`: a stop
# sends TERM and waits, and the workload may ignore TERM.
# shellcheck disable=SC2329  # reached through the signal and EXIT traps
kill_container() {
  local cause="$1"
  if container_running; then
    if [[ "${container_killed_by}" == none ]]; then
      container_killed_by="${cause}"
      container_killed_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    fi
    docker kill --signal KILL "${container_name}" >/dev/null 2>&1 || true
  fi
}

# Print the container's exit code once Docker records it as exited, polling for
# up to $1 seconds; fail when it has not exited by then.
# shellcheck disable=SC2329  # reached through the signal and EXIT traps
container_exit_code() {
  local deadline state
  deadline=$(($(date +%s) + $1))
  while true; do
    state="$(docker inspect --format '{{.State.Status}} {{.State.ExitCode}}' \
      "${container_name}" 2>/dev/null || echo unknown)"
    if [[ "${state}" =~ ${exited_state_re} ]]; then
      echo "${BASH_REMATCH[1]}"
      return 0
    fi
    if [[ "$(date +%s)" -ge "${deadline}" ]]; then
      echo "the container has not exited (${state})" >&2
      return 1
    fi
    sleep 0.5
  done
}

# Whether process $1 is a child of this batch shell: status 0 if it is, 1 if it
# is not, 2 if it cannot be read (gone). Builtins only, since the hard-stop
# timer calls it every few seconds; /proc/<pid>/stat is "pid (comm) state ppid".
# shellcheck disable=SC2329  # reached through the hard-stop timer and EXIT trap
is_batch_shell_child() {
  local stat parent
  { read -r stat < "/proc/$1/stat"; } 2>/dev/null || return 2
  stat="${stat##*") "}"
  stat="${stat#* }"
  parent="${stat%% *}"
  [[ "${parent}" =~ ^[0-9]+$ ]] || return 2
  [[ "${parent}" == "$$" ]]
}

# In the hard-stop timer: whether its parent, the batch shell, is gone. That
# happens when the shell alone is SIGKILLed (the OOM killer, `scancel --batch
# --signal=KILL`): no trap runs, and Slurm already counts the job as over and
# its GPUs as free.
# shellcheck disable=SC2329  # reached through the background hard-stop timer
batch_script_gone() {
  local status=0
  is_batch_shell_child "${BASHPID}" || status=$?
  [[ "${status}" -eq 1 ]]
}

# The hard stop. Runs as a background subshell from just after docker create.
# At hard_stop_epoch, or as soon as the batch shell is gone, it SIGKILLs the
# container, keeps doing so while Docker reports it running, and ends once a
# kill has taken (or once the shell is gone and nothing runs). It ignores USR1
# (that signal belongs to the checkpoint protocol) and dies on TERM, which Slurm
# sends to every process of an ending job; the TERM trap then owns the
# container. Otherwise on_exit stops it.
# shellcheck disable=SC2329  # reached through the background hard-stop timer
hard_stop_timer() {
  local now cause=time_limit killed=false
  # errexit would end this subshell at its first failed command, such as the
  # record write on a full or failing disk, before it had killed anything.
  set +e
  trap '' USR1
  while printf -v now '%(%s)T' -1 && [[ "${now}" -lt "${hard_stop_epoch}" ]]; do
    if batch_script_gone; then
      cause=batch_script_gone
      break
    fi
    if [[ $((hard_stop_epoch - now)) -lt 5 ]]; then
      sleep $((hard_stop_epoch - now))
    else
      sleep 5
    fi
  done
  while true; do
    if container_running; then
      # The record goes first so the batch shell finds it when it sees the
      # container exit. It is best-effort: a failed write never skips the kill.
      if [[ ! -e "${hard_stop_file}" ]]; then
        {
          echo "hard_stop_at=${hard_stop_at}"
          echo "cause=${cause}"
          echo "killed_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        } > "${hard_stop_file}"
      fi
      docker kill --signal KILL "${container_name}" >/dev/null 2>&1
      killed=true
    elif [[ "${killed}" == true ]] || batch_script_gone; then
      return 0
    fi
    sleep 1
  done
}

# After a TERM interrupted docker create before the CLI printed an ID, watch
# for up to $1 seconds for the container that dockerd may still be creating.
# shellcheck disable=SC2329  # reached through the EXIT trap
await_interrupted_create() {
  local deadline
  deadline=$(($(date +%s) + $1))
  while true; do
    if docker inspect --format '{{.Id}}' "${container_name}" >/dev/null 2>&1; then
      container_created=true
      return 0
    fi
    if [[ "$(date +%s)" -ge "${deadline}" ]]; then
      return 0
    fi
    sleep 0.5
  done
}

# Slurm is ending the job and sends KILL KillWait seconds after this TERM, which
# no trap survives. Give the workload term_grace_seconds to save a TERM-triggered
# checkpoint and exit, SIGKILL the container, and exit so on_exit removes it in
# time.
# shellcheck disable=SC2329  # reached through the TERM trap
on_term() {
  local status=143 deadline_ns
  trap '' USR1 TERM
  deadline_ns=$(($(date +%s%N) + term_grace_seconds * 1000000000))
  forward_signal TERM "${term_grace_seconds}"
  # A confirmed checkpoint may still have work after its marker (a receipt, log
  # flushes, an engine shutdown): let the container exit by itself until the
  # grace ends, and only then SIGKILL it.
  while container_running && [[ "$(date +%s%N)" -lt "${deadline_ns}" ]]; do
    sleep 0.5
  done
  kill_container signal_TERM
  if [[ -n "${docker_client_pid}" ]]; then
    status="$(container_exit_code 10)" || status=143
  fi
  exit "${status}"
}

# shellcheck disable=SC2329  # reached through the signal and EXIT traps
on_exit() {
  local exit_code="$?"
  trap '' USR1 TERM
  # Only a timer still running as this shell's child: one that already ended
  # may have had its PID reused by another process of this user.
  if [[ -n "${hard_stop_timer_pid}" ]] && is_batch_shell_child "${hard_stop_timer_pid}"; then
    kill "${hard_stop_timer_pid}" 2>/dev/null || true
  fi
  if [[ -f "${hard_stop_file}" && "${container_killed_by}" == none ]]; then
    container_killed_by=hard_stop
    container_killed_at="$(sed -n 's/^killed_at=//p' "${hard_stop_file}")"
    container_killed_at="${container_killed_at:-unknown}"
  fi
  # A TERM can interrupt the script between docker create and the line that
  # records it; a printed container ID shows that the container exists. Slurm's
  # TERM also reaches the docker CLI and can kill it before it prints the ID,
  # while dockerd still finishes the create; then watch for the container.
  if [[ "${create_attempted}" == true && "${container_created}" != true ]]; then
    if [[ -s "${run_dir}/container-id.txt" ]]; then
      container_created=true
    else
      await_interrupted_create 5
    fi
  fi
  if [[ "${container_created}" == true ]]; then
    kill_container exit
    docker inspect "${container_name}" > "${run_dir}/container-final-inspect.json" \
      2>/dev/null || true
    docker logs "${container_name}" > "${run_dir}/container.log" 2>&1 || true
    docker rm --force "${container_name}" >/dev/null 2>&1 || true
  fi
  if [[ "${termination_reason}" == running ]]; then
    if [[ "${container_killed_by}" == hard_stop && "${exit_code}" -eq 137 ]]; then
      termination_reason="hard_stop"
    elif [[ "${exit_code}" -eq 0 ]]; then
      termination_reason="completed"
    else
      termination_reason="workload_failed"
    fi
  fi
  write_termination "${exit_code}"
}

trap 'forward_signal USR1 "${checkpoint_wait_seconds}"' USR1
trap on_term TERM
trap on_exit EXIT

cpu_list="$(awk '/Cpus_allowed_list/ {print $2}' /proc/self/status)"
if [[ -z "${cpu_list}" ]]; then
  echo "could not determine the Slurm CPU affinity" >&2
  exit 2
fi
# The early admission check proved SLURM_MEM_PER_NODE equals memory_gb * 1024.
memory_limit_mb="${SLURM_MEM_PER_NODE:?Slurm memory limit is unavailable}"
if [[ ! "${memory_limit_mb}" =~ ^[1-9][0-9]*$ ]]; then
  echo "Slurm memory limit is unavailable" >&2
  exit 2
fi
docker_gpu_request="device=${gpu_devices}"
if [[ "${gpu_count}" -gt 1 ]]; then
  # Docker's comma-separated device grammar requires the value itself to retain
  # quotes (the documented CLI form is --gpus '"device=0,1"').
  docker_gpu_request="\"device=${gpu_devices}\""
fi

# $COTCODEC_MODEL_ID is expanded by the container's shell, not this one.
# shellcheck disable=SC2016
if [[ "${model_kind}" == checkpoint ]]; then
  container_script='python scripts/verify_compute_provenance.py > /outputs/provenance-verification.txt && bash scripts/check_compute_env.sh container > /outputs/container-doctor.txt && python scripts/fetch_open_model.py --model-root /model-cache/cotcodec-models --receipt-root /model-cache/cotcodec-receipts verify "$COTCODEC_MODEL_ID" > /outputs/model-verification.txt && exec python scripts/exec_research_workload.py'
else
  container_script='python scripts/verify_compute_provenance.py > /outputs/provenance-verification.txt && bash scripts/check_compute_env.sh container > /outputs/container-doctor.txt && exec python scripts/exec_research_workload.py'
fi

# Foreign-process prolog. Slurm 21.08 here has no device cgroups, so an
# allocation does not prove the GPUs are idle. Refuse to start when any compute
# process already holds an allocated GPU (timing and contention integrity),
# unless the manifest declared allow_shared_gpu with a reason.
count_foreign_gpu_processes() {
  local allocated_uuids
  allocated_uuids="$(nvidia-smi -i "${gpu_devices}" --query-gpu=uuid \
    --format=csv,noheader)" || return 1
  nvidia-smi --query-compute-apps=gpu_uuid,pid,process_name,used_memory \
    --format=csv,noheader > "${run_dir}/gpu-compute-apps-prolog.csv" || return 1
  python - "${run_dir}/gpu-compute-apps-prolog.csv" "${COTCODEC_EXPECTED_GPUS}" \
    "${allocated_uuids}" <<'PY'
import pathlib
import re
import sys

uuid_re = re.compile(r"GPU-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
allocated = [line.strip() for line in sys.argv[3].splitlines() if line.strip()]
if (
    len(allocated) != int(sys.argv[2])
    or len(set(allocated)) != len(allocated)
    or not all(uuid_re.fullmatch(value) for value in allocated)
):
    raise SystemExit("nvidia-smi did not report one UUID per allocated GPU")
foreign = 0
for line in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    row = line.strip()
    if not row or row == "No running processes found":
        continue
    gpu_uuid = row.split(",", 1)[0].strip()
    if not uuid_re.fullmatch(gpu_uuid):
        raise SystemExit("unparseable nvidia-smi compute-apps row")
    if gpu_uuid in allocated:
        foreign += 1
print(foreign)
PY
}

if foreign_gpu_processes="$(count_foreign_gpu_processes)"; then
  :
else
  foreign_gpu_processes=unknown
fi
if [[ "${foreign_gpu_processes}" == 0 ]]; then
  gpu_prolog_decision=exclusive
elif [[ "${allow_shared_gpu}" == true ]]; then
  gpu_prolog_decision=shared_allowed
  echo "allocated GPUs are not verifiably idle (foreign compute processes: ${foreign_gpu_processes}); continuing because the manifest set allow_shared_gpu" >&2
else
  gpu_prolog_decision=refused
fi
{
  echo "foreign_compute_processes=${foreign_gpu_processes}"
  echo "allow_shared_gpu=${allow_shared_gpu}"
  echo "decision=${gpu_prolog_decision}"
} > "${run_dir}/gpu-prolog.env"
if [[ "${gpu_prolog_decision}" == refused ]]; then
  if [[ "${foreign_gpu_processes}" == unknown ]]; then
    termination_reason="gpu_prolog_unavailable"
    echo "could not list GPU compute processes; refusing to start without allow_shared_gpu" >&2
    exit 2
  fi
  termination_reason="foreign_gpu_process"
  echo "refusing to start: ${foreign_gpu_processes} foreign compute process(es) hold allocated GPUs" >&2
  exit "${foreign_gpu_process_exit_code}"
fi

if [[ "$(date +%s)" -ge "${hard_stop_epoch}" ]]; then
  termination_reason="hard_stop_before_start"
  echo "the container hard stop (${hard_stop_at}) has passed; refusing to start" >&2
  exit 2
fi
# --stop-timeout gives a `docker stop` (by an operator, or by dockerd shutting
# down) the same TERM-then-KILL bound as this script's TERM path.
create_attempted=true
create_status=0
docker create \
  --name "${container_name}" \
  --stop-timeout "${term_grace_seconds}" \
  --entrypoint /bin/bash \
  --gpus "${docker_gpu_request}" \
  --network none \
  --read-only \
  --tmpfs "${container_tmpfs}" \
  "${container_shm_args[@]}" \
  --tmpfs "${archive_mask}" \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --pids-limit "${container_pids_limit}" \
  --cpuset-cpus "${cpu_list}" \
  --memory "${memory_limit_mb}m" \
  --memory-swap "${memory_limit_mb}m" \
  --ulimit core=0 \
  --user "$(id -u):$(id -g)" \
  --workdir /workspace/cotcodec \
  --env COTCODEC_COMMAND_JSON_HEX="${COTCODEC_COMMAND_JSON_HEX}" \
  --env COTCODEC_GIT_SHA="${COTCODEC_GIT_SHA}" \
  --env COTCODEC_SOURCE_SHA256="${COTCODEC_SOURCE_SHA256}" \
  --env COTCODEC_EXPECTED_GPUS="${COTCODEC_EXPECTED_GPUS}" \
  --env COTCODEC_OUTPUT_DIR=/outputs \
  --env COTCODEC_CHECKPOINT_MARKER=/outputs/checkpoint.ready \
  --env COTCODEC_MODEL_ID="${COTCODEC_MODEL_ID}" \
  --env USER=cotcodec \
  --env LOGNAME=cotcodec \
  --env HOME=/tmp/home \
  --env XDG_CACHE_HOME=/tmp/cache \
  --env TORCH_HOME=/tmp/torch \
  --env TORCHINDUCTOR_CACHE_DIR=/tmp/torchinductor \
  --env CUBLAS_WORKSPACE_CONFIG=:4096:8 \
  --env HF_HUB_OFFLINE=1 \
  --env TRANSFORMERS_OFFLINE=1 \
  --env HF_HOME=/tmp/huggingface \
  --env PYTHONUNBUFFERED=1 \
  --volume "${run_dir}:/outputs:rw" \
  "${model_cache_mount[@]}" \
  "${memory_bundle_mount[@]}" \
  "${public_benchmark_mount[@]}" \
  "${study_artifact_mount[@]}" \
  "${claim_admission_mounts[@]}" \
  "${COTCODEC_IMAGE_ID}" \
  -lc "${container_script}" \
  > "${run_dir}/container-id.txt" || create_status=$?
# The CLI returned. Only a create whose CLI a signal killed (status above 128;
# create_attempted stays true for on_exit) is watched for. A plain failure, such
# as a name conflict with a leftover container, adopts nothing.
if [[ "${create_status}" -eq 0 ]]; then
  container_created=true
  create_attempted=false
elif [[ "${create_status}" -le 128 ]]; then
  create_attempted=false
fi
if [[ "${create_status}" -ne 0 ]]; then
  echo "docker create failed with status ${create_status}" >&2
  exit "${create_status}"
fi
docker inspect "${container_name}" > "${run_dir}/container-created-inspect.json"
hard_stop_timer &
hard_stop_timer_pid=$!

termination_reason="running"
# Bash runs a trap only after the foreground command returns, so a foreground
# `docker start --attach` would hold SIGUSR1 until the workload had exited.
# Waiting on a background client lets forward_signal run while the workload is
# alive: `wait` returns early (status > 128) after each trapped signal.
term_marker_before="$(checkpoint_marker_identity)"
term_requested_ns="$(date +%s%N)"
docker start --attach "${container_name}" &
docker_client_pid=$!
while true; do
  wait_status=0
  wait "${docker_client_pid}" || wait_status=$?
  if [[ "${wait_status}" -eq 127 ]] || ! kill -0 "${docker_client_pid}" 2>/dev/null; then
    break
  fi
done
# The container's recorded exit code is authoritative; the client's status
# may be a signal-interrupted `wait`.
if ! workload_exit_code="$(container_exit_code 5)"; then
  echo "the Docker client returned before the container exited" >&2
  workload_exit_code=1
fi
if [[ "${termination_reason}" == running ]]; then
  # The hard stop's record with a SIGKILL exit; a container that exited by
  # itself as the timer fired keeps its own outcome.
  if [[ -f "${hard_stop_file}" && "${workload_exit_code}" -eq 137 ]]; then
    termination_reason="hard_stop"
  elif [[ "${workload_exit_code}" -eq 0 ]]; then
    termination_reason="completed"
  else
    termination_reason="workload_failed"
  fi
fi
exit "${workload_exit_code}"
